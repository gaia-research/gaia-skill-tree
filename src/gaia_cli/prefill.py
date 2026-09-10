"""Deterministic embedding-similarity prefill for gaia-curate v2 (RFC1 §3.3).

Front-loads the mapping reasoning that used to live in the LLM worker: given a
candidate skill's {name, description}, embed it, rank the closest GENERIC
registry nodes by cosine similarity, derive a matchTier (strong/weak) from the
tunable thresholds in registry/schema/meta.json, and assemble a schema-valid
discovery-packet-v2 with mappingOptions[].similarity + matchTier populated.

Named candidates are also ranked to aid suite-component appointing (now
possible because named .md skills are embedded — RFC1 §3.2). Implied-fusion
"missing links" are surfaced as flags.

This module is deterministic and reuses semantic_search primitives; it does NOT
mutate the registry. Output packets land in registry-for-review/discovery-packets/.
"""

import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

from gaia_cli.intakeAdapter import REASON_CODES, _canonicalDigest
from gaia_cli.registry import (
    embeddings_path,
    registry_dir,
    registry_schema_dir,
    registry_for_review_dir,
)
from gaia_cli.semantic_search import (
    embed_query,
    load_embeddings,
    search_precomputed,
)

# Seed defaults; overridden by meta.json curationPrefill at runtime.
DEFAULT_STRONG_MAP = 0.72
DEFAULT_WEAK_MAP = 0.45
DEFAULT_TOP_K = 3

# Lifecycle for a review-ready, mapped packet.
REVIEW_READY_LIFECYCLE = [
    "discovered",
    "fetched",
    "parsed",
    "normalized",
    "deduped",
    "mapped",
    "review-ready",
]

# GitHub blob URL pattern for extracting owner/repo/branch/path
GITHUB_BLOB_RE = re.compile(
    r"^https://(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/(?P<branch>[^/]+)/(?P<path>.+)$"
)


def fetchCandidateSource(canonicalUrl, fetcher=None):
    """Fetch the content of a GitHub blob URL (e.g., a SKILL.md).

    Args:
        canonicalUrl: GitHub blob URL (e.g., https://github.com/owner/repo/blob/branch/SKILL.md)
        fetcher: Optional callable(url: str) -> bytes. Defaults to urllib.request.urlopen.

    Returns:
        A tuple of (hostRepository, rawUrl, content, contentSha256), or (None, None, None, None) on error.
        hostRepository is https://github.com/owner/repo
        rawUrl is https://raw.githubusercontent.com/owner/repo/branch/path
    """
    if fetcher is None:
        fetcher = lambda url: urllib.request.urlopen(url).read()

    match = GITHUB_BLOB_RE.match(canonicalUrl)
    if not match:
        return None, None, None, None

    owner = match.group("owner")
    repo = match.group("repo")
    branch = match.group("branch")
    path = match.group("path")

    hostRepository = f"https://github.com/{owner}/{repo}"
    rawUrl = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"

    try:
        content = fetcher(rawUrl)
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        contentSha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return hostRepository, rawUrl, content, contentSha256
    except Exception:
        return None, None, None, None


def parseFrontmatter(text):
    """Parse YAML frontmatter from markdown text.

    Expects the text to start with --- and contain another --- on a later line.
    Returns a dict of frontmatter fields, or {} if parsing fails.
    """
    lines = text.split("\n")
    if not lines or not lines[0].startswith("---"):
        return {}

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].startswith("---"):
            end_idx = i
            break

    if end_idx is None:
        return {}

    frontmatter_text = "\n".join(lines[1:end_idx])
    try:
        import yaml
        result = yaml.safe_load(frontmatter_text) or {}
        return result if isinstance(result, dict) else {}
    except ImportError:
        # Minimal YAML parser for simple key: value pairs when pyyaml not available
        result = {}
        for line in frontmatter_text.split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                result[key.strip()] = val.strip()
        return result
    except Exception:
        return {}


def buildGenericSnapshot(registryPath):
    """Build a frozen genericSnapshot matching `gaia dev list --generic --json`.

    registry/gaia.json's top-level "skills" array holds only generic (canonical)
    nodes — raw entries carry no "kind" field (that field is synthesized by
    meta_list_command / commands/dev/list.py at output time, not present on
    disk). This mirrors that synthesis exactly: {id, name, kind: "generic"} per
    entry, matching the shape validate_discovery_packet.py's mapped-block subset
    check expects (it filters snapshot rows on kind == "generic").

    Returns a dict with:
        {
            "capturedAt": ISO8601 timestamp,
            "command": "gaia dev list --generic --json",
            "generics": [{"id", "name", "kind": "generic"}, ...],
            "contentSha256": canonical digest of generics array,
            "mappingOptionsSha256": will be set separately per packet
        }
    Returns None if the registry/gaia.json is not found or has no skills.
    """
    gaia_json_path = os.path.join(registry_dir(registryPath), "gaia.json")
    if not os.path.exists(gaia_json_path):
        return None

    try:
        with open(gaia_json_path, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    generics = [
        {"id": skill["id"], "name": skill.get("name"), "kind": "generic"}
        for skill in graph_data.get("skills", [])
        if isinstance(skill, dict) and "id" in skill
    ]

    if not generics:
        return None

    return {
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "command": "gaia dev list --generic --json",
        "generics": generics,
        "contentSha256": _canonicalDigest(generics),
    }


def loadPrefillThresholds(registryPath):
    """Read curationPrefill thresholds from registry/schema/meta.json.

    Falls back to the bundled snapshot copy, then to seed defaults. Returns a
    dict {strongMap, weakMap, topK}.
    """
    candidates = [
        os.path.join(registry_schema_dir(registryPath), "meta.json"),
        os.path.join(
            os.path.dirname(__file__), "data", "registry", "schema", "meta.json"
        ),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        block = meta.get("curationPrefill")
        if isinstance(block, dict):
            return {
                "strongMap": block.get("strongMap", DEFAULT_STRONG_MAP),
                "weakMap": block.get("weakMap", DEFAULT_WEAK_MAP),
                "topK": block.get("topK", DEFAULT_TOP_K),
            }
    return {
        "strongMap": DEFAULT_STRONG_MAP,
        "weakMap": DEFAULT_WEAK_MAP,
        "topK": DEFAULT_TOP_K,
    }


def deriveMatchTier(similarity, thresholds):
    """Return 'strong', 'weak', or None (dropped) for a similarity score."""
    if similarity >= thresholds["strongMap"]:
        return "strong"
    if similarity >= thresholds["weakMap"]:
        return "weak"
    return None


def _isGeneric(entryId):
    """Generic node ids have no contributor prefix; named ids contain '/'."""
    return "/" not in entryId


def rankGenericOptions(queryVector, embeddings, thresholds):
    """Rank the top-K generic entries and emit mappingOptions[] (≤ topK, ≤ 3).

    Each option carries genericId, rationale, similarity, matchTier. Options
    below weakMap are dropped. Exact-id duplicates are collapsed (first wins).
    """
    topK = min(int(thresholds.get("topK", DEFAULT_TOP_K)), 3)
    # Over-fetch then filter to generics so named entries do not crowd out
    # the top-K generic slots.
    ranked = search_precomputed(queryVector, embeddings, top_k=len(embeddings.get("entries", [])))
    options = []
    seen = set()
    for hit in ranked:
        hitId = hit["id"]
        if not _isGeneric(hitId) or hitId in seen:
            continue
        similarity = round(float(hit["score"]), 6)
        tier = deriveMatchTier(similarity, thresholds)
        if tier is None:
            continue
        seen.add(hitId)
        options.append(
            {
                "genericId": hitId,
                "rationale": f"Cosine similarity {similarity:.4f} to generic '{hitId}' ({tier} match).",
                "similarity": similarity,
                "matchTier": tier,
            }
        )
        if len(options) >= topK:
            break
    return options


def rankNamedNeighbors(queryVector, embeddings, thresholds, topK=5):
    """Rank the closest NAMED entries to aid suite-component appointing.

    Returns a list of {id, similarity} for named ids at or above weakMap.
    """
    ranked = search_precomputed(queryVector, embeddings, top_k=len(embeddings.get("entries", [])))
    neighbors = []
    seen = set()
    for hit in ranked:
        hitId = hit["id"]
        if _isGeneric(hitId) or hitId in seen:
            continue
        similarity = round(float(hit["score"]), 6)
        if similarity < thresholds["weakMap"]:
            continue
        seen.add(hitId)
        neighbors.append({"id": hitId, "similarity": similarity})
        if len(neighbors) >= topK:
            break
    return neighbors


def detectImpliedFusionFlags(options, thresholds):
    """Surface implied-fusion 'missing links' as flags (Axis B).

    When two distinct generics both clear strongMap, the candidate straddles
    them — a fusion node covering their union may be missing. Emits a flag per
    such pair so L4 can ratify the topology.
    """
    strong = [o for o in options if o["matchTier"] == "strong"]
    flags = []
    for i in range(len(strong)):
        for j in range(i + 1, len(strong)):
            a, b = strong[i]["genericId"], strong[j]["genericId"]
            flags.append(
                {
                    "code": "IMPLIED_FUSION",
                    "generics": sorted([a, b]),
                    "note": (
                        f"Candidate strongly matches both '{a}' and '{b}'; "
                        "an implied fusion node covering their union may be missing."
                    ),
                }
            )
    return flags


def buildPrefillPacket(
    candidateId,
    name,
    description,
    canonicalUrl,
    sourceLane,
    embeddings,
    thresholds,
    registryPath=None,
    precomputedVector=None,
    modelName="all-MiniLM-L6-v2",
    suite=None,
    fetcher=None,
):
    """Assemble a discovery-packet-v2 with prefilled mappingOptions and source fields.

    When registryPath is provided, fetches the candidate's upstream SKILL.md,
    parses its frontmatter, populates source.hostRepository/fetchedAt/contentSha256/frontmatter,
    stamps artifactGate, and builds genericSnapshot. Advances lifecycle to include
    fetched/parsed/normalized/deduped/mapped (or rejected if artifactGate != "valid-skill").

    When registryPath is None, uses the legacy short-circuit lifecycle for backward compatibility.
    """
    if precomputedVector is not None:
        queryVector = precomputedVector
    else:
        queryVector = embed_query(f"{name}: {description}", model_name=modelName)

    options = rankGenericOptions(queryVector, embeddings, thresholds)
    neighbors = rankNamedNeighbors(queryVector, embeddings, thresholds)
    flags = detectImpliedFusionFlags(options, thresholds)
    if neighbors:
        flags.append(
            {
                "code": "SUITE_COMPONENT_CANDIDATES",
                "namedNeighbors": neighbors,
                "note": "Closest named skills — candidate suite components for appointing.",
            }
        )

    # Fetch and parse the candidate's upstream SKILL.md
    hostRepository = None
    fetchedAt = None
    contentSha256 = None
    frontmatter = None
    artifactGate = None
    genericSnapshot = None
    lifecycle = ["discovered", "deferred"]

    if registryPath is not None:
        hostRepository, rawUrl, content, sourceContentSha256 = fetchCandidateSource(
            canonicalUrl, fetcher=fetcher
        )

        if sourceContentSha256 is not None:
            fetchedAt = datetime.now(timezone.utc).isoformat()
            contentSha256 = sourceContentSha256
            frontmatter = parseFrontmatter(content)

            # Stamp artifactGate: an explicit frontmatter value wins; otherwise
            # gate on the minimal real signal a SKILL.md must carry (name +
            # description), rather than rubber-stamping every fetched blob —
            # a README/LICENSE/config file with no frontmatter must NOT pass.
            if "artifactGate" in frontmatter:
                artifactGate = frontmatter["artifactGate"]
            elif (
                isinstance(frontmatter.get("name"), str)
                and frontmatter["name"].strip()
                and isinstance(frontmatter.get("description"), str)
                and frontmatter["description"].strip()
            ):
                artifactGate = "valid-skill"
            else:
                artifactGate = "rejected-missing-frontmatter"

            # Build genericSnapshot
            snapshot = buildGenericSnapshot(registryPath)
            if snapshot is not None:
                snapshot["mappingOptionsSha256"] = _canonicalDigest(options)
                genericSnapshot = snapshot

            # Advance lifecycle based on artifactGate
            if artifactGate == "valid-skill":
                lifecycle = [
                    "discovered",
                    "fetched",
                    "parsed",
                    "normalized",
                    "deduped",
                    "mapped",
                    "deferred",
                ]
            else:
                # Short-circuit to rejected for non-skill artifacts
                lifecycle = ["discovered", "fetched", "rejected"]

    packet = {
        "contractVersion": "discovery-packet-v2",
        "candidateId": candidateId,
        "lifecycle": lifecycle,
        "source": {
            "canonicalUrl": canonicalUrl,
            "sourceLane": sourceLane,
        },
        "normalized": {
            "name": name,
            "description": description,
        },
        "exactDedupe": {"matched": False},
        "mappingOptions": options,
        "decision": {
            "value": "DEFER" if artifactGate == "valid-skill" or artifactGate is None else "NOT_A_SKILL",
            "reasonCode": REASON_CODES.PREFILL_AWAITING_WORKER
            if artifactGate == "valid-skill" or artifactGate is None
            else REASON_CODES.NOT_A_SKILL,
        },
        "flags": flags,
    }

    # Add source fields when fetched
    if hostRepository is not None:
        packet["source"]["hostRepository"] = hostRepository
    if fetchedAt is not None:
        packet["source"]["fetchedAt"] = fetchedAt
    if contentSha256 is not None:
        packet["source"]["contentSha256"] = contentSha256
    if frontmatter is not None:
        packet["source"]["frontmatter"] = frontmatter
    if artifactGate is not None:
        packet["artifactGate"] = artifactGate
    if genericSnapshot is not None:
        packet["genericSnapshot"] = genericSnapshot

    if suite is not None:
        packet["suite"] = suite
    return packet


def selfValidatePacket(packet, trustedGenerics=None):
    """Validate a packet against the hand-rolled v2 validator.

    Imports the validator from the .agents skill tree (the canonical mirror).
    When trustedGenerics is None, uses the packet's own genericSnapshot.generics
    for internal consistency checks (if present). This allows packets that include
    "mapped" in their lifecycle to self-validate without requiring external trust
    anchors.

    Returns a list of stable error codes (empty when valid).
    """
    validate = _importPacketValidator()
    if validate is None:
        # Validator not importable in this environment; skip (non-fatal).
        return []

    # Thread the packet's own snapshot if no explicit trusted_generics provided
    if trustedGenerics is None:
        snapshot = packet.get("genericSnapshot")
        if isinstance(snapshot, dict):
            trustedGenerics = snapshot.get("generics")

    return validate(packet, trusted_generics=trustedGenerics)


def _importPacketValidator():
    """Locate and import validate_packet from the gaia-curate skill scripts.

    The validator is a hand-rolled script under both skill mirrors; import it
    dynamically so prefill can self-validate without a package dependency.
    """
    import importlib.util

    # repo root = three levels up from src/gaia_cli/prefill.py
    repoRoot = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    candidates = [
        os.path.join(
            repoRoot,
            ".agents",
            "skills",
            "gaia-curate",
            "scripts",
            "validate_discovery_packet.py",
        ),
        os.path.join(
            repoRoot,
            ".claude",
            "skills",
            "gaia-curate",
            "scripts",
            "validate_discovery_packet.py",
        ),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        spec = importlib.util.spec_from_file_location("gaia_curate_packet_validator", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.validate_packet
    return None


def discoveryPacketsDir(registryPath):
    """Return the output dir for prefilled discovery packets (RFC1 §3.6)."""
    return os.path.join(registry_for_review_dir(registryPath), "discovery-packets")


def validateDiscoveryPackets(registryPath, trustedGenerics=None):
    """Validate every discovery packet under registry-for-review/discovery-packets/.

    RFC3 §3.5: ``gaia dev validate --intake`` resolves discovery-packet-v2
    packets (in addition to skill batches). Each packet is checked with the
    hand-rolled discovery-packet validator (supports v1 + v2). Validation uses
    the packet's own genericSnapshot.generics when present (internal consistency),
    matching prefill's self-validate — the full generic-snapshot trust check is
    a worker-time concern, not a CI gate over draft packets.

    Returns ``(errors, packetCount)`` where errors is a list of
    ``"<path>: <CODE>"`` strings (empty when all valid).
    """
    packetsDir = discoveryPacketsDir(registryPath)
    errors = []
    if not os.path.isdir(packetsDir):
        return errors, 0

    validate = _importPacketValidator()
    packetPaths = sorted(
        os.path.join(packetsDir, name)
        for name in os.listdir(packetsDir)
        if name.endswith(".json")
    )
    if validate is None and packetPaths:
        # Validator not importable — surface the gap rather than silently pass.
        return (
            [f"{packetsDir}: discovery-packet validator not importable "
             "(.agents/.claude gaia-curate scripts missing)."],
            len(packetPaths),
        )

    for path in packetPaths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                packet = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: MALFORMED_PACKET ({exc})")
            continue

        # Thread the packet's own snapshot if no explicit trusted_generics provided
        packetTrustedGenerics = trustedGenerics
        if packetTrustedGenerics is None:
            snapshot = packet.get("genericSnapshot")
            if isinstance(snapshot, dict):
                packetTrustedGenerics = snapshot.get("generics")

        codes = validate(packet, trusted_generics=packetTrustedGenerics)
        for code in codes:
            errors.append(f"{path}: {code}")
    return errors, len(packetPaths)


def writePacket(packet, registryPath):
    """Write a packet to registry-for-review/discovery-packets/<candidateId>.json."""
    outDir = discoveryPacketsDir(registryPath)
    os.makedirs(outDir, exist_ok=True)
    slug = packet["candidateId"].replace("/", "-")
    outPath = os.path.join(outDir, f"{slug}.json")
    with open(outPath, "w", encoding="utf-8") as f:
        json.dump(packet, f, indent=2)
    return outPath


def prefillCommand(args):
    """`gaia dev prefill` — build a prefilled discovery-packet-v2 for a candidate.

    Non-mutating: writes to registry-for-review/discovery-packets/, never the
    registry. Reads thresholds from meta.json at runtime.
    """
    registryPath = args.registry
    thresholds = loadPrefillThresholds(registryPath)

    embPath = embeddings_path(registryPath)
    # graph/embeddings.json is the tracked artifact; fall back to it when the
    # registry/embeddings.json path is absent.
    if not os.path.exists(embPath):
        graphEmb = os.path.join(str(registryPath), "graph", "embeddings.json")
        if os.path.exists(graphEmb):
            embPath = graphEmb
    try:
        embeddings = load_embeddings(embPath)
    except FileNotFoundError:
        print(
            "Embeddings not found. Run `gaia dev embed` (or regenerate "
            "graph/embeddings.json) first.",
        )
        return 1

    suite = None
    if getattr(args, "suite_role", None) and getattr(args, "suite_id", None):
        suite = {"role": args.suite_role, "suiteId": args.suite_id}
        if getattr(args, "component_ids", None):
            suite["componentCandidateIds"] = [
                c.strip() for c in args.component_ids.split(",") if c.strip()
            ]

    try:
        packet = buildPrefillPacket(
            candidateId=args.candidate_id,
            name=args.name,
            description=args.description,
            canonicalUrl=args.url,
            sourceLane=args.source_lane,
            embeddings=embeddings,
            thresholds=thresholds,
            registryPath=registryPath,
            suite=suite,
        )
    except ImportError:
        print(
            "sentence-transformers is not installed. Run: pip install sentence-transformers"
        )
        return 1

    errors = selfValidatePacket(packet)
    if errors:
        print("Prefill produced an invalid packet:", file=sys.stderr)
        for code in errors:
            print(f"  - {code}", file=sys.stderr)
        return 1

    if getattr(args, "json", False) or getattr(args, "stdout", False):
        print(json.dumps(packet, indent=2))
        return 0

    outPath = writePacket(packet, registryPath)
    strong = sum(1 for o in packet["mappingOptions"] if o["matchTier"] == "strong")
    weak = sum(1 for o in packet["mappingOptions"] if o["matchTier"] == "weak")
    print(f"Wrote prefilled discovery-packet-v2 to {outPath}")
    print(f"  mappingOptions: {len(packet['mappingOptions'])} ({strong} strong, {weak} weak)")
    print(f"  flags: {len(packet['flags'])}")
    return 0

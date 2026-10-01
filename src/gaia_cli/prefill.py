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
import math
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from gaia_cli.curation.assessment import _atomic_write_json, buildAssessment
from gaia_cli.curation.retrieval import (
    canonicalize_model_id,
    embeddingStatus,
    loadRetrievalConfig,
    validateVector,
)
from gaia_cli.intakeAdapter import REASON_CODES, _canonicalDigest
from gaia_cli.registry import (
    embeddings_path,
    generated_output_dir,
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

# Safe candidate identifier regex: alphanumeric, _, ., - segments joined by /
SAFE_CANDIDATE_RE = re.compile(r"^[a-zA-Z0-9_.-]+(/[a-zA-Z0-9_.-]+)*$")


def safeCandidateSlug(candidateId: str) -> str:
    """Validate candidateId format and convert to safe filename slug."""
    if not isinstance(candidateId, str) or not candidateId.strip():
        raise ValueError("Candidate ID must be a non-empty string")
    cleanId = candidateId.strip()
    if not SAFE_CANDIDATE_RE.fullmatch(cleanId) or ".." in cleanId:
        raise ValueError(f"Unsafe or invalid candidateId: {candidateId!r}")
    return cleanId.replace("/", "-")


# GitHub blob URL pattern for extracting owner/repo/branch/path
GITHUB_BLOB_RE = re.compile(
    r"^https://(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/(?P<branch>[^/]+)/(?P<path>.+)$"
)

MAX_FETCH_BYTES = 1024 * 1024  # 1MB
FETCH_TIMEOUT_SECONDS = 15


def defaultFetcher(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Gaia-Curate-Prefill/1.0"},
    )
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_SECONDS) as resp:
        return resp.read(MAX_FETCH_BYTES + 1)


def fetchCandidateSource(canonicalUrl, fetcher=None):
    """Fetch the content of a GitHub blob URL (e.g., a SKILL.md).

    Args:
        canonicalUrl: GitHub blob URL (e.g., https://github.com/owner/repo/blob/branch/SKILL.md)
        fetcher: Optional callable(url: str) -> bytes. Defaults to bounded urllib fetcher.

    Returns:
        A tuple of (hostRepository, rawUrl, content, contentSha256), or (None, None, None, None) on error.
        hostRepository is https://github.com/owner/repo
        rawUrl is https://raw.githubusercontent.com/owner/repo/branch/path
    """
    if fetcher is None:
        fetcher = defaultFetcher

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
        raw_data = fetcher(rawUrl)
        if isinstance(raw_data, bytes):
            if len(raw_data) > MAX_FETCH_BYTES:
                return None, None, None, None
            content = raw_data.decode("utf-8")
        else:
            content = str(raw_data)
            if len(content.encode("utf-8")) > MAX_FETCH_BYTES:
                return None, None, None, None
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

    Prefers canonical source nodes under registry/nodes/ (sorted by id) when present,
    falling back to the legacy registry/gaia.json graph file for backward compatibility.
    This ensures prefill works on fresh checkouts where generated gaia.json is absent.
    If the nodes/ directory exists but is empty, it does not fall back to a stale graph.

    Returns a dict with:
        {
            "capturedAt": ISO8601 timestamp,
            "command": "gaia dev list --generic --json",
            "generics": [{"id", "name", "kind": "generic"}, ...],
            "contentSha256": canonical digest of generics array,
            "mappingOptionsSha256": will be set separately per packet
        }
    Returns None if neither canonical nodes nor gaia.json are found, or contain no skills.
    """
    reg_dir = registry_dir(registryPath)
    nodes_dir = os.path.join(reg_dir, "nodes")
    generics = []

    if os.path.isdir(nodes_dir):
        node_files = sorted(Path(nodes_dir).rglob("*.json"))
        for p in node_files:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("id"), str) and data["id"].strip():
                    generics.append({
                        "id": data["id"],
                        "name": data.get("name"),
                        "kind": "generic",
                    })
            except (OSError, json.JSONDecodeError):
                continue
        seen = set()
        unique_generics = []
        for g in generics:
            if g["id"] not in seen:
                seen.add(g["id"])
                unique_generics.append(g)
        unique_generics.sort(key=lambda x: x["id"])
        generics = unique_generics
    else:
        # Fallback graph legacy when nodes/ directory does not exist
        gaia_json_path = os.path.join(reg_dir, "gaia.json")
        if os.path.exists(gaia_json_path):
            try:
                with open(gaia_json_path, "r", encoding="utf-8") as f:
                    graph_data = json.load(f)
                legacy_generics = [
                    {"id": skill["id"], "name": skill.get("name"), "kind": "generic"}
                    for skill in graph_data.get("skills", [])
                    if isinstance(skill, dict) and isinstance(skill.get("id"), str) and skill["id"].strip()
                ]
                seen = set()
                for g in legacy_generics:
                    if g["id"] not in seen:
                        seen.add(g["id"])
                        generics.append(g)
            except (OSError, json.JSONDecodeError):
                return None

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


def parseAndValidateVector(
    vectorSource,
    expectedModel=None,
    expectedRevision=None,
    expectedDim=None,
):
    """Parse and strictly validate precomputed query vector.

    Note: On the CLI, `--vector FILE` intentionally requires a file path (to keep
    command-line invocations safe, bounded, and free of shell-escaping issues).
    This function additionally accepts in-memory dicts, lists, or JSON strings
    for programmatic and testing convenience.

    Accepts:
      - Filepath containing an envelope or plain list
      - Envelope object: {"model": str, "revision": Optional[str], "vector": list[float]}
      - Plain list: [float, ...] (tied to active artifact)
      - JSON string representation of either

    Rejects non-finite values (inf, -inf, NaN) and booleans.
    Verifies model and revision match active artifact configuration if present.
    Verifies dimensions match expectedDim if provided.
    """
    if isinstance(vectorSource, str):
        if os.path.exists(vectorSource):
            with open(vectorSource, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            try:
                data = json.loads(vectorSource)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Failed to parse vector JSON: {exc}") from exc
    elif isinstance(vectorSource, (dict, list)):
        data = vectorSource
    else:
        raise ValueError("Invalid vector source: must be filepath, JSON string, dict, or list")

    if isinstance(data, dict):
        if "vector" not in data:
            raise ValueError("Precomputed vector envelope missing 'vector' key")
        vec = data["vector"]
        model_in_env = data.get("model")
        rev_in_env = data.get("revision")

        if model_in_env and expectedModel:
            norm_env_model = canonicalize_model_id(model_in_env) or model_in_env
            norm_exp_model = canonicalize_model_id(expectedModel) or expectedModel
            if norm_env_model != norm_exp_model:
                raise ValueError(
                    f"Vector model '{model_in_env}' does not match active artifact model '{expectedModel}'"
                )
        if rev_in_env is not None and expectedRevision is not None and rev_in_env != expectedRevision:
            raise ValueError(
                f"Vector revision '{rev_in_env}' does not match active artifact revision '{expectedRevision}'"
            )
    elif isinstance(data, list):
        vec = data
    else:
        raise ValueError("Precomputed vector must be a JSON object with 'vector' or a list of numbers")

    if not isinstance(vec, (list, tuple)):
        raise ValueError("Vector must be a list of numbers")
    if len(vec) == 0:
        raise ValueError("Vector cannot be empty")

    for idx, val in enumerate(vec):
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val):
            raise ValueError(f"Vector contains invalid or non-finite value at index {idx}: {val}")

    if expectedDim is not None and len(vec) != expectedDim:
        raise ValueError(f"Vector dimension ({len(vec)}) does not match expected dimension ({expectedDim})")

    return [float(x) for x in vec]


def detectImpliedFusionFlags(options, thresholds):
    """Surface multi-generic ambiguity / multi-domain overlap as flags.

    Cosine similarity is a recall hint, not an implied fusion requirement.
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
                        f"Candidate has high semantic similarity to multiple generics ('{a}', '{b}'); "
                        "represents potential ambiguity or multi-domain overlap, not an automatic fusion requirement."
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
    modelName=None,
    suite=None,
    fetcher=None,
    config=None,
    staleStatus=None,
    allowStale=False,
):
    """Assemble a discovery-packet-v2 with prefilled mappingOptions and source fields.

    When registryPath is provided, fetches the candidate's upstream SKILL.md,
    parses its frontmatter, populates source.hostRepository/fetchedAt/contentSha256/frontmatter,
    stamps artifactGate, and builds genericSnapshot. Advances lifecycle to include
    fetched/parsed/normalized/deduped/mapped (or rejected if artifactGate != "valid-skill").

    When registryPath is None, uses the legacy short-circuit lifecycle for backward compatibility.
    """
    effectiveModel = modelName or embeddings.get("model") or "all-MiniLM-L6-v2"
    retrievalConfig = config
    if retrievalConfig is None:
        try:
            retrievalConfig = loadRetrievalConfig(registryPath or ".", modelName=effectiveModel)
        except Exception:
            retrievalConfig = None

    if precomputedVector is not None:
        expected_dim = embeddings.get("dimensions") or (retrievalConfig.get("dimensions") if retrievalConfig else None)
        expected_model = (retrievalConfig.get("modelId") if retrievalConfig else None) or embeddings.get("model")
        expected_rev = retrievalConfig.get("revision") if retrievalConfig else None
        queryVector = parseAndValidateVector(
            precomputedVector,
            expectedModel=expected_model,
            expectedRevision=expected_rev,
            expectedDim=expected_dim,
        )
    else:
        queryVector = embed_query(
            f"{name}: {description}",
            model_name=effectiveModel,
            config=retrievalConfig,
        )

    options = rankGenericOptions(queryVector, embeddings, thresholds)
    neighbors = rankNamedNeighbors(queryVector, embeddings, thresholds)
    flags = detectImpliedFusionFlags(options, thresholds)
    if neighbors:
        flags.append(
            {
                "code": "SUITE_COMPONENT_CANDIDATES",
                "namedNeighbors": neighbors,
                "note": "Nearby named skills by semantic similarity; advisory context only, not a suite declaration or appointing decision.",
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

            has_valid_frontmatter = (
                isinstance(frontmatter.get("name"), str)
                and bool(frontmatter["name"].strip())
                and isinstance(frontmatter.get("description"), str)
                and bool(frontmatter["description"].strip())
            )

            # Stamp artifactGate: Cannot be spoofed by upstream frontmatter 'valid-skill'
            # when name or description is absent/empty.
            if not has_valid_frontmatter:
                artifactGate = "rejected-missing-frontmatter"
            elif "artifactGate" in frontmatter and frontmatter["artifactGate"] != "valid-skill":
                artifactGate = frontmatter["artifactGate"]
            else:
                artifactGate = "valid-skill"

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

    # Add retrieval provenance metadata
    # Never infer revision for legacy unmanifested artifacts
    artifact_config = embeddings.get("config") if isinstance(embeddings.get("config"), dict) else None
    artifact_rev = embeddings.get("revision") or (artifact_config.get("revision") if artifact_config else None)

    retrieval_meta = {
        "model": effectiveModel,
        "revision": artifact_rev,
        "fingerprint": embeddings.get("fingerprint"),
        "thresholds": thresholds,
    }
    if staleStatus or allowStale:
        retrieval_meta["provenance"] = "stale/unverified"
        retrieval_meta["stale"] = True
        if staleStatus:
            retrieval_meta["status"] = staleStatus
        if allowStale:
            retrieval_meta["allowStale"] = True
    if precomputedVector is not None:
        retrieval_meta["vectorSource"] = "precomputed-vector-file"
    packet["retrieval"] = retrieval_meta

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
    """Write a packet to registry-for-review/discovery-packets/<candidateId>.json atomically."""
    slug = safeCandidateSlug(packet.get("candidateId", ""))
    outDir = Path(discoveryPacketsDir(registryPath)).resolve()
    outDir.mkdir(parents=True, exist_ok=True)
    outPath = (outDir / f"{slug}.json").resolve()
    if not str(outPath).startswith(str(outDir) + os.sep):
        raise ValueError(f"Candidate path escapes target directory: {outPath}")
    _atomic_write_json(outPath, packet)
    return str(outPath)


def prefillCommand(args):
    """`gaia dev prefill` — build a prefilled discovery-packet-v2 for a candidate.

    Non-mutating: writes to registry-for-review/discovery-packets/, never the
    registry. Reads thresholds from meta.json at runtime.
    """
    candidate_id = getattr(args, "candidate_id", None)
    try:
        slug = safeCandidateSlug(candidate_id or "")
    except ValueError as exc:
        print(f"Error: Invalid candidate identity: {exc}", file=sys.stderr)
        return 1

    registryPath = getattr(args, "registry", ".") or "."
    thresholds = loadPrefillThresholds(registryPath)

    try:
        retrievalCfg = loadRetrievalConfig(registryPath)
    except Exception:
        retrievalCfg = None

    embPath = embeddings_path(registryPath)
    # graph/embeddings.json is the tracked artifact; fall back to it when the
    # registry/embeddings.json path is absent.
    if not os.path.exists(embPath):
        for alt in [
            os.path.join(str(registryPath), "graph", "embeddings.json"),
            os.path.join(str(registryPath), "docs", "graph", "embeddings.json"),
        ]:
            if os.path.exists(alt):
                embPath = alt
                break

    # Check embeddings artifact freshness and presence
    status = embeddingStatus(
        registryPath=registryPath,
        artifactPath=embPath,
        config=retrievalCfg,
    )
    status_val = status.get("status")

    if status_val == "missing":
        print(
            "Embeddings artifact not found. Run `gaia dev embed` first.",
            file=sys.stderr,
        )
        return 1

    allow_stale = getattr(args, "allow_stale", False)
    if status_val in ("stale", "invalid"):
        if allow_stale:
            print(
                f"Warning: Embeddings artifact is {status_val} ({status.get('reason')}). Proceeding with --allow-stale.",
                file=sys.stderr,
            )
        else:
            print(
                f"Error: Embeddings artifact is {status_val}: {status.get('reason')}.\n"
                "Run `gaia dev embed` to update embeddings, or pass --allow-stale to proceed.",
                file=sys.stderr,
            )
            return 1

    try:
        embeddings = load_embeddings(embPath)
    except FileNotFoundError:
        print(
            "Embeddings not found. Run `gaia dev embed` first.",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"Error loading embeddings: {exc}", file=sys.stderr)
        return 1

    # Handle precomputed vector argument
    precomputedVector = None
    vector_file = getattr(args, "vector", None)
    if vector_file:
        if not os.path.exists(vector_file):
            print(f"Vector file not found: {vector_file}", file=sys.stderr)
            return 1
        expected_dim = embeddings.get("dimensions") or (retrievalCfg.get("dimensions") if retrievalCfg else 384)
        expected_model = (retrievalCfg.get("modelId") if retrievalCfg else None) or embeddings.get("model")
        expected_rev = embeddings.get("revision") or (embeddings.get("config", {}).get("revision") if isinstance(embeddings.get("config"), dict) else None)
        try:
            precomputedVector = parseAndValidateVector(
                vector_file,
                expectedModel=expected_model,
                expectedRevision=expected_rev,
                expectedDim=expected_dim,
            )
        except Exception as exc:
            print(f"Error parsing --vector: {exc}", file=sys.stderr)
            return 1

    suite = None
    if getattr(args, "suite_role", None) and getattr(args, "suite_id", None):
        suite = {"role": args.suite_role, "suiteId": args.suite_id}
        if getattr(args, "component_ids", None):
            suite["componentCandidateIds"] = [
                c.strip() for c in args.component_ids.split(",") if c.strip()
            ]

    effective_model = embeddings.get("model") or (retrievalCfg.get("modelId") if retrievalCfg else "all-MiniLM-L6-v2")

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
            precomputedVector=precomputedVector,
            modelName=effective_model,
            suite=suite,
            config=retrievalCfg,
            fetcher=getattr(args, "fetcher", None),
            staleStatus=status_val if status_val in ("stale", "invalid") else None,
            allowStale=allow_stale,
        )
    except ImportError:
        print(
            "sentence-transformers is not installed. Run: pip install sentence-transformers",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"Error building prefill packet: {exc}", file=sys.stderr)
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

    try:
        outPath = writePacket(packet, registryPath)
    except Exception as exc:
        print(f"Error writing packet: {exc}", file=sys.stderr)
        return 1

    strong = sum(1 for o in packet["mappingOptions"] if o["matchTier"] == "strong")
    weak = sum(1 for o in packet["mappingOptions"] if o["matchTier"] == "weak")
    print(f"Wrote prefilled discovery-packet-v2 to {outPath}")
    print(f"  mappingOptions: {len(packet['mappingOptions'])} ({strong} strong, {weak} weak)")
    print(f"  flags: {len(packet['flags'])}")

    # Automatic advisory assessment receipt generation for disk writes
    curation_out_dir = Path(generated_output_dir(registryPath)) / "curation"
    curation_out_dir.mkdir(parents=True, exist_ok=True)
    curation_out_dir_resolved = curation_out_dir.resolve()
    assessment_path = (curation_out_dir / f"{slug}.assessment.json").resolve()
    if not str(assessment_path).startswith(str(curation_out_dir_resolved) + os.sep):
        print(f"Warning: Assessment path escapes target directory: {assessment_path}", file=sys.stderr)
    else:
        try:
            receipt = buildAssessment(packet, registryPath=registryPath, client=None)
            _atomic_write_json(assessment_path, receipt)
            print(f"Wrote advisory assessment receipt to {assessment_path}")
        except Exception as exc:
            print(f"Warning: Failed to generate advisory assessment receipt: {exc}", file=sys.stderr)

    return 0

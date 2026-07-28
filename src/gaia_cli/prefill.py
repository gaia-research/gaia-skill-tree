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

import json
import os
import sys

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
    precomputedVector=None,
    modelName="all-MiniLM-L6-v2",
    suite=None,
):
    """Assemble a discovery-packet-v2 with prefilled mappingOptions.

    Deterministic: given the same inputs it returns the same packet. Emits a
    packet at the 'discovered' lifecycle stage carrying pre-ranked mapping
    options for the worker to confirm/adjudicate; it does NOT decide MAP itself.
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

    packet = {
        "contractVersion": "discovery-packet-v2",
        "candidateId": candidateId,
        # Prefill hands the worker a not-yet-decided packet: DEFER + the shortest
        # valid deferred lifecycle. The worker advances the lifecycle and emits
        # the final decision (MAP/NEW_GENERIC/...) after adjudicating the
        # pre-ranked mappingOptions below.
        "lifecycle": ["discovered", "deferred"],
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
            "value": "DEFER",
            "reasonCode": "PREFILL_AWAITING_WORKER",
        },
        "flags": flags,
    }
    if suite is not None:
        packet["suite"] = suite
    return packet


def selfValidatePacket(packet):
    """Validate a packet against the hand-rolled v2 validator.

    Imports the validator from the .agents skill tree (the canonical mirror).
    Returns a list of stable error codes (empty when valid).
    """
    validate = _importPacketValidator()
    if validate is None:
        # Validator not importable in this environment; skip (non-fatal).
        return []
    return validate(packet, trusted_generics=None)


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

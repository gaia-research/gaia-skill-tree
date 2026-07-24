"""Canon-side rank/grade helpers.

Under Yggdrasil II the non-dev CLI never self-assigns rank — the self-promote
machinery (candidate handshake, level writes into user trees) has been retired.
What remains here are the canon-curation helpers consumed by the grading /
verification pipeline: the Unique-branch gate, the rank-floor rule, the
evidence-grade reader, and the level-name/level-order metadata.
"""

import json
import os

# Grade ordering for evidence rows: S > A > B > C (index 0 = strongest).
_GRADE_ORDER = ["S", "A", "B", "C"]


def _load_meta():
    """Load registry/schema/meta.json from repo root or bundled fallback."""
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "registry", "schema", "meta.json"),
        os.path.join(os.path.dirname(__file__), "data", "registry", "schema", "meta.json"),
    ]
    for p in candidates:
        resolved = os.path.normpath(p)
        if os.path.isfile(resolved):
            with open(resolved, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("Cannot find registry/schema/meta.json")


_META = _load_meta()
LEVEL_ORDER = _META["levels"]["order"]
LEVEL_NAMES = _META["levels"]["labels"]

# NOTE (Yggdrasil II, ratified 2026-07-07): the **Evidence Floor** is gone.
# `meta.json levels.evidenceFloors` was dropped from the schema and Trust
# Magnitude (`gaia_cli.trustMagnitude`) is now the SOLE promotion gate. The
# former `EVIDENCE_FLOOR` constant and `_meets_evidence_floor()` helper were
# deleted here rather than left returning an unconditional True — a gate that
# always passes reads like a gate and invites re-wiring. Do not reintroduce a
# per-level evidence-class floor; raise the TM threshold instead.


def next_level(current: str) -> str | None:
    """Return the next level string, or None if already at max."""
    try:
        idx = LEVEL_ORDER.index(current)
    except ValueError:
        return None
    if idx >= len(LEVEL_ORDER) - 1:
        return None
    return LEVEL_ORDER[idx + 1]



def _effective_grade(ev: dict) -> str | None:
    """Return the effective grade for a single evidence row.

    Reads ``grade`` first (S/A/B/C, per G7 Trust Taxonomy RFC).  Falls back to
    ``class`` (A/B/C legacy) when ``grade`` is absent.  Returns None for rows
    that carry neither a recognised grade nor a recognised class (ungraded).
    """
    grade = ev.get("grade")
    if grade in _GRADE_ORDER:
        return grade
    cls = ev.get("class")
    if cls in _GRADE_ORDER:
        return cls
    return None


def _passes_rank_floor(
    graph_skill: dict,
    user_level: str,
    overall_grade: str | None,
) -> bool:
    """Rank-floor sanity rule (RFC §4.3).

    A skill held at 4★+ in any user tree cannot land below B in the registry
    without explicit review. Returns True if the rank-floor is satisfied
    (i.e., the skill may publish at this grade).

    Args:
        graph_skill: The graph skill node (used for context; reserved for
            future per-skill overrides like a `rankFloorOverride` flag).
        user_level: The skill's current level in any user's tree (e.g. "4★").
        overall_grade: The Overall Trust Grade computed via the G7 formula
            (one of "S", "A", "B", "C", or None for ungraded).

    Returns:
        True if the rule passes (publish allowed); False if the rule fails
        (publish blocked pending rank-floor-override review).
    """
    del graph_skill  # reserved for future per-skill overrides
    if user_level not in LEVEL_ORDER:
        return True
    rankIndex = LEVEL_ORDER.index(user_level)
    fourStarIndex = LEVEL_ORDER.index("4★") if "4★" in LEVEL_ORDER else 4
    if rankIndex < fourStarIndex:
        return True
    # 4★+ skills must land at B or higher.
    if overall_grade in ("S", "A", "B"):
        return True
    return False


def effectiveGrade(entry: dict) -> str | None:
    """Return the effective grade letter for an evidence entry, or None.

    Reads ``grade`` first; falls back to the deprecated ``class`` field.
    Shared helper exposed for verification.py (G4 #709 TODO collapse).
    """
    return _effective_grade(entry)


# Unique-branch grade gates (Yggdrasil II Q3, amended 2026-07-19): 4★ Unique
# needs A (TM >= 100), 5★ Unique Ultimate needs S (TM >= 250).
#
# Origin is evaluated DIFFERENTLY per gate (the two were conflated before the
# 2026-07-19 amendment — see YGGDRASIL_II_RATIFICATION_2026-07-07.md Q3):
#   - 4★ Unique          -> BUCKET-LEVEL origin (META.md §4.1): does the skill
#                           hold Origin on the generic bucket it DIRECTLY
#                           implements (`genericSkillRef`)?  No fusion/prereq
#                           check — Origin is "the most renowned implementation
#                           in a generic bucket", exactly one per bucket.
#   - 5★+ Unique Ultimate -> FUSION-STRUCTURE origin: the creator must hold
#                           Origin on >=1 of the generic parent's
#                           `prerequisites` (the fusion recipe they built).
_UNIQUE_GATE_BY_LEVEL = {
    "4★": {"grade": "A", "tmFloor": 100.0},
    "5★": {"grade": "S", "tmFloor": 250.0},
}


def _contributor_holds_origin_in(
    contributor: str | None,
    node_ids,
    named_skill_map: dict | None,
) -> bool:
    """True iff ``contributor`` holds Origin status on >=1 of ``node_ids``.

    Mirrors the Suite-gate origin predicate ("proposer holds Origin on >=1
    suiteComponent") but points at the fusion structure: a node in ``node_ids``
    (generic skill ids drawn from the generic parent's ``prerequisites``) counts
    when the contributor owns a named skill with ``origin: true`` whose
    ``genericSkillRef`` (or ``targetSkillId``) resolves to that node.
    """
    if not contributor or not node_ids or not named_skill_map:
        return False
    targets = set(node_ids)
    for entry in named_skill_map.values():
        if not isinstance(entry, dict):
            continue
        if entry.get("contributor") != contributor:
            continue
        if entry.get("origin") is not True:
            continue
        ref = entry.get("genericSkillRef") or entry.get("targetSkillId")
        if ref in targets:
            return True
    return False


def _holds_bucket_origin(named: dict) -> bool:
    """True iff ``named`` holds BUCKET-LEVEL Origin on its own generic bucket.

    META.md §4.1: "the most renowned implementation IN A GENERIC BUCKET earns
    Origin … exactly one Origin per bucket." Origin is the curator-granted merit
    mark stored on the named skill as ``origin: true``; it is authoritative
    (singular per bucket by construction). This is the origin predicate for the
    4★ **Unique** gate — it asks only whether THIS skill is the Origin on the
    generic it directly implements (``genericSkillRef``), with NO reference to
    the generic's fusion structure / prerequisites (that belongs to the 5★+
    gate). A skill with no ``genericSkillRef`` cannot hold bucket origin.
    """
    if not named.get("genericSkillRef"):
        return False
    return named.get("origin") is True


def checkUniqueBranchGate(
    named: dict,
    level: str,
    genericSkillMap: dict | None = None,
    namedSkillMap: dict | None = None,
) -> dict:
    """Evaluate the Unique-branch promotion gate for a named skill (Yggdrasil II).

    Gate (Q3 decision log, amended 2026-07-19):
      - 4★ **Unique**          = Origin present + TM >= 100 (A-grade)
      - 5★ **Unique Ultimate** = Origin present + TM >= 250 (S-grade)

    ``Origin present`` is evaluated per gate (they were conflated pre-amendment):
      - **4★ Unique** — BUCKET-LEVEL origin (META.md §4.1): the skill holds
        Origin on the generic bucket it DIRECTLY implements (``genericSkillRef``).
        No prerequisite/fusion-structure check at 4★.
      - **5★ Unique Ultimate** — FUSION-STRUCTURE origin: the contributor holds
        Origin on >=1 node in the generic parent's ``prerequisites`` (the fusion
        recipe), NOT in ``suiteComponents``.

    ``suiteRef`` membership does NOT disqualify — a world-renowned standalone
    skill that happens to live inside a suite is still Unique. Branch membership
    is confirmed via :func:`computeBranch` evaluated at the target ``level``.
    Trust Magnitude is recomputed live via :func:`computeTrustMagnitude` (never a
    stale precomputed value).

    Returns a predicate-shaped dict::

        {
          "originPresent":  bool,
          "tmThresholdMet": bool,
          "tm":             float,
          "grade":          str | None,   # required grade for this level (A/S)
          "passed":         bool,
        }
    """
    from gaia_cli.trustMagnitude import computeTrustMagnitude
    from gaia_cli.taxonomy import branchFor as computeBranch

    spec = _UNIQUE_GATE_BY_LEVEL.get(level)
    grade = spec["grade"] if spec else None

    # Recompute Trust Magnitude live (effective pool handled internally when a
    # genericSkillMap is supplied). Never trust a precomputed frontmatter value.
    # Pre-merge namedSkillMap so suite-component origin IDs (e.g. "gsd-build/discuss-phase")
    # resolve correctly in _gradedOriginCount — named skill IDs miss a generic-only map.
    mergedMap = {**(genericSkillMap or {}), **(namedSkillMap or {})}
    tm = float(computeTrustMagnitude(named, mergedMap))

    # Confirm the skill sits on the Unique branch AT the target level.
    branch = computeBranch({**named, "level": level})

    # Origin predicate FORKS by rank (amended 2026-07-19):
    #   4★  -> bucket-level origin on the skill's own genericSkillRef (§4.1).
    #   5★+ -> fusion-structure origin on the generic parent's prerequisites.
    if level == "4★":
        origin_present = _holds_bucket_origin(named)
    else:
        prereqs: list[str] = []
        if genericSkillMap is not None:
            generic = genericSkillMap.get(named.get("genericSkillRef"))
            if generic:
                prereqs = list(generic.get("prerequisites") or [])
        origin_present = _contributor_holds_origin_in(
            named.get("contributor"), prereqs, namedSkillMap
        )

    tm_threshold_met = bool(spec) and tm >= spec["tmFloor"]
    passed = bool(spec) and branch == "unique" and origin_present and tm_threshold_met

    return {
        "originPresent": origin_present,
        "tmThresholdMet": tm_threshold_met,
        "tm": round(tm, 2),
        "grade": grade,
        "passed": passed,
    }


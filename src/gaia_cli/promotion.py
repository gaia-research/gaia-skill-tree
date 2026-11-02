"""Canon-side rank/grade helpers.

Under Yggdrasil II the non-dev CLI never self-assigns rank — the self-promote
machinery (candidate handshake, level writes into user trees) has been retired.
What remains here are the canon-curation helpers consumed by the grading /
verification pipeline: the Unique-branch gate, the rank-floor rule, the
evidence-grade reader, and the level-name/level-order metadata.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

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


# Unique-branch grade gates: 4★ Unique needs A (TM >= 100), 5★ Unique Ultimate
# needs S (TM >= 250).
#
# Origin on the Unique branch (founder ruling 2026-10-30, EPIC #2189): the skill
# must be the Origin of its own generic bucket, derived automatically as the
# highest-merit implementation (gaia_cli.origin). That is the ONLY Origin
# requirement at 4★ and 5★. There is no fusion-prerequisite Origin requirement
# for Uniques: "Uniques dont need a fusion prerequisite origin at all … thats
# from suites." The Suite rule (Origin on >=1 suiteComponent at 5★, META §4.2)
# is separate and unchanged.
_UNIQUE_GATE_BY_LEVEL = {
    "4★": {"grade": "A", "tmFloor": 100.0},
    "5★": {"grade": "S", "tmFloor": 250.0},
}


def _holds_bucket_origin(named: dict, namedSkillMap: dict | None = None, level: str | None = None) -> bool:
    """True iff ``named`` is (or at ``level`` would be) its bucket's derived Origin.

    Origin is the highest-merit named implementation of the generic bucket
    (``genericSkillRef``), computed by :func:`gaia_cli.origin.holdsBucketOrigin`.
    Never read from a stored flag. A skill with no ``genericSkillRef`` has no
    bucket and cannot hold Origin.
    """
    from gaia_cli.origin import holdsBucketOrigin

    return holdsBucketOrigin(named, namedSkillMap, level=level)


def checkUniqueBranchGate(
    named: dict,
    level: str,
    genericSkillMap: dict | None = None,
    namedSkillMap: dict | None = None,
    originPool: dict | None = None,
) -> dict:
    """Evaluate the Unique-branch promotion gate for a named skill (Yggdrasil II).

    NOTE: This gate is strictly for the **Unique branch** (standalone skills
    without ``suiteComponents``). If a skill has ``suiteComponents``, it sits on
    the **Suite branch**, where promotion requirements differ:
      - 4★ **Extra**: requires Overall Trust Grade A (TM >= 100) and live verified
        blob evidence (Star Bar). It does NOT require bucket-level origin on its
        generic bucket.
      - 5★ **Ultimate**: requires Overall Trust Grade S (TM >= 250) and holding Origin
        on >=1 of the ``suiteComponents`` (META.md §4.2).

    Gate for the Unique branch (founder ruling 2026-10-30):
      - 4★ **Unique**          = bucket Origin + TM >= 100 (A-grade)
      - 5★ **Unique Ultimate** = bucket Origin + TM >= 250 (S-grade)

    ``Origin present`` means the skill would be the derived Origin of its own
    generic bucket at the target level (highest merit: published level, then
    TM; see :mod:`gaia_cli.origin`). There is no fusion-prerequisite Origin
    requirement and no star floor on Origin.

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
          "branch":         str,          # 'unique', 'suite', etc.
          "reason":         str | None,   # explanation when non-unique or branch mismatch
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

    # Clean check: if named has suiteComponents, it belongs to the Suite branch.
    # The Unique branch gate is strictly for standalone skills on the Unique branch.
    # On the Suite branch, 4★ Extra requires Grade A TM >= 100 and does NOT require
    # bucket-level origin; Origin is required at 5★ Ultimate across suiteComponents
    # per META.md §4.2.
    if named.get("suiteComponents"):
        logger.info(
            "Skill '%s' has suiteComponents; Suite branch applies (4★ Extra requires "
            "Grade A TM >= 100, origin not required until 5★ Ultimate per META.md §4.2), "
            "not Unique branch.",
            named.get("id"),
        )
        tm_threshold_met = bool(spec) and tm >= spec["tmFloor"]
        return {
            "originPresent": False,
            "tmThresholdMet": tm_threshold_met,
            "tm": round(tm, 2),
            "grade": grade,
            "passed": False,
            "branch": "suite",
            "reason": (
                "Suite branch applies: skill defines suiteComponents. "
                "4★ Extra requires Grade A TM >= 100 and does not require bucket-level origin; "
                "origin is required at 5★ Ultimate across suiteComponents (META.md §4.2)."
            ),
        }

    # Confirm the skill sits on the Unique branch AT the target level.
    branch = computeBranch({**named, "level": level})

    # One Origin predicate at every Unique gate: the skill is its bucket's
    # derived Origin when placed at the target level.
    # ``originPool`` adds awakened records (gaia_cli.origin.contenderPool); they
    # compete for Origin but stay out of the Trust Magnitude map.
    pool = originPool if originPool is not None else (mergedMap if namedSkillMap else None)
    origin_present = _holds_bucket_origin(named, pool, level=level)

    tm_threshold_met = bool(spec) and tm >= spec["tmFloor"]
    passed = bool(spec) and branch == "unique" and origin_present and tm_threshold_met

    return {
        "originPresent": origin_present,
        "tmThresholdMet": tm_threshold_met,
        "tm": round(tm, 2),
        "grade": grade,
        "passed": passed,
        "branch": branch,
    }


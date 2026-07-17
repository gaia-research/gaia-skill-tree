"""taxonomy.py — Yggdrasil II taxonomy-resolution authority (PR1 keystone).

SINGLE SOURCE OF TRUTH for branch / rank-word / medallion derivation, ported
from the four live resolvers this module supersedes:

  JS  #1  docs/js/skill-semantics.js         (computeBranch, rankWord, rankLabel)
  Py  #3  src/gaia_cli/trustMagnitude.py     (computeBranch + _starRank/_suiteComponentsPresent)
  Py  #4  src/gaia_cli/formatting.py          (rank_word, LEVEL_LABELS_SUITE/UNIQUE)
  JS  #2  docs/js/world-tree-layout.js        (resolveSemantics — the Ygg I/II fork)

Nothing consumes this module yet (PR1 is a pure add). Downstream PRs migrate
each consumer onto these functions; PR3b deletes the JS/Py resolvers above.

Canonical semantics — FOUNDER RULING (do NOT reintroduce JS #1's `type==='basic'`
guard). Branch is derived from rank + suiteComponents-presence ONLY; `type` is
never consulted at display time:

    rank < 4                                  -> 'standard'
    rank >= 4 AND suiteComponents present     -> 'suite'
    rank >= 4 AND no suiteComponents          -> 'unique'

This is Py #3's type-INDEPENDENT logic. It intentionally diverges from JS #1
(which consults `type`) on `type != 'basic'` nodes at rank >= 4 with no
suiteComponents. That divergence is deliberate and is pinned by the contract
oracle (tests/test_taxonomy_contract.py).

Rank ladders (canonical — fork at 4 stars+):
    SHARED  {0 Basic, 1 Awakened, 2 Named, 3 Evolved}
    SUITE   {4 Extra, 5 Ultimate, 6 Apex}
    UNIQUE  {4 Unique, 5 Unique Ultimate, 6 Unique Impossible}

BANNED words anywhere in emitted vocabulary: 'Transcendent', 'Hardened'
(scripts/check_rank_vocabulary.py enforces).

Absent-field fallback: every resolver accepts BOTH a pre-resolved entry (reads
an emitted `branch`/`rank` field when present) AND a raw entry (field absent ->
derive). The fallback lives INSIDE this module — never hard-index a resolved
field. Rationale: a stale bundled wheel snapshot must still render before the
user's first `gaia pull`.

Repo style: no underscores in public function names (dunders excepted).
"""

from typing import Any, Optional


# ---------------------------------------------------------------------------
# Meta-epoch constants
# ---------------------------------------------------------------------------

# meta.json `metaEpochs.order` — see docs/graph/gaia.json.
EPOCH_YGG_I = "yggdrasil-i"
EPOCH_YGG_II = "yggdrasil-ii"


# ---------------------------------------------------------------------------
# Rank-word ladders (canonical single source)
# ---------------------------------------------------------------------------

# Shared 0-3 stars (branch-agnostic). 0 stars = Basic (starless).
SHARED_WORD = {0: "Basic", 1: "Awakened", 2: "Named", 3: "Evolved"}
# Suite branch 4-6 stars.
SUITE_WORD = {4: "Extra", 5: "Ultimate", 6: "Apex"}
# Unique branch 4-6 stars.
UNIQUE_WORD = {4: "Unique", 5: "Unique Ultimate", 6: "Unique Impossible"}

# Structural-class glyph / medallion token (resolveSemantics 3.1/6):
#   unique . suite . root (basic, standard) . else (crown, standard).
# The authority exposes a single medallion() resolver keyed on the RESOLVED
# branch (+ rank), not on `type`. Since branch already encodes the
# suite/unique/standard distinction, a standard node maps to the neutral
# crown glyph (the root glyph in resolveSemantics is a hemisphere-by-type
# artifact that the type-independent authority does not reproduce).
MEDALLION_UNIQUE = "◉"    # circled bullet
MEDALLION_SUITE = "◆"     # black diamond
MEDALLION_STANDARD = "◇"  # white diamond


# ---------------------------------------------------------------------------
# Level parsing
# ---------------------------------------------------------------------------

def levelNum(level: Any) -> int:
    """Parse a level ("5star" | "5" | 5 | None) to a clamped integer 0..6.

    Mirrors skill-semantics.js levelNum() and trustMagnitude._starRank(),
    unified. None / unparseable -> 0.
    """
    if level is None:
        return 0
    if isinstance(level, bool):  # guard: bool is an int subclass
        return 0
    if isinstance(level, int):
        return max(0, min(6, level))
    digits = ""
    for ch in str(level):
        if ch.isdigit():
            digits += ch
        elif digits:
            break
    if not digits:
        return 0
    return max(0, min(6, int(digits)))


def suiteComponentsPresent(entry: dict) -> bool:
    """True iff the entry carries a non-empty suiteComponents list.

    Mirrors JS #1 (`Array.isArray && length > 0`) and Py #3
    `_suiteComponentsPresent` (the generic-parent read is threaded by callers
    that resolve the parent onto the entry before normalize()).
    """
    sc = entry.get("suiteComponents")
    return bool(sc) and isinstance(sc, (list, tuple)) and len(sc) > 0


# ---------------------------------------------------------------------------
# normalize — the ONLY meta-version-aware code (absorbs resolveSemantics fork)
# ---------------------------------------------------------------------------

def normalize(entry: Optional[dict], metaEpoch: str = EPOCH_YGG_II) -> dict:
    """Reduce a raw skill entry to ONE canonical internal shape.

    This is the sole meta-version-aware function. It absorbs the Ygg I/II fork
    from world-tree-layout.js resolveSemantics() (L356-413): a Ygg I
    `type:'ultimate'`/`'unique'`/`'extra'` node and a Ygg II
    `type:'fusion'`/`'basic'` node both map to the same canonical dict.

    metaEpoch selects the fork. Ygg III later = add a branch here; no consumer
    downstream ever forks on epoch again.

    Returned canonical shape (stable keys):
        {
          'rank':                  int 0..6 (resolved effective star level),
          'suiteComponentsPresent': bool,
          'branchEligible':        bool  (rank >= 4 — the normalized
                                          branch-eligibility signal),
          'branch':                str|None  (pre-resolved 'branch' field iff
                                              the entry already carried one;
                                              None -> resolveDisplayBranch derives),
          'metaEpoch':             str,
        }

    Rank read order (absent-field fallback): explicit `rank` field ->
    `level` field -> `namedMaxLevel` field (gaia.json generic nodes carry only
    namedMaxLevel) -> 0.
    """
    entry = entry or {}
    epoch = metaEpoch or EPOCH_YGG_II

    # --- resolved rank (absent-field fallback ladder) ---
    if "rank" in entry and entry.get("rank") is not None:
        rank = levelNum(entry.get("rank"))
    elif entry.get("level") is not None:
        rank = levelNum(entry.get("level"))
    else:
        # gaia.json generic nodes have no `level`; the effective star rank is
        # the highest named form (`namedMaxLevel`). None -> 0 (starless).
        rank = levelNum(entry.get("namedMaxLevel"))

    hasSuite = suiteComponentsPresent(entry)
    kind = entry.get("type")

    # --- Ygg I/II fork (resolveSemantics 3.2 isUnique / isSuite mapping) ---
    # The fork exists to translate legacy type-driven signals into the same
    # rank + suiteComponents shape the Ygg II resolver expects. Under Ygg I a
    # node's structural class was carried by `type`; under Ygg II it is carried
    # by rank + suiteComponents. normalize() reconciles both onto:
    #   suiteComponentsPresent  (drives the suite branch at 4 stars+)
    #   branchEligible          (rank >= 4)
    if epoch == EPOCH_YGG_I:
        # Ygg I: type === 'ultimate' | 'extra' behaved as suite carriers;
        # type === 'unique' behaved as the unique branch. Fold the legacy type
        # signal into the canonical suite-presence flag so the type-independent
        # resolveDisplayBranch produces the same branch it did under Ygg I.
        if kind in ("ultimate", "extra"):
            hasSuite = True
        # A Ygg I 'unique' had no suiteComponents by construction; leave
        # hasSuite as-is so a 4 stars+ unique resolves to 'unique'.
    # Ygg II: nothing to fold — type in {basic, fusion} is display-irrelevant.

    # --- pre-resolved branch passthrough (stale-snapshot fallback) ---
    branch = entry.get("branch")
    if branch not in ("standard", "suite", "unique"):
        branch = None  # unrecognised / absent -> derive downstream

    return {
        "rank": rank,
        "suiteComponentsPresent": hasSuite,
        "branchEligible": rank >= 4,
        "branch": branch,
        "metaEpoch": epoch,
    }


# ---------------------------------------------------------------------------
# resolveDisplayBranch — canonical (type-independent) branch resolver
# ---------------------------------------------------------------------------

def resolveDisplayBranch(normalized: dict) -> str:
    """Return 'standard' | 'suite' | 'unique' from a normalize() shape.

    CANONICAL SEMANTICS — FOUNDER RULING (see module docstring). Type-independent:

        rank < 4                              -> 'standard'
        rank >= 4 AND suiteComponents present -> 'suite'
        rank >= 4 AND no suiteComponents      -> 'unique'

    Absent-field fallback: a normalize() shape that already carried a
    pre-resolved `branch` (from an emitted field) is honoured verbatim; only a
    None branch is derived. This lets a stale bundled snapshot render its
    emitted branch without re-deriving.
    """
    normalized = normalized or {}
    pre = normalized.get("branch")
    if pre in ("standard", "suite", "unique"):
        return pre
    if not normalized.get("branchEligible") or normalized.get("rank", 0) < 4:
        return "standard"
    if normalized.get("suiteComponentsPresent"):
        return "suite"
    return "unique"


def branchFor(entry: dict, metaEpoch: str = EPOCH_YGG_II) -> str:
    """Convenience: normalize(entry) then resolveDisplayBranch(...).

    Accepts a raw OR pre-resolved entry (fallback lives in normalize +
    resolveDisplayBranch). This is the single call a consumer makes when it
    holds a raw skill object rather than an already-normalized shape.
    """
    return resolveDisplayBranch(normalize(entry, metaEpoch))


# ---------------------------------------------------------------------------
# rankWord / rankLabel — the single branch-forked ladder
# ---------------------------------------------------------------------------

def rankWord(level: Any, branch: str = "standard") -> str:
    """Return the bare rank word for a (level, branch) pair.

    1-3 stars (and 0) are the SHARED ladder — branch-agnostic. 4 stars+ forks by
    branch. Never emits the banned words 'Transcendent' / 'Hardened'.

      level:  "5star" | 5 | "5"
      branch: 'standard' | 'suite' | 'unique' (default 'standard')
    """
    n = levelNum(level)
    if n <= 3:
        return SHARED_WORD.get(n, "Basic")
    # 4 stars+ fork. 'suite' is the neutral default for 4 stars+ (a resolved
    # 4 stars+ skill is always 'suite' or 'unique' — 'standard' never reaches
    # this ladder in practice, but if it does it reads as the suite word rather
    # than crashing).
    if branch == "unique":
        return UNIQUE_WORD.get(n, UNIQUE_WORD[6])
    return SUITE_WORD.get(n, SUITE_WORD[6])


def rankLabel(level: Any, branch: str = "standard") -> str:
    """Return '<rankWord> . N stars' (e.g. 'Unique Ultimate . 5 stars')."""
    n = levelNum(level)
    return f"{rankWord(level, branch)} · {n}★"


# ---------------------------------------------------------------------------
# medallion — resolved art token
# ---------------------------------------------------------------------------

def medallion(branch: str, rank: Any = None) -> str:
    """Return the structural-class medallion glyph for a resolved branch.

    Keyed on the RESOLVED branch (rank is accepted for forward-compat / future
    rank-scaled art but is not currently consulted — branch already encodes the
    suite/unique/standard distinction). Sourced from resolveSemantics 3.1/6:

        'unique'   -> circled-bullet
        'suite'    -> black-diamond
        'standard' -> white-diamond  (neutral crown glyph)

    See the MEDALLION_* module constants for the decision rationale (the root
    glyph in resolveSemantics is a hemisphere-by-type artifact not reproduced by
    the type-independent authority).
    """
    if branch == "unique":
        return MEDALLION_UNIQUE
    if branch == "suite":
        return MEDALLION_SUITE
    return MEDALLION_STANDARD

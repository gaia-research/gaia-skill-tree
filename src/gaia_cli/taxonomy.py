"""taxonomy.py — Yggdrasil II taxonomy-resolution authority (PR1 keystone).

SINGLE SOURCE OF TRUTH for branch / rank-word / medallion derivation. It ported
and SUPERSEDED the four live resolvers below; PR3b DELETED all four, leaving this
module as the sole authority:

  JS  #1  docs/js/skill-semantics.js         (computeBranch, rankWord, rankLabel)
  Py  #3  src/gaia_cli/trustMagnitude.py     (computeBranch + _starRank/_suiteComponentsPresent)
  Py  #4  src/gaia_cli/formatting.py          (rank_word, LEVEL_LABELS_SUITE/UNIQUE)
  JS  #2  docs/js/world-tree-layout.js        (resolveSemantics — the Ygg I/II fork)

Every consumer now derives branch/rank/medallion through these functions; the
inline resolvers above no longer exist.

Canonical semantics — FOUNDER RULING v2, the SYNTHESIS rule (do NOT consult
`type`). Suite-PRESENCE decides branch FIRST (no rank gate); rank only splits
the no-suite case:

    suiteComponents present                   -> 'suite'   (ANY rank 1..6 —
                                                 "anything can be a suite")
    no suiteComponents, rank 1..3             -> 'standard'
    no suiteComponents, rank 4..6             -> 'unique'

This is the synthesis of both legacy resolvers — NEITHER verbatim:
  * suite-presence-first, no rank gate  = JS #1's suite logic (skill-semantics.js L61)
  * type-independent unique at 4 stars+  = Python #3's unique logic (trustMagnitude)
Canonical therefore agrees with JS #1 on the suite class (rank<4 + suite) where
Python #3 does not, AND agrees with Python #3 on the unique class (fusion rank>=4
no-suite) where JS #1 does not. Both divergences are pinned by the contract
oracle (tests/test_taxonomy_contract.py).

BRANCH vs DECORATION SPLIT (load-bearing): branch === 'suite' holds from 1 star up
(for grouping / membership / sorting), BUT the suite rank-WORD (Extra/Ultimate/
Apex) and the suite GLYPH only render at 4..6 stars — those ladder words simply do
not exist below 4. So:
  * rankWord(level, 'suite') for level 1..3  -> the SHARED word (Awakened/Named/
    Evolved), NOT Extra/etc.; only 4..6 return the suite words.
  * medallion('suite', rank) -> plain glyph (white diamond) for rank<4, suite
    glyph (black diamond) for rank 4..6.
Unique only exists at 4..6 by construction, but the same guard applies (shared
word / plain glyph below 4) defensively.

Rank ladders (canonical — decoration forks at 4 stars+):
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

    CANONICAL SEMANTICS — FOUNDER RULING v2, the SYNTHESIS rule (see module
    docstring). Suite-PRESENCE decides branch FIRST; rank only splits the
    no-suite case:

        suiteComponents present        -> 'suite'    (ANY rank 1..6 — no gate)
        no suiteComponents, rank 1..3  -> 'standard'
        no suiteComponents, rank 4..6  -> 'unique'

    Absent-field fallback: a normalize() shape that already carried a
    pre-resolved `branch` (from an emitted field) is honoured verbatim; only a
    None branch is derived. This lets a stale bundled snapshot render its
    emitted branch without re-deriving.
    """
    normalized = normalized or {}
    pre = normalized.get("branch")
    if pre in ("standard", "suite", "unique"):
        return pre
    # Suite-presence FIRST — no rank gate on branch membership.
    if normalized.get("suiteComponentsPresent"):
        return "suite"
    # No suite: rank splits standard (1..3) from unique (4..6).
    if normalized.get("rank", 0) >= 4:
        return "unique"
    return "standard"


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

    BRANCH vs DECORATION SPLIT (founder ruling v2): a node's `branch` can be
    'suite' or 'unique' from 1 star up, but the suite/unique rank WORDS only exist
    at 4..6 stars. So 0..3 stars ALWAYS returns the SHARED ladder word regardless of
    branch (a 2 stars suite node reads 'Named', not 'Extra'). Only 4..6 fork:
        4..6 + 'unique' -> Unique / Unique Ultimate / Unique Impossible
        4..6 + else     -> Extra  / Ultimate        / Apex  (suite ladder)
    Never emits the banned words 'Transcendent' / 'Hardened'.

      level:  "5star" | 5 | "5"
      branch: 'standard' | 'suite' | 'unique' (default 'standard')
    """
    n = levelNum(level)
    if n <= 3:
        # SHARED ladder for 0..3 stars — branch-agnostic (decoration split).
        return SHARED_WORD.get(n, "Basic")
    # 4 stars+ fork. 'suite' is the neutral default for 4 stars+ (a resolved
    # 4 stars+ non-suite node is 'unique'; a non-branch 'standard' node above
    # 3 stars reads as the suite word rather than crashing).
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
    """Return the structural-class medallion glyph for a (branch, rank) pair.

    BRANCH vs DECORATION SPLIT (founder ruling v2): the custom suite/unique glyph
    only renders at 4..6 stars. Below 4 stars a suite/unique branch node uses the
    plain shared glyph (the suite/unique DECORATION does not exist yet), even
    though its branch is already 'suite'/'unique' for grouping/membership.

        4..6 stars + 'unique'   -> circled-bullet
        4..6 stars + 'suite'    -> black-diamond
        otherwise (incl. rank<4, standard, unknown) -> white-diamond (plain)

    Sourced from resolveSemantics 3.1/6 (the root glyph there is a
    hemisphere-by-type artifact not reproduced by the type-independent authority).
    """
    n = levelNum(rank) if rank is not None else 6  # None => assume decorated rank
    if n >= 4:
        if branch == "unique":
            return MEDALLION_UNIQUE
        if branch == "suite":
            return MEDALLION_SUITE
    return MEDALLION_STANDARD

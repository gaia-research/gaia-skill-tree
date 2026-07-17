"""Unit tests for gaia_cli.taxonomy — the Yggdrasil II taxonomy authority (PR1).

Covers:
  - Ygg I input shapes   (type: 'ultimate' / 'unique' / 'extra')
  - Ygg II input shapes  (type: 'fusion' / 'basic' + suiteComponents)
  - the full rank ladder 0..6 across all three branches
  - the absent-field fallback (raw entry vs pre-resolved entry)
  - assertion that NO banned words ('Transcendent', 'Hardened') are ever emitted

Run: PYTHONIOENCODING=utf-8 PYTHONPATH=./src python -m pytest tests/test_taxonomy.py -q
"""

import pytest

from gaia_cli import taxonomy


BANNED = ("Transcendent", "Hardened")


# ---------------------------------------------------------------------------
# levelNum
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    (None, 0),
    (0, 0),
    (3, 3),
    (6, 6),
    (99, 6),      # clamp high
    (-1, 0),      # clamp low
    ("4★", 4),
    ("5", 5),
    ("2 star", 2),
    ("", 0),
    ("garbage", 0),
    (True, 0),    # bool guard
])
def test_levelNum(raw, expected):
    assert taxonomy.levelNum(raw) == expected


# ---------------------------------------------------------------------------
# resolveDisplayBranch — canonical (type-independent) semantics
# ---------------------------------------------------------------------------

def test_branch_standard_below_4():
    for lvl in range(0, 4):
        n = taxonomy.normalize({"type": "basic", "level": f"{lvl}★"})
        assert taxonomy.resolveDisplayBranch(n) == "standard", lvl


def test_branch_suite_when_4plus_with_suitecomponents():
    for lvl in (4, 5, 6):
        n = taxonomy.normalize({"type": "fusion", "level": f"{lvl}★",
                                "suiteComponents": ["a", "b"]})
        assert taxonomy.resolveDisplayBranch(n) == "suite", lvl


def test_branch_unique_when_4plus_no_suitecomponents():
    for lvl in (4, 5, 6):
        n = taxonomy.normalize({"type": "fusion", "level": f"{lvl}★"})
        assert taxonomy.resolveDisplayBranch(n) == "unique", lvl


def test_branch_type_independent_basic_4star_no_suite_is_unique():
    # FOUNDER RULING: a basic 4★ with no suiteComponents is UNIQUE (JS #1 would
    # also say unique here — the divergence is on type != 'basic', see contract).
    n = taxonomy.normalize({"type": "basic", "level": "4★"})
    assert taxonomy.resolveDisplayBranch(n) == "unique"


def test_branch_basic_carrying_suitecomponents_is_suite():
    # Orthogonality: a basic node carrying suiteComponents at 4★+ is Suite.
    n = taxonomy.normalize({"type": "basic", "level": "5★",
                            "suiteComponents": ["x"]})
    assert taxonomy.resolveDisplayBranch(n) == "suite"


# ---------------------------------------------------------------------------
# Ygg I input shapes — normalize() fork
# ---------------------------------------------------------------------------

def test_ygg1_ultimate_maps_to_suite():
    # Ygg I: type='ultimate' was a suite carrier. Fold to suite at 4★+.
    n = taxonomy.normalize({"type": "ultimate", "level": "5★"},
                           taxonomy.EPOCH_YGG_I)
    assert n["suiteComponentsPresent"] is True
    assert taxonomy.resolveDisplayBranch(n) == "suite"


def test_ygg1_extra_maps_to_suite():
    n = taxonomy.normalize({"type": "extra", "level": "4★"},
                           taxonomy.EPOCH_YGG_I)
    assert taxonomy.resolveDisplayBranch(n) == "suite"


def test_ygg1_unique_maps_to_unique():
    # Ygg I: type='unique' at 4★+ with no suiteComponents -> unique.
    n = taxonomy.normalize({"type": "unique", "level": "4★"},
                           taxonomy.EPOCH_YGG_I)
    assert taxonomy.resolveDisplayBranch(n) == "unique"


def test_ygg1_ultimate_below_4_still_standard():
    # Even a legacy suite carrier below 4★ reads as the shared standard ladder.
    n = taxonomy.normalize({"type": "ultimate", "level": "3★"},
                           taxonomy.EPOCH_YGG_I)
    assert taxonomy.resolveDisplayBranch(n) == "standard"


def test_ygg2_type_never_consulted():
    # Under Ygg II, type is display-irrelevant: fusion vs basic at same
    # rank/suiteComponents produce the same branch.
    a = taxonomy.normalize({"type": "fusion", "level": "4★"})
    b = taxonomy.normalize({"type": "basic", "level": "4★"})
    assert taxonomy.resolveDisplayBranch(a) == taxonomy.resolveDisplayBranch(b) == "unique"


# ---------------------------------------------------------------------------
# rank ladder 0..6 across all three branches
# ---------------------------------------------------------------------------

SHARED_EXPECT = {0: "Basic", 1: "Awakened", 2: "Named", 3: "Evolved"}
SUITE_EXPECT = {4: "Extra", 5: "Ultimate", 6: "Apex"}
UNIQUE_EXPECT = {4: "Unique", 5: "Unique Ultimate", 6: "Unique Impossible"}


def test_rankword_shared_ladder_all_branches():
    # 0-3★ is branch-agnostic.
    for branch in ("standard", "suite", "unique"):
        for lvl, word in SHARED_EXPECT.items():
            assert taxonomy.rankWord(f"{lvl}★", branch) == word, (lvl, branch)


def test_rankword_suite_ladder():
    for lvl, word in SUITE_EXPECT.items():
        assert taxonomy.rankWord(f"{lvl}★", "suite") == word


def test_rankword_unique_ladder():
    for lvl, word in UNIQUE_EXPECT.items():
        assert taxonomy.rankWord(f"{lvl}★", "unique") == word


def test_ranklabel_format():
    assert taxonomy.rankLabel("5★", "unique") == "Unique Ultimate · 5★"
    assert taxonomy.rankLabel(4, "suite") == "Extra · 4★"
    assert taxonomy.rankLabel("2★", "standard") == "Named · 2★"


def test_ranklabel_full_ladder_never_banned():
    for branch in ("standard", "suite", "unique"):
        for lvl in range(0, 7):
            label = taxonomy.rankLabel(f"{lvl}★", branch)
            for bad in BANNED:
                assert bad not in label, (lvl, branch, label)


def test_rankword_full_ladder_never_banned():
    for branch in ("standard", "suite", "unique"):
        for lvl in range(0, 7):
            word = taxonomy.rankWord(f"{lvl}★", branch)
            for bad in BANNED:
                assert bad not in word, (lvl, branch, word)


# ---------------------------------------------------------------------------
# Absent-field fallback — raw vs pre-resolved
# ---------------------------------------------------------------------------

def test_fallback_raw_entry_derives_branch():
    # No emitted branch/rank fields; derive from type-independent logic.
    raw = {"type": "fusion", "level": "5★", "suiteComponents": ["a"]}
    n = taxonomy.normalize(raw)
    assert n["branch"] is None            # nothing pre-resolved
    assert taxonomy.resolveDisplayBranch(n) == "suite"


def test_fallback_preresolved_branch_honored_verbatim():
    # A stale snapshot emitted branch='suite' even though raw logic would say
    # 'unique' (no suiteComponents). The pre-resolved field wins.
    entry = {"type": "fusion", "level": "5★", "branch": "suite"}
    n = taxonomy.normalize(entry)
    assert n["branch"] == "suite"
    assert taxonomy.resolveDisplayBranch(n) == "suite"


def test_fallback_preresolved_rank_field():
    # `rank` field takes precedence over `level`/`namedMaxLevel`.
    n = taxonomy.normalize({"rank": 6, "suiteComponents": ["a"]})
    assert n["rank"] == 6
    assert taxonomy.resolveDisplayBranch(n) == "suite"


def test_fallback_namedmaxlevel_when_no_level():
    # gaia.json generic nodes carry only namedMaxLevel.
    n = taxonomy.normalize({"type": "fusion", "namedMaxLevel": "5★"})
    assert n["rank"] == 5
    assert taxonomy.resolveDisplayBranch(n) == "unique"  # no suiteComponents


def test_fallback_unrecognised_branch_field_is_derived():
    entry = {"type": "fusion", "level": "4★", "branch": "bogus"}
    n = taxonomy.normalize(entry)
    assert n["branch"] is None
    assert taxonomy.resolveDisplayBranch(n) == "unique"


def test_branchFor_convenience_raw():
    assert taxonomy.branchFor({"type": "basic", "level": "2★"}) == "standard"
    assert taxonomy.branchFor({"type": "fusion", "level": "4★",
                               "suiteComponents": ["a"]}) == "suite"
    assert taxonomy.branchFor({"type": "fusion", "level": "4★"}) == "unique"


def test_normalize_none_entry():
    n = taxonomy.normalize(None)
    assert n["rank"] == 0
    assert taxonomy.resolveDisplayBranch(n) == "standard"


# ---------------------------------------------------------------------------
# medallion
# ---------------------------------------------------------------------------

def test_medallion_tokens():
    assert taxonomy.medallion("unique") == taxonomy.MEDALLION_UNIQUE
    assert taxonomy.medallion("suite") == taxonomy.MEDALLION_SUITE
    assert taxonomy.medallion("standard") == taxonomy.MEDALLION_STANDARD
    # unknown branch -> neutral standard glyph
    assert taxonomy.medallion("wat") == taxonomy.MEDALLION_STANDARD


def test_medallion_distinct():
    tokens = {taxonomy.medallion(b) for b in ("unique", "suite", "standard")}
    assert len(tokens) == 3


# ---------------------------------------------------------------------------
# suiteComponentsPresent edge cases
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("entry,expected", [
    ({"suiteComponents": ["a"]}, True),
    ({"suiteComponents": []}, False),
    ({"suiteComponents": None}, False),
    ({}, False),
    ({"suiteComponents": ("a", "b")}, True),
])
def test_suite_components_present(entry, expected):
    assert taxonomy.suiteComponentsPresent(entry) is expected

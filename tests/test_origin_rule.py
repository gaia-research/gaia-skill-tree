"""Origin is automatic: highest merit per bucket (founder rulings 2026-10-30, EPIC #2189).

Regression guards: these fail if a fusion-prerequisite Origin requirement for
Uniques, an Origin star floor, a manual Origin flag, or a tie vacancy returns.
"""

from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gaia_cli.frozen import frozenIds, frozenLock, isSelfFrozen  # noqa: E402
from gaia_cli.origin import (  # noqa: E402
    bucketHolders,
    contributorHoldsOriginIn,
    deriveBucketOrigins,
    meritKey,
    publishedLevelNumber,
)


def c(sid, level, tm):
    return {"id": sid, "levelNumber": level, "tm": tm}


# --------------------------------------------------------------------------- rule

def test_merit_is_level_then_tm():
    assert meritKey(3, 50.0) > meritKey(2, 999.0)
    assert deriveBucketOrigins([c("a", 3, 60.0), c("b", 3, 95.0), c("z", 2, 400.0)]) == {"b"}


def test_tm_compares_at_published_precision():
    assert deriveBucketOrigins([c("a", 3, 50.001), c("b", 3, 50.004)]) == {"a", "b"}


def test_ties_all_hold_origin_and_there_is_no_vacancy():
    assert deriveBucketOrigins([c("a", 3, 50.0), c("b", 3, 50.0), c("c", 2, 70.0)]) == {"a", "b"}
    # The rule never consults a stored/incumbent flag.
    assert deriveBucketOrigins([{**c("a", 3, 50.0), "incumbent": True}, c("b", 3, 50.0)]) == {"a", "b"}


def test_one_star_can_be_origin_no_star_floor():
    assert deriveBucketOrigins([c("solo", 1, 0.0)]) == {"solo"}


def test_published_level_is_capped_by_grade():
    assert publishedLevelNumber("4★", "C") == 2
    assert publishedLevelNumber("3★", "ungraded") == 1
    assert publishedLevelNumber("2★", "S") == 2


def _named(sid, ref, level, tm, grade, **extra):
    owner = sid.split("/")[0]
    return {"id": sid, "contributor": owner, "genericSkillRef": ref, "status": "named",
            "level": level, "trustMagnitude": tm, "overallTrustGrade": grade, **extra}


_FROZEN_EVENT = [{"action": "upstream_deprecated", "timestamp": "2026-08-01T00:00:00Z"}]


def test_frozen_contender_competes_with_locked_values_and_can_win(monkeypatch):
    import gaia_cli.trustMagnitude as tmm
    monkeypatch.setattr(tmm, "computeTrustMagnitude", lambda *a, **k: 40.0)
    monkeypatch.setattr(tmm, "computeOverallTrustGradeFromSkill", lambda *a, **k: "C")
    live = _named("live/x", "g", "3★", 0, "ungraded")
    frozen = _named("old/x", "g", "3★", 94.92, "B", installable=False, timeline=_FROZEN_EVENT)
    merged = {live["id"]: live, frozen["id"]: frozen}
    # live recomputes to (C→2★, 40); frozen keeps its lock (B→3★, 94.92)
    assert bucketHolders("g", merged) == {"old/x"}


def test_stored_origin_flag_is_ignored(monkeypatch):
    import gaia_cli.trustMagnitude as tmm
    monkeypatch.setattr(tmm, "computeTrustMagnitude", lambda s, *a, **k: s["_tm"])
    monkeypatch.setattr(tmm, "computeOverallTrustGradeFromSkill", lambda *a, **k: "B")
    a = {**_named("a/x", "g", "3★", 0, "B", origin=True), "_tm": 60.0}
    b = {**_named("b/x", "g", "3★", 0, "B", origin=False), "_tm": 80.0}
    assert bucketHolders("g", {a["id"]: a, b["id"]: b}) == {"b/x"}


def test_suite_ultimate_origin_reads_derived_component_origin(monkeypatch):
    import gaia_cli.trustMagnitude as tmm
    monkeypatch.setattr(tmm, "computeTrustMagnitude", lambda s, *a, **k: s["_tm"])
    monkeypatch.setattr(tmm, "computeOverallTrustGradeFromSkill", lambda *a, **k: "B")
    mine = {**_named("me/comp", "g", "3★", 0, "B", origin=False), "_tm": 90.0}
    other = {**_named("you/comp", "g", "3★", 0, "B", origin=True), "_tm": 60.0}
    merged = {mine["id"]: mine, other["id"]: other}
    assert contributorHoldsOriginIn("me", ["me/comp"], merged) is True
    assert contributorHoldsOriginIn("you", ["you/comp"], merged) is False


# ------------------------------------------------------------------------- frozen

def test_frozen_definition_self_and_through_suite():
    personal = {"id": "m/personal", "suiteComponents": ["m/a"], "installable": False, "timeline": _FROZEN_EVENT}
    comp = {"id": "m/a"}
    via_ref = {"id": "m/b", "suiteRef": "m/personal"}
    live_suite = {"id": "m/skills", "suiteComponents": ["m/c"], "timeline": _FROZEN_EVENT}  # component removal only
    comp_c = {"id": "m/c"}
    explicit = {"id": "x/y", "frozen": True}
    not_installable = {"id": "x/z", "installable": False}
    ids = frozenIds([personal, comp, via_ref, live_suite, comp_c, explicit, not_installable])
    assert ids == {"m/personal", "m/a", "m/b", "x/y"}
    assert not isSelfFrozen(live_suite)


def test_frozen_lock_reads_cached_values():
    assert frozenLock({"trustMagnitude": 94.92, "overallTrustGrade": "B"}) == (94.92, "B")
    assert frozenLock({"trustMagnitude": 1.0}) is None


# ------------------------------------------------------------- named index (build)

def test_named_index_derives_origin_and_ignores_star_floor():
    from scripts.generateNamedIndex import apply_derived_origins

    buckets = {
        "solo": [{"id": "a/solo", "level": "1★", "overallTrustGrade": "ungraded", "trustMagnitude": 0.0, "origin": False}],
        "pair": [
            {"id": "a/p", "level": "3★", "overallTrustGrade": "B", "trustMagnitude": 50.0, "origin": True},
            {"id": "b/p", "level": "3★", "overallTrustGrade": "B", "trustMagnitude": 50.0, "origin": False},
            {"id": "c/p", "level": "4★", "overallTrustGrade": "C", "trustMagnitude": 30.0, "origin": True},
        ],
    }
    awaiting = [{"id": "z/await", "origin": True}]
    holders = apply_derived_origins(buckets, awaiting)
    assert holders["solo"] == {"a/solo"}
    assert holders["pair"] == {"a/p", "b/p"}  # c/p is capped to 2★ by grade C
    assert {e["id"]: e["origin"] for e in buckets["pair"]} == {"a/p": True, "b/p": True, "c/p": False}
    assert awaiting[0]["origin"] is False


def test_awakened_record_competes_for_origin():
    """Founder: "It is still the origin, it is just not 'named'." (r2-hermes)."""
    from scripts.generateNamedIndex import apply_derived_origins

    buckets = {"b": [{"id": "n/x", "level": "2★", "overallTrustGrade": "C", "trustMagnitude": 30.0}]}
    awaiting = [
        {"id": "x/hermes", "genericSkillRef": "x-twitter", "level": "1★"},
        {"id": "a/strong", "genericSkillRef": "b", "level": "1★"},
    ]
    holders = apply_derived_origins(buckets, awaiting, {"x/hermes": (1, 42.47), "a/strong": (1, 99.0)})
    assert holders["x-twitter"] == {"x/hermes"}
    assert awaiting[0]["origin"] is True
    assert holders["b"] == {"n/x"}  # level ranks before TM
    assert awaiting[1]["origin"] is False


def test_frontmatter_mirror_never_writes_frozen_files(tmp_path):
    from scripts.generateNamedIndex import sync_origin_frontmatter

    live = tmp_path / "live.md"
    frozen = tmp_path / "frozen.md"
    live.write_text("---\nid: a/live\norigin: false\nlevel: 2★\n---\nbody\n", encoding="utf-8")
    frozen.write_text("---\nid: a/frozen\norigin: false\nlevel: 2★\n---\nbody\n", encoding="utf-8")
    named = [(str(live), {"id": "a/live", "origin": False}), (str(frozen), {"id": "a/frozen", "origin": False})]
    buckets = {"g": [{"id": "a/live", "origin": True}, {"id": "a/frozen", "origin": True}]}
    changed = sync_origin_frontmatter(named, buckets, [], {"a/frozen"})
    assert changed == [("a/live", True)]
    assert "origin: true" in live.read_text(encoding="utf-8")
    assert "origin: false" in frozen.read_text(encoding="utf-8")


# ------------------------------------------------------------ regression guards

def test_unique_gate_has_no_fusion_prerequisite_origin():
    import gaia_cli.promotion as promotion

    src = inspect.getsource(promotion.checkUniqueBranchGate) + inspect.getsource(promotion._holds_bucket_origin)
    assert "prerequisites" not in src.replace("fusion-prerequisite Origin", "")
    assert not hasattr(promotion, "_contributor_holds_origin_in")


def test_named_index_has_no_origin_star_floor():
    text = (ROOT / "scripts" / "generateNamedIndex.py").read_text(encoding="utf-8")
    assert not re.search(r"origin.{0,80}is_redacted|is_redacted.{0,80}origin", text)


_DOC_GLOBS = [
    "META.md", "CONTEXT.md", "CLAUDE.md", "GOVERNANCE.md", "AGENTS.md",
    "docs/agents/*.md", ".agents/skills/**/*.md", ".claude/skills/**/*.md",
    "docs/index.html", "docs/trust/leaderboard/index.html",
]
_FORBIDDEN = [
    r"cannot hold Origin",
    r"≤1★ cannot hold Origin",
    r"<=1★ forbidden",
    r"origins? counted in \*{0,2}fusion structure",
    r"Unique gates count origins in fusion structure",
    r"Origin on a node in the generic parent's prerequisites",
    r"first published the technique",
    r"--origin true",
]


@pytest.mark.parametrize("pattern", _FORBIDDEN)
def test_retired_origin_rules_do_not_reappear_in_docs_or_skills(pattern):
    hits = []
    for glob in _DOC_GLOBS:
        for path in ROOT.glob(glob):
            if path.is_file() and re.search(pattern, path.read_text(encoding="utf-8")):
                hits.append(str(path.relative_to(ROOT)))
    assert hits == [], f"retired Origin rule {pattern!r} reappeared in {hits}"

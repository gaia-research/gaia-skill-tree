"""Regression for ADJ-180 / F73: the meta-sweep champion-cluster check.

Champion is a DERIVED, display-only ordering (rank desc, Origin first, id in
``generateNamedIndex.championSortKey``), never a stored ``champion`` field. The
old check flagged every multi-implementation generic as "no Champion
designated"; it must now flag only a derived Champion whose Trust Magnitude is
lower than another implementation's (META.md section 6.1).
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from generateNamedIndex import championSortKey  # noqa: E402
from run_meta_sweep import championClusterFindings  # noqa: E402


def skill(skillId, level, generic="g", origin=False, status="named"):
    meta = {"id": skillId, "level": level, "genericSkillRef": generic, "status": status}
    if origin:
        meta["origin"] = True
    return skillId, {"meta": meta, "body": "", "path": f"registry/named/{skillId}.md"}


def registry(*skills):
    return dict(skills)


def test_cluster_without_stored_champion_is_not_flagged():
    named = registry(skill("a/x", "3★"), skill("b/y", "2★"), skill("c/z", "2★"))
    # Champion a/x also has the highest TM: nothing to review, and no
    # "no Champion designated" finding exists any more.
    assert championClusterFindings(named, {"a/x": 90.0, "b/y": 50.0, "c/z": 10.0}) == []


def test_single_implementation_is_never_a_cluster():
    named = registry(skill("a/x", "3★"))
    assert championClusterFindings(named, {"a/x": 0.0}) == []


def test_flags_derived_champion_with_lower_tm_than_a_sibling():
    named = registry(skill("a/x", "3★"), skill("b/y", "2★"))
    found = championClusterFindings(named, {"a/x": 50.0, "b/y": 94.9})
    assert len(found) == 1
    assert found[0]["target"] == "g"
    assert found[0]["priority"] == "P3"
    assert "a/x" in found[0]["reason"] and "b/y" in found[0]["reason"]
    assert "do not write a champion field" in found[0]["suggestedAction"]


def test_equal_tm_is_not_flagged():
    named = registry(skill("a/x", "3★"), skill("b/y", "3★"))
    assert championClusterFindings(named, {"a/x": 50.0, "b/y": 50.0}) == []


def test_origin_breaks_a_rank_tie_for_champion():
    named = registry(skill("a/x", "3★"), skill("b/y", "3★", origin=True))
    # b/y is the derived Champion (Origin first); it has the lower TM, so flag.
    found = championClusterFindings(named, {"a/x": 80.0, "b/y": 40.0})
    assert len(found) == 1 and "Derived Champion 'b/y'" in found[0]["reason"]
    # ...and when the Origin holds the higher TM there is nothing to review.
    assert championClusterFindings(named, {"a/x": 40.0, "b/y": 80.0}) == []


def test_one_star_origin_flag_is_ignored_like_the_index_builder():
    # META 4.1: a <=1 star entry cannot hold Origin, so it cannot win the tie.
    named = registry(skill("a/x", "1★"), skill("b/y", "1★", origin=True))
    found = championClusterFindings(named, {"a/x": 10.0, "b/y": 90.0})
    # a/x sorts first (id) because b/y's Origin is cleared; a/x TM < b/y TM.
    assert len(found) == 1 and "Derived Champion 'a/x'" in found[0]["reason"]


def test_non_named_status_is_excluded():
    named = registry(skill("a/x", "3★"), skill("b/y", "1★", status="pre-named"))
    assert championClusterFindings(named, {"a/x": 1.0, "b/y": 99.0}) == []


def test_sort_key_is_rank_desc_origin_first_id():
    entries = [
        {"id": "c", "level": "2★"},
        {"id": "b", "level": "3★"},
        {"id": "a", "level": "3★", "origin": True},
        {"id": "d", "level": "3★"},
    ]
    assert [e["id"] for e in sorted(entries, key=championSortKey)] == ["a", "b", "d", "c"]

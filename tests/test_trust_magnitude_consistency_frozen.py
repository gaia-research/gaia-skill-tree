"""Frozen skills are checked against their locked stamp, never a fresh recomputation.

The 49.9 suite cap (#2378) moved the recomputed Trust Magnitude of frozen skills
whose stamps are locked and never rewritten (gaia_cli.frozen). The consistency
gate must not call that drift a violation, and must keep flagging the same drift
on non-frozen skills.
"""

from __future__ import annotations

import pytest

from scripts import check_trust_magnitude_consistency as gate

RECOMPUTED = 49.9


@pytest.fixture(autouse=True)
def drifting_recomputation(monkeypatch):
    monkeypatch.setattr(gate, "computeTrustMagnitude", lambda skill, merged: RECOMPUTED)
    monkeypatch.setattr(gate, "computeTrustMagnitudeInputHash", lambda skill: "same-hash")


def skill(skillId: str, **extra) -> dict:
    return {
        "id": skillId,
        "status": "named",
        "trustMagnitude": 50.0,
        "overallTrustGrade": "B",
        "trustMagnitudeInputHash": "same-hash",
        **extra,
    }


def index(skillId: str, tm: float = 50.0, grade: str = "B") -> dict:
    return {skillId: {"id": skillId, "trustMagnitude": tm, "overallTrustGrade": grade}}


def test_frozen_skill_whose_recomputation_drifts_is_not_a_violation():
    skills = [skill("a/frozen", frozen=True)]
    violations, cacheChecked, indexChecked = gate.findViolations(skills, {}, index("a/frozen"))
    assert violations == []
    assert indexChecked == 1
    assert cacheChecked == 0  # the lock is the stamp; there is nothing to re-derive


def test_non_frozen_skill_with_the_same_drift_is_still_a_violation():
    skills = [skill("a/live")]
    violations, cacheChecked, indexChecked = gate.findViolations(skills, {}, index("a/live"))
    assert cacheChecked == 1 and indexChecked == 1
    assert len(violations) == 2
    assert any("frontmatter trustMagnitude=50.0" in item for item in violations)
    assert any("named-skills.json trustMagnitude=50.0" in item for item in violations)


def test_frozen_skill_inherited_from_a_frozen_suite_uses_the_lock():
    skills = [
        skill("a/suite", frozen=True, suiteComponents=["a/member"]),
        skill("a/member", suiteRef="a/suite"),
    ]
    both = {**index("a/suite"), **index("a/member")}
    assert gate.findViolations(skills, {}, both)[0] == []


def test_index_that_drifts_from_the_lock_is_a_violation():
    skills = [skill("a/frozen", frozen=True)]
    violations, _, _ = gate.findViolations(skills, {}, index("a/frozen", tm=49.9))
    assert len(violations) == 1
    assert "locked stamp (frozen)" in violations[0]
    assert "50.0" in violations[0]


def test_index_grade_that_drifts_from_the_lock_is_a_violation():
    skills = [skill("a/frozen", frozen=True)]
    violations, _, _ = gate.findViolations(skills, {}, index("a/frozen", grade="A"))
    assert len(violations) == 1
    assert "locked grade B" in violations[0]


@pytest.mark.parametrize("broken", [{"trustMagnitude": None}, {"overallTrustGrade": "Z"}])
def test_frozen_skill_without_a_valid_lock_is_a_violation(broken):
    skills = [skill("a/frozen", frozen=True, **broken)]
    violations, _, _ = gate.findViolations(skills, {}, index("a/frozen"))
    assert len(violations) == 1
    assert "lacks a valid" in violations[0]

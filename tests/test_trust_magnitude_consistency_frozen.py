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
    assert "locked stamp 50.0 (frozen)" in violations[0]
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


FROZEN = {"id": "x/f", "status": "named", "frozen": True, "trustMagnitude": 50.0, "overallTrustGrade": "B"}


@pytest.mark.parametrize(
    "published, fragment",
    [
        ({}, "missing from registry/named-skills.json"),
        ({"x/f": {}}, "trustMagnitude=None"),
        ({"x/f": {"trustMagnitude": "NaN", "overallTrustGrade": "B"}}, "trustMagnitude='NaN'"),
        ({"x/f": {"trustMagnitude": float("nan"), "overallTrustGrade": "B"}}, "is not its locked stamp"),
        ({"x/f": {"trustMagnitude": float("inf"), "overallTrustGrade": "B"}}, "is not its locked stamp"),
        ({"x/f": {"trustMagnitude": True, "overallTrustGrade": "B"}}, "is not its locked stamp"),
        ({"x/f": {"trustMagnitude": 49.99, "overallTrustGrade": "B"}}, "trustMagnitude=49.99"),
        ({"x/f": {"trustMagnitude": 50.0}}, "overallTrustGrade=None"),
    ],
)
def test_frozen_index_must_publish_exactly_the_lock(published, fragment):
    violations, _, _ = gate.findViolations([dict(FROZEN)], {}, published)
    assert violations, "a bad published value for a frozen skill must be a violation"
    assert any(fragment in item for item in violations), violations


def test_frozen_index_exactly_equal_to_the_lock_passes():
    published = {"x/f": {"trustMagnitude": 50.0, "overallTrustGrade": "B"}}
    assert gate.findViolations([dict(FROZEN)], {}, published) == ([], 0, 1)


def test_unbuilt_index_skips_the_cross_check_but_an_empty_built_one_does_not():
    assert gate.findViolations([dict(FROZEN)], {}, None)[0] == []
    assert gate.findViolations([dict(FROZEN)], {}, {})[0]


def test_malformed_or_unreadable_inputs_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "named_skills_index_path", lambda registry: str(tmp_path / "named-skills.json"))
    assert gate._loadGeneratedIndex(str(tmp_path)) is None
    for broken in ("{not json", "[]", '{"buckets": []}', '{"buckets": {"a": [1]}}'):
        (tmp_path / "named-skills.json").write_text(broken, encoding="utf-8")
        with pytest.raises(gate.InputError):
            gate._loadGeneratedIndex(str(tmp_path))

    named = tmp_path / "registry" / "named" / "a"
    named.mkdir(parents=True)
    (named / "b.md").write_bytes(b"\xff\xfe not utf-8")
    monkeypatch.setattr(gate, "named_skills_dir", lambda registry: str(tmp_path / "registry" / "named"))
    with pytest.raises(gate.InputError):
        gate._loadNamedSkills(str(tmp_path))


@pytest.mark.parametrize("content", ["corrupt content without frontmatter", "", "---\n---\n", "---\nstatus: named\n---\n"])
def test_named_file_without_usable_frontmatter_fails_closed(tmp_path, monkeypatch, content):
    named = tmp_path / "registry" / "named" / "demo"
    named.mkdir(parents=True)
    (named / "f.md").write_text(content, encoding="utf-8")
    monkeypatch.setattr(gate, "named_skills_dir", lambda registry: str(tmp_path / "registry" / "named"))
    with pytest.raises(gate.InputError):
        gate._loadNamedSkills(str(tmp_path))


def test_main_exits_nonzero_when_a_named_file_is_malformed(tmp_path, monkeypatch, capsys):
    named = tmp_path / "registry" / "named" / "demo"
    named.mkdir(parents=True)
    (named / "f.md").write_text("corrupt content without frontmatter", encoding="utf-8")
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(gate, "named_skills_dir", lambda registry: str(tmp_path / "registry" / "named"))
    assert gate.main() == 1
    assert "cannot be established" in capsys.readouterr().out


@pytest.mark.parametrize("bad", [True, False, "50.0", "NaN", float("nan"), float("inf"), None])
def test_frozen_source_lock_of_the_wrong_type_is_a_violation(bad):
    frozen = {**FROZEN, "trustMagnitude": bad}
    # Even an index that equals the coerced value (True -> 1.0) must not rescue it.
    published = {"x/f": {"trustMagnitude": 1.0 if bad is True else 50.0, "overallTrustGrade": "B"}}
    violations, _, _ = gate.findViolations([frozen], {}, published)
    assert len(violations) == 1
    assert "lacks a valid" in violations[0]

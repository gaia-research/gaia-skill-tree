"""Frozen skills are checked against their locked stamp, never a fresh recomputation.

The 49.9 suite cap (#2378) moved the recomputed Trust Magnitude of frozen skills
whose stamps are locked and never rewritten (gaia_cli.frozen). The consistency
gate must not call that drift a violation, and must keep flagging the same drift
on non-frozen skills.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts import check_trust_magnitude_consistency as gate

RECOMPUTED = 49.9
REPO = Path(__file__).resolve().parent.parent


def writeSchema(root: Path) -> None:
    """Give a temporary registry the real named-skill schema (the status enum is read from it)."""
    target = root / "registry" / "schema"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "registry" / "schema" / "namedSkill.schema.json", target)


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


def test_missing_index_is_not_agreement_for_a_frozen_skill():
    violations, cacheChecked, indexChecked = gate.findViolations([dict(FROZEN)], {}, None)
    assert indexChecked == 0
    assert len(violations) == 1
    assert "named index not built" in violations[0]
    assert "scripts/generateNamedIndex.py" in violations[0]


def test_missing_index_is_skipped_only_with_the_explicit_opt_in():
    assert gate.findViolations([dict(FROZEN)], {}, None, allowMissingIndex=True)[0] == []
    # The opt-in never excuses a built index that lacks the frozen skill.
    assert gate.findViolations([dict(FROZEN)], {}, {}, allowMissingIndex=True)[0]


def _stageRegistry(tmp_path, monkeypatch, frozen=True):
    writeSchema(tmp_path)
    named = tmp_path / "registry" / "named" / "demo"
    named.mkdir(parents=True)
    lines = ["---", "id: demo/f", "status: named", "genericSkillRef: demo-generic"]
    if frozen:
        lines += ["frozen: true", "trustMagnitude: 50.0", "overallTrustGrade: B"]
    else:
        lines += ["trustMagnitude: 50.0", "trustMagnitudeInputHash: same-hash"]
    (named / "f.md").write_text("\n".join(lines + ["---", ""]), encoding="utf-8")
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(gate, "named_skills_dir", lambda registry: str(tmp_path / "registry" / "named"))
    monkeypatch.setattr(gate, "named_skills_index_path", lambda registry: str(tmp_path / "registry" / "named-skills.json"))
    monkeypatch.setattr(gate, "buildMergedSkillMap", lambda registry: {})


def test_main_fails_closed_when_the_index_is_absent(tmp_path, monkeypatch, capsys):
    _stageRegistry(tmp_path, monkeypatch)
    assert gate.main([]) == 1
    out = capsys.readouterr().out
    assert "named index not built; run scripts/generateNamedIndex.py (gaia dev docs)" in out


def test_main_fails_closed_for_an_absent_index_even_without_frozen_skills(tmp_path, monkeypatch):
    _stageRegistry(tmp_path, monkeypatch, frozen=False)
    assert gate.main([]) == 1


def test_main_passes_without_an_index_only_with_allow_missing_index(tmp_path, monkeypatch, capsys):
    _stageRegistry(tmp_path, monkeypatch)
    assert gate.main(["--allow-missing-index"]) == 0
    assert "skipped by --allow-missing-index" in capsys.readouterr().out


def test_main_passes_with_a_built_index_that_publishes_the_lock(tmp_path, monkeypatch):
    _stageRegistry(tmp_path, monkeypatch)
    index = {"buckets": {"g": [{"id": "demo/f", "trustMagnitude": 50.0, "overallTrustGrade": "B"}]}}
    (tmp_path / "registry" / "named-skills.json").write_text(json.dumps(index), encoding="utf-8")
    assert gate.main([]) == 0


def test_malformed_or_unreadable_inputs_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "named_skills_index_path", lambda registry: str(tmp_path / "named-skills.json"))
    assert gate._loadGeneratedIndex(str(tmp_path)) is None
    for broken in ("{not json", "[]", '{"buckets": []}', '{"buckets": {"a": [1]}}'):
        (tmp_path / "named-skills.json").write_text(broken, encoding="utf-8")
        with pytest.raises(gate.InputError):
            gate._loadGeneratedIndex(str(tmp_path))

    writeSchema(tmp_path)
    named = tmp_path / "registry" / "named" / "a"
    named.mkdir(parents=True)
    (named / "b.md").write_bytes(b"\xff\xfe not utf-8")
    monkeypatch.setattr(gate, "named_skills_dir", lambda registry: str(tmp_path / "registry" / "named"))
    with pytest.raises(gate.InputError):
        gate._loadNamedSkills(str(tmp_path))


@pytest.mark.parametrize("content", ["corrupt content without frontmatter", "", "---\n---\n", "---\nstatus: named\n---\n"])
def test_named_file_without_usable_frontmatter_fails_closed(tmp_path, monkeypatch, content):
    writeSchema(tmp_path)
    named = tmp_path / "registry" / "named" / "demo"
    named.mkdir(parents=True)
    (named / "f.md").write_text(content, encoding="utf-8")
    monkeypatch.setattr(gate, "named_skills_dir", lambda registry: str(tmp_path / "registry" / "named"))
    with pytest.raises(gate.InputError):
        gate._loadNamedSkills(str(tmp_path))


def test_main_exits_nonzero_when_a_named_file_is_malformed(tmp_path, monkeypatch, capsys):
    writeSchema(tmp_path)
    named = tmp_path / "registry" / "named" / "demo"
    named.mkdir(parents=True)
    (named / "f.md").write_text("corrupt content without frontmatter", encoding="utf-8")
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(gate, "named_skills_dir", lambda registry: str(tmp_path / "registry" / "named"))
    assert gate.main([]) == 1
    assert "cannot be established" in capsys.readouterr().out


@pytest.mark.parametrize("bad", [True, False, "50.0", "NaN", float("nan"), float("inf"), None])
def test_frozen_source_lock_of_the_wrong_type_is_a_violation(bad):
    frozen = {**FROZEN, "trustMagnitude": bad}
    # Even an index that equals the coerced value (True -> 1.0) must not rescue it.
    published = {"x/f": {"trustMagnitude": 1.0 if bad is True else 50.0, "overallTrustGrade": "B"}}
    violations, _, _ = gate.findViolations([frozen], {}, published)
    assert len(violations) == 1
    assert "lacks a valid" in violations[0]


# --------------------------------------------------------------------------
# One complete pass over every field the gate reads from a named file.
# Each case is (field, frontmatter override, message fragment). ``None`` removes the key.
# --------------------------------------------------------------------------

LIVE = {
    "id": "demo/live",
    "status": "named",
    "genericSkillRef": "demo-generic",
    "trustMagnitude": 50.0,
    "trustMagnitudeInputHash": "same-hash",
}

FIELD_CASES = [
    # id: a non-empty string
    ("id", None, "'id'"),
    ("id", "", "'id'"),
    ("id", "   ", "'id'"),
    ("id", 7, "'id'"),
    # status: present and in the schema enum (the reviewer's repro: id but no status)
    ("status", None, "'status'"),
    ("status", "frozenish", "'status'"),
    ("status", "", "'status'"),
    ("status", True, "'status'"),
    # frozen: a bool when present
    ("frozen", "yes", "'frozen'"),
    ("frozen", 1, "'frozen'"),
    # frozenAt, installable, suiteRef, suiteComponents, timeline: typed when present
    ("frozenAt", 20260101, "'frozenAt'"),
    ("frozenAt", "  ", "'frozenAt'"),
    ("installable", "false", "'installable'"),
    ("suiteRef", 3, "'suiteRef'"),
    ("suiteRef", "", "'suiteRef'"),
    ("suiteComponents", "a/b", "'suiteComponents'"),
    ("suiteComponents", ["a/b", 4], "'suiteComponents'"),
    ("timeline", "upstream_deprecated", "'timeline'"),
    ("timeline", ["upstream_deprecated"], "'timeline'"),
    # genericSkillRef: required for a named record
    ("genericSkillRef", None, "'genericSkillRef'"),
    ("genericSkillRef", "", "'genericSkillRef'"),
    ("genericSkillRef", 5, "'genericSkillRef'"),
    # stamp and hash: required, finite and typed for a non-frozen named record
    ("trustMagnitude", None, "'trustMagnitude'"),
    ("trustMagnitude", "50.0", "'trustMagnitude'"),
    ("trustMagnitude", True, "'trustMagnitude'"),
    ("trustMagnitude", float("nan"), "'trustMagnitude'"),
    ("trustMagnitude", float("inf"), "'trustMagnitude'"),
    ("trustMagnitudeInputHash", None, "'trustMagnitudeInputHash'"),
    ("trustMagnitudeInputHash", "", "'trustMagnitudeInputHash'"),
    ("trustMagnitudeInputHash", 12, "'trustMagnitudeInputHash'"),
]


def yamlLine(key, value) -> str:
    if isinstance(value, float) and value != value:
        return f"{key}: .nan"
    if isinstance(value, float) and value in (float("inf"), float("-inf")):
        return f"{key}: .inf"
    return f"{key}: {json.dumps(value)}"


def stageFile(tmp_path, monkeypatch, meta: dict) -> Path:
    writeSchema(tmp_path)
    named = tmp_path / "registry" / "named" / "demo"
    named.mkdir(parents=True, exist_ok=True)
    path = named / "skill.md"
    path.write_text("---\n" + "\n".join(yamlLine(k, v) for k, v in meta.items()) + "\n---\n", encoding="utf-8")
    monkeypatch.setattr(gate, "named_skills_dir", lambda registry: str(tmp_path / "registry" / "named"))
    return path


@pytest.mark.parametrize("field, value, fragment", FIELD_CASES)
def test_every_field_the_gate_reads_aborts_with_file_and_field(tmp_path, monkeypatch, field, value, fragment):
    meta = dict(LIVE)
    if value is None:
        meta.pop(field)
    else:
        meta[field] = value
    path = stageFile(tmp_path, monkeypatch, meta)
    with pytest.raises(gate.InputError) as caught:
        gate._loadNamedSkills(str(tmp_path))
    assert str(path) in str(caught.value), "the message must name the file"
    assert fragment in str(caught.value), "the message must name the field"


def test_the_reviewers_repro_a_frozen_skill_without_status_aborts(tmp_path, monkeypatch):
    path = stageFile(tmp_path, monkeypatch, {"id": "frozen-skill", "frozen": True, "trustMagnitude": 50, "overallTrustGrade": "A"})
    with pytest.raises(gate.InputError, match="'status'") as caught:
        gate._loadNamedSkills(str(tmp_path))
    assert str(path) in str(caught.value)


def test_non_named_status_is_excluded_explicitly_but_still_in_the_frozen_census(tmp_path, monkeypatch):
    stageFile(tmp_path, monkeypatch, {"id": "demo/awake", "status": "awakened"})
    records = gate._loadNamedSkills(str(tmp_path))
    assert [r["id"] for r in records] == ["demo/awake"]
    # No stamp or genericSkillRef is demanded of an excluded status, and no check runs on it.
    assert gate.findViolations(records, {}, {}) == ([], 0, 0)
    # But a frozen awakened capstone still freezes its named members.
    capstone = {"id": "demo/cap", "status": "awakened", "frozen": True, "suiteComponents": ["demo/live"]}
    member = {**LIVE, "trustMagnitude": 50.0, "overallTrustGrade": "B"}
    violations, _, _ = gate.findViolations([capstone, member], {}, {"demo/live": {"trustMagnitude": 50.0, "overallTrustGrade": "B"}})
    assert violations == []


def test_frozen_through_the_timeline_is_found_and_its_lock_enforced():
    frozen = {**LIVE, "timeline": [{"action": "upstream_deprecated"}], "trustMagnitude": 50.0, "overallTrustGrade": "B"}
    violations, _, _ = gate.findViolations([frozen], {}, {"demo/live": {"trustMagnitude": 49.9, "overallTrustGrade": "B"}})
    assert len(violations) == 1 and "locked stamp 50.0 (frozen)" in violations[0]


def test_a_frozen_skill_missing_from_a_built_index_is_reported_even_with_a_valid_lock():
    frozen = {**LIVE, "frozen": True, "overallTrustGrade": "B"}
    violations, _, _ = gate.findViolations([frozen], {}, {})
    assert violations and "missing from registry/named-skills.json" in violations[0]


def test_duplicate_ids_abort(tmp_path, monkeypatch):
    path = stageFile(tmp_path, monkeypatch, dict(LIVE))
    (path.parent / "other.md").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(gate.InputError, match="'id'"):
        gate._loadNamedSkills(str(tmp_path))


@pytest.mark.parametrize("published", [{}, {"trustMagnitude": "x"}, {"trustMagnitude": float("nan")}, {"trustMagnitude": True}])
def test_non_frozen_index_value_must_be_a_finite_number(published):
    violations, _, indexChecked = gate.findViolations([dict(LIVE)], {}, {"demo/live": published})
    assert indexChecked == 1
    assert any("not a finite number" in item for item in violations)


def test_a_fully_valid_non_frozen_record_loads(tmp_path, monkeypatch):
    stageFile(tmp_path, monkeypatch, dict(LIVE))
    assert [r["id"] for r in gate._loadNamedSkills(str(tmp_path))] == ["demo/live"]


# --------------------------------------------------------------------------
# Round-5 findings (a)-(e) and schema-derived validation, table-driven.
# --------------------------------------------------------------------------

def realSchema() -> dict:
    return json.loads((REPO / "registry/schema/namedSkill.schema.json").read_text(encoding="utf-8"))


def writeCustomSchema(root: Path, mutate) -> Path:
    schema = realSchema()
    mutate(schema)
    target = root / "registry" / "schema"
    target.mkdir(parents=True, exist_ok=True)
    path = target / "namedSkill.schema.json"
    path.write_text(json.dumps(schema), encoding="utf-8")
    return path


def test_the_gate_reads_status_and_grade_sets_from_the_schema(tmp_path):
    writeSchema(tmp_path)
    context = gate._loadSchema(str(tmp_path))
    schema = realSchema()["properties"]
    assert context.statuses == frozenset(schema["status"]["enum"])
    assert context.grades == frozenset(schema["overallTrustGrade"]["enum"])
    # gaia_cli.frozen keeps its own grade set; the two must never diverge.
    from gaia_cli import frozen
    assert frozen._VALID_GRADES == context.grades
    writeCustomSchema(tmp_path, lambda s: s["properties"]["status"].update(enum=["named", "retired"]))
    assert gate._loadSchema(str(tmp_path)).statuses == {"named", "retired"}


# (e) a malformed schema enum, or schema, aborts
@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s["properties"]["status"].update(enum={"named": 1, "awakened": 2}),  # object, not a list
        lambda s: s["properties"]["status"].update(enum="named"),
        lambda s: s["properties"]["status"].update(enum=[]),
        lambda s: s["properties"]["status"].update(enum=["named", 3]),
        lambda s: s["properties"]["status"].update(enum=["named", ""]),
        lambda s: s["properties"]["status"].pop("enum"),
        lambda s: s["properties"]["status"].update(enum=["awakened"]),  # no gated status
        lambda s: s["properties"]["overallTrustGrade"].update(enum={"S": 1}),
        lambda s: s["properties"]["overallTrustGrade"].update(enum=[]),
        lambda s: s["properties"].pop("trustMagnitude"),
        lambda s: s["properties"]["evidence"].update(type="object"),
        lambda s: s.pop("properties"),
    ],
)
def test_a_malformed_schema_aborts(tmp_path, mutate):
    writeCustomSchema(tmp_path, mutate)
    with pytest.raises(gate.InputError):
        gate._loadSchema(str(tmp_path))


def test_an_unreadable_or_non_json_schema_aborts(tmp_path):
    with pytest.raises(gate.InputError):
        gate._loadSchema(str(tmp_path))
    (tmp_path / "registry" / "schema").mkdir(parents=True)
    (tmp_path / "registry" / "schema" / "namedSkill.schema.json").write_text("{nope", encoding="utf-8")
    with pytest.raises(gate.InputError):
        gate._loadSchema(str(tmp_path))


# (a) timeline items and null; (c) evidence shape; (d) lock minimum; schema-derived types
RECORD_CASES = [
    # (a) timeline action must be a non-empty string; null is rejected
    ("timeline", [{"timestamp": "2026-01-01"}], "'action'"),
    ("timeline", [{"action": None}], "'action'"),
    ("timeline", [{"action": ""}], "'action'"),
    ("timeline", [{"action": 5}], "'action'"),
    ("timeline", [{"action": "note"}, {"details": "x"}], "'timeline'[1]"),
    ("timeline", None, "'timeline'"),
    ("timeline", {"action": "upstream_deprecated"}, "'timeline'"),
    # (c) evidence must be an array of mappings
    ("evidence", {"type": "repo-own"}, "'evidence'"),
    ("evidence", "repo-own", "'evidence'"),
    ("evidence", [3], "'evidence'[0]"),
    ("evidence", [{"type": "repo-own"}, "x"], "'evidence'[1]"),
    ("evidence", None, "'evidence'"),
    # (d) the TM minimum is the schema's, and the grade set is the schema's
    ("trustMagnitude", -0.01, "'trustMagnitude'"),
    ("trustMagnitude", -50, "'trustMagnitude'"),
    ("overallTrustGrade", "D", "'overallTrustGrade'"),
    ("overallTrustGrade", None, "'overallTrustGrade'"),
    # schema-derived suite fields and explicit non-schema fields
    ("suiteRef", "Not A Ref", "'suiteRef'"),
    ("frozen", None, "'frozen'"),
]


@pytest.mark.parametrize("field, value, fragment", RECORD_CASES)
def test_schema_derived_and_explicit_record_checks_abort(tmp_path, monkeypatch, field, value, fragment):
    meta = {**LIVE, field: value}
    path = stageFile(tmp_path, monkeypatch, meta)
    with pytest.raises(gate.InputError) as caught:
        gate._loadNamedSkills(str(tmp_path))
    assert str(path) in str(caught.value)
    assert fragment in str(caught.value)


def test_a_missing_evidence_key_is_accepted_because_real_files_omit_it(tmp_path, monkeypatch):
    stageFile(tmp_path, monkeypatch, dict(LIVE))  # LIVE has no evidence key (61 real files have none)
    assert gate._loadNamedSkills(str(tmp_path))


def test_a_well_formed_timeline_and_evidence_load(tmp_path, monkeypatch):
    meta = {**LIVE, "timeline": [{"action": "note", "details": "x"}], "evidence": [{"type": "repo-own", "updatedAt": "2026-01-01"}]}
    stageFile(tmp_path, monkeypatch, meta)
    assert gate._loadNamedSkills(str(tmp_path))  # updatedAt is real drift; item schema is deliberately not applied


# (a) the gate and frozen.py must agree on what freezes a skill
@pytest.mark.parametrize(
    "timeline, frozenExpected",
    [
        ([{"action": "upstream_deprecated"}], True),
        ([{"action": "note"}, {"action": "upstream_deprecated"}], True),
        ([{"action": "upstream_deprecated "}], False),
        ([{"action": "Upstream_Deprecated"}], False),
        ([{"action": "note"}], False),
    ],
)
def test_timeline_freezing_is_decided_by_frozen_py_alone(timeline, frozenExpected):
    from gaia_cli.frozen import frozenIds
    meta = {**LIVE, "timeline": timeline, "overallTrustGrade": "B"}
    assert (meta["id"] in frozenIds([meta])) is frozenExpected
    published = {meta["id"]: {"trustMagnitude": 49.0, "overallTrustGrade": "B"}}
    violations, _, _ = gate.findViolations([meta], {}, published)
    # A frozen skill is compared exactly against its lock (49.0 != 50.0); a live one is not.
    assert any("locked stamp" in item for item in violations) is frozenExpected


# (d) a negative lock is not a lock
@pytest.mark.parametrize("tm", [-0.01, -1, -250.0])
def test_a_negative_frozen_lock_is_invalid_and_a_violation(tm):
    from gaia_cli.frozen import frozenLock
    assert frozenLock({"trustMagnitude": tm, "overallTrustGrade": "B"}) is None
    frozen = {"id": "x/f", "status": "named", "frozen": True, "trustMagnitude": tm, "overallTrustGrade": "B"}
    violations, _, _ = gate.findViolations([frozen], {}, {"x/f": {"trustMagnitude": tm, "overallTrustGrade": "B"}})
    assert len(violations) == 1 and "lacks a valid" in violations[0]


def test_a_zero_lock_is_valid():
    from gaia_cli.frozen import frozenLock
    assert frozenLock({"trustMagnitude": 0, "overallTrustGrade": "ungraded"}) == (0.0, "ungraded")


# (b) the generated index: structure and duplicates
INDEX_CASES = [
    ('{"buckets": {"a": [{"id": "x/y"}], "b": [{"id": "x/y"}]}}', "duplicate id 'x/y'"),
    ('{"buckets": {"a": [{"id": "x/y"}, {"id": "x/y"}]}}', "duplicate id 'x/y'"),
    ('{"buckets": {"a": [{"trustMagnitude": 1}]}}', "non-empty string 'id'"),
    ('{"buckets": {"a": [{"id": ""}]}}', "non-empty string 'id'"),
    ('{"buckets": {"a": [{"id": 4}]}}', "non-empty string 'id'"),
    ('{"buckets": {"a": ["x/y"]}}', "non-empty string 'id'"),
    ('{"buckets": {"a": {"id": "x/y"}}}', "must be a list"),
    ('{"buckets": []}', "'buckets' object"),
    ('{"buckets": null}', "'buckets' object"),
    ("[]", "'buckets' object"),
    ("{}", "'buckets' object"),
    ("{not json", "malformed"),
]


@pytest.mark.parametrize("content, fragment", INDEX_CASES)
def test_the_generated_index_must_be_valid_and_duplicate_free(tmp_path, monkeypatch, content, fragment):
    monkeypatch.setattr(gate, "named_skills_index_path", lambda registry: str(tmp_path / "named-skills.json"))
    (tmp_path / "named-skills.json").write_text(content, encoding="utf-8")
    with pytest.raises(gate.InputError, match=fragment):
        gate._loadGeneratedIndex(str(tmp_path))


def test_a_valid_index_loads_and_an_empty_one_is_valid(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "named_skills_index_path", lambda registry: str(tmp_path / "named-skills.json"))
    (tmp_path / "named-skills.json").write_text('{"buckets": {"a": [{"id": "x/y"}], "b": []}}', encoding="utf-8")
    assert set(gate._loadGeneratedIndex(str(tmp_path))) == {"x/y"}
    (tmp_path / "named-skills.json").write_text('{"buckets": {}}', encoding="utf-8")
    assert gate._loadGeneratedIndex(str(tmp_path)) == {}


def test_a_schema_invalid_record_aborts_the_gate(tmp_path, monkeypatch, capsys):
    _stageRegistry(tmp_path, monkeypatch)
    index = {"buckets": {"g": [{"id": "demo/f", "trustMagnitude": 50.0, "overallTrustGrade": "B"}]}}
    (tmp_path / "registry" / "named-skills.json").write_text(json.dumps(index), encoding="utf-8")
    assert gate.main([]) == 0  # a valid record and index pass
    skill = tmp_path / "registry" / "named" / "demo" / "f.md"
    skill.write_text(skill.read_text(encoding="utf-8").replace("trustMagnitude: 50.0", "trustMagnitude: -3.0"), encoding="utf-8")
    assert gate.main([]) == 1
    out = capsys.readouterr().out
    assert "cannot be established" in out and "'trustMagnitude'" in out and str(skill) in out

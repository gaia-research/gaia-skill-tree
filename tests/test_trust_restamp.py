"""Event-driven Trust Magnitude restamp (founder ruling 2026-11-06, #1642, option 8A).

Proves, on a synthetic registry, the two halves of the ruling:

* stale stamps are cleared inside the evidence-changing invocation, for the
  affected skills only, and
* nothing but a derived stamp ever moves: no star level, no grade that would
  disagree with a level, no frozen skill, and no skill the gate holds.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from gaia_cli.commands.dev.calibrate import calibrate_trust_magnitude_command
from gaia_cli.commands.dev.evidence import meta_evidence_command, meta_rm_evidence_command
from gaia_cli.registryMaps import buildMergedSkillMap
from gaia_cli.steward.sensors import TrustCalibrationDriftSensor
from gaia_cli.trustMagnitude import (
    computeOverallTrustGradeFromSkill,
    computeTrustMagnitude,
    computeTrustMagnitudeInputHash,
)
from tests.steward.sensor_fixtures import commit_all, make_repo
from gaia_cli.trustRestamp import (
    RestampVerificationError,
    TrustFingerprint,
    affectedSkillIds,
    holdReasons,
    isRecomputationOnly,
    namedTrustSnapshot,
    protectedState,
    restampAfterEvidenceChange,
    verifyRestamp,
)

pytestmark = [pytest.mark.integration]

NOW = "2026-11-07T00:00:00Z"
PARENT_SOURCE = "https://arxiv.org/abs/2401.00001"


def _meta() -> dict:
    return {
        "evidence": {
            "gradeThresholds": {"S": 250, "A": 100, "B": 50, "C": 20},
            "types": [
                {"id": "arxiv", "gradeCeiling": "A"},
                {"id": "github-stars-own", "gradeCeiling": "B"},
                {"id": "repo-own", "gradeCeiling": "S"},
            ],
            "perRowGradeThresholds": {},
        }
    }


def _generic(root: Path, skill_id: str, evidence: list | None = None) -> None:
    nodes = root / "registry" / "nodes" / "basic"
    nodes.mkdir(parents=True, exist_ok=True)
    (nodes / f"{skill_id}.json").write_text(json.dumps({
        "id": skill_id,
        "name": skill_id,
        "type": "basic",
        "description": "A generic parent used by the restamp tests.",
        "evidence": evidence or [],
        "timeline": [],
    }, indent=2), encoding="utf-8")


def _named(root: Path, slug: str, *, level: str, parent: str, stars: int = 1000, **extra: object) -> Path:
    contributor, name = slug.split("/", 1)
    folder = root / "registry" / "named" / contributor
    folder.mkdir(parents=True, exist_ok=True)
    skill = {
        "id": slug,
        "title": name,
        "contributor": contributor,
        "status": "named",
        "level": level,
        "genericSkillRef": parent,
        "evidence": [{
            "type": "github-stars-own",
            "source": f"https://github.com/{slug}",
            "stars": stars,
            "grade": "B",
        }],
        **extra,
    }
    path = folder / f"{name}.md"
    path.write_text("---\n" + yaml.safe_dump(skill, sort_keys=False, allow_unicode=True) + "---\n\n# body\n", encoding="utf-8")
    return path


def _read(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])


def _stamp(root: Path, path: Path) -> None:
    """Write a fresh, correct stamp the way the engine would."""
    context = buildMergedSkillMap(root)
    skill = _read(path)
    live = context[skill["id"]]
    skill["trustMagnitude"] = round(computeTrustMagnitude(live, context), 2)
    skill["overallTrustGrade"] = computeOverallTrustGradeFromSkill(live, context)
    skill["trustMagnitudeInputHash"] = computeTrustMagnitudeInputHash(live)
    body = path.read_text(encoding="utf-8").split("---", 2)[2]
    path.write_text("---\n" + yaml.safe_dump(skill, sort_keys=False, allow_unicode=True) + "---" + body, encoding="utf-8")


def _set(path: Path, **fields: object) -> None:
    skill = _read(path)
    skill.update(fields)
    body = path.read_text(encoding="utf-8").split("---", 2)[2]
    path.write_text("---\n" + yaml.safe_dump(skill, sort_keys=False, allow_unicode=True) + "---" + body, encoding="utf-8")


@pytest.fixture
def registry(tmp_path, monkeypatch):
    monkeypatch.setattr("gaia_cli.commands.dev.evidence._get_contributor", lambda: "tester")
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._get_contributor", lambda: "tester")
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True)
    (schema / "meta.json").write_text(json.dumps(_meta()), encoding="utf-8")
    _generic(tmp_path, "parent")
    _generic(tmp_path, "other-parent")
    paths = {
        # Affected and a pure recomputation: grade B agrees with 3★.
        "pure": _named(tmp_path, "acme/pure", level="3★", parent="parent"),
        # Affected but not a recomputation: grade B disagrees with 2★.
        "governed": _named(tmp_path, "acme/governed", level="2★", parent="parent"),
        # Frozen, inherits from the same parent.
        "frozen": _named(tmp_path, "acme/frozen", level="3★", parent="parent", frozen=True),
        # Not affected by evidence on `parent`; carries a stale stamp of its own.
        "unaffected": _named(tmp_path, "acme/unaffected", level="3★", parent="other-parent"),
        # Affected but never stamped: the refresh must not create a stamp.
        "unstamped": _named(tmp_path, "acme/unstamped", level="3★", parent="parent"),
    }
    for key in ("pure", "governed", "frozen"):
        _stamp(tmp_path, paths[key])
    _set(paths["unaffected"], trustMagnitude=10.0, overallTrustGrade="B", trustMagnitudeInputHash="stale")
    paths["root"] = tmp_path
    make_repo(tmp_path, {})  # the sensor reads the version-control inventory
    return paths


def _evidence(root: Path, skill_id: str, *, stars: int | None = None, citations: int | None = 50,
              evidence_type: str = "arxiv", **overrides) -> SimpleNamespace:
    base = dict(
        registry=str(root), skill_id=skill_id, source=PARENT_SOURCE, index=None,
        evidence_type=evidence_type, trust=None, evaluator=None, date=None, notes=None,
        stars=stars, views=None, citations=citations, reviewers=None, commits=None,
        contributors=None, skill_count_in_repo=None, percentile=None, source_started_at=None,
        downloads=None, likes=None, comments=None, no_build=True, no_restamp=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _rm(root: Path, skill_id: str, **overrides) -> SimpleNamespace:
    base = dict(registry=str(root), skill_id=skill_id, index=None, source=PARENT_SOURCE,
                no_build=True, yes=True, no_restamp=False)
    base.update(overrides)
    return SimpleNamespace(**base)


def _stale(root: Path) -> dict[str, dict]:
    commit_all(root)
    return {
        o.subject.id: dict(o.observed_state)
        for o in TrustCalibrationDriftSensor().scan(root, NOW)
        if o.kind == "trust_stamp_stale"
    }


def _levels_and_grades(registry: dict) -> dict:
    return {
        key: (_read(path)["level"], _read(path).get("overallTrustGrade"))
        for key, path in registry.items() if key != "root"
    }


def test_the_fixture_starts_with_one_stale_stamp_the_unaffected_one(registry) -> None:
    assert set(_stale(registry["root"])) == {"acme/unaffected"}


def test_evidence_on_the_generic_restamps_only_the_affected_pure_recomputations(registry, capsys) -> None:
    root = registry["root"]
    before_bytes = {key: registry[key].read_bytes() for key in ("governed", "frozen", "unaffected", "unstamped")}
    before_levels = _levels_and_grades(registry)
    old_grade = _read(registry["pure"])["overallTrustGrade"]

    meta_evidence_command(_evidence(root, "parent"))

    pure = _read(registry["pure"])
    assert pure["overallTrustGrade"] == old_grade  # a restamp never changes the stored grade
    context = buildMergedSkillMap(root)
    assert pure["trustMagnitude"] == round(computeTrustMagnitude(context["acme/pure"], context), 2)
    assert pure["trustMagnitude"] > 70.0
    assert pure["trustMagnitudeInputHash"] == computeTrustMagnitudeInputHash(pure)
    # The refresh is one CLI-logged timeline event that says it was event-driven.
    events = [e for e in pure["timeline"] if e["action"] == "recalibrate_trust_magnitude"]
    assert len(events) == 1 and "event-driven restamp after gaia dev evidence" in events[0]["details"]
    assert "star level unchanged" in events[0]["details"]

    # Nothing else moved: held, frozen, unaffected and unstamped files are byte-identical.
    for key, content in before_bytes.items():
        assert registry[key].read_bytes() == content, key
    # No star or grade moved on any skill.
    assert _levels_and_grades(registry) == before_levels
    out = capsys.readouterr().out
    assert "HELD acme/governed" in out and "no star level written" in out

    # The stale stamp the evidence caused is cleared; the held one and the
    # unrelated pre-existing one remain visible to the periodic backstop.
    stale = _stale(root)
    assert "acme/pure" not in stale
    assert stale["acme/governed"]["recomputationOnly"] is False
    assert "acme/unaffected" in stale
    assert "acme/frozen" in stale  # frozen: untouched, still measured, never restamped


def test_a_removed_row_restamps_back_down_through_the_same_path(registry) -> None:
    root = registry["root"]
    meta_evidence_command(_evidence(root, "parent"))
    raised = _read(registry["pure"])["trustMagnitude"]

    meta_rm_evidence_command(_rm(root, "parent"))

    lowered = _read(registry["pure"])
    assert lowered["trustMagnitude"] < raised
    assert lowered["level"] == "3★"
    assert "acme/pure" not in _stale(root)
    details = [e["details"] for e in lowered["timeline"] if e["action"] == "recalibrate_trust_magnitude"]
    assert any("after gaia dev rm-evidence" in item for item in details)


def test_evidence_on_a_named_skill_restamps_that_skill(registry) -> None:
    root = registry["root"]
    meta_evidence_command(_evidence(
        root, "acme/pure", stars=None, citations=None, evidence_type="repo-own",
        source="https://github.com/acme/pure", commits=816, contributors=2,
    ))

    pure = _read(registry["pure"])
    context = buildMergedSkillMap(root)
    assert pure["trustMagnitude"] == round(computeTrustMagnitude(context["acme/pure"], context), 2)
    assert pure["level"] == "3★"
    assert "acme/pure" not in _stale(root)


def test_no_restamp_leaves_the_stamp_stale_for_the_backstop(registry) -> None:
    root = registry["root"]
    before = registry["pure"].read_bytes()

    meta_evidence_command(_evidence(root, "parent", no_restamp=True))

    assert registry["pure"].read_bytes() == before
    assert "acme/pure" in _stale(root)


def test_a_restamp_that_would_move_a_grade_away_from_its_level_is_held_not_written(registry, capsys) -> None:
    root = registry["root"]
    # Push `pure` from grade B to grade A: a restamp would now describe a level it does not hold.
    before = registry["pure"].read_bytes()

    meta_evidence_command(_evidence(root, "parent", citations=500))

    assert registry["pure"].read_bytes() == before
    assert "HELD acme/pure" in capsys.readouterr().out
    assert _stale(root)["acme/pure"]["recomputationOnly"] is False


def test_the_verb_gates_on_recomputation_only_even_when_called_directly(registry) -> None:
    root = registry["root"]
    before_governed = registry["governed"].read_bytes()
    _set(registry["pure"], trustMagnitude=1.0)  # stale, but a pure recomputation
    _set(registry["governed"], trustMagnitude=1.0)  # stale and level-disagreeing

    result = calibrate_trust_magnitude_command(SimpleNamespace(
        registry=str(root), skill=None, all=True, dry_run=False, yes=True, no_build=True,
        refresh_apex=False, recomputation_only=True,
    ))

    assert "acme/pure" in result["changed"]
    assert [item["skillId"] for item in result["held"]] == ["acme/governed"]
    assert "acme/unstamped" in result["unchanged"]
    assert "trustMagnitude" not in _read(registry["unstamped"])  # never creates a stamp
    assert _read(registry["governed"])["trustMagnitude"] == 1.0
    assert registry["governed"].read_bytes() != before_governed  # only because the test seeded it
    # Frozen skills are skipped by --all, not refreshed.
    assert "acme/frozen" not in result["changed"]


def test_the_all_form_without_the_flag_keeps_its_old_behaviour(registry) -> None:
    root = registry["root"]
    _set(registry["governed"], trustMagnitude=1.0)

    result = calibrate_trust_magnitude_command(SimpleNamespace(
        registry=str(root), skill=None, all=True, dry_run=False, yes=True, no_build=True, refresh_apex=False,
    ))

    assert result["held"] == []
    assert "acme/governed" in result["changed"]


def test_the_gate_is_the_one_the_sensor_stamps_on_every_finding() -> None:
    assert isRecomputationOnly("3★", "B", "B") and not isRecomputationOnly("2★", "B", "B")
    # The refresh may not rewrite the grade already stored, nor introduce one.
    assert not isRecomputationOnly("3★", "B", "A")
    assert not isRecomputationOnly("3★", "B", None)
    assert isRecomputationOnly("1★", "ungraded", "ungraded") and not isRecomputationOnly("4★", "S", "S")
    assert not isRecomputationOnly("6★", "S", "S") and not isRecomputationOnly(None, "ungraded", "ungraded")
    assert holdReasons("2★", "B", "B") == ["level-disagrees-with-computed-grade"]
    assert holdReasons("3★", "B", None) == ["stored-grade-missing"]
    assert holdReasons("3★", "B", "A") == ["stored-grade-differs-from-computed-grade"]
    assert holdReasons("2★", "B", "A") == ["level-disagrees-with-computed-grade", "stored-grade-differs-from-computed-grade"]
    assert holdReasons("3★", "B", "B") == []


def _fp(tm: float, grade: str = "B", digest: str = "h") -> TrustFingerprint:
    return TrustFingerprint(tm=tm, grade=grade, inputHash=digest)


def test_affected_skills_are_those_whose_tm_grade_or_hash_moved_plus_the_target() -> None:
    before = {"a": _fp(10.0), "b": _fp(20.0), "c": _fp(30.0), "g": _fp(40.0), "h": _fp(50.0)}
    after = {
        "a": _fp(10.0),
        "b": _fp(25.0),  # TM moved
        "c": _fp(30.0),
        "d": _fp(1.0),
        "g": _fp(40.0, grade="A"),  # grade moved, TM unchanged (type diversity or witness)
        "h": _fp(50.0, digest="other"),  # own-input hash moved, TM unchanged
    }
    assert affectedSkillIds(before, after, "c") == ("b", "c", "g", "h")
    assert affectedSkillIds(before, after, "owner/new") == ("b", "g", "h")
    assert affectedSkillIds(before, after, "d") == ("b", "d", "g", "h")


def test_namedTrustSnapshot_is_read_only(registry) -> None:
    root = registry["root"]
    before = {key: path.read_bytes() for key, path in registry.items() if key != "root"}

    snapshot = namedTrustSnapshot(str(root))

    assert set(snapshot) == {"acme/pure", "acme/governed", "acme/frozen", "acme/unaffected", "acme/unstamped"}
    assert {key: path.read_bytes() for key, path in registry.items() if key != "root"} == before



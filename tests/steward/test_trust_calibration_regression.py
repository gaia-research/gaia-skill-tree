"""Regression tests for TrustCalibrationDriftSensor (#2114, #1642).

#2114: the sensor scored named skills against an empty context map, so evidence
inherited from the generic parent was dropped and a correctly-rated skill was
reported as a false demotion (``hikari9/auto-office``: stored 3★, own-only
TM 21.68 / grade C vs the inspector's 88.97 / grade B).
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

import gaia_cli.steward.sensors as sensors_module
from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH
from gaia_cli.steward.primitives.files import SensorUnavailable
from gaia_cli.steward.sensors import TrustCalibrationDriftSensor
from gaia_cli.trustMagnitude import computeOverallTrustGradeFromSkill, computeTrustMagnitude
from tests.steward.sensor_fixtures import make_repo, tree_digest

NOW = "2026-10-20T00:00:00Z"
START = datetime(2026, 10, 20, tzinfo=timezone.utc)

PARENT = {
    "id": "parent-platform",
    "name": "Parent Platform",
    "type": "fusion",
    "description": "Generic parent whose research evidence is inherited by named skills.",
    "evidence": [
        {
            "source": "https://arxiv.org/abs/2308.00352",
            "type": "arxiv",
            "citations": 156,
            "grade": "C",
            "date": "2026-10-08",
            "evaluator": "unknown",
        }
    ],
}


def _named(skill_id: str, *, level: str, stars: int = 100, **extra: object) -> str:
    skill = {
        "id": skill_id,
        "name": skill_id.split("/")[-1],
        "status": "named",
        "level": level,
        "genericSkillRef": "parent-platform",
        "evidence": [
            {
                "type": "github-stars-own",
                "source": f"https://github.com/{skill_id}",
                "stars": stars,
            }
        ],
        **extra,
    }
    return "---\n" + yaml.safe_dump(skill, sort_keys=False, allow_unicode=True) + "---\n"


def _fixture(tmp_path: Path, *, level: str = "3★", **extra: object) -> Path:
    return make_repo(
        tmp_path,
        {
            "registry/nodes/fusion/parent-platform.json": json.dumps(PARENT),
            "registry/named/owner/child.md": _named("owner/child", level=level, **extra),
        },
    )


def _skill(repo: Path) -> dict:
    text = (repo / "registry/named/owner/child.md").read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---", 2)[1])


def test_fixture_discriminates_own_only_from_effective_evidence(tmp_path: Path) -> None:
    """Guard the guard: the fixture must really differ between the two contexts."""

    repo = _fixture(tmp_path)
    skill = _skill(repo)
    context = {"parent-platform": PARENT}

    assert computeOverallTrustGradeFromSkill(skill, {}) == "C"  # old behaviour: 2★
    assert computeOverallTrustGradeFromSkill(skill, context) == "B"  # effective: 3★
    assert computeTrustMagnitude(skill, {}) < 50 <= computeTrustMagnitude(skill, context)


def test_inherited_evidence_keeps_stored_level_correct(tmp_path: Path) -> None:
    repo = _fixture(tmp_path, level="3★")

    assert TrustCalibrationDriftSensor().scan(repo, NOW) == []


def test_genuine_drift_is_still_reported_against_effective_evidence(tmp_path: Path) -> None:
    repo = _fixture(tmp_path, level="5★")

    (observation,) = TrustCalibrationDriftSensor().scan(repo, NOW)

    assert observation.kind == "trust_calibration_drift"
    assert observation.subject.id == "owner/child"
    assert observation.current_state == {"level": "5★"}
    assert observation.observed_state["trustGrade"] == "B"
    assert observation.observed_state["targetLevel"] == "3★"
    assert observation.observed_state["trustMagnitude"] == pytest.approx(56.84)
    assert observation.observed_state["calibrationCommand"] == "gaia dev calibrate owner/child 3★"


def test_freeze_exemption_is_preserved(tmp_path: Path) -> None:
    repo = _fixture(
        tmp_path,
        level="5★",
        timeline=[{"action": "upstream_deprecated", "timestamp": "2026-01-01T00:00:00Z"}],
    )

    assert TrustCalibrationDriftSensor().scan(repo, NOW) == []


def test_sensor_is_deterministic_and_read_only(tmp_path: Path) -> None:
    repo = _fixture(tmp_path, level="5★")
    before = tree_digest(repo)

    first = TrustCalibrationDriftSensor().scan(repo, NOW)
    second = TrustCalibrationDriftSensor().scan(repo, NOW)

    assert [item.to_dict() for item in first] == [item.to_dict() for item in second]
    assert tree_digest(repo) == before


def test_context_is_built_once_per_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = make_repo(
        tmp_path,
        {
            "registry/nodes/fusion/parent-platform.json": json.dumps(PARENT),
            "registry/named/owner/a.md": _named("owner/a", level="3★"),
            "registry/named/owner/b.md": _named("owner/b", level="3★"),
            "registry/named/owner/c.md": _named("owner/c", level="3★"),
        },
    )
    calls: list[Path] = []
    original = sensors_module.buildMergedSkillMap

    def counting(path: Path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(sensors_module, "buildMergedSkillMap", counting)

    assert TrustCalibrationDriftSensor().scan(repo, NOW) == []
    assert len(calls) == 1


def test_context_build_failure_is_sensor_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _fixture(tmp_path, level="5★")

    def broken(_path: Path):
        raise RuntimeError("registry maps exploded")

    monkeypatch.setattr(sensors_module, "buildMergedSkillMap", broken)

    with pytest.raises(SensorUnavailable, match="effective-evidence context"):
        TrustCalibrationDriftSensor().scan(repo, NOW)


def test_missing_generic_parent_is_unavailable_not_a_demotion(tmp_path: Path) -> None:
    """A dangling genericSkillRef would silently reintroduce the own-only score."""

    repo = make_repo(
        tmp_path,
        {"registry/named/owner/child.md": _named("owner/child", level="3★")},
    )

    with pytest.raises(SensorUnavailable, match="genericSkillRef"):
        TrustCalibrationDriftSensor().scan(repo, NOW)


@pytest.mark.parametrize(
    "broken",
    ["---\nid: [unterminated\n---\n", "---\n- just\n- a list\n---\n"],
    ids=["invalid-yaml", "non-mapping-frontmatter"],
)
def test_unreadable_named_record_is_unavailable_not_skipped(tmp_path: Path, broken: str) -> None:
    """A record the sensor cannot evaluate must not be silently skipped.

    Skipping would let an exhaustive sweep resolve that subject's open debt
    although this run never evaluated it.
    """

    repo = _fixture(tmp_path)
    (repo / "registry/named/owner/broken.md").write_text(broken, encoding="utf-8")

    with pytest.raises(SensorUnavailable):
        TrustCalibrationDriftSensor().scan(repo, NOW)


def test_tree_without_named_registry_is_unavailable_not_empty(tmp_path: Path) -> None:
    # The sensor is exhaustive: an empty result would sweep every open trust
    # debt as resolved, so a missing registry must be reported as blindness.
    repo = make_repo(tmp_path, {"README.md": "no registry here\n"})

    with pytest.raises(SensorUnavailable, match="named-skill records are missing"):
        TrustCalibrationDriftSensor().scan(repo, NOW)


def test_trust_sensor_declares_exhaustive_resolution() -> None:
    assert TrustCalibrationDriftSensor.resolution_scope == "exhaustive"


# ------------------------------------------------------------- stale stamps (#1642)

EFFECTIVE_TM = 56.84  # own 35.0 + inherited 21.84, see the discriminating fixture


def test_stale_trust_stamp_is_reported_without_touching_calibration(tmp_path: Path) -> None:
    repo = _fixture(tmp_path, level="3★", trustMagnitude=50.0)

    (observation,) = TrustCalibrationDriftSensor().scan(repo, NOW)

    assert observation.kind == "trust_stamp_stale"
    assert observation.subject.type == "named-skill"
    assert observation.subject.id == "owner/child"
    assert observation.status == "drift"
    assert observation.confidence == 1.0
    assert observation.current_state == {"trustMagnitude": 50.0}
    assert observation.observed_state["trustMagnitude"] == pytest.approx(EFFECTIVE_TM)
    assert observation.observed_state["delta"] == pytest.approx(EFFECTIVE_TM - 50.0, abs=0.01)
    assert observation.observed_state["tolerance"] == TrustCalibrationDriftSensor._STAMP_TOLERANCE


def test_freshly_rounded_stamp_is_not_stale(tmp_path: Path) -> None:
    repo = _fixture(tmp_path, level="3★", trustMagnitude=round(EFFECTIVE_TM, 2))

    assert TrustCalibrationDriftSensor().scan(repo, NOW) == []


@pytest.mark.parametrize(
    ("offset", "reported"),
    [(0.0, False), (0.005, False), (0.015, False), (0.03, True), (-0.03, True)],
)
def test_stamp_tolerance_separates_rounding_from_movement(
    tmp_path: Path, offset: float, reported: bool
) -> None:
    computed = computeTrustMagnitude(_skill(_fixture(tmp_path / "probe")), {"parent-platform": PARENT})
    repo = _fixture(tmp_path / "subject", level="3★", trustMagnitude=round(computed + offset, 4))

    kinds = [item.kind for item in TrustCalibrationDriftSensor().scan(repo, NOW)]

    assert kinds == (["trust_stamp_stale"] if reported else [])


@pytest.mark.parametrize("stamp", [None, "56.84", True, [56.84]])
def test_absent_or_non_numeric_stamp_is_not_a_stale_finding(tmp_path: Path, stamp: object) -> None:
    extra = {} if stamp is None else {"trustMagnitude": stamp}
    repo = _fixture(tmp_path, level="3★", **extra)

    assert TrustCalibrationDriftSensor().scan(repo, NOW) == []


def test_stamp_finding_does_not_alter_calibration_findings(tmp_path: Path) -> None:
    plain = TrustCalibrationDriftSensor().scan(_fixture(tmp_path / "plain", level="5★"), NOW)
    stamped = TrustCalibrationDriftSensor().scan(
        _fixture(tmp_path / "stamped", level="5★", trustMagnitude=10.0), NOW
    )

    assert [item.kind for item in plain] == ["trust_calibration_drift"]
    assert sorted(item.kind for item in stamped) == ["trust_calibration_drift", "trust_stamp_stale"]
    calibration = next(item for item in stamped if item.kind == "trust_calibration_drift")
    assert calibration.to_dict() == plain[0].to_dict()


def test_frozen_skill_keeps_its_rank_but_its_stale_stamp_is_still_measured(tmp_path: Path) -> None:
    repo = _fixture(
        tmp_path,
        level="5★",
        trustMagnitude=10.0,
        timeline=[{"action": "upstream_deprecated", "timestamp": "2026-01-01T00:00:00Z"}],
    )

    assert [item.kind for item in TrustCalibrationDriftSensor().scan(repo, NOW)] == ["trust_stamp_stale"]


def test_stamp_findings_resolve_through_the_controller_when_restamped(tmp_path: Path) -> None:
    repo = _fixture(tmp_path, level="3★", trustMagnitude=10.0)
    policy = repo / POLICY_RELATIVE_PATH
    policy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__).resolve().parents[2] / POLICY_RELATIVE_PATH, policy)
    ticks = iter(START + timedelta(minutes=n) for n in range(100))
    controller = StewardController(sensors=[TrustCalibrationDriftSensor()], clock=lambda: next(ticks))

    first = controller.scan(repo)
    assert [debt.kind for debt in first.open_debts] == ["trust_stamp_stale"]
    assert first.open_debts[0].authority.value == "C"

    named = repo / "registry/named/owner/child.md"
    named.write_text(_named("owner/child", level="3★", trustMagnitude=round(EFFECTIVE_TM, 2)), encoding="utf-8")
    second = controller.scan(repo)

    assert second.open_debts == ()
    assert second.receipt.debt_resolved == (first.open_debts[0].id,)

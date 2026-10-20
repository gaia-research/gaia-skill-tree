"""Regression tests for TrustCalibrationDriftSensor (#2114, #1642).

#2114: the sensor scored named skills against an empty context map, so evidence
inherited from the generic parent was dropped and a correctly-rated skill was
reported as a false demotion (``hikari9/auto-office``: stored 3★, own-only
TM 21.68 / grade C vs the inspector's 88.97 / grade B).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import gaia_cli.steward.sensors as sensors_module
from gaia_cli.steward.primitives.files import SensorUnavailable
from gaia_cli.steward.sensors import TrustCalibrationDriftSensor
from gaia_cli.trustMagnitude import computeOverallTrustGradeFromSkill, computeTrustMagnitude
from tests.steward.sensor_fixtures import make_repo, tree_digest

NOW = "2026-10-20T00:00:00Z"

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


def test_tree_without_named_registry_has_no_subjects(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {"README.md": "no registry here\n"})

    assert TrustCalibrationDriftSensor().scan(repo, NOW) == []


def test_trust_sensor_declares_exhaustive_resolution() -> None:
    assert TrustCalibrationDriftSensor.resolution_scope == "exhaustive"

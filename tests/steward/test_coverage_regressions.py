from __future__ import annotations

import importlib.util
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.models import Observation, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH, PolicyError, StewardPolicy
from gaia_cli.steward.routing import RoutingError, render_dispatch, render_founder_queue
from gaia_cli.steward.sensors import TrustCalibrationDriftSensor
from gaia_cli.trustMagnitude import (
    computeOverallTrustGradeFromSkill,
    computeTrustMagnitudeInputHash,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN = datetime(2026, 10, 15, tzinfo=timezone.utc)


def _repo(tmp_path: Path) -> Path:
    policy = tmp_path / POLICY_RELATIVE_PATH
    policy.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, policy)
    return tmp_path


def _build_docs_module():
    script = REPO_ROOT / "scripts" / "build_docs.py"
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    sys.path.insert(0, str(REPO_ROOT / "src"))
    spec = importlib.util.spec_from_file_location("coverage_regression_build_docs", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_issue_2042_check_globs_new_english_pages_and_preserves_clean_and_stale_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The English-page glob covers new pages; check mode reports but never writes."""
    build_docs = _build_docs_module()
    en_dir = tmp_path / "docs" / "en"
    en_dir.mkdir(parents=True)
    monkeypatch.setattr(build_docs, "ROOT", tmp_path)
    monkeypatch.setattr(build_docs, "_read_version", lambda: "9.9.9")

    clean_bytes = (
        '<link rel="stylesheet" href="../css/styles.css?v=9.9.9">\n'
        '<span class="nav-version">v9.9.9</span>\n'
        '<script src="../js/site-nav.js?v=9.9.9"></script>\n'
        'window.GAIA_VERSION = "9.9.9";\n'
    ).encode()
    clean_page = en_dir / "existing.html"
    clean_page.write_bytes(clean_bytes)
    assert build_docs.build_html_cache_busting(check=True) is False
    assert clean_page.read_bytes() == clean_bytes

    stale_bytes = (
        '<link rel="stylesheet" href="../css/styles.css?v=8.8.8">\n'
        '<span class="nav-version">v8.8.8</span>\n'
        '<script src="../js/site-nav.js?v=8.8.8"></script>\n'
        'window.GAIA_VERSION = "8.8.8";\n'
    ).encode()
    new_page = en_dir / "new-unregistered-page.html"
    new_page.write_bytes(stale_bytes)

    assert build_docs.build_html_cache_busting(check=True) is True
    assert "diff docs/en/new-unregistered-page.html" in capsys.readouterr().out
    assert new_page.read_bytes() == stale_bytes
    assert clean_page.read_bytes() == clean_bytes


def test_issue_1642_rank_sensor_does_not_prove_cached_tm_input_freshness(tmp_path: Path) -> None:
    """A matching rank/grade can hide changed evidence when the cache hash is stale.

    This is a documented coverage limit of TrustCalibrationDriftSensor, not
    evidence that all trust-calibration coverage is healthy or cache-aware.
    """
    named = tmp_path / "registry" / "named" / "fixture"
    named.mkdir(parents=True)
    path = named / "skill.md"
    skill = {
        "id": "fixture/skill",
        "level": "2★",
        "evidence": [
            {
                "type": "github-stars-own",
                "grade": "B",
                "source": "https://github.com/example/project/stargazers",
                "stars": 100,
            }
        ],
    }
    skill["trustMagnitudeInputHash"] = computeTrustMagnitudeInputHash(skill)
    original_hash = skill["trustMagnitudeInputHash"]
    original_grade = computeOverallTrustGradeFromSkill(skill, {})
    # A small but real TM input change leaves the skill in the same grade/rank.
    skill["evidence"][0]["stars"] = 101
    changed_hash = computeTrustMagnitudeInputHash(skill)
    changed_grade = computeOverallTrustGradeFromSkill(skill, {})
    assert changed_hash != original_hash
    assert skill["trustMagnitudeInputHash"] == original_hash  # deliberately stale
    assert changed_grade == original_grade
    assert skill["level"] == "2★"
    skill["overallTrustGrade"] = original_grade
    path.write_text("---\n" + yaml.safe_dump(skill, sort_keys=False) + "---\n", encoding="utf-8")

    observations = TrustCalibrationDriftSensor().scan(tmp_path, "2026-10-15T00:00:00Z")

    # The sensor compares current level to computed target grade; it does not
    # compare trustMagnitudeInputHash, so this fixture cannot establish cache freshness.
    assert observations == []


class _FailingAfterDriftSensor:
    id = "fixture-routing-sensor"

    def __init__(self) -> None:
        self.fail = False

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        if self.fail:
            raise OSError("fixture coverage unavailable")
        return [
            Observation(
                kind="registry_integrity_failed",
                subject=Subject(type="repository-surface", id="fixture"),
                observed_at=observed_at,
                source=self.id,
                status="drift",
                current_state={"valid": True},
                observed_state={"violations": [{"path": "registry/nodes/fixture.json"}]},
            )
        ]


def test_unknown_sensor_coverage_preserves_prior_debt_and_blocks_routing(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = _FailingAfterDriftSensor()
    controller = StewardController(sensors=[sensor], clock=lambda: FROZEN)
    first = controller.scan(root)
    prior_debt = next(item for item in first.open_debts if item.kind == "registry_integrity_failed")
    ledger_path = first.debt_state_path
    sensor.fail = True

    failed = controller.scan(root)

    assert failed.receipt.result_status == "blocked"
    assert failed.receipt.coverage_unknown == (sensor.id,)
    assert prior_debt.id in {item.id for item in failed.open_debts}
    assert any(item.kind == "sensor_coverage_unknown" for item in failed.open_debts)
    policy = StewardPolicy.load(root)
    assert policy.dispatch_rule_for("sensor_coverage_unknown") is None
    with pytest.raises(RoutingError, match="sensor coverage is unknown"):
        render_dispatch(root, prior_debt.id, controller=controller)
    with pytest.raises(RoutingError, match="sensor coverage is unknown"):
        render_founder_queue(root, controller=controller)
    assert ledger_path.exists()


@pytest.mark.parametrize(
    "forbidden_scope",
    ["founder/**", ".gaia/**", ".github/**", "registry/schema/**", ".agents/**"],
)
def test_policy_rejects_dispatch_writable_paths_in_protected_surfaces(
    tmp_path: Path, forbidden_scope: str
) -> None:
    data = yaml.safe_load((REPO_ROOT / POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    first_rule = next(iter(data["routing"]["dispatchRules"].values()))
    first_rule["allowedPaths"] = [forbidden_scope]
    policy_path = tmp_path / POLICY_RELATIVE_PATH
    policy_path.parent.mkdir(parents=True)
    policy_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    with pytest.raises(PolicyError, match="may not reach the protected path"):
        StewardPolicy.load(tmp_path)

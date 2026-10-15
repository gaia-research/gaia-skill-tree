from __future__ import annotations

import json
from pathlib import Path

from scripts.check_steward_coverage import ROOT, validate


CATALOG = ROOT / "founder/steward/routine-coverage.json"


def _catalog(tmp_path: Path) -> tuple[Path, dict]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    path = tmp_path / "routine-coverage.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, data


def test_catalog_is_static_and_reports_registration_dependency_pending() -> None:
    result = validate(ROOT, CATALOG)

    assert result["capabilityOnly"] is True
    assert result["liveHealth"] == "not-evaluated"
    assert result["routineCount"] == 17
    assert result["registeredSensorCount"] == 13
    assert result["dispatchRuleCount"] == 5
    assert result["repairExecutorCount"] == 2
    assert result["dependencyPending"] is True
    assert any("expected 14 sensors including repository-hygiene" in error for error in result["errors"])
    assert any("not registered" in error and "repository-hygiene" in error for error in result["errors"])
    assert result["statusCounts"]["partial"] > 0
    assert "present" not in result["statusCounts"]


def test_catalog_rejects_unknown_sensor_and_fabricated_live_routes(tmp_path: Path) -> None:
    path, data = _catalog(tmp_path)
    binding = data["routines"][5]["bindings"][0]
    binding["sensorId"] = "invented-sensor"
    binding["dispatchRule"] = "invented-dispatch"
    binding["repairExecutor"] = "invented-executor"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = validate(ROOT, path)

    assert any("unknown sensor claim 'invented-sensor'" in error for error in result["errors"])
    assert any("fabricated dispatch rule 'invented-dispatch'" in error for error in result["errors"])
    assert any("fabricated repair executor 'invented-executor'" in error for error in result["errors"])


def test_catalog_rejects_wrong_sensor_kind_authority_and_titles(tmp_path: Path) -> None:
    path, data = _catalog(tmp_path)
    data["routines"][5]["title"] = "CLI is healthy"
    data["routines"][5]["bindings"][0]["debtKind"] = "knowledge_contradiction"
    data["routines"][5]["bindings"][0]["authority"] = "A"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = validate(ROOT, path)

    assert any("expected exact number/title" in error for error in result["errors"])
    assert any("does not own emitted debt kind" in error for error in result["errors"])
    assert any("authority mismatch" in error for error in result["errors"])


def test_catalog_rejects_unaccounted_registered_sensor_and_missing_test_path(tmp_path: Path) -> None:
    path, data = _catalog(tmp_path)
    data["routines"][5]["bindings"] = []
    data["routines"][5]["tests"] = ["tests/steward/not-a-test.py"]
    path.write_text(json.dumps(data), encoding="utf-8")

    result = validate(ROOT, path)

    assert any("registered sensors not accounted for: cli-contract" in error for error in result["errors"])
    assert any("existing repository test paths" in error for error in result["errors"])

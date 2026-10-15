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


def test_catalog_is_static_and_has_expected_routine_distribution() -> None:
    result = validate(ROOT, CATALOG)

    assert result["capabilityOnly"] is True
    assert result["liveHealth"] == "not-evaluated"
    assert result["routineCount"] == 17
    assert result["statusCounts"]["absent"] == 6
    assert result["statusCounts"]["partial"] == 11
    assert result["statusCounts"]["human-gated"] == 0
    assert "present" not in result["statusCounts"]


def test_catalog_uses_authoritative_routine_headings_from_root_copy(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "founder").mkdir(parents=True)
    source = (ROOT / "founder/ROUTINES.md").read_text(encoding="utf-8")
    (root / "founder/ROUTINES.md").write_text(source.replace("Dead-Code Gardener", "Renamed authoritative routine", 1), encoding="utf-8")
    catalog, data = _catalog(tmp_path)

    result = validate(root, catalog)

    assert any("expected authoritative title 'Renamed authoritative routine'" in error for error in result["errors"])


def test_catalog_rejects_unknown_sensor_and_fabricated_live_routes(tmp_path: Path) -> None:
    path, data = _catalog(tmp_path)
    binding = data["routines"][5]["bindings"][0]
    binding["sensorId"] = "invented-sensor"
    binding["dispatchRule"] = "invented-dispatch"
    binding["bindingStatus"] = "route-bound"
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

    assert any("expected authoritative title" in error for error in result["errors"])


def test_catalog_rejects_routes_bound_to_the_wrong_policy_debt(tmp_path: Path) -> None:
    path, data = _catalog(tmp_path)
    binding = data["routines"][5]["bindings"][0]
    binding["debtKind"] = "registry_integrity_failed"
    binding["authority"] = "B"
    binding["dispatchRule"] = "trust-calibration-drift"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = validate(ROOT, path)

    assert any("does not own emitted debt kind" in error for error in result["errors"])
    assert any("does not authorize 'registry_integrity_failed'" in error for error in result["errors"])


def test_catalog_rejects_empty_gaps_and_test_path_escape(tmp_path: Path) -> None:
    path, data = _catalog(tmp_path)
    row = data["routines"][5]
    row["remainingGaps"] = []
    row["tests"] = ["tests/../../outside.py"]
    path.write_text(json.dumps(data), encoding="utf-8")

    result = validate(ROOT, path)

    assert any("remainingGaps must be a non-empty" in error for error in result["errors"])
    assert any("within tests/**" in error for error in result["errors"])


def test_catalog_rejects_missing_live_binding_and_invalid_founder_route(tmp_path: Path) -> None:
    path, data = _catalog(tmp_path)
    binding = data["routines"][10]["bindings"][0]
    binding["founderRule"] = "invented-rule"
    binding["bindingStatus"] = "founder-routed"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = validate(ROOT, path)

    assert any("founder rule must be live generic-mapping-decision" in error for error in result["errors"])


def test_catalog_rejects_fabricated_hook_health(tmp_path: Path) -> None:
    path, data = _catalog(tmp_path)
    data["hooks"][0]["status"] = "verified"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = validate(ROOT, path)

    assert any("absent evidence cannot claim healthy or verified" in error for error in result["errors"])


def test_catalog_rejects_unaccounted_registered_sensor_and_missing_test_path(tmp_path: Path) -> None:
    path, data = _catalog(tmp_path)
    data["routines"][5]["bindings"] = []
    data["routines"][5]["tests"] = ["tests/steward/not-a-test.py"]
    path.write_text(json.dumps(data), encoding="utf-8")

    result = validate(ROOT, path)

    assert any("registered sensors not accounted for" in error for error in result["errors"])
    assert any("existing paths within tests/**" in error for error in result["errors"])

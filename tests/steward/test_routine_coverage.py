from __future__ import annotations

import json
from pathlib import Path

import pytest

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

    assert any("does not authorize 'generic_mapping' at 'C'" in error for error in result["errors"])


@pytest.mark.parametrize(
    ("row_index", "binding_index", "field", "value", "missing"),
    [
        (5, 0, "dispatchRule", None, "missing live dispatch route"),
        (16, 1, "repairExecutor", None, "missing live repair executor"),
        (10, 0, "founderRule", None, "missing live founder rule"),
    ],
)
def test_catalog_requires_each_live_debt_binding(
    tmp_path: Path, row_index: int, binding_index: int, field: str, value, missing: str,
) -> None:
    path, data = _catalog(tmp_path)
    binding = data["routines"][row_index]["bindings"][binding_index]
    binding[field] = value
    binding["bindingStatus"] = (
        "route-bound" if binding["dispatchRule"] is not None else
        "executor-bound" if binding["repairExecutor"] is not None else
        "founder-routed" if binding["founderRule"] is not None else "unrouted"
    )
    path.write_text(json.dumps(data), encoding="utf-8")

    result = validate(ROOT, path)

    assert any(missing in error for error in result["errors"])


@pytest.mark.parametrize("malformation", ["non-dict", "owner", "path-and-function"])
def test_catalog_rejects_malformed_hooks_without_traceback(tmp_path: Path, malformation: str) -> None:
    path, data = _catalog(tmp_path)
    if malformation == "non-dict":
        data["hooks"][0] = None
    elif malformation == "owner":
        data["hooks"][0]["owner"] = []
    else:
        data["hooks"][0]["producerPaths"] = [None]
        data["hooks"][0]["producerFunctions"] = [42]
    path.write_text(json.dumps(data), encoding="utf-8")

    result = validate(ROOT, path)

    assert result["errors"]


def test_catalog_rejects_unhashable_founder_rule_without_traceback(tmp_path: Path) -> None:
    path, data = _catalog(tmp_path)
    data["routines"][10]["bindings"][0]["founderRule"] = []
    data["routines"][10]["bindings"][0]["bindingStatus"] = "founder-routed"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = validate(ROOT, path)

    assert any("founderRule must be a string or null" in error for error in result["errors"])


def test_catalog_rejects_nonsequential_authoritative_heading_numbers(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "founder").mkdir(parents=True)
    source = (ROOT / "founder/ROUTINES.md").read_text(encoding="utf-8")
    (root / "founder/ROUTINES.md").write_text(source.replace("## 12. Artifact", "## 13. Artifact", 1), encoding="utf-8")
    catalog, data = _catalog(tmp_path)
    data["routines"][11]["number"] = 99
    catalog.write_text(json.dumps(data), encoding="utf-8")

    result = validate(root, catalog)

    assert any("heading numbers must be exactly 1..17" in error for error in result["errors"])


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

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_steward_coverage import ROOT, live_states, validate


CATALOG = ROOT / "founder/steward/routine-coverage.json"


def _binding(data: dict, routine: int, sensor_id: str | None, kind: str | None = None) -> dict:
    for binding in data["routines"][routine - 1]["bindings"]:
        if binding["sensorId"] == sensor_id and (kind is None or binding["debtKind"] == kind):
            return binding
    raise AssertionError(f"routine {routine} has no binding for {sensor_id}:{kind}")


def _detector(data: dict, sensor_id: str) -> dict:
    return next(item for item in data["detectors"] if item["id"] == sensor_id)


def _errors(tmp_path: Path, data: dict) -> list[str]:
    path = tmp_path / "routine-coverage.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return validate(ROOT, path)["errors"]


def _catalog(tmp_path: Path) -> tuple[Path, dict]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    path = tmp_path / "routine-coverage.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, data


def test_catalog_is_static_and_has_expected_routine_distribution() -> None:
    result = validate(ROOT, CATALOG)

    assert result["ok"], result["errors"]
    assert result["capabilityOnly"] is True
    assert result["liveHealth"] == "not-evaluated"
    assert result["routineCount"] == 17
    # Every routine has at least one registered detector, and a static catalog
    # never claims full coverage.
    assert result["statusCounts"] == {"absent": 0, "partially-covered": 17}
    assert result["registeredSensorCount"] == result["accountedSensorCount"] == 30
    assert result["unaccountedSensors"] == []


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
    binding = _binding(data, 6, "cli-contract")
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
    _binding(data, 6, "cli-contract")["debtKind"] = "knowledge_contradiction"
    _binding(data, 6, "cli-contract")["authority"] = "A"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = validate(ROOT, path)

    assert any("expected authoritative title" in error for error in result["errors"])


def test_catalog_rejects_routes_bound_to_the_wrong_policy_debt(tmp_path: Path) -> None:
    path, data = _catalog(tmp_path)
    binding = _binding(data, 6, "cli-contract")
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
    binding = _binding(data, 11, "discovery-generic-mapping")
    binding["founderRule"] = "invented-rule"
    binding["bindingStatus"] = "founder-routed"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = validate(ROOT, path)

    assert any("does not authorize 'generic_mapping' at 'C'" in error for error in result["errors"])


@pytest.mark.parametrize(
    ("routine", "sensor_id", "field", "value", "missing"),
    [
        (6, "cli-contract", "dispatchRule", None, "missing live dispatch route"),
        (17, "agent-skill-mirror", "repairExecutor", None, "missing live repair executor"),
        (11, "discovery-generic-mapping", "founderRule", None, "missing live founder rule"),
    ],
)
def test_catalog_requires_each_live_debt_binding(
    tmp_path: Path, routine: int, sensor_id: str, field: str, value, missing: str,
) -> None:
    path, data = _catalog(tmp_path)
    binding = _binding(data, routine, sensor_id)
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
    _binding(data, 11, "discovery-generic-mapping")["founderRule"] = []
    _binding(data, 11, "discovery-generic-mapping")["bindingStatus"] = "founder-routed"
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

    assert any("registered sensors not accounted for: cli-contract" in error for error in result["errors"])
    assert any("bindings must cover each detector debt kind exactly" in error for error in result["errors"])
    assert any("existing paths within tests/**" in error for error in result["errors"])


# ------------------------------------------------------------ v2 omissions


def test_catalog_rejects_a_registered_sensor_without_a_detector_contract(tmp_path: Path) -> None:
    _, data = _catalog(tmp_path)
    data["detectors"] = [item for item in data["detectors"] if item["id"] != "dead-code"]

    errors = _errors(tmp_path, data)

    assert any("registered sensors without a detector contract: dead-code" in error for error in errors)


def test_catalog_rejects_a_contract_for_an_unregistered_detector(tmp_path: Path) -> None:
    _, data = _catalog(tmp_path)
    invented = dict(_detector(data, "dead-code"), id="invented-detector")
    data["detectors"].append(invented)

    errors = _errors(tmp_path, data)

    assert any("'invented-detector' is not a registered sensor" in error for error in errors)


def test_catalog_rejects_a_routine_that_drops_its_detector(tmp_path: Path) -> None:
    _, data = _catalog(tmp_path)
    row = data["routines"][0]
    row["detectorIds"] = []
    row["bindings"] = []
    row["status"] = "absent"

    errors = _errors(tmp_path, data)

    assert any("routine 1: detectorIds must be exactly" in error for error in errors)
    assert any("routine 1: status must be 'partially-covered'" in error for error in errors)


def test_catalog_rejects_a_missing_debt_kind_binding(tmp_path: Path) -> None:
    _, data = _catalog(tmp_path)
    row = data["routines"][0]
    row["bindings"] = [b for b in row["bindings"] if b["debtKind"] != "orphan_module"]

    errors = _errors(tmp_path, data)

    assert any("missing ['dead-code:orphan_module']" in error for error in errors)


@pytest.mark.parametrize("status", ["covered", "present", "healthy"])
def test_catalog_never_claims_full_coverage(tmp_path: Path, status: str) -> None:
    _, data = _catalog(tmp_path)
    data["routines"][0]["status"] = status

    errors = _errors(tmp_path, data)

    assert any("a static catalog never claims full coverage" in error for error in errors)


def test_catalog_cannot_claim_live_observation(tmp_path: Path) -> None:
    _, data = _catalog(tmp_path)
    _detector(data, "dead-code")["coverageStatus"]["live"] = "actively-observed"

    errors = _errors(tmp_path, data)

    assert any("cannot claim live coverage" in error for error in errors)


@pytest.mark.parametrize(
    ("sensor_id", "mutation", "message"),
    [
        ("dead-code", lambda d: d.update(routineIds=[2]), "routineIds"),
        ("dead-code", lambda d: d.update(debtKinds=["unused_import"]), "debtKinds must equal"),
        ("secret-scan", lambda d: d["coverageStatus"].update(static=["registered", "executable"]), "static coverage must be"),
        ("agent-skill-mirror", lambda d: d["coverageStatus"].update(static=["registered", "executable"]), "static coverage must be"),
        ("dead-code", lambda d: d.update(authority={"unused_import": "A", "orphan_module": "B"}), "authority must match"),
        ("ci-health", lambda d: d["inputs"][0].update(required=True), "cannot be required"),
        ("ci-health", lambda d: d.update(freshness="checkout-head"), "freshness must be"),
        ("ci-health", lambda d: d["failureBehavior"].update(notEvaluated=None), "failureBehavior must be"),
        ("dead-code", lambda d: d["inputs"].append({"path": "no/such/dir", "required": True}), "is not tracked by Git"),
        ("dead-code", lambda d: d.update(owningSkill="gaia-steward-imaginary"), "owningSkill"),
        ("secret-scan", lambda d: d["dispositionSkills"].update(credential_leak="gaia-steward-lane"), "dispositionSkills"),
        ("dead-code", lambda d: d.update(proof=["tests/steward/test_digest.py"]), "references the sensor"),
        ("dead-code", lambda d: d.update(resolutionScope="observed-only"), "resolutionScope"),
        ("dead-code", lambda d: d.pop("dedupeKey"), "fields must be exactly"),
    ],
)
def test_catalog_rejects_inaccurate_detector_contracts(tmp_path: Path, sensor_id: str, mutation, message: str) -> None:
    _, data = _catalog(tmp_path)
    mutation(_detector(data, sensor_id))

    errors = _errors(tmp_path, data)

    assert any(message in error for error in errors), errors


def test_catalog_requires_the_full_state_vocabulary(tmp_path: Path) -> None:
    _, data = _catalog(tmp_path)
    del data["stateVocabulary"]["unknown-unavailable"]

    errors = _errors(tmp_path, data)

    assert any("stateVocabulary must define exactly" in error for error in errors)


def test_live_states_never_count_an_unexecuted_probe_as_healthy() -> None:
    receipt = {
        "coverageKnown": ["dead-code", "ci-health"],
        "coverageUnknown": ["secret-scan"],
        "notEvaluated": [{"sensor": "ci-health", "reason": "no ci-runs.json supplied"}],
    }

    states = live_states(ROOT, receipt)

    assert "actively-observed" in states["dead-code"]
    # Unknown, not evaluated, and simply absent from the receipt are all blind.
    assert "unknown-unavailable" in states["secret-scan"]
    assert "unknown-unavailable" in states["ci-health"]
    assert "unknown-unavailable" in states["agent-skill-mirror"]
    assert all(
        ("actively-observed" in value) != ("unknown-unavailable" in value) for value in states.values()
    )
    assert "human-gated" in states["secret-scan"]
    assert "eligible-auto-remediation" in states["agent-skill-mirror"]

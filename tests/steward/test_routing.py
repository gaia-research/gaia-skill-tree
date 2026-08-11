from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil

import pytest

import gaia_cli.steward.routing as routing_module
from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.models import Observation, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH
from gaia_cli.steward.receipts import StateError
from gaia_cli.steward.routing import RoutingError, render_dispatch, render_founder_queue


REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN = datetime(2026, 8, 9, tzinfo=timezone.utc)


def _repo(tmp_path: Path) -> Path:
    policy = tmp_path / POLICY_RELATIVE_PATH
    policy.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, policy)
    return tmp_path


class RoutingSensor:
    id = "routing-fixture"

    def __init__(self, *, include_b: bool = True, include_c: int = 2, target: str = "Generic Mapping/X") -> None:
        self.include_b = include_b
        self.include_c = include_c
        self.target = target

    def scan(self, root: Path, observed_at: str) -> list[Observation]:
        result: list[Observation] = []
        if self.include_b:
            result.append(Observation(
                kind="registry_integrity_failed", subject=Subject("surface", "registry-nodes"),
                observed_at=observed_at, source=self.id, status="drift",
                current_state={"valid": True}, observed_state={"violations": [{"path": "registry/nodes/a.json"}]},
            ))
        for number in range(self.include_c):
            result.append(Observation(
                kind="generic_mapping", subject=Subject("named-skill", f"candidate-{number}"),
                observed_at=observed_at, source=self.id, status="drift",
                current_state={"mapped": False},
                observed_state={"decisionTarget": self.target, "candidate": number},
            ))
        return result


def _controller(sensor: RoutingSensor) -> StewardController:
    return StewardController(sensors=[sensor], clock=lambda: FROZEN)


def test_dispatch_is_fresh_report_only_and_keeps_semantic_identity_on_evidence_refresh(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    first = render_dispatch(root, debt_id, controller=controller)
    sensor.target = "unused"  # same B debt, but refresh unrelated sensor content
    second = render_dispatch(root, debt_id, controller=controller)

    assert first.artifact.dispatch_id == second.artifact.dispatch_id
    assert first.artifact.packet_hash == second.artifact.packet_hash
    assert first.artifact.budget.to_dict() == {"modelCalls": 0, "maxTokens": 0, "maxMinutes": 0}
    assert first.receipt_path == second.receipt_path
    assert len(list(first.receipt_path.parent.glob("*.json"))) == 2  # scan + routing receipt
    assert not (root / "registry").exists()


def test_founder_groups_only_exact_normalized_target_and_identity_survives_growth(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = RoutingSensor(include_b=False, include_c=2, target=" Generic Mapping/X ")
    controller = _controller(sensor)

    first = render_founder_queue(root, controller=controller)
    assert len(first.artifact.decisions) == 1
    decision = first.artifact.decisions[0]
    assert decision.decision_target == "generic-mapping/x"
    assert len(decision.debt_ids) == 2

    sensor.include_c = 3
    grown = render_founder_queue(root, controller=controller)
    assert len(grown.artifact.decisions) == 1
    assert grown.artifact.decisions[0].decision_id == decision.decision_id
    assert len(grown.artifact.decisions[0].debt_ids) == 3
    assert grown.artifact.queue_id == first.artifact.queue_id
    assert grown.artifact.queue_hash != first.artifact.queue_hash


def test_founder_rejects_invalid_target_and_dispatch_rejects_unsupported_or_stale_debt(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    invalid = RoutingSensor(include_b=False, include_c=1, target="prose target?")
    with pytest.raises(RoutingError, match="invalid decisionTarget"):
        render_founder_queue(root, controller=_controller(invalid))

    stale_sensor = RoutingSensor(include_b=False, include_c=0)
    controller = _controller(stale_sensor)
    initial = controller.scan(root)
    # Preserve a previously observed B debt in local state but do not observe it
    # in this fresh scan; routing must not resurrect it.
    debt_path = initial.debt_state_path
    debt_path.write_text(debt_path.read_text(encoding="utf-8").replace('"debts": []', '''"debts": [{
      "schemaVersion": "steward-debt-v1", "id": "debt:cli_contract_drift:x:stale", "kind": "cli_contract_drift",
      "subject": {"type": "surface", "id": "x"}, "source": "old", "currentState": {}, "observedState": {}, "confidence": 1.0,
      "priority": {"importance": 0.7, "decisionImpact": 0.6, "exposure": 0.8, "freshnessNeed": 0.8, "expectedCost": 0.4, "score": 0.672},
      "authority": {"class": "B"}, "status": "open", "firstObservedAt": "2020-01-01T00:00:00Z", "lastObservedAt": "2020-01-01T00:00:00Z", "observationCount": 1
    }]'''), encoding="utf-8")
    with pytest.raises(RoutingError, match="stale"):
        render_dispatch(root, "debt:cli_contract_drift:x:stale", controller=controller)


def test_unknown_coverage_and_routing_receipt_failure_fail_closed_without_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    debt_id = controller.scan(root).open_debts[0].id
    before = set((root / ".gaia/steward/receipts").glob("*.json"))

    def fail_receipt(*args, **kwargs):
        raise StateError("routing receipt unavailable")

    monkeypatch.setattr(routing_module, "write_immutable_receipt", fail_receipt)
    with pytest.raises(StateError, match="routing receipt unavailable"):
        render_dispatch(root, debt_id, controller=controller)
    assert set((root / ".gaia/steward/receipts").glob("*.json")) == before

    class FailingSensor(RoutingSensor):
        def scan(self, root: Path, observed_at: str) -> list[Observation]:
            raise OSError("coverage unavailable")

    with pytest.raises(RoutingError, match="coverage is unknown"):
        render_founder_queue(root, controller=_controller(FailingSensor()))

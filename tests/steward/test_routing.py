from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess

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
    assert len(list(first.receipt_path.parent.glob("*.json"))) == 3  # initial scan, fresh routing scan, routing receipt
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


def test_founder_rejects_invalid_target_and_dispatch_rejects_stale_same_second_debt(tmp_path: Path) -> None:
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
      "authority": {"class": "B"}, "status": "open", "firstObservedAt": "2026-08-09T00:00:00Z", "lastObservedAt": "2026-08-09T00:00:00Z", "observationCount": 1
    }]'''), encoding="utf-8")
    with pytest.raises(RoutingError, match="stale"):
        render_dispatch(root, "debt:cli_contract_drift:x:stale", controller=controller)


def test_unknown_coverage_and_routing_receipt_failure_fail_closed_without_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    debt_id = controller.scan(root).open_debts[0].id
    ledger_before = (root / ".gaia/steward/debt.json").read_bytes()
    before = {path.name: path.read_bytes() for path in (root / ".gaia/steward/receipts").glob("*.json")}

    def fail_receipt(*args, **kwargs):
        raise StateError("routing receipt unavailable")

    monkeypatch.setattr(routing_module, "write_immutable_receipt", fail_receipt)
    with pytest.raises(StateError, match="routing receipt unavailable"):
        render_dispatch(root, debt_id, controller=controller)
    assert (root / ".gaia/steward/debt.json").read_bytes() == ledger_before
    assert {path.name: path.read_bytes() for path in (root / ".gaia/steward/receipts").glob("*.json")} == before

    class FailingSensor(RoutingSensor):
        def scan(self, root: Path, observed_at: str) -> list[Observation]:
            raise OSError("coverage unavailable")

    with pytest.raises(RoutingError, match="coverage is unknown"):
        render_founder_queue(root, controller=_controller(FailingSensor()))


def _git_repo(tmp_path: Path) -> Path:
    root = _repo(tmp_path)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)
    return root


def test_render_dispatch_scan_reuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    assert scan.head_commit is not None
    assert scan.to_dict()["headCommit"] == scan.head_commit
    debt_id = scan.open_debts[0].id

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 0
    assert result.scan is scan


def test_render_dispatch_scan_expiration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    clock_time = FROZEN + timedelta(seconds=10)
    monkeypatch.setattr(controller, "clock", lambda: clock_time)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan, max_age_seconds=5)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_head_move(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    initial_head = scan.head_commit
    debt_id = scan.open_debts[0].id

    subprocess.run(["git", "commit", "--allow-empty", "-qm", "second commit"], cwd=root, check=True)
    current_head = routing_module.git_head_commit(root)
    assert current_head != initial_head

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan
    assert result.scan.head_commit == current_head


def test_render_dispatch_unknown_coverage_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    from dataclasses import replace
    unknown_receipt = replace(scan.receipt, coverage_unknown=("broken-sensor",))
    scan_with_unknown = replace(scan, receipt=unknown_receipt)

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan_with_unknown)
    assert len(scan_called) == 1
    assert result.scan is not scan_with_unknown


def test_render_dispatch_null_head_in_git_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    from dataclasses import replace
    scan_null_head = replace(scan, head_commit=None)

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan_null_head)
    assert len(scan_called) == 1
    assert result.scan is not scan_null_head
    assert result.scan.head_commit is not None


def test_render_dispatch_dirty_tree_status_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    from dataclasses import replace
    scan_dirty = replace(scan, tree_clean=False)

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan_dirty)
    assert len(scan_called) == 1
    assert result.scan is not scan_dirty
    assert result.scan.tree_clean is True


def test_render_dispatch_non_git_repo_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    # In a non-git repo, scan reuse is refused and fresh scan runs
    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_symlinked_inputs_dir_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Create a symlink in state directory
    target = tmp_path / "external_inputs"
    target.mkdir()
    (target / "sample.json").write_text("{}", encoding="utf-8")
    (root / ".gaia/steward/inputs").symlink_to(target)

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_untracked_files_with_git_config_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    subprocess.run(["git", "config", "status.showUntrackedFiles", "no"], cwd=root, check=True)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Create an untracked file
    (root / "untracked_script.py").write_text("# new untracked file", encoding="utf-8")

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_ignored_surface_modification_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from gaia_cli.steward.controller import git_tree_is_clean

    root = _git_repo(tmp_path)
    # Put generated-output/ into .gitignore and commit it so git status considers it ignored
    (root / ".gitignore").write_text("generated-output/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "add gitignore"], cwd=root, check=True)

    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Create artifact in ignored surface generated-output/
    out_dir = root / "generated-output"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "artifact.json").write_text("{}", encoding="utf-8")

    # Tree is still clean according to git status because generated-output/ is ignored
    assert git_tree_is_clean(root) is True

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    # But local_inputs_fingerprint catches the ignored surface change and forces rescan
    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_upstream_watcher_manifest_change_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Add watcher manifest in .gaia/upstream-watcher/
    watcher_dir = root / ".gaia/upstream-watcher"
    watcher_dir.mkdir(parents=True, exist_ok=True)
    (watcher_dir / "manifest.json").write_text('{"target": "upstream"}', encoding="utf-8")

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_ignored_script_change_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from gaia_cli.steward.controller import git_tree_is_clean

    root = _git_repo(tmp_path)
    # Ignore build/ via .gitignore
    (root / ".gitignore").write_text("build/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "ignore build dir"], cwd=root, check=True)

    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Create an ignored python script under scripts/build/example.py
    script_dir = root / "scripts/build"
    script_dir.mkdir(parents=True, exist_ok=True)
    (script_dir / "example.py").write_text("# ignored build script\n", encoding="utf-8")

    # Git status considers scripts/build/ ignored, so tree is reported clean
    assert git_tree_is_clean(root) is True

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    # But local_inputs_fingerprint hashes scripts/ py sources and forces a rescan
    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_agent_skills_ignored_file_change_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from gaia_cli.steward.controller import git_tree_is_clean

    root = _git_repo(tmp_path)
    # Ignore *.tmp via .gitignore
    (root / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "ignore tmp files"], cwd=root, check=True)

    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Add an ignored .tmp file under .agents/skills/
    skills_dir = root / ".agents/skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    (skills_dir / "draft.tmp").write_text("temporary content", encoding="utf-8")

    # Tree is clean according to git status because draft.tmp is ignored
    assert git_tree_is_clean(root) is True

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    # But local_inputs_fingerprint includes .agents/skills/ files and forces a rescan
    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_expired_observation_input_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    from dataclasses import replace
    # Create an observation whose collectedAt was valid at scan time (6 days, 23 hours, 59 minutes ago)
    # but crosses the 7-day boundary when clock advances 120 seconds
    valid_near_boundary = (FROZEN - timedelta(days=7) + timedelta(seconds=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    obs = replace(scan.observations[0], provenance={"collectedAt": valid_near_boundary})
    boundary_scan = replace(scan, observations=(obs,))

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    # Advance clock past the 7-day boundary
    clock_time = FROZEN + timedelta(seconds=120)
    monkeypatch.setattr(controller, "clock", lambda: clock_time)

    result = render_dispatch(root, debt_id, controller=controller, scan=boundary_scan)
    assert len(scan_called) == 1
    assert result.scan is not boundary_scan


def test_render_dispatch_empty_mirror_root_removal_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    # Ensure .claude/skills exists initially
    mirror_dir = root / ".claude/skills"
    mirror_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "commit", "--allow-empty", "-qm", "add empty mirror root"], cwd=root, check=True)

    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Remove the empty mirror root
    mirror_dir.rmdir()

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    # Removal of empty mirror root alters local_inputs_fingerprint directory existence token
    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_scan_receipt_id_binds_finished_at(tmp_path: Path) -> None:
    from gaia_cli.steward.policy import StewardPolicy

    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)

    # Scans with identical observation inputs but different finished_at must yield distinct receipt IDs
    scan1 = controller.scan(root)
    from gaia_cli.steward.controller import _timestamp
    later_finished = _timestamp(FROZEN + timedelta(seconds=10))
    scan2 = controller._reconcile_and_commit(
        root=root,
        policy=StewardPolicy.load(root),
        observed_at=scan1.receipt.started_at,
        observations=list(scan1.observations),
        state_directory=root / ".gaia/steward",
        debt_state_path=root / ".gaia/steward/debt.json",
        receipts_directory=root / ".gaia/steward/receipts",
        finished_at=later_finished,
    )
    assert scan1.receipt.started_at == scan2.receipt.started_at
    assert scan1.receipt.finished_at != scan2.receipt.finished_at
    assert scan1.receipt.run_id != scan2.receipt.run_id


def test_render_dispatch_lowercase_z_future_transition_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Create an input with lowercase z that is 6 minutes in the future at scan time (> 5 min tolerance: "future")
    inputs_dir = root / ".gaia/steward/inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    future_input = inputs_dir / "ci-runs.json"
    future_time = (FROZEN + timedelta(minutes=6)).strftime("%Y-%m-%dT%H:%M:%Sz")
    future_input.write_text(f'{{"collectedAt": "{future_time}"}}', encoding="utf-8")

    scan = controller.scan(root)

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    # When clock advances 2 minutes, timestamp is now 4 minutes in future (<= 5 min tolerance), transitioning "future" -> "valid"
    monkeypatch.setattr(controller, "clock", lambda: FROZEN + timedelta(minutes=2))

    result = render_dispatch(root, debt_id, controller=controller, scan=scan, max_age_seconds=1000000)
    # The transition from "future" to "valid" forces a rescan
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_non_utf8_receipt_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Corrupt receipt with invalid UTF-8 bytes
    scan.receipt_path.write_bytes(b"\x80\xff\xfe\xfd invalid utf-8")

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_changed_tail_beyond_1mb_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    # Ignore generated-output
    (root / ".gitignore").write_text("generated-output/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "ignore generated-output"], cwd=root, check=True)

    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)

    out_dir = root / "generated-output"
    out_dir.mkdir(parents=True, exist_ok=True)
    target_file = out_dir / "target.bin"
    # Create 2 MiB file with zeros
    target_file.write_bytes(b"\0" * (2 * 1024 * 1024))

    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id
    orig_stat = target_file.stat()

    # Modify bytes beyond 1.5 MiB, preserving exact size and mtime
    with target_file.open("r+b") as f:
        f.seek(1572864)
        f.write(b"modified_tail_bytes_beyond_1mb")
    os.utime(target_file, (orig_stat.st_atime, orig_stat.st_mtime))

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    # Complete file streaming in fingerprinting detects the tail change despite identical mtime and size
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_github_issues_census_expiration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Create github-issues.json containing both collectedAt and fetchedAt
    inputs_dir = root / ".gaia/steward/inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    census_file = inputs_dir / "github-issues.json"
    fetched_at = (FROZEN - timedelta(hours=6) + timedelta(seconds=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    collected_at = (FROZEN - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    census_file.write_text(f'{{"schemaVersion": "github-issues-v1", "fetchedAt": "{fetched_at}", "collectedAt": "{collected_at}"}}', encoding="utf-8")

    scan = controller.scan(root)

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    # Advance clock past the 6-hour census boundary (120 seconds forward)
    clock_time = FROZEN + timedelta(seconds=120)
    monkeypatch.setattr(controller, "clock", lambda: clock_time)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    # Census boundary (6 hours via fetchedAt) triggers rescan rather than 7-day collectedAt
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_github_prs_census_expiration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Create github-prs.json with fetchedAt 59 minutes old (valid under 1h policy)
    inputs_dir = root / ".gaia/steward/inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    census_file = inputs_dir / "github-prs.json"
    fetched_at = (FROZEN - timedelta(minutes=59)).strftime("%Y-%m-%dT%H:%M:%SZ")
    census_file.write_text(f'{{"schemaVersion": "github-prs-v1", "fetchedAt": "{fetched_at}"}}', encoding="utf-8")

    scan = controller.scan(root)

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    # Advance clock past the 1-hour PR census boundary (120 seconds forward = 61 minutes old)
    clock_time = FROZEN + timedelta(seconds=120)
    monkeypatch.setattr(controller, "clock", lambda: clock_time)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    # PR census boundary (1 hour) triggers rescan
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_bundled_schema_ignored_file_change_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from gaia_cli.steward.controller import git_tree_is_clean

    root = _git_repo(tmp_path)
    (root / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "ignore tmp files"], cwd=root, check=True)

    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Create an ignored *.tmp file in src/gaia_cli/data/registry/schema/
    schema_dir = root / "src/gaia_cli/data/registry/schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (schema_dir / "draft.tmp").write_text("{}", encoding="utf-8")

    assert git_tree_is_clean(root) is True

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    # Bundled schema mirror surface change alters fingerprint and forces rescan
    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_different_controller_instance_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller1 = _controller(sensor)
    scan = controller1.scan(root)
    debt_id = scan.open_debts[0].id

    # Create distinct controller instance with same sensor config
    controller2 = _controller(sensor)

    scan_called = []
    orig_scan = controller2.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller2, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller2, scan=scan)
    # Different controller instance forces a fresh scan
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_mismatched_controller_sensors_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor1 = RoutingSensor(include_c=0)
    controller1 = _controller(sensor1)
    scan = controller1.scan(root)
    debt_id = scan.open_debts[0].id

    # Create controller2 with a different sensor
    class OtherSensor(RoutingSensor):
        id = "other-sensor"

    sensor2 = OtherSensor(include_c=0)
    controller2 = _controller(sensor2)

    scan_called = []
    orig_scan = controller2.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller2, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller2, scan=scan)
    # Mismatched sensor set on receiving controller forces a fresh scan
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_mutated_sensor_config_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Mutate the sensor configuration under the same sensor ID
    sensor.include_c = 1

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    # Sensor configuration change alters sensor_signature and forces rescan
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_private_sensor_attr_change_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    sensor._private_threshold = 42
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Mutate private attribute
    sensor._private_threshold = 99

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_cyclic_sensor_config_handled_safely(tmp_path: Path) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    # Create cyclic configuration
    cyclic_list: list[Any] = []
    cyclic_list.append(cyclic_list)
    sensor.cyclic = cyclic_list

    controller = _controller(sensor)
    # Does not raise RecursionError during scan
    scan = controller.scan(root)
    assert scan is not None


def test_render_dispatch_mixed_dict_slotted_nested_config_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)

    class MixedConfig:
        __slots__ = ("slot_val", "__dict__")

        def __init__(self, slot_val: str, dict_val: int):
            self.slot_val = slot_val
            self.dict_val = dict_val

    sensor = RoutingSensor(include_c=0)
    cfg = MixedConfig("initial_slot", 100)
    sensor.mixed_cfg = cfg
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Mutate the slotted attribute on the mixed object
    cfg.slot_val = "changed_slot"

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_container_type_mutation_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    # Start with list
    sensor.items = ["a", "b"]
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Mutate from list to tuple
    sensor.items = ("a", "b")

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    # Distinct container types list[...] vs tuple(...) forces rescan
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_undeclared_telemetry_attr_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    # Undeclared counter field
    sensor.scans = 1
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Mutate undeclared field
    sensor.scans = 2

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    # Without _telemetry_attrs declaration, mutating scans forces rescan
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_symlink_target_content_change_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    (root / ".gitignore").write_text("generated-output/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "ignore generated-output"], cwd=root, check=True)

    out_dir = root / "generated-output"
    out_dir.mkdir(parents=True, exist_ok=True)
    real_file = out_dir / "real.txt"
    real_file.write_text("initial content", encoding="utf-8")
    link_file = out_dir / "link.txt"
    link_file.symlink_to(real_file)

    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Change the target file content while keeping symlink intact
    real_file.write_text("modified content through symlink", encoding="utf-8")

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    # Target content change alters local inputs fingerprint and forces rescan
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_symlink_under_surface_does_not_disable_reuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    (root / ".gitignore").write_text("generated-output/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "ignore generated-output"], cwd=root, check=True)

    out_dir = root / "generated-output"
    out_dir.mkdir(parents=True, exist_ok=True)
    real_file = out_dir / "real.txt"
    real_file.write_text("content", encoding="utf-8")
    link_file = out_dir / "link.txt"
    link_file.symlink_to(real_file)

    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    # Symlink under surface is hashed via link target without making fingerprint None
    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 0
    assert result.scan is scan


def test_render_dispatch_sensor_config_mutation_during_scan_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)

    class MidScanMutatingSensor(RoutingSensor):
        def __init__(self):
            super().__init__(include_c=0)
            self.mode = "before"

        def scan(self, repo_root: Path, observed_at: str):
            res = super().scan(repo_root, observed_at)
            self.mode = "after_collection"
            return res

    sensor = MidScanMutatingSensor()
    controller = _controller(sensor)
    scan = controller.scan(root)
    # Mutation during observation collection makes sensor_signature empty/None
    assert scan.sensor_signature == ()
    debt_id = scan.open_debts[0].id

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_slotted_sensor_attr_change_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)

    class SlottedSensor(RoutingSensor):
        __slots__ = ("slotted_mode",)

        def __init__(self, mode: str):
            super().__init__(include_c=0)
            self.slotted_mode = mode

    sensor = SlottedSensor("fast")
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Mutate slotted attribute
    sensor.slotted_mode = "thorough"

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_string_and_mangled_slots_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)

    class MangledSlottedSensor(RoutingSensor):
        __slots__ = "__mangled_mode"

        def __init__(self, mode: str):
            super().__init__(include_c=0)
            self.__mangled_mode = mode

        def set_mode(self, mode: str):
            self.__mangled_mode = mode

    sensor = MangledSlottedSensor("initial")
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Mutate string-declared, name-mangled private slot
    sensor.set_mode("updated")

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_nested_mutable_config_obj_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)

    class CustomConfig:
        def __init__(self, val: int):
            self.val = val

    sensor = RoutingSensor(include_c=0)
    cfg = CustomConfig(10)
    sensor.custom_cfg = cfg
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Mutate field inside nested mutable config object
    cfg.val = 20

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_remote_origin_url_change_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/gaia-research/gaia-skill-tree.git"], cwd=root, check=True)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Change remote.origin.url
    subprocess.run(["git", "remote", "set-url", "origin", "https://github.com/attacker/malicious.git"], cwd=root, check=True)

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    # Origin URL change alters local inputs fingerprint and forces rescan
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_nested_timestamp_not_mistaken_for_top_level(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Create an input where fetchedAt is nested inside an inner object, but top-level collectedAt is fresh
    inputs_dir = root / ".gaia/steward/inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    test_file = inputs_dir / "ci-runs.json"
    fresh_time = (FROZEN - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    nested_stale_time = (FROZEN - timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M:%SZ")
    test_file.write_text(f'{{"collectedAt": "{fresh_time}", "extra": {{"fetchedAt": "{nested_stale_time}"}}}}', encoding="utf-8")

    scan = controller.scan(root)

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    # Nested fetchedAt does not override top-level collectedAt; scan reuse succeeds
    assert len(scan_called) == 0
    assert result.scan is scan


def test_render_dispatch_large_census_expiry_boundary_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Create a >20 MiB oversized file in inputs/
    inputs_dir = root / ".gaia/steward/inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    census_file = inputs_dir / "github-issues.json"
    with census_file.open("wb") as f:
        f.seek(22 * 1024 * 1024 - 1)
        f.write(b"\0")

    scan = controller.scan(root)

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    # Oversized input file in inputs/ fails closed and forces a rescan
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_large_artifact_does_not_disable_reuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    # Ignore generated-output
    (root / ".gitignore").write_text("generated-output/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "ignore generated-output"], cwd=root, check=True)

    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)

    # Pre-create a large artifact (35 MiB sparse file) in generated-output/ before initial scan
    out_dir = root / "generated-output"
    out_dir.mkdir(parents=True, exist_ok=True)
    large_file = out_dir / "large_model.bin"
    with large_file.open("wb") as f:
        f.seek(35 * 1024 * 1024 - 1)
        f.write(b"\0")

    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    # Large file was boundedly fingerprinted without failing; scan reuse succeeds
    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 0
    assert result.scan is scan


def test_render_dispatch_corrupted_receipt_forces_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Corrupt a field in the persisted receipt on disk while keeping the original runId
    receipt_dict = json.loads(scan.receipt_path.read_text(encoding="utf-8"))
    receipt_dict["observationsCollected"] = 99999
    scan.receipt_path.write_text(json.dumps(receipt_dict), encoding="utf-8")

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_census_expiry_boundary_invalidates_reuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Create a census input whose fetchedAt is 5 hours, 59 minutes old (valid under 6h policy)
    inputs_dir = root / ".gaia/steward/inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    census_file = inputs_dir / "census.json"
    fetched_at = (FROZEN - timedelta(hours=6) + timedelta(seconds=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    census_file.write_text(f'{{"fetchedAt": "{fetched_at}"}}', encoding="utf-8")

    scan = controller.scan(root)

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    # Advance clock past the 6-hour boundary (120 seconds forward)
    clock_time = FROZEN + timedelta(seconds=120)
    monkeypatch.setattr(controller, "clock", lambda: clock_time)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_already_stale_input_does_not_force_rescan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Create an input file in inputs/ that was already stale (10 days old) at scan time
    inputs_dir = root / ".gaia/steward/inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    stale_file = inputs_dir / "old-advisories.json"
    stale_file.write_text('{"collectedAt": "2026-07-01T00:00:00Z"}', encoding="utf-8")

    # Rescan so scan incorporates the stale input in inputs_hash and finishes
    scan = controller.scan(root)

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    # Calling render_dispatch does not rescan because its status ('past') didn't change
    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 0
    assert result.scan is scan


def test_render_dispatch_inputs_change_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Add an input file after scan
    inputs_dir = root / ".gaia/steward/inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    (inputs_dir / "test-history.json").write_text('{"runs": 1}', encoding="utf-8")

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_foreign_checkout_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path / "first")
    foreign_root = _git_repo(tmp_path / "foreign")
    sensor = RoutingSensor(include_c=0)
    foreign_controller = _controller(sensor)
    foreign_scan = foreign_controller.scan(foreign_root)
    debt_id = foreign_scan.open_debts[0].id

    controller = _controller(sensor)
    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=foreign_scan)
    assert len(scan_called) == 1
    assert result.scan is not foreign_scan
    assert result.scan.debt_state_path == root / ".gaia/steward/debt.json"


def test_head_change_during_sensor_collection_unstable_head(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    committed = [False]

    class HeadChangingSensor(RoutingSensor):
        def scan(self, repo_root: Path, observed_at: str):
            if not committed[0]:
                committed[0] = True
                subprocess.run(["git", "commit", "--allow-empty", "-qm", "mid-scan-commit"], cwd=repo_root, check=True)
            return super().scan(repo_root, observed_at)

    sensor = HeadChangingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    # Because HEAD changed during observation collection, head_commit must be None
    assert scan.head_commit is None
    debt_id = scan.open_debts[0].id

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan
    assert result.scan.head_commit is not None


def test_render_dispatch_working_tree_modification_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Modify a tracked file in the working tree
    tracked_file = root / "founder/steward/POLICY.yaml"
    tracked_file.write_text(tracked_file.read_text(encoding="utf-8") + "\n# modified", encoding="utf-8")

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_ledger_modification_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from gaia_cli.steward.receipts import write_current_state

    root = _git_repo(tmp_path)
    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Overwrite debt.json with empty debt state
    debt_path = root / ".gaia/steward/debt.json"
    state_root = root / ".gaia/steward"
    write_current_state(debt_path, [], repo_root=root, state_root=state_root)

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_fullrun_batch_dispatch_single_scan(tmp_path: Path) -> None:
    from tests.steward.test_fullrun_scenarios import hygieneRunner, pinMaxInFlight
    from tests.steward.test_fullrun import makeRunner

    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path, ["a", "b", "c"])
    pinMaxInFlight(repo, 3, perRun=3)
    controller = StewardController(sensors=(sensor,))
    scan_count = [0]
    orig_scan = controller.scan

    def counted_scan(*args, **kwargs):
        scan_count[0] += 1
        return orig_scan(*args, **kwargs)

    controller.scan = counted_scan

    runner = makeRunner(repo, store, [sensor])
    runner.config.controller_factory = lambda: controller

    view = runner.start("full")
    build_actions = [a for a in view.actions if a["type"] == "agent.build"]
    assert len(build_actions) == 3
    assert scan_count[0] == 1


def test_render_dispatch_ignored_dot_prefixed_sensor_input_modification_forces_rescan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _git_repo(tmp_path)
    inputs_dir = root / ".gaia/steward/inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    dot_input = inputs_dir / ".ci-runs.json"
    dot_input.write_text('{"schemaVersion": "steward-ci-runs-v1", "runs": []}', encoding="utf-8")

    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Verify initial scan is reusable
    result_same = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert result_same.scan is scan

    # Modify the ignored dot-prefixed sensor input
    dot_input.write_text('{"schemaVersion": "steward-ci-runs-v1", "runs": [{"id": "run-1"}]}', encoding="utf-8")

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_ignored_dot_prefixed_directory_input_modification_forces_rescan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _git_repo(tmp_path)
    hidden_dir = root / ".gaia/steward/.custom_inputs"
    hidden_dir.mkdir(parents=True, exist_ok=True)
    hidden_file = hidden_dir / "config.json"
    hidden_file.write_text('{"mode": "default"}', encoding="utf-8")

    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Verify initial scan is reusable
    result_same = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert result_same.scan is scan

    # Modify file inside ignored dot-prefixed directory
    hidden_file.write_text('{"mode": "modified"}', encoding="utf-8")

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan


def test_render_dispatch_ignored_dot_prefixed_watcher_input_forces_rescan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _git_repo(tmp_path)
    watcher_dir = root / ".gaia/upstream-watcher"
    watcher_dir.mkdir(parents=True, exist_ok=True)
    dot_feed = watcher_dir / ".custom_feed.json"
    dot_feed.write_text('{"entries": []}', encoding="utf-8")

    sensor = RoutingSensor(include_c=0)
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id

    # Verify initial scan is reusable
    result_same = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert result_same.scan is scan

    # Modify file inside ignored dot-prefixed watcher
    dot_feed.write_text('{"entries": ["entry-1"]}', encoding="utf-8")

    scan_called = []
    orig_scan = controller.scan

    def spy_scan(*args, **kwargs):
        scan_called.append(True)
        return orig_scan(*args, **kwargs)

    monkeypatch.setattr(controller, "scan", spy_scan)

    result = render_dispatch(root, debt_id, controller=controller, scan=scan)
    assert len(scan_called) == 1
    assert result.scan is not scan

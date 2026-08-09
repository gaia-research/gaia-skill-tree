from __future__ import annotations

import json
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

import gaia_cli.steward.controller as controller_module
import gaia_cli.steward.receipts as receipt_store
from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.models import Observation, Receipt, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH
from gaia_cli.steward.receipts import StateError


REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN = datetime(2026, 8, 9, tzinfo=timezone.utc)
LATER = datetime(2026, 8, 10, tzinfo=timezone.utc)


def _repo(tmp_path: Path) -> Path:
    destination = tmp_path / POLICY_RELATIVE_PATH
    destination.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, destination)
    (tmp_path / "tracked.txt").write_text("untouched\n", encoding="utf-8")
    return tmp_path


def _observation(status: str, observed_at: str = "2026-08-09T00:00:00Z") -> Observation:
    return Observation(
        kind="bundled_schema_mirror_drift",
        subject=Subject(type="repository-surface", id="registry-schema"),
        observed_at=observed_at,
        source="fixture-sensor",
        status=status,
        current_state={"digest": "canonical"},
        observed_state={"digest": "mirror" if status == "drift" else "canonical"},
        confidence=1.0,
    )


def _receipt(run_id: str = "steward-concurrency-fixture") -> Receipt:
    return Receipt(
        run_id=run_id,
        started_at="2026-08-09T00:00:00Z",
        finished_at="2026-08-09T00:00:00Z",
        observations_collected=0,
        coverage_unknown=(),
        debt_created=(),
        debt_updated=(),
        debt_resolved=(),
        open_debt=(),
        authority_counts={"A": 0, "B": 0, "C": 0},
        result_status="no_change",
    )


@dataclass
class MutableSensor:
    id: str = "fixture-sensor"
    status: str = "healthy"
    duplicate: bool = False
    fail: bool = False

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        if self.fail:
            raise OSError("fixture sensor unavailable")
        item = _observation(self.status, observed_at)
        return [item, item] if self.duplicate else [item]


def _files_outside_state(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".gaia" not in path.relative_to(root).parts
    }


def test_clean_scan_writes_no_change_receipt_only_under_ignored_state(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    before = _files_outside_state(root)
    controller = StewardController(sensors=[MutableSensor()], clock=lambda: FROZEN)

    result = controller.scan(root)

    assert result.open_debts == ()
    assert result.receipt.result_status == "no_change"
    assert result.receipt.debt_created == ()
    assert result.debt_state_path == root / ".gaia/steward/debt.json"
    assert result.receipt_path.parent == root / ".gaia/steward/receipts"
    assert _files_outside_state(root) == before


def test_duplicate_drift_is_deduplicated_and_same_clock_is_idempotent(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = MutableSensor(status="drift", duplicate=True)
    controller = StewardController(sensors=[sensor], clock=lambda: FROZEN)

    first = controller.scan(root)
    first_state = first.debt_state_path.read_bytes()
    second = controller.scan(root)

    assert len(first.open_debts) == 1
    assert first.open_debts[0].observation_count == 1
    assert second.open_debts[0].id == first.open_debts[0].id
    assert second.open_debts[0].observation_count == 1
    assert second.receipt.debt_created == ()
    assert second.receipt.debt_updated == ()
    assert second.debt_state_path.read_bytes() == first_state


def test_recovered_observation_resolves_but_retains_debt_record(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = MutableSensor(status="drift")
    StewardController(sensors=[sensor], clock=lambda: FROZEN).scan(root)
    sensor.status = "healthy"

    recovered = StewardController(sensors=[sensor], clock=lambda: LATER).scan(root)

    assert recovered.open_debts == ()
    assert len(recovered.debts) == 1
    assert recovered.debts[0].status == "resolved"
    assert recovered.debts[0].resolution == "condition_recovered"
    assert recovered.receipt.debt_resolved == (recovered.debts[0].id,)


def test_sensor_failure_is_unknown_and_does_not_clear_existing_debt(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = MutableSensor(status="drift")
    first = StewardController(sensors=[sensor], clock=lambda: FROZEN).scan(root)
    original_id = first.open_debts[0].id
    sensor.fail = True

    failed = StewardController(sensors=[sensor], clock=lambda: LATER).scan(root)

    assert failed.receipt.result_status == "blocked"
    assert failed.receipt.coverage_unknown == ("fixture-sensor",)
    assert original_id in {debt.id for debt in failed.open_debts}
    coverage = [debt for debt in failed.open_debts if debt.kind == "sensor_coverage_unknown"]
    assert len(coverage) == 1
    assert coverage[0].authority.value == "B"
    assert coverage[0].observed_state["coverage"] == "unknown"


def test_run_refuses_class_a_mutation_when_any_sensor_coverage_is_unknown(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    mirror = root / "src/gaia_cli/data/registry/schema/fixture.json"
    mirror.parent.mkdir(parents=True)
    mirror.write_text('{"before":"must-survive"}\n', encoding="utf-8")
    before = mirror.read_bytes()

    result = StewardController(
        sensors=[
            MutableSensor(status="drift"),
            MutableSensor(id="unrelated-failure", fail=True),
        ],
        clock=lambda: FROZEN,
    ).run(root)

    assert result.receipt.result_status == "blocked"
    assert result.receipt.repairs == ()
    assert result.receipt.blocked[0]["coverageUnknown"] == ["unrelated-failure"]
    assert mirror.read_bytes() == before


def test_receipts_are_immutable_and_equivalent_repeat_reuses_receipt(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    controller = StewardController(sensors=[MutableSensor()], clock=lambda: FROZEN)
    first = controller.scan(root)
    receipt_bytes = first.receipt_path.read_bytes()

    second = controller.scan(root)

    assert second.receipt_path == first.receipt_path
    assert second.receipt_path.read_bytes() == receipt_bytes
    assert len(list(second.receipt_path.parent.glob("*.json"))) == 1


@pytest.mark.parametrize("symlink_location", [".gaia", ".gaia/steward", ".gaia/steward/receipts"])
def test_state_path_symlink_escape_is_refused_before_any_write(
    tmp_path: Path,
    symlink_location: str,
) -> None:
    root = _repo(tmp_path / "repo")
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / symlink_location
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("directory symlinks are unavailable on this platform")

    with pytest.raises(StateError, match="symlink|escapes"):
        StewardController(sensors=[MutableSensor(status="drift")], clock=lambda: FROZEN).scan(root)

    assert list(outside.iterdir()) == []


def test_symlinked_debt_file_is_refused_without_touching_target(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")
    state = root / ".gaia/steward"
    state.mkdir(parents=True)
    outside = tmp_path / "outside-debt.json"
    outside.write_text("sentinel\n", encoding="utf-8")
    try:
        (state / "debt.json").symlink_to(outside)
    except (NotImplementedError, OSError):
        pytest.skip("file symlinks are unavailable on this platform")

    with pytest.raises(StateError, match="symlink"):
        StewardController(sensors=[MutableSensor(status="drift")], clock=lambda: FROZEN).scan(root)

    assert outside.read_text(encoding="utf-8") == "sentinel\n"


def test_receipt_failure_cannot_commit_new_debt_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    baseline = StewardController(
        sensors=[MutableSensor(status="healthy")], clock=lambda: FROZEN
    ).scan(root)
    state_before = baseline.debt_state_path.read_bytes()

    def fail_receipt(*args, **kwargs):
        raise StateError("fixture receipt failure")

    monkeypatch.setattr("gaia_cli.steward.controller.write_immutable_receipt", fail_receipt)

    with pytest.raises(StateError, match="fixture receipt failure"):
        StewardController(
            sensors=[MutableSensor(status="drift")], clock=lambda: LATER
        ).scan(root)

    assert baseline.debt_state_path.read_bytes() == state_before
    assert not (root / ".gaia/steward/.scan.lock").exists()


def test_ledger_failure_removes_receipt_from_aborted_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)

    def fail_state(*args, **kwargs):
        raise StateError("fixture ledger failure")

    monkeypatch.setattr("gaia_cli.steward.controller.write_current_state", fail_state)

    with pytest.raises(StateError, match="fixture ledger failure"):
        StewardController(
            sensors=[MutableSensor(status="drift")], clock=lambda: FROZEN
        ).scan(root)

    assert not (root / ".gaia/steward/debt.json").exists()
    assert list((root / ".gaia/steward/receipts").glob("*.json")) == []
    assert not (root / ".gaia/steward/.scan.lock").exists()


def test_transaction_lock_prevents_failed_run_from_revoking_successful_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    controller = StewardController(
        sensors=[MutableSensor(status="drift")], clock=lambda: FROZEN
    )
    receipt_published = threading.Event()
    allow_ledger_failure = threading.Event()
    first_write = True
    real_write = controller_module.write_current_state

    def fail_first_ledger_commit(*args, **kwargs):
        nonlocal first_write
        if first_write:
            first_write = False
            receipt_published.set()
            assert allow_ledger_failure.wait(timeout=5)
            raise StateError("fixture first ledger failure")
        return real_write(*args, **kwargs)

    monkeypatch.setattr(
        controller_module,
        "write_current_state",
        fail_first_ledger_commit,
    )

    with ThreadPoolExecutor(max_workers=1) as executor:
        failed_run = executor.submit(controller.scan, root)
        assert receipt_published.wait(timeout=5)

        with pytest.raises(StateError, match="another scan is active|prior process crashed"):
            controller.scan(root)

        allow_ledger_failure.set()
        with pytest.raises(StateError, match="fixture first ledger failure"):
            failed_run.result(timeout=10)

    assert not (root / ".gaia/steward/.scan.lock").exists()
    assert list((root / ".gaia/steward/receipts").glob("*.json")) == []

    successful_run = controller.scan(root)

    assert successful_run.receipt_path.is_file()
    assert json.loads(successful_run.receipt_path.read_text(encoding="utf-8")) == (
        successful_run.receipt.to_dict()
    )
    assert successful_run.debt_state_path.is_file()
    assert not (root / ".gaia/steward/.scan.lock").exists()


def test_stale_scan_lock_fails_closed_with_recovery_guidance(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    lock = root / ".gaia/steward/.scan.lock"
    lock.mkdir(parents=True)

    with pytest.raises(StateError, match="prior process crashed.*confirming no scan"):
        StewardController(sensors=[MutableSensor()], clock=lambda: FROZEN).scan(root)

    assert lock.is_dir()
    assert not (root / ".gaia/steward/debt.json").exists()
    assert not (root / ".gaia/steward/receipts").exists()


def test_short_receipt_write_error_leaves_no_partial_final_or_changed_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    baseline = StewardController(
        sensors=[MutableSensor(status="healthy")], clock=lambda: FROZEN
    ).scan(root)
    ledger_before = baseline.debt_state_path.read_bytes()
    receipt_before = baseline.receipt_path.read_bytes()
    real_write = receipt_store.os.write
    calls = 0

    def short_then_error(file_descriptor: int, content: memoryview) -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            return real_write(file_descriptor, content[:7])
        raise OSError("fixture short receipt write")

    monkeypatch.setattr(receipt_store, "_write_chunk", short_then_error)

    with pytest.raises(OSError, match="fixture short receipt write"):
        StewardController(
            sensors=[MutableSensor(status="drift")], clock=lambda: LATER
        ).scan(root)

    receipts = root / ".gaia/steward/receipts"
    assert baseline.debt_state_path.read_bytes() == ledger_before
    assert baseline.receipt_path.read_bytes() == receipt_before
    assert list(receipts.glob("*.json")) == [baseline.receipt_path]
    assert list(receipts.glob(".*.tmp")) == []


def test_keyboard_interrupt_cleans_new_receipt_but_preserves_preexisting_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    baseline = StewardController(
        sensors=[MutableSensor(status="healthy")], clock=lambda: FROZEN
    ).scan(root)
    ledger_before = baseline.debt_state_path.read_bytes()
    receipt_before = baseline.receipt_path.read_bytes()

    def interrupt_state(*args, **kwargs):
        raise KeyboardInterrupt("fixture interrupt after receipt")

    monkeypatch.setattr("gaia_cli.steward.controller.write_current_state", interrupt_state)

    # A newly published receipt from a different run is transaction-owned and
    # must be removed when the following ledger commit is interrupted.
    with pytest.raises(KeyboardInterrupt, match="fixture interrupt"):
        StewardController(
            sensors=[MutableSensor(status="drift")], clock=lambda: LATER
        ).scan(root)

    receipts = root / ".gaia/steward/receipts"
    assert list(receipts.glob("*.json")) == [baseline.receipt_path]
    assert baseline.debt_state_path.read_bytes() == ledger_before

    # An equivalent run reuses the pre-existing immutable receipt. Cleanup may
    # not delete it because this transaction did not create it.
    with pytest.raises(KeyboardInterrupt, match="fixture interrupt"):
        StewardController(
            sensors=[MutableSensor(status="healthy")], clock=lambda: FROZEN
        ).scan(root)

    assert baseline.receipt_path.read_bytes() == receipt_before
    assert list(receipts.glob("*.json")) == [baseline.receipt_path]
    assert baseline.debt_state_path.read_bytes() == ledger_before
    assert not (root / ".gaia/steward/.scan.lock").exists()


def test_concurrent_identical_receipt_publish_is_complete_and_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    state = root / ".gaia/steward"
    receipts = state / "receipts"
    receipt = _receipt()
    barrier = threading.Barrier(2)
    real_publish = receipt_store._publish_stage

    def simultaneous_publish(stage: Path, final: Path) -> None:
        barrier.wait(timeout=5)
        real_publish(stage, final)

    monkeypatch.setattr(receipt_store, "_publish_stage", simultaneous_publish)

    def publish() -> tuple[Path, bool]:
        return receipt_store.write_immutable_receipt(
            receipts,
            receipt,
            repo_root=root,
            state_root=state,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(publish), executor.submit(publish)]
        results = [future.result(timeout=10) for future in futures]

    final = receipts / f"{receipt.run_id}.json"
    assert sorted(created for _path, created in results) == [False, True]
    assert {path for path, _created in results} == {final}
    assert json.loads(final.read_text(encoding="utf-8")) == receipt.to_dict()
    assert final.stat().st_size > 0
    assert list(receipts.glob(".*.tmp")) == []


def test_receipt_publication_boundary_is_absent_then_complete_never_partial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    state = root / ".gaia/steward"
    receipts = state / "receipts"
    receipt = _receipt("steward-crash-window-fixture")
    final = receipts / f"{receipt.run_id}.json"
    before_link = threading.Event()
    allow_link = threading.Event()
    after_link = threading.Event()
    allow_return = threading.Event()
    real_publish = receipt_store._publish_stage

    def paused_publish(stage: Path, target: Path) -> None:
        before_link.set()
        assert allow_link.wait(timeout=5)
        real_publish(stage, target)
        after_link.set()
        assert allow_return.wait(timeout=5)

    monkeypatch.setattr(receipt_store, "_publish_stage", paused_publish)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            receipt_store.write_immutable_receipt,
            receipts,
            receipt,
            repo_root=root,
            state_root=state,
        )
        assert before_link.wait(timeout=5)
        assert not final.exists()

        allow_link.set()
        assert after_link.wait(timeout=5)
        assert final.stat().st_size > 0
        assert json.loads(final.read_text(encoding="utf-8")) == receipt.to_dict()

        allow_return.set()
        path, created = future.result(timeout=10)

    assert (path, created) == (final, True)
    assert json.loads(final.read_text(encoding="utf-8")) == receipt.to_dict()
    assert list(receipts.glob(".*.tmp")) == []


def test_stage_cleanup_failure_cannot_revoke_concurrently_reused_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    state = root / ".gaia/steward"
    receipts = state / "receipts"
    receipt = _receipt("steward-stage-cleanup-fixture")
    final = receipts / f"{receipt.run_id}.json"
    cleanup_started = threading.Event()
    allow_cleanup_failure = threading.Event()
    injected = False
    real_unlink = receipt_store._unlink_owned

    def transient_stage_unlink_failure(path: Path) -> None:
        nonlocal injected
        if path.suffix == ".tmp" and not injected:
            injected = True
            cleanup_started.set()
            assert allow_cleanup_failure.wait(timeout=5)
            raise OSError("fixture transient stage unlink failure")
        real_unlink(path)

    monkeypatch.setattr(receipt_store, "_unlink_owned", transient_stage_unlink_failure)

    with ThreadPoolExecutor(max_workers=1) as executor:
        publisher = executor.submit(
            receipt_store.write_immutable_receipt,
            receipts,
            receipt,
            repo_root=root,
            state_root=state,
        )
        assert cleanup_started.wait(timeout=5)
        assert json.loads(final.read_text(encoding="utf-8")) == receipt.to_dict()

        reused_path, reused_created = receipt_store.write_immutable_receipt(
            receipts,
            receipt,
            repo_root=root,
            state_root=state,
        )
        assert (reused_path, reused_created) == (final, False)
        assert json.loads(final.read_text(encoding="utf-8")) == receipt.to_dict()

        allow_cleanup_failure.set()
        published_path, published_created = publisher.result(timeout=10)

    assert (published_path, published_created) == (final, True)
    assert json.loads(final.read_text(encoding="utf-8")) == receipt.to_dict()
    assert list(receipts.glob(".*.tmp")) == []

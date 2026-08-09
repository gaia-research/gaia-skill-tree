from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.models import Observation, Subject
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

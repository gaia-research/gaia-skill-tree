"""Sweep resolution and the honest "not evaluated" state (steward-full §4)."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.debt import reconcile_debt
from gaia_cli.steward.models import Observation, Receipt, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH, StewardPolicy
from gaia_cli.steward.primitives.files import SensorNotEvaluated, SensorUnavailable
from gaia_cli.steward.sensors import BundledSchemaMirrorSensor

REPO_ROOT = Path(__file__).resolve().parents[2]
START = datetime(2026, 10, 20, tzinfo=timezone.utc)


class Clock:
    """A clock that advances one minute per read, so every run is distinct."""

    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> datetime:
        self.now += timedelta(minutes=1)
        return self.now


def _stamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _repo(tmp_path: Path) -> Path:
    destination = tmp_path / POLICY_RELATIVE_PATH
    destination.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, destination)
    return tmp_path


def _class_a_repo(tmp_path: Path) -> Path:
    root = _repo(tmp_path)
    script = root / "scripts/sync_bundled_schemas.py"
    script.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / "scripts/sync_bundled_schemas.py", script)
    canonical = root / "registry/schema/fixture.json"
    canonical.parent.mkdir(parents=True)
    canonical.write_text('{"type":"canonical"}\n', encoding="utf-8")
    mirror = root / "src/gaia_cli/data/registry/schema/fixture.json"
    mirror.parent.mkdir(parents=True)
    mirror.write_text('{"type":"old"}\n', encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.test", "commit", "-qm", "base"],
        cwd=root,
        check=True,
    )
    return root


@dataclass
class DriftSensor:
    """Emits drift for ``subjects``; ``outcome`` selects how the scan ends."""

    id: str
    subjects: list[str] = field(default_factory=list)
    resolution_scope: str | None = "exhaustive"
    outcome: str = "ok"  # ok | raise | unavailable | not-evaluated
    reason: str = "no CI history supplied"

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        if self.outcome == "raise":
            raise OSError("fixture sensor failure")
        if self.outcome == "unavailable":
            raise SensorUnavailable("fixture required input missing")
        if self.outcome == "not-evaluated":
            raise SensorNotEvaluated(self.reason)
        return [
            Observation(
                kind="trust_calibration_drift",
                subject=Subject(type="named-skill", id=name),
                observed_at=observed_at,
                source=self.id,
                status="drift",
                current_state={"level": "3★"},
                observed_state={"targetLevel": "2★"},
                confidence=1.0,
            )
            for name in self.subjects
        ]


def _debts(result) -> dict[str, object]:
    return {debt.subject.id: debt for debt in result.debts}


def _open_ids(result) -> set[str]:
    return {debt.subject.id for debt in result.open_debts if debt.kind == "trust_calibration_drift"}


# --------------------------------------------------------------------- sweep


def test_exhaustive_sensor_resolves_debt_it_no_longer_observes(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = DriftSensor("fixture-exhaustive", ["owner/a", "owner/b"])
    controller = StewardController(sensors=[sensor], clock=Clock())

    first = controller.scan(root)
    assert _open_ids(first) == {"owner/a", "owner/b"}

    sensor.subjects = ["owner/a"]
    second = controller.scan(root)
    resolved = _debts(second)["owner/b"]

    assert _open_ids(second) == {"owner/a"}
    assert resolved.status == "resolved"
    assert resolved.resolution == "condition_not_reobserved"
    assert resolved.last_observed_at == second.receipt.finished_at
    assert second.receipt.debt_resolved == (resolved.id,)
    assert resolved.id not in second.receipt.open_debt


def test_swept_debt_reopens_when_the_condition_returns(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = DriftSensor("fixture-exhaustive", ["owner/a"])
    controller = StewardController(sensors=[sensor], clock=Clock())
    controller.scan(root)
    sensor.subjects = []
    swept = controller.scan(root)
    assert _debts(swept)["owner/a"].status == "resolved"

    sensor.subjects = ["owner/a"]
    reopened = _debts(controller.scan(root))["owner/a"]

    assert reopened.status == "open"
    assert reopened.resolution is None


def test_sensor_that_raised_resolves_nothing(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = DriftSensor("fixture-exhaustive", ["owner/a"])
    controller = StewardController(sensors=[sensor], clock=Clock())
    controller.scan(root)

    sensor.outcome = "raise"
    failed = controller.scan(root)

    assert _open_ids(failed) == {"owner/a"}
    assert failed.receipt.debt_resolved == ()
    assert failed.receipt.coverage_unknown == ("fixture-exhaustive",)


def test_unavailable_sensor_resolves_nothing(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = DriftSensor("fixture-exhaustive", ["owner/a"])
    controller = StewardController(sensors=[sensor], clock=Clock())
    controller.scan(root)

    sensor.outcome = "unavailable"
    failed = controller.scan(root)

    assert _open_ids(failed) == {"owner/a"}
    assert failed.receipt.debt_resolved == ()
    assert failed.receipt.coverage_unknown == ("fixture-exhaustive",)


def test_non_exhaustive_sensor_keeps_todays_semantics(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = DriftSensor("fixture-partial", ["owner/a"], resolution_scope=None)
    controller = StewardController(sensors=[sensor], clock=Clock())
    controller.scan(root)

    sensor.subjects = []
    second = controller.scan(root)

    assert _open_ids(second) == {"owner/a"}
    assert second.receipt.debt_resolved == ()


def test_unrecognized_resolution_scope_does_not_sweep(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = DriftSensor("fixture-odd", ["owner/a"], resolution_scope="partial")
    controller = StewardController(sensors=[sensor], clock=Clock())
    controller.scan(root)

    sensor.subjects = []

    assert _open_ids(controller.scan(root)) == {"owner/a"}


def test_debt_from_another_source_is_unaffected(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    exhaustive = DriftSensor("fixture-exhaustive", ["owner/a"])
    partial = DriftSensor("fixture-partial", ["owner/p"], resolution_scope=None)
    flaky = DriftSensor("fixture-flaky", ["owner/f"])
    controller = StewardController(sensors=[exhaustive, partial, flaky], clock=Clock())
    controller.scan(root)

    exhaustive.subjects = []
    partial.subjects = []
    flaky.outcome = "raise"
    second = controller.scan(root)

    debts = _debts(second)
    assert debts["owner/a"].status == "resolved"
    assert debts["owner/p"].status == "open"  # non-exhaustive: today's semantics
    assert debts["owner/f"].status == "open"  # its sensor raised: nothing swept
    assert second.receipt.debt_resolved == (debts["owner/a"].id,)


def test_controller_coverage_debt_is_never_swept(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = DriftSensor("fixture-exhaustive", ["owner/a"])
    controller = StewardController(sensors=[sensor], clock=Clock())
    sensor.outcome = "raise"
    controller.scan(root)  # opens sensor_coverage_unknown (source steward-controller)

    sensor.outcome = "ok"
    sensor.subjects = []
    recovered = controller.scan(root)

    coverage = [debt for debt in recovered.debts if debt.kind == "sensor_coverage_unknown"]
    assert len(coverage) == 1
    # Resolved by its own healthy observation, not by the sweep.
    assert coverage[0].resolution == "condition_recovered"


def test_repeated_scans_are_idempotent_after_a_sweep(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = DriftSensor("fixture-exhaustive", ["owner/a", "owner/b"])
    controller = StewardController(sensors=[sensor], clock=Clock())
    controller.scan(root)
    sensor.subjects = ["owner/a"]
    swept = controller.scan(root)
    resolved_at = _debts(swept)["owner/b"].last_observed_at

    third = controller.scan(root)
    fourth = controller.scan(root)

    for later in (third, fourth):
        debt = _debts(later)["owner/b"]
        assert debt.status == "resolved"  # already-resolved stays resolved
        assert debt.last_observed_at == resolved_at  # and is not re-stamped
        assert later.receipt.debt_resolved == ()
    assert [d.to_dict() for d in third.debts if d.subject.id == "owner/b"] == [
        d.to_dict() for d in fourth.debts if d.subject.id == "owner/b"
    ]


def test_run_sweeps_in_its_reconciliation(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = DriftSensor("fixture-exhaustive", ["owner/a"])
    controller = StewardController(sensors=[sensor], clock=Clock())
    controller.scan(root)

    sensor.subjects = []
    result = controller.run(root)

    assert result.final is not None
    assert _debts(result.final)["owner/a"].resolution == "condition_not_reobserved"
    assert result.receipt.debt_resolved == (_debts(result.final)["owner/a"].id,)


def test_reconcile_debt_is_pure_and_requires_a_timestamp_to_sweep(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = DriftSensor("fixture-exhaustive", ["owner/a"])
    controller = StewardController(sensors=[sensor], clock=Clock())
    seeded = controller.scan(root)
    existing = {debt.id: debt for debt in seeded.debts}
    snapshot = dict(existing)
    policy = StewardPolicy.load(root)

    with pytest.raises(ValueError, match="observed_at"):
        reconcile_debt([], existing, policy, exhaustive_sources={"fixture-exhaustive"})

    outcome = reconcile_debt(
        [], existing, policy,
        exhaustive_sources={"fixture-exhaustive"},
        observed_at="2026-10-21T00:00:00Z",
    )
    assert existing == snapshot  # the input mapping is never mutated
    assert [debt.resolution for debt in outcome.debts] == ["condition_not_reobserved"]

    untouched = reconcile_debt([], existing, policy)
    assert [debt.status for debt in untouched.debts] == ["open"]


# ------------------------------------------------------------- not evaluated


def test_not_evaluated_sensor_creates_no_coverage_debt_and_is_listed(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = DriftSensor("fixture-optional", outcome="not-evaluated")
    controller = StewardController(sensors=[sensor], clock=Clock())

    result = controller.scan(root)

    assert result.debts == ()
    assert result.receipt.coverage_unknown == ()
    assert result.receipt.result_status == "no_change"
    assert result.receipt.not_evaluated == (
        {"sensor": "fixture-optional", "reason": "no CI history supplied"},
    )
    assert result.receipt.to_dict()["notEvaluated"] == [
        {"sensor": "fixture-optional", "reason": "no CI history supplied"}
    ]
    assert not any(item.kind == "sensor_coverage_unknown" for item in result.observations)


def test_not_evaluated_sensor_sweeps_nothing(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = DriftSensor("fixture-optional", ["owner/a"])
    controller = StewardController(sensors=[sensor], clock=Clock())
    controller.scan(root)

    sensor.outcome = "not-evaluated"
    sensor.subjects = []
    second = controller.scan(root)

    assert _open_ids(second) == {"owner/a"}
    assert second.receipt.debt_resolved == ()
    assert [item["sensor"] for item in second.receipt.not_evaluated] == ["fixture-optional"]


def test_not_evaluated_does_not_disturb_other_sensors(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    optional = DriftSensor("fixture-optional", outcome="not-evaluated")
    working = DriftSensor("fixture-working", ["owner/a"])
    controller = StewardController(sensors=[optional, working], clock=Clock())

    result = controller.scan(root)

    assert _open_ids(result) == {"owner/a"}
    assert result.receipt.coverage_unknown == ()
    assert len(result.receipt.not_evaluated) == 1


def test_unavailable_still_takes_the_unknown_path(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    controller = StewardController(
        sensors=[DriftSensor("fixture-required", outcome="unavailable")], clock=Clock()
    )

    result = controller.scan(root)

    assert result.receipt.coverage_unknown == ("fixture-required",)
    assert result.receipt.not_evaluated == ()
    assert result.receipt.result_status == "blocked"


def test_receipt_without_not_evaluated_defaults_to_empty() -> None:
    receipt = Receipt(
        run_id="steward-legacy",
        started_at="2026-10-20T00:00:00Z",
        finished_at="2026-10-20T00:00:00Z",
        observations_collected=0,
        coverage_unknown=(),
        debt_created=(),
        debt_updated=(),
        debt_resolved=(),
        open_debt=(),
        authority_counts={"A": 0, "B": 0, "C": 0},
        result_status="no_change",
    )

    assert receipt.not_evaluated == ()
    assert receipt.to_dict()["notEvaluated"] == []
    json.dumps(receipt.to_dict())


def test_run_id_commits_to_not_evaluated(tmp_path: Path) -> None:
    ids = []
    for index, reason in enumerate(("no CI history supplied", "advisory feed absent")):
        root = _repo(tmp_path / f"r{index}")
        sensor = DriftSensor("fixture-optional", outcome="not-evaluated", reason=reason)
        controller = StewardController(sensors=[sensor], clock=lambda: START)
        ids.append(controller.scan(root).receipt.run_id)

    assert ids[0] != ids[1]


def test_run_repairs_class_a_when_a_sensor_is_merely_not_evaluated(tmp_path: Path) -> None:
    root = _class_a_repo(tmp_path)
    controller = StewardController(
        sensors=[BundledSchemaMirrorSensor(), DriftSensor("fixture-optional", outcome="not-evaluated")],
        clock=Clock(),
    )

    result = controller.run(root)

    assert result.receipt.result_status == "repaired"
    assert result.receipt.coverage_unknown == ()
    assert [item["sensor"] for item in result.receipt.not_evaluated] == ["fixture-optional"]
    assert (root / "src/gaia_cli/data/registry/schema/fixture.json").read_bytes() == (
        root / "registry/schema/fixture.json"
    ).read_bytes()


def test_run_refuses_class_a_when_a_sensor_is_unavailable(tmp_path: Path) -> None:
    root = _class_a_repo(tmp_path)
    mirror = root / "src/gaia_cli/data/registry/schema/fixture.json"
    before = mirror.read_bytes()
    controller = StewardController(
        sensors=[BundledSchemaMirrorSensor(), DriftSensor("fixture-required", outcome="unavailable")],
        clock=Clock(),
    )

    result = controller.run(root)

    assert result.receipt.result_status == "blocked"
    assert result.receipt.blocked[0]["coverageUnknown"] == ["fixture-required"]
    assert mirror.read_bytes() == before

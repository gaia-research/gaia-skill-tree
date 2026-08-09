"""One finite, report-only Gaia Steward scan cycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from gaia_cli.steward.debt import reconcile_debt
from gaia_cli.steward.models import AuthorityClass, Debt, Observation, Receipt, Subject
from gaia_cli.steward.policy import StewardPolicy
from gaia_cli.steward.receipts import (
    ensure_local_state_path,
    load_debts,
    make_run_id,
    write_current_state,
    write_immutable_receipt,
)
from gaia_cli.steward.sensors import Sensor, default_sensors


Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Steward clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class ScanResult:
    observations: tuple[Observation, ...]
    debts: tuple[Debt, ...]
    receipt: Receipt
    debt_state_path: Path
    receipt_path: Path

    @property
    def open_debts(self) -> tuple[Debt, ...]:
        return tuple(debt for debt in self.debts if debt.status == "open")

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt": self.receipt.to_dict(),
            "observations": [item.to_dict() for item in self.observations],
            "debt": [item.to_dict() for item in self.debts],
            "state": {
                "debt": str(self.debt_state_path),
                "receipt": str(self.receipt_path),
            },
        }


class StewardController:
    def __init__(
        self,
        *,
        sensors: Iterable[Sensor] | None = None,
        clock: Clock = _utc_now,
    ) -> None:
        self.sensors = tuple(sensors) if sensors is not None else default_sensors()
        self.clock = clock
        sensor_ids = [sensor.id for sensor in self.sensors]
        if len(sensor_ids) != len(set(sensor_ids)):
            raise ValueError("Steward sensor ids must be unique")

    def scan(self, repo_root: Path) -> ScanResult:
        root = repo_root.resolve()
        policy = StewardPolicy.load(root)
        observed_at = _timestamp(self.clock())
        observations: list[Observation] = []

        for sensor in self.sensors:
            try:
                sensor_observations = sensor.scan(root, observed_at)
                for observation in sensor_observations:
                    if observation.source != sensor.id:
                        raise ValueError(
                            f"sensor {sensor.id} emitted observation with source {observation.source}"
                        )
                observations.extend(sensor_observations)
                observations.append(self._coverage_observation(sensor.id, observed_at, healthy=True))
            except Exception as exc:
                observations.append(
                    self._coverage_observation(sensor.id, observed_at, healthy=False, error=exc)
                )

        if len(observations) > policy.max_observations_per_run:
            raise RuntimeError(
                f"Steward observation budget exceeded: {len(observations)} > "
                f"{policy.max_observations_per_run}"
            )

        state_directory = root / policy.state_directory
        debt_state_path = state_directory / "debt.json"
        receipts_directory = state_directory / policy.receipts_directory
        # Preflight every directory that this run could touch before reading or
        # writing state. In particular, a symlinked receipts directory must not
        # allow the earlier debt write to escape or partially commit.
        ensure_local_state_path(root, state_directory, state_directory)
        ensure_local_state_path(root, state_directory, debt_state_path)
        ensure_local_state_path(root, state_directory, receipts_directory)
        existing = load_debts(
            debt_state_path,
            repo_root=root,
            state_root=state_directory,
        )
        reconciliation = reconcile_debt(observations, existing, policy)
        open_debts = tuple(debt for debt in reconciliation.debts if debt.status == "open")
        coverage_unknown = tuple(
            sorted(
                observation.subject.id
                for observation in observations
                if observation.kind == "sensor_coverage_unknown"
                and observation.status == "drift"
            )
        )
        authority_counts = {
            authority.value: sum(1 for debt in open_debts if debt.authority is authority)
            for authority in AuthorityClass
        }
        result_status = (
            "blocked" if coverage_unknown else "debt_reported" if open_debts else "no_change"
        )
        receipt_payload = {
            "observedAt": observed_at,
            "observations": [observation.to_dict() for observation in observations],
            "created": reconciliation.created,
            "updated": reconciliation.updated,
            "resolved": reconciliation.resolved,
            "openDebt": [debt.id for debt in open_debts],
            "result": result_status,
        }
        run_id = make_run_id(observed_at, receipt_payload)
        receipt = Receipt(
            run_id=run_id,
            started_at=observed_at,
            finished_at=observed_at,
            observations_collected=len(observations),
            coverage_unknown=coverage_unknown,
            debt_created=reconciliation.created,
            debt_updated=reconciliation.updated,
            debt_resolved=reconciliation.resolved,
            open_debt=tuple(debt.id for debt in open_debts),
            authority_counts=authority_counts,
            result_status=result_status,
        )

        write_current_state(
            debt_state_path,
            reconciliation.debts,
            repo_root=root,
            state_root=state_directory,
        )
        receipt_path = write_immutable_receipt(
            receipts_directory,
            receipt,
            repo_root=root,
            state_root=state_directory,
        )
        return ScanResult(
            observations=tuple(observations),
            debts=reconciliation.debts,
            receipt=receipt,
            debt_state_path=debt_state_path,
            receipt_path=receipt_path,
        )

    @staticmethod
    def _coverage_observation(
        sensor_id: str,
        observed_at: str,
        *,
        healthy: bool,
        error: Exception | None = None,
    ) -> Observation:
        observed_state: dict[str, object] = {"coverage": "known" if healthy else "unknown"}
        if error is not None:
            observed_state.update(
                {"errorType": type(error).__name__, "error": str(error)}
            )
        return Observation(
            kind="sensor_coverage_unknown",
            subject=Subject(type="sensor", id=sensor_id),
            observed_at=observed_at,
            source="steward-controller",
            status="healthy" if healthy else "drift",
            current_state={"coverage": "known"},
            observed_state=observed_state,
            confidence=1.0,
            provenance={"sensor": sensor_id},
        )

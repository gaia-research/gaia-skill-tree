"""Finite Gaia Steward scans plus one policy-authorized Class A repair."""

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
    exclusive_scan_lock,
    load_debts,
    make_run_id,
    remove_uncommitted_receipt,
    write_current_state,
    write_immutable_receipt,
)
from gaia_cli.steward.sensors import Sensor, default_sensors
from gaia_cli.steward.repairs import MirrorTransaction, RepairError, prepare_mirror_repair


Clock = Callable[[], datetime]


class RepairPostconditionError(RepairError):
    """A verified install did not produce a fully known resolved debt state."""


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
    # Open debt ids observed as drift during this reconciliation. Routing must
    # use this membership, not a clock-resolution-dependent timestamp.
    fresh_open_debt_ids: frozenset[str]

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


@dataclass(frozen=True)
class RunResult:
    initial: ScanResult
    final: ScanResult | None
    receipt: Receipt
    receipt_path: Path

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt": self.receipt.to_dict(),
            "initial": self.initial.to_dict(),
            "final": self.final.to_dict() if self.final is not None else None,
            "state": {"receipt": str(self.receipt_path)},
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

    def scan(self, repo_root: Path, *, _lock_held: bool = False) -> ScanResult:
        root = repo_root.resolve()
        policy = StewardPolicy.load(root)
        observed_at = _timestamp(self.clock())
        observations = self._collect_observations(root, policy, observed_at)

        state_directory = root / policy.state_directory
        debt_state_path = state_directory / "debt.json"
        receipts_directory = state_directory / policy.receipts_directory
        lock_directory = state_directory / ".scan.lock"
        # Preflight every directory that this run could touch before reading or
        # writing state. In particular, a symlinked receipts directory must not
        # allow the earlier debt write to escape or partially commit.
        ensure_local_state_path(root, state_directory, state_directory)
        ensure_local_state_path(root, state_directory, debt_state_path)
        ensure_local_state_path(root, state_directory, receipts_directory)
        ensure_local_state_path(root, state_directory, lock_directory)
        if _lock_held:
            return self._reconcile_and_commit(
                root=root,
                policy=policy,
                observed_at=observed_at,
                observations=observations,
                state_directory=state_directory,
                debt_state_path=debt_state_path,
                receipts_directory=receipts_directory,
            )
        with exclusive_scan_lock(
            lock_directory,
            repo_root=root,
            state_root=state_directory,
        ):
            return self._reconcile_and_commit(
                root=root,
                policy=policy,
                observed_at=observed_at,
                observations=observations,
                state_directory=state_directory,
                debt_state_path=debt_state_path,
                receipts_directory=receipts_directory,
            )

    def run(self, repo_root: Path) -> RunResult:
        """Resolve at most one eligible, policy-declared Class A debt."""

        root = repo_root.resolve()
        policy = StewardPolicy.load(root)
        state_directory = root / policy.state_directory
        receipts_directory = state_directory / policy.receipts_directory
        lock_directory = state_directory / ".scan.lock"
        ensure_local_state_path(root, state_directory, state_directory)
        ensure_local_state_path(root, state_directory, receipts_directory)
        ensure_local_state_path(root, state_directory, lock_directory)
        with exclusive_scan_lock(lock_directory, repo_root=root, state_root=state_directory):
            initial = self.scan(root, _lock_held=True)
            if initial.receipt.coverage_unknown:
                return self._run_receipt(
                    root, state_directory, receipts_directory, initial, None,
                    result_status="blocked",
                    blocked=({
                        "reason": "sensor coverage is unknown; refusing Class A mutation",
                        "coverageUnknown": list(initial.receipt.coverage_unknown),
                    },),
                )
            eligible = tuple(
                debt for debt in initial.open_debts
                if debt.authority is AuthorityClass.A and policy.executor_for(debt.kind) is not None
            )
            if not eligible:
                if not initial.open_debts:
                    return RunResult(initial=initial, final=initial, receipt=initial.receipt, receipt_path=initial.receipt_path)
                return self._run_receipt(
                    root, state_directory, receipts_directory, initial, None,
                    result_status="blocked",
                    blocked=({"reason": "no eligible Class A repair debt", "openDebt": list(initial.receipt.open_debt)},),
                )

            # Each authorized executor owns a disjoint writable surface, so a
            # debt that cannot be proven blocks only its own repair. A blocked
            # surface must never suppress an unrelated proven one.
            prepared: list[tuple[Debt, MirrorTransaction]] = []
            blocked: list[dict[str, object]] = []
            for debt in sorted(eligible, key=lambda item: (-item.priority.score, item.id)):
                if len(prepared) >= policy.max_repairs_per_run:
                    blocked.append({
                        "debtId": debt.id,
                        "reason": "policy repair budget for this run is exhausted",
                    })
                    continue
                executor = policy.executor_for(debt.kind)
                assert executor is not None
                try:
                    transaction = prepare_mirror_repair(root, executor, state_root=state_directory)
                except RepairError as exc:
                    blocked.append({"debtId": debt.id, "reason": str(exc)})
                    continue
                except BaseException:
                    self._rollback_all(prepared)
                    raise
                if transaction is not None:
                    prepared.append((debt, transaction))

            if not prepared:
                if blocked:
                    return self._run_receipt(
                        root, state_directory, receipts_directory, initial, None,
                        result_status="blocked",
                        blocked=tuple(blocked),
                    )
                return RunResult(initial=initial, final=initial, receipt=initial.receipt, receipt_path=initial.receipt_path)

            try:
                finished_at = _timestamp(self.clock())
                observations = self._collect_observations(root, policy, finished_at)
                repair_records: list[dict[str, object]] = []
                for debt, transaction in prepared:
                    record = transaction.receipt()
                    record.update(
                        {
                            "debtId": debt.id,
                            "detected": dict(debt.observed_state),
                            "resolved": True,
                        }
                    )
                    repair_records.append(record)
                for _debt, transaction in prepared:
                    transaction.commit()
                final = self._reconcile_and_commit(
                    root=root,
                    policy=policy,
                    observed_at=finished_at,
                    observations=observations,
                    state_directory=state_directory,
                    debt_state_path=initial.debt_state_path,
                    receipts_directory=receipts_directory,
                    cycle_start=initial.receipt,
                    repairs=tuple(repair_records),
                    required_resolved=tuple(debt.id for debt, _transaction in prepared),
                    require_known_coverage=True,
                    result_status="repaired",
                    blocked=tuple(blocked),
                )
            except RepairPostconditionError as exc:
                self._rollback_all(prepared)
                return self._run_receipt(
                    root, state_directory, receipts_directory, initial, None,
                    result_status="blocked",
                    repairs=(),
                    blocked=tuple(blocked) + (
                        {
                            "debtId": ", ".join(debt.id for debt, _transaction in prepared),
                            "reason": str(exc),
                        },
                    ),
                )
            except BaseException:
                self._rollback_all(prepared)
                raise
            return RunResult(
                initial=initial,
                final=final,
                receipt=final.receipt,
                receipt_path=final.receipt_path,
            )

    @staticmethod
    def _rollback_all(prepared: list[tuple[Debt, MirrorTransaction]]) -> None:
        """Undo installed mirrors in reverse order, newest first."""

        for _debt, transaction in reversed(prepared):
            transaction.rollback()

    def _run_receipt(
        self, root: Path, state_directory: Path, receipts_directory: Path,
        initial: ScanResult, final: ScanResult | None, *, result_status: str,
        repairs: tuple[dict[str, object], ...] = (), blocked: tuple[dict[str, object], ...] = (),
    ) -> RunResult:
        finished_at = _timestamp(self.clock())
        payload = {"initial": initial.receipt.run_id, "final": final.receipt.run_id if final else None, "repairs": repairs, "blocked": blocked, "result": result_status}
        receipt = Receipt(
            run_id=make_run_id(finished_at, payload), started_at=initial.receipt.started_at,
            finished_at=finished_at, observations_collected=initial.receipt.observations_collected + (final.receipt.observations_collected if final else 0),
            coverage_unknown=initial.receipt.coverage_unknown + (final.receipt.coverage_unknown if final else ()),
            debt_created=initial.receipt.debt_created, debt_updated=initial.receipt.debt_updated,
            debt_resolved=final.receipt.debt_resolved if final else (), open_debt=final.receipt.open_debt if final else initial.receipt.open_debt,
            authority_counts=final.receipt.authority_counts if final else initial.receipt.authority_counts,
            result_status=result_status, repairs=repairs, blocked=blocked,
        )
        path, _created = write_immutable_receipt(receipts_directory, receipt, repo_root=root, state_root=state_directory)
        return RunResult(initial=initial, final=final, receipt=receipt, receipt_path=path)

    @staticmethod
    def _reconcile_and_commit(
        *,
        root: Path,
        policy: StewardPolicy,
        observed_at: str,
        observations: list[Observation],
        state_directory: Path,
        debt_state_path: Path,
        receipts_directory: Path,
        cycle_start: Receipt | None = None,
        repairs: tuple[dict[str, object], ...] = (),
        blocked: tuple[dict[str, object], ...] = (),
        required_resolved: tuple[str, ...] = (),
        require_known_coverage: bool = False,
        result_status: str | None = None,
    ) -> ScanResult:
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
        if require_known_coverage and coverage_unknown:
            raise RepairPostconditionError(
                "post-repair observation coverage is unknown: " + ", ".join(coverage_unknown)
            )
        unresolved = tuple(
            debt_id
            for debt_id in required_resolved
            if debt_id not in reconciliation.resolved
            or any(debt.id == debt_id and debt.status != "resolved" for debt in reconciliation.debts)
        )
        if unresolved:
            raise RepairPostconditionError(
                "post-repair observations did not resolve debt: " + ", ".join(unresolved)
            )
        resolved_status = result_status or (
            "blocked" if coverage_unknown else "debt_reported" if open_debts else "no_change"
        )
        debt_created = (cycle_start.debt_created if cycle_start else ()) + reconciliation.created
        debt_updated = (cycle_start.debt_updated if cycle_start else ()) + reconciliation.updated
        receipt_payload = {
            "observedAt": observed_at,
            "observations": [observation.to_dict() for observation in observations],
            "cycleStart": cycle_start.run_id if cycle_start else None,
            "created": debt_created,
            "updated": debt_updated,
            "resolved": reconciliation.resolved,
            "openDebt": [debt.id for debt in open_debts],
            "repairs": repairs,
            "blocked": blocked,
            "result": resolved_status,
        }
        run_id = make_run_id(observed_at, receipt_payload)
        receipt = Receipt(
            run_id=run_id,
            started_at=cycle_start.started_at if cycle_start else observed_at,
            finished_at=observed_at,
            observations_collected=(
                (cycle_start.observations_collected if cycle_start else 0) + len(observations)
            ),
            coverage_unknown=coverage_unknown,
            debt_created=debt_created,
            debt_updated=debt_updated,
            debt_resolved=reconciliation.resolved,
            open_debt=tuple(debt.id for debt in open_debts),
            authority_counts=authority_counts,
            result_status=resolved_status,
            repairs=repairs,
            blocked=blocked,
        )

        # The receipt is the audit precondition for committing current state.
        # If it cannot be persisted, debt.json remains untouched. If the later
        # atomic ledger replace fails, remove only the receipt created by this
        # aborted transaction.
        receipt_path: Path | None = None
        receipt_created = False
        try:
            receipt_path, receipt_created = write_immutable_receipt(
                receipts_directory,
                receipt,
                repo_root=root,
                state_root=state_directory,
            )
            write_current_state(
                debt_state_path,
                reconciliation.debts,
                repo_root=root,
                state_root=state_directory,
            )
        except BaseException:
            if receipt_created and receipt_path is not None:
                remove_uncommitted_receipt(
                    receipt_path,
                    repo_root=root,
                    state_root=state_directory,
                )
            raise
        assert receipt_path is not None
        return ScanResult(
            observations=tuple(observations),
            debts=reconciliation.debts,
            receipt=receipt,
            debt_state_path=debt_state_path,
            receipt_path=receipt_path,
            fresh_open_debt_ids=frozenset(
                observation.debt_id
                for observation in observations
                if observation.status == "drift"
            ),
        )

    def _collect_observations(
        self,
        root: Path,
        policy: StewardPolicy,
        observed_at: str,
    ) -> list[Observation]:
        """Collect sensor output without reading or writing Steward state."""

        observations: list[Observation] = []
        for sensor in self.sensors:
            try:
                sensor_observations = sensor.scan(root, observed_at)
                for observation in sensor_observations:
                    if observation.source != sensor.id:
                        raise ValueError(
                            f"sensor {sensor.id} emitted observation with source "
                            f"{observation.source}"
                        )
                observations.extend(sensor_observations)
                observations.append(
                    self._coverage_observation(sensor.id, observed_at, healthy=True)
                )
            except Exception as exc:
                observations.append(
                    self._coverage_observation(
                        sensor.id,
                        observed_at,
                        healthy=False,
                        error=exc,
                    )
                )

        if len(observations) > policy.max_observations_per_run:
            raise RuntimeError(
                f"Steward observation budget exceeded: {len(observations)} > "
                f"{policy.max_observations_per_run}"
            )
        return observations

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

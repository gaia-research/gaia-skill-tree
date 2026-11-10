"""Finite Gaia Steward scans plus one policy-authorized Class A repair."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import subprocess
from typing import Any, Callable, Iterable

from gaia_cli.steward.debt import reconcile_debt
from gaia_cli.steward.models import AuthorityClass, Debt, Observation, Receipt, SensorScan, Subject
from gaia_cli.steward.primitives.files import SKIP_CAP, SensorNotEvaluated, SensorUnavailable
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
from gaia_cli.steward.clock import utcNow


Clock = Callable[[], datetime]


class RepairPostconditionError(RepairError):
    """A verified install did not produce a fully known resolved debt state."""


def _utc_now() -> datetime:
    return utcNow()


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Steward clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def git_head_commit(root: Path) -> str | None:
    if not (root / ".git").exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD^{commit}"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def git_origin_url(root: Path) -> str | None:
    if not (root / ".git").exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def git_tree_is_clean(root: Path, state_dir_name: str = ".gaia") -> bool:
    if not (root / ".git").exists():
        return False
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all", "--", f":!{state_dir_name}"],
            cwd=root,
            capture_output=True,
            check=False,
        )
        if proc.returncode == 0:
            return len(proc.stdout.strip()) == 0
    except (OSError, subprocess.SubprocessError):
        return False
    return False


def _hash_file_bounded(path: Path, h: Any, visited_symlinks: set[str] | None = None) -> bool:
    if visited_symlinks is None:
        visited_symlinks = set()
    try:
        if path.is_symlink():
            link_target = os.readlink(path)
            h.update(f"symlink:{link_target}".encode("utf-8"))
            try:
                resolved = path.resolve(strict=True)
            except (OSError, RuntimeError):
                return False
            resolved_str = str(resolved)
            if resolved_str in visited_symlinks:
                return False
            visited_symlinks.add(resolved_str)
            if not resolved.is_file():
                return False
            target_path = resolved
        else:
            target_path = path

        st = target_path.stat()
        if not target_path.is_file():
            return False
        h.update(str(st.st_size).encode("utf-8"))
        h.update(str(st.st_mtime_ns).encode("utf-8"))
        with target_path.open("rb") as handle:
            while True:
                chunk = handle.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return True
    except (OSError, ValueError):
        return False


def local_inputs_fingerprint(state_dir: Path, repo_root: Path | None = None) -> str | None:
    h = hashlib.sha256()

    def on_error(err: OSError) -> None:
        raise err

    if state_dir.is_dir():
        try:
            for root_dir, dirs, files in os.walk(state_dir, onerror=on_error):
                root_path = Path(root_dir)
                if root_path.is_symlink():
                    return None
                for d in dirs:
                    if (root_path / d).is_symlink():
                        return None
                rel_root = root_path.relative_to(state_dir)
                if rel_root.parts and rel_root.parts[0] in {"receipts", "full", ".scan.lock"}:
                    continue
                if rel_root != Path("."):
                    h.update(f"d:{rel_root}".encode("utf-8"))
                dirs[:] = [
                    d for d in sorted(dirs)
                    if not (rel_root == Path(".") and d in {"receipts", "full", ".scan.lock"})
                    and d != ".git"
                ]
                for filename in sorted(files):
                    if filename == ".git":
                        continue
                    if rel_root == Path(".") and filename in {"debt.json", "lane.json"}:
                        continue
                    file_path = root_path / filename
                    rel_path = file_path.relative_to(state_dir)
                    h.update(str(rel_path).encode("utf-8"))
                    if not _hash_file_bounded(file_path, h):
                        return None
        except OSError:
            return None

    if repo_root is not None:
        h.update(f"origin:{git_origin_url(repo_root)}".encode("utf-8"))
        ignored_surfaces = (
            repo_root / "generated-output",
            repo_root / ".gaia/upstream-watcher",
            repo_root / ".agents/skills",
            repo_root / ".claude/skills",
            repo_root / "registry",
            repo_root / "src/gaia_cli/data/registry/schema",
        )
        for surface_dir in ignored_surfaces:
            h.update(f"surface:{surface_dir.name}:{surface_dir.is_dir()}".encode("utf-8"))
            if surface_dir.is_dir():
                try:
                    for root_dir, dirs, files in os.walk(surface_dir, onerror=on_error):
                        root_path = Path(root_dir)
                        if root_path.is_symlink():
                            return None
                        for d in dirs:
                            if (root_path / d).is_symlink():
                                return None
                        rel_root = root_path.relative_to(surface_dir)
                        h.update(f"d:{surface_dir.name}/{rel_root}".encode("utf-8"))
                        dirs[:] = [d for d in sorted(dirs) if d != ".git"]
                        for filename in sorted(files):
                            file_path = root_path / filename
                            rel_path = file_path.relative_to(repo_root)
                            h.update(str(rel_path).encode("utf-8"))
                            if not _hash_file_bounded(file_path, h):
                                return None
                except OSError:
                    return None

        # Python source trees read by sensors (scripts/ and src/)
        for py_dir_name in ("scripts", "src"):
            py_dir = repo_root / py_dir_name
            h.update(f"py_surface:{py_dir_name}:{py_dir.is_dir()}".encode("utf-8"))
            if py_dir.is_dir():
                try:
                    for root_dir, dirs, files in os.walk(py_dir, onerror=on_error):
                        root_path = Path(root_dir)
                        if root_path.is_symlink():
                            return None
                        for d in dirs:
                            if (root_path / d).is_symlink():
                                return None
                        dirs[:] = [d for d in sorted(dirs) if d != "__pycache__" and d != ".git"]
                        for filename in sorted(files):
                            if filename.endswith(".py"):
                                file_path = root_path / filename
                                rel_path = file_path.relative_to(repo_root)
                                h.update(str(rel_path).encode("utf-8"))
                                if not _hash_file_bounded(file_path, h):
                                    return None
                except OSError:
                    return None

    return h.hexdigest()


_DEFAULT_HEAD = object()


def _normalize_slots(slots_decl: Any) -> tuple[str, ...]:
    if isinstance(slots_decl, str):
        return (slots_decl,)
    if isinstance(slots_decl, Iterable):
        return tuple(str(x) for x in slots_decl)
    return ()


def _resolve_slot_name(cls: type, slot: str) -> str:
    if slot.startswith("__") and not slot.endswith("__"):
        return f"_{cls.__name__.lstrip('_')}{slot}"
    return slot


def _serialize_config_val(v: Any, visited: set[int] | None = None) -> str:
    if visited is None:
        visited = set()
    obj_id = id(v)
    if obj_id in visited:
        return "cycle"
    if isinstance(v, (str, int, float, bool, bytes)) or v is None:
        return repr(v)

    visited.add(obj_id)
    try:
        if isinstance(v, frozenset):
            return "frozenset{" + ",".join(sorted(_serialize_config_val(x, visited) for x in v)) + "}"
        if isinstance(v, set):
            return "set{" + ",".join(sorted(_serialize_config_val(x, visited) for x in v)) + "}"
        if isinstance(v, tuple):
            return "tuple(" + ",".join(_serialize_config_val(x, visited) for x in v) + ")"
        if isinstance(v, list):
            return "list[" + ",".join(_serialize_config_val(x, visited) for x in v) + "]"
        if isinstance(v, dict):
            return "{" + ",".join(f"{repr(k)}:{_serialize_config_val(val, visited)}" for k, val in sorted(v.items(), key=lambda i: str(i[0]))) + "}"

        parts = ["obj:" + v.__class__.__name__]
        if hasattr(v, "__dict__"):
            parts.append("dict:" + _serialize_config_val(v.__dict__, visited))
        for cls in getattr(v.__class__, "__mro__", ()):
            for slot in _normalize_slots(getattr(cls, "__slots__", ())):
                resolved = _resolve_slot_name(cls, slot)
                if hasattr(v, resolved):
                    parts.append(f"slot:{slot}:" + _serialize_config_val(getattr(v, resolved), visited))
        if len(parts) > 1:
            return ";".join(parts)
        return repr(v)
    finally:
        visited.remove(obj_id)


def sensor_signature(sensors: Iterable[Sensor]) -> tuple[Any, ...]:
    sig = []
    for s in sensors:
        telemetry = getattr(s, "_telemetry_attrs", frozenset())
        attrs = []
        for k, v in getattr(s, "__dict__", {}).items():
            if k in telemetry:
                continue
            attrs.append((k, _serialize_config_val(v)))
        for cls in s.__class__.__mro__:
            for raw_slot in _normalize_slots(getattr(cls, "__slots__", ())):
                if raw_slot in telemetry:
                    continue
                resolved = _resolve_slot_name(cls, raw_slot)
                if hasattr(s, resolved):
                    attrs.append((raw_slot, _serialize_config_val(getattr(s, resolved))))
        attrs.sort()
        sig.append((s.id, s.__class__.__module__, s.__class__.__qualname__, tuple(attrs)))
    return tuple(sig)


@dataclass(frozen=True)
class _Collection:
    """Everything one pass over the sensors produced."""

    observations: list[Observation]
    # Exhaustive sensors that completed this run; only these may sweep debt.
    exhaustive_sources: frozenset[str]
    # Sensors whose optional external input was not supplied this run.
    not_evaluated: tuple[dict[str, str], ...]
    # Sensors that completed but could not evaluate some subjects. They never
    # sweep: an unevaluated subject is unknown, not resolved.
    partial_coverage: tuple[dict[str, object], ...] = ()


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
    head_commit: str | None = None
    debt_state_hash: str | None = None
    tree_clean: bool = False
    inputs_hash: str | None = None
    sensor_ids: tuple[str, ...] = ()
    controller_id: int | None = None
    controller_token: str | None = None
    sensor_signature: tuple[Any, ...] = ()

    @property
    def open_debts(self) -> tuple[Debt, ...]:
        return tuple(debt for debt in self.debts if debt.status == "open")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "receipt": self.receipt.to_dict(),
            "observations": [item.to_dict() for item in self.observations],
            "debt": [item.to_dict() for item in self.debts],
            "state": {
                "debt": str(self.debt_state_path),
                "receipt": str(self.receipt_path),
            },
        }
        if self.head_commit is not None:
            payload["headCommit"] = self.head_commit
        if self.debt_state_hash is not None:
            payload["debtStateHash"] = self.debt_state_hash
        if self.tree_clean:
            payload["treeClean"] = True
        if self.inputs_hash is not None:
            payload["inputsHash"] = self.inputs_hash
        if self.sensor_ids:
            payload["sensorIds"] = list(self.sensor_ids)
        if self.controller_token is not None:
            payload["controllerToken"] = self.controller_token
        return payload


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
        self.instance_token = f"ctrl-{os.urandom(16).hex()}"
        sensor_ids = [sensor.id for sensor in self.sensors]
        if len(sensor_ids) != len(set(sensor_ids)):
            raise ValueError("Steward sensor ids must be unique")

    def scan(self, repo_root: Path, *, _lock_held: bool = False) -> ScanResult:
        root = repo_root.resolve()
        policy = StewardPolicy.load(root)
        state_prefix = policy.state_directory.parts[0] if policy.state_directory.parts else ".gaia"
        head_before = git_head_commit(root)
        tree_before_clean = git_tree_is_clean(root, state_prefix)
        inputs_before = local_inputs_fingerprint(root / policy.state_directory, repo_root=root)
        sig_before = sensor_signature(self.sensors)
        observed_at = _timestamp(self.clock())
        collection = self._collect_observations(root, policy, observed_at)
        finished_at = observed_at
        sig_after = sensor_signature(self.sensors)
        head_after = git_head_commit(root)
        tree_after_clean = git_tree_is_clean(root, state_prefix)
        inputs_after = local_inputs_fingerprint(root / policy.state_directory, repo_root=root)
        sensor_sig = sig_after if sig_before == sig_after else ()
        if (root / ".git").exists():
            head_commit = head_after if (head_before is not None and head_before == head_after) else None
            tree_clean = tree_before_clean and tree_after_clean
        else:
            head_commit = None
            tree_clean = False
        inputs_hash = inputs_after if (inputs_before is not None and inputs_before == inputs_after) else None

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
        sensor_ids = tuple(s.id for s in self.sensors)
        if _lock_held:
            return self._reconcile_and_commit(
                root=root,
                policy=policy,
                observed_at=observed_at,
                observations=collection.observations,
                exhaustive_sources=collection.exhaustive_sources,
                not_evaluated=collection.not_evaluated,
                partial_coverage=collection.partial_coverage,
                state_directory=state_directory,
                debt_state_path=debt_state_path,
                receipts_directory=receipts_directory,
                head_commit=head_commit,
                tree_clean=tree_clean,
                inputs_hash=inputs_hash,
                finished_at=finished_at,
                sensor_ids=sensor_ids,
                controller_id=id(self),
                controller_token=self.instance_token,
                sensor_sig=sensor_sig,
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
                observations=collection.observations,
                exhaustive_sources=collection.exhaustive_sources,
                not_evaluated=collection.not_evaluated,
                partial_coverage=collection.partial_coverage,
                state_directory=state_directory,
                debt_state_path=debt_state_path,
                receipts_directory=receipts_directory,
                head_commit=head_commit,
                tree_clean=tree_clean,
                inputs_hash=inputs_hash,
                finished_at=finished_at,
                sensor_ids=sensor_ids,
                controller_id=id(self),
                controller_token=self.instance_token,
                sensor_sig=sensor_sig,
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
                collection = self._collect_observations(root, policy, finished_at)
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
                    observations=collection.observations,
                    exhaustive_sources=collection.exhaustive_sources,
                    not_evaluated=collection.not_evaluated,
                    partial_coverage=collection.partial_coverage,
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
        """Undo every installed mirror, newest first, before reporting failure.

        One transaction's rollback must never cancel another's. ``rollback()``
        raises even when the mirror was restored and only its temporary
        recovery could not be cleaned up, so aborting the loop on the first
        exception would leave a later surface installed while the receipt
        reports no repair — the working tree and the audit record disagreeing.
        Every transaction is therefore attempted, and failures are aggregated.
        """

        failures: list[str] = []
        for _debt, transaction in reversed(prepared):
            try:
                transaction.rollback()
            except Exception as exc:
                failures.append(f"{transaction.spec.id}: {exc}")
        if failures:
            raise RepairError("rollback incomplete: " + "; ".join(failures))

    def _run_receipt(
        self, root: Path, state_directory: Path, receipts_directory: Path,
        initial: ScanResult, final: ScanResult | None, *, result_status: str,
        repairs: tuple[dict[str, object], ...] = (), blocked: tuple[dict[str, object], ...] = (),
    ) -> RunResult:
        finished_at = _timestamp(self.clock())
        not_evaluated = initial.receipt.not_evaluated + (final.receipt.not_evaluated if final else ())
        partial_coverage = initial.receipt.partial_coverage + (final.receipt.partial_coverage if final else ())
        payload = {"initial": initial.receipt.run_id, "final": final.receipt.run_id if final else None, "repairs": repairs, "blocked": blocked, "notEvaluated": not_evaluated, "partialCoverage": partial_coverage, "result": result_status}
        receipt = Receipt(
            run_id=make_run_id(finished_at, payload), started_at=initial.receipt.started_at,
            finished_at=finished_at, observations_collected=initial.receipt.observations_collected + (final.receipt.observations_collected if final else 0),
            coverage_unknown=initial.receipt.coverage_unknown + (final.receipt.coverage_unknown if final else ()),
            debt_created=initial.receipt.debt_created, debt_updated=initial.receipt.debt_updated,
            debt_resolved=final.receipt.debt_resolved if final else (), open_debt=final.receipt.open_debt if final else initial.receipt.open_debt,
            authority_counts=final.receipt.authority_counts if final else initial.receipt.authority_counts,
            result_status=result_status, repairs=repairs, blocked=blocked,
            not_evaluated=not_evaluated,
            partial_coverage=partial_coverage,
            coverage_known=tuple(sorted(set(initial.receipt.coverage_known) | set(final.receipt.coverage_known if final else ()))),
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
        exhaustive_sources: frozenset[str] = frozenset(),
        not_evaluated: tuple[dict[str, str], ...] = (),
        partial_coverage: tuple[dict[str, object], ...] = (),
        cycle_start: Receipt | None = None,
        repairs: tuple[dict[str, object], ...] = (),
        blocked: tuple[dict[str, object], ...] = (),
        required_resolved: tuple[str, ...] = (),
        require_known_coverage: bool = False,
        result_status: str | None = None,
        head_commit: str | None | object = _DEFAULT_HEAD,
        tree_clean: bool = False,
        inputs_hash: str | None = None,
        finished_at: str | None = None,
        sensor_ids: tuple[str, ...] = (),
        controller_id: int | None = None,
        controller_token: str | None = None,
        sensor_sig: tuple[Any, ...] = (),
    ) -> ScanResult:
        if head_commit is _DEFAULT_HEAD:
            head_commit = git_head_commit(root)
        existing = load_debts(
            debt_state_path,
            repo_root=root,
            state_root=state_directory,
        )
        reconciliation = reconcile_debt(
            observations,
            existing,
            policy,
            exhaustive_sources=exhaustive_sources,
            observed_at=observed_at,
        )
        open_debts = tuple(debt for debt in reconciliation.debts if debt.status == "open")
        coverage_unknown = tuple(
            sorted(
                observation.subject.id
                for observation in observations
                if observation.kind == "sensor_coverage_unknown"
                and observation.status == "drift"
            )
        )
        coverage_known = tuple(
            sorted(
                observation.subject.id
                for observation in observations
                if observation.kind == "sensor_coverage_unknown"
                and observation.status == "healthy"
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
        scan_finished = finished_at or observed_at
        receipt_payload = {
            "observedAt": observed_at,
            "finishedAt": scan_finished,
            "observations": [observation.to_dict() for observation in observations],
            "cycleStart": cycle_start.run_id if cycle_start else None,
            "created": debt_created,
            "updated": debt_updated,
            "resolved": reconciliation.resolved,
            "openDebt": [debt.id for debt in open_debts],
            "repairs": repairs,
            "blocked": blocked,
            "notEvaluated": not_evaluated,
            "partialCoverage": partial_coverage,
            "result": resolved_status,
        }
        run_id = make_run_id(observed_at, receipt_payload)
        receipt = Receipt(
            run_id=run_id,
            started_at=cycle_start.started_at if cycle_start else observed_at,
            finished_at=scan_finished,
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
            not_evaluated=not_evaluated,
            partial_coverage=partial_coverage,
            coverage_known=coverage_known,
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
        debt_state_hash = (
            hashlib.sha256(debt_state_path.read_bytes()).hexdigest()
            if debt_state_path.is_file()
            else None
        )
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
            head_commit=head_commit,
            debt_state_hash=debt_state_hash,
            tree_clean=tree_clean,
            inputs_hash=inputs_hash,
            sensor_ids=sensor_ids,
            controller_id=controller_id,
            controller_token=controller_token,
            sensor_signature=sensor_sig,
        )

    def _collect_observations(
        self,
        root: Path,
        policy: StewardPolicy,
        observed_at: str,
    ) -> _Collection:
        """Collect sensor output without reading or writing Steward state."""

        observations: list[Observation] = []
        exhaustive_sources: set[str] = set()
        not_evaluated: list[dict[str, str]] = []
        partial_coverage: list[dict[str, object]] = []
        budget = policy.max_observations_per_run
        for sensor in self.sensors:
            try:
                result = self._scan_sensor(sensor, root, observed_at)
                sensor_observations = list(result.observations)
                for observation in sensor_observations:
                    if observation.source != sensor.id:
                        raise ValueError(
                            f"sensor {sensor.id} emitted observation with source "
                            f"{observation.source}"
                        )
                # The sensor that crosses the budget loses its own coverage
                # (reported as unknown with the reason); the others keep
                # theirs. Truncating its observations instead would drop
                # findings without saying so.
                if len(observations) + len(sensor_observations) + 1 > budget:
                    raise SensorUnavailable(
                        f"Steward observation budget exceeded: {len(sensor_observations)} "
                        f"observation(s) from {sensor.id} do not fit in the remaining "
                        f"{max(budget - len(observations), 0)} of {budget}"
                    )
                observations.extend(sensor_observations)
                observations.append(
                    self._coverage_observation(sensor.id, observed_at, healthy=True)
                )
                if result.skipped:
                    partial_coverage.append({
                        "sensor": sensor.id,
                        "skippedCount": len(result.skipped),
                        "skipped": [dict(item) for item in result.skipped[:SKIP_CAP]],
                    })
                elif getattr(sensor, "resolution_scope", None) == "exhaustive":
                    exhaustive_sources.add(sensor.id)
            except SensorNotEvaluated as exc:
                # An optional external input was not supplied: the sensor saw
                # nothing, so there is no coverage mark either way, nothing to
                # sweep, and no reason to block a repair elsewhere.
                entry = {"sensor": sensor.id, "reason": str(exc)}
                if getattr(exc, "input_absent", False):
                    entry["inputAbsent"] = True
                not_evaluated.append(entry)
            except Exception as exc:
                observations.append(
                    self._coverage_observation(
                        sensor.id,
                        observed_at,
                        healthy=False,
                        error=exc,
                    )
                )

        return _Collection(
            observations=observations,
            exhaustive_sources=frozenset(exhaustive_sources),
            not_evaluated=tuple(not_evaluated),
            partial_coverage=tuple(partial_coverage),
        )

    @staticmethod
    def _scan_sensor(sensor: Sensor, root: Path, observed_at: str) -> SensorScan:
        """Run one sensor, preferring ``scan_detailed`` so skips stay visible.

        A legacy sensor returns a plain list and has no skipped subjects.
        """

        detailed = getattr(sensor, "scan_detailed", None)
        result = detailed(root, observed_at) if callable(detailed) else sensor.scan(root, observed_at)
        if isinstance(result, SensorScan):
            return result
        return SensorScan(observations=tuple(result))

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

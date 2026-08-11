"""Report-only Class B and Class C Steward routing.

This module deliberately renders policy-bounded artifacts only.  It never
invokes a model, creates a patch/worktree, or changes canonical repository
state.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from gaia_cli.steward.controller import ScanResult, StewardController
from gaia_cli.steward.models import (
    AuthorityClass,
    Debt,
    DispatchPacket,
    FounderDecision,
    FounderQueue,
    normalize_decision_target,
)
from gaia_cli.steward.policy import StewardPolicy
from gaia_cli.steward.receipts import (
    ensure_local_state_path,
    exclusive_scan_lock,
    make_run_id,
    write_immutable_receipt,
)


class RoutingError(RuntimeError):
    """A routing precondition was not proven; no report is rendered."""


@dataclass(frozen=True)
class RoutingReceipt:
    """Small immutable audit record for one report-only routing request."""

    run_id: str
    action: str
    scan_receipt_id: str
    artifact: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": "steward-routing-receipt-v1",
            "runId": self.run_id,
            "action": self.action,
            "scanReceiptId": self.scan_receipt_id,
            "models": [],
            "repairs": [],
            "result": {"status": "reported"},
            "artifact": dict(self.artifact),
        }


@dataclass(frozen=True)
class RoutingResult:
    scan: ScanResult
    artifact: DispatchPacket | FounderQueue
    receipt: RoutingReceipt
    receipt_path: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt": self.receipt.to_dict(),
            "artifact": self.artifact.to_dict(),
            "state": {"receipt": str(self.receipt_path)},
        }


def _assert_known_fresh_scan(scan: ScanResult) -> None:
    if scan.receipt.coverage_unknown:
        raise RoutingError(
            "sensor coverage is unknown; refusing routing: "
            + ", ".join(scan.receipt.coverage_unknown)
        )


def _assert_fresh_open(debt: Debt, scan: ScanResult) -> None:
    if debt.status != "open":
        raise RoutingError(f"debt is not open: {debt.id}")
    if debt.id not in scan.fresh_open_debt_ids:
        raise RoutingError(f"debt is stale for this scan: {debt.id}")


def _routing_evidence(debt: Debt) -> dict[str, Any]:
    return {
        "debtId": debt.id,
        "source": debt.source,
        "subject": debt.subject.to_dict(),
        "currentState": dict(debt.current_state),
        "observedState": dict(debt.observed_state),
        "lastObservedAt": debt.last_observed_at,
        "confidence": debt.confidence,
    }


def _persist(
    *,
    root: Path,
    policy: StewardPolicy,
    scan: ScanResult,
    action: str,
    artifact: DispatchPacket | FounderQueue,
) -> tuple[RoutingReceipt, Path]:
    artifact_dict = artifact.to_dict()
    # Artifact identity is semantic and intentionally stable; this hash records
    # changing evidence or membership independently.
    payload = {
        "action": action,
        "scanReceiptId": scan.receipt.run_id,
        "artifact": artifact_dict,
    }
    receipt = RoutingReceipt(
        run_id=make_run_id(scan.receipt.finished_at, payload),
        action=action,
        scan_receipt_id=scan.receipt.run_id,
        artifact=artifact_dict,
    )
    path, _created = write_immutable_receipt(
        root / policy.state_directory / policy.receipts_directory,
        receipt,
        repo_root=root,
        state_root=root / policy.state_directory,
    )
    return receipt, path


def _restore_routing_scan_state(scan: ScanResult, ledger_before: bytes | None, receipts_before: set[Path]) -> None:
    """Undo scan state if the paired routing receipt cannot be published."""

    if ledger_before is None:
        try:
            scan.debt_state_path.unlink()
        except FileNotFoundError:
            pass
    else:
        fd, temporary_name = tempfile.mkstemp(
            dir=scan.debt_state_path.parent,
            prefix=f".{scan.debt_state_path.name}.",
            suffix=".routing-rollback",
        )
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(ledger_before)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, scan.debt_state_path)
        except BaseException:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise
    for path in scan.receipt_path.parent.glob("*.json"):
        if path not in receipts_before:
            path.unlink()


def _scan_and_persist_routing(
    root: Path,
    policy: StewardPolicy,
    action: str,
    controller: StewardController,
    build: Any,
) -> RoutingResult:
    """Make scan + routing receipt one local-state transaction."""

    state_directory = root / policy.state_directory
    ledger_path = state_directory / "debt.json"
    receipts_directory = state_directory / policy.receipts_directory
    lock_directory = state_directory / ".scan.lock"
    for path in (state_directory, ledger_path, receipts_directory, lock_directory):
        ensure_local_state_path(root, state_directory, path)
    with exclusive_scan_lock(lock_directory, repo_root=root, state_root=state_directory):
        ledger_before = ledger_path.read_bytes() if ledger_path.exists() else None
        receipts_before = set(receipts_directory.glob("*.json")) if receipts_directory.exists() else set()
        scan = controller.scan(root, _lock_held=True)
        try:
            artifact = build(scan)
            receipt, receipt_path = _persist(
                root=root, policy=policy, scan=scan, action=action, artifact=artifact
            )
        except BaseException:
            _restore_routing_scan_state(scan, ledger_before, receipts_before)
            raise
    return RoutingResult(scan=scan, artifact=artifact, receipt=receipt, receipt_path=receipt_path)


def render_dispatch(repo_root: Path, debt_id: str, *, controller: StewardController | None = None) -> RoutingResult:
    """Freshly scan, then render exactly one policy-supported Class B packet."""

    root = repo_root.resolve()
    policy = StewardPolicy.load(root)
    def build(scan: ScanResult) -> DispatchPacket:
        _assert_known_fresh_scan(scan)
        debt = next((item for item in scan.debts if item.id == debt_id), None)
        if debt is None:
            raise RoutingError(f"unknown debt id: {debt_id}")
        _assert_fresh_open(debt, scan)
        rule = policy.dispatch_rule_for(debt.kind)
        if rule is None:
            raise RoutingError(f"unsupported Class B routing debt: {debt.id}")
        if debt.authority is not AuthorityClass.B or rule.authority is not AuthorityClass.B:
            raise RoutingError(f"authority mismatch for dispatch debt: {debt.id}")
        return DispatchPacket.create(
            debt=debt.to_dict(), evidence=_routing_evidence(debt), authority=debt.authority,
            rule=rule.id, routine=rule.routine, objective=rule.objective,
            allowed_paths=rule.allowed_paths, allowed_commands=rule.allowed_commands,
            forbidden_paths=rule.forbidden_paths, stop_conditions=rule.stop_conditions,
            proof=rule.proof, budget=policy.routing_budget,
        )

    return _scan_and_persist_routing(root, policy, "dispatch", controller or StewardController(), build)


def render_founder_queue(repo_root: Path, *, controller: StewardController | None = None) -> RoutingResult:
    """Freshly scan and render only exact-target Class C governance groups."""

    root = repo_root.resolve()
    policy = StewardPolicy.load(root)
    def build(scan: ScanResult) -> FounderQueue:
        _assert_known_fresh_scan(scan)
        groups: dict[tuple[str, str], list[Debt]] = {}
        for debt in scan.open_debts:
            if debt.authority is not AuthorityClass.C:
                continue
            _assert_fresh_open(debt, scan)
            rule = policy.founder_rule_for(debt.kind)
            if rule is None:
                raise RoutingError(f"unsupported Class C routing debt: {debt.id}")
            if rule.authority is not AuthorityClass.C:
                raise RoutingError(f"authority mismatch for founder debt: {debt.id}")
            raw_target = debt.observed_state.get(rule.decision_target_field)
            try:
                target = normalize_decision_target(raw_target)
            except ValueError as exc:
                raise RoutingError(f"invalid decisionTarget for debt {debt.id}: {exc}") from exc
            groups.setdefault((rule.id, target), []).append(debt)
        decisions: list[FounderDecision] = []
        for (rule_id, target), debts in sorted(groups.items()):
            rule = policy.founder_rules[rule_id]
            ordered = sorted(debts, key=lambda item: item.id)
            decisions.append(FounderDecision.create(
                rule=rule.id, decision_target=target, objective=rule.objective,
                debt_ids=tuple(item.id for item in ordered),
                evidence=tuple(_routing_evidence(item) for item in ordered),
            ))
        return FounderQueue.create(tuple(decisions))

    return _scan_and_persist_routing(root, policy, "founder", controller or StewardController(), build)

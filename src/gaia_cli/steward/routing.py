"""Report-only Class B and Class C Steward routing.

This module deliberately renders policy-bounded artifacts only.  It never
invokes a model, creates a patch/worktree, or changes canonical repository
state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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
from gaia_cli.steward.receipts import make_run_id, write_immutable_receipt


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
    if debt.last_observed_at != scan.receipt.finished_at:
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


def render_dispatch(repo_root: Path, debt_id: str, *, controller: StewardController | None = None) -> RoutingResult:
    """Freshly scan, then render exactly one policy-supported Class B packet."""

    root = repo_root.resolve()
    policy = StewardPolicy.load(root)
    scan = (controller or StewardController()).scan(root)
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

    packet = DispatchPacket.create(
        debt=debt.to_dict(),
        evidence=_routing_evidence(debt),
        authority=debt.authority,
        rule=rule.id,
        routine=rule.routine,
        objective=rule.objective,
        allowed_paths=rule.allowed_paths,
        allowed_commands=rule.allowed_commands,
        forbidden_paths=rule.forbidden_paths,
        stop_conditions=rule.stop_conditions,
        proof=rule.proof,
        budget=policy.routing_budget,
    )
    receipt, receipt_path = _persist(
        root=root, policy=policy, scan=scan, action="dispatch", artifact=packet
    )
    return RoutingResult(scan=scan, artifact=packet, receipt=receipt, receipt_path=receipt_path)


def render_founder_queue(repo_root: Path, *, controller: StewardController | None = None) -> RoutingResult:
    """Freshly scan and render only exact-target Class C governance groups."""

    root = repo_root.resolve()
    policy = StewardPolicy.load(root)
    scan = (controller or StewardController()).scan(root)
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
        decisions.append(
            FounderDecision.create(
                rule=rule.id,
                decision_target=target,
                objective=rule.objective,
                debt_ids=tuple(item.id for item in ordered),
                evidence=tuple(_routing_evidence(item) for item in ordered),
            )
        )
    queue = FounderQueue.create(tuple(decisions))
    receipt, receipt_path = _persist(
        root=root, policy=policy, scan=scan, action="founder", artifact=queue
    )
    return RoutingResult(scan=scan, artifact=queue, receipt=receipt, receipt_path=receipt_path)

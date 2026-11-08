"""Report-only Class B and Class C Steward routing.

This module deliberately renders policy-bounded artifacts only.  It never
invokes a model, creates a patch/worktree, or changes canonical repository
state.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Any, Mapping, Sequence

from gaia_cli.steward.controller import ScanResult, StewardController
from gaia_cli.steward.models import (
    AuthorityClass,
    Debt,
    DispatchPacket,
    FounderDecision,
    FounderQueue,
    normalize_decision_target,
)
from gaia_cli.steward.lane import (
    Lane,
    lane_document,
    load_lane,
    mark_dispatched,
    next_dispatchable,
    reconcile,
    record_verdict,
)
from gaia_cli.steward.calibrationroute import (
    CALIBRATION_ROUTE_DEBT_KIND,
    CALIBRATION_ROUTE_RULE_ID,
    ineligibilityReason,
)
from gaia_cli.steward.policy import WORKFLOW_ROUTE_DEBT_KIND, WORKFLOW_ROUTE_RULE_ID, StewardPolicy
from gaia_cli.steward.receipts import (
    ensure_local_state_path,
    exclusive_scan_lock,
    make_run_id,
    run_id_matches,
    write_immutable_receipt,
)
from gaia_cli.steward.verification import (
    MAX_DIFF_BYTES,
    MAX_TRANSCRIPT_BYTES,
    VerificationError,
    VerificationVerdict,
    calibration_structure_violations,
    workflow_history_check,
    evaluate,
    is_workflow_path,
    parse_proof_transcript,
    checkoutBase,
    parse_unified_diff,
    read_text_input,
)


class RoutingError(RuntimeError):
    """A routing precondition was not proven; no report is rendered."""


class LaneEmpty(RoutingError):
    """The lane has nothing it may hand out. This is a healthy outcome.

    Kept distinct from every other routing failure so callers can tell "Steward
    is idle" from "Steward is broken". A scheduled pickup that treated the two
    alike would either page a human every quiet day or hide a real stall.
    """


@dataclass(frozen=True)
class LaneReport:
    """A rendered view of the rolling lane at one moment."""

    lane: Lane
    next_debt_id: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": "steward-lane-report-v1",
            "lane": self.lane.to_dict(),
            "summary": self.lane.summary(),
            "next": {"debtId": self.next_debt_id, "reason": self.reason},
        }


@dataclass(frozen=True)
class RoutingReceipt:
    """Small immutable audit record for one report-only routing request."""

    run_id: str
    action: str
    scan_receipt_id: str
    artifact: Mapping[str, Any]
    status: str = "reported"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": "steward-routing-receipt-v1",
            "runId": self.run_id,
            "action": self.action,
            "scanReceiptId": self.scan_receipt_id,
            "models": [],
            "repairs": [],
            "result": {"status": self.status},
            "artifact": dict(self.artifact),
        }


@dataclass(frozen=True)
class RoutingResult:
    scan: ScanResult
    artifact: DispatchPacket | FounderQueue | VerificationVerdict | LaneReport
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


def _workflow_baseline(root: Path, paths: tuple[str, ...]) -> dict[str, str | None]:
    """Tracked content at ``HEAD`` of every workflow file a candidate diff touches.

    The structural proof needs the exact bytes the diff was cut against, not the
    working tree (which may already carry the candidate). Verification therefore
    runs from a checkout whose ``HEAD`` is that baseline; a file absent there, or
    content that is not UTF-8, is ``None`` and the edit is rejected as unprovable.
    """

    import subprocess

    baseline: dict[str, str | None] = {}
    for path in paths:
        if not is_workflow_path(path):
            continue
        done = subprocess.run(
            ["git", "-C", str(root), "cat-file", "blob", f"HEAD:{path}"],
            capture_output=True,
            check=False,
        )
        try:
            baseline[path] = done.stdout.decode("utf-8") if done.returncode == 0 else None
        except UnicodeDecodeError:
            baseline[path] = None
    return baseline


def _assert_route_eligible(rule: Any, debt: Debt) -> None:
    """Refuse a packet the route's own contract says it may never carry.

    The workflow-timeout route is the only Steward write into ``.github/``. Its
    envelope was ruled for missing job timeouts alone, so a debt gets that packet
    only when every finding is ``missing-timeout``, the list is complete (not
    capped), the subject is a direct-child, hand-written workflow file, and the
    sensor did not mark it lane-ineligible. Mixed or other findings never obtain
    it, whether the debt came from the lane or from an explicit ``--debt`` request.
    """

    if rule.id == CALIBRATION_ROUTE_RULE_ID or debt.kind == CALIBRATION_ROUTE_DEBT_KIND:
        _assert_calibration_eligible(rule, debt)
        return
    if rule.id != WORKFLOW_ROUTE_RULE_ID and debt.kind != WORKFLOW_ROUTE_DEBT_KIND:
        return
    state = debt.observed_state
    findings = state.get("findings")
    subject = debt.subject.id
    reason = None
    if rule.id != WORKFLOW_ROUTE_RULE_ID or debt.kind != WORKFLOW_ROUTE_DEBT_KIND:
        reason = "the workflow rule and debt kind must be paired"
    elif state.get("laneEligible") is False:
        reason = str(state.get("laneIneligibleReason") or "the sensor marked this debt lane-ineligible")
    elif not isinstance(findings, list) or not findings or state.get("findingsCapped"):
        reason = "the finding list is empty or capped, so every finding cannot be proven to be missing-timeout"
    elif any(not isinstance(item, dict) or item.get("rule") != "missing-timeout" for item in findings):
        reason = "the debt has findings other than missing-timeout; only missing-timeout is repairable by this route"
    elif not (
        subject.startswith(".github/workflows/")
        and subject.endswith(".yml")
        and subject.count("/") == 2
        and not subject.endswith(".lock.yml")
    ):
        reason = "the subject is not a direct-child hand-written .github/workflows/*.yml file"
    if reason is not None:
        raise RoutingError(f"debt {debt.id} is not eligible for rule {rule.id}: {reason}")


def _assert_calibration_eligible(rule: Any, debt: Debt) -> None:
    """Refuse a calibration packet founder ruling F1 does not cover.

    The scan behind a dispatch is fresh, so the finding's own annotations are
    live; ``calibrationroute.ineligibilityReason`` is the one rule the sensor
    and verification apply too. Lane-ineligible findings (a demotion, a frozen
    skill, a recorded prior demotion under F3, cap-only suite evidence to 3★+,
    a refused or unevaluable preflight) stay open and visible for the curator,
    but never obtain a packet, from the lane or from an explicit ``--debt``.
    """

    reason = None
    if rule.id != CALIBRATION_ROUTE_RULE_ID or debt.kind != CALIBRATION_ROUTE_DEBT_KIND:
        reason = "the calibration rule and debt kind must be paired"
    elif debt.observed_state.get("laneEligible") is False:
        reason = str(debt.observed_state.get("laneIneligibleReason") or "the sensor marked this debt lane-ineligible")
    else:
        reason = ineligibilityReason(debt.observed_state, debt.current_state.get("level"))
    if reason is not None:
        raise RoutingError(f"debt {debt.id} is not eligible for rule {rule.id}: {reason}")


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
    artifact: DispatchPacket | FounderQueue | VerificationVerdict | LaneReport,
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
        status=(
            f"verdict:{artifact.verdict}"
            if isinstance(artifact, VerificationVerdict)
            else "reported"
        ),
    )
    path, _created = write_immutable_receipt(
        root / policy.state_directory / policy.receipts_directory,
        receipt,
        repo_root=root,
        state_root=root / policy.state_directory,
    )
    return receipt, path


def _restore_bytes(path: Path, before: bytes | None, *, tag: str) -> None:
    """Atomically put one local-state file back the way this transaction found it."""

    if before is None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return
    fd, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=tag
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(before)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _restore_routing_scan_state(
    scan: ScanResult,
    ledger_before: bytes | None,
    receipts_before: set[Path],
    *,
    lane_path: Path | None = None,
    lane_before: bytes | None = None,
) -> None:
    """Undo scan and lane state if the paired routing receipt cannot be published."""

    _restore_bytes(scan.debt_state_path, ledger_before, tag=".routing-rollback")
    if lane_path is not None:
        _restore_bytes(lane_path, lane_before, tag=".lane-rollback")
    for path in scan.receipt_path.parent.glob("*.json"):
        if path not in receipts_before:
            path.unlink()


def _scan_and_persist_routing(
    root: Path,
    policy: StewardPolicy,
    action: str,
    controller: StewardController,
    build: Any,
    commit: Any = None,
) -> RoutingResult:
    """Make scan, routing receipt, and any lane move one local-state transaction.

    ``commit`` runs after the receipt is published but still under the lock and
    still inside the rollback. That ordering is deliberate: the receipt is the
    audit precondition for a lane move, so a lane must never advance past a
    dispatch that was never recorded.
    """

    state_directory = root / policy.state_directory
    ledger_path = state_directory / "debt.json"
    lane_path = state_directory / LANE_STATE_FILE
    receipts_directory = state_directory / policy.receipts_directory
    lock_directory = state_directory / ".scan.lock"
    for path in (state_directory, ledger_path, lane_path, receipts_directory, lock_directory):
        ensure_local_state_path(root, state_directory, path)
    with exclusive_scan_lock(lock_directory, repo_root=root, state_root=state_directory):
        ledger_before = ledger_path.read_bytes() if ledger_path.exists() else None
        lane_before = lane_path.read_bytes() if lane_path.exists() else None
        receipts_before = set(receipts_directory.glob("*.json")) if receipts_directory.exists() else set()
        scan = controller.scan(root, _lock_held=True)
        try:
            artifact = build(scan)
            receipt, receipt_path = _persist(
                root=root, policy=policy, scan=scan, action=action, artifact=artifact
            )
            if commit is not None:
                commit(scan, artifact)
        except BaseException:
            _restore_routing_scan_state(
                scan,
                ledger_before,
                receipts_before,
                lane_path=lane_path,
                lane_before=lane_before,
            )
            raise
    return RoutingResult(scan=scan, artifact=artifact, receipt=receipt, receipt_path=receipt_path)


LANE_STATE_FILE = "lane.json"

# Escalation out of the rolling lane is not one of the founder rules in policy:
# it is not a question about a debt kind, it is a question about an envelope
# that kept failing. It carries its own identity so a lowered attempt ceiling
# cannot silently re-file every escalation as a different decision.
LANE_ESCALATION_RULE = "lane-escalation"
LANE_ESCALATION_OBJECTIVE = (
    "Bounded repair exhausted its attempt ceiling on this routine. Decide "
    "whether the authority envelope is wrong, whether the finding is a Class C "
    "question in disguise, or whether the routine should be retired. Another "
    "attempt under the same envelope is not one of the options — that is what "
    "the ceiling already ruled out."
)


def _lane_path(root: Path, policy: StewardPolicy) -> Path:
    return root / policy.state_directory / LANE_STATE_FILE


def _read_lane(root: Path, policy: StewardPolicy) -> Lane:
    path = _lane_path(root, policy)
    ensure_local_state_path(root, root / policy.state_directory, path)
    if not path.is_file():
        return load_lane(None, policy.lane)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoutingError(f"cannot read Steward lane state at {path}: {exc}") from exc
    return load_lane(data, policy.lane)


def _write_lane(root: Path, policy: StewardPolicy, lane: Lane) -> None:
    path = _lane_path(root, policy)
    ensure_local_state_path(root, root / policy.state_directory, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        json.dumps(lane_document(lane), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    if path.is_file() and path.read_bytes() == content:
        return
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    ensure_local_state_path(root, root / policy.state_directory, temporary)
    try:
        with temporary.open("xb") as handle:
            handle.write(content)
        os.replace(temporary, path)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise


def _dispatchable_kinds(policy: StewardPolicy) -> dict[str, str]:
    return {rule.debt_kind: rule.id for rule in policy.dispatch_rules.values()}


def _reconciled_lane(root: Path, policy: StewardPolicy, scan: ScanResult) -> Lane:
    """The lane, brought into agreement with what this scan actually observed.

    Only debt this scan saw as drift can hold a live lane slot. A stale ledger
    entry that no sensor confirmed must not occupy capacity that a real finding
    needs — that is how a bounded lane silently becomes a blocked one.
    """

    fresh = tuple(
        debt for debt in scan.open_debts if debt.id in scan.fresh_open_debt_ids
    )
    return reconcile(
        _read_lane(root, policy),
        open_debts=fresh,
        dispatchable_kinds=_dispatchable_kinds(policy),
        now=scan.receipt.finished_at,
    )


def render_lane(repo_root: Path, *, controller: StewardController | None = None) -> RoutingResult:
    """Reconcile the rolling lane against a fresh scan and report it."""

    root = repo_root.resolve()
    policy = StewardPolicy.load(root)
    pending: dict[str, Lane] = {}

    def build(scan: ScanResult) -> LaneReport:
        _assert_known_fresh_scan(scan)
        lane = _reconciled_lane(root, policy, scan)
        pending["lane"] = lane
        entry, reason = next_dispatchable(lane, now=scan.receipt.finished_at)
        return LaneReport(lane=lane, next_debt_id=entry.debt_id if entry else None, reason=reason)

    def commit(_scan: ScanResult, _artifact: object) -> None:
        _write_lane(root, policy, pending["lane"])

    return _scan_and_persist_routing(
        root, policy, "lane", controller or StewardController(), build, commit
    )


def render_lane_next(
    repo_root: Path,
    *,
    controller: StewardController | None = None,
    prompt: bool = False,
) -> tuple[RoutingResult, str | None]:
    """Hand out the next bounded Class B dispatch the lane permits, if any.

    This is the pickup point. It writes the same `dispatch` receipt that
    `gaia steward dispatch` writes, so verification can find the envelope the
    work was authorized under without knowing which command produced it.
    """

    from gaia_cli.steward.prompt import render_tree_keeper_prompt

    root = repo_root.resolve()
    policy = StewardPolicy.load(root)
    pending: dict[str, Any] = {}

    def build(scan: ScanResult) -> DispatchPacket:
        _assert_known_fresh_scan(scan)
        lane = _reconciled_lane(root, policy, scan)
        entry, reason = next_dispatchable(lane, now=scan.receipt.finished_at)
        if entry is None:
            # A lane with nothing to hand out is a healthy lane. It still
            # persists the reconciliation so the reason is auditable.
            _write_lane(root, policy, lane)
            raise LaneEmpty(reason)
        debt = next((item for item in scan.debts if item.id == entry.debt_id), None)
        if debt is None:
            raise RoutingError(f"lane references debt absent from this scan: {entry.debt_id}")
        _assert_fresh_open(debt, scan)
        rule = policy.dispatch_rule_for(debt.kind)
        if rule is None or debt.authority is not AuthorityClass.B or rule.authority is not AuthorityClass.B:
            raise RoutingError(f"lane selected non-Class-B debt: {debt.id}")
        _assert_route_eligible(rule, debt)
        head_commit = None
        if (root / ".git").exists():
            head = subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD^{commit}"],
                cwd=root, capture_output=True, text=True, check=False,
            )
            if head.returncode != 0 or not head.stdout.strip():
                raise RoutingError("cannot determine dispatch HEAD commit")
            head_commit = head.stdout.strip()
        packet = DispatchPacket.create(
            head_commit=head_commit, debt=debt.to_dict(), evidence=_routing_evidence(debt), authority=debt.authority,
            rule=rule.id, routine=rule.routine, objective=rule.objective,
            allowed_paths=rule.allowed_paths, allowed_commands=rule.allowed_commands,
            forbidden_paths=rule.forbidden_paths, stop_conditions=rule.stop_conditions,
            proof=rule.proof, budget=policy.routing_budget, capability=rule.capability,
        )
        pending["lane"] = mark_dispatched(
            lane, entry, dispatch_id=packet.dispatch_id, now=scan.receipt.finished_at
        )
        pending["rule"] = rule
        return packet

    def commit(_scan: ScanResult, _artifact: object) -> None:
        _write_lane(root, policy, pending["lane"])

    result = _scan_and_persist_routing(
        root, policy, "dispatch", controller or StewardController(), build, commit
    )
    if not prompt:
        return result, None
    packet = result.artifact
    assert isinstance(packet, DispatchPacket)
    return result, render_tree_keeper_prompt(
        packet,
        prompt_guide=pending["rule"].prompt_guide,
        receipt=result.receipt.to_dict(),
    )


def record_lane_verdict(
    repo_root: Path,
    debt_id: str,
    verdict: str,
    *,
    note: str = "",
    controller: StewardController | None = None,
) -> RoutingResult:
    """Record an outcome the lane cannot observe for itself.

    ``accept`` only ever arrives here. Steward's own verification is structurally
    incapable of producing one, so closing an entry as accepted is always the
    act of a person or an independent verifier, and the note records who said so.
    """

    root = repo_root.resolve()
    policy = StewardPolicy.load(root)
    pending: dict[str, Lane] = {}

    def build(scan: ScanResult) -> LaneReport:
        _assert_known_fresh_scan(scan)
        lane = _reconciled_lane(root, policy, scan)
        if lane.by_id(debt_id) is None:
            raise RoutingError(f"the lane is not tracking debt {debt_id}")
        updated = record_verdict(lane, debt_id, verdict, now=scan.receipt.finished_at, note=note)
        pending["lane"] = updated
        entry, reason = next_dispatchable(updated, now=scan.receipt.finished_at)
        return LaneReport(
            lane=updated, next_debt_id=entry.debt_id if entry else None, reason=reason
        )

    def commit(_scan: ScanResult, _artifact: object) -> None:
        _write_lane(root, policy, pending["lane"])

    return _scan_and_persist_routing(
        root, policy, "lane", controller or StewardController(), build, commit
    )


def render_dispatch(
    repo_root: Path,
    debt_id: str,
    *,
    controller: StewardController | None = None,
    policy: StewardPolicy | None = None,
) -> RoutingResult:
    """Freshly scan, then render exactly one policy-supported Class B packet.

    A caller that needs the rule behind the packet must pass the same policy
    object it will read, rather than loading the file a second time: two loads
    can straddle an edit and describe the packet with a rule that never
    authorized it.
    """

    root = repo_root.resolve()
    policy = policy if policy is not None else StewardPolicy.load(root)
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
        _assert_route_eligible(rule, debt)
        head_commit = None
        if (root / ".git").exists():
            head = subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD^{commit}"],
                cwd=root, capture_output=True, text=True, check=False,
            )
            if head.returncode != 0 or not head.stdout.strip():
                raise RoutingError("cannot determine dispatch HEAD commit")
            head_commit = head.stdout.strip()
        return DispatchPacket.create(
            head_commit=head_commit, debt=debt.to_dict(), evidence=_routing_evidence(debt), authority=debt.authority,
            rule=rule.id, routine=rule.routine, objective=rule.objective,
            allowed_paths=rule.allowed_paths, allowed_commands=rule.allowed_commands,
            forbidden_paths=rule.forbidden_paths, stop_conditions=rule.stop_conditions,
            proof=rule.proof, budget=policy.routing_budget, capability=rule.capability,
        )

    return _scan_and_persist_routing(root, policy, "dispatch", controller or StewardController(), build)


def render_dispatch_prompt(
    repo_root: Path, debt_id: str, *, controller: StewardController | None = None
) -> tuple[RoutingResult, str]:
    """Render one Class B packet and its harness-neutral Tree Keeper prompt.

    The prompt is a projection of the packet that was just rendered and
    receipted; it introduces no new authority, no new evidence, and no second
    receipt.  Choosing a harness for it stays a human scheduling decision.
    """

    from gaia_cli.steward.prompt import render_tree_keeper_prompt

    root = repo_root.resolve()
    # One load serves both the envelope and its routine pointer.
    policy = StewardPolicy.load(root)
    result = render_dispatch(root, debt_id, controller=controller, policy=policy)
    packet = result.artifact
    if not isinstance(packet, DispatchPacket):
        raise RoutingError("dispatch did not render a Class B packet")
    rule = policy.dispatch_rules.get(packet.rule)
    if rule is None:
        raise RoutingError(f"packet references an unknown dispatch rule: {packet.rule}")
    prompt = render_tree_keeper_prompt(
        packet,
        prompt_guide=rule.prompt_guide,
        receipt=result.receipt.to_dict(),
    )
    return result, prompt


_MAX_RECEIPT_BYTES = 8 * 1024 * 1024


def _read_receipt(path: Path) -> Mapping[str, Any]:
    raw = path.read_bytes()
    if len(raw) > _MAX_RECEIPT_BYTES:
        raise RoutingError(f"Steward receipt exceeds its safety limit: {path.name}")
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoutingError(f"invalid Steward receipt {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise RoutingError(f"Steward receipt must be an object: {path.name}")
    return data


def _dispatch_receipt_for(
    receipts_directory: Path, debt_id: str, dispatch_id: str | None = None
) -> Mapping[str, Any]:
    """Return the most recent dispatch receipt that authorized work on this debt.

    Verification is only meaningful for work Steward actually dispatched. If no
    receipt authorized it, there is no envelope to verify against and the
    request fails closed rather than inventing one.  Receipt ids embed a
    fixed-width timestamp, so lexicographic order is chronological order.
    """

    candidates: list[Mapping[str, Any]] = []
    for path in sorted(receipts_directory.glob("steward-*.json")):
        data = _read_receipt(path)
        if data.get("action") != "dispatch":
            continue
        artifact = data.get("artifact")
        if not isinstance(artifact, dict):
            continue
        debt = artifact.get("debt")
        if not isinstance(debt, dict) or debt.get("id") != debt_id:
            continue
        if dispatch_id is not None and dispatch_id not in (
            data.get("receiptId"), artifact.get("dispatch_id"), artifact.get("dispatchId"), data.get("runId")
        ):
            continue
        # The receipt is the only record of what was authorized, so it has to
        # still attest to itself. Its id is a digest of exactly this payload;
        # an envelope widened after publication no longer hashes to its name.
        if not run_id_matches(
            str(data.get("runId", "")),
            {
                "action": "dispatch",
                "scanReceiptId": data.get("scanReceiptId"),
                "artifact": artifact,
            },
        ):
            raise RoutingError(
                f"dispatch receipt {path.name} no longer matches its own content "
                "hash; it has been edited since publication and is not evidence "
                "of what was authorized"
            )
        candidates.append(data)
    if not candidates:
        if dispatch_id is not None:
            raise RoutingError(f"no dispatch receipt found for dispatch {dispatch_id} (debt {debt_id})")
        raise RoutingError(
            f"no dispatch receipt exists for debt {debt_id}; run "
            f"`gaia steward dispatch {debt_id}` before verifying work against it"
        )
    return max(candidates, key=lambda item: (
        dispatch_id is not None and item.get("receiptId") == dispatch_id,
        str(item.get("runId", "")),
    ))


def _latest_dispatch_receipt(receipts_directory: Path, debt_id: str) -> Mapping[str, Any]:
    return _dispatch_receipt_for(receipts_directory, debt_id)


_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")
_PATH_LINE_PREFIXES = ("--- ", "+++ ", "rename from ", "rename to ", "copy from ", "copy to ")


def _path_safe(path: str) -> bool:
    """A repository-relative path with no traversal, absolute root, .git entry or escape characters."""

    if not path or path.startswith(("/", '"')) or any(c in path for c in ("\\", "\0", "\t", "\r")):
        return False
    parts = path.split("/")
    return all(part not in ("", ".", "..") for part in parts) and ".git" not in parts


def _diff_paths_safe(diff_text: str) -> bool:
    """Path validation for a candidate diff, before anything is applied.

    Every path a header names must be a safe repository-relative path. Unified
    headers may carry the ``a/`` / ``b/`` prefix or name ``/dev/null``; ``diff --git``
    headers must not be quoted, and none of their tokens may traverse or be absolute.
    """

    old_left = new_left = 0
    for line in diff_text.splitlines():
        if old_left > 0 or new_left > 0:
            # Inside a hunk: content lines, never headers (a removed "-- x" line reads "--- x").
            marker = line[:1]
            if marker == " ":
                old_left, new_left = old_left - 1, new_left - 1
            elif marker == "-":
                old_left -= 1
            elif marker == "+":
                new_left -= 1
            elif marker != "\\":
                return False
            if old_left < 0 or new_left < 0:
                return False
            continue
        hunk = _HUNK_HEADER.match(line)
        if hunk:
            old_left = int(hunk.group(1)) if hunk.group(1) is not None else 1
            new_left = int(hunk.group(2)) if hunk.group(2) is not None else 1
            continue
        if line.startswith("diff --git "):
            rest = line[len("diff --git "):]
            if '"' in rest or "\\" in rest:
                return False
            # Same rules as every other header path (a path with spaces splits into
            # tokens, each of which must still be safe), so a mode-only diff naming
            # .git is refused too.
            for token in rest.split(" "):
                if token.startswith(("a/", "b/")):
                    token = token[2:]
                if not _path_safe(token):
                    return False
            continue
        for prefix in _PATH_LINE_PREFIXES:
            if not line.startswith(prefix):
                continue
            path = line[len(prefix):].split("\t", 1)[0]
            if prefix in ("--- ", "+++ "):
                if path == "/dev/null":
                    break
                if path.startswith(("a/", "b/")):
                    path = path[2:]
            if not _path_safe(path):
                return False
            break
    return True


SENSOR_INPUTS_RELATIVE = Path(".gaia/steward/inputs")


class _UnsafeInputPath(Exception):
    """A sensor-input path component is a symlink, not a directory, or escapes its root."""


def _safe_directory(root: Path, relative: Path, *, create: bool) -> Path | None:
    """``root/relative`` with every component checked by lstat, never followed.

    Each component from ``root`` down must be a real directory (not a symlink);
    with ``create`` a missing component is made with ``os.mkdir``, which never
    follows a symlink. The result must resolve under ``root``. Returns None when
    the path is absent (and not created); raises _UnsafeInputPath otherwise.
    """

    base = root.resolve()
    current = base
    for part in relative.parts:
        if part in ("", ".", ".."):
            raise _UnsafeInputPath(f"unsafe component {part!r}")
        current = current / part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            if not create:
                return None
            os.mkdir(current, 0o755)
            info = os.lstat(current)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise _UnsafeInputPath(f"{current} is not a real directory")
    if not current.resolve().is_relative_to(base):
        raise _UnsafeInputPath(f"{current} resolves outside {base}")
    return current


def _mirror_sensor_inputs(repo_root: Path, tree: Path) -> bool:
    """Copy the checkout's ignored sensor inputs into ``tree``, read-only.

    Returns False (the caller fails closed) on any unsafe path: a symlink in any
    component of the source path from the repo root down to every input file,
    a symlink or non-directory in any destination component under the scratch
    tree, a path resolving outside its root, or a destination file that already
    exists. Files are read with O_NOFOLLOW and written with
    O_CREAT|O_EXCL|O_NOFOLLOW, mode 0444. With no inputs directory nothing is
    copied, and both scratch trees stay identical.
    """

    try:
        source = _safe_directory(repo_root, SENSOR_INPUTS_RELATIVE, create=False)
        if source is None:
            return True
        target = _safe_directory(tree, SENSOR_INPUTS_RELATIVE, create=True)
        assert target is not None
        for current, directories, files in os.walk(source, followlinks=False):
            here = Path(current)
            relative = here.relative_to(source)
            for name in directories:
                if stat.S_ISLNK(os.lstat(here / name).st_mode):
                    raise _UnsafeInputPath(f"{here / name} is a symlink")
            destination = _safe_directory(target, relative, create=True) if relative.parts else target
            for name in files:
                entry = here / name
                info = os.lstat(entry)
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                    raise _UnsafeInputPath(f"{entry} is not a regular file")
                reader = os.open(entry, os.O_RDONLY | os.O_NOFOLLOW)
                with os.fdopen(reader, "rb") as stream:
                    payload = stream.read()
                writer = os.open(
                    destination / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444
                )
                with os.fdopen(writer, "wb") as stream:
                    stream.write(payload)
        return True
    except (_UnsafeInputPath, OSError):
        return False


def _not_evaluated_key(receipt: Any) -> frozenset[tuple[str, bool]]:
    """The set of (sensor, input absent) pairs a scan could not evaluate."""

    return frozenset(
        (str(item.get("sensor")), bool(item.get("inputAbsent")))
        for item in (receipt.not_evaluated or ())
    )


def compute_patch_attribution(
    repo_root: Path,
    diff_text: str,
    target_debt_id: str,
    controller: StewardController,
    base_commit: str | None = None,
) -> Sequence[str] | None:
    """Compute which debts were introduced specifically by a candidate patch.

    Creates scratch environments for the base and patched trees, applies the
    candidate diff to the patched tree, scans both, and returns any new debts
    present in the patched tree that were not present in the base tree (excluding
    the target debt being repaired).

    Fails closed (returns None) if the patch fails to apply cleanly or if any
    error occurs during evaluation. Path validation runs first, before any
    scratch directory exists: a diff naming an absolute, ``..``, ``.git`` or
    otherwise unsafe path is refused without touching the filesystem, and the
    apply never uses ``--unsafe-paths``.
    """
    if not _diff_paths_safe(diff_text):
        return None
    scratch_dir = Path(tempfile.mkdtemp(prefix="gaia-steward-attrib-")).resolve()
    base_dir = scratch_dir / "base"
    patched_dir = scratch_dir / "patched"
    worktrees_to_cleanup: list[Path] = []

    is_git = False
    try:
        is_git = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=repo_root, capture_output=True, text=True, check=False,
        ).returncode == 0
        if is_git:
            if base_commit is None:
                return None
            proc = subprocess.run(
                ["git", "rev-parse", "--verify", f"{base_commit}^{{commit}}"],
                cwd=repo_root, capture_output=True, text=True, check=False,
            )
            if proc.returncode != 0 or not proc.stdout.strip():
                return None
            target_commit = proc.stdout.strip()

            wt_base = subprocess.run(
                ["git", "worktree", "add", "--quiet", "--detach", str(base_dir), target_commit],
                cwd=repo_root,
                capture_output=True,
                check=False,
            )
            if wt_base.returncode != 0:
                return None
            worktrees_to_cleanup.append(base_dir)

            wt_patch = subprocess.run(
                ["git", "worktree", "add", "--quiet", "--detach", str(patched_dir), target_commit],
                cwd=repo_root,
                capture_output=True,
                check=False,
            )
            if wt_patch.returncode != 0:
                return None
            worktrees_to_cleanup.append(patched_dir)
            # Detached worktrees lack the ignored sensor inputs, so give both
            # trees the same read-only copy: base and patched then see identical
            # inputs, and their coverage matches the main scan's.
            for tree in (base_dir, patched_dir):
                if not _mirror_sensor_inputs(repo_root, tree):
                    return None
        else:
            # NOT a git repo (e.g. mock test tmp_path)
            def _ignore_patterns(path: str, names: list[str]) -> set[str]:
                ignored = {".git", ".scan.lock", ".pytest_cache", "__pycache__"}
                return {name for name in names if name in ignored}

            shutil.copytree(repo_root, base_dir, symlinks=True, ignore=_ignore_patterns)
            shutil.copytree(base_dir, patched_dir, symlinks=True)

        diff_file = scratch_dir / "patch.diff"
        diff_file.write_text(diff_text, encoding="utf-8")
        apply_proc = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", str(diff_file)],
            cwd=patched_dir,
            capture_output=True,
            check=False,
        )
        if apply_proc.returncode != 0:
            return None

        # Scan base directory with controller
        base_scan = controller.scan(base_dir)
        # Scan patched directory with controller
        patched_scan = controller.scan(patched_dir)

        # Fail closed on unknown or partial coverage, or when the two scans were
        # blind in different places. A sensor that is not evaluated in BOTH scans
        # (identically, e.g. an optional input that is absent) is a symmetric blind
        # spot: it can neither add nor hide a difference between base and patch.
        if any(
            receipt.coverage_unknown or receipt.partial_coverage
            for receipt in (base_scan.receipt, patched_scan.receipt)
        ):
            return None
        if _not_evaluated_key(base_scan.receipt) != _not_evaluated_key(patched_scan.receipt):
            return None

        base_debts = {debt.id for debt in base_scan.open_debts}
        patched_debts = {debt.id for debt in patched_scan.open_debts}

        # Extract introduced debts
        introduced_debts = tuple(
            sorted(set(patched_debts) - set(base_debts) - {target_debt_id})
        )
        return introduced_debts
    except Exception:
        return None
    finally:
        for wt in worktrees_to_cleanup:
            try:
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(wt)],
                    cwd=repo_root,
                    capture_output=True,
                    check=False,
                )
            except Exception:
                pass
        if is_git:
            try:
                subprocess.run(
                    ["git", "worktree", "prune"],
                    cwd=repo_root,
                    capture_output=True,
                    check=False,
                )
            except Exception:
                pass
        shutil.rmtree(scratch_dir, ignore_errors=True)


_FULL_SHA_LENGTHS = (40, 64)
_MIN_ABBREV = 7


def _diff_preimages(diff_text: str) -> list[tuple[str, str, bool]] | None:
    """Return (path, abbreviated pre-image blob, is_new) for every file in a git diff.

    Returns None when any file block cannot be authenticated: no `diff --git`
    header, no `index` line (mode-only or pure-rename blocks), a quoted or
    missing path, or an abbreviated hash too short to bind a blob.
    """

    blocks: list[list[str]] = []
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            blocks.append([line])
        elif blocks:
            blocks[-1].append(line)
        elif line.startswith(("--- ", "+++ ", "@@")):
            return None  # hunks without a git header carry no before-image hash
    if not blocks:
        return None
    result: list[tuple[str, str, bool]] = []
    for block in blocks:
        index = old_path = new_path = rename_from = None
        new_file = False
        for line in block[1:]:
            if line.startswith(("@@", "Binary files ")):
                break
            if line.startswith("index "):
                index = line[len("index "):].split(" ")[0]
            elif line.startswith("new file mode"):
                new_file = True
            elif line.startswith("rename from "):
                rename_from = line[len("rename from "):]
            elif line.startswith("--- "):
                old_path = line[len("--- "):]
            elif line.startswith("+++ "):
                new_path = line[len("+++ "):]
        if index is None or ".." not in index:
            return None
        pre = index.split("..", 1)[0]
        if len(pre) < _MIN_ABBREV or any(c not in "0123456789abcdef" for c in pre):
            return None
        absent = set(pre) == {"0"}
        if absent != new_file:
            return None
        if new_file:
            if new_path is None or not new_path.startswith("b/"):
                return None
            path = new_path[2:]
        elif rename_from is not None:
            path = rename_from
        else:
            if old_path is None or not old_path.startswith("a/"):
                return None
            path = old_path[2:]
        if not path or path.startswith('"') or "\t" in path:
            return None
        result.append((path, pre, new_file))
    return result


def authenticate_runner_baseline(
    repo_root: Path, commit: str | None, branch_ref: str | None, diff_text: str
) -> tuple[str | None, str]:
    """Authenticate a runner-recorded integration head as a patch attribution base.

    Legacy dispatch receipts predate `headCommit`, so the only historical base
    is the integration head the Steward runner itself recorded for the run that
    dispatched the work. It is accepted only when all of these hold, else the
    caller fails closed:

    1. it is a full commit id that resolves to itself in this repository;
    2. it is an ancestor of (or equal to) the recorded integration branch ref,
       so it is real branch history rather than an arbitrary commit;
    3. every file in the stored candidate diff names its before-image blob,
       and that blob is exactly the file at this commit (a created file must
       be absent there).

    Returns (commit, note) on success and (None, reason) on failure.
    """

    if not commit or len(commit) not in _FULL_SHA_LENGTHS or any(
        c not in "0123456789abcdef" for c in commit
    ):
        return None, f"runner-recorded integration head is not a full commit id: {commit!r}"
    if not branch_ref:
        return None, "no recorded integration branch to authenticate the runner baseline against"

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=repo_root, capture_output=True, text=True, check=False
        )

    resolved = git("rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}")
    if resolved.returncode != 0 or resolved.stdout.strip() != commit:
        return None, f"runner-recorded integration head {commit} does not resolve in this repository"
    branch = git("rev-parse", "--verify", "--quiet", f"{branch_ref}^{{commit}}")
    if branch.returncode != 0 or not branch.stdout.strip():
        return None, f"recorded integration branch {branch_ref} does not resolve"
    if git("merge-base", "--is-ancestor", commit, branch.stdout.strip()).returncode != 0:
        return None, f"runner-recorded integration head {commit} is not an ancestor of {branch_ref}"
    preimages = _diff_preimages(diff_text)
    if preimages is None:
        return None, "stored diff does not name a before-image blob for every file"
    for path, pre, is_new in preimages:
        if is_new:
            if git("cat-file", "-e", f"{commit}:{path}").returncode == 0:
                return None, f"stored diff creates {path}, which already exists at {commit}"
            continue
        blob = git("rev-parse", "--verify", "--quiet", f"{commit}:{path}")
        if blob.returncode != 0 or not blob.stdout.strip().startswith(pre):
            return None, f"before-image of {path} in the stored diff does not match {commit}"
    return commit, (
        f"attribution base {commit}: runner-recorded integration head, ancestor of "
        f"{branch_ref}, before-images match the stored diff"
    )


def render_verification(
    repo_root: Path,
    debt_id: str,
    *,
    diff_path: Path,
    proof_path: Path,
    controller: StewardController | None = None,
    base_commit: str | None = None,
    dispatch_id: str | None = None,
    runner_baseline: Mapping[str, str | None] | None = None,
) -> tuple[RoutingResult, str, Mapping[int, tuple[str, ...]]]:
    """Verify one dispatched Class B patch against the envelope that authorized it.

    The packet is restored from its dispatch receipt rather than re-rendered.
    A packet re-derived from today's policy would quietly hold the builder to
    an envelope that did not exist when the work was commissioned.
    """

    root = repo_root.resolve()
    policy = StewardPolicy.load(root)
    receipts_directory = root / policy.state_directory / policy.receipts_directory
    dispatch_receipt = _dispatch_receipt_for(receipts_directory, debt_id, dispatch_id)
    try:
        packet = DispatchPacket.from_dict(dispatch_receipt["artifact"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RoutingError(f"unusable dispatch receipt for debt {debt_id}: {exc}") from exc

    baseline_receipt_path = receipts_directory / f"{dispatch_receipt.get('scanReceiptId')}.json"
    if not baseline_receipt_path.is_file():
        raise RoutingError(
            "the scan receipt behind this dispatch is missing; new debt cannot be "
            "distinguished from pre-existing debt"
        )
        # Failing closed here is deliberate: without the baseline, "new debt
        # appeared" would silently become "all debt is new".
    baseline_receipt = _read_receipt(baseline_receipt_path)
    baseline_open = baseline_receipt.get("openDebt")
    if not isinstance(baseline_open, list):
        raise RoutingError("the scan receipt behind this dispatch records no open debt set")

    # Only a field inside the digest-verified payload can name a baseline. The
    # receipt id hashes action, scanReceiptId and artifact; anything else at the
    # top level could be added after publication without breaking the digest,
    # so its presence is treated as tampering, not as a hint.
    for field in ("headCommit", "gitHead"):
        if field in dispatch_receipt:
            raise RoutingError(
                f"dispatch receipt for debt {debt_id} carries a top-level {field}, which its "
                "content hash does not cover; refusing an unauthenticated baseline"
            )
    if "gitHead" in dispatch_receipt["artifact"]:
        raise RoutingError(
            f"dispatch receipt for debt {debt_id} carries artifact.gitHead, which is not a "
            "dispatch packet field; refusing an ambiguous baseline"
        )
    receipt_base_commit = packet.head_commit
    if receipt_base_commit is not None and (
        not isinstance(receipt_base_commit, str)
        or len(receipt_base_commit) not in _FULL_SHA_LENGTHS
        or any(c not in "0123456789abcdef" for c in receipt_base_commit)
    ):
        raise RoutingError(
            f"dispatch receipt for debt {debt_id} records a headCommit that is not a full commit id"
        )
    if base_commit and receipt_base_commit and base_commit != receipt_base_commit:
        raise RoutingError("supplied base_commit does not match authenticated dispatch receipt base")
    # A caller-supplied commit is never trusted as a baseline. The dispatch
    # receipt's own headCommit is authoritative (it is inside the hashed
    # payload). A legacy receipt without one may use only the runner-recorded
    # integration head, and only once authenticate_runner_baseline() proves it
    # is branch history whose before-images match the stored diff. Anything
    # else leaves no base, so compute_patch_attribution fails closed.
    resolved_base_commit = receipt_base_commit

    diff_text = read_text_input(diff_path, label="candidate diff", limit=MAX_DIFF_BYTES)
    baseline_note: str | None = None
    if resolved_base_commit is None and runner_baseline is not None:
        resolved_base_commit, baseline_note = authenticate_runner_baseline(
            root,
            runner_baseline.get("commit"),
            runner_baseline.get("branchRef"),
            diff_text,
        )
        if resolved_base_commit is None:
            baseline_note = "runner baseline rejected: " + baseline_note
    transcript_text = read_text_input(
        proof_path, label="proof transcript", limit=MAX_TRANSCRIPT_BYTES
    )
    change_set = parse_unified_diff(diff_text, base=checkoutBase(root))
    workflow_baseline = _workflow_baseline(root, change_set.paths)
    transcript = parse_proof_transcript(
        transcript_text, proof_contract_length=len(packet.proof)
    )

    active_controller = controller or StewardController()
    sensor_sources = tuple(sensor.id for sensor in active_controller.sensors)
    pending: dict[str, Lane] = {}

    def build(scan: ScanResult) -> VerificationVerdict:
        _assert_known_fresh_scan(scan)
        rule = policy.dispatch_rule_for(str(packet.debt.get("kind")))
        still_class_b = (
            policy.authority.get(str(packet.debt.get("kind"))) is AuthorityClass.B
            and rule is not None
            and rule.id == packet.rule
        )
        common: dict[str, Any] = {
            "packet": packet,
            "change_set": change_set,
            "transcript": transcript,
            "debt_source": str(packet.debt.get("source")),
            "sensor_sources": sensor_sources,
            "baseline_open_debt": [str(item) for item in baseline_open],
            "current_open_debt": [debt.id for debt in scan.open_debts],
            "authority_still_class_b": still_class_b,
            "workflow_baseline": workflow_baseline,
            "calibration_violations": calibration_structure_violations(root, packet, change_set),
            "history_check": workflow_history_check(packet, transcript_text),
        }
        # Scope is a pure function of the diff and the envelope, so it is decided
        # before anything is applied. An out-of-scope change set is never handed to
        # attribution: nothing from it is written anywhere, even in scratch.
        unattributed = evaluate(**common, patch_introduced_debt=None, attribution_failed=False)
        if not unattributed.scope_valid:
            return dataclasses.replace(
                unattributed,
                reasons=unattributed.reasons
                + ("patch attribution not run: the change set is out of scope",),
            )
        patch_introduced_debt = compute_patch_attribution(
            repo_root=root,
            diff_text=diff_text,
            target_debt_id=str(packet.debt.get("id")),
            controller=active_controller,
            base_commit=resolved_base_commit,
        )
        attribution_failed = patch_introduced_debt is None
        verdict = evaluate(
            **common, patch_introduced_debt=patch_introduced_debt, attribution_failed=attribution_failed
        )
        if baseline_note:
            verdict = dataclasses.replace(verdict, reasons=verdict.reasons + (baseline_note,))
        return verdict

    def commit(scan: ScanResult, artifact: object) -> None:
        # The lane rolls forward off real verification outcomes, not off manual
        # bookkeeping. A lane advanced by hand would drift from the receipts.
        if not isinstance(artifact, VerificationVerdict):
            return
        lane = _reconciled_lane(root, policy, scan)
        if lane.by_id(debt_id) is None or lane.by_id(debt_id).state != "dispatched":
            _write_lane(root, policy, lane)
            return
        _write_lane(
            root,
            policy,
            record_verdict(
                lane,
                debt_id,
                artifact.verdict,
                now=scan.receipt.finished_at,
                note=f"receipt {artifact.dispatch_id}",
            ),
        )

    result = _scan_and_persist_routing(
        root, policy, "verify", active_controller, build, commit
    )
    return result, diff_text, transcript.outputs


def render_verifier_prompt_for(
    repo_root: Path,
    debt_id: str,
    *,
    diff_path: Path,
    proof_path: Path,
    controller: StewardController | None = None,
    base_commit: str | None = None,
    dispatch_id: str | None = None,
) -> tuple[RoutingResult, str]:
    """Verify mechanically, then render a judgment prompt only if one is needed."""

    from gaia_cli.steward.prompt import render_verifier_prompt

    root = repo_root.resolve()
    policy = StewardPolicy.load(root)
    result, diff_text, proof_outputs = render_verification(
        root,
        debt_id,
        diff_path=diff_path,
        proof_path=proof_path,
        controller=controller,
        base_commit=base_commit,
        dispatch_id=dispatch_id,
    )
    verdict = result.artifact
    if not isinstance(verdict, VerificationVerdict):
        raise RoutingError("verification did not render a verdict")
    if verdict.decided:
        raise VerificationError(
            f"machinery already reached {verdict.verdict!r}; no independent judgment "
            "is required and none should be paid for. Reasons: "
            + "; ".join(verdict.reasons)
        )
    dispatch_receipt = _dispatch_receipt_for(
        root / policy.state_directory / policy.receipts_directory, debt_id, dispatch_id
    )
    packet = DispatchPacket.from_dict(dispatch_receipt["artifact"])
    rule = policy.dispatch_rules.get(packet.rule)
    if rule is None:
        raise RoutingError(f"packet references an unknown dispatch rule: {packet.rule}")
    prompt = render_verifier_prompt(
        packet,
        verdict,
        prompt_guide=rule.prompt_guide,
        diff_text=diff_text,
        proof_outputs=proof_outputs,
        receipt=result.receipt.to_dict(),
    )
    return result, prompt


def render_founder_queue(repo_root: Path, *, controller: StewardController | None = None) -> RoutingResult:
    """Freshly scan and render only exact-target Class C governance groups."""

    root = repo_root.resolve()
    policy = StewardPolicy.load(root)
    def build(scan: ScanResult) -> FounderQueue:
        _assert_known_fresh_scan(scan)
        groups: dict[tuple[str, str], list[Debt]] = {}
        # Debt the rolling lane gave up on belongs here. Exhausting the attempt
        # ceiling is exactly the permitted B → C downgrade: bounded repair kept
        # failing, so the envelope — not the attempt — is the likelier defect,
        # and an envelope is a governance question. The reverse never happens;
        # nothing in this file can promote a founder matter back into the lane.
        escalated = {
            entry.debt_id: entry
            for entry in _reconciled_lane(root, policy, scan).escalated
        }
        for debt in scan.open_debts:
            if debt.id in escalated and debt.id in scan.fresh_open_debt_ids:
                # Grouped by the routine whose envelope kept failing, because
                # that is the shared decision: one ruling on one envelope can
                # unblock every debt that routine gave up on.
                groups.setdefault(
                    (LANE_ESCALATION_RULE, f"lane-escalation/{escalated[debt.id].rule}"), []
                ).append(debt)
                continue
            if debt.authority is not AuthorityClass.C:
                continue
            # Founder output is a current governance queue, not a historical
            # debt ledger.  A condition absent from this scan is not a decision
            # question, even if an older local ledger entry remains open.
            if debt.id not in scan.fresh_open_debt_ids:
                continue
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
            objective = (
                LANE_ESCALATION_OBJECTIVE
                if rule_id == LANE_ESCALATION_RULE
                else policy.founder_rules[rule_id].objective
            )
            ordered = sorted(debts, key=lambda item: item.id)
            decisions.append(FounderDecision.create(
                rule=rule_id, decision_target=target, objective=objective,
                debt_ids=tuple(item.id for item in ordered),
                evidence=tuple(_routing_evidence(item) for item in ordered),
            ))
        return FounderQueue.create(tuple(decisions))

    return _scan_and_persist_routing(root, policy, "founder", controller or StewardController(), build)


def render_founder_digest(
    repo_root: Path, *, controller: StewardController | None = None
) -> tuple[RoutingResult, str]:
    """Render the founder queue as the digest a person actually reads.

    The digest is a pure projection of the queue that was just rendered and
    receipted. It introduces no new evidence, writes no second receipt, and
    spends nothing.
    """

    from gaia_cli.steward.desk import classify_decision_records, load_decision_records
    from gaia_cli.steward.digest import render_founder_digest as _render

    root = repo_root.resolve()
    policy = StewardPolicy.load(root)
    result = render_founder_queue(root, controller=controller)
    queue = result.artifact
    if not isinstance(queue, FounderQueue):
        raise RoutingError("founder routing did not render a queue")
    records = classify_decision_records(load_decision_records(root))
    return result, _render(result.scan, queue, _read_lane(root, policy), records)

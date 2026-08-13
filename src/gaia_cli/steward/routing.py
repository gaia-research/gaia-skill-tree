"""Report-only Class B and Class C Steward routing.

This module deliberately renders policy-bounded artifacts only.  It never
invokes a model, creates a patch/worktree, or changes canonical repository
state.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
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
from gaia_cli.steward.lane import (
    Lane,
    LaneError,
    lane_document,
    load_lane,
    mark_dispatched,
    next_dispatchable,
    reconcile,
    record_verdict,
)
from gaia_cli.steward.policy import StewardPolicy
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
    evaluate,
    parse_proof_transcript,
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
        packet = DispatchPacket.create(
            debt=debt.to_dict(), evidence=_routing_evidence(debt), authority=debt.authority,
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
        return DispatchPacket.create(
            debt=debt.to_dict(), evidence=_routing_evidence(debt), authority=debt.authority,
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


def _latest_dispatch_receipt(receipts_directory: Path, debt_id: str) -> Mapping[str, Any]:
    """Return the most recent dispatch receipt that authorized work on this debt.

    Verification is only meaningful for work Steward actually dispatched. If no
    receipt authorized it, there is no envelope to verify against and the
    request fails closed rather than inventing one.  Receipt ids embed a
    fixed-width timestamp, so lexicographic order is chronological order.
    """

    if not receipts_directory.is_dir():
        raise RoutingError(f"no dispatch receipt exists for debt {debt_id}")
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
        raise RoutingError(
            f"no dispatch receipt exists for debt {debt_id}; run "
            f"`gaia steward dispatch {debt_id}` before verifying work against it"
        )
    return max(candidates, key=lambda item: str(item.get("runId", "")))


def render_verification(
    repo_root: Path,
    debt_id: str,
    *,
    diff_path: Path,
    proof_path: Path,
    controller: StewardController | None = None,
) -> tuple[RoutingResult, str, Mapping[int, tuple[str, ...]]]:
    """Verify one dispatched Class B patch against the envelope that authorized it.

    The packet is restored from its dispatch receipt rather than re-rendered.
    A packet re-derived from today's policy would quietly hold the builder to
    an envelope that did not exist when the work was commissioned.
    """

    root = repo_root.resolve()
    policy = StewardPolicy.load(root)
    receipts_directory = root / policy.state_directory / policy.receipts_directory
    dispatch_receipt = _latest_dispatch_receipt(receipts_directory, debt_id)
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
    baseline_open = _read_receipt(baseline_receipt_path).get("openDebt")
    if not isinstance(baseline_open, list):
        raise RoutingError("the scan receipt behind this dispatch records no open debt set")

    diff_text = read_text_input(diff_path, label="candidate diff", limit=MAX_DIFF_BYTES)
    transcript_text = read_text_input(
        proof_path, label="proof transcript", limit=MAX_TRANSCRIPT_BYTES
    )
    change_set = parse_unified_diff(diff_text)
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
        return evaluate(
            packet=packet,
            change_set=change_set,
            transcript=transcript,
            debt_source=str(packet.debt.get("source")),
            sensor_sources=sensor_sources,
            baseline_open_debt=[str(item) for item in baseline_open],
            current_open_debt=[debt.id for debt in scan.open_debts],
            authority_still_class_b=still_class_b,
        )

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
) -> tuple[RoutingResult, str]:
    """Verify mechanically, then render a judgment prompt only if one is needed."""

    from gaia_cli.steward.prompt import render_verifier_prompt

    root = repo_root.resolve()
    policy = StewardPolicy.load(root)
    result, diff_text, proof_outputs = render_verification(
        root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller
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
    dispatch_receipt = _latest_dispatch_receipt(
        root / policy.state_directory / policy.receipts_directory, debt_id
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

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
    artifact: DispatchPacket | FounderQueue | VerificationVerdict
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
    artifact: DispatchPacket | FounderQueue | VerificationVerdict,
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

    result = _scan_and_persist_routing(root, policy, "verify", active_controller, build)
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
        for debt in scan.open_debts:
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
            rule = policy.founder_rules[rule_id]
            ordered = sorted(debts, key=lambda item: item.id)
            decisions.append(FounderDecision.create(
                rule=rule.id, decision_target=target, objective=rule.objective,
                debt_ids=tuple(item.id for item in ordered),
                evidence=tuple(_routing_evidence(item) for item in ordered),
            ))
        return FounderQueue.create(tuple(decisions))

    return _scan_and_persist_routing(root, policy, "founder", controller or StewardController(), build)

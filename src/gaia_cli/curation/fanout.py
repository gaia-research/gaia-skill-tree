"""Bounded model-neutral callable fanout for frozen Lane C inventories.

``maxTasks`` counts candidate tasks admitted for dispatch; ``maxAttempts`` is
per admitted candidate, so the maximum number of callable invocations is their
product. Retries are limited to worker exceptions/non-mapping returns: a
receipt that fails deterministic binding/packet validation is not retried.
Exactly one valid terminal receipt suppresses dispatch, including a semantic
DEFER. ``retryDeferred=True`` explicitly reopens those decisions; invalid/missing
attempts are retried normally. ``timeoutSeconds`` is one run wall-clock budget,
not a fresh allowance per future. Threads cannot forcibly stop running callables.
Workers must be side-effect-free or own isolated per-attempt output locations:
only completed immutable packet/assessment snapshots enter reconciliation, but
worker-side effects cannot be cancelled by this scheduler.
"""
from __future__ import annotations

import concurrent.futures
import copy
import hashlib
import math
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from .reconciliation import _safe_packet_bytes, reconcileInventory


def shardFor(candidateId: str, shardCount: int) -> int:
    """Return a stable shard number independent of inventory/order/completion."""
    if not isinstance(shardCount, int) or shardCount < 1:
        raise ValueError("shardCount must be a positive integer")
    return int(hashlib.sha256(candidateId.encode("utf-8")).hexdigest(), 16) % shardCount


def _snapshot(receipt: Mapping[str, Any], packetRoot: str) -> dict[str, Any]:
    """Capture the ACTUAL artifact bytes a receipt refers to.

    A plain DEFER receipt may legitimately have no assessment: it asserts no
    reviewed decision. Forcing an assessment there would pressure fabrication,
    so assessment bytes are captured only when the receipt actually points at
    one. Every other outcome still requires assessment bytes, and the
    reconciliation contract rejects a receipt whose digest does not match.
    """
    captured = copy.deepcopy(dict(receipt))
    captured["packetBytes"] = bytes(_safe_packet_bytes(captured, Path(packetRoot)))
    has_assessment = ("assessmentBytes" in captured
                      or isinstance(captured.get("assessment"), Mapping)
                      or bool(captured.get("assessmentPath")))
    if has_assessment and "assessmentBytes" not in captured and not isinstance(captured.get("assessment"), Mapping):
        captured["assessmentBytes"] = bytes(_safe_packet_bytes({"packetPath": captured.get("assessmentPath")}, Path(packetRoot)))
    return captured


def runFanout(envelope: Mapping[str, Any], worker: Callable[[Mapping[str, Any], int], Mapping[str, Any]] | None, *, maxWorkers: int = 4, maxAttempts: int = 2, maxTasks: int | None = None, timeoutSeconds: float | None = None, priorReceipts: Iterable[Mapping[str, Any]] = (), packetRoot: str = ".", retryDeferred: bool = False) -> dict[str, Any]:
    """Dispatch bounded frozen tasks; retain errors and immutable receipt copies."""
    if (not isinstance(maxWorkers, int) or maxWorkers < 1 or not isinstance(maxAttempts, int)
            or maxAttempts < 1 or (maxTasks is not None and (not isinstance(maxTasks, int) or maxTasks < 0))):
        raise ValueError("worker, attempt, and task bounds must be positive (maxTasks may be zero)")
    if timeoutSeconds is not None and (isinstance(timeoutSeconds, bool) or not isinstance(timeoutSeconds, (int, float)) or not math.isfinite(timeoutSeconds) or timeoutSeconds <= 0):
        raise ValueError("timeoutSeconds must be a positive finite wall-clock budget")
    deadline = time.monotonic() + timeoutSeconds if timeoutSeconds is not None else None
    envelope = copy.deepcopy(dict(envelope))
    reconcileInventory(envelope, [], packetRoot=packetRoot)  # Validate before dispatch.
    rows = list(envelope.get("candidates", []))
    known_ids = {row["candidateId"] for row in rows}
    supplied_prior = [copy.deepcopy(dict(r)) for r in priorReceipts if isinstance(r, Mapping)]
    prior_errors: dict[str, str] = {}
    snapshots = []
    for prior in supplied_prior:
        cid = prior.get("candidateId")
        if not isinstance(cid, str) or cid not in known_ids:
            snapshots.append(prior)
            continue
        try:
            snapshots.append(_snapshot(prior, packetRoot))
        except Exception as exc:
            prior_errors[cid] = f"invalid prior artifacts: {type(exc).__name__}: {exc}"
    supplied_prior = snapshots
    prior_report = reconcileInventory(envelope, supplied_prior, packetRoot=packetRoot)
    prior_valid = {row["candidateId"] for row in prior_report["decisions"]
                   if row.get("receiptValid") is True and (not retryDeferred or row["outcome"] != "deferred")}
    # A stale/invalid/reopened attempt must not compete with its replacement.
    # Unknown prior rows remain visible in the final reconciliation diagnostics.
    receipts = [r for r in supplied_prior if not isinstance(r.get("candidateId"), str) or r["candidateId"] in prior_valid or r["candidateId"] not in known_ids]
    errors: dict[str, str] = {}
    pending = [row for row in rows if row.get("candidateId") not in prior_valid]
    pending.sort(key=lambda row: (shardFor(row["candidateId"], max(1, len(rows))), row["candidateId"]))
    if worker is None:
        for row in pending:
            errors[row["candidateId"]] = "worker unavailable"
        return {"receipts": receipts, "errors": dict(sorted(errors.items())), "dispatched": 0,
                "attemptBudget": 0, "budgetUnit": "candidate-tasks", "priorReceiptErrors": prior_errors, "shards": {r["candidateId"]: shardFor(r["candidateId"], max(1, len(rows))) for r in rows}}
    selected = pending if maxTasks is None else pending[:maxTasks]
    for row in pending[len(selected):]:
        errors[row["candidateId"]] = "dispatch budget exhausted (maxTasks counts candidate tasks)"

    def invoke(row: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        last_error = "worker failed"
        for attempt in range(1, maxAttempts + 1):
            if deadline is not None and time.monotonic() >= deadline:
                return None, "run wall-clock budget exhausted"
            try:
                returned = worker(copy.deepcopy(dict(row)), attempt)
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                continue
            if not isinstance(returned, Mapping):
                last_error = "worker returned a non-mapping receipt"
                continue
            try:
                captured = copy.deepcopy(dict(returned))
                expected = {"candidateId": row["candidateId"], "taskId": row["taskId"],
                            "attempt": attempt, "inputDigest": row["inputDigest"]}
                if any(captured.get(key) != value for key, value in expected.items()):
                    return None, "worker receipt task/attempt/input binding mismatch"
                captured = _snapshot(captured, packetRoot)
                check = reconcileInventory(envelope, [captured], packetRoot=packetRoot)
                decision = next(d for d in check["decisions"] if d["candidateId"] == row["candidateId"])
                pending_duplicate = (captured.get("outcome") == "proven-duplicate"
                                     and decision.get("reason") == "duplicate target is not a surviving accounted candidate")
                if decision.get("receiptValid") is not True and not pending_duplicate:
                    # Binding failures are deterministic. A source-proven duplicate
                    # waits for final all-worker reconciliation to establish survival.
                    return None, decision.get("reason") or "receipt validation failed"
                if deadline is not None and time.monotonic() > deadline:
                    return None, "run wall-clock budget exhausted; late result discarded"
                return captured, None
            except Exception as exc:
                return None, f"invalid receipt: {type(exc).__name__}: {exc}"
        return None, last_error

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=maxWorkers)
    futures = {executor.submit(invoke, row): row for row in selected}
    try:
        for future, row in list(futures.items()):
            cid = row["candidateId"]
            try:
                remaining = max(0.0, deadline - time.monotonic()) if deadline is not None else None
                receipt, error = future.result(timeout=remaining)
                if receipt is None:
                    errors[cid] = error or "worker failed"
                else:
                    receipts.append(copy.deepcopy(receipt))
            except concurrent.futures.TimeoutError:
                future.cancel()
                errors[cid] = "worker timeout (callable may continue; late result is discarded)"
            except Exception as exc:
                errors[cid] = f"{type(exc).__name__}: {exc}"
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    receipts.sort(key=lambda r: (str(r.get("candidateId")), str(r.get("attempt", ""))))
    return {"receipts": receipts, "errors": dict(sorted(errors.items())), "dispatched": len(selected),
            "attemptBudget": len(selected) * maxAttempts, "budgetUnit": "candidate-tasks", "priorReceiptErrors": prior_errors,
            "shards": {r["candidateId"]: shardFor(r["candidateId"], max(1, len(rows))) for r in rows}}


def reconcileFanout(envelope: Mapping[str, Any], fanoutResult: Mapping[str, Any], *, packetRoot: str = ".", genericDefinitions: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Reconcile receipts and convert otherwise-lost fanout errors to DEFER reasons."""
    report = reconcileInventory(envelope, fanoutResult.get("receipts", ()), packetRoot=packetRoot, genericDefinitions=genericDefinitions)
    report["priorReceiptErrors"] = copy.deepcopy(fanoutResult.get("priorReceiptErrors", {}))
    errors = fanoutResult.get("errors", {})
    if isinstance(errors, Mapping):
        for decision in report["decisions"]:
            if decision["outcome"] == "deferred" and decision["candidateId"] in errors:
                decision["reason"] = str(errors[decision["candidateId"]])
    return report

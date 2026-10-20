"""Bounded model-neutral callable fanout for frozen Lane C inventories.

``maxTasks`` counts candidate tasks admitted for dispatch; ``maxAttempts`` is
per admitted candidate, so the maximum number of callable invocations is their
product. Retries are limited to worker exceptions/non-mapping returns: a
receipt that fails deterministic binding/packet validation is not retried.
Prior receipts suppress dispatch only when exactly one valid, non-deferred
receipt exists. Threads cannot forcibly stop a timed-out callable. Workers must
cooperate with timeout/cancellation; late worker effects are isolated because
only completed immutable receipt snapshots are captured, and timed-out futures
are never read into the reconciliation result.
"""
from __future__ import annotations

import concurrent.futures
import copy
import hashlib
from typing import Any, Callable, Iterable, Mapping

from .reconciliation import canonicalJson, reconcileInventory


def shardFor(candidateId: str, shardCount: int) -> int:
    """Return a stable shard number independent of inventory/order/completion."""
    if not isinstance(shardCount, int) or shardCount < 1:
        raise ValueError("shardCount must be a positive integer")
    return int(hashlib.sha256(candidateId.encode("utf-8")).hexdigest(), 16) % shardCount


def _is_valid_prior(envelope: Mapping[str, Any], receipt: Mapping[str, Any], packetRoot: str) -> bool:
    cid = receipt.get("candidateId")
    try:
        probe = reconcileInventory(envelope, [receipt], packetRoot=packetRoot)
        row = next(item for item in probe["decisions"] if item["candidateId"] == cid)
        return row.get("receiptValid") is True
    except (ValueError, StopIteration):
        return False


def runFanout(envelope: Mapping[str, Any], worker: Callable[[Mapping[str, Any], int], Mapping[str, Any]] | None, *, maxWorkers: int = 4, maxAttempts: int = 2, maxTasks: int | None = None, timeoutSeconds: float | None = None, priorReceipts: Iterable[Mapping[str, Any]] = (), packetRoot: str = ".") -> dict[str, Any]:
    """Dispatch bounded frozen tasks; retain errors and immutable receipt copies."""
    if (not isinstance(maxWorkers, int) or maxWorkers < 1 or not isinstance(maxAttempts, int)
            or maxAttempts < 1 or (maxTasks is not None and (not isinstance(maxTasks, int) or maxTasks < 0))):
        raise ValueError("worker, attempt, and task bounds must be positive (maxTasks may be zero)")
    rows = list(envelope.get("candidates", []))
    supplied_prior = [copy.deepcopy(dict(r)) for r in priorReceipts if isinstance(r, Mapping)]
    prior_counts: dict[Any, int] = {}
    for prior in supplied_prior:
        prior_counts[prior.get("candidateId")] = prior_counts.get(prior.get("candidateId"), 0) + 1
    prior_valid = {r.get("candidateId") for r in supplied_prior
                   if prior_counts.get(r.get("candidateId")) == 1 and _is_valid_prior(envelope, r, packetRoot)}
    # Keep only completed valid receipts. A stale/deferred/invalid attempt must
    # not compete with the replacement attempt in the deterministic reconciler.
    receipts = [r for r in supplied_prior if r.get("candidateId") in prior_valid]
    errors: dict[str, str] = {}
    pending = [row for row in rows if row.get("candidateId") not in prior_valid]
    pending.sort(key=lambda row: (shardFor(row["candidateId"], max(1, len(rows))), row["candidateId"]))
    if worker is None:
        for row in pending:
            errors[row["candidateId"]] = "worker unavailable"
        return {"receipts": receipts, "errors": dict(sorted(errors.items())), "dispatched": 0,
                "attemptBudget": 0, "budgetUnit": "candidate-tasks", "shards": {r["candidateId"]: shardFor(r["candidateId"], max(1, len(rows))) for r in rows}}
    selected = pending if maxTasks is None else pending[:maxTasks]
    for row in pending[len(selected):]:
        errors[row["candidateId"]] = "dispatch budget exhausted (maxTasks counts candidate tasks)"

    def invoke(row: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        last_error = "worker failed"
        for attempt in range(1, maxAttempts + 1):
            try:
                returned = worker(copy.deepcopy(dict(row)), attempt)
                if not isinstance(returned, Mapping):
                    return None, "worker returned a non-mapping receipt"
                captured = copy.deepcopy(dict(returned))
                expected = {"candidateId": row["candidateId"], "taskId": row["taskId"],
                            "attempt": attempt, "inputDigest": row["inputDigest"]}
                if any(captured.get(key) != value for key, value in expected.items()):
                    return None, "worker receipt task/attempt/input binding mismatch"
                check = reconcileInventory(envelope, [captured], packetRoot=packetRoot)
                decision = next(d for d in check["decisions"] if d["candidateId"] == row["candidateId"])
                if decision.get("receiptValid") is not True:
                    # Packet/digest/binding failures are deterministic; do not retry.
                    return None, decision.get("reason") or "receipt validation failed"
                return captured, None
            except Exception as exc:  # worker exceptions alone are retryable
                last_error = f"{type(exc).__name__}: {exc}"
        return None, last_error

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=maxWorkers)
    futures = {executor.submit(invoke, row): row for row in selected}
    try:
        for future, row in list(futures.items()):
            cid = row["candidateId"]
            try:
                receipt, error = future.result(timeout=timeoutSeconds)
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
    receipts.sort(key=lambda r: (str(r.get("candidateId")), int(r.get("attempt", 0))))
    return {"receipts": receipts, "errors": dict(sorted(errors.items())), "dispatched": len(selected),
            "attemptBudget": len(selected) * maxAttempts, "budgetUnit": "candidate-tasks",
            "shards": {r["candidateId"]: shardFor(r["candidateId"], max(1, len(rows))) for r in rows}}


def reconcileFanout(envelope: Mapping[str, Any], fanoutResult: Mapping[str, Any], *, packetRoot: str = ".", genericDefinitions: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Reconcile receipts and convert otherwise-lost fanout errors to DEFER reasons."""
    report = reconcileInventory(envelope, fanoutResult.get("receipts", ()), packetRoot=packetRoot, genericDefinitions=genericDefinitions)
    errors = fanoutResult.get("errors", {})
    if isinstance(errors, Mapping):
        for decision in report["decisions"]:
            if decision["outcome"] == "deferred" and decision["candidateId"] in errors:
                decision["reason"] = str(errors[decision["candidateId"]])
    return report

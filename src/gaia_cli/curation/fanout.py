"""Model-neutral bounded worker fanout for a frozen Lane C inventory.

``runFanout(envelope, worker, ...)`` invokes a caller-supplied callable with
(task, attempt); it does not spawn agents, select models, touch the registry, or
write to GitHub. Shards are stable hashes of candidate IDs. Valid prior receipts
may be supplied for resume; only candidates without one are dispatched. Budget,
timeout, missing-worker, and exhausted-retry cases are retained as explicit
errors and are ultimately DEFERred by ``reconcileInventory``. Worker outputs
must satisfy the receipt binding and actual packet hashing contract documented
in ``reconciliation.py``. This module is the shared callable contract for Lane D.
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


def runFanout(envelope: Mapping[str, Any], worker: Callable[[Mapping[str, Any], int], Mapping[str, Any]] | None, *, maxWorkers: int = 4, maxAttempts: int = 2, maxTasks: int | None = None, timeoutSeconds: float | None = None, priorReceipts: Iterable[Mapping[str, Any]] = (), packetRoot: str = ".") -> dict[str, Any]:
    """Dispatch bounded frozen tasks and return deterministic receipts/status.

    ``maxTasks`` bounds newly started candidates (not retry count). Each worker
    receives its immutable frozen row and one-based attempt number. A valid prior
    receipt suppresses dispatch, allowing partial resume. Failed attempts may be
    retried up to ``maxAttempts``. On timeout the task is marked deferred; Python
    cannot forcibly stop a running callable, so its executor is shut down without
    waiting and the callable must itself honor the caller's timeout discipline.
    """
    if maxWorkers < 1 or maxAttempts < 1 or (maxTasks is not None and maxTasks < 0):
        raise ValueError("worker, attempt, and task bounds must be positive")
    rows = envelope.get("candidates", [])
    receipts = list(priorReceipts)
    already = set()
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            continue
        cid = receipt.get("candidateId")
        if cid in already:
            continue
        try:
            probe = reconcileInventory(envelope, [receipt], packetRoot=packetRoot)
            if next(d for d in probe["decisions"] if d["candidateId"] == cid)["outcome"] != "deferred":
                already.add(cid)
        except (ValueError, StopIteration):
            continue
    errors: dict[str, str] = {}
    pending = [row for row in rows if row.get("candidateId") not in already]
    pending.sort(key=lambda row: (shardFor(row["candidateId"], max(1, len(rows))), row["candidateId"]))
    if worker is None:
        for row in pending:
            errors[row["candidateId"]] = "worker unavailable"
        return {"receipts": receipts, "errors": errors, "dispatched": 0, "shards": {r["candidateId"]: shardFor(r["candidateId"], max(1, len(rows))) for r in rows}}
    selected = pending if maxTasks is None else pending[:maxTasks]
    for row in pending[len(selected):]:
        errors[row["candidateId"]] = "dispatch budget exhausted"
    def invoke(row: Mapping[str, Any]) -> tuple[str, Mapping[str, Any] | None, str | None]:
        cid = row["candidateId"]
        last_error = "worker failed"
        for attempt in range(1, maxAttempts + 1):
            try:
                # Workers receive detached input; even a buggy callable cannot
                # mutate the frozen shared envelope or another task's input.
                receipt = worker(copy.deepcopy(dict(row)), attempt)
                if not isinstance(receipt, Mapping):
                    raise ValueError("worker returned a non-mapping receipt")
                bound = dict(receipt)
                bound.setdefault("candidateId", cid)
                bound.setdefault("taskId", row["taskId"])
                bound.setdefault("attempt", attempt)
                bound.setdefault("inputDigest", row["inputDigest"])
                # Reconciliation verifies the actual bytes against both claims.
                # Do not repair missing/self-asserted output hashes here.
                checked = reconcileInventory(envelope, [bound], packetRoot=packetRoot)
                result = next(d for d in checked["decisions"] if d["candidateId"] == cid)
                if result["outcome"] == "deferred" and result.get("reason") != bound.get("reason"):
                    last_error = result.get("reason") or "receipt validation failed"
                    continue
                return cid, bound, None
            except Exception as exc:  # worker boundary: preserve failure as DEFER
                last_error = f"{type(exc).__name__}: {exc}"
        return cid, None, last_error
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=maxWorkers)
    futures = {executor.submit(invoke, row): row for row in selected}
    try:
        for future, row in list(futures.items()):
            cid = row["candidateId"]
            try:
                result = future.result(timeout=timeoutSeconds)
                if result[1] is None:
                    errors[cid] = result[2] or "worker failed"
                else:
                    receipts.append(result[1])
            except concurrent.futures.TimeoutError:
                future.cancel()
                errors[cid] = "worker timeout"
            except Exception as exc:
                errors[cid] = f"{type(exc).__name__}: {exc}"
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    receipts.sort(key=lambda r: (str(r.get("candidateId")), int(r.get("attempt", 0))))
    errors = dict(sorted(errors.items()))
    return {
        "receipts": receipts, "errors": errors, "dispatched": len(selected),
        "shards": {r["candidateId"]: shardFor(r["candidateId"], max(1, len(rows))) for r in rows},
    }


def reconcileFanout(envelope: Mapping[str, Any], fanoutResult: Mapping[str, Any], *, packetRoot: str = ".", genericDefinitions: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Convenience seam for Lane D: reconcile receipts, treating errors as DEFER."""
    return reconcileInventory(envelope, fanoutResult.get("receipts", ()), packetRoot=packetRoot, genericDefinitions=genericDefinitions)

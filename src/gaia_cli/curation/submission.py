"""Content-addressed intake proposals; never approval or promotion authority.

A local receipt serializes issue creation. A crash in the uncertain network window
fails closed until explicit existing-intake recovery; retrying never blindly opens
another issue. Authorization/freshness MUST run before entering this module.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def contentKey(batch):
    """Hash submission content, not wall-clock/batch/issue bookkeeping."""
    payload = {key: batch.get(key) for key in (
        "userId", "sourceRepo", "proposedSkills", "curationHandoff",
    )}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def atomicJson(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def advisoryLock(path):
    """Cross-platform process lock, released by the OS after interruption."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as lock:
        if os.name == "nt":  # pragma: no cover - exercised by Windows CI
            import msvcrt
            if path.stat().st_size == 0:
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            acquire = lambda: msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            release = lambda: (lock.seek(0), msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1))
        else:
            import fcntl
            acquire = lambda: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            release = lambda: fcntl.flock(lock, fcntl.LOCK_UN)
        try:
            acquire()
        except OSError as exc:
            raise ValueError("Identical submission is already in progress; resume after it finishes.") from exc
        try:
            yield
        finally:
            release()


@contextmanager
def submissionLock(root, key):
    directory = Path(root) / ".gaia/curation/submissions"
    with advisoryLock(directory / f"{key}.lock"):
        yield directory / f"{key}.json"


def lookupExistingIntake(issue, batch, root="."):
    """Verify existing proposal identity, NOT its human approval status."""
    if not re.fullmatch(r"[1-9][0-9]*|https://github\.com/gaia-research/gaia-skill-tree/issues/[1-9][0-9]*", str(issue)):
        raise ValueError("Existing intake must be a positive issue number or canonical tracker issue URL.")
    result = subprocess.run(
        ["gh", "issue", "view", str(issue), "--repo", "gaia-research/gaia-skill-tree",
         "--json", "number,url,body,labels"], cwd=root, capture_output=True, text=True,
    )
    if result.returncode:
        raise ValueError("Cannot independently read existing intake; refusing a second submission.")
    record = json.loads(result.stdout)
    labels = {row.get("name") for row in record.get("labels", [])}
    body = record.get("body", "")
    if "intake" not in labels or f"| Batch ID | `{batch['batchId']}` |" not in body:
        raise ValueError("Existing issue does not reference this exact intake batch.")
    marker = f"<!-- gaia:submission {contentKey(batch)} -->"
    if marker not in body:
        # Legacy continuation: only an already persisted byte-equivalent batch
        # may be handed onward; never manufacture a replacement batch or issue.
        stored = Path(root) / "registry-for-review/skill-batches" / f"{batch['batchId']}.json"
        if not stored.is_file() or contentKey(json.loads(stored.read_text())) != contentKey(batch):
            raise ValueError("Existing intake content cannot be verified; preserve the original batch and issue.")
    url = record.get("url", "")
    if not re.fullmatch(r"https://github\.com/gaia-research/gaia-skill-tree/issues/[1-9][0-9]*", url):
        raise ValueError("Invalid existing intake URL.")
    return url


def submitBatch(batch, root, *, writeBatch, openIssue, noIssue=False,
                existingIntake=None, existingBatchId=None, lookupIssue=None):
    """Return an existing/new durable receipt; create at most once locally.

    ``submitting`` and ``uncertain`` require explicit recovery with an independently
    read existing issue. Local receipts are operational state, not L4 evidence.
    """
    key = contentKey(batch)
    batch = dict(batch)
    batch["submissionKey"] = key
    if existingBatchId:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", existingBatchId):
            raise ValueError("Invalid existing batch ID.")
        if not existingIntake:
            raise ValueError("--existing-batch-id requires --existing-intake.")
        batch["batchId"] = existingBatchId
    with submissionLock(root, key) as path:
        receipt = json.loads(path.read_text()) if path.exists() else None
        if receipt and receipt.get("submissionKey") != key:
            raise ValueError("Submission receipt content mismatch.")
        if existingIntake:
            if receipt and not existingBatchId:
                batch["batchId"] = receipt["batchId"]
            issueUrl = (lookupIssue or lookupExistingIntake)(existingIntake, batch, root)
            receipt = {"submissionKey": key, "batchId": batch["batchId"],
                       "issueUrl": issueUrl, "status": "submitted", "continued": True,
                       "nextPhase": "evidence-verification"}
            atomicJson(path, receipt)
            return receipt
        if receipt and receipt.get("status") == "submitted":
            return receipt
        if receipt and receipt.get("status") in {"submitting", "uncertain"}:
            raise ValueError("Prior issue creation is uncertain. Use --existing-intake to recover; no second issue opened.")
        if receipt:
            batch["batchId"] = receipt["batchId"]
            batchPath = receipt["batchPath"]
        else:
            batchPath = writeBatch(batch, root)
            receipt = {"submissionKey": key, "batchId": batch["batchId"],
                       "batchPath": str(batchPath), "status": "prepared", "issueUrl": None}
            atomicJson(path, receipt)
        if noIssue:
            return receipt
        receipt["status"] = "submitting"
        atomicJson(path, receipt)
        try:
            issueUrl = openIssue(batch.get("userId", "unknown"), batch,
                                 batch_path=batchPath, repo_root=root)
        except Exception:
            receipt["status"] = "uncertain"
            atomicJson(path, receipt)
            raise
        if not issueUrl:
            receipt["status"] = "uncertain"
            atomicJson(path, receipt)
            raise ValueError("Issue creation did not produce a receipt; recover explicitly before retrying.")
        receipt.update(status="submitted", issueUrl=issueUrl,
                       nextPhase="evidence-verification")
        atomicJson(path, receipt)
        return receipt

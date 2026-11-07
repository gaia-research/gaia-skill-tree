"""Checkout-local PR diagnostics, independent-verifier inputs and model dispatch.

These fsynced JSONL files and their local lock are NOT critical coordination or
settlement authority. New merge/close preparation, claims, budgets and evidence
live only on the separately pinned canonical coordinator ref. Legacy outcome,
900-second reservation and counter readers remain historical diagnostics; they
cannot issue a send grant, expire/refund an unknown sender or migrate old work.
Profiles/dispatch/receipt publication bookkeeping stays local and best effort.
"""

from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

STORE = Path(".gaia/steward/pr-maintenance")
NAMES = ("outcomes", "verifications", "dispatches", "receipts")
TERMINAL = ("merged", "closed", "already-merged", "already-closed")
SETTLED = TERMINAL + ("failed", "refused", "aborted")
STALE_RESERVATION_SECONDS = 900
KILL_FILE = "KILL"


class StoreError(RuntimeError):
    """The store is unreadable or unsafe. Callers fail closed."""


def storeDir(root: Path, create: bool = True) -> Path:
    directory = root / STORE
    parents = [directory, *directory.parents]
    if any(p.is_symlink() for p in parents if p != root.parent and str(p).startswith(str(root))):
        raise StoreError("the PR-maintenance store is reached through a symlink")
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


@contextmanager
def lock(root: Path) -> Iterator[None]:
    handle = open(storeDir(root) / "lock", "a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def appendRecord(root: Path, name: str, record: Mapping[str, Any]) -> None:
    if name not in NAMES:
        raise StoreError(f"unknown store {name!r}")
    line = json.dumps(dict(record), sort_keys=True) + "\n"
    descriptor = os.open(storeDir(root) / f"{name}.jsonl", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(descriptor, line.encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def readRecords(root: Path, name: str) -> list[dict]:
    path = storeDir(root, create=False) / f"{name}.jsonl"
    if not path.exists():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise StoreError(f"{name}.jsonl line {number} is not valid JSON") from exc
        if isinstance(row, dict):
            rows.append(row)
    return rows


def keyOf(record: Mapping[str, Any]) -> tuple:
    return (record.get("repo"), record.get("number"), record.get("action"))


def terminalFor(root: Path, repo: str, number: int, action: str) -> dict | None:
    """The terminal outcome already recorded for this pull request and action, if any."""

    for row in reversed(readRecords(root, "outcomes")):
        if keyOf(row) == (repo, number, action) and row.get("state") in TERMINAL:
            return row
    return None


def openReservation(root: Path, repo: str, number: int, action: str, now: datetime) -> dict | None:
    """A reservation with no later settled line. Stale ones (a crashed attempt) are returned flagged ``stale``."""

    reserved: dict | None = None
    for row in readRecords(root, "outcomes"):
        if keyOf(row) != (repo, number, action):
            continue
        if row.get("state") == "reserved":
            reserved = row
        elif row.get("state") in SETTLED:
            reserved = None
    if reserved is None:
        return None
    at = datetime.strptime(reserved["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return {**reserved, "stale": now - at > timedelta(seconds=STALE_RESERVATION_SECONDS)}


def writesWithin(root: Path, now: datetime, seconds: int = 3600, actions: tuple[str, ...] = ("merge", "close")) -> int:
    """Reservations and completed writes inside the window. A reservation counts: it will spend the budget."""

    horizon = now - timedelta(seconds=seconds)
    spent: set[tuple] = set()
    for row in readRecords(root, "outcomes"):
        if row.get("action") in actions and row.get("state") in ("reserved",) + TERMINAL:
            when = datetime.strptime(row["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if when >= horizon:
                spent.add((row.get("repo"), row.get("number"), row.get("action"), row.get("headSha")))
    return len(spent)


def writesInRun(root: Path, runId: str, action: str) -> int:
    return len({(r.get("repo"), r.get("number")) for r in readRecords(root, "outcomes")
                if r.get("runId") == runId and r.get("action") == action and r.get("state") in ("reserved",) + TERMINAL})


def killSwitchActive(root: Path, policyKill: bool = False) -> str | None:
    """The reason the route is revoked, or ``None``. Policy, a local file or an environment flag each suffice."""

    if policyKill:
        return "policy prMaintenance.killSwitch is true"
    if (storeDir(root, create=False) / KILL_FILE).exists():
        return f"{STORE.as_posix()}/{KILL_FILE} exists"
    if os.environ.get("GAIA_STEWARD_PR_KILL", "").strip().lower() in {"1", "true", "yes", "on"}:
        return "GAIA_STEWARD_PR_KILL is set"
    return None


def recordReceipt(root: Path, record: Mapping[str, Any]) -> None:
    appendRecord(root, "receipts", record)


def receiptPosted(root: Path, repo: str, number: int, kind: str, head12: str) -> dict | None:
    for row in reversed(readRecords(root, "receipts")):
        if (row.get("repo"), row.get("number"), row.get("kind"), row.get("head12")) == (repo, number, kind, head12):
            return row
    return None

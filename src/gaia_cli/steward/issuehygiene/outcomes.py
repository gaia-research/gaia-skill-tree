"""Durable closure outcomes for ``forge.close_issue`` (contract sections 3.4 and 3.5).

The runner emits a closure action whose params are a plan from ``closure.planClosures``.
A driver performs it and records one outcome with ``gaia steward full record``. The
outcome lands in this store, which is the memory that makes closure exactly-once
across runs. A run record alone is not enough, because retained runs are compacted.

Closure is keyed on the pair (semantic key, issue number), the same pair that lane B's
receipts file records. ``donePairs`` therefore counts both this store and every
receipts file under ``.gaia/steward/issue-hygiene/receipts/``, so a closure the
driver script made directly is never repeated by the runner.

The store is local to the checkout (``.gaia/steward/issue-hygiene/``, ignored). An
unreadable store is an error, not an empty store: an empty store would re-emit every
closure already performed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from gaia_cli.steward.issuehygiene.closure import resumeState

STORE = Path(".gaia/steward/issue-hygiene/outcomes.json")
RECEIPTDIR = Path(".gaia/steward/issue-hygiene/receipts")
STORESCHEMA = "steward-issue-closure-outcomes-v1"
# ``refused`` (B8 H-3a) is the outcome of an exit-2 gate refusal: the step settles, the pair is emitted again by a later
# run, and RETRYLIMIT refusals escalate to the founder desk as one Class C question.
OUTCOMES = ("closed", "stale-skip", "already-closed", "failed", "blocked", "blocked-identity", "refused")
TERMINALOUTCOMES = frozenset({"closed", "already-closed"})
RETRYABLE = frozenset({"failed", "blocked", "blocked-identity", "refused"})
RETRYLIMIT = 3


class OutcomeStoreError(RuntimeError):
    """The closure outcome store cannot be read or written safely."""


def storePath(root: Path) -> Path:
    return root / STORE


def pairKey(key: str, issue: int) -> str:
    return f"{key}#{issue}"


def loadOutcomes(root: Path) -> dict[str, dict[str, Any]]:
    """Return ``{pair key: entry}``. A missing store is empty; a malformed one raises."""

    path = storePath(root)
    if not path.exists():
        return {}
    if not path.is_file():
        raise OutcomeStoreError(f"{STORE.as_posix()} is not a regular file")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise OutcomeStoreError(f"{STORE.as_posix()} is unreadable: {type(exc).__name__}") from exc
    if not isinstance(document, dict) or document.get("schemaVersion") != STORESCHEMA:
        raise OutcomeStoreError(f"{STORE.as_posix()} does not declare {STORESCHEMA}")
    entries = document.get("entries")
    if not isinstance(entries, dict):
        raise OutcomeStoreError(f"{STORE.as_posix()} entries must be an object")
    return {str(name): dict(value) for name, value in entries.items() if isinstance(value, dict)}


def closedPairs(entries: Mapping[str, Mapping[str, Any]]) -> frozenset[tuple[str, int]]:
    """(key, issue) pairs this store records as done."""

    done = set()
    for entry in entries.values():
        key, issue = entry.get("key"), entry.get("issue")
        if entry.get("outcome") in TERMINALOUTCOMES and isinstance(key, str) and isinstance(issue, int):
            done.add((key, issue))
    return frozenset(done)


def receiptPairs(root: Path) -> frozenset[tuple[str, int]]:
    """(key, issue) pairs recorded done in any receipts file, including the driver script's."""

    directory = root / RECEIPTDIR
    if not directory.is_dir():
        return frozenset()
    done: set[tuple[str, int]] = set()
    for path in sorted(directory.glob("*.jsonl")):
        done |= resumeState(path).done
    return frozenset(done)


def doneClosures(root: Path) -> dict[tuple[str, int], str | None]:
    """Every pair already closed by any path, with the latest ``closedAt`` it records (None when unknown).

    Reads the outcome store and every receipts file of the checkout. Raises ``OutcomeStoreError`` when the store is
    unreadable. A pair reopened by a person is still done here: the steward never closes it again (B8 H-1).
    """

    found: dict[tuple[str, int], str | None] = {}
    for entry in loadOutcomes(root).values():
        key, issue = entry.get("key"), entry.get("issue")
        if entry.get("outcome") in TERMINALOUTCOMES and isinstance(key, str) and isinstance(issue, int):
            found[(key, issue)] = laterOf(found.get((key, issue)), entry.get("closedAt"))
    directory = root / RECEIPTDIR
    if directory.is_dir():
        for path in sorted(directory.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict) or entry.get("outcome") not in TERMINALOUTCOMES:
                    continue
                key, issue = entry.get("key"), entry.get("issue")
                if isinstance(key, str) and isinstance(issue, int):
                    found[(key, issue)] = laterOf(found.get((key, issue)), entry.get("closedAt"))
    return found


def laterOf(current: str | None, candidate: Any) -> str | None:
    if not isinstance(candidate, str):
        return current
    return candidate if current is None or candidate > current else current


def donePairs(root: Path) -> frozenset[tuple[str, int]]:
    """Every (key, issue) pair already closed by any path. Raises ``OutcomeStoreError`` when unreadable."""

    return frozenset(doneClosures(root))


def failedAttempts(entries: Mapping[str, Mapping[str, Any]], key: str, issue: int) -> int:
    entry = entries.get(pairKey(key, issue)) or {}
    return int(entry.get("attempts", 0)) if entry.get("outcome") in RETRYABLE else 0


def writeOutcome(root: Path, key: str, issue: int, entry: Mapping[str, Any]) -> str:
    """Record one outcome for (key, issue). Returns ``repeat`` when a terminal outcome already stands.

    Terminal outcomes are never overwritten. A retryable outcome (``failed``,
    ``blocked``, ``stale-skip``) replaces the previous retryable one and counts attempts.
    """

    path = storePath(root)
    entries = loadOutcomes(root)
    name = pairKey(key, issue)
    previous = entries.get(name)
    if previous is not None and previous.get("outcome") in TERMINALOUTCOMES:
        return "repeat"
    stored = dict(entry)
    stored["key"] = key
    stored["issue"] = issue
    stored["attempts"] = failedAttempts(entries, key, issue) + 1 if stored.get("outcome") in RETRYABLE else 0
    entries[name] = stored
    document = {"schemaVersion": STORESCHEMA, "entries": {k: entries[k] for k in sorted(entries)}}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return "recorded"


def manifestEight(digest: str) -> str:
    return digest[:8]

"""Durable closure outcomes for ``forge.close_issue`` (contract sections 3.4 and 3.5).

The runner emits a closure action; a driver performs it and records one outcome
with ``gaia steward full record``. The outcome lands in this store, which is the
memory that makes closure exactly-once across runs: a semantic key that reached a
terminal outcome is never emitted again, whatever the census says afterwards. A
run record alone is not enough, because retained runs are compacted.

The store is local to the checkout (``.gaia/steward/issue-hygiene/``, ignored).
An unreadable store is an error, not an empty store: an empty store would
re-emit every closure already performed.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

from gaia_cli.steward.primitives.redact import scrub

STORE = Path(".gaia/steward/issue-hygiene/outcomes.json")
STORESCHEMA = "steward-issue-closure-outcomes-v1"
OUTCOMES = ("closed", "stale-skip", "already-closed", "failed", "blocked")
TERMINALOUTCOMES = frozenset({"closed", "already-closed"})
RETRYLIMIT = 3
STATEREASONS = ("completed", "not_planned", "duplicate")
MAXPAYLOADCHARS = 4000
_PAYLOAD = re.compile(r"<!-- gaia-upstream-payload.*?-->", re.DOTALL)


class OutcomeStoreError(RuntimeError):
    """The closure outcome store cannot be read or written safely."""


def storePath(root: Path) -> Path:
    return root / STORE


def loadOutcomes(root: Path) -> dict[str, dict[str, Any]]:
    """Return ``{semantic key: entry}``. A missing store is empty; a malformed one raises."""

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
    return {str(key): dict(value) for key, value in entries.items() if isinstance(value, dict)}


def closedKeys(entries: Mapping[str, Mapping[str, Any]]) -> frozenset[str]:
    return frozenset(key for key, entry in entries.items() if entry.get("outcome") in TERMINALOUTCOMES)


def failedAttempts(entries: Mapping[str, Mapping[str, Any]], key: str) -> int:
    entry = entries.get(key) or {}
    return int(entry.get("attempts", 0)) if entry.get("outcome") in {"failed", "blocked"} else 0


def writeOutcome(root: Path, key: str, entry: Mapping[str, Any]) -> str:
    """Record one outcome for ``key``. Returns ``repeat`` when a terminal outcome already stands.

    Terminal outcomes are never overwritten. A retryable outcome (``failed``,
    ``blocked``, ``stale-skip``) replaces the previous retryable one and counts attempts.
    """

    path = storePath(root)
    entries = loadOutcomes(root)
    previous = entries.get(key)
    if previous is not None and previous.get("outcome") in TERMINALOUTCOMES:
        return "repeat"
    stored = dict(entry)
    stored["attempts"] = failedAttempts(entries, key) + 1 if stored.get("outcome") in {"failed", "blocked"} else 0
    entries[key] = stored
    document = {"schemaVersion": STORESCHEMA, "entries": {k: entries[k] for k in sorted(entries)}}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return "recorded"


def manifestEight(digest: str) -> str:
    return digest[:8]


def closureMarker(key: str, digest: str) -> str:
    return f"<!-- gaia-steward-closure:{key}:{manifestEight(digest)} -->"


def payloadBlock(body: str | None) -> str | None:
    """The candidate payload block of an upstream child body, scrubbed and bounded."""

    if not isinstance(body, str):
        return None
    found = _PAYLOAD.search(body)
    if found is None:
        return None
    return scrub(found.group(0))[:MAXPAYLOADCHARS]


def closureComment(
    *, key: str, ruleId: str, stateReason: str, title: str, labels: list[str], bodySha256: str,
    evidence: list[Mapping[str, Any]], payload: str | None, digest: str, duplicateOf: int | None = None,
) -> str:
    """The closing comment: the proof, the original payload, and the marker a resumed driver looks for."""

    lines = [
        f"Closed by Steward issue hygiene rule `{ruleId}` (#2130). Reason: `{stateReason}`.",
    ]
    if duplicateOf is not None:
        lines.append(f"Duplicate of #{duplicateOf}.")
    lines.append("")
    lines.append("Proof:")
    for ref in evidence or [{"type": "policy", "ref": ruleId, "sha256": ""}]:
        digestText = f" sha256:{str(ref.get('sha256', ''))[:12]}" if ref.get("sha256") else ""
        lines.append(f"- {ref.get('type', 'evidence')}: {ref.get('ref', '')}{digestText}")
    lines.extend([
        "",
        "Original payload (preserved for audit):",
        f"- title: {scrub(title)[:200]}",
        f"- labels: {', '.join(scrub(label) for label in labels) or 'none'}",
        f"- bodySha256: {bodySha256}",
        f"- semantic key: `{scrub(key)[:200]}`",
    ])
    lines.append("")
    lines.append(payload if payload else "_No candidate payload block was present in the issue body._")
    lines.extend(["", closureMarker(key, digest)])
    return "\n".join(lines)

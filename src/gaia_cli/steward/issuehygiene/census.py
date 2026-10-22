"""Census input for issue hygiene: schema ``steward-github-census-v1`` (contract section 3.1).

The census is a driver-written snapshot of open GitHub issues and pull requests plus
recently closed rows. This module only reads and judges it: it never fetches anything
and never raises on bad data. Anything unusable is reported through ``CensusStatus``
with machine-readable reasons, so the caller can fail closed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from gaia_cli.steward.clock import utcNow

SCHEMA_VERSION = "steward-github-census-v1"
COMPLETE = "complete"
INCOMPLETE = "incomplete"
STALE = "stale"
MISSING = "missing"
STATUSES = (COMPLETE, INCOMPLETE, STALE, MISSING)
SECTIONS = ("issues", "pulls")


def bodySha256(text: str | None) -> str:
    """Hex sha256 of a body as UTF-8. A null body hashes as the empty string."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def parseTimestamp(value: Any) -> datetime | None:
    """Parse an RFC 3339 timestamp such as ``2026-10-21T19:00:00Z``; None when unparsable."""
    if not isinstance(value, str) or not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@dataclass(frozen=True)
class CensusStatus:
    """Verdict on a census: one of STATUSES plus every reason that contributed."""

    status: str
    reasons: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return self.status == COMPLETE


@dataclass(frozen=True)
class Census:
    """A loaded census document with its verdict. ``document`` is None when nothing parsed."""

    document: dict | None
    status: CensusStatus
    source: str = ""

    def rows(self, field: str = "issues") -> list[dict]:
        if not isinstance(self.document, dict):
            return []
        value = self.document.get(field)
        if not isinstance(value, list):
            return []
        return [row for row in value if isinstance(row, dict)]

    def openIssues(self) -> list[dict]:
        """Open rows that are issues (not pull requests)."""
        return [row for row in self.rows("issues") if not row.get("isPullRequest")]

    def openPulls(self) -> list[dict]:
        """Open rows that are pull requests."""
        return [row for row in self.rows("issues") if row.get("isPullRequest")]

    def byNumber(self) -> dict[int, dict]:
        """Every open row (issues and pulls) keyed by number."""
        return {row["number"]: row for row in self.rows("issues") if isinstance(row.get("number"), int)}

    def mergedPulls(self) -> list[dict]:
        """Merged pull requests from open and recently closed rows (``isPullRequest`` with ``mergedAt``)."""
        found = []
        for field in ("issues", "recentlyClosed"):
            for row in self.rows(field):
                if row.get("isPullRequest") and row.get("mergedAt"):
                    found.append(row)
        return found


def rowProblems(row: dict, label: str) -> list[str]:
    reasons = []
    number = row.get("number", "?")
    if "body" not in row:
        reasons.append(f"{label}-row-missing-body:#{number}")
        return reasons
    recorded = row.get("bodySha256")
    if not isinstance(recorded, str) or recorded != bodySha256(row.get("body")):
        reasons.append(f"{label}-body-sha256-mismatch:#{number}")
    return reasons


def validateCensus(raw: Any, now: Any, maxAgeSeconds: int) -> CensusStatus:
    """Judge a parsed census document. Never raises on bad data.

    Precedence: missing > incomplete > stale > complete. All reasons are reported.
    ``now`` may be a datetime or an RFC 3339 string.
    """
    if not isinstance(raw, dict):
        return CensusStatus(MISSING, ("not-an-object",))
    reasons: list[str] = []
    level = COMPLETE
    schema = raw.get("schemaVersion")
    if schema != SCHEMA_VERSION:
        reasons.append(f"unknown-schema-version:{schema}")
        level = INCOMPLETE

    completeness = raw.get("completeness")
    if not isinstance(completeness, dict):
        reasons.append("completeness-missing")
        level = INCOMPLETE
        completeness = {}
    for section in SECTIONS:
        info = completeness.get(section)
        if not isinstance(info, dict):
            reasons.append(f"{section}-completeness-missing")
            level = INCOMPLETE
            continue
        if info.get("complete") is not True:
            reasons.append(f"{section}-complete-false")
            level = INCOMPLETE
        fetched = info.get("pagesFetched")
        expected = info.get("expectedPages")
        if fetched != expected or not isinstance(fetched, int):
            reasons.append(f"{section}-pages-mismatch:{fetched}/{expected}")
            level = INCOMPLETE
        # itemCount is what the listing returned: "issues" counts every open row (pull requests included,
        # as GitHub's issues endpoint lists them) and "pulls" counts the pull-request rows.
        openRows = raw.get("issues") if isinstance(raw.get("issues"), list) else []
        openRows = [row for row in openRows if isinstance(row, dict)]
        wanted = len(openRows) if section == "issues" else sum(1 for row in openRows if row.get("isPullRequest"))
        if info.get("itemCount") != wanted:
            reasons.append(f"{section}-item-count-mismatch:{info.get('itemCount')}/{wanted}")
            level = INCOMPLETE

    for field in ("issues", "recentlyClosed"):
        value = raw.get(field, [])
        if not isinstance(value, list):
            reasons.append(f"{field}-not-a-list")
            level = INCOMPLETE
            continue
        for row in value:
            if not isinstance(row, dict):
                reasons.append(f"{field}-row-not-an-object")
                level = INCOMPLETE
                continue
            rowReasons = rowProblems(row, field)
            if rowReasons:
                reasons.extend(rowReasons)
                level = INCOMPLETE

    fetchedAt = parseTimestamp(raw.get("fetchedAt"))
    nowAt = now if isinstance(now, datetime) else parseTimestamp(now)
    if fetchedAt is None or nowAt is None:
        reasons.append("fetchedAt-unparsable")
        level = INCOMPLETE
    else:
        if nowAt.tzinfo is None:
            nowAt = nowAt.replace(tzinfo=timezone.utc)
        age = (nowAt - fetchedAt).total_seconds()
        if age < 0:
            reasons.append("fetchedAt-in-future")
            level = INCOMPLETE
        elif age > maxAgeSeconds:
            reasons.append(f"fetchedAt-too-old:{int(age)}s")
            if level == COMPLETE:
                level = STALE
    return CensusStatus(level, tuple(reasons))


def loadCensus(path: str | Path, now: Any = None, maxAgeSeconds: int = 6 * 3600) -> Census:
    """Read a census file. A missing or unparsable file yields ``missing``; never raises.

    ``now`` defaults to the current UTC time. ``maxAgeSeconds`` defaults to six hours.
    """
    source = str(path)
    if now is None:
        now = utcNow()
    target = Path(path)
    if not target.is_file():
        return Census(None, CensusStatus(MISSING, ("file-missing",)), source)
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return Census(None, CensusStatus(MISSING, ("unparsable-json",)), source)
    status = validateCensus(raw, now, maxAgeSeconds)
    document = raw if isinstance(raw, dict) else None
    return Census(document, status, source)


__all__ = [
    "SCHEMA_VERSION",
    "STATUSES",
    "COMPLETE",
    "INCOMPLETE",
    "STALE",
    "MISSING",
    "Census",
    "CensusStatus",
    "bodySha256",
    "loadCensus",
    "parseTimestamp",
    "validateCensus",
]

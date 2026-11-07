"""PR census input: schema ``steward-pr-census-v1`` (written by ``scripts/steward_pr_census.py``).

The census is a driver-written, read-only snapshot of one repository's open pull requests, each
enriched with commits, files, reviews, check runs and comments, plus the destination branch tips
and the branch-protection facts. This module only reads and judges it: it never fetches and never
raises on bad data. An unusable census is reported through ``CensusStatus`` so callers fail closed.
A stale, short-paged, partially enriched or duplicated census is never ``complete``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from gaia_cli.steward.clock import utcNow
from gaia_cli.steward.issuehygiene.census import (
    COMPLETE,
    INCOMPLETE,
    MISSING,
    STALE,
    Census,
    CensusStatus,
    bodySha256,
    parseTimestamp,
)

SCHEMA_VERSION = "steward-pr-census-v1"
CENSUS_INPUT = Path(".gaia/steward/inputs/github-prs.json")
DEFAULT_MAX_AGE_SECONDS = 3600
SHA = re.compile(r"[0-9a-f]{40}")
ROW_KEYS = (
    "number", "title", "state", "draft", "author", "headRef", "headSha", "headRepo", "baseRef", "baseSha", "labels",
    "mergeable", "mergeableState", "body", "bodySha256", "commits", "files", "reviews", "checkRuns", "comments",
    "reviewThreadsUnresolved", "updatedAt",
)


def rowProblems(row: dict) -> list[str]:
    number = row.get("number", "?")
    problems = [f"pull-row-missing-{key}:#{number}" for key in ROW_KEYS if key not in row]
    if problems:
        return problems
    if row["state"] != "open":
        problems.append(f"pull-row-not-open:#{number}")
    if not isinstance(row["headSha"], str) or not SHA.fullmatch(row["headSha"]):
        problems.append(f"pull-row-bad-head-sha:#{number}")
    if not isinstance(row["baseSha"], str) or not SHA.fullmatch(row["baseSha"]):
        problems.append(f"pull-row-bad-base-sha:#{number}")
    if row["bodySha256"] != bodySha256(row.get("body")):
        problems.append(f"pull-body-sha256-mismatch:#{number}")
    for key in ("commits", "files", "reviews", "checkRuns", "comments", "labels"):
        if not isinstance(row[key], list):
            problems.append(f"pull-row-{key}-not-a-list:#{number}")
    if not isinstance(row["author"], dict) or "login" not in row["author"]:
        problems.append(f"pull-row-author-malformed:#{number}")
    return problems


def validateCensus(raw: Any, now: Any, maxAgeSeconds: int = DEFAULT_MAX_AGE_SECONDS) -> CensusStatus:
    """Judge a parsed census. Precedence: missing > incomplete > stale > complete. All reasons are reported."""

    if not isinstance(raw, dict):
        return CensusStatus(MISSING, ("not-an-object",))
    reasons: list[str] = []
    level = COMPLETE
    if raw.get("schemaVersion") != SCHEMA_VERSION:
        reasons.append(f"unknown-schema-version:{raw.get('schemaVersion')}")
        level = INCOMPLETE
    if not isinstance(raw.get("repo"), str) or "/" not in raw.get("repo", ""):
        reasons.append("repo-missing")
        level = INCOMPLETE
    pulls = raw.get("pulls")
    if not isinstance(pulls, list):
        reasons.append("pulls-not-a-list")
        level = INCOMPLETE
        pulls = []
    completeness = raw.get("completeness") if isinstance(raw.get("completeness"), dict) else {}
    listing = completeness.get("pulls")
    if not isinstance(listing, dict):
        reasons.append("pulls-completeness-missing")
        level = INCOMPLETE
    else:
        if listing.get("complete") is not True:
            reasons.append("pulls-complete-false")
            level = INCOMPLETE
        fetched, expected = listing.get("pagesFetched"), listing.get("expectedPages")
        if not isinstance(fetched, int) or isinstance(fetched, bool) or fetched != expected:
            reasons.append(f"pulls-pages-mismatch:{fetched}/{expected}")
            level = INCOMPLETE
        if listing.get("itemCount") != len(pulls):
            reasons.append(f"pulls-item-count-mismatch:{listing.get('itemCount')}/{len(pulls)}")
            level = INCOMPLETE
    detail = completeness.get("details")
    if not isinstance(detail, dict) or detail.get("complete") is not True \
            or detail.get("expected") != len(pulls) or detail.get("fetched") != len(pulls):
        reasons.append("details-incomplete")
        level = INCOMPLETE
    seen: set = set()
    for row in pulls:
        if not isinstance(row, dict):
            reasons.append("pull-row-not-an-object")
            level = INCOMPLETE
            continue
        problems = rowProblems(row)
        if problems:
            reasons.extend(problems)
            level = INCOMPLETE
        if row.get("number") in seen:
            reasons.append(f"pulls-duplicate-number:#{row.get('number')}")
            level = INCOMPLETE
        seen.add(row.get("number"))
    tips = raw.get("baseTips")
    if not isinstance(tips, dict) or not all(isinstance(v, str) and SHA.fullmatch(v) for v in tips.values()) or not tips:
        reasons.append("base-tips-missing")
        level = INCOMPLETE
    else:
        for row in pulls:
            if isinstance(row, dict) and row.get("baseRef") not in tips:
                reasons.append(f"base-tip-missing:{row.get('baseRef')}")
                level = INCOMPLETE
    protection = raw.get("protection")
    if not isinstance(protection, dict) or protection.get("complete") is not True \
            or not isinstance(protection.get("requiredChecks"), list):
        reasons.append("protection-unknown")
        level = INCOMPLETE
    if not isinstance(raw.get("recentlyClosed", []), list):
        reasons.append("recentlyClosed-not-a-list")
        level = INCOMPLETE
    fetchedAt = parseTimestamp(raw.get("fetchedAt"))
    nowAt = now if hasattr(now, "tzinfo") else parseTimestamp(now)
    if fetchedAt is None or nowAt is None:
        reasons.append("fetchedAt-unparsable")
        level = INCOMPLETE
    else:
        age = (nowAt - fetchedAt).total_seconds()
        if age < 0:
            reasons.append("fetchedAt-in-future")
            level = INCOMPLETE
        elif age > maxAgeSeconds:
            reasons.append(f"fetchedAt-too-old:{int(age)}s")
            if level == COMPLETE:
                level = STALE
    return CensusStatus(level, tuple(reasons))


def loadPrCensus(path: str | Path, now: Any = None, maxAgeSeconds: int = DEFAULT_MAX_AGE_SECONDS) -> Census:
    """Read a PR census file. A missing or unparsable file yields ``missing``; never raises."""

    source = str(path)
    now = utcNow() if now is None else now
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        return Census(None, CensusStatus(MISSING, ("file-missing",)), source)
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return Census(None, CensusStatus(MISSING, ("unparsable-json",)), source)
    status = validateCensus(raw, now, maxAgeSeconds)
    return Census(raw if isinstance(raw, dict) else None, status, source)


def pullRows(census: Census) -> list[dict]:
    if not isinstance(census.document, dict):
        return []
    return [row for row in census.document.get("pulls", []) if isinstance(row, dict)]


__all__ = ["CENSUS_INPUT", "SCHEMA_VERSION", "loadPrCensus", "pullRows", "rowProblems", "validateCensus"]

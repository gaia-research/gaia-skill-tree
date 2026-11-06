"""
scripts.upstream_watcher.staging — staged batching by upstream repository and review window (#2283, ruling #12).

Founder ruling #12 (``founder/steward/decisions/steward-upstream-batch-rollout.json``): upstream skills change almost
daily, the founder reviews one Class B pass a day or one batch a week, so the watcher must write far fewer issue
updates. The watcher still OBSERVES every day. It WRITES (creates or updates the one umbrella per upstream repository)
only when the review window is due, or when a finding is urgent.

This module is pure planning plus one small observation journal. It performs no GitHub write. ``batch.run_batch``
consults it through ``Stager.gate``; with staging ``off`` (the default) nothing here runs and behaviour is unchanged.

Window
------
A window is one week, flushed on ``flushWeekday`` (Monday by default, UTC). A finding is written when ANY of:

* ``urgent``         — the narrow urgent rule below holds (bypasses the delay);
* ``flush-day``      — today is the flush weekday;
* ``window-elapsed`` — the release is already ``windowDays`` old, so a missed flush day never stretches a hold past
                       one window.

Otherwise it is ``hold``: planned against live GitHub (reads only), observed, and not written. A held finding is not
lost: the next run recomputes it from the same release and registry, and the journal keeps the provenance of every
version and candidate seen in the meantime.

Urgent (deliberately narrow)
----------------------------
A finding is urgent only when it carries a ``linkLiveness`` row for a registry-tracked component whose HTTP status is
exactly 404 or 410: an installed skill's source link is dead, so it cannot be installed. Nothing else is urgent: not a
new version, a component add or remove, name drift, a 403/429/5xx (rate limit or transient, known limit L-4) or a
network error (never hashed). Urgent bypasses the delay only; the write is still the one umbrella update, and an
unchanged payload is still a no-op, so an unchanged dead link never re-bypasses into a second write.

Closed umbrellas
----------------
A closed umbrella is a completed epic (ruling #6). Staging never reads one as a hold target, edits it, or reopens it:
new changes wait for the window and then start a new batch (or update the open canonical umbrella) exactly as the
batch planner already does.

Journal
-------
``Journal`` is an advisory JSON record of daily observations per repository: the versions seen and the candidate ids
seen, each deduplicated (a re-observation on the same UTC day changes nothing, a later day bumps ``observationDays``
and ``lastObserved``) with first/last observed and first/last seen version kept. It is never an input to a write
decision and never stands in for the umbrella's own rows or dispositions. A candidate seen in the window but absent at
flush is reported as ``transient`` (not filed: it no longer exists upstream) so it is visible, not silently dropped.
A lost or corrupt journal costs only that provenance.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

MODES = ("off", "weekly")
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
DEFAULTWINDOWDAYS = 7
# The only statuses that make a finding urgent: the tracked component's source is gone.
URGENTSTATUSES = frozenset({404, 410})
JOURNALVERSION = 1
MAXVERSIONS = 50

DECISIONHOLD = "hold"
DECISIONFLUSH = "flush"
DECISIONURGENT = "urgent"

# Outcomes (batch.process_suite) after which a repository's journaled observations are settled.
SETTLEDOUTCOMES = frozenset({"created", "updated", "noop", "suppressed-processed"})


@dataclass(frozen=True)
class StagingConfig:
    """Resolved staging switch. ``mode == "off"`` is the default and means no staging at all."""

    mode: str = "off"
    flushWeekday: int = 0
    windowDays: int = DEFAULTWINDOWDAYS
    now: dt.datetime | None = None
    journalPath: str | None = None

    @property
    def active(self) -> bool:
        return self.mode != "off"

    def asOf(self) -> dt.datetime:
        return self.now or dt.datetime.now(dt.timezone.utc)


def parseWeekday(text: str) -> int:
    value = str(text).strip().lower()
    for index, name in enumerate(WEEKDAYS):
        if value in (name, name[:3]):
            return index
    raise ValueError(f"unknown weekday {text!r}; use one of {', '.join(WEEKDAYS)}")


def parseTime(text: str | None) -> dt.datetime | None:
    """Parse an ISO-8601 instant (``Z`` or an offset) to an aware UTC datetime. None when absent or unparseable."""
    if not text:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def isoTime(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def isFlushDay(now: dt.datetime, config: StagingConfig) -> bool:
    return now.astimezone(dt.timezone.utc).weekday() == config.flushWeekday


def nextFlushDate(now: dt.datetime, config: StagingConfig) -> str:
    """The date (UTC) of the next flush weekday, today included."""
    today = now.astimezone(dt.timezone.utc).date()
    ahead = (config.flushWeekday - today.weekday()) % 7
    return (today + dt.timedelta(days=ahead)).isoformat()


def urgentReasons(finding: dict) -> list[str]:
    """Why *finding* is urgent, or an empty list. See the module docstring: only a 404/410 on a tracked component."""
    reasons = []
    for row in finding.get("linkLiveness") or []:
        status = row.get("status")
        # bool is an int subclass; a boolean is never an HTTP status.
        if isinstance(status, int) and not isinstance(status, bool) and status in URGENTSTATUSES:
            reasons.append(f"dead-link:{row.get('skillId', '?')}:{status}")
    return sorted(set(reasons))


def decide(finding: dict, config: StagingConfig) -> dict:
    """Pure write-or-hold decision for one update finding. Returns ``{decision, reasons, ...}``."""
    now = config.asOf()
    urgent = urgentReasons(finding)
    released = parseTime(finding.get("releasedAt"))
    maxHold = isoTime(released + dt.timedelta(days=config.windowDays)) if released else None
    if urgent:
        decision, reasons = DECISIONURGENT, urgent
    elif isFlushDay(now, config):
        decision, reasons = DECISIONFLUSH, ["flush-day"]
    elif released is not None and now - released >= dt.timedelta(days=config.windowDays):
        decision, reasons = DECISIONFLUSH, ["window-elapsed"]
    else:
        decision, reasons = DECISIONHOLD, ["within-review-window"]
    return {
        "decision": decision,
        "reasons": reasons,
        "nextFlush": nextFlushDate(now, config),
        "maxHoldUntil": maxHold,
    }


# ---------------------------------------------------------------------------
# Observation journal
# ---------------------------------------------------------------------------


def emptyJournal() -> dict:
    return {"schemaVersion": JOURNALVERSION, "repos": {}}


class Journal:
    """Deduplicated daily observations per upstream repository. Advisory provenance, never a write input."""

    def __init__(self, data: dict | None = None):
        self.data = data if data is not None else emptyJournal()

    # -- persistence -------------------------------------------------------
    @classmethod
    def load(cls, path: str | os.PathLike | None) -> "Journal":
        """Read *path*. A missing, empty, corrupt or foreign-version file is an empty journal (with a warning)."""
        if not path or not Path(path).is_file():
            return cls()
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"::warning::staging journal {path} unreadable ({exc}); starting an empty journal.", file=sys.stderr)
            return cls()
        if not isinstance(data, dict) or data.get("schemaVersion") != JOURNALVERSION or not isinstance(data.get("repos"), dict):
            print(f"::warning::staging journal {path} has an unknown shape; starting an empty journal.", file=sys.stderr)
            return cls()
        return cls(data)

    def save(self, path: str | os.PathLike) -> None:
        """Atomic write: a crash leaves the previous journal intact."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        handle, temp = tempfile.mkstemp(dir=str(target.parent), prefix=target.name + ".", suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(json.dumps(self.data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
            os.replace(temp, target)
        except BaseException:
            try:
                os.unlink(temp)
            except OSError:
                pass
            raise

    # -- observation -------------------------------------------------------
    def repo(self, repo: str) -> dict:
        return self.data["repos"].setdefault(repo.lower(), {"versions": [], "candidates": {}})

    @staticmethod
    def touch(entry: dict, day: str, stamp: str) -> None:
        """Record one observation. The same UTC day is idempotent, a later day counts once."""
        if entry.get("lastObservedDay") != day:
            entry["observationDays"] = int(entry.get("observationDays", 0)) + 1
            entry["lastObservedDay"] = day
        entry["lastObserved"] = stamp

    def observe(self, repo: str, finding: dict, now: dt.datetime) -> None:
        """Fold today's finding for *repo* into the journal, deduplicating versions and candidate ids."""
        day = now.astimezone(dt.timezone.utc).date().isoformat()
        stamp = isoTime(now)
        bucket = self.repo(repo)
        version = finding.get("newVersion", "")
        known = next((row for row in bucket["versions"] if row["version"] == version), None)
        if known is None:
            known = {"version": version, "releasedAt": finding.get("releasedAt", ""), "firstObserved": stamp}
            bucket["versions"].append(known)
            del bucket["versions"][:-MAXVERSIONS]
        self.touch(known, day, stamp)
        contributor = finding["skillId"].split("/")[0] if "/" in finding["skillId"] else finding["skillId"]
        for slug in finding.get("componentAdds") or []:
            ident = f"{repo}:{slug}"
            row = bucket["candidates"].get(ident)
            if row is None:
                row = {
                    "suggestedId": f"{contributor}/{slug}",
                    "firstSeenVersion": version,
                    "firstObserved": stamp,
                }
                bucket["candidates"][ident] = row
            row["lastSeenVersion"] = version
            self.touch(row, day, stamp)

    def clear(self, repo: str) -> None:
        self.data["repos"].pop(repo.lower(), None)

    def window(self, repo: str, currentIds: set[str]) -> dict:
        """The window's observation summary for *repo*: versions seen and candidates seen but absent now."""
        bucket = self.data["repos"].get(repo.lower())
        if not bucket:
            return {"versionsObserved": [], "transientCandidates": []}
        transient = [
            {"id": ident, **row} for ident, row in sorted(bucket["candidates"].items()) if ident not in currentIds
        ]
        return {"versionsObserved": [dict(row) for row in bucket["versions"]], "transientCandidates": transient}


# ---------------------------------------------------------------------------
# Stager — the seam batch.run_batch uses
# ---------------------------------------------------------------------------


class Stager:
    """Per-run staging state: decides hold/flush/urgent per planned suite and builds the report section."""

    def __init__(self, config: StagingConfig, journal: Journal | None = None):
        self.config = config
        self.journal = journal if journal is not None else Journal.load(config.journalPath)
        self.rows: dict[str, dict] = {}

    def gate(self, finding: dict, plan: dict) -> dict:
        """Called for a suite whose plan would write (create/update). Returns the staging row (with ``decision``)."""
        repo = plan["suite"]
        verdict = decide(finding, self.config)
        self.journal.observe(repo, finding, self.config.asOf())
        ids = {f"{repo}:{slug}" for slug in finding.get("componentAdds") or []}
        row = {
            "suite": repo,
            "skillId": finding["skillId"],
            "planAction": plan["action"],
            "version": finding["newVersion"],
            "releasedAt": finding.get("releasedAt", ""),
            "candidateIds": sorted(ids),
            "newRows": list(plan["newRows"]),
            "outcome": None,
            **verdict,
            **self.journal.window(repo, ids),
        }
        self.rows[repo] = row
        return row

    def settle(self, suiteRow: dict) -> None:
        """Record the final outcome for a suite and settle its journaled observations once it was surfaced."""
        repo = suiteRow["suite"]
        row = self.rows.get(repo)
        if row is not None:
            row["outcome"] = suiteRow["outcome"]
            if suiteRow["outcome"] == "held":
                print(
                    f"::notice::{repo} {row['version']}: staged, not written (review window). Next flush "
                    f"{row['nextFlush']}; at the latest {row['maxHoldUntil'] or 'next flush'}.",
                    file=sys.stderr,
                )
        if suiteRow["outcome"] in SETTLEDOUTCOMES:
            self.journal.clear(repo)

    def finish(self, report: dict, apply: bool) -> None:
        """Attach the staging section to *report*; persist the journal only on an apply run."""
        now = self.config.asOf()
        rows = [self.rows[key] for key in sorted(self.rows)]
        report["staging"] = {
            "mode": self.config.mode,
            "asOf": isoTime(now),
            "flushWeekday": WEEKDAYS[self.config.flushWeekday],
            "windowDays": self.config.windowDays,
            "flushDay": isFlushDay(now, self.config),
            "held": [row for row in rows if row["outcome"] == "held"],
            "flushed": [row for row in rows if row["decision"] == DECISIONFLUSH and row["outcome"] != "held"],
            "urgent": [row for row in rows if row["decision"] == DECISIONURGENT],
        }
        if apply and self.config.journalPath:
            self.journal.save(self.config.journalPath)


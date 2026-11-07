"""
scripts.upstream_watcher.staging — staged batching by upstream repository and review window (#2283, ruling #12).

Founder ruling #12 (``founder/steward/decisions/steward-upstream-batch-rollout.json``): upstream skills change almost
daily, the founder reviews one Class B pass a day or one batch a week, so the watcher must write far fewer issue
updates. The watcher still OBSERVES every day. It WRITES (creates or updates the one umbrella per upstream repository)
only when the review window is due, or when a finding is urgent.

This module is pure planning plus a durable pending-observation journal. It performs no GitHub write. ``batch.run_batch``
consults it through ``Stager``; with staging ``off`` (the default) nothing here runs and behaviour is unchanged.

Window
------
A window is one week, flushed on ``flushWeekday`` (Monday by default, UTC). A finding is written when ANY of:

* ``urgent``         - the narrow urgent rule below holds (bypasses the delay);
* ``flush-day``      - today is the flush weekday;
* ``window-elapsed`` - the FIRST pending observation of the change is already ``windowDays`` old. The clock starts when
                       the watcher first observed the pending change (``pendingSince`` in the journal), never at the
                       release date, so an old release plus a new non-urgent change on a Tuesday still holds until
                       Monday, and the deadline does not slide when later releases arrive.

Otherwise it is ``hold``: planned against live GitHub (reads only), observed, and not written.

Pending observations are durable and feed the flush
----------------------------------------------------
The journal is required state, not a convenience. Per upstream repository it keeps ``pendingSince``, every version
seen, and every candidate row seen (the full unchecked row, with first and last seen version). At the flush the
journal's candidates that are no longer in the fresh finding are replayed into the planner as ordinary rows, so the
umbrella ends up with exactly the rows that daily unstaged runs would have accumulated (rows are never dropped),
and a candidate keeps the version it was FIRST seen at, not the flush version. Dispositions and child links live on
the umbrella rows and are merged by the planner exactly as before; a hold writes nothing, so they cannot be disturbed.

Pending rows are never dropped. They are cleared only when demonstrably incorporated: the umbrella write that carried
them succeeded, the plan is a no-op because the umbrella already holds them, or a closed umbrella that suppresses the
finding already records them (the planner refuses to suppress a finding whose pending rows no closed umbrella
carries, and starts a new batch instead). A suite with no finding stays pending and is reported (``absent``) until a
finding returns; it never expires. A failed read or precheck leaves the journal as it was.

A journal that is missing or corrupt FAILS CLOSED: the run stops before ANY GitHub write (suite writes and bootstrap
findings alike), every suite is held, urgent findings are reported under ``urgentBlocked``, the run exits 3 and the
report says why. Nothing silently resets. A first run with no journal yet is allowed only when explicitly marked
``bootstrap``. A corrupt journal is never overwritten and is not cured by ``bootstrap``: a human removes it first.

A durable ``initialized`` marker lives OUTSIDE the cache (the repo variable ``UPSTREAM_STAGING_INITIALIZED``, which the
workflow reads and passes as ``--staging-initialized``). With it, a missing journal is a LOST journal (cache eviction)
and not a first-ever bootstrap. A loss fails closed until an explicit recovery dispatch (``--staging-bootstrap``),
which re-observes the current upstream state. The permitted loss is exactly this: observations of candidates that are
no longer present upstream are gone, and for candidates still present the first-seen provenance (version and time)
restarts at the recovery observation. Every row first observed during a recovery carries ``provenanceReset: true`` (and
the report says so), so the loss is auditable. Nothing else is lost and nothing is reconstructed from anywhere else.

Urgent (deliberately narrow)
----------------------------
A finding is urgent only when it carries a ``linkLiveness`` row for a registry-tracked component whose HTTP status is
exactly 404 or 410 in a check that actually ran: an installed skill's source link is dead, so it cannot be installed.
Nothing else is urgent: not a new version, a component add or remove, name drift, a 403/429/5xx (rate limit or
transient, known limit L-4) or a network error (never hashed). Liveness is only checked when a release finding is
computed (deployed behaviour, unchanged here), so "urgent" never means "a link died that nothing checked". Urgent
bypasses the delay only; an unchanged payload is still a no-op, so an unchanged dead link never re-bypasses.

Closed umbrellas
----------------
A closed umbrella is a completed epic (ruling #6). Staging never reads one as a hold target, edits it, or reopens it.
New changes wait for the window and then start a new batch (or update the open canonical umbrella) as the planner
already does. ``batch.ClosureGuard`` re-reads the umbrella immediately before each mutation of a staged run and aborts
and re-plans if it was closed in the meantime.
"""

from __future__ import annotations

import datetime as dt
import hashlib
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
JOURNALVERSION = 2
MAXVERSIONS = 50

DECISIONHOLD = "hold"
DECISIONFLUSH = "flush"
DECISIONURGENT = "urgent"

STATUSOK = "ok"
STATUSBOOTSTRAP = "bootstrap"
STATUSMISSING = "missing"
STATUSCORRUPT = "corrupt"
STATUSLOST = "lost"
STATUSRECOVERY = "recovery"
BLOCKED = frozenset({STATUSMISSING, STATUSCORRUPT, STATUSLOST})

# Outcomes (batch.process_suite) after which a repository's journaled observations are settled.
SETTLEDOUTCOMES = frozenset({"created", "updated", "noop", "suppressed-processed"})
# The fields of a candidate row (batch.candidate_rows) that the journal replays into the planner.
ROWFIELDS = ("id", "slug", "suggestedId", "evidenceUrl", "firstSeenVersion", "lastSeenVersion", "child")


@dataclass(frozen=True)
class StagingConfig:
    """Resolved staging switch. ``mode == "off"`` is the default and means no staging at all."""

    mode: str = "off"
    flushWeekday: int = 0
    windowDays: int = DEFAULTWINDOWDAYS
    now: dt.datetime | None = None
    journalPath: str | None = None
    bootstrap: bool = False
    initialized: bool = False

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


def decide(finding: dict, config: StagingConfig, pendingSince: dt.datetime | None = None) -> dict:
    """Pure write-or-hold decision for one update finding.

    *pendingSince* is when the watcher FIRST observed the pending change (None = this very run is the first
    observation). The release date plays no part: only observation age can elapse the window.
    """
    now = config.asOf()
    first = pendingSince or now
    deadline = first + dt.timedelta(days=config.windowDays)
    urgent = urgentReasons(finding)
    if urgent:
        decision, reasons = DECISIONURGENT, urgent
    elif isFlushDay(now, config):
        decision, reasons = DECISIONFLUSH, ["flush-day"]
    elif now >= deadline:
        decision, reasons = DECISIONFLUSH, ["window-elapsed"]
    else:
        decision, reasons = DECISIONHOLD, ["within-review-window"]
    return {
        "decision": decision,
        "reasons": reasons,
        "pendingSince": isoTime(first),
        "nextFlush": nextFlushDate(now, config),
        "maxHoldUntil": isoTime(deadline),
    }


# ---------------------------------------------------------------------------
# Durable pending-observation journal
# ---------------------------------------------------------------------------


def emptyJournal() -> dict:
    return {"schemaVersion": JOURNALVERSION, "repos": {}}


def digestOf(data: dict) -> str:
    body = {key: value for key, value in data.items() if key != "digest"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


class Journal:
    """Pending observations per upstream repository. Required state: a missing or corrupt journal blocks writes."""

    def __init__(self, data: dict | None = None, status: str = STATUSOK, detail: str = ""):
        self.data = data if data is not None else emptyJournal()
        self.status = status
        self.detail = detail

    @property
    def blocked(self) -> bool:
        return self.status in BLOCKED

    # -- persistence -------------------------------------------------------
    @classmethod
    def load(cls, path: str | os.PathLike | None, bootstrap: bool = False, initialized: bool = False) -> "Journal":
        """Read *path*. Missing is ``bootstrap`` only when explicitly allowed, else ``missing`` (blocked).

        *initialized* is the durable marker kept outside the cache: with it a missing journal is ``lost`` (blocked),
        or ``recovery`` when *bootstrap* explicitly authorises re-observing current upstream state.

        Unreadable, tampered (digest mismatch) or foreign-shaped content is ``corrupt`` (blocked) even with
        *bootstrap*: nothing is silently reset, and ``bootstrap`` never papers over damage.
        """
        if not path:
            return cls(status=STATUSMISSING, detail="no journal path configured")
        target = Path(path)
        if not target.is_file():
            if initialized:
                if bootstrap:
                    return cls(status=STATUSRECOVERY, detail=f"journal lost at {path}; explicit recovery re-observes "
                               "current upstream state (observations of candidates no longer upstream are gone)")
                return cls(status=STATUSLOST, detail=f"journal LOST at {path} (the initialized marker is set, so this is "
                           "a cache eviction, not a first run)")
            if bootstrap:
                return cls(status=STATUSBOOTSTRAP, detail=f"no journal at {path}; explicit bootstrap")
            return cls(status=STATUSMISSING, detail=f"no journal at {path}")
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return cls(status=STATUSCORRUPT, detail=f"journal {path} unreadable: {exc}")
        if not isinstance(data, dict) or data.get("schemaVersion") != JOURNALVERSION or not isinstance(data.get("repos"), dict):
            return cls(status=STATUSCORRUPT, detail=f"journal {path} has an unknown shape")
        if data.get("digest") != digestOf(data):
            return cls(status=STATUSCORRUPT, detail=f"journal {path} fails its digest check")
        return cls(data)

    def save(self, path: str | os.PathLike) -> None:
        """Atomic write with a self-digest. Refuses while blocked, so a corrupt journal is never overwritten."""
        if self.blocked:
            raise RuntimeError(f"refusing to write a {self.status} journal: {self.detail}")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: value for key, value in self.data.items() if key != "digest"}
        payload["digest"] = digestOf(payload)
        handle, temp = tempfile.mkstemp(dir=str(target.parent), prefix=target.name + ".", suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
            os.replace(temp, target)
        except BaseException:
            try:
                os.unlink(temp)
            except OSError:
                pass
            raise

    # -- observation -------------------------------------------------------
    def bucket(self, repo: str) -> dict | None:
        return self.data["repos"].get(repo.lower())

    def pendingSince(self, repo: str) -> dt.datetime | None:
        bucket = self.bucket(repo)
        return parseTime(bucket.get("pendingSince")) if bucket else None

    @staticmethod
    def touch(entry: dict, day: str, stamp: str) -> None:
        """Record one observation. The same UTC day is idempotent, a later day counts once."""
        if entry.get("lastObservedDay") != day:
            entry["observationDays"] = int(entry.get("observationDays", 0)) + 1
            entry["lastObservedDay"] = day
        entry["lastObserved"] = stamp

    def observe(self, repo: str, finding: dict, rows: list[dict], now: dt.datetime) -> None:
        """Fold today's finding for *repo* into the journal. *rows* are its unchecked candidate rows.

        The first observation since the last settle starts ``pendingSince``; it is never moved by later ones.
        Versions and candidates are deduplicated; a candidate keeps the version it was first seen at.
        """
        day = now.astimezone(dt.timezone.utc).date().isoformat()
        stamp = isoTime(now)
        bucket = self.data["repos"].get(repo.lower())
        if bucket is None:
            bucket = {"pendingSince": stamp, "versions": [], "candidates": {}}
            if self.status == STATUSRECOVERY:
                bucket["provenanceReset"] = True
            self.data["repos"][repo.lower()] = bucket
        version = finding.get("newVersion", "")
        known = next((row for row in bucket["versions"] if row["version"] == version), None)
        if known is None:
            known = {"version": version, "releasedAt": finding.get("releasedAt", ""), "firstObserved": stamp}
            bucket["versions"].append(known)
            del bucket["versions"][:-MAXVERSIONS]
        self.touch(known, day, stamp)
        for row in rows:
            entry = bucket["candidates"].get(row["id"])
            if entry is None:
                entry = {**{key: row.get(key) for key in ROWFIELDS}, "firstSeenVersion": version, "firstObserved": stamp}
                if self.status == STATUSRECOVERY:
                    entry["provenanceReset"] = True
                bucket["candidates"][row["id"]] = entry
            entry["lastSeenVersion"] = version
            self.touch(entry, day, stamp)

    def clear(self, repo: str) -> None:
        self.data["repos"].pop(repo.lower(), None)

    def window(self, repo: str, currentIds: set[str]) -> dict:
        """The pending summary for *repo*: versions seen, and candidates seen but absent from *currentIds*."""
        bucket = self.bucket(repo)
        if not bucket:
            return {"pendingSince": None, "versionsObserved": [], "transientCandidates": []}
        transient = [{**row} for ident, row in sorted(bucket["candidates"].items()) if ident not in currentIds]
        return {"pendingSince": bucket.get("pendingSince"), "versionsObserved": [dict(r) for r in bucket["versions"]],
                "transientCandidates": transient}

    def pendingRows(self, repo: str, currentIds: set[str]) -> list[dict]:
        """Journaled candidate rows absent from *currentIds*, as clean planner rows (observation metadata dropped)."""
        bucket = self.bucket(repo)
        if not bucket:
            return []
        return [
            {**{key: row.get(key) for key in ROWFIELDS}, **({"provenanceReset": True} if row.get("provenanceReset") else {})}
            for ident, row in sorted(bucket["candidates"].items()) if ident not in currentIds
        ]

    def provenanceReset(self, repo: str, ids: set[str]) -> set[str]:
        """The ids among *ids* whose journaled provenance restarted at a recovery observation."""
        bucket = self.bucket(repo)
        if not bucket:
            return set()
        return {ident for ident, row in bucket["candidates"].items() if ident in ids and row.get("provenanceReset")}

    def firstSeen(self, repo: str, ids: set[str]) -> dict[str, str]:
        """The first-seen version the journal holds for each of *ids* it knows."""
        bucket = self.bucket(repo)
        if not bucket:
            return {}
        return {ident: row["firstSeenVersion"] for ident, row in bucket["candidates"].items() if ident in ids}


# ---------------------------------------------------------------------------
# Stager - the seam batch.run_batch uses
# ---------------------------------------------------------------------------


class Stager:
    """Per-run staging state: annotates findings from the journal, decides hold/flush/urgent, builds the report."""

    def __init__(self, config: StagingConfig, journal: Journal | None = None):
        self.config = config
        if journal is None:
            if not config.journalPath:
                raise ValueError("staging requires a journal: pass --staging-journal (pending observations are durable state)")
            journal = Journal.load(config.journalPath, config.bootstrap, config.initialized)
        self.journal = journal
        self.rows: dict[str, dict] = {}
        self.prior: dict[str, dict] = {}
        self.current: dict[str, list[dict]] = {}
        self.seen: set[str] = set()
        self.closedDuringWrite: list[dict] = []

    @property
    def blocked(self) -> bool:
        return self.journal.blocked

    def blockedDetail(self) -> str:
        if self.journal.status == STATUSLOST:
            how = "Recover by re-dispatching with staging_bootstrap=true (re-observes current upstream state)."
        elif self.journal.status == STATUSCORRUPT:
            how = "Delete the damaged journal (and its cache entries), then re-dispatch with staging_bootstrap=true."
        else:
            how = "For a first run, re-dispatch with staging_bootstrap=true."
        return (f"staging journal is {self.journal.status}: {self.journal.detail}. The run stops before any GitHub "
                f"write, every suite is held and nothing is reset silently. {how}")

    def prepare(self, finding: dict, repo: str, rows: list[dict]) -> dict:
        """Annotate *finding* from the journal, before planning, so the flush is fed by pending observations."""
        self.seen.add(repo.lower())
        ids = {row["id"] for row in rows}
        self.current[repo] = rows
        if self.blocked:
            return finding
        # Recovery after a lost journal: every current candidate's first-seen provenance restarts now. Mark them.
        reset = set(ids) if self.journal.status == STATUSRECOVERY else self.journal.provenanceReset(repo, ids)
        if self.journal.bucket(repo) is None and not reset:
            return finding
        if self.journal.bucket(repo) is not None:
            self.prior[repo] = self.journal.window(repo, ids)
        return {**finding, "pendingFirstSeen": self.journal.firstSeen(repo, ids),
                "pendingRows": self.journal.pendingRows(repo, ids), "pendingProvenanceReset": sorted(reset)}

    def gate(self, finding: dict, plan: dict) -> dict:
        """Called for a suite whose plan would write (create/update). Returns the staging row (with ``decision``)."""
        repo = plan["suite"]
        now = self.config.asOf()
        ids = {row["id"] for row in self.current.get(repo, [])}
        if self.blocked:
            urgent = urgentReasons(finding)
            verdict = {"decision": DECISIONHOLD, "reasons": [f"journal-unavailable:{self.journal.status}"],
                       "pendingSince": None, "nextFlush": nextFlushDate(now, self.config), "maxHoldUntil": None}
            if urgent:
                verdict["urgentBlocked"] = urgent
        else:
            verdict = decide(finding, self.config, self.journal.pendingSince(repo))
            self.journal.observe(repo, finding, self.current.get(repo, []), now)
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
            **(self.journal.window(repo, ids) if not self.blocked else {}),
        }
        if not self.blocked and (self.journal.status == STATUSRECOVERY or (self.journal.bucket(repo) or {}).get("provenanceReset")):
            row["provenanceReset"] = True
        self.rows[repo] = row
        return row

    def settle(self, suiteRow: dict) -> None:
        """Record the final outcome for a suite; settle its pending observations once it was surfaced.

        A suite that settles without a write (noop, already processed) still reports what was pending, so a
        transient candidate is never dropped silently.
        """
        repo = suiteRow["suite"]
        row = self.rows.get(repo)
        prior = self.prior.get(repo)
        if row is None and prior is not None and suiteRow["outcome"] in SETTLEDOUTCOMES:
            row = self.rows[repo] = {
                "suite": repo, "planAction": suiteRow["action"], "version": suiteRow["version"], "decision": "settled",
                "reasons": [suiteRow["outcome"]], "outcome": None,
                "candidateIds": sorted(row["id"] for row in self.current.get(repo, [])), **prior,
            }
        if row is not None:
            row["outcome"] = suiteRow["outcome"]
            if suiteRow.get("closedDuringWrite"):
                row["closedDuringWrite"] = list(suiteRow["closedDuringWrite"])
                self.closedDuringWrite.append({"suite": repo, "closed": list(suiteRow["closedDuringWrite"]),
                                               "outcome": suiteRow["outcome"]})
            if suiteRow["outcome"] == "held":
                print(
                    f"::notice::{repo} {row['version']}: staged, not written ({','.join(row['reasons'])}). Next flush "
                    f"{row['nextFlush']}; deadline {row['maxHoldUntil'] or 'unknown'}.",
                    file=sys.stderr,
                )
        if suiteRow["outcome"] in SETTLEDOUTCOMES and not self.blocked:
            self.journal.clear(repo)

    def finish(self, report: dict, apply: bool) -> None:
        """Attach the staging section to *report*; persist the journal on an apply or explicit-bootstrap run."""
        now = self.config.asOf()
        absent: list[dict] = []
        # A run that stopped on a failed read has not seen every suite; absence would be an artefact, so say nothing.
        incomplete = any(entry.get("stopped") for entry in report.get("unknownEvidence", []))
        if not self.blocked and not incomplete:
            for repo, bucket in sorted(self.journal.data["repos"].items()):
                if repo in self.seen:
                    continue
                absent.append({"suite": repo, "pendingSince": bucket.get("pendingSince"),
                               "versionsObserved": [dict(r) for r in bucket["versions"]],
                               "transientCandidates": [dict(r) for _id, r in sorted(bucket["candidates"].items())]})
        rows = [self.rows[key] for key in sorted(self.rows)]
        report["staging"] = {
            "mode": self.config.mode,
            "asOf": isoTime(now),
            "flushWeekday": WEEKDAYS[self.config.flushWeekday],
            "windowDays": self.config.windowDays,
            "flushDay": isFlushDay(now, self.config),
            "journal": {"status": self.journal.status, "detail": self.journal.detail},
            "held": [row for row in rows if row["outcome"] == "held"],
            "flushed": [row for row in rows if row["decision"] == DECISIONFLUSH and row["outcome"] != "held"],
            "urgent": [row for row in rows if row["decision"] == DECISIONURGENT],
            "urgentBlocked": [row for row in rows if row.get("urgentBlocked")],
            "settled": [row for row in rows if row["decision"] == "settled"],
            "absent": absent,
            "closedDuringWrite": list(self.closedDuringWrite),
        }
        if not self.blocked and (apply or self.config.bootstrap) and self.config.journalPath:
            self.journal.save(self.config.journalPath)

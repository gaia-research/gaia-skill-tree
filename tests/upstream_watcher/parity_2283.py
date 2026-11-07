"""Dry-run parity harness for staged batching (#2283, founder ruling #12).

Runs the SAME recorded findings through three emitters and compares what each would write:

* ``legacy``  - the deployed fanout (``issuer.create_issues``), driven offline by an in-memory world;
* ``batch``   - ``batch.run_batch`` unstaged (``--child-mode batch``);
* ``staged``  - ``batch.run_batch`` with ``--staging weekly`` on a hold day, then on the flush day.

Parity means: every candidate the legacy fanout would file or adopt is a retained row in the batch record, at the
flush and on any single day, with its disposition (tracked child, new, suppressed) intact. Noise is measured as GitHub
writes. Nothing here touches GitHub: the legacy path runs against patched issuer helpers, the batch path against
``FakeGh``.

Run it for the evidence report::

    python tests/upstream_watcher/parity_2283.py > parity-report.json
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import pathlib
import sys
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for entry in (str(ROOT), str(HERE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from scripts.upstream_watcher import batch as bt  # noqa: E402
from scripts.upstream_watcher import issuer, staging  # noqa: E402
from upstream_fakes import FakeGh, fixture_issue_rows, fixture_registry_entries, index_from_entries  # noqa: E402

FIXTURE = json.loads((HERE / "fixtures" / "live_families.json").read_text(encoding="utf-8"))
TUESDAY = dt.datetime(2026, 11, 3, 6, 0, tzinfo=dt.timezone.utc)
MONDAY = dt.datetime(2026, 11, 9, 6, 0, tzinfo=dt.timezone.utc)


# ---------------------------------------------------------------------------
# Recorded findings
# ---------------------------------------------------------------------------


def liveFindings() -> list[dict]:
    """The four live umbrella families of the 2026-10-21 census, as the watcher saw them."""
    out = []
    for umbrella in FIXTURE["umbrellas"]:
        payload = bt.parse_payload(umbrella["body"])
        out.append({
            "finding_type": "update",
            "skillId": payload["skillId"],
            "currentVersion": payload["previousVersion"],
            "newVersion": payload["newVersion"],
            "releasedAt": payload["releasedAt"],
            "sourceUrl": payload["sourceUrl"],
            "mode": payload["mode"],
            "componentAdds": list(payload["componentAdds"]),
            "componentRemoves": list(payload["componentRemoves"]),
            "linkLiveness": [],
            "nameDrift": [],
        })
    return out


def nextFindings(version: str = "next", extra: int = 2, released: str = "2026-11-03T01:00:00Z") -> list[dict]:
    """The same families one release later: every recorded component stays and ``extra`` new ones appear."""
    out = []
    for finding in liveFindings():
        repo = finding["sourceUrl"].split("/releases/")[0].removeprefix("https://github.com/")
        out.append({
            **copy.deepcopy(finding),
            "currentVersion": finding["newVersion"],
            "newVersion": f"{finding['newVersion']}-{version}",
            "releasedAt": released,
            "sourceUrl": f"https://github.com/{repo}/releases/tag/{finding['newVersion']}-{version}",
            "componentAdds": finding["componentAdds"] + [f"parity-new-{n}" for n in range(extra)],
        })
    return out


# ---------------------------------------------------------------------------
# Legacy fanout, offline
# ---------------------------------------------------------------------------


class LegacyWorld:
    """Just enough GitHub for ``issuer.create_issues``: LIST snapshot, create, edit, comment. Counts every write."""

    def __init__(self, rows: list[dict]):
        self.rows = {row["number"]: copy.deepcopy(row) for row in rows}
        self.next = max(self.rows, default=5000) + 1
        self.created: list[dict] = []
        self.updated: list[int] = []
        self.comments = 0
        self.adopted: list[str] = []

    @property
    def writes(self) -> int:
        return len(self.created) + len(self.updated) + self.comments

    def snapshot(self, labels=issuer.IDEMPOTENCY_LABELS) -> dict:
        def names(row):
            return {label if isinstance(label, str) else label["name"] for label in row["labels"]}

        out = {label: [copy.deepcopy(r) for r in self.rows.values() if r["state"] == "open" and label in names(r)]
               for label in labels}
        out[issuer.CLOSED_BOOTSTRAP_KEY] = []
        return out

    def create(self, title, labels, body, dry_run, verbose=False):
        if dry_run:
            return None
        number = self.next
        self.next += 1
        self.rows[number] = {"number": number, "title": title, "state": "open", "labels": list(labels), "body": body,
                             "updated_at": "2026-11-03T00:00:00Z"}
        self.created.append({"number": number, "title": title})
        return number

    def update(self, number, title, body, comment=None, dry_run=False, verbose=False, add_labels=(), remove_labels=()):
        if not dry_run:
            self.rows[number].update({"title": title, "body": body})
            self.updated.append(number)
            self.comments += 1 if comment else 0
        return True

    def edit(self, number, children, dry_run):
        if not dry_run and children:
            self.comments += 1

    def run(self, findings: list[dict]) -> dict:
        real = issuer._find_existing_issue

        def watched(search, label, run_cache=None, snapshot=None):
            hit = real(search, label, run_cache, snapshot)
            if hit and label == "intake":
                self.adopted.append(search.removeprefix("[intake] "))
            return hit

        reset = mock.Mock()
        live = lambda number: {**self.rows[number], "labels": [{"name": l if isinstance(l, str) else l["name"]}
                                                                for l in self.rows[number]["labels"]]}
        with mock.patch.multiple(
            issuer, _open_snapshot=lambda labels=issuer.IDEMPOTENCY_LABELS: self.snapshot(labels),
            _create_issue=self.create, _update_issue=self.update, _edit_umbrella_body=self.edit,
            _live_issue=live, _fanout_approval_reset=reset, _find_existing_issue=watched,
        ):
            issuer.create_issues(findings, apply=True)
        return {
            "writes": self.writes,
            "issuesCreated": len(self.created),
            "children": sorted(row["title"].removeprefix("[intake] ") for row in self.created if row["title"].startswith("[intake]")),
            "adopted": sorted(set(self.adopted)),
        }


# ---------------------------------------------------------------------------
# Batch, offline
# ---------------------------------------------------------------------------


def liveGh() -> FakeGh:
    return FakeGh(fixture_issue_rows(FIXTURE))


def liveIndex() -> dict:
    return index_from_entries(fixture_registry_entries(FIXTURE))


def batchRows(gh: FakeGh) -> dict[str, dict]:
    """Every candidate row of every open canonical umbrella, keyed by candidate id (record comments included)."""
    rows = {}
    for issue in gh.issues.values():
        if issue["state"] != "open" or not issue["title"].startswith("[upstream] "):
            continue
        payload = bt.parse_payload(issue["body"])
        if payload:
            for row in bt.load_rows(gh, issue["number"], payload):
                rows[row["id"]] = {**row, "umbrella": issue["number"]}
    return rows


def runBatch(findings, gh, config=None, journal=None, apply=True):
    index = liveIndex()
    return bt.run_batch(findings, gh, apply=apply, index_loader=lambda: index, staging=config, journal=journal)


def candidateIds(findings: list[dict]) -> set[str]:
    out = set()
    for finding in findings:
        repo = finding["sourceUrl"].split("/releases/")[0].removeprefix("https://github.com/")
        out |= {f"{repo}:{slug}" for slug in finding["componentAdds"]}
    return out


def weekly(now: dt.datetime) -> staging.StagingConfig:
    return staging.StagingConfig(mode="weekly", now=now)


# ---------------------------------------------------------------------------
# Scenarios and report
# ---------------------------------------------------------------------------


def scenarioLiveFamilies() -> dict:
    """Day after the census: every family ships a new release with two new components."""
    findings = nextFindings()
    wanted = candidateIds(findings)

    legacy = LegacyWorld(fixture_issue_rows(FIXTURE)).run(findings)
    legacyCovered = {f"{finding['sourceUrl'].split('/releases/')[0].removeprefix('https://github.com/')}:{slug}"
                     for finding in findings for slug in finding["componentAdds"]
                     if f"{finding['skillId'].split('/')[0]}/{slug}" in set(legacy["children"]) | set(legacy["adopted"])}

    plainGh = liveGh()
    plainReport, _ = runBatch(nextFindings(), plainGh)
    plainRows = batchRows(plainGh)

    heldGh, journal = liveGh(), staging.Journal()
    heldReport, _ = runBatch(nextFindings(), heldGh, weekly(TUESDAY), journal)
    heldWrites = heldGh.write_count()
    flushReport, _ = runBatch(nextFindings(), heldGh, weekly(MONDAY), journal)
    stagedRows = batchRows(heldGh)

    return {
        "scenario": "live-families-next-release",
        "families": sorted(f["skillId"] for f in findings),
        "candidatesInFindings": len(wanted),
        "legacy": {"writes": legacy["writes"], "issuesCreated": legacy["issuesCreated"],
                   "childrenCreated": len(legacy["children"]), "childrenAdopted": len(legacy["adopted"]),
                   "candidatesCovered": len(legacyCovered)},
        "batch": {"writes": plainGh.write_count(), "issuesCreated": plainReport["issuesCreated"],
                  "rows": len(plainRows)},
        "staged": {"holdDayWrites": heldWrites, "heldSuites": len(heldReport["staging"]["held"]),
                   "flushDayWrites": heldGh.write_count() - heldWrites, "rows": len(stagedRows),
                   "flushedSuites": len(flushReport["staging"]["flushed"])},
        "parity": {
            "legacyCandidatesMissingFromBatch": sorted(legacyCovered - set(plainRows)),
            "legacyCandidatesMissingFromStaged": sorted(legacyCovered - set(stagedRows)),
            "stagedRowsEqualBatchRows": {k: (v["status"], v.get("child")) for k, v in stagedRows.items()}
            == {k: (v["status"], v.get("child")) for k, v in plainRows.items()},
        },
    }


def week() -> list[tuple[dt.datetime, str, list[str], list[dict]]]:
    """One review window of daily releases for one suite: Tue..Mon. ``transient`` exists only on Wednesday."""
    base = {"finding_type": "update", "skillId": "garrytan/gbrain", "currentVersion": "v0", "mode": "components",
            "componentRemoves": [], "linkLiveness": [], "nameDrift": []}
    adds = [["alpha"], ["alpha", "beta", "transient"], ["alpha", "beta"], ["alpha", "beta", "gamma"],
            ["alpha", "beta", "gamma"], ["alpha", "beta", "gamma", "delta"], ["alpha", "beta", "gamma", "delta"]]
    out = []
    for offset, slugs in enumerate(adds):
        day = dt.datetime(2026, 11, 3, 6, 0, tzinfo=dt.timezone.utc) + dt.timedelta(days=offset)
        version = f"v{offset + 1}"
        out.append((day, version, slugs, [{
            **base, "newVersion": version, "releasedAt": (day - dt.timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sourceUrl": f"https://github.com/garrytan/gbrain/releases/tag/{version}", "componentAdds": slugs}]))
    return out


def scenarioDailyWeek() -> dict:
    legacyWorld, legacyWrites = LegacyWorld([]), []
    legacyFiled: set[str] = set()
    for _day, _version, _slugs, findings in week():
        result = legacyWorld.run(copy.deepcopy(findings))
        legacyWrites.append(result["writes"])
        legacyFiled |= set(result["children"])

    unstaged, unstagedWrites = FakeGh(), []
    for _day, _version, _slugs, findings in week():
        before = unstaged.write_count()
        bt.run_batch(findings, unstaged, apply=True, index_loader=lambda: index_from_entries([]))
        unstagedWrites.append(unstaged.write_count() - before)

    gh, journal, perDay = FakeGh(), staging.Journal(), []
    flushReport = None
    for day, _version, _slugs, findings in week():
        before = gh.write_count()
        report, code = bt.run_batch(findings, gh, apply=True, index_loader=lambda: index_from_entries([]),
                                    staging=weekly(day), journal=journal)
        assert code == 0
        perDay.append(gh.write_count() - before)
        flushReport = report
    rows, unstagedRows = batchRows(gh), batchRows(unstaged)
    lastAdds = {f"garrytan/gbrain:{slug}" for slug in week()[-1][2]}
    legacyIds = {f"garrytan/gbrain:{c.split('/')[1]}" for c in legacyFiled}
    transient = [row["id"] for row in flushReport["staging"]["flushed"][0]["transientCandidates"]]
    strip = lambda table: {k: {f: v for f, v in row.items() if f != "umbrella"} for k, row in table.items()}
    return {
        "scenario": "daily-releases-over-one-window",
        "days": [day.strftime("%a %Y-%m-%d") for day, *_ in week()],
        "legacy": {"writesPerDay": legacyWrites, "totalWrites": sum(legacyWrites),
                   "childIssuesFiled": len(legacyFiled)},
        "batch": {"writesPerDay": unstagedWrites, "totalWrites": sum(unstagedWrites)},
        "staged": {"writesPerDay": perDay, "totalWrites": sum(perDay), "umbrellas": len(gh.by_title("[upstream]")),
                   "children": len(gh.by_title("[intake]"))},
        "parity": {
            "candidatesAtFlushMissingFromRows": sorted(lastAdds - set(rows)),
            "legacyFiledMissingFromStagedRows": sorted(legacyIds - set(rows)),
            "rowsNotInLegacyOrFlushedFinding": sorted(set(rows) - lastAdds - legacyIds),
            "stagedRowsEqualDailyUnstagedRows": strip(rows) == strip(unstagedRows),
            "transientRetainedAsRow": transient,
        },
    }


def buildReport() -> dict:
    return {"ruling": "founder ruling #12 (#2283)", "scenarios": [scenarioLiveFamilies(), scenarioDailyWeek()]}


if __name__ == "__main__":
    print(json.dumps(buildReport(), indent=2, ensure_ascii=False))

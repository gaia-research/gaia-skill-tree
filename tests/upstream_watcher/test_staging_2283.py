"""Staged batching (#2283, founder ruling #12): window, urgent bypass, durable pending observations, fail-closed
journal, closed umbrellas (including closure mid-write), the V2 gate and the switch."""

import datetime as dt
import json
import pathlib

import pytest
import yaml

from scripts.upstream_watcher import batch as bt
from scripts.upstream_watcher import staging as st
from scripts.upstream_watcher import watcher
from scripts.upstream_watcher.batch import parse_payload, run_batch
from tests.upstream_watcher.test_watcher_workflows import _run_block_with
from upstream_fakes import FakeGh, index_from_entries

UTC = dt.timezone.utc
TUE = dt.datetime(2026, 11, 3, 6, 0, tzinfo=UTC)
WED = TUE + dt.timedelta(days=1)
SUN = dt.datetime(2026, 11, 8, 6, 0, tzinfo=UTC)
MON = dt.datetime(2026, 11, 9, 6, 0, tzinfo=UTC)
NEXTTUE = TUE + dt.timedelta(days=7)
PREFIX = "[upstream] garrytan/gbrain → "
REPO = "garrytan/gbrain"
ROOT = pathlib.Path(__file__).resolve().parents[2]


def finding(version="v1", adds=("alpha",), released="2026-11-03T01:00:00Z", liveness=(), removes=(), drift=()):
    return {
        "finding_type": "update", "skillId": "garrytan/gbrain", "currentVersion": "v0", "newVersion": version,
        "releasedAt": released, "sourceUrl": f"https://github.com/garrytan/gbrain/releases/tag/{version}",
        "mode": "components", "componentAdds": list(adds), "componentRemoves": list(removes),
        "linkLiveness": list(liveness), "nameDrift": list(drift),
    }


def dead(status, skill="garrytan/alpha"):
    return {"skillId": skill, "url": "https://github.com/garrytan/gbrain/blob/main/skills/alpha/SKILL.md",
            "rawUrl": "https://raw.githubusercontent.com/garrytan/gbrain/main/skills/alpha/SKILL.md", "status": status}


def weekly(now, **kw):
    return st.StagingConfig(mode="weekly", now=now, **kw)


def go(gh, findings, config=None, journal=None, apply=True, entries=()):
    """Run the batch. An active config without a journal gets a fresh in-memory one (continuity needs a shared one)."""
    if config is not None and config.active and journal is None and not config.journalPath:
        journal = st.Journal()
    index = index_from_entries(list(entries))
    return run_batch(findings, gh, apply=apply, index_loader=lambda: index, staging=config, journal=journal)


def open_umbrellas(gh):
    return [r for r in gh.issues.values() if r["state"] == "open" and r["title"].startswith("[upstream] ")]


def rows_of(gh):
    return {row["id"]: row for row in parse_payload(open_umbrellas(gh)[0]["body"])["candidates"]}


def rowsFrom(gh, number):
    payload = parse_payload(gh.issues[number]["body"])
    return {row["id"]: row for row in bt.load_rows(gh, number, payload)}


# --- the window -----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("now,pending,decision,reason", [
    (TUE, None, "hold", "within-review-window"),
    (SUN, TUE, "hold", "within-review-window"),
    (MON, TUE, "flush", "flush-day"),
    # the deadline is one window after the FIRST pending observation, so a missed flush day cannot stretch a hold
    (NEXTTUE, TUE, "flush", "window-elapsed"),
    (NEXTTUE, TUE + dt.timedelta(seconds=1), "hold", "within-review-window"),
    (WED, TUE, "hold", "within-review-window"),
])
def test_window_decision_runs_from_the_first_pending_observation(now, pending, decision, reason):
    verdict = st.decide(finding(), weekly(now), pending)
    assert (verdict["decision"], verdict["reasons"]) == (decision, [reason])


@pytest.mark.parametrize("released", ["2026-10-01T00:00:00Z", "", "not-a-date", "2020-01-01T00:00:00Z"])
def test_release_age_never_releases_a_hold_only_observation_age_does(released):
    # B1: an old release plus a new non-urgent change observed on a Tuesday holds until Monday.
    verdict = st.decide(finding(released=released, liveness=[dead(403)]), weekly(TUE), None)
    assert verdict["decision"] == "hold" and verdict["reasons"] == ["within-review-window"]
    assert verdict["maxHoldUntil"] == "2026-11-10T06:00:00Z"


def test_old_release_and_a_new_non_urgent_change_hold_until_monday_end_to_end():
    gh, journal = FakeGh(), st.Journal()
    old = "2026-09-01T00:00:00Z"
    report, _ = go(gh, [finding("v1", ["alpha"], released=old, liveness=[dead(429)], removes=["gone"])], weekly(TUE), journal)
    assert gh.write_count() == 0 and report["suites"][0]["outcome"] == "held"
    assert report["staging"]["held"][0]["pendingSince"] == "2026-11-03T06:00:00Z"
    go(gh, [finding("v2", ["alpha"], released=old)], weekly(SUN), journal)
    assert gh.write_count() == 0
    go(gh, [finding("v2", ["alpha"], released=old)], weekly(MON), journal)
    assert [w[0] for w in gh.writes] == ["create"]


def test_the_deadline_is_anchored_at_the_first_observation_and_does_not_slide(tmp_path):
    path = tmp_path / "journal.json"
    gh = FakeGh()
    config = weekly(TUE, journalPath=str(path), bootstrap=True)
    go(gh, [finding("v1")], config)
    for offset in (1, 2, 3):  # daily releases keep arriving; the clock must stay at Tuesday
        day = TUE + dt.timedelta(days=offset)
        go(gh, [finding(f"v{offset + 1}")], weekly(day, journalPath=str(path)))
    assert gh.write_count() == 0
    assert st.Journal.load(path).pendingSince(REPO) == TUE, "persisted, and read back by the next process"
    # Monday was missed (no run). The next Tuesday is exactly one window after the first observation.
    report, _ = go(gh, [finding("v9")], weekly(NEXTTUE, journalPath=str(path)))
    assert report["staging"]["flushed"][0]["reasons"] == ["window-elapsed"]
    assert [w[0] for w in gh.writes] == ["create"]


# --- urgent: deliberately narrow ------------------------------------------------------------------------------------


@pytest.mark.parametrize("status", [404, 410])
def test_a_dead_tracked_component_link_is_urgent(status):
    assert st.urgentReasons(finding(liveness=[dead(status)])) == [f"dead-link:garrytan/alpha:{status}"]
    assert st.decide(finding(liveness=[dead(status)]), weekly(TUE))["decision"] == "urgent"


@pytest.mark.parametrize("case", [
    {"liveness": [dead(403)]}, {"liveness": [dead(429)]}, {"liveness": [dead(500)]}, {"liveness": [dead(503)]},
    {"liveness": [dead(301)]}, {"liveness": [dead("network_error")]}, {"liveness": [dead(True)]},
    {"liveness": [dead(None)]}, {"adds": ["a", "b", "c"]}, {"removes": ["gone"]},
    {"drift": [{"skillId": "garrytan/alpha", "registrySlug": "a", "sanitizedName": "b"}]},
    {"version": "v99"}, {},
])
def test_nothing_else_is_urgent(case):
    assert st.urgentReasons(finding(**case)) == []
    assert st.decide(finding(**case), weekly(TUE))["decision"] == "hold"


def test_urgent_bypasses_the_hold_once_and_an_unchanged_dead_link_never_writes_again():
    gh, journal = FakeGh(), st.Journal()
    report, code = go(gh, [finding(liveness=[dead(404)])], weekly(TUE), journal)
    assert code == 0 and [w[0] for w in gh.writes] == ["create"]
    assert [row["reasons"] for row in report["staging"]["urgent"]] == [["dead-link:garrytan/alpha:404"]]
    assert report["staging"]["held"] == []
    before = gh.write_count()
    report2, _ = go(gh, [finding(liveness=[dead(404)])], weekly(WED), journal)
    assert gh.write_count() == before, "the same dead link on the next day is a no-op, not a second urgent write"
    assert report2["suites"][0]["outcome"] == "noop"


def test_urgent_writes_the_one_umbrella_it_never_opens_a_second_or_a_child():
    gh = FakeGh()
    go(gh, [finding("v1", ["alpha"])], weekly(MON))
    number = open_umbrellas(gh)[0]["number"]
    go(gh, [finding("v2", ["alpha", "beta"], liveness=[dead(410)])], weekly(TUE))
    assert [row["number"] for row in open_umbrellas(gh)] == [number]
    assert open_umbrellas(gh)[0]["title"] == PREFIX + "v2"
    assert not gh.by_title("[intake]")


# --- hold: planned and observed, never written ----------------------------------------------------------------------


def test_off_and_none_are_the_unstaged_behaviour_with_no_staging_report():
    a, b, c = FakeGh(), FakeGh(), FakeGh()
    ra, _ = go(a, [finding()], None)
    rb, _ = go(b, [finding()], st.StagingConfig())
    rc, _ = go(c, [finding()], st.StagingConfig(mode="off", now=TUE))
    assert [w[0] for w in a.writes] == [w[0] for w in b.writes] == [w[0] for w in c.writes] == ["create"]
    assert "staging" not in ra and "staging" not in rb and "staging" not in rc
    assert not st.StagingConfig().active and weekly(TUE).active


def test_hold_makes_zero_github_writes_and_reports_the_observation():
    gh = FakeGh()
    report, code = go(gh, [finding("v1", ["alpha", "beta"])], weekly(TUE))
    assert code == 0 and gh.write_count() == 0
    assert report["issuesCreated"] == 0 and report["issuesUpdated"] == 0
    assert report["suites"][0]["outcome"] == "held"
    [row] = report["staging"]["held"]
    assert row["suite"] == REPO and row["version"] == "v1" and row["planAction"] == "create"
    assert row["candidateIds"] == ["garrytan/gbrain:alpha", "garrytan/gbrain:beta"]
    assert row["nextFlush"] == "2026-11-09" and row["maxHoldUntil"] == "2026-11-10T06:00:00Z"
    assert report["staging"]["flushDay"] is False and report["staging"]["flushWeekday"] == "monday"
    assert report["staging"]["journal"]["status"] == "ok"


def test_dry_run_flush_day_plans_the_write_without_making_it():
    gh = FakeGh()
    report, _ = go(gh, [finding()], weekly(MON), apply=False)
    assert gh.write_count() == 0
    assert report["suites"][0]["outcome"] == "planned" and report["issuesCreated"] == 1
    assert report["staging"]["flushDay"] is True and len(report["staging"]["flushed"]) == 1


def test_hold_does_not_reset_an_approved_umbrella_but_the_flush_does():
    gh = FakeGh()
    go(gh, [finding("v1", ["alpha"])], weekly(MON))
    number = open_umbrellas(gh)[0]["number"]
    gh.edit_labels(number, add=["upstream:approved"])
    gh.writes.clear()
    journal = st.Journal()
    go(gh, [finding("v2", ["alpha", "beta"])], weekly(TUE), journal)
    assert gh.write_count() == 0
    assert "upstream:approved" in [label["name"] for label in gh.issues[number]["labels"]]
    go(gh, [finding("v2", ["alpha", "beta"])], weekly(MON + dt.timedelta(days=7)), journal)
    labels = [label["name"] for label in gh.issues[number]["labels"]]
    assert "upstream:approved" not in labels and "upstream:needs-info" in labels


def test_a_week_of_daily_releases_is_one_write_on_the_flush_day_into_one_umbrella():
    gh, journal = FakeGh(), st.Journal()
    for offset in range(7):
        day = TUE + dt.timedelta(days=offset)
        released = (day - dt.timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        go(gh, [finding(f"v{offset + 1}", ["alpha", "beta"], released=released)], weekly(day), journal)
    assert [w[0] for w in gh.writes] == ["create"]
    assert len(open_umbrellas(gh)) == 1 and open_umbrellas(gh)[0]["title"] == PREFIX + "v7"
    assert not gh.by_title("[intake]")


def test_flush_updates_the_existing_open_umbrella_in_place():
    gh, journal = FakeGh(), st.Journal()
    go(gh, [finding("v1", ["alpha"])], weekly(MON), journal)
    number = open_umbrellas(gh)[0]["number"]
    go(gh, [finding("v2", ["alpha", "beta"])], weekly(WED), journal)
    go(gh, [finding("v2", ["alpha", "beta"])], weekly(MON + dt.timedelta(days=7)), journal)
    assert [row["number"] for row in open_umbrellas(gh)] == [number]
    payload = parse_payload(gh.issues[number]["body"])
    assert payload["newVersion"] == "v2"
    assert [row["id"] for row in payload["candidates"]] == ["garrytan/gbrain:alpha", "garrytan/gbrain:beta"]
    assert "pendingRows" not in gh.issues[number]["body"] and "pendingFirstSeen" not in gh.issues[number]["body"]


# --- closed umbrella is a completed epic (ruling #6) ----------------------------------------------------------------


def test_a_closed_umbrella_is_never_touched_and_new_changes_start_a_new_batch_after_the_window():
    gh, journal = FakeGh(), st.Journal()
    go(gh, [finding("v1", ["alpha", "beta"])], weekly(MON), journal)
    closed = open_umbrellas(gh)[0]["number"]
    gh.issues[closed]["state"] = "closed"
    snapshot = json.dumps(gh.issues[closed], sort_keys=True)
    gh.writes.clear()

    held, _ = go(gh, [finding("v2", ["alpha", "beta", "gamma"])], weekly(TUE), journal)
    assert gh.write_count() == 0 and held["suites"][0]["outcome"] == "held"
    assert held["staging"]["held"][0]["planAction"] == "create", "a closed umbrella is not a hold or update target"

    go(gh, [finding("v2", ["alpha", "beta", "gamma"])], weekly(MON + dt.timedelta(days=7)), journal)
    assert [w[0] for w in gh.writes] == ["create"] and all(w[1] != closed for w in gh.writes if w[0] != "create")
    assert json.dumps(gh.issues[closed], sort_keys=True) == snapshot, "the closed epic is preserved byte for byte"
    [new] = open_umbrellas(gh)
    assert new["number"] != closed and new["title"] == PREFIX + "v2"
    carried = {row["id"]: row for row in parse_payload(new["body"])["candidates"]}
    assert carried["garrytan/gbrain:alpha"]["carriedFrom"] == f"#{closed}"
    assert "garrytan/gbrain:gamma" in carried


def test_a_finding_a_closed_umbrella_already_processed_is_neither_held_nor_recreated():
    gh = FakeGh()
    go(gh, [finding("v1", ["alpha"])], weekly(MON))
    gh.issues[open_umbrellas(gh)[0]["number"]]["state"] = "closed"
    report, _ = go(gh, [finding("v1", ["alpha"])], weekly(TUE))
    assert report["suites"][0]["outcome"] == "suppressed-processed"
    assert report["staging"]["held"] == [] and report["suppressedProcessed"]


class ClosingGh(FakeGh):
    """FakeGh that logs reads and writes and can close an issue when its Nth get_issue read happens (B4)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = []
        self.gets = 0
        self.closeAtGet = None
        self.closeNumber = None
        self.onClose = None

    def get_issue(self, number):
        self.gets += 1
        if self.closeAtGet == self.gets and self.closeNumber is not None:
            self.issues[self.closeNumber]["state"] = "closed"
            if self.onClose:
                self.onClose(self.issues[self.closeNumber])
        self.log.append(("get", self.gets, number))
        return super().get_issue(number)

    def comment(self, number, body):
        self.log.append(("write", "comment", number))
        return super().comment(number, body)

    def edit_issue(self, number, title, body):
        self.log.append(("write", "edit_issue", number))
        return super().edit_issue(number, title, body)

    def edit_labels(self, number, add=(), remove=()):
        self.log.append(("write", "edit_labels", number))
        return super().edit_labels(number, add=add, remove=remove)


def closureWorld(approved):
    gh = ClosingGh()
    go(gh, [finding("v1", ["alpha"])], None)
    number = open_umbrellas(gh)[0]["number"]
    if approved:
        gh.edit_labels(number, add=["upstream:approved"])
    gh.log.clear()
    gh.writes.clear()
    return gh, number


@pytest.mark.parametrize("approved", [False, True])
def test_closure_between_the_plan_read_and_each_mutation_aborts_replans_and_reports(approved):
    probe, number = closureWorld(approved)
    go(probe, [finding("v2", ["alpha", "beta"])], weekly(MON))
    mutations = [i for i, entry in enumerate(probe.log) if entry[0] == "write" and entry[2] == number]
    assert len(mutations) == (3 if approved else 2), probe.log
    assert all(probe.log[i - 1][0] == "get" and probe.log[i - 1][2] == number for i in mutations), (
        "every umbrella mutation is immediately preceded by a re-read of that umbrella")
    # the read just before mutation k is the one the human's close must win against; k == -1 is the pre-write read
    cases = [(probe.log[i - 1][1], index) for index, i in enumerate(mutations)]
    cases.append((next(entry[1] for entry in probe.log if entry[0] == "get" and entry[2] == number), -1))
    for closeAt, index in cases:
        gh, number = closureWorld(approved)
        gh.closeNumber, gh.closeAtGet = number, gh.gets + closeAt
        report, code = go(gh, [finding("v2", ["alpha", "beta"])], weekly(MON))
        assert code == 0, (index, report["unknownEvidence"])
        assert gh.issues[number]["state"] == "closed"
        onOld = [entry for entry in gh.log if entry[0] == "write" and entry[2] == number]
        assert len(onOld) == max(index, 0), f"mutation {index} and every later one on the closed umbrella is aborted"
        [new] = open_umbrellas(gh)
        assert new["number"] != number and new["title"] == PREFIX + "v2", "re-planned as a new batch"
        assert report["staging"]["closedDuringWrite"] == [{"suite": REPO, "closed": [number], "outcome": "created"}]
        assert report["suites"][0]["outcome"] == "created" and report["issuesCreated"] == 1


def test_closure_whose_closed_umbrella_already_records_the_finding_writes_nothing_more():
    # The human closes the umbrella as completed, and what they closed already records exactly this v2 finding.
    other = FakeGh()
    go(other, [finding("v2", ["alpha"])], None)
    v2 = open_umbrellas(other)[0]
    gh, number = closureWorld(False)
    gh.closeNumber, gh.closeAtGet = number, gh.gets + 1
    gh.onClose = lambda issue: issue.update(title=v2["title"], body=v2["body"])
    report, code = go(gh, [finding("v2", ["alpha"])], weekly(MON))
    assert code == 0 and gh.issues[number]["state"] == "closed"
    assert report["suites"][0]["outcome"] == "suppressed-processed" and gh.write_count() == 0
    assert report["staging"]["closedDuringWrite"][0]["closed"] == [number]


# --- durable pending observations feed the flush --------------------------------------------------------------------


def candidateRows(version, adds):
    return bt.candidate_rows(finding(version, adds))


def test_journal_deduplicates_versions_and_candidates_but_keeps_first_and_last_seen():
    journal = st.Journal()
    for day, version in ((TUE, "v1"), (TUE + dt.timedelta(hours=3), "v1"), (WED, "v1"), (WED, "v2")):
        journal.observe(REPO, finding(version, ["alpha"]), candidateRows(version, ["alpha"]), day)
    bucket = journal.data["repos"][REPO]
    assert [row["version"] for row in bucket["versions"]] == ["v1", "v2"]
    v1 = bucket["versions"][0]
    assert v1["observationDays"] == 2 and v1["firstObserved"] == "2026-11-03T06:00:00Z"
    assert v1["lastObserved"] == "2026-11-04T06:00:00Z"
    alpha = bucket["candidates"]["garrytan/gbrain:alpha"]
    assert alpha["firstSeenVersion"] == "v1" and alpha["lastSeenVersion"] == "v2" and alpha["observationDays"] == 2
    assert list(bucket["candidates"]) == ["garrytan/gbrain:alpha"], "one entry per candidate, however often it is seen"
    assert bucket["pendingSince"] == "2026-11-03T06:00:00Z", "later observations never move the clock"


def test_a_rerun_in_the_same_day_does_not_change_the_journal_or_the_report_rows():
    gh, journal = FakeGh(), st.Journal()
    first, _ = go(gh, [finding("v1", ["alpha"])], weekly(TUE), journal)
    second, _ = go(gh, [finding("v1", ["alpha"])], weekly(TUE + dt.timedelta(hours=2)), journal)
    assert gh.write_count() == 0
    alpha = journal.data["repos"][REPO]["candidates"]["garrytan/gbrain:alpha"]
    assert alpha["observationDays"] == 1 and alpha["lastObserved"] == "2026-11-03T08:00:00Z"
    assert first["staging"]["held"][0]["candidateIds"] == second["staging"]["held"][0]["candidateIds"]


def weekAdds():
    """Daily releases Tue..Mon. `ephemeral` exists only on Wednesday; `delta` arrives on Saturday."""
    return [["alpha"], ["alpha", "beta", "ephemeral"], ["alpha", "beta"], ["alpha", "beta", "gamma"],
            ["alpha", "beta", "gamma"], ["alpha", "beta", "gamma", "delta"], ["alpha", "beta", "gamma", "delta"]]


def runWeek(gh, config, journal=None):
    reports = []
    for offset, adds in enumerate(weekAdds()):
        day = TUE + dt.timedelta(days=offset)
        reports.append(go(gh, [finding(f"v{offset + 1}", adds)], config(day) if config else None, journal)[0])
    return reports


def test_full_row_parity_staged_week_equals_the_rows_daily_unstaged_runs_accumulate():
    unstaged = FakeGh()
    runWeek(unstaged, None)
    staged = FakeGh()
    runWeek(staged, weekly, st.Journal())
    assert [w[0] for w in unstaged.writes].count("create") == 1 and len(unstaged.writes) > 7, "daily unstaged runs write every day"
    assert [w[0] for w in staged.writes] == ["create"]
    want, got = rows_of(unstaged), rows_of(staged)
    assert got == want, "every field of every row, including first/last seen, status, child and precheck"
    assert "garrytan/gbrain:ephemeral" in got, "rows are never dropped: the vanished candidate stays visible"
    assert got["garrytan/gbrain:ephemeral"]["firstSeenVersion"] == "v2" == got["garrytan/gbrain:ephemeral"]["lastSeenVersion"]
    assert got["garrytan/gbrain:delta"]["firstSeenVersion"] == "v6"
    assert got["garrytan/gbrain:beta"]["firstSeenVersion"] == "v2" and got["garrytan/gbrain:beta"]["lastSeenVersion"] == "v7"


def test_transients_are_reported_with_their_provenance_and_the_journal_is_settled_by_the_write():
    gh, journal = FakeGh(), st.Journal()
    reports = runWeek(gh, weekly, journal)
    [row] = reports[-1]["staging"]["flushed"]
    assert [t["id"] for t in row["transientCandidates"]] == ["garrytan/gbrain:ephemeral"]
    assert row["transientCandidates"][0]["firstSeenVersion"] == "v2"
    assert [v["version"] for v in row["versionsObserved"]][:3] == ["v1", "v2", "v3"]
    assert row["pendingSince"] == "2026-11-03T06:00:00Z"
    assert REPO not in journal.data["repos"]


def test_dispositions_and_first_seen_provenance_survive_held_days_and_the_flush():
    gh = FakeGh([{
        "number": 41, "title": "[intake] garrytan/rejected-one", "state": "closed",
        "labels": [{"name": "upstream:child"}, {"name": "upstream:rejected"}],
        "body": "**Suggested ID:** `garrytan/rejected-one`\n\n### Evidence\n\n"
                "- **url:** https://github.com/garrytan/gbrain/blob/main/skills/rejected-one/SKILL.md\n",
    }])
    go(gh, [finding("v1", ["alpha", "beta", "rejected-one"])], None)
    before = rows_of(gh)
    assert before["garrytan/gbrain:rejected-one"]["status"] == "rejected"
    gh.writes.clear()
    journal = st.Journal()
    adds = ["alpha", "beta", "rejected-one", "delta"]
    for offset, version in enumerate(("v2", "v3", "v4")):
        go(gh, [finding(version, adds)], weekly(TUE + dt.timedelta(days=offset)), journal)
    assert gh.write_count() == 0
    go(gh, [finding("v5", adds)], weekly(MON), journal)
    after = rows_of(gh)
    assert after["garrytan/gbrain:rejected-one"]["status"] == "rejected"
    for ident in ("garrytan/gbrain:alpha", "garrytan/gbrain:beta"):
        assert after[ident]["firstSeenVersion"] == "v1" and after[ident]["lastSeenVersion"] == "v5"
        assert after[ident]["status"] == before[ident]["status"]
    # B2: delta was first observed on the held Tuesday (v2), not at the flush (v5).
    assert after["garrytan/gbrain:delta"]["firstSeenVersion"] == "v2"
    assert after["garrytan/gbrain:delta"]["lastSeenVersion"] == "v5"


def test_an_escalated_row_keeps_its_child_across_the_staged_flush():
    gh = FakeGh()
    go(gh, [finding("v1", ["alpha", "beta"])], None)
    umbrella = open_umbrellas(gh)[0]
    child = gh.create_issue("[intake] garrytan/alpha", ["intake", "needs-triage", "upstream:child"],
                            f"> Auto-populated by upstream watcher. Umbrella: #{umbrella['number']}.\n\n"
                            "**Suggested ID:** `garrytan/alpha`\n\n### Evidence\n\n"
                            "- **url:** https://github.com/garrytan/gbrain/blob/main/skills/alpha/SKILL.md\n")
    go(gh, [finding("v1", ["alpha", "beta"])], None)  # re-adopts the open child as `tracked`
    assert rows_of(gh)["garrytan/gbrain:alpha"]["child"] == child
    gh.writes.clear()
    journal = st.Journal()
    go(gh, [finding("v2", ["alpha", "beta", "gamma"])], weekly(TUE), journal)
    assert gh.write_count() == 0
    go(gh, [finding("v2", ["alpha", "beta", "gamma"])], weekly(MON), journal)
    row = rows_of(gh)["garrytan/gbrain:alpha"]
    assert row["child"] == child and row["status"] == "tracked"
    assert not [w for w in gh.writes if w[0] == "create"], "no second child for an already-tracked candidate"


def test_transients_are_reported_when_the_fresh_plan_is_a_noop():
    # The umbrella already holds the vanished row, so the fresh plan is a no-op: nothing to write, yet the pending
    # observation must still be reported (not silently dropped) and then settled.
    gh = FakeGh()
    go(gh, [finding("v1", ["alpha", "ephemeral"])], None)
    go(gh, [finding("v2", ["alpha"])], None)
    assert "garrytan/gbrain:ephemeral" in rows_of(gh)
    journal = st.Journal()
    journal.observe(REPO, finding("v1", ["alpha", "ephemeral"]), candidateRows("v1", ["alpha", "ephemeral"]), TUE)
    gh.writes.clear()
    report, _ = go(gh, [finding("v2", ["alpha"])], weekly(WED), journal)
    assert report["suites"][0]["outcome"] == "noop" and gh.write_count() == 0
    [row] = report["staging"]["settled"]
    assert [t["id"] for t in row["transientCandidates"]] == ["garrytan/gbrain:ephemeral"]
    assert REPO not in journal.data["repos"]


def test_a_finding_a_closed_umbrella_suppresses_is_not_suppressed_while_pending_rows_are_uncarried():
    # The closed umbrella records the v2 finding but NOT the candidate the journal saw earlier. The pending row must
    # not be dropped: the finding is not "processed", a new batch is started at the flush, and the row rides in it.
    gh = FakeGh()
    journal = st.Journal()
    go(gh, [finding("v1", ["alpha", "ephemeral"])], weekly(TUE), journal)
    go(gh, [finding("v2", ["alpha"])], None)
    closed = open_umbrellas(gh)[0]["number"]
    gh.issues[closed]["state"] = "closed"
    gh.writes.clear()
    report, _ = go(gh, [finding("v2", ["alpha"])], weekly(WED), journal)
    assert report["suites"][0]["outcome"] == "held" and gh.write_count() == 0
    assert report["staging"]["held"][0]["planAction"] == "create", "a new batch, not suppressed-processed"
    assert "garrytan/gbrain:ephemeral" in journal.data["repos"][REPO]["candidates"], "still pending"
    go(gh, [finding("v2", ["alpha"])], weekly(MON), journal)
    [new] = open_umbrellas(gh)
    assert new["number"] != closed
    carried = rows_of(gh)
    assert carried["garrytan/gbrain:ephemeral"]["firstSeenVersion"] == "v1"
    assert REPO not in journal.data["repos"], "cleared only now, once the flush carried it"


def test_a_suppressed_finding_clears_pending_rows_only_when_the_closed_umbrella_demonstrably_carries_them():
    gh = FakeGh()
    go(gh, [finding("v1", ["alpha", "ephemeral"])], None)   # unstaged daily runs keep the vanished row
    go(gh, [finding("v2", ["alpha"])], None)
    assert "garrytan/gbrain:ephemeral" in rows_of(gh)
    gh.issues[open_umbrellas(gh)[0]["number"]]["state"] = "closed"
    journal = st.Journal()
    journal.observe(REPO, finding("v1", ["alpha", "ephemeral"]), candidateRows("v1", ["alpha", "ephemeral"]), TUE)
    gh.writes.clear()
    report, _ = go(gh, [finding("v2", ["alpha"])], weekly(WED), journal)
    assert report["suites"][0]["outcome"] == "suppressed-processed" and gh.write_count() == 0
    [row] = report["staging"]["settled"]
    assert [t["id"] for t in row["transientCandidates"]] == ["garrytan/gbrain:ephemeral"]
    assert REPO not in journal.data["repos"], "carried by the closed umbrella's rows: demonstrably incorporated"


def test_pending_observations_for_a_suite_with_no_finding_are_reported_every_run_and_never_expire():
    gh = FakeGh()
    journal = st.Journal()
    go(gh, [finding("v1", ["alpha", "ephemeral"])], weekly(TUE), journal)
    snapshot = json.dumps(journal.data, sort_keys=True)
    for days in (1, 8, 29, 120, 400):
        report, _ = go(gh, [], weekly(TUE + dt.timedelta(days=days)), journal)
        [absent] = report["staging"]["absent"]
        assert absent["suite"] == REPO
        assert [t["id"] for t in absent["transientCandidates"]] == ["garrytan/gbrain:alpha", "garrytan/gbrain:ephemeral"]
        assert "expired" not in report["staging"]
    assert json.dumps(journal.data, sort_keys=True) == snapshot, "prolonged absence changes nothing"


def test_after_a_long_absence_a_returning_finding_flushes_every_pending_row_with_full_row_parity():
    unstaged = FakeGh()
    go(unstaged, [finding("v1", ["alpha", "ephemeral"])], None)
    go(unstaged, [finding("v2", ["alpha", "beta"])], None)
    gh = FakeGh()
    journal = st.Journal()
    go(gh, [finding("v1", ["alpha", "ephemeral"])], weekly(TUE), journal)
    go(gh, [], weekly(TUE + dt.timedelta(days=60)), journal)           # absent for two months
    report, _ = go(gh, [finding("v2", ["alpha", "beta"])], weekly(MON + dt.timedelta(days=70)), journal)
    assert [w[0] for w in gh.writes] == ["create"] and report["staging"]["flushed"][0]["reasons"] in (["flush-day"], ["window-elapsed"])
    assert rows_of(gh) == rows_of(unstaged)
    assert REPO not in journal.data["repos"]


@pytest.mark.parametrize("failure", ["registry", "list", "get"])
def test_a_failed_read_or_precheck_never_clears_or_expires_pending_rows(tmp_path, failure):
    from scripts.upstream_watcher import prechecks

    path = tmp_path / "journal.json"
    journal = st.Journal()
    old = TUE - dt.timedelta(days=29)
    journal.observe(REPO, finding("v1", ["alpha", "ephemeral"]), candidateRows("v1", ["alpha", "ephemeral"]), old)
    journal.observe("other/suite", finding("v1", ["x"]), candidateRows("v1", ["x"]), old)
    journal.save(path)
    before = json.loads(path.read_text())
    gh = FakeGh()
    loader = lambda: index_from_entries([])
    if failure == "registry":
        def loader():
            raise prechecks.RegistryUnreadable("registry unreadable (test)")
    elif failure == "list":
        gh.fail_list = True
    else:  # a get/precheck read fails after the plan started: the suite's child probe
        go(gh, [finding("v1", ["alpha"])], None)
        gh.fail_get = True
    report, code = run_batch([finding("v2", ["alpha", "ephemeral"])], gh, apply=True, index_loader=loader,
                             staging=weekly(MON, journalPath=str(path)))
    assert code == 3
    after = json.loads(path.read_text())
    assert after["repos"].keys() == before["repos"].keys(), "no entry was dropped"
    assert after["repos"][REPO]["candidates"].keys() == before["repos"][REPO]["candidates"].keys()
    assert after["repos"][REPO]["pendingSince"] == before["repos"][REPO]["pendingSince"]
    assert report["staging"]["absent"] == [], "a run that stopped on a failed read reports no artefact absence"


# --- fail closed: the journal is required state ---------------------------------------------------------------------


def snapshotWrites(gh):
    return gh.write_count()


@pytest.mark.parametrize("day,extra", [(TUE, {}), (MON, {}), (TUE, {"liveness": [dead(404)]})])
def test_a_missing_journal_fails_closed_on_any_day_urgent_included(tmp_path, day, extra):
    path = tmp_path / "journal.json"
    gh = FakeGh()
    report, code = go(gh, [finding(**extra)], weekly(day, journalPath=str(path)))
    assert code == 3 and gh.write_count() == 0
    assert report["unknownEvidence"][0]["source"] == "staging-journal"
    assert "before any GitHub write" in report["unknownEvidence"][0]["detail"]
    assert report["unknownEvidence"][0]["stopped"] is True, "stops the run: bootstrap findings are not written either"
    assert report["staging"]["journal"]["status"] == "missing"
    [row] = report["staging"]["held"]
    assert row["reasons"] == ["journal-unavailable:missing"]
    assert bool(row.get("urgentBlocked")) is bool(extra)
    assert (report["staging"]["urgentBlocked"] != []) is bool(extra)
    assert not path.exists(), "a missing journal is never silently created"


@pytest.mark.parametrize("damage", ["garbage", "tamper", "shape"])
@pytest.mark.parametrize("bootstrap", [False, True])
def test_a_corrupt_journal_fails_closed_is_never_overwritten_and_bootstrap_does_not_cure_it(tmp_path, damage, bootstrap):
    path = tmp_path / "journal.json"
    journal = st.Journal()
    journal.observe(REPO, finding("v1", ["alpha"]), candidateRows("v1", ["alpha"]), TUE)
    journal.save(path)
    good = json.loads(path.read_text())
    if damage == "garbage":
        path.write_text("{not json", encoding="utf-8")
    elif damage == "tamper":
        good["repos"][REPO]["pendingSince"] = "2020-01-01T00:00:00Z"  # tries to force an early flush
        path.write_text(json.dumps(good), encoding="utf-8")
    else:
        path.write_text(json.dumps({"schemaVersion": 99, "repos": {}}), encoding="utf-8")
    before = path.read_bytes()
    gh = FakeGh()
    report, code = go(gh, [finding("v2", ["alpha"])], weekly(MON, journalPath=str(path), bootstrap=bootstrap))
    assert code == 3 and gh.write_count() == 0
    assert report["staging"]["journal"]["status"] == "corrupt"
    assert path.read_bytes() == before, "never overwritten"


def test_an_explicit_bootstrap_allows_a_first_run_with_no_journal_and_creates_it_even_in_a_dry_run(tmp_path):
    path = tmp_path / "nested" / "journal.json"
    gh = FakeGh()
    report, code = go(gh, [finding()], weekly(TUE, journalPath=str(path), bootstrap=True), apply=False)
    assert code == 0 and gh.write_count() == 0
    assert report["staging"]["journal"]["status"] == "bootstrap"
    assert st.Journal.load(path).pendingSince(REPO) == TUE
    assert not list(path.parent.glob("*.tmp"))


def test_a_dry_run_without_bootstrap_does_not_persist_the_journal(tmp_path):
    path = tmp_path / "journal.json"
    journal = st.Journal()
    journal.save(path)
    gh = FakeGh()
    go(gh, [finding()], weekly(TUE, journalPath=str(path)), apply=False)
    assert REPO not in json.loads(path.read_text())["repos"]


def test_loss_and_recovery_the_flush_is_fed_by_the_restored_journal_not_a_reset_one(tmp_path):
    path = tmp_path / "journal.json"
    gh = FakeGh()
    go(gh, [finding("v1", ["alpha", "ephemeral"])], weekly(TUE, journalPath=str(path), bootstrap=True))
    backup = path.read_bytes()
    go(gh, [finding("v2", ["alpha", "beta"])], weekly(WED, journalPath=str(path)))
    withBeta = path.read_bytes()
    path.unlink()  # cache eviction
    report, code = go(gh, [finding("v3", ["alpha", "beta"])], weekly(SUN, journalPath=str(path)))
    assert code == 3 and gh.write_count() == 0 and report["staging"]["journal"]["status"] == "missing"
    # Monday would have flushed, and still must not write while the journal is gone.
    report, code = go(gh, [finding("v3", ["alpha", "beta"])], weekly(MON, journalPath=str(path)))
    assert code == 3 and gh.write_count() == 0 and not path.exists()
    path.write_bytes(withBeta)  # recovery: restore the last good journal
    report, code = go(gh, [finding("v3", ["alpha", "beta"])], weekly(MON, journalPath=str(path)))
    assert code == 0 and [w[0] for w in gh.writes] == ["create"]
    rows = rows_of(gh)
    assert rows["garrytan/gbrain:ephemeral"]["firstSeenVersion"] == "v1"
    assert rows["garrytan/gbrain:beta"]["firstSeenVersion"] == "v2"
    assert backup != withBeta


def test_journal_roundtrip_atomic_save_digest_and_refusal_to_write_when_blocked(tmp_path):
    path = tmp_path / "journal.json"
    journal = st.Journal()
    journal.observe(REPO, finding(), candidateRows("v1", ["alpha"]), TUE)
    journal.save(path)
    saved = json.loads(path.read_text())
    assert saved["schemaVersion"] == st.JOURNALVERSION and saved["digest"] == st.digestOf(saved)
    assert not list(tmp_path.glob("*.tmp"))
    assert st.Journal.load(path).data["repos"] == journal.data["repos"]
    assert st.Journal.load(tmp_path / "absent.json").status == "missing"
    assert st.Journal.load(tmp_path / "absent.json", bootstrap=True).status == "bootstrap"
    assert st.Journal.load(None).status == "missing"
    with pytest.raises(RuntimeError):
        st.Journal(status="corrupt", detail="x").save(path)


def test_a_gh_failure_still_exits_3_with_a_staging_section(tmp_path):
    gh = FakeGh()
    gh.fail_list = True
    report, code = go(gh, [finding()], weekly(TUE), st.Journal())
    assert code == 3 and gh.write_count() == 0
    assert report["staging"]["held"] == []


def test_a_records_reset_is_never_staged():
    gh = FakeGh()
    with pytest.raises(ValueError, match="reset-records"):
        run_batch([finding()], gh, apply=True, index_loader=lambda: index_from_entries([]),
                  reset_records="garrytan/gbrain", staging=weekly(TUE), journal=st.Journal())
    assert watcher.main(["--child-mode", "batch", "--apply", "--staging", "weekly", "--staging-journal", "/x/j.json",
                         "--reset-records", "garrytan/gbrain"]) == 1


def test_an_active_config_with_no_journal_at_all_is_refused():
    with pytest.raises(ValueError, match="journal"):
        run_batch([finding()], FakeGh(), apply=False, index_loader=lambda: index_from_entries([]), staging=weekly(TUE))


# --- the CLI switch and the V2 gate ---------------------------------------------------------------------------------


def test_cli_staging_requires_batch_a_journal_and_valid_values(capsys):
    assert watcher.main(["--staging", "weekly", "--staging-journal", "j"]) == 1
    assert "requires --child-mode batch" in capsys.readouterr().err
    assert watcher.main(["--child-mode", "batch", "--staging", "weekly"]) == 1
    assert "requires --staging-journal" in capsys.readouterr().err
    assert watcher.main(["--child-mode", "batch", "--staging", "weekly", "--staging-journal", "j",
                         "--staging-as-of", "yesterday"]) == 1
    assert watcher.main(["--child-mode", "batch", "--staging", "weekly", "--staging-journal", "j",
                         "--staging-flush-day", "someday"]) == 1
    with pytest.raises(SystemExit):
        watcher.main(["--staging", "daily"])


def stubWatcher(monkeypatch, seen):
    monkeypatch.setattr(watcher, "_build_registry_map", lambda: seen.setdefault("polled", True) and {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda: [])
    monkeypatch.setattr(watcher, "run_batch", lambda *a, **k: seen.update(k) or (bt.new_report(), 0))
    monkeypatch.setattr(watcher, "batch_stopped", lambda report: False)


def test_cli_off_is_the_default_and_passes_no_staging_argument(monkeypatch):
    seen = {}
    stubWatcher(monkeypatch, seen)
    assert watcher.main(["--child-mode", "batch", "--apply"]) == 0
    assert "staging" not in seen, "the default call is exactly the deployed one"


def test_cli_passes_the_resolved_staging_config(monkeypatch):
    seen = {}
    stubWatcher(monkeypatch, seen)
    monkeypatch.setenv("STEWARD_ISSUE_HYGIENE_V2", "true")
    assert watcher.main(["--child-mode", "batch", "--apply", "--staging", "weekly", "--staging-flush-day", "Fri",
                         "--staging-as-of", "2026-11-03T06:00:00Z", "--staging-journal", "/tmp/x.json",
                         "--staging-bootstrap"]) == 0
    config = seen["staging"]
    assert (config.mode, config.flushWeekday, config.journalPath, config.bootstrap) == ("weekly", 4, "/tmp/x.json", True)
    assert config.now == TUE


@pytest.mark.parametrize("value", [None, "", "false", "False", "TRUE", "1", "yes"])
def test_cli_staged_apply_is_refused_before_any_write_or_poll_unless_v2_is_true(monkeypatch, capsys, value):
    seen = {}
    stubWatcher(monkeypatch, seen)
    if value is None:
        monkeypatch.delenv("STEWARD_ISSUE_HYGIENE_V2", raising=False)
    else:
        monkeypatch.setenv("STEWARD_ISSUE_HYGIENE_V2", value)
    assert watcher.main(["--child-mode", "batch", "--apply", "--staging", "weekly", "--staging-journal", "j"]) == 1
    assert "STEWARD_ISSUE_HYGIENE_V2=true" in capsys.readouterr().err
    assert seen == {}, "refused before the registry poll and before run_batch"


def test_cli_staged_apply_proceeds_when_v2_is_true_and_a_dry_run_never_needs_it(monkeypatch):
    seen = {}
    stubWatcher(monkeypatch, seen)
    monkeypatch.delenv("STEWARD_ISSUE_HYGIENE_V2", raising=False)
    assert watcher.main(["--child-mode", "batch", "--staging", "weekly", "--staging-journal", "j"]) == 0
    assert seen["staging"].active
    seen.clear()
    monkeypatch.setenv("STEWARD_ISSUE_HYGIENE_V2", "true")
    assert watcher.main(["--child-mode", "batch", "--apply", "--staging", "weekly", "--staging-journal", "j"]) == 0
    assert seen["staging"].active and seen["polled"] is True


def test_cli_off_apply_needs_no_v2_gate(monkeypatch):
    seen = {}
    stubWatcher(monkeypatch, seen)
    monkeypatch.delenv("STEWARD_ISSUE_HYGIENE_V2", raising=False)
    assert watcher.main(["--child-mode", "batch", "--apply"]) == 0


# --- the workflow switch --------------------------------------------------------------------------------------------


def test_workflow_default_has_no_staging_and_keeps_the_deployed_contract(tmp_path):
    result, calls = _run_block_with(tmp_path, "schedule", {})
    assert result.returncode == 0 and "--child-mode fanout" in calls[0] and "--staging" not in calls[0]
    (tmp_path / "d").mkdir()
    result, calls = _run_block_with(tmp_path / "d", "workflow_dispatch", {"INPUT_STAGING": "inherit", "STAGING_VAR": ""})
    assert result.returncode == 0 and "--staging" not in calls[0]


def test_workflow_variable_weekly_moves_the_schedule_onto_staged_batch_only_when_v2_is_on(tmp_path):
    (tmp_path / "a").mkdir()
    result, calls = _run_block_with(tmp_path / "a", "schedule", {"STAGING_VAR": "weekly", "V2_ENABLED": "true",
                                                                  "STAGING_INITIALIZED": "true"})
    assert result.returncode == 0
    assert "--child-mode batch" in calls[0] and "--apply" in calls[0] and "--staging-initialized" in calls[0]
    assert "--staging weekly --staging-journal generated-output/staging-journal.json" in calls[0]
    assert "--staging-bootstrap" not in calls[0], "the schedule never bootstraps"
    (tmp_path / "b").mkdir()
    result, calls = _run_block_with(tmp_path / "b", "schedule", {"STAGING_VAR": "weekly", "V2_ENABLED": ""})
    assert result.returncode == 1 and calls == [], "fails closed: staged writes still need STEWARD_ISSUE_HYGIENE_V2"


def test_workflow_dispatch_staging_rules(tmp_path):
    for name, env, code, staged in [
        ("weekly-fanout", {"INPUT_STAGING": "weekly", "INPUT_CHILD_MODE": "fanout"}, 1, None),
        ("weekly-batch-dry", {"INPUT_STAGING": "weekly", "INPUT_CHILD_MODE": "batch"}, 0, True),
        ("off-overrides-var", {"INPUT_STAGING": "off", "STAGING_VAR": "weekly", "INPUT_CHILD_MODE": "batch"}, 0, False),
        ("inherit-follows-var", {"INPUT_STAGING": "inherit", "STAGING_VAR": "weekly", "INPUT_CHILD_MODE": "batch"}, 0, True),
        ("bad-value", {"STAGING_VAR": "daily"}, 1, None),
    ]:
        (tmp_path / name).mkdir()
        result, calls = _run_block_with(tmp_path / name, "workflow_dispatch", env)
        assert result.returncode == code, (name, result.stdout, result.stderr)
        if staged is None:
            assert calls == [], name
        else:
            assert ("--staging weekly" in calls[0]) is staged, name
            assert "--dry-run" in calls[0], "a manual run without apply stays a dry run"
            assert "--staging-bootstrap" not in calls[0], name


def test_workflow_bootstrap_is_an_explicit_dispatch_input_only(tmp_path):
    (tmp_path / "a").mkdir()
    result, calls = _run_block_with(tmp_path / "a", "workflow_dispatch", {
        "INPUT_STAGING": "weekly", "INPUT_CHILD_MODE": "batch", "INPUT_STAGING_BOOTSTRAP": "true"})
    assert result.returncode == 0 and "--staging-bootstrap" in calls[0]
    (tmp_path / "b").mkdir()
    result, calls = _run_block_with(tmp_path / "b", "schedule", {
        "STAGING_VAR": "weekly", "V2_ENABLED": "true", "STAGING_INITIALIZED": "true", "INPUT_STAGING_BOOTSTRAP": "true"})
    assert result.returncode == 0 and "--staging-bootstrap" not in calls[0]


def test_workflow_escalation_never_stages(tmp_path):
    result, calls = _run_block_with(tmp_path, "workflow_dispatch", {
        "INPUT_STAGING": "weekly", "INPUT_CHILD_MODE": "batch", "INPUT_ESCALATE": "garrytan/gbrain:alpha"})
    assert result.returncode == 0 and "--escalate garrytan/gbrain:alpha" in calls[0] and "--staging" not in calls[0]


def test_workflow_cache_steps_run_only_when_staging_is_on_and_triggers_are_unchanged():
    doc = yaml.safe_load((ROOT / ".github/workflows/upstream-watcher.yml").read_text())
    steps = {step["name"]: step for step in doc["jobs"]["watcher"]["steps"]}
    for name in ("Restore staging journal", "Save staging journal"):
        gate = steps[name]["if"]
        assert "UPSTREAM_BATCH_STAGING == 'weekly'" in gate and "inputs.escalate_candidate == ''" in gate
    assert "actions/cache/restore" in steps["Restore staging journal"]["uses"]
    assert "actions/cache/save" in steps["Save staging journal"]["uses"]
    env = steps["Run upstream watcher"]["env"]
    assert env["STEWARD_ISSUE_HYGIENE_V2"] == "${{ vars.STEWARD_ISSUE_HYGIENE_V2 }}", "the CLI reads the same gate"
    triggers = doc.get("on", doc.get(True))
    assert triggers["schedule"] == [{"cron": "0 6 * * *"}]
    assert triggers["workflow_dispatch"]["inputs"]["staging"]["default"] == "inherit"
    assert triggers["workflow_dispatch"]["inputs"]["staging_bootstrap"]["default"] is False
    assert triggers["workflow_dispatch"]["inputs"]["child_mode"]["default"] == "fanout"
    assert doc["permissions"] == {"issues": "write", "contents": "read"}


def test_workflow_scheduled_staging_requires_the_durable_initialized_marker(tmp_path):
    for name, marker, code in [("unset", "", 1), ("false", "false", 1), ("true", "true", 0)]:
        (tmp_path / name).mkdir()
        result, calls = _run_block_with(tmp_path / name, "schedule", {
            "STAGING_VAR": "weekly", "V2_ENABLED": "true", "STAGING_INITIALIZED": marker})
        assert result.returncode == code, (name, result.stdout)
        assert (calls == []) is (code == 1), "refused before the watcher runs"


def test_workflow_dispatch_passes_the_initialized_marker_so_a_loss_is_recognised(tmp_path):
    (tmp_path / "a").mkdir()
    result, calls = _run_block_with(tmp_path / "a", "workflow_dispatch", {
        "INPUT_STAGING": "weekly", "INPUT_CHILD_MODE": "batch", "STAGING_INITIALIZED": "true"})
    assert result.returncode == 0 and "--staging-initialized" in calls[0]
    (tmp_path / "b").mkdir()
    result, calls = _run_block_with(tmp_path / "b", "workflow_dispatch", {
        "INPUT_STAGING": "weekly", "INPUT_CHILD_MODE": "batch"})
    assert result.returncode == 0 and "--staging-initialized" not in calls[0]


# --- B3 of the second review: eviction versus a first-ever bootstrap ---------------------------------------------------


def test_journal_load_distinguishes_a_first_run_from_a_lost_journal(tmp_path):
    absent = tmp_path / "absent.json"
    assert st.Journal.load(absent).status == "missing"
    assert st.Journal.load(absent, bootstrap=True).status == "bootstrap"
    lost = st.Journal.load(absent, initialized=True)
    assert lost.status == "lost" and lost.blocked and "LOST" in lost.detail
    recovery = st.Journal.load(absent, bootstrap=True, initialized=True)
    assert recovery.status == "recovery" and not recovery.blocked and "no longer upstream" in recovery.detail


def test_eviction_fails_closed_then_the_explicit_recovery_reobserves_and_every_present_candidate_reappears(tmp_path):
    path = tmp_path / "journal.json"
    gh = FakeGh()
    # Initialised and observing: the journal holds a candidate that later vanishes upstream.
    go(gh, [finding("v1", ["alpha", "vanishing"])], weekly(TUE, journalPath=str(path), bootstrap=True, initialized=False))
    go(gh, [finding("v2", ["alpha", "beta"])], weekly(WED, journalPath=str(path), initialized=True))
    path.unlink()  # cache eviction
    report, code = go(gh, [finding("v3", ["alpha", "beta", "gamma"])], weekly(MON, journalPath=str(path), initialized=True))
    assert code == 3 and gh.write_count() == 0 and report["staging"]["journal"]["status"] == "lost"
    assert "LOST" in report["unknownEvidence"][0]["detail"] and not path.exists()
    # Recovery: explicit dispatch, re-observes the current upstream state.
    report, code = go(gh, [finding("v3", ["alpha", "beta", "gamma"])],
                      weekly(MON + dt.timedelta(days=1), journalPath=str(path), bootstrap=True, initialized=True))
    assert code == 0 and gh.write_count() == 0 and report["staging"]["journal"]["status"] == "recovery"
    assert st.Journal.load(path, initialized=True).pendingSince(REPO) == MON + dt.timedelta(days=1)
    go(gh, [finding("v3", ["alpha", "beta", "gamma"])], weekly(NEXTTUE + dt.timedelta(days=6), journalPath=str(path), initialized=True))
    rows = rows_of(gh)
    assert {"garrytan/gbrain:alpha", "garrytan/gbrain:beta", "garrytan/gbrain:gamma"} <= set(rows), \
        "every candidate still present upstream reappears"
    assert "garrytan/gbrain:vanishing" not in rows, "a permitted loss: a candidate no longer present upstream"
    # The other permitted loss: first-seen provenance of candidates still present restarts at the recovery
    # observation. alpha was observed at v1 before the eviction; after recovery at v3 it reads v3, and says so.
    assert rows["garrytan/gbrain:alpha"]["firstSeenVersion"] == "v3"
    assert all(rows[i]["provenanceReset"] is True for i in
               ("garrytan/gbrain:alpha", "garrytan/gbrain:beta", "garrytan/gbrain:gamma")), "auditable marker"
    assert "(provenance reset)" in open_umbrellas(gh)[0]["body"]


# --- stop before EVERY write, bootstrap findings included (CLI level) ------------------------------------------------


def cliWorld(monkeypatch, gh):
    index = index_from_entries([])
    suites = {
        "garrytan/gbrain": finding("v1", ["alpha"]),
        "x/newsuite": {"finding_type": "bootstrap", "skillId": "x/newsuite", "currentVersion": None, "newVersion": "v1",
                       "releasedAt": "2026-11-03T00:00:00Z", "sourceUrl": "https://github.com/x/newsuite/releases/tag/v1"},
    }
    calls = []
    monkeypatch.setenv("STEWARD_ISSUE_HYGIENE_V2", "true")
    monkeypatch.setattr(watcher, "_build_registry_map", lambda: {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda: iter([(None, {"id": key}) for key in suites]))
    monkeypatch.setattr(watcher, "_poll_suite", lambda fm, rm, verbose: suites[fm["id"]])
    monkeypatch.setattr(watcher, "LiveGh", lambda *a, **k: gh)
    monkeypatch.setattr(watcher, "run_batch", lambda *a, **k: bt.run_batch(*a, index_loader=lambda: index, **k))
    monkeypatch.setattr(watcher, "create_issues", lambda *a, **k: calls.append((a, k)) or [])
    return calls


@pytest.mark.parametrize("damage", ["missing", "garbage", "tamper", "lost"])
def test_cli_missing_or_corrupt_journal_stops_before_every_github_write_bootstrap_findings_included(
        monkeypatch, tmp_path, damage):
    path = tmp_path / "journal.json"
    if damage != "missing" and damage != "lost":
        good = st.Journal()
        good.observe(REPO, finding(), candidateRows("v1", ["alpha"]), TUE)
        good.save(path)
        if damage == "garbage":
            path.write_text("{", encoding="utf-8")
        else:
            data = json.loads(path.read_text())
            data["repos"][REPO]["pendingSince"] = "2020-01-01T00:00:00Z"
            path.write_text(json.dumps(data), encoding="utf-8")
    gh = FakeGh()
    calls = cliWorld(monkeypatch, gh)
    argv = ["--child-mode", "batch", "--apply", "--staging", "weekly", "--staging-journal", str(path),
            "--staging-as-of", "2026-11-09T06:00:00Z", "--report", str(tmp_path / "report.json")]
    if damage == "lost":
        argv.append("--staging-initialized")
    assert watcher.main(argv) == 3
    assert calls == [], "create_issues (bootstrap findings) was never reached"
    assert gh.write_count() == 0 and gh.writes == [], "zero create/edit/comment/label calls"
    assert not [w for w in gh.writes if w[0] in ("create", "edit", "comment", "labels")]
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["unknownEvidence"][0]["source"] == "staging-journal"


def test_cli_with_a_good_journal_does_reach_the_bootstrap_pass(monkeypatch, tmp_path):
    path = tmp_path / "journal.json"
    gh = FakeGh()
    calls = cliWorld(monkeypatch, gh)
    argv = ["--child-mode", "batch", "--apply", "--staging", "weekly", "--staging-journal", str(path),
            "--staging-bootstrap", "--staging-as-of", "2026-11-09T06:00:00Z"]
    assert watcher.main(argv) == 0
    assert len(calls) == 1 and [f["skillId"] for f in calls[0][0][0]] == ["x/newsuite"]


# --- B4 of the second review: records-mode create is guarded ----------------------------------------------------------


class CreatedClosingGh(ClosingGh):
    """Closes the most recently created issue when the Nth get_issue read happens."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created = []

    def create_issue(self, title, labels, body):
        number = super().create_issue(title, labels, body)
        self.log.append(("create", number))
        self.created.append(number)
        return number

    def get_issue(self, number):
        self.gets += 1
        if self.closeAtGet == self.gets and self.created:
            self.issues[self.created[-1]]["state"] = "closed"
        self.log.append(("get", self.gets, number))
        return FakeGh.get_issue(self, number)


def recordsAdds():
    return [f"skill-{n:03d}" for n in range(250)]


def test_staged_records_mode_create_guards_every_mutation_after_the_placeholder():
    probe = CreatedClosingGh()
    go(probe, [finding("v1", recordsAdds())], weekly(MON))
    [number] = probe.created
    mutations = [i for i, e in enumerate(probe.log) if e[0] == "write" and e[2] == number]
    assert len(mutations) == 6, "five record comments and one body edit"
    assert all(probe.log[i - 1][0] == "get" and probe.log[i - 1][2] == number for i in mutations), \
        "each is immediately preceded by a re-read of the new umbrella"
    for index, i in enumerate(mutations):
        gh = CreatedClosingGh()
        gh.closeAtGet = probe.log[i - 1][1]
        report, code = go(gh, [finding("v1", recordsAdds())], weekly(MON))
        [new] = gh.created
        assert gh.issues[new]["state"] == "closed"
        onNew = [e for e in gh.log if e[0] == "write" and e[2] == new]
        assert len(onNew) == index, f"mutation {index} and every later one on the closed issue is aborted"
        assert gh.created == [new], "no second umbrella is created: the closed placeholder is ambiguous evidence"
        assert report["suites"][0]["outcome"] == "blocked-identity" and code == 3
        assert report["staging"]["closedDuringWrite"][0]["closed"] == [new]
        comments = gh.comments.get(new, [])
        assert len(comments) == index, "the record comments already written stay in place and recoverable"


# --- round 3: full handoff before suppression, the recovery marker, and staging versus other write paths ---------------


def test_carries_pending_demands_identity_and_first_and_last_seen_for_current_and_vanished_candidates():
    f = {**finding("v2", ["alpha"]), "pendingFirstSeen": {"garrytan/gbrain:alpha": "v1"},
         "pendingRows": [{"id": "garrytan/gbrain:gone", "firstSeenVersion": "v1", "lastSeenVersion": "v1"}]}
    ok = [{"id": "garrytan/gbrain:alpha", "firstSeenVersion": "v1", "lastSeenVersion": "v2"},
          {"id": "garrytan/gbrain:gone", "firstSeenVersion": "v1", "lastSeenVersion": "v1"}]
    assert bt.carriesPending(ok, f)
    for index, change in enumerate([{"firstSeenVersion": "v2"}, {"lastSeenVersion": "v1"}]):
        assert not bt.carriesPending([{**ok[0], **change}, ok[1]], f), index
    for change in ({"firstSeenVersion": "v0"}, {"lastSeenVersion": "v2"}):
        assert not bt.carriesPending([ok[0], {**ok[1], **change}], f)
    assert not bt.carriesPending([ok[1]], f) and not bt.carriesPending([ok[0]], f)


def test_a_closed_umbrella_with_the_same_candidate_but_later_provenance_does_not_suppress_or_clear_the_journal():
    # The journal holds alpha and `ephemeral` first seen at v1 (held). An unstaged v2 umbrella was created and closed:
    # it has alpha first seen at v2 and no `ephemeral`. Identity alone must not count as a handoff.
    gh, journal = FakeGh(), st.Journal()
    go(gh, [finding("v1", ["alpha", "ephemeral"])], weekly(TUE), journal)
    go(gh, [finding("v2", ["alpha"])], None)
    closed = open_umbrellas(gh)[0]["number"]
    assert rows_of(gh)["garrytan/gbrain:alpha"]["firstSeenVersion"] == "v2"
    gh.issues[closed]["state"] = "closed"
    snapshot = json.dumps(gh.issues[closed], sort_keys=True)
    gh.writes.clear()
    report, _ = go(gh, [finding("v2", ["alpha"])], weekly(WED), journal)
    assert report["suites"][0]["outcome"] == "held", "not suppressed-processed"
    assert report["staging"]["held"][0]["planAction"] == "create"
    assert set(journal.data["repos"][REPO]["candidates"]) == {"garrytan/gbrain:alpha", "garrytan/gbrain:ephemeral"}
    go(gh, [finding("v2", ["alpha"])], weekly(MON), journal)
    assert json.dumps(gh.issues[closed], sort_keys=True) == snapshot, "the closed issue is never edited"
    [new] = open_umbrellas(gh)
    rows = rows_of(gh)
    # The vanished candidate has no other record: its journaled provenance is carried exactly.
    assert rows["garrytan/gbrain:ephemeral"]["firstSeenVersion"] == "v1" == rows["garrytan/gbrain:ephemeral"]["lastSeenVersion"]
    # A row already on an umbrella keeps that umbrella's provenance when carried forward (the journal postdates it
    # in staged operation); the conflicting journal value is not silently invented over it.
    assert rows["garrytan/gbrain:alpha"]["carriedFrom"] == f"#{closed}"
    assert REPO not in journal.data["repos"], "cleared only once the flush carried the rows"


def recordsCarrierWorld(journalFirstSeen):
    gh = FakeGh()
    adds = recordsAdds()
    go(gh, [finding("v1", adds)], None)                      # records-mode umbrella, rows first/last seen v1
    [number] = [r["number"] for r in open_umbrellas(gh)]
    assert "candidateRecords" in parse_payload(gh.issues[number]["body"]), "records mode"
    gh.issues[number]["state"] = "closed"
    journal = st.Journal()
    journal.observe(REPO, finding("v1", adds), candidateRows("v1", adds), TUE)
    if journalFirstSeen:
        journal.data["repos"][REPO]["candidates"]["garrytan/gbrain:skill-007"]["firstSeenVersion"] = journalFirstSeen
    gh.writes.clear()
    return gh, journal, number


def test_records_mode_closed_carrier_with_matching_provenance_suppresses_and_clears():
    gh, journal, number = recordsCarrierWorld(None)
    report, _ = go(gh, [finding("v1", recordsAdds())], weekly(WED), journal)
    assert report["suites"][0]["outcome"] == "suppressed-processed" and gh.write_count() == 0
    assert REPO not in journal.data["repos"]


def test_records_mode_closed_carrier_with_different_provenance_keeps_the_rows_for_a_new_batch():
    gh, journal, number = recordsCarrierWorld("v0")
    report, _ = go(gh, [finding("v1", recordsAdds())], weekly(WED), journal)
    assert report["suites"][0]["outcome"] == "held" and gh.write_count() == 0
    assert journal.data["repos"][REPO]["candidates"]["garrytan/gbrain:skill-007"]["firstSeenVersion"] == "v0"
    go(gh, [finding("v1", recordsAdds())], weekly(MON), journal)
    new = [r for r in open_umbrellas(gh) if r["number"] != number]
    assert len(new) == 1, "a new batch, the closed records-mode umbrella untouched"
    assert len(rowsFrom(gh, new[0]["number"])) == 250 and REPO not in journal.data["repos"]


def test_recovery_marks_only_recovered_rows_and_never_touches_rows_already_on_an_umbrella(tmp_path):
    path = tmp_path / "journal.json"
    gh = FakeGh()
    go(gh, [finding("v1", ["alpha"])], None)                 # an umbrella exists with alpha first seen v1
    number = open_umbrellas(gh)[0]["number"]
    report, code = go(gh, [finding("v2", ["alpha", "beta"])],
                      weekly(MON, journalPath=str(path), bootstrap=True, initialized=True))
    assert code == 0 and report["staging"]["journal"]["status"] == "recovery"
    [flushed] = report["staging"]["flushed"]
    assert flushed["provenanceReset"] is True
    rows = rows_of(gh)
    assert [r["number"] for r in open_umbrellas(gh)] == [number]
    assert rows["garrytan/gbrain:alpha"]["firstSeenVersion"] == "v1" and "provenanceReset" not in rows["garrytan/gbrain:alpha"], \
        "provenance already on the umbrella is intact"
    assert rows["garrytan/gbrain:beta"]["provenanceReset"] is True and rows["garrytan/gbrain:beta"]["firstSeenVersion"] == "v2"


def test_the_marker_persists_in_the_journal_so_a_later_flush_is_still_marked(tmp_path):
    path = tmp_path / "journal.json"
    gh = FakeGh()
    go(gh, [finding("v1", ["alpha"])], weekly(TUE, journalPath=str(path), bootstrap=True, initialized=True))
    report, _ = go(gh, [finding("v2", ["alpha", "late"])], weekly(MON, journalPath=str(path), initialized=True))
    rows = rows_of(gh)
    assert rows["garrytan/gbrain:alpha"]["provenanceReset"] is True, "observed during the recovery run"
    assert "provenanceReset" not in rows["garrytan/gbrain:late"], "first seen after the recovery: ordinary provenance"
    assert report["staging"]["flushed"][0]["provenanceReset"] is True


def test_a_normal_first_bootstrap_is_not_marked_as_a_provenance_reset(tmp_path):
    path = tmp_path / "journal.json"
    gh = FakeGh()
    go(gh, [finding("v1", ["alpha"])], weekly(MON, journalPath=str(path), bootstrap=True))
    assert "provenanceReset" not in rows_of(gh)["garrytan/gbrain:alpha"]


@pytest.mark.parametrize("damage", ["missing", "garbage", "lost"])
@pytest.mark.parametrize("mode", ["escalate", "challenge-watch", "challenge-only"])
def test_cli_rejects_staging_with_escalation_and_challenge_watch_with_zero_writes(monkeypatch, tmp_path, damage, mode):
    path = tmp_path / "journal.json"
    if damage == "garbage":
        path.write_text("{", encoding="utf-8")
    gh = FakeGh()
    reached = []
    monkeypatch.setenv("STEWARD_ISSUE_HYGIENE_V2", "true")
    monkeypatch.setattr(watcher, "LiveGh", lambda *a, **k: gh)
    monkeypatch.setattr(watcher, "_build_registry_map", lambda: reached.append("registry") or {})
    monkeypatch.setattr(watcher, "escalate_candidate", lambda *a, **k: reached.append("escalate") or ({}, 0))
    monkeypatch.setattr(watcher, "runChallengeWatchStep", lambda *a, **k: reached.append("challenge") or None)
    argv = ["--child-mode", "batch", "--apply", "--staging", "weekly", "--staging-journal", str(path)]
    if damage == "lost":
        argv.append("--staging-initialized")
    argv += {"escalate": ["--escalate", "garrytan/gbrain:alpha"], "challenge-watch": ["--challenge-watch"],
             "challenge-only": ["--challenge-only"]}[mode]
    assert watcher.main(argv) == 1
    assert reached == [], "no write-capable path ran"
    assert gh.write_count() == 0 and gh.writes == []


def test_cli_rejects_staging_with_the_challenge_watch_env_switch(monkeypatch, tmp_path):
    monkeypatch.setenv("GAIA_CHALLENGE_WATCH_ENABLED", "1")
    monkeypatch.setattr(watcher, "runChallengeWatchStep", lambda *a, **k: pytest.fail("challenge watch ran"))
    assert watcher.main(["--child-mode", "batch", "--staging", "weekly", "--staging-journal", str(tmp_path / "j")]) == 1


def test_unstaged_escalation_and_challenge_watch_are_untouched(monkeypatch):
    seen = []
    monkeypatch.delenv("STEWARD_ISSUE_HYGIENE_V2", raising=False)
    monkeypatch.setattr(watcher, "escalate_candidate", lambda *a, **k: seen.append("escalate") or ({}, 0))
    assert watcher.main(["--child-mode", "batch", "--apply", "--escalate", "garrytan/gbrain:alpha"]) == 0
    assert seen == ["escalate"]


# --- round 4: a vanished candidate keeps its exact journal provenance even when carried rows already hold it ------------


def childIntake(number, slug, umbrella):
    return {
        "number": number, "title": f"[intake] garrytan/{slug}", "state": "open",
        "labels": [{"name": "intake"}, {"name": "upstream:child"}],
        "body": (f"> Auto-populated by upstream watcher. Umbrella: #{umbrella}.\n\n**Suggested ID:** `garrytan/{slug}`\n\n"
                 f"### Evidence\n\n- **url:** https://github.com/garrytan/gbrain/blob/main/skills/{slug}/SKILL.md\n"),
    }


def test_a_vanished_candidate_already_in_carried_rows_keeps_the_journals_exact_provenance_and_its_disposition():
    gh = FakeGh([childIntake(77, "ephemeral", 1)])
    go(gh, [finding("v2", ["alpha", "ephemeral"])], None)        # closed-to-be umbrella: ephemeral first/last v2
    closed = open_umbrellas(gh)[0]["number"]
    carriedBefore = rows_of(gh)["garrytan/gbrain:ephemeral"]
    assert (carriedBefore["firstSeenVersion"], carriedBefore["lastSeenVersion"]) == ("v2", "v2")
    assert carriedBefore["child"] == 77 and carriedBefore["status"] == "tracked"
    gh.issues[closed]["state"] = "closed"
    snapshot = json.dumps(gh.issues[closed], sort_keys=True)
    journal = st.Journal()
    journal.observe(REPO, finding("v1", ["alpha", "ephemeral"]), candidateRows("v1", ["alpha", "ephemeral"]), TUE)
    gh.writes.clear()
    held, _ = go(gh, [finding("v3", ["alpha"])], weekly(WED), journal)
    assert held["suites"][0]["outcome"] == "held" and gh.write_count() == 0
    assert "garrytan/gbrain:ephemeral" in journal.data["repos"][REPO]["candidates"], "still pending until the handoff"
    go(gh, [finding("v3", ["alpha"])], weekly(MON), journal)
    assert json.dumps(gh.issues[closed], sort_keys=True) == snapshot, "the closed umbrella is never edited"
    [new] = open_umbrellas(gh)
    row = rows_of(gh)["garrytan/gbrain:ephemeral"]
    assert (row["firstSeenVersion"], row["lastSeenVersion"]) == ("v1", "v1"), "the journal's exact provenance"
    assert row["child"] == 77 and row["status"] == "tracked", "disposition and child linkage preserved"
    assert row["carriedFrom"] == f"#{closed}"
    assert REPO not in journal.data["repos"], "cleared only after the handoff"


def test_a_vanished_candidate_in_a_records_mode_carried_umbrella_keeps_the_journals_exact_provenance():
    adds = recordsAdds()
    gh = FakeGh()
    go(gh, [finding("v2", adds)], None)                          # records-mode umbrella, every row first/last v2
    [closed] = [r["number"] for r in open_umbrellas(gh)]
    assert "candidateRecords" in parse_payload(gh.issues[closed]["body"])
    gh.issues[closed]["state"] = "closed"
    snapshot = json.dumps(gh.issues[closed], sort_keys=True)
    journal = st.Journal()
    journal.observe(REPO, finding("v1", ["skill-007"]), candidateRows("v1", ["skill-007"]), TUE)
    gh.writes.clear()
    remaining = [slug for slug in adds if slug != "skill-007"]
    go(gh, [finding("v3", remaining)], weekly(MON), journal)
    assert json.dumps(gh.issues[closed], sort_keys=True) == snapshot
    [new] = [r for r in open_umbrellas(gh)]
    assert "candidateRecords" in parse_payload(new["body"]), "the new batch is records mode too"
    rows = rowsFrom(gh, new["number"])
    assert len(rows) == 250
    assert (rows["garrytan/gbrain:skill-007"]["firstSeenVersion"], rows["garrytan/gbrain:skill-007"]["lastSeenVersion"]) == ("v1", "v1")
    assert rows["garrytan/gbrain:skill-008"]["firstSeenVersion"] == "v2", "still-present rows: the umbrella's provenance wins"
    assert REPO not in journal.data["repos"]


def test_still_present_candidates_keep_the_umbrella_provenance_and_vanished_ones_the_journal_provenance_together():
    gh = FakeGh()
    go(gh, [finding("v2", ["alpha", "ephemeral"])], None)
    gh.issues[open_umbrellas(gh)[0]["number"]]["state"] = "closed"
    journal = st.Journal()
    journal.observe(REPO, finding("v1", ["alpha", "ephemeral"]), candidateRows("v1", ["alpha", "ephemeral"]), TUE)
    go(gh, [finding("v3", ["alpha"])], weekly(MON), journal)
    rows = rows_of(gh)
    assert (rows["garrytan/gbrain:alpha"]["firstSeenVersion"], rows["garrytan/gbrain:alpha"]["lastSeenVersion"]) == ("v2", "v3")
    assert (rows["garrytan/gbrain:ephemeral"]["firstSeenVersion"], rows["garrytan/gbrain:ephemeral"]["lastSeenVersion"]) == ("v1", "v1")


def test_a_vanished_candidate_on_the_open_umbrella_keeps_its_older_umbrella_first_seen_never_a_later_journal_value():
    gh = FakeGh([childIntake(77, "ephemeral", 1)])
    go(gh, [finding("v1", ["alpha", "ephemeral"])], None)
    go(gh, [finding("v2", ["alpha", "ephemeral"])], None)
    number = open_umbrellas(gh)[0]["number"]
    before = rows_of(gh)["garrytan/gbrain:ephemeral"]
    assert (before["firstSeenVersion"], before["lastSeenVersion"]) == ("v1", "v2")
    # The journal began observing later, at v3: its first-seen for ephemeral is a LATER value than the umbrella's.
    journal = st.Journal()
    journal.observe(REPO, finding("v3", ["alpha", "ephemeral"]), candidateRows("v3", ["alpha", "ephemeral"]), TUE)
    assert journal.data["repos"][REPO]["candidates"]["garrytan/gbrain:ephemeral"]["firstSeenVersion"] == "v3"
    go(gh, [finding("v4", ["alpha"])], weekly(MON), journal)
    assert [r["number"] for r in open_umbrellas(gh)] == [number], "updated in place on the open umbrella"
    row = rows_of(gh)["garrytan/gbrain:ephemeral"]
    assert row["firstSeenVersion"] == "v1", "earliest true observation wins; the later journal value never overwrites it"
    assert row["lastSeenVersion"] == "v2" and row["child"] == 77 and row["status"] == "tracked"
    assert "carriedFrom" not in row
    assert REPO not in journal.data["repos"]


@pytest.mark.parametrize("unstaged", [None, "off"])
def test_midcycle_rollback_from_staged_hold_to_unstaged_executes_cleanly_with_dormant_journal(tmp_path, unstaged, monkeypatch):
    path = tmp_path / "journal.json"
    gh = FakeGh()

    # Day 1: Run with weekly staging holding candidates in journalPath=str(tmp_path / "journal.json"), bootstrap=True, initialized=True.
    report1, code1 = go(
        gh,
        [finding("v1", ["alpha", "transient_held"])],
        weekly(TUE, journalPath=str(path), bootstrap=True, initialized=True),
    )
    assert code1 == 0
    assert gh.write_count() == 0
    assert report1["suites"][0]["outcome"] == "held"
    assert path.is_file()

    journal_day1 = st.Journal.load(path, initialized=True)
    assert journal_day1.pendingSince(REPO) == TUE
    assert "garrytan/gbrain:transient_held" in journal_day1.data["repos"][REPO]["candidates"]

    journal_bytes_before = path.read_bytes()

    # Instrument/monkeypatch st.Journal.load and st.Journal.save during the unstaged step
    # to guarantee no journal operations occur during unstaged run.
    load_calls = []
    save_calls = []

    def spy_load(*args, **kwargs):
        load_calls.append((args, kwargs))
        raise AssertionError("st.Journal.load was called during unstaged run")

    def spy_save(*args, **kwargs):
        save_calls.append((args, kwargs))
        raise AssertionError("st.Journal.save was called during unstaged run")

    monkeypatch.setattr(st.Journal, "load", spy_load)
    monkeypatch.setattr(st.Journal, "save", spy_save)

    # Day 2: Simulate operator rollback by running without staging (e.g. staging=None or mode="off", with the existing journal still on disk).
    config2 = None if unstaged is None else st.StagingConfig(mode="off", now=WED, journalPath=str(path))
    report2, code2 = go(gh, [finding("v2", ["alpha", "gamma"])], config2)
    assert code2 == 0
    assert gh.write_count() == 1
    assert report2["issuesCreated"] == 1
    assert report2["suites"][0]["outcome"] == "created"

    # Guarantee no journal operations occurred during unstaged run.
    assert load_calls == []
    assert save_calls == []

    umbrellas = open_umbrellas(gh)
    assert len(umbrellas) == 1
    assert umbrellas[0]["title"] == PREFIX + "v2"
    rows = rows_of(gh)
    assert "garrytan/gbrain:alpha" in rows and "garrytan/gbrain:gamma" in rows

    # Assert that 'transient_held' is completely absent from the created umbrella/rows (proves journal was not replayed).
    assert "garrytan/gbrain:transient_held" not in rows
    assert "transient_held" not in umbrellas[0]["body"]

    # Assert that 'alpha' has firstSeenVersion='v2' (proves it took the fresh finding, not journal's v1).
    assert rows["garrytan/gbrain:alpha"]["firstSeenVersion"] == "v2"
    assert rows["garrytan/gbrain:gamma"]["firstSeenVersion"] == "v2"

    # Verify the unstaged run succeeds with exit code 0, creates the normal unstaged umbrella / findings on FakeGh,
    # the report does not have active staging ("staging" not in report or staging mode is off/None), and dormant journal is untouched.
    assert "staging" not in report2 or report2.get("staging") is None or report2["staging"].get("mode") in (None, "off")

    # Verify file bytes remain identical on disk.
    assert path.read_bytes() == journal_bytes_before

    # Verify dormant journal on disk remains intact and valid when reloaded.
    monkeypatch.undo()
    assert st.Journal.load(path, initialized=True).pendingSince(REPO) == TUE


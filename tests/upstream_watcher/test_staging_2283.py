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


def test_transients_are_reported_when_the_fresh_plan_is_suppressed_by_a_closed_umbrella():
    gh = FakeGh()
    journal = st.Journal()
    go(gh, [finding("v1", ["alpha", "ephemeral"])], weekly(TUE), journal)
    go(gh, [finding("v2", ["alpha"])], None)
    gh.issues[open_umbrellas(gh)[0]["number"]]["state"] = "closed"
    gh.writes.clear()
    report, _ = go(gh, [finding("v2", ["alpha"])], weekly(WED), journal)
    assert report["suites"][0]["outcome"] == "suppressed-processed" and gh.write_count() == 0
    [row] = report["staging"]["settled"]
    assert row["reasons"] == ["suppressed-processed"]
    assert [t["id"] for t in row["transientCandidates"]] == ["garrytan/gbrain:ephemeral"]


def test_pending_observations_for_a_suite_with_no_finding_are_reported_then_expire():
    gh = FakeGh()
    journal = st.Journal()
    go(gh, [finding("v1", ["alpha", "ephemeral"])], weekly(TUE), journal)
    report, _ = go(gh, [], weekly(WED), journal)
    [absent] = report["staging"]["absent"]
    assert absent["suite"] == REPO and [t["id"] for t in absent["transientCandidates"]][:1] == ["garrytan/gbrain:alpha"]
    assert REPO in journal.data["repos"], "retained while within the retention window"
    late = TUE + dt.timedelta(days=7 * st.EXPIRYWINDOWS)
    report, _ = go(gh, [], weekly(late), journal)
    assert [row["suite"] for row in report["staging"]["expired"]] == [REPO] and report["staging"]["absent"] == []
    assert REPO not in journal.data["repos"]


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
    assert "no silent reset" in report["unknownEvidence"][0]["detail"]
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
    result, calls = _run_block_with(tmp_path / "a", "schedule", {"STAGING_VAR": "weekly", "V2_ENABLED": "true"})
    assert result.returncode == 0
    assert "--child-mode batch" in calls[0] and "--apply" in calls[0]
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
        "STAGING_VAR": "weekly", "V2_ENABLED": "true", "INPUT_STAGING_BOOTSTRAP": "true"})
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

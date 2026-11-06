"""Staged batching (#2283, founder ruling #12): window, urgent bypass, dedupe/provenance, closed umbrellas, switch."""

import datetime as dt
import json

import pytest

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
PREFIX = "[upstream] garrytan/gbrain → "


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
    index = index_from_entries(list(entries))
    return run_batch(findings, gh, apply=apply, index_loader=lambda: index, staging=config, journal=journal)


def open_umbrellas(gh):
    return [r for r in gh.issues.values() if r["state"] == "open" and r["title"].startswith("[upstream] ")]


# --- the window -----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("now,released,decision,reason", [
    (TUE, "2026-11-03T01:00:00Z", "hold", "within-review-window"),
    (SUN, "2026-11-08T01:00:00Z", "hold", "within-review-window"),
    (MON, "2026-11-09T01:00:00Z", "flush", "flush-day"),
    # a release a full window old is never held longer, even when the flush day was missed
    (WED, "2026-10-28T06:00:00Z", "flush", "window-elapsed"),
    (WED, "2026-10-28T06:00:01Z", "hold", "within-review-window"),
    # no usable release date: only the flush day releases the hold
    (TUE, "", "hold", "within-review-window"),
    (TUE, "not-a-date", "hold", "within-review-window"),
    (MON, "", "flush", "flush-day"),
])
def test_window_decision(now, released, decision, reason):
    verdict = st.decide(finding(released=released), weekly(now))
    assert (verdict["decision"], verdict["reasons"]) == (decision, [reason])


def test_flush_weekday_is_configurable_and_next_flush_is_reported():
    friday = weekly(TUE, flushWeekday=st.parseWeekday("fri"))
    assert st.decide(finding(), friday)["nextFlush"] == "2026-11-06"
    assert st.decide(finding(), weekly(TUE))["nextFlush"] == "2026-11-09"
    assert st.decide(finding(), weekly(MON))["nextFlush"] == "2026-11-09"
    with pytest.raises(ValueError):
        st.parseWeekday("someday")


# --- urgent: deliberately narrow ------------------------------------------------------------------------------------


@pytest.mark.parametrize("status", [404, 410])
def test_a_dead_tracked_component_link_is_urgent(status):
    assert st.urgentReasons(finding(liveness=[dead(status)])) == [f"dead-link:garrytan/alpha:{status}"]
    verdict = st.decide(finding(liveness=[dead(status)]), weekly(TUE))
    assert verdict["decision"] == "urgent"


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
    gh = FakeGh()
    report, code = go(gh, [finding(liveness=[dead(404)])], weekly(TUE))
    assert code == 0 and [w[0] for w in gh.writes] == ["create"]
    assert [row["reasons"] for row in report["staging"]["urgent"]] == [["dead-link:garrytan/alpha:404"]]
    assert report["staging"]["held"] == []
    before = gh.write_count()
    report2, _ = go(gh, [finding(liveness=[dead(404)])], weekly(WED))
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
    assert row["suite"] == "garrytan/gbrain" and row["version"] == "v1" and row["planAction"] == "create"
    assert row["candidateIds"] == ["garrytan/gbrain:alpha", "garrytan/gbrain:beta"]
    assert row["nextFlush"] == "2026-11-09" and row["maxHoldUntil"] == "2026-11-10T01:00:00Z"
    assert report["staging"]["flushDay"] is False and report["staging"]["flushWeekday"] == "monday"


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
    go(gh, [finding("v2", ["alpha", "beta"])], weekly(TUE))
    assert gh.write_count() == 0
    assert "upstream:approved" in [label["name"] for label in gh.issues[number]["labels"]]
    go(gh, [finding("v2", ["alpha", "beta"])], weekly(MON + dt.timedelta(days=7)))
    assert "upstream:approved" not in [label["name"] for label in gh.issues[number]["labels"]]
    assert "upstream:needs-info" in [label["name"] for label in gh.issues[number]["labels"]]


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
    gh = FakeGh()
    go(gh, [finding("v1", ["alpha"])], weekly(MON))
    number = open_umbrellas(gh)[0]["number"]
    go(gh, [finding("v2", ["alpha", "beta"])], weekly(WED))
    go(gh, [finding("v2", ["alpha", "beta"])], weekly(MON + dt.timedelta(days=7)))
    assert [row["number"] for row in open_umbrellas(gh)] == [number]
    payload = parse_payload(gh.issues[number]["body"])
    assert payload["newVersion"] == "v2"
    assert [row["id"] for row in payload["candidates"]] == ["garrytan/gbrain:alpha", "garrytan/gbrain:beta"]


# --- closed umbrella is a completed epic (ruling #6) ----------------------------------------------------------------


def test_a_closed_umbrella_is_never_touched_and_new_changes_start_a_new_batch_after_the_window():
    gh = FakeGh()
    go(gh, [finding("v1", ["alpha", "beta"])], weekly(MON))
    closed = open_umbrellas(gh)[0]["number"]
    gh.issues[closed]["state"] = "closed"
    snapshot = json.dumps(gh.issues[closed], sort_keys=True)
    gh.writes.clear()

    held, _ = go(gh, [finding("v2", ["alpha", "beta", "gamma"])], weekly(TUE))
    assert gh.write_count() == 0 and held["suites"][0]["outcome"] == "held"
    assert held["staging"]["held"][0]["planAction"] == "create", "a closed umbrella is not a hold or update target"

    go(gh, [finding("v2", ["alpha", "beta", "gamma"])], weekly(MON + dt.timedelta(days=7)))
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


# --- dedupe without losing provenance or dispositions ---------------------------------------------------------------


def test_journal_deduplicates_versions_and_candidates_but_keeps_first_and_last_seen():
    journal = st.Journal()
    for day, version in ((TUE, "v1"), (TUE + dt.timedelta(hours=3), "v1"), (WED, "v1"), (WED, "v2")):
        journal.observe("garrytan/gbrain", finding(version, ["alpha"]), day)
    bucket = journal.data["repos"]["garrytan/gbrain"]
    assert [row["version"] for row in bucket["versions"]] == ["v1", "v2"]
    v1 = bucket["versions"][0]
    assert v1["observationDays"] == 2 and v1["firstObserved"] == "2026-11-03T06:00:00Z"
    assert v1["lastObserved"] == "2026-11-04T06:00:00Z"
    alpha = bucket["candidates"]["garrytan/gbrain:alpha"]
    assert alpha["firstSeenVersion"] == "v1" and alpha["lastSeenVersion"] == "v2" and alpha["observationDays"] == 2
    assert list(bucket["candidates"]) == ["garrytan/gbrain:alpha"], "one entry per candidate, however often it is seen"


def test_a_rerun_in_the_same_day_does_not_change_the_journal_or_the_report_rows():
    gh, journal = FakeGh(), st.Journal()
    first, _ = go(gh, [finding("v1", ["alpha"])], weekly(TUE), journal)
    second, _ = go(gh, [finding("v1", ["alpha"])], weekly(TUE + dt.timedelta(hours=2)), journal)
    assert gh.write_count() == 0
    alpha = journal.data["repos"]["garrytan/gbrain"]["candidates"]["garrytan/gbrain:alpha"]
    assert alpha["observationDays"] == 1 and alpha["lastObserved"] == "2026-11-03T08:00:00Z"
    assert first["staging"]["held"][0]["candidateIds"] == second["staging"]["held"][0]["candidateIds"]


def test_a_candidate_seen_in_the_window_but_gone_at_flush_is_reported_transient_not_filed():
    gh, journal = FakeGh(), st.Journal()
    go(gh, [finding("v1", ["alpha", "ephemeral"])], weekly(TUE), journal)
    report, _ = go(gh, [finding("v2", ["alpha"])], weekly(MON), journal)
    [row] = report["staging"]["flushed"]
    assert [t["id"] for t in row["transientCandidates"]] == ["garrytan/gbrain:ephemeral"]
    assert row["transientCandidates"][0]["firstSeenVersion"] == "v1"
    assert [v["version"] for v in row["versionsObserved"]] == ["v1", "v2"]
    assert [c["id"] for c in parse_payload(open_umbrellas(gh)[0]["body"])["candidates"]] == ["garrytan/gbrain:alpha"]
    assert "garrytan/gbrain" not in journal.data["repos"], "settled by the write"


def test_the_journal_survives_a_hold_and_is_settled_by_a_write_or_a_noop():
    gh, journal = FakeGh(), st.Journal()
    go(gh, [finding("v1", ["alpha"])], weekly(TUE), journal)
    assert "garrytan/gbrain" in journal.data["repos"]
    go(gh, [finding("v1", ["alpha"])], weekly(MON), journal)
    assert journal.data["repos"] == {}
    go(gh, [finding("v1", ["alpha"])], weekly(MON + dt.timedelta(days=1)), journal)  # noop: nothing to gate
    assert journal.data["repos"] == {}


def test_journal_persists_on_apply_only_and_tolerates_a_missing_or_corrupt_file(tmp_path, capsys):
    path = tmp_path / "nested" / "journal.json"
    gh = FakeGh()
    go(gh, [finding()], weekly(TUE, journalPath=str(path)), apply=False)
    assert not path.exists()
    go(gh, [finding()], weekly(TUE, journalPath=str(path)), apply=True)
    saved = json.loads(path.read_text())
    assert saved["schemaVersion"] == 1 and "garrytan/gbrain" in saved["repos"]
    assert not list(path.parent.glob("*.tmp"))
    go(gh, [finding()], weekly(WED, journalPath=str(path)))
    assert json.loads(path.read_text())["repos"]["garrytan/gbrain"]["versions"][0]["observationDays"] == 2
    path.write_text("{not json", encoding="utf-8")
    assert st.Journal.load(path).data == st.emptyJournal()
    assert "unreadable" in capsys.readouterr().err
    path.write_text(json.dumps({"schemaVersion": 99, "repos": {}}), encoding="utf-8")
    assert st.Journal.load(path).data == st.emptyJournal()
    assert st.Journal.load(tmp_path / "absent.json").data == st.emptyJournal()


def child_row_world():
    """An open umbrella (unstaged v1) whose rows include a candidate a closed child rejected."""
    gh = FakeGh([{
        "number": 41, "title": "[intake] garrytan/rejected-one", "state": "closed",
        "labels": [{"name": "upstream:child"}, {"name": "upstream:rejected"}],
        "body": "**Suggested ID:** `garrytan/rejected-one`\n\n### Evidence\n\n"
                "- **url:** https://github.com/garrytan/gbrain/blob/main/skills/rejected-one/SKILL.md\n",
    }])
    go(gh, [finding("v1", ["alpha", "beta", "rejected-one"])], None)
    return gh


def rows_of(gh):
    return {row["id"]: row for row in parse_payload(open_umbrellas(gh)[0]["body"])["candidates"]}


def test_dispositions_and_first_seen_provenance_survive_held_days_and_the_flush():
    gh = child_row_world()
    before = rows_of(gh)
    assert before["garrytan/gbrain:rejected-one"]["status"] == "rejected"
    assert before["garrytan/gbrain:alpha"]["firstSeenVersion"] == "v1"
    gh.writes.clear()
    journal = st.Journal()
    for offset, version in enumerate(("v2", "v3", "v4")):
        go(gh, [finding(version, ["alpha", "beta", "rejected-one", "delta"])], weekly(TUE + dt.timedelta(days=offset)), journal)
    assert gh.write_count() == 0
    go(gh, [finding("v5", ["alpha", "beta", "rejected-one", "delta"])], weekly(MON), journal)
    after = rows_of(gh)
    assert after["garrytan/gbrain:rejected-one"]["status"] == "rejected"
    for ident in ("garrytan/gbrain:alpha", "garrytan/gbrain:beta"):
        assert after[ident]["firstSeenVersion"] == "v1" and after[ident]["lastSeenVersion"] == "v5"
        assert after[ident]["status"] == before[ident]["status"]
    assert after["garrytan/gbrain:delta"]["firstSeenVersion"] == "v5"


def test_an_escalated_row_keeps_its_child_across_the_staged_flush():
    gh = FakeGh()
    go(gh, [finding("v1", ["alpha", "beta"])], None)
    umbrella = open_umbrellas(gh)[0]
    # An escalation is a human decision: it adds a child and marks the row. Reproduce its stored result.
    child = gh.create_issue("[intake] garrytan/alpha", ["intake", "needs-triage", "upstream:child"],
                            f"> Auto-populated by upstream watcher. Umbrella: #{umbrella['number']}.\n\n"
                            "**Suggested ID:** `garrytan/alpha`\n\n### Evidence\n\n"
                            "- **url:** https://github.com/garrytan/gbrain/blob/main/skills/alpha/SKILL.md\n")
    go(gh, [finding("v1", ["alpha", "beta"])], None)  # re-adopts the open child as `tracked`
    assert rows_of(gh)["garrytan/gbrain:alpha"]["child"] == child
    gh.writes.clear()
    go(gh, [finding("v2", ["alpha", "beta", "gamma"])], weekly(TUE))
    assert gh.write_count() == 0
    go(gh, [finding("v2", ["alpha", "beta", "gamma"])], weekly(MON))
    row = rows_of(gh)["garrytan/gbrain:alpha"]
    assert row["child"] == child and row["status"] == "tracked"
    assert not [w for w in gh.writes if w[0] == "create"], "no second child for an already-tracked candidate"


# --- guards ---------------------------------------------------------------------------------------------------------


def test_a_records_reset_is_never_staged():
    gh = FakeGh()
    with pytest.raises(ValueError, match="reset-records"):
        run_batch([finding()], gh, apply=True, index_loader=lambda: index_from_entries([]),
                  reset_records="garrytan/gbrain", staging=weekly(TUE))
    assert watcher.main(["--child-mode", "batch", "--apply", "--staging", "weekly",
                         "--reset-records", "garrytan/gbrain"]) == 1


def test_a_gh_failure_still_exits_3_with_a_staging_section_and_no_journal_corruption(tmp_path):
    gh = FakeGh()
    gh.fail_list = True
    path = tmp_path / "j.json"
    report, code = go(gh, [finding()], weekly(TUE, journalPath=str(path)))
    assert code == 3 and gh.write_count() == 0
    assert report["staging"]["held"] == []


# --- the CLI switch -------------------------------------------------------------------------------------------------


def test_cli_staging_requires_batch_and_valid_values(capsys):
    assert watcher.main(["--staging", "weekly"]) == 1
    assert "requires --child-mode batch" in capsys.readouterr().err
    assert watcher.main(["--child-mode", "batch", "--staging", "weekly", "--staging-as-of", "yesterday"]) == 1
    assert watcher.main(["--child-mode", "batch", "--staging", "weekly", "--staging-flush-day", "someday"]) == 1
    with pytest.raises(SystemExit):
        watcher.main(["--staging", "daily"])


def test_cli_off_is_the_default_and_passes_an_inert_config(monkeypatch):
    seen = {}
    monkeypatch.setattr(watcher, "_build_registry_map", lambda: {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda: [])
    monkeypatch.setattr(watcher, "run_batch", lambda *a, **k: seen.update(k) or (bt.new_report(), 0))
    monkeypatch.setattr(watcher, "batch_stopped", lambda report: False)
    assert watcher.main(["--child-mode", "batch", "--apply"]) == 0
    assert "staging" not in seen, "the default call is exactly the deployed one"
    seen.clear()
    assert watcher.main(["--child-mode", "batch", "--apply", "--staging", "weekly", "--staging-flush-day", "Fri",
                         "--staging-as-of", "2026-11-03T06:00:00Z", "--staging-journal", "/tmp/x.json"]) == 0
    config = seen["staging"]
    assert (config.mode, config.flushWeekday, config.journalPath) == ("weekly", 4, "/tmp/x.json")
    assert config.now == TUE


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


def test_workflow_escalation_never_stages(tmp_path):
    result, calls = _run_block_with(tmp_path, "workflow_dispatch", {
        "INPUT_STAGING": "weekly", "INPUT_CHILD_MODE": "batch", "INPUT_ESCALATE": "garrytan/gbrain:alpha"})
    assert result.returncode == 0 and "--escalate garrytan/gbrain:alpha" in calls[0] and "--staging" not in calls[0]


def test_workflow_cache_steps_run_only_when_staging_is_on_and_triggers_are_unchanged():
    import pathlib
    import yaml

    doc = yaml.safe_load((pathlib.Path(__file__).resolve().parents[2] / ".github/workflows/upstream-watcher.yml").read_text())
    steps = {step["name"]: step for step in doc["jobs"]["watcher"]["steps"]}
    for name in ("Restore staging journal", "Save staging journal"):
        gate = steps[name]["if"]
        assert "UPSTREAM_BATCH_STAGING == 'weekly'" in gate and "inputs.escalate_candidate == ''" in gate
    assert "actions/cache/restore" in steps["Restore staging journal"]["uses"]
    assert "actions/cache/save" in steps["Save staging journal"]["uses"]
    triggers = doc.get("on", doc.get(True))
    assert triggers["schedule"] == [{"cron": "0 6 * * *"}]
    assert triggers["workflow_dispatch"]["inputs"]["staging"]["default"] == "inherit"
    assert triggers["workflow_dispatch"]["inputs"]["child_mode"]["default"] == "fanout"
    assert doc["permissions"] == {"issues": "write", "contents": "read"}

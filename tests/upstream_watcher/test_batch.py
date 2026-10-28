"""Batch planner tests for upstream watcher issue #2131 (F3 amendment, payloadVersion 2)."""

import json
import pathlib
import subprocess

import pytest

from scripts.upstream_watcher import batch as bt
from scripts.upstream_watcher import prechecks as pc
from scripts.upstream_watcher import watcher
from scripts.upstream_watcher.live import GhError, LiveGh, read_live
from scripts.upstream_watcher.batch import canonical_hash, new_report, parse_payload, plan_suite, run_batch, escalate_candidate
from upstream_fakes import FakeGh, FakeRunner, RestGhRunner, fixture_issue_rows, fixture_registry_entries, index_from_entries

FIXTURE = json.loads(
    (pathlib.Path(__file__).parent / "fixtures" / "live_families.json").read_text(encoding="utf-8")
)
BLOB = "https://github.com/garrytan/gbrain/blob/main/skills/{slug}/SKILL.md"
PREFIX = "[upstream] garrytan/gbrain → "


def finding(version, adds, previous="v0", skill="garrytan/gbrain"):
    return {
        "finding_type": "update",
        "skillId": skill,
        "currentVersion": previous,
        "newVersion": version,
        "releasedAt": "2026-10-21T10:00:00Z",
        "sourceUrl": f"https://github.com/garrytan/gbrain/releases/tag/{version}",
        "mode": "components",
        "componentAdds": list(adds),
        "componentRemoves": [],
        "linkLiveness": [],
        "nameDrift": [],
    }


def open_child(number, slug, contributor="garrytan", umbrella=1):
    return {
        "number": number, "title": f"[intake] {contributor}/{slug}", "state": "open",
        "labels": [{"name": "intake"}, {"name": "upstream:child"}],
        "body": (
            f"> Auto-populated by upstream watcher. Umbrella: #{umbrella}.\n\n"
            f"**Suggested ID:** `{contributor}/{slug}`\n\n### Evidence\n\n"
            f"- **url:** {BLOB.format(slug=slug)}\n"
        ),
    }


def run(gh, findings, apply=True, entries=()):
    index = index_from_entries(list(entries))
    return run_batch(findings, gh, apply=apply, index_loader=lambda: index)


def umbrellas(gh, prefix=PREFIX):
    return [row for row in gh.issues.values() if row["title"].startswith(prefix) and row["state"] == "open"]


def all_umbrellas(gh):
    return [row for row in gh.issues.values() if row["state"] == "open" and "upstream:release" in
            [label["name"] for label in row["labels"]]]


def test_default_batch_emits_one_umbrella_and_no_children():
    gh = FakeGh()
    report, code = run(gh, [finding("v1", ["ask-user", "briefing"])])
    assert code == 0
    assert [w[0] for w in gh.writes] == ["create"]
    assert gh.writes[0][2] == PREFIX + "v1"
    assert all(not row["title"].startswith("[intake]") for row in gh.issues.values())
    payload = parse_payload(umbrellas(gh)[0]["body"])
    assert payload["payloadVersion"] == 2
    assert [row["id"] for row in payload["candidates"]] == ["garrytan/gbrain:ask-user", "garrytan/gbrain:briefing"]
    assert payload["payloadSha256"] == canonical_hash(payload)
    body = umbrellas(gh)[0]["body"]
    assert "### Batch review" in body and "`cand:garrytan/gbrain:ask-user`" in body
    assert report["issuesCreated"] == 1 and report["childMode"] == "batch"


def test_precheck_matrix_retains_every_row_and_suppresses_duplicates():
    gh = FakeGh([
        open_child(40, "tracked-one"),
        {"number": 41, "title": "[intake] garrytan/rejected-one", "state": "closed",
         "labels": [{"name": "upstream:child"}, {"name": "upstream:rejected"}],
         "body": "**Suggested ID:** `garrytan/rejected-one`\n\n### Evidence\n\n"
                 "- **url:** https://github.com/garrytan/gbrain/blob/main/skills/rejected-one/SKILL.md\n"},
    ])
    entries = [
        {"id": "garrytan/present-one", "github": BLOB.format(slug="present-one")},
        {"id": "addy-osmani/alias-one", "github": BLOB.format(slug="alias-one")},
    ]
    report, code = run(gh, [finding("v1", ["present-one", "tracked-one", "rejected-one", "alias-one", "fresh"])],
                       entries=entries)
    assert code == 0
    rows = {row["slug"]: row for row in parse_payload(umbrellas(gh)[0]["body"])["candidates"]}
    assert rows["present-one"]["status"] == "present"
    assert rows["tracked-one"]["status"] == "tracked" and rows["tracked-one"]["child"] == 40
    assert rows["rejected-one"]["status"] == "rejected"
    assert rows["alias-one"]["status"] == "new" and rows["alias-one"]["precheck"]["registry"] == "alias-suspect"
    assert rows["fresh"]["status"] == "new"
    assert len(rows) == 5
    assert report["suppressedDuplicates"] == 3
    assert report["retainedCandidates"] == 5


def test_search_is_never_used_and_lists_are_read_for_tracking():
    gh = FakeGh([open_child(40, "tracked-one")])
    run(gh, [finding("v1", ["tracked-one"])])
    assert gh.list_calls and {state for state, _ in gh.list_calls} == {"open", "closed"}


def test_version_churn_across_three_releases_keeps_one_umbrella_and_keyed_rows():
    gh = FakeGh()
    for version in ("v1", "v2", "v3"):
        _report, code = run(gh, [finding(version, ["ask-user", "briefing"], previous="v0")])
        assert code == 0
    assert len(umbrellas(gh)) == 1
    assert umbrellas(gh)[0]["title"] == PREFIX + "v3"
    payload = parse_payload(umbrellas(gh)[0]["body"])
    ids = [row["id"] for row in payload["candidates"]]
    assert ids == sorted(set(ids)) and len(ids) == 2
    assert all(row["firstSeenVersion"] == "v1" and row["lastSeenVersion"] == "v3" for row in payload["candidates"])
    assert [w[0] for w in gh.writes].count("create") == 1


def test_churn_keeps_rows_that_upstream_dropped():
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user", "briefing"])])
    run(gh, [finding("v2", ["ask-user"], previous="v1")])
    ids = [row["id"] for row in parse_payload(umbrellas(gh)[0]["body"])["candidates"]]
    assert ids == ["garrytan/gbrain:ask-user", "garrytan/gbrain:briefing"]


def test_rerun_of_same_release_performs_zero_writes():
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user"])])
    before = gh.write_count()
    report, code = run(gh, [finding("v1", ["ask-user"])])
    assert code == 0
    assert gh.write_count() == before
    assert report["issuesCreated"] == 0 and report["issuesUpdated"] == 0


def test_dry_run_performs_no_writes_and_reports_plan():
    gh = FakeGh()
    report, code = run(gh, [finding("v1", ["ask-user"])], apply=False)
    assert code == 0 and gh.write_count() == 0
    assert report["dryRun"] is True
    assert report["suites"][0]["newRows"] == 1


def test_approved_umbrella_resets_visibly_on_new_version_once():
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user"])])
    gh.edit_labels(umbrellas(gh)[0]["number"], add=["upstream:approved"])
    comments_before = sum(1 for w in gh.writes if w[0] == "comment")
    run(gh, [finding("v2", ["ask-user"], previous="v1")])
    issue = umbrellas(gh)[0]
    labels = [label["name"] for label in issue["labels"]]
    assert "upstream:approved" not in labels and "upstream:needs-info" in labels
    new_comments = [w for w in gh.writes if w[0] == "comment"][comments_before:]
    assert len(new_comments) == 1
    assert "`v1`" in new_comments[0][2] and "`v2`" in new_comments[0][2]


def test_legacy_approved_umbrella_conversion_resets_approval_once_when_an_approved_field_changed():
    legacy_body = (
        "## legacy\n\n<!-- gaia-upstream-payload\n"
        + json.dumps({"skillId": "garrytan/gbrain", "previousVersion": "v0", "newVersion": "v1",
                      "releasedAt": "", "sourceUrl": "https://github.com/garrytan/gbrain/releases/tag/v1",
                      "mode": "components", "componentAdds": ["ask-user", "briefing"]}, indent=2)
        + "\n-->\n"
    )
    gh = FakeGh([{"number": 77, "title": PREFIX + "v1", "state": "open",
                  "labels": [{"name": "upstream:release"}, {"name": "upstream:approved"}],
                  "body": legacy_body}])
    report, code = run(gh, [finding("v1", ["ask-user", "briefing"])])
    assert code == 0
    # H1: the legacy releasedAt ("") differs from the new release's, an approved field, so approval does not
    # survive. A conversion whose approved fields are unchanged keeps approval (representation_only).
    labels = [label["name"] for label in gh.issues[77]["labels"]]
    assert "upstream:approved" not in labels and "upstream:needs-info" in labels
    assert len(parse_payload(gh.issues[77]["body"])["candidates"]) == 2


def test_racing_writer_triggers_one_replan_then_succeeds_without_duplicate():
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user"])])
    number = umbrellas(gh)[0]["number"]
    gh.stale_on_get[number] = {"updated_at": "racer-1", "body": "changed by someone else"}
    report, code = run(gh, [finding("v2", ["ask-user"], previous="v1")])
    assert code == 0
    assert len(umbrellas(gh)) == 1
    assert umbrellas(gh)[0]["title"] == PREFIX + "v2"
    assert report["suites"][0]["outcome"] == "updated"


def test_racing_writer_persistent_conflict_gives_up_without_duplicate_create():
    class AlwaysRacing(FakeGh):
        def get_issue(self, number):
            self.issues[number]["updated_at"] = self.stamp()
            return super().get_issue(number)

    gh = AlwaysRacing()
    run(gh, [finding("v1", ["ask-user"])])
    report, code = run(gh, [finding("v2", ["ask-user"], previous="v1")])
    assert code == 0
    assert report["suites"][0]["outcome"] == "raced-skip"
    assert len(umbrellas(gh)) == 1
    assert [w[0] for w in gh.writes].count("create") == 1


def test_registry_unreadable_fails_closed_with_zero_writes():
    gh = FakeGh()

    def broken():
        raise pc.RegistryUnreadable("boom")

    report, code = run_batch([finding("v1", ["ask-user"])], gh, apply=True, index_loader=broken)
    assert code == 3
    assert gh.write_count() == 0
    assert report["unknownEvidence"][0]["source"] == "registry"


def test_github_list_failure_fails_closed_with_zero_writes():
    gh = FakeGh()
    gh.fail_list = True
    report, code = run(gh, [finding("v1", ["ask-user"])])
    assert code == 3
    assert gh.write_count() == 0
    assert report["unknownEvidence"][0]["source"] == "github-list"


def test_github_get_failure_mid_run_stops_further_writes():
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user"])])
    gh.fail_get = True
    report, code = run(gh, [finding("v2", ["ask-user"], previous="v1")])
    assert code == 3
    assert report["unknownEvidence"][0]["source"] == "github-write"


def test_report_shape_is_stable():
    gh = FakeGh()
    report, _ = run(gh, [finding("v1", ["ask-user"])])
    for key in ("issuesCreated", "issuesUpdated", "suppressedDuplicates", "retainedCandidates",
                "unknownEvidence", "suites"):
        assert key in report
    assert report["suites"][0].keys() >= {"suite", "umbrella", "newRows", "totalRows"}
    json.dumps(report)


def test_escalate_creates_one_child_and_links_the_row():
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user", "briefing"])])
    result, code = escalate_candidate("garrytan/gbrain:ask-user", gh, apply=True)
    assert code == 0 and result["outcome"] == "created"
    child = gh.issues[result["child"]]
    assert "Umbrella: #" in child["body"] and "upstream:child" in [l["name"] for l in child["labels"]]
    row = next(r for r in parse_payload(umbrellas(gh)[0]["body"])["candidates"] if r["slug"] == "ask-user")
    assert row["child"] == result["child"] and row["status"] == "escalated"
    again, _ = escalate_candidate("garrytan/gbrain:ask-user", gh, apply=True)
    assert again["outcome"] == "already-child"
    assert sum(1 for w in gh.writes if w[0] == "create") == 2  # umbrella + one child only


def test_escalate_adopts_an_existing_child_instead_of_duplicating():
    gh = FakeGh([open_child(40, "ask-user")])
    run(gh, [finding("v1", ["ask-user"])])
    row = next(r for r in parse_payload(umbrellas(gh)[0]["body"])["candidates"] if r["slug"] == "ask-user")
    assert row["child"] == 40  # adopted at plan time, so escalation is a no-op for this row
    result, _ = escalate_candidate("garrytan/gbrain:ask-user", gh, apply=True)
    assert result["outcome"] == "already-child" and result["child"] == 40
    assert sum(1 for w in gh.writes if w[0] == "create") == 1


def test_escalate_does_not_adopt_same_suggested_id_from_another_source_repo():
    unrelated = open_child(40, "ask-user")
    unrelated["body"] = unrelated["body"].replace(
        "https://github.com/garrytan/gbrain/",
        "https://github.com/another/source-repo/",
    )
    gh = FakeGh([unrelated])
    run(gh, [finding("v1", ["ask-user"])])

    result, code = escalate_candidate("garrytan/gbrain:ask-user", gh, apply=True)

    assert code == 0 and result["outcome"] == "created"
    assert result["child"] != 40
    assert gh.issues[40]["state"] == "open"
    assert sum(1 for write in gh.writes if write[0] == "create") == 2


def test_escalate_adopts_a_child_created_after_the_umbrella_was_written():
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user"])])
    gh.add(open_child(40, "ask-user"))
    result, _ = escalate_candidate("garrytan/gbrain:ask-user", gh, apply=True)
    assert result["outcome"] == "adopted" and result["child"] == 40
    assert sum(1 for w in gh.writes if w[0] == "create") == 1


def _row(gh, slug="ask-user"):
    return next(r for r in parse_payload(umbrellas(gh)[0]["body"])["candidates"] if r["slug"] == slug)


def test_escalate_child_created_then_row_update_loses_race_next_run_adopts_without_duplicate():
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user"])])
    gh.stale_on_get[umbrellas(gh)[0]["number"]] = {"updated_at": "racer-1"}
    raced, code = escalate_candidate("garrytan/gbrain:ask-user", gh, apply=True)
    assert code == 0 and raced["outcome"] == "raced-skip"
    child = raced["child"]
    assert gh.issues[child]["title"] == "[intake] garrytan/ask-user"
    assert _row(gh)["child"] is None  # the child exists but the umbrella row update lost the race
    creates = sum(1 for w in gh.writes if w[0] == "create")
    assert creates == 2  # umbrella + the one child created before the race

    again, code = escalate_candidate("garrytan/gbrain:ask-user", gh, apply=True)
    assert code == 0 and again["outcome"] == "adopted" and again["child"] == child
    assert sum(1 for w in gh.writes if w[0] == "create") == creates  # no duplicate child
    assert _row(gh)["child"] == child
    open_intakes = [r["number"] for r in gh.issues.values()
                    if r["state"] == "open" and r["title"] == "[intake] garrytan/ask-user"]
    assert open_intakes == [child]


def test_poll_after_lost_escalation_race_links_the_existing_child_without_duplicate():
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user"])])
    gh.stale_on_get[umbrellas(gh)[0]["number"]] = {"updated_at": "racer-1"}
    raced, _ = escalate_candidate("garrytan/gbrain:ask-user", gh, apply=True)
    assert raced["outcome"] == "raced-skip"
    report, code = run(gh, [finding("v1", ["ask-user"])])
    assert code == 0 and report["suites"][0]["outcome"] == "updated"
    assert _row(gh)["child"] == raced["child"] and _row(gh)["status"] == "tracked"
    assert sum(1 for w in gh.writes if w[0] == "create") == 2  # no second child from the poll


def test_escalate_unknown_candidate_exits_two():
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user"])])
    result, code = escalate_candidate("garrytan/gbrain:nope", gh, apply=True)
    assert code == 2 and result["outcome"] == "not-found"


def test_pagination_follows_three_pages_and_never_searches():
    rows = [{"number": n, "state": "open", "title": "t", "labels": [], "body": ""} for n in range(1, 206)]
    runner = RestGhRunner(rows)
    gh = LiveGh(repo="gaia-research/gaia-skill-tree", runner=runner)
    listed = gh.list_issues("open")
    assert len(listed) == 205
    assert not any(arg.startswith("search") or "/search/" in arg for call in runner.calls for arg in call)


def test_a_full_page_without_a_next_link_is_confirmed_only_by_the_repository_count():
    """A full page with no next link is not proof of the end. The open listing is confirmed exactly by the count."""

    rows = [{"number": n, "state": "open", "title": "t", "labels": [], "body": ""} for n in range(1, 101)]
    confirmed = RestGhRunner(rows, no_link_pages={("open", "", 1)})
    assert len(LiveGh(repo="gaia-research/gaia-skill-tree", runner=confirmed).list_issues("open")) == 100

    refuted = RestGhRunner(rows, no_link_pages={("open", "", 1)}, open_count=150)
    with pytest.raises(GhError):
        LiveGh(repo="gaia-research/gaia-skill-tree", runner=refuted).list_issues("open")


def test_pagination_refuses_silent_truncation():
    full = [{"number": n} for n in range(100)]
    runner = FakeRunner({"open": [full] * 200})
    gh = LiveGh(repo="gaia-research/gaia-skill-tree", runner=runner)
    with pytest.raises(GhError):
        gh.list_issues("open")


def test_list_failure_from_gh_is_surfaced_as_gherror():
    def failing(args, capture_output=True, text=True, timeout=None):
        import subprocess
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="rate limited")

    with pytest.raises(GhError):
        LiveGh(repo="gaia-research/gaia-skill-tree", runner=failing).list_issues("open")


def test_legacy_approved_umbrella_detection_does_not_treat_seen_components_as_new():
    previous = {"componentAdds": ["ask-user"], "newVersion": "v1"}
    assert bt.baseline_ids(previous, "garrytan/gbrain") == {"garrytan/gbrain:ask-user"}
    assert bt.baseline_ids(None, "garrytan/gbrain") == set()


def test_fanout_mode_uses_legacy_create_issues(monkeypatch):
    calls = {"create": [], "batch": []}
    monkeypatch.setattr(watcher, "_build_registry_map", lambda: {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda: iter([(None, {"id": "garrytan/gbrain", "links": {"github": "https://github.com/garrytan/gbrain"}})]))
    monkeypatch.setattr(watcher, "_poll_suite", lambda fm, rm, verbose: finding("v1", ["ask-user"]))

    def fake_create(findings, apply, verbose=False):
        calls["create"].append((len(findings), apply))
        return []

    monkeypatch.setattr(watcher, "create_issues", fake_create)
    monkeypatch.setattr(watcher, "run_batch", lambda *a, **k: calls["batch"].append(1) or ({}, 0))
    assert watcher.main(["--apply", "--child-mode", "fanout"]) == 0
    assert calls["create"] == [(1, True)] and calls["batch"] == []


def _fanout_finding(version="v1"):
    return {**finding(version, ["ask-user"]), "mode": "components"}


def test_fanout_github_list_failure_exits_3_with_zero_writes(monkeypatch, tmp_path):
    # The open umbrella LIST fails on its first page. The fanout must exit 3 and create nothing.
    world = RestGhRunner([], fail_pages={("open", "", 1)})
    monkeypatch.setattr(subprocess, "run", world)
    monkeypatch.setattr(watcher, "_build_registry_map", lambda: {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda: iter([(None, {"id": "garrytan/gbrain"})]))
    monkeypatch.setattr(watcher, "_poll_suite", lambda fm, rm, verbose: _fanout_finding())
    report_path = tmp_path / "report.json"
    code = watcher.main(["--apply", "--child-mode", "fanout", "--report", str(report_path)])
    assert code == 3
    assert world.writes == []
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["unknownEvidence"][0]["source"] == "github-list"
    assert report["issuesCreated"] == 0


def test_fanout_child_list_failure_creates_no_umbrella_either(monkeypatch, tmp_path):
    # Only the intake LIST fails. Its lookup comes after the umbrella lookup, yet it must
    # still stop the run before the umbrella is written.
    world = RestGhRunner([], fail_pages={("open", "", 1)})
    monkeypatch.setattr(subprocess, "run", world)
    monkeypatch.setattr(watcher, "_build_registry_map", lambda: {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda: iter([(None, {"id": "garrytan/gbrain"})]))
    monkeypatch.setattr(watcher, "_poll_suite", lambda fm, rm, verbose: _fanout_finding())
    code = watcher.main(["--apply", "--child-mode", "fanout", "--report", str(tmp_path / "r.json")])
    assert code == 3
    assert world.writes == []


def test_batch_mode_bootstrap_lookup_failure_exits_3(monkeypatch, tmp_path):
    bootstrap = {
        "finding_type": "bootstrap", "skillId": "garrytan/gbrain", "newVersion": "v1",
        "releasedAt": "2026-10-21T10:00:00Z",
        "sourceUrl": "https://github.com/garrytan/gbrain/releases/tag/v1",
        "mode": "bootstrap", "componentAdds": [], "componentRemoves": [], "linkLiveness": [], "nameDrift": [],
    }
    world = RestGhRunner([], fail_pages={("open", "", 1)})
    monkeypatch.setattr(subprocess, "run", world)
    monkeypatch.setattr(watcher, "_build_registry_map", lambda: {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda: iter([(None, {"id": "garrytan/gbrain"})]))
    monkeypatch.setattr(watcher, "_poll_suite", lambda fm, rm, verbose: bootstrap)
    monkeypatch.setattr(watcher, "run_batch", lambda *a, **k: (new_report(), 0))
    report_path = tmp_path / "report.json"
    code = watcher.main(["--apply", "--report", str(report_path)])
    assert code == 3
    assert world.writes == []
    assert json.loads(report_path.read_text(encoding="utf-8"))["unknownEvidence"][0]["source"] == "github-list"


def test_batch_mode_is_default_and_fails_closed_on_registry(monkeypatch, tmp_path):
    monkeypatch.setattr(watcher, "_build_registry_map", lambda: (_ for _ in ()).throw(RuntimeError("no registry")))
    report_path = tmp_path / "report.json"
    code = watcher.main(["--apply", "--report", str(report_path)])
    assert code == 3
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["unknownEvidence"][0]["source"] == "registry"
    assert report["issuesCreated"] == 0


# ---------------------------------------------------------------------------
# Dry-run simulation on the four live families (fixture from the 2026-10-21 census)
# ---------------------------------------------------------------------------


def family_findings():
    result = []
    for umbrella in FIXTURE["umbrellas"]:
        payload = parse_payload(umbrella["body"])
        result.append({
            "finding_type": "update",
            "skillId": payload["skillId"],
            "currentVersion": payload["previousVersion"],
            "newVersion": payload["newVersion"],
            "releasedAt": payload["releasedAt"],
            "sourceUrl": payload["sourceUrl"],
            "mode": payload["mode"],
            "componentAdds": payload["componentAdds"],
            "componentRemoves": payload["componentRemoves"],
            "linkLiveness": [],
            "nameDrift": [],
        })
    return result


def family_gh():
    return FakeGh(fixture_issue_rows(FIXTURE))


def test_simulation_dry_run_on_live_families_proposes_no_creates():
    gh = family_gh()
    index = index_from_entries(fixture_registry_entries(FIXTURE))
    report, code = run_batch(family_findings(), gh, apply=False, index_loader=lambda: index)
    assert code == 0
    assert report["issuesCreated"] == 0
    assert gh.write_count() == 0
    by_suite = {row["suite"]: row for row in report["suites"]}
    assert set(by_suite) == {"garrytan/gbrain", "addyosmani/agent-skills", "obra/superpowers", "heygen-com/hyperframes"}
    assert {s: by_suite[s]["totalRows"] for s in by_suite} == {
        "garrytan/gbrain": 72, "addyosmani/agent-skills": 17, "obra/superpowers": 4, "heygen-com/hyperframes": 3,
    }
    assert report["retainedCandidates"] == 96
    # Every live child is open and tracks its candidate: all 96 are suppressed, none is new work.
    assert report["suppressedDuplicates"] == 96
    assert {s: by_suite[s]["newRows"] for s in by_suite} == {
        "garrytan/gbrain": 72, "addyosmani/agent-skills": 17, "obra/superpowers": 4, "heygen-com/hyperframes": 3,
    }


def test_simulation_apply_then_rerun_is_idempotent_and_keeps_approvals():
    gh = family_gh()
    index = index_from_entries(fixture_registry_entries(FIXTURE))
    report, code = run_batch(family_findings(), gh, apply=True, index_loader=lambda: index)
    assert code == 0 and report["issuesCreated"] == 0 and report["issuesUpdated"] == 4
    approved = {row["title"] for row in all_umbrellas(gh) if "upstream:approved" in [l["name"] for l in row["labels"]]}
    assert approved == {"[upstream] garrytan/gbrain → v0.60.340.0", "[upstream] heygen-com/hyperframes → v0.8.181"}
    before = gh.write_count()
    report2, code2 = run_batch(family_findings(), gh, apply=True, index_loader=lambda: index)
    assert code2 == 0 and gh.write_count() == before
    assert report2["issuesUpdated"] == 0 and report2["issuesCreated"] == 0
    assert all(s["outcome"] == "noop" for s in report2["suites"])
    assert len(all_umbrellas(gh)) == 4


def test_simulation_status_breakdown_pins_live_precheck_results():
    gh = family_gh()
    index = index_from_entries(fixture_registry_entries(FIXTURE))
    live = read_live(gh)
    statuses = {}
    alias = 0
    for item in family_findings():
        plan = plan_suite(item, live, index)
        for row in plan["payload"]["candidates"]:
            statuses[row["status"]] = statuses.get(row["status"], 0) + 1
            alias += row["precheck"]["registry"] == "alias-suspect"
    assert statuses == {"present": 17, "tracked": 79}
    assert alias == 24

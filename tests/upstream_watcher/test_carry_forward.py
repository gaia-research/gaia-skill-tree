"""Carry-forward of unresolved candidate rows from a closed umbrella (#2131).

Closing an umbrella must never drop candidates. A new umbrella for the suite is
seeded with the unresolved rows of the newest closed one: status, child link and
firstSeenVersion are kept, and carriedFrom records the umbrella they came from.
"""

import datetime as dt

import pytest

from scripts.upstream_watcher import batch as bt
from scripts.upstream_watcher import live
from scripts.upstream_watcher.batch import parse_payload, run_batch
from scripts.upstream_watcher.live import LiveGh, read_live
from upstream_fakes import FakeGh, RestGhRunner, index_from_entries

PREFIX = "[upstream] garrytan/gbrain → "
REPO = "gaia-research/gaia-skill-tree"
BLOB = "https://github.com/garrytan/gbrain/blob/main/skills/{slug}/SKILL.md"


def days_ago(days):
    now = dt.datetime.now(dt.timezone.utc)
    return (now - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def finding(version, adds, previous="v0"):
    return {
        "finding_type": "update",
        "skillId": "garrytan/gbrain",
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


def row(slug, status="new", child=None, first="v1"):
    return {
        "id": f"garrytan/gbrain:{slug}", "slug": slug, "suggestedId": f"garrytan/{slug}",
        "evidenceUrl": BLOB.format(slug=slug), "firstSeenVersion": first, "lastSeenVersion": first,
        "child": child, "status": status, "precheck": {"registry": "absent", "tracked": "none",
                                                       "priorDisposition": "none"},
    }


def closed_umbrella(number, version, rows, previous="v0"):
    payload = bt.build_payload(
        {**finding(version, [], previous=previous), "componentAdds": []}, rows, previous_version=previous
    )
    return {
        "number": number, "title": f"{PREFIX}{version}", "state": "closed",
        "labels": [{"name": "upstream:release"}], "body": bt.render_batch_body(payload),
        "updated_at": "2026-10-20T10:00:00Z",
    }


def child_issue(number, state, slug="ask-user"):
    return {
        "number": number, "title": f"[intake] garrytan/{slug}", "state": state,
        "labels": [{"name": "upstream:child"}],
        "body": f"> Auto-populated by upstream watcher. Umbrella: #10.\n\n**Suggested ID:** `garrytan/{slug}`\n",
    }


def run(gh, findings):
    return run_batch(findings, gh, apply=True, index_loader=lambda: index_from_entries([]))


def open_umbrella(gh):
    found = [r for r in gh.issues.values() if r["title"].startswith(PREFIX) and r["state"] == "open"]
    assert len(found) == 1, [r["title"] for r in found]
    return found[0]


def rows_of(gh):
    return {r["id"]: r for r in parse_payload(open_umbrella(gh)["body"])["candidates"]}


def test_closing_an_umbrella_with_unresolved_rows_carries_them_into_the_new_one():
    gh = FakeGh([closed_umbrella(10, "v1", [row("ask-user"), row("briefing")])])
    report, code = run(gh, [finding("v2", ["fresh"], previous="v1")])
    assert code == 0
    rows = rows_of(gh)
    assert sorted(rows) == ["garrytan/gbrain:ask-user", "garrytan/gbrain:briefing", "garrytan/gbrain:fresh"]
    assert rows["garrytan/gbrain:ask-user"]["carriedFrom"] == "#10"
    assert rows["garrytan/gbrain:ask-user"]["firstSeenVersion"] == "v1"
    assert "carriedFrom" not in rows["garrytan/gbrain:fresh"]
    assert report["suites"][0]["carriedForward"] == 2
    assert [w[0] for w in gh.writes].count("create") == 1


def test_carried_rows_keep_their_status_and_child_link():
    gh = FakeGh([
        child_issue(41, "open", slug="ask-user"),
        closed_umbrella(10, "v1", [row("ask-user", status="escalated", child=41)]),
    ])
    run(gh, [finding("v2", [], previous="v1")])
    kept = rows_of(gh)["garrytan/gbrain:ask-user"]
    assert kept["status"] == "escalated" and kept["child"] == 41
    assert kept["firstSeenVersion"] == "v1" and kept["carriedFrom"] == "#10"


def test_a_row_the_new_release_also_lists_is_not_duplicated_and_keeps_its_first_seen():
    gh = FakeGh([closed_umbrella(10, "v1", [row("ask-user")])])
    run(gh, [finding("v2", ["ask-user"], previous="v1")])
    rows = parse_payload(open_umbrella(gh)["body"])["candidates"]
    ids = [r["id"] for r in rows]
    assert ids == ["garrytan/gbrain:ask-user"]
    assert rows[0]["firstSeenVersion"] == "v1" and rows[0]["lastSeenVersion"] == "v2"
    assert rows[0]["carriedFrom"] == "#10"


def test_resolved_rows_are_not_carried():
    gh = FakeGh([
        # Closed WITH upstream:rejected: a disposition, so its row resolves. (A closed child without one keeps its
        # row; test_c8_m3_m6_rows.py covers that rule.)
        {**child_issue(41, "closed", slug="done-one"),
         "labels": [{"name": "upstream:child"}, {"name": "upstream:rejected"}]},
        closed_umbrella(10, "v1", [
            row("present-one", status="present"),
            row("rejected-one", status="rejected"),
            row("done-one", status="tracked", child=41),
            row("still-new"),
        ]),
    ])
    run(gh, [finding("v2", [], previous="v1")])
    assert sorted(rows_of(gh)) == ["garrytan/gbrain:still-new"]


def test_a_closed_child_that_is_absent_is_carried_as_unresolved_and_its_link_cleared():
    # Child #999 is gone (404): the row is unresolved again, so it is carried with no link.
    gh = FakeGh([closed_umbrella(10, "v1", [row("ask-user", status="escalated", child=999)])])
    run(gh, [finding("v2", [], previous="v1")])
    kept = rows_of(gh)["garrytan/gbrain:ask-user"]
    assert kept["child"] is None and kept["status"] == "new"
    assert kept["carriedFrom"] == "#10"


def test_only_the_newest_closed_umbrella_is_the_source():
    gh = FakeGh([
        closed_umbrella(10, "v1", [row("old-only")]),
        closed_umbrella(20, "v2", [row("newer-only", first="v2")], previous="v1"),
    ])
    run(gh, [finding("v3", ["fresh"], previous="v2")])
    assert sorted(rows_of(gh)) == ["garrytan/gbrain:fresh", "garrytan/gbrain:newer-only"]
    assert rows_of(gh)["garrytan/gbrain:newer-only"]["carriedFrom"] == "#20"


def test_carry_is_idempotent_and_a_rerun_performs_zero_writes():
    gh = FakeGh([closed_umbrella(10, "v1", [row("ask-user"), row("briefing")])])
    run(gh, [finding("v2", ["fresh"], previous="v1")])
    before = gh.write_count()
    report, code = run(gh, [finding("v2", ["fresh"], previous="v1")])
    assert code == 0 and gh.write_count() == before
    assert report["issuesCreated"] == 0 and report["issuesUpdated"] == 0
    assert len(rows_of(gh)) == 3


def test_no_carry_when_an_open_umbrella_already_exists():
    gh = FakeGh([
        closed_umbrella(10, "v1", [row("old-only")]),
        {"number": 11, "title": f"{PREFIX}v2", "state": "open", "labels": [{"name": "upstream:release"}],
         "body": bt.render_batch_body(bt.build_payload(
             {**finding("v2", [], previous="v1"), "componentAdds": []}, [row("live")], previous_version="v1")),
         "updated_at": "2026-10-20T10:00:00Z"},
    ])
    run(gh, [finding("v2", [], previous="v1")])
    assert sorted(rows_of(gh)) == ["garrytan/gbrain:live"]


def test_a_legacy_closed_umbrella_carries_nothing():
    legacy = {
        "number": 10, "title": f"{PREFIX}v1", "state": "closed", "labels": [{"name": "upstream:release"}],
        "body": "<!-- gaia-upstream-payload\n" + '{"skillId": "garrytan/gbrain", "newVersion": "v1", '
                '"componentAdds": ["ask-user"]}' + "\n-->",
        "updated_at": "2026-10-20T10:00:00Z",
    }
    gh = FakeGh([legacy])
    report, code = run(gh, [finding("v2", ["fresh"], previous="v1")])
    assert code == 0
    assert sorted(rows_of(gh)) == ["garrytan/gbrain:fresh"]
    assert report["suites"][0]["carriedForward"] == 0


def test_carried_umbrella_body_says_where_the_rows_came_from():
    gh = FakeGh([closed_umbrella(10, "v1", [row("ask-user"), row("briefing")])])
    run(gh, [finding("v2", [], previous="v1")])
    assert "Carried forward from closed umbrella #10: 2 unresolved row(s) kept open." in open_umbrella(gh)["body"]


def test_no_carried_note_when_nothing_was_carried():
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user"])])
    assert "Carried forward" not in open_umbrella(gh)["body"]


# ---------------------------------------------------------------------------
# The source is the full closed umbrella history, not the 30-day window (#2131).
# ---------------------------------------------------------------------------


def _other_suite_umbrella(number):
    return {**closed_umbrella(number, "v1", []), "title": f"[upstream] other/suite{number} → v1",
            "updated_at": days_ago(90)}


def test_an_umbrella_closed_ninety_days_ago_still_carries_its_unresolved_rows():
    old = closed_umbrella(10, "v1", [row("ask-user"), row("briefing")])
    old["updated_at"] = days_ago(90)
    gh = FakeGh([old])
    # The recently-closed window cannot see it, so only the full history can carry it.
    assert 10 not in {issue["number"] for issue in read_live(gh)["issues"]}
    report, code = run(gh, [finding("v2", ["fresh"], previous="v1")])
    assert code == 0
    rows = rows_of(gh)
    assert sorted(rows) == ["garrytan/gbrain:ask-user", "garrytan/gbrain:briefing", "garrytan/gbrain:fresh"]
    assert rows["garrytan/gbrain:ask-user"]["carriedFrom"] == "#10"
    assert report["suites"][0]["carriedForward"] == 2


def test_carry_walks_every_page_of_the_closed_umbrella_history_to_find_the_newest(monkeypatch):
    monkeypatch.setattr(live, "PER_PAGE", 2)
    old = closed_umbrella(10, "v1", [row("ask-user")])
    old["updated_at"] = days_ago(90)
    world = RestGhRunner([_other_suite_umbrella(n) for n in (1, 2, 3, 4)] + [old])
    gh = LiveGh(repo=REPO, runner=world)
    # Five closed umbrellas over three pages of two: #10 sits on the last, short page.
    assert {issue["number"] for issue in read_live(gh)["closedUmbrellas"]} == {1, 2, 3, 4, 10}
    report, code = run(gh, [finding("v2", ["fresh"], previous="v1")])
    assert code == 0 and report["unknownEvidence"] == []
    creates = [write for write in world.writes if write[0] == "create"]
    assert len(creates) == 1
    payload = parse_payload(creates[0][2])
    assert sorted(row["id"] for row in payload["candidates"]) == ["garrytan/gbrain:ask-user", "garrytan/gbrain:fresh"]
    assert next(row for row in payload["candidates"] if row["slug"] == "ask-user")["carriedFrom"] == "#10"


@pytest.mark.parametrize("failing_page", [1, 2])
def test_an_incomplete_closed_umbrella_walk_is_unknown_evidence_with_zero_writes(monkeypatch, failing_page):
    monkeypatch.setattr(live, "PER_PAGE", 2)
    old = closed_umbrella(10, "v1", [row("ask-user")])
    old["updated_at"] = days_ago(90)
    world = RestGhRunner(
        [_other_suite_umbrella(n) for n in (1, 2, 3, 4)] + [old],
        fail_pages={("closed", "upstream:release", failing_page)},
    )
    report, code = run(LiveGh(repo=REPO, runner=world), [finding("v2", ["fresh"], previous="v1")])
    assert code == 3
    assert report["unknownEvidence"] and report["unknownEvidence"][0]["source"] == "github-list"
    assert world.writes == []
    assert report["issuesCreated"] == 0

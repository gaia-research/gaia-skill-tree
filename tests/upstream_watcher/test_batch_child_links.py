"""Dead and absent child links for the batch planner (#2131).

A definitive 301 (transferred), 404 or 410 clears the link and returns the row
to visible unresolved work (nothing is dropped). A live child that the LIST
snapshot omits keeps its link. Any other lookup failure fails closed with zero
writes.
"""

import subprocess

import pytest

from scripts.upstream_watcher import batch as bt
from scripts.upstream_watcher.batch import escalate_candidate, parse_payload, run_batch
from scripts.upstream_watcher.live import GhError, LiveGh
from upstream_fakes import FakeGh, index_from_entries

PREFIX = "[upstream] garrytan/gbrain → "


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


def open_child(number, slug):
    return {
        "number": number, "title": f"[intake] garrytan/{slug}", "state": "open",
        "labels": [{"name": "intake"}, {"name": "upstream:child"}],
        "body": f"> Auto-populated by upstream watcher. Umbrella: #1.\n\n**Suggested ID:** `garrytan/{slug}`\n",
    }


def run(gh, findings, apply=True):
    index = index_from_entries([])
    return run_batch(findings, gh, apply=apply, index_loader=lambda: index)


def umbrella_rows(gh):
    return [row for row in gh.issues.values() if row["title"].startswith(PREFIX) and row["state"] == "open"]


def row_of(gh, slug="ask-user"):
    payload = parse_payload(umbrella_rows(gh)[0]["body"])
    return next(r for r in payload["candidates"] if r["slug"] == slug)


def escalated_child(gh, slug="ask-user"):
    run(gh, [finding("v1", [slug, "briefing"])])
    result, _ = escalate_candidate(f"garrytan/gbrain:{slug}", gh, apply=True)
    assert result["outcome"] == "created"
    return result["child"]


def test_deleted_escalated_child_clears_link_and_row_is_unresolved_again():
    gh = FakeGh()
    child = escalated_child(gh)
    assert row_of(gh)["status"] == "escalated" and row_of(gh)["child"] == child

    del gh.issues[child]  # GitHub now answers 404 for the child
    report, code = run(gh, [finding("v2", ["ask-user", "briefing"], previous="v1")])
    assert code == 0 and report["unknownEvidence"] == []
    row = row_of(gh)
    assert row["child"] is None
    assert row["status"] == "new"
    assert row["precheck"]["tracked"] == "none"
    assert row["id"] == "garrytan/gbrain:ask-user"  # retained, never dropped


def test_deleted_tracked_child_goes_back_to_new_and_stays_in_the_umbrella():
    gh = FakeGh([open_child(40, "ask-user")])
    run(gh, [finding("v1", ["ask-user"])])
    assert row_of(gh)["status"] == "tracked" and row_of(gh)["child"] == 40

    del gh.issues[40]
    run(gh, [finding("v2", ["ask-user"], previous="v1")])
    row = row_of(gh)
    assert row["child"] is None and row["status"] == "new"


def test_dead_child_clear_is_idempotent_on_rerun():
    gh = FakeGh()
    child = escalated_child(gh)
    del gh.issues[child]
    run(gh, [finding("v2", ["ask-user", "briefing"], previous="v1")])
    before = gh.write_count()
    report, code = run(gh, [finding("v2", ["ask-user", "briefing"], previous="v1")])
    assert code == 0 and gh.write_count() == before
    assert report["issuesUpdated"] == 0


def test_live_child_hidden_from_the_snapshot_keeps_its_link():
    # GitHub still serves #N as open, so it is not absent: the link and status stay.
    gh = FakeGh()
    child = escalated_child(gh)
    gh.hidden_from_list.add(child)
    run(gh, [finding("v2", ["ask-user", "briefing"], previous="v1")])
    row = row_of(gh)
    assert row["child"] == child and row["status"] == "escalated"


def test_closed_child_outside_the_window_keeps_link_and_stays_resolved():
    gh = FakeGh()
    child = escalated_child(gh)
    gh.issues[child]["state"] = "closed"
    gh.hidden_from_list.add(child)
    run(gh, [finding("v2", ["ask-user", "briefing"], previous="v1")])
    row = row_of(gh)
    assert row["child"] == child and row["status"] == "escalated"


def test_probe_failure_on_a_hidden_child_fails_closed_with_zero_writes():
    gh = FakeGh()
    child = escalated_child(gh)
    gh.hidden_from_list.add(child)
    gh.fail_get = True
    before = gh.write_count()
    report, code = run(gh, [finding("v2", ["ask-user", "briefing"], previous="v1")])
    assert code == 3
    assert gh.write_count() == before
    assert report["unknownEvidence"][0]["source"] == "github-write"
    assert row_of(gh)["child"] == child  # unknown evidence never clears a link


def test_escalate_adopting_a_child_marks_the_row_tracked_at_once():
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user", "briefing"])])
    assert row_of(gh)["status"] == "new"
    gh.add(open_child(40, "ask-user"))
    result, _ = escalate_candidate("garrytan/gbrain:ask-user", gh, apply=True)
    assert result["outcome"] == "adopted" and result["child"] == 40
    row = row_of(gh)
    assert row["status"] == "tracked" and row["child"] == 40
    assert row["precheck"]["tracked"] == "child:#40"


def test_escalate_replaces_an_absent_child_instead_of_reporting_already_child():
    gh = FakeGh()
    child = escalated_child(gh)
    del gh.issues[child]
    result, code = escalate_candidate("garrytan/gbrain:ask-user", gh, apply=True)
    assert code == 0 and result["outcome"] == "created"
    assert result["child"] != child
    row = row_of(gh)
    assert row["child"] == result["child"] and row["status"] == "escalated"
    assert sum(1 for w in gh.writes if w[0] == "create") == 3  # umbrella, first child, replacement


def test_escalate_with_a_failing_child_probe_is_unknown_not_already_child():
    gh = FakeGh()
    child = escalated_child(gh)
    gh.hidden_from_list.add(child)
    gh.fail_get = True
    result, code = escalate_candidate("garrytan/gbrain:ask-user", gh, apply=True)
    assert code == 3 and result["outcome"] == "unknown"


def test_merge_rows_clears_only_dead_links_and_keeps_live_ones():
    existing = [
        {"id": "a/x:one", "slug": "one", "status": "tracked", "child": 10, "precheck": {"tracked": "child:#10"}},
        {"id": "a/x:two", "slug": "two", "status": "escalated", "child": 11, "precheck": {}},
        {"id": "a/x:three", "slug": "three", "status": "present", "child": 12, "precheck": {}},
    ]
    rows, added = bt.merge_rows(existing, [], "v9", dead=frozenset({10, 11}))
    by_id = {row["id"]: row for row in rows}
    assert by_id["a/x:one"]["child"] is None and by_id["a/x:one"]["status"] == "new"
    assert by_id["a/x:one"]["precheck"]["tracked"] == "none"
    assert by_id["a/x:two"]["child"] is None and by_id["a/x:two"]["status"] == "new"
    assert by_id["a/x:three"]["child"] == 12 and by_id["a/x:three"]["status"] == "present"
    assert added == [] and len(rows) == 3


def test_child_state_lookup_probes_only_numbers_the_snapshot_lacks():
    probed = []

    def probe(number):
        probed.append(number)
        return "absent"

    live = {"issues": [{"number": 1, "state": "open"}, {"number": 2, "state": "closed"}]}
    state_of = bt.child_state_lookup(live, probe)
    assert state_of(1) == "open" and state_of(2) == "closed"
    assert state_of(3) == "absent" and state_of(3) == "absent"
    assert probed == [3]  # one GET, cached
    assert bt.child_state_lookup(live)(9) == bt.CHILD_UNKNOWN  # no probe: unknown, never absent


def test_unknown_probe_result_keeps_the_row_unresolved_and_its_link():
    # A probe-less lookup (pure planning) must never clear a link.
    rows = [{"id": "a/x:one", "status": "escalated", "child": 77}]
    state_of = bt.child_state_lookup({"issues": []})
    assert bt.dead_children(rows, state_of) == frozenset()
    assert bt.row_is_unresolved(rows[0], state_of) is True


def test_transferred_escalated_child_301_clears_link_and_row_is_unresolved_again():
    # The child was transferred: its old number answers HTTP 301, so it is absent.
    gh = FakeGh()
    child = escalated_child(gh)
    gh.moved.add(child)
    report, code = run(gh, [finding("v2", ["ask-user", "briefing"], previous="v1")])
    assert code == 0 and report["unknownEvidence"] == []
    row = row_of(gh)
    assert row["child"] is None
    assert row["status"] == "new"
    assert row["precheck"]["tracked"] == "none"
    assert row["id"] == "garrytan/gbrain:ask-user"  # retained, never dropped


def test_transferred_child_301_is_absent_to_escalation_which_creates_a_replacement():
    gh = FakeGh()
    child = escalated_child(gh)
    gh.moved.add(child)
    result, code = escalate_candidate("garrytan/gbrain:ask-user", gh, apply=True)
    assert code == 0 and result["outcome"] == "created"
    assert result["child"] != child
    assert row_of(gh)["child"] == result["child"]


@pytest.mark.parametrize(
    ("stderr", "expected"),
    [
        ("gh: Moved Permanently (HTTP 301)", "absent"),
        ("gh: Not Found (HTTP 404)", "absent"),
        ("gh: Gone (HTTP 410)", "absent"),
        ("gh: Forbidden (HTTP 403)", "error"),
        ("gh: Server Error (HTTP 502)", "error"),
        ("gh: Moved Permanently (HTTP 3011)", "error"),  # 301 must be the whole status, not a prefix
        ("gh: something went wrong", "error"),
    ],
)
def test_only_301_404_410_are_absent_every_other_failure_is_unknown(stderr, expected, capsys):
    def runner(args, capture_output=True, text=True, timeout=None):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr=stderr)

    gh = LiveGh(repo="gaia-research/gaia-skill-tree", runner=runner)
    if expected == "absent":
        assert gh.issue_state(5001) == "absent"
        notice = capsys.readouterr().err
        assert "::notice::child #5001 is absent" in notice
    else:
        with pytest.raises(GhError):
            gh.issue_state(5001)


def test_transferred_child_is_never_a_list_answer_so_a_list_301_fails_closed():
    # A 301 on the LIST endpoint is not an absent child: the snapshot is unknown evidence.
    def runner(args, capture_output=True, text=True, timeout=None):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="gh: Moved Permanently (HTTP 301)")

    with pytest.raises(GhError):
        LiveGh(repo="gaia-research/gaia-skill-tree", runner=runner).list_issues("open")


def test_unparseable_child_answer_is_unknown_not_absent():
    def runner(args, capture_output=True, text=True, timeout=None):
        return subprocess.CompletedProcess(args, 0, stdout="<html>proxy</html>", stderr="")

    with pytest.raises(GhError):
        LiveGh(repo="gaia-research/gaia-skill-tree", runner=runner).issue_state(5001)

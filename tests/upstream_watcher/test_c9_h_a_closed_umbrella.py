"""#2131 round-5 verifier FAIL, H-A: a closed umbrella suppresses recreating its own suite and version.

Before this change ``plan_suite`` created an umbrella whenever no OPEN umbrella with the suite prefix existed.
A rejected umbrella was therefore re-created every day for the same version: day 1 #5000, rejected and closed,
then day 2 #5001 for the same version, and every day after.

Now the newest closed ``upstream:release`` umbrella whose title names the same suite and version suppresses the
create. It is reported under ``suppressedClosedUmbrella`` with its issue number, whatever its disposition:
``rejected`` (upstream:rejected), ``completed`` (closed as completed by the approve flow) or
``closed-unresolved`` (closed with no disposition). A NEW version creates normally. A failed page of the closed
umbrella history is unknown evidence: exit 3, zero writes.
"""

from __future__ import annotations

from upstream_fakes import FakeGh, RestGhRunner, index_from_entries

from scripts.upstream_watcher.batch import run_batch
from scripts.upstream_watcher.live import LiveGh

SUITE = "garrytan/gbrain"
PREFIX = "[upstream] garrytan/gbrain → "
INDEX = index_from_entries([])
ADDS = ["ask-user", "briefing"]


def finding(version, adds=ADDS, skill=SUITE):
    return {
        "finding_type": "update",
        "skillId": skill,
        "currentVersion": "v0",
        "newVersion": version,
        "releasedAt": "2026-10-21T10:00:00Z",
        "sourceUrl": f"https://github.com/{skill}/releases/tag/{version}",
        "mode": "components",
        "componentAdds": list(adds),
        "componentRemoves": [],
        "linkLiveness": [],
        "nameDrift": [],
    }


def run(gh, findings=None, apply=True):
    return run_batch(findings or [finding("v1")], gh, apply=apply, index_loader=lambda: INDEX)


def umbrella_numbers(gh, prefix=PREFIX):
    return sorted(number for number, row in gh.issues.items() if row["title"].startswith(prefix))


def close(gh, number, label="upstream:rejected", state_reason=None):
    if label:
        gh.edit_labels(number, add=[label])
    gh.issues[number]["state"] = "closed"
    if state_reason:
        gh.issues[number]["state_reason"] = state_reason


def test_day_one_creates_then_a_rejected_closed_umbrella_is_never_recreated_for_the_same_version():
    gh = FakeGh()
    report, code = run(gh)
    assert code == 0 and [w[0] for w in gh.writes] == ["create"]
    assert umbrella_numbers(gh) == [5000]
    close(gh, 5000)
    for day in range(2, 6):
        before = gh.write_count()
        report, code = run(gh)
        assert code == 0, report
        assert gh.write_count() == before, f"day {day} must write nothing for a version already closed"
        assert report["issuesCreated"] == 0
        assert report["suppressedClosedUmbrella"] == [
            {"suite": SUITE, "version": "v1", "umbrella": 5000, "closedAs": "rejected"}
        ]
    assert umbrella_numbers(gh) == [5000]


def test_a_closed_umbrella_without_a_label_is_suppressed_and_reported_as_closed_unresolved():
    gh = FakeGh()
    run(gh)
    close(gh, 5000, label=None)
    before = gh.write_count()
    report, code = run(gh)
    assert code == 0 and gh.write_count() == before
    assert report["suppressedClosedUmbrella"] == [
        {"suite": SUITE, "version": "v1", "umbrella": 5000, "closedAs": "closed-unresolved"}
    ]


def test_an_umbrella_closed_as_completed_by_the_approve_flow_is_suppressed_too():
    gh = FakeGh()
    run(gh)
    close(gh, 5000, label=None, state_reason="completed")
    before = gh.write_count()
    report, code = run(gh)
    assert code == 0 and gh.write_count() == before
    assert report["suppressedClosedUmbrella"][0]["closedAs"] == "completed"
    assert report["suppressedClosedUmbrella"][0]["umbrella"] == 5000


def test_a_new_version_creates_once_and_a_rerun_of_it_writes_nothing():
    gh = FakeGh()
    run(gh)
    close(gh, 5000)
    before = gh.write_count()
    report, code = run(gh, [finding("v2")])
    assert code == 0
    assert [w[0] for w in gh.writes[before:]] == ["create"]
    assert gh.writes[before][2] == PREFIX + "v2"
    assert report["issuesCreated"] == 1 and report["suppressedClosedUmbrella"] == []
    before = gh.write_count()
    report, code = run(gh, [finding("v2")])
    assert code == 0 and gh.write_count() == before


def test_a_closed_umbrella_for_another_suite_with_the_same_version_does_not_suppress():
    gh = FakeGh()
    run(gh, [finding("v1", skill="addyosmani/agent-skills")])
    close(gh, 5000)
    report, code = run(gh, [finding("v1")])
    assert code == 0
    assert [w[0] for w in gh.writes].count("create") == 2
    assert report["suppressedClosedUmbrella"] == []


def closed_umbrella_rows(count):
    return [
        {
            "number": 6000 + index,
            "title": f"[upstream] garrytan/gbrain → v0.{index}",
            "state": "closed",
            "labels": [{"name": "upstream:release"}],
            "body": "",
            "updated_at": "2026-01-01T00:00:00Z",
        }
        for index in range(count)
    ]


def test_a_failed_page_of_the_closed_umbrella_history_is_unknown_evidence_with_zero_writes():
    # A full first page forces the walk to request page 2. That request fails.
    runner = RestGhRunner(closed_umbrella_rows(100), fail_pages={("closed", "upstream:release", 2)})
    gh = LiveGh(repo="gaia-research/gaia-skill-tree", runner=runner)
    report, code = run_batch([finding("v1")], gh, apply=True, index_loader=lambda: INDEX)
    assert code == 3
    assert report["unknownEvidence"][0]["source"] == "github-list"
    assert runner.writes == [], "a failed closed-history read writes nothing"


def test_a_complete_closed_history_read_of_the_same_size_is_not_an_error():
    # Control for the test above: a full page followed by an empty page is a complete history.
    runner = RestGhRunner(closed_umbrella_rows(100))
    gh = LiveGh(repo="gaia-research/gaia-skill-tree", runner=runner)
    report, code = run_batch([finding("v1")], gh, apply=True, index_loader=lambda: INDEX)
    assert code == 0, report
    assert [w[0] for w in runner.writes] == ["create"]
    assert report["suppressedClosedUmbrella"] == []

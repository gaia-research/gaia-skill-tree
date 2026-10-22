"""#2131 round-5 H-A, superseded by the founder's canonical-issue correction (PR #2133).

Round 5 suppressed the create when the newest closed umbrella had the same suite and version, so a rejected
umbrella was never re-created. The founder reversed that: Steward owns closure, the watcher never reopens or edits a
closed issue, and when no OPEN canonical umbrella exists it creates a new one, even if closed ones exist for the same
suite. So a closed umbrella no longer blocks a create. The closed history is still read, because carry-forward keeps
the unresolved rows of the newest closed umbrella. A failed page of that history is unknown evidence: exit 3, zero
writes.
"""

from __future__ import annotations

import pytest

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


def test_a_closed_umbrella_never_blocks_a_new_open_one_for_the_same_version():
    gh = FakeGh()
    run(gh)
    close(gh, 5000)
    before = gh.write_count()

    report, code = run(gh)

    assert code == 0, report
    assert [w[0] for w in gh.writes[before:]] == ["create"]
    assert report["issuesCreated"] == 1
    assert umbrella_numbers(gh) == [5000, 5001]
    assert all(w[1] != 5000 for w in gh.writes[before:] if w[0] in ("edit", "labels", "comment")), \
        "the closed umbrella is never edited, commented on or relabelled"
    assert gh.issues[5000]["state"] == "closed"


def test_the_new_open_umbrella_is_then_left_alone_by_later_daily_runs():
    gh = FakeGh()
    run(gh)
    close(gh, 5000)
    run(gh)
    before = gh.write_count()
    for _day in range(3):
        report, code = run(gh)
        assert code == 0, report
    assert gh.write_count() == before, "findings unchanged against the open canonical issue: no writes"
    assert umbrella_numbers(gh) == [5000, 5001]


@pytest.mark.parametrize("label, state_reason", [
    (None, None),
    (None, "completed"),
])
def test_a_closed_umbrella_with_no_rejection_label_also_opens_a_new_one(label, state_reason):
    gh = FakeGh()
    run(gh)
    close(gh, 5000, label=label, state_reason=state_reason)

    run(gh)

    assert umbrella_numbers(gh) == [5000, 5001]
    assert gh.issues[5000]["state"] == "closed"


def test_a_new_version_creates_once_and_a_rerun_of_it_writes_nothing():
    gh = FakeGh()
    run(gh)
    close(gh, 5000)
    before = gh.write_count()
    report, code = run(gh, [finding("v2")])
    assert code == 0
    assert [w[0] for w in gh.writes[before:]] == ["create"]
    assert gh.writes[before][2] == PREFIX + "v2"
    assert report["issuesCreated"] == 1
    before = gh.write_count()
    report, code = run(gh, [finding("v2")])
    assert code == 0 and gh.write_count() == before


def test_a_closed_umbrella_for_another_suite_with_the_same_version_does_not_matter():
    gh = FakeGh()
    run(gh, [finding("v1", skill="addyosmani/agent-skills")])
    close(gh, 5000)
    report, code = run(gh, [finding("v1")])
    assert code == 0
    assert [w[0] for w in gh.writes].count("create") == 2


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

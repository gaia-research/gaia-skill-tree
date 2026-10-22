"""#2131 round-5 H-A, revised twice (PR #2133).

Round 5 suppressed a create whenever the newest closed umbrella had the same suite and version. The founder's
canonical-issue correction then let a closed umbrella stop blocking a new one, which re-created the same finding every
day when its rows were left unresolved. The hardening pass settles it with evidence: a closed umbrella's payload
records the finding it processed. The same finding (suite, version, candidate ids) that a closed umbrella records is
not re-created. A new version, or a new candidate, is a genuinely new finding and creates. A closed umbrella whose
payload cannot prove its finding is ambiguous: nothing is created and the run exits 3.

The closed history is read in full, because it is the evidence. A failed page of it is unknown evidence: exit 3, zero
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


def test_a_closed_umbrella_suppresses_recreation_of_the_same_finding():
    gh = FakeGh()
    run(gh)
    close(gh, 5000)
    before = gh.write_count()

    report, code = run(gh)

    assert code == 0, report
    assert gh.write_count() == before, "its payload records this finding: nothing is created"
    assert umbrella_numbers(gh) == [5000]
    assert report["suppressedProcessed"] == [{"suite": SUITE, "version": "v1", "closed": [5000]}]


def test_repeated_daily_scans_after_closure_write_nothing():
    gh = FakeGh()
    run(gh)
    close(gh, 5000)
    before = gh.write_count()
    for _day in range(5):
        report, code = run(gh)
        assert code == 0, report
    assert gh.write_count() == before
    assert umbrella_numbers(gh) == [5000]


@pytest.mark.parametrize("label, state_reason", [
    (None, None),
    (None, "completed"),
])
def test_a_closed_umbrella_with_no_rejection_label_is_still_processed_and_not_recreated(label, state_reason):
    gh = FakeGh()
    run(gh)
    close(gh, 5000, label=label, state_reason=state_reason)

    run(gh)

    assert umbrella_numbers(gh) == [5000]
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


def test_a_closed_history_of_one_full_page_is_refused_because_its_end_cannot_be_confirmed():
    # Exactly one full page: GitHub links an empty page after it, and a closed listing has no count to confirm the end.
    runner = RestGhRunner(closed_umbrella_rows(100))
    gh = LiveGh(repo="gaia-research/gaia-skill-tree", runner=runner)
    report, code = run_batch([finding("v1")], gh, apply=True, index_loader=lambda: INDEX)
    assert code == 3, report
    assert report["unknownEvidence"][0]["source"] == "github-list"
    assert runner.writes == [], "unknown closed history writes nothing"


def test_a_closed_history_with_a_partial_last_page_is_read_as_complete():
    runner = RestGhRunner(closed_umbrella_rows(99))
    gh = LiveGh(repo="gaia-research/gaia-skill-tree", runner=runner)
    report, code = run_batch([finding("v1")], gh, apply=True, index_loader=lambda: INDEX)
    assert code == 0, report
    assert [w[0] for w in runner.writes] == ["create"]
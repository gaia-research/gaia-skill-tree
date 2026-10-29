"""#2131 round-5 (C9): reruns of converged umbrellas write nothing, at the row counts the records design measured.

The first apply of a suite creates its umbrella (inline below the body budget, records mode above it). Any
rerun with unchanged input must write nothing. Covers 96 (inline), 250 and 600 (records mode) rows.
"""

from __future__ import annotations

import pytest
from upstream_fakes import FakeGh, index_from_entries

from scripts.upstream_watcher.batch import parse_payload, run_batch

SUITE = "garrytan/gbrain"
INDEX = index_from_entries([])


def finding(count, version="v1"):
    return {
        "finding_type": "update",
        "skillId": SUITE,
        "currentVersion": "v0",
        "newVersion": version,
        "releasedAt": "2026-10-21T00:00:00Z",
        "sourceUrl": f"https://github.com/{SUITE}/releases/tag/{version}",
        "mode": "components",
        "componentAdds": [f"skill-{number:03d}" for number in range(count)],
        "componentRemoves": [],
        "linkLiveness": [],
        "linkLivenessUnknown": [],
        "nameDrift": [],
    }


@pytest.mark.parametrize("count", [96, 250, 600])
def test_a_rerun_of_a_converged_umbrella_writes_nothing(count):
    gh = FakeGh()
    report, code = run_batch([finding(count)], gh, apply=True, index_loader=lambda: INDEX)
    assert code == 0, report
    assert report["issuesCreated"] == 1
    before = gh.write_count()

    for _rerun in range(2):
        report, code = run_batch([finding(count)], gh, apply=True, index_loader=lambda: INDEX)
        assert code == 0, report
        assert gh.write_count() == before, "a rerun with an unchanged payload writes nothing"
        assert report["suites"][0]["outcome"] == "noop"
    (umbrella,) = [row for row in gh.issues.values() if row["state"] == "open"]
    assert parse_payload(umbrella["body"]) is not None, "the umbrella keeps a readable payload"
    assert report["retainedCandidates"] == count

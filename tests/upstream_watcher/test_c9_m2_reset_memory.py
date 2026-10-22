"""#2131 round-5 verifier MEDIUM, M-2: --reset-records carries the closed umbrella's memory through the reset.

Before this change a reset discarded the umbrella's rows and started from the fresh poll alone, so a row that a
closed, rejected umbrella had settled (M3) came back as new work after the reset. The reset now also reads the
newest closed umbrella's rows, as carry-forward does, so a settled rejection survives it.
"""

from __future__ import annotations

import pytest

from scripts.upstream_watcher import batch as bt
from scripts.upstream_watcher.batch import parse_payload, run_batch
from upstream_fakes import FakeGh, index_from_entries

SUITE = "garrytan/gbrain"
INDEX = index_from_entries([])
SMALL = ["skill-000", "skill-001", "skill-002"]
BIG = [f"skill-{number:03d}" for number in range(250)]  # records mode: 5 chunks of 50


def finding(adds, version):
    return {
        "finding_type": "update",
        "skillId": SUITE,
        "currentVersion": "v0",
        "newVersion": version,
        "releasedAt": "2026-10-21T00:00:00Z",
        "sourceUrl": f"https://github.com/{SUITE}/releases/tag/{version}",
        "mode": "components",
        "componentAdds": list(adds),
        "componentRemoves": [],
        "linkLiveness": [],
        "linkLivenessUnknown": [],
        "nameDrift": [],
    }


def run(gh, item, reset=None):
    return run_batch([item], gh, apply=True, index_loader=lambda: INDEX, reset_records=reset)


def close_rejected(gh, number):
    gh.edit_labels(number, add=["upstream:rejected"])
    gh.issues[number]["state"] = "closed"


def delete_chunk(gh, number, index):
    target = next(
        row for row in gh.comments[number]
        if row["body"].startswith("<!-- gaia-upstream-record ") and f"chunk={index} of" in row["body"].split("\n", 1)[0]
    )
    gh.delete_comment(target["id"])


def row_of(gh, number, row_id):
    rows = bt.load_rows(gh, number, parse_payload(gh.issues[number]["body"]))
    return next(row for row in rows if row["id"] == row_id)


def test_a_reset_keeps_the_rejection_the_closed_umbrella_settled():
    gh = FakeGh()
    report, code = run(gh, finding(SMALL, "v1"))
    assert code == 0
    close_rejected(gh, 5000)

    report, code = run(gh, finding(BIG, "v2"))
    assert code == 0, report
    assert row_of(gh, 5001, f"{SUITE}:skill-000")["status"] == "rejected"

    delete_chunk(gh, 5001, 1)  # chunk 1 holds skill-000: the suite now fails closed
    report, code = run(gh, finding(BIG, "v2"))
    assert code == 3

    report, code = run(gh, finding(BIG, "v2"), reset=SUITE)
    assert code == 0, report
    assert row_of(gh, 5001, f"{SUITE}:skill-000")["status"] == "rejected", "the reset keeps the settled rejection"
    assert row_of(gh, 5001, f"{SUITE}:skill-003")["status"] == "new", "a row no closed umbrella saw stays new work"


def test_the_reset_records_the_rejection_source_so_the_row_stays_explained():
    gh = FakeGh()
    run(gh, finding(SMALL, "v1"))
    close_rejected(gh, 5000)
    run(gh, finding(BIG, "v2"))
    delete_chunk(gh, 5001, 1)
    run(gh, finding(BIG, "v2"), reset=SUITE)
    assert row_of(gh, 5001, f"{SUITE}:skill-000").get("rejectedBy") == "#5000"


def test_the_reset_still_fails_closed_when_the_closed_umbrella_cannot_be_read(monkeypatch):
    gh = FakeGh()
    run(gh, finding(SMALL, "v1"))
    close_rejected(gh, 5000)
    run(gh, finding(BIG, "v2"))
    delete_chunk(gh, 5001, 1)

    def unreadable(gh_, number, payload):
        raise bt.RecordError(f"record comments of #{number} could not be listed (fake)")

    monkeypatch.setattr(bt, "load_rows", unreadable)
    report, code = run(gh, finding(BIG, "v2"), reset=SUITE)
    assert code == 3, "an unreadable closed history is unknown evidence, so the reset does not guess"
    assert report["unknownEvidence"][0]["suite"] == SUITE


@pytest.mark.parametrize("reset", [None, "some/other-suite"])
def test_a_reset_for_another_suite_is_not_a_reset_of_this_one(reset):
    gh = FakeGh()
    run(gh, finding(SMALL, "v1"))
    close_rejected(gh, 5000)
    run(gh, finding(BIG, "v2"))
    delete_chunk(gh, 5001, 1)
    report, code = run(gh, finding(BIG, "v2"), reset=reset)
    assert code == 3

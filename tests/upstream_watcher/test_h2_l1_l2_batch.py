"""Regression tests for H2, L1 and L2 (#2131 verifier FAIL) in scripts/upstream_watcher/batch.py.

H2: an approved umbrella must lose upstream:approved BEFORE its body can change. If the
    reset cannot land, the body is left alone, so the next run still sees a payload change
    (non-noop) and tries the reset again. Approval never survives a payload change.
L1: a create that lands on an identical umbrella (created by a racing run) is a noop with
    zero writes. The old code edited the umbrella anyway.
L2: a transient head-check network error is not a broken link. It stays out of the hashed
    linkLiveness, and the previous state for that component is carried forward.
"""

from __future__ import annotations

import pytest

from scripts.upstream_watcher.batch import plan_suite, process_suite, run_batch, write_umbrella
from scripts.upstream_watcher.live import GhError, read_live
from upstream_fakes import FakeGh, index_from_entries

INDEX = index_from_entries([])
SUITE = "garrytan/gbrain"


def finding(version, adds=(), liveness=(), liveness_unknown=()):
    return {
        "finding_type": "update",
        "skillId": SUITE,
        "currentVersion": "v0",
        "newVersion": version,
        "releasedAt": "2026-10-21T00:00:00Z",
        "sourceUrl": f"https://github.com/garrytan/gbrain/releases/tag/{version}",
        "mode": "components",
        "componentAdds": list(adds),
        "componentRemoves": [],
        "linkLiveness": list(liveness),
        "linkLivenessUnknown": list(liveness_unknown),
        "nameDrift": [],
    }


def seed_umbrella(gh, version, adds=(), labels=("upstream:release", "upstream:approved"), liveness=()):
    """Create the umbrella the planner would have written for *version*, as a fixture."""
    plan = plan_suite(finding(version, adds, liveness), read_live(gh), INDEX)
    return gh.create_issue(plan["title"], list(labels), plan["body"])


class LabelFlakyGh(FakeGh):
    """A FakeGh whose label edits fail for the first *fail_label_times* calls."""

    def __init__(self, *args, fail_label_times=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.fail_label_times = fail_label_times
        self.label_attempts = 0

    def edit_labels(self, number, add=(), remove=()):
        self.label_attempts += 1
        if self.fail_label_times > 0:
            self.fail_label_times -= 1
            raise GhError("label edit failed (fake)")
        return super().edit_labels(number, add, remove)


def labels_of(gh, number):
    return {label["name"] for label in gh.issues[number]["labels"]}


# ---------------------------------------------------------------------------
# H2: reset the approval before the body changes
# ---------------------------------------------------------------------------


def test_failed_reset_leaves_the_body_untouched_and_the_next_run_is_not_noop():
    gh = LabelFlakyGh(fail_label_times=99)
    number = seed_umbrella(gh, "v1")
    original_body = gh.issues[number]["body"]
    new = finding("v2", adds=["ask-user"])

    plan = plan_suite(new, read_live(gh), INDEX)
    assert plan["reset"] is True  # approved umbrella, version changed

    with pytest.raises(GhError):
        write_umbrella(plan, gh)

    assert gh.issues[number]["body"] == original_body, "the body must not change when the reset did not land"
    assert not any(write[0] == "edit" for write in gh.writes), gh.writes
    rerun = plan_suite(new, read_live(gh), INDEX)
    assert rerun["action"] == "update", "a failed reset must keep the next run non-noop"
    assert "upstream:approved" in labels_of(gh, number)


def test_reset_label_lands_before_the_body_write_and_is_retried_once():
    gh = LabelFlakyGh(fail_label_times=1)
    number = seed_umbrella(gh, "v1")
    plan = plan_suite(finding("v2", adds=["ask-user"]), read_live(gh), INDEX)

    assert write_umbrella(plan, gh) == "updated"

    kinds = [write[0] for write in gh.writes]
    assert "labels" in kinds and "edit" in kinds
    assert kinds.index("labels") < kinds.index("edit"), gh.writes
    assert "upstream:approved" not in labels_of(gh, number)
    assert "upstream:needs-info" in labels_of(gh, number)
    assert gh.label_attempts == 2


def test_run_batch_reports_the_failed_reset_as_unknown_evidence_and_exits_3():
    gh = LabelFlakyGh(fail_label_times=99)
    number = seed_umbrella(gh, "v1")
    original_body = gh.issues[number]["body"]

    report, code = run_batch([finding("v2", adds=["ask-user"])], gh, apply=True, index_loader=lambda: INDEX)

    assert code == 3
    assert report["unknownEvidence"][0]["source"] == "github-write"
    assert gh.issues[number]["body"] == original_body


def test_unapproved_umbrella_update_writes_the_body_without_a_label_reset():
    gh = LabelFlakyGh(fail_label_times=99)
    number = seed_umbrella(gh, "v1", labels=("upstream:release",))
    plan = plan_suite(finding("v2", adds=["ask-user"]), read_live(gh), INDEX)
    assert plan["reset"] is False
    assert write_umbrella(plan, gh) == "updated"
    assert gh.label_attempts == 0
    assert gh.issues[number]["title"].endswith("v2")


# ---------------------------------------------------------------------------
# L1: a create that lands on an identical umbrella writes nothing
# ---------------------------------------------------------------------------


def test_create_race_onto_an_identical_umbrella_is_a_noop_with_zero_writes():
    gh = FakeGh()
    # A racing run created the identical umbrella after this run took its snapshot.
    seed_umbrella(gh, "v1", adds=["ask-user"], labels=("upstream:release", "needs-triage"))
    stale_live = {"issues": [], "closedUmbrellas": []}
    writes_before = len(gh.writes)

    row, _live = process_suite(finding("v1", adds=["ask-user"]), gh, INDEX, stale_live, apply=True)

    assert row["outcome"] == "noop", row
    assert gh.writes[writes_before:] == [], gh.writes[writes_before:]


# ---------------------------------------------------------------------------
# L2: transient network errors do not enter the payload hash
# ---------------------------------------------------------------------------


def test_unknown_link_without_a_previous_state_is_omitted_not_recorded_as_broken():
    plan = plan_suite(finding("v1", liveness_unknown=["mattpocock/caveman"]), {"issues": [], "closedUmbrellas": []}, INDEX)
    assert plan["payload"]["linkLiveness"] == []
    assert all(row["status"] != "network_error" for row in plan["payload"]["linkLiveness"])


def test_unknown_link_carries_the_previous_state_and_leaves_the_hash_unchanged():
    gh = FakeGh()
    previous = {"skillId": "mattpocock/caveman", "url": "u", "rawUrl": "r", "status": 404}
    seed_umbrella(gh, "v1", liveness=[previous])
    rerun = plan_suite(finding("v1", liveness_unknown=["mattpocock/caveman"]), read_live(gh), INDEX)
    assert rerun["payload"]["linkLiveness"] == [previous]
    assert rerun["action"] == "noop", "a transient network error must not churn the umbrella"


def test_definitive_status_changes_are_still_recorded():
    gh = FakeGh()
    seed_umbrella(gh, "v1")
    fresh = {"skillId": "mattpocock/caveman", "url": "u", "rawUrl": "r", "status": 410}
    plan = plan_suite(finding("v1", liveness=[fresh]), read_live(gh), INDEX)
    assert plan["payload"]["linkLiveness"] == [fresh]
    assert plan["action"] == "update"

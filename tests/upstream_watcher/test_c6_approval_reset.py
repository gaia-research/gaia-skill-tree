"""#2131 round-2 regression tests: H1 (approval reset on any hashed-payload change) and L3 (the
reviewer note is posted once per payload, even across retries).

H1 ruling: while an umbrella carries upstream:approved, ANY change to its hashed payload resets the
    approval (label removed, upstream:needs-info added, one reviewer note) before the body changes.
    Only a change outside the payload hash (a timestamp or other metadata) is exempt.
L3: the reviewer note carries a marker per payload hash, so a retried reset does not repeat it.
"""

from __future__ import annotations

import pytest

from scripts.upstream_watcher import batch
from scripts.upstream_watcher.batch import escalate_candidate, parse_payload, run_batch
from scripts.upstream_watcher.live import GhError
from upstream_fakes import FakeGh, index_from_entries

SUITE = "garrytan/gbrain"
PREFIX = "[upstream] garrytan/gbrain → "
EMPTY_INDEX = index_from_entries([])


def finding(version="v1", adds=("ask-user", "briefing"), **overrides):
    base = {
        "finding_type": "update",
        "skillId": SUITE,
        "currentVersion": "v0",
        "newVersion": version,
        "releasedAt": "2026-10-21T00:00:00Z",
        "sourceUrl": f"https://github.com/garrytan/gbrain/releases/tag/{version}",
        "mode": "components",
        "componentAdds": list(adds),
        "componentRemoves": [],
        "linkLiveness": [],
        "linkLivenessUnknown": [],
        "nameDrift": [],
    }
    base.update(overrides)
    return base


def run(gh, findings, index=None):
    index = index if index is not None else EMPTY_INDEX
    return run_batch(findings, gh, apply=True, index_loader=lambda: index)


def umbrella_number(gh):
    (number,) = [n for n, row in gh.issues.items() if row["title"].startswith(PREFIX) and row["state"] == "open"]
    return number


def labels_of(gh, number):
    return {label["name"] for label in gh.issues[number]["labels"]}


def approve(gh, number):
    FakeGh.edit_labels(gh, number, add=["upstream:approved"])


def reset_notes(gh, number):
    return [row["body"] for row in gh.comments.get(number, []) if "Approval reset" in row["body"]]


def approved_v1(**overrides):
    gh = FakeGh()
    run(gh, [finding("v1", **overrides)])
    number = umbrella_number(gh)
    approve(gh, number)
    return gh, number


def assert_reset(gh, number, field):
    assert "upstream:approved" not in labels_of(gh, number), "approval must not survive a payload change"
    assert "upstream:needs-info" in labels_of(gh, number)
    notes = reset_notes(gh, number)
    assert len(notes) == 1, notes
    assert field in notes[0], notes[0]


# ---------------------------------------------------------------------------
# H1: every hashed-payload change resets the approval
# ---------------------------------------------------------------------------


def test_a_changed_link_liveness_resets_an_approved_umbrella_at_the_same_version():
    gh, number = approved_v1()
    broken = [{"skillId": "garrytan/ask-user", "url": "https://x", "rawUrl": "https://x", "status": 404}]

    report, code = run(gh, [finding("v1", linkLiveness=broken)])

    assert code == 0
    assert parse_payload(gh.issues[number]["body"])["linkLiveness"] == broken
    assert_reset(gh, number, "linkLiveness")


def test_a_changed_component_removal_resets_an_approved_umbrella_at_the_same_version():
    gh, number = approved_v1()

    report, code = run(gh, [finding("v1", componentRemoves=["old-one"])])

    assert code == 0
    assert_reset(gh, number, "componentRemoves")


def test_a_changed_name_drift_resets_an_approved_umbrella_at_the_same_version():
    gh, number = approved_v1()
    drift = [{"skillId": "garrytan/ask-user", "registrySlug": "ask-user", "sanitizedName": "ask-users",
              "fixCommand": "gaia dev rename"}]

    report, code = run(gh, [finding("v1", nameDrift=drift)])

    assert code == 0
    assert_reset(gh, number, "nameDrift")


def test_a_row_whose_status_changes_resets_an_approved_umbrella_at_the_same_version():
    gh, number = approved_v1()
    present = index_from_entries([{
        "id": "garrytan/ask-user",
        "github": "https://github.com/garrytan/gbrain/blob/main/skills/ask-user/SKILL.md",
    }])
    assert {row["id"]: row["status"] for row in parse_payload(gh.issues[number]["body"])["candidates"]}[
        "garrytan/gbrain:ask-user"
    ] == "new"

    report, code = run(gh, [finding("v1")], index=present)

    assert code == 0
    statuses = {row["id"]: row["status"] for row in parse_payload(gh.issues[number]["body"])["candidates"]}
    assert statuses["garrytan/gbrain:ask-user"] == "present"
    assert_reset(gh, number, "candidates")


def test_a_timestamp_only_change_keeps_the_approval_and_writes_nothing():
    gh, number = approved_v1()
    gh.issues[number]["updated_at"] = "2099-01-01T00:00:00Z"
    before = gh.write_count()

    report, code = run(gh, [finding("v1")])

    assert code == 0
    assert gh.write_count() == before
    assert "upstream:approved" in labels_of(gh, number)
    assert reset_notes(gh, number) == []


def legacy_approved(**approved_fields):
    """An approved legacy (pre-v2) umbrella whose v1 fields are *approved_fields* over the v1 defaults."""
    import json

    legacy = {"skillId": SUITE, "previousVersion": "v0", "newVersion": "v1",
              "releasedAt": "2026-10-21T00:00:00Z",
              "sourceUrl": "https://github.com/garrytan/gbrain/releases/tag/v1",
              "mode": "components", "componentAdds": ["ask-user", "briefing"]}
    legacy.update(approved_fields)
    body = "## legacy\n\n<!-- gaia-upstream-payload\n" + json.dumps(legacy, indent=2) + "\n-->\n"
    return FakeGh([{"number": 77, "title": PREFIX + "v1", "state": "open",
                    "labels": [{"name": "upstream:release"}, {"name": "upstream:approved"}], "body": body}])


def test_converting_a_legacy_approved_umbrella_keeps_the_approval_when_every_approved_field_is_unchanged():
    # The live approved umbrellas are legacy payloads. Converting one to v2 changes its representation,
    # not the approved content, so the approval survives (and the components are not counted as new).
    gh = legacy_approved()

    report, code = run(gh, [finding("v1")])

    assert code == 0
    assert "upstream:approved" in {label["name"] for label in gh.issues[77]["labels"]}
    assert reset_notes(gh, 77) == []
    assert len(parse_payload(gh.issues[77]["body"])["candidates"]) == 2


def test_converting_a_legacy_approved_umbrella_resets_it_when_an_approved_field_changed():
    gh = legacy_approved()

    report, code = run(gh, [finding("v1", componentRemoves=["old-one"])])

    assert code == 0
    assert_reset(gh, 77, "componentRemoves")


def test_escalating_a_row_of_an_approved_umbrella_resets_its_approval():
    gh, number = approved_v1()

    result, code = escalate_candidate("garrytan/gbrain:ask-user", gh, apply=True)

    assert code == 0 and result["outcome"] == "created"
    assert_reset(gh, number, "candidates")


def test_an_unapproved_umbrella_changes_without_a_reset_or_note():
    gh = FakeGh()
    run(gh, [finding("v1")])
    number = umbrella_number(gh)
    run(gh, [finding("v1", componentRemoves=["old-one"])])

    assert "upstream:needs-info" not in labels_of(gh, number)
    assert reset_notes(gh, number) == []


# ---------------------------------------------------------------------------
# L3: one reviewer note per payload, across retries
# ---------------------------------------------------------------------------


class LabelFlakyGh(FakeGh):
    """A FakeGh whose label edits fail for the first *fail_label_times* calls."""

    def __init__(self, *args, fail_label_times=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.fail_label_times = fail_label_times

    def edit_labels(self, number, add=(), remove=()):
        if self.fail_label_times > 0:
            self.fail_label_times -= 1
            raise GhError("label edit failed (fake)")
        return super().edit_labels(number, add, remove)


def test_a_retried_reset_posts_its_reviewer_note_once():
    gh = LabelFlakyGh()
    run(gh, [finding("v1")])
    number = umbrella_number(gh)
    approve(gh, number)
    gh.fail_label_times = 3  # every attempt of the first run fails: the reset cannot land

    _report, first = run(gh, [finding("v2")])
    assert first == 3
    assert gh.issues[number]["title"] == PREFIX + "v1", "the body must not change while the reset is pending"

    gh.fail_label_times = 0
    report, second = run(gh, [finding("v2")])

    assert second == 0
    assert "upstream:approved" not in labels_of(gh, number)
    assert "upstream:needs-info" in labels_of(gh, number)
    assert len(reset_notes(gh, number)) == 1, reset_notes(gh, number)


def test_the_reset_note_names_the_approved_and_new_versions_and_the_changed_fields():
    gh = FakeGh()
    run(gh, [finding("v1")])
    number = umbrella_number(gh)
    approve(gh, number)

    run(gh, [finding("v2")])

    (note,) = reset_notes(gh, number)
    assert "`v1`" in note and "`v2`" in note
    assert "Re-apply `upstream:approved`" in note
    assert batch.reset_marker(parse_payload(gh.issues[number]["body"])["payloadSha256"]) in note

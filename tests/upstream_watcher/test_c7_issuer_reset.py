"""#2131 round-3 verifier FAIL, D8 and D10 (issuer side).

D8: a bootstrap reset decides whether upstream:approved is on the issue from the run-start snapshot. An
approval applied after the snapshot survived a version move. The reset now reads the live labels at reset
time, and a failed read stops the run before the body is written (fail closed).

D10: the fanout (legacy, --child-mode fanout) update path must reset an approved umbrella whose payload
changed, the same way the batch path does (H1). The reset note goes first, then the labels, then the body.
"""

from __future__ import annotations

import subprocess

import pytest

from scripts.upstream_watcher import issuer, live
from scripts.upstream_watcher.issuer import UmbrellaWriteError, create_issues
from scripts.upstream_watcher.live import GhError
from upstream_fakes import RestGhRunner

SUITE = "firecrawl/firecrawl-skills"
BOOT_OLD = f"[upstream:bootstrap] {SUITE} → baseline at v2.10.0"
BOOTSTRAP = {
    "finding_type": "bootstrap",
    "skillId": SUITE,
    "newVersion": "v2.11.0",
    "releasedAt": "2026-10-21T00:00:00Z",
    "sourceUrl": "https://github.com/firecrawl/firecrawl/releases/tag/v2.11.0",
    "mode": "bootstrap",
    "componentAdds": [],
    "componentRemoves": [],
    "linkLiveness": [],
    "nameDrift": [],
}

GBRAIN = "garrytan/gbrain"


def row(number, title, state, labels, body=""):
    return {
        "number": number, "title": title, "state": state, "body": body, "updated_at": "2026-10-21T12:00:00Z",
        "labels": [{"name": name} for name in labels],
    }


def world_for(monkeypatch, issues):
    world = RestGhRunner(issues)
    monkeypatch.setattr(subprocess, "run", world)
    return world


def label_edits(world):
    return [call for call in world.calls if call[1:3] == ["issue", "edit"]]


# ---------------------------------------------------------------------------
# D8: the bootstrap reset reads the live labels.
# ---------------------------------------------------------------------------


def test_a_bootstrap_approved_after_the_run_snapshot_still_loses_its_approval_on_a_version_move(monkeypatch):
    world = world_for(monkeypatch, [row(1755, BOOT_OLD, "open", ["upstream:bootstrap", "upstream:approved"])])
    real_snapshot = issuer._open_snapshot

    def stale_snapshot(labels=issuer.IDEMPOTENCY_LABELS):
        snapshot = real_snapshot(labels)
        for issue in snapshot.get("upstream:bootstrap", []):
            issue["labels"] = [label for label in issue["labels"] if label["name"] != "upstream:approved"]
        return snapshot

    monkeypatch.setattr(issuer, "_open_snapshot", stale_snapshot)

    create_issues([BOOTSTRAP], apply=True)

    edits = label_edits(world)
    assert len(edits) == 1, world.calls
    assert "--remove-label" in edits[0] and edits[0][edits[0].index("--remove-label") + 1] == "upstream:approved"
    assert "--add-label" in edits[0] and edits[0][edits[0].index("--add-label") + 1] == "upstream:needs-info"


def test_a_bootstrap_without_approval_is_moved_without_any_label_change(monkeypatch):
    world = world_for(monkeypatch, [row(1755, BOOT_OLD, "open", ["upstream:bootstrap"])])

    create_issues([BOOTSTRAP], apply=True)

    edits = label_edits(world)
    assert len(edits) == 1 and "--remove-label" not in edits[0] and "--add-label" not in edits[0]


def test_a_failed_live_label_read_stops_the_bootstrap_update_with_no_write(monkeypatch):
    world = world_for(monkeypatch, [row(1755, BOOT_OLD, "open", ["upstream:bootstrap", "upstream:approved"])])

    def unreadable(self, number):
        raise GhError(f"could not read #{number} (fake)")

    monkeypatch.setattr(live.LiveGh, "get_issue", unreadable)

    with pytest.raises(UmbrellaWriteError):
        create_issues([BOOTSTRAP], apply=True)
    assert label_edits(world) == []


# ---------------------------------------------------------------------------
# D10: the fanout update path resets an approved umbrella whose payload changed.
# ---------------------------------------------------------------------------


def fanout_finding(version, removes=()):
    return {
        "finding_type": "update",
        "skillId": GBRAIN,
        "currentVersion": "v0",
        "newVersion": version,
        "releasedAt": "2026-10-21T00:00:00Z",
        "sourceUrl": f"https://github.com/garrytan/gbrain/releases/tag/{version}",
        "mode": "components",
        "componentAdds": [],
        "componentRemoves": list(removes),
        "linkLiveness": [],
        "nameDrift": [],
    }


def existing_umbrella(labels):
    body = issuer.render_umbrella_body(fanout_finding("v1"), "components", [], [], [], [])
    return row(5000, "[upstream] garrytan/gbrain → v1", "open", ["upstream:release", *labels], body=body)


def comment_bodies(world):
    return world.comment_texts


def test_a_fanout_update_of_an_approved_umbrella_resets_its_approval_before_the_body_changes(monkeypatch):
    world = world_for(monkeypatch, [existing_umbrella(["upstream:approved"])])

    create_issues([fanout_finding("v2", removes=["ghost-skill"])], apply=True)

    reset_notes = [text for text in comment_bodies(world) if "Approval reset" in text]
    assert len(reset_notes) == 1 and "componentRemoves" in reset_notes[0]
    edits = label_edits(world)
    assert edits, world.calls
    first_label_edit = edits[0]
    assert "--remove-label" in first_label_edit and "upstream:approved" in first_label_edit
    assert "--body-file" not in first_label_edit, "the label reset runs before the body write"
    body_edits = [call for call in world.calls if call[1:3] == ["issue", "edit"] and "--body-file" in call]
    assert body_edits and world.calls.index(first_label_edit) < world.calls.index(body_edits[0])


def test_a_fanout_update_of_an_unapproved_umbrella_writes_no_reset_note(monkeypatch):
    world = world_for(monkeypatch, [existing_umbrella([])])

    create_issues([fanout_finding("v2")], apply=True)

    assert not [text for text in comment_bodies(world) if "Approval reset" in text]
    assert not [call for call in label_edits(world) if "--remove-label" in call]


def test_a_fanout_reset_note_already_posted_by_the_watcher_is_not_posted_again(monkeypatch):
    umbrella = existing_umbrella(["upstream:approved"])
    world = world_for(monkeypatch, [umbrella])
    finding = fanout_finding("v2", removes=["ghost-skill"])
    from scripts.upstream_watcher.approval import canonical_hash, reset_marker

    payload_hash = canonical_hash(issuer.fanout_payload(finding, "components", [], ["ghost-skill"], [], []))
    world.comments[5000] = [{
        "id": 1, "body": reset_marker(payload_hash),
        "user": {"login": "github-actions[bot]", "type": "Bot"},
    }]

    create_issues([finding], apply=True)

    assert not [text for text in comment_bodies(world) if "Approval reset" in text]

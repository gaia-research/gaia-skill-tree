"""#2131 round-3 verifier FAIL, D1 and D9 (watcher side).

D1: approval used to be keyed on the STORED payloadSha256. A body edit (componentRemoves, newVersion)
that left the stored digest alone kept the approval, and the sync then used the edited payload. The
watcher now recomputes the digest of the body payload on every read. A mismatch is a tampered payload:
the approval is reset with one reviewer note and the body is repaired from the fresh plan.

D9: the reset-note suppression counts only comments the watcher wrote. A human quoting the marker
must not stop the note from being posted.
"""

from __future__ import annotations

import re

import pytest

from scripts.upstream_watcher import batch
from scripts.upstream_watcher.batch import (
    PAYLOAD_RE,
    canonical_hash,
    payload_block,
    parse_payload,
    reset_marker,
    run_batch,
)
from upstream_fakes import FakeGh, index_from_entries

INDEX = index_from_entries([])
BOT = "github-actions[bot]"
UMBRELLA_PREFIX = "[upstream] garrytan/gbrain → "


def finding(version="v1", adds=("ask-user",), removes=()):
    return {
        "finding_type": "update",
        "skillId": "garrytan/gbrain",
        "currentVersion": "v0",
        "newVersion": version,
        "releasedAt": "2026-10-21T00:00:00Z",
        "sourceUrl": f"https://github.com/garrytan/gbrain/releases/tag/{version}",
        "mode": "components",
        "componentAdds": list(adds),
        "componentRemoves": list(removes),
        "linkLiveness": [],
        "linkLivenessUnknown": [],
        "nameDrift": [],
    }


def run(gh, fnd):
    return run_batch([fnd], gh, apply=True, index_loader=lambda: INDEX)


def approved_umbrella(gh):
    run(gh, finding())
    (number,) = [n for n, row in gh.issues.items() if row["title"].startswith(UMBRELLA_PREFIX)]
    gh.edit_labels(number, add=["upstream:approved"])
    return number


def body_of(gh, number):
    return gh.issues[number]["body"]


def labels_of(gh, number):
    return {label["name"] for label in gh.issues[number]["labels"]}


def tamper(gh, number, mutate):
    """Edit the body payload in place, keeping whatever payloadSha256 the body already stores."""
    payload = parse_payload(body_of(gh, number))
    mutate(payload)
    body = PAYLOAD_RE.sub(lambda _match: payload_block(payload), body_of(gh, number), count=1)
    gh.issues[number]["body"] = body


def reset_notes(gh, number):
    return [row["body"] for row in gh.comments.get(number, []) if "Approval reset" in row["body"]]


def test_control_an_unedited_approved_umbrella_keeps_its_approval_and_writes_nothing():
    gh = FakeGh()
    number = approved_umbrella(gh)
    before = gh.write_count()
    report, code = run(gh, finding())
    assert code == 0
    assert report["suites"][0]["outcome"] == "noop"
    assert gh.write_count() == before
    assert "upstream:approved" in labels_of(gh, number)
    assert reset_notes(gh, number) == []


def test_componentRemoves_edit_with_a_stale_stored_digest_resets_approval_and_repairs_the_body():
    gh = FakeGh()
    number = approved_umbrella(gh)
    stored = parse_payload(body_of(gh, number))["payloadSha256"]
    tamper(gh, number, lambda payload: payload.update(componentRemoves=["ghost-skill"]))
    assert parse_payload(body_of(gh, number))["payloadSha256"] == stored, "the repro keeps the stored digest"

    report, code = run(gh, finding())

    assert code == 0
    assert "upstream:approved" not in labels_of(gh, number)
    assert "upstream:needs-info" in labels_of(gh, number)
    notes = reset_notes(gh, number)
    assert len(notes) == 1 and "componentRemoves" in notes[0]
    repaired = parse_payload(body_of(gh, number))
    assert repaired["componentRemoves"] == []
    assert repaired["payloadSha256"] == canonical_hash(repaired)
    assert report["suites"][0]["outcome"] == "updated"


def test_newVersion_edit_with_a_stale_stored_digest_resets_approval_and_repairs_the_body():
    gh = FakeGh()
    number = approved_umbrella(gh)
    stored = parse_payload(body_of(gh, number))["payloadSha256"]
    tamper(gh, number, lambda payload: payload.update(newVersion="v9-forged"))
    assert parse_payload(body_of(gh, number))["payloadSha256"] == stored

    run(gh, finding())

    assert "upstream:approved" not in labels_of(gh, number)
    assert "upstream:needs-info" in labels_of(gh, number)
    notes = reset_notes(gh, number)
    assert len(notes) == 1 and "newVersion" in notes[0]
    repaired = parse_payload(body_of(gh, number))
    assert repaired["newVersion"] == "v1"
    assert repaired["payloadSha256"] == canonical_hash(repaired)


def test_a_rewritten_stored_digest_alone_is_detected_and_resets_approval():
    gh = FakeGh()
    number = approved_umbrella(gh)
    tamper(gh, number, lambda payload: payload.update(payloadSha256="0" * 64))

    run(gh, finding())

    assert "upstream:approved" not in labels_of(gh, number)
    notes = reset_notes(gh, number)
    assert len(notes) == 1 and "payloadSha256" in notes[0]
    repaired = parse_payload(body_of(gh, number))
    assert repaired["payloadSha256"] == canonical_hash(repaired)


def test_a_tampered_unapproved_umbrella_is_repaired_without_a_reset_note():
    gh = FakeGh()
    run(gh, finding())
    (number,) = [n for n, row in gh.issues.items() if row["title"].startswith(UMBRELLA_PREFIX)]
    tamper(gh, number, lambda payload: payload.update(componentRemoves=["ghost-skill"]))

    report, code = run(gh, finding())

    assert code == 0
    assert report["suites"][0]["outcome"] == "updated"
    assert reset_notes(gh, number) == []
    assert parse_payload(body_of(gh, number))["componentRemoves"] == []


def test_a_tampered_child_link_is_dropped_so_the_row_stays_unresolved():
    gh = FakeGh()
    number = approved_umbrella(gh)
    gh.add({"number": 7001, "title": "[intake] garrytan/ask-user", "state": "closed",
            "labels": [{"name": "upstream:child"}], "body": "Umbrella: #%d." % number})

    def link_closed_child(payload):
        for row in payload["candidates"]:
            row["child"] = 7001
            row["status"] = "escalated"

    tamper(gh, number, link_closed_child)
    run(gh, finding())

    repaired = parse_payload(body_of(gh, number))
    row = next(row for row in repaired["candidates"] if row["slug"] == "ask-user")
    assert row["child"] is None, "a forged child link must not count as a resolved row"
    assert row["status"] != "escalated"


def test_a_human_comment_quoting_the_reset_marker_does_not_suppress_the_reset_note():
    gh = FakeGh()
    number = approved_umbrella(gh)
    current_hash = parse_payload(body_of(gh, number))["payloadSha256"]
    gh.next_comment_id += 1
    gh.comments.setdefault(number, []).append({
        "id": gh.next_comment_id,
        "body": f"Please ignore. {reset_marker(current_hash)}",
        "user": {"login": "mallory", "type": "User"},
    })
    tamper(gh, number, lambda payload: payload.update(componentRemoves=["ghost-skill"]))

    run(gh, finding())

    bot_notes = [row for row in gh.comments[number] if "Approval reset" in row["body"]
                 and row["user"]["login"] == BOT]
    assert len(bot_notes) == 1, "the watcher must still post its one reviewer note"


def test_a_retried_reset_for_the_same_payload_posts_its_note_only_once():
    gh = FakeGh()
    number = approved_umbrella(gh)
    tamper(gh, number, lambda payload: payload.update(componentRemoves=["ghost-skill"]))
    run(gh, finding())
    # The reset retried after its labels failed: the note must not be posted again.
    gh.edit_labels(number, add=["upstream:approved"], remove=["upstream:needs-info"])
    tamper(gh, number, lambda payload: payload.update(componentRemoves=["ghost-skill"]))

    run(gh, finding())

    bot_notes = [row for row in gh.comments[number] if "Approval reset" in row["body"]
                 and row["user"]["login"] == BOT]
    assert len(bot_notes) == 1

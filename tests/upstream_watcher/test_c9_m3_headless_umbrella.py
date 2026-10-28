"""#2131 round-5 verifier MEDIUM, M-3: an open umbrella whose payload block is missing or unparseable is tampered.

Before this change a headless body was planned as if it were new: its stored digest was not checked, and it was
not flagged, so the note never said the body had been changed. The planner now treats it as tampered. The body
is repaired from the plan, an approval is reset (one reviewer note, then the labels), and every escalated child
is re-adopted through the live list lookup. No duplicate child is created, and --escalate on the same row adopts
the child that is already open.
"""

from __future__ import annotations

import pytest
from upstream_fakes import FakeGh, index_from_entries

from scripts.upstream_watcher import batch as bt
from scripts.upstream_watcher.batch import (
    canonical_hash,
    escalate_candidate,
    parse_payload,
    plan_suite,
    run_batch,
)
from scripts.upstream_watcher.live import read_live
from scripts.upstream_watcher.markers import PAYLOAD_RE

SUITE = "garrytan/gbrain"
INDEX = index_from_entries([])
ROW = f"{SUITE}:ask-user"


def finding(version="v1"):
    return {
        "finding_type": "update",
        "skillId": SUITE,
        "currentVersion": "v0",
        "newVersion": version,
        "releasedAt": "2026-10-21T10:00:00Z",
        "sourceUrl": f"https://github.com/{SUITE}/releases/tag/{version}",
        "mode": "components",
        "componentAdds": ["ask-user", "briefing"],
        "componentRemoves": [],
        "linkLiveness": [],
        "nameDrift": [],
    }


def open_child(number, slug):
    return {
        "number": number, "title": f"[intake] garrytan/{slug}", "state": "open",
        "labels": [{"name": "intake"}, {"name": "upstream:child"}],
        "body": (
            f"> Auto-populated by upstream watcher. Umbrella: #5000.\n\n"
            f"**Suggested ID:** `garrytan/{slug}`\n\n### Evidence\n\n"
            f"- **url:** https://github.com/garrytan/gbrain/blob/main/skills/{slug}/SKILL.md\n"
        ),
    }


def run(gh):
    return run_batch([finding()], gh, apply=True, index_loader=lambda: INDEX)


def damage(body, how):
    if how == "missing":
        return PAYLOAD_RE.sub("", body)
    if how == "unparseable":
        return PAYLOAD_RE.sub(lambda match: "<!-- gaia-upstream-payload\n{ not json\n-->", body)
    return bt.PLACEHOLDER_BODY  # a create that stopped before the body was written


def creates(gh):
    return [write for write in gh.writes if write[0] == "create"]


def intake_creates(gh):
    return [write for write in creates(gh) if "[intake]" in write[2]]


@pytest.mark.parametrize("how", ["missing", "unparseable", "placeholder"])
@pytest.mark.parametrize("approved", [True, False])
def test_a_headless_open_umbrella_is_tampered_repaired_reset_and_keeps_its_child(how, approved):
    gh = FakeGh([open_child(40, "ask-user")])
    report, code = run(gh)
    assert code == 0 and parse_payload(gh.issues[5000]["body"])["candidates"][0]["child"] == 40
    if approved:
        gh.edit_labels(5000, add=["upstream:approved"])
    gh.issues[5000]["body"] = damage(gh.issues[5000]["body"], how)
    creates_before = len(creates(gh))

    plan = plan_suite(finding(), read_live(gh), INDEX, probe=gh.child_state, gh=gh)
    assert plan["tampered"] is True, "a headless body is treated as tampered"
    assert plan["reset"] is approved

    report, code = run(gh)
    assert code == 0, report
    assert len(creates(gh)) == creates_before, "the umbrella is repaired in place, not recreated"
    assert intake_creates(gh) == [], "a re-adopted child is never duplicated"

    payload = parse_payload(gh.issues[5000]["body"])
    assert payload is not None and payload["payloadSha256"] == canonical_hash(payload)
    row = next(candidate for candidate in payload["candidates"] if candidate["id"] == ROW)
    assert row["child"] == 40 and row["status"] == "tracked"

    labels = {label["name"] for label in gh.issues[5000]["labels"]}
    if approved:
        assert "upstream:approved" not in labels and "upstream:needs-info" in labels
        assert any("Approval reset" in note["body"] for note in gh.comments[5000])
    else:
        assert "upstream:approved" not in labels and "upstream:needs-info" not in labels


def test_escalating_the_same_row_after_the_repair_adopts_the_open_child():
    gh = FakeGh([open_child(40, "ask-user")])
    run(gh)
    gh.issues[5000]["body"] = damage(gh.issues[5000]["body"], "missing")
    run(gh)
    before = len(intake_creates(gh))

    result, code = escalate_candidate(ROW, gh, apply=True)
    assert code == 0
    assert result["outcome"] == "already-child" and result["child"] == 40
    assert len(intake_creates(gh)) == before, "no duplicate child for an escalated row"

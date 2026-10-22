"""#2131 round-4 verifier FAIL, M3 and M6: rejection and closure never silently drop a candidate row.

M3. A closed umbrella that carries upstream:rejected settles its childless rows. Each such row becomes
    status 'rejected': suppressed in later umbrellas, kept in the record, and escalated only by an explicit
    human action. It must not reappear as new work, and that memory survives an umbrella closed later as
    completed.
M6. A closed child without upstream:rejected does NOT resolve its row. The row stays unresolved with the note
    'child closed without a disposition', unless the child is closed AND the candidate is curated in the
    registry. A child closed with upstream:rejected is a disposition and resolves its row.
"""

from __future__ import annotations

import json

from scripts.upstream_watcher import batch
from scripts.upstream_watcher.batch import (
    NOTE_CLOSED_WITHOUT_DISPOSITION,
    carry_forward,
    child_state_lookup,
    escalate_candidate,
    layout,
    parse_payload,
    plan_suite,
    row_is_unresolved,
    run_batch,
    unresolved_row_ids,
)
from scripts.upstream_watcher.live import read_live
from upstream_fakes import FakeGh, index_from_entries

GBRAIN = "garrytan/gbrain"
PREFIX = "[upstream] garrytan/gbrain → "
SOURCE = "https://github.com/garrytan/gbrain/releases/tag/{v}"
EMPTY_INDEX = index_from_entries([])


def finding(version, adds):
    return {
        "finding_type": "update",
        "skillId": GBRAIN,
        "currentVersion": "v0",
        "newVersion": version,
        "releasedAt": "2026-10-21T00:00:00Z",
        "sourceUrl": SOURCE.format(v=version),
        "mode": "components",
        "componentAdds": list(adds),
        "componentRemoves": [],
        "linkLiveness": [],
        "linkLivenessUnknown": [],
        "nameDrift": [],
    }


def row(slug, status, child=None, registry="absent"):
    return {
        "id": f"{GBRAIN}:{slug}", "slug": slug, "suggestedId": f"garrytan/{slug}",
        "evidenceUrl": f"https://github.com/garrytan/gbrain/blob/main/skills/{slug}/SKILL.md",
        "firstSeenVersion": "v1", "lastSeenVersion": "v1", "status": status, "child": child,
        "precheck": {"registry": registry, "tracked": "none", "priorDisposition": "none"},
    }


def closed_umbrella(gh, number, version, rows, labels):
    payload = {
        "payloadVersion": 2, "skillId": GBRAIN, "previousVersion": "v0", "newVersion": version,
        "releasedAt": "2026-10-21T00:00:00Z", "sourceUrl": SOURCE.format(v=version), "mode": "components",
        "componentAdds": [r["slug"] for r in rows], "componentRemoves": [], "linkLiveness": [], "nameDrift": [],
        "candidates": rows,
    }
    from scripts.upstream_watcher.approval import canonical_hash
    payload["payloadSha256"] = canonical_hash(payload)
    body = batch.payload_block(payload) + "\n\n### Version\n"
    gh.add({
        "number": number, "title": f"{PREFIX}{version}", "state": "closed",
        "labels": [{"name": name} for name in ("upstream:release", *labels)], "body": body,
    })
    return number


def child(gh, number, slug, state, labels=("upstream:child",)):
    gh.add({
        "number": number, "title": f"[intake] garrytan/{slug}", "state": state,
        "labels": [{"name": name} for name in ("intake", *labels)],
        "body": f"> Umbrella: #5000.\n\n**Suggested ID:** `garrytan/{slug}`\n",
    })


def open_umbrella_with(gh, number, version, rows, approved=False):
    finding_ = finding(version, [r["slug"] for r in rows])
    _payload, body, _records = layout(finding_, rows, previous_version="v0")
    labels = ["upstream:release"] + (["upstream:approved"] if approved else [])
    gh.add({"number": number, "title": f"{PREFIX}{version}", "state": "open",
            "labels": [{"name": name} for name in labels], "body": body})
    return number


def live_of(gh):
    return read_live(gh)


def candidate(payload, slug):
    return next(r for r in payload["candidates"] if r["slug"] == slug)


# ---------------------------------------------------------------------------
# M3: rejecting an umbrella settles its childless rows
# ---------------------------------------------------------------------------


def test_carry_from_a_rejected_umbrella_turns_childless_rows_into_rejected_rows():
    gh = FakeGh()
    closed_umbrella(gh, 10, "v1", [row("ask-user", "new"), row("briefing", "new")],
                    labels=("upstream:rejected",))
    plan = plan_suite(finding("v2", ["ask-user", "briefing"]), live_of(gh), EMPTY_INDEX)
    assert candidate(plan["payload"], "ask-user")["status"] == "rejected"
    assert candidate(plan["payload"], "briefing")["status"] == "rejected"
    assert candidate(plan["payload"], "ask-user")["carriedFrom"] == "#10"


def test_rejected_rows_are_suppressed_and_do_not_reappear_as_new_work(tmp_path):
    gh = FakeGh()
    closed_umbrella(gh, 10, "v1", [row("ask-user", "new")], labels=("upstream:rejected",))
    report, code = run_batch([finding("v2", ["ask-user"])], gh, apply=True, index_loader=lambda: EMPTY_INDEX)
    assert code == 0
    assert report["suppressedDuplicates"] == 1
    assert report["retainedCandidates"] == 1, "the row is kept in the record, not dropped"
    (open_number,) = [n for n, issue in gh.issues.items() if issue["state"] == "open"]
    payload = parse_payload(gh.issues[open_number]["body"])
    assert candidate(payload, "ask-user")["status"] == "rejected"


def test_rejected_rows_are_not_unresolved_so_they_do_not_hold_an_umbrella_open():
    rows = [row("ask-user", "rejected")]
    assert unresolved_row_ids({"candidates": rows}, child_state_lookup({"issues": []})) == []


def test_a_rejected_childless_row_survives_a_later_umbrella_closed_as_completed():
    gh = FakeGh()
    closed_umbrella(gh, 10, "v1", [row("ask-user", "new")], labels=("upstream:rejected",))
    # Closed completed, no rejection label. The row keeps the rejectedBy record M3 wrote.
    closed_umbrella(gh, 11, "v2", [{**row("ask-user", "rejected"), "rejectedBy": "#10"}], labels=())
    plan = plan_suite(finding("v3", ["ask-user"]), live_of(gh), EMPTY_INDEX)
    assert candidate(plan["payload"], "ask-user")["status"] == "rejected"


def test_a_rejection_does_not_touch_a_row_that_has_a_child():
    gh = FakeGh()
    child(gh, 41, "ask-user", "open")
    closed_umbrella(gh, 10, "v1", [row("ask-user", "tracked", child=41), row("briefing", "new")],
                    labels=("upstream:rejected",))
    carried = carry_forward(live_of(gh), GBRAIN, child_state_lookup(live_of(gh), gh.child_state), gh)
    by_slug = {r["slug"]: r for r in carried}
    assert by_slug["ask-user"]["status"] == "tracked", "the child link keeps the row's own status"
    assert by_slug["briefing"]["status"] == "rejected"


def test_an_escalated_rejected_row_gets_a_child_only_by_explicit_human_action(tmp_path):
    gh = FakeGh()
    closed_umbrella(gh, 10, "v1", [row("ask-user", "new")], labels=("upstream:rejected",))
    run_batch([finding("v2", ["ask-user"])], gh, apply=True, index_loader=lambda: EMPTY_INDEX)
    assert not [n for n, issue in gh.issues.items() if issue["title"].startswith("[intake]")], \
        "the watcher alone creates no child"
    result, code = escalate_candidate(f"{GBRAIN}:ask-user", gh, apply=True)
    assert code == 0 and result["outcome"] == "created"
    (open_number,) = [n for n, issue in gh.issues.items() if issue["state"] == "open" and n != result["child"]]
    payload = parse_payload(gh.issues[open_number]["body"])
    assert candidate(payload, "ask-user")["status"] == "escalated"


# ---------------------------------------------------------------------------
# M6: a closed child without a disposition does not resolve its row
# ---------------------------------------------------------------------------


def test_a_child_closed_without_a_disposition_leaves_its_row_unresolved():
    gh = FakeGh()
    child(gh, 41, "ask-user", "closed")  # closed, no upstream:rejected
    state_of = child_state_lookup(live_of(gh), gh.child_state)
    assert state_of(41) == "closed"
    assert row_is_unresolved(row("ask-user", "escalated", child=41), state_of) is True


def test_a_child_closed_with_a_rejection_resolves_its_row():
    gh = FakeGh()
    child(gh, 41, "ask-user", "closed", labels=("upstream:child", "upstream:rejected"))
    state_of = child_state_lookup(live_of(gh), gh.child_state)
    assert state_of(41) == "closed-rejected"
    assert row_is_unresolved(row("ask-user", "escalated", child=41), state_of) is False


def test_a_child_closed_without_disposition_resolves_only_when_the_candidate_is_registry_present():
    gh = FakeGh()
    child(gh, 41, "ask-user", "closed")
    state_of = child_state_lookup(live_of(gh), gh.child_state)
    assert row_is_unresolved(row("ask-user", "escalated", child=41, registry="present"), state_of) is False
    assert row_is_unresolved(row("ask-user", "escalated", child=41, registry="absent"), state_of) is True


def test_the_row_of_an_undispositioned_closed_child_carries_a_note_in_the_plan():
    gh = FakeGh()
    child(gh, 41, "ask-user", "closed")
    open_umbrella_with(gh, 5000, "v1", [row("ask-user", "escalated", child=41)])
    plan = plan_suite(finding("v1", ["ask-user"]), live_of(gh), EMPTY_INDEX, probe=gh.child_state)
    assert candidate(plan["payload"], "ask-user")["note"] == NOTE_CLOSED_WITHOUT_DISPOSITION
    assert NOTE_CLOSED_WITHOUT_DISPOSITION == "child closed without a disposition"


def test_the_note_is_rendered_in_the_body_and_the_row_stays_counted(tmp_path):
    gh = FakeGh()
    child(gh, 41, "ask-user", "closed")
    open_umbrella_with(gh, 5000, "v1", [row("ask-user", "escalated", child=41)])
    report, code = run_batch([finding("v1", ["ask-user"])], gh, apply=True, index_loader=lambda: EMPTY_INDEX)
    assert code == 0
    body = gh.issues[5000]["body"]
    assert NOTE_CLOSED_WITHOUT_DISPOSITION in body
    payload = parse_payload(body)
    assert unresolved_row_ids(payload, child_state_lookup({"issues": []}, gh.child_state)) == [f"{GBRAIN}:ask-user"]


def test_an_undispositioned_closed_child_is_carried_forward_not_dropped():
    gh = FakeGh()
    child(gh, 41, "ask-user", "closed")
    closed_umbrella(gh, 10, "v1", [row("ask-user", "escalated", child=41)], labels=())
    carried = carry_forward(live_of(gh), GBRAIN, child_state_lookup(live_of(gh), gh.child_state), gh)
    assert [r["slug"] for r in carried] == ["ask-user"], "closing an umbrella never drops the row"


def test_the_note_is_removed_once_the_child_is_dispositioned():
    gh = FakeGh()
    child(gh, 41, "ask-user", "closed")
    open_umbrella_with(gh, 5000, "v1", [row("ask-user", "escalated", child=41)])
    plan = plan_suite(finding("v1", ["ask-user"]), live_of(gh), EMPTY_INDEX, probe=gh.child_state)
    assert NOTE_CLOSED_WITHOUT_DISPOSITION in json.dumps(plan["payload"])
    gh.issues[41]["labels"].append({"name": "upstream:rejected"})
    plan = plan_suite(finding("v1", ["ask-user"]), live_of(gh), EMPTY_INDEX, probe=gh.child_state)
    assert "note" not in candidate(plan["payload"], "ask-user")

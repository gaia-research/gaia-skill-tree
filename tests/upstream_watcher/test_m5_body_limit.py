"""Regression tests for M5 (#2131 verifier FAIL): the umbrella body must never exceed GitHub's
65,536-character limit, and the batch record must stay lossless.

Small suites keep the full rows in the body (inline mode, unchanged). A suite whose full
record would overflow the body keeps a compact index (id, status, child) in the body and the
full rows in numbered ``gaia-upstream-record`` comments (records mode). Readers verify the
rows against the body's digest, so a tampered or missing record fails closed (exit 3).
"""

from __future__ import annotations

import json


from scripts.upstream_watcher import records
from scripts.upstream_watcher.batch import (
    BODY_LIMIT,
    escalate_candidate,
    load_rows,
    run_batch,
)
from upstream_fakes import FakeGh, index_from_entries

INDEX = index_from_entries([])
BOT = "github-actions[bot]"


def finding(version, adds):
    return {
        "finding_type": "update",
        "skillId": "garrytan/gbrain",
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


def slugs(count):
    return [f"skill-{number:03d}" for number in range(count)]


def run(gh, fnd, apply=True):
    return run_batch([fnd], gh, apply=apply, index_loader=lambda: INDEX)


def umbrella_numbers(gh):
    return sorted(number for number, row in gh.issues.items() if row["title"].startswith("[upstream] "))


def umbrella_body(gh):
    (number,) = umbrella_numbers(gh)
    return number, gh.issues[number]["body"]


def payload_of(body):
    return json.loads(records.PAYLOAD_RE.search(body).group(1))


def writes_of(gh, kinds):
    return [write for write in gh.writes if write[0] in kinds]


def child(number, slug, state="open", labels=("intake", "upstream:child")):
    return {
        "number": number,
        "title": f"[intake] garrytan/{slug}",
        "state": state,
        "labels": [{"name": name} for name in labels],
        "body": f"> Umbrella: #5000.\n\n**Suggested ID:** `garrytan/{slug}`\n",
        "updated_at": "2026-10-20T00:00:00Z",
    }


# ---------------------------------------------------------------------------
# Inline mode is unchanged for small suites
# ---------------------------------------------------------------------------


def test_small_suite_keeps_full_rows_in_the_body_and_writes_no_record_comments():
    gh = FakeGh()
    run(gh, finding("v1", slugs(5)))
    number, body = umbrella_body(gh)
    payload = payload_of(body)
    assert "candidateRecords" not in payload
    assert len(payload["candidates"]) == 5 and "suggestedId" in payload["candidates"][0]
    assert gh.list_comments(number) == []


# ---------------------------------------------------------------------------
# 250 rows: the body stays under the limit and the record stays lossless
# ---------------------------------------------------------------------------


def test_250_rows_keep_the_body_under_the_github_limit():
    gh = FakeGh()
    report, code = run(gh, finding("v1", slugs(250)))
    assert code == 0
    number, body = umbrella_body(gh)
    assert len(body) <= BODY_LIMIT
    payload = payload_of(body)
    assert payload["candidateRecords"]["rows"] == 250
    assert payload["candidateRecords"]["chunks"] == 5  # 250 rows at 50 per chunk
    assert len(payload["candidates"]) == 250
    assert set(payload["candidates"][0]) == {"id", "status", "child"}


def test_250_rows_round_trip_from_the_record_comments_with_no_rows_lost():
    gh = FakeGh()
    run(gh, finding("v1", slugs(250)))
    number, body = umbrella_body(gh)
    rows = load_rows(gh, number, payload_of(body))
    assert [row["slug"] for row in rows] == slugs(250)
    assert all(row["suggestedId"] == f"garrytan/{row['slug']}" for row in rows)
    assert all(row["evidenceUrl"].endswith(f"/{row['slug']}/SKILL.md") for row in rows)
    assert all(row["precheck"]["registry"] == "absent" for row in rows)


def test_rerun_with_no_change_performs_zero_writes():
    gh = FakeGh()
    run(gh, finding("v1", slugs(250)))
    before = len(gh.writes)
    report, code = run(gh, finding("v1", slugs(250)))
    assert code == 0
    assert gh.writes[before:] == []
    assert report["suites"][0]["outcome"] == "noop"


def test_a_changed_row_edits_only_the_chunk_that_holds_it_and_the_body():
    gh = FakeGh()
    run(gh, finding("v1", slugs(250)))
    gh.add(child(7001, "skill-010"))  # an open intake now tracks row skill-010
    before = len(gh.writes)
    report, code = run(gh, finding("v1", slugs(250)))
    assert code == 0
    new_writes = gh.writes[before:]
    assert [w[0] for w in new_writes].count("edit_comment") == 1, new_writes
    assert [w[0] for w in new_writes].count("comment") == 0, new_writes
    assert [w[0] for w in new_writes].count("edit") == 1, new_writes
    number, body = umbrella_body(gh)
    rows = {row["slug"]: row for row in load_rows(gh, number, payload_of(body))}
    assert rows["skill-010"]["status"] == "tracked"
    assert rows["skill-010"]["child"] == 7001


def test_escalating_a_row_in_a_records_umbrella_rewrites_its_chunk_and_keeps_the_rest():
    gh = FakeGh()
    run(gh, finding("v1", slugs(250)))
    result, code = escalate_candidate("garrytan/gbrain:skill-120", gh, apply=True)
    assert code == 0 and result["outcome"] == "created"
    number, body = umbrella_body(gh)
    rows = {row["slug"]: row for row in load_rows(gh, number, payload_of(body))}
    assert len(rows) == 250
    assert rows["skill-120"]["status"] == "escalated"
    assert rows["skill-120"]["child"] == result["child"]
    assert rows["skill-121"]["status"] == "new"


# ---------------------------------------------------------------------------
# Carry-forward reads the record comments of a closed umbrella
# ---------------------------------------------------------------------------


def test_carry_forward_reads_all_250_rows_back_from_a_closed_umbrella():
    gh = FakeGh()
    run(gh, finding("v1", slugs(250)))
    old_number, _body = umbrella_body(gh)
    gh.issues[old_number]["state"] = "closed"
    report, code = run(gh, finding("v2", []))
    assert code == 0
    fresh = [number for number in umbrella_numbers(gh) if number != old_number]
    assert len(fresh) == 1
    carried = load_rows(gh, fresh[0], payload_of(gh.issues[fresh[0]]["body"]))
    assert len(carried) == 250
    assert all(row["carriedFrom"] == f"#{old_number}" for row in carried)


# ---------------------------------------------------------------------------
# Fail closed: nothing is written from a record that cannot be verified
# ---------------------------------------------------------------------------


def _record_comments(gh, number):
    """The stored comment rows themselves (FakeGh.list_comments returns copies)."""
    return [c for c in gh.comments[number] if records.HEADER_RE.search(c["body"])]


def test_a_tampered_record_comment_fails_closed_with_zero_writes():
    gh = FakeGh()
    run(gh, finding("v1", slugs(250)))
    number, _ = umbrella_body(gh)
    victim = _record_comments(gh, number)[2]
    victim["body"] = victim["body"].replace("skill-1", "skill-9", 1)
    before = len(gh.writes)
    report, code = run(gh, finding("v1", slugs(250)))
    assert code == 3
    assert gh.writes[before:] == []
    assert report["unknownEvidence"]


def test_a_missing_record_chunk_fails_closed_with_zero_writes():
    gh = FakeGh()
    run(gh, finding("v1", slugs(250)))
    number, _ = umbrella_body(gh)
    gh.comments[number] = gh.comments[number][:-1]  # drop the last chunk
    before = len(gh.writes)
    report, code = run(gh, finding("v1", slugs(250)))
    assert code == 3
    assert gh.writes[before:] == []


def test_an_index_too_large_for_the_body_fails_closed_instead_of_writing_a_broken_body():
    """Ceiling: the compact index is about 65 characters a row, so roughly 900 rows fit. Beyond that the
    run stops with exit 3 and writes nothing. It never writes a body over the limit."""
    gh = FakeGh()
    report, code = run(gh, finding("v1", slugs(1000)))
    assert code == 3
    assert gh.writes == []
    assert report["unknownEvidence"][0]["source"] == "github-write"


def test_chunks_are_packed_so_each_comment_stays_under_the_limit():
    rows = [
        {"id": f"garrytan/gbrain:{slug}", "slug": slug, "suggestedId": f"garrytan/{slug}",
         "evidenceUrl": "https://github.com/garrytan/gbrain/blob/main/skills/x/SKILL.md",
         "firstSeenVersion": "v1", "lastSeenVersion": "v1", "child": None, "status": "new",
         "precheck": {"registry": "absent", "tracked": "none", "priorDisposition": "none"}}
        for slug in slugs(120)
    ]
    chunks = records.chunk_rows(rows)
    assert [len(chunk) for chunk in chunks] == [50, 50, 20]
    for index, chunk in enumerate(chunks, start=1):
        assert len(records.render_chunk(index, len(chunks), chunk)) <= records.COMMENT_LIMIT

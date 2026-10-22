"""#2131 round-2 regression tests: H2 (record trust), M6 (ceiling message), M7 (chunk churn).

H2: a record comment is trusted only when the watcher identity authored it. A forged header
    from any other user is ignored and counted, and cannot wedge a run. A trusted chunk that
    fails its digest, or a trusted duplicate of a current chunk, still fails closed. A RecordError
    for one suite does not stop the other suites.
M6: a suite over the records ceiling fails with a message that names the suite, the row count,
    the body limit and the curation decision it needs.
M7: a chunk-set change edits chunks in place, creates only new trailing chunks, and deletes
    surplus chunks, so exactly the current set of watcher record comments remains.
"""

from __future__ import annotations

import pytest

from scripts.upstream_watcher import batch, records
from scripts.upstream_watcher.live import LiveGh
from scripts.upstream_watcher.records import RecordError
from upstream_fakes import FakeGh, index_from_entries

INDEX = index_from_entries([])
BOT = "github-actions[bot]"
MALLORY = "mallory"
SUITE = "garrytan/gbrain"


def finding_for(owner_repo, version, adds):
    return {
        "finding_type": "update",
        "skillId": owner_repo,
        "currentVersion": "v0",
        "newVersion": version,
        "releasedAt": "2026-10-21T00:00:00Z",
        "sourceUrl": f"https://github.com/{owner_repo}/releases/tag/{version}",
        "mode": "components",
        "componentAdds": list(adds),
        "componentRemoves": [],
        "linkLiveness": [],
        "linkLivenessUnknown": [],
        "nameDrift": [],
    }


def slugs(count):
    return [f"skill-{number:03d}" for number in range(count)]


def run(gh, findings):
    return batch.run_batch(findings, gh, apply=True, index_loader=lambda: INDEX)


def umbrella_of(gh, owner_repo=SUITE):
    prefix = f"[upstream] {owner_repo} → "
    (number,) = [n for n, row in gh.issues.items() if row["title"].startswith(prefix) and row["state"] == "open"]
    return number


def stored_records(gh, number):
    """The stored record comment dicts themselves, so a test can tamper with them."""
    return [comment for comment in gh.comments.get(number, []) if records.HEADER_RE.search(comment["body"])]


def add_comment(gh, number, body, login):
    gh.next_comment_id += 1
    gh.comments.setdefault(number, []).append({"id": gh.next_comment_id, "body": body, "user": {"login": login}})
    return gh.next_comment_id


def row(slug, suite=SUITE):
    contributor = suite.split("/")[0]
    return {
        "id": f"{suite}:{slug}", "slug": slug, "suggestedId": f"{contributor}/{slug}",
        "evidenceUrl": f"https://github.com/{suite}/blob/main/skills/{slug}/SKILL.md",
        "firstSeenVersion": "v1", "lastSeenVersion": "v1", "child": None, "status": "new",
        "precheck": {"registry": "absent", "tracked": "none", "priorDisposition": "none"},
    }


def bot_chunk(comment_id, index, of, rows):
    return {"id": comment_id, "user": {"login": BOT}, "body": records.render_chunk(index, of, rows)}


# ---------------------------------------------------------------------------
# H2: only the watcher identity's record comments are read
# ---------------------------------------------------------------------------


def test_a_forged_record_from_another_user_is_ignored_logged_and_does_not_wedge_the_run(capsys):
    gh = FakeGh()
    run(gh, [finding_for(SUITE, "v1", slugs(250))])
    number = umbrella_of(gh)
    forged = records.render_chunk(1, 5, [row("evil")])
    add_comment(gh, number, forged, MALLORY)
    before = gh.write_count()

    report, code = run(gh, [finding_for(SUITE, "v1", slugs(250))])

    assert code == 0, report["unknownEvidence"]
    assert gh.write_count() == before
    assert report["suites"][0]["outcome"] == "noop"
    err = capsys.readouterr().err
    assert "ignored 1 record-looking comment(s) not authored by github-actions[bot]" in err


@pytest.mark.parametrize(
    "garbage",
    [
        "<!-- gaia-upstream-record chunk=1 of=5 sha256=" + "0" * 64 + " -->\nnot a record",
        "<!-- gaia-upstream-record chunk=4 of=2 sha256=" + "f" * 64 + " -->\nstale and broken",
    ],
)
def test_a_forged_broken_header_from_another_user_is_ignored(garbage):
    gh = FakeGh()
    run(gh, [finding_for(SUITE, "v1", slugs(250))])
    add_comment(gh, umbrella_of(gh), garbage, MALLORY)

    report, code = run(gh, [finding_for(SUITE, "v1", slugs(250))])

    assert code == 0, report["unknownEvidence"]
    assert report["suites"][0]["outcome"] == "noop"


def test_a_trusted_chunk_that_fails_its_digest_still_fails_closed_with_zero_writes():
    gh = FakeGh()
    run(gh, [finding_for(SUITE, "v1", slugs(250))])
    number = umbrella_of(gh)
    victim = stored_records(gh, number)[1]
    victim["body"] = victim["body"].replace("skill-0", "skill-9", 1)
    before = gh.write_count()

    report, code = run(gh, [finding_for(SUITE, "v1", slugs(250))])

    assert code == 3
    assert gh.write_count() == before
    assert report["unknownEvidence"]


def test_a_stale_chunk_set_with_a_broken_digest_is_never_read():
    current_rows = [row(slug) for slug in slugs(100)]
    chunks = records.chunk_rows(current_rows)
    meta = {"chunks": len(chunks), "rows": len(current_rows), "sha256": records.rows_digest(current_rows)}
    comments = [bot_chunk(index + 1, index + 1, len(chunks), chunk) for index, chunk in enumerate(chunks)]
    # A watcher comment from an earlier, larger chunk set. Its header digest is broken.
    comments.append({
        "id": 77, "user": {"login": BOT},
        "body": "<!-- gaia-upstream-record chunk=4 of=5 sha256=" + "f" * 64 + " -->\nstale and broken",
    })

    assert records.read_rows(comments, meta) == current_rows


def test_a_record_error_in_one_suite_does_not_block_the_next_suite():
    gh = FakeGh()
    run(gh, [finding_for(SUITE, "v1", slugs(250)), finding_for("acme/tool", "v1", ["alpha", "beta"])])
    number_a = umbrella_of(gh, SUITE)
    stored_records(gh, number_a)[1]["body"] = stored_records(gh, number_a)[1]["body"].replace("skill-0", "skill-9", 1)
    before_a = (gh.issues[number_a]["title"], gh.issues[number_a]["body"])

    report, code = run(gh, [
        finding_for(SUITE, "v2", slugs(250)),            # suite A first: a stop here would hide suite B
        finding_for("acme/tool", "v2", ["alpha", "beta"]),
    ])

    assert code == 3
    assert (gh.issues[number_a]["title"], gh.issues[number_a]["body"]) == before_a, "suite A must not be written"
    number_b = umbrella_of(gh, "acme/tool")
    assert gh.issues[number_b]["title"].endswith("→ v2"), "suite B must still be processed"
    assert [entry["suite"] for entry in report["unknownEvidence"]] == [SUITE]


def test_two_trusted_copies_of_one_chunk_fail_closed_even_when_identical():
    gh = FakeGh()
    run(gh, [finding_for(SUITE, "v1", slugs(250))])
    number = umbrella_of(gh)
    add_comment(gh, number, stored_records(gh, number)[0]["body"], BOT)
    before = gh.write_count()

    report, code = run(gh, [finding_for(SUITE, "v1", slugs(250))])

    assert code == 3
    assert gh.write_count() == before
    assert report["unknownEvidence"]


def test_the_same_comment_listed_twice_by_pagination_is_one_copy():
    current_rows = [row(slug) for slug in slugs(60)]
    chunks = records.chunk_rows(current_rows)
    meta = {"chunks": len(chunks), "rows": len(current_rows), "sha256": records.rows_digest(current_rows)}
    comments = [bot_chunk(index + 1, index + 1, len(chunks), chunk) for index, chunk in enumerate(chunks)]
    assert records.read_rows(comments + comments[:1], meta) == current_rows


def test_a_trusted_duplicate_chunk_in_plan_writes_is_fail_closed():
    current_rows = [row(slug) for slug in slugs(60)]
    chunks = records.chunk_rows(current_rows)
    comments = [bot_chunk(index + 1, index + 1, len(chunks), chunk) for index, chunk in enumerate(chunks)]
    comments.append(bot_chunk(99, 1, len(chunks), chunks[0]))
    with pytest.raises(RecordError):
        records.plan_writes(comments, current_rows)


# ---------------------------------------------------------------------------
# M6: the ceiling is named, measured in rows, and says what to do
# ---------------------------------------------------------------------------


def test_a_suite_over_the_records_ceiling_names_the_suite_rows_limit_and_the_decision_needed():
    gh = FakeGh()
    long_slugs = [f"very-long-skill-slug-name-{number:04d}-with-a-tail" for number in range(1500)]

    report, code = run(gh, [finding_for(SUITE, "v1", long_slugs)])

    assert code == 3
    assert gh.writes == []
    detail = report["unknownEvidence"][0]["detail"]
    assert SUITE in detail
    assert "1500 candidate rows" in detail
    assert "65536" in detail
    assert "curation decision" in detail


# ---------------------------------------------------------------------------
# M7: chunk-set churn
# ---------------------------------------------------------------------------


def test_growing_the_chunk_set_edits_the_existing_chunks_and_creates_only_the_new_one():
    # 250 rows is records mode (5 chunks); 300 rows is 6 chunks. Inline mode would not write record comments.
    gh = FakeGh()
    run(gh, [finding_for(SUITE, "v1", slugs(250))])
    number = umbrella_of(gh)
    before_ids = [comment["id"] for comment in stored_records(gh, number)]
    assert len(before_ids) == 5

    run(gh, [finding_for(SUITE, "v1", slugs(300))])

    comments = stored_records(gh, number)
    assert len(comments) == 6, [comment["body"].splitlines()[0] for comment in comments]
    assert all(" of=6 " in comment["body"].splitlines()[0] for comment in comments)
    assert [comment["id"] for comment in comments[:5]] == before_ids, "existing chunks are edited in place"


def test_plan_writes_deletes_surplus_chunks_when_the_set_shrinks():
    big = [row(slug) for slug in slugs(150)]
    big_chunks = records.chunk_rows(big)
    comments = [bot_chunk(index + 1, index + 1, len(big_chunks), chunk) for index, chunk in enumerate(big_chunks)]
    small = [row(slug) for slug in slugs(100)]

    writes = records.plan_writes(comments, small)

    assert [kind for kind, _id, _text in writes] == ["edit", "edit", "delete"]
    assert writes[-1][1] == 3


def test_plan_writes_with_no_rows_deletes_every_record_comment():
    rows = [row(slug) for slug in slugs(120)]
    chunks = records.chunk_rows(rows)
    comments = [bot_chunk(index + 1, index + 1, len(chunks), chunk) for index, chunk in enumerate(chunks)]
    assert [kind for kind, _id, _text in records.plan_writes(comments, [])] == ["delete"] * 3


def test_plan_writes_ignores_a_stale_comment_from_another_user_when_deleting():
    rows = [row(slug) for slug in slugs(60)]
    chunks = records.chunk_rows(rows)
    comments = [bot_chunk(1, 1, 2, chunks[0]), bot_chunk(2, 2, 2, chunks[1])]
    comments.append({"id": 50, "user": {"login": MALLORY}, "body": records.render_chunk(1, 9, [row("x")])})
    assert records.plan_writes(comments, rows) == []


def test_live_gh_can_delete_a_comment():
    calls = []

    class Done:
        returncode = 0
        stdout = ""
        stderr = ""

    def runner(args, capture_output=True, text=True, timeout=None):
        calls.append(list(args))
        return Done()

    LiveGh(repo="gaia-research/gaia-skill-tree", runner=runner).delete_comment(55)

    assert calls == [[
        "gh", "api", "--method", "DELETE", "repos/gaia-research/gaia-skill-tree/issues/comments/55",
    ]]

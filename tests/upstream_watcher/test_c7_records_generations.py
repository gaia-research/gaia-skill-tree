"""#2131 round-3 verifier FAIL, D4 and I3: records-mode writes are generation-safe.

Before this change a chunk-set change edited chunk comments in place. A partial write (chunk 1 edited,
chunk 2 failed) then left a mix that matched neither the old body nor the new one, so every later run
failed closed with zero writes: a permanent wedge.

The fix. Every record chunk carries its generation (the digest of the full ordered row set). A change
never edits a chunk. The new generation is written as NEW comments first, then the umbrella body is
switched to name it, and only then is the old generation deleted (best effort). The reader reads exactly
the generation the body names. A crash at any step leaves the body naming a complete generation.

I3. A record comment counts only when the watcher login AND the Bot user type wrote it.
"""

from __future__ import annotations

import json

import pytest

from scripts.upstream_watcher import records
from scripts.upstream_watcher.batch import load_rows, parse_payload, run_batch
from scripts.upstream_watcher.live import GhError
from upstream_fakes import FakeGh, index_from_entries

INDEX = index_from_entries([])
RECORD = "<!-- gaia-upstream-record "
SUITE_URL = "https://github.com/garrytan/gbrain/releases/tag/v1"


def finding(version, count):
    return {
        "finding_type": "update",
        "skillId": "garrytan/gbrain",
        "currentVersion": "v0",
        "newVersion": version,
        "releasedAt": "2026-10-21T00:00:00Z",
        "sourceUrl": SUITE_URL,
        "mode": "components",
        "componentAdds": [f"skill-{number:03d}" for number in range(count)],
        "componentRemoves": [],
        "linkLiveness": [],
        "linkLivenessUnknown": [],
        "nameDrift": [],
    }


class FaultyGh(FakeGh):
    """A FakeGh that fails one kind of write on demand. A create may land before it reports an error."""

    def __init__(self, *, create_fault_at=None, landed=False, body_fault=False, delete_fault=False, **kwargs):
        super().__init__(**kwargs)
        self.create_fault_at = create_fault_at
        self.landed = landed
        self.body_fault = body_fault
        self.delete_fault = delete_fault
        self.record_creates = 0

    def comment(self, number, body):
        if body.startswith(RECORD):
            self.record_creates += 1
            if self.record_creates == self.create_fault_at:
                if self.landed:
                    super().comment(number, body)
                raise GhError("injected: record create failed")
        super().comment(number, body)

    def edit_issue(self, number, title, body):
        if self.body_fault:
            raise GhError("injected: body edit failed")
        super().edit_issue(number, title, body)

    def delete_comment(self, comment_id):
        if self.delete_fault:
            raise GhError("injected: record delete failed")
        super().delete_comment(comment_id)


def umbrella(gh):
    (number,) = [n for n, row in gh.issues.items()
                 if row["title"].startswith("[upstream] ") and row["state"] == "open"]
    return number


def named_rows(gh):
    number = umbrella(gh)
    payload = parse_payload(gh.issues[number]["body"])
    return load_rows(gh, number, payload)


def record_comments(gh):
    return [row for row in gh.comments.get(umbrella(gh), []) if row["body"].startswith(RECORD)]


def generations_on_umbrella(gh):
    return sorted({row["body"].split("gen=", 1)[1][:64] for row in record_comments(gh)})


def body_generation(gh):
    return parse_payload(gh.issues[umbrella(gh)]["body"])["candidateRecords"]["sha256"]


def run(gh, version, count):
    return run_batch([finding(version, count)], gh, apply=True, index_loader=lambda: INDEX)


def converged_250(gh):
    report, code = run(gh, "v1", 250)
    assert code == 0, report
    return gh


# ---------------------------------------------------------------------------
# Failure injection at every write step, then a fault-free rerun.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fault_at", [1, 3, 6])
def test_a_failed_record_create_leaves_the_old_generation_intact_and_a_rerun_converges(fault_at):
    gh = converged_250(FaultyGh())
    old_rows = named_rows(gh)
    old_generation = body_generation(gh)
    gh.create_fault_at = fault_at
    gh.record_creates = 0

    report, code = run(gh, "v1", 300)

    assert code == 3 and report["unknownEvidence"], "the failed create stops the suite"
    assert body_generation(gh) == old_generation, "the body still names the complete old generation"
    assert named_rows(gh) == old_rows, "no row is lost while the new generation is incomplete"

    gh.create_fault_at = None
    report, code = run(gh, "v1", 300)
    assert code == 0, report
    assert len(named_rows(gh)) == 300
    assert generations_on_umbrella(gh) == [body_generation(gh)], "only the named generation remains"
    before = gh.write_count()
    run(gh, "v1", 300)
    assert gh.write_count() == before, "a converged rerun performs zero writes"


@pytest.mark.parametrize("fault_at", [2, 5])
def test_a_create_that_landed_before_its_error_is_reused_on_rerun_without_a_second_copy(fault_at):
    gh = converged_250(FaultyGh())
    gh.create_fault_at = fault_at
    gh.landed = True
    gh.record_creates = 0
    run(gh, "v1", 300)

    gh.create_fault_at = None
    report, code = run(gh, "v1", 300)

    assert code == 0, report
    assert len(named_rows(gh)) == 300
    indexes = [row["body"].split("chunk=", 1)[1].split(" ", 1)[0] for row in record_comments(gh)]
    assert sorted(indexes) == [str(n) for n in range(1, 7)], "exactly one copy of each chunk"


def test_a_failed_body_switch_keeps_the_old_generation_and_a_rerun_converges():
    gh = converged_250(FaultyGh())
    old_rows = named_rows(gh)
    old_generation = body_generation(gh)
    gh.body_fault = True

    report, code = run(gh, "v1", 300)

    assert code == 3
    assert body_generation(gh) == old_generation
    assert named_rows(gh) == old_rows
    assert len(record_comments(gh)) == 5 + 6, "the new generation is complete and the old one is still there"

    gh.body_fault = False
    report, code = run(gh, "v1", 300)
    assert code == 0, report
    assert len(named_rows(gh)) == 300
    assert generations_on_umbrella(gh) == [body_generation(gh)]


def test_a_failed_old_generation_delete_is_cleaned_by_a_later_run_and_never_affects_readers():
    gh = converged_250(FaultyGh())
    gh.delete_fault = True

    report, code = run(gh, "v1", 300)

    assert code == 0, "cleanup is best effort: the body already names the complete new generation"
    assert len(named_rows(gh)) == 300
    assert len(record_comments(gh)) == 5 + 6

    gh.delete_fault = False
    run(gh, "v1", 300)
    assert generations_on_umbrella(gh) == [body_generation(gh)]
    assert len(record_comments(gh)) == 6
    before = gh.write_count()
    run(gh, "v1", 300)
    assert gh.write_count() == before


def test_a_converged_umbrella_still_carries_every_row_forward_after_a_crashed_generation():
    gh = converged_250(FaultyGh())
    gh.create_fault_at = 4
    run(gh, "v1", 300)
    gh.create_fault_at = None
    run(gh, "v1", 300)
    gh.issues[umbrella(gh)]["state"] = "closed"

    report, code = run(gh, "v2", 300)

    assert code == 0, report
    carried = [row for row in named_rows(gh) if row.get("carriedFrom")]
    assert len(named_rows(gh)) == 300
    assert carried, "the closed umbrella's unresolved rows are carried forward"


def test_a_600_row_suite_converges_after_a_mid_run_fault_and_then_writes_nothing():
    gh = FaultyGh()
    report, code = run(gh, "v1", 600)
    assert code == 0 and len(record_comments(gh)) == 12

    gh.create_fault_at = None
    gh.record_creates = 0
    gh.add({"number": 7001, "title": "[intake] garrytan/skill-010", "state": "open",
            "labels": [{"name": "upstream:child"}],
            "body": f"> Auto-populated by upstream watcher. Umbrella: #{umbrella(gh)}.\n\n"
                    "**Suggested ID:** `garrytan/skill-010`\n\n### Evidence\n\n"
                    "- **url:** https://github.com/garrytan/gbrain/blob/main/skills/skill-010/SKILL.md\n"})
    gh.create_fault_at = 7
    report, code = run(gh, "v1", 600)
    assert code == 3

    gh.create_fault_at = None
    report, code = run(gh, "v1", 600)
    assert code == 0, report
    rows = {row["slug"]: row for row in named_rows(gh)}
    assert len(rows) == 600
    assert rows["skill-010"]["child"] == 7001
    before = gh.write_count()
    run(gh, "v1", 600)
    assert gh.write_count() == before


# ---------------------------------------------------------------------------
# The reader reads exactly the generation the body names.
# ---------------------------------------------------------------------------


def _generation_comments(rows, *, author=records.WATCHER_LOGIN, bot=True):
    chunks = records.chunk_rows(rows)
    gen = records.rows_digest(rows)
    user = {"login": author, "type": "Bot" if bot else "User"}
    return gen, [
        {"id": 100 + index, "user": dict(user), "body": records.render_chunk(gen, index, len(chunks), chunk)}
        for index, chunk in enumerate(chunks, start=1)
    ]


def _row(slug):
    return {"id": f"garrytan/gbrain:{slug}", "slug": slug, "suggestedId": f"garrytan/{slug}",
            "status": "new", "child": None}


def test_the_reader_ignores_chunks_of_other_generations_and_reads_exactly_the_named_one():
    old_rows = [_row(f"a{n:03d}") for n in range(100)]
    new_rows = [_row(f"b{n:03d}") for n in range(120)]
    old_gen, old_comments = _generation_comments(old_rows)
    new_gen, new_comments = _generation_comments(new_rows)
    comments = old_comments + new_comments

    meta_new = {"chunks": 3, "rows": 120, "sha256": new_gen}
    meta_old = {"chunks": 2, "rows": 100, "sha256": old_gen}

    assert records.read_rows(comments, meta_new) == new_rows
    assert records.read_rows(comments, meta_old) == old_rows


def test_a_partial_new_generation_beside_the_complete_old_one_never_changes_what_is_read():
    old_rows = [_row(f"a{n:03d}") for n in range(100)]
    new_rows = [_row(f"b{n:03d}") for n in range(120)]
    old_gen, old_comments = _generation_comments(old_rows)
    _new_gen, new_comments = _generation_comments(new_rows)
    partial = new_comments[:1]  # two of three new chunks never landed

    assert records.read_rows(old_comments + partial, {"chunks": 2, "rows": 100, "sha256": old_gen}) == old_rows


def test_two_trusted_copies_of_the_named_generation_fail_closed_even_when_identical():
    rows = [_row(f"a{n:03d}") for n in range(60)]
    gen, comments = _generation_comments(rows)
    comments.append(dict(comments[0], id=999))
    with pytest.raises(records.RecordError):
        records.read_rows(comments, {"chunks": 2, "rows": 60, "sha256": gen})


def test_a_tampered_copy_of_the_named_generation_fails_closed():
    rows = [_row(f"a{n:03d}") for n in range(60)]
    gen, comments = _generation_comments(rows)
    comments[0]["body"] = comments[0]["body"].replace("garrytan/a000", "garrytan/evil", 1)
    with pytest.raises(records.RecordError):
        records.read_rows(comments, {"chunks": 2, "rows": 60, "sha256": gen})


# ---------------------------------------------------------------------------
# The planner: new generation first, old generation only after the switch.
# ---------------------------------------------------------------------------


def test_planning_a_new_generation_creates_every_chunk_and_deletes_the_old_one_only_as_cleanup():
    old_rows = [_row(f"a{n:03d}") for n in range(250)]
    new_rows = [_row(f"a{n:03d}") for n in range(300)]
    old_gen, old_comments = _generation_comments(old_rows)

    plan = records.plan_generation(old_comments, new_rows)

    assert [kind for kind, _id, _text in plan.prewrites] == ["create"] * 6
    assert [kind for kind, _id, _text in plan.cleanup] == ["delete"] * 5
    assert {comment_id for _kind, comment_id, _text in plan.cleanup} == {101, 102, 103, 104, 105}


def test_planning_the_named_generation_again_writes_nothing():
    rows = [_row(f"a{n:03d}") for n in range(250)]
    gen, comments = _generation_comments(rows)

    plan = records.plan_generation(comments, rows)

    assert plan.prewrites == [] and plan.cleanup == []


def test_planning_an_inline_umbrella_marks_every_record_for_cleanup():
    rows = [_row(f"a{n:03d}") for n in range(120)]
    gen, comments = _generation_comments(rows)

    plan = records.plan_generation(comments, None)

    assert plan.generation is None and plan.prewrites == []
    assert [kind for kind, _id, _text in plan.cleanup] == ["delete"] * 3


def test_a_trusted_duplicate_of_the_target_generation_fails_closed_in_the_planner():
    rows = [_row(f"a{n:03d}") for n in range(60)]
    gen, comments = _generation_comments(rows)
    comments.append(dict(comments[0], id=777))
    with pytest.raises(records.RecordError):
        records.plan_generation(comments, rows)


# ---------------------------------------------------------------------------
# I3: the Bot user type is part of the trust check, not only the login.
# ---------------------------------------------------------------------------


def test_a_record_from_a_user_named_like_the_watcher_but_not_typed_as_a_bot_is_not_trusted(capsys):
    rows = [_row(f"a{n:03d}") for n in range(60)]
    gen, comments = _generation_comments(rows, bot=False)

    assert records.trusted_comments(comments) == []
    assert "not authored by" in capsys.readouterr().err
    with pytest.raises(records.RecordError, match="missing"):
        records.read_rows(comments, {"chunks": 2, "rows": 60, "sha256": gen})


def test_is_watcher_comment_needs_both_the_exact_login_and_the_bot_type():
    assert records.is_watcher_comment({"user": {"login": records.WATCHER_LOGIN, "type": "Bot"}})
    assert not records.is_watcher_comment({"user": {"login": records.WATCHER_LOGIN, "type": "User"}})
    assert not records.is_watcher_comment({"user": {"login": records.WATCHER_LOGIN}})
    assert not records.is_watcher_comment({"user": {"login": "github-actions", "type": "Bot"}})
    assert not records.is_watcher_comment({"user": None})

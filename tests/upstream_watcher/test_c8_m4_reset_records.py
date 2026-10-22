"""#2131 round-4 verifier FAIL, M4: an explicit recovery path for a deleted or corrupt record chunk.

A deleted record chunk (or one edited by hand) fails the suite closed with zero writes, forever, because no run
can read the generation the body names. ``--reset-records SUITE`` (apply-only) discards that suite's record
state and rebuilds its rows from the fresh upstream poll. Per-row status and child links stored only in the
lost chunks are not recovered. A child intake that is still open is re-adopted by the list lookup.

The exit-3 message names the flag and the suite. A reset run converges: after it, a later run writes nothing.
"""

from __future__ import annotations

import pytest

from scripts.upstream_watcher import watcher
from scripts.upstream_watcher.batch import parse_payload, run_batch
from scripts.upstream_watcher.records import ROWS_PER_CHUNK
from upstream_fakes import FakeGh, index_from_entries

INDEX = index_from_entries([])
RECORD = "<!-- gaia-upstream-record "
SUITE = "garrytan/gbrain"
SOURCE = "https://github.com/garrytan/gbrain/releases/tag/v1"
ROWS = 250  # 5 chunks of 50: records mode (the inline body would exceed the budget)


def finding(count=ROWS, version="v1"):
    return {
        "finding_type": "update",
        "skillId": SUITE,
        "currentVersion": "v0",
        "newVersion": version,
        "releasedAt": "2026-10-21T00:00:00Z",
        "sourceUrl": SOURCE,
        "mode": "components",
        "componentAdds": [f"skill-{number:03d}" for number in range(count)],
        "componentRemoves": [],
        "linkLiveness": [],
        "linkLivenessUnknown": [],
        "nameDrift": [],
    }


def run(gh, reset=None, apply=True, count=ROWS):
    return run_batch([finding(count)], gh, apply=apply, index_loader=lambda: INDEX, reset_records=reset)


def umbrella(gh):
    (number,) = [n for n, row in gh.issues.items() if row["title"].startswith("[upstream] ") and row["state"] == "open"]
    return number


def record_comments(gh):
    return [row for row in gh.comments.get(umbrella(gh), []) if row["body"].startswith(RECORD)]


def converged(gh):
    report, code = run(gh)
    assert code == 0, report
    assert parse_payload(gh.issues[umbrella(gh)]["body"])["candidateRecords"]["chunks"] == ROWS // ROWS_PER_CHUNK
    return gh


def delete_chunk(gh, index):
    target = next(c for c in record_comments(gh) if f"chunk={index} of" in c["body"].split("\n", 1)[0])
    gh.delete_comment(target["id"])


# ---------------------------------------------------------------------------
# The fault and the exit message
# ---------------------------------------------------------------------------


def test_a_deleted_chunk_fails_the_suite_closed_with_zero_writes_and_names_the_flag():
    gh = converged(FakeGh())
    delete_chunk(gh, 2)
    writes_before = gh.write_count()
    report, code = run(gh)
    assert code == 3
    assert gh.write_count() == writes_before, "no write while the record state cannot be read"
    detail = report["unknownEvidence"][0]
    assert detail["suite"] == SUITE and detail["stopped"] is False
    assert "--reset-records garrytan/gbrain" in detail["detail"]
    assert "--apply" in detail["detail"]


def test_an_edited_chunk_fails_closed_and_is_repaired_by_the_reset():
    gh = converged(FakeGh())
    victim = record_comments(gh)[0]
    victim["body"] = victim["body"].replace("Batch record 1 of 5", "Batch record 1 of 5 edited")
    report, code = run(gh)
    assert code == 3 and report["unknownEvidence"][0]["suite"] == SUITE
    report, code = run(gh, reset=SUITE)
    assert code == 0, report


# ---------------------------------------------------------------------------
# The reset rebuilds from the fresh poll and converges
# ---------------------------------------------------------------------------


def test_a_deleted_chunk_then_a_reset_converges_and_a_later_run_writes_nothing():
    gh = converged(FakeGh())
    delete_chunk(gh, 2)
    report, code = run(gh)
    assert code == 3

    report, code = run(gh, reset=SUITE)
    assert code == 0, report
    assert report["suites"][0]["totalRows"] == ROWS
    assert len(record_comments(gh)) == ROWS // ROWS_PER_CHUNK, "every chunk is back, with no duplicate"

    before = gh.write_count()
    report, code = run(gh, reset=SUITE)
    assert code == 0 and gh.write_count() == before, "a converged reset rerun writes nothing"
    assert report["suites"][0]["outcome"] == "noop"


def test_a_later_run_without_the_flag_also_writes_nothing_after_the_reset():
    gh = converged(FakeGh())
    delete_chunk(gh, 4)
    run(gh, reset=SUITE)
    before = gh.write_count()
    report, code = run(gh)
    assert code == 0 and gh.write_count() == before


def test_the_reset_keeps_every_row_of_the_fresh_poll():
    gh = converged(FakeGh())
    delete_chunk(gh, 1)
    run(gh, reset=SUITE)
    rows = parse_payload(gh.issues[umbrella(gh)]["body"])
    assert rows["candidateRecords"]["rows"] == ROWS


def test_the_reset_is_scoped_to_the_named_suite():
    gh = converged(FakeGh())
    delete_chunk(gh, 3)
    report, code = run(gh, reset="some/other-suite")
    assert code == 3, "a reset for another suite does not repair this one"


def test_a_reset_of_an_inline_umbrella_is_harmless():
    gh = FakeGh()
    run(gh, count=3)
    before = gh.write_count()
    report, code = run(gh, reset=SUITE, count=3)
    assert code == 0 and gh.write_count() == before


def test_the_reset_is_refused_without_apply():
    gh = converged(FakeGh())
    with pytest.raises(ValueError, match="--apply"):
        run(gh, reset=SUITE, apply=False)


# ---------------------------------------------------------------------------
# The CLI flag
# ---------------------------------------------------------------------------


def test_the_cli_refuses_reset_records_without_apply(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(watcher, "_build_registry_map", lambda root=None: pytest.fail("no registry read"))
    code = watcher.main(["--reset-records", SUITE])
    assert code == 1
    assert "--reset-records requires --apply" in capsys.readouterr().err


def test_the_cli_accepts_reset_records_with_apply(monkeypatch, tmp_path):
    captured = {}

    def fake_run_batch(findings, gh, apply, index_loader=None, reset_records=None):  # noqa: ARG001
        captured["reset"] = reset_records
        from scripts.upstream_watcher.batch import new_report
        return new_report(), 0

    monkeypatch.setattr(watcher, "_build_registry_map", lambda root=None: {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda root=None: iter([]))
    monkeypatch.setattr(watcher, "run_batch", fake_run_batch)
    monkeypatch.setattr(watcher, "LiveGh", lambda *a, **k: FakeGh())
    assert watcher.main(["--apply", "--reset-records", SUITE, "--report", str(tmp_path / "r.json")]) == 0
    assert captured["reset"] == SUITE

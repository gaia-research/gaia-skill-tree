"""Unit tests for scaffolded curation run state."""

from __future__ import annotations

from gaia_cli.curation.state import CurationRun, STATE_NAMES


def test_state_names_length_is_locked():
    assert len(STATE_NAMES) == 25


def test_curation_run_serializes_and_roundtrips(tmp_path):
    run = CurationRun(
        run_id="run-123",
        input_url="https://github.com/example/repo",
        suggested_generic_id="document-editing",
        discover=True,
        dry_run=True,
    )
    run.source["repo"] = "example/repo"
    run.artifacts["discovery_packet"]["path"] = "artifacts/discovery.json"
    run.decisions["mapping_proposal"] = {"generic_id": "document-editing"}
    run.external_refs["branch"] = "review/meta/run-123"
    run.git["created_commits"].append("abc123")
    run.ledger.append({"state": "INITIALIZED", "message": "created"})

    target = tmp_path / "curation-run"
    run.save(target)
    loaded = CurationRun.load(target)

    assert loaded == run
    assert (target / "state.json").exists()


def test_curation_run_ledger_append_persists(tmp_path):
    run = CurationRun(run_id="run-ledger")
    entry = {"state": "INITIALIZED", "message": "queued"}

    run.ledger.append(entry)
    run.save(tmp_path / run.run_id)

    loaded = CurationRun.load(tmp_path / run.run_id)
    assert loaded.ledger == [entry]

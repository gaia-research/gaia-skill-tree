"""Unit tests for the `gaia curate` command scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from gaia_cli.commands.curate import CurateCommand
from gaia_cli.curation.state import CurationRun


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_curate_command_name_and_help_are_stable():
    command = CurateCommand()

    assert command.name == "curate"
    assert command.help == "Discover candidates and prepare packets for human L4 review"


def test_curate_command_configure_runs_without_error():
    command = CurateCommand()
    parser = argparse.ArgumentParser(prog="gaia curate")

    command.configure(parser)
    parsed = parser.parse_args(
        [
            "https://github.com/example/repo",
            "--generic",
            "document-editing",
            "--discover",
            "--resume",
            "run-123",
            "--status",
            "--dry-run",
        ]
    )

    assert parsed.url == "https://github.com/example/repo"
    assert parsed.generic == "document-editing"
    assert parsed.discover is True
    assert parsed.resume == "run-123"
    assert parsed.status is True
    assert parsed.dry_run is True


def test_curate_command_help_text_renders():
    command = CurateCommand()
    parser = argparse.ArgumentParser(prog="gaia curate")

    command.configure(parser)
    help_text = parser.format_help()
    normalized_help = " ".join(help_text.split())

    assert "--generic" in help_text
    assert "--discover" in help_text
    assert "--resume" in help_text
    assert "--status" in help_text
    assert "--dry-run" in help_text
    assert "Frozen JSON candidate array/envelope" in normalized_help
    assert "maximum five candidates" in normalized_help
    assert "Existing intake issue number" in normalized_help


def test_dynamic_curate_help_does_not_promise_workflow_execution(monkeypatch, capsys):
    from gaia_cli.main import main

    monkeypatch.setattr("sys.argv", ["gaia", "curate", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    help_text = capsys.readouterr().out
    normalized_help = " ".join(help_text.split())
    assert "sequential source discovery and packet prefill" in normalized_help
    assert "always stop at AWAITING_L4_REVIEW" in normalized_help
    assert "submission" not in normalized_help


def test_curate_execute_persists_an_initialized_paused_ledger(tmp_path, monkeypatch, capsys):
    command = CurateCommand()
    parser = argparse.ArgumentParser(prog="gaia curate")
    command.configure(parser)
    args = parser.parse_args(
        ["https://github.com/example/repo", "--discover", "--dry-run"]
    )
    monkeypatch.chdir(tmp_path)

    assert command.execute(args) == 0

    state_files = list((tmp_path / ".gaia" / "curation" / "runs").glob("*/state.json"))
    assert len(state_files) == 1
    state = json.loads(state_files[0].read_text(encoding="utf-8"))
    assert state["current_state"] == "INITIALIZED"
    assert state["discover"] is True
    assert state["dry_run"] is True
    output = capsys.readouterr().out
    assert "State: INITIALIZED" in output


def test_quick_curate_skill_describes_the_paused_scaffold_truthfully():
    skill_text = (
        REPO_ROOT / ".agents" / "skills" / "gaia-quick-curate" / "SKILL.md"
    ).read_text(encoding="utf-8")
    frontmatter = skill_text.split("---", 2)[1]

    assert "paused orchestration scaffold" in skill_text
    assert ".gaia/curation/runs/<run-id>/state.json" in skill_text
    assert "src/gaia_cli/curation/orchestrator.py" in skill_text
    assert "final merge to `main` must remain founder-gated" in skill_text
    assert "Fully automated" not in frontmatter
    assert "PR merge as a 25-state machine" not in frontmatter
    assert "Do not describe this skill as an automated two-gate pipeline" in skill_text


@pytest.mark.parametrize("status_only", [False, True])
def test_resume_preserves_current_blockers_without_reviving_history(
    tmp_path, monkeypatch, capsys, status_only
):
    monkeypatch.chdir(tmp_path)
    run = CurationRun(run_id="synthetic-resume", current_state="RESOLVING_URL")
    run.checkpoint = {
        "sourceRevisions": {"example/tool": "synthetic-sha"},
        "blockers": [
            {"checkId": "batch-recovery", "status": "resolved",
             "resolutionEvidence": "synthetic recovery check passed"},
            {"checkId": "missing-blob", "status": "open", "summary": "blob required"},
            {"checkId": "unproven", "status": "resolved"},
        ],
    }
    run.ledger = [{"checkId": "batch-recovery", "message": "historical failure"}]
    run.save(run.run_dir)
    command = CurateCommand()
    parser = argparse.ArgumentParser()
    command.configure(parser)
    argv = ["--resume", run.run_id] + (["--status"] if status_only else [])

    # A live active blocker pauses before any transition (RESOLVING_URL is a stub).
    # Repeated resumes must remain stable, retaining the resolution evidence.
    for _ in range(2):
        assert command.execute(parser.parse_args(argv)) == 0
        output = capsys.readouterr().out
        active, resolved = output.split("Resolved blockers (with evidence):")
        assert "missing-blob: open" in active
        assert "unproven: unproven-resolution" in active
        assert "batch-recovery" not in active
        assert "batch-recovery: synthetic recovery check passed" in resolved
        assert "example/tool: synthetic-sha" in resolved
        assert CurationRun.load(run.run_dir) == run


@pytest.mark.parametrize("gate", [
    "AWAITING_L4_REVIEW", "AWAITING_EVIDENCE_APPROVAL", "AWAITING_CALIBRATION_APPROVAL"
])
def test_resume_resolved_blockers_do_not_cross_human_gates(tmp_path, monkeypatch, gate):
    monkeypatch.chdir(tmp_path)
    run = CurationRun(run_id="synthetic-gate", current_state=gate)
    run.checkpoint = {"blockers": [
        {"checkId": "recovery", "status": "resolved", "resolutionEvidence": "rc=0"}
    ]}
    run.save(run.run_dir)
    command = CurateCommand()
    parser = argparse.ArgumentParser()
    command.configure(parser)
    assert command.execute(parser.parse_args(["--resume", run.run_id])) == 0
    assert CurationRun.load(run.run_dir) == run


def test_resume_legacy_ledger_without_checkpoint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run = CurationRun(run_id="legacy")
    run.save(run.run_dir)
    target = run.run_dir / "state.json"
    data = json.loads(target.read_text())
    del data["checkpoint"]
    target.write_text(json.dumps(data))
    command = CurateCommand()
    parser = argparse.ArgumentParser()
    command.configure(parser)
    assert command.execute(parser.parse_args(["--resume", "legacy"])) == 1
    assert CurationRun.load(run.run_dir).checkpoint == {}

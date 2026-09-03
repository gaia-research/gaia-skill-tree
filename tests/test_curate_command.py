"""Unit tests for the `gaia curate` command scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from gaia_cli.commands.curate import CurateCommand


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_curate_command_name_and_help_are_stable():
    command = CurateCommand()

    assert command.name == "curate"
    assert command.help == "Initialize or inspect a paused Gaia curation ledger"


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
    assert "discovery does not run" in normalized_help
    assert "no curation workflow transitions run" in normalized_help


def test_dynamic_curate_help_does_not_promise_workflow_execution(monkeypatch, capsys):
    from gaia_cli.main import main

    monkeypatch.setattr("sys.argv", ["gaia", "curate", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    help_text = capsys.readouterr().out
    normalized_help = " ".join(help_text.split())
    assert "new runs pause at INITIALIZED" in normalized_help
    assert "discovery does not run" in normalized_help
    assert "drive it through the gated Gaia curation workflow" not in normalized_help


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

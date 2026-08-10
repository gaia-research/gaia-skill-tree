"""Unit tests for the `gaia curate` command scaffold."""

from __future__ import annotations

import argparse

from gaia_cli.commands.curate import CurateCommand


def test_curate_command_name_and_help_are_stable():
    command = CurateCommand()

    assert command.name == "curate"
    assert command.help == "Scaffold a guided Gaia curation run"


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

    assert "--generic" in help_text
    assert "--discover" in help_text
    assert "--resume" in help_text
    assert "--status" in help_text
    assert "--dry-run" in help_text

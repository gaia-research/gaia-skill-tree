"""Tests for the `gaia curate` command scaffold."""

from __future__ import annotations

import argparse

from gaia_cli.commands.curate import CurateCommand
from gaia_cli.curation.orchestrator import GATE_STATES


def test_curate_scaffold_persists_initial_run_without_crashing(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    args = argparse.Namespace(
        url="https://github.com/example/repo",
        generic=None,
        discover=False,
        resume=None,
        status=False,
        dry_run=False,
    )

    assert CurateCommand().execute(args) == 0

    out = capsys.readouterr().out
    assert "State: INITIALIZED" in out
    assert "URL: https://github.com/example/repo" in out
    assert len(list((tmp_path / ".gaia" / "curation" / "runs").glob("*/state.json"))) == 1


def test_calibration_approval_is_a_human_gate():
    assert "AWAITING_CALIBRATION_APPROVAL" in GATE_STATES

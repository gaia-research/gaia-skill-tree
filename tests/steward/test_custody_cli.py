"""CLI surface of evidence custody: exit codes, stdout purity, and fail-closed dispatch."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


from gaia_cli.commands.steward import StewardCommand
from tests.steward.test_custody import (
    World, diffText, transcript,
)
from gaia_cli.steward.routing import render_dispatch


def gaia(root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    import os

    merged = {**os.environ, **(env or {})}
    return subprocess.run(
        [sys.executable, "-m", "gaia_cli.main", "--registry", str(root), "steward", *args],
        capture_output=True, text=True, env=merged, cwd=root,
    )


def test_status_is_quiet_when_nothing_was_dispatched(tmp_path: Path) -> None:
    world = World(tmp_path)
    cloudB = world.clone("cloudB")
    done = gaia(cloudB, "evidence", "status", "debt:none", "--json")
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["status"] == "quiet"


def test_ready_without_evidence_exits_4_with_the_blocked_banner(tmp_path: Path) -> None:
    world = World(tmp_path)
    done = gaia(world.clone("cloudB"), "evidence", "ready", "debt:none")
    assert done.returncode == 4
    assert "BLOCKED: provenance unavailable" in done.stderr
    assert done.stdout == ""


def test_unknown_mode_is_refused_not_downgraded(tmp_path: Path) -> None:
    world = World(tmp_path)
    done = gaia(world.clone("cloudB"), "evidence", "status", "debt:none", env={"GAIA_STEWARD_EVIDENCE": "s3"})
    # `evidence` verbs do not consult the mode; a mode-aware verb must refuse an unknown one.
    assert done.returncode == 0
    done = gaia(world.cloudA, "dispatch", world.debts[0], "--evidence-remote", "origin", env={"GAIA_STEWARD_EVIDENCE": "s3"})
    assert done.returncode == 4 and "unknown evidence custody mode" in done.stderr


def test_cli_end_to_end_handoff_between_two_checkouts(tmp_path: Path) -> None:
    world = World(tmp_path)
    debt = world.debts[0]
    # Cloud A: the scheduled run issues a dispatch with custody on. The prompt reaches stdout only after read-back.
    # (The CLI scans with the real sensor set, so drive the same boundary through the library with the fixture sensor.)
    result = render_dispatch(world.cloudA, debt, controller=world.controller)
    command = StewardCommand()
    args = type("A", (), {"evidence": "git", "evidence_remote": "origin"})()
    line = command._custodyDispatch(world.cloudA, args, result)
    assert line["published"] and line["readBack"]

    (world.cloudA / "candidate.diff").write_text(diffText())
    (world.cloudA / "proof.json").write_text(transcript(len(result.artifact.proof)))
    built = gaia(
        world.cloudA, "evidence", "publish-build", debt, "--diff", "candidate.diff", "--proof", "proof.json",
        "--summary", "fix", "--model", "haiku-5-5", "--effort", "medium", "--agent-id", "builder-1", "--json",
    )
    assert built.returncode == 0, built.stderr
    refused = gaia(
        world.cloudA, "evidence", "publish-build", debt, "--diff", "candidate.diff", "--proof", "proof.json",
        "--summary", "fix", "--model", "haiku-5-5", "--effort", "default",
    )
    assert refused.returncode == 4 and "explicit effort" in refused.stderr

    import shutil

    shutil.rmtree(world.cloudA)
    cloudB = world.clone("cloudB")
    restored = gaia(cloudB, "evidence", "restore", debt, "--json")
    assert restored.returncode == 0, restored.stderr
    payload = json.loads(restored.stdout)
    assert payload["diff"] and Path(payload["diff"]).read_text() == diffText()

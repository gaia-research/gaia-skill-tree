"""Evidence custody requires the shared git-ref ledger (issue #2448, Codex re-review finding 1).

An ephemeral cloud checkout that quietly fell back to a local ledger would record run, lease and
quiet-day state that disappears with the container. With custody on there is no such fallback.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from gaia_cli.commands.steward import StewardCommand
from gaia_cli.steward.custody import CustodyRefused
from gaia_cli.steward.fullrun import FullRunConfig
from gaia_cli.steward.ledger import FileLedgerStore, GitRefLedgerStore

from tests.steward.test_fullrun import git, makeFixture

LOCAL_LEDGER = Path(".gaia") / "steward" / "full" / "ledger.json"


def gaia(root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    merged = {k: v for k, v in os.environ.items() if k != "GAIA_STEWARD_EVIDENCE"}
    merged.update(env or {})
    return subprocess.run(
        [sys.executable, "-m", "gaia_cli.main", "--registry", str(root), "steward", *args],
        capture_output=True, text=True, env=merged, cwd=root, timeout=300,
    )


def unreachable(tmp_path: Path) -> Path:
    """A checkout whose origin has gone away: the transient-outage case."""

    repo, _ = makeFixture(tmp_path)
    git(repo, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    assert not (repo / LOCAL_LEDGER).exists()
    return repo


@pytest.mark.parametrize("choice", ["auto", "git"])
def test_custody_selects_the_shared_ledger_without_probing_the_remote(tmp_path: Path, choice: str) -> None:
    repo = unreachable(tmp_path)
    store = StewardCommand._fullStore(repo, choice, "origin", custody=True)
    assert isinstance(store, GitRefLedgerStore) and store.shared


def test_legacy_auto_still_falls_back_to_local_when_custody_is_off(tmp_path: Path) -> None:
    repo = unreachable(tmp_path)
    assert isinstance(StewardCommand._fullStore(repo, "auto", "origin", custody=False), FileLedgerStore)


def test_a_local_ledger_cannot_back_a_custody_run(tmp_path: Path) -> None:
    repo, _ = makeFixture(tmp_path)
    local = FileLedgerStore(repo / LOCAL_LEDGER)
    with pytest.raises(CustodyRefused, match="shared git-ref ledger"):
        FullRunConfig(repo_root=repo, store=local, evidence="git")
    FullRunConfig(repo_root=repo, store=local, evidence=None)  # legacy local behaviour is untouched
    FullRunConfig(repo_root=repo, store=GitRefLedgerStore(repo), evidence="git")


def test_the_environment_variable_alone_also_refuses_a_local_ledger(tmp_path: Path, monkeypatch) -> None:
    repo, _ = makeFixture(tmp_path)
    monkeypatch.setenv("GAIA_STEWARD_EVIDENCE", "git")
    with pytest.raises(CustodyRefused):
        FullRunConfig(repo_root=repo, store=FileLedgerStore(repo / LOCAL_LEDGER))


@pytest.mark.parametrize("ledger", [[], ["--ledger", "auto"], ["--ledger", "git"]])
def test_unreachable_remote_blocks_a_quiet_scheduled_run_and_creates_no_local_ledger(
    tmp_path: Path, ledger: list[str]
) -> None:
    repo = unreachable(tmp_path)
    done = gaia(repo, "full", "run", "--trigger", "scheduled", "--json", *ledger,
                env={"GAIA_STEWARD_EVIDENCE": "git"})
    assert done.returncode == 4, (done.stdout, done.stderr)
    assert "BLOCKED: provenance unavailable" in done.stderr
    assert "ledger_local_only" not in done.stdout and "local-file" not in done.stdout
    assert not (repo / LOCAL_LEDGER).exists(), "no local ledger may be created or presented as a durable run"
    assert not (repo / ".gaia" / "steward" / "full").exists()


def test_the_explicit_flag_blocks_exactly_like_the_environment(tmp_path: Path) -> None:
    repo = unreachable(tmp_path)
    done = gaia(repo, "full", "run", "--trigger", "scheduled", "--evidence", "git", "--json")
    assert done.returncode == 4 and "BLOCKED: provenance unavailable" in done.stderr
    assert not (repo / LOCAL_LEDGER).exists()


def test_asking_for_a_local_ledger_with_custody_is_refused_even_when_the_remote_is_up(tmp_path: Path) -> None:
    repo, _ = makeFixture(tmp_path)
    done = gaia(repo, "full", "run", "--trigger", "scheduled", "--ledger", "local", "--json",
                env={"GAIA_STEWARD_EVIDENCE": "git"})
    assert done.returncode == 4 and "shared git-ref ledger" in done.stderr
    assert not (repo / LOCAL_LEDGER).exists()


@pytest.mark.parametrize("verb", [["status"], ["record", "run-x", "step-x", "--input", "-"]])
def test_other_full_verbs_do_not_degrade_either(tmp_path: Path, verb: list[str]) -> None:
    repo = unreachable(tmp_path)
    done = gaia(repo, "full", *verb, env={"GAIA_STEWARD_EVIDENCE": "git"})
    assert done.returncode in (2, 4), (done.stdout, done.stderr)
    assert not (repo / LOCAL_LEDGER).exists()


def test_negative_control_without_custody_the_legacy_auto_path_does_create_local_state(tmp_path: Path) -> None:
    repo = unreachable(tmp_path)
    done = gaia(repo, "full", "run", "--observe", "--trigger", "manual", "--json")
    assert "BLOCKED: provenance unavailable" not in done.stderr
    assert (repo / LOCAL_LEDGER).exists(), "the old fallback silently created local-only run state"
    assert '"transport": "local-file"' in done.stdout

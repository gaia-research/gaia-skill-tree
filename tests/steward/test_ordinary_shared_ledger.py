"""Ordinary `steward full` state stays on the shared Git ledger; only Routine 19 has its own coordination ref.

Regression for the reverted "local-only ordinary state" change, which made `full run|record --ledger git` refuse
("general git ledger is read-only legacy status"). Nothing here touches the real shared ledger: every ref lives on a
disposable bare remote under ``tmp_path``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaia_cli.commands.steward import StewardCommand
from gaia_cli.steward.ledger import GitRefLedgerStore
from tests.steward.test_fullrun import StubSensor, git, makeFixture, makeRunner
from tests.steward.test_fullrun_cli import runCli, useSensors

REFUSAL_MARKERS = ("read-only", "legacy status", "legacy", "general git ledger", "ordinary mutations")


def sharedRefs(bare: Path) -> str:
    return git(bare, "for-each-ref", "--format=%(refname)", "refs/heads/steward")


def assertNotRefused(code: int, out: str, err: str, *, allowed: tuple[int, ...] = (0,)) -> None:
    text = f"{out}\n{err}".lower()
    assert not any(marker in text for marker in REFUSAL_MARKERS), text
    assert code in allowed, text  # exit 2 is the refusal / bad-input code


def test_full_run_with_ledger_git_is_not_refused_and_writes_the_shared_ledger_ref(tmp_path: Path, monkeypatch, capsys) -> None:
    repo, bare = makeFixture(tmp_path)
    useSensors(monkeypatch, [StubSensor("repository-hygiene", "repository_hygiene")])
    assert "refs/heads/steward/ledger" not in sharedRefs(bare).split()
    code, out, err = runCli(monkeypatch, capsys, repo, "run", "--observe", "--ledger", "git", "--trigger", "scheduled", "--json")
    assertNotRefused(code, out, err)
    view = json.loads(out)
    assert view["ledger"]["shared"] is True and view["ledger"]["transport"] == "git-ref"
    assert "warning" not in view["ledger"]  # the shared ledger is not reported as local-only
    assert "steward/ledger" in sharedRefs(bare)
    document, _tip = GitRefLedgerStore(repo, "origin").load()
    assert view["runId"] in document["runs"]  # the run was recorded on the shared ref, not in a local file
    assert not (repo / ".gaia/steward/full/ledger.json").exists()


def test_full_record_with_ledger_git_is_not_refused_and_settles_on_the_shared_ledger(tmp_path: Path, monkeypatch, capsys) -> None:
    repo, bare = makeFixture(tmp_path)
    sensor = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])
    view = makeRunner(repo, StewardCommand._fullStore(repo, "git", "origin"), [sensor]).start("full")
    useSensors(monkeypatch, [sensor])
    step = view.actions[0]["stepId"]
    outcome = tmp_path / "outcome.json"
    outcome.write_text(json.dumps({"agentId": "b1", "model": "haiku", "effort": "medium",
                                   "noChange": True, "summary": "does not reproduce"}), encoding="utf-8")
    code, out, err = runCli(monkeypatch, capsys, repo, "record", view.runId, step, "--input", str(outcome), "--ledger", "git", "--json")
    assertNotRefused(code, out, err)
    payload = json.loads(out)
    assert payload["runId"] == view.runId and payload["actions"] == []
    document, _tip = GitRefLedgerStore(repo, "origin").load()
    recorded = next(a for a in document["runs"][view.runId]["actions"] if a["stepId"] == step)
    assert recorded["status"] == "done"  # the outcome was written to the shared ref


def test_full_abandon_and_status_with_ledger_git_are_not_refused(tmp_path: Path, monkeypatch, capsys) -> None:
    repo, _bare = makeFixture(tmp_path)
    sensor = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])
    view = makeRunner(repo, StewardCommand._fullStore(repo, "git", "origin"), [sensor]).start("full")
    useSensors(monkeypatch, [sensor])
    code, out, err = runCli(monkeypatch, capsys, repo, "status", "--ledger", "git", "--json")
    assertNotRefused(code, out, err)
    code, out, err = runCli(monkeypatch, capsys, repo, "abandon", view.runId, "--reason", "regression probe", "--ledger", "git", "--json")
    assertNotRefused(code, out, err, allowed=(0, 1))  # an abandoned run exits 1; only 2 is a refusal
    document, _tip = GitRefLedgerStore(repo, "origin").load()
    assert document["runs"][view.runId]["status"] == "abandoned"


def test_auto_still_prefers_the_shared_ref_when_the_remote_answers_and_falls_back_only_when_it_does_not(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    assert StewardCommand._fullStore(repo, "auto", "origin").transport == "git-ref"
    lonely = tmp_path / "lonely"
    lonely.mkdir()
    git(lonely, "init", "-q")
    assert StewardCommand._fullStore(lonely, "auto", "origin").transport == "local-file"


def test_the_r19_coordination_ref_is_distinct_from_the_ordinary_ledger_ref() -> None:
    from gaia_cli.steward import ledger
    from gaia_cli.steward.prmaintenance import coordination

    assert coordination.REF != ledger.DEFAULT_REF
    assert coordination.REF == "steward/pr-write-coordination-v1" and ledger.DEFAULT_REF == "steward/ledger"

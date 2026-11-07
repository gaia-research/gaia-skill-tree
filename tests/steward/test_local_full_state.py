"""Ordinary state is local; legacy shared history stays read-only and unmigrated."""
import pytest

from gaia_cli.commands.steward import StewardCommand
from gaia_cli.steward.fullrun import FullRunConfig, FullRunner
from gaia_cli.steward.ledger import GitRefLedgerStore
from tests.steward.test_fullrun import fileStore, git, makeFixture, makeRunner, StubSensor
from tests.steward.test_fullrun_cli import runCli


def test_auto_and_local_do_not_probe_origin_or_choose_a_shared_store(tmp_path, monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: pytest.fail("ordinary auto/local must not probe Git"))
    for choice in ("auto", "local"):
        result = StewardCommand._fullStore(tmp_path, choice, "origin")
        assert result.shared is False and result.transport == "local-file"


@pytest.mark.parametrize("action,args", [("run", []), ("record", ["OLD", "STEP", "--input", "absent.json"]),
                                          ("abandon", ["OLD", "--reason", "fixture"])])
def test_cli_rejects_legacy_mutation_before_store_construction(tmp_path, monkeypatch, capsys, action, args):
    repo, _ = makeFixture(tmp_path)
    monkeypatch.setattr(StewardCommand, "_fullStore", lambda *a: pytest.fail("legacy mutation may not construct/load store"))
    code, _, error = runCli(monkeypatch, capsys, repo, action, *args, "--ledger", "git")
    assert code == 2 and "read-only legacy status" in error


def test_independent_checkouts_with_one_origin_keep_ordinary_runs_separate(tmp_path):
    repo, bare = makeFixture(tmp_path)
    clone = tmp_path / "independent-checkout"
    git(tmp_path, "clone", str(bare), str(clone))
    before = git(bare, "show-ref")
    left = StewardCommand._fullStore(repo, "auto", "origin")
    right = StewardCommand._fullStore(clone, "auto", "origin")
    first = makeRunner(repo, left, [StubSensor("repository-hygiene", "repository_hygiene")], trigger="scheduled").start("observe")
    retained, _ = left.load()
    assert first.runId in retained["runs"] and right.load()[0]["runs"] == {}
    second = makeRunner(clone, right, [StubSensor("repository-hygiene", "repository_hygiene")], trigger="scheduled").start("observe")
    assert left.load()[0] == retained
    assert list(right.load()[0]["runs"]) == [second.runId]
    assert git(bare, "show-ref") == before  # no shared ledger creation/backfill


def test_legacy_status_does_not_migrate_or_settle_any_history(tmp_path):
    repo, bare = makeFixture(tmp_path)
    local = fileStore(tmp_path)
    view = makeRunner(repo, local, [StubSensor("repository-hygiene", "repository_hygiene")], trigger="scheduled").start("observe")
    document, _ = local.load()
    legacy = GitRefLedgerStore(repo, "origin")
    # Explicit administrative legacy HISTORY fixture, not a production run.
    before = legacy.compare_and_swap(None, document, "disposable historical legacy fixture")
    status = FullRunner(FullRunConfig(repo, legacy)).status()
    assert status.ledger["shared"] is True and status.ledger["scope"] == "legacy-read-only"
    after, tip = legacy.load()
    assert tip == before and view.runId in after["runs"]
    assert after["runs"][view.runId] == document["runs"][view.runId]
    normal = StewardCommand._fullStore(repo, "auto", "origin")
    assert normal.load()[0]["runs"] == {}  # no copied/migrated eligible work
    assert not (repo / ".gaia/steward/full/ledger.json").exists()
    assert git(bare, "rev-parse", "refs/heads/steward/ledger") == before

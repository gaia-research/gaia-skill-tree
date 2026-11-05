"""Memory command integration against disposable shared Git, never campaigns."""
from __future__ import annotations

import json

import pytest

from gaia_cli.steward import archive as a
from tests.steward.test_archive import hosts, seed, refs
from tests.steward.test_fullrun_cli import runCli


def test_memory_cli_preview_apply_search_show_and_forward_rollback(hosts, monkeypatch, capsys):
    remote, one, two = hosts
    original, version = seed(one)
    branches = refs(remote)
    code, out, err = runCli(monkeypatch, capsys, one.repo_root, "archive", "run-a")
    assert code == 0, err
    assert json.loads(out)["eligible"] == ["run-a"]
    assert refs(remote) == branches
    code, out, err = runCli(monkeypatch, capsys, one.repo_root, "archive", "run-a", "--apply")
    assert code == 0, err
    assert json.loads(out)["archived"] == ["run-a"]
    migrated = two.load()
    code, out, err = runCli(monkeypatch, capsys, two.repo_root, "show", "run-a")
    assert code == 0, err
    assert json.loads(out)["run"] == original["runs"]["run-a"]
    code, out, err = runCli(monkeypatch, capsys, two.repo_root, "history", "--debt", "debt-c", "--routine", "18")
    assert code == 0, err
    assert [r["runId"] for r in json.loads(out)["entries"]] == ["run-a"]
    code, out, err = runCli(monkeypatch, capsys, two.repo_root, "rollback", "run-a")
    assert code == 0, err
    assert json.loads(out)["applyRequired"]
    assert one.load() == migrated
    code, out, err = runCli(monkeypatch, capsys, two.repo_root, "rollback", "run-a", "--apply")
    assert code == 0, err
    assert json.loads(out)["restored"] == ["run-a"]
    assert one.load()[0]["runs"] == original["runs"]
    assert one.load()[1] != version
    assert [r["event"] for r in a.history(one, pages=2)["entries"]] == ["rollback", "archive"]
    assert not (one.repo_root / ".gaia").exists()
    assert not (two.repo_root / ".gaia").exists()


def test_memory_cli_snapshot_emits_exact_original_ledger_bytes(hosts, monkeypatch, capsys):
    _, one, two = hosts
    _, version = seed(one)
    from tests.steward.test_archive import raw_source
    original = raw_source(one, version)
    a.migrate(one)
    code, out, err = runCli(monkeypatch, capsys, two.repo_root, "show", "run-a", "--snapshot")
    assert code == 0, err
    assert out.encode("utf-8") == original


@pytest.mark.parametrize("argv, expected", [
    (("history", "--cursor", "not-json"), 2),
    (("history", "--cursor", "{}"), 1),
    (("history", "--pages", "11"), 2),
    (("archive", "--max-runs", "33"), 2),
    (("show", "missing"), 1),
])
def test_memory_cli_refusals_are_read_only(hosts, monkeypatch, capsys, argv, expected):
    remote, one, _ = hosts
    before = seed(one)
    branches = refs(remote)
    code, out, err = runCli(monkeypatch, capsys, one.repo_root, *argv)
    assert code == expected
    assert "refused" in err or "failed" in err
    assert one.load() == before
    assert refs(remote) == branches

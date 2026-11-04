"""Ordinary readers, large runs and archive-only provenance (temporary remotes)."""
from __future__ import annotations

import json

import pytest

from gaia_cli.steward import archive as a
from gaia_cli.steward.fullrun import FullRunConfig, FullRunner
from gaia_cli.steward.ledger import GitRefLedgerStore, LedgerUnavailable
from tests.steward.test_archive import hosts, seed, run_record, git, raw_source


def reader(store):
    return FullRunner(FullRunConfig(repo_root=store.repo_root, store=store))


@pytest.mark.parametrize("missing", ["run", "snapshot", "anchor"])
def test_ordinary_view_resume_and_repeat_record_keep_original_coverage(hosts, monkeypatch, missing):
    remote, one, two = hosts
    record = run_record()
    # Explicit unknown coverage must never become a falsely healthy empty list.
    record["phases"]["observe"].update(coverageUnknown=["unavailable-sensor"],
                                       notEvaluated=[{"sensor": "optional", "reason": "off"}])
    before, _ = seed(one, {"run-a": record})
    original = reader(one)._view(before, "run-a").to_dict()
    a.migrate(one)
    runner = reader(two)
    hot, _ = two.load()
    view = runner._view(hot, "run-a").to_dict()
    assert view == original
    assert runner.resume("run-a").to_dict() == original
    # Isolate outcome validation from the record replay behavior: no forge calls.
    monkeypatch.setattr(runner, "_recordPullRequest", lambda *args: lambda *args: None)
    assert runner.record("run-a", "forge:one", record["actions"][0]["outcome"]).to_dict() == original
    pointer = two.load()[0]["runs"]["run-a"][a.POINTER]
    envelope = a.resolve_segment(a.GitArchive(two), pointer["segment"])
    damaged = {"run": pointer["segment"], "snapshot": envelope["source"], "anchor": envelope["sourceAnchor"]}[missing]
    git(remote, "update-ref", "-d", f"refs/heads/{a.PREFIX}/{missing}/{damaged['sha256']}")
    frozen = two.load()
    for operation in (lambda: runner._view(frozen[0], "run-a"), lambda: runner.resume("run-a"),
                      lambda: runner.record("run-a", "forge:one", record["actions"][0]["outcome"]),
                      lambda: runner._loadRun("run-a")):
        with pytest.raises(LedgerUnavailable):
            operation()
        assert two.load() == frozen  # not even a no-op hot generation is advanced


def test_valid_run_above_two_mib_roundtrips_bounded_envelope(hosts):
    _, one, two = hosts
    record = run_record(phases={"observe": {"payload": "x" * (2 * 1024 * 1024 + 4096)}})
    before, version = seed(one, {"run-a": record})
    raw = raw_source(one, version)
    result = a.migrate(one)
    assert result["archived"] == ["run-a"]
    assert a.show(two, "run-a")["run"] == before["runs"]["run-a"]
    assert a.snapshot(two, "run-a") == raw
    a.rollback(two, "run-a")
    assert one.load()[0]["runs"] == before["runs"]


def test_equal_snapshots_at_distinct_commits_keep_each_source_reachable_from_archive_only(hosts, tmp_path):
    remote, one, _ = hosts
    before, first = seed(one)
    raw = raw_source(one, first)
    # Same JSON, different source identity; no live data or historical ref rewrite.
    blob = git(remote, "hash-object", "-w", "--stdin", data=raw)
    tree = git(remote, "mktree", data=f"100644 blob {blob}\tledger.json\n".encode())
    second = git(remote, "commit-tree", tree, "-m", "independent identical source")
    archive = a.GitArchive(one)
    snapshot = archive.publish("snapshot", raw, parent=first)
    # Fetch the second synthetic source commit so the worker can create its anchor.
    git(remote, "update-ref", "refs/heads/steward/synthetic-source", second)
    git(one.repo_root, "fetch", "origin", "refs/heads/steward/synthetic-source")
    assert archive.publish("snapshot", raw, parent=second) == snapshot
    anchor = archive.publish("anchor", a.packed({"schemaVersion": a.SCHEMA, "kind": "anchor",
                             "source": snapshot, "sourceCommit": second}), parent=second)
    segment = archive.publish("run", a.packed({"schemaVersion": a.SCHEMA, "kind": "run", "runId": "run-a",
                              "run": before["runs"]["run-a"], "source": snapshot, "sourceAnchor": anchor,
                              "sourceCommit": second, "ledgerRef": one.ref}))
    # Drop only disposable test hot/source refs. A truly fresh repo fetches just
    # archive branches, not source ledger history from another ref/cache.
    git(remote, "update-ref", "-d", "refs/heads/steward/synthetic-source")
    git(remote, "update-ref", "-d", "refs/heads/steward/ledger")
    root = tmp_path / "archive-only"
    root.mkdir()
    git(root, "init", "--quiet")
    git(root, "remote", "add", "origin", str(remote))
    fresh = a.GitArchive(GitRefLedgerStore(root))
    assert a.resolve_segment(fresh, segment)["sourceCommit"] == second
    assert fresh.read(snapshot) == raw
    assert git(root, "cat-file", "-p", f"{second}:ledger.json").encode() + b"\n" == raw


def test_hot_index_is_constant_shape_while_pages_and_metadata_growth_are_explicit(hosts):
    _, one, _ = hosts
    seed(one, {f"r-{n}": run_record(f"r-{n}") for n in range(3)})
    sizes = []
    for n in range(3):
        a.migrate(one, run_ids=[f"r-{n}"])
        memory = a.memory(one.load()[0])
        sizes.append(len(a.packed(memory)))
        assert memory["pages"] == memory["events"] == n + 1
    assert max(sizes) - min(sizes) < 8  # counters, never one hot entry per event
    assert len(a.history(one, pages=3)["entries"]) == 3
    report = a.plan(one)
    assert "remain hot and grow" in report["capacity"]["retentionLimit"]

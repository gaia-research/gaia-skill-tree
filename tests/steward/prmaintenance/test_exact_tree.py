"""Exact base tree materialization is independent of Git archive attributes."""
import dataclasses

import pytest

from gaia_cli.steward.prmaintenance import gate, proofs
from tests.steward.prmaintenance import helpers as h
from tests.steward.prmaintenance.test_executor import world, prepare


@pytest.mark.parametrize("source", ["environment", "info", "committed"])
def test_exact_blob_bytes_modes_and_manifest_ignore_attributes(tmp_path, monkeypatch, source):
    root = tmp_path / "repo"
    root.mkdir()
    h.run(root, "init", "-q")
    historical = root / "docs/reports/2026-42/index.html"
    historical.parent.mkdir(parents=True)
    historical.write_bytes(b"literal $Format:%H$\n")
    executable = root / "docs/reports/run"
    executable.write_bytes(b"#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    subst = root / "docs/reports/subst"
    subst.write_bytes(b"literal $Format:%H$\n")
    attrs = ("docs/reports/2026-42/index.html export-ignore\n"
             "docs/reports/subst export-subst\n")
    if source == "committed":
        (root / ".gitattributes").write_text(attrs)
    h.run(root, "add", ".")
    h.run(root, "commit", "-qm", "fixture")
    sha = h.run(root, "rev-parse", "HEAD")
    if source == "info":
        (root / ".git/info/attributes").write_text(attrs)
    if source == "environment":
        attrfile = tmp_path / "attributes"
        attrfile.write_text(attrs)
        monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
        monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.attributesFile")
        monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(attrfile))
    target = tmp_path / "out"
    assert proofs.exportBase(root, sha, ["docs/reports"], target)
    assert (target / "docs/reports/2026-42/index.html").read_bytes() == b"literal $Format:%H$\n"
    assert (target / "docs/reports/run").read_bytes() == executable.read_bytes()
    assert (target / "docs/reports/run").stat().st_mode & 0o111
    assert not (target / "docs/reports/subst").stat().st_mode & 0o111
    assert (target / "docs/reports/subst").read_bytes() == b"literal $Format:%H$\n"
    assert {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()} == {
        "docs/reports/2026-42/index.html", "docs/reports/run", "docs/reports/subst"}


@pytest.mark.parametrize("source", ["environment", "info"])
def test_dropped_history_cannot_be_hidden_by_attributes(tmp_path, monkeypatch, source):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, clock, executor, request, cold = fixture
    historical = fx.root / "docs/reports/2026-42/index.html"
    original = historical.read_bytes()
    historical.unlink()
    fx.rebuildIndexes()
    historical.write_bytes(original)
    bad = fx.commit("bad fixture index")
    forge.snap = dataclasses.replace(forge.snap, row=h.row(fx, bad, "2026-44", prId="2270", repositoryId="42"))
    forge.fact["head"]["sha"] = bad
    request["expectedHeadSha"] = bad
    with pytest.raises(gate.GateRefused, match="index-rebuild"):
        gate.validateWrite(fx.root, request, forge.snap, h.utc(), "merge")
    attrtext = "/docs/reports/2026-42/index.html export-ignore\n"
    if source == "info":
        (fx.root / ".git/info/attributes").write_text(attrtext)
    else:
        attrfile = tmp_path / "attributes"
        attrfile.write_text(attrtext)
        monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
        monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.attributesFile")
        monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(attrfile))
    with pytest.raises(gate.GateRefused, match="index-rebuild"):
        gate.validateWrite(fx.root, request, forge.snap, h.utc(), "merge")
    assert len(forge.invocations) == len(forge.effects) == 0


def test_clean_history_with_info_attributes_still_executes(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, _, executor, _, _ = fixture
    (fx.root / ".git/info/attributes").write_text("/docs/reports/2026-42/index.html export-ignore\n")
    result = executor.execute(prepare(fixture)["operationId"])
    assert result["state"] == "merged"
    assert len(forge.invocations) == len(forge.effects) == 1


def test_committed_attributes_do_not_hide_historical_index_rows(tmp_path):
    fx = h.makeRepo(tmp_path / "content")
    (fx.root / ".gitattributes").write_text("/docs/reports/2026-42/index.html export-ignore\n")
    fx.base = fx.commit("base with committed attributes")
    head = fx.head("2026-44")
    assert all(p.state == proofs.PASS for p in proofs.contentEngineProofs(fx.root, fx.base, head, "2026-44"))
    historical = fx.root / "docs/reports/2026-42/index.html"
    original = historical.read_bytes()
    historical.unlink()
    fx.rebuildIndexes()
    historical.write_bytes(original)
    bad = fx.commit("drop history from indexes")
    result = {p.name: p for p in proofs.contentEngineProofs(fx.root, fx.base, bad, "2026-44")}
    assert result["index-rebuild"].state == proofs.FAIL
    assert "index.json rows differ" in result["index-rebuild"].detail
    assert "index.html differs" in result["index-rebuild"].detail


def test_symlinks_and_missing_paths_fail_closed(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    h.run(root, "init", "-q")
    (root / "dir").mkdir()
    (root / "dir/file").write_text("ok")
    (root / "dir/link").symlink_to("file")
    h.run(root, "add", ".")
    h.run(root, "commit", "-qm", "fixture")
    sha = h.run(root, "rev-parse", "HEAD")
    assert not proofs.exportBase(root, sha, ["dir"], tmp_path / "out1")
    assert not proofs.exportBase(root, sha, ["missing"], tmp_path / "out2")
    assert not proofs.exportBase(root, sha, ["../dir"], tmp_path / "out3")
    out = tmp_path / "out4"
    out.mkdir()
    (out / "dir").symlink_to(tmp_path, target_is_directory=True)
    assert not proofs.exportBase(root, sha, ["dir/file"], out)
    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    assert not proofs.exportBase(root, sha, ["dir/file"], alias / "out5")


def test_oversize_blob_and_gitlink_fail_closed(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    h.run(root, "init", "-q")
    (root / "large").write_bytes(b"x" * (16 * 1024 * 1024 + 1))
    h.run(root, "add", "large")
    h.run(root, "commit", "-qm", "large")
    sha = h.run(root, "rev-parse", "HEAD")
    assert not proofs.exportBase(root, sha, ["large"], tmp_path / "out-large")
    h.run(root, "update-index", "--add", "--cacheinfo", "160000", sha, "linked")
    h.run(root, "commit", "-qm", "gitlink")
    sha = h.run(root, "rev-parse", "HEAD")
    assert not proofs.exportBase(root, sha, ["linked"], tmp_path / "out-link")

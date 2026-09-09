from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import pytest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def loadBuildDocs():
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location("build_docs_arbor_test", ROOT / "scripts" / "build_docs.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_arbor_projection_is_offline_scoped_and_deterministic(tmp_path, monkeypatch):
    buildDocs = loadBuildDocs()
    monkeypatch.setattr(buildDocs, "ROOT", tmp_path)
    shutil.copytree(
        ROOT / "registry" / "arbor" / "contracts",
        tmp_path / "registry" / "arbor" / "contracts",
    )
    outside = tmp_path / "docs" / "graph" / "untouched.json"
    outside.parent.mkdir(parents=True)
    outside.write_text("keep", encoding="utf-8")

    assert buildDocs.build_arbor_projection(check=True) is True
    assert not (tmp_path / "docs" / "graph" / "arbor").exists()
    assert buildDocs.build_arbor_projection(check=False) is True
    first = {
        path.relative_to(tmp_path / "docs" / "graph" / "arbor"): path.read_bytes()
        for path in (tmp_path / "docs" / "graph" / "arbor").rglob("*")
        if path.is_file()
    }
    stale = tmp_path / "docs" / "graph" / "arbor" / "stale.txt"
    stale.write_text("stale", encoding="utf-8")
    assert buildDocs.build_arbor_projection(check=True) is True
    assert stale.exists()
    assert buildDocs.build_arbor_projection(check=False) is True
    second = {
        path.relative_to(tmp_path / "docs" / "graph" / "arbor"): path.read_bytes()
        for path in (tmp_path / "docs" / "graph" / "arbor").rglob("*")
        if path.is_file()
    }
    assert first == second
    assert outside.read_text(encoding="utf-8") == "keep"
    sources = tmp_path / "registry" / "arbor" / "sources"
    assert not sources.exists() or not list(sources.rglob("*.json"))


@pytest.mark.parametrize("shape", ["root", "parent", "nested", "leaf"])
def test_arbor_publisher_rejects_symlinked_managed_paths_without_deleting_target(
    tmp_path, monkeypatch, shape
):
    buildDocs = loadBuildDocs()
    monkeypatch.setattr(buildDocs, "ROOT", tmp_path)
    shutil.copytree(
        ROOT / "registry" / "arbor" / "contracts",
        tmp_path / "registry" / "arbor" / "contracts",
    )
    buildDocs.build_arbor_projection(check=False)

    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "marker.txt"
    marker.write_text("must survive", encoding="utf-8")
    committed = tmp_path / "docs" / "graph" / "arbor"
    if shape == "root":
        shutil.rmtree(committed)
        os.symlink(outside, committed)
    elif shape == "parent":
        shutil.rmtree(committed)
        shutil.rmtree(tmp_path / "docs" / "graph")
        os.symlink(outside, tmp_path / "docs" / "graph")
    elif shape == "nested":
        runtime = committed / "runtime"
        shutil.rmtree(runtime)
        os.symlink(outside, runtime)
    else:
        edges = committed / "edges.json"
        edges.unlink()
        os.symlink(marker, edges)

    from gaia_cli.arbor import ArborError

    with pytest.raises(ArborError, match="Arbor managed path"):
        buildDocs.build_arbor_projection(check=True)
    assert marker.read_text(encoding="utf-8") == "must survive"

"""Tests for the ``--cache-bust-only`` mode in ``scripts/build_docs.py``.

Pins the release-time version-sync contract (PR #1114): a release commit must
be self-consistent for ``gaia dev docs --check``, which validates every
version-derived surface. ``gaia dev release`` bumps ``pyproject.toml`` but the
only surfaces it must additionally re-stamp are:

  1. the ``?v=X.Y.Z`` / ``GAIA_VERSION`` strings in tracked Class S docs/*.html
  2. the README version region (``<!-- gaia:version-start --> … end``)

Both derive solely from ``pyproject.toml``. ``--cache-bust-only`` refreshes
exactly those two and NOTHING else — in particular it must never read the
gitignored Class P registry snapshot or rebuild badges (the 2026-06-24
stale-snapshot badge-wipe class of failure).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "build_docs.py"


def _load() -> object:
    """Import ``build_docs`` by path (the script is not in a package)."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    sys.path.insert(0, str(REPO_ROOT / "src"))
    spec = importlib.util.spec_from_file_location("build_docs", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def bd():
    return _load()


def test_readme_version_only_rewrites_only_version_region(bd, tmp_path, monkeypatch):
    """build_readme_version_only touches the version region and nothing else."""
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Title\n\n"
        "<!-- gaia:version-start -->\n"
        "Current Gaia CLI version: `1.0.0`.\n"
        "<!-- gaia:version-end -->\n\n"
        "<!-- gaia:registry-start -->\n"
        "SACRED-TREE-CONTENT-DO-NOT-TOUCH\n"
        "<!-- gaia:registry-end -->\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(bd, "ROOT", tmp_path)
    monkeypatch.setattr(bd, "_read_version", lambda: "9.9.9")

    changed = bd.build_readme_version_only(check=False)

    text = readme.read_text(encoding="utf-8")
    assert changed is True
    assert "`9.9.9`" in text
    assert "`1.0.0`" not in text
    # The registry region must be left exactly as-is — version-only refresh must
    # never touch registry-tree / CLI-help / layout (they need Class P gaia.json).
    assert "SACRED-TREE-CONTENT-DO-NOT-TOUCH" in text


def test_readme_version_only_idempotent(bd, tmp_path, monkeypatch):
    readme = tmp_path / "README.md"
    readme.write_text(
        "<!-- gaia:version-start -->\n"
        "Current Gaia CLI version: `9.9.9`.\n"
        "<!-- gaia:version-end -->\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(bd, "ROOT", tmp_path)
    monkeypatch.setattr(bd, "_read_version", lambda: "9.9.9")

    # _versions() emits the full install-instructions body, so seed a realistic
    # already-current region and assert a second pass is a no-op.
    bd.build_readme_version_only(check=False)
    before = readme.read_text(encoding="utf-8")
    changed = bd.build_readme_version_only(check=False)
    after = readme.read_text(encoding="utf-8")
    assert changed is False
    assert before == after


def test_readme_version_only_missing_file_is_noop(bd, tmp_path, monkeypatch):
    monkeypatch.setattr(bd, "ROOT", tmp_path)  # no README.md present
    assert bd.build_readme_version_only(check=False) is False


def test_cache_bust_only_main_refreshes_html_and_readme(bd, monkeypatch):
    """--cache-bust-only runs BOTH refreshers and never the full pipeline."""
    calls = []
    monkeypatch.setattr(
        bd, "build_html_cache_busting", lambda check: calls.append(("html", check)) or True
    )
    monkeypatch.setattr(
        bd, "build_readme_version_only", lambda check: calls.append(("readme", check)) or False
    )
    # Guard: a full-pipeline step must NOT run in cache-bust-only mode.
    monkeypatch.setattr(
        bd, "build_badges", lambda check: (_ for _ in ()).throw(
            AssertionError("build_badges must not run under --cache-bust-only")
        )
    )

    rc = bd.main(["--cache-bust-only"])

    assert rc == 0
    assert ("html", False) in calls
    assert ("readme", False) in calls

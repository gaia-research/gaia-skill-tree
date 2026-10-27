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
    monkeypatch.setattr(
        bd, "build_health_version_only", lambda check: calls.append(("health", check)) or False
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
    assert ("health", False) in calls


# --- build_html_cache_busting: docs/en/*.html coverage (#2042) -------------

_EN_PAGE = (
    "<!doctype html>\n<html>\n<head>\n  <title>t</title>\n"
    '  <link rel="stylesheet" href="../css/styles.css?v=8.18.2">\n'
    "</head>\n<body>\n"
    '  <nav><span class="nav-version">v8.18.2</span></nav>\n'
    '  <script src="../js/site-nav.js?v=8.18.2"></script>\n'
    "</body>\n</html>\n"
)


def _seed_en_root(bd, tmp_path, monkeypatch, version="9.9.9"):
    (tmp_path / "docs" / "en").mkdir(parents=True)
    monkeypatch.setattr(bd, "ROOT", tmp_path)
    monkeypatch.setattr(bd, "_read_version", lambda: version)
    return tmp_path / "docs" / "en"


def test_en_glob_covers_unregistered_page(bd, tmp_path, monkeypatch, capsys):
    """A page dropped into docs/en/ is picked up with no list entry to add."""
    en_dir = _seed_en_root(bd, tmp_path, monkeypatch)
    page = en_dir / "newpage.html"
    page.write_text(_EN_PAGE, encoding="utf-8")

    assert bd.build_html_cache_busting(check=True) is True
    assert "diff docs/en/newpage.html" in capsys.readouterr().out
    assert page.read_text(encoding="utf-8") == _EN_PAGE  # check mode never writes

    assert bd.build_html_cache_busting(check=False) is True
    text = page.read_text(encoding="utf-8")
    assert '<span class="nav-version">v9.9.9</span>' in text
    assert "../js/site-nav.js?v=9.9.9" in text
    assert "../css/styles.css?v=9.9.9" in text
    assert 'window.GAIA_VERSION = "9.9.9";' in text
    assert bd.build_html_cache_busting(check=True) is False


def test_weekly_report_page_is_cache_busted(bd, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(bd, "ROOT", tmp_path)
    monkeypatch.setattr(bd, "_read_version", lambda: "9.9.9")
    report_dir = tmp_path / "docs" / "reports" / "2026-43"
    report_dir.mkdir(parents=True)
    page = report_dir / "index.html"
    stale = (
        _EN_PAGE.replace(
            "<head>",
            '<head><script>window.GAIA_VERSION = "8.18.2";</script>',
        )
        .replace("../css/", "../../css/")
        .replace("../js/", "../../js/")
    )
    page.write_text(stale, encoding="utf-8")

    assert bd.build_html_cache_busting(check=True) is True
    assert "diff docs/reports/2026-43/index.html" in capsys.readouterr().out
    assert page.read_text(encoding="utf-8") == stale  # check mode never writes

    assert bd.build_html_cache_busting(check=False) is True
    updated = page.read_text(encoding="utf-8")
    assert 'window.GAIA_VERSION = "9.9.9";' in updated
    assert "../../css/styles.css?v=9.9.9" in updated
    assert "../../js/site-nav.js?v=9.9.9" in updated
    assert 'class="nav-version">v9.9.9</span>' in updated
    assert bd.build_html_cache_busting(check=True) is False


def test_stale_nav_version_chip_fails_check(bd, tmp_path, monkeypatch, capsys):
    """A stale version chip alone is drift: check reports it and does not heal it."""
    en_dir = _seed_en_root(bd, tmp_path, monkeypatch)
    stale = (
        "<!doctype html>\n<html>\n<head>\n"
        '  <link rel="stylesheet" href="../css/styles.css?v=9.9.9">\n'
        "</head>\n<body>\n"
        '  <span class="docs-nav-version" id="ver">v8.11.1</span>\n'
        "</body>\n</html>\n"
    )
    page = en_dir / "faq.html"
    page.write_text(stale, encoding="utf-8")

    assert bd.build_html_cache_busting(check=True) is True
    assert "diff docs/en/faq.html" in capsys.readouterr().out
    assert "v8.11.1" in page.read_text(encoding="utf-8")

    assert bd.build_html_cache_busting(check=False) is True
    assert '<span class="docs-nav-version" id="ver">v9.9.9</span>' in page.read_text(encoding="utf-8")


def test_cache_bust_preserves_crlf_line_endings(bd, tmp_path, monkeypatch):
    """CRLF pages stay CRLF: no line-by-line rewrite, no bare-LF injections."""
    en_dir = _seed_en_root(bd, tmp_path, monkeypatch)
    page = en_dir / "crlf.html"
    page.write_bytes(_EN_PAGE.replace("\n", "\r\n").encode("utf-8"))

    assert bd.build_html_cache_busting(check=False) is True

    data = page.read_bytes()
    assert b"\r\n" in data
    assert data.count(b"\n") == data.count(b"\r\n")  # every newline is CRLF
    assert b'window.GAIA_VERSION = "9.9.9";' in data
    assert b'<span class="nav-version">v9.9.9</span>' in data


def test_health_version_only_restamps_version_and_nothing_else(bd, tmp_path, monkeypatch):
    health = tmp_path / "docs" / "api" / "v1" / "health.json"
    health.parent.mkdir(parents=True)
    health.write_text(
        '{\n  "ok": true,\n  "version": "1.0.0",\n  "namedSkillsCount": 7\n}',
        encoding="utf-8",
    )
    monkeypatch.setattr(bd, "ROOT", tmp_path)
    monkeypatch.setattr(bd, "_read_version", lambda: "9.9.9")

    assert bd.build_health_version_only(check=True) is True
    assert '"1.0.0"' in health.read_text(encoding="utf-8")  # check never writes
    assert bd.build_health_version_only(check=False) is True
    assert health.read_text(encoding="utf-8") == (
        '{\n  "ok": true,\n  "version": "9.9.9",\n  "namedSkillsCount": 7\n}'
    )
    assert bd.build_health_version_only(check=False) is False

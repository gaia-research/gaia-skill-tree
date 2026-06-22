"""Tests for the post-write redaction backstop in ``scripts/build_docs.py``.

Pins the Option B behavior added for Issue #807: after the canonical
regenerate-and-replace cycle in ``build_badges()``, both the generator
tempdir and the committed ``docs/badges/`` tree must be free of any
artifact for an entirely-pre-named contributor (every named entry ≤1★).

Mirrors ``scripts/validate_redaction.py`` Section D — the two surfaces
must agree on the redaction invariant.
"""

from __future__ import annotations

import importlib.util
import json
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
def bd(monkeypatch):
    """Load ``build_docs`` and stub ``_prenamed_handles`` with a fixed set."""
    mod = _load()
    fake = {"alpha", "beta"}
    monkeypatch.setattr(mod, "_prenamed_handles", lambda: fake)
    return mod, fake


def _seed(badges: Path, handles: list[str], extras: list[str]) -> None:
    """Materialize a minimal badges/ tree with the given handle dirs + registry."""
    assets = badges / "_assets"
    for h in handles + extras:
        d = assets / h
        d.mkdir(parents=True, exist_ok=True)
        (d / "rank.svg").write_text(f"<svg>{h}</svg>", encoding="utf-8")
    contribs = {h: {"rank": "Awakened"} for h in handles}
    contribs.update({h: {"rank": "named"} for h in extras})
    (badges / "registry.json").write_text(
        json.dumps({"contributors": contribs}, indent=2) + "\n",
        encoding="utf-8",
    )


# ── _committed_redaction_violations() ────────────────────────────────────────

def test_violations_detect_handle_dirs(tmp_path, bd):
    """Pre-named handle directory on disk is flagged."""
    mod, _ = bd
    badges = tmp_path / "badges"
    _seed(badges, handles=["alpha"], extras=["realdev"])
    v = mod._committed_redaction_violations(badges)
    assert "_assets/alpha/" in v
    assert "registry.json[alpha]" in v
    assert not any("realdev" in x for x in v)


def test_violations_clean_tree_returns_empty(tmp_path, bd):
    """A tree with no pre-named entries surfaces no drift."""
    mod, _ = bd
    badges = tmp_path / "badges"
    _seed(badges, handles=[], extras=["realdev", "anotherdev"])
    assert mod._committed_redaction_violations(badges) == []


def test_violations_handles_missing_registry(tmp_path, bd):
    """Missing registry.json still surfaces dir-level drift."""
    mod, _ = bd
    badges = tmp_path / "badges"
    (badges / "_assets" / "alpha").mkdir(parents=True)
    v = mod._committed_redaction_violations(badges)
    assert "_assets/alpha/" in v
    assert not any("registry.json" in x for x in v)


def test_violations_handles_corrupt_registry(tmp_path, bd):
    """A junk registry.json doesn't crash the backstop."""
    mod, _ = bd
    badges = tmp_path / "badges"
    (badges / "_assets" / "alpha").mkdir(parents=True)
    (badges / "registry.json").write_text("not json", encoding="utf-8")
    v = mod._committed_redaction_violations(badges)
    assert "_assets/alpha/" in v


def test_violations_empty_prenamed_returns_empty(tmp_path, monkeypatch):
    """If the helper returns an empty set, the backstop is a no-op."""
    mod = _load()
    monkeypatch.setattr(mod, "_prenamed_handles", lambda: set())
    badges = tmp_path / "badges"
    _seed(badges, handles=["alpha"], extras=["realdev"])
    assert mod._committed_redaction_violations(badges) == []


# ── _apply_redaction_backstop() ──────────────────────────────────────────────

def test_apply_strips_handle_dirs_and_registry(tmp_path, bd):
    """In apply mode (check=False), the backstop removes dirs + registry entries."""
    mod, _ = bd
    badges = tmp_path / "badges"
    _seed(badges, handles=["alpha", "beta"], extras=["realdev"])
    mod._apply_redaction_backstop(badges, check=False)
    assert not (badges / "_assets" / "alpha").exists()
    assert not (badges / "_assets" / "beta").exists()
    assert (badges / "_assets" / "realdev").exists()
    reg = json.loads((badges / "registry.json").read_text())
    assert "alpha" not in reg["contributors"]
    assert "beta" not in reg["contributors"]
    assert "realdev" in reg["contributors"]


def test_apply_check_mode_is_readonly(tmp_path, bd):
    """In check mode, the backstop must NOT mutate the tree."""
    mod, _ = bd
    badges = tmp_path / "badges"
    _seed(badges, handles=["alpha"], extras=["realdev"])
    mod._apply_redaction_backstop(badges, check=True)
    # Both dirs survive — check mode is observation-only.
    assert (badges / "_assets" / "alpha").exists()
    assert (badges / "_assets" / "realdev").exists()
    reg = json.loads((badges / "registry.json").read_text())
    assert "alpha" in reg["contributors"]


def test_apply_is_idempotent(tmp_path, bd):
    """A second apply on a clean tree is a no-op."""
    mod, _ = bd
    badges = tmp_path / "badges"
    _seed(badges, handles=["alpha"], extras=["realdev"])
    mod._apply_redaction_backstop(badges, check=False)
    mod._apply_redaction_backstop(badges, check=False)  # no crash on missing dir
    assert mod._committed_redaction_violations(badges) == []

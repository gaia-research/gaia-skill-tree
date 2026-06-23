"""Guard rails for `gaia_cli.tui.tokens` — the canonical color module.

Three independent invariants:
1. No bare hex literals anywhere in `src/gaia_cli/tui/` outside tokens.py.
2. Tier and rank constants match `registry/gaia.json.meta.*` exactly.
3. Banned CONTEXT.md vocabulary does not appear in TUI identifiers or
   user-facing strings.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
pytestmark = [pytest.mark.integration]



REPO_ROOT = Path(__file__).resolve().parent.parent
TUI_DIR = REPO_ROOT / "src" / "gaia_cli" / "tui"
TOKENS_PATH = TUI_DIR / "tokens.py"
REGISTRY = REPO_ROOT / "registry" / "gaia.json"

_HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")


def _walk_tui_files() -> list[Path]:
    paths: list[Path] = []
    for root, _, files in os.walk(TUI_DIR):
        for f in files:
            if f.endswith((".py", ".tcss")):
                paths.append(Path(root) / f)
    return paths


def test_no_stray_hex_outside_tokens():
    offenders: list[tuple[Path, int, str]] = []
    for path in _walk_tui_files():
        if path == TOKENS_PATH:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in _HEX_RE.finditer(line):
                offenders.append((path, lineno, line.strip()))
                break
    assert not offenders, (
        "Bare hex literals must live only in tokens.py. Offenders:\n"
        + "\n".join(f"  {p.relative_to(REPO_ROOT)}:{n} -> {ln}" for p, n, ln in offenders)
    )


def test_tier_tokens_match_registry():
    from gaia_cli.tui import tokens

    meta = json.loads(REGISTRY.read_text(encoding="utf-8")).get("meta", {})
    type_colors = meta.get("typeColors", {})

    for tier in ("basic", "extra", "unique", "ultimate"):
        entry = type_colors.get(tier) or {}
        expected = entry.get("hex")
        if not expected:
            continue
        actual = tokens.TIER_BY_KEY[tier]
        assert actual == expected, (
            f"TIER_BY_KEY['{tier}'] = {actual} but registry says {expected}"
        )


def test_rank_tokens_match_registry():
    from gaia_cli.tui import tokens

    meta = json.loads(REGISTRY.read_text(encoding="utf-8")).get("meta", {})
    level_colors = meta.get("levelColors", {})

    for star in ("0★", "1★", "2★", "3★", "4★", "5★", "6★"):
        entry = level_colors.get(star) or {}
        expected = entry.get("hex")
        if not expected:
            continue
        actual = tokens.RANK_BY_STAR[star]
        assert actual == expected, (
            f"RANK_BY_STAR['{star}'] = {actual} but registry says {expected}"
        )


def test_brand_tokens_are_restricted():
    from gaia_cli.tui import tokens

    assert tokens.BRAND_HONOR_RED == "#ef4444"
    assert tokens.BRAND_APEX_GOLD == "#fbbf24"


def test_textual_variables_complete():
    from gaia_cli.tui import tokens

    vars_ = tokens.textual_variables()
    for key in (
        "gaia-bg", "gaia-surface", "gaia-border", "gaia-text", "gaia-muted",
        "gaia-tier-basic", "gaia-tier-extra", "gaia-tier-unique", "gaia-tier-ultimate",
        "gaia-honor-red", "gaia-apex-gold",
    ):
        assert key in vars_, f"textual_variables() missing '{key}'"
        assert vars_[key].startswith("#"), f"variable '{key}' is not a hex string: {vars_[key]}"


@pytest.mark.parametrize("banned", ["legendary", "database", "catalog"])
def test_banned_vocabulary_absent_from_tui(banned: str):
    """CONTEXT.md prohibits these in user-facing copy; check TUI identifiers
    and string literals don't smuggle them in.

    'card' is allowed in Textual class names (Static, etc.) so we don't
    enforce it here — covered by separate review.
    """
    pattern = re.compile(rf"\b{banned}\b", re.IGNORECASE)
    offenders: list[tuple[Path, int, str]] = []
    for path in _walk_tui_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                offenders.append((path, lineno, line.strip()))
    assert not offenders, (
        f"Banned word '{banned}' found in TUI:\n"
        + "\n".join(f"  {p.relative_to(REPO_ROOT)}:{n} -> {ln}" for p, n, ln in offenders)
    )


def test_app_wires_css_variables():
    from gaia_cli.tui.app import GaiaApp
    from gaia_cli.tui import tokens

    app = GaiaApp()
    # Subset check — App may add more from its own theme
    expected = tokens.textual_variables()
    actual = app.get_css_variables()
    for key, value in expected.items():
        assert actual.get(key) == value, (
            f"get_css_variables() missing/wrong for {key}: got {actual.get(key)}, want {value}"
        )

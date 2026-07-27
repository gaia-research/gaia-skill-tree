"""Canonical color tokens for the Gaia TUI.

Single source of truth: `registry/gaia.json.meta.{typeColors,levelColors}`.
This module mirrors `scripts/generateCssTokens.py` for the Python TUI side,
so the web CSS and the terminal palette can never drift.

Vocabulary tracks CONTEXT.md § Taxonomy v6 (Yggdrasil II) exactly:
- Type axis (structural): Basic / Fusion
- Branch axis (derived, named-only): standard / suite / unique
- Rank words (0★ → 6★):
    shared  0-3  Basic / Awakened / Named / Evolved
    suite   4-6  Extra / Ultimate / Apex
    unique  4-6  Unique / Unique Ultimate / Unique Impossible
- Brand: Honor Red (contributor handles only),
         Apex Gold (6★ / Apex / Diamond Seal only — never decorative)

These names are the load-bearing contract every TUI screen reads. Branch/rank
DECISIONS are never made here or in a screen — they route through
`gaia_cli.taxonomy` (build + read only). This module only maps a resolved
branch word or star to a color/glyph token.

NEVER hardcode a hex anywhere else in `src/gaia_cli/tui/`. Import from here.
"""

from __future__ import annotations

import json
import os
from typing import Final


from gaia_cli.registry import resolve_registry_path


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    h = value.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _load_meta() -> dict:
    # Use centralized resolution to find gaia.json
    root = resolve_registry_path()
    path = os.path.join(root, "registry", "gaia.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh).get("meta", {})
    except Exception:
        return {}


_META = _load_meta()
_TYPE_COLORS = _META.get("typeColors", {})
_LEVEL_COLORS = _META.get("levelColors", {})


def _accent_hex(key: str, fallback: str) -> str:
    entry = _TYPE_COLORS.get(key) or {}
    return entry.get("hex", fallback)


def _rank_hex(star: str, fallback: str) -> str:
    entry = _LEVEL_COLORS.get(star) or {}
    return entry.get("hex", fallback)


# ── Neutrals (DESIGN.md "Color Palette") ─────────────────────────────────────

NEUTRAL_BG:             Final[str] = "#030712"
NEUTRAL_SURFACE:        Final[str] = "#0f172a"
NEUTRAL_BORDER:         Final[str] = "#1e293b"
NEUTRAL_BORDER_STRONG:  Final[str] = "#334155"
NEUTRAL_TEXT:           Final[str] = "#e2e8f0"
NEUTRAL_TEXT_MUTED:     Final[str] = "#64748b"
NEUTRAL_TEXT_DIM:       Final[str] = "#475569"

# ── Palette anchors (raw registry-backed hues) ───────────────────────────────
#
# These are bare COLOR VALUES, not taxonomy words — the four hues the branch and
# rank ramps are built from. `meta.typeColors` post-Yggdrasil II carries only
# {basic, fusion}, so the three non-basic anchors read their hardcoded
# fallbacks. Consumers should reference the semantic BRANCH_ACCENT / RANK_*
# tokens below, not these anchors directly.
ACCENT_SKY:      Final[str] = _accent_hex("basic",    "#38bdf8")  # base / standard
ACCENT_VIOLET:   Final[str] = _accent_hex("extra",    "#c084fc")  # mid ramp
ACCENT_AMETHYST: Final[str] = _accent_hex("unique",   "#7c3aed")  # unique branch
ACCENT_AMBER:    Final[str] = _accent_hex("ultimate", "#f59e0b")  # suite branch

# ── Branch accents (Ygg II: keyed on the derived branch word) ────────────────
#
# The named-skill BRANCH axis (standard | suite | unique) is the display axis.
# These lookups are keyed on the branch words that taxonomy.branchFor() emits;
# the suite pinnacle is amber (→ Apex gold at 6★), unique is amethyst, standard
# is the base sky accent. A screen READS this map with a resolved branch word —
# it never derives the branch itself.
BRANCH_ACCENT: Final[dict[str, str]] = {
    "standard": ACCENT_SKY,
    "suite":    ACCENT_AMBER,
    "unique":   ACCENT_AMETHYST,
}

BRANCH_GLYPH: Final[dict[str, str]] = {
    "standard": "○",
    "suite":    "◆",
    "unique":   "◉",
}

# ── Rank ramp (CONTEXT.md § Taxonomy v6 rank words, 0★ → 6★) ─────────────────
#
# The rank ladder forks at 4★ (decoration split): 0-3 are shared; 4-6 carry the
# suite ladder words (Extra / Ultimate / Apex). The Unique-branch 4-6 ranks
# (Unique / Unique Ultimate / Unique Impossible) reuse these same hues by star,
# so the aliases below point at the shared per-star color. `medallion()` /
# `rankWord()` in taxonomy.py decide which word a star renders as — this map is
# color only.
RANK_UNAWAKENED: Final[str] = _rank_hex("0★", "#94a3b8")
RANK_AWAKENED:   Final[str] = _rank_hex("1★", "#38bdf8")
RANK_NAMED:      Final[str] = _rank_hex("2★", "#63cab7")
RANK_EVOLVED:    Final[str] = _rank_hex("3★", "#a78bfa")
RANK_EXTRA:      Final[str] = _rank_hex("4★", "#e879f9")  # 4★ Extra (suite) / Unique
RANK_ULTIMATE:   Final[str] = _rank_hex("5★", "#fbbf24")  # 5★ Ultimate / Unique Ultimate
RANK_APEX:       Final[str] = _rank_hex("6★", "#fbbf24")  # 6★ Apex / Unique Impossible

RAMP_RANK: Final[tuple[str, ...]] = (
    RANK_UNAWAKENED,
    RANK_AWAKENED,
    RANK_NAMED,
    RANK_EVOLVED,
    RANK_EXTRA,
    RANK_ULTIMATE,
    RANK_APEX,
)

RANK_BY_STAR: Final[dict[str, str]] = {
    "0★": RANK_UNAWAKENED,
    "1★": RANK_AWAKENED,
    "2★": RANK_NAMED,
    "3★": RANK_EVOLVED,
    "4★": RANK_EXTRA,
    "5★": RANK_ULTIMATE,
    "6★": RANK_APEX,
}

# ── Brand tokens (restricted use — see CONTEXT.md) ───────────────────────────

BRAND_HONOR_RED: Final[str] = "#ef4444"
BRAND_APEX_GOLD: Final[str] = "#fbbf24"

# ── Functional state tokens ──────────────────────────────────────────────────

STATE_OWNED:                 Final[str] = "#22c55e"
STATE_DETECTED:              Final[str] = ACCENT_SKY
STATE_INSTALL_ACTION:        Final[str] = "#15803d"
STATE_INSTALL_ACTION_HOVER:  Final[str] = "#16a34a"
STATE_INSTALL_ERROR:         Final[str] = "#f85149"
STATE_SCAN_COMPLETE:         Final[str] = STATE_OWNED

# ── Animation cycles (DESIGN.md "Skill color cycling") ───────────────────────

# Apex 6-stop cycle: sky → violet → amber → red → violet → green
CYCLE_APEX: Final[tuple[str, ...]] = (
    ACCENT_SKY,
    RANK_EVOLVED,
    ACCENT_AMBER,
    BRAND_HONOR_RED,
    ACCENT_VIOLET,
    "#34d399",
)


def as_rgb(token: str) -> tuple[int, int, int]:
    """Return an ``(r, g, b)`` triple for a token hex (for ANSI parity)."""
    return _hex_to_rgb(token)


def textual_variables() -> dict[str, str]:
    """Map Textual CSS variable names → hex values.

    Consumed by :meth:`GaiaApp.get_css_variables`. Names mirror the short
    aliases used in ``docs/css/tokens.css`` so contributors switching
    between web and TUI see the same vocabulary.
    """
    return {
        "gaia-bg":             NEUTRAL_BG,
        "gaia-surface":        NEUTRAL_SURFACE,
        "gaia-border":         NEUTRAL_BORDER,
        "gaia-border-strong":  NEUTRAL_BORDER_STRONG,
        "gaia-text":           NEUTRAL_TEXT,
        "gaia-muted":          NEUTRAL_TEXT_MUTED,
        "gaia-dim":            NEUTRAL_TEXT_DIM,
        "gaia-branch-standard": BRANCH_ACCENT["standard"],
        "gaia-branch-suite":    BRANCH_ACCENT["suite"],
        "gaia-branch-unique":   BRANCH_ACCENT["unique"],
        "gaia-honor-red":      BRAND_HONOR_RED,
        "gaia-apex-gold":      BRAND_APEX_GOLD,
        "gaia-install-action": STATE_INSTALL_ACTION,
        "gaia-install-hover":  STATE_INSTALL_ACTION_HOVER,
        "gaia-owned":          STATE_OWNED,
    }

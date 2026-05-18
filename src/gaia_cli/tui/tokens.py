"""Canonical color tokens for the Gaia TUI.

Single source of truth: `registry/gaia.json.meta.{typeColors,levelColors}`.
This module mirrors `scripts/generateCssTokens.py` for the Python TUI side,
so the web CSS and the terminal palette can never drift.

Vocabulary tracks CONTEXT.md exactly:
- Tiers: Basic / Extra / Unique / Ultimate
- Ranks (0★ → 6★): Unawakened / Awakened / Named / Evolved /
                    Hardened / Transcendent / Transcendent ★
- Brand: Honor Red (contributor handles only),
         Apex Gold (6★ / Ultimate / Diamond Seal only — never decorative)

NEVER hardcode a hex anywhere else in `src/gaia_cli/tui/`. Import from here.
"""

from __future__ import annotations

import json
import os
from typing import Final


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    h = value.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _load_meta() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    path = os.path.join(root, "registry", "gaia.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh).get("meta", {})
    except Exception:
        return {}


_META = _load_meta()
_TYPE_COLORS = _META.get("typeColors", {})
_LEVEL_COLORS = _META.get("levelColors", {})


def _tier_hex(key: str, fallback: str) -> str:
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

# ── Tier accents (registry-backed) ───────────────────────────────────────────

TIER_BASIC:    Final[str] = _tier_hex("basic",    "#38bdf8")
TIER_EXTRA:    Final[str] = _tier_hex("extra",    "#c084fc")
TIER_UNIQUE:   Final[str] = _tier_hex("unique",   "#7c3aed")
TIER_ULTIMATE: Final[str] = _tier_hex("ultimate", "#f59e0b")

TIER_BY_KEY: Final[dict[str, str]] = {
    "basic":    TIER_BASIC,
    "extra":    TIER_EXTRA,
    "unique":   TIER_UNIQUE,
    "ultimate": TIER_ULTIMATE,
}

GLYPH_BY_TIER: Final[dict[str, str]] = {
    "basic":    "○",
    "extra":    "◇",
    "unique":   "◉",
    "ultimate": "◆",
}

# ── Rank ramp (CONTEXT.md rank names, 0★ → 6★) ───────────────────────────────

RANK_UNAWAKENED:        Final[str] = _rank_hex("0★", "#94a3b8")
RANK_AWAKENED:          Final[str] = _rank_hex("1★", "#38bdf8")
RANK_NAMED:             Final[str] = _rank_hex("2★", "#63cab7")
RANK_EVOLVED:           Final[str] = _rank_hex("3★", "#a78bfa")
RANK_HARDENED:          Final[str] = _rank_hex("4★", "#e879f9")
RANK_TRANSCENDENT:      Final[str] = _rank_hex("5★", "#fbbf24")
RANK_TRANSCENDENT_APEX: Final[str] = _rank_hex("6★", "#fbbf24")

RAMP_RANK: Final[tuple[str, ...]] = (
    RANK_UNAWAKENED,
    RANK_AWAKENED,
    RANK_NAMED,
    RANK_EVOLVED,
    RANK_HARDENED,
    RANK_TRANSCENDENT,
    RANK_TRANSCENDENT_APEX,
)

RANK_BY_STAR: Final[dict[str, str]] = {
    "0★": RANK_UNAWAKENED,
    "1★": RANK_AWAKENED,
    "2★": RANK_NAMED,
    "3★": RANK_EVOLVED,
    "4★": RANK_HARDENED,
    "5★": RANK_TRANSCENDENT,
    "6★": RANK_TRANSCENDENT_APEX,
}

# ── Brand tokens (restricted use — see CONTEXT.md) ───────────────────────────

BRAND_HONOR_RED: Final[str] = "#ef4444"
BRAND_APEX_GOLD: Final[str] = "#fbbf24"

# ── Functional state tokens ──────────────────────────────────────────────────

STATE_OWNED:                 Final[str] = "#22c55e"
STATE_DETECTED:              Final[str] = TIER_BASIC
STATE_INSTALL_ACTION:        Final[str] = "#15803d"
STATE_INSTALL_ACTION_HOVER:  Final[str] = "#16a34a"
STATE_INSTALL_ERROR:         Final[str] = "#f85149"
STATE_SCAN_COMPLETE:         Final[str] = STATE_OWNED

# ── Animation cycles (DESIGN.md "Skill type color cycling") ──────────────────

# Ultimate 6-stop cycle: blue → violet → gold → red → purple → green
CYCLE_ULTIMATE: Final[tuple[str, ...]] = (
    TIER_BASIC,
    RANK_EVOLVED,
    TIER_ULTIMATE,
    BRAND_HONOR_RED,
    TIER_EXTRA,
    "#34d399",
)

# Extra 5-stop cycle (no gold — Extras never glow apex)
CYCLE_EXTRA: Final[tuple[str, ...]] = (
    TIER_BASIC,
    RANK_EVOLVED,
    BRAND_HONOR_RED,
    TIER_EXTRA,
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
        "gaia-tier-basic":     TIER_BASIC,
        "gaia-tier-extra":     TIER_EXTRA,
        "gaia-tier-unique":    TIER_UNIQUE,
        "gaia-tier-ultimate":  TIER_ULTIMATE,
        "gaia-honor-red":      BRAND_HONOR_RED,
        "gaia-apex-gold":      BRAND_APEX_GOLD,
        "gaia-install-action": STATE_INSTALL_ACTION,
        "gaia-install-hover":  STATE_INSTALL_ACTION_HOVER,
        "gaia-owned":          STATE_OWNED,
    }

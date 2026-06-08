"""Centralized display formatting for skill identifiers.

Implements the three-tier slash-naming hierarchy with ANSI coloring.
"""

# Brand color choke point — keep canonical role tokens centralised here:
#   - Honor Red  (#ef4444) → COLOR_CONTRIBUTOR — Origin Contributor handles
#   - Apex Gold  (#fbbf24) → 6★ Transcendent ★ accent, sourced via RANK_COLORS
# See CONTEXT.md "Brand-color roles" and PRODUCT.md "Brand Personality".

from __future__ import annotations
import json
import os
import sys


from gaia_cli.registry import resolve_registry_path


# --- ANSI helpers (minimal, reuses pattern from cardRenderer) ---

def _use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    # Support explicit force flags (standard in many CLIs)
    if os.environ.get("FORCE_COLOR") or os.environ.get("CLICOLOR_FORCE"):
        return True
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


def _fg(r: int, g: int, b: int) -> str:
    if not _use_color():
        return ""
    colorterm = os.environ.get("COLORTERM", "")
    if colorterm in ("truecolor", "24bit"):
        return f"\033[38;2;{r};{g};{b}m"
    index = 16 + (36 * (r // 51)) + (6 * (g // 51)) + (b // 51)
    return f"\033[38;5;{index}m"


def _reset() -> str:
    return "\033[0m" if _use_color() else ""


def _bold() -> str:
    return "\033[1m" if _use_color() else ""


# --- Color palettes (single source of truth: registry/gaia.json meta) ---

def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _load_palette_from_registry() -> tuple[dict, dict]:
    """Parse TIER_COLORS and RANK_COLORS from gaia.json at module load."""
    _fallback_tier = {
        "basic": (56, 189, 248),
        "extra": (192, 132, 252),
        "unique": (124, 58, 237),
        "ultimate": (245, 158, 11),
    }
    _fallback_rank = {
        "0★": (148, 163, 184),
        "1★": (56, 189, 248),
        "2★": (99, 202, 183),
        "3★": (167, 139, 250),
        "4★": (232, 121, 249),
        "5★": (251, 191, 36),
        "6★": (251, 191, 36),
    }
    try:
        _root = resolve_registry_path()
        _path = os.path.join(_root, "registry", "gaia.json")
        with open(_path, "r", encoding="utf-8") as _f:
            _data = json.load(_f)
        _meta = _data.get("meta", {})
        tier_colors = {
            k: _hex_to_rgb(v["hex"])
            for k, v in _meta.get("typeColors", {}).items()
            if "hex" in v
        } or _fallback_tier
        rank_colors = {
            k: _hex_to_rgb(v["hex"])
            for k, v in _meta.get("levelColors", {}).items()
            if "hex" in v
        } or _fallback_rank
        return tier_colors, rank_colors
    except Exception:
        return _fallback_tier, _fallback_rank


TIER_COLORS, RANK_COLORS = _load_palette_from_registry()

TYPE_SYMBOLS = {"basic": "○", "extra": "◇", "unique": "◉", "ultimate": "◆"}

COLOR_CONTRIBUTOR = (239, 68, 68)      # #ef4444 -- red for named contributors
COLOR_LOCAL_USER  = (134, 239, 172)    # #86efac -- bright green for local/user skills

# Redaction policy lives in the single source of truth: gaia_cli.redaction.
# Re-exported here so existing importers of formatting keep working.
from gaia_cli.redaction import (  # noqa: E402
    COLOR_REDACTED,
    REDACTED_BLOCK,
    is_redacted,
    level_num as _level_num,
)


# --- Public formatting API ---

def _split_named_ref(named_ref: str, local_user: str | None) -> tuple[str, str, bool]:
    """Split 'contributor/nickname' into (contributor, nickname, is_own)."""
    if "/" in named_ref:
        contrib, nickname = named_ref.split("/", 1)
        return contrib, nickname, bool(local_user and contrib == local_user)
    return "", named_ref.lstrip("/"), False


def format_skill_plain(skill_id: str, *, named_ref: str | None = None,
                       named_contributor: str | None = None,
                       is_local: bool = False, local_user: str | None = None,
                       level: str | None = None) -> str:
    """Return plain display string without ANSI codes.

    Prefer named_ref ('contributor/nickname') over the legacy named_contributor param.
    When ``level`` is provided and ≤ 1★, the contributor segment is replaced with
    the redaction block (████████) — the skill slug is preserved.
    """
    if named_ref:
        contrib, nickname, is_own = _split_named_ref(named_ref, local_user)
        if is_own:
            return f"/{nickname}"
        if level is not None and is_redacted(level):
            contrib = REDACTED_BLOCK
        return f"{contrib}/{nickname}" if contrib else f"/{nickname}"
    if named_contributor:
        if level is not None and is_redacted(level):
            named_contributor = REDACTED_BLOCK
        return f"{named_contributor}/{skill_id}"
    return f"/{skill_id}"


def format_skill_colored(skill_id: str, level: str = "0★", *,
                         named_ref: str | None = None,
                         named_contributor: str | None = None,
                         is_local: bool = False, local_user: str | None = None) -> str:
    """Return ANSI-colored display string.

    - Own named (named_ref, contrib == local_user): GREEN /contributor/nickname
    - Other named: RED contributor / rank-colored nickname (SLATE for ≤1★)
    - Local novel: GREEN /skill-id
    - Canon: rank-colored /skill-id
    """
    r = _reset()
    rank_color = RANK_COLORS.get(level, RANK_COLORS["0★"])

    if named_ref:
        contrib, nickname, is_own = _split_named_ref(named_ref, local_user)
        handle_color = COLOR_LOCAL_USER if is_own else COLOR_CONTRIBUTOR
        nick_colored = f"{_fg(*rank_color)}{nickname}{r}"
        if contrib:
            if not is_own and is_redacted(level):
                # Pre-named: replace honor-red handle with slate redaction block
                return f"{_fg(*COLOR_REDACTED)}/{REDACTED_BLOCK}{r}/{nick_colored}"
            return f"{_fg(*handle_color)}/{contrib}{r}/{nick_colored}"
        return f"{_fg(*handle_color)}/{nickname}{r}"

    if named_contributor:
        handle_color = COLOR_LOCAL_USER if local_user and named_contributor == local_user else COLOR_CONTRIBUTOR
        if not (local_user and named_contributor == local_user) and is_redacted(level):
            contrib_colored = f"{_fg(*COLOR_REDACTED)}{REDACTED_BLOCK}{r}"
        else:
            contrib_colored = f"{_fg(*handle_color)}{named_contributor}{r}"
        skill_colored = f"{_fg(*rank_color)}{skill_id}{r}"
        return f"{_fg(*handle_color)}/{r}{contrib_colored}/{skill_colored}"
    if is_local:
        return f"{_fg(*COLOR_LOCAL_USER)}/{skill_id}{r}"
    return f"{_fg(*rank_color)}/{skill_id}{r}"


def format_type_label(skill_type: str) -> str:
    """Return type glyph + label like '○ Basic Skill'."""
    labels = {"basic": "Basic Skill", "extra": "Extra Skill", "unique": "Unique Skill", "ultimate": "Ultimate Skill"}
    symbol = TYPE_SYMBOLS.get(skill_type, "?")
    label = labels.get(skill_type, skill_type)
    return f"{symbol} {label}"


def format_type_colored(skill_type: str) -> str:
    """Return colored type glyph + label."""
    raw = format_type_label(skill_type)
    color = TIER_COLORS.get(skill_type, (148, 163, 184))
    return f"{_fg(*color)}{raw}{_reset()}"


def format_level_colored(level: str) -> str:
    """Return level badge colored by rank."""
    rank_color = RANK_COLORS.get(level, RANK_COLORS["0★"])
    return f"{_fg(*rank_color)}{level}{_reset()}"


def fusion_equation(prereqs: list[str], result: str, result_glyph: str = "◇") -> str:
    """Plain text fusion equation: /a + /b -> /result glyph"""
    parts = " + ".join(f"/{p}" for p in prereqs)
    return f"{parts} → /{result} {result_glyph}"

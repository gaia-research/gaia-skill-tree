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


def _bg(r: int, g: int, b: int) -> str:
    if not _use_color():
        return ""
    colorterm = os.environ.get("COLORTERM", "")
    if colorterm in ("truecolor", "24bit"):
        return f"\033[48;2;{r};{g};{b}m"
    index = 16 + (36 * (r // 51)) + (6 * (g // 51)) + (b // 51)
    return f"\033[48;5;{index}m"


def _reset() -> str:
    return "\033[0m" if _use_color() else ""


def _bold() -> str:
    return "\033[1m" if _use_color() else ""


_RAINBOW_STOPS = [
    (56, 189, 248),
    (167, 139, 250),
    (245, 158, 11),
    (239, 68, 68),
    (192, 132, 252),
    (52, 211, 153)
]


def _rainbow_text(text: str) -> str:
    if not _use_color() or not text:
        return text
    n = len(text)
    if n <= 1:
        return _fg(*_RAINBOW_STOPS[0]) + text + _reset()

    parts = []
    num_stops = len(_RAINBOW_STOPS)
    for i, ch in enumerate(text):
        pos = (i / (n - 1)) * (num_stops - 1)
        idx = int(pos)
        frac = pos - idx
        if idx >= num_stops - 1:
            color = _RAINBOW_STOPS[-1]
        else:
            c1 = _RAINBOW_STOPS[idx]
            c2 = _RAINBOW_STOPS[idx + 1]
            r = int(c1[0] + frac * (c2[0] - c1[0]))
            g = int(c1[1] + frac * (c2[1] - c1[1]))
            b = int(c1[2] + frac * (c2[2] - c1[2]))
            color = (r, g, b)
        parts.append(_fg(*color) + ch)
    return "".join(parts) + _reset()


# --- Color palettes (single source of truth: registry/gaia.json meta) ---

def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _load_palette_from_registry() -> tuple[dict, dict]:
    """Parse TIER_COLORS and RANK_COLORS from gaia.json at module load."""
    _fallback_tier = {
        # Yggdrasil II collapsed the type axis to {basic, fusion}. Mirrors
        # meta.json types.colors so the fallback matches the registry palette.
        "basic": (56, 189, 248),
        "fusion": (245, 158, 11),
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


def _load_types_from_meta() -> tuple[dict, dict]:
    """Load the canonical type labels + symbols from registry/schema/meta.json.

    Single source of truth for the Yggdrasil II {basic, fusion} type axis. The
    schema meta block (`types.labels`, `types.symbols`) is authoritative; the
    hard-coded fallback mirrors it so the CLI still renders if meta.json is
    unreadable in a stripped install.
    """
    _fallback_symbols = {"basic": "○", "fusion": "◆"}
    _fallback_labels = {"basic": "Basic", "fusion": "Fusion"}
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "registry", "schema", "meta.json"),
        os.path.join(os.path.dirname(__file__), "data", "registry", "schema", "meta.json"),
    ]
    for p in candidates:
        resolved = os.path.normpath(p)
        if not os.path.isfile(resolved):
            continue
        try:
            with open(resolved, "r", encoding="utf-8") as f:
                types = json.load(f).get("types", {})
            symbols = dict(types.get("symbols") or {}) or _fallback_symbols
            labels = dict(types.get("labels") or {}) or _fallback_labels
            return symbols, labels
        except Exception:
            break
    return _fallback_symbols, _fallback_labels


# Type glyphs + labels — single source of truth: meta.json `types` block.
# Yggdrasil II collapsed the type axis to {basic, fusion}; type words stand
# bare ("Basic", "Fusion") with NO "Skill" suffix (that suffix is a rank-word
# convention — see check_rank_vocabulary.py).
TYPE_SYMBOLS, TYPE_LABELS = _load_types_from_meta()


def _load_level_labels_from_meta() -> dict:
    """Load the Suite/shared rank labels from registry/schema/meta.json.

    meta.json `levels.labels` holds the Suite-branch (and 1-3★ shared) defaults:
    0★ Basic · 1★ Awakened · 2★ Named · 3★ Evolved · 4★ Extra · 5★ Ultimate ·
    6★ Apex. The Unique-branch alternates are rendered in code (below), not stored
    in meta.
    """
    _fallback = {
        "0★": "Basic", "1★": "Awakened", "2★": "Named", "3★": "Evolved",
        "4★": "Extra", "5★": "Ultimate", "6★": "Apex",
    }
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "registry", "schema", "meta.json"),
        os.path.join(os.path.dirname(__file__), "data", "registry", "schema", "meta.json"),
    ]
    for p in candidates:
        resolved = os.path.normpath(p)
        if not os.path.isfile(resolved):
            continue
        try:
            with open(resolved, "r", encoding="utf-8") as f:
                labels = json.load(f).get("levels", {}).get("labels") or {}
            return dict(labels) or _fallback
        except Exception:
            break
    return _fallback


# Suite / shared rank labels (meta.json defaults) and the Unique-branch alternates.
# Yggdrasil II v2 ladders (fork at 4★+):
#   Suite : 4★ Extra  · 5★ Ultimate         · 6★ Apex
#   Unique: 4★ Unique · 5★ Unique Ultimate  · 6★ Unique Impossible
# 1★-3★ are the shared ladder (no branch distinction).
LEVEL_LABELS_SUITE = _load_level_labels_from_meta()
LEVEL_LABELS_UNIQUE = {
    "4★": "Unique",
    "5★": "Unique Ultimate",
    "6★": "Unique Impossible",
}

# Distinct dark-violet accent for the Unique branch ("standing stones beside the
# tree" — design-v6.1.1 §2.2). Only the 4★-6★ fork carries a distinct color;
# 1★-3★ share the standard rank ramp.
RANK_COLORS_UNIQUE = {
    "4★": (139, 92, 246),   # #8b5cf6 violet
    "5★": (124, 58, 237),   # #7c3aed deep violet
    "6★": (109, 40, 217),   # #6d28d9 darkest violet (Impossible)
}

# Evidence Grade colors — single source of truth for grade design tokens.
# Platinum (S) / Gold (A) / Silver (B) / Bronze (C)
GRADE_COLORS: dict[str, tuple[int, int, int]] = {
    "S": (226, 232, 240),   # Platinum — #e2e8f0
    "A": (251, 191, 36),    # Gold     — #fbbf24
    "B": (148, 163, 184),   # Silver   — #94a3b8
    "C": (180, 83, 9),      # Bronze   — #b45309
}

COLOR_CONTRIBUTOR = (239, 68, 68)      # #ef4444 -- red for named contributors
COLOR_LOCAL_USER  = (134, 239, 172)    # #86efac -- bright green for local/user skills
COLOR_GREY        = (148, 163, 184)    # #94a3b8 -- slate grey for dev commands
COLOR_FUSION      = (192, 132, 252)    # #c084fc -- fuse purple

# Harness/Environment brand colors
HARNESS_COLORS = {
    "claude": (249, 115, 22),       # Orange
    "cursor": (0, 163, 255),        # Blue
    "windsurf": (0, 122, 255),      # Blue
    "gemini": (71, 140, 255),       # Gemini Blue
    "codex": (16, 163, 127),        # OpenAI Green
    "copilot": (0, 90, 255),        # GitHub Blue
    "antigravity": (192, 132, 252), # Purple
    "agents": (134, 239, 172),      # Green (Local User)
}


def get_harness_color(path: str) -> tuple[int, int, int]:
    """Return the brand color for a given scan path based on detected harness."""
    p_lower = path.lower()
    if ".claude" in p_lower:
        return HARNESS_COLORS["claude"]
    if ".cursor" in p_lower:
        return HARNESS_COLORS["cursor"]
    if ".windsurf" in p_lower:
        return HARNESS_COLORS["windsurf"]
    if ".gemini" in p_lower:
        return HARNESS_COLORS["gemini"]
    if ".antigravity" in p_lower:
        return HARNESS_COLORS["antigravity"]
    if "codex" in p_lower:
        return HARNESS_COLORS["codex"]
    if "copilot" in p_lower:
        return HARNESS_COLORS["copilot"]
    if ".agents" in p_lower or "agents" in p_lower:
        return HARNESS_COLORS["agents"]
    return COLOR_GREY

# Redaction policy lives in the single source of truth: gaia_cli.redaction.
# Re-exported here so existing importers of formatting keep working.
from gaia_cli.redaction import (  # noqa: E402
    COLOR_REDACTED,
    REDACTED_BLOCK,
    is_redacted,
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
        if contrib:
            if not is_own and level is not None and is_redacted(level):
                contrib = REDACTED_BLOCK
            return f"{contrib}/{nickname}"
        return f"/{nickname}"
    if named_contributor:
        if level is not None and not (local_user and named_contributor == local_user) and is_redacted(level):
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
                return f"{_fg(*COLOR_REDACTED)}{REDACTED_BLOCK}{r}/{nick_colored}"
            return f"{_fg(*handle_color)}{contrib}{r}/{nick_colored}"
        return f"{_fg(*handle_color)}/{nickname}{r}"

    if named_contributor:
        handle_color = COLOR_LOCAL_USER if local_user and named_contributor == local_user else COLOR_CONTRIBUTOR
        if not (local_user and named_contributor == local_user) and is_redacted(level):
            contrib_colored = f"{_fg(*COLOR_REDACTED)}{REDACTED_BLOCK}{r}"
        else:
            contrib_colored = f"{_fg(*handle_color)}{named_contributor}{r}"
        skill_colored = f"{_fg(*rank_color)}{skill_id}{r}"
        return f"{_fg(*handle_color)}{r}{contrib_colored}/{skill_colored}"
    if is_local:
        return f"{_fg(*COLOR_LOCAL_USER)}/{skill_id}{r}"
    return f"{_fg(*rank_color)}/{skill_id}{r}"


def format_type_label(skill_type: str) -> str:
    """Return type glyph + label like '○ Basic'.

    Yggdrasil II: type words stand bare (no "Skill" suffix). Labels + glyphs are
    sourced from meta.json via TYPE_LABELS / TYPE_SYMBOLS (single source).
    """
    symbol = TYPE_SYMBOLS.get(skill_type, "?")
    label = TYPE_LABELS.get(skill_type, skill_type.capitalize())
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


def rank_word(level: str, branch: str = "suite") -> str:
    """DEPRECATED shim — delegates to taxonomy.rankWord (the canonical authority).

    Retained for backward-compat callers; will be deleted in PR3b once all
    consumers are migrated onto taxonomy.rankWord directly.
    """
    from gaia_cli.taxonomy import rankWord
    return rankWord(level, branch)


def format_rank_label(level: str, branch: str = "suite") -> str:
    """Return the full branch-aware rank label, e.g. '4★ Extra' or '4★ Unique'.

    Delegates to taxonomy.rankWord (single source of truth for rank vocabulary).
    """
    from gaia_cli.taxonomy import rankWord
    word = rankWord(level, branch)
    return f"{level} {word}" if word else level


def rank_color_for(level: str, branch: str = "suite") -> tuple[int, int, int]:
    """Return the RGB for a (level, branch) pair.

    The Unique branch (4★+) uses the distinct dark-violet accent; every other
    case falls back to the standard rank ramp (RANK_COLORS).
    """
    if branch == "unique" and level in RANK_COLORS_UNIQUE:
        return RANK_COLORS_UNIQUE[level]
    return RANK_COLORS.get(level, RANK_COLORS["0★"])


def rank_hex(rank: str) -> str:
    """Return '#rrggbb' for a given rank string, sourced from RANK_COLORS."""
    r, g, b = RANK_COLORS.get(rank, RANK_COLORS.get("0★", (148, 163, 184)))
    return f"#{r:02x}{g:02x}{b:02x}"


def tier_hex(skill_type: str) -> str:
    """Return '#rrggbb' for a skill type, sourced from TIER_COLORS (registry meta.typeColors)."""
    r, g, b = TIER_COLORS.get(skill_type, TIER_COLORS.get("basic", (56, 189, 248)))
    return f"#{r:02x}{g:02x}{b:02x}"


def fusion_equation(prereqs: list[str], result: str, result_glyph: str = "◇") -> str:
    """Plain text fusion equation: /a + /b -> /result glyph"""
    parts = " + ".join(f"/{p}" for p in prereqs)
    return f"{parts} → /{result} {result_glyph}"


def format_grade_colored(grade: str) -> str:
    """Return colored Evidence Grade badge: e.g. \033[...]S\033[0m."""
    color = GRADE_COLORS.get(grade, COLOR_GREY)
    return f"{_fg(*color)}{grade}{_reset()}"

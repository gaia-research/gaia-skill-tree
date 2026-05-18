"""HeroScreen — animated splash screen on startup.

Renders the Diamond Seal mark in ASCII, animates the glyph and title
through the official DESIGN.md color cycles, then auto-transitions
to AgentScreen. Any keypress skips immediately.

Color system — exact DESIGN.md values:
  Ultimate cycle (6-stop):  #38bdf8 → #a78bfa → #f59e0b → #ef4444 → #c084fc → #34d399
  Rank ramp:  slate → sky-blue → teal → violet → fuchsia → amber
  Apex gold:  #fbbf24  (seal, GAIA title)
  Honor red:  #ef4444  (contributor names)
"""

from __future__ import annotations

import os
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from rich.align import Align
from rich.console import Console
from rich.segment import Segment


# ── Design-system colors (DESIGN.md canonical) ───────────────────────────────

APEX_GOLD   = "#fbbf24"
HONOR_RED   = "#ef4444"
BG          = "#030712"
MUTED       = "#64748b"
TEXT        = "#e2e8f0"
BORDER      = "#1e293b"

# Ultimate 6-stop cycle
ULT_CYCLE = [
    "#38bdf8",  # 0%   blue
    "#a78bfa",  # 18%  purple/violet
    "#f59e0b",  # 36%  gold
    "#ef4444",  # 54%  red
    "#c084fc",  # 72%  purple
    "#34d399",  # 90%  green
]

# Rank ramp (0★ → 5★)
RANK_RAMP = [
    "#94a3b8",  # 0★  Unawakened  slate
    "#38bdf8",  # 1★  Awakened    sky-blue
    "#63cab7",  # 2★  Named       teal
    "#a78bfa",  # 3★  Evolved     violet
    "#e879f9",  # 4★  Hardened    fuchsia
    "#fbbf24",  # 5★  Transcend.  amber
]

# Tier accent colors
TIER_COLORS = {
    "basic":    "#38bdf8",
    "extra":    "#c084fc",
    "unique":   "#7c3aed",
    "ultimate": "#f59e0b",
}


# ── Diamond Seal ASCII art ────────────────────────────────────────────────────
# Mirrors the SVG: M32,4 L60,32 L32,60 L4,32 Z — rotated square with G inside.
# Terminal chars: ╱╲ for diagonal edges.

_SEAL_LINES = [
    "          ╱╲",
    "        ╱    ╲",
    "      ╱        ╲",
    "    ╱     G      ╲",
    "      ╲        ╱",
    "        ╲    ╱",
    "          ╲╱",
]

# G sits on line 3 (0-indexed), char 10 from left in that line
_G_LINE = 3
_G_COL  = 10  # position of 'G' in the seal line


def _seal_text(color: str) -> Text:
    """Render Diamond Seal with all strokes in `color`, G in apex gold."""
    t = Text()
    for i, line in enumerate(_SEAL_LINES):
        if i == _G_LINE:
            # Split at G
            g_idx = line.index("G")
            t.append(line[:g_idx], style=color)
            t.append("G", style=f"bold {APEX_GOLD}")
            t.append(line[g_idx + 1:], style=color)
        else:
            t.append(line, style=color)
        t.append("\n")
    return t


def _title_text(frame: int) -> Text:
    """G·A·I·A letters, each in a staggered rank-ramp color."""
    t = Text()
    letters = list("G A I A")
    for i, ch in enumerate(letters):
        if ch == " ":
            t.append(" ")
            continue
        # Each letter offset by frame + index*2, wraps through rank ramp
        idx = (frame + i * 2) % len(RANK_RAMP)
        t.append(ch, style=f"bold {RANK_RAMP[idx]}")
    return t


# ── Registry stats (loaded once) ─────────────────────────────────────────────

def _load_stats(registry_path: str) -> dict:
    import json
    path = os.path.join(registry_path, "registry", "gaia.json")
    if not os.path.exists(path):
        return {"total": 0, "extra": 0, "ultimate": 0, "named": 0}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    skills = data.get("skills", [])
    type_counts: dict[str, int] = {}
    for s in skills:
        t = s.get("type", "basic")
        type_counts[t] = type_counts.get(t, 0) + 1

    # Count named skills
    named_dir = os.path.join(registry_path, "registry", "named")
    named = 0
    if os.path.isdir(named_dir):
        for _, _, files in os.walk(named_dir):
            named += sum(1 for f in files if f.endswith(".md"))

    return {
        "total":    len(skills),
        "basic":    type_counts.get("basic", 0),
        "extra":    type_counts.get("extra", 0),
        "unique":   type_counts.get("unique", 0),
        "ultimate": type_counts.get("ultimate", 0),
        "named":    named,
    }


# ── Hero screen ───────────────────────────────────────────────────────────────

class HeroScreen(Screen):
    """Animated splash screen. Any key → AgentScreen."""

    _frame: reactive[int] = reactive(0, init=False)
    _stats: dict = {}

    BINDINGS = []  # catch-all via on_key

    def __init__(self, registry_path: str, username: str, version: str):
        super().__init__()
        self.registry_path = registry_path
        self.username = username
        self.version = version

    def compose(self) -> ComposeResult:
        with Static(id="hero-content"):
            yield Static("", id="hero-seal")
            yield Static("", id="hero-title")
            yield Static(
                "The AI Agent Skill Registry",
                id="hero-tagline",
            )
            yield Static("", id="hero-stats")
            yield Static(
                "── press any key ──",
                id="hero-hint",
            )

    def on_mount(self) -> None:
        self._stats = _load_stats(self.registry_path)
        self._update_stats()
        self._render_frame()
        # 12 fps animation
        self.set_interval(1 / 12, self._tick)
        # Auto-advance after 3 seconds
        self.set_timer(3.0, self._advance)

    def _tick(self) -> None:
        self._frame = (self._frame + 1) % (len(ULT_CYCLE) * 8)
        self._render_frame()

    def _render_frame(self) -> None:
        frame = self._frame

        # Seal color cycles through ULT_CYCLE, 8 frames per stop
        stop_idx = (frame // 8) % len(ULT_CYCLE)
        next_idx = (stop_idx + 1) % len(ULT_CYCLE)
        t_blend  = (frame % 8) / 8.0
        seal_color = _lerp_hex(ULT_CYCLE[stop_idx], ULT_CYCLE[next_idx], t_blend)

        self.query_one("#hero-seal", Static).update(
            Align.center(_seal_text(seal_color))
        )
        self.query_one("#hero-title", Static).update(
            Align.center(_title_text(frame // 2))
        )

        # Pulse hint text
        hint_alpha = int(128 + 127 * __import__("math").sin(frame * 0.3))
        gray = f"#{hint_alpha:02x}{hint_alpha:02x}{hint_alpha:02x}"
        self.query_one("#hero-hint", Static).update(
            Align.center(Text("── press any key ──", style=gray))
        )

    def _update_stats(self) -> None:
        s = self._stats
        if not s.get("total"):
            self.query_one("#hero-stats", Static).update("")
            return
        t = Text()
        t.append(f"○ {s['basic']} basic", style=TIER_COLORS["basic"])
        t.append("  ·  ", style=MUTED)
        t.append(f"◇ {s['extra']} extra", style=TIER_COLORS["extra"])
        t.append("  ·  ", style=MUTED)
        t.append(f"◆ {s['ultimate']} ultimate", style=TIER_COLORS["ultimate"])
        t.append("  ·  ", style=MUTED)
        t.append(f"✦ {s['named']} named", style=APEX_GOLD)
        self.query_one("#hero-stats", Static).update(Align.center(t))

    def on_key(self, event) -> None:
        self._advance()

    def _advance(self) -> None:
        from gaia_cli.tui.screens.agent import AgentScreen
        self.app.switch_screen(
            AgentScreen(self.registry_path, self.username, self.version)
        )


# ── Color interpolation ───────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lerp_hex(a: str, b: str, t: float) -> str:
    r1, g1, b1 = _hex_to_rgb(a)
    r2, g2, b2 = _hex_to_rgb(b)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"

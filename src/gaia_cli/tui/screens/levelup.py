"""Level-up modal — anime-style unlock animation.

Triggered after a successful skill install. Cycles through glyph
frames and shows tier-colored text before auto-dismissing.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Static
from textual.reactive import reactive
from textual import on
from rich.text import Text
from rich.align import Align
import asyncio

_GLYPHS     = {"basic": "○", "extra": "◇", "unique": "◉", "ultimate": "◆"}
# Canonical DESIGN.md tier colors
_TIER_COLOR = {"basic": "#38bdf8", "extra": "#c084fc", "unique": "#7c3aed", "ultimate": "#f59e0b"}
_TIER_LABEL = {"basic": "BASIC", "extra": "EXTRA", "unique": "UNIQUE", "ultimate": "ULTIMATE"}

# Animation frames: glyph sequence leading to the skill's tier
# Colors follow the rank ramp: slate → sky-blue → teal → violet → fuchsia → amber
_FRAMES = [
    ("·", "#1e293b"),   # 0  dormant
    ("○", "#94a3b8"),   # 1  awakened   slate
    ("○", "#38bdf8"),   # 2  confirmed  sky-blue
    ("◇", "#c084fc"),   # 3  extra      purple
    ("◆", "#7c3aed"),   # 4  unique     deep violet
    ("◉", "#fbbf24"),   # 5  ultimate   apex gold
]

_TIER_FRAME_IDX = {"basic": 2, "extra": 3, "unique": 4, "ultimate": 5}

_BANNERS = {
    "basic":    " SKILL ACQUIRED ",
    "extra":    " SKILL UNLOCKED ",
    "unique":   " ★  RARE SKILL  ★ ",
    "ultimate": " ★ ★  ULTIMATE  ★ ★ ",
}


class LevelUpModal(ModalScreen[None]):
    """Flashy level-up screen. Dismiss with any key or auto-dismiss after 2.5s."""

    BINDINGS = [
        Binding("escape", "dismiss_modal", "", show=False),
        Binding("enter", "dismiss_modal", "", show=False),
        Binding("space", "dismiss_modal", "", show=False),
    ]

    _frame: reactive[int] = reactive(0, init=False)

    def __init__(self, skill_id: str, tier: str, level: str = ""):
        super().__init__()
        self.skill_id = skill_id
        self.tier = tier
        self.level = level
        self._target_frame = _TIER_FRAME_IDX.get(tier, 3)

    def compose(self) -> ComposeResult:
        yield Static(id="lu-backdrop")
        yield Static("", id="lu-card")

    def on_mount(self) -> None:
        self._render_frame(0)
        self.set_interval(0.13, self._tick, pause=False)
        # Auto-dismiss after 2.5 seconds
        self.set_timer(2.5, self.action_dismiss_modal)

    def _tick(self) -> None:
        next_frame = self._frame + 1
        if next_frame <= self._target_frame:
            self._frame = next_frame
            self._render_frame(self._frame)

    def _render_frame(self, frame_idx: int) -> None:
        card = self.query_one("#lu-card", Static)
        glyph, gcolor = _FRAMES[min(frame_idx, len(_FRAMES) - 1)]
        tier_color = _TIER_COLOR.get(self.tier, "#8b949e")
        banner = _BANNERS.get(self.tier, " SKILL UNLOCKED ")
        sid = self.skill_id

        lines: list[tuple[str, str]] = []

        # Top border
        width = max(len(sid) + 8, len(banner) + 4, 36)
        border_h = "═" * (width - 2)
        lines.append((f"╔{border_h}╗", tier_color))
        lines.append((f"║{'':^{width-2}}║", "#30363d"))

        # Banner
        padded_banner = banner.center(width - 2)
        lines.append((f"║{padded_banner}║", tier_color))

        # Glyph animation (big)
        big_glyph = f"  {glyph}  "
        lines.append((f"║{'':^{width-2}}║", "#30363d"))
        lines.append((f"║{big_glyph:^{width-2}}║", gcolor))
        lines.append((f"║{'':^{width-2}}║", "#30363d"))

        # Skill ID
        sid_line = f"  {sid}  "
        lines.append((f"║{sid_line:^{width-2}}║", "#e6edf3"))

        # Level
        if self.level:
            lv_line = f"  {self.level}  "
            lines.append((f"║{lv_line:^{width-2}}║", "#8b949e"))

        # Progress dots
        progress = ""
        for i in range(self._target_frame + 1):
            g, _ = _FRAMES[i]
            progress += g + " "
        progress_line = progress.strip().center(width - 2)
        lines.append((f"║{'':^{width-2}}║", "#30363d"))
        lines.append((f"║{progress_line}║", tier_color))

        # Hint
        hint = " [press any key] "
        if frame_idx < self._target_frame:
            hint = ""
        lines.append((f"║{'':^{width-2}}║", "#30363d"))
        lines.append((f"║{hint:^{width-2}}║", "#484f58"))

        # Bottom border
        lines.append((f"╚{border_h}╝", tier_color))

        t = Text()
        for line, color in lines:
            t.append(line + "\n", style=color)

        card.update(Align.center(t, vertical="middle"))

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

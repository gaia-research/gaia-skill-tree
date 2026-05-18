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

from gaia_cli.tui import tokens as T

_TIER_LABEL = {"basic": "BASIC", "extra": "EXTRA", "unique": "UNIQUE", "ultimate": "ULTIMATE"}

# Animation frames: glyph + color pair. Color sequence walks the rank ramp:
# dormant (border) → unawakened slate → awakened sky-blue → evolved violet
# → unique deep-violet → apex gold. Indexes map to tiers via _TIER_FRAME_IDX.
_FRAMES = [
    ("·", T.NEUTRAL_BORDER),
    ("○", T.RANK_UNAWAKENED),
    ("○", T.RANK_AWAKENED),
    ("◇", T.TIER_EXTRA),
    ("◆", T.TIER_UNIQUE),
    ("◉", T.BRAND_APEX_GOLD),
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
        tier_color = T.TIER_BY_KEY.get(self.tier, T.NEUTRAL_TEXT_MUTED)
        banner = _BANNERS.get(self.tier, " SKILL UNLOCKED ")
        sid = self.skill_id

        lines: list[tuple[str, str]] = []
        gutter = T.NEUTRAL_BORDER

        # Top border
        width = max(len(sid) + 8, len(banner) + 4, 36)
        border_h = "═" * (width - 2)
        lines.append((f"╔{border_h}╗", tier_color))
        lines.append((f"║{'':^{width-2}}║", gutter))

        # Banner
        padded_banner = banner.center(width - 2)
        lines.append((f"║{padded_banner}║", tier_color))

        # Glyph animation (big)
        big_glyph = f"  {glyph}  "
        lines.append((f"║{'':^{width-2}}║", gutter))
        lines.append((f"║{big_glyph:^{width-2}}║", gcolor))
        lines.append((f"║{'':^{width-2}}║", gutter))

        # Skill ID
        sid_line = f"  {sid}  "
        lines.append((f"║{sid_line:^{width-2}}║", T.NEUTRAL_TEXT))

        # Level
        if self.level:
            lv_line = f"  {self.level}  "
            lines.append((f"║{lv_line:^{width-2}}║", T.NEUTRAL_TEXT_MUTED))

        # Progress dots
        progress = ""
        for i in range(self._target_frame + 1):
            g, _ = _FRAMES[i]
            progress += g + " "
        progress_line = progress.strip().center(width - 2)
        lines.append((f"║{'':^{width-2}}║", gutter))
        lines.append((f"║{progress_line}║", tier_color))

        # Hint
        hint = " [press any key] "
        if frame_idx < self._target_frame:
            hint = ""
        lines.append((f"║{'':^{width-2}}║", gutter))
        lines.append((f"║{hint:^{width-2}}║", T.NEUTRAL_TEXT_DIM))

        # Bottom border
        lines.append((f"╚{border_h}╝", tier_color))

        t = Text()
        for line, color in lines:
            t.append(line + "\n", style=color)

        card.update(Align.center(t, vertical="middle"))

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

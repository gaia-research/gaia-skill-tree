"""Level-up modal — anime-style unlock animation.

Triggered after a successful skill install. Cycles through glyph frames and
shows rank-colored text before auto-dismissing.

BUILD + READ ONLY (Ygg III forward-compat): this modal derives nothing about
branch/rank itself. It reads the caller-supplied branch word (already resolved
via ``taxonomy.branchFor``) and the star level, and calls the taxonomy authority
(``levelNum`` / ``rankWord``) for every display decision. There
are no hand-keyed branch→frame or branch→banner tables — the animation depth is
a *stars* concept (``levelNum``) and the banner text is the authority's
``rankWord``; branch only selects the accent color.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from rich.align import Align

from gaia_cli.tui import tokens as T
from gaia_cli.taxonomy import levelNum, rankWord

# Animation frames: glyph + color pair, indexed by star level 0..6. Frame N is
# shown for an N-star unlock, so the reveal climbs the shared rank ramp and, at
# 4★+, lands on the branch pinnacle. This is a pure stars ladder — NOT a
# branch→frame map — so no banned resolver logic lives here.
_FRAMES = [
    ("·", T.NEUTRAL_BORDER),          # 0★ dormant
    ("○", T.RANK_AWAKENED),           # 1★ awakened — sky blue
    ("○", T.RANK_NAMED),              # 2★ named — teal
    ("◇", T.RANK_EVOLVED),            # 3★ evolved — violet
    ("◈", T.RANK_EXTRA),              # 4★ extra/unique — fuchsia
    ("◆", T.RANK_ULTIMATE),           # 5★ ultimate — amber
    ("✦", T.BRAND_APEX_GOLD),         # 6★ apex — gold
]


class LevelUpModal(ModalScreen[None]):
    """Flashy level-up screen. Dismiss with any key or auto-dismiss after 2.5s."""

    BINDINGS = [
        Binding("escape", "dismiss_modal", "", show=False),
        Binding("enter", "dismiss_modal", "", show=False),
        Binding("space", "dismiss_modal", "", show=False),
    ]

    _frame: reactive[int] = reactive(0, init=False)

    def __init__(self, skill_id: str, branch: str, level: str = ""):
        super().__init__()
        self.skill_id = skill_id
        # branch is a resolved display-branch word (standard|suite|unique) the
        # caller obtained from taxonomy.branchFor — never re-derived here.
        self.branch = branch
        self.level = level
        # Frame depth is the star level, clamped through the authority. A 6★
        # unlock climbs to the apex frame; a 2★ unlock stops at the named frame.
        self._target_frame = levelNum(level)

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
        # Accent color: read the branch→accent token map (build+read — no inline
        # branch logic). Banner text: the authority's rank word for this
        # (level, branch), so a 4★ suite reads "EXTRA", a 6★ unique reads
        # "UNIQUE IMPOSSIBLE", a 2★ reads "NAMED" — never a hand-rolled label.
        accent = T.BRANCH_ACCENT.get(self.branch, T.NEUTRAL_TEXT_MUTED)
        word = rankWord(self.level, self.branch)
        banner = f" {word.upper()} " if word else " SKILL UNLOCKED "
        sid = self.skill_id

        lines: list[tuple[str | Text, str]] = []
        gutter = T.NEUTRAL_BORDER

        # Top border
        # width calculation needs the raw sid length
        width = max(len(sid) + 10, len(banner) + 4, 36)
        border_h = "═" * (width - 2)
        lines.append((f"╔{border_h}╗", accent))
        lines.append((f"║{'':^{width-2}}║", gutter))

        # Banner
        padded_banner = banner.center(width - 2)
        lines.append((f"║{padded_banner}║", accent))

        # Glyph animation (big)
        big_glyph = f"  {glyph}  "
        lines.append((f"║{'':^{width-2}}║", gutter))
        lines.append((f"║{big_glyph:^{width-2}}║", gcolor))
        lines.append((f"║{'':^{width-2}}║", gutter))

        # Skill ID rendering: @handle/slug — pre-named/demoted handles redacted.
        t_sid = Text()
        if "/" in sid:
            from gaia_cli.redaction import REDACTED_BLOCK, is_redacted
            contrib, name = sid.split("/", 1)
            if is_redacted(self.level):
                t_sid.append(REDACTED_BLOCK, style=T.RANK_UNAWAKENED)
            else:
                t_sid.append("@" + contrib, style=T.BRAND_HONOR_RED)
            t_sid.append("/" + name, style=T.STATE_OWNED)
        else:
            t_sid.append(sid, style=T.STATE_OWNED)
        
        # Center the Text object manually for the box
        content_len = len(t_sid.plain)
        pad = (width - 2 - content_len) // 2
        lpad = " " * pad
        rpad = " " * (width - 2 - content_len - pad)
        t_line = Text("║")
        t_line.append(lpad)
        t_line.append(t_sid)
        t_line.append(rpad)
        t_line.append("║")
        lines.append((t_line, ""))

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
        lines.append((f"║{progress_line}║", accent))

        # Hint
        hint = " [press any key] "
        if frame_idx < self._target_frame:
            hint = ""
        lines.append((f"║{'':^{width-2}}║", gutter))
        lines.append((f"║{hint:^{width-2}}║", T.NEUTRAL_TEXT_DIM))

        # Bottom border
        lines.append((f"╚{border_h}╝", accent))

        t = Text()
        for line, color in lines:
            if isinstance(line, Text):
                t.append(line)
                t.append("\n")
            else:
                t.append(line + "\n", style=color)

        card.update(Align.center(t, vertical="middle"))

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

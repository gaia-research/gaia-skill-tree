"""Scan screen — live streaming gaia scan output with skill card animations."""

from __future__ import annotations

import re
import subprocess
import sys
from typing import Iterator

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static, RichLog
from textual.reactive import reactive
from textual import work
from rich.text import Text

_GLYPHS     = {"basic": "○", "extra": "◇", "unique": "◉", "ultimate": "◆"}
# Canonical DESIGN.md tier colors
_TIER_COLOR = {"basic": "#38bdf8", "extra": "#c084fc", "unique": "#7c3aed", "ultimate": "#f59e0b"}

# Patterns from gaia scan output
_MATCH_RE    = re.compile(r"◇|◉|○|◆\s+(/?\S+)")
_UNLOCK_RE   = re.compile(r"SKILL UNLOCKED|skill unlocked", re.IGNORECASE)
_FUSION_RE   = re.compile(r"──▶\s+(/?\S+)")
_SKILL_RE    = re.compile(r"(◇|◉|○|◆)\s+([\w/\-]+)")


class ScanScreen(Screen):
    """Streams gaia scan live. Press A to go back."""

    BINDINGS = [
        Binding("a", "goto_agent", "Agent", show=True),
        Binding("q", "quit_app", "Quit", show=True),
        Binding("r", "rescan", "Rescan", show=True),
        Binding("escape", "goto_agent", "Back", show=False),
    ]

    _running: reactive[bool] = reactive(False)

    def __init__(self, registry_path: str):
        super().__init__()
        self.registry_path = registry_path

    def compose(self) -> ComposeResult:
        with Static(id="header"):
            yield Static("  ◆ GAIA ", id="header-logo")
            yield Static("SCANNING", id="header-section")

        yield RichLog(id="scan-log", highlight=False, markup=True, auto_scroll=True)

        with Static(id="status-bar"):
            yield Static("", id="status-counts")
            yield Static(
                "[dim]r[/] rescan  [dim]a[/] agent  [dim]q[/] quit",
                id="status-hints",
            )

    def on_mount(self) -> None:
        self._run_scan()

    def action_rescan(self) -> None:
        log = self.query_one("#scan-log", RichLog)
        log.clear()
        self._run_scan()

    @work(thread=True)
    def _run_scan(self) -> None:
        log = self.query_one("#scan-log", RichLog)
        status = self.query_one("#status-counts", Static)

        self.app.call_from_thread(status.update, "Scanning…")
        self.app.call_from_thread(
            log.write,
            Text("  Scanning repository…\n", style="#8b949e"),
        )

        matched = 0
        unlocked = 0

        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "gaia_cli.main", "scan"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for raw_line in proc.stdout:  # type: ignore[union-attr]
                line = raw_line.rstrip("\n")
                styled = self._style_line(line)
                self.app.call_from_thread(log.write, styled)

                # Count matches
                if _SKILL_RE.search(line):
                    matched += 1
                if _UNLOCK_RE.search(line):
                    unlocked += 1

                self.app.call_from_thread(
                    status.update,
                    f"{matched} skills matched  ·  {unlocked} unlocked",
                )

            proc.wait()
            self.app.call_from_thread(
                log.write,
                Text("\n  ✓ Scan complete\n", style="#3fb950"),
            )
        except Exception as exc:
            self.app.call_from_thread(
                log.write,
                Text(f"\n  ✗ Scan error: {exc}\n", style="#f85149"),
            )

    def _style_line(self, line: str) -> Text:
        """Apply tier colors to scan output lines."""
        t = Text()

        # Skill unlock banner
        if _UNLOCK_RE.search(line):
            t.append("  " + line + "\n", style="#f59e0b bold")
            return t

        # Matched skill lines (◇ /skill-id etc)
        m = _SKILL_RE.search(line)
        if m:
            glyph = m.group(1)
            sid = m.group(2)
            glyph_color = {
                "○": "#38bdf8",
                "◇": "#c084fc",
                "◉": "#7c3aed",
                "◆": "#f59e0b",
            }.get(glyph, "#38bdf8")
            # Render with colored glyph
            pre = line[:m.start()]
            post = line[m.end():]
            t.append("  " + pre, style="#64748b")
            t.append(glyph + " ", style=glyph_color)
            t.append(sid, style="#e2e8f0")
            t.append(post + "\n", style="#94a3b8")
            return t

        # Fusion lines
        if "──▶" in line or "─┤" in line or "─┘" in line:
            t.append("  " + line + "\n", style="#c084fc")
            return t

        # Status / count lines
        if line.startswith("⚡") or "reachable" in line or "saved" in line:
            t.append("  " + line + "\n", style="#22c55e")
            return t

        # Default dim
        t.append("  " + line + "\n", style="#484f58")
        return t

    def action_goto_agent(self) -> None:
        self.app.pop_screen()

    def action_quit_app(self) -> None:
        self.app.exit()

"""Scan screen — live streaming gaia scan output with skill card animations."""

from __future__ import annotations

import os
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

from gaia_cli.tui import tokens as T

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
            Text("  Scanning repository…\n", style=T.NEUTRAL_TEXT_MUTED),
        )

        matched = 0
        unlocked = 0

        # We want ANSI colors even though we're piping
        env = os.environ.copy()
        env["FORCE_COLOR"] = "1"

        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "gaia_cli.main", "scan"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
            for raw_line in proc.stdout:  # type: ignore[union-attr]
                line = raw_line.rstrip("\n")
                
                # Render the ANSI-colored line directly
                styled = Text.from_ansi("  " + line + "\n")
                self.app.call_from_thread(log.write, styled)

                # Strip ANSI for count matching to ensure robustness
                plain_line = Text.from_ansi(line).plain
                if _SKILL_RE.search(plain_line):
                    matched += 1
                if _UNLOCK_RE.search(plain_line):
                    unlocked += 1

                self.app.call_from_thread(
                    status.update,
                    f"{matched} skills matched  ·  {unlocked} unlocked",
                )

            proc.wait()
            self.app.call_from_thread(
                log.write,
                Text("\n  ✓ Scan complete\n", style=T.STATE_SCAN_COMPLETE),
            )
        except Exception as exc:
            self.app.call_from_thread(
                log.write,
                Text(f"\n  ✗ Scan error: {exc}\n", style=T.STATE_INSTALL_ERROR),
            )

    def _style_line(self, line: str) -> Text:
        """Legacy helper, now mostly unused by pass-through."""
        return Text.from_ansi("  " + line + "\n")

    def action_goto_agent(self) -> None:
        self.app.pop_screen()

    def action_quit_app(self) -> None:
        self.app.exit()

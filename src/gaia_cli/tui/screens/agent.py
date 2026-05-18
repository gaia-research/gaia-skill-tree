"""Agent screen — default TUI landing.

Search skills by name, description, or natural language phrase.
Arrow-key navigate, Enter to install, Tab to multi-select.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from textual.widgets import Input, ListView, ListItem, Label, Static, RichLog, Button
from textual.reactive import reactive
from textual.message import Message
from textual import on, work
from rich.text import Text


# ── Data helpers ──────────────────────────────────────────────────────────────

def _load_skills(registry_path: str) -> list[dict]:
    """Return all skills from registry + detected scan, merged and deduplicated."""
    skills: dict[str, dict] = {}

    # 1. Canon registry skills
    try:
        from gaia_cli.localContext import LocalContext
        from gaia_cli.scanner import load_config
        cfg = load_config() or {}
        username = cfg.get("gaiaUser", cfg.get("user", ""))
        ctx = LocalContext.load(registry_path, username)
        for sid, skill in ctx._skill_map.items():
            tier = skill.get("type", "basic")
            level = skill.get("level", "")
            desc = skill.get("description", "")
            installed = sid in (ctx.owned_ids | ctx.detected_ids)
            skills[sid] = {
                "id": sid,
                "type": tier,
                "level": level,
                "description": desc,
                "installed": installed,
                "detected": sid in ctx.detected_ids,
                "owned": sid in ctx.owned_ids,
            }
    except Exception:
        pass

    # 2. Named skills from registry (overlay meta if missing)
    try:
        from gaia_cli.install import list_available, load_manifest
        available = list_available(registry_path)
        installed_ids = {e["id"] for e in load_manifest().get("installed", [])}
        for sid, meta in available:
            if sid not in skills:
                skills[sid] = {
                    "id": sid,
                    "type": meta.get("type", "extra"),
                    "level": meta.get("level", ""),
                    "description": meta.get("description", ""),
                    "installed": sid in installed_ids,
                    "detected": False,
                    "owned": False,
                }
            else:
                skills[sid]["installed"] = skills[sid]["installed"] or (sid in installed_ids)
    except Exception:
        pass

    # Sort: installed first, then by type weight, then alphabetical
    _type_order = {"ultimate": 0, "unique": 1, "extra": 2, "basic": 3}
    return sorted(
        skills.values(),
        key=lambda s: (
            not s.get("installed", False),
            _type_order.get(s.get("type", "basic"), 4),
            s["id"],
        ),
    )


def _fuzzy_match(query: str, skill: dict) -> bool:
    """Return True if query tokens all appear in skill id or description."""
    q = query.lower()
    target = f"{skill['id']} {skill.get('description', '')}".lower()
    return all(tok in target for tok in q.split())


def _filter_skills(query: str, skills: list[dict]) -> list[dict]:
    if not query.strip():
        return skills
    return [s for s in skills if _fuzzy_match(query, s)]


# ── Glyph / color helpers ─────────────────────────────────────────────────────

_GLYPHS = {"basic": "○", "extra": "◇", "unique": "◉", "ultimate": "◆"}
_TIER_MARKUP = {
    "basic": "glyph-basic",
    "extra": "glyph-extra",
    "unique": "glyph-unique",
    "ultimate": "glyph-ultimate",
}


def _skill_label(skill: dict) -> Text:
    tier = skill.get("type", "basic")
    glyph = _GLYPHS.get(tier, "○")
    sid = skill["id"]
    level = skill.get("level", "")
    installed = skill.get("installed", False)

    t = Text()
    # glyph
    colors = {"basic": "#8b949e", "extra": "#79c0ff", "unique": "#d2a8ff", "ultimate": "#e3b341"}
    t.append(glyph + " ", style=colors.get(tier, "#8b949e"))
    # skill id — contributor colored differently
    if "/" in sid:
        contrib, name = sid.split("/", 1)
        t.append(contrib + "/", style="#8b949e")
        t.append(name, style="#e6edf3")
    else:
        t.append(sid, style="#e6edf3")
    # level badge
    if level:
        t.append(f"  {level}", style="#484f58")
    # installed marker
    if installed:
        t.append("  ✓", style="#3fb950")
    return t


# ── Install modal ─────────────────────────────────────────────────────────────

class InstallModal(ModalScreen):
    """Confirm + stream install output."""

    BINDINGS = [
        Binding("escape", "dismiss(False)", "Cancel"),
        Binding("enter", "confirm_install", "Install", show=False),
    ]

    def __init__(self, skill: dict, registry_path: str):
        super().__init__()
        self.skill = skill
        self.registry_path = registry_path
        self._installing = False

    def compose(self) -> ComposeResult:
        tier = self.skill.get("type", "basic")
        colors = {"basic": "#8b949e", "extra": "#79c0ff", "unique": "#d2a8ff", "ultimate": "#e3b341"}
        tier_color = colors.get(tier, "#8b949e")
        glyph = _GLYPHS.get(tier, "○")

        with Static(id="install-dialog"):
            yield Static("Install skill", id="install-title")
            yield Static(
                Text.from_markup(
                    f"[bold {tier_color}]{glyph} {self.skill['id']}[/]"
                ),
                id="install-skill-id",
            )
            meta_parts = []
            if self.skill.get("type"):
                meta_parts.append(self.skill["type"])
            if self.skill.get("level"):
                meta_parts.append(self.skill["level"])
            yield Static("  ·  ".join(meta_parts), id="install-meta")
            yield RichLog(id="install-log", highlight=True, markup=True)
            with Static(id="install-buttons"):
                yield Button("Install", id="btn-install", variant="success")
                yield Button("Cancel", id="btn-cancel")

    def on_mount(self) -> None:
        self.query_one("#install-log", RichLog).write(
            "[dim]Press Install to proceed, Escape to cancel.[/]"
        )

    @on(Button.Pressed, "#btn-install")
    def action_confirm_install(self) -> None:
        if self._installing:
            return
        self._installing = True
        self.query_one("#btn-install", Button).disabled = True
        self.query_one("#btn-cancel", Button).disabled = True
        self._do_install()

    @on(Button.Pressed, "#btn-cancel")
    def _cancel(self) -> None:
        self.dismiss(False)

    @work(thread=True)
    def _do_install(self) -> None:
        log = self.query_one("#install-log", RichLog)
        sid = self.skill["id"]
        try:
            from gaia_cli.install import install_skill
            log.write(f"[dim]Installing [bold]{sid}[/]...[/]")

            # Capture stdout from install_skill
            import io
            from contextlib import redirect_stdout, redirect_stderr
            out = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                result = install_skill(sid, self.registry_path)

            for line in out.getvalue().splitlines():
                log.write(line)
            for line in err.getvalue().splitlines():
                log.write(f"[red]{line}[/]")

            if result is not False:
                log.write(f"[green]✓ Installed {sid}[/]")
                self.app.call_from_thread(self.dismiss, True)
            else:
                log.write(f"[red]✗ Install failed — see above[/]")
                self.app.call_from_thread(
                    lambda: setattr(self.query_one("#btn-cancel", Button), "disabled", False)
                )
        except Exception as exc:
            log.write(f"[red]Error: {exc}[/]")
            self.app.call_from_thread(
                lambda: setattr(self.query_one("#btn-cancel", Button), "disabled", False)
            )


# ── Agent screen ──────────────────────────────────────────────────────────────

class AgentScreen(Screen):
    """Main landing screen — skill search and install."""

    BINDINGS = [
        Binding("ctrl+t", "goto_tree", "Tree [ctrl+t]"),
        Binding("ctrl+g", "goto_scan", "Scan [ctrl+g]"),
        Binding("ctrl+q", "quit_app", "Quit [ctrl+q]"),
        Binding("q", "quit_app", "Quit", show=False),
        Binding("escape", "clear_search", "Clear", show=False),
        Binding("i", "install_selected", "Install", show=False, priority=True),
        Binding("ctrl+r", "reload", "Reload", show=False),
    ]

    search_query: reactive[str] = reactive("", init=False)
    _all_skills: list[dict] = []
    _filtered: list[dict] = []

    def __init__(self, registry_path: str, username: str, version: str):
        super().__init__()
        self.registry_path = registry_path
        self.username = username
        self.version = version

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Static(id="header"):
            yield Static("  GAIA ", id="header-logo")
            if self.username:
                yield Static(f"◉ {self.username}", id="header-user")
            yield Static(f"v{self.version}", id="header-version")

        with Static(id="search-container"):
            yield Static(
                "Search skills by name, description, or intent — press [bold]Enter[/] to install",
                id="search-label",
            )
            yield Input(placeholder="> ", id="search-input")

        yield ListView(id="skills-container")

        with Static(id="status-bar"):
            yield Static("", id="status-counts")
            yield Static(
                "[dim]↑↓[/] navigate  [dim]Enter[/] install  [dim]^T[/] tree  [dim]^G[/] scan  [dim]q[/] quit",
                id="status-hints",
            )

    def on_mount(self) -> None:
        self._load_data()
        self.query_one("#search-input", Input).focus()

    @work(thread=True)
    def _load_data(self) -> None:
        self.app.call_from_thread(self._set_status, "Loading skills…")
        skills = _load_skills(self.registry_path)
        self.app.call_from_thread(self._apply_skills, skills)

    def _apply_skills(self, skills: list[dict]) -> None:
        self._all_skills = skills
        self._filtered = list(skills)
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        lv = self.query_one("#skills-container", ListView)
        lv.clear()
        for skill in self._filtered:
            item = ListItem(Label(Text.assemble(_skill_label(skill))), name=skill["id"])
            lv.append(item)
        self._set_status()

    def _set_status(self, msg: str = "") -> None:
        sb = self.query_one("#status-counts", Static)
        if msg:
            sb.update(msg)
            return
        total = len(self._all_skills)
        shown = len(self._filtered)
        installed = sum(1 for s in self._all_skills if s.get("installed"))
        if shown < total:
            sb.update(f"{shown} of {total} skills  ·  {installed} installed")
        else:
            sb.update(f"{total} skills  ·  {installed} installed")

    # ── Search ────────────────────────────────────────────────────────────────

    @on(Input.Changed, "#search-input")
    def _on_search_change(self, event: Input.Changed) -> None:
        q = event.value.strip()
        self._filtered = _filter_skills(q, self._all_skills)
        self._rebuild_list()
        # Re-focus first item
        lv = self.query_one("#skills-container", ListView)
        if self._filtered:
            lv.index = 0

    @on(Input.Submitted, "#search-input")
    def _on_search_submit(self, event: Input.Submitted) -> None:
        lv = self.query_one("#skills-container", ListView)
        if self._filtered:
            idx = lv.index or 0
            if 0 <= idx < len(self._filtered):
                self._open_install(self._filtered[idx])

    # ── List navigation ───────────────────────────────────────────────────────

    @on(ListView.Selected)
    def _on_list_selected(self, event: ListView.Selected) -> None:
        sid = event.item.name
        skill = next((s for s in self._filtered if s["id"] == sid), None)
        if skill:
            self._open_install(skill)

    # ── Install ───────────────────────────────────────────────────────────────

    def action_install_selected(self) -> None:
        lv = self.query_one("#skills-container", ListView)
        idx = lv.index
        if idx is not None and 0 <= idx < len(self._filtered):
            self._open_install(self._filtered[idx])

    def _open_install(self, skill: dict) -> None:
        was_installed = skill.get("installed", False)

        def _on_close(installed: bool) -> None:
            if installed:
                for s in self._all_skills:
                    if s["id"] == skill["id"]:
                        s["installed"] = True
                self._filtered = _filter_skills(
                    self.query_one("#search-input", Input).value, self._all_skills
                )
                self._rebuild_list()
                # Level-up animation for newly installed skills
                if not was_installed:
                    from gaia_cli.tui.screens.levelup import LevelUpModal
                    self.app.push_screen(
                        LevelUpModal(
                            skill["id"],
                            skill.get("type", "basic"),
                            skill.get("level", ""),
                        )
                    )

        self.app.push_screen(
            InstallModal(skill, self.registry_path),
            callback=_on_close,
        )

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_clear_search(self) -> None:
        inp = self.query_one("#search-input", Input)
        if inp.value:
            inp.value = ""
        else:
            inp.focus()

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_reload(self) -> None:
        self._load_data()

    def action_goto_scan(self) -> None:
        from gaia_cli.tui.screens.scan import ScanScreen
        self.app.push_screen(ScanScreen(self.registry_path))

    def action_goto_tree(self) -> None:
        from gaia_cli.tui.screens.tree import SkillTreeScreen
        from gaia_cli.localContext import LocalContext
        from gaia_cli.scanner import load_config
        cfg = load_config() or {}
        username = cfg.get("gaiaUser", cfg.get("user", ""))
        try:
            ctx = LocalContext.load(self.registry_path, username)
            owned = ctx.owned_ids
            detected = ctx.detected_ids
        except Exception:
            owned, detected = set(), set()
        self.app.push_screen(SkillTreeScreen(self.registry_path, owned, detected))

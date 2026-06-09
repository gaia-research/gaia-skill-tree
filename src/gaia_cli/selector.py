"""gaia default selector — shown when `gaia` is run with no arguments in a TTY."""

from __future__ import annotations

import os
import sys


from gaia_cli.formatting import (
    RANK_COLORS,
    _fg,
    _reset,
    _bold,
    _use_color,
)
from gaia_cli.interactive import _has_interactive


# ── Color shortcuts ────────────────────────────────────────────────────────────

def _c(rank: str) -> tuple[int, int, int]:
    return RANK_COLORS.get(rank, (200, 200, 200))


# ── Logo: large G ─────────────────────────────────────────────────────────────
#
# Visually dominant G in apex gold. Five-line box-drawing letter:
#
#   ╔═══════╗   top bar
#   ║            left wall only (open right side)
#   ║   ╔═══╣   middle crossbar + right junction
#   ║       ║   inner right wall
#   ╚═══════╝   bottom bar
#
_G_LINES = [
    "  ╔═══════╗  ",
    "  ║          ",
    "  ║   ╔═══╣  ",
    "  ║       ║  ",
    "  ╚═══════╝  ",
]

# ── Logo: diamond seal mark ────────────────────────────────────────────────────

_SEAL_LINES = [
    "       ╱╲       ",
    "     ╱    ╲     ",
    "   ╱        ╲   ",
    "   ╲        ╱   ",
    "     ╲    ╱     ",
    "       ╲╱       ",
]


def _render_logo() -> None:
    gold = _c("6★")
    accent = _c("4★")
    muted = (100, 116, 139)  # slate-500 dim

    gold_bold = _fg(*gold) + _bold()
    accent_c = _fg(*accent)
    reset = _reset()
    dim = _fg(*muted)

    lines: list[str] = []

    # Big G
    for line in _G_LINES:
        lines.append(f"  {gold_bold}{line}{reset}")

    lines.append("")

    # Diamond seal
    for line in _SEAL_LINES:
        lines.append(f"  {accent_c}{line}{reset}")

    lines.append("")

    # G · A · I · A title (staggered rank colors)
    ramp = ["1★", "2★", "3★", "4★", "5★", "6★"]
    letters = ["G", "·", "A", "·", "I", "·", "A"]
    title = ""
    color_idx = 0
    for ch in letters:
        if ch == "·":
            title += f"  {dim}·{reset}  "
        else:
            c = _c(ramp[color_idx % len(ramp)])
            title += f"{_fg(*c)}{_bold()}{ch}{reset}"
            color_idx += 1
    lines.append(f"  {title}")

    # Tagline
    lines.append(f"  {dim}The AI Agent Skill Registry{reset}")

    # Version (lazy import to avoid startup cost)
    try:
        from importlib.metadata import version as _ver
        ver = _ver("gaia-cli")
        lines.append(f"  {dim}v{ver}{reset}")
    except Exception:
        pass

    lines.append("")

    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


# ── Command catalogue ──────────────────────────────────────────────────────────

_CORE = [
    ("init",    "1★", "Initialize your skill tree"),
    ("scan",    "2★", "Detect skills in your codebase"),
    ("push",    "3★", "Propose skills to the registry"),
]

_DAILY = [
    ("tree",    "5★", "Visualize your skill tree"),
    ("promote", "5★", "Rank up a detected skill"),
    ("fuse",    "5★", "Create a skill fusion"),
    ("pull",    "3★", "Fetch latest registry"),
    ("appraise","4★", "Appraise a skill"),
    ("stats",   "4★", "Show statistics"),
    ("path",    "5★", "Show unlock path to a skill"),
    ("lookup",  "2★", "Look up a skill"),
]

_SKILLS = [
    ("skills list",      "6★", "List available named skills"),
    ("skills search",    "6★", "Search named skills"),
    ("skills install",   "6★", "Install a named skill"),
    ("skills uninstall", "6★", "Uninstall a named skill"),
]

_UTILITIES = [
    ("whoami",  "2★", "Show identity and auth status"),
    ("version", "1★", "Print version"),
    ("update",  "3★", "Update CLI and registry"),
    ("mcp",     "3★", "Print MCP server config"),
    ("graph",   "1★", "Open skills graph"),
]


def _choice_label(cmd: str, rank: str, desc: str) -> str:
    c = _c(rank)
    reset = _reset()
    bold = _bold()
    if _use_color():
        cmd_colored = f"{_fg(*c)}{bold}{cmd}{reset}"
    else:
        cmd_colored = cmd
    pad = max(1, 18 - len(cmd))
    return f"  {cmd_colored}{' ' * pad}{desc}"


def _build_choices(expanded: bool = False) -> list:
    try:
        import questionary
    except ImportError:
        return []

    choices: list = []

    choices.append(questionary.Separator("  ── Getting started ─────────────────────────"))
    for cmd, rank, desc in _CORE:
        choices.append(questionary.Choice(title=_choice_label(cmd, rank, desc), value=cmd))

    choices.append(questionary.Separator("  ── Daily ───────────────────────────────────"))
    for cmd, rank, desc in _DAILY:
        choices.append(questionary.Choice(title=_choice_label(cmd, rank, desc), value=cmd))

    if expanded:
        choices.append(questionary.Separator("  ── Skills ──────────────────────────────────"))
        for cmd, rank, desc in _SKILLS:
            choices.append(questionary.Choice(title=_choice_label(cmd, rank, desc), value=cmd))

        choices.append(questionary.Separator("  ── Utilities ───────────────────────────────"))
        for cmd, rank, desc in _UTILITIES:
            choices.append(questionary.Choice(title=_choice_label(cmd, rank, desc), value=cmd))
    else:
        choices.append(questionary.Separator("  ─────────────────────────────────────────────"))
        choices.append(questionary.Choice(
            title=f"  {'·· More ··':18}Skills and utilities",
            value="__more__",
        ))

    return choices


# ── Main entry point ───────────────────────────────────────────────────────────

def run_selector(parser) -> None:
    """Show the Gaia command selector. Falls back to parser.print_help() if not interactive."""
    if not _has_interactive():
        parser.print_help()
        return

    try:
        import questionary
    except ImportError:
        parser.print_help()
        return

    _render_logo()

    expanded = False
    while True:
        choices = _build_choices(expanded=expanded)
        try:
            selected = questionary.select(
                "Select a command:",
                choices=choices,
                use_shortcuts=False,
                use_indicator=True,
                style=questionary.Style([
                    ("separator", "fg:#4b5563"),
                    ("selected", "bold"),
                    ("pointer", "fg:#fbbf24 bold"),
                    ("answer", "fg:#fbbf24 bold"),
                ]),
            ).ask()
        except KeyboardInterrupt:
            sys.stdout.write("\n")
            return

        if selected is None:
            return
        if selected == "__more__":
            expanded = True
            continue

        argv0 = sys.argv[0]
        cmd_parts = selected.split()
        os.execvp(argv0, [argv0] + cmd_parts)

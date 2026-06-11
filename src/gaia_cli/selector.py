"""gaia default selector — shown when `gaia` is run with no arguments in a TTY.

Implemented as a custom prompt_toolkit Application so that:
  - FormattedText hex colors render correctly (raw ANSI breaks in questionary)
  - Left/right arrow keys navigate nested submenus and flag toggles
  - An animated apex-rainbow shimmer flows across the G logo each frame
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field

from gaia_cli.interactive import _has_interactive


# ── Menu model ────────────────────────────────────────────────────────────────

@dataclass
class MenuItem:
    label: str
    rank: str
    desc: str
    argv: list[str] | None = None          # leaf: args to pass after argv0
    children: list["MenuItem"] | None = None  # submenu items
    flags: list[tuple[str, str]] | None = None  # flag-frame: [(flag, desc), ...]
    _toggled: set[str] = field(default_factory=set, repr=False)

    def is_leaf(self) -> bool:
        return self.children is None and self.flags is None

    def effective_argv(self) -> list[str]:
        """Return argv for this item, including any toggled flags."""
        base = self.argv or self.label.split()
        if self.flags:
            base = base + [f for f, _ in self.flags if f in self._toggled]
        return base


def _build_catalogue() -> list[tuple[str, list[MenuItem]]]:
    """Return [(group_title, [MenuItem, ...]), ...]."""

    init_item = MenuItem(
        label="init", rank="1★", desc="Initialize your skill tree",
        argv=["init"],
        flags=[("--force", "Force re-init"), ("--yes", "Skip confirmations")],
    )

    scan_item = MenuItem(
        label="scan", rank="2★", desc="Detect skills in your codebase",
        argv=["scan"],
        flags=[
            ("--all", "Scan all paths"),
            ("--json", "Output JSON"),
            ("--quiet", "Suppress output"),
        ],
    )

    push_item = MenuItem(
        label="push", rank="3★", desc="Propose skills to the registry",
        argv=["push"],
        flags=[
            ("--dry-run", "Show what would be pushed"),
            ("--no-issue", "Skip GitHub issue"),
            ("--yes", "Skip confirmations"),
        ],
    )

    tree_item = MenuItem(
        label="tree", rank="5★", desc="Visualize your skill tree",
        argv=["tree"],
        flags=[
            ("--named", "Show named skills"),
            ("--title", "Show title"),
            ("--canon", "Show canonical data"),
            ("--all", "Show all skills"),
        ],
    )

    promote_item = MenuItem(
        label="promote", rank="5★", desc="Rank up a detected skill",
        argv=["promote"],
        flags=[
            ("--all", "Promote all candidates"),
            ("--unique", "Unique skills only"),
        ],
    )

    graph_item = MenuItem(
        label="graph", rank="1★", desc="Open skills graph",
        argv=["graph"],
        flags=[
            ("--canon", "Show canonical graph"),
            ("--all", "Include all nodes"),
        ],
    )

    stats_item = MenuItem(
        label="stats", rank="4★", desc="Show statistics",
        argv=["stats"],
        flags=[("--canon", "Show canonical stats")],
    )

    skills_item = MenuItem(
        label="skills", rank="6★", desc="Manage named skills",
        argv=["skills"],
        children=[
            MenuItem(label="list",      rank="6★", desc="List available named skills",   argv=["skills", "list"]),
            MenuItem(label="search",    rank="6★", desc="Search named skills",           argv=["skills", "search"]),
            MenuItem(label="install",   rank="6★", desc="Install a named skill",         argv=["skills", "install"]),
            MenuItem(label="uninstall", rank="6★", desc="Uninstall a named skill",       argv=["skills", "uninstall"]),
            MenuItem(label="info",      rank="6★", desc="Show named skill info",         argv=["skills", "info"]),
            MenuItem(label="update",    rank="3★", desc="Update installed skills",       argv=["skills", "update"]),
        ],
    )

    dev_item = MenuItem(
        label="dev", rank="0★", desc="Developer/registry tools",
        argv=["dev"],
        children=[
            MenuItem(label="list",  rank="0★", desc="List registry skills",   argv=["dev", "list"]),
            MenuItem(label="audit", rank="0★", desc="Audit registry",         argv=["dev", "audit"]),
            MenuItem(label="diff",  rank="0★", desc="Show registry diff",     argv=["dev", "diff"]),
        ],
    )

    docs_item = MenuItem(
        label="docs", rank="2★", desc="Build documentation",
        argv=["docs"],
        children=[
            MenuItem(label="build", rank="2★", desc="Build docs site", argv=["docs", "build"]),
        ],
    )

    getting_started = [init_item, scan_item, push_item]

    daily = [
        tree_item,
        promote_item,
        MenuItem(label="fuse",    rank="5★", desc="Create a skill fusion",  argv=["fuse"]),
        MenuItem(label="pull",    rank="3★", desc="Fetch latest registry",  argv=["pull"]),
        MenuItem(label="appraise",rank="4★", desc="Appraise a skill",       argv=["appraise"]),
        stats_item,
        MenuItem(label="path",    rank="5★", desc="Show unlock path to a skill", argv=["path"]),
        MenuItem(label="lookup",  rank="2★", desc="Look up a skill",        argv=["lookup"]),
    ]

    skills_group = [skills_item]

    utilities = [
        MenuItem(label="whoami",  rank="2★", desc="Show identity and auth status", argv=["whoami"]),
        MenuItem(label="version", rank="1★", desc="Print version",                 argv=["version"]),
        MenuItem(label="update",  rank="3★", desc="Update CLI and registry",       argv=["update"]),
        MenuItem(label="mcp",     rank="3★", desc="Print MCP server config",       argv=["mcp"]),
        graph_item,
        docs_item,
        dev_item,
    ]

    return [
        ("Getting started", getting_started),
        ("Daily", daily),
        ("Skills", skills_group),
        ("Utilities", utilities),
    ]


# ── Logo art ──────────────────────────────────────────────────────────────────

# Diamond-framed G: diamond strokes are apex-gold #fbbf24; G is shimmer-animated.
# Each row is a list of (char, role) where role is "diamond", "G", or "space".
# Built once, queried each frame.

def _build_logo_rows() -> list[list[tuple[str, str]]]:
    """Return per-character annotated rows for the combined diamond+G logo."""
    # We draw a 9-line diamond (height) wide enough to contain the G.
    # Format chosen to look clean at 80-col width.
    raw = [
        #          0123456789012345678901234
        "        ◆               ",  # apex
        "      ◆   ◆             ",
        "    ◆       ◆  ╔═════╗  ",  # G top bar
        "  ◆           ◆║         ",  # G open side
        "◆               ◆║  ╔══╣ ",  # G crossbar
        "  ◆           ◆║      ║ ",  # G inner right
        "    ◆       ◆  ╚═════╝  ",  # G bottom bar
        "      ◆   ◆             ",
        "        ◆               ",  # nadir
    ]
    rows: list[list[tuple[str, str]]] = []
    # Mark each cell
    G_CHARS = set("╔═╗║╣╚╝")
    DIAMOND_CHARS = set("◆")
    for line in raw:
        row: list[tuple[str, str]] = []
        for ch in line:
            if ch in DIAMOND_CHARS:
                row.append((ch, "diamond"))
            elif ch in G_CHARS:
                row.append((ch, "G"))
            else:
                row.append((ch, "space"))
        rows.append(row)
    return rows


_LOGO_ROWS: list[list[tuple[str, str]]] = _build_logo_rows()


def _shimmer_color(phase: float, col: int, total_cols: int) -> str:
    """Return hex color for a G cell, driven by shimmer phase."""
    from gaia_cli.formatting import _RAINBOW_STOPS
    stops = _RAINBOW_STOPS
    n = len(stops)
    # Position in gradient: offset by phase to create flow
    pos = ((col / max(total_cols - 1, 1)) + phase) % 1.0
    scaled = pos * (n - 1)
    idx = int(scaled)
    frac = scaled - idx
    if idx >= n - 1:
        c = stops[-1]
    else:
        c1, c2 = stops[idx], stops[idx + 1]
        c = (
            int(c1[0] + frac * (c2[0] - c1[0])),
            int(c1[1] + frac * (c2[1] - c1[1])),
            int(c1[2] + frac * (c2[2] - c1[2])),
        )
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"


def _logo_fragments(phase: float, animated: bool) -> list[tuple[str, str]]:
    """Return a FormattedText fragment list for the logo."""
    GOLD = "#fbbf24"
    DIM  = "#4b5563"

    # Count total G-role columns for shimmer width
    g_cols = [col for row in _LOGO_ROWS for col, (ch, role) in enumerate(row) if role == "G"]
    total_g = len(g_cols) or 1

    frags: list[tuple[str, str]] = []
    g_idx = 0
    for row in _LOGO_ROWS:
        frags.append(("", "  "))  # left margin
        for ch, role in row:
            if role == "diamond":
                frags.append((f"fg:{GOLD} bold", ch))
            elif role == "G":
                if animated:
                    color = _shimmer_color(phase, g_idx, total_g)
                    frags.append((f"fg:{color} bold", ch))
                else:
                    frags.append((f"fg:{GOLD} bold", ch))
                g_idx += 1
            else:
                frags.append(("", ch))
        frags.append(("", "\n"))

    # Version line
    try:
        from importlib.metadata import version as _ver
        ver = _ver("gaia-cli")
        frags.append((f"fg:{DIM}", f"  GAIA · v{ver}\n"))
    except Exception:
        frags.append((f"fg:{DIM}", "  GAIA\n"))

    frags.append(("", "\n"))
    return frags


# ── Rank color helpers ─────────────────────────────────────────────────────────

def _rank_hex(rank: str) -> str:
    from gaia_cli.formatting import rank_hex
    return rank_hex(rank)


# ── Menu rendering ─────────────────────────────────────────────────────────────

@dataclass
class _MenuFrame:
    title: str
    items: list[MenuItem]   # navigable items (no separator objects)
    groups: list[tuple[str, list[MenuItem]]] | None  # root-level grouping
    cursor: int = 0
    parent_item: MenuItem | None = None  # item that opened this frame (for flag frames)

    def clamp(self) -> None:
        n = len(self.items)
        if n == 0:
            self.cursor = 0
        else:
            self.cursor = max(0, min(self.cursor, n - 1))


def _menu_fragments(frame: _MenuFrame, is_flag_frame: bool = False) -> list[tuple[str, str]]:
    """Render the current menu frame as FormattedText fragments."""
    GOLD  = "#fbbf24"
    DIM   = "#4b5563"
    SEP   = "#374151"

    frags: list[tuple[str, str]] = []

    if is_flag_frame and frame.parent_item:
        parent = frame.parent_item
        frags.append((f"fg:{GOLD} bold", f"  {parent.label}  "))
        frags.append((f"fg:{DIM}", "flags\n"))
        frags.append((f"fg:{DIM}", "  Toggle flags then press ⏎ to run\n\n"))
    elif frame.title and frame.groups is None:
        frags.append((f"fg:{GOLD} bold", f"  {frame.title}\n\n"))

    if frame.groups is not None:
        # Root frame with group separators
        flat_idx = 0
        for group_title, group_items in frame.groups:
            frags.append((f"fg:{SEP}", f"  ── {group_title} {'─' * max(1, 38 - len(group_title))}\n"))
            for item in group_items:
                _append_item_row(frags, item, flat_idx, frame, is_flag_frame=False)
                flat_idx += 1
            frags.append(("", "\n"))
    else:
        for idx, item in enumerate(frame.items):
            _append_item_row(frags, item, idx, frame, is_flag_frame)

    return frags


def _append_item_row(
    frags: list,
    item: MenuItem,
    idx: int,
    frame: _MenuFrame,
    is_flag_frame: bool,
) -> None:
    GOLD  = "#fbbf24"
    DIM   = "#4b5563"
    WHITE = "#e2e8f0"

    selected = (idx == frame.cursor)
    rank_color = _rank_hex(item.rank)

    if is_flag_frame:
        # item.label is the flag string (e.g. "--named")
        toggled = item.label in (frame.parent_item._toggled if frame.parent_item else set())
        check = "◉" if toggled else "○"
        check_color = GOLD if toggled else DIM
        if selected:
            frags.append((f"fg:{GOLD} bold", "  ❯ "))
            frags.append((f"fg:{check_color} bold", f"{check} "))
            frags.append((f"fg:{WHITE} bold", f"{item.label:<16}"))
            frags.append((f"fg:{DIM}", f" {item.desc}"))
        else:
            frags.append(("", "      "))
            frags.append((f"fg:{check_color}", f"{check} "))
            frags.append((f"fg:{WHITE}", f"{item.label:<16}"))
            frags.append((f"fg:{DIM}", f" {item.desc}"))
    else:
        has_sub = (item.children is not None) or (item.flags is not None)
        arrow = " ❯" if has_sub else "  "
        if selected:
            frags.append((f"fg:{GOLD} bold", "  ❯ "))
            frags.append((f"fg:{rank_color} bold", f"{item.label:<16}"))
            frags.append(("fg:#94a3b8", f" {item.desc}"))
            frags.append((f"fg:{DIM}", arrow))
        else:
            frags.append(("", "    "))
            frags.append((f"fg:{rank_color}", f"{item.label:<16}"))
            frags.append((f"fg:{DIM}", f" {item.desc}"))
            frags.append((f"fg:{DIM}", arrow))
    frags.append(("", "\n"))


def _footer_fragments(stack_depth: int, is_flag_frame: bool) -> list[tuple[str, str]]:
    DIM = "#4b5563"
    if is_flag_frame:
        hint = "↑↓ move · space toggle · ⏎ run · ← back · esc quit"
    elif stack_depth > 1:
        hint = "↑↓ move · → submenu · ← back · ⏎ run · esc quit"
    else:
        hint = "↑↓ move · → submenu/flags · ⏎ run · esc quit"
    return [(f"fg:{DIM}", f"\n  {hint}\n")]


# ── Application ────────────────────────────────────────────────────────────────

def _is_truecolor() -> bool:
    ct = os.environ.get("COLORTERM", "").lower()
    return ct in ("truecolor", "24bit")


def run_selector(parser) -> None:
    """Show the Gaia command selector. Falls back to parser.print_help() if not interactive."""
    if not _has_interactive():
        parser.print_help()
        return

    try:
        from prompt_toolkit import Application
        from prompt_toolkit.buffer import Buffer
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import Layout
        from prompt_toolkit.layout.containers import HSplit, Window
        from prompt_toolkit.layout.controls import FormattedTextControl
        from prompt_toolkit.output import ColorDepth
        from prompt_toolkit.styles import Style
    except ImportError:
        parser.print_help()
        return

    no_color = bool(os.environ.get("NO_COLOR"))
    animated = (not no_color) and _is_truecolor()

    # Build menu model
    catalogue = _build_catalogue()
    # Flatten all items for root frame
    all_root_items: list[MenuItem] = []
    for _, items in catalogue:
        all_root_items.extend(items)

    root_frame = _MenuFrame(
        title="",
        items=all_root_items,
        groups=catalogue,
        cursor=0,
    )
    stack: list[_MenuFrame] = [root_frame]

    result_argv: list[str] | None = None

    # ── Key bindings ────────────────────────────────────────────────────────

    kb = KeyBindings()

    @kb.add("up")
    def _up(event):
        frame = stack[-1]
        if frame.cursor > 0:
            frame.cursor -= 1

    @kb.add("down")
    def _down(event):
        frame = stack[-1]
        if frame.cursor < len(frame.items) - 1:
            frame.cursor += 1

    @kb.add("right")
    def _right(event):
        frame = stack[-1]
        if not frame.items:
            return
        item = frame.items[frame.cursor]
        is_flag = frame.parent_item is not None and frame.groups is None and frame.parent_item.flags is not None

        if is_flag:
            return  # already in flag frame; right does nothing

        if item.children:
            child_frame = _MenuFrame(
                title=item.label,
                items=item.children,
                groups=None,
                cursor=0,
                parent_item=item,
            )
            stack.append(child_frame)
        elif item.flags:
            # Build flag items
            flag_items = [
                MenuItem(label=flag, rank="0★", desc=desc, argv=None)
                for flag, desc in item.flags
            ]
            flag_frame = _MenuFrame(
                title=item.label,
                items=flag_items,
                groups=None,
                cursor=0,
                parent_item=item,
            )
            stack.append(flag_frame)

    @kb.add("left")
    def _left(event):
        if len(stack) > 1:
            stack.pop()

    @kb.add("space")
    def _space(event):
        frame = stack[-1]
        if not frame.items or frame.parent_item is None:
            return
        # Only toggle in flag frames
        if frame.parent_item.flags is None:
            return
        flag = frame.items[frame.cursor].label
        toggled = frame.parent_item._toggled
        if flag in toggled:
            toggled.discard(flag)
        else:
            toggled.add(flag)

    @kb.add("enter")
    def _enter(event):
        nonlocal result_argv
        frame = stack[-1]
        if not frame.items:
            return
        item = frame.items[frame.cursor]
        is_flag_frame = (frame.parent_item is not None and frame.parent_item.flags is not None)

        if is_flag_frame:
            # Run parent command with toggled flags
            parent = frame.parent_item
            base = parent.argv or parent.label.split()
            flags = [f for f, _ in (parent.flags or []) if f in parent._toggled]
            result_argv = base + flags
        else:
            result_argv = item.effective_argv()

        event.app.exit()

    @kb.add("escape")
    @kb.add("c-c")
    @kb.add("q")
    def _quit(event):
        event.app.exit()

    # ── Layout ──────────────────────────────────────────────────────────────

    def _get_logo_text():
        phase = (time.monotonic() * 0.4) % 1.0 if animated else 0.0
        return _logo_fragments(phase, animated=animated)

    def _get_menu_text():
        frame = stack[-1]
        is_flag = (frame.parent_item is not None and
                   frame.parent_item.flags is not None and
                   frame.groups is None)
        frags = _menu_fragments(frame, is_flag_frame=is_flag)
        frags += _footer_fragments(len(stack), is_flag)
        return frags

    logo_window = Window(
        content=FormattedTextControl(text=_get_logo_text),
        dont_extend_height=True,
    )
    menu_window = Window(
        content=FormattedTextControl(text=_get_menu_text),
    )

    layout = Layout(HSplit([logo_window, menu_window]))

    style = Style.from_dict({
        "": "#e2e8f0",
    })

    color_depth = ColorDepth.DEPTH_24_BIT if (animated or not no_color) else ColorDepth.DEPTH_8_BIT

    app: Application = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        color_depth=color_depth,
        refresh_interval=0.1 if animated else None,
        full_screen=False,
        mouse_support=False,
    )

    try:
        app.run()
    except KeyboardInterrupt:
        pass

    if result_argv:
        argv0 = sys.argv[0]
        os.execvp(argv0, [argv0] + result_argv)

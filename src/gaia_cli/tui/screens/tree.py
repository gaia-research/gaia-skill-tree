"""Skill tree screen — navigable RPG-style dependency graph.

Left panel: collapsible Textual Tree, tier-colored.
Right panel: reactive skill detail card.
"""

from __future__ import annotations

import json
import os
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Tree, Static, Input
from textual.widgets.tree import TreeNode
from textual.reactive import reactive
from textual import events, on
from rich.text import Text

from gaia_cli.tui import tokens as T


def _load_graph(registry_path: str) -> dict:
    path = os.path.join(registry_path, "registry", "gaia.json")
    if not os.path.exists(path):
        return {"skills": [], "edges": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_tree_data(
    graph: dict,
    owned_ids: set[str],
    detected_ids: set[str],
) -> dict:
    """Build adjacency structures for tree rendering."""
    skills = {s["id"]: s for s in graph.get("skills", [])}
    edges = graph.get("edges", [])

    # prereq edges: src is prerequisite of tgt
    # We want: parent -> children (derivatives)
    children: dict[str, list[str]] = {}
    parents: dict[str, list[str]] = {}
    for e in edges:
        if e.get("edgeType") == "prerequisite":
            src, tgt = e["sourceSkillId"], e["targetSkillId"]
            children.setdefault(src, []).append(tgt)
            parents.setdefault(tgt, []).append(src)

    # Root skills: those that are not a prerequisite of anything
    # (they have no parents — or we use field-level prerequisites)
    all_ids = set(skills.keys())
    has_parent = set(parents.keys())
    roots = sorted(all_ids - has_parent, key=lambda x: (
        {"ultimate": 0, "unique": 1, "extra": 2, "basic": 3}.get(
            skills.get(x, {}).get("type", "basic"), 4
        ),
        x,
    ))

    return {
        "skills": skills,
        "children": children,
        "parents": parents,
        "roots": roots,
        "owned_ids": owned_ids,
        "detected_ids": detected_ids,
    }


def _node_label(skill: dict, owned_ids: set, detected_ids: set) -> Text:
    tid = skill.get("type", "basic")
    glyph = T.GLYPH_BY_TIER.get(tid, "○")
    color = T.TIER_BY_KEY.get(tid, T.NEUTRAL_TEXT_MUTED)
    sid = skill.get("id", "?")
    level = skill.get("level", "")
    owned = sid in owned_ids
    detected = sid in detected_ids

    # Highlight slug with STATE_OWNED if owned or detected
    name_style = T.STATE_OWNED if (owned or detected) else T.NEUTRAL_TEXT

    t = Text()
    t.append(glyph + " ", style=color)
    if "/" in sid:
        contrib, name = sid.split("/", 1)
        t.append("@" + contrib, style=T.BRAND_HONOR_RED)
        t.append("/" + name, style=name_style)
    else:
        t.append(sid, style=name_style)
    if level:
        t.append(f"  {level}", style=T.RANK_BY_STAR.get(level, T.NEUTRAL_BORDER_STRONG))
    if owned:
        t.append("  ✓", style=T.STATE_OWNED)
    elif detected:
        t.append("  ◎", style=T.STATE_DETECTED)
    return t


# ── Detail panel ──────────────────────────────────────────────────────────────

class SkillDetail(Static):
    """Right-panel detail card. Updated reactively on tree focus."""

    skill_id: reactive[str] = reactive("", init=False)

    def __init__(self, tree_data: dict, **kwargs: Any):
        super().__init__("", **kwargs)
        self._tree_data = tree_data

    def watch_skill_id(self, sid: str) -> None:
        self.update(self._build_content(sid))

    def _build_content(self, sid: str) -> Text | str:
        if not sid:
            return Text("Select a skill to see details", style=T.NEUTRAL_TEXT_DIM)

        skills = self._tree_data.get("skills", {})
        skill = skills.get(sid)
        if not skill:
            return Text(sid, style=T.NEUTRAL_TEXT_MUTED)

        tid = skill.get("type", "basic")
        glyph = T.GLYPH_BY_TIER.get(tid, "○")
        color = T.TIER_BY_KEY.get(tid, T.NEUTRAL_TEXT_MUTED)
        level = skill.get("level", "")
        level_color = T.RANK_BY_STAR.get(level, T.NEUTRAL_TEXT_DIM)
        desc = skill.get("description", "")
        name = skill.get("name", sid)

        owned = sid in self._tree_data.get("owned_ids", set())
        detected = sid in self._tree_data.get("detected_ids", set())

        children = self._tree_data.get("children", {}).get(sid, [])
        parents = self._tree_data.get("parents", {}).get(sid, [])

        t = Text()
        t.append(f"{glyph} ", style=color)
        t.append(f"{sid}\n", style=f"bold {color}")
        t.append(f"{name}\n", style=T.NEUTRAL_TEXT_MUTED)
        t.append("\n")

        # Tier + level
        t.append(f"{tid.upper()}  ", style=color)
        if level:
            t.append(f"{level}\n", style=level_color)
        else:
            t.append("\n")
        t.append("\n")

        # Status
        if owned:
            t.append("✓ Owned\n", style=T.STATE_OWNED)
        elif detected:
            t.append("◎ Detected\n", style=T.STATE_DETECTED)
        else:
            t.append("○ Not acquired\n", style=T.NEUTRAL_BORDER_STRONG)
        t.append("\n")

        # Description
        if desc:
            t.append(desc + "\n", style=T.NEUTRAL_TEXT)
            t.append("\n")

        # Prerequisites (parents)
        if parents:
            t.append("Requires:\n", style=T.NEUTRAL_TEXT_MUTED)
            for p in parents[:6]:
                p_skill = skills.get(p, {})
                p_tid = p_skill.get("type", "basic")
                p_color = T.TIER_BY_KEY.get(p_tid, T.NEUTRAL_TEXT_MUTED)
                t.append(f"  {T.GLYPH_BY_TIER.get(p_tid, '○')} {p}\n", style=p_color)
            if len(parents) > 6:
                t.append(f"  … +{len(parents) - 6} more\n", style=T.NEUTRAL_TEXT_DIM)
            t.append("\n")

        # Unlocks (children)
        if children:
            t.append("Unlocks:\n", style=T.NEUTRAL_TEXT_MUTED)
            for c in children[:6]:
                c_skill = skills.get(c, {})
                c_tid = c_skill.get("type", "basic")
                c_color = T.TIER_BY_KEY.get(c_tid, T.NEUTRAL_TEXT_MUTED)
                t.append(f"  {T.GLYPH_BY_TIER.get(c_tid, '○')} {c}\n", style=c_color)
            if len(children) > 6:
                t.append(f"  … +{len(children) - 6} more\n", style=T.NEUTRAL_TEXT_DIM)

        return t


# ── Skill tree screen ─────────────────────────────────────────────────────────

class SkillTreeScreen(Screen):
    """Navigable skill dependency tree with detail panel."""

    BINDINGS = [
        Binding("a", "goto_agent", "Agent", show=True),
        Binding("q", "quit_app", "Quit", show=True),
        Binding("i", "install_focused", "Install", show=True),
        Binding("escape", "clear_search", "Clear", show=False),
        Binding("space", "toggle_node", "Expand", show=True),
        Binding("ctrl+f", "focus_search", "Search", show=False),
    ]

    search_query: reactive[str] = reactive("", init=False)

    def __init__(self, registry_path: str, owned_ids: set[str], detected_ids: set[str]):
        super().__init__()
        self.registry_path = registry_path
        self._owned = owned_ids
        self._detected = detected_ids
        self._tree_data: dict = {}
        self._node_map: dict[int, str] = {}  # node_id -> skill_id

    def compose(self) -> ComposeResult:
        with Static(id="header"):
            yield Static("  ◆ GAIA ", id="header-logo")
            yield Static("SKILL TREE", id="header-section")

        with Static(id="search-container"):
            yield Input(placeholder="Search skills…", id="tree-search")

        with Container(id="tree-layout"):
            with ScrollableContainer(id="tree-panel"):
                yield Tree("Skills", id="skill-tree")
            yield SkillDetail({}, id="detail-panel")

        with Static(id="status-bar"):
            yield Static("", id="status-counts")
            yield Static(
                "[dim]↑↓[/] navigate  [dim]Space[/] expand  [dim]i[/] install  [dim]a[/] agent",
                id="status-hints",
            )

    def on_mount(self) -> None:
        graph = _load_graph(self.registry_path)
        self._tree_data = _build_tree_data(graph, self._owned, self._detected)
        self._populate_tree()
        detail = self.query_one("#detail-panel", SkillDetail)
        detail._tree_data = self._tree_data

        # Status counts
        skills = self._tree_data.get("skills", {})
        owned = len(self._owned)
        detected = len(self._detected)
        total = len(skills)
        self.query_one("#status-counts", Static).update(
            f"  [b]{owned}[/] owned  [b]{detected}[/] detected  [dim]of {total}[/]"
        )

    @on(events.Resize)
    def on_resize(self, event: events.Resize) -> None:
        """Handle screen resize to toggle mobile layout."""
        if event.size.width < 85:
            self.add_class("-mobile")
        else:
            self.remove_class("-mobile")

    def _populate_tree(self, query: str = "") -> None:
        tree = self.query_one("#skill-tree", Tree)
        tree.clear()
        tree.root.expand()

        skills = self._tree_data["skills"]
        children = self._tree_data["children"]
        roots = self._tree_data["roots"]
        owned = self._tree_data["owned_ids"]
        detected = self._tree_data["detected_ids"]

        # Pre-filter: which nodes should be visible?
        visible_nodes: set[str] = set()
        if query:
            q = query.lower()
            # 1. Direct matches
            matches = {
                sid for sid, s in skills.items()
                if q in sid.lower() or q in s.get("description", "").lower()
            }
            # 2. Ancestors of matches (to maintain hierarchy)
            for sid in matches:
                curr = sid
                while curr:
                    visible_nodes.add(curr)
                    # For simplicity, just pick first parent if multi
                    p_list = self._tree_data["parents"].get(curr, [])
                    curr = p_list[0] if p_list else None
        else:
            visible_nodes = set(skills.keys())

        # Group roots by tier for visual structure
        tier_order = {"ultimate": 0, "unique": 1, "extra": 2, "basic": 3}
        tier_roots: dict[str, list[str]] = {t: [] for t in tier_order}
        for sid in roots:
            if sid not in visible_nodes:
                continue
            skill = skills.get(sid, {})
            tier = skill.get("type", "basic")
            tier_roots.setdefault(tier, []).append(sid)

        tier_labels = {
            "ultimate": ("◆ ULTIMATES", T.TIER_ULTIMATE),
            "unique":   ("◉ UNIQUES",   T.TIER_UNIQUE),
            "extra":    ("◇ EXTRAS",    T.TIER_EXTRA),
            "basic":    ("○ BASICS",    T.TIER_BASIC),
        }

        visited: set[str] = set()

        def add_children(node: TreeNode, sid: str, depth: int = 0) -> None:
            # When searching, we want to expand matches automatically
            should_expand_all = bool(query)

            for child_id in sorted(children.get(sid, []), key=lambda x: (
                tier_order.get(skills.get(x, {}).get("type", "basic"), 4), x
            )):
                if child_id not in visible_nodes or child_id in visited:
                    continue
                visited.add(child_id)
                child_skill = skills.get(child_id, {"id": child_id, "type": "basic"})
                label = _node_label(child_skill, owned, detected)
                has_kids = any(k in visible_nodes for k in children.get(child_id, []))
                
                # Expand if search is active
                is_expanded = should_expand_all and has_kids
                child_node = node.add(label, data=child_id, expand=is_expanded, allow_expand=has_kids)
                self._node_map[id(child_node)] = child_id
                
                # Recurse if search is active or it's a root expand
                if has_kids:
                    if should_expand_all or depth < 1:
                        add_children(child_node, child_id, depth + 1)

        for tier in ["ultimate", "unique", "extra", "basic"]:
            sids = tier_roots.get(tier, [])
            if not sids:
                continue
            label_text, color = tier_labels[tier]
            tier_node = tree.root.add(
                Text(label_text, style=f"bold {color}"),
                data=f"__tier_{tier}",
                expand=True,
            )
            for sid in sorted(sids):
                if sid in visited:
                    continue
                visited.add(sid)
                skill = skills.get(sid, {"id": sid, "type": tier})
                label = _node_label(skill, owned, detected)
                has_kids = any(k in visible_nodes for k in children.get(sid, []))
                
                skill_node = tier_node.add(
                    label,
                    data=sid,
                    expand=bool(query) and has_kids,
                    allow_expand=has_kids,
                )
                self._node_map[id(skill_node)] = sid
                if has_kids:
                    if query or tier in ("ultimate", "unique"):
                        add_children(skill_node, sid, depth=1)

    @on(Input.Changed, "#tree-search")
    def _on_search_change(self, event: Input.Changed) -> None:
        self._populate_tree(event.value.strip())

    def action_clear_search(self) -> None:
        inp = self.query_one("#tree-search", Input)
        if inp.value:
            inp.value = ""
        else:
            self.action_goto_agent()

    def action_focus_search(self) -> None:
        self.query_one("#tree-search", Input).focus()

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        sid = event.node.data
        if sid and not str(sid).startswith("__tier_"):
            detail = self.query_one("#detail-panel", SkillDetail)
            detail.skill_id = str(sid)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        # Toggle expand/collapse on select
        node = event.node
        if node.allow_expand:
            if node.is_expanded:
                node.collapse()
            else:
                node.expand()

    def action_toggle_node(self) -> None:
        tree = self.query_one("#skill-tree", Tree)
        node = tree.cursor_node
        if node and node.allow_expand:
            if node.is_expanded:
                node.collapse()
            else:
                node.expand()

    def action_install_focused(self) -> None:
        tree = self.query_one("#skill-tree", Tree)
        node = tree.cursor_node
        if node and node.data and not str(node.data).startswith("__tier_"):
            sid = str(node.data)
            skills = self._tree_data.get("skills", {})
            skill = skills.get(sid, {"id": sid, "type": "basic", "level": ""})
            from gaia_cli.tui.screens.agent import InstallModal

            def _on_install(installed: bool) -> None:
                if installed:
                    self._owned.add(sid)
                    self._rebuild_node_label(node, sid)

            self.app.push_screen(
                InstallModal(skill, self.registry_path),
                callback=_on_install,
            )

    def _rebuild_node_label(self, node: TreeNode, sid: str) -> None:
        skills = self._tree_data.get("skills", {})
        skill = skills.get(sid, {"id": sid, "type": "basic"})
        node.set_label(_node_label(skill, self._owned, self._detected))

    def action_goto_agent(self) -> None:
        from gaia_cli.tui.screens.agent import AgentScreen
        # app.py has _load_meta
        from gaia_cli.tui.app import _load_meta
        _, username, version = _load_meta()
        self.app.switch_screen(AgentScreen(self.registry_path, username, version))

    def action_quit_app(self) -> None:
        self.app.exit()

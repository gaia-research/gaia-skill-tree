"""Tests for timeline routing: gaia dev timeline with --user should write to named skill
file (not user tree) when the skill_id resolves to a named skill.

Regression guard for the bug where meta_timeline_command unconditionally called
append_skill_tree_event when --user was supplied, even for named skill IDs like
'mattpocock/skills' that live in registry/named/.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure src is importable
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))


# ---------------------------------------------------------------------------
# Helpers to build minimal fixture registries
# ---------------------------------------------------------------------------

def _make_registry(tmp_path: Path, *, with_named: bool = True) -> Path:
    """Create a minimal registry fixture under tmp_path/registry."""
    registry = tmp_path / "registry"
    nodes = registry / "nodes" / "basic"
    nodes.mkdir(parents=True)
    named = registry / "named" / "testuser"
    named.mkdir(parents=True)

    # Generic node (simple ID, no slash)
    (nodes / "generic-skill.json").write_text(
        json.dumps({
            "id": "generic-skill",
            "name": "Generic Skill",
            "type": "basic",
            "level": "1★",
            "description": "A generic skill",
            "status": "provisional",
            "prerequisites": [],
            "derivatives": [],
            "evidence": [],
            "knownAgents": [],
            "createdAt": "2026-06-01",
            "updatedAt": "2026-06-01",
            "version": "0.1.0",
        }),
        encoding="utf-8",
    )

    if with_named:
        # Named skill with composite id (slash-separated)
        (named / "myskill.md").write_text(
            "---\n"
            "id: testuser/myskill\n"
            "name: My Named Skill\n"
            "contributor: testuser\n"
            "origin: true\n"
            "genericSkillRef: generic-skill\n"
            "status: named\n"
            "level: 2★\n"
            "description: A named skill for testing\n"
            "---\n"
            "\n# Testuser / My Skill\n",
            encoding="utf-8",
        )

    return tmp_path


# ---------------------------------------------------------------------------
# Tests for _named_skill_file helper
# ---------------------------------------------------------------------------

class TestNamedSkillFile:
    def test_returns_path_for_slash_id(self, tmp_path):
        from gaia_cli.timeline import _named_skill_file

        root = _make_registry(tmp_path)
        result = _named_skill_file("testuser/myskill", registry_path=str(root))
        assert result is not None
        assert result.name == "myskill.md"

    def test_returns_none_for_unknown_id(self, tmp_path):
        from gaia_cli.timeline import _named_skill_file

        root = _make_registry(tmp_path)
        result = _named_skill_file("nonexistent/skill", registry_path=str(root))
        assert result is None

    def test_returns_none_for_generic_node_id(self, tmp_path):
        from gaia_cli.timeline import _named_skill_file

        root = _make_registry(tmp_path)
        # 'generic-skill' has no slash so no direct guess; won't match frontmatter
        result = _named_skill_file("generic-skill", registry_path=str(root))
        assert result is None


# ---------------------------------------------------------------------------
# Test: append_skill_event writes to named skill .md, not node JSON
# ---------------------------------------------------------------------------

class TestAppendSkillEventRouting:
    def test_timeline_named_skill_routes_to_named_file(self, tmp_path):
        """append_skill_event with a named skill ID must write to the .md file."""
        from gaia_cli.timeline import append_skill_event

        root = _make_registry(tmp_path)
        named_md = root / "registry" / "named" / "testuser" / "myskill.md"
        original_content = named_md.read_text(encoding="utf-8")

        # The named skill file should not contain a timeline yet
        assert "timeline:" not in original_content

        append_skill_event(
            "testuser/myskill",
            "demote",
            "testuser",
            "Test demote event",
            registry_path=str(root),
        )

        updated_content = named_md.read_text(encoding="utf-8")
        assert "timeline:" in updated_content
        assert "demote" in updated_content

        # Generic node must NOT be touched
        node_json = root / "registry" / "nodes" / "basic" / "generic-skill.json"
        node_data = json.loads(node_json.read_text(encoding="utf-8"))
        assert "timeline" not in node_data


# ---------------------------------------------------------------------------
# Test: meta_timeline_command with --user routes to user tree even for named skill
# ---------------------------------------------------------------------------

class TestMetaTimelineCommandRouting:
    def _make_args(self, skill_id, action, notes, user, registry, timestamp=None, no_build=True):
        args = MagicMock()
        args.skill_id = skill_id
        args.action = action
        args.notes = notes
        args.user = user
        args.registry = registry
        args.timestamp = timestamp
        args.no_build = no_build
        return args

    def test_timeline_with_user_routes_to_user_tree_when_skill_is_named(self, tmp_path):
        """meta_timeline_command with --user must write to the user tree, even for named IDs."""
        from gaia_cli.commands.dev import meta_timeline_command

        root = _make_registry(tmp_path)
        named_md = root / "registry" / "named" / "testuser" / "myskill.md"
        before_named = named_md.read_text(encoding="utf-8")
        user_tree_dir = root / "skill-trees" / "mbtiongson1"
        user_tree_dir.mkdir(parents=True)
        user_tree = user_tree_dir / "skill-tree.json"
        user_tree.write_text(
            json.dumps({"username": "mbtiongson1", "unlockedSkills": [], "timeline": []}),
            encoding="utf-8",
        )

        args = self._make_args(
            skill_id="testuser/myskill",
            action="demote",
            notes="apex gate failed",
            user="mbtiongson1",
            registry=str(root),
            no_build=True,
        )

        meta_timeline_command(args)

        assert named_md.read_text(encoding="utf-8") == before_named
        tree_data = json.loads(user_tree.read_text(encoding="utf-8"))
        assert any(
            ev.get("action") == "demote" and ev.get("skillId") == "testuser/myskill"
            for ev in tree_data.get("timeline", [])
        )

    def test_timeline_with_user_routes_to_user_tree_for_generic_skill(self, tmp_path):
        """meta_timeline_command with --user must write to user tree for generic skill IDs."""
        from gaia_cli.commands.dev import meta_timeline_command

        root = _make_registry(tmp_path)

        # Create a user tree for mbtiongson1
        user_tree_dir = root / "skill-trees" / "mbtiongson1"
        user_tree_dir.mkdir(parents=True)
        user_tree_file = user_tree_dir / "skill-tree.json"
        user_tree_file.write_text(
            json.dumps({
                "username": "mbtiongson1",
                "unlockedSkills": [],
                "timeline": [],
            }),
            encoding="utf-8",
        )

        args = self._make_args(
            skill_id="generic-skill",
            action="note",
            notes="Testing generic routing",
            user="mbtiongson1",
            registry=str(root),
            no_build=True,
        )

        meta_timeline_command(args)

        tree_data = json.loads(user_tree_file.read_text(encoding="utf-8"))
        timeline = tree_data.get("timeline", [])
        assert any(ev.get("action") == "note" and ev.get("skillId") == "generic-skill" for ev in timeline)

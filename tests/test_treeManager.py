"""Tests for src/gaia_cli/treeManager.py — path-traversal rejection and show_tree modes."""

import json
import os
import pytest

from gaia_cli.treeManager import load_tree, save_tree, show_tree


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_tree(tmp_path, username, data):
    user_dir = tmp_path / "skill-trees" / username
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "skill-tree.json").write_text(json.dumps(data))


_SAMPLE_TREE = {
    "userId": "alice",
    "updatedAt": "2026-01-01",
    "unlockedSkills": [],
    "pendingCombinations": [],
    "stats": {"totalUnlocked": 0, "highestRarity": "common", "deepestLineage": 0},
}


# ---------------------------------------------------------------------------
# load_tree — valid username
# ---------------------------------------------------------------------------


class TestLoadTreeValid:
    def test_returns_tree_for_valid_username(self, tmp_path):
        _write_tree(tmp_path, "alice", _SAMPLE_TREE)
        result = load_tree("alice", registry_path=str(tmp_path))
        assert result is not None
        assert result["userId"] == "alice"

    def test_returns_none_when_file_missing(self, tmp_path):
        result = load_tree("alice", registry_path=str(tmp_path))
        assert result is None

    def test_accepts_username_with_dots_and_hyphens(self, tmp_path):
        _write_tree(tmp_path, "alice.bob-99", _SAMPLE_TREE)
        result = load_tree("alice.bob-99", registry_path=str(tmp_path))
        assert result is not None


# ---------------------------------------------------------------------------
# load_tree — invalid username
# ---------------------------------------------------------------------------


class TestLoadTreeInvalid:
    @pytest.mark.parametrize("bad", [
        "../evil",
        "../../etc/passwd",
        "",
        "/root",
        "foo/bar",
        "foo bar",
        "foo\x00bar",
        ".hidden",
    ])
    def test_raises_for_path_traversal(self, tmp_path, bad):
        with pytest.raises(ValueError, match="Invalid username"):
            load_tree(bad, registry_path=str(tmp_path))


# ---------------------------------------------------------------------------
# save_tree — valid username
# ---------------------------------------------------------------------------


class TestSaveTreeValid:
    def test_writes_tree_to_correct_path(self, tmp_path):
        save_tree("alice", _SAMPLE_TREE, registry_path=str(tmp_path))
        expected = tmp_path / "skill-trees" / "alice" / "skill-tree.json"
        assert expected.exists()
        data = json.loads(expected.read_text())
        assert data["userId"] == "alice"

    def test_creates_parent_directories(self, tmp_path):
        save_tree("newuser", _SAMPLE_TREE, registry_path=str(tmp_path))
        assert (tmp_path / "skill-trees" / "newuser" / "skill-tree.json").exists()


# ---------------------------------------------------------------------------
# save_tree — invalid username
# ---------------------------------------------------------------------------


class TestSaveTreeInvalid:
    @pytest.mark.parametrize("bad", [
        "../evil",
        "../../etc/passwd",
        "",
        "/root",
        "foo/bar",
    ])
    def test_raises_for_path_traversal(self, tmp_path, bad):
        with pytest.raises(ValueError, match="Invalid username"):
            save_tree(bad, _SAMPLE_TREE, registry_path=str(tmp_path))


# ---------------------------------------------------------------------------
# show_tree — display modes
# ---------------------------------------------------------------------------

_GRAPH_DATA = {
    "skills": [
        {"id": "web-search", "name": "Web Search", "type": "basic", "level": "1★", "prerequisites": []},
        {"id": "summarize",  "name": "Summarize",  "type": "basic", "level": "0★", "prerequisites": []},
        {"id": "research",   "name": "Research",   "type": "extra", "level": "3★", "prerequisites": ["web-search", "summarize"]},
    ]
}

_TREE_DATA = {
    "userId": "testuser",
    "updatedAt": "2026-01-01",
    "unlockedSkills": [
        {"skillId": "web-search", "level": "1★"},
        {"skillId": "summarize",  "level": "0★"},
        {"skillId": "research",   "level": "3★"},
    ],
    "pendingCombinations": [],
    "stats": {},
}


def _make_named_index(tmp_path, buckets):
    named_dir = tmp_path / "registry"
    named_dir.mkdir(parents=True, exist_ok=True)
    (named_dir / "named-skills.json").write_text(json.dumps({"generatedAt": "2026-01-01", "buckets": buckets, "awaitingClassification": [], "byContributor": {}}))


class TestShowTreeModes:
    def test_default_shows_slash_slugs(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        show_tree(_TREE_DATA, graph_data=_GRAPH_DATA, registry_path=str(tmp_path), mode="default")
        out = capsys.readouterr().out
        assert "/research" in out
        assert "/web-search" in out
        assert "Research" not in out  # display name should not appear in default mode

    def test_title_shows_display_names(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        show_tree(_TREE_DATA, graph_data=_GRAPH_DATA, registry_path=str(tmp_path), mode="title")
        out = capsys.readouterr().out
        assert "Research" in out
        assert "Web Search" in out
        assert "/research" not in out

    def test_default_shows_named_contributor_id(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        _make_named_index(tmp_path, {
            "research": [{"id": "alice/deep-research", "name": "Deep Research", "contributor": "alice",
                          "origin": True, "genericSkillRef": "research", "status": "named",
                          "level": "3★", "description": ""}]
        })
        show_tree(_TREE_DATA, graph_data=_GRAPH_DATA, registry_path=str(tmp_path), mode="default")
        out = capsys.readouterr().out
        assert "alice/deep-research" in out
        # Generic skills without a named impl still show slash form
        assert "/web-search" in out

    def test_named_mode_filters_to_named_only(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        _make_named_index(tmp_path, {
            "research": [{"id": "alice/deep-research", "name": "Deep Research", "contributor": "alice",
                          "origin": True, "genericSkillRef": "research", "status": "named",
                          "level": "3★", "description": ""}]
        })
        show_tree(_TREE_DATA, graph_data=_GRAPH_DATA, registry_path=str(tmp_path), mode="named")
        out = capsys.readouterr().out
        assert "alice/deep-research" in out
        # Unnamed skills should not appear
        assert "/web-search" not in out
        assert "/summarize" not in out

    def test_named_mode_empty_when_no_named_skills(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        show_tree(_TREE_DATA, graph_data=_GRAPH_DATA, registry_path=str(tmp_path), mode="named")
        out = capsys.readouterr().out
        # Only username header, no skill lines
        assert "testuser" in out
        assert "├" not in out and "└" not in out

    def test_tree_connectors_present(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        show_tree(_TREE_DATA, graph_data=_GRAPH_DATA, registry_path=str(tmp_path), mode="title")
        out = capsys.readouterr().out
        assert "├" in out or "└" in out


class TestTreeRenderFixes:
    def test_fusion_candidate_color(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        custom_state_dir = tmp_path / ".gaia"
        custom_state_dir.mkdir(parents=True, exist_ok=True)
        custom_state = {
            "customSkills": [],
            "customFusions": {
                "/feature-pipeline": {
                    "sources": ["/fp-drift"],
                    "type": "extra",
                    "level": "0★"
                }
            }
        }
        (custom_state_dir / "custom_state.json").write_text(json.dumps(custom_state))
        
        graph_data = {
            "skills": [
                {"id": "fp-drift", "name": "FP Drift", "type": "basic", "level": "0★", "prerequisites": []}
            ]
        }
        tree_data = {
            "userId": "testuser",
            "unlockedSkills": [
                {"skillId": "/feature-pipeline"},
                {"skillId": "/fp-drift"}
            ],
            "stats": {}
        }
        
        monkeypatch.setenv("FORCE_COLOR", "1")
        monkeypatch.setenv("COLORTERM", "truecolor")
        show_tree(tree_data, graph_data=graph_data, registry_path=str(tmp_path), custom=True)
        out = capsys.readouterr().out
        
        # Target fusion should use extra purple color (TIER_COLORS["extra"] = (192, 132, 252))
        assert "\033[38;2;192;132;252m" in out

    def test_unowned_skill_formatting(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        graph_data = {
            "skills": [
                {"id": "unowned-skill", "name": "Unowned Skill", "type": "basic", "level": "3★", "prerequisites": []},
                {"id": "root-skill", "name": "Root Skill", "type": "basic", "level": "1★", "prerequisites": ["unowned-skill"]}
            ]
        }
        tree_data = {
            "userId": "testuser",
            "unlockedSkills": [
                {"skillId": "root-skill"}
            ],
            "stats": {}
        }
        monkeypatch.setenv("FORCE_COLOR", "1")
        monkeypatch.setenv("COLORTERM", "truecolor")
        show_tree(tree_data, graph_data=graph_data, registry_path=str(tmp_path))
        out = capsys.readouterr().out
        
        # 1. do not include the "-> name/skill-slug", only the star
        assert "-> unowned-skill" not in out
        assert "-> /unowned-skill" not in out
        assert "/??? 3★" in out
        
        # 2. inherit the color of the skill it is tied to (3★ rank color is (167, 139, 250))
        assert "\033[38;2;167;139;250m" in out

    def test_owned_starless_slate_blue(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        graph_data = {
            "skills": [
                {"id": "starless-skill", "name": "Starless Skill", "type": "basic", "level": "0★", "prerequisites": []}
            ]
        }
        tree_data = {
            "userId": "testuser",
            "unlockedSkills": [
                {"skillId": "starless-skill"}
            ],
            "stats": {}
        }
        monkeypatch.setenv("FORCE_COLOR", "1")
        monkeypatch.setenv("COLORTERM", "truecolor")
        show_tree(tree_data, graph_data=graph_data, registry_path=str(tmp_path))
        out = capsys.readouterr().out
        
        # Owned starless should always be slate blue: (106, 90, 205)
        assert "\033[38;2;106;90;205m" in out

    def test_owned_named_honor_red(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        _make_named_index(tmp_path, {
            "named-skill": [{"id": "alice/named-skill", "name": "Named Skill", "contributor": "alice",
                             "origin": False, "genericSkillRef": "named-skill", "status": "named",
                             "level": "2★", "description": ""}]
        })
        graph_data = {
            "skills": [
                {"id": "named-skill", "name": "Named Skill", "type": "basic", "level": "2★", "prerequisites": []}
            ]
        }
        tree_data = {
            "userId": "testuser",
            "unlockedSkills": [
                {"skillId": "named-skill"}
            ],
            "stats": {}
        }
        monkeypatch.setenv("FORCE_COLOR", "1")
        monkeypatch.setenv("COLORTERM", "truecolor")
        show_tree(tree_data, graph_data=graph_data, registry_path=str(tmp_path))
        out = capsys.readouterr().out
        
        # Owned named skills should show honor red handle (COLOR_CONTRIBUTOR = (239, 68, 68))
        assert "\033[38;2;239;68;68m" in out

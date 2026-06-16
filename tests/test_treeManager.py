"""Tests for src/gaia_cli/treeManager.py — path-traversal rejection and show_tree modes."""

import json
import os
import pytest

from gaia_cli.treeManager import load_tree, save_tree, show_tree, prune_to_subset


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
    "stats": {"totalUnlocked": 0, "deepestLineage": 0},
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
        """Unowned prerequisites render as /??? with their rank color.

        The /??? teaser is only rendered when known_only=False, because
        show_tree's default (known_only=True) hides all unowned prerequisites to
        keep the tree clean. The `known_only` parameter was introduced in commit
        5d1c9aaa alongside the reveal-unowned logic; passing known_only=False is
        the correct way to exercise this code path. (The test was added in the
        same commit but mistakenly called show_tree without known_only=False.)
        """
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
        # known_only=False is required to reveal unowned prerequisites as /???
        show_tree(tree_data, graph_data=graph_data, registry_path=str(tmp_path), known_only=False)
        out = capsys.readouterr().out

        # 1. do not show the full skill slug or its star count inline with the node
        assert "-> unowned-skill" not in out
        assert "-> /unowned-skill" not in out
        assert "/???" in out
        # "3★" may appear in the legend (rank chips), but must NOT appear adjacent
        # to the /??? entry — the unowned node label is just "/???" without stars.
        assert "/??? 3★" not in out
        assert "/???  3★" not in out

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
        
        # Owned starless should always be slate: (148, 163, 184)
        assert "\033[38;2;148;163;184m" in out

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


# ---------------------------------------------------------------------------
# prune_to_subset — unit tests for the narrowing helper
# ---------------------------------------------------------------------------

# Graph layout used by subset tests:
#
#   ultimate-skill  (ultimate, has two extras as prerequisites)
#       ├── extra-a  (extra, requires basic-a + basic-b)
#       │       ├── basic-a  (basic)
#       │       └── basic-b  (basic)
#       └── extra-b  (extra, requires basic-c + basic-d)
#               ├── basic-c  (basic)
#               └── basic-d  (basic)
#
# Total 7 skills: 1 ultimate, 2 extras, 4 basics.

_SUBSET_SKILL_MAP = {
    "ultimate-skill": {"id": "ultimate-skill", "type": "ultimate", "level": "3★", "prerequisites": ["extra-a", "extra-b"]},
    "extra-a":        {"id": "extra-a",        "type": "extra",    "level": "2★", "prerequisites": ["basic-a", "basic-b"]},
    "extra-b":        {"id": "extra-b",        "type": "extra",    "level": "2★", "prerequisites": ["basic-c", "basic-d"]},
    "basic-a":        {"id": "basic-a",        "type": "basic",    "level": "1★", "prerequisites": []},
    "basic-b":        {"id": "basic-b",        "type": "basic",    "level": "1★", "prerequisites": []},
    "basic-c":        {"id": "basic-c",        "type": "basic",    "level": "1★", "prerequisites": []},
    "basic-d":        {"id": "basic-d",        "type": "basic",    "level": "1★", "prerequisites": []},
}

_ALL_SKILL_IDS = set(_SUBSET_SKILL_MAP.keys())


class TestPruneToSubset:
    """Unit tests for prune_to_subset — the path-narrowing helper."""

    def test_none_subset_returns_full_set(self):
        """When path_subset is None the full node_ids set comes back unchanged."""
        result = prune_to_subset(_ALL_SKILL_IDS, _SUBSET_SKILL_MAP, None)
        assert result == _ALL_SKILL_IDS

    def test_basic_narrow_three_skill_path(self):
        """Subset of {ultimate-skill, extra-a, basic-a} keeps them plus the
        ancestor path from ultimate-skill down through extra-a to basic-a.
        Sibling branch extra-b and its leaves basic-c / basic-d are absent."""
        subset = {"ultimate-skill", "extra-a", "basic-a"}
        result = prune_to_subset(_ALL_SKILL_IDS, _SUBSET_SKILL_MAP, subset)
        # All three requested nodes must appear.
        assert "ultimate-skill" in result
        assert "extra-a" in result
        assert "basic-a" in result
        # basic-b is extra-a's sibling leaf — it is NOT in the subset and has no
        # subset descendant, so it should be absent.
        assert "basic-b" not in result
        # entire extra-b branch must be absent
        assert "extra-b" not in result
        assert "basic-c" not in result
        assert "basic-d" not in result

    def test_empty_subset_returns_empty(self):
        """An empty subset set means no node qualifies — result is empty."""
        result = prune_to_subset(_ALL_SKILL_IDS, _SUBSET_SKILL_MAP, set())
        assert result == set()

    def test_full_coverage_subset_equals_full_tree(self):
        """When the subset equals every node in the tree the result is the full set."""
        result = prune_to_subset(_ALL_SKILL_IDS, _SUBSET_SKILL_MAP, _ALL_SKILL_IDS)
        assert result == _ALL_SKILL_IDS

    def test_unrelated_subset_ids_return_empty(self):
        """IDs that do not appear anywhere in node_ids or skill_map yield nothing."""
        result = prune_to_subset(_ALL_SKILL_IDS, _SUBSET_SKILL_MAP, {"ghost-skill", "phantom"})
        assert result == set()

    def test_leaf_only_subset_keeps_full_ancestor_chain(self):
        """Selecting a single leaf keeps every ancestor node on the path to it."""
        # basic-a is reachable via: ultimate-skill -> extra-a -> basic-a
        result = prune_to_subset(_ALL_SKILL_IDS, _SUBSET_SKILL_MAP, {"basic-a"})
        assert "basic-a" in result
        assert "extra-a" in result
        assert "ultimate-skill" in result
        # sibling branch must be absent
        assert "extra-b" not in result
        assert "basic-b" not in result
        assert "basic-c" not in result
        assert "basic-d" not in result


# ---------------------------------------------------------------------------
# show_tree with path_subset — integration tests
# ---------------------------------------------------------------------------

# 3-level graph: root → mid → leaf + a sibling branch root → mid → sibling-leaf
_NARROW_GRAPH = {
    "skills": [
        {"id": "ultimate-skill", "name": "Ultimate",     "type": "ultimate", "level": "3★",
         "prerequisites": ["extra-a", "extra-b"]},
        {"id": "extra-a",        "name": "Extra A",      "type": "extra",    "level": "2★",
         "prerequisites": ["basic-a", "basic-b"]},
        {"id": "extra-b",        "name": "Extra B",      "type": "extra",    "level": "2★",
         "prerequisites": ["basic-c", "basic-d"]},
        {"id": "basic-a",        "name": "Basic A",      "type": "basic",    "level": "1★",
         "prerequisites": []},
        {"id": "basic-b",        "name": "Basic B",      "type": "basic",    "level": "1★",
         "prerequisites": []},
        {"id": "basic-c",        "name": "Basic C",      "type": "basic",    "level": "1★",
         "prerequisites": []},
        {"id": "basic-d",        "name": "Basic D",      "type": "basic",    "level": "1★",
         "prerequisites": []},
    ]
}

_NARROW_TREE = {
    "userId": "narrowuser",
    "updatedAt": "2026-01-01",
    "unlockedSkills": [
        {"skillId": "ultimate-skill", "level": "3★"},
        {"skillId": "extra-a",        "level": "2★"},
        {"skillId": "extra-b",        "level": "2★"},
        {"skillId": "basic-a",        "level": "1★"},
        {"skillId": "basic-b",        "level": "1★"},
        {"skillId": "basic-c",        "level": "1★"},
        {"skillId": "basic-d",        "level": "1★"},
    ],
    "pendingCombinations": [],
    "stats": {},
}


class TestShowTreePathSubset:
    """Integration tests for show_tree's path_subset parameter."""

    def test_backward_compat_no_subset(self, tmp_path, monkeypatch, capsys):
        """Calling show_tree without path_subset renders the full tree (no regression)."""
        monkeypatch.chdir(tmp_path)
        show_tree(_NARROW_TREE, graph_data=_NARROW_GRAPH, registry_path=str(tmp_path))
        out = capsys.readouterr().out
        assert "/ultimate-skill" in out
        assert "/extra-a" in out
        assert "/extra-b" in out
        assert "/basic-a" in out
        assert "/basic-c" in out

    def test_narrow_subset_shows_only_path_and_ancestors(self, tmp_path, monkeypatch, capsys):
        """path_subset={ultimate-skill, extra-a, basic-a} keeps the path branch
        and drops sibling branch extra-b, basic-b, basic-c, basic-d."""
        monkeypatch.chdir(tmp_path)
        subset = {"ultimate-skill", "extra-a", "basic-a"}
        show_tree(_NARROW_TREE, graph_data=_NARROW_GRAPH, registry_path=str(tmp_path),
                  path_subset=subset)
        out = capsys.readouterr().out
        assert "/ultimate-skill" in out
        assert "/extra-a" in out
        assert "/basic-a" in out
        # sibling branch must be absent
        assert "/extra-b" not in out
        assert "/basic-b" not in out
        assert "/basic-c" not in out
        assert "/basic-d" not in out

    def test_empty_subset_produces_no_skill_lines(self, tmp_path, monkeypatch, capsys):
        """path_subset=set() → nothing passes the filter → no tree connectors."""
        monkeypatch.chdir(tmp_path)
        show_tree(_NARROW_TREE, graph_data=_NARROW_GRAPH, registry_path=str(tmp_path),
                  path_subset=set())
        out = capsys.readouterr().out
        # No tree connectors means no skill lines were rendered.
        assert "├" not in out and "└" not in out

    def test_full_subset_equals_unnarrowed_render(self, tmp_path, monkeypatch, capsys):
        """path_subset equal to all skill IDs produces the same output as no subset."""
        monkeypatch.chdir(tmp_path)
        all_ids = {s["id"] for s in _NARROW_GRAPH["skills"]}
        show_tree(_NARROW_TREE, graph_data=_NARROW_GRAPH, registry_path=str(tmp_path),
                  path_subset=all_ids)
        out_narrow = capsys.readouterr().out

        show_tree(_NARROW_TREE, graph_data=_NARROW_GRAPH, registry_path=str(tmp_path))
        out_full = capsys.readouterr().out

        assert out_narrow == out_full

    def test_unrelated_subset_produces_no_skill_lines(self, tmp_path, monkeypatch, capsys):
        """path_subset of IDs not in the tree → nothing rendered."""
        monkeypatch.chdir(tmp_path)
        show_tree(_NARROW_TREE, graph_data=_NARROW_GRAPH, registry_path=str(tmp_path),
                  path_subset={"ghost-skill", "phantom"})
        out = capsys.readouterr().out
        assert "├" not in out and "└" not in out

"""Tests for gaia_cli.pathEngine."""

import json
import os

import pytest

from gaia_cli.pathEngine import (
    compute_paths,
    diff_paths,
    load_paths,
    save_paths,
    regenerate_paths,
    PATHS_FILE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mini_graph():
    """Mini graph: 3 basic + 2 extra skills."""
    return {
        "skills": [
            {
                "id": "skill-a",
                "name": "Skill A",
                "type": "basic",
                "level": "0★",
                "prerequisites": [],
                "derivatives": ["skill-d"],
            },
            {
                "id": "skill-b",
                "name": "Skill B",
                "type": "basic",
                "level": "0★",
                "prerequisites": [],
                "derivatives": ["skill-d", "skill-e"],
            },
            {
                "id": "skill-c",
                "name": "Skill C",
                "type": "basic",
                "level": "0★",
                "prerequisites": [],
                "derivatives": ["skill-e"],
            },
            {
                "id": "skill-d",
                "name": "Skill D",
                "type": "extra",
                "level": "1★",
                "prerequisites": ["skill-a", "skill-b"],
                "derivatives": [],
            },
            {
                "id": "skill-e",
                "name": "Skill E",
                "type": "extra",
                "level": "1★",
                "prerequisites": ["skill-b", "skill-c"],
                "derivatives": [],
            },
        ]
    }


# ---------------------------------------------------------------------------
# compute_paths tests
# ---------------------------------------------------------------------------

class TestComputePaths:
    def test_near_unlocks_all_prereqs_met(self, mini_graph):
        """Skill D should be near-unlock when both A and B are available."""
        owned = ["skill-a", "skill-b"]
        detected = []
        result = compute_paths(mini_graph, owned, detected)

        near_ids = [e["skillId"] for e in result["nearUnlocks"]]
        assert "skill-d" in near_ids
        # skill-e is missing skill-c, so NOT near-unlock
        assert "skill-e" not in near_ids

    def test_near_unlocks_with_detected(self, mini_graph):
        """detected_ids count toward prerequisite satisfaction."""
        owned = ["skill-a"]
        detected = ["skill-b"]
        result = compute_paths(mini_graph, owned, detected)

        near_ids = [e["skillId"] for e in result["nearUnlocks"]]
        assert "skill-d" in near_ids

    def test_one_away_detection(self, mini_graph):
        """Skill E should be one-away when only B is available (missing C)."""
        owned = ["skill-b"]
        detected = []
        result = compute_paths(mini_graph, owned, detected)

        one_away_entries = {e["skillId"]: e for e in result["oneAway"]}
        assert "skill-e" in one_away_entries
        assert one_away_entries["skill-e"]["missingPrereq"] == "skill-c"
        assert one_away_entries["skill-e"]["satisfiedPrereqs"] == ["skill-b"]

    def test_one_away_not_when_zero_missing(self, mini_graph):
        """Skill D should NOT be in oneAway if all prereqs are met."""
        owned = ["skill-a", "skill-b"]
        detected = []
        result = compute_paths(mini_graph, owned, detected)

        one_away_ids = [e["skillId"] for e in result["oneAway"]]
        assert "skill-d" not in one_away_ids

    def test_already_owned_excluded(self, mini_graph):
        """Skills already owned should not appear in nearUnlocks or oneAway."""
        owned = ["skill-a", "skill-b", "skill-d"]
        detected = []
        result = compute_paths(mini_graph, owned, detected)

        near_ids = [e["skillId"] for e in result["nearUnlocks"]]
        one_away_ids = [e["skillId"] for e in result["oneAway"]]
        assert "skill-d" not in near_ids
        assert "skill-d" not in one_away_ids

    def test_basic_skills_excluded(self, mini_graph):
        """Basic skills never appear in nearUnlocks or oneAway."""
        owned = []
        detected = []
        result = compute_paths(mini_graph, owned, detected)

        all_ids = (
            [e["skillId"] for e in result["nearUnlocks"]]
            + [e["skillId"] for e in result["oneAway"]]
        )
        for sid in ["skill-a", "skill-b", "skill-c"]:
            assert sid not in all_ids

    def test_available_paths_bfs_distance(self, mini_graph):
        """BFS from owned skill-a should find skill-d at distance 1."""
        owned = ["skill-a"]
        detected = []
        result = compute_paths(mini_graph, owned, detected)

        paths_map = {e["skillId"]: e["distance"] for e in result["availablePaths"]}
        assert "skill-d" in paths_map
        assert paths_map["skill-d"] == 1

    def test_available_paths_excludes_owned(self, mini_graph):
        """BFS should not include already-owned skills in availablePaths."""
        owned = ["skill-a", "skill-d"]
        detected = []
        result = compute_paths(mini_graph, owned, detected)

        paths_ids = [e["skillId"] for e in result["availablePaths"]]
        assert "skill-a" not in paths_ids
        assert "skill-d" not in paths_ids

    def test_available_paths_multi_hop(self):
        """BFS correctly computes multi-hop distances."""
        graph = {
            "skills": [
                {"id": "s1", "name": "S1", "type": "basic", "prerequisites": [], "derivatives": ["s2"]},
                {"id": "s2", "name": "S2", "type": "extra", "prerequisites": ["s1"], "derivatives": ["s3"]},
                {"id": "s3", "name": "S3", "type": "extra", "prerequisites": ["s2"], "derivatives": ["s4"]},
                {"id": "s4", "name": "S4", "type": "ultimate", "prerequisites": ["s3"], "derivatives": []},
            ]
        }
        result = compute_paths(graph, ["s1"], [])
        paths_map = {e["skillId"]: e["distance"] for e in result["availablePaths"]}
        assert paths_map["s2"] == 1
        assert paths_map["s3"] == 2
        assert paths_map["s4"] == 3

    def test_available_paths_capped_at_max_distance(self):
        """BFS should not go beyond MAX_BFS_DISTANCE=5."""
        skills = []
        for i in range(8):
            skills.append({
                "id": f"s{i}",
                "name": f"S{i}",
                "type": "basic" if i == 0 else "extra",
                "prerequisites": [f"s{i-1}"] if i > 0 else [],
                "derivatives": [f"s{i+1}"] if i < 7 else [],
            })
        graph = {"skills": skills}
        result = compute_paths(graph, ["s0"], [])
        paths_map = {e["skillId"]: e["distance"] for e in result["availablePaths"]}
        # Distance 5 should be reachable
        assert paths_map.get("s5") == 5
        # Distance 6 should not be
        assert "s6" not in paths_map

    def test_computed_at_present(self, mini_graph):
        """Result should include a computedAt ISO timestamp."""
        result = compute_paths(mini_graph, [], [])
        assert "computedAt" in result
        # Should be parseable as ISO format
        from datetime import datetime
        datetime.fromisoformat(result["computedAt"])

    def test_path_entries_include_effective_level_metadata(self):
        graph = {
            "skills": [
                {"id": "skill-a", "name": "Skill A", "type": "basic", "level": "0★", "prerequisites": [], "derivatives": []},
                {"id": "skill-b", "name": "Skill B", "type": "basic", "level": "0★", "prerequisites": [], "derivatives": []},
                {
                    "id": "skill-fusion",
                    "name": "Skill Fusion",
                    "type": "extra",
                    "level": "3★",
                    "demerits": ["experimental-feature"],
                    "prerequisites": ["skill-a", "skill-b"],
                    "derivatives": [],
                },
            ]
        }
        result = compute_paths(graph, ["skill-a"], [])
        one_away = result["oneAway"][0]
        assert one_away["levelFloor"] == "2★"
        assert one_away["baseLevelFloor"] == "3★"
        assert one_away["effectiveLevelFloor"] == "2★"
        assert one_away["levelMeta"]["baseLevel"] == "3★"
        assert one_away["levelMeta"]["effectiveLevel"] == "2★"

        result = compute_paths(graph, ["skill-a", "skill-b"], [])
        entry = result["nearUnlocks"][0]
        assert entry["levelFloor"] == "2★"
        assert entry["baseLevelFloor"] == "3★"
        assert entry["effectiveLevelFloor"] == "2★"
        assert entry["levelMeta"]["baseLevel"] == "3★"
        assert entry["levelMeta"]["effectiveLevel"] == "2★"


# ---------------------------------------------------------------------------
# Yggdrasil II fusion-detection (structural, type-independent) — regression
# for #1220/#1221: filters keyed on retired ('extra','ultimate') matched
# nothing against the ratified {basic, fusion} schema.
# ---------------------------------------------------------------------------

class TestYggIIFusionDetection:
    @pytest.fixture
    def ygg2_graph(self):
        """Ygg II graph: 2 basic + 1 fusion (type='fusion', >=1 prereq)."""
        return {
            "skills": [
                {"id": "base-a", "name": "Base A", "type": "basic", "level": "0★", "prerequisites": [], "derivatives": ["combo"]},
                {"id": "base-b", "name": "Base B", "type": "basic", "level": "0★", "prerequisites": [], "derivatives": ["combo"]},
                {"id": "combo", "name": "Combo", "type": "fusion", "level": "1★", "prerequisites": ["base-a", "base-b"], "derivatives": []},
            ]
        }

    def test_fusion_near_unlock(self, ygg2_graph):
        """A type='fusion' node whose prereqs are owned is a near-unlock."""
        result = compute_paths(ygg2_graph, ["base-a", "base-b"], [])
        near_ids = [e["skillId"] for e in result["nearUnlocks"]]
        assert "combo" in near_ids

    def test_fusion_one_away(self, ygg2_graph):
        """A type='fusion' node missing one prereq is one-away."""
        result = compute_paths(ygg2_graph, ["base-a"], [])
        one_away = {e["skillId"]: e for e in result["oneAway"]}
        assert "combo" in one_away
        assert one_away["combo"]["missingPrereq"] == "base-b"

    def test_basic_with_prereqs_is_structural_fusion(self):
        """Composite membership is STRUCTURAL: a node carrying >=1 prereq is a
        fusion regardless of its type literal (do NOT consult `type`)."""
        graph = {
            "skills": [
                {"id": "a", "name": "A", "type": "basic", "prerequisites": [], "derivatives": []},
                # legacy-shaped node whose type literal is not 'fusion' but has a prereq:
                {"id": "c", "name": "C", "type": "basic", "prerequisites": ["a"], "derivatives": []},
            ]
        }
        result = compute_paths(graph, ["a"], [])
        near_ids = [e["skillId"] for e in result["nearUnlocks"]]
        assert "c" in near_ids

    def test_zero_prereq_never_composite(self):
        """A node with no prerequisites is never near-unlock/one-away even if
        its type literal is 'fusion' (structural rule: len(prereqs) >= 1)."""
        graph = {
            "skills": [
                {"id": "lonely", "name": "Lonely", "type": "fusion", "prerequisites": [], "derivatives": []},
            ]
        }
        result = compute_paths(graph, [], [])
        all_ids = (
            [e["skillId"] for e in result["nearUnlocks"]]
            + [e["skillId"] for e in result["oneAway"]]
        )
        assert "lonely" not in all_ids


# ---------------------------------------------------------------------------
# diff_paths tests
# ---------------------------------------------------------------------------

class TestDiffPaths:
    def test_diff_detects_new_near_unlocks(self):
        old = {"nearUnlocks": [{"skillId": "x"}], "oneAway": []}
        new = {"nearUnlocks": [{"skillId": "x"}, {"skillId": "y", "satisfiedPrereqs": ["a"]}], "oneAway": []}
        diff = diff_paths(old, new)
        assert "y" in diff["new_near_unlocks"]
        assert "x" not in diff["new_near_unlocks"]

    def test_diff_detects_new_one_away(self):
        old = {"nearUnlocks": [], "oneAway": [{"skillId": "a"}]}
        new = {"nearUnlocks": [], "oneAway": [{"skillId": "a"}, {"skillId": "b"}]}
        diff = diff_paths(old, new)
        assert "b" in diff["new_one_away"]
        assert "a" not in diff["new_one_away"]

    def test_diff_with_none_old_first_run(self):
        """When old_paths is None (first run), everything is new."""
        new = {
            "nearUnlocks": [{"skillId": "x", "satisfiedPrereqs": ["p1"]}],
            "oneAway": [{"skillId": "y"}],
        }
        diff = diff_paths(None, new)
        assert "x" in diff["new_near_unlocks"]
        assert "y" in diff["new_one_away"]

    def test_diff_promotions_available(self):
        """Prereqs of newly near-unlocked skills are promotion candidates."""
        old = {"nearUnlocks": [], "oneAway": []}
        new = {
            "nearUnlocks": [{"skillId": "combo", "satisfiedPrereqs": ["base-a", "base-b"]}],
            "oneAway": [],
        }
        diff = diff_paths(old, new)
        assert "base-a" in diff["promotions_available"]
        assert "base-b" in diff["promotions_available"]

    def test_diff_no_changes(self):
        paths = {"nearUnlocks": [{"skillId": "x", "satisfiedPrereqs": []}], "oneAway": [{"skillId": "y"}]}
        diff = diff_paths(paths, paths)
        assert diff["new_near_unlocks"] == []
        assert diff["new_one_away"] == []
        assert diff["promotions_available"] == []


# ---------------------------------------------------------------------------
# save_paths / load_paths round-trip
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_load_round_trip(self, tmp_path, monkeypatch):
        """save_paths then load_paths should return the same data."""
        paths_file = str(tmp_path / ".gaia" / "paths.json")
        monkeypatch.setattr("gaia_cli.pathEngine.PATHS_FILE", paths_file)

        data = {
            "nearUnlocks": [{"skillId": "test-skill", "satisfiedPrereqs": ["a", "b"]}],
            "oneAway": [],
            "availablePaths": [{"skillId": "far", "name": "Far", "distance": 3}],
            "computedAt": "2026-01-01T00:00:00+00:00",
            "userId": "testuser",
        }
        save_paths(data)
        loaded = load_paths()
        assert loaded == data

    def test_load_paths_returns_none_when_missing(self, tmp_path, monkeypatch):
        """load_paths returns None when the file does not exist."""
        monkeypatch.setattr("gaia_cli.pathEngine.PATHS_FILE", str(tmp_path / "nope.json"))
        assert load_paths() is None

    def test_save_paths_creates_directory(self, tmp_path, monkeypatch):
        """save_paths creates the parent directory if it doesn't exist."""
        paths_file = str(tmp_path / "nested" / "dir" / "paths.json")
        monkeypatch.setattr("gaia_cli.pathEngine.PATHS_FILE", paths_file)
        save_paths({"test": True})
        assert os.path.exists(paths_file)


# ---------------------------------------------------------------------------
# regenerate_paths (integration with mocks)
# ---------------------------------------------------------------------------

class TestRegeneratePaths:
    def test_regenerate_paths_end_to_end(self, tmp_path, monkeypatch):
        """Full pipeline with mocked scanner/resolver/tree/graph."""
        # Setup .gaia/config.json
        gaia_dir = tmp_path / ".gaia"
        gaia_dir.mkdir()
        config = {"gaiaUser": "alice", "scanPaths": ["src"]}
        (gaia_dir / "config.json").write_text(json.dumps(config))

        # Setup user tree
        user_dir = tmp_path / "skill-trees" / "alice"
        user_dir.mkdir(parents=True)
        tree = {
            "userId": "alice",
            "unlockedSkills": [
                {"skillId": "web-scrape", "level": "0★"},
                {"skillId": "parse-json", "level": "0★"},
            ],
        }
        (user_dir / "skill-tree.json").write_text(json.dumps(tree))

        # Setup graph
        graph_dir = tmp_path / "registry"
        graph_dir.mkdir()
        graph_data = {
            "skills": [
                {"id": "web-scrape", "name": "Web Scrape", "type": "basic", "prerequisites": [], "derivatives": ["data-pipeline"]},
                {"id": "parse-json", "name": "Parse JSON", "type": "basic", "prerequisites": [], "derivatives": ["data-pipeline"]},
                {"id": "http-client", "name": "HTTP Client", "type": "basic", "prerequisites": [], "derivatives": []},
                {"id": "data-pipeline", "name": "Data Pipeline", "type": "extra", "prerequisites": ["web-scrape", "parse-json"], "derivatives": []},
            ]
        }
        (graph_dir / "gaia.json").write_text(json.dumps(graph_data))

        # Paths file location
        paths_file = str(gaia_dir / "paths.json")
        monkeypatch.setattr("gaia_cli.pathEngine.PATHS_FILE", paths_file)

        # Mock scanner to return a known token (http-client detected in repo)
        monkeypatch.setattr(
            "gaia_cli.pathEngine.scan_repo_detailed",
            lambda: {"tokens": {"http-client"}, "files_scanned": 1, "candidate_count": 1, "paths_found": [], "paths_missing": []},
        )
        monkeypatch.setattr(
            "gaia_cli.pathEngine.load_config",
            lambda: config,
        )

        registry_path = str(tmp_path)
        result = regenerate_paths(registry_path)

        # Verify near-unlocks: data-pipeline has prereqs web-scrape + parse-json (both owned)
        near_ids = [e["skillId"] for e in result["nearUnlocks"]]
        assert "data-pipeline" in near_ids

        # Verify userId and computedAt are present
        assert result["userId"] == "alice"
        assert "computedAt" in result

        # Verify file was written
        assert os.path.exists(paths_file)
        loaded = json.loads(open(paths_file, "r", encoding="utf-8").read())
        assert loaded["userId"] == "alice"

    def test_regenerate_paths_no_config_raises(self, monkeypatch):
        """Should raise RuntimeError when config is missing."""
        monkeypatch.setattr("gaia_cli.pathEngine.load_config", lambda: None)
        with pytest.raises(RuntimeError, match="No .gaia/config.json"):
            regenerate_paths(".")

    def test_regenerate_paths_no_user_raises(self, monkeypatch):
        """Should raise RuntimeError when gaiaUser is not set."""
        monkeypatch.setattr("gaia_cli.pathEngine.load_config", lambda: {"scanPaths": []})
        with pytest.raises(RuntimeError, match="No gaiaUser"):
            regenerate_paths(".")

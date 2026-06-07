"""Tests for gaia_cli.pathEngine unlock-path helpers, combinator chain
fusions, and the `gaia path` CLI command.

Fixture graphs use self-contained inline data so tests remain offline and
independent of registry changes.  Where real IDs are used (CLI smoke tests),
they are verified to exist in registry/gaia.json:
  - agent-environment-setup (extra, prereqs: document-editing, tool-use)
  - advanced-swarm-coordination (extra; prereq multi-agent-debate is itself
    an extra with basic prereqs — a genuine multi-hop chain)
"""

import json
import os
import subprocess
import sys

import pytest

from gaia_cli.pathEngine import unlock_path, render_unlock_path, _path_tree_to_dict
from gaia_cli.combinator import transitive_close, detect_combinations

# ---------------------------------------------------------------------------
# Shared fixture graphs
# ---------------------------------------------------------------------------

@pytest.fixture
def linear_graph():
    """A → B → C (C needs B needs A)."""
    return {
        "skills": [
            {"id": "a", "name": "A", "type": "basic", "level": "0★",
             "prerequisites": [], "derivatives": ["b"]},
            {"id": "b", "name": "B", "type": "extra", "level": "1★",
             "prerequisites": ["a"], "derivatives": ["c"]},
            {"id": "c", "name": "C", "type": "ultimate", "level": "2★",
             "prerequisites": ["b"], "derivatives": []},
        ]
    }


@pytest.fixture
def diamond_graph():
    """Diamond: root → left + right → tip.

    root (basic) ──┐
                   ├──▷ left (extra, needs root)
                   └──▷ right (extra, needs root)
    tip (ultimate, needs left + right)
    """
    return {
        "skills": [
            {"id": "root", "name": "Root", "type": "basic",
             "prerequisites": [], "derivatives": ["left", "right"]},
            {"id": "left", "name": "Left", "type": "extra",
             "prerequisites": ["root"], "derivatives": ["tip"]},
            {"id": "right", "name": "Right", "type": "extra",
             "prerequisites": ["root"], "derivatives": ["tip"]},
            {"id": "tip", "name": "Tip", "type": "ultimate",
             "prerequisites": ["left", "right"], "derivatives": []},
        ]
    }


@pytest.fixture
def chain_fusion_graph():
    """Multi-hop chain for detect_combinations.

    a (basic) + b (basic) → ab (extra)
    ab + c (basic) → abc (ultimate)

    If the user owns a, b, c but NOT ab, detect_combinations should surface
    abc as a chain_fusion candidate (ab is the intermediate step).
    """
    return {
        "skills": [
            {"id": "a", "name": "A", "type": "basic", "level": "0★",
             "prerequisites": [], "derivatives": ["ab"]},
            {"id": "b", "name": "B", "type": "basic", "level": "0★",
             "prerequisites": [], "derivatives": ["ab"]},
            {"id": "c", "name": "C", "type": "basic", "level": "0★",
             "prerequisites": [], "derivatives": ["abc"]},
            {"id": "ab", "name": "AB", "type": "extra", "level": "1★",
             "prerequisites": ["a", "b"], "derivatives": ["abc"]},
            {"id": "abc", "name": "ABC", "type": "ultimate", "level": "2★",
             "prerequisites": ["ab", "c"], "derivatives": []},
        ]
    }


# ---------------------------------------------------------------------------
# transitive_close
# ---------------------------------------------------------------------------

class TestTransitiveClose:
    def test_empty_initial_set(self, chain_fusion_graph):
        """Starting from nothing, no composites unlock."""
        result = transitive_close(chain_fusion_graph, set())
        assert result == set()

    def test_only_basic_skills(self, chain_fusion_graph):
        """Basic skills don't change the set — they have no prerequisites."""
        result = transitive_close(chain_fusion_graph, {"a"})
        # 'a' alone can't unlock 'ab' (needs 'b' too)
        assert result == {"a"}

    def test_single_hop(self, chain_fusion_graph):
        """Owning both prereqs of 'ab' causes it to join the set."""
        result = transitive_close(chain_fusion_graph, {"a", "b"})
        assert "ab" in result

    def test_multi_hop_fixpoint(self, chain_fusion_graph):
        """Owning a, b, c triggers ab, then abc — full transitive closure."""
        result = transitive_close(chain_fusion_graph, {"a", "b", "c"})
        assert "ab" in result
        assert "abc" in result

    def test_partial_chain_stops(self, chain_fusion_graph):
        """If 'c' is missing, 'abc' stays locked even though 'ab' unlocks."""
        result = transitive_close(chain_fusion_graph, {"a", "b"})
        assert "ab" in result
        assert "abc" not in result

    def test_cycle_safe(self):
        """A cycle in prerequisites must not cause an infinite loop."""
        # Contrived graph where two extras reference each other.
        graph = {
            "skills": [
                {"id": "x", "type": "extra", "prerequisites": ["y"], "derivatives": []},
                {"id": "y", "type": "extra", "prerequisites": ["x"], "derivatives": []},
            ]
        }
        # Should return without error; x and y are never added
        # because neither prerequisite set is fully satisfied.
        result = transitive_close(graph, set())
        assert "x" not in result
        assert "y" not in result

    def test_already_owned_not_duplicated(self, chain_fusion_graph):
        """Skills already in the initial set are preserved as-is."""
        result = transitive_close(chain_fusion_graph, {"ab", "a", "b", "c"})
        # abc should now unlock too
        assert "abc" in result
        # ab already in set — still there
        assert "ab" in result

    def test_empty_graph(self):
        result = transitive_close({"skills": []}, {"x"})
        assert result == {"x"}


# ---------------------------------------------------------------------------
# unlock_path
# ---------------------------------------------------------------------------

class TestUnlockPath:
    def test_leaf_basic_skill(self, linear_graph):
        """A leaf basic skill has no children in its path tree."""
        node = unlock_path(linear_graph, "a", set())
        assert node["id"] == "a"
        assert node["owned"] is False
        assert node["children"] == []

    def test_owned_leaf_has_no_children(self, linear_graph):
        """An owned skill stops recursion regardless of prerequisites."""
        # Even though 'b' has prereq 'a', if 'b' is owned we don't recurse.
        node = unlock_path(linear_graph, "b", {"b"})
        assert node["owned"] is True
        assert node["children"] == []

    def test_single_hop_missing(self, linear_graph):
        """Missing skill with one prerequisite has that prereq as its child."""
        node = unlock_path(linear_graph, "b", set())
        assert node["owned"] is False
        assert len(node["children"]) == 1
        assert node["children"][0]["id"] == "a"

    def test_multi_hop_chain(self, linear_graph):
        """Full chain a→b→c shows three levels deep."""
        node = unlock_path(linear_graph, "c", set())
        # c is missing
        assert node["owned"] is False
        # b is a child of c
        b_node = node["children"][0]
        assert b_node["id"] == "b"
        # a is a child of b
        a_node = b_node["children"][0]
        assert a_node["id"] == "a"

    def test_partially_owned(self, linear_graph):
        """Owned nodes stop recursion; their subtrees are absent."""
        node = unlock_path(linear_graph, "c", {"b"})
        # c is not owned; b is owned → b has no children even though a exists
        b_node = node["children"][0]
        assert b_node["owned"] is True
        assert b_node["children"] == []

    def test_unknown_target_raises(self, linear_graph):
        with pytest.raises(ValueError, match="not found in registry"):
            unlock_path(linear_graph, "does-not-exist", set())

    def test_cycle_raises_value_error(self):
        """A real cycle in prerequisite graph raises ValueError."""
        cyclic = {
            "skills": [
                {"id": "x", "type": "extra", "prerequisites": ["y"], "derivatives": []},
                {"id": "y", "type": "extra", "prerequisites": ["x"], "derivatives": []},
            ]
        }
        with pytest.raises(ValueError, match="[Cc]ycle"):
            unlock_path(cyclic, "x", set())

    def test_diamond_all_missing(self, diamond_graph):
        """Diamond with nothing owned: tip has left+right as children."""
        node = unlock_path(diamond_graph, "tip", set())
        child_ids = {c["id"] for c in node["children"]}
        assert child_ids == {"left", "right"}

    def test_root_already_owned(self, diamond_graph):
        """With 'root' owned, left and right recurse to it but stop."""
        node = unlock_path(diamond_graph, "tip", {"root"})
        # left and right are not owned, so they are children
        child_ids = {c["id"] for c in node["children"]}
        assert "left" in child_ids
        assert "right" in child_ids
        for child in node["children"]:
            # Their child is 'root' which IS owned → no grandchildren
            assert child["children"][0]["owned"] is True
            assert child["children"][0]["children"] == []


# ---------------------------------------------------------------------------
# render_unlock_path
# ---------------------------------------------------------------------------

class TestRenderUnlockPath:
    def test_basic_leaf_renders(self, linear_graph):
        text = render_unlock_path(linear_graph, "a", set())
        assert "a" in text
        # leaf has no children, summary should say 0 owned out of 0
        assert "0 / 0" in text

    def test_footer_counts_correct(self, linear_graph):
        text = render_unlock_path(linear_graph, "c", set())
        # 2 prerequisites total (a, b), 0 owned
        assert "0 / 2" in text
        assert "2 skill(s) needed" in text

    def test_footer_with_owned(self, linear_graph):
        # unlock_path stops recursing into owned nodes, so the visible tree
        # for 'c' with owned={'a','b'} is: c(missing) + b(owned, no children).
        # 'a' is not in the tree because b is already owned → recursion stops.
        # Count: 1 prerequisite total (b), 1 owned (b).
        text = render_unlock_path(linear_graph, "c", {"a", "b"})
        assert "1 / 1" in text
        assert "0 skill(s) needed" in text

    def test_owned_only_prunes_owned_branches(self, linear_graph):
        """--owned-only prunes the display of owned 'b' from the output."""
        text = render_unlock_path(linear_graph, "c", {"b"}, owned_only=True)
        # 'b' is owned and pruned from display; only 'c' (missing) remains.
        # The footer still reports the counts from the underlying tree.
        assert "✓ owned" not in text
        # Footer still present even when all children are pruned
        assert "skill(s) needed" in text

    def test_markers_present(self, linear_graph):
        text = render_unlock_path(linear_graph, "c", {"a"})
        assert "✓ owned" in text
        assert "✗ missing" in text

    def test_json_serialisable_via_path_tree_to_dict(self, diamond_graph):
        """_path_tree_to_dict output must round-trip through json.dumps."""
        from gaia_cli.pathEngine import unlock_path, _path_tree_to_dict
        node = unlock_path(diamond_graph, "tip", {"root"})
        skill_map = {s["id"]: s for s in diamond_graph["skills"]}
        out = _path_tree_to_dict(node, skill_map)
        serialised = json.dumps(out)
        restored = json.loads(serialised)
        assert restored["id"] == "tip"
        assert "children" in restored

    def test_unknown_raises(self, linear_graph):
        with pytest.raises(ValueError, match="not found"):
            render_unlock_path(linear_graph, "missing-skill", set())


# ---------------------------------------------------------------------------
# detect_combinations — chain_fusion
# ---------------------------------------------------------------------------

class TestDetectCombinationsChainFusion:
    def test_chain_fusion_detected_when_intermediate_missing(self, chain_fusion_graph):
        """User owns a, b, c but NOT ab → abc should be a chain_fusion candidate."""
        owned = [{"skillId": "a"}, {"skillId": "b"}, {"skillId": "c"}]
        result = detect_combinations(chain_fusion_graph, owned, [])
        # ab should be new_fusion (a+b are owned)
        ab_candidates = [r for r in result if r["candidateResult"] == "ab"]
        assert ab_candidates, "expected 'ab' as new_fusion candidate"
        assert ab_candidates[0]["status"] == "new_fusion"

        # abc should be chain_fusion (ab missing but reachable via a+b)
        abc_candidates = [r for r in result if r["candidateResult"] == "abc"]
        assert abc_candidates, "expected 'abc' as chain_fusion candidate"
        abc = abc_candidates[0]
        assert abc["status"] == "chain_fusion"
        assert "chainSteps" in abc
        assert "ab" in abc["chainSteps"]

    def test_no_chain_fusion_when_directly_available(self, chain_fusion_graph):
        """When 'ab' is owned too, abc should be new_fusion, not chain_fusion."""
        owned = [{"skillId": "a"}, {"skillId": "b"}, {"skillId": "c"}, {"skillId": "ab"}]
        result = detect_combinations(chain_fusion_graph, owned, [])
        abc_candidates = [r for r in result if r["candidateResult"] == "abc"]
        assert abc_candidates, "expected 'abc' as a fusion candidate"
        assert abc_candidates[0]["status"] == "new_fusion"

    def test_no_chain_fusion_when_prereq_unreachable(self, chain_fusion_graph):
        """If 'b' is missing, 'ab' can't be unlocked; abc should not appear."""
        owned = [{"skillId": "a"}, {"skillId": "c"}]
        result = detect_combinations(chain_fusion_graph, owned, [])
        abc_candidates = [r for r in result if r["candidateResult"] == "abc"]
        # abc unreachable because ab needs b which is absent
        assert not abc_candidates, "abc should not appear when 'b' is absent"

    def test_chain_steps_lists_only_composites(self, chain_fusion_graph):
        """chainSteps should only list intermediate extra/ultimate skills."""
        owned = [{"skillId": "a"}, {"skillId": "b"}, {"skillId": "c"}]
        result = detect_combinations(chain_fusion_graph, owned, [])
        abc = next(r for r in result if r["candidateResult"] == "abc")
        for step in abc["chainSteps"]:
            # Each chain step must be extra or ultimate in the graph
            skill_map = {s["id"]: s for s in chain_fusion_graph["skills"]}
            assert skill_map[step]["type"] in ("extra", "ultimate")

    def test_existing_new_fusion_unaffected(self, chain_fusion_graph):
        """Direct fusions still get status new_fusion after chain logic."""
        owned = [{"skillId": "a"}, {"skillId": "b"}, {"skillId": "c"}]
        result = detect_combinations(chain_fusion_graph, owned, [])
        ab_entry = next(r for r in result if r["candidateResult"] == "ab")
        assert ab_entry["status"] == "new_fusion"
        assert "chainSteps" not in ab_entry

    def test_owned_skills_excluded_from_results(self, chain_fusion_graph):
        """Skills already owned must not appear as fusion candidates."""
        owned = [{"skillId": "ab"}]
        result = detect_combinations(chain_fusion_graph, owned, [])
        candidate_ids = {r["candidateResult"] for r in result}
        assert "ab" not in candidate_ids

    def test_detected_skills_count_as_available(self, chain_fusion_graph):
        """detected_skills contribute to prerequisite satisfaction."""
        owned = [{"skillId": "c"}]
        detected = ["a", "b"]
        result = detect_combinations(chain_fusion_graph, owned, detected)
        # ab prereqs are a+b (detected), so new_fusion
        ab_candidates = [r for r in result if r["candidateResult"] == "ab"]
        assert ab_candidates
        assert ab_candidates[0]["status"] == "new_fusion"


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RUN = [sys.executable, "-m", "gaia_cli.main", "--registry", REPO_ROOT]


class TestPathCommandCLI:
    def test_path_exits_zero_for_real_id(self):
        """gaia path agent-environment-setup exits 0."""
        r = subprocess.run(
            _RUN + ["path", "agent-environment-setup"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr

    def test_path_output_contains_skill_id(self):
        """Human-readable output mentions the target skill id."""
        r = subprocess.run(
            _RUN + ["path", "agent-environment-setup"],
            capture_output=True, text=True,
        )
        assert "agent-environment-setup" in r.stdout

    def test_path_output_contains_markers(self):
        """Output includes owned/missing markers."""
        r = subprocess.run(
            _RUN + ["path", "agent-environment-setup"],
            capture_output=True, text=True,
        )
        assert "✓ owned" in r.stdout or "✗ missing" in r.stdout

    def test_path_json_flag_exits_zero(self):
        """gaia path --json exits 0."""
        r = subprocess.run(
            _RUN + ["path", "agent-environment-setup", "--json"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr

    def test_path_json_flag_emits_valid_json(self):
        """--json output parses as valid JSON with expected keys."""
        r = subprocess.run(
            _RUN + ["path", "agent-environment-setup", "--json"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["skillId"] == "agent-environment-setup"
        assert "tree" in data
        assert "ownedIds" in data

    def test_path_slash_form_accepted(self):
        """Leading slash in skill ID is stripped and resolves correctly."""
        r = subprocess.run(
            _RUN + ["path", "/agent-environment-setup"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "agent-environment-setup" in r.stdout

    def test_path_owned_only_flag_accepted(self):
        """--owned-only flag does not crash the command."""
        r = subprocess.run(
            _RUN + ["path", "agent-environment-setup", "--owned-only"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr

    def test_path_unknown_skill_exits_nonzero(self):
        """Unknown skill ID causes exit code 1."""
        r = subprocess.run(
            _RUN + ["path", "this-skill-definitely-does-not-exist"],
            capture_output=True, text=True,
        )
        assert r.returncode == 1
        assert "not found" in r.stderr.lower() or "not found" in r.stdout.lower()

    def test_path_multi_hop_real_skill(self):
        """Multi-hop skill (advanced-swarm-coordination) renders successfully."""
        r = subprocess.run(
            _RUN + ["path", "advanced-swarm-coordination"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        # Root skill should be in output
        assert "advanced-swarm-coordination" in r.stdout
        # Indirect prerequisite should also appear
        assert "multi-agent-debate" in r.stdout

    def test_path_json_tree_has_children(self):
        """JSON tree for a composite skill has non-empty children."""
        r = subprocess.run(
            _RUN + ["path", "agent-environment-setup", "--json"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data["tree"]["children"]) > 0

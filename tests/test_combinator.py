"""Tests for gaia_cli.combinator — Yggdrasil II fusion detection.

Composite membership is STRUCTURAL (taxonomy.isFusion: >=1 prerequisite), not a
`type` literal. These fixtures use the ratified {basic, fusion} type axis and
prove the retired ('extra','ultimate') filters no longer gate detection
(regression for #1220/#1221).
"""

from gaia_cli.combinator import (
    detect_combinations,
    get_combinations,
    transitive_close,
)


def _ygg2_graph():
    """2 basic + 1 direct fusion + 1 chain fusion."""
    return {
        "skills": [
            {"id": "base-a", "name": "Base A", "type": "basic", "level": "0★", "prerequisites": []},
            {"id": "base-b", "name": "Base B", "type": "basic", "level": "0★", "prerequisites": []},
            {"id": "combo", "name": "Combo", "type": "fusion", "level": "1★", "prerequisites": ["base-a", "base-b"]},
            {"id": "apex", "name": "Apex", "type": "fusion", "level": "2★", "prerequisites": ["combo", "base-a"]},
        ]
    }


class TestTransitiveClose:
    def test_expands_through_fusion(self):
        graph = _ygg2_graph()
        # Own both bases -> combo is unlockable -> apex becomes reachable.
        expanded = transitive_close(graph, {"base-a", "base-b"})
        assert "combo" in expanded
        assert "apex" in expanded

    def test_basic_never_added_as_composite(self):
        graph = _ygg2_graph()
        # Basics have no prereqs; they are never introduced by the close.
        expanded = transitive_close(graph, set())
        assert expanded == set()


class TestDetectCombinations:
    def test_direct_fusion_detected(self):
        graph = _ygg2_graph()
        combos = detect_combinations(graph, ["base-a", "base-b"], [])
        results = {c["candidateResult"]: c for c in combos}
        assert "combo" in results
        assert results["combo"]["status"] == "new_fusion"

    def test_chain_fusion_detected(self):
        graph = _ygg2_graph()
        # Owning only the bases: combo is direct; apex is a chain fusion
        # (needs combo, which is itself unlockable).
        combos = detect_combinations(graph, ["base-a", "base-b"], [])
        results = {c["candidateResult"]: c for c in combos}
        assert "apex" in results
        assert results["apex"]["status"] == "chain_fusion"
        assert "combo" in results["apex"]["chainSteps"]

    def test_zero_prereq_fusion_type_ignored(self):
        """A node whose type literal is 'fusion' but has 0 prereqs is not a
        combination (structural rule: len(prereqs) >= 1)."""
        graph = {"skills": [{"id": "lonely", "type": "fusion", "prerequisites": []}]}
        assert detect_combinations(graph, [], []) == []

    def test_owned_fusion_excluded(self):
        graph = _ygg2_graph()
        combos = detect_combinations(graph, ["base-a", "base-b", "combo"], [])
        assert "combo" not in {c["candidateResult"] for c in combos}

    def test_get_combinations_delegates(self):
        graph = _ygg2_graph()
        assert get_combinations(graph, ["base-a", "base-b"], []) == \
            detect_combinations(graph, ["base-a", "base-b"], [])

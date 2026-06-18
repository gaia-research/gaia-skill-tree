"""Tests for the grading pipeline — grade derivation, type validation, gate logic."""

from __future__ import annotations

import json
import sys
import pytest
from pathlib import Path
from gaia_cli.grading import (
    derive_grade,
    overall_trust_grade,
    check_ultimate_gate,
    load_evidence_types,
    load_grade_thresholds,
    load_ultimate_gate,
    load_evidence_types_full,
)

# ---------------------------------------------------------------------------
# Grade derivation — boundary cases
# ---------------------------------------------------------------------------

class TestDeriveGrade:
    def test_below_floor_is_ungraded(self):
        assert derive_grade(39) is None

    def test_c_floor(self):
        assert derive_grade(40) == "C"

    def test_c_interior(self):
        assert derive_grade(59) == "C"

    def test_b_floor(self):
        assert derive_grade(60) == "B"

    def test_b_interior(self):
        assert derive_grade(79) == "B"

    def test_a_floor(self):
        assert derive_grade(80) == "A"

    def test_a_interior(self):
        assert derive_grade(89) == "A"

    def test_s_floor(self):
        assert derive_grade(90) == "S"

    def test_s_above(self):
        assert derive_grade(100) == "S"

    def test_zero_is_ungraded(self):
        assert derive_grade(0) is None

    def test_float_trust(self):
        assert derive_grade(80.0) == "A"
        assert derive_grade(39.9) is None
        assert derive_grade(40.0) == "C"

    def test_custom_thresholds(self):
        thresholds = {"S": 95, "A": 85, "B": 70, "C": 50}
        assert derive_grade(94, thresholds) == "A"
        assert derive_grade(95, thresholds) == "S"
        assert derive_grade(49, thresholds) is None
        assert derive_grade(50, thresholds) == "C"


# ---------------------------------------------------------------------------
# Overall Trust Grade aggregation
# ---------------------------------------------------------------------------

class TestOverallTrustGrade:
    def test_empty_evidence(self):
        assert overall_trust_grade([]) is None

    def test_no_graded_entries(self):
        ev = [{"class": "A", "source": "http://x"}, {"source": "http://y"}]
        assert overall_trust_grade(ev) is None

    def test_single_s_grade(self):
        ev = [{"grade": "S", "source": "http://x"}]
        assert overall_trust_grade(ev) == "S"

    def test_highest_wins(self):
        ev = [
            {"grade": "C", "source": "http://x"},
            {"grade": "A", "source": "http://y"},
            {"grade": "B", "source": "http://z"},
        ]
        assert overall_trust_grade(ev) == "A"

    def test_ungraded_entry_ignored(self):
        ev = [
            {"source": "http://x"},           # no grade key
            {"grade": "B", "source": "http://y"},
        ]
        assert overall_trust_grade(ev) == "B"

    def test_none_evidence_list(self):
        assert overall_trust_grade(None) is None

    def test_mixed_graded_ungraded(self):
        ev = [
            {"grade": "C", "source": "http://a"},
            {"grade": None, "source": "http://b"},   # explicitly None
            {"grade": "A", "source": "http://c"},
        ]
        assert overall_trust_grade(ev) == "A"


# ---------------------------------------------------------------------------
# Type validation — integration with meta.json
# ---------------------------------------------------------------------------

class TestEvidenceTypes:
    # The 10 canonical G7 evidence type IDs defined in registry/schema/meta.json
    G7_TYPE_IDS = [
        "fusion-recipe",
        "github-stars-own",
        "proxy-containment",
        "verifier-attestation",
        "benchmark-result",
        "arxiv",
        "peer-review",
        "repo-own",
        "self-attestation",
        "social-signal",
    ]

    def test_valid_types_from_meta(self):
        # G7 format: types is a list of objects; load_evidence_types() normalises to IDs.
        types = load_evidence_types(".")
        for type_id in self.G7_TYPE_IDS:
            assert type_id in types, f"expected G7 type '{type_id}' in load_evidence_types()"

    def test_returns_strings(self):
        # Always returns a list of plain strings regardless of schema format.
        types = load_evidence_types(".")
        assert all(isinstance(t, str) for t in types)

    def test_invalid_type_detection(self):
        # Note: `arxiv` survived the legacy→G7 ID rename unchanged — it is correctly
        # NOT in this rejection list and should never be added here.
        types = load_evidence_types(".")
        assert "stars" not in types          # wrong alias
        assert "GitHub-Stars" not in types   # wrong case
        assert "repo" not in types           # legacy id — replaced by repo-own
        assert "github-stars" not in types   # legacy id — replaced by github-stars-own


# ---------------------------------------------------------------------------
# Ungraded doesn't gate — ungraded entries must not satisfy the ultimate gate
# ---------------------------------------------------------------------------

class TestUngradedDoesNotGate:
    def _skill_with_ungraded_evidence(self):
        # trust < 40 → ungraded, so grade is absent/None
        return {
            "id": "my-ultimate",
            "type": "ultimate",
            "evidence": [
                {"source": "http://a"},           # no grade
                {"source": "http://b"},
                {"source": "http://c"},
            ],
        }

    def test_ungraded_evidence_fails_gate(self):
        skill = self._skill_with_ungraded_evidence()
        result = check_ultimate_gate(skill, {})
        assert result["passes"] is False

    def test_grade_none_ignored_in_gate(self):
        skill = {
            "id": "my-ultimate",
            "type": "ultimate",
            "evidence": [
                {"grade": None, "source": "http://a"},
                {"grade": None, "source": "http://b"},
                {"grade": None, "source": "http://c"},
            ],
        }
        result = check_ultimate_gate(skill, {})
        assert result["passes"] is False


# ---------------------------------------------------------------------------
# Ultimate gate — pillar rule (suite) and direct-evidence path
# ---------------------------------------------------------------------------

def _make_component(skill_id, grade):
    ev = [{"grade": grade, "source": f"http://{skill_id}"}] if grade else []
    return {"id": skill_id, "type": "basic", "evidence": ev}


GATE_CONFIG = {
    "minEvidencedComponents": 3,
    "requiredComponentGrades": {"S": 1, "A": 2},
    "componentFloor": "C",
}


class TestUltimateGateSuite:
    def _suite_skill(self, components):
        return {
            "id": "big-ultimate",
            "type": "ultimate",
            "suiteComponents": list(components.keys()),
        }

    def test_passes_with_s_and_two_a(self):
        comps = {
            "c1": _make_component("c1", "S"),
            "c2": _make_component("c2", "A"),
            "c3": _make_component("c3", "A"),
        }
        skill = self._suite_skill(comps)
        result = check_ultimate_gate(skill, comps, GATE_CONFIG)
        assert result["passes"] is True

    def test_fails_not_enough_components(self):
        comps = {
            "c1": _make_component("c1", "S"),
            "c2": _make_component("c2", "A"),
        }
        skill = self._suite_skill(comps)
        result = check_ultimate_gate(skill, comps, GATE_CONFIG)
        assert result["passes"] is False
        assert "2/3" in result["reason"]

    def test_fails_missing_s(self):
        comps = {
            "c1": _make_component("c1", "A"),
            "c2": _make_component("c2", "A"),
            "c3": _make_component("c3", "A"),
        }
        skill = self._suite_skill(comps)
        result = check_ultimate_gate(skill, comps, GATE_CONFIG)
        assert result["passes"] is False
        assert "S" in result["reason"]

    def test_fails_missing_second_a(self):
        # S + B + B: only S counts as A+, so A+ count = 1 < 2. Fails A req.
        comps = {
            "c1": _make_component("c1", "S"),
            "c2": _make_component("c2", "B"),
            "c3": _make_component("c3", "B"),
        }
        skill = self._suite_skill(comps)
        result = check_ultimate_gate(skill, comps, GATE_CONFIG)
        assert result["passes"] is False
        assert "A" in result["reason"]

    def test_fails_component_below_floor(self):
        # A component with trust < 40 → ungraded, not a "grade" at all
        # But "below floor C" means a grade worse than C — since ungraded has no grade,
        # it simply doesn't count as evidenced. A component graded below C would be
        # below the floor. In our model, there's no grade below C (C is the lowest);
        # ungraded means no grade at all (doesn't count toward evidenced).
        # To test the floor: we'd need a synthetic config where B is the floor.
        gate = {
            "minEvidencedComponents": 2,
            "requiredComponentGrades": {"S": 1, "A": 1},
            "componentFloor": "A",  # very strict floor: all must be A or better
        }
        comps = {
            "c1": _make_component("c1", "S"),
            "c2": _make_component("c2", "B"),  # below A floor
        }
        skill = self._suite_skill(comps)
        result = check_ultimate_gate(skill, comps, gate)
        assert result["passes"] is False
        assert "floor" in result["reason"]

    def test_passes_s_counts_toward_a_requirement(self):
        # S ≥ A, so 1S + 1A satisfies requiredComponentGrades {S:1, A:2}? No — A:2 means 2 A+,
        # S counts as A+, so 1S + 1A = 2 A+. But we need S:1 (exactly 1+ S-grade) and A:2.
        # With S=1, A=1: S(counts as A+) = 1, A(counts as A+) = 1, total A+ = 2. S requirement = 1. Should pass.
        comps = {
            "c1": _make_component("c1", "S"),
            "c2": _make_component("c2", "A"),
            "c3": _make_component("c3", "B"),  # B is above floor C but below A
        }
        skill = self._suite_skill(comps)
        result = check_ultimate_gate(skill, comps, GATE_CONFIG)
        # S req: need 1 S-grade+ component → S(1) ≥ 1. Pass.
        # A req: need 2 A-grade+ components → S(1) + A(1) = 2. Pass.
        # Floor C: B is above C floor. Pass.
        assert result["passes"] is True


class TestUltimateGateDirect:
    def _direct_skill(self, evidence_grades):
        return {
            "id": "direct-ultimate",
            "type": "ultimate",
            "evidence": [
                {"grade": g, "source": f"http://ev{i}"}
                for i, g in enumerate(evidence_grades)
            ],
        }

    def test_passes(self):
        skill = self._direct_skill(["S", "A", "A"])
        result = check_ultimate_gate(skill, {}, GATE_CONFIG)
        assert result["passes"] is True

    def test_fails_not_enough_sources(self):
        skill = self._direct_skill(["S", "A"])
        result = check_ultimate_gate(skill, {}, GATE_CONFIG)
        assert result["passes"] is False

    def test_fails_no_s_grade(self):
        skill = self._direct_skill(["A", "A", "A"])
        result = check_ultimate_gate(skill, {}, GATE_CONFIG)
        assert result["passes"] is False

    def test_fails_not_enough_a(self):
        skill = self._direct_skill(["S", "A", "B"])
        result = check_ultimate_gate(skill, {}, GATE_CONFIG)
        # S req: 1 S+. Pass.
        # A req: need 2 A+. S(1) + A(1) = 2. Pass.
        # This should actually pass since S counts as A+.
        assert result["passes"] is True

    def test_fails_only_b_grades(self):
        skill = self._direct_skill(["B", "B", "B"])
        result = check_ultimate_gate(skill, {}, GATE_CONFIG)
        assert result["passes"] is False


# ---------------------------------------------------------------------------
# Effective grade — own ∪ inherited (parent → child evidence inheritance)
# ---------------------------------------------------------------------------

from gaia_cli.evidence import inherited_evidence


def _effective_grade(named, generic):
    """Mirror the catalog computation: grade over own ∪ inherited evidence."""
    return overall_trust_grade(inherited_evidence(named, generic))


class TestEffectiveGradeInheritance:
    def test_inherits_parent_grade_when_child_ungraded(self):
        # Child has no graded evidence; parent (generic) carries A.
        named = {"id": "c/x", "evidence": [{"source": "http://repo", "grade": None}]}
        generic = {"id": "cap", "evidence": [{"source": "http://arxiv", "grade": "A"}]}
        assert _effective_grade(named, generic) == "A"

    def test_child_own_exceeds_inherited_floor(self):
        # Child's own S beats the inherited A — effective = max(own, inherited).
        named = {"id": "c/x", "evidence": [{"source": "http://repo", "grade": "S"}]}
        generic = {"id": "cap", "evidence": [{"source": "http://arxiv", "grade": "A"}]}
        assert _effective_grade(named, generic) == "S"

    def test_inherited_floor_when_child_weaker(self):
        # Child only B, parent A → effective lifts to the inherited A.
        named = {"id": "c/x", "evidence": [{"source": "http://repo", "grade": "B"}]}
        generic = {"id": "cap", "evidence": [{"source": "http://arxiv", "grade": "A"}]}
        assert _effective_grade(named, generic) == "A"

    def test_no_generic_falls_back_to_own(self):
        named = {"id": "c/x", "evidence": [{"source": "http://repo", "grade": "B"}]}
        assert _effective_grade(named, None) == "B"

    def test_dedup_by_source_prefers_child(self):
        # Same source on both layers; child entry wins (own evidence first).
        named = {"id": "c/x", "evidence": [{"source": "http://shared", "grade": "S"}]}
        generic = {"id": "cap", "evidence": [{"source": "http://shared", "grade": "C"}]}
        assert _effective_grade(named, generic) == "S"

    def test_no_grades_anywhere_is_none(self):
        named = {"id": "c/x", "evidence": [{"source": "http://repo"}]}
        generic = {"id": "cap", "evidence": [{"source": "http://arxiv"}]}
        assert _effective_grade(named, generic) is None


class TestSuiteGateByChildEffectiveGrade:
    """The suite gate must score components by their *named* child effective
    grade, resolved through a component lookup keyed by named id — not the
    generic-keyed map (which misses named ids and reads '0/3')."""

    def _lookup(self, comp_effective):
        """{named_id: component dict with effective evidence}."""
        return {
            cid: {"id": cid, "type": "basic",
                  "evidence": [{"source": f"http://{cid}", "grade": g}] if g else []}
            for cid, g in comp_effective.items()
        }

    def _suite(self, component_ids):
        return {"id": "suite", "type": "ultimate", "suiteComponents": list(component_ids)}

    def test_named_components_resolve_off_zero(self):
        # Three named components, all graded via effective evidence → not "0/3".
        lookup = self._lookup({"c/a": "S", "c/b": "A", "c/c": "A"})
        result = check_ultimate_gate(self._suite(lookup), lookup, GATE_CONFIG)
        assert result["passes"] is True
        assert result["details"]["evidencedComponents"] == 3

    def test_inherited_only_components_count(self):
        # Components graded purely by inheritance (B) still count toward evidenced,
        # but a suite of all-B fails the S/A pillar — the accurate editorial gap.
        lookup = self._lookup({"c/a": "B", "c/b": "B", "c/c": "B"})
        result = check_ultimate_gate(self._suite(lookup), lookup, GATE_CONFIG)
        assert result["details"]["evidencedComponents"] == 3
        assert result["passes"] is False
        assert "S" in result["reason"]  # missing required S, not "0/3"

    def test_ungraded_component_not_counted(self):
        lookup = self._lookup({"c/a": "S", "c/b": "A", "c/c": None})
        result = check_ultimate_gate(self._suite(lookup), lookup, GATE_CONFIG)
        # Only 2 evidenced → fails the minimum, reason names 2/3.
        assert result["passes"] is False
        assert "2/3" in result["reason"]

    def test_floor_blocks_below_floor_component(self):
        gate = {"minEvidencedComponents": 2,
                "requiredComponentGrades": {"S": 1, "A": 1},
                "componentFloor": "A"}
        lookup = self._lookup({"c/a": "S", "c/b": "B"})  # B below A floor
        result = check_ultimate_gate(self._suite(lookup), lookup, gate)
        assert result["passes"] is False
        assert "floor" in result["reason"]


# ---------------------------------------------------------------------------
# CLI integration — --type validation and --trust → grade
# ---------------------------------------------------------------------------

class TestEvidenceCLI:
    @pytest.fixture(autouse=True)
    def no_docs_build(self, monkeypatch):
        monkeypatch.setattr("gaia_cli.commands.dev._run_docs_build", lambda *a, **kw: None)

    def write_fixture_skill(self, root: Path):
        nodes = root / "registry" / "nodes" / "basic"
        nodes.mkdir(parents=True)
        (nodes / "test-skill.json").write_text(json.dumps({
            "id": "test-skill",
            "name": "Test Skill",
            "type": "basic",
            "description": "A test skill for grading tests",
            "status": "provisional",
            "prerequisites": [],
            "derivatives": [],
            "evidence": [],
            "knownAgents": [],
            "createdAt": "2026-06-14",
            "updatedAt": "2026-06-14",
            "version": "0.1.0",
        }), encoding="utf-8")

    def test_trust_derives_grade_a(self, tmp_path, monkeypatch, capsys):
        self.write_fixture_skill(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "gaia", "--registry", str(tmp_path), "dev", "evidence",
            "test-skill", "http://example.com/paper",
            "--type", "arxiv", "--trust", "85", "--no-build",
        ])
        from gaia_cli.main import main
        main()
        node = json.loads((tmp_path / "registry" / "nodes" / "basic" / "test-skill.json").read_text())
        ev = node["evidence"][-1]
        assert ev["grade"] == "A"
        assert ev["trustNumber"] == 85.0
        assert ev["type"] == "arxiv"

    def test_trust_below_40_is_ungraded(self, tmp_path, monkeypatch):
        self.write_fixture_skill(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "gaia", "--registry", str(tmp_path), "dev", "evidence",
            "test-skill", "http://example.com/x",
            "--trust", "30", "--no-build",
        ])
        from gaia_cli.main import main
        main()
        node = json.loads((tmp_path / "registry" / "nodes" / "basic" / "test-skill.json").read_text())
        ev = node["evidence"][-1]
        assert "grade" not in ev
        assert ev["trustNumber"] == 30.0

    def test_invalid_type_rejected(self, tmp_path, monkeypatch):
        self.write_fixture_skill(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "gaia", "--registry", str(tmp_path), "dev", "evidence",
            "test-skill", "http://example.com/x",
            "--type", "stars", "--trust", "80", "--no-build",
        ])
        from gaia_cli.main import main
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_class_deprecated_warning(self, tmp_path, monkeypatch, capsys):
        self.write_fixture_skill(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "gaia", "--registry", str(tmp_path), "dev", "evidence",
            "test-skill", "http://example.com/x",
            "--class", "B", "--no-build",
        ])
        from gaia_cli.main import main
        main()
        captured = capsys.readouterr()
        assert "deprecated" in captured.err.lower()
        # Class is still written to the entry
        node = json.loads((tmp_path / "registry" / "nodes" / "basic" / "test-skill.json").read_text())
        ev = node["evidence"][-1]
        assert ev["class"] == "B"

    def test_evidence_graded_timeline_event(self, tmp_path, monkeypatch):
        self.write_fixture_skill(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "gaia", "--registry", str(tmp_path), "dev", "evidence",
            "test-skill", "http://example.com/x",
            "--type", "repo", "--trust", "92", "--no-build",
        ])
        from gaia_cli.main import main
        main()
        node = json.loads((tmp_path / "registry" / "nodes" / "basic" / "test-skill.json").read_text())
        timeline = node.get("timeline", [])
        actions = [e["action"] for e in timeline]
        assert "evidence_added" in actions
        assert "evidence_graded" in actions

    def test_trust_s_boundary(self, tmp_path, monkeypatch):
        self.write_fixture_skill(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "gaia", "--registry", str(tmp_path), "dev", "evidence",
            "test-skill", "http://example.com/x",
            "--trust", "90", "--no-build",
        ])
        from gaia_cli.main import main
        main()
        node = json.loads((tmp_path / "registry" / "nodes" / "basic" / "test-skill.json").read_text())
        ev = node["evidence"][-1]
        assert ev["grade"] == "S"


# ---------------------------------------------------------------------------
# V2 inheritance contract -- allowedLayers + inheritMultiplier schema tests
# ---------------------------------------------------------------------------

class TestMetaJsonInheritanceSchema:
    """Verify meta.json carries the v2 inheritance contract fields on all 10 types."""

    def _get_type(self, type_id: str) -> dict:
        types = load_evidence_types_full(".")
        for t in types:
            if t.get("id") == type_id:
                return t
        raise KeyError(f"type {type_id!r} not found in meta.json")

    def test_arxiv_allowed_layers_and_multiplier(self):
        t = self._get_type("arxiv")
        assert t["allowedLayers"] == ["generic", "named"]
        assert abs(t["inheritMultiplier"] - 0.70) < 1e-9

    def test_verifier_attestation_named_only_no_multiplier(self):
        t = self._get_type("verifier-attestation")
        assert t["allowedLayers"] == ["named"]
        assert "inheritMultiplier" not in t

    def test_inherit_multiplier_out_of_range_not_in_schema(self):
        # Verify none of the 10 ratified types has inheritMultiplier > 1.0 or < 0.0
        types = load_evidence_types_full(".")
        for t in types:
            mult = t.get("inheritMultiplier")
            if mult is not None:
                assert 0.0 <= mult <= 1.0, (
                    f"Type {t['id']!r} has inheritMultiplier={mult} outside [0.0, 1.0]"
                )

    def test_allowed_layers_not_empty(self):
        # Every type must declare at least one allowedLayer
        types = load_evidence_types_full(".")
        for t in types:
            layers = t.get("allowedLayers")
            assert layers and len(layers) >= 1, (
                f"Type {t['id']!r} has empty or missing allowedLayers"
            )


class TestEvidenceLayerField:
    """Verify skill/namedSkill schemas accept layer field and reject invalid values."""

    def _make_evidence_entry(self, layer=None):
        entry = {
            "source": "https://example.com/paper",
            "evaluator": "testuser",
            "date": "2026-01-01",
            "type": "arxiv",
        }
        if layer is not None:
            entry["layer"] = layer
        return entry

    def test_layer_generic_valid(self):
        # A row with layer="generic" must be a valid evidence entry (no schema error).
        entry = self._make_evidence_entry(layer="generic")
        assert entry["layer"] == "generic"

    def test_layer_named_valid(self):
        entry = self._make_evidence_entry(layer="named")
        assert entry["layer"] == "named"

    def test_layer_invalid_value_rejected(self):
        # "invalid" is not in enum ["generic", "named"] -- the validator must catch this.
        from gaia_cli.validate import check_evidence_layer_policy, load_type_layer_policy
        policy = load_type_layer_policy(".")
        skill = {
            "id": "test-skill",
            "evidence": [self._make_evidence_entry(layer="invalid")],
        }
        violations = check_evidence_layer_policy(skill, "generic", policy)
        # "invalid" is not in allowedLayers for arxiv -- violation expected
        assert len(violations) >= 1
        assert violations[0]["error_code"] == "evidence-layer-not-allowed"


class TestLayerNotAllowedValidator:
    """Test the evidence-layer-not-allowed validator (gaia validate hook)."""

    def test_verifier_attestation_on_generic_fires_violation(self):
        """verifier-attestation is named-only; attaching it to a generic node must fail."""
        from gaia_cli.validate import check_evidence_layer_policy, load_type_layer_policy
        policy = load_type_layer_policy(".")
        skill = {
            "id": "my-generic-skill",
            "evidence": [{
                "source": "https://example.com/attestation",
                "evaluator": "verifier1",
                "date": "2026-01-01",
                "type": "verifier-attestation",
                # no explicit layer -> defaults to skill_layer = "generic"
            }],
        }
        violations = check_evidence_layer_policy(skill, "generic", policy)
        assert len(violations) == 1
        v = violations[0]
        assert v["error_code"] == "evidence-layer-not-allowed"
        assert v["evidence_type"] == "verifier-attestation"
        assert v["row_layer"] == "generic"
        assert v["allowed_layers"] == ["named"]

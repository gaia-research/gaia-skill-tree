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
    def test_valid_types_from_meta(self):
        # The real meta.json should have arxiv, repo, github-stars
        types = load_evidence_types(".")
        assert "arxiv" in types
        assert "repo" in types
        assert "github-stars" in types

    def test_invalid_type_detection(self):
        types = load_evidence_types(".")
        assert "stars" not in types          # wrong alias
        assert "GitHub-Stars" not in types   # wrong case


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

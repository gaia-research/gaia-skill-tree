"""Tests for src/gaia_cli/promotion.py — level promotion logic."""

import json
import os
from datetime import date

import pytest

from gaia_cli.promotion import (
    LEVEL_ORDER,
    LEVEL_NAMES,
    next_level,
    check_promotion_eligibility,
    promote_skill,
    promotion_state,
    _effective_grade,
    _meets_evidence_floor,
    _holds_bucket_origin,
    _contributor_holds_origin_in,
    checkUniqueBranchGate,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_graph(*skills):
    """Build a minimal graph_data dict from skill dicts."""
    return {"skills": list(skills), "edges": []}


def _make_skill(skill_id, name=None, level="0★", evidence=None, demerits=None):
    """Build a minimal skill node."""
    return {
        "id": skill_id,
        "name": name or skill_id.replace("-", " ").title(),
        "type": "basic",
        "level": level,
        "description": f"Test skill: {skill_id}",
        "prerequisites": [],
        "derivatives": [],
        "conditions": "",
        "evidence": evidence or [],
        "knownAgents": [],
        "status": "provisional",
        "createdAt": "2026-01-01",
        "updatedAt": "2026-01-01",
        "version": "0.1.0",
        "demerits": demerits or [],
    }


def _make_tree(username, unlocked_skills):
    """Build a minimal tree_data dict."""
    return {
        "userId": username,
        "updatedAt": "2026-01-01",
        "unlockedSkills": unlocked_skills,
        "pendingCombinations": [],
        "stats": {
            "totalUnlocked": len(unlocked_skills),
            "deepestLineage": 0,
        },
    }


def _make_unlocked(skill_id, level="1★"):
    """Build a minimal unlockedSkill entry."""
    return {
        "skillId": skill_id,
        "level": level,
        "unlockedAt": "2026-01-01",
        "unlockedIn": "test/repo",
    }


def _write_tree(tmp_path, username, tree_data):
    """Write tree_data to the expected file path under tmp_path."""
    tree_dir = tmp_path / "skill-trees" / username
    tree_dir.mkdir(parents=True, exist_ok=True)
    tree_path = tree_dir / "skill-tree.json"
    tree_path.write_text(json.dumps(tree_data, indent=2))
    return tree_path


# ---------------------------------------------------------------------------
# Tests: next_level
# ---------------------------------------------------------------------------


class TestNextLevel:
    def test_basic_to_awakened(self):
        assert next_level("0★") == "1★"

    def test_awakened_to_named(self):
        assert next_level("1★") == "2★"

    def test_transcendent_to_transcendent_star(self):
        assert next_level("5★") == "6★"

    def test_max_level_returns_none(self):
        assert next_level("6★") is None

    def test_invalid_level_returns_none(self):
        assert next_level("X") is None

    def test_full_progression(self):
        level = "0★"
        visited = [level]
        while True:
            nxt = next_level(level)
            if nxt is None:
                break
            visited.append(nxt)
            level = nxt
        assert visited == LEVEL_ORDER


# ---------------------------------------------------------------------------
# Tests: check_promotion_eligibility
# ---------------------------------------------------------------------------


class TestCheckPromotionEligibility:
    def test_basic_skill_eligible_no_evidence_needed(self):
        """0★★ -> 1★ requires no evidence, so skill is eligible."""
        graph = _make_graph(_make_skill("tokenize"))
        tree = _make_tree("alice", [_make_unlocked("tokenize", "0★")])
        eligible = check_promotion_eligibility(graph, tree)
        assert len(eligible) == 1
        assert eligible[0]["skillId"] == "tokenize"
        assert eligible[0]["currentLevel"] == "0★"
        assert eligible[0]["nextLevel"] == "1★"

    def test_level_I_to_II_eligible_with_class_C_evidence(self):
        """1★ -> 2★ requires class C/B/A evidence."""
        ev = [{"class": "C", "source": "http://example.com", "evaluator": "x", "date": "2026-01-01", "notes": ""}]
        graph = _make_graph(_make_skill("tokenize", evidence=ev))
        tree = _make_tree("alice", [_make_unlocked("tokenize", "1★")])
        eligible = check_promotion_eligibility(graph, tree)
        assert len(eligible) == 1
        assert eligible[0]["nextLevel"] == "2★"

    def test_level_I_to_II_not_eligible_without_evidence(self):
        """1★ -> 2★ blocked if no evidence at all."""
        graph = _make_graph(_make_skill("tokenize"))
        tree = _make_tree("alice", [_make_unlocked("tokenize", "1★")])
        eligible = check_promotion_eligibility(graph, tree)
        assert len(eligible) == 0

    def test_level_II_to_III_requires_class_B(self):
        """2★ -> 3★ requires class B or A evidence."""
        ev_c_only = [{"class": "C", "source": "http://x.com", "evaluator": "x", "date": "2026-01-01", "notes": ""}]
        graph = _make_graph(_make_skill("tokenize", evidence=ev_c_only))
        tree = _make_tree("alice", [_make_unlocked("tokenize", "2★")])
        eligible = check_promotion_eligibility(graph, tree)
        assert len(eligible) == 0  # C is not enough for 3★

    def test_level_II_to_III_eligible_with_class_B(self):
        ev_b = [{"class": "B", "source": "http://x.com", "evaluator": "x", "date": "2026-01-01", "notes": ""}]
        graph = _make_graph(_make_skill("tokenize", evidence=ev_b))
        tree = _make_tree("alice", [_make_unlocked("tokenize", "2★")])
        eligible = check_promotion_eligibility(graph, tree)
        assert len(eligible) == 1
        assert eligible[0]["nextLevel"] == "3★"

    def test_max_level_not_eligible(self):
        """A skill at 6★ cannot be promoted further."""
        ev = [{"class": "A", "source": "http://x.com", "evaluator": "x", "date": "2026-01-01", "notes": ""}]
        graph = _make_graph(_make_skill("tokenize", evidence=ev))
        tree = _make_tree("alice", [_make_unlocked("tokenize", "6★")])
        eligible = check_promotion_eligibility(graph, tree)
        assert len(eligible) == 0

    def test_multiple_skills_mixed_eligibility(self):
        """Only eligible skills appear in the result list."""
        ev_b = [{"class": "B", "source": "http://x.com", "evaluator": "x", "date": "2026-01-01", "notes": ""}]
        graph = _make_graph(
            _make_skill("tokenize", evidence=ev_b),
            _make_skill("classify"),  # no evidence
        )
        tree = _make_tree("alice", [
            _make_unlocked("tokenize", "0★"),   # eligible (no evidence needed for 0★->1★)
            _make_unlocked("classify", "1★"),   # not eligible (no evidence for 1★->2★)
        ])
        eligible = check_promotion_eligibility(graph, tree)
        assert len(eligible) == 1
        assert eligible[0]["skillId"] == "tokenize"

    def test_skill_not_in_graph_skipped(self):
        """If a tree skill doesn't exist in the graph, it's skipped."""
        graph = _make_graph()  # empty graph
        tree = _make_tree("alice", [_make_unlocked("phantom", "1★")])
        eligible = check_promotion_eligibility(graph, tree)
        assert len(eligible) == 0

    def test_promotion_blocked_by_demerit_ceiling(self):
        """One demerit can lower effective ceiling so next level is blocked."""
        ev_b = [{"class": "B", "source": "http://x.com", "evaluator": "x", "date": "2026-01-01", "notes": ""}]
        graph = _make_graph(
            _make_skill(
                "tokenize",
                level="3★",
                evidence=ev_b,
                demerits=["heavyweight-dependency"],
            )
        )
        tree = _make_tree("alice", [_make_unlocked("tokenize", "2★")])
        eligible = check_promotion_eligibility(graph, tree)
        assert len(eligible) == 0


# ---------------------------------------------------------------------------
# Tests: promote_skill
# ---------------------------------------------------------------------------


class TestPromoteSkill:
    def test_promotes_skill_one_level(self, tmp_path):
        tree_data = _make_tree("alice", [_make_unlocked("tokenize", "1★")])
        _write_tree(tmp_path, "alice", tree_data)
        result = promote_skill("alice", "tokenize", str(tmp_path), new_display_name="Tokenize")
        assert result["skillId"] == "tokenize"
        assert result["previousLevel"] == "1★"
        assert result["newLevel"] == "2★"
        assert result["displayName"] == "Tokenize"

    def test_persists_new_level_to_disk(self, tmp_path):
        tree_data = _make_tree("bob", [_make_unlocked("classify", "2★")])
        _write_tree(tmp_path, "bob", tree_data)
        promote_skill("bob", "classify", str(tmp_path), new_display_name="Classify")
        # Re-read from disk
        tree_path = tmp_path / "skill-trees" / "bob" / "skill-tree.json"
        saved = json.loads(tree_path.read_text())
        entry = next(s for s in saved["unlockedSkills"] if s["skillId"] == "classify")
        assert entry["level"] == "3★"

    def test_updates_updated_at(self, tmp_path):
        tree_data = _make_tree("carol", [_make_unlocked("tokenize", "0★")])
        _write_tree(tmp_path, "carol", tree_data)
        promote_skill("carol", "tokenize", str(tmp_path), new_display_name="Tokenize")
        tree_path = tmp_path / "skill-trees" / "carol" / "skill-tree.json"
        saved = json.loads(tree_path.read_text())
        assert saved["updatedAt"] == date.today().isoformat()

    def test_raises_if_no_tree(self, tmp_path):
        with pytest.raises(ValueError, match="No skill tree found"):
            promote_skill("nobody", "tokenize", str(tmp_path))

    def test_raises_if_skill_not_in_tree(self, tmp_path):
        tree_data = _make_tree("alice", [_make_unlocked("tokenize", "1★")])
        _write_tree(tmp_path, "alice", tree_data)
        with pytest.raises(ValueError, match="not found"):
            promote_skill("alice", "nonexistent", str(tmp_path))

    def test_raises_if_already_max_level(self, tmp_path):
        tree_data = _make_tree("alice", [_make_unlocked("tokenize", "6★")])
        _write_tree(tmp_path, "alice", tree_data)
        with pytest.raises(ValueError, match="maximum level"):
            promote_skill("alice", "tokenize", str(tmp_path))

    def test_reads_display_name_from_graph_when_not_provided(self, tmp_path):
        tree_data = _make_tree("alice", [_make_unlocked("tokenize", "1★")])
        _write_tree(tmp_path, "alice", tree_data)
        # Write a graph file
        graph_dir = tmp_path / "registry"
        graph_dir.mkdir(parents=True, exist_ok=True)
        graph_data = _make_graph(_make_skill("tokenize", name="Tokenize"))
        (graph_dir / "gaia.json").write_text(json.dumps(graph_data))
        result = promote_skill("alice", "tokenize", str(tmp_path))
        assert result["displayName"] == "Tokenize"

    def test_fallback_display_name_when_no_graph(self, tmp_path):
        tree_data = _make_tree("alice", [_make_unlocked("tokenize", "1★")])
        _write_tree(tmp_path, "alice", tree_data)
        # No graph file exists
        result = promote_skill("alice", "tokenize", str(tmp_path))
        assert result["displayName"] == "tokenize"


# ---------------------------------------------------------------------------
# Tests: promotion_state
# ---------------------------------------------------------------------------


class TestPromotionState:
    def test_not_unlocked(self):
        graph = _make_graph(_make_skill("tokenize"))
        tree = _make_tree("alice", [])
        assert promotion_state("tokenize", tree, graph) == "not_unlocked"

    def test_max_level(self):
        graph = _make_graph(_make_skill("tokenize"))
        tree = _make_tree("alice", [_make_unlocked("tokenize", "6★")])
        assert promotion_state("tokenize", tree, graph) == "max_level"

    def test_eligible_no_evidence_needed(self):
        graph = _make_graph(_make_skill("tokenize"))
        tree = _make_tree("alice", [_make_unlocked("tokenize", "0★")])
        assert promotion_state("tokenize", tree, graph) == "eligible"

    def test_eligible_with_evidence(self):
        ev = [{"class": "B", "source": "http://x.com", "evaluator": "x", "date": "2026-01-01", "notes": ""}]
        graph = _make_graph(_make_skill("tokenize", evidence=ev))
        tree = _make_tree("alice", [_make_unlocked("tokenize", "1★")])
        assert promotion_state("tokenize", tree, graph) == "eligible"

    def test_blocked_by_evidence(self):
        graph = _make_graph(_make_skill("tokenize"))  # no evidence
        tree = _make_tree("alice", [_make_unlocked("tokenize", "1★")])
        assert promotion_state("tokenize", tree, graph) == "blocked"

    def test_blocked_skill_not_in_graph(self):
        graph = _make_graph()  # empty
        tree = _make_tree("alice", [_make_unlocked("phantom", "2★")])
        assert promotion_state("phantom", tree, graph) == "blocked"


# ---------------------------------------------------------------------------
# Tests: Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_level_order_length(self):
        assert len(LEVEL_ORDER) == 7

    def test_level_names_keys_match_order(self):
        assert list(LEVEL_NAMES.keys()) == LEVEL_ORDER

    def test_level_names_apex(self):
        assert LEVEL_NAMES["6★"] == "Apex"


# ---------------------------------------------------------------------------
# Tests: _effective_grade and _meets_evidence_floor (grade/class translation)
# ---------------------------------------------------------------------------


class TestGradeTranslation:
    """Tests for evidence grade/class fallback logic in _meets_evidence_floor.

    Per G7 Trust Taxonomy RFC: evidence[].grade (S/A/B/C) supersedes the
    legacy evidence[].class (A/B/C).  Floor lists encode "at least one row at
    grade >= the weakest letter in the list".  Grade ordering: S > A > B > C.
    """

    # 1. Legacy: class-only row passes a ["B","A"] floor.
    def test_legacy_class_only_passes_floor(self):
        """A row with only class="B" (no grade field) satisfies a ["B","A"] floor."""
        skill = _make_skill(
            "legacy-skill",
            evidence=[{"class": "B", "source": "http://x.com", "evaluator": "x",
                        "date": "2026-01-01", "notes": ""}],
        )
        assert _meets_evidence_floor(skill, "3★") is True

    # 2. New: grade-only row passes a ["B","A"] floor.
    def test_new_grade_only_passes_floor(self):
        """A row with only grade="B" (no class field) satisfies a ["B","A"] floor."""
        skill = _make_skill(
            "graded-skill",
            evidence=[{"grade": "B", "source": "http://x.com", "evaluator": "x",
                        "date": "2026-01-01", "notes": ""}],
        )
        assert _meets_evidence_floor(skill, "3★") is True

    # 3. Mixed list: one class-only + one grade-only together pass a ["B","A"] floor.
    def test_mixed_class_and_grade_rows_pass_floor(self):
        """A list with one class-only (C) and one grade-only (B) entry passes ["B","A"]."""
        skill = _make_skill(
            "mixed-skill",
            evidence=[
                {"class": "C", "source": "http://c.com", "evaluator": "x",
                 "date": "2026-01-01", "notes": "class-only"},
                {"grade": "B", "source": "http://b.com", "evaluator": "x",
                 "date": "2026-01-01", "notes": "grade-only"},
            ],
        )
        assert _meets_evidence_floor(skill, "3★") is True

    # 4. Boundary: grade="C" only FAILS a ["B","A"] floor.
    def test_grade_c_fails_b_floor(self):
        """A row with only grade="C" does NOT satisfy a ["B","A"] floor."""
        skill = _make_skill(
            "weak-skill",
            evidence=[{"grade": "C", "source": "http://x.com", "evaluator": "x",
                        "date": "2026-01-01", "notes": ""}],
        )
        assert _meets_evidence_floor(skill, "3★") is False

    # 5. Bonus: S satisfies an A floor (["A"]).
    def test_grade_s_satisfies_a_floor(self):
        """A row with grade="S" satisfies a ["A"] floor (6★ gate). S > A."""
        skill = _make_skill(
            "apex-skill",
            evidence=[{"grade": "S", "source": "http://x.com", "evaluator": "x",
                        "date": "2026-01-01", "notes": ""}],
        )
        assert _meets_evidence_floor(skill, "6★") is True

    # 6. Ungraded entry (no class, no grade) is ignored.
    def test_ungraded_entry_ignored(self):
        """An entry with neither class nor grade does not satisfy any floor."""
        skill = _make_skill(
            "ungraded-skill",
            evidence=[{"source": "http://x.com", "evaluator": "x",
                        "date": "2026-01-01", "notes": "no grade or class"}],
        )
        assert _meets_evidence_floor(skill, "2★") is False

    # Integration: grade-only evidence propagates through check_promotion_eligibility.
    def test_grade_only_evidence_enables_eligibility(self):
        """A skill with grade-only evidence is included in promotion candidates."""
        ev = [{"grade": "B", "source": "http://x.com", "evaluator": "x",
               "date": "2026-01-01", "notes": ""}]
        graph = _make_graph(_make_skill("graded-skill", evidence=ev))
        tree = _make_tree("alice", [_make_unlocked("graded-skill", "2★")])
        eligible = check_promotion_eligibility(graph, tree)
        assert len(eligible) == 1
        assert eligible[0]["skillId"] == "graded-skill"
        assert eligible[0]["nextLevel"] == "3★"


# ---------------------------------------------------------------------------
# Unique-branch origin gate (Yggdrasil II Q3, amended 2026-07-19)
# 4★ Unique = BUCKET-LEVEL origin (§4.1); 5★+ = fusion-structure origin.
# Regression: graphify (sole 4★ named on a fusion generic with 0-named-impl
# prereqs) must PASS the 4★ gate — its Origin is on its own bucket, not on the
# prerequisite fusion structure.
# ---------------------------------------------------------------------------
class TestBucketOrigin:
    def test_holds_bucket_origin_true(self):
        assert _holds_bucket_origin(
            {"genericSkillRef": "knowledge-graph-build", "origin": True}
        ) is True

    def test_holds_bucket_origin_false_when_not_origin(self):
        assert _holds_bucket_origin(
            {"genericSkillRef": "knowledge-graph-build", "origin": False}
        ) is False

    def test_holds_bucket_origin_false_without_generic_ref(self):
        # No bucket to hold Origin on.
        assert _holds_bucket_origin({"origin": True}) is False


class TestUniqueBranchGateOriginFork:
    """The 4★ Unique gate reads bucket-level origin; 5★ reads fusion structure."""

    def _patch_tm_branch(self, monkeypatch, tm, branch="unique"):
        import gaia_cli.trustMagnitude as tmm
        import gaia_cli.taxonomy as tax
        monkeypatch.setattr(tmm, "computeTrustMagnitude", lambda *a, **k: tm)
        monkeypatch.setattr(tax, "branchFor", lambda *a, **k: branch)

    def test_4star_passes_on_bucket_origin_despite_empty_prereqs(self, monkeypatch):
        """Regression for graphify: fusion generic, prereqs have zero named
        implementations, but the skill holds Origin on its OWN bucket → PASS."""
        self._patch_tm_branch(monkeypatch, tm=122.85)
        named = {
            "id": "safishamsi/graphify",
            "contributor": "safishamsi",
            "genericSkillRef": "knowledge-graph-build",
            "origin": True,
        }
        generic_map = {
            "knowledge-graph-build": {
                "id": "knowledge-graph-build",
                "type": "fusion",
                # prereqs with NO named implementations (unsatisfiable at 5★)
                "prerequisites": ["extract-entities", "logical-inference"],
            }
        }
        named_map = {named["id"]: named}
        res = checkUniqueBranchGate(named, "4★", generic_map, named_map)
        assert res["originPresent"] is True
        assert res["tmThresholdMet"] is True
        assert res["passed"] is True

    def test_4star_fails_when_not_bucket_origin(self, monkeypatch):
        self._patch_tm_branch(monkeypatch, tm=200.0)
        named = {
            "id": "someone/impl",
            "contributor": "someone",
            "genericSkillRef": "knowledge-graph-build",
            "origin": False,
        }
        generic_map = {"knowledge-graph-build": {"prerequisites": ["a", "b"]}}
        res = checkUniqueBranchGate(named, "4★", generic_map, {named["id"]: named})
        assert res["originPresent"] is False
        assert res["passed"] is False

    def test_5star_still_reads_fusion_structure_origin(self, monkeypatch):
        """5★ gate is UNCHANGED: origin comes from holding Origin on a
        prerequisite node, NOT the skill's own bucket flag."""
        self._patch_tm_branch(monkeypatch, tm=300.0)
        # This skill holds bucket origin (origin: True) but does NOT hold origin
        # on any prerequisite node → 5★ fusion-structure origin must be False.
        named = {
            "id": "safishamsi/graphify",
            "contributor": "safishamsi",
            "genericSkillRef": "knowledge-graph-build",
            "origin": True,
        }
        generic_map = {
            "knowledge-graph-build": {
                "prerequisites": ["extract-entities", "logical-inference"],
            }
        }
        # No named skill by this contributor holds origin on a prereq node.
        named_map = {named["id"]: named}
        res = checkUniqueBranchGate(named, "5★", generic_map, named_map)
        assert res["originPresent"] is False
        assert res["passed"] is False

    def test_5star_passes_when_contributor_holds_prereq_origin(self, monkeypatch):
        self._patch_tm_branch(monkeypatch, tm=300.0)
        capstone = {
            "id": "c/capstone",
            "contributor": "c",
            "genericSkillRef": "knowledge-graph-build",
            "origin": True,
        }
        prereq_impl = {
            "id": "c/entities",
            "contributor": "c",
            "genericSkillRef": "extract-entities",
            "origin": True,
        }
        generic_map = {
            "knowledge-graph-build": {
                "prerequisites": ["extract-entities", "logical-inference"],
            }
        }
        named_map = {capstone["id"]: capstone, prereq_impl["id"]: prereq_impl}
        res = checkUniqueBranchGate(capstone, "5★", generic_map, named_map)
        assert res["originPresent"] is True
        assert res["passed"] is True


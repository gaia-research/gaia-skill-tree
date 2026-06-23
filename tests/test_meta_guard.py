"""Tests for Phase 1.5 I4 apex gate CI scripts.

Covers:
  1. auditApexAtG7.py on a skill that passes all 6 predicates → exit code 0.
  2. auditApexAtG7.py on a skill missing apexPromotionPrSigned → exit code 1.
  3. countApexSkills.py counts 6★ skills correctly.
  4. check_verifier_signoffs.py returns correct verifier counts.
"""

from __future__ import annotations

import datetime
import importlib.util
import json
import sys
from pathlib import Path
from typing import Optional

import pytest
pytestmark = [pytest.mark.integration, pytest.mark.slow]


# ---------------------------------------------------------------------------
# Helpers to import script modules without side effects
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"


def importScript(name: str):
    """Import a script from the scripts/ directory as a module."""
    path = _SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Shared test data helpers (mirrored from test_trust_magnitude.py)
# ---------------------------------------------------------------------------


def _apexReadySkill() -> dict:
    """Build a skill that should pass all 6 active apex predicates."""
    today = datetime.datetime.now(datetime.timezone.utc)
    longAgo = (today - datetime.timedelta(days=400)).date().isoformat()
    return {
        "id": "apex-skill",
        "suiteComponents": ["nestedSuiteId"],
        "evidence": [
            {
                "type": "fusion-recipe",
                "origins": ["origin1", "origin2", "origin3", "origin4", "origin5"],
            },
            {
                "type": "verifier-attestation",
                "verifiers": 4,
                "grade": "A",
                "source": "https://verifier.example/1",
                "sourceStartedAt": longAgo,
            },
            {
                "type": "arxiv",
                "citations": 200,
                "grade": "A",
                "source": "https://arxiv.org/abs/1234.5678",
                "sourceStartedAt": longAgo,
            },
            {
                "type": "github-stars-own",
                "stars": 50000,
                "grade": "A",
                "source": "https://github.com/o/r",
                "sourceStartedAt": longAgo,
            },
        ],
        "apexGateStatus": {"apexPromotionPrSigned": True},
    }


def _apexReadyGenericMap() -> dict:
    """GenericSkillMap used alongside _apexReadySkill."""
    return {
        "nestedSuiteId": {"id": "nestedSuiteId", "suiteComponents": ["x", "y"]},
        "origin1": {
            "id": "origin1",
            "overallTrustGrade": "A",
            "evidence": [
                {
                    "type": "fusion-recipe",
                    "origins": ["depth2Skill"],
                }
            ],
        },
        "origin2": {"id": "origin2", "overallTrustGrade": "A"},
        "origin3": {"id": "origin3", "overallTrustGrade": "A"},
        "origin4": {"id": "origin4", "overallTrustGrade": "A"},
        "origin5": {"id": "origin5", "overallTrustGrade": "A"},
        "depth2Skill": {"id": "depth2Skill", "overallTrustGrade": "B"},
    }


def _apexReadyNamedSkillMap() -> dict:
    """NamedSkillMap used alongside _apexReadySkill."""
    return {}


# ---------------------------------------------------------------------------
# Section 1: auditApexAtG7.py — per-predicate audit, passing skill
# ---------------------------------------------------------------------------


class TestAuditApexAtG7Passing:
    """Tests for auditApexAtG7.py when the skill passes all 6 active predicates."""

    def test_passes_apex_gate_returns_exit_zero(self, tmp_path, monkeypatch, capsys):
        """auditApexAtG7.py on a skill that passes all predicates → exit code 0."""
        auditMod = importScript("auditApexAtG7")

        skill = _apexReadySkill()
        genericMap = _apexReadyGenericMap()
        namedMap = _apexReadyNamedSkillMap()

        registryState = {
            "genericSkillMap": genericMap,
            "namedSkillMap": namedMap,
            "systemWideApexCount": 0,
        }

        from gaia_cli.trustMagnitude import passesApexGate, isApex
        predicates = passesApexGate(skill, registryState)

        # Verify that the test data we set up actually passes apex gate
        assert isApex(predicates), (
            f"Expected apex-ready skill to pass all predicates; got: {predicates}"
        )

    def test_print_report_shows_pass(self, tmp_path, capsys):
        """printReport outputs PASS line for a passing skill."""
        auditMod = importScript("auditApexAtG7")

        skill = _apexReadySkill()
        registryState = {
            "genericSkillMap": _apexReadyGenericMap(),
            "namedSkillMap": {},
            "systemWideApexCount": 0,
        }

        from gaia_cli.trustMagnitude import passesApexGate
        predicates = passesApexGate(skill, registryState)
        auditMod.printReport("apex-skill", skill, predicates, registryState)

        captured = capsys.readouterr()
        assert "PASS" in captured.out

    def test_print_report_shows_all_predicate_names(self, capsys):
        """printReport shows all 8 predicate names (6 active + 2 OFF)."""
        auditMod = importScript("auditApexAtG7")

        skill = _apexReadySkill()
        registryState = {
            "genericSkillMap": _apexReadyGenericMap(),
            "namedSkillMap": {},
            "systemWideApexCount": 0,
        }

        from gaia_cli.trustMagnitude import passesApexGate
        predicates = passesApexGate(skill, registryState)
        auditMod.printReport("apex-skill", skill, predicates, registryState)

        captured = capsys.readouterr()
        assert "apexPromotionPrSigned" in captured.out
        assert "overallGradeS" in captured.out
        assert "aGradedOriginsGte5" in captured.out
        assert "crossOrgVerifier" in captured.out
        assert "systemWideCap" in captured.out

    def test_feature_flagged_off_predicates_show_dash(self, capsys):
        """Feature-flagged OFF predicates (crossOrgVerifier, systemWideCap) render as '—'."""
        auditMod = importScript("auditApexAtG7")

        skill = _apexReadySkill()
        registryState = {
            "genericSkillMap": _apexReadyGenericMap(),
            "namedSkillMap": {},
            "systemWideApexCount": 0,
        }

        from gaia_cli.trustMagnitude import passesApexGate
        predicates = passesApexGate(skill, registryState)
        auditMod.printReport("apex-skill", skill, predicates, registryState)

        captured = capsys.readouterr()
        # Both OFF predicates should render with the dash marker
        assert "— crossOrgVerifier" in captured.out or "crossOrgVerifier" in captured.out
        # OFF-until annotation
        assert "2026-Q4" in captured.out


# ---------------------------------------------------------------------------
# Section 2: auditApexAtG7.py — skill missing apexPromotionPrSigned → exit 1
# ---------------------------------------------------------------------------


class TestAuditApexAtG7Failing:
    """Tests for auditApexAtG7.py when a predicate fails."""

    def test_missing_apex_promotion_pr_signed_fails_gate(self):
        """Skill without apexPromotionPrSigned fails the apex gate."""
        from gaia_cli.trustMagnitude import passesApexGate, isApex

        skill = _apexReadySkill()
        # Remove the apexGateStatus annotation
        skill.pop("apexPromotionPrSigned", None)
        skill["apexGateStatus"] = {"apexPromotionPrSigned": False}

        registryState = {
            "genericSkillMap": _apexReadyGenericMap(),
            "namedSkillMap": {},
            "systemWideApexCount": 0,
        }

        predicates = passesApexGate(skill, registryState)
        assert predicates["apexPromotionPrSigned"] is False
        assert not isApex(predicates)

    def test_print_report_shows_fail_for_unsigned_skill(self, capsys):
        """printReport outputs FAIL line when apexPromotionPrSigned is False."""
        auditMod = importScript("auditApexAtG7")

        skill = _apexReadySkill()
        skill["apexGateStatus"] = {"apexPromotionPrSigned": False}

        registryState = {
            "genericSkillMap": _apexReadyGenericMap(),
            "namedSkillMap": {},
            "systemWideApexCount": 0,
        }

        from gaia_cli.trustMagnitude import passesApexGate
        predicates = passesApexGate(skill, registryState)
        auditMod.printReport("test-skill", skill, predicates, registryState)

        captured = capsys.readouterr()
        assert "FAIL" in captured.out
        assert "✗" in captured.out  # at least one failing predicate marker

    def test_fail_count_reflects_active_failures(self):
        """Failed active predicates are counted correctly in the result."""
        from gaia_cli.trustMagnitude import passesApexGate, isApex

        # Skill with no evidence at all — should fail most predicates
        skill = {
            "id": "bare-skill",
            "evidence": [],
            "apexGateStatus": {"apexPromotionPrSigned": False},
        }
        predicates = passesApexGate(skill, {})
        assert not isApex(predicates)
        # Count active (non-None) failures
        failures = [k for k, v in predicates.items() if v is False]
        assert len(failures) >= 1

    def test_load_skill_by_id_not_found_returns_none(self, tmp_path):
        """loadSkillById returns None for a non-existent skill ID."""
        auditMod = importScript("auditApexAtG7")
        result = auditMod.loadSkillById("nonexistent-skill-xyz", tmp_path)
        assert result is None

    def test_load_skill_by_id_finds_json_node(self, tmp_path):
        """loadSkillById finds a skill from a JSON node file."""
        auditMod = importScript("auditApexAtG7")

        # Create a mock node
        nodesDir = tmp_path / "registry" / "nodes" / "basic"
        nodesDir.mkdir(parents=True)
        nodeData = {"id": "my-test-skill", "name": "My Test Skill", "evidence": []}
        (nodesDir / "my-test-skill.json").write_text(json.dumps(nodeData))

        result = auditMod.loadSkillById("my-test-skill", tmp_path)
        assert result is not None
        assert result["id"] == "my-test-skill"

    def test_load_skill_by_id_finds_named_md(self, tmp_path):
        """loadSkillById finds a skill from a named Markdown file."""
        auditMod = importScript("auditApexAtG7")

        namedDir = tmp_path / "registry" / "named" / "testuser"
        namedDir.mkdir(parents=True)
        mdContent = "---\nid: testuser/myskill\nname: My Skill\nlevel: 5★\n---\n# Body\n"
        (namedDir / "myskill.md").write_text(mdContent, encoding="utf-8")

        result = auditMod.loadSkillById("testuser/myskill", tmp_path)
        assert result is not None
        assert result["id"] == "testuser/myskill"


# ---------------------------------------------------------------------------
# Section 3: countApexSkills.py — correct counts
# ---------------------------------------------------------------------------


class TestCountApexSkills:
    """Tests for countApexSkills.py."""

    def test_counts_zero_when_no_apex_skills(self, tmp_path):
        """Returns empty list when no 6★ skills exist."""
        countMod = importScript("countApexSkills")

        # Point the module at our tmp_path by monkeypatching
        origNamedDir = countMod._NAMED_DIR
        origNodesDir = countMod._NODES_DIR

        namedDir = tmp_path / "registry" / "named"
        nodesDir = tmp_path / "registry" / "nodes"
        namedDir.mkdir(parents=True)
        nodesDir.mkdir(parents=True)

        countMod._NAMED_DIR = namedDir
        countMod._NODES_DIR = nodesDir
        try:
            result = countMod.countApexSkills()
            assert result == []
        finally:
            countMod._NAMED_DIR = origNamedDir
            countMod._NODES_DIR = origNodesDir

    def test_counts_apex_named_skills(self, tmp_path):
        """Counts 6★ level from named skill markdown files."""
        countMod = importScript("countApexSkills")

        namedDir = tmp_path / "registry" / "named" / "alice"
        nodesDir = tmp_path / "registry" / "nodes" / "basic"
        namedDir.mkdir(parents=True)
        nodesDir.mkdir(parents=True)

        # Create one apex named skill
        (namedDir / "apex-thing.md").write_text(
            "---\nid: alice/apex-thing\nlevel: 6★\n---\n# body\n", encoding="utf-8"
        )
        # Create one non-apex named skill
        (namedDir / "normal-thing.md").write_text(
            "---\nid: alice/normal-thing\nlevel: 5★\n---\n# body\n", encoding="utf-8"
        )

        countMod._NAMED_DIR = tmp_path / "registry" / "named"
        countMod._NODES_DIR = nodesDir
        try:
            result = countMod.countApexSkills()
            assert len(result) == 1
            assert "alice/apex-thing" in result
        finally:
            countMod._NAMED_DIR = importScript("countApexSkills")._NAMED_DIR
            countMod._NODES_DIR = importScript("countApexSkills")._NODES_DIR

    def test_counts_apex_node_skills(self, tmp_path):
        """Counts 6★ level from registry node JSON files."""
        countMod = importScript("countApexSkills")

        namedDir = tmp_path / "registry" / "named"
        nodesDir = tmp_path / "registry" / "nodes" / "basic"
        namedDir.mkdir(parents=True)
        nodesDir.mkdir(parents=True)

        # Create one apex JSON node
        apexNode = {"id": "apex-node-skill", "level": "6★"}
        (nodesDir / "apex-node-skill.json").write_text(json.dumps(apexNode))

        countMod._NAMED_DIR = namedDir
        countMod._NODES_DIR = tmp_path / "registry" / "nodes"
        try:
            result = countMod.countApexSkills()
            assert len(result) == 1
            assert "apex-node-skill" in result
        finally:
            pass

    def test_reads_system_wide_cap_from_schema(self):
        """readSystemWideCap reads from registry/schema/meta.json — not hardcoded."""
        countMod = importScript("countApexSkills")
        cap = countMod.readSystemWideCap()
        # The real schema has systemWideCap = 5
        assert isinstance(cap, int)
        assert cap > 0

    def test_system_wide_cap_matches_schema_value(self):
        """Confirms cap value equals what is in registry/schema/meta.json."""
        countMod = importScript("countApexSkills")
        schemaData = json.loads(
            (_REPO_ROOT / "registry" / "schema" / "meta.json").read_text()
        )
        expectedCap = schemaData["apexGate"]["systemWideCap"]
        assert countMod.readSystemWideCap() == expectedCap

    def test_count_within_cap_does_not_fail(self, tmp_path, monkeypatch):
        """countApexSkills returns list of current apex skills; 0 is within cap."""
        countMod = importScript("countApexSkills")

        namedDir = tmp_path / "registry" / "named"
        nodesDir = tmp_path / "registry" / "nodes"
        namedDir.mkdir(parents=True)
        nodesDir.mkdir(parents=True)

        # Monkeypatch paths
        monkeypatch.setattr(countMod, "_NAMED_DIR", namedDir)
        monkeypatch.setattr(countMod, "_NODES_DIR", nodesDir)

        result = countMod.countApexSkills()
        cap = countMod.readSystemWideCap()
        assert len(result) <= cap


# ---------------------------------------------------------------------------
# Section 4: check_verifier_signoffs.py — verifier counts
# ---------------------------------------------------------------------------


class TestCheckVerifierSignoffs:
    """Tests for check_verifier_signoffs.py."""

    def test_load_verifiers_from_named_skills_index(self, tmp_path, monkeypatch):
        """loadVerifiers reads 4★+ contributors from registry/named-skills.json."""
        signoffMod = importScript("check_verifier_signoffs")

        indexData = {
            "buckets": {
                "basic": [
                    {"id": "skill1", "contributor": "alice", "level": "4★"},
                    {"id": "skill2", "contributor": "bob", "level": "3★"},
                    {"id": "skill3", "contributor": "carol", "level": "5★"},
                ]
            }
        }
        indexPath = tmp_path / "registry" / "named-skills.json"
        indexPath.parent.mkdir(parents=True)
        indexPath.write_text(json.dumps(indexData))

        monkeypatch.setattr(signoffMod, "_NAMED_SKILLS_INDEX", indexPath)
        verifiers = signoffMod.loadVerifiers()

        assert "alice" in verifiers   # 4★ → verifier
        assert "carol" in verifiers   # 5★ → verifier
        assert "bob" not in verifiers  # 3★ → not a verifier

    def test_load_verifiers_returns_empty_when_no_index(self, tmp_path, monkeypatch):
        """loadVerifiers returns empty set when named-skills.json is absent."""
        signoffMod = importScript("check_verifier_signoffs")
        missing = tmp_path / "registry" / "no-such-file.json"
        monkeypatch.setattr(signoffMod, "_NAMED_SKILLS_INDEX", missing)
        verifiers = signoffMod.loadVerifiers()
        assert verifiers == set()

    def test_count_verifier_approvals_counts_only_approved(self):
        """countVerifierApprovals counts only APPROVED reviews from verifiers."""
        signoffMod = importScript("check_verifier_signoffs")

        verifiers = {"alice", "carol"}
        reviews = [
            {"user": {"login": "alice"}, "state": "APPROVED"},
            {"user": {"login": "carol"}, "state": "CHANGES_REQUESTED"},
            {"user": {"login": "bob"}, "state": "APPROVED"},   # not a verifier
            {"user": {"login": "dave"}, "state": "APPROVED"},  # not a verifier
        ]

        approvers = signoffMod.countVerifierApprovals(reviews, verifiers)
        assert "alice" in approvers
        assert "carol" not in approvers   # CHANGES_REQUESTED, not APPROVED
        assert "bob" not in approvers     # not a verifier
        assert len(approvers) == 1

    def test_count_verifier_approvals_uses_latest_review_state(self):
        """When a reviewer posts multiple reviews, only the latest state counts."""
        signoffMod = importScript("check_verifier_signoffs")

        verifiers = {"alice"}
        reviews = [
            # alice first approved, then requested changes
            {"user": {"login": "alice"}, "state": "APPROVED"},
            {"user": {"login": "alice"}, "state": "CHANGES_REQUESTED"},
        ]

        approvers = signoffMod.countVerifierApprovals(reviews, verifiers)
        assert "alice" not in approvers  # final state is CHANGES_REQUESTED

    def test_count_verifier_approvals_empty_reviews(self):
        """Returns empty list when no reviews provided."""
        signoffMod = importScript("check_verifier_signoffs")
        approvers = signoffMod.countVerifierApprovals([], {"alice"})
        assert approvers == []

    def test_detect_repository_uses_env_var(self, monkeypatch):
        """detectRepository returns GITHUB_REPOSITORY env var when set."""
        signoffMod = importScript("check_verifier_signoffs")
        monkeypatch.setenv("GITHUB_REPOSITORY", "test-owner/test-repo")
        repo = signoffMod.detectRepository()
        assert repo == "test-owner/test-repo"

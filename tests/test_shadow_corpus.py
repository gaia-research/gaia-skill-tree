"""Tests for Yggdrasil IV registry census and shadow evaluation runner."""

from __future__ import annotations

import copy
import datetime as dt
import json
from pathlib import Path

import pytest

from gaia_cli import shadowCorpus as sc
from gaia_cli import shadowEvaluation as shadow
from gaia_cli import trustMagnitude as tm
from gaia_cli.fusionScore import computeFusionScore


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_TIME = dt.datetime(2026, 10, 25, 0, 0, 0, tzinfo=dt.timezone.utc)


# ---------------------------------------------------------------------------
# 1. Output Path Safeguards
# ---------------------------------------------------------------------------


def test_output_path_safeguards_reject_canonical_paths() -> None:
    """Safeguards must reject canonical/public directories."""
    forbiddenCases = [
        "registry",
        "registry/named",
        "registry/nodes",
        "docs",
        "docs/graph",
        "skill-trees",
        "skill-trees/alice",
        "src",
        "src/gaia_cli",
        ".agents/skills",
        ".claude/skills",
        ".github",
        "./docs/about.html",
    ]
    for path in forbiddenCases:
        with pytest.raises(ValueError, match="Output path rejected"):
            sc.validateOutputPath(path, repoRoot=REPO_ROOT)


def test_output_path_safeguards_allow_ignored_and_external_paths(tmp_path: Path) -> None:
    """Safeguards must allow external paths and allowed gitignored local paths."""
    # External path
    external = tmp_path / "shadow-results"
    assert sc.validateOutputPath(external, repoRoot=REPO_ROOT) == external.resolve()

    # Allowed local directories
    for allowed in [".gaia/shadow", "generated-output/shadow", ".tmp/shadow"]:
        expected = (REPO_ROOT / allowed).resolve()
        assert sc.validateOutputPath(allowed, repoRoot=REPO_ROOT) == expected


# ---------------------------------------------------------------------------
# 2. Complete Registry Census on Current Live Corpus
# ---------------------------------------------------------------------------


def test_census_full_corpus_statuses_and_counts() -> None:
    """Census must load every record and reconcile yaml.safe_load vs load_yaml_simple."""
    census = sc.censusRegistry(REPO_ROOT, failClosed=True, evaluationAtUTC=PINNED_TIME)

    assert census.totalNamedFiles == 398
    assert census.statusCounts == {"named": 350, "awakened": 48}
    assert census.totalGenericFiles == 299
    assert census.namedEvidenceRowCount == 613
    assert census.genericEvidenceRowCount == 254
    assert census.cacheHashCount == 347

    # Parser reconciliation
    assert len(census.parseFailures) == 0
    assert len(census.parserDiscrepancies) == 0
    assert len(census.missingIds) == 0
    assert len(census.unresolvedRefs) == 0
    assert census.isValid is True


# ---------------------------------------------------------------------------
# 3. Fail-Closed Parsing in Synthetic Malformed Repository
# ---------------------------------------------------------------------------


def test_parse_failure_fail_closed_in_synthetic_repo(tmp_path: Path) -> None:
    """Census must record parse failures honestly and fail closed."""
    reg = tmp_path / "registry"
    nodes = reg / "nodes"
    named = reg / "named" / "author"
    nodes.mkdir(parents=True)
    named.mkdir(parents=True)

    # Valid generic
    (nodes / "good.json").write_text('{"id": "good-gen", "evidence": []}', encoding="utf-8")
    # Broken generic JSON
    (nodes / "corrupt.json").write_text('{not valid json', encoding="utf-8")

    # Valid named
    (named / "good.md").write_text(
        "---\nid: author/good\nstatus: named\ngenericSkillRef: good-gen\nevidence: []\n---\n# Good\n",
        encoding="utf-8",
    )
    # Broken frontmatter
    (named / "corrupt.md").write_text(
        "---\nid: author/corrupt\nstatus: [unclosed list\n---\n# Corrupt\n",
        encoding="utf-8",
    )

    census = sc.censusRegistry(tmp_path, failClosed=True)
    assert census.isValid is False
    assert len(census.parseFailures) == 2
    failedPaths = [p["path"] for p in census.parseFailures]
    assert any("corrupt.json" in p for p in failedPaths)
    assert any("corrupt.md" in p for p in failedPaths)


# ---------------------------------------------------------------------------
# 4. Manifest Before/After Catches Concurrent Input Mutation
# ---------------------------------------------------------------------------


def test_manifest_verification_detects_mutation(tmp_path: Path) -> None:
    """Manifest verification must detect file modification, addition, and deletion."""
    reg = tmp_path / "registry" / "nodes"
    reg.mkdir(parents=True)
    f1 = reg / "a.json"
    f1.write_text('{"id": "a"}', encoding="utf-8")

    before = sc.buildFileDigestManifest(tmp_path)
    clean, disc = sc.verifyFileDigestManifest(before, tmp_path)
    assert clean is True
    assert len(disc) == 0

    # Modify file
    f1.write_text('{"id": "a-modified"}', encoding="utf-8")
    cleanMod, discMod = sc.verifyFileDigestManifest(before, tmp_path)
    assert cleanMod is False
    assert any("file-modified" in item for item in discMod)

    # Add file
    f2 = reg / "b.json"
    f2.write_text('{"id": "b"}', encoding="utf-8")
    cleanAdd, discAdd = sc.verifyFileDigestManifest(before, tmp_path)
    assert cleanAdd is False
    assert any("file-added" in item for item in discAdd)

    # Delete file
    f1.unlink()
    cleanDel, discDel = sc.verifyFileDigestManifest(before, tmp_path)
    assert cleanDel is False
    assert any("file-deleted" in item for item in discDel)


# ---------------------------------------------------------------------------
# 5. Seam Coordination: Preserves Valid Coverage on Invalid Input
# ---------------------------------------------------------------------------


def test_seam_coordination_preserves_valid_coverage(tmp_path: Path) -> None:
    """Seam coordinator must evaluate valid skills even if an invalid skill exists."""
    validSkill = {
        "id": "author/valid",
        "evidence": [
            {"type": "github-stars-own", "source": "https://github.com/a/valid", "stars": 1000},
        ],
    }
    futureSkill = {
        "id": "author/future",
        "evidence": [
            {"type": "repo-own", "source": "https://github.com/a/future", "lastVerified": "2029-01-01T00:00:00Z"},
        ],
    }
    suiteSkill = {
        "id": "author/suite",
        "suiteComponents": ["author/valid"],
        "evidence": [],
    }

    ctx = shadow.ShadowEvaluationContext(
        evaluationAtUTC=PINNED_TIME,
        policyVersion="g7-v1",
        policyDigest="digest",
        benchmarkCatalog={"benchmarks": []},
        benchmarkCatalogDigest="cat-digest",
        registryRevision="rev1",
        canonicalInputDigest="input-digest",
        genericSkillMap={},
        namedSkillMap={},
        verifierStanding={},
        perRowGradeThresholds={},
        gradeCeiling={},
        gradeThresholds={"S": 250, "A": 100, "B": 50, "C": 20},
    )

    result = sc.evaluateRegistryWithSeam([validSkill, futureSkill, suiteSkill], ctx)
    assert result["status"] == "partial"
    assessments = {a["skillId"]: a for a in result["assessments"]}

    assert assessments["author/valid"]["status"] == "evaluated"
    assert assessments["author/valid"]["tmRaw"] == 70.0

    assert assessments["author/future"]["status"] == "not-evaluated"
    assert "future date" in assessments["author/future"]["reason"]

    assert assessments["author/suite"]["status"] == "evaluated"


# ---------------------------------------------------------------------------
# 6. Dependency Cycle Handling
# ---------------------------------------------------------------------------


def test_dependency_cycle_is_reported_honestly() -> None:
    """Skills participating in a suite component cycle must be reported not-evaluated."""
    skillX = {"id": "author/x", "suiteComponents": ["author/y"], "evidence": []}
    skillY = {"id": "author/y", "suiteComponents": ["author/x"], "evidence": []}

    ctx = shadow.ShadowEvaluationContext(
        evaluationAtUTC=PINNED_TIME,
        policyVersion="g7-v1",
        policyDigest="digest",
        benchmarkCatalog={"benchmarks": []},
        benchmarkCatalogDigest="cat-digest",
        registryRevision="rev1",
        canonicalInputDigest="input-digest",
        genericSkillMap={},
        namedSkillMap={},
        verifierStanding={},
        perRowGradeThresholds={},
        gradeCeiling={},
        gradeThresholds={"S": 250, "A": 100, "B": 50, "C": 20},
    )

    result = sc.evaluateRegistryWithSeam([skillX, skillY], ctx)
    assert result["status"] == "not-evaluated"
    for assessment in result["assessments"]:
        assert assessment["status"] == "not-evaluated"
        assert "dependency cycle" in assessment["reason"]


# ---------------------------------------------------------------------------
# 7. Threshold Transitions & Star Ceiling Proposals
# ---------------------------------------------------------------------------


def test_threshold_transition_triggers_demotion_risk() -> None:
    """TM drop crossing grade floor must propose a lower grade ceiling and flag demotion risk."""
    highSkill = {
        "id": "author/high",
        "level": "4★",
        "evidence": [
            {"type": "github-stars-own", "source": "https://github.com/a/h", "stars": 10000},
        ],
    }
    lowSkill = {
        "id": "author/low",
        "level": "4★",
        "evidence": [
            {"type": "github-stars-own", "source": "https://github.com/a/l", "stars": 1000},
        ],
    }

    ctx = shadow.ShadowEvaluationContext(
        evaluationAtUTC=PINNED_TIME,
        policyVersion="g7-v1",
        policyDigest="digest",
        benchmarkCatalog={"benchmarks": []},
        benchmarkCatalogDigest="cat-digest",
        registryRevision="rev1",
        canonicalInputDigest="input-digest",
        genericSkillMap={},
        namedSkillMap={},
        verifierStanding={},
        perRowGradeThresholds={"github-stars-own": {"A": 100, "B": 50}},
        gradeCeiling={},
        gradeThresholds={"S": 250, "A": 100, "B": 50, "C": 20},
    )

    highResult = shadow.evaluateShadow(highSkill, ctx)
    lowResult = shadow.evaluateShadow(lowSkill, ctx)

    assert highResult["tmRaw"] == 105.0
    assert highResult["grade"] == "A"
    assert highResult["gradeCeilingProposal"] == 4

    assert lowResult["tmRaw"] == 70.0
    assert lowResult["grade"] == "B"
    assert lowResult["gradeCeilingProposal"] == 3


# ---------------------------------------------------------------------------
# 8. Fusion Score Invariance
# ---------------------------------------------------------------------------


def test_evidence_changes_leave_fusion_score_invariant() -> None:
    """Fusion Score is purely structural and must remain unchanged across evidence changes."""
    skillBefore = {
        "id": "author/fusion-test",
        "prerequisites": ["generic/a", "generic/b"],
        "evidence": [
            {"type": "github-stars-own", "source": "https://github.com/a/f", "stars": 50000},
        ],
    }
    skillAfter = copy.deepcopy(skillBefore)
    skillAfter["evidence"] = [
        {"type": "github-stars-own", "source": "https://github.com/a/f", "stars": 500},
    ]

    fsBefore = computeFusionScore(skillBefore)
    fsAfter = computeFusionScore(skillAfter)
    assert fsBefore == fsAfter


# ---------------------------------------------------------------------------
# 9. CLI Run and Report Writing into Temp/Ignored Directory
# ---------------------------------------------------------------------------


def test_cli_shadow_command_writes_into_scratch(tmp_path: Path) -> None:
    """CLI must write valid deterministic machine JSON and readable summary into scratch."""
    outDir = tmp_path / "shadow-output"
    reportData = sc.runShadowEvaluation(
        registryPath=REPO_ROOT,
        evaluationAtUTC=PINNED_TIME,
        filterStatus="awakened",  # Bounded subset for fast test
    )
    written = sc.writeShadowReport(reportData, outDir, repoRoot=REPO_ROOT)

    assert written["json"].is_file()
    assert written["summary"].is_file()

    # Verify JSON content
    loaded = json.loads(written["json"].read_text(encoding="utf-8"))
    assert loaded["metadata"]["engineVersion"] == shadow.SHADOW_ENGINE_VERSION
    assert loaded["summary"]["targetSkillsCount"] == 48
    assert loaded["summary"]["manifestVerification"]["clean"] is True

    # Verify summary text
    summaryText = written["summary"].read_text(encoding="utf-8")
    assert "GAIA YGGDRASIL IV TRUST MAGNITUDE" in summaryText
    assert "Total Named Records       : 398" in summaryText

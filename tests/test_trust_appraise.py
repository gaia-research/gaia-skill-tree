"""Focused regressions for the non-mutating suite appraisal script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "trust_appraise.py"


def loadAppraiser():
    spec = importlib.util.spec_from_file_location("trust_appraise", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(spec.name)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop(spec.name, None)
        else:
            sys.modules[spec.name] = previous
    return module


def test_suite_appraisal_grades_the_actual_synthetic_evidence(monkeypatch):
    appraiser = loadAppraiser()
    monkeypatch.setattr(appraiser, "repoMeta", lambda _repo: {
        "stargazerCount": 200000,
        "isArchived": False,
        "defaultBranchRef": {"name": "main"},
    })
    monkeypatch.setattr(appraiser, "contributorStats", lambda _repo: (100, 100000))

    def failIfLegacyGradeCall(*_args, **_kwargs):
        raise AssertionError("appraise() must grade the synthetic skill evidence")

    monkeypatch.setattr(appraiser, "computeOverallTrustGrade", failIfLegacyGradeCall, raising=False)
    result = appraiser.appraise(appraiser.AppraisalTarget("example/suite", 1, "SKILL.md"))

    assert result["tm"] == 186.54
    assert result["grade"] == "A"
    assert "fusion-recipe" not in result["byType"]


def test_appraise_skill_named_resolves_real_tm():
    """Named skill appraises with real TM from .md frontmatter (Issue #1742)."""
    appraiser = loadAppraiser()
    result = appraiser.appraise_skill("leonxlnx/taste-skill")
    assert result["skillRef"] == "leonxlnx/taste-skill"
    assert isinstance(result["tm"], (int, float)) and result["tm"] > 0
    assert result["grade"] == "A"
    assert "github-stars-own" in result["byType"]
    assert "repo-own" in result["byType"]
    assert "fusionScore" in result
    assert result.get("fusionScoreVersion") == "yggdrasil-iii-v1"
    assert len(result.get("rows", [])) >= 2


def test_appraise_skill_named_resolves_frozen_inputs_exact_tm():
    """Hermetic appraisal with frozen inputs resolves exact TM deterministically."""
    appraiser = loadAppraiser()
    frozen_skill = {
        "id": "synthetic/frozen-skill",
        "evidence": [
            {
                "type": "github-stars-own",
                "source": "https://github.com/example/repo/blob/main/SKILL.md",
                "stars": 79067,
            },
            {
                "type": "repo-own",
                "source": "https://github.com/example/repo",
                "commits": 100,
                "contributors": 10,
            },
        ],
    }
    tm = appraiser.computeTrustMagnitude(frozen_skill)
    assert round(tm, 2) == 172.43


def test_appraise_node_delegation():
    """appraiseNode delegates directly to appraise_skill."""
    appraiser = loadAppraiser()
    res1 = appraiser.appraise_skill("leonxlnx/taste-skill")
    res2 = appraiser.appraiseNode("leonxlnx/taste-skill")
    assert res1 == res2



# ---------------------------------------------------------------------------
# #2052: metric provenance, appraisal scope, claim status (offline, synthetic)
# ---------------------------------------------------------------------------


def _fakeRepo(appraiser, monkeypatch, contributions=(500, 316)):
    monkeypatch.setattr(appraiser, "repoMeta", lambda _repo: {
        "stargazerCount": 1000,
        "isArchived": False,
        "updatedAt": "2026-10-01T00:00:00Z",
        "defaultBranchRef": {"name": "main"},
    })
    rows = [{"login": f"c{i}", "contributions": n} for i, n in enumerate(contributions)]
    monkeypatch.setattr(appraiser, "runJson", lambda _command: rows)


def test_contributor_stats_is_a_contribution_sum(monkeypatch):
    appraiser = loadAppraiser()
    _fakeRepo(appraiser, monkeypatch)
    assert appraiser.contributorStats("example/tool") == (2, 816)


def test_contribution_sum_stays_distinct_from_unique_commits(monkeypatch):
    from gaia_cli.curationCheckpoint import exportClaims

    appraiser = loadAppraiser()
    _fakeRepo(appraiser, monkeypatch)
    result = appraiser.appraise(appraiser.AppraisalTarget("example/tool", 1, "SKILL.md"))

    assert "commits" not in result
    assert result["contributorContributionSum"] == 816
    claims = {c["metric"]: c for c in result["metricClaims"]}
    assert claims["contributorContributionSum"]["value"] == 816
    assert "not a count of unique reachable commits" in claims["contributorContributionSum"]["method"]
    assert claims["repo-own.commits (engine input)"]["status"] == "inferred"

    uniqueCommits = {
        "metric": "uniqueReachableCommits",
        "value": 826,
        "status": "verified",
        "method": "git rev-list --count <default-branch>",
        "repro": "synthetic fixture",
    }
    exported = exportClaims(result["metricClaims"] + [uniqueCommits])
    byMetric = {c["metric"]: c["value"] for c in exported}
    assert byMetric["contributorContributionSum"] == 816
    assert byMetric["uniqueReachableCommits"] == 826
    assert not any(c["metric"] == "commits" for c in exported)


def test_proposal_is_labelled_partial_own_only(monkeypatch):
    appraiser = loadAppraiser()
    _fakeRepo(appraiser, monkeypatch)
    result = appraiser.appraise(appraiser.AppraisalTarget("example/tool", 1, "SKILL.md"))

    assert result["scope"] == "named-own/proposal"
    assert result["genericResolution"] == "not evaluated"
    assert result["totalStatus"] == "partial"
    assert "not the effective named TM" in result["tmLabel"]
    assert result["sourceRevision"]["defaultBranch"] == "main"
    assert result["sourceRevision"]["repoUpdatedAt"] == "2026-10-01T00:00:00Z"
    # Value unchanged: the repo-own input still receives the contribution sum.
    assert round(result["byType"]["repo-own"], 3) == 7.25


def _namedFixture(tmp_path):
    named = tmp_path / "registry" / "named" / "example" / "tool.md"
    named.parent.mkdir(parents=True)
    named.write_text(
        "---\n"
        "id: example/tool\n"
        "genericSkillRef: synthetic-generic\n"
        "evidence:\n"
        "  - type: repo-own\n"
        "    source: https://github.com/example/tool\n"
        "    commits: 816\n"
        "    contributors: 2\n"
        "---\n",
        encoding="utf-8",
    )


GENERIC_MAP = {"synthetic-generic": {"id": "synthetic-generic", "evidence": [
    {"type": "arxiv", "source": "https://example.org/paper", "citations": 100, "layer": "generic"}
]}}


def test_named_appraisal_scope_effective_vs_not_evaluated(tmp_path, monkeypatch):
    appraiser = loadAppraiser()
    _namedFixture(tmp_path)
    monkeypatch.setattr(appraiser, "REPO_ROOT", tmp_path)

    resolved = appraiser.appraise_skill("example/tool", generic_map=dict(GENERIC_MAP), named_map={})
    assert resolved["tm"] == 21.25
    assert resolved["scope"] == "effective named"
    assert resolved["genericResolution"] == "resolved"
    assert resolved["totalStatus"] == "final"

    missing = appraiser.appraise_skill("example/tool", generic_map={}, named_map={})
    assert missing["tm"] == 7.25
    assert missing["scope"] == "named-own"
    assert missing["genericResolution"] == "not evaluated"
    assert missing["totalStatus"] == "partial"
    assert missing["registryRevision"]

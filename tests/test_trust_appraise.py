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

    # Compute expected TM independently via canonical TM engine rather than hardcoding a magic number
    from gaia_cli.registryMaps import buildMergedSkillMap
    from gaia_cli.trustMagnitude import computeTrustMagnitude
    import yaml

    named_path = ROOT / "registry" / "named" / "leonxlnx" / "taste-skill.md"
    m = appraiser.FRONTMATTER_RE.match(named_path.read_text(encoding="utf-8"))
    assert m is not None, "Named skill must have valid frontmatter"
    fm = yaml.safe_load(m.group(1))
    merged_map = buildMergedSkillMap(ROOT)
    expected_tm = round(computeTrustMagnitude(fm, merged_map), 2)

    assert result["tm"] == expected_tm
    assert result["grade"] == "A"
    assert "github-stars-own" in result["byType"]


def test_appraise_node_delegation():
    """appraiseNode delegates directly to appraise_skill."""
    appraiser = loadAppraiser()
    res1 = appraiser.appraise_skill("leonxlnx/taste-skill")
    res2 = appraiser.appraiseNode("leonxlnx/taste-skill")
    assert res1 == res2


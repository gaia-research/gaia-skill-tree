"""Tests for the Yggdrasil III Fusion Score (structural lane).

The invariants that matter most are the *independence* ones: Fusion Score and
Trust Magnitude must never move each other. Everything else in this file is
mechanics — the curve, the closure, the breakdown determinism.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest

from gaia_cli.fusionScore import (
    FUSION_MAX_DEPTH,
    FUSION_SCORE_VERSION,
    computeFusionScore,
    explainFusionScore,
    fusionScalar,
    fusionScoreProjection,
    resolveFusionStructure,
)
from gaia_cli.trustMagnitude import computeTrustMagnitude

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Fixtures — a small hand-built structural graph
# ---------------------------------------------------------------------------


def _basic(skillId):
    return {"id": skillId, "type": "basic"}


@pytest.fixture
def graph():
    """A five-leaf generic recipe plus a suite that nests another suite.

    generic-fusion  --prereq-->  leaf-a .. leaf-e
    named/suite     --suite-->   named/inner, leaf-a
    named/inner     --suite-->   leaf-b, leaf-c
    """
    nodes = {
        "leaf-a": _basic("leaf-a"),
        "leaf-b": _basic("leaf-b"),
        "leaf-c": _basic("leaf-c"),
        "leaf-d": _basic("leaf-d"),
        "leaf-e": _basic("leaf-e"),
        "generic-fusion": {
            "id": "generic-fusion",
            "type": "fusion",
            "prerequisites": ["leaf-a", "leaf-b", "leaf-c", "leaf-d", "leaf-e"],
        },
        "named/inner": {
            "id": "named/inner",
            "genericSkillRef": "leaf-a",
            "suiteComponents": ["leaf-b", "leaf-c"],
        },
        "named/suite": {
            "id": "named/suite",
            "genericSkillRef": "leaf-a",
            "suiteComponents": ["named/inner", "leaf-a"],
        },
    }
    return nodes


# ---------------------------------------------------------------------------
# The V1 curve
# ---------------------------------------------------------------------------


def test_no_structure_scores_zero(graph):
    assert computeFusionScore(_basic("leaf-a"), graph, graph) == 0.0
    assert fusionScalar(0) == 0.0


def test_linear_below_the_knee():
    for n in range(1, 11):
        assert fusionScalar(n) == pytest.approx(20.0 * n)


def test_sqrt_softening_above_the_knee():
    assert fusionScalar(11) == pytest.approx(200.0 + 20.0)
    assert fusionScalar(26) == pytest.approx(200.0 + 20.0 * 4)
    # Softening must actually soften: doubling N past the knee must add less
    # than the linear rate would.
    assert fusionScalar(40) - fusionScalar(20) < 20.0 * 20


def test_curve_is_monotonic_and_two_decimal_stable():
    previous = -1.0
    for n in range(0, 300):
        value = fusionScalar(n)
        assert value >= previous
        assert value == round(value, 2)
        previous = value


def test_generic_prerequisites_contribute(graph):
    assert computeFusionScore(graph["generic-fusion"], graph, graph) == 100.0


# ---------------------------------------------------------------------------
# Closure semantics
# ---------------------------------------------------------------------------


def test_duplicate_paths_count_once(graph):
    # named/suite reaches leaf-a directly AND through nothing else; named/inner
    # reaches leaf-b and leaf-c. Closure = {named/inner, leaf-a, leaf-b, leaf-c}.
    structure = resolveFusionStructure(graph["named/suite"], graph, graph)
    assert structure["nodes"] == ["leaf-a", "leaf-b", "leaf-c", "named/inner"]
    assert len(structure["nodes"]) == 4


def test_root_is_excluded_from_its_own_closure():
    selfRef = {
        "id": "self-fusion",
        "prerequisites": ["self-fusion", "leaf-a"],
    }
    nodes = {"self-fusion": selfRef, "leaf-a": _basic("leaf-a")}
    structure = resolveFusionStructure(selfRef, nodes, nodes)
    assert structure["nodes"] == ["leaf-a"]
    assert computeFusionScore(selfRef, nodes, nodes) == 20.0


def test_variant_role_never_counts():
    nodes = {
        "root": {"id": "root", "prerequisites": ["kept", "dropped"]},
        "kept": _basic("kept"),
        "dropped": {"id": "dropped", "role": "variant"},
    }
    structure = resolveFusionStructure(nodes["root"], nodes, nodes)
    assert structure["nodes"] == ["kept"]


def test_inline_variant_role_on_a_fusion_origin_never_counts():
    root = {
        "id": "root",
        "evidence": [
            {
                "type": "fusion-recipe",
                "origins": [
                    {"id": "kept"},
                    {"id": "dropped", "role": "variant"},
                ],
            }
        ],
    }
    nodes = {"root": root, "kept": _basic("kept"), "dropped": _basic("dropped")}
    assert resolveFusionStructure(root, nodes, nodes)["nodes"] == ["kept"]


def test_fusion_recipe_origins_are_a_fallback_not_a_second_count():
    """An origin already reachable canonically must not be counted twice."""
    nodes = {
        "generic": {"id": "generic", "prerequisites": ["leaf-a"]},
        "leaf-a": _basic("leaf-a"),
        "named/x": {
            "id": "named/x",
            "genericSkillRef": "generic",
            "evidence": [{"type": "fusion-recipe", "origins": ["leaf-a"]}],
        },
    }
    structure = resolveFusionStructure(nodes["named/x"], nodes, nodes)
    assert structure["nodes"] == ["leaf-a"]
    assert computeFusionScore(nodes["named/x"], nodes, nodes) == 20.0


def test_cycles_fail_closed_without_hanging():
    nodes = {
        "a": {"id": "a", "prerequisites": ["b"]},
        "b": {"id": "b", "prerequisites": ["c"]},
        "c": {"id": "c", "prerequisites": ["a", "b"]},
    }
    structure = resolveFusionStructure(nodes["a"], nodes, nodes)
    assert structure["nodes"] == ["b", "c"]
    assert computeFusionScore(nodes["a"], nodes, nodes) == 40.0


def test_traversal_stops_at_the_declared_limit():
    depth = FUSION_MAX_DEPTH + 5
    nodes = {
        f"n{i}": {"id": f"n{i}", "prerequisites": [f"n{i + 1}"]}
        for i in range(depth)
    }
    nodes[f"n{depth}"] = _basic(f"n{depth}")
    structure = resolveFusionStructure(nodes["n0"], nodes, nodes)
    assert structure["truncated"] is True
    assert structure["maxDepth"] == FUSION_MAX_DEPTH


def test_unresolvable_ids_still_count_as_structure():
    root = {"id": "root", "suiteComponents": ["ghost-one", "ghost-two"]}
    structure = resolveFusionStructure(root, {}, {})
    assert structure["nodes"] == ["ghost-one", "ghost-two"]


# ---------------------------------------------------------------------------
# Breakdown
# ---------------------------------------------------------------------------


def test_breakdown_is_deterministic(graph):
    first = fusionScoreProjection(graph["named/suite"], graph, graph)
    second = fusionScoreProjection(graph["named/suite"], graph, graph)
    assert first == second
    assert first["fusionScoreVersion"] == FUSION_SCORE_VERSION
    assert first["fusionBreakdown"] == {
        "directCount": 2,
        "transitiveCount": 4,
        "maxDepth": 2,
        "nestedSuiteCount": 1,
    }


def test_transitive_count_is_the_scored_n(graph):
    projection = fusionScoreProjection(graph["named/suite"], graph, graph)
    assert projection["fusionScore"] == fusionScalar(
        projection["fusionBreakdown"]["transitiveCount"]
    )


def test_explain_states_the_independence_and_the_arithmetic(graph):
    text = explainFusionScore(graph["generic-fusion"], graph, graph)
    assert "Fusion Score: 100.00" in text
    assert "independent of Trust Magnitude" in text
    assert "FS = 20 x 5 = 100.00" in text


def test_explain_always_says_why_the_numbers_moved(graph):
    """A returning reader must never see a Fusion Score without the migration.

    They are looking at a Trust Magnitude that dropped. Omitting the note
    invites the one false reading — "my skill was downgraded" — so it is
    printed for a scored skill and an unscored one alike.
    """
    for skill in (graph["generic-fusion"], _basic("leaf-a")):
        text = explainFusionScore(skill, graph, graph)
        assert "Why the numbers moved:" in text
        assert "Yggdrasil II" in text
        assert "0 TM" in text
        assert "No evidence, star, or rank was changed." in text


def test_frontend_strip_carries_the_same_migration_framing():
    """The browser surface must state the movement visibly, not only on hover."""
    source = (REPO_ROOT / "docs" / "js" / "skill-explorer.js").read_text(encoding="utf-8")
    assert "se-fs-migration" in source
    assert "Yggdrasil III" in source
    assert "inside" in source
    assert "No evidence, star, or rank changed" in source


# ---------------------------------------------------------------------------
# Independence invariants — the load-bearing ones
# ---------------------------------------------------------------------------


def _evidenceRow(source):
    return {
        "type": "repo-own",
        "source": source,
        "commits": 400,
        "contributors": 5,
    }


def test_changing_evidence_does_not_change_fusion_score(graph):
    skill = dict(graph["named/suite"])
    before = fusionScoreProjection(skill, graph, graph)

    skill["evidence"] = [
        _evidenceRow("https://github.com/acme/one"),
        {"type": "github-stars-own", "source": "https://github.com/acme/one", "stars": 9000},
        {"type": "peer-review", "source": "https://example.test/review", "reviewers": 4},
    ]
    skill["level"] = "6★"
    skill["overallTrustGrade"] = "S"
    skill["trustMagnitude"] = 991.0
    after = fusionScoreProjection(skill, graph, graph)

    assert after == before


def test_changing_structure_does_not_change_trust_magnitude(graph):
    skill = {
        "id": "named/tm-probe",
        "genericSkillRef": "leaf-a",
        "evidence": [_evidenceRow("https://github.com/acme/one")],
    }
    tmBefore = computeTrustMagnitude(skill, graph)
    fsBefore = computeFusionScore(skill, graph, graph)

    skill["suiteComponents"] = ["leaf-b", "leaf-c", "leaf-d"]
    tmAfter = computeTrustMagnitude(skill, graph)
    fsAfter = computeFusionScore(skill, graph, graph)

    assert tmAfter == tmBefore, "structural change must not move Trust Magnitude"
    assert fsAfter > fsBefore, "structural change must move Fusion Score"


def test_fusion_score_ignores_grade_stars_and_freshness():
    """Two identical structures whose targets differ only in trust must tie."""
    plain = {
        "id": "plain-target",
    }
    decorated = {
        "id": "decorated-target",
        "level": "6★",
        "overallTrustGrade": "S",
        "trustMagnitude": 4200.0,
        "stars": 90000,
        "lastVerified": "2020-01-01",
        "evidence": [_evidenceRow("https://github.com/acme/two")],
    }
    nodes = {
        "plain-root": {"id": "plain-root", "prerequisites": ["plain-target"]},
        "decorated-root": {"id": "decorated-root", "prerequisites": ["decorated-target"]},
        "plain-target": plain,
        "decorated-target": decorated,
    }
    assert computeFusionScore(nodes["plain-root"], nodes, nodes) == computeFusionScore(
        nodes["decorated-root"], nodes, nodes
    )


# ---------------------------------------------------------------------------
# Persistence and single-authority guards
# ---------------------------------------------------------------------------


def test_fusion_score_is_never_persisted_in_registry_source():
    """The registry stores structural inputs, not the derived answer."""
    offenders = []
    for path in (REPO_ROOT / "registry" / "named").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        header = text.split("---", 2)[1] if text.startswith("---") else ""
        if "fusionScore" in header:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    for path in (REPO_ROOT / "registry" / "nodes").rglob("*.json"):
        if "fusionScore" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], f"Fusion Score must not be persisted in registry source: {offenders}"


def test_no_frontend_file_reimplements_the_formula():
    """Browser code consumes the generated value; it must not carry the curve.

    The signature we forbid is the softening constant pair (200 / sqrt) applied
    to a fusion count in JavaScript. `docs/js/` may read `fusionScore` and
    `fusionBreakdown` freely — it just may not derive them.
    """
    offenders = []
    for path in (REPO_ROOT / "docs" / "js").glob("*.js"):
        text = path.read_text(encoding="utf-8")
        if not re.search(r"fusionScore|fusionBreakdown", text):
            continue
        if re.search(r"Math\.sqrt", text):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], (
        "frontend must not recompute Fusion Score; render the generated value: "
        f"{offenders}"
    )


def test_python_result_equals_the_generated_public_projection():
    """Every fusionScore in the shipped index must match a fresh computation.

    Scope note: this asserts *agreement*, not *presence*. The index is a
    generated artifact — it can legitimately be absent (fresh clone; it is
    rebuilt by `scripts/build_docs.py`) or predate the projection on a stacked
    branch. Whether the projection actually ran is enforced where it belongs,
    by `build_docs.py --check` in CI. What this test owns is the invariant that
    a shipped number never disagrees with the Python authority.
    """
    indexPath = REPO_ROOT / "docs" / "graph" / "named" / "index.json"
    if not indexPath.exists():
        pytest.skip("docs/graph/named/index.json not generated in this checkout")

    from gaia_cli.registryMaps import buildMergedSkillMap

    index = json.loads(indexPath.read_text(encoding="utf-8"))
    scored = [
        entry
        for entries in (index.get("buckets") or {}).values()
        for entry in entries
        if "fusionScore" in entry
    ]
    if not scored:
        pytest.skip("index predates the Fusion Score projection; nothing to compare")

    mergedMap = buildMergedSkillMap(REPO_ROOT)
    for entry in scored:
        expected = fusionScoreProjection(entry, mergedMap, mergedMap)
        assert entry["fusionScore"] == expected["fusionScore"], entry.get("id")
        assert entry["fusionBreakdown"] == expected["fusionBreakdown"], entry.get("id")
        assert entry["fusionScoreVersion"] == FUSION_SCORE_VERSION

"""Live-engine agreement for the canonical curation authority map (#2052).

Byte parity between `.agents/skills` and `.claude/skills` cannot catch semantic
drift. These tests parse docs/agents/curation-authority-map.md and compare every
number it states with the live Trust Magnitude engine. They also reject retired
claims in the trust skills and curation docs that point at the map.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from gaia_cli import promotion
from gaia_cli.steward.knowledge_contracts import BANNED_PATTERNS, TRUST_SURFACES, bannedClaims
from gaia_cli.trustMagnitude import (
    EVIDENCE_TYPE_LAYER_CONTRACT,
    GRADE_A_FLOOR,
    GRADE_B_FLOOR,
    GRADE_C_FLOOR,
    GRADE_S_FLOOR,
    TYPE_CAPS,
    TYPE_WEIGHTS,
    computeOverallTrustGrade,
    computeTrustMagnitude,
)

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "docs" / "agents" / "curation-authority-map.md"
MAP_LINK = "curation-authority-map.md"


def mapText() -> str:
    return MAP.read_text(encoding="utf-8")


def tableRows(text: str, header: str) -> list[list[str]]:
    """Return the body rows of the first markdown table whose header starts with ``header``."""
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if line.startswith(header):
            rows = []
            for row in lines[idx + 2:]:
                if not row.startswith("|"):
                    break
                rows.append([cell.strip() for cell in row.strip().strip("|").split("|")])
            return rows
    raise AssertionError(f"table not found: {header}")


def cellNumber(cell: str) -> float | None:
    return None if cell in ("none", "n/a") else float(cell)


def scoringDisagreements(text: str) -> list[str]:
    """Compare the map's §1 table with the engine. Empty list means agreement."""
    problems: list[str] = []
    rows = tableRows(text, "| Evidence Type | Weight | Cap |")
    seen = set()
    for etype, weight, cap, inherit, _raw, probe, probeTm in rows:
        seen.add(etype)
        if TYPE_WEIGHTS.get(etype) != float(weight):
            problems.append(f"{etype}: weight {weight} != engine {TYPE_WEIGHTS.get(etype)}")
        if TYPE_CAPS.get(etype) != cellNumber(cap):
            problems.append(f"{etype}: cap {cap} != engine {TYPE_CAPS.get(etype)}")
        contract = EVIDENCE_TYPE_LAYER_CONTRACT[etype]["inheritMultiplier"]
        stated = None if inherit == "pinned-named" else float(inherit)
        if contract != stated:
            problems.append(f"{etype}: inherit {inherit} != engine {contract}")
        if probe != "catalog-gated":
            row = {"type": etype, "source": f"https://example.org/{etype}", **json.loads(probe.strip("`"))}
            live = round(computeTrustMagnitude({"id": "probe", "evidence": [row]}), 3)
            if live != float(probeTm):
                problems.append(f"{etype}: probe TM {probeTm} != engine {live}")
    missing = set(TYPE_WEIGHTS) - seen
    if missing:
        problems.append(f"engine types missing from map: {sorted(missing)}")
    return problems


def gradeMaxStars() -> dict[str, int]:
    """Extract the GRADE_MAX_STARS clamp literal from scripts/generateNamedIndex.py."""
    tree = ast.parse((ROOT / "scripts" / "generateNamedIndex.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "GRADE_MAX_STARS" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("GRADE_MAX_STARS clamp not found in generateNamedIndex.py")


def gradeDisagreements(text: str) -> list[str]:
    problems: list[str] = []
    floors = {"S": GRADE_S_FLOOR, "A": GRADE_A_FLOOR, "B": GRADE_B_FLOOR, "C": GRADE_C_FLOOR}
    clamp = gradeMaxStars()
    for grade, floor, _extra, maxStars in tableRows(text, "| Overall Trust Grade | TM floor |"):
        if grade in floors and floors[grade] != float(floor):
            problems.append(f"grade {grade}: floor {floor} != engine {floors[grade]}")
        if clamp.get(grade) != int(maxStars):
            problems.append(f"grade {grade}: max stars {maxStars} != clamp {clamp.get(grade)}")
    return problems


# ---------------------------------------------------------------------------
# The map agrees with the live engine
# ---------------------------------------------------------------------------


def test_map_scoring_table_agrees_with_engine():
    assert scoringDisagreements(mapText()) == []


def test_map_grade_table_agrees_with_engine_and_clamp():
    assert gradeDisagreements(mapText()) == []


def _named(generic: bool = False) -> tuple[dict, dict | None]:
    named = {
        "id": "example/tool",
        "genericSkillRef": "synthetic-generic",
        "evidence": [{"type": "repo-own", "source": "https://github.com/example/tool",
                      "commits": 816, "contributors": 2}],
    }
    genericMap = {"synthetic-generic": {"id": "synthetic-generic", "evidence": [
        {"type": "arxiv", "source": "https://example.org/paper", "citations": 100, "layer": "generic"}
    ]}}
    return named, (genericMap if generic else None)


def workedExamples() -> list[float]:
    named, _ = _named()
    _, genericMap = _named(generic=True)
    crossType = {"id": "x", "evidence": [
        {"type": "github-stars-own", "source": "https://github.com/example/tool", "stars": 1000},
        {"type": "repo-own", "source": "https://github.com/example/tool", "commits": 816, "contributors": 2},
    ]}
    divisor = {"id": "x", "evidence": [
        {"type": "github-stars-own", "source": "https://github.com/e/r", "stars": 1000, "skillCountInRepo": 50}
    ]}
    return [
        round(computeTrustMagnitude(named), 3),
        round(computeTrustMagnitude(named, genericMap), 3),
        round(computeTrustMagnitude(crossType), 3),
        round(computeTrustMagnitude(divisor), 3),
    ]


def test_map_worked_examples_agree_with_engine():
    stated = [float(tm) for _scenario, tm in tableRows(mapText(), "| Scenario | TM |")]
    assert stated == workedExamples()


# ---------------------------------------------------------------------------
# Issue #2052 exact offline repro numbers
# ---------------------------------------------------------------------------


def test_named_own_vs_effective_named_repro():
    named, _ = _named()
    _, genericMap = _named(generic=True)
    assert round(computeTrustMagnitude(named), 3) == 7.248
    assert round(computeTrustMagnitude(named, genericMap), 3) == 21.248


def test_cross_type_same_url_does_not_collapse():
    stars = {"type": "github-stars-own", "source": "https://github.com/example/tool", "stars": 1000}
    repo = {"type": "repo-own", "source": "https://github.com/example/tool", "commits": 816, "contributors": 2}
    both = computeTrustMagnitude({"id": "x", "evidence": [stars, repo]})
    alone = computeTrustMagnitude({"id": "x", "evidence": [stars]}) + computeTrustMagnitude(
        {"id": "x", "evidence": [repo]}
    )
    assert round(both, 3) == 77.248
    assert round(both, 3) == round(alone, 3)


@pytest.mark.parametrize("count", [1, 50])
def test_stars_score_ignores_skill_count_in_repo(count):
    row = {"type": "github-stars-own", "source": "https://github.com/e/r", "stars": 1000, "skillCountInRepo": count}
    assert computeTrustMagnitude({"id": "x", "evidence": [row]}) == 70.0


def test_four_star_requires_grade_a_strictly():
    clamp = gradeMaxStars()
    assert computeOverallTrustGrade(99.99, 3, False) == "B"
    assert clamp["B"] == 3
    assert computeOverallTrustGrade(100.0, 1, False) == "A"
    assert clamp["A"] == 4


@pytest.mark.parametrize("surface", [
    "CONTEXT.md", "META.md", "docs/codex/trust-methodology.html",
    "docs/meta/2026-06-trust-methodology.md",
    ".agents/skills/trust-methodology-consult/SKILL.md",
    ".claude/skills/trust-methodology-consult/SKILL.md",
])
def test_tm_storage_surfaces_preserve_the_cli_cache_ruling(surface):
    text = " ".join((ROOT / surface).read_text(encoding="utf-8").split())
    assert "gaia dev calibrate-trust-magnitude" in text
    assert "hash-signed" in text
    assert "eligible generic-layer evidence" in text
    # Fusion Score remains unpersisted; this checks the retired TM/grade claims.
    assert "evidence inventory, never stored on a node" not in text
    assert "never stored in a node" not in text
    assert "generated catalogs — never stored on a node" not in text
    assert promotion._UNIQUE_GATE_BY_LEVEL["4★"] == {"grade": "A", "tmFloor": 100.0}


# ---------------------------------------------------------------------------
# Trust skills / docs: reference the map, never restate retired claims
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rel", TRUST_SURFACES)
def test_trust_surface_points_at_map_and_has_no_retired_claims(rel):
    text = (ROOT / rel).read_text(encoding="utf-8")
    assert MAP_LINK in text, f"{rel} must reference {MAP_LINK}"
    assert bannedClaims(text) == [], f"{rel} restates retired claims"


def test_map_body_has_no_retired_claims():
    body = mapText().split("## Banned claims")[0]
    assert bannedClaims(body) == []


def test_write_back_helper_is_retired():
    for tree in (".agents", ".claude"):
        assert not (ROOT / tree / "skills" / "trust-methodology-consult" / "scripts" / "recompute_one_tm.py").exists()


# ---------------------------------------------------------------------------
# Negative controls: the checks are not vacuous
# ---------------------------------------------------------------------------


def test_negative_control_detects_wrong_weight_and_probe():
    text = mapText().replace(
        "| repo-own | 0.6 | 60.0 | pinned-named |", "| repo-own | 0.5 | 60.0 | pinned-named |"
    ).replace("`{\"stars\": 1000}` | 70.0 |", "`{\"stars\": 1000}` | 1.4 |")
    problems = scoringDisagreements(text)
    assert any("repo-own: weight" in p for p in problems)
    assert any("github-stars-own: probe TM" in p for p in problems)


def test_negative_control_detects_lenient_four_star_clamp():
    text = mapText().replace("| B | 50.0 | — | 3 |", "| B | 50.0 | — | 4 |")
    assert any("grade B: max stars" in p for p in gradeDisagreements(text))


@pytest.mark.parametrize(
    "sentence",
    [
        "- `github-stars-own` and `repo-own` pointing to the same URL → deduped; only the higher score counts",
        "per-skill contribution is tiny due to `/ skill_count_in_repo` divisor",
        "3. Does `overallTrustGrade` ≥ B (TM ≥ 50)? Grade A (TM ≥ 100) is the norm for 4★ in practice.",
        "    python3 .claude/skills/trust-methodology-consult/scripts/recompute_one_tm.py owner/skill",
        "`artifact_score = (stars/1000) / skill_count_in_repo * weight`",
    ],
)
def test_negative_control_detects_retired_sentences(sentence):
    assert bannedClaims(sentence) != []

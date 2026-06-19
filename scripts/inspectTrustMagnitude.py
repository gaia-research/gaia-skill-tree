#!/usr/bin/env python3
"""Inspect Trust Magnitude for named skills — single-skill breakdown or leaderboard.

Usage:
    python scripts/inspectTrustMagnitude.py --skill <skillId>
    python scripts/inspectTrustMagnitude.py --leaderboard
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

import yaml

# Make repo root and src/ importable.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from gaia_cli.trustMagnitude import (  # noqa: E402
    GRADE_A_FLOOR,
    GRADE_B_FLOOR,
    GRADE_C_FLOOR,
    GRADE_S_FLOOR,
    computeTrustMagnitude,
    computeOverallTrustGradeFromSkill,
    explainTrustMagnitude,
)

NAMED_DIR = REPO_ROOT / "registry" / "named"
NODES_DIR = REPO_ROOT / "registry" / "nodes"
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)", re.DOTALL)

# Force UTF-8 stdout (handles Windows cp1252)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def loadNamedSkill(path: Path) -> tuple[dict | None, str]:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    fm = yaml.safe_load(m.group(1)) or {}
    return fm, m.group(2)


def buildGenericSkillMap(nodesDir: Path) -> dict[str, dict]:
    gmap: dict[str, dict] = {}
    for p in nodesDir.rglob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        sid = d.get("id")
        if sid:
            gmap[sid] = d
    return gmap


def buildNamedSkillMap(namedDir: Path) -> dict[str, dict]:
    """Walk registry/named/**/*.md and return a dict keyed by skill id.

    Used so fusion-recipe origin lookups for suite components resolve to graded
    named skills rather than falling back to ``None`` (ungraded).
    """
    nmap: dict[str, dict] = {}
    for p in namedDir.rglob("*.md"):
        fm, _ = loadNamedSkill(p)
        if fm is None:
            continue
        sid = fm.get("id")
        if sid:
            nmap[sid] = fm
    return nmap


def buildMergedMap(nodesDir: Path, namedDir: Path) -> dict[str, dict]:
    """Return genericSkillMap merged with namedSkillMap.

    Named skill IDs use ``owner/name`` form and never collide with generic IDs.
    The merged map lets ``_gradedOriginCount`` resolve suite-component origins.
    """
    gmap = buildGenericSkillMap(nodesDir)
    nmap = buildNamedSkillMap(namedDir)
    return {**gmap, **nmap}


def loadAllNamedSkills() -> list[dict]:
    skills = []
    for p in sorted(NAMED_DIR.rglob("*.md")):
        fm, _ = loadNamedSkill(p)
        if fm is None:
            continue
        skills.append(fm)
    return skills


def nextGradeInfo(tm: float) -> tuple[str, float]:
    """Return (nextGrade, pointsNeeded) for current TM."""
    if tm >= GRADE_S_FLOOR:
        return ("S (already at top)", 0.0)
    if tm >= GRADE_A_FLOOR:
        return ("S", GRADE_S_FLOOR - tm)
    if tm >= GRADE_B_FLOOR:
        return ("A", GRADE_A_FLOOR - tm)
    if tm >= GRADE_C_FLOOR:
        return ("B", GRADE_B_FLOOR - tm)
    return ("C", GRADE_C_FLOOR - tm)


def mostEfficientNextType(skill: dict, genericSkillMap: dict) -> str:
    """Suggest the most efficient evidence type to add for more TM."""
    existingTypes = {
        r.get("type") for r in (skill.get("evidence") or [])
        if isinstance(r, dict) and r.get("type")
    }
    suggestions = []
    if "verifier-attestation" not in existingTypes:
        suggestions.append("verifier-attestation (30 TM per verifier, weight 1.5 = 45 raw)")
    if "github-stars-own" not in existingTypes:
        suggestions.append("github-stars-own (1000 stars = 1.0 magnitude, weight 1.0 = 1.0 TM)")
    if "benchmark-result" not in existingTypes:
        suggestions.append("benchmark-result (percentile-based, weight 1.4, cap 100)")
    if "proxy-containment" not in existingTypes:
        suggestions.append("proxy-containment (10k+ external stars required, weight 1.0, cap 160)")
    if "arxiv" not in existingTypes:
        suggestions.append("arxiv (citations/5 magnitude, weight 1.0, cap 100)")
    if suggestions:
        return suggestions[0]
    return "Add more evidence rows with higher grades (A/S)"


def inspectMode(skillId: str) -> int:
    print(f"Loading skill maps from {NODES_DIR} + {NAMED_DIR}...")
    genericSkillMap = buildMergedMap(NODES_DIR, NAMED_DIR)

    # Find the skill file
    found = None
    for p in NAMED_DIR.rglob("*.md"):
        fm, _ = loadNamedSkill(p)
        if fm is None:
            continue
        fmId = fm.get("id") or p.stem
        # Accept exact match or contributor/name match
        if fmId == skillId or p.stem == skillId or str(p.relative_to(NAMED_DIR)).replace("\\", "/").replace(".md", "") == skillId:
            found = (p, fm)
            break

    if found is None:
        print(f"ERROR: skill '{skillId}' not found in {NAMED_DIR}", file=sys.stderr)
        return 1

    path, fm = found
    skillDisplayId = fm.get("id") or path.stem
    print(f"\n{'='*70}")
    print(f"Trust Magnitude Inspection: {skillDisplayId}")
    print(f"File: {path.relative_to(REPO_ROOT).as_posix()}")
    print(f"{'='*70}\n")

    explanation = explainTrustMagnitude(fm, genericSkillMap)
    print(explanation)

    # Next grade analysis
    tm = computeTrustMagnitude(fm, genericSkillMap)
    nextGrade, pointsNeeded = nextGradeInfo(tm)
    print(f"\n--- Next Grade Analysis ---")
    if pointsNeeded > 0:
        print(f"  Current TM: {tm:.2f}")
        print(f"  Next grade: {nextGrade}")
        print(f"  Points needed: {pointsNeeded:.2f}")
        print(f"  Most efficient type to add: {mostEfficientNextType(fm, genericSkillMap)}")
    else:
        print(f"  Already at top grade (S, TM={tm:.2f})")

    # Suite components info
    suiteComponents = fm.get("suiteComponents") or []
    if suiteComponents:
        print(f"\n--- Fusion Recipe (auto-derived) ---")
        print(f"  suiteComponents count: {len(suiteComponents)}")
        print(f"  Components: {', '.join(suiteComponents[:10])}")
        if len(suiteComponents) > 10:
            print(f"  ... and {len(suiteComponents)-10} more")

    return 0


def leaderboardMode() -> int:
    print(f"Loading skill maps from {NODES_DIR} + {NAMED_DIR}...")
    genericSkillMap = buildMergedMap(NODES_DIR, NAMED_DIR)

    print(f"Loading all named skills from {NAMED_DIR}...")
    skills = loadAllNamedSkills()
    print(f"Found {len(skills)} named skills\n")

    # Compute TM for all skills with live calculation
    rows = []
    for fm in skills:
        skillId = fm.get("id") or "unknown"
        tm = computeTrustMagnitude(fm, genericSkillMap)
        grade = computeOverallTrustGradeFromSkill(fm, genericSkillMap)
        level = fm.get("level") or fm.get("rank") or "?"
        contributor = skillId.split("/")[0] if "/" in skillId else "?"
        rows.append({
            "skillId": skillId,
            "tm": tm,
            "grade": grade,
            "level": level,
            "contributor": contributor,
        })

    rows.sort(key=lambda r: -r["tm"])

    # Print leaderboard
    grade_bands = [
        ("S", "S grade (TM >= 250)", lambda r: r["grade"] == "S"),
        ("A", "A grade (TM >= 100, <250)", lambda r: r["grade"] == "A"),
        ("B", "B grade (TM >= 50, <100)", lambda r: r["grade"] == "B"),
        ("C", "C grade (TM >= 20, <50)", lambda r: r["grade"] == "C"),
        ("ungraded", "Ungraded (TM < 20)", lambda r: r["grade"] == "ungraded"),
    ]

    print(f"{'='*75}")
    print(f"GAIA TRUST MAGNITUDE LEADERBOARD — {len(rows)} named skills")
    print(f"{'='*75}")

    rank = 1
    for bandKey, bandLabel, filterFn in grade_bands:
        bandRows = [r for r in rows if filterFn(r)]
        if not bandRows:
            continue
        print(f"\n[ {bandLabel} ] ({len(bandRows)} skills)")
        print(f"  {'Rank':<6} {'ID':<45} {'TM':>8}  {'Grade':<7} {'Level'}")
        print(f"  {'-'*6} {'-'*45} {'-'*8}  {'-'*7} {'-'*10}")
        for r in bandRows:
            print(f"  {rank:<6} {r['skillId']:<45} {r['tm']:>8.2f}  {r['grade']:<7} {r['level']}")
            rank += 1

    print(f"\n{'='*75}")
    print(f"Total: {len(rows)} skills | Grades: " +
          " | ".join(
              f"{g}={sum(1 for r in rows if r['grade']==g)}"
              for g in ["S", "A", "B", "C", "ungraded"]
          ))
    print(f"{'='*75}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Trust Magnitude for named skills")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--skill", metavar="SKILL_ID",
                       help="Skill ID (e.g. contributor/name) to inspect in detail")
    group.add_argument("--leaderboard", action="store_true",
                       help="Show ranked leaderboard of all named skills by TM")
    args = parser.parse_args()

    if args.leaderboard:
        return leaderboardMode()
    else:
        return inspectMode(args.skill)


if __name__ == "__main__":
    sys.exit(main())

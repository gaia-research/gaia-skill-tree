#!/usr/bin/env python3
"""Inspect Trust Magnitude for named skills — single-skill breakdown or leaderboard.

Usage:
    python scripts/inspectTrustMagnitude.py --skill <skillId>          # terminal
    python scripts/inspectTrustMagnitude.py --skill <skillId> --json   # JSON to stdout
    python scripts/inspectTrustMagnitude.py --skill <skillId> --html [--out path.html]
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
    APEX_AGRADED_ORIGINS_MIN,
    GRADE_A_FLOOR,
    GRADE_B_FLOOR,
    GRADE_C_FLOOR,
    GRADE_S_FLOOR,
    computeTrustMagnitude,
    computeOverallTrustGradeFromSkill,
    explainTrustMagnitude,
    passesApexGate,
    isApex,
)
from auditApexAtG7 import formatPredicateDetail  # noqa: E402

NAMED_DIR = REPO_ROOT / "registry" / "named"
NODES_DIR = REPO_ROOT / "registry" / "nodes"
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)", re.DOTALL)

# Force UTF-8 stdout (handles Windows cp1252)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# CONTEXT.md nomenclature: the axis is "stars"; individual values use rank names
STARS_TO_RANK_NAME: dict[str, str] = {
    "0★": "Unawakened",
    "1★": "Awakened",
    "2★": "Named",
    "3★": "Evolved",
    "4★": "Hardened",
    "5★": "Transcendent",
    "6★": "Transcendent ★",
}

# G7 RFC §10.10: trust grade -> effective stars
GRADE_TO_EFFECTIVE_STARS: dict[str, str] = {
    "S":        "5★",
    "A":        "4★",
    "B":        "3★",
    "C":        "2★",
    "ungraded": "1★",
}

STARS_ORDER: dict[str, int] = {
    "0★": 0, "1★": 1, "2★": 2, "3★": 3,
    "4★": 4, "5★": 5, "6★": 6,
}

# Human-readable labels for apex gate predicates (RFC §11.12)
APEX_GATE_LABELS: dict[str, str] = {
    "aGradedOriginsGte5":          f"§11.12.5  >={APEX_AGRADED_ORIGINS_MIN} A/S-graded origins in transitive closure",
    "sourceTenureDaysGte180AorS":  "§11.12.7  Tenure >= 180 days at A-or-S",
    "directNestedSuiteGte1":       "§11.12.2  >=1 direct component with suiteComponents",
    "depth2OnlyReachableGte1":     "§11.12.3  >=1 node reachable only at depth >= 2",
    "overallGradeS":               "§11.12.4  Overall Trust Grade S (strict-evidence reading)",
    "apexPromotionPrSigned":       "§11.12.8  apex-promotion PR signed by >=2 verifiers",
    "crossOrgVerifier":            "§11.12.6  >=2 cross-org 4-star+ verifier-attestations  [flagged OFF]",
    "systemWideCap":               "§11.12.9  System-wide <=5 apex skills  [flagged OFF]",
}


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
    """Walk registry/named/**/*.md, keyed by skill id."""
    nmap: dict[str, dict] = {}
    for p in namedDir.rglob("*.md"):
        fm, _ = loadNamedSkill(p)
        if fm is None:
            continue
        sid = fm.get("id")
        if sid:
            nmap[sid] = fm
    return nmap


def buildMaps() -> tuple[dict, dict]:
    """Return (mergedMap, namedSkillMap)."""
    gmap = buildGenericSkillMap(NODES_DIR)
    nmap = buildNamedSkillMap(NAMED_DIR)
    return {**gmap, **nmap}, nmap


def loadAllNamedSkills() -> list[dict]:
    skills = []
    for p in sorted(NAMED_DIR.rglob("*.md")):
        fm, _ = loadNamedSkill(p)
        if fm is None:
            continue
        skills.append(fm)
    return skills


def starsLabel(stars: str) -> str:
    """Return 'X★ RankName' e.g. '4★ Hardened'."""
    name = STARS_TO_RANK_NAME.get(stars, "")
    return f"{stars} {name}" if name else stars


def effectiveRank(grade: str, currentStars: str) -> tuple[str, str]:
    """Return (effectiveStars, flag) per G7 RFC.

    flag: '' clean | '[floor]' rank-floor §10.10 | '[up]' G7 implies promotion
    """
    g7Stars = GRADE_TO_EFFECTIVE_STARS.get(grade, "1★")
    currentOrd = STARS_ORDER.get(currentStars, -1)
    g7Ord = STARS_ORDER.get(g7Stars, 1)

    # Rank-floor: 4★+ blocked from landing below Evolved (3★)
    if currentOrd >= 4 and g7Ord < 3:
        return ("3★", "[floor]")

    # G7 grade implies higher stars than current
    if g7Ord > currentOrd >= 0:
        return (g7Stars, "[up]")

    return (g7Stars, "")


def nextGradeInfo(tm: float) -> tuple[str, float]:
    if tm >= GRADE_S_FLOOR:
        return ("S (already at top)", 0.0)
    if tm >= GRADE_A_FLOOR:
        return ("S", GRADE_S_FLOOR - tm)
    if tm >= GRADE_B_FLOOR:
        return ("A", GRADE_A_FLOOR - tm)
    if tm >= GRADE_C_FLOOR:
        return ("B", GRADE_B_FLOOR - tm)
    return ("C", GRADE_C_FLOOR - tm)


def mostEfficientNextType(skill: dict, mergedMap: dict) -> str:
    existingTypes = {
        r.get("type") for r in (skill.get("evidence") or [])
        if isinstance(r, dict) and r.get("type")
    }
    suggestions = []
    if "verifier-attestation" not in existingTypes:
        suggestions.append("verifier-attestation (30 TM per verifier, weight 1.5 = 45 raw)")
    if "github-stars-own" not in existingTypes:
        suggestions.append("github-stars-own (1000 stars = 1.0 magnitude, weight 1.0)")
    if "benchmark-result" not in existingTypes:
        suggestions.append("benchmark-result (percentile-based, weight 1.4, cap 100)")
    if "proxy-containment" not in existingTypes:
        suggestions.append("proxy-containment (10k+ external stars required, weight 1.0, cap 160)")
    if "arxiv" not in existingTypes:
        suggestions.append("arxiv (citations/5 magnitude, weight 1.0, cap 100)")
    return suggestions[0] if suggestions else "Add more evidence rows with higher grades (A/S)"


def formatApexGateLines(skill: dict, mergedMap: dict, namedSkillMap: dict) -> list[str]:
    """Return formatted lines for the apex gate (6-star predicates)."""
    state = {"genericSkillMap": mergedMap, "namedSkillMap": namedSkillMap}
    results = passesApexGate(skill, state)
    apex = isApex(results)
    activeResults = {k: v for k, v in results.items() if v is not None}
    passedCount = sum(1 for v in activeResults.values() if v)

    lines = []
    verdict = "PASS — apex-eligible" if apex else f"FAIL — {passedCount}/{len(activeResults)} active predicates passed"
    lines.append(f"  Apex gate (6-star Transcendent):  {verdict}")
    lines.append(f"  {'─'*64}")
    for key, val in results.items():
        mark = "PASS" if val is True else ("FAIL" if val is False else "OFF ")
        detail = formatPredicateDetail(key, val, skill, state)
        suffix = f"  {detail}" if detail else ""
        lines.append(f"    {mark}  {APEX_GATE_LABELS.get(key, key)}{suffix}")
    lines.append(f"  {'─'*64}")
    return lines


def inspectMode(skillId: str) -> int:
    print(f"Loading skill maps from {NODES_DIR} + {NAMED_DIR}...")
    mergedMap, namedSkillMap = buildMaps()

    found = None
    for p in NAMED_DIR.rglob("*.md"):
        fm, _ = loadNamedSkill(p)
        if fm is None:
            continue
        fmId = fm.get("id") or p.stem
        if (fmId == skillId or p.stem == skillId or
                str(p.relative_to(NAMED_DIR)).replace("\\", "/").replace(".md", "") == skillId):
            found = (p, fm)
            break

    if found is None:
        print(f"ERROR: skill '{skillId}' not found in {NAMED_DIR}", file=sys.stderr)
        return 1

    path, fm = found
    skillDisplayId = fm.get("id") or path.stem
    currentStars = fm.get("level") or fm.get("rank") or "?"
    print(f"\n{'='*70}")
    print(f"Trust Magnitude Inspection: {skillDisplayId}")
    print(f"File: {path.relative_to(REPO_ROOT).as_posix()}")
    print(f"{'='*70}\n")

    explanation = explainTrustMagnitude(fm, mergedMap)
    print(explanation)

    tm = computeTrustMagnitude(fm, mergedMap)
    grade = computeOverallTrustGradeFromSkill(fm, mergedMap)
    g7Stars, flag = effectiveRank(grade, currentStars)
    nextGrade, pointsNeeded = nextGradeInfo(tm)

    print(f"\n--- Stars & Grade ---")
    print(f"  Current stars:  {starsLabel(currentStars)}")
    print(f"  Trust Grade:    {grade}  (TM {tm:.2f})")
    print(f"  G7 Eff. stars:  {starsLabel(g7Stars)}{'  ' + flag if flag else ''}")

    print(f"\n--- Next Grade Analysis ---")
    if pointsNeeded > 0:
        print(f"  Next grade: {nextGrade}")
        print(f"  Points needed: {pointsNeeded:.2f}")
        print(f"  Most efficient type to add: {mostEfficientNextType(fm, mergedMap)}")
    else:
        print(f"  Already at top grade (S, TM={tm:.2f})")

    if grade == "S":
        print(f"\n--- Apex Gate (6-star predicates, RFC §11.12) ---")
        for line in formatApexGateLines(fm, mergedMap, namedSkillMap):
            print(line)

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
    mergedMap, namedSkillMap = buildMaps()

    print(f"Loading all named skills from {NAMED_DIR}...")
    skills = loadAllNamedSkills()
    print(f"Found {len(skills)} named skills\n")

    apexState = {"genericSkillMap": mergedMap, "namedSkillMap": namedSkillMap}

    rows = []
    for fm in skills:
        skillId = fm.get("id") or "unknown"
        tm = computeTrustMagnitude(fm, mergedMap)
        grade = computeOverallTrustGradeFromSkill(fm, mergedMap)
        currentStars = fm.get("level") or fm.get("rank") or "?"
        g7Stars, flag = effectiveRank(grade, currentStars)

        apexResults = None
        if grade == "S":
            apexResults = passesApexGate(fm, apexState)

        rows.append({
            "skillId": skillId,
            "tm": tm,
            "grade": grade,
            "currentStars": currentStars,
            "g7Stars": g7Stars,
            "flag": flag,
            "apexResults": apexResults,
            "skill": fm,
        })

    rows.sort(key=lambda r: -r["tm"])

    grade_bands = [
        ("S",        "S grade (TM >= 250)",    lambda r: r["grade"] == "S"),
        ("A",        "A grade (TM >= 100)",     lambda r: r["grade"] == "A"),
        ("B",        "B grade (TM >= 50)",      lambda r: r["grade"] == "B"),
        ("C",        "C grade (TM >= 20)",      lambda r: r["grade"] == "C"),
        ("ungraded", "Ungraded (TM < 20)",      lambda r: r["grade"] == "ungraded"),
    ]

    W = 100
    print(f"{'='*W}")
    print(f"GAIA TRUST MAGNITUDE LEADERBOARD — {len(rows)} named skills")
    print(f"{'='*W}")
    print(f"  Stars     = current stars (CONTEXT.md rank names: Awakened/Named/Evolved/Hardened/Transcendent)")
    print(f"  G7 Stars  = effective stars per G7 RFC (S=5-star A=4-star B=3-star C=2-star ungraded=1-star)")
    print(f"  [floor]   = rank-floor §10.10: 4-star+ held at >= Evolved (3-star) despite grade")
    print(f"  [up]      = G7 grade implies promotion above current stars")
    print(f"  Apex      = predicates passed / active (S-grade only, RFC §11.12)")

    pos = 1
    for bandKey, bandLabel, filterFn in grade_bands:
        bandRows = [r for r in rows if filterFn(r)]
        if not bandRows:
            continue
        print(f"\n[ {bandLabel} ] ({len(bandRows)} skills)")

        if bandKey == "S":
            print(f"  {'#':<5} {'ID':<47} {'TM':>8}  {'Grade':<6} {'Stars':<6} {'G7 Stars':<8} {'Note':<10} Apex")
            print(f"  {'-'*5} {'-'*47} {'-'*8}  {'-'*6} {'-'*6} {'-'*8} {'-'*10} {'-'*16}")
            for r in bandRows:
                ar = r["apexResults"] or {}
                activeVals = {k: v for k, v in ar.items() if v is not None}
                passedCount = sum(1 for v in activeVals.values() if v)
                failedKeys = [k for k, v in activeVals.items() if not v]
                apexSummary = f"{passedCount}/{len(activeVals)}"
                if failedKeys:
                    shortFailed = ", ".join(
                        k.replace("aGradedOriginsGte5", "A-origins")
                         .replace("sourceTenureDaysGte180AorS", "tenure")
                         .replace("directNestedSuiteGte1", "directNest")
                         .replace("depth2OnlyReachableGte1", "depth2")
                         .replace("overallGradeS", "gradeS")
                         .replace("apexPromotionPrSigned", "prSigned")
                        for k in failedKeys
                    )
                    apexSummary += f" FAIL:{shortFailed}"

                print(f"  {pos:<5} {r['skillId']:<47} {r['tm']:>8.2f}  {r['grade']:<6} {r['currentStars']:<6} {r['g7Stars']:<8} {r['flag']:<10} {apexSummary}")

                # Per-predicate detail inline (all, including flagged-OFF)
                for key, val in r["apexResults"].items():
                    mark = "PASS" if val is True else ("FAIL" if val is False else "OFF ")
                    label = APEX_GATE_LABELS.get(key, key)
                    detail = formatPredicateDetail(key, val, r["skill"], apexState)
                    suffix = f"  {detail}" if detail else ""
                    print(f"         {' '*49}  {mark}  {label}{suffix}")
                print()
                pos += 1
        else:
            print(f"  {'#':<5} {'ID':<47} {'TM':>8}  {'Grade':<6} {'Stars':<6} {'G7 Stars':<8} Note")
            print(f"  {'-'*5} {'-'*47} {'-'*8}  {'-'*6} {'-'*6} {'-'*8} {'-'*10}")
            for r in bandRows:
                print(f"  {pos:<5} {r['skillId']:<47} {r['tm']:>8.2f}  {r['grade']:<6} {r['currentStars']:<6} {r['g7Stars']:<8} {r['flag']}")
                pos += 1

    print(f"\n{'='*W}")
    print(f"Total: {len(rows)} skills | Grades: " +
          " | ".join(
              f"{g}={sum(1 for r in rows if r['grade']==g)}"
              for g in ["S", "A", "B", "C", "ungraded"]
          ))
    floors = sum(1 for r in rows if r["flag"] == "[floor]")
    ups = sum(1 for r in rows if r["flag"] == "[up]")
    print(f"Rank-floor protections: {floors} | Implied promotions [up]: {ups}")
    print(f"{'='*W}")
    return 0


def buildSkillJson(skillId: str, mergedMap: dict, namedSkillMap: dict) -> dict | None:
    """Return a structured dict for a skill — used by both --json and --html modes."""
    found = None
    for p in NAMED_DIR.rglob("*.md"):
        fm, _ = loadNamedSkill(p)
        if fm is None:
            continue
        fmId = fm.get("id") or p.stem
        if (fmId == skillId or p.stem == skillId or
                str(p.relative_to(NAMED_DIR)).replace("\\", "/").replace(".md", "") == skillId):
            found = (p, fm)
            break
    if found is None:
        return None

    path, fm = found
    tm = computeTrustMagnitude(fm, mergedMap)
    grade = computeOverallTrustGradeFromSkill(fm, mergedMap)
    currentStars = fm.get("level") or fm.get("rank") or "?"
    g7Stars, rankFlag = effectiveRank(grade, currentStars)
    nextGrade, pointsNeeded = nextGradeInfo(tm)

    apexResults = None
    if grade == "S":
        state = {"genericSkillMap": mergedMap, "namedSkillMap": namedSkillMap}
        apexResults = passesApexGate(fm, state)

    # Evidence rows
    evidenceRows = []
    for row in (fm.get("evidence") or []):
        if not isinstance(row, dict):
            continue
        evidenceRows.append({
            "type": row.get("type", ""),
            "source": row.get("source") or row.get("url") or "",
            "grade": row.get("grade") or row.get("class") or "",
            "sourceStartedAt": row.get("sourceStartedAt"),
            "lastVerified": row.get("lastVerified"),
            "stars": row.get("stars"),
            "views": row.get("views"),
            "citations": row.get("citations"),
        })

    # Suite components with sub-data
    suiteComponents = fm.get("suiteComponents") or []
    compRows = []
    for cid in suiteComponents:
        cfm = namedSkillMap.get(cid) or {}
        ctm = computeTrustMagnitude(cfm, mergedMap) if cfm else 0
        cgrade = computeOverallTrustGradeFromSkill(cfm, mergedMap) if cfm else "ungraded"
        cStars = cfm.get("level") or cfm.get("rank") or "?"
        cNested = cfm.get("suiteComponents") or []
        compRows.append({
            "id": cid,
            "name": cfm.get("name") or cfm.get("title") or cid.split("/")[-1],
            "tm": round(ctm, 2),
            "grade": cgrade,
            "stars": cStars,
            "nestedCount": len(cNested),
        })
    compRows.sort(key=lambda r: -r["tm"])

    return {
        "id": fm.get("id") or skillId,
        "name": fm.get("name") or fm.get("title") or skillId,
        "contributor": fm.get("contributor") or skillId.split("/")[0],
        "description": fm.get("description") or "",
        "stars": currentStars,
        "starsLabel": starsLabel(currentStars),
        "tm": round(tm, 2),
        "grade": grade,
        "g7Stars": g7Stars,
        "g7StarsLabel": starsLabel(g7Stars),
        "rankFlag": rankFlag,
        "nextGrade": nextGrade,
        "pointsNeeded": round(pointsNeeded, 2),
        "createdAt": fm.get("createdAt") or "",
        "updatedAt": fm.get("updatedAt") or "",
        "evidence": evidenceRows,
        "apexGate": apexResults,
        "components": compRows,
    }


def jsonMode(skillId: str) -> int:
    mergedMap, namedSkillMap = buildMaps()
    data = buildSkillJson(skillId, mergedMap, namedSkillMap)
    if data is None:
        print(f"ERROR: skill '{skillId}' not found", file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def buildLeaderboardRows() -> list[dict]:
    """Return the same row data the terminal leaderboard uses, JSON-serializable."""
    mergedMap, namedSkillMap = buildMaps()
    skills = loadAllNamedSkills()
    apexState = {"genericSkillMap": mergedMap, "namedSkillMap": namedSkillMap}

    rows = []
    for fm in skills:
        skillId = fm.get("id") or "unknown"
        tm = computeTrustMagnitude(fm, mergedMap)
        grade = computeOverallTrustGradeFromSkill(fm, mergedMap)
        currentStars = fm.get("level") or fm.get("rank") or "?"
        g7Stars, flag = effectiveRank(grade, currentStars)
        apexResults = passesApexGate(fm, apexState) if grade == "S" else None

        rows.append({
            "skillId": skillId,
            "tm": round(tm, 2),
            "grade": grade,
            "currentStars": currentStars,
            "g7Stars": g7Stars,
            "flag": flag,
            "apexResults": apexResults,
        })

    rows.sort(key=lambda r: -r["tm"])
    return rows


def leaderboardHtmlMode(outPath: str | None) -> int:
    print(f"Loading skill maps from {NODES_DIR} + {NAMED_DIR}...")
    rows = buildLeaderboardRows()
    print(f"Loaded {len(rows)} named skills")

    templatePath = REPO_ROOT / "scripts" / "leaderboard.html"
    if not templatePath.exists():
        print(f"ERROR: HTML template not found at {templatePath}", file=sys.stderr)
        return 1
    template = templatePath.read_text(encoding="utf-8")
    html = template.replace("__ROWS_DATA__", json.dumps(rows, ensure_ascii=False))

    if outPath is None:
        outDir = REPO_ROOT / "generated-output"
        outDir.mkdir(exist_ok=True)
        outPath = str(outDir / "leaderboard.html")

    Path(outPath).write_text(html, encoding="utf-8")
    print(f"Written: {outPath}")

    # Per-grade summary so the user can spot-check the file
    gradeCounts: dict[str, int] = {}
    for r in rows:
        gradeCounts[r["grade"]] = gradeCounts.get(r["grade"], 0) + 1
    summary = " ".join(f"{g}={gradeCounts.get(g,0)}" for g in ["S", "A", "B", "C", "ungraded"])
    floors = sum(1 for r in rows if r["flag"] == "[floor]")
    ups = sum(1 for r in rows if r["flag"] == "[up]")
    print(f"Total {len(rows)} | {summary} | rank-floor={floors} [up]={ups}")
    return 0


def htmlMode(skillId: str, outPath: str | None) -> int:
    mergedMap, namedSkillMap = buildMaps()
    data = buildSkillJson(skillId, mergedMap, namedSkillMap)
    if data is None:
        print(f"ERROR: skill '{skillId}' not found", file=sys.stderr)
        return 1

    templatePath = REPO_ROOT / "scripts" / "inspect_skill.html"
    if not templatePath.exists():
        print(f"ERROR: HTML template not found at {templatePath}", file=sys.stderr)
        return 1
    template = templatePath.read_text(encoding="utf-8")
    html = template.replace("__SKILL_DATA__", json.dumps(data, ensure_ascii=False))

    if outPath is None:
        safeId = skillId.replace("/", "_")
        outDir = REPO_ROOT / "generated-output"
        outDir.mkdir(exist_ok=True)
        outPath = str(outDir / f"inspect_{safeId}.html")

    Path(outPath).write_text(html, encoding="utf-8")
    print(f"Written: {outPath}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Trust Magnitude for named skills")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--skill", metavar="SKILL_ID",
                       help="Skill ID (e.g. contributor/name) to inspect in detail")
    group.add_argument("--leaderboard", action="store_true",
                       help="Show ranked leaderboard of all named skills by TM")
    parser.add_argument("--json", action="store_true",
                        help="Emit structured JSON instead of terminal text (--skill only)")
    parser.add_argument("--html", action="store_true",
                        help="Write interactive HTML viewer (works with --skill or --leaderboard)")
    parser.add_argument("--out", metavar="PATH",
                        help="Output path for --html (default: generated-output/<skillId>.html or generated-output/leaderboard.html)")
    args = parser.parse_args()

    if args.leaderboard:
        if args.html:
            return leaderboardHtmlMode(args.out)
        return leaderboardMode()
    if args.json:
        return jsonMode(args.skill)
    if args.html:
        return htmlMode(args.skill, args.out)
    return inspectMode(args.skill)


if __name__ == "__main__":
    sys.exit(main())

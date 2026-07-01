#!/usr/bin/env python3
"""Apex gate audit CLI — per-predicate 6★ eligibility report.

Usage:
  python scripts/auditApexAtG7.py <skill-id>
  python scripts/auditApexAtG7.py --pr <PR_NUMBER>

When --pr is given, the script scans the diff for newly-added 6★ lines in
registry/named/ or registry/nodes/ and audits each promoted skill.

Exit code:
  0 — all active predicates pass (or no skills found when --pr provided)
  1 — one or more active predicates fail
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Ensure gaia_cli is importable when run from repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from gaia_cli.trustMagnitude import (  # noqa: E402
    APEX_AGRADED_ORIGINS_MIN,
    APEX_TENURE_DAYS_MIN,
    GRADE_S_FLOOR,
    computeTrustMagnitude,
    isApex,
    passesApexGate,
)


# ---------------------------------------------------------------------------
# Skill loading helpers
# ---------------------------------------------------------------------------


def parseFrontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from a Markdown file."""
    import yaml

    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def loadSkillById(skillId: str, repoRoot: Path) -> Optional[dict]:
    """Locate and return the skill dict for the given skill ID.

    Searches:
      1. registry/named/<contributor>/<slug>.md  (for IDs like "user/slug")
      2. registry/nodes/**/<id>.json             (for generic IDs)
    """
    namedDir = repoRoot / "registry" / "named"
    nodesDir = repoRoot / "registry" / "nodes"

    # 1. Named skill: "contributor/slug" or plain "slug" under any contributor.
    if "/" in skillId:
        contributor, slug = skillId.split("/", 1)
        candidate = namedDir / contributor / f"{slug}.md"
        if candidate.exists():
            return parseFrontmatter(candidate)
    else:
        # Search all named subdirs
        for mdFile in namedDir.rglob("*.md"):
            meta = parseFrontmatter(mdFile)
            if meta.get("id") == skillId or mdFile.stem == skillId:
                return meta

    # 2. Registry node JSON
    for jsonFile in nodesDir.rglob("*.json"):
        try:
            data = json.loads(jsonFile.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("id") == skillId or jsonFile.stem == skillId:
            return data

    return None


def buildRegistryState(repoRoot: Path) -> dict:
    """Build a minimal registryState dict with genericSkillMap and namedSkillMap."""
    nodesDir = repoRoot / "registry" / "nodes"
    namedDir = repoRoot / "registry" / "named"

    genericSkillMap: dict[str, dict] = {}
    for jsonFile in nodesDir.rglob("*.json"):
        try:
            data = json.loads(jsonFile.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        sid = data.get("id")
        if sid:
            genericSkillMap[sid] = data

    namedSkillMap: dict[str, dict] = {}
    for mdFile in namedDir.rglob("*.md"):
        try:
            meta = parseFrontmatter(mdFile)
        except Exception:
            continue
        sid = meta.get("id")
        if sid:
            namedSkillMap[sid] = meta

    # Count current 6★ apex skills for system-wide cap
    apexCount = sum(
        1 for m in namedSkillMap.values()
        if str(m.get("level", "")).startswith("6")
    )

    # Apex predicates need to traverse both generic nodes and named suite
    # components (suite ultimates often point at named component IDs). Keep the
    # named map separately for grade lookups, but provide a merged lookup map to
    # match inspectTrustMagnitude.py's predicate context.
    mergedSkillMap = {**genericSkillMap, **namedSkillMap}

    return {
        "genericSkillMap": mergedSkillMap,
        "namedSkillMap": namedSkillMap,
        "systemWideApexCount": apexCount,
    }


# ---------------------------------------------------------------------------
# PR diff scanning
# ---------------------------------------------------------------------------


def findPromotedApexSkillIds(prNumber: int, repoRoot: Path) -> list[str]:
    """Scan the PR diff (vs origin base) for lines adding 'level: 6★'.

    Returns a list of skill IDs inferred from the affected files.
    """
    import subprocess

    # Determine base ref
    baseRef = os.environ.get("GITHUB_BASE_REF", "main")
    try:
        result = subprocess.run(
            ["git", "fetch", "origin", baseRef, "--quiet"],
            capture_output=True,
            cwd=str(repoRoot),
        )
    except Exception:
        pass

    try:
        mergeBase = subprocess.run(
            ["git", "merge-base", f"origin/{baseRef}", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(repoRoot),
        ).stdout.strip()
    except Exception:
        mergeBase = f"origin/{baseRef}"

    try:
        diffOutput = subprocess.run(
            ["git", "diff", mergeBase, "HEAD",
             "--", "registry/named/**", "registry/nodes/**"],
            capture_output=True,
            text=True,
            cwd=str(repoRoot),
        ).stdout
    except Exception:
        return []

    skillIds: list[str] = []
    currentFile: Optional[str] = None
    for line in diffOutput.splitlines():
        if line.startswith("+++ b/"):
            currentFile = line[6:]
        elif line.startswith("+") and "level:" in line and "6★" in line:
            if currentFile:
                # Extract skill ID from file path
                p = Path(currentFile)
                if p.suffix == ".md":
                    # named skill: registry/named/<contributor>/<slug>.md
                    parts = p.parts
                    if len(parts) >= 4:
                        skillIds.append(f"{parts[-2]}/{p.stem}")
                elif p.suffix == ".json":
                    skillIds.append(p.stem)

    return skillIds


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

# Predicate display labels and detail-generators
_PREDICATE_LABELS = {
    "aGradedOriginsGte5": "aGradedOriginsGte5",
    "sourceTenureDaysGte180AorS": "sourceTenureDaysGte180AorS",
    "directNestedSuiteGte1": "directNestedSuiteGte1",
    "depth2OnlyReachableGte1": "depth2OnlyReachableGte1",
    "overallGradeS": "overallGradeS",
    "apexPromotionPrSigned": "apexPromotionPrSigned",
    "crossOrgVerifier": "crossOrgVerifier",
    "systemWideCap": "systemWideCap",
}

_OFF_UNTIL = {
    "crossOrgVerifier": "OFF until 2026-Q4",
    "systemWideCap": "OFF until 2026-Q4",
}


def formatPredicateDetail(predicate: str, passed: Optional[bool], skill: dict, registryState: dict) -> str:
    """Return an operator-facing detail string for a predicate result.

    The apex predicates intentionally stay boolean in trustMagnitude.py. This
    helper is the reporting layer: it explains *why* a false predicate failed
    without mutating ranks, evidence, or gate semantics.
    """
    if predicate == "aGradedOriginsGte5":
        genericMap = registryState.get("genericSkillMap")
        namedMap = registryState.get("namedSkillMap")
        count = _countAGradedOrigins(skill, genericMap, namedMap)
        deficit = max(0, APEX_AGRADED_ORIGINS_MIN - count)
        if passed:
            return f"({count}/{APEX_AGRADED_ORIGINS_MIN} A/S origins; sufficient)"
        return f"(insufficient A/S origins: {count}/{APEX_AGRADED_ORIGINS_MIN}, needs +{deficit})"
    if predicate == "overallGradeS":
        tm = computeTrustMagnitude(skill, registryState.get("genericSkillMap"))
        if passed:
            return f"(TM = {tm:.2f}, S-floor = {GRADE_S_FLOOR:.0f}; sufficient)"
        return f"(TM = {tm:.2f}, S-floor = {GRADE_S_FLOOR:.0f}; below S)"
    if predicate == "sourceTenureDaysGte180AorS":
        return _formatSourceTenureDetail(skill, passed)
    if predicate == "directNestedSuiteGte1":
        count = _countDirectNestedSuites(skill, registryState.get("genericSkillMap") or {})
        if passed:
            return f"({count} direct nested suite component(s))"
        return "(no direct suite component has its own suiteComponents)"
    if predicate == "depth2OnlyReachableGte1":
        return _formatDepth2Detail(skill, registryState, passed)
    if predicate == "apexPromotionPrSigned":
        status = skill.get("apexGateStatus") or {}
        apexPr = skill.get("apexPromotionPr") or {}
        if status.get("apexPromotionPrSigned") is True:
            return "(PR-signed gate passed: apexGateStatus.apexPromotionPrSigned = true)"
        if apexPr.get("signed"):
            return "(PR-signed gate passed: apexPromotionPr.signed = true)"
        return "(PR-signed gate failure: no signed apex-promotion PR annotation)"
    if predicate in _OFF_UNTIL:
        return f"({_OFF_UNTIL[predicate]})"
    return ""


def _parseIsoDate(value: object) -> Optional[datetime.datetime]:
    """Parse a sourceStartedAt value into UTC, returning None when absent/invalid."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.datetime.fromisoformat(raw)
    except ValueError:
        try:
            parsed = datetime.datetime.strptime(raw[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.astimezone(datetime.timezone.utc)


def _evidenceGrade(row: dict) -> Optional[str]:
    grade = row.get("grade") or row.get("class")
    return grade if grade in {"S", "A", "B", "C"} else None


def _formatSourceTenureDetail(skill: dict, passed: Optional[bool]) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    aOrSRows = [
        row for row in skill.get("evidence") or []
        if isinstance(row, dict) and _evidenceGrade(row) in {"A", "S"}
    ]
    if not aOrSRows:
        return "(missing A/S provenance: no A/S evidence rows to age)"

    datedRows: list[tuple[int, str]] = []
    missingRows = 0
    invalidRows = 0
    for row in aOrSRows:
        rawStartedAt = row.get("sourceStartedAt")
        parsed = _parseIsoDate(rawStartedAt)
        if parsed is None:
            if rawStartedAt:
                invalidRows += 1
            else:
                missingRows += 1
            continue
        source = row.get("source") or row.get("url") or row.get("sourceUrl") or "unknown source"
        datedRows.append(((now - parsed).days, str(source)))

    if not datedRows:
        missingBits = []
        if missingRows:
            missingBits.append(f"missing sourceStartedAt on {missingRows}/{len(aOrSRows)} A/S row(s)")
        if invalidRows:
            missingBits.append(f"invalid sourceStartedAt on {invalidRows}/{len(aOrSRows)} A/S row(s)")
        return "(" + "; ".join(missingBits) + "; max age = 0d)"

    maxAge, source = max(datedRows, key=lambda item: item[0])
    suffix = []
    if missingRows:
        suffix.append(f"{missingRows} missing sourceStartedAt")
    if invalidRows:
        suffix.append(f"{invalidRows} invalid sourceStartedAt")
    suffixText = "; " + "; ".join(suffix) if suffix else ""
    if passed:
        return f"(oldest A/S source age {maxAge}d >= {APEX_TENURE_DAYS_MIN}d: {source}{suffixText})"
    return f"(insufficient tenure: oldest A/S source age {maxAge}d < {APEX_TENURE_DAYS_MIN}d: {source}{suffixText})"


def _countDirectNestedSuites(skill: dict, genericSkillMap: dict) -> int:
    count = 0
    for cid in skill.get("suiteComponents") or []:
        node = genericSkillMap.get(cid) or {}
        if node.get("suiteComponents"):
            count += 1
    return count


def _formatDepth2Detail(skill: dict, registryState: dict, passed: Optional[bool]) -> str:
    from gaia_cli.trustMagnitude import _fusionAndSuiteOriginIds

    genericMap = registryState.get("genericSkillMap") or {}
    namedMap = registryState.get("namedSkillMap") or {}
    skillId = skill.get("id") or skill.get("skillId")
    depth1 = set(_fusionAndSuiteOriginIds(skill, genericMap, namedMap))
    depth2: set[str] = set()
    for d1id in depth1:
        node = namedMap.get(d1id) or genericMap.get(d1id) or {}
        for d2id in _fusionAndSuiteOriginIds(node, genericMap, namedMap):
            if d2id != skillId:
                depth2.add(d2id)
    if passed:
        return f"(depth2 passed: {len(depth2)} depth-2 node(s) via {len(depth1)} depth-1 origin(s))"
    if not depth1:
        return "(depth2 failure: no fusion origins or suiteComponents at depth 1)"
    return f"(depth2 failure: {len(depth1)} depth-1 origin(s), 0 depth-2 node(s))"


def _countAGradedOrigins(skill: dict, genericSkillMap: Optional[dict], namedSkillMap: Optional[dict]) -> int:
    """Count A/S-graded origins for the aGradedOriginsGte5 predicate (for display)."""
    from gaia_cli.trustMagnitude import _typeOf

    allOrigins: set[str] = set()

    for row in skill.get("evidence") or []:
        if _typeOf(row) != "fusion-recipe":
            continue
        for entry in row.get("origins") or []:
            if isinstance(entry, dict):
                originId = entry.get("id") or entry.get("skillId")
                inlineRole = entry.get("role")
            else:
                originId = entry
                inlineRole = None
            if not originId:
                continue
            role = inlineRole
            if role is None and genericSkillMap:
                role = (genericSkillMap.get(originId) or {}).get("role")
            if role == "variant":
                continue
            allOrigins.add(originId)

    for cid in skill.get("suiteComponents") or []:
        allOrigins.add(cid)

    count = 0
    for originId in allOrigins:
        grade = None
        if namedSkillMap:
            node = namedSkillMap.get(originId)
            if node:
                grade = node.get("overallTrustGrade") or node.get("overallGrade") or node.get("grade")
        if grade is None and genericSkillMap:
            node = genericSkillMap.get(originId)
            if node:
                grade = node.get("overallTrustGrade") or node.get("overallGrade") or node.get("grade")
        if grade in ("S", "A"):
            count += 1
    return count


def printReport(skillId: str, skill: dict, predicates: dict, registryState: dict) -> None:
    """Print the human-readable apex gate audit report."""
    print(f"\nApex gate audit: {skillId}")
    activePassed = 0
    activeTotal = 0
    for name, result in predicates.items():
        detail = formatPredicateDetail(name, result, skill, registryState)
        if result is None:
            marker = "—"
        elif result:
            marker = "✓"
            activePassed += 1
            activeTotal += 1
        else:
            marker = "✗"
            activeTotal += 1

        label = _PREDICATE_LABELS.get(name, name)
        line = f"  {marker} {label}"
        if detail:
            line += f"  {detail}"
        print(line)

    overallPassed = isApex(predicates)
    resultStr = "PASS" if overallPassed else "FAIL"
    print(f"\n  RESULT: {resultStr} ({activePassed}/{activeTotal} active predicates passed)")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apex gate audit — per-predicate 6★ eligibility check."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("skill_id", nargs="?", help="Skill ID to audit (e.g. 'user/slug' or 'generic-id')")
    group.add_argument("--pr", type=int, metavar="PR_NUMBER",
                       help="Scan PR diff for 6★ promotions and audit each.")
    args = parser.parse_args()

    repoRoot = _REPO_ROOT
    registryState = buildRegistryState(repoRoot)

    if args.pr is not None:
        skillIds = findPromotedApexSkillIds(args.pr, repoRoot)
        if not skillIds:
            print(f"No 6★ promotions found in PR #{args.pr}.")
            return 0
        anyFail = False
        for sid in skillIds:
            skill = loadSkillById(sid, repoRoot)
            if skill is None:
                print(f"\nWARNING: Could not load skill '{sid}' — skipping.")
                anyFail = True
                continue
            predicates = passesApexGate(skill, registryState)
            printReport(sid, skill, predicates, registryState)
            if not isApex(predicates):
                anyFail = True
        return 1 if anyFail else 0

    # Single skill mode
    skillId = args.skill_id
    skill = loadSkillById(skillId, repoRoot)
    if skill is None:
        print(f"ERROR: Could not find skill '{skillId}' in registry/named/ or registry/nodes/.", file=sys.stderr)
        return 1

    predicates = passesApexGate(skill, registryState)
    printReport(skillId, skill, predicates, registryState)
    return 0 if isApex(predicates) else 1


if __name__ == "__main__":
    sys.exit(main())

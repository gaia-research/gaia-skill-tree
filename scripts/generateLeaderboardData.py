#!/usr/bin/env python3
"""Generate Trust Ledger JSON for the public /trust/ledger/ page.

Writes ``docs/graph/ledger/data.json`` containing:

    {
      "version":   "<gaia.json version>",
      "generatedAt": "<ISO 8601 UTC>",
      "rows": [ { skillId, tm, grade, currentStars, mayStars, juneStars, g7Stars, flag, apexResults }, ... ],
      "summary": { total, S, A, B, C, ungraded, floor, up }
    }

Run:
    python scripts/generateLeaderboardData.py
    python scripts/generateLeaderboardData.py --out path/to/data.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

# Reuse existing logic from inspectTrustMagnitude.
# Note: inspectTrustMagnitude rewraps sys.stdout for UTF-8 on Windows; we inherit that.
from scripts.inspectTrustMagnitude import (  # noqa: E402
    NAMED_DIR,
    NODES_DIR,
    buildMaps,
    effectiveRank,
    loadAllNamedSkills,
)
from gaia_cli.trustMagnitude import (  # noqa: E402
    computeOverallTrustGradeFromSkill,
    computeTrustMagnitude,
    passesApexGate,
)

DEFAULT_OUT = REPO_ROOT / "docs" / "graph" / "ledger" / "data.json"
GAIA_JSON = REPO_ROOT / "registry" / "gaia.json"
SKILL_TREES_DIR = REPO_ROOT / "skill-trees"

# G7 cutover — anything before this date is "May meta" (pre-G7), at/after is "June meta".
G7_CUTOVER = "2026-06-18T12:54:50Z"


def readGaiaVersion() -> str:
    try:
        gj = json.loads(GAIA_JSON.read_text(encoding="utf-8"))
        return gj.get("version") or ""
    except Exception:
        return ""


def buildMayStarsMap() -> dict[str, str]:
    """Walk every skill-tree.json and return {skillId: mayStars}.

    mayStars is the level that was current on the G7 cutover date — i.e. the
    latest levelHistory entry with achievedAt < cutover, or the unlockedAt level
    if no earlier history exists. Skills with no user-tree entry are absent from
    the map; callers should fall back to current registry stars in that case.
    """
    out: dict[str, str] = {}
    if not SKILL_TREES_DIR.exists():
        return out
    for tree in SKILL_TREES_DIR.glob("*/skill-tree.json"):
        try:
            data = json.loads(tree.read_text(encoding="utf-8"))
        except Exception:
            continue
        for s in data.get("unlockedSkills", []) or []:
            sid = s.get("skillId")
            if not sid:
                continue
            history = s.get("levelHistory") or []
            # Find the latest event before the G7 cutover
            beforeCutover = [h for h in history
                             if isinstance(h, dict)
                             and h.get("achievedAt", "") < G7_CUTOVER]
            if beforeCutover:
                # Use the latest entry — the "level" field of a history entry
                # is the level *attained* by that event, so it's still current
                # at the cutover instant.
                latest = max(beforeCutover, key=lambda h: h.get("achievedAt", ""))
                out[sid] = latest.get("level") or s.get("level") or ""
            elif s.get("unlockedAt", "") < G7_CUTOVER:
                # Registered before cutover with no history — current level
                # was set at register time and held through the cutover.
                out[sid] = s.get("level") or ""
            # else: registered after cutover → no May value
    return out


def buildRows() -> list[dict]:
    mergedMap, namedSkillMap = buildMaps()
    skills = loadAllNamedSkills()
    apexState = {"genericSkillMap": mergedMap, "namedSkillMap": namedSkillMap}
    mayStarsMap = buildMayStarsMap()

    rows: list[dict] = []
    for fm in skills:
        skillId = fm.get("id") or "unknown"
        tm = computeTrustMagnitude(fm, mergedMap)
        grade = computeOverallTrustGradeFromSkill(fm, mergedMap)
        currentStars = fm.get("level") or fm.get("rank") or "?"
        g7Stars, flag = effectiveRank(grade, currentStars)
        # May meta = stars on the eve of G7 cutover (pre-ratification).
        # June meta = current stars after G7 ratification (which is what
        # `currentStars` already is).
        mayStars = mayStarsMap.get(skillId, currentStars)

        apexResults = None
        if grade == "S":
            apexResults = passesApexGate(fm, apexState)

        rows.append({
            "skillId":      skillId,
            "tm":           round(tm, 2),
            "grade":        grade,
            "currentStars": currentStars,   # kept for backward compat
            "mayStars":     mayStars,
            "juneStars":    currentStars,
            "g7Stars":      g7Stars,        # kept for backward compat
            "flag":         flag,
            "apexResults":  apexResults,
        })

    rows.sort(key=lambda r: -r["tm"])
    return rows


def buildSummary(rows: list[dict]) -> dict:
    total = len(rows)
    counts = {g: 0 for g in ("S", "A", "B", "C", "ungraded")}
    for r in rows:
        g = r["grade"]
        if g in counts:
            counts[g] += 1
    floors = sum(1 for r in rows if r["flag"] == "[floor]")
    ups = sum(1 for r in rows if r["flag"] == "[up]")
    return {
        "total":    total,
        "S":        counts["S"],
        "A":        counts["A"],
        "B":        counts["B"],
        "C":        counts["C"],
        "ungraded": counts["ungraded"],
        "floor":    floors,
        "up":       ups,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate /trust/ledger/ data.json")
    parser.add_argument("--out", metavar="PATH", default=str(DEFAULT_OUT),
                        help=f"Output path (default: {DEFAULT_OUT.relative_to(REPO_ROOT)})")
    args = parser.parse_args()

    print(f"Loading skill maps from {NODES_DIR.relative_to(REPO_ROOT)} + {NAMED_DIR.relative_to(REPO_ROOT)}...")
    rows = buildRows()
    summary = buildSummary(rows)

    payload = {
        "version":     readGaiaVersion(),
        "generatedAt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary":     summary,
        "rows":        rows,
    }

    outPath = Path(args.out)
    outPath.parent.mkdir(parents=True, exist_ok=True)
    outPath.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote {outPath.relative_to(REPO_ROOT) if outPath.is_relative_to(REPO_ROOT) else outPath}")
    print(f"  total={summary['total']} | S={summary['S']} A={summary['A']} B={summary['B']} C={summary['C']} ungraded={summary['ungraded']}")
    print(f"  rank-floor={summary['floor']} | implied-promotions={summary['up']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

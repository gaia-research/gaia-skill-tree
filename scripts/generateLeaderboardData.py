#!/usr/bin/env python3
"""Generate Trust Magnitude leaderboard JSON for the public /trust/leaderboard/ page.

Writes ``docs/graph/leaderboard/data.json`` containing:

    {
      "version":   "<gaia.json version>",
      "generatedAt": "<ISO 8601 UTC>",
      "rows": [ { skillId, tm, grade, currentStars, g7Stars, flag, apexResults }, ... ],
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

DEFAULT_OUT = REPO_ROOT / "docs" / "graph" / "leaderboard" / "data.json"
GAIA_JSON = REPO_ROOT / "registry" / "gaia.json"


def readGaiaVersion() -> str:
    try:
        gj = json.loads(GAIA_JSON.read_text(encoding="utf-8"))
        return gj.get("version") or ""
    except Exception:
        return ""


def buildRows() -> list[dict]:
    mergedMap, namedSkillMap = buildMaps()
    skills = loadAllNamedSkills()
    apexState = {"genericSkillMap": mergedMap, "namedSkillMap": namedSkillMap}

    rows: list[dict] = []
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
            "skillId":      skillId,
            "tm":           round(tm, 2),
            "grade":        grade,
            "currentStars": currentStars,
            "g7Stars":      g7Stars,
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
    parser = argparse.ArgumentParser(description="Generate /trust/leaderboard/ data.json")
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

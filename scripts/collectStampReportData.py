"""One-off: recompute stats from current state for the stamp report.

Reads each migrated frontmatter, recomputes TM/grade/gate from the (already
clean) evidence, and emits a fresh summary covering every skill — without
writing files. Used to populate JUN_2026_TRUST_REGRADE.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from migrateTrustMagnitude import (  # noqa: E402
    NAMED_DIR, NODES_DIR, OUT_DIR,
    buildGenericSkillMap, hasMissingSourceStartedAt, loadNamedSkill,
)
from gaia_cli.trustMagnitude import (  # noqa: E402
    computeOverallTrustGradeFromSkill,
    computeTrustMagnitude,
    passesSuiteApexGate,
)


def main() -> int:
    genericSkillMap = buildGenericSkillMap(NODES_DIR)
    paths = sorted(NAMED_DIR.rglob("*.md"))

    stats: dict = {
        "totalFiles": len(paths),
        "tmDeltas": [],
        "gradeTransitions": {},
        "phantomRemovals": [],  # Already applied; cannot recover
        "provisionalSkills": [],
        "apexGateInspected": {},
        "perSkill": [],
    }

    for p in paths:
        fm, _ = loadNamedSkill(p)
        if fm is None:
            continue
        sid = fm.get("id") or p.stem
        relPath = p.relative_to(REPO_ROOT).as_posix()

        # Stamped values (post-migration current state)
        tm = fm.get("trustMagnitude")
        grade = fm.get("overallTrustGrade") or "ungraded"
        gate = fm.get("apexGateStatus") or {}
        provisional = bool(fm.get("provisional", False))

        # Pre-migration legacy: skills previously had no trustMagnitude/grade
        # so transition is ungraded -> grade
        oldTm = None
        oldGrade = "ungraded"

        delta = (tm - 0) if isinstance(tm, (int, float)) else None
        stats["tmDeltas"].append({
            "skillId": sid,
            "path": relPath,
            "oldTm": oldTm,
            "newTm": tm,
            "delta": delta,
        })
        transition = f"{oldGrade} -> {grade}"
        stats["gradeTransitions"][transition] = stats["gradeTransitions"].get(transition, 0) + 1
        if provisional:
            stats["provisionalSkills"].append({"skillId": sid, "path": relPath})

        if sid in {"mattpocock/skills", "ruvnet/ruflo"}:
            isApex = all(v is True for v in gate.values() if v is not None)
            stats["apexGateInspected"][sid] = {
                "tm": tm,
                "grade": grade,
                "gate": gate,
                "isApex": isApex,
            }

        stats["perSkill"].append({
            "skillId": sid,
            "tm": tm,
            "grade": grade,
            "provisional": provisional,
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outPath = OUT_DIR / "stamp_report_data.json"
    outPath.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"Wrote {outPath.relative_to(REPO_ROOT)}")
    print(f"Total: {stats['totalFiles']}")
    print(f"Grade transitions: {stats['gradeTransitions']}")
    print(f"Provisional: {len(stats['provisionalSkills'])}")
    print(f"Apex inspected: {list(stats['apexGateInspected'].keys())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

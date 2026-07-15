#!/usr/bin/env python3
"""Surgical recompute-and-persist of Trust Magnitude for a single named skill.

This is the "CLI gap" remediation companion to the trust-methodology-consult
skill. The live CLI does NOT recompute+persist a named skill's
`trustMagnitude`/`overallTrustGrade` when evidence is added, a suite is fused,
or a level is calibrated (see the skill's SKILL.md). That leaves the stored
frontmatter field stale while the leaderboard — which recomputes at build time
via `computeTrustMagnitude` — shows the correct value. Consumers that trust the
stored field (contributors API, badges, Hall-of-Heroes topSkill selection) then
disagree with the leaderboard.

This script reuses the canonical write-back logic from the archived big-bang
migration (scripts/archive/migrateTrustMagnitude.py) but applies it to exactly
ONE node, so unrelated stale skills are never swept into the diff. It is
idempotent: if the input hash already matches, it skips.

Usage (from anywhere in the repo tree):
  python3 <this>/recompute_one_tm.py <owner/skill-id> [--dry-run]
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    """Walk upward until we find the repo markers, independent of where this
    helper is vendored (skill dir, scripts/, worktree, ...)."""
    for candidate in [start, *start.parents]:
        if (candidate / "registry" / "named").is_dir() and (
            candidate / "scripts" / "archive" / "migrateTrustMagnitude.py"
        ).is_file():
            return candidate
    raise SystemExit(
        "ERROR: could not locate the gaia-skill-tree repo root "
        "(need registry/named + scripts/archive/migrateTrustMagnitude.py)."
    )


REPO_ROOT = find_repo_root(Path(__file__).resolve())
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

# Load the canonical write-back logic from the archived migration module.
_mig_path = REPO_ROOT / "scripts" / "archive" / "migrateTrustMagnitude.py"
_spec = importlib.util.spec_from_file_location("_migrate_tm", _mig_path)
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)

# The archived module derives its own REPO_ROOT from its file location; repoint
# its globals at the real tree so relative-path printing and map building work.
mig.REPO_ROOT = REPO_ROOT
mig.NAMED_DIR = REPO_ROOT / "registry" / "named"
mig.NODES_DIR = REPO_ROOT / "registry" / "nodes"


def find_skill_path(skill_id: str) -> Path | None:
    for p in sorted(mig.NAMED_DIR.rglob("*.md")):
        fm, _ = mig.loadNamedSkill(p)
        if fm and fm.get("id") == skill_id:
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("skill_id", help="Named skill id, e.g. firecrawl/firecrawl-skills")
    ap.add_argument("--dry-run", dest="dry_run", action="store_true",
                    help="Compute the new TM/grade but do not write the file")
    args = ap.parse_args()

    path = find_skill_path(args.skill_id)
    if not path:
        print(f"ERROR: skill not found: {args.skill_id}", file=sys.stderr)
        return 2

    print(f"Building maps from {mig.NODES_DIR} + {mig.NAMED_DIR} ...")
    generic = mig.buildGenericSkillMap(mig.NODES_DIR)
    named = mig.buildNamedSkillMap(mig.NAMED_DIR)
    merged = {**generic, **named}

    stats: dict = {
        "processed": 0,
        "skipped": 0,
        "tmDeltas": [],
        "gradeTransitions": {},
        "phantomRemovals": [],
        "provisionalSkills": [],
        "apexGateInspected": {},
    }

    print(f"Recomputing {args.skill_id} "
          f"({path.relative_to(REPO_ROOT).as_posix()}) dry_run={args.dry_run}")
    mig.migrateSkill(path, merged, stats, args.dry_run)
    if stats["tmDeltas"]:
        print("Delta:", stats["tmDeltas"])
    if not args.dry_run and stats["tmDeltas"]:
        print("\nNext: run `gaia dev docs` (or `python scripts/build_docs.py`) "
              "to propagate the new value into docs/ artifacts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Verify that the shared Steward refs are protected against rewrite and deletion.

`steward/evidence` is append-only custody. Content hashes prove the stored bytes
were not altered; they cannot stop a repository writer from force-pushing history
away or deleting the ref. That protection is repository configuration, not code,
so this checker reads the repository's rulesets and answers one question: does an
ACTIVE branch ruleset with no bypass actors block deletion and non-fast-forward
updates for every protected ref?

Exit 0 only when every required ref is covered. Anything unreadable is a failure:
"could not inspect" is never "protected".

    gh api repos/gaia-research/gaia-skill-tree/rulesets            # list
    python scripts/check_steward_evidence_protection.py --live     # inspects each
    python scripts/check_steward_evidence_protection.py --rulesets-file rulesets.json
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

REPOSITORY = "gaia-research/gaia-skill-tree"
REQUIRED_REFS = (
    "refs/heads/steward/evidence",
    "refs/heads/steward/evidence-rehearsal-2448",
    "refs/heads/steward/ledger",
)
REQUIRED_RULES = ("deletion", "non_fast_forward")


def matches(patterns: Sequence[str], ref: str) -> bool:
    return any(fnmatch.fnmatchcase(ref, pattern) for pattern in patterns)


def rulesetCovers(ruleset: dict[str, Any], ref: str) -> tuple[bool, list[str]]:
    """Whether one ruleset protects `ref`; the list says what is missing."""

    problems: list[str] = []
    if ruleset.get("target") != "branch":
        problems.append("not a branch ruleset")
    if ruleset.get("enforcement") != "active":
        problems.append(f"enforcement is {ruleset.get('enforcement')!r}, not 'active'")
    conditions = (ruleset.get("conditions") or {}).get("ref_name") or {}
    if not matches(conditions.get("include") or [], ref) or matches(conditions.get("exclude") or [], ref):
        problems.append("the ref is not included by the ruleset's ref_name conditions")
    present = {rule.get("type") for rule in ruleset.get("rules") or []}
    for needed in REQUIRED_RULES:
        if needed not in present:
            problems.append(f"missing rule {needed!r}")
    if ruleset.get("bypass_actors"):
        problems.append(
            f"{len(ruleset['bypass_actors'])} bypass actor(s) can override it; an append-only guarantee needs none"
        )
    return not problems, problems


def evaluate(rulesets: list[dict[str, Any]], refs: Sequence[str] = REQUIRED_REFS) -> dict[str, Any]:
    report: dict[str, Any] = {"protected": True, "refs": {}}
    for ref in refs:
        best: list[str] | None = None
        covered = False
        for ruleset in rulesets:
            ok, problems = rulesetCovers(ruleset, ref)
            if ok:
                covered = True
                break
            if best is None or len(problems) < len(best):
                best = problems
        report["refs"][ref] = {
            "covered": covered,
            "problems": [] if covered else (best if best is not None else ["no ruleset exists"]),
        }
        report["protected"] = report["protected"] and covered
    return report


def gh(*args: str) -> Any:
    result = subprocess.run(["gh", "api", *args], capture_output=True, text=True, timeout=60, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"gh api {' '.join(args)} failed: {(result.stderr or result.stdout).strip()[:300]}")
    return json.loads(result.stdout)


def loadLive(repository: str) -> list[dict[str, Any]]:
    listing = gh(f"repos/{repository}/rulesets")
    return [gh(f"repos/{repository}/rulesets/{item['id']}") for item in listing]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--live", action="store_true", help="Read rulesets with `gh api` (needs admin read access)")
    source.add_argument("--rulesets-file", type=Path, help="JSON list of full ruleset objects")
    parser.add_argument("--repository", default=REPOSITORY)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        rulesets = loadLive(args.repository) if args.live else json.loads(args.rulesets_file.read_text())
        if not isinstance(rulesets, list) or any(not isinstance(item, dict) for item in rulesets):
            raise ValueError("rulesets must be a JSON list of objects")
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"UNVERIFIED: could not inspect rulesets: {exc}", file=sys.stderr)
        return 2
    report = evaluate(rulesets)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for ref, item in report["refs"].items():
            print(f"{'PROTECTED  ' if item['covered'] else 'UNPROTECTED'} {ref}")
            for problem in item["problems"]:
                print(f"    - {problem}")
        print("RESULT: protected" if report["protected"] else "RESULT: NOT protected; the daily scheduler must stay disabled")
    return 0 if report["protected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

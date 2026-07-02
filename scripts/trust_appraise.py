#!/usr/bin/env python3
"""Dry-run Trust Magnitude appraisal for proposed named suites.

This script is intentionally non-mutating. It appraises a proposed suite before
curation by combining live GitHub repository signals with a proposed component
count, then runs the same Trust Magnitude scorer used by the registry.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gaia_cli.trustMagnitude import (  # noqa: E402
    computeOverallTrustGrade,
    computeTrustMagnitude,
    computeTrustMagnitudeByType,
)


@dataclass(frozen=True)
class AppraisalTarget:
    repo: str
    componentCount: int
    evidencePath: str
    sourceStartedAt: str | None = None


def runJson(command: list[str]) -> Any:
    return json.loads(subprocess.check_output(command, text=True))


def repoMeta(repo: str) -> dict[str, Any]:
    return runJson([
        "gh",
        "repo",
        "view",
        repo,
        "--json",
        "nameWithOwner,description,stargazerCount,isArchived,url,updatedAt,defaultBranchRef",
    ])


def contributorStats(repo: str) -> tuple[int, int]:
    try:
        contributors = runJson(["gh", "api", f"repos/{repo}/contributors", "--paginate"])
    except subprocess.CalledProcessError:
        return 0, 0
    return len(contributors), sum(int(row.get("contributions", 0) or 0) for row in contributors)


def appraise(target: AppraisalTarget) -> dict[str, Any]:
    meta = repoMeta(target.repo)
    contributorCount, commitCount = contributorStats(target.repo)
    stars = int(meta.get("stargazerCount", 0) or 0)
    evidenceUrl = f"https://github.com/{target.repo}/blob/{meta['defaultBranchRef']['name']}/{target.evidencePath}"
    repoUrl = f"https://github.com/{target.repo}"
    evidence: list[dict[str, Any]] = [
        {
            "type": "github-stars-own",
            "source": evidenceUrl,
            "stars": stars,
            "skillCountInRepo": target.componentCount,
        },
        {
            "type": "repo-own",
            "source": repoUrl,
            "commits": commitCount,
            "contributors": contributorCount,
        },
        {
            "type": "fusion-recipe",
            "source": f"{repoUrl}#suite-components",
            "gradedOriginCount": target.componentCount,
        },
    ]
    if target.sourceStartedAt:
        for row in evidence:
            row["sourceStartedAt"] = target.sourceStartedAt
    skill = {"id": target.repo.replace("/", "-"), "evidence": evidence}
    tm = computeTrustMagnitude(skill)
    return {
        "repo": target.repo,
        "archived": bool(meta.get("isArchived")),
        "stars": stars,
        "components": target.componentCount,
        "contributors": contributorCount,
        "commits": commitCount,
        "evidenceUrl": evidenceUrl,
        "tm": round(tm, 2),
        "grade": computeOverallTrustGrade(tm, distinctTypes=3, hasNonSelfProducible=True),
        "byType": computeTrustMagnitudeByType(skill),
    }


def defaultTargets() -> list[AppraisalTarget]:
    return [
        AppraisalTarget("gsd-build/get-shit-done", 5, "docs/INVENTORY.md"),
        AppraisalTarget("addyosmani/agent-skills", 7, "README.md"),
        AppraisalTarget("open-gsd/gsd-core", 5, "README.md"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run TM for proposed Gaia suites")
    parser.add_argument("--repo", action="append", help="GitHub repo owner/name")
    parser.add_argument("--components", action="append", type=int, help="Component count for matching --repo")
    parser.add_argument("--evidence-path", action="append", default=[], help="Evidence path for matching --repo")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    if args.repo:
        componentCounts = args.components or []
        if len(componentCounts) != len(args.repo):
            parser.error("pass one --components value for each --repo")
        evidencePaths = list(args.evidence_path)
        while len(evidencePaths) < len(args.repo):
            evidencePaths.append("README.md")
        targets = [AppraisalTarget(repo, count, path) for repo, count, path in zip(args.repo, componentCounts, evidencePaths)]
    else:
        targets = defaultTargets()

    rows = [appraise(target) for target in targets]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    print("| Repo | Archived | Stars | Components | Repo signals | TM by type | Total | Grade |")
    print("|---|---:|---:|---:|---|---|---:|---|")
    for row in rows:
        repoSignals = f"{row['commits']} commits / {row['contributors']} contributors"
        byType = ", ".join(f"{key}={value}" for key, value in row["byType"].items())
        print(f"| `{row['repo']}` | {row['archived']} | {row['stars']:,} | {row['components']} | {repoSignals} | {byType} | {row['tm']:.2f} | {row['grade']} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

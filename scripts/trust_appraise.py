#!/usr/bin/env python3
"""Dry-run Trust Magnitude appraisal for proposed Gaia skills or suites.

Two modes:
  --skill  contributor/skill-id   Appraise an already-curated registry node
  --repo   owner/repo             Appraise a proposed suite from live GitHub signals

This script is intentionally non-mutating.

Every result states its appraisal scope (``named-own/proposal``, ``generic``,
``effective named``), its generic-resolution status, and the provenance and
claim status of the metrics it collected. See
``docs/agents/curation-authority-map.md`` §2 and §5. A ``--repo`` proposal sums
only its own rows: it is a partial total, never the effective named TM.
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gaia_cli.fusionScore import fusionScoreProjection  # noqa: E402
from gaia_cli.registryMaps import buildMergedSkillMap  # noqa: E402
from gaia_cli.trustMagnitude import (  # noqa: E402
    computeOverallTrustGrade,
    computeOverallTrustGradeFromSkill,
    computeRowArtifactScores,
    computeTrustMagnitude,
    computeTrustMagnitudeByType,
    _countDistinctEvidenceTypes,
    _hasEligibleIndependentWitness,
)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)

# Appraisal scope labels (docs/agents/curation-authority-map.md §2).
SCOPE_PROPOSAL = "named-own/proposal"
SCOPE_GENERIC = "generic"
SCOPE_EFFECTIVE_NAMED = "effective named"
SCOPE_NAMED_OWN = "named-own"
GENERIC_RESOLVED = "resolved"
GENERIC_NOT_EVALUATED = "not evaluated"
GENERIC_NOT_APPLICABLE = "not applicable"

CONTRIBUTION_SUM_METHOD = (
    "sum of per-contributor `contributions` from `gh api repos/{repo}/contributors "
    "--paginate` (GitHub default branch; anonymous contributors excluded). "
    "This is a contributor-contribution sum, not a count of unique reachable commits."
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
    """Return ``(contributor count, contributor-contribution sum)``.

    The second value sums GitHub's per-contributor ``contributions``. It is a
    different measurement from unique reachable commits on a ref, and must be
    reported as ``contributorContributionSum``, never as plain "commits".
    """
    try:
        contributors = runJson(["gh", "api", f"repos/{repo}/contributors", "--paginate"])
    except subprocess.CalledProcessError:
        return 0, 0
    return len(contributors), sum(int(row.get("contributions", 0) or 0) for row in contributors)


def utcNow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def registryRevision(repo_root: Path = REPO_ROOT) -> str:
    """Return the registry checkout's HEAD sha, or ``unknown`` when it cannot be read."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return out.strip() or "unknown"


def appraise(target: AppraisalTarget) -> dict[str, Any]:
    meta = repoMeta(target.repo)
    collectedAt = utcNow()
    contributorCount, contributionSum = contributorStats(target.repo)
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
            # The engine's repo-own input field is `commits`. This proposal
            # fills it from the contributor-contribution sum. The value is
            # unchanged; only the label in the result below differs, where it
            # is reported as an `inferred` input.
            "commits": contributionSum,
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
    defaultBranch = (meta.get("defaultBranchRef") or {}).get("name")
    ghRepro = f"gh repo view {target.repo} --json stargazerCount,defaultBranchRef,updatedAt"
    contribRepro = f"gh api repos/{target.repo}/contributors --paginate"
    return {
        "repo": target.repo,
        "archived": bool(meta.get("isArchived")),
        "stars": stars,
        "components": target.componentCount,
        "contributors": contributorCount,
        "contributorContributionSum": contributionSum,
        "evidenceUrl": evidenceUrl,
        "tm": round(tm, 2),
        "grade": computeOverallTrustGradeFromSkill(skill),
        "byType": computeTrustMagnitudeByType(skill),
        "scope": SCOPE_PROPOSAL,
        "genericResolution": GENERIC_NOT_EVALUATED,
        "totalStatus": "partial",
        "tmLabel": "own-only proposal total (partial; not the effective named TM)",
        "sourceRevision": {
            "repo": target.repo,
            "defaultBranch": defaultBranch,
            "repoUpdatedAt": meta.get("updatedAt"),
            "collectedAt": collectedAt,
        },
        "metricClaims": [
            {
                "metric": "stars",
                "value": stars,
                "status": "verified",
                "method": "GitHub stargazerCount",
                "repro": ghRepro,
                "collectedAt": collectedAt,
            },
            {
                "metric": "contributors",
                "value": contributorCount,
                "status": "verified",
                "method": "count of GitHub contributor rows (anonymous excluded)",
                "repro": contribRepro,
                "collectedAt": collectedAt,
            },
            {
                "metric": "contributorContributionSum",
                "value": contributionSum,
                "status": "verified",
                "method": CONTRIBUTION_SUM_METHOD,
                "repro": contribRepro,
                "collectedAt": collectedAt,
            },
            {
                "metric": "repo-own.commits (engine input)",
                "value": contributionSum,
                "status": "inferred",
                "method": "filled from contributorContributionSum; unique reachable commits were not measured",
                "collectedAt": collectedAt,
            },
        ],
    }


def namedScope(named: dict[str, Any], mergedMap: dict[str, Any]) -> tuple[str, str]:
    """Return ``(scope, genericResolution)`` for a named-skill appraisal."""
    ref = named.get("genericSkillRef")
    if not ref:
        return SCOPE_EFFECTIVE_NAMED, GENERIC_NOT_APPLICABLE
    if ref in mergedMap:
        return SCOPE_EFFECTIVE_NAMED, GENERIC_RESOLVED
    return SCOPE_NAMED_OWN, GENERIC_NOT_EVALUATED


def _load_registry_maps(repo_root: Path = REPO_ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load generic and named skill maps from the registry."""
    generic_map: dict[str, Any] = {}
    nodes_dir = repo_root / "registry" / "nodes"
    if nodes_dir.exists():
        for p in nodes_dir.rglob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("id"):
                    generic_map[data["id"]] = data
            except Exception:
                pass

    named_map: dict[str, Any] = {}
    named_dir = repo_root / "registry" / "named"
    if named_dir.exists():
        for p in named_dir.rglob("*.md"):
            try:
                text = p.read_text(encoding="utf-8")
                m = FRONTMATTER_RE.match(text)
                if m:
                    fm = yaml.safe_load(m.group(1)) or {}
                    if isinstance(fm, dict) and fm.get("id"):
                        named_map[fm["id"]] = fm
            except Exception:
                pass

    return generic_map, named_map


def appraise_skill(
    skill_id: str,
    generic_map: dict[str, Any] | None = None,
    named_map: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Appraise a curated registry node or named skill by ID.

    When skill_id contains a slash (indicating a named skill such as contributor/skill),
    resolves to registry/named/<contributor>/<skill>.md, parses frontmatter and evidence list
    with yaml.safe_load, loads generic and named skill maps, and computes the real Trust
    Magnitude using computeTrustMagnitude(named_dict, generic_map, named_map) and
    computeOverallTrustGrade.
    """
    if generic_map is None or named_map is None:
        loaded_generic, loaded_named = _load_registry_maps(REPO_ROOT)
        if generic_map is None:
            generic_map = loaded_generic
        if named_map is None:
            named_map = loaded_named

    merged_map = {**generic_map, **named_map}

    if "/" in skill_id:
        contributor, skillSlug = skill_id.split("/", 1)
        named_path = REPO_ROOT / "registry" / "named" / contributor / f"{skillSlug}.md"
        if named_path.exists():
            text = named_path.read_text(encoding="utf-8")
            m = FRONTMATTER_RE.match(text)
            fm_text = m.group(1) if m else text
            named_dict = yaml.safe_load(fm_text) or {}

            tm = computeTrustMagnitude(named_dict, merged_map, named_map)
            distinct_types = _countDistinctEvidenceTypes(named_dict, merged_map)
            has_witness = _hasEligibleIndependentWitness(named_dict, merged_map)
            grade = computeOverallTrustGrade(tm, distinct_types, has_witness)
            row_scores = computeRowArtifactScores(named_dict, merged_map)
            by_type = computeTrustMagnitudeByType(named_dict, merged_map)
            scope, genericResolution = namedScope(named_dict, merged_map)

            return {
                "skillRef": skill_id,
                "tm": round(tm, 2),
                "grade": grade,
                "scope": scope,
                "genericResolution": genericResolution,
                "totalStatus": "final" if genericResolution != GENERIC_NOT_EVALUATED else "partial",
                "registryRevision": registryRevision(),
                **fusionScoreProjection(named_dict, merged_map, merged_map),
                "byType": dict(by_type),
                "rows": [
                    {
                        "type": ev.get("type"),
                        "score": round(score, 2),
                        "trust": ev.get("trustNumber"),
                        "source": ev.get("source", "")[:80],
                    }
                    for ev, score in row_scores
                ],
            }
        # If named file does not exist, fall back to generic node search
        node_id = skillSlug
    else:
        node_id = skill_id

    # Resolve generic node
    node_path = None
    for p in [
        REPO_ROOT / "registry" / "nodes" / "basic" / f"{node_id}.json",
        REPO_ROOT / "registry" / "nodes" / "fusion" / f"{node_id}.json",
        REPO_ROOT / "registry" / "nodes" / "extra" / f"{node_id}.json",
    ]:
        if p.exists():
            node_path = p
            break

    if node_path is None or not node_path.exists():
        return {"skillRef": skill_id, "error": f"node not found for {skill_id!r}"}

    skill = json.loads(node_path.read_text(encoding="utf-8"))
    tm = computeTrustMagnitude(skill, merged_map, named_map)
    distinct_types = _countDistinctEvidenceTypes(skill, merged_map)
    has_witness = _hasEligibleIndependentWitness(skill, merged_map)
    grade = computeOverallTrustGrade(tm, distinct_types, has_witness)
    row_scores = computeRowArtifactScores(skill, merged_map)
    by_type = computeTrustMagnitudeByType(skill, merged_map)

    return {
        "skillRef": skill_id,
        "tm": round(tm, 2),
        "grade": grade,
        "scope": SCOPE_GENERIC,
        "genericResolution": GENERIC_NOT_APPLICABLE,
        "totalStatus": "final",
        "registryRevision": registryRevision(),
        **fusionScoreProjection(skill, merged_map, merged_map),
        "byType": dict(by_type),
        "rows": [
            {
                "type": ev.get("type"),
                "score": round(score, 2),
                "trust": ev.get("trustNumber"),
                "source": ev.get("source", "")[:80],
            }
            for ev, score in row_scores
        ],
    }


def appraiseNode(skillRef: str) -> dict[str, Any]:
    """Appraise an already-curated registry node by contributor/skill-id or bare id."""
    return appraise_skill(skillRef)


def defaultTargets() -> list[AppraisalTarget]:
    return [
        AppraisalTarget("gsd-build/get-shit-done", 5, "docs/INVENTORY.md"),
        AppraisalTarget("addyosmani/agent-skills", 7, "README.md"),
        AppraisalTarget("open-gsd/gsd-core", 5, "README.md"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run TM appraisal for Gaia skills or suites")
    parser.add_argument("--skill", action="append", metavar="CONTRIBUTOR/SKILL-ID",
                        help="Appraise a curated registry node (e.g. rico-favor/implement-with-discernment)")
    parser.add_argument("--repo", action="append", help="GitHub repo owner/name (suite mode)")
    parser.add_argument("--components", action="append", type=int, help="Component count for matching --repo")
    parser.add_argument("--evidence-path", action="append", default=[], help="Evidence path for matching --repo")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    if args.skill:
        results = [appraiseNode(ref) for ref in args.skill]
        if args.json:
            print(json.dumps(results, indent=2))
            return 0
        for r in results:
            if "error" in r:
                print(f"ERROR {r['skillRef']}: {r['error']}")
                continue
            print(f"\n=== {r['skillRef']} ===")
            print(
                f"  Scope: {r['scope']}  Generic: {r['genericResolution']}"
                f"  Total: {r['totalStatus']}  Registry rev: {r['registryRevision']}"
            )
            print(f"  TM: {r['tm']:.1f}  Grade: {r['grade']}")
            fb = r.get("fusionBreakdown") or {}
            print(
                f"  Fusion Score: {r.get('fusionScore', 0):.2f}"
                f"  ({r.get('fusionScoreVersion', '')};"
                f" direct {fb.get('directCount', 0)},"
                f" transitive {fb.get('transitiveCount', 0)},"
                f" depth {fb.get('maxDepth', 0)},"
                f" nested suites {fb.get('nestedSuiteCount', 0)})"
            )
            print("  Fusion Score is structural only — it gates no rank and feeds no TM.")
            print(f"  {'Type':<22} {'Score':>7}  {'Trust':>6}  Source")
            for row in r["rows"]:
                print(f"  {row['type']:<22} {row['score']:>7.1f}  {str(row['trust'] or ''):>6}  {row['source']}")
            byType = ", ".join(f"{k}={v}" for k, v in r["byType"].items())
            print(f"  By type: {byType}")
        return 0

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

    print(
        f"Scope: {SCOPE_PROPOSAL} (own rows only). Generic context: {GENERIC_NOT_EVALUATED}. "
        "Totals are partial and are not the effective named TM."
    )
    print("| Repo | Archived | Stars | Components | Repo signals | TM by type | Own-only TM (partial) | Grade (own-only) |")
    print("|---|---:|---:|---:|---|---|---:|---|")
    for row in rows:
        repoSignals = (
            f"{row['contributorContributionSum']} contributor contributions (inferred as repo-own commits input)"
            f" / {row['contributors']} contributors"
        )
        byType = ", ".join(f"{key}={value}" for key, value in row["byType"].items())
        print(f"| `{row['repo']}` | {row['archived']} | {row['stars']:,} | {row['components']} | {repoSignals} | {byType} | {row['tm']:.2f} | {row['grade']} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

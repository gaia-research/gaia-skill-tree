#!/usr/bin/env python3
"""Recreate mbtiongson1 named skills without catalogRef."""
import subprocess, sys, json, shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Wipe existing
shutil.rmtree(ROOT / "registry/named/mbtiongson1", ignore_errors=True)

SKILLS = [
    dict(
        name="Gaia Curate",
        generic_ref="registry-curation",
        level="4★",
        title="The Registrar",
        origin=True,
        link="https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-curate/SKILL.md",
        tags=["registry-curation","skill-discovery","evidence","validation","research"],
        description="Expands the Gaia skill registry with new, fully evidenced AI agent skills — researching skill sources, running validation, opening versioned PRs, and appending discovered marketplaces to the sources registry in one end-to-end workflow.",
    ),
    dict(
        name="Gaia Meta Audit",
        generic_ref="gaia-meta-audit",
        level="4★",
        title="The Triage Director",
        origin=True,
        link="https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-meta-audit/SKILL.md",
        tags=["registry-curation","prioritization","triage","quality-control"],
        description="Produces a prioritized review queue of Gaia registry entries needing attention — flagging stale evidence, broken links, mis-classified tiers, and naming inconsistencies in one structured audit pass.",
    ),
    dict(
        name="Gaia Audit",
        generic_ref="gaia-audit",
        level="3★",
        title="The Source Detective",
        origin=True,
        link="https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-audit/SKILL.md",
        tags=["registry-curation","source-verification","evidence","correction"],
        description="Performs a focused source-level correction for one target registry entry — verifying links, checking evidence classes, and filing an inline-diff fix PR with full citations.",
    ),
    dict(
        name="Research",
        generic_ref="research",
        level="3★",
        title="The Cartographer",
        origin=True,
        link="https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-curate/SKILL.md",
        tags=["research","synthesis","citation","multi-source"],
        description="Conducts multi-source research by decomposing a topic into sub-questions, cross-referencing sources, and synthesising findings into a structured answer with inline citations — flagging contradictions explicitly.",
    ),
    dict(
        name="Web Scrape",
        generic_ref="web-scrape",
        level="4★",
        title="The Registry Crawler",
        origin=False,
        link="https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/scrape/SKILL.md",
        tags=["web-scrape","extraction","markdown","structured-data"],
        description="Fetches, parses, and structures web content into clean Markdown or JSON — strips boilerplate, extracts main content, and preserves source provenance for downstream AI pipelines.",
    ),
    dict(
        name="Gaia Bot Curate",
        generic_ref="registry-curation",
        level="3★",
        title="The Automated Curator",
        origin=False,
        link="https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-bot-curate/SKILL.md",
        tags=["registry-curation","automation","batch-processing"],
        description="Runs an automated batch curation pass over the Gaia skill registry — scanning for new agent skills, validating evidence, and opening versioned draft PRs without human intervention.",
    ),
    dict(
        name="Gaia Draft Curate",
        generic_ref="registry-curation",
        level="3★",
        title="The Draft Architect",
        origin=False,
        link="https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-draft-curate/SKILL.md",
        tags=["registry-curation","draft","workflow"],
        description="Creates structured draft skill entries for registry review — staging new discoveries with placeholder evidence and flagging fields that need human validation before promotion.",
    ),
    dict(
        name="Gaia Curation Review",
        generic_ref="registry-curation",
        level="3★",
        title="The Quality Gate",
        origin=False,
        link="https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-curate/SKILL.md",
        tags=["registry-curation","review","quality-gate"],
        description="Reviews pending skill submissions against registry standards — checking evidence class thresholds, naming conventions, and tier accuracy before approving or requesting revisions.",
    ),
    dict(
        name="Graphify Triage",
        generic_ref="knowledge-graph-build",
        level="3★",
        title="The Graph Surgeon",
        origin=False,
        link="https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/graphify-triage/SKILL.md",
        tags=["graph-analysis","triage","visualization","skill-graph"],
        description="Analyzes the Gaia skill dependency graph to surface orphaned nodes, missing prerequisites, and structural inconsistencies — producing a prioritized list of graph fixes needed.",
    ),
    dict(
        name="Gaia Wiki Sync",
        generic_ref="document-editing",
        level="2★",
        title="The Wiki Keeper",
        origin=False,
        link="https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-wiki-sync/SKILL.md",
        tags=["documentation","wiki","sync"],
        description="Synchronizes the Gaia project wiki with the current registry state — updating skill pages, contributor profiles, and changelog entries to reflect the latest approved changes.",
    ),
    dict(
        name="Gaia Docs Sync",
        generic_ref="document-editing",
        level="2★",
        title="The Docs Steward",
        origin=False,
        link="https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-docs-sync/SKILL.md",
        tags=["documentation","docs","sync"],
        description="Keeps the generated Gaia documentation site in sync with the registry — rebuilding HTML pages, updating skill indexes, and regenerating badges when registry content changes.",
    ),
    dict(
        name="Gaia Integrity",
        generic_ref="registry-curation",
        level="3★",
        title="The Schema Sentinel",
        origin=False,
        link="https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-integrity/SKILL.md",
        tags=["registry-curation","integrity","validation","schema"],
        description="Validates the structural integrity of the Gaia registry — checking schema compliance, detecting duplicate IDs, verifying cross-references, and reporting any inconsistencies that would break build or generation.",
    ),
    dict(
        name="Gaia Triage",
        generic_ref="registry-curation",
        level="2★",
        title="The Issue Sorter",
        origin=False,
        link="https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-triage/SKILL.md",
        tags=["registry-curation","triage","prioritization"],
        description="Triages incoming skill proposals and issues against the Gaia registry backlog — sorting by impact, feasibility, and dependency order to produce an actionable prioritized work queue.",
    ),
    dict(
        name="Gaia Preview",
        generic_ref="registry-curation",
        level="2★",
        title="The Change Previewer",
        origin=False,
        link="https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-curate/SKILL.md",
        tags=["registry-curation","preview","staging"],
        description="Generates a preview render of proposed registry changes — showing how new or modified skill entries will appear on the profile page and in the skill graph before the PR is merged.",
    ),
]

for s in SKILLS:
    extra = {"links": {"github": s["link"]}, "tags": s["tags"]}
    if s["origin"]:
        extra["origin"] = True
    cmd = [
        sys.executable, "-m", "gaia_cli", "dev", "add", s["name"],
        "--named", "--contributor", "mbtiongson1",
        "--generic-ref", s["generic_ref"],
        "--level", s["level"],
        "--title", s["title"],
        "--extra-fields", json.dumps(extra),
        "--description", s["description"],
        "--no-build",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if result.returncode != 0:
        print(f"ERROR: {s['name']}")
        print(result.stderr)
        sys.exit(1)
    print(result.stdout.strip())

print("\nDone — all 14 skills recreated.")

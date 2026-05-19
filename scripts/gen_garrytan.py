"""Generate the 28 remaining garrytan named skill .md files."""
import os

BASE = os.path.join(os.path.dirname(__file__), "..", "registry", "named", "garrytan")

SKILLS = [
    # 4-star
    dict(
        slug="skillify",
        name="Skillify",
        genericSkillRef="skill-authoring",
        level="4★",
        title="Gstack Skillify — Skill Authoring Pipeline",
        description="Converts a freeform prompt, repo pattern, or workflow description into a complete, registry-ready named skill: writes the SKILL.md definition, populates frontmatter fields, and opens a PR for review.",
        tags=["skill-authoring", "automation", "meta"],
    ),
    # 3-star
    dict(
        slug="design-review",
        name="Design Review",
        genericSkillRef="ux-audit",
        level="3★",
        title="Gstack Design Review — UX Audit Pass",
        description="Runs a structured UX audit over a product interface, scoring layout clarity, affordance, and accessibility against the Gstack design rubric to surface actionable improvements.",
        tags=["ux-audit", "design", "review"],
    ),
    dict(
        slug="scrape",
        name="Scrape",
        genericSkillRef="web-scrape",
        level="3★",
        title="Gstack Scrape — Structured Web Extraction",
        description="Fetches target URLs with a headless browser, parses structured data from rendered HTML, and returns clean JSON or markdown ready for downstream analysis or ingestion.",
        tags=["web-scrape", "data-extraction", "automation"],
    ),
    dict(
        slug="retro",
        name="Retro",
        genericSkillRef="write-report",
        level="3★",
        title="Gstack Retro — Sprint Retrospective Report",
        description="Synthesises commit history, PR comments, and issue notes into a written sprint retrospective covering wins, misses, root causes, and action items.",
        tags=["write-report", "retrospective", "documentation"],
    ),
    dict(
        slug="browse",
        name="Browse",
        genericSkillRef="browser-control",
        level="3★",
        title="Gstack Browse — Directed Browser Navigation",
        description="Drives a browser to a target URL, navigates multi-step user journeys, and captures screenshots or structured observations for downstream verification or reporting.",
        tags=["browser-control", "navigation", "qa"],
    ),
    dict(
        slug="devex-review",
        name="DevEx Review",
        genericSkillRef="ux-audit",
        level="3★",
        title="Gstack DevEx Review — Developer Experience Audit",
        description="Audits CLI ergonomics, API surface clarity, and onboarding friction from a developer perspective, producing a scored report with prioritised fixes.",
        tags=["ux-audit", "developer-experience", "review"],
    ),
    dict(
        slug="health",
        name="Health",
        genericSkillRef="automated-testing",
        level="3★",
        title="Gstack Health — Automated Test Suite Runner",
        description="Executes the full automated test suite, collects pass/fail counts and coverage deltas, and surfaces any newly introduced failures with concise root-cause notes.",
        tags=["automated-testing", "ci", "quality"],
    ),
    dict(
        slug="benchmark-models",
        name="Benchmark Models",
        genericSkillRef="skill-performance-benchmarking",
        level="3★",
        title="Gstack Benchmark Models — LLM Performance Profiling",
        description="Runs a standardised prompt suite across multiple model versions, records latency and quality scores, and produces a ranked comparison table to guide model selection.",
        tags=["skill-performance-benchmarking", "llm", "evaluation"],
    ),
    dict(
        slug="codex",
        name="Codex",
        genericSkillRef="multi-agent-debate",
        level="3★",
        title="Gstack Codex — Multi-Agent Code Debate",
        description="Spins up a structured Claude-versus-Codex debate over a proposed implementation, with each agent mounting adversarial critiques, to surface hidden design flaws before code lands.",
        tags=["multi-agent-debate", "code-review", "adversarial"],
    ),
    dict(
        slug="pair-agent",
        name="Pair Agent",
        genericSkillRef="mcp-integration",
        level="3★",
        title="Gstack Pair Agent — MCP Tool Integration",
        description="Wires a new MCP server into the Gstack agent environment, validates the tool manifest, and demonstrates round-trip invocation through a test prompt.",
        tags=["mcp-integration", "tooling", "agents"],
    ),
    dict(
        slug="learn",
        name="Learn",
        genericSkillRef="memory-manage",
        level="3★",
        title="Gstack Learn — Persistent Memory Management",
        description="Reads the active memory store, consolidates new observations from the current session, deduplicates stale entries, and writes back an updated, ranked knowledge base for future sessions.",
        tags=["memory-manage", "context", "knowledge"],
    ),
    dict(
        slug="guard",
        name="Guard",
        genericSkillRef="guardrails",
        level="3★",
        title="Gstack Guard — Safety Guardrail Enforcement",
        description="Applies configurable content and output guardrails to agent responses, flagging or blocking unsafe outputs and logging violations with structured evidence for audit.",
        tags=["guardrails", "safety", "compliance"],
    ),
    dict(
        slug="make-pdf",
        name="Make PDF",
        genericSkillRef="format-output",
        level="3★",
        title="Gstack Make PDF — Formatted Output Generator",
        description="Converts markdown or structured data into a polished PDF document with consistent heading styles, table formatting, and page layout ready for distribution.",
        tags=["format-output", "pdf", "documentation"],
    ),
    # 2-star
    dict(
        slug="qa-only",
        name="QA Only",
        genericSkillRef="e2e-testing",
        level="2★",
        title="Gstack QA Only — Focused E2E Test Run",
        description="Runs the scoped end-to-end test suite for a single feature or route without launching the full QA pipeline, for fast targeted regression checks.",
        tags=["e2e-testing", "qa", "targeted"],
    ),
    dict(
        slug="document-release",
        name="Document Release",
        genericSkillRef="document-editing",
        level="2★",
        title="Gstack Document Release — Release Note Authoring",
        description="Reads the diff between two version tags and drafts concise, user-facing release notes following the Gstack changelog format.",
        tags=["document-editing", "release", "changelog"],
    ),
    dict(
        slug="setup-browser-cookies",
        name="Setup Browser Cookies",
        genericSkillRef="browser-control",
        level="2★",
        title="Gstack Setup Browser Cookies — Auth Cookie Injection",
        description="Injects pre-authenticated session cookies into the browser context so subsequent automation steps can access gated pages without a manual login flow.",
        tags=["browser-control", "auth", "setup"],
    ),
    dict(
        slug="plan-tune",
        name="Plan Tune",
        genericSkillRef="prompt-optimization",
        level="2★",
        title="Gstack Plan Tune — Prompt Refinement Pass",
        description="Takes a draft plan or system prompt, identifies vague or ambiguous instructions, and rewrites them to reduce hallucination and improve task completion rate.",
        tags=["prompt-optimization", "planning", "quality"],
    ),
    dict(
        slug="context-save",
        name="Context Save",
        genericSkillRef="context-compression",
        level="2★",
        title="Gstack Context Save — Session State Snapshot",
        description="Compresses the current session context into a compact summary file that can be restored later, enabling long-running workflows to survive context-window limits.",
        tags=["context-compression", "session", "continuity"],
    ),
    dict(
        slug="context-restore",
        name="Context Restore",
        genericSkillRef="context-compression",
        level="2★",
        title="Gstack Context Restore — Session State Recovery",
        description="Reads a saved context snapshot and reconstructs a warm session state, surfacing the last decision point and pending tasks so work can resume without recap.",
        tags=["context-compression", "session", "continuity"],
    ),
    dict(
        slug="landing-report",
        name="Landing Report",
        genericSkillRef="project-management",
        level="2★",
        title="Gstack Landing Report — Project Status Summary",
        description="Generates a one-page project landing report from open issues, recent commits, and milestone progress, giving stakeholders a quick read on health and next steps.",
        tags=["project-management", "reporting", "status"],
    ),
    dict(
        slug="setup-gbrain",
        name="Setup GBrain",
        genericSkillRef="knowledge-management",
        level="2★",
        title="Gstack Setup GBrain — Knowledge Base Initialisation",
        description="Bootstraps the GBrain knowledge store for a new project: creates the index structure, ingests seed documents, and validates retrieval with a sample query.",
        tags=["knowledge-management", "setup", "gbrain"],
    ),
    dict(
        slug="sync-gbrain",
        name="Sync GBrain",
        genericSkillRef="knowledge-management",
        level="2★",
        title="Gstack Sync GBrain — Knowledge Base Sync",
        description="Incrementally syncs new documents and updated pages into the GBrain index, deduplicates embeddings, and reports ingestion counts and any errors.",
        tags=["knowledge-management", "sync", "gbrain"],
    ),
    dict(
        slug="careful",
        name="Careful",
        genericSkillRef="guardrails",
        level="2★",
        title="Gstack Careful — Conservative Execution Mode",
        description="Activates a conservative execution profile that pauses before irreversible actions, requests explicit confirmation for destructive operations, and logs all side effects.",
        tags=["guardrails", "safety", "confirmation"],
    ),
    dict(
        slug="freeze",
        name="Freeze",
        genericSkillRef="guardrails",
        level="2★",
        title="Gstack Freeze — Change Freeze Enforcement",
        description="Sets a change-freeze flag that blocks non-critical commits and PR merges until explicitly lifted, protecting release branches or post-incident windows.",
        tags=["guardrails", "freeze", "release-management"],
    ),
    dict(
        slug="unfreeze",
        name="Unfreeze",
        genericSkillRef="guardrails",
        level="2★",
        title="Gstack Unfreeze — Change Freeze Lift",
        description="Clears the active change-freeze flag and restores normal merge permissions, logging the unfreeze event with a timestamp and justification.",
        tags=["guardrails", "freeze", "release-management"],
    ),
    dict(
        slug="open-gstack-browser",
        name="Open GStack Browser",
        genericSkillRef="browser-control",
        level="2★",
        title="Gstack Open Browser — Browser Session Launch",
        description="Launches a new headless or headed browser session with the Gstack environment variables and extension profile pre-loaded, ready for automation commands.",
        tags=["browser-control", "setup", "automation"],
    ),
    dict(
        slug="setup-deploy",
        name="Setup Deploy",
        genericSkillRef="deployment-automation",
        level="2★",
        title="Gstack Setup Deploy — Deployment Environment Init",
        description="Provisions the deployment environment by creating secrets, configuring environment variables, and running infrastructure-as-code init steps before the first deploy.",
        tags=["deployment-automation", "setup", "infrastructure"],
    ),
    dict(
        slug="gstack-upgrade",
        name="GStack Upgrade",
        genericSkillRef="workspace-automation",
        level="2★",
        title="Gstack Upgrade — Workspace Dependency Upgrade",
        description="Scans the workspace for outdated dependencies, runs upgrades within semver-compatible bounds, re-runs tests, and commits a clean dependency bump PR.",
        tags=["workspace-automation", "dependencies", "maintenance"],
    ),
]

TEMPLATE = """\
---
id: garrytan/{slug}
name: {name}
contributor: garrytan
origin: false
genericSkillRef: {genericSkillRef}
status: named
title: "{title}"
catalogRef: garrytan-{slug}
level: "{level}"
description: {description}
links:
  github: https://github.com/garrytan/gstack/blob/main/{slug}/SKILL.md
tags:
{tags_yaml}
createdAt: "2026-05-18"
updatedAt: "2026-05-18"
---

## Overview

{description}
"""

for s in SKILLS:
    tags_yaml = "\n".join(f"  - {t}" for t in s["tags"])
    content = TEMPLATE.format(
        slug=s["slug"],
        name=s["name"],
        genericSkillRef=s["genericSkillRef"],
        title=s["title"],
        level=s["level"],
        description=s["description"],
        tags_yaml=tags_yaml,
    )
    path = os.path.join(BASE, f"{s['slug']}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote {s['slug']}.md ({s['level']})")

print(f"\nDone: {len(SKILLS)} files written.")

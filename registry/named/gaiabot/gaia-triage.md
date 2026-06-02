---
id: gaiabot/gaia-triage
name: Gaia Triage (Internal)
contributor: gaiabot
origin: false
genericSkillRef: issue-triage
status: awakened
level: "2★"
description: Automates repository triage for the Gaia Skill Tree, including fixing documentation drift, managing build dependencies (build, setuptools, wheel), and synchronizing generated graph projections and GEXF exports.
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-triage/SKILL.md
tags:
  - maintenance
  - triage
  - automation
  - ci-fix
  - packaging
createdAt: "2026-05-10"
updatedAt: "2026-05-10"
---

## Overview

Gaia Triage is a project-specific implementation of the `/gaia-triage` skill. it focuses on the three most common causes of PR failure in the Gaia Skill Tree repository:

1.  **Documentation Drift:** Regenerating `docs/index.html` when skills are added.
2.  **Environment Readiness:** Ensuring build tools like `setuptools` and `wheel` are present.
3.  **Projections Sync:** Synchronizing `gaia.gexf` and registry indices.

## Implementation Details

The skill executes via a series of localized scripts:

### 1. Documentation Check
```bash
uv run python scripts/build_docs.py --check
# If stale:
uv run python scripts/build_docs.py
```

### 2. Dependency Management
Ensures the local environment can run packaging tests:
```bash
uv pip install pytest build setuptools wheel
```

### 3. Registry Projections
Synchronizes the visual and structural graph data:
```bash
uv run python scripts/generateProjections.py
uv run python scripts/exportGexf.py
```

## Guardrails
Always run the full test suite (`uv run pytest`) after these fixes to ensure no regressions were introduced by the environment or sync changes.

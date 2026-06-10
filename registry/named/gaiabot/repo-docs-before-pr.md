---
id: gaiabot/repo-docs-before-pr
name: Repo Docs Before PR
contributor: gaiabot
origin: false
genericSkillRef: write-report
status: awakened
level: 2★
description: Builds and validates repository documentation as a pre-PR guardrail by
  reminding contributors to run the local docs drift check, then surfaces actionable
  regeneration commands so pull requests do not fail CI on documentation freshness.
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree
tags:
- documentation
- ci
- pre-pr
- quality-gate
- repo-maintenance
createdAt: '2026-05-01'
updatedAt: '2026-06-10'
evidence:
- class: B
  source: https://github.com/mbtiongson1/gaia-skill-tree
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: 'Exercised in this repository''s own CI: the docs drift check (gaia docs
    build --check) gates every PR, demonstrating the skill in production.'
timeline:
- timestamp: '2026-06-10T05:38:16Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/mbtiongson1/gaia-skill-tree
---

## Overview

Repo Docs Before PR is a repository hygiene skill that enforces docs freshness before opening or reviewing a pull request. It reminds contributors to run the project's local docs drift check, checks whether generated documentation is stale, and asks the agent to stage regenerated files as part of the same change set.

## Notes

This implementation targets repositories that expose a dedicated docs build command. In Gaia, the copyable pre-review check is:

```bash
python scripts/build_docs.py --check
```

If the check reports drift, regenerate with:

```bash
python scripts/build_docs.py
```

The repository reminder workflow surfaces this command on every PR so contributors do not need to infer it from a failed CI log.

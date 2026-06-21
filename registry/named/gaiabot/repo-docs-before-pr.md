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
updatedAt: '2026-06-21'
evidence:
- class: B
  source: https://github.com/mbtiongson1/gaia-skill-tree
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: 'Exercised in this repository''s own CI: the docs drift check (gaia docs
    build --check) gates every PR, demonstrating the skill in production. (backfilled
    — class-to-type migration) (CLI gap: commits+contributors not writable via gaia
    dev evidence)'
  type: repo
  commits: 90
  contributors: 10
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-10T05:38:16Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/mbtiongson1/gaia-skill-tree
- timestamp: '2026-06-14T12:32:18Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mbtiongson1/gaia-skill-tree
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:14Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:36Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
trustMagnitude: 36.0
overallTrustGrade: C
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
verification:
  firstEvidenceAt: '2026-06-10T05:38:16Z'
trustMagnitudeInputHash: 73a9df9acba590a4a8bb7d99df1e6f4827ffc7ed045571ac6d7c39f3ed1797ef
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

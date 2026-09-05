---
id: mattpocock/git-guardrails-claude-code
name: Git Guardrails Claude Code
contributor: mattpocock
origin: false
genericSkillRef: guardrails
status: named
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/misc/git-guardrails-claude-code/SKILL.md
level: 2★
description: Set up Claude Code hooks to block dangerous git commands before they
  execute.
createdAt: '2026-06-19'
updatedAt: '2026-09-05'
timeline:
- timestamp: '2026-06-19T12:59:34Z'
  action: add
  contributor: unknown
  details: Added named skill mattpocock/git-guardrails-claude-code
- timestamp: '2026-06-19T13:04:53Z'
  action: evidence_added
  contributor: unknown
  details: Added evidence from https://github.com/mattpocock/skills/blob/main/skills/misc/git-guardrails-claude-code/SKILL.md
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:41Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T18:37:24Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/mattpocock/skills/blob/main/skills/misc/git-guardrails-claude-code/SKILL.md
    (type: repo-own)'
- timestamp: '2026-06-19T18:37:24Z'
  action: evidence_graded
  contributor: mbtiongson1
  details: 'Graded evidence from https://github.com/mattpocock/skills/blob/main/skills/misc/git-guardrails-claude-code/SKILL.md
    as B (trustNumber: 65.0)'
- timestamp: '2026-06-19T18:37:25Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/mattpocock/skills/blob/main/skills/misc/git-guardrails-claude-code
    (type: self-attestation)'
- timestamp: '2026-06-19T18:37:26Z'
  action: evidence_graded
  contributor: mbtiongson1
  details: 'Graded evidence from https://github.com/mattpocock/skills/blob/main/skills/misc/git-guardrails-claude-code
    as C (trustNumber: 45.0)'
- timestamp: '2026-06-19T18:41:27Z'
  action: rank_up
  contributor: mbtiongson1
  details: 'I13 classify: status promoted from awakened to named (evidence floor met:
    repo-own B + self-attestation C)'
- timestamp: '2026-06-20T06:31:31Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 2★ to 1★ per G7 final rankings calibration.
- timestamp: '2026-08-20T05:14:33Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/mattpocock/skills (type: repo-own)'
- timestamp: '2026-08-20T05:15:18Z'
  action: rank_up
  contributor: mbtiongson1
  details: Calibrated level from 1★ to 2★
- timestamp: '2026-08-29T17:15:52Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 0.0 -> 41.0, grade ungraded -> C (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-09-04T10:58:45Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
  details: 'TM 41.0 -> 41.0, grade C -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
- timestamp: '2026-09-04T18:43:51Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
  details: 'TM 41.0 -> 41.0, grade C -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
evidence:
- source: https://github.com/mattpocock/skills/blob/main/skills/misc/git-guardrails-claude-code/SKILL.md
  evaluator: unknown
  date: '2026-06-19'
  class: B
- source: https://github.com/mattpocock/skills/blob/main/skills/misc/git-guardrails-claude-code/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-20'
  type: repo-own
  trustNumber: 65.0
  notes: 'I13 classify: repo-own evidence backfill (skill file)'
  skillCountInRepo: 34
  sourceStartedAt: '2026-06-19'
- source: https://github.com/mattpocock/skills/blob/main/skills/misc/git-guardrails-claude-code
  evaluator: mbtiongson1
  date: '2026-06-20'
  type: self-attestation
  trustNumber: 45.0
  grade: C
  notes: 'I13 classify: contributor-owned skill directory evidence'
  sourceStartedAt: '2026-06-19'
- source: https://github.com/mattpocock/skills
  evaluator: mbtiongson1
  date: '2026-08-20'
  type: repo-own
  commits: 525
  contributors: 7
  grade: B
verification:
  firstEvidenceAt: '2026-06-19T13:04:53Z'
trustMagnitude: 41.0
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
trustMagnitudeInputHash: fa9a0814f1e0984e06c4fa5c5c79ca79fba37b5a823aa436700bdaa85b184169
title: Git Guardrails for Claude Code
suiteRef: mattpocock/misc
---

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.

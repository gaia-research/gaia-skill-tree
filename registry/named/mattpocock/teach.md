---
id: mattpocock/teach
name: Teach
contributor: mattpocock
origin: false
genericSkillRef: knowledge-management
status: named
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/productivity/teach/SKILL.md
level: 2★
description: Teach the user a new skill or concept in a workspace with mission, reference
  materials, and lessons.
createdAt: '2026-06-19'
updatedAt: '2026-09-04'
timeline:
- timestamp: '2026-06-19T13:02:46Z'
  action: add
  contributor: unknown
  details: Added named skill mattpocock/teach
- timestamp: '2026-06-19T13:07:26Z'
  action: evidence_added
  contributor: unknown
  details: Added evidence from https://github.com/mattpocock/skills/blob/main/skills/productivity/teach/SKILL.md
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:41Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T18:37:51Z'
  action: evidence_added
  contributor: testuser
  details: 'Added evidence from https://github.com/mattpocock/skills/blob/main/skills/productivity/teach/SKILL.md
    (type: repo-own)'
- timestamp: '2026-06-19T18:37:51Z'
  action: evidence_graded
  contributor: testuser
  details: 'Graded evidence from https://github.com/mattpocock/skills/blob/main/skills/productivity/teach/SKILL.md
    as B (trustNumber: 65.0)'
- timestamp: '2026-06-19T18:37:53Z'
  action: evidence_added
  contributor: testuser
  details: 'Added evidence from https://github.com/mattpocock/skills/blob/main/skills/productivity/teach
    (type: self-attestation)'
- timestamp: '2026-06-19T18:37:53Z'
  action: evidence_graded
  contributor: testuser
  details: 'Graded evidence from https://github.com/mattpocock/skills/blob/main/skills/productivity/teach
    as C (trustNumber: 45.0)'
- timestamp: '2026-06-19T18:39:16Z'
  action: evidence_added
  contributor: testuser
  details: 'Added evidence from https://www.youtube.com/watch?v=s5T5oQJcJ6U (type:
    social-signal)'
- timestamp: '2026-06-19T18:39:16Z'
  action: evidence_graded
  contributor: testuser
  details: 'Graded evidence from https://www.youtube.com/watch?v=s5T5oQJcJ6U as B
    (trustNumber: 65.0)'
- timestamp: '2026-06-19T18:41:33Z'
  action: rank_up
  contributor: testuser
  details: 'I13 classify: status promoted from awakened to named (evidence floor met:
    repo-own B + self-attestation C)'
- timestamp: '2026-08-20T04:55:14Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to mattpocock/productivity
- timestamp: '2026-08-29T17:15:54Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 0.0 -> 44.48, grade ungraded -> C (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-09-04T10:58:45Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
  details: 'TM 44.48 -> 44.48, grade C -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
evidence:
- source: https://github.com/mattpocock/skills/blob/main/skills/productivity/teach/SKILL.md
  evaluator: unknown
  date: '2026-06-19'
  class: B
- source: https://github.com/mattpocock/skills/blob/main/skills/productivity/teach/SKILL.md
  evaluator: testuser
  date: '2026-06-20'
  type: repo-own
  trustNumber: 65.0
  notes: 'I13 classify: repo-own evidence backfill (skill file)'
  skillCountInRepo: 34
  sourceStartedAt: '2026-06-19'
- source: https://github.com/mattpocock/skills/blob/main/skills/productivity/teach
  evaluator: testuser
  date: '2026-06-20'
  type: self-attestation
  trustNumber: 45.0
  grade: C
  notes: 'I13 classify: contributor-owned skill directory evidence'
  sourceStartedAt: '2026-06-19'
- source: https://www.youtube.com/watch?v=s5T5oQJcJ6U
  evaluator: testuser
  date: '2026-06-20'
  type: social-signal
  trustNumber: 65.0
  grade: B
  notes: 'I13 classify: YouTube video ''Learn anything with the /teach skill'' (86K
    views) — mattpocock''s own channel'
  views: 86000
  sourceStartedAt: '2026-06-19'
verification:
  firstEvidenceAt: '2026-06-19T13:07:26Z'
trustMagnitude: 44.48
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
trustMagnitudeInputHash: 793d80005c490b798e5d2190fa98e44ec3444c00826304912094a2ac2b3c1733
title: Teach
suiteRef: "mattpocock/skills"
---

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.

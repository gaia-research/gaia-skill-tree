---
id: mattpocock/handoff
name: Handoff
contributor: mattpocock
origin: false
genericSkillRef: agent-handoff
status: named
title: The Handoff Protocol
level: 4★
description: Compacts the current conversation into a summary for a fresh agent to
  continue the work.
createdAt: '2026-05-21'
updatedAt: '2026-06-14'
suiteRef: mattpocock/productivity
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/productivity/handoff
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/productivity/handoff/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-22'
  notes: 'High-fidelity agent handoff and context compaction skill. (backfilled —
    class-to-type" migration) (CLI gap: --commits/--contributors not supported by
    gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 137
  contributors: 3
timeline:
- timestamp: '2026-06-14T12:32:43Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mattpocock/skills/blob/main/skills/productivity/handoff/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 11.21, grade ungraded -> ungraded (direct edit -- CLI gap)
trustMagnitude: 11.21
overallTrustGrade: ungraded
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 50f47d5e66a654ba2b92dc1089e5ce8b8f5c52fd4ec651ad0ec34824684e679a
---

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.

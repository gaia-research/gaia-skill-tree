---
id: mattpocock/handoff
name: Handoff
contributor: mattpocock
origin: false
genericSkillRef: agent-handoff
status: named
title: The Handoff Protocol
level: 3★
description: Compacts the current conversation into a summary for a fresh agent to
  continue the work.
createdAt: '2026-05-21'
updatedAt: '2026-06-19'
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
- source: https://github.com/mattpocock/skills/issues/171
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: GitHub issue about handoff skill enhancement.
- source: https://github.com/mattpocock/skills/issues/172
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: GitHub issue about handoff skill UX improvement.
- source: https://github.com/mattpocock/skills/issues/175
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: GitHub issue about handoff skill bug on macOS.
- source: https://github.com/mattpocock/skills/issues/186
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: GitHub issue about handoff skill context preservation.
- source: https://github.com/mattpocock/skills/issues/235
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: GitHub issue with handoff skill feature suggestions.
- source: https://github.com/mattpocock/skills/issues/349
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: GitHub issue about handoff skill output format.
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
- timestamp: '2026-06-19T12:33:32Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/issues/171 (type:
    peer-review)'
- timestamp: '2026-06-19T12:33:47Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/issues/172 (type:
    peer-review)'
- timestamp: '2026-06-19T12:34:01Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/issues/175 (type:
    peer-review)'
- timestamp: '2026-06-19T12:34:16Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/issues/186 (type:
    peer-review)'
- timestamp: '2026-06-19T12:34:32Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/issues/235 (type:
    peer-review)'
- timestamp: '2026-06-19T12:34:46Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/issues/349 (type:
    peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T12:53:50Z'
  details: TM 11.21 -> 63.71, grade ungraded -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 63.71, grade ungraded -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:41Z'
  details: TM 0.0 -> 63.71, grade ungraded -> B (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:31Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 4★ to 3★ per G7 final rankings calibration.
trustMagnitude: 63.71
overallTrustGrade: B
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
  firstEvidenceAt: '2026-06-19T12:33:32Z'
trustMagnitudeInputHash: 2f4991fdd86fa9d43e89b01fa5cc924762dda957019dd375014572ce1c54df59
---

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.

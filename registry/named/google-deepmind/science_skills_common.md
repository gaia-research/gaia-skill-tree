---
id: google-deepmind/science_skills_common
name: Science-Skills-Common
contributor: google-deepmind
origin: false
genericSkillRef: core-platform-implementation
status: awakened
level: 4★
description: Shared Python package for Science Skills, currently containing http_client
  -- a unified HTTP client with rate limiting, retries, and exponential backoff. Not
  a standalone agent skill. Do not invoke directly.
createdAt: '2026-05-23'
updatedAt: '2026-06-21'
links:
  github: https://github.com/google-deepmind/science-skills/blob/main/skills/science_skills_common
evidence:
- class: B
  source: https://github.com/google-deepmind/science-skills/blob/main/skills/science_skills_common/SKILL.md
  evaluator: unknown
  date: '2026-05-23'
  notes: Official Google DeepMind science_skills_common science-skill implementation.
    (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  commits: 6
  contributors: 3
  grade: C
- source: https://github.com/google-deepmind/science-skills
  evaluator: unknown
  date: '2026-06-20'
  type: peer-review
  trustNumber: 78.0
  grade: S
  notes: google-deepmind/science-skills common utilities — 2k+ GitHub stars; shared
    infrastructure for 30+ database skills
  reviewers: 3
  sourceStartedAt: '2024-01-01'
timeline:
- timestamp: '2026-06-14T12:32:38Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/google-deepmind/science-skills/blob/main/skills/science_skills_common/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:17Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:57Z'
  details: TM 0.0 -> 10.82, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 10.82, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:39Z'
  details: TM 0.0 -> 10.82, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T17:06:57Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/google-deepmind/science-skills
    (type: peer-review)'
- timestamp: '2026-06-19T17:06:57Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/google-deepmind/science-skills
    as B (trustNumber: 78.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:02Z'
  details: TM 10.82 -> 100.82, grade ungraded -> A (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:27Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 2★ to 4★ per G7 final rankings calibration.
trustMagnitude: 100.82
overallTrustGrade: A
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 0318c27283170e94e677a11679cb4860f9b90e9e6191f878d3d14dd3b2e32138
verification:
  firstEvidenceAt: '2026-06-19T17:06:57Z'
---

# Science Skills Common

This is a shared Python package, not an agent skill. Skills import it as:

```python
from science_skills.science_skills_common import http_client
```

Each skill declares this as a dependency in its inline `uv` script header, so it
is installed automatically on first use.

This SKILL.md file is included so that standard skill installers automatically
discover and install this package alongside the skills that depend on it.

---
id: google-deepmind/science_skills_common
name: Science-Skills-Common
contributor: google-deepmind
origin: false
genericSkillRef: core-platform-implementation
status: awakened
level: 2★
description: Shared Python package for Science Skills, currently containing http_client
  -- a unified HTTP client with rate limiting, retries, and exponential backoff. Not
  a standalone agent skill. Do not invoke directly.
createdAt: '2026-05-23'
updatedAt: '2026-06-20'
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
  grade: B
  commits: 6
  contributors: 3
- source: https://github.com/google-deepmind/science-skills
  evaluator: unknown
  date: '2026-06-20'
  type: peer-review
  trustNumber: 78.0
  grade: B
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
trustMagnitude: 10.82
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
trustMagnitudeInputHash: e4614fe274a477d96978fab525c9c6432e4266176685de56062c2ce0828deb04
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

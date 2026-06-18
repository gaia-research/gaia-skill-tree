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
updatedAt: '2026-06-14'
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
timeline:
- timestamp: '2026-06-14T12:32:38Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/google-deepmind/science-skills/blob/main/skills/science_skills_common/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:17Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
trustMagnitude: 0.0
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
trustMagnitudeInputHash: 40ce4ee4b951ea5564a50a05266e5bcef67bfc1f4cd06ee097113c6aeb3d6131
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

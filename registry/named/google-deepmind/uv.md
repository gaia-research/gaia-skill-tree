---
id: google-deepmind/uv
name: Uv
contributor: google-deepmind
origin: false
genericSkillRef: core-platform-implementation
status: awakened
level: 2★
description: Checks whether the uv Python package manager is installed and installs
  it if missing. Ensures uv is on PATH. Use when another skill requires uv as a prerequisite.
createdAt: '2026-05-23'
updatedAt: '2026-06-20'
links:
  github: https://github.com/google-deepmind/science-skills/blob/main/skills/uv/SKILL.md
evidence:
- class: B
  source: https://github.com/google-deepmind/science-skills/blob/main/skills/uv/SKILL.md
  evaluator: unknown
  date: '2026-05-23'
  notes: Official Google DeepMind uv science-skill implementation. (backfilled — class-to-type
    migration)
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 6
  contributors: 3
- source: https://github.com/astral-sh/uv
  evaluator: unknown
  date: '2026-06-20'
  type: peer-review
  trustNumber: 78.0
  grade: B
  notes: uv — ultra-fast Python package manager by Astral (Ruff team); 51k+ GitHub
    stars; replaces pip+venv+poetry
  reviewers: 3
  sourceStartedAt: '2024-01-01'
timeline:
- timestamp: '2026-06-14T12:32:40Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/google-deepmind/science-skills/blob/main/skills/uv/SKILL.md
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
  timestamp: '2026-06-19T13:26:40Z'
  details: TM 0.0 -> 10.82, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T17:06:52Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/astral-sh/uv (type: peer-review)'
- timestamp: '2026-06-19T17:06:53Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/astral-sh/uv as B (trustNumber:
    78.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:02Z'
  details: TM 10.82 -> 100.82, grade ungraded -> A (direct edit -- CLI gap)
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
trustMagnitudeInputHash: 1e681dd683e378e65adadcc58e92dd0560095480fea01e7c5d82c251c2c403e6
verification:
  firstEvidenceAt: '2026-06-19T17:06:52Z'
---

# uv (Python Package Manager)

`uv` is a fast Python package manager used by Science Skills to run their Python
CLI scripts. Many skills depend on `uv` being installed and on PATH.

Ensure `uv` is available before running any skill that depends on it.

## Setup

1.  Check if `uv` is already available: `uv --version` If this succeeds, `uv` is
    ready — skip the remaining steps.
2.  Check whether `uv` is installed at its default location but not on PATH:
    `"$HOME/.local/bin/uv" --version` If this succeeds, skip to step 4.
3.  If uv is not installed do both these steps in order:
    (a) Tell the user that uv is a tool for creating a consistent and reliable
        Python environment used for running the Science Skills, and that you
        need to install it now.
    (b) Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`
4.  Add `uv` to PATH and verify (run as a single command): `export
    PATH="$HOME/.local/bin:$PATH" && uv --version`

After setup, bare `uv` commands should work without repeating the export.

---
id: t3dotgg/babysit-pr
name: babysit-pr
contributor: t3dotgg
origin: false
genericSkillRef: pr-ci-monitoring
status: named
level: 3★
description: Monitors an open pull request via stateful event watching across CI checks,
  review threads, and base-branch drift, distinguishing real defects from flakes.
createdAt: '2026-11-17'
updatedAt: '2026-11-18'
title: Babysit PR
links:
  github: https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/babysit-pr/SKILL.md
suiteRef: t3dotgg/tstack
timeline:
- timestamp: '2026-11-17T14:04:55Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill t3dotgg/babysit-pr
- timestamp: '2026-11-17T14:33:20Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/t3dotgg/tstack (type: repo-own)'
- timestamp: '2026-11-17T14:33:47Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/babysit-pr/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-11-17T14:34:11Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://www.youtube.com/watch?v=GGrvSnpPTGo (type:
    social-signal)'
- timestamp: '2026-11-17T17:14:59Z'
  action: rank_up
  contributor: mbtiongson1
  details: Calibrated level from 2★ to 3★
- timestamp: '2026-11-17T18:20:52Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 81.01, grade (none) -> B (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-11-17T18:35:20Z'
  action: installation_updated
  contributor: mbtiongson1
  details: 'Replaced ## Installation section from /data/data/com.termux/files/usr/tmp/tmpjbscjpdy/babysit-pr.md'
- timestamp: '2026-11-17T18:53:45Z'
  action: installation_updated
  contributor: mbtiongson1
  details: 'Replaced ## Installation section from /data/data/com.termux/files/usr/tmp/tmp3btow7tf/babysit-pr.md'
evidence:
- source: https://github.com/t3dotgg/tstack
  evaluator: mbtiongson1
  date: '2026-11-17'
  type: repo-own
  notes: Shared suite baseline t3dotgg/tstack at 11e37a74d0a6868c121cd0910ab2b3bd9873b92a
    (capped with github-stars-own at 49.90 TM).
  commits: 6
  contributors: 1
  sourceStartedAt: '2026-10-24'
- source: https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/babysit-pr/SKILL.md
  evaluator: mbtiongson1
  date: '2026-11-17'
  type: github-stars-own
  notes: Shared suite baseline 4,033 stars on t3dotgg/tstack (capped at 49.90 TM under
    suiteRef).
  stars: 4033
  skillCountInRepo: 9
  sourceStartedAt: '2026-10-24'
  grade: A
- source: https://www.youtube.com/watch?v=GGrvSnpPTGo
  evaluator: mbtiongson1
  date: '2026-11-17'
  type: social-signal
  notes: Third-party Better Stack breakdown of babysit-pr CI monitoring (03:22-04:33,
    07:09).
  views: 38821
  likes: 433
  comments: 45
  creator: '@betterstack'
  creatorRelation: third-party
  relevanceNote: Third-party Better Stack breakdown of babysit-pr CI monitoring (03:22-04:33,
    07:09).
  sourceStartedAt: '2026-11-12'
  grade: B
verification:
  firstEvidenceAt: '2026-11-17T14:33:14Z'
trustMagnitude: 81.01
overallTrustGrade: B
trustMagnitudeInputHash: 0a12f16eb280f35e20ba5b990b9f8ea116456bbc60cf7870b4fd0355a98c6286
---

## Installation
Install `babysit-pr` (or the full `tstack` suite) at the verified commit (`11e37a74d0a6868c121cd0910ab2b3bd9873b92a`) into Claude Code or Codex:

```bash
git clone https://github.com/t3dotgg/tstack
git -C tstack checkout 11e37a74d0a6868c121cd0910ab2b3bd9873b92a
mkdir -p ~/.claude/skills   # or ~/.codex/skills for Codex
cp -R tstack/skills/babysit-pr ~/.claude/skills/
```

### Dependencies & Requirements
- Uses `leaving-pr-comments` when posting PR replies; requires authenticated `gh` and `python3` (for `pr-wait`).

Upstream skill file: https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/babysit-pr/SKILL.md

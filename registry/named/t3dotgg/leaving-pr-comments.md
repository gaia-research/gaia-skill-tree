---
id: t3dotgg/leaving-pr-comments
name: leaving-pr-comments
contributor: t3dotgg
origin: false
genericSkillRef: format-output
status: named
level: 2★
description: Formats and posts concise, structured, line-anchored pull request review
  comments and summaries.
createdAt: '2026-11-17'
updatedAt: '2026-11-18'
title: Leaving PR Comments
links:
  github: https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/leaving-pr-comments/SKILL.md
suiteRef: t3dotgg/tstack
timeline:
- timestamp: '2026-11-17T14:05:03Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill t3dotgg/leaving-pr-comments
- timestamp: '2026-11-17T14:34:36Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/t3dotgg/tstack (type: repo-own)'
- timestamp: '2026-11-17T14:35:00Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/leaving-pr-comments/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-11-17T18:21:06Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 49.9, grade (none) -> C (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-11-17T18:35:35Z'
  action: installation_updated
  contributor: mbtiongson1
  details: 'Replaced ## Installation section from /data/data/com.termux/files/usr/tmp/tmpjbscjpdy/leaving-pr-comments.md'
- timestamp: '2026-11-17T18:54:00Z'
  action: installation_updated
  contributor: mbtiongson1
  details: 'Replaced ## Installation section from /data/data/com.termux/files/usr/tmp/tmp3btow7tf/leaving-pr-comments.md'
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
- source: https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/leaving-pr-comments/SKILL.md
  evaluator: mbtiongson1
  date: '2026-11-17'
  type: github-stars-own
  notes: Shared suite baseline 4,033 stars on t3dotgg/tstack (capped at 49.90 TM under
    suiteRef).
  stars: 4033
  skillCountInRepo: 9
  sourceStartedAt: '2026-10-24'
  grade: A
verification:
  firstEvidenceAt: '2026-11-17T14:34:30Z'
trustMagnitude: 49.9
overallTrustGrade: C
trustMagnitudeInputHash: 005873767f39852a2d4065a552f7189811585c8184b1cc99b6b5708aad830d20
---

## Installation
Install `leaving-pr-comments` (or the full `tstack` suite) at the verified commit (`11e37a74d0a6868c121cd0910ab2b3bd9873b92a`) into Claude Code or Codex:

```bash
git clone https://github.com/t3dotgg/tstack
git -C tstack checkout 11e37a74d0a6868c121cd0910ab2b3bd9873b92a
mkdir -p ~/.claude/skills   # or ~/.codex/skills for Codex
cp -R tstack/skills/leaving-pr-comments ~/.claude/skills/
```

### Dependencies & Requirements
- Invoked automatically by `file-pr`, `babysit-pr`, and `modernize` when posting PR comments; requires authenticated `gh`.

Upstream skill file: https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/leaving-pr-comments/SKILL.md

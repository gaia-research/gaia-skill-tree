---
id: t3dotgg/file-pr
name: file-pr
contributor: t3dotgg
origin: false
genericSkillRef: pull-request-authoring
status: named
level: 2★
description: Reviews a local branch diff against its base, runs pre-push secret checks,
  writes problem-first PR metadata, and opens a non-draft pull request.
createdAt: '2026-11-17'
updatedAt: '2026-11-18'
title: File PR
links:
  github: https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/file-pr/SKILL.md
suiteRef: t3dotgg/tstack
timeline:
- timestamp: '2026-11-17T14:05:17Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill t3dotgg/file-pr
- timestamp: '2026-11-17T16:44:13Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/t3dotgg/tstack (type: repo-own)'
- timestamp: '2026-11-17T16:44:52Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/file-pr/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-11-17T18:21:41Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 49.9, grade (none) -> C (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-11-17T18:36:06Z'
  action: installation_updated
  contributor: mbtiongson1
  details: 'Replaced ## Installation section from /data/data/com.termux/files/usr/tmp/tmpjbscjpdy/file-pr.md'
- timestamp: '2026-11-17T18:55:12Z'
  action: installation_updated
  contributor: mbtiongson1
  details: 'Replaced ## Installation section from /data/data/com.termux/files/usr/tmp/tmp3btow7tf/file-pr.md'
evidence:
- source: https://github.com/t3dotgg/tstack
  evaluator: mbtiongson1
  date: '2026-11-18'
  type: repo-own
  notes: Shared suite baseline t3dotgg/tstack at 11e37a74d0a6868c121cd0910ab2b3bd9873b92a
    (capped with github-stars-own at 49.90 TM).
  commits: 6
  contributors: 1
  sourceStartedAt: '2026-10-24'
- source: https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/file-pr/SKILL.md
  evaluator: mbtiongson1
  date: '2026-11-18'
  type: github-stars-own
  notes: Shared suite baseline 4,033 stars on t3dotgg/tstack (capped at 49.90 TM under
    suiteRef).
  stars: 4033
  skillCountInRepo: 9
  sourceStartedAt: '2026-10-24'
  grade: A
verification:
  firstEvidenceAt: '2026-11-17T16:44:09Z'
trustMagnitude: 49.9
overallTrustGrade: C
trustMagnitudeInputHash: a731c21f0bd2cede2e889ea94cdf69c16e4ec39cf086aab28558fe84232774d8
---

## Installation
Install `file-pr` (or the full `tstack` suite) at the verified commit (`11e37a74d0a6868c121cd0910ab2b3bd9873b92a`) into Claude Code or Codex:

```bash
git clone https://github.com/t3dotgg/tstack
git -C tstack checkout 11e37a74d0a6868c121cd0910ab2b3bd9873b92a
mkdir -p ~/.claude/skills   # or ~/.codex/skills for Codex
cp -R tstack/skills/file-pr ~/.claude/skills/
```

### Dependencies & Requirements
- Uses `leaving-pr-comments` and authenticated `gh`.

Upstream skill file: https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/file-pr/SKILL.md

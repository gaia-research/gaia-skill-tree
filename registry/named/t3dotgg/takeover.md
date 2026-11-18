---
id: t3dotgg/takeover
name: takeover
contributor: t3dotgg
origin: false
genericSkillRef: finishing-a-development-branch
status: named
level: 3★
description: Takes over an existing pull request branch, evaluates open review feedback
  and CI state, resolves remaining issues, and prepares the branch for merge.
createdAt: '2026-11-17'
updatedAt: '2026-11-18'
title: Takeover
links:
  github: https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/takeover/SKILL.md
suiteRef: t3dotgg/tstack
timeline:
- timestamp: '2026-11-17T14:04:39Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill t3dotgg/takeover
- timestamp: '2026-11-17T14:31:26Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/t3dotgg/tstack (type: repo-own)'
- timestamp: '2026-11-17T14:31:53Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/takeover/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-11-17T14:32:25Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://www.youtube.com/watch?v=5Bmp9cz1JN8 (type:
    social-signal)'
- timestamp: '2026-11-17T14:32:49Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://www.youtube.com/watch?v=SY_woOjzlW4 (type:
    social-signal)'
- timestamp: '2026-11-17T17:14:38Z'
  action: rank_up
  contributor: mbtiongson1
  details: Calibrated level from 2★ to 3★
- timestamp: '2026-11-17T18:20:47Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 92.9, grade (none) -> B (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-11-17T18:35:05Z'
  action: installation_updated
  contributor: mbtiongson1
  details: 'Replaced ## Installation section from /data/data/com.termux/files/usr/tmp/tmpjbscjpdy/takeover.md'
- timestamp: '2026-11-17T18:53:30Z'
  action: installation_updated
  contributor: mbtiongson1
  details: 'Replaced ## Installation section from /data/data/com.termux/files/usr/tmp/tmp3btow7tf/takeover.md'
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
- source: https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/takeover/SKILL.md
  evaluator: mbtiongson1
  date: '2026-11-17'
  type: github-stars-own
  notes: Shared suite baseline 4,033 stars on t3dotgg/tstack (capped at 49.90 TM under
    suiteRef).
  stars: 4033
  skillCountInRepo: 9
  sourceStartedAt: '2026-10-24'
  grade: A
- source: https://www.youtube.com/watch?v=5Bmp9cz1JN8
  evaluator: mbtiongson1
  date: '2026-11-17'
  type: social-signal
  notes: First-party Theo substantive 1m24s walkthrough of takeover (22:45-24:09)
    in 'These 3 skills changed my life'.
  views: 247982
  likes: 3059
  comments: 168
  creator: '@theo'
  creatorRelation: first-party
  relevanceNote: First-party Theo substantive 1m24s walkthrough of takeover (22:45-24:09)
    in 'These 3 skills changed my life'.
  sourceStartedAt: '2026-10-26'
  grade: B
- source: https://www.youtube.com/watch?v=SY_woOjzlW4
  evaluator: mbtiongson1
  date: '2026-11-17'
  type: social-signal
  notes: Pre-push live T3 Code stream (2026-10-14, 10 days before GitHub repo creation)
    invoking 'takeover' by exact skill name (00:31:07, 00:33:29).
  views: 50968
  likes: 441
  comments: 10
  creator: '@theo'
  creatorRelation: first-party
  relevanceNote: Pre-push live T3 Code stream (2026-10-14, 10 days before GitHub repo
    creation) invoking 'takeover' by exact skill name (00:31:07, 00:33:29).
  sourceStartedAt: '2026-10-14'
  grade: C
verification:
  firstEvidenceAt: '2026-11-17T14:31:19Z'
trustMagnitude: 92.9
overallTrustGrade: B
trustMagnitudeInputHash: c2cc019d19fc04cd1d4e82c06eaa639314c0bdaad2214a9d2e03a1efd7b4e233
---

## Installation
Install `takeover` (or the full `tstack` suite) at the verified commit (`11e37a74d0a6868c121cd0910ab2b3bd9873b92a`) into Claude Code or Codex:

```bash
git clone https://github.com/t3dotgg/tstack
git -C tstack checkout 11e37a74d0a6868c121cd0910ab2b3bd9873b92a
mkdir -p ~/.claude/skills   # or ~/.codex/skills for Codex
cp -R tstack/skills/takeover ~/.claude/skills/
```

### Dependencies & Requirements
- Calls `modernize`, `file-pr`, `babysit-pr`, and `leaving-pr-comments`; install the full `tstack` suite or include those dependencies. Requires authenticated `gh` and `python3` (for `babysit-pr`'s `pr-wait`).

Upstream skill file: https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/takeover/SKILL.md

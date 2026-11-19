---
id: t3dotgg/council
name: council
contributor: t3dotgg
origin: false
genericSkillRef: multi-agent-debate
status: named
level: 4★
description: Multi-agent debate and verification workflow that convenes parallel model
  perspectives to critique, refine, and converge on high-confidence solutions.
createdAt: '2026-11-17'
updatedAt: '2026-11-18'
title: Council
links:
  github: https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/council/SKILL.md
suiteRef: t3dotgg/tstack
timeline:
- timestamp: '2026-11-17T14:05:09Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill t3dotgg/council
- timestamp: '2026-11-17T14:35:37Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/t3dotgg/tstack (type: repo-own)'
- timestamp: '2026-11-17T16:39:21Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://www.youtube.com/watch?v=xq0eB8vxeqk (type:
    social-signal)'
- timestamp: '2026-11-17T16:40:13Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://www.youtube.com/watch?v=TWoS5Nmyoc8 (type:
    social-signal)'
- timestamp: '2026-11-17T16:42:10Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://www.youtube.com/watch?v=GGrvSnpPTGo (type:
    social-signal)'
- timestamp: '2026-11-17T17:14:23Z'
  action: rank_up
  contributor: mbtiongson1
  details: Calibrated level from 2★ to 4★
- timestamp: '2026-11-17T18:21:24Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 129.9, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-11-17T18:35:50Z'
  action: installation_updated
  contributor: mbtiongson1
  details: 'Replaced ## Installation section from /data/data/com.termux/files/usr/tmp/tmpjbscjpdy/council.md'
- timestamp: '2026-11-17T18:54:17Z'
  action: installation_updated
  contributor: mbtiongson1
  details: 'Replaced ## Installation section from /data/data/com.termux/files/usr/tmp/tmp3btow7tf/council.md'
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
- source: https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/council/SKILL.md
  evaluator: mbtiongson1
  date: '2026-11-17'
  type: github-stars-own
  notes: Shared suite baseline 4,033 stars on t3dotgg/tstack (capped at 49.90 TM under
    suiteRef).
  stars: 4033
  skillCountInRepo: 9
  sourceStartedAt: '2026-10-24'
  grade: A
- source: https://www.youtube.com/watch?v=xq0eB8vxeqk
  evaluator: mbtiongson1
  date: '2026-11-18'
  type: social-signal
  notes: First-party Theo full UI hill-climbing demo of council (04:26-31:00) in 'Agents
    Sucked At UI (Until Today)'.
  views: 438112
  likes: 6034
  comments: 516
  creator: '@theo'
  creatorRelation: first-party
  relevanceNote: First-party Theo full UI hill-climbing demo of council (04:26-31:00)
    in 'Agents Sucked At UI (Until Today)'.
  sourceStartedAt: '2026-11-03'
  grade: B
- source: https://www.youtube.com/watch?v=TWoS5Nmyoc8
  evaluator: mbtiongson1
  date: '2026-11-18'
  type: social-signal
  notes: First-party Theo 'council 9.5' verification clause demo (05:21-15:00+) in
    'Stop Searching For the Perfect Model'.
  views: 129817
  likes: 1961
  comments: 239
  creator: '@theo'
  creatorRelation: first-party
  relevanceNote: First-party Theo 'council 9.5' verification clause demo (05:21-15:00+)
    in 'Stop Searching For the Perfect Model'.
  sourceStartedAt: '2026-11-16'
  grade: B
- source: https://www.youtube.com/watch?v=GGrvSnpPTGo
  evaluator: mbtiongson1
  date: '2026-11-18'
  type: social-signal
  notes: Third-party Better Stack analytical critique of council (04:33-05:06).
  views: 38821
  likes: 433
  comments: 45
  creator: '@betterstack'
  creatorRelation: third-party
  relevanceNote: Third-party Better Stack analytical critique of council (04:33-05:06).
  sourceStartedAt: '2026-11-12'
  grade: B
verification:
  firstEvidenceAt: '2026-11-17T14:35:30Z'
trustMagnitude: 129.9
overallTrustGrade: A
trustMagnitudeInputHash: 79075c635f5e91942d289a95a757dff13ed0c8ea35616dd8eb0c18259cd724e8
---

## Installation
Install `council` (or the full `tstack` suite) at the verified commit (`11e37a74d0a6868c121cd0910ab2b3bd9873b92a`) into Claude Code or Codex:

```bash
git clone https://github.com/t3dotgg/tstack
git -C tstack checkout 11e37a74d0a6868c121cd0910ab2b3bd9873b92a
mkdir -p ~/.claude/skills   # or ~/.codex/skills for Codex
cp -R tstack/skills/council ~/.claude/skills/
```

### Dependencies & Requirements
- Requires subagent execution across multiple model providers (`delegate_task` in T3 Code or equivalent harness).

Upstream skill file: https://github.com/t3dotgg/tstack/blob/11e37a74d0a6868c121cd0910ab2b3bd9873b92a/skills/council/SKILL.md

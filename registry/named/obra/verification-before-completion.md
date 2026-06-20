---
id: obra/verification-before-completion
name: Verification Before Completion
contributor: obra
origin: true
genericSkillRef: verification-before-completion
status: named
title: The Completion Gate
level: 3★
description: Requires running verification commands and confirming their output before
  claiming any work is complete, fixed, or passing — no claim without evidence.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md
tags:
- verification
- completion
- testing
- quality-gate
- discipline
createdAt: '2026-05-18'
updatedAt: '2026-06-19'
suiteRef: obra/superpowers
evidence:
- class: B
  source: https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-18'
  notes: obra/superpowers — complete software development methodology for coding agents,
    196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode,
    Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 609
  contributors: 36
- source: https://github.com/obra/superpowers/issues/1783
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: Design-Fidelity Gate framed as UI-specific instance of verification-before-completion.
- source: https://github.com/obra/superpowers/issues/1755
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: Updates verification-before-completion to require outcome checks, not just
    command success.
- source: https://www.youtube.com/watch?v=6YltXh12W-g
  evaluator: unknown
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: 'Larridin podcast: Jesse Vincent explains obra/superpowers methodology covering
    brainstorming, plans, subagents, debugging, and git worktrees. 4,402 views (2026-06-19).'
  views: 4402
- source: https://www.youtube.com/watch?v=6YltXh12W-g
  evaluator: unknown
  date: '2026-06-19'
timeline:
- timestamp: '2026-06-14T12:32:49Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T12:47:33Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1783 (type:
    social-signal)'
- timestamp: '2026-06-19T12:47:50Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1755 (type:
    peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T12:53:51Z'
  details: TM 36.0 -> 66.0, grade C -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 66.0, grade ungraded -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:43Z'
  details: TM 0.0 -> 66.0, grade ungraded -> B (direct edit -- CLI gap)
- timestamp: '2026-06-19T14:26:01Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=6YltXh12W-g (type:
    social-signal)'
- timestamp: '2026-06-19T14:27:36Z'
  action: evidence_added
  contributor: unknown
  details: Added evidence from https://www.youtube.com/watch?v=6YltXh12W-g
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T14:31:47Z'
  details: TM 66.0 -> 95.15, grade B -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T14:32:19Z'
  details: TM 95.15 -> 95.15, grade B -> B (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:35Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 2★ to 3★ per G7 final rankings calibration.
trustMagnitude: 95.15
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
  firstEvidenceAt: '2026-06-19T12:47:33Z'
trustMagnitudeInputHash: 510420642b8632599e83ce4408243157a165de0c3bb070bc9549a1da49682f7e
---

## Overview

Verification Before Completion by @obra is the simplest and most broadly applicable skill in the superpowers library: the agent is not allowed to say "done", "fixed", or "passing" without first running the relevant verification command and including its output. This single constraint eliminates an entire class of hallucinated completions and untested "fixes" that create downstream rework.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `verification-before-completion` skill bucket.

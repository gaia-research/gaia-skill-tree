---
id: mattpocock/productivity
name: Productivity
contributor: mattpocock
origin: true
title: The Matt Pocock Productivity Suite
genericSkillRef: productivity
status: named
level: 4★
description: Productivity category suite for Matt Pocock's skills. Removed from mattpocock/skills
  suite in v1.0.1.
createdAt: '2026-05-21'
updatedAt: '2026-09-06'
trustMagnitude: 102.5
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
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:41Z'
  details: TM 0.0 -> 120.0, grade ungraded -> A (direct edit -- CLI gap)
- timestamp: '2026-07-20T18:16:45Z'
  action: type_change
  contributor: mbtiongson1
  details: 'Generic parent ''productivity'' type: extra/ultimate → fusion (Yggdrasil
    II taxonomy migration #997)'
  metaEpoch: yggdrasil-ii
  migrationBatch: yggdrasil-ii@2026-07-20
- timestamp: '2026-08-06T00:03:12Z'
  action: upstream_deprecated
  contributor: unknown
  details: 'Component mattpocock/caveman permanently removed (not frozen) from this
    suite: Author''s CHANGELOG: caveman was a duplicate of another skill being tested
    and was never meant to be public. No replacement. (Issue #1453)'
- timestamp: '2026-08-20T04:39:10Z'
  action: demote
  contributor: mbtiongson1
  details: Calibrated level from 4★ to 3★
- timestamp: '2026-08-20T04:52:58Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef=mattpocock/productivity, genericSkillRef=productivity via
    `gaia dev fuse`.
- timestamp: '2026-08-20T09:30:06Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 120.0 -> 180.0, grade A -> A (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
- timestamp: '2026-08-29T17:15:53Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 180.0 -> 0.0, grade A -> ungraded (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-09-06T09:52:45Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/mattpocock/skills (type: github-stars-own)'
- timestamp: '2026-09-06T09:52:47Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/mattpocock/skills (type: repo-own)'
- timestamp: '2026-09-06T09:52:57Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://www.aihero.dev/things-people-get-wrong-with-grill-me-and-grill-with-docs
    (type: peer-review)'
- timestamp: '2026-09-06T09:52:59Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://www.ai.joaoqueiros.com/blog/matt-pocock-ai-coding-skills-grill-spec-ticket-review
    (type: peer-review)'
- timestamp: '2026-09-06T09:53:12Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://ai.plainenglish.io/i-tested-matt-pococks-claude-code-skills-and-the-lesson-was-not-what-i-expected-9f2aceca59c6
    (type: peer-review)'
- timestamp: '2026-09-06T09:54:39Z'
  action: rank_up
  contributor: mbtiongson1
  details: Calibrated level from 3★ to 4★
- timestamp: '2026-09-06T10:04:18Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 0.0 -> 102.5, grade ungraded -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
suiteRef: mattpocock/skills
trustMagnitudeInputHash: ef557d2f98403a69c15d5b41ccdfe0b7f0c34e4383f68d81428a01a93af4c0dd
suiteComponents:
- mattpocock/grill-me
- mattpocock/handoff
- mattpocock/teach
- mattpocock/to-questionnaire
- mattpocock/wait-what
- mattpocock/write-a-skill
evidence:
- source: https://github.com/mattpocock/skills
  evaluator: mbtiongson1
  date: '2026-09-06'
  type: github-stars-own
  notes: 253k GitHub stars on mattpocock/skills — upstream repository for all productivity-suite
    components (grill-me, handoff, teach, to-questionnaire, wait-what, write-a-skill).
  stars: 253393
  sourceStartedAt: '2026-02-03'
  grade: A
- source: https://github.com/mattpocock/skills
  evaluator: mbtiongson1
  date: '2026-09-06'
  type: repo-own
  notes: 459 commits, 4 contributors. Productivity skills (grill-me, handoff, teach,
    write-a-skill, wait-what, to-questionnaire) are a primary category.
  commits: 459
  contributors: 4
  sourceStartedAt: '2026-02-03'
  grade: C
- source: https://www.aihero.dev/things-people-get-wrong-with-grill-me-and-grill-with-docs
  evaluator: mbtiongson1
  date: '2026-09-06'
  type: peer-review
  notes: Independent technical deep-dive on aihero.dev covering /grill-me failure
    modes — the core productivity workflow skill. Covers how grill-me integrates with
    handoff and prototype patterns. 1 independent author.
  reviewers: 1
  sourceStartedAt: '2026-05-01'
  grade: C
- source: https://www.ai.joaoqueiros.com/blog/matt-pocock-ai-coding-skills-grill-spec-ticket-review
  evaluator: mbtiongson1
  date: '2026-09-06'
  type: peer-review
  notes: Independent blog review covering the recommended default workflow — including
    grill-me, teach, writing-for-agents, and ask-matt as productivity orchestrators.
    1 independent reviewer.
  reviewers: 1
  sourceStartedAt: '2026-07-01'
  grade: C
- source: https://ai.plainenglish.io/i-tested-matt-pococks-claude-code-skills-and-the-lesson-was-not-what-i-expected-9f2aceca59c6
  evaluator: mbtiongson1
  date: '2026-09-06'
  type: peer-review
  notes: 'Independent 7-min Medium review (Plain English) explicitly evaluating the
    productivity workflow: handoffs, grilling, and agent context management skills.
    1 independent reviewer.'
  reviewers: 1
  sourceStartedAt: '2026-08-19'
  grade: C
verification:
  firstEvidenceAt: '2026-09-06T09:52:45Z'
---
## Overview

The Matt Pocock Productivity Suite bundles three skills that optimise the agent-developer feedback loop: Grill Me conducts a one-question-at-a-time design interview, substituting codebase exploration for empirically answerable questions; Handoff compacts the current conversation into a summary ready for a fresh agent context; and Write a Skill scaffolds new agent skills through a structured interview that produces a trigger-aware SKILL.md with progressive-disclosure layout. The suite covers the cognitive overhead of working with agents — prompt economy, design clarity, context continuity, and skill authoring.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.

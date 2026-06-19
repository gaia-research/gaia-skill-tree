---
id: addy-osmani/performance-optimization
name: Performance Optimization
contributor: addy-osmani
origin: true
genericSkillRef: performance-tuning
status: named
level: 3★
description: 'Measurement-driven performance workflow: baseline with Lighthouse and
  RUM, identify bottlenecks via profiling, fix targeted issues (N+1 queries, render
  blocking, unoptimized images), verify against Core Web Vitals thresholds (LCP ≤2.5s,
  INP ≤200ms, CLS ≤0.1), and guard against regression with perf budgets.'
createdAt: '2026-05-31'
updatedAt: '2026-06-19'
title: The Perf Loop
links:
  github: https://github.com/addyosmani/agent-skills/blob/main/skills/performance-optimization/SKILL.md
tags:
- performance
- core-web-vitals
- lighthouse
- profiling
- web-performance
timeline:
- timestamp: '2026-05-31T02:15:44Z'
  action: add
  contributor: unknown
  details: Added named skill addy-osmani/performance-optimization
- timestamp: '2026-05-31T02:16:53Z'
  action: installation_updated
  contributor: unknown
  details: 'Replaced ## Installation section from /tmp/perf_install.md'
- timestamp: '2026-06-02T01:43:00Z'
  action: rank_up
  contributor: unknown
  details: Origin status set to true.
- timestamp: '2026-06-14T12:32:16Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/addyosmani/agent-skills/blob/main/skills/performance-optimization/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:14Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T09:20:40Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/addyosmani/agent-skills (type:
    github-stars-own)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:29:08Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:34:46Z'
  details: TM 0.0 -> 47.2, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:25Z'
  details: TM 47.2 -> 83.2, grade C -> B (direct edit -- CLI gap)
evidence:
- class: A
  source: https://github.com/addyosmani/agent-skills/blob/main/skills/performance-optimization/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-31'
  notes: 'Addy Osmani''s performance-optimization SKILL.md in agent-skills repo (47.2k
    stars, verified 2026-05-31). Defines a measurement-driven 5-step workflow (Measure
    → Identify → Fix → Verify → Guard) with explicit Core Web Vitals thresholds. Qualifies
    for Class A per META §2.1 large-scale adoption criterion. (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 260
  contributors: 36
  trustNumber: 70.0
  grade: B
- source: https://github.com/addyosmani/agent-skills/stargazers
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: github-stars-own
  class: A
  notes: 47,200 GitHub stars as of 2026-06-19 (verified via firecrawl validation report;
    standalone skill)
  stars: 47200
trustMagnitude: 83.2
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
  firstEvidenceAt: '2026-06-19T09:20:40Z'
trustMagnitudeInputHash: 2d82c6ee5ac9e86e5dd3d1b4664385daf1eca3161cb78c89da2e4e2fd84b71ff
---

## Installation
Install via [gaia](https://github.com/mbtiongson1/gaia-skill-tree):

```bash
gaia skills install https://github.com/addyosmani/agent-skills/blob/main/skills/performance-optimization/SKILL.md
```

Or copy the raw skill file directly into your agent context:

```
https://github.com/addyosmani/agent-skills/blob/main/skills/performance-optimization/SKILL.md
```

**Usage**: Invoke `/performance-optimization` (Claude Code) to trigger the measurement-driven 5-step performance audit workflow.

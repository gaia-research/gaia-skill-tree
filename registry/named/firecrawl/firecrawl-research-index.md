---
id: firecrawl/firecrawl-research-index
name: Firecrawl Research Index
contributor: firecrawl
origin: false
genericSkillRef: literature-search
status: named
level: 5★
description: Retrieve and query academic literature through Firecrawl Research.
createdAt: '2026-07-13'
updatedAt: '2026-09-02'
title: Firecrawl Research Index
links:
  github: https://github.com/firecrawl/skills/blob/main/skills/firecrawl-research-index/SKILL.md
timeline:
- timestamp: '2026-07-13T06:22:18Z'
  action: add
  contributor: unknown
  details: Added named skill firecrawl/academic-literature-retrieval
- timestamp: '2026-07-13T06:22:37Z'
  action: suite_ref_set
  contributor: unknown
  details: Set suiteRef to firecrawl/firecrawl
- timestamp: '2026-07-13T09:08:48Z'
  action: note
  contributor: mbtiongson1
  details: Renamed from firecrawl/academic-literature-retrieval to firecrawl/firecrawl-research-index
    — aligned to official firecrawl/skills repo naming
- timestamp: '2026-07-30T22:15:52Z'
  action: evidence_removed
  contributor: marcotiongson
  details: 'Removed dead/invalid evidence: https://github.com/firecrawl/skills/blob/main/skills/firecrawl-research-index/SKILL.md'
- timestamp: '2026-07-30T22:15:52Z'
  action: evidence_added
  contributor: marcotiongson
  details: 'Added evidence from https://github.com/firecrawl/firecrawl/stargazers
    (type: github-stars-own)'
- timestamp: '2026-07-30T22:36:54Z'
  action: rank_up
  contributor: marcotiongson
  details: Calibrated level from 2★ to 3★
- timestamp: '2026-08-03T00:00:00Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added reported benchmark evidence from https://www.firecrawl.dev/blog/research-index-launch
    (type: benchmark-result)'
- timestamp: '2026-08-29T17:15:45Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 360.62, grade (none) -> S (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-09-02T15:11:16Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 3★ to 5★
evidence:
- type: repo-own
  source: https://github.com/firecrawl/firecrawl
  commits: 5714
  contributors: 155
  grade: B
  evaluator: mbtiongson1
  date: '2026-07-13'
  sourceStartedAt: '2023-08-01'
- source: https://github.com/firecrawl/firecrawl/stargazers
  updatedAt: '2026-09-01'
  evaluator: mbtiongson1
  date: '2026-07-31'
  type: github-stars-own
  stars: 175038
  skillCountInRepo: 6
  grade: B
- type: benchmark-result
  source: https://www.firecrawl.dev/blog/research-index-launch
  evaluator: mbtiongson1
  date: '2026-08-03'
  benchmarkId: alphaxiv-arxivqa@v1.0
  score: 53.3
  unit: pct
  provenance: reported
  attestor: https://www.firecrawl.dev/blog/research-index-launch
  notes: 'Firecrawl-reported ArXivQA recall: 53.3% at $0.32/task versus 45.4% next
    best; MRR 0.750.'
  grade: A
catalogRef: firecrawl-firecrawl-research-index
suiteRef: firecrawl/firecrawl-skills
verification:
  firstEvidenceAt: '2026-07-30T22:15:52Z'
trustMagnitude: 360.62
overallTrustGrade: S
trustMagnitudeInputHash: cbd1f3627d7b9ed26815bb23599913b120914ab3723634e8d282a8e84d24189b
---

## Installation
Add installation instructions here.

---
id: mattpocock/wayfinder
name: Wayfinder
contributor: mattpocock
origin: false
genericSkillRef: decision-ticket-planning
status: named
level: 2★
description: Plan a huge chunk of work (more than one agent session can hold) as a
  shared map of decision tickets on your issue tracker, and resolve them one at a
  time until the way to the destination is clear.
createdAt: '2026-08-20'
updatedAt: '2026-09-01'
title: The Decision Ticket Cartographer
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md
timeline:
- timestamp: '2026-08-19T16:10:19Z'
  action: add
  contributor: marco-tngsn
  details: Added named skill mattpocock/wayfinder
- timestamp: '2026-08-19T16:10:33Z'
  action: evidence_added
  contributor: marco-tngsn
  details: 'Added evidence from https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md
    (type: repo-own)'
- timestamp: '2026-08-20T04:55:13Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to mattpocock/engineering
- timestamp: '2026-08-29T17:15:54Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 20.77, grade (none) -> C (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-09-01T19:08:39Z'
  action: installation_updated
  contributor: mbtiongson1
  details: 'Filled in the placeholder Installation section (Gaia tracker-document setup)'
evidence:
- source: https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md
  evaluator: marco-tngsn
  date: '2026-08-20'
  type: repo-own
  notes: Confirmed-promoted skill in mattpocock/skills engineering bucket per upstream
    v1.2.3 taxonomy. Shared-repo metrics (523 commits, 4 contributors, MIT license)
    per Stage-1 collection 2026-08-19.
  commits: 523
  contributors: 4
  grade: C
verification:
  firstEvidenceAt: '2026-08-19T16:10:33Z'
suiteRef: mattpocock/engineering
trustMagnitude: 20.77
overallTrustGrade: C
trustMagnitudeInputHash: 93bd0e91667a5d4a00d86b8402add7c8824342cd7d80226d53827db026d275a3
---

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

### Gaia-specific setup — required

Wayfinder is deliberately tracker-agnostic: it defers the mechanics of maps, child tickets, blocking, and the frontier query to a per-repo tracker document. Installing the upstream file alone leaves those undefined.

The Gaia expression of that document ships in this repo as `.agents/skills/wayfinder/SKILL.md` (mirrored to `.claude/skills/wayfinder/`). It pins down:

- **Headquarters** — every map and every ticket lives on the `gaia-research/gaia-skill-tree` tracker, regardless of which repo the resulting code lands in, with a `**Target repo:**` line tagging where the work goes.
- **Hierarchy** — GitHub native sub-issues, attached by issue *id*, not number.
- **Blocking** — a `**Blocked by:** #n, #m` body convention, because neither `gh` nor the GitHub MCP toolset exposes a usable native dependency edge here.
- **The frontier query, claiming, and resolution recording.**

Reference implementation: [Wayfinder map: Trust Magnitude recalibration backlog (post-Yggdrasil III)](https://github.com/gaia-research/gaia-skill-tree/issues/1636) — 6 sub-issues, 6/6 closed.

The `wayfinder:map`, `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling`, and `wayfinder:task` labels are declared in `.github/labels.yml` and must stay declared — `labels-sync.yml` deletes undeclared labels off live issues.

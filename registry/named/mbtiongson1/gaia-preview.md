---
id: mbtiongson1/gaia-preview
name: Gaia Preview
contributor: mbtiongson1
origin: false
genericSkillRef: deployment-automation
status: named
level: 2★
description: Generates a preview render of proposed registry changes — showing how
  new or modified skill entries will appear on the profile page and in the skill graph
  before the PR is merged.
createdAt: '2026-05-27'
updatedAt: '2026-06-14'
title: The Change Previewer
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-preview/SKILL.md
tags:
- registry-curation
- preview
- staging
timeline:
- timestamp: '2026-05-26T16:37:01Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-preview
- timestamp: '2026-06-10T05:38:17Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-preview/SKILL.md
- timestamp: '2026-06-14T12:32:45Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-preview/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
evidence:
- class: B
  source: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-preview/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: Project-local agent skill driving branch preview deploys via sync-artifacts.yml;
    implementation public at SKILL.md. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
trustMagnitude: 0.0
overallTrustGrade: ungraded
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 3a5d74bb37e0f4fad2bcae34b2209fb45472f4bd11f941075a5caab34c618eeb
verification:
  firstEvidenceAt: '2026-06-10T05:38:17Z'
---

## Overview

Triggers a remote documentation regeneration and Cloudflare deployment for the current branch via `gh workflow run sync-artifacts.yml -f deploy=true`. Preferred for design previews when working in containerized environments where `localhost` is not available. Zero local footprint, consistent canonical build environment, automatic deployment.

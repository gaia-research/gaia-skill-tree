---
id: vercel/find-skills
name: Find Skills
contributor: vercel
origin: true
genericSkillRef: skill-discovery
status: named
title: The Registry Scout
catalogRef: vercel-find-skills
level: 2★
description: Searches the skills.sh registry by keyword or category, queries install
  counts to surface popular skills, and auto-installs the selected skill into the
  current project's skills directory.
links:
  github: https://github.com/vercel-labs/skills/blob/main/skills/find-skills/SKILL.md
tags:
- skill-registry
- discovery
- skills-sh
- auto-install
createdAt: '2026-04-30'
updatedAt: '2026-06-14'
evidence:
- class: B
  source: https://github.com/vercel-labs/skills/blob/main/skills/find-skills/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: Vercel /find-skills slash command -- queries the skills.sh registry, checks
    install counts, and auto-installs matching skills. (backfilled — class-to-type
    migration) (CLI gap: --commits/--contributors not supported by gaia dev evidence)
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 330
  contributors: 102
timeline:
- timestamp: '2026-06-14T12:33:03Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/vercel-labs/skills/blob/main/skills/find-skills/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:21Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
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
trustMagnitudeInputHash: ed2fea85251c76fa7de44219179ac06726c163f4775ff2821d1e12faa2c13082
---

## Overview

Find Skills is a registry-aware discovery tool published by Vercel Labs. The agent queries the skills.sh registry, filters results by the user's keyword, ranks candidates by install count, and installs the chosen skill with a single command. It eliminates the need for manual browsing of skill repositories.

## Origin

First published by @vercel (Vercel Labs). This is the origin implementation for the `skill-discovery` skill bucket.

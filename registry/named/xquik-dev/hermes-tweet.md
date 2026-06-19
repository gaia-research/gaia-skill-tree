---
id: xquik-dev/hermes-tweet
name: Hermes Tweet
contributor: xquik-dev
origin: true
genericSkillRef: x-twitter-automation
status: awakened
level: 4★
description: Installable Hermes Agent skill and plugin for X/Twitter search, reply
  reading, user lookup, monitoring, follower export, and approval-gated write actions.
links:
  github: https://github.com/Xquik-dev/hermes-tweet/blob/master/skills/hermes-tweet/SKILL.md
  docs: https://docs.xquik.com/guides/hermes-tweet
tags:
- x-twitter
- twitter
- social-automation
- hermes-agent
- monitoring
createdAt: '2026-05-15'
updatedAt: '2026-06-14'
evidence:
- class: B
  source: https://github.com/Xquik-dev/hermes-tweet
  evaluator: kriptoburak
  date: '2026-05-15'
  notes: 'Hermes Tweet provides an installable Hermes Agent X/Twitter skill and plugin
    for searching tweets, reading replies, looking up users, monitoring tweets, exporting
    followers, and gating post, reply, and DM actions. (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 439
  contributors: 2
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-14T12:33:03Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/Xquik-dev/hermes-tweet as B
    (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:21Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 6.12, grade ungraded -> ungraded (direct edit -- CLI gap)
trustMagnitude: 6.12
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
trustMagnitudeInputHash: 487dda9ad1b68b4569a83c8caaf6a10c465273d22fb4625ead283e7af75e6ab3
---

## Overview

Hermes Tweet gives Hermes Agent workflows a reusable X/Twitter automation route for searching tweets, reading replies, looking up users, monitoring tweets, exporting followers, and gating post, reply, or DM actions behind explicit approval.

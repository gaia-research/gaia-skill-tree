---
id: garrytan/remote-mcp
name: remote-mcp
contributor: garrytan
origin: false
genericSkillRef: mcp-server-deployment
status: named
level: 2★
description: 'Publish the user''s own gbrain over MCP so other devices, desktop apps
  and

  cloud agents can reach it. `gbrain mcp expose` installs and signs in

  Tailscale, publishes the running `gbrain serve --http` on the tailnet

  (HTTPS, tailnet-only by default; Funnel only when a client lives in a

  vendor cloud), keeps the server alive as a user service, and hands back the

  MCP URL. Then grant one least-privilege client per consumer, install the

  handoff inside that client, and verify a real memory round trip.'
createdAt: '2026-09-23'
updatedAt: '2026-10-30'
title: remote-mcp
links:
  github: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/remote-mcp/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:12Z'
  action: add
  contributor: unknown
  details: Added named skill garrytan/remote-mcp
- timestamp: '2026-10-29T16:55:42Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/remote-mcp/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:55:43Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain (type: repo-own)'
- timestamp: '2026-10-29T16:56:48Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 158.36, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-10-30T13:15:26Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-10-30T13:15:28Z'
  action: note
  contributor: mbtiongson1
  details: 'Founder ruling 2026-10-30 (FD-7 suite linking is automatic; sibling cap
    unchanged, audit filed as #2263) and audit correction C1 of PR #2251: suiteRef
    garrytan/gbrain set. Upstream path is inside the suite repo: garrytan/gbrain/blob/v0.51.6.0/plugin/skills/remote-mcp/SKILL.md.'
- timestamp: '2026-10-30T13:17:39Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 158.36 -> 50.0, grade A -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/remote-mcp/SKILL.md
  evaluator: mbtiongson1
  date: '2026-10-29'
  type: github-stars-own
  notes: 'GitHub REST stargazers_count of garrytan/gbrain at 2026-10-29 (host suite
    repo); skill-file blob link verified HTTP 200 at its pinned ref. Founder ruling
    2026-10-30 FD-7: skill was added at intake (2026-09-23) with no evidence rows.'
  stars: 31330
  skillCountInRepo: 71
  sourceStartedAt: '2026-04-05'
  grade: A
- source: https://github.com/garrytan/gbrain
  evaluator: mbtiongson1
  date: '2026-10-29'
  type: repo-own
  notes: GitHub REST default-branch commit count and contributor count of garrytan/gbrain
    at 2026-10-29; host-repository maintenance, not independent quality evidence.
    Founder ruling 2026-10-30 FD-7.
  commits: 11443
  contributors: 136
  sourceStartedAt: '2026-04-05'
  grade: B
verification:
  firstEvidenceAt: '2026-10-29T16:55:42Z'
trustMagnitude: 50.0
overallTrustGrade: B
trustMagnitudeInputHash: 2e8b0347381c974d03e83722723dddac262c95023ca1a2c2d051f9ebdfb377c6
suiteRef: garrytan/gbrain
---

## Installation
Add installation instructions here.

---
id: intelligentcode-ai/mcp-client
name: MCP Client
contributor: intelligentcode-ai
origin: false
links:
  github: https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-client/SKILL.md
genericSkillRef: mcp-integration
status: named
title: The Protocol Bridge
level: 1★
description: Portable CLI tool that connects to MCP servers on-demand, enumerates
  available tools, displays them, and executes calls — works with any MCP-compatible
  backend without platform lock-in.
tags:
- mcp
- model-context-protocol
- tool-integration
- cli
updatedAt: '2026-06-20'
evidence:
- class: C
  source: https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-client/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: intelligentcode-ai/skills — practical coding agent skills; mcp-client provides
    production-ready implementation (trust updated from C=50 to B-equiv=65)
  type: repo
  trustNumber: 65.0
  grade: B
  commits: 34
  contributors: 1
- source: https://github.com/intelligentcode-ai/skills
  evaluator: unknown
  date: '2026-06-20'
  type: self-attestation
  trustNumber: 60.0
  grade: B
  notes: intelligentcode-ai/skills suite self-attested via README description; practical
    agent skill for mcp-client domain
  sourceStartedAt: '2025-01-01'
timeline:
- timestamp: '2026-06-14T12:32:41Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-client/SKILL.md
    as C (trustNumber: 50.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:17Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 1.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 1.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:40Z'
  details: TM 0.0 -> 1.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T17:10:10Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-client/SKILL.md
    as B (trustNumber: 65.0)'
- timestamp: '2026-06-19T17:10:45Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/intelligentcode-ai/skills (type:
    self-attestation)'
- timestamp: '2026-06-19T17:10:45Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/intelligentcode-ai/skills as B
    (trustNumber: 60.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:02Z'
  details: TM 1.3 -> 6.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:28Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 2★ to 1★ per G7 final rankings calibration.
trustMagnitude: 6.3
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
trustMagnitudeInputHash: d0cad627c1f98aa52862ce55655dd2cc2410da700991c68b04a8c1402f1e4af3
verification:
  firstEvidenceAt: '2026-06-19T17:10:45Z'
---

## Overview

A universal MCP client that treats server connections as ephemeral: connect, list tools, call, disconnect. Designed for use inside agent loops where the set of available MCP servers may change between turns.

## Key behaviours

- Enumerates all tools exposed by a target MCP server at connection time
- Executes tool calls with structured arguments and returns typed responses
- Handles multi-server routing — each call specifies the server by name or URL
- Authentication is handled via environment variables; no credentials in prompts

## Source

[intelligentcode-ai/skills — mcp-client/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-client/SKILL.md)

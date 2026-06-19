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
level: 2★
description: Portable CLI tool that connects to MCP servers on-demand, enumerates
  available tools, displays them, and executes calls — works with any MCP-compatible
  backend without platform lock-in.
tags:
- mcp
- model-context-protocol
- tool-integration
- cli
updatedAt: '2026-06-14'
evidence:
- class: C
  source: https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-client/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: 'intelligentcode-ai/skills mcp-client — portable CLI MCP client with server"
    enumeration, tool display, and on-demand execution. (backfilled — class-to-type
    migration) (CLI gap: --commits/--contributors not supported by gaia dev evidence)'
  type: repo
  trustNumber: 50.0
  grade: C
  commits: 34
  contributors: 1
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

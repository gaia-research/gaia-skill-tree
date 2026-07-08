---
id: obra/superpowers
name: Superpowers
contributor: obra
origin: true
genericSkillRef: superpowers
status: named
title: The Complete Agentic Discipline
level: 5★
description: A complete software development methodology for coding agents — brainstorming,
  planning, parallel execution, systematic debugging, code review loops, and branch
  discipline unified into a single agentic workflow.
links:
  github: https://github.com/obra/superpowers
tags:
- ultimate
- methodology
- agentic-workflow
- discipline
- multi-skill
createdAt: '2026-05-18'
updatedAt: '2026-06-21'
suiteComponents:
- obra/brainstorming
- obra/dispatching-parallel-agents
- obra/executing-plans
- obra/finishing-a-development-branch
- obra/receiving-code-review
- obra/requesting-code-review
- obra/subagent-driven-development
- obra/systematic-debugging
- obra/using-git-worktrees
- obra/verification-before-completion
- obra/writing-plans
evidence:
- class: B
  source: https://github.com/obra/superpowers
  evaluator: mbtiongson1
  date: '2026-05-18'
  notes: 'obra/superpowers v5.1.0 — 196k+ GitHub stars, 17.5k forks, multi-platform
    adoption (Claude Code, Codex CLI, Factory Droid, Gemini CLI, OpenCode, Cursor,
    GitHub Copilot CLI). Most widely adopted AI agent discipline framework; confirms
    landmark methodology status. (backfilled — class-to-type migration) commits+contributors
    patched 2026-06-19 via obra/superpowers repo (CLI gap: no --commits flag on gaia
    dev evidence)'
  type: repo
  commits: 609
  contributors: 36
  trustNumber: 70.0
  grade: B
- source: https://github.com/obra/superpowers/stargazers
  evaluator: mbtiongson1
  updatedAt: '2026-07-01'
  date: '2026-06-19'
  type: github-stars-own
  class: A
  notes: 230,818 GitHub stars as of 2026-06-19 (verified via firecrawl validation
    report; mothership with 11+ sub-skills, divisor=4)
  stars: 243025
  skillCountInRepo: 11
  grade: B
- source: https://www.youtube.com/watch?v=6YltXh12W-g
  evaluator: unknown
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: 'Larridin podcast: ''Superpowers: How Jesse Built the #1 AI Claude Code/Codex
    Plugin''. Jesse Vincent explains obra/superpowers agentic discipline. 4,402 views
    (firecrawl verified 2026-06-19).'
  views: 4402
  grade: B
timeline:
- timestamp: '2026-06-14T12:32:48Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/obra/superpowers as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T09:17:53Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers (type: github-stars-own)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:29:08Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:34:47Z'
  details: TM 0.0 -> 50.0, grade ungraded -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 50.0 -> 50.0, grade B -> B (direct edit -- CLI gap)
- timestamp: '2026-06-19T10:46:09Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=gT5R01Z2J-0 (type:
    social-signal)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:52:25Z'
  details: TM 50.0 -> 86.0, grade B -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 86.0, grade ungraded -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:43Z'
  details: TM 0.0 -> 416.0, grade ungraded -> S (direct edit -- CLI gap)
- timestamp: '2026-06-19T14:25:32Z'
  action: evidence_removed
  contributor: unknown
  details: 'Removed dead/invalid evidence: https://www.youtube.com/watch?v=gT5R01Z2J-0'
- timestamp: '2026-06-19T14:25:41Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=6YltXh12W-g (type:
    social-signal)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T14:31:47Z'
  details: TM 416.0 -> 445.15, grade S -> S (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T14:32:19Z'
  details: TM 445.15 -> 445.15, grade S -> S (direct edit -- CLI gap)
- timestamp: '2026-06-19T16:27:40Z'
  action: verified
  contributor: unknown
  details: 'Apex promotion PR stamped by Marco (founder/mbtiongson1) per #746 directive
    — superpowers qualifies for §11.12.8 (apexPromotionPrSigned)'
- timestamp: '2026-07-08T19:56:27Z'
  action: upstream_synced
  contributor: github-actions[bot]
  previousValue: null
  newValue: v6.1.1
  details: first-run baseline
trustMagnitude: 445.15
overallTrustGrade: S
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: true
  apexPromotionPrSigned: true
  apexPromotionPrSignedBy: mbtiongson1
  apexPromotionPrSignedAt: '2026-06-20'
  crossOrgVerifier: null
  systemWideCap: null
verification:
  firstEvidenceAt: '2026-06-19T09:17:53Z'
trustMagnitudeInputHash: 2d67b35c36b1d3e307febe93181725bf1ac72fc1f25555849b9517d275189606
upstream:
  mode: components
  releasedAt: '2026-07-02T21:58:30Z'
  repo: obra/superpowers
  sourceUrl: https://github.com/obra/superpowers/releases/tag/v6.1.1
  syncedAt: '2026-07-08T19:56:27Z'
  version: v6.1.1
---

## Overview

Superpowers by @obra is the fusion of all 11 obra discipline skills into a unified agentic development methodology. Rather than applying individual practices in isolation, an agent with this skill runs the full loop: collaborative brainstorming, written plans, parallel subagent dispatch, systematic debugging, explicit code review cycles, and clean branch discipline — every time, on every task.

## Origin

First published by @obra as the obra/superpowers skill library. This is the origin implementation for the `superpowers` ultimate skill. The repository has accumulated 196k+ GitHub stars and 17.5k forks across multi-platform adoption (Claude Code, Codex CLI, Factory Droid, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI), confirming it as the most widely adopted AI agent discipline framework.

## Installation

Installation differs by harness. If you use more than one, install Superpowers separately for each one.

### Claude Code

Superpowers is available via the [official Claude plugin marketplace](https://claude.com/plugins/superpowers)

#### Official Marketplace

- Install the plugin from Anthropic's official marketplace:

  ```bash
  /plugin install superpowers@claude-plugins-official
  ```bash
#### Superpowers Marketplace

The Superpowers marketplace provides Superpowers and some other related plugins for Claude Code.

- Register the marketplace:

  ```bash
  /plugin marketplace add obra/superpowers-marketplace
  ```

- Install the plugin from this marketplace:

  ```bash
  /plugin install superpowers@superpowers-marketplace
  ```

### Antigravity

Install Superpowers as a plugin from this repository:

```bash
agy plugin install https://github.com/obra/superpowers
```bash
Antigravity runs the plugin's session-start hook, so Superpowers is active from
the first message. Reinstall with the same command to update.

### Codex App

Superpowers is available via the [official Codex plugin marketplace](https://github.com/openai/plugins).

- In the Codex app, click on Plugins in the sidebar.
- You should see `Superpowers` in the Coding section.
- Click the `+` next to Superpowers and follow the prompts.

### Codex CLI

Superpowers is available via the [official Codex plugin marketplace](https://github.com/openai/plugins).

- Open the plugin search interface:

  ```bash
  /plugins
  ```

- Search for Superpowers:

  ```bash
  superpowers
  ```

- Select `Install Plugin`.

### Cursor

- In Cursor Agent chat, install from marketplace:

  ```bash
  /add-plugin superpowers
  ```

- Or search for "superpowers" in the plugin marketplace.

### Factory Droid

- Register the marketplace:

  ```bash
  droid plugin marketplace add https://github.com/obra/superpowers
  ```

- Install the plugin:

  ```bash
  droid plugin install superpowers@superpowers
  ```

### GitHub Copilot CLI

- Register the marketplace:

  ```bash
  copilot plugin marketplace add obra/superpowers-marketplace
  ```

- Install the plugin:

  ```bash
  copilot plugin install superpowers@superpowers-marketplace
  ```

### Kimi Code

Superpowers is available in Kimi Code's plugin marketplace.

- Open Kimi Code's plugin manager:

  ```bash
  /plugins
  ```

- Go to `Marketplace` > `Superpowers` and install it.

- Or install directly from this repository:

  ```bash
  /plugins install https://github.com/obra/superpowers
  ```

- Detailed docs: [docs/README.kimi.md](docs/README.kimi.md)

### OpenCode

OpenCode uses its own plugin install; install Superpowers separately even if you
already use it in another harness.

- Tell OpenCode:

  ```
  Fetch and follow instructions from https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.opencode/INSTALL.md
  ```

- Detailed docs: [docs/README.opencode.md](docs/README.opencode.md)

### Pi

Install Superpowers as a Pi package from this repository:

```bash
pi install git:github.com/obra/superpowers
```bash
For local development, run Pi with this checkout loaded as a temporary package:

```bash
pi -e /path/to/superpowers
```

The Pi package loads the Superpowers skills and a small extension that injects the `using-superpowers` bootstrap at session startup and again after compaction. Pi has native skills, so no compatibility `Skill` tool is required. Subagent and task-list tools remain optional Pi companion packages.

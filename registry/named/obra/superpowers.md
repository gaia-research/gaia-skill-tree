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
updatedAt: '2026-05-19'
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
  notes: obra/superpowers v5.1.0 — 196k+ GitHub stars, 17.5k forks, multi-platform
    adoption (Claude Code, Codex CLI, Factory Droid, Gemini CLI, OpenCode, Cursor,
    GitHub Copilot CLI). Most widely adopted AI agent discipline framework; confirms
    landmark methodology status.
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
  ```

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

### Codex App

Superpowers is available via the [official Codex plugin marketplace](https://github.com/openai/plugins).

- In the Codex app, click on Plugins in the sidebar.
- You should see `Superpowers` in the Coding section.
- Click the `+` next to Superpowers and follow the prompts.

### Factory Droid

- Register the marketplace:

  ```bash
  droid plugin marketplace add https://github.com/obra/superpowers
  ```

- Install the plugin:

  ```bash
  droid plugin install superpowers@superpowers
  ```

### Gemini CLI

- Install the extension:

  ```bash
  gemini extensions install https://github.com/obra/superpowers
  ```

- Update later:

  ```bash
  gemini extensions update superpowers
  ```

### OpenCode

OpenCode uses its own plugin install; install Superpowers separately even if you
already use it in another harness.

- Tell OpenCode:

  ```
  Fetch and follow instructions from https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.opencode/INSTALL.md
  ```

- Detailed docs: [docs/README.opencode.md](docs/README.opencode.md)

### Cursor

- In Cursor Agent chat, install from marketplace:

  ```bash
  /add-plugin superpowers
  ```

- Or search for "superpowers" in the plugin marketplace.

### GitHub Copilot CLI

- Register the marketplace:

  ```bash
  copilot plugin marketplace add obra/superpowers-marketplace
  ```

- Install the plugin:

  ```bash
  copilot plugin install superpowers@superpowers-marketplace
  ```

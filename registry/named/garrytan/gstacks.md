---
id: garrytan/gstacks
name: Founder Mode
contributor: garrytan
origin: true
genericSkillRef: gstack
status: named
title: "Gstack — Garry Tan's Full-Stack Agent Suite"
catalogRef: garrytan-gstacks
level: "5★"
description: The legendary fusion of Garry Tan's complete agent discipline library — browser QA, security auditing, design exploration, vertical-slice planning, and founder-mode orchestration — unified into a single autonomous product-development workflow.
links:
  github: https://github.com/garrytan/gstack
tags:
  - founder-mode
  - full-stack
  - browser-automation
  - security-audit
  - design-exploration
  - orchestration
  - ultimate
createdAt: "2026-05-18"
updatedAt: "2026-05-18"
---

## Overview

Gstacks is the ultimate node fusing all five Garry Tan discipline skills into an end-to-end autonomous product studio: from ideation and design through QA, security hardening, and strategic founder-mode review.

## Component Skills

| Skill | Named Title | Level |
|---|---|---|
| browser-automation | Gstack Browser Engine | 4★ |
| security-audit | Chief Security Officer Mode | 4★ |
| design-review | Design Shotgun | 4★ |
| vertical-slice-planning | Founder Mode Autoplan | 5★ |
| question-answer | YC Office Hours | 4★ |

## Installation

**30-second install** — Requirements: Claude Code, Git, Bun v1.0+, Node.js (Windows only)

### Step 1: Install on your machine

Open Claude Code and paste this. Claude does the rest.

```
Install gstack: run git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup then add a "gstack" section to CLAUDE.md that says to use the /browse skill from gstack for all web browsing, never use mcp__claude-in-chrome__* tools, and lists the available skills: /office-hours, /plan-ceo-review, /plan-eng-review, /plan-design-review, /design-consultation, /design-shotgun, /design-html, /review, /ship, /land-and-deploy, /canary, /benchmark, /browse, /connect-chrome, /qa, /qa-only, /design-review, /setup-browser-cookies, /setup-deploy, /setup-gbrain, /retro, /investigate, /document-release, /document-generate, /codex, /cso, /autoplan, /plan-devex-review, /devex-review, /careful, /freeze, /guard, /unfreeze, /gstack-upgrade, /learn. Then ask the user if they also want to add gstack to the current project so teammates get it.
```

### Step 2: Team mode — auto-update for shared repos (recommended)

From inside your repo, paste this. Switches you to team mode, bootstraps the repo so teammates get gstack automatically, and commits the change:

```
(cd ~/.claude/skills/gstack && ./setup --team) && ~/.claude/skills/gstack/bin/gstack-team-init required && git add .claude/ CLAUDE.md && git commit -m "require gstack for AI-assisted work"
```

No vendored files in your repo, no version drift, no manual upgrades. Every Claude Code session starts with a fast auto-update check (throttled to once/hour, network-failure-safe, completely silent).

Swap `required` for `optional` if you'd rather nudge teammates than block them.

## OpenClaw

OpenClaw spawns Claude Code sessions via ACP, so every gstack skill just works when Claude Code has gstack installed. Paste this to your OpenClaw agent:

```
Install gstack: run git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup to install gstack for Claude Code. Then add a "Coding Tasks" section to AGENTS.md that says: when spawning Claude Code sessions for coding work, tell the session to use gstack skills. Include these examples — security audit: "Load gstack. Run /cso", code review: "Load gstack. Run /review", QA test a URL: "Load gstack. Run /qa https://...", build a feature end-to-end: "Load gstack. Run /autoplan, implement the plan, then run /ship", plan before building: "Load gstack. Run /office-hours then /autoplan. Save the plan, don't implement."
```

## Native OpenClaw Skills

Four methodology skills that work directly in your OpenClaw agent, no Claude Code session needed. Install from ClawHub:

```
clawhub install gstack-openclaw-office-hours gstack-openclaw-ceo-review gstack-openclaw-investigate gstack-openclaw-retro
```

| Skill | What it does |
|---|---|
| gstack-openclaw-office-hours | Product interrogation with 6 forcing questions |
| gstack-openclaw-ceo-review | Strategic challenge with 4 scope modes |
| gstack-openclaw-investigate | Root cause debugging methodology |
| gstack-openclaw-retro | Weekly engineering retrospective |

## Other AI Agents

gstack works on 10 AI coding agents, not just Claude. Setup auto-detects which agents you have installed:

```
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/gstack
cd ~/gstack && ./setup
```

Or target a specific agent with `./setup --host <name>`:

| Agent | Flag | Skills install to |
|---|---|---|
| OpenAI Codex CLI | --host codex | ~/.codex/skills/gstack-*/ |
| OpenCode | --host opencode | ~/.config/opencode/skills/gstack-*/ |
| Cursor | --host cursor | ~/.cursor/skills/gstack-*/ |
| Factory Droid | --host factory | ~/.factory/skills/gstack-*/ |
| Slate | --host slate | ~/.slate/skills/gstack-*/ |
| Kiro | --host kiro | ~/.kiro/skills/gstack-*/ |
| Hermes | --host hermes | ~/.hermes/skills/gstack-*/ |
| GBrain (mod) | --host gbrain | ~/.gbrain/skills/gstack-*/ |

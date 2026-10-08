---
id: hikari9/auto-office
name: Auto Office
contributor: hikari9
origin: false
genericSkillRef: autonomous-engineering-platform
status: named
level: 3★
description: Adaptive office engineering runtime for the complete lifecycle from intent
  through planning, routed execution, independent review, verification, and closeout,
  driven through one `office` CLI. Use when explicitly invoked as /auto-office or
  when the user directly asks to run an Auto Office lifecycle. Routes each role by
  harness, model, and effort under pinned policy, trust and capability floors, and
  live quota; the runtime owns state, receipts, evidence, and review mechanics. Preserves
  human merge-to-main unless the user chose merge or end-to-end at intake, no-self-approval,
  private evidence, and version-pinned runs.
createdAt: '2026-10-09'
updatedAt: '2026-10-09'
title: Auto Office
links:
  github: https://github.com/Hikari9/auto-office/blob/da6aa9a93dbab98c03d2fbb3593f994acf85d7a7/SKILL.md
attribution:
  upstream_author: Hikari9
  skill_file_url: https://github.com/Hikari9/auto-office/blob/da6aa9a93dbab98c03d2fbb3593f994acf85d7a7/SKILL.md
  type: self-made
timeline:
- timestamp: '2026-10-08T21:36:11Z'
  action: add
  contributor: unknown
  details: Added named skill hikari9/auto-office
- timestamp: '2026-10-08T21:36:14Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/Hikari9/auto-office/blob/da6aa9a93dbab98c03d2fbb3593f994acf85d7a7/SKILL.md
    (type: repo-own)'
- timestamp: '2026-10-08T21:36:16Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/Hikari9/auto-office (type: github-stars-own)'
- timestamp: '2026-10-08T21:36:34Z'
  action: suite_ref_set
  contributor: unknown
  details: 'Updated via `gaia dev fuse`: suiteRef=hikari9/auto-office, suiteComponents+=[''hikari9/office-submit''].'
- timestamp: '2026-10-08T21:36:52Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 1★ to 3★
- timestamp: '2026-10-08T21:37:21Z'
  action: installation_updated
  contributor: unknown
  details: 'Replaced ## Installation section from generated-output/2054-installation.md'
- timestamp: '2026-10-08T21:47:57Z'
  action: installation_updated
  contributor: unknown
  details: 'Replaced ## Installation section from generated-output/2054-installation.md'
- timestamp: '2026-10-09T07:00:00Z'
  action: installation_updated
  contributor: unknown
  details: Added structured custom installation instructions with multi-harness tabs and worktree configuration
evidence:
- source: https://github.com/Hikari9/auto-office/blob/da6aa9a93dbab98c03d2fbb3593f994acf85d7a7/SKILL.md
  evaluator: unknown
  date: '2026-10-08'
  type: repo-own
  notes: Whole runtime repository baseline at pinned HEAD da6aa9a93dbab98c03d2fbb3593f994acf85d7a7;
    metrics enumerate whole repository, not this SKILL.md alone. See receipts/head.json,
    commit-shas.txt, contributors.json.
  commits: 826
  contributors: 4
  skillCountInRepo: 21
  sourceStartedAt: '2026-10-08'
  grade: C
- source: https://github.com/Hikari9/auto-office
  evaluator: unknown
  date: '2026-10-08'
  type: github-stars-own
  notes: Observed GitHub API stargazers_count. Shared repository baseline across 21
    skills; not independent per-component adoption.
  stars: 1
  skillCountInRepo: 21
  sourceStartedAt: '2026-10-08'
verification:
  firstEvidenceAt: '2026-10-08T21:36:14Z'
suiteComponents:
- hikari9/office-submit
---

## Installation

Auto Office uses its own runtime installer rather than a standalone SKILL.md copy. Install from upstream using either `uv` or `pipx`, or as an agent plugin.

### Step 1: Install the CLI

For normal use:

```bash
uv tool install git+https://github.com/Hikari9/auto-office.git
```

For browser capture and visual gates:

```bash
uv tool install 'git+https://github.com/Hikari9/auto-office.git#egg=auto-office[visual]'
```

Alternatively, install using `pipx`:

```bash
pipx install git+https://github.com/Hikari9/auto-office.git
```

### Plugin Marketplace

This repository is a plugin marketplace for both Claude Code and Codex / ChatGPT:

```bash
# Claude Code
claude plugin marketplace add Hikari9/auto-office
claude plugin install auto-office@auto-office

# Codex / ChatGPT desktop
codex plugin marketplace add Hikari9/auto-office
```

Enable `auto-office` from the Codex plugin directory. Claude reads `.claude-plugin/marketplace.json`; Codex reads `.agents/plugins/marketplace.json` and the root `plugin.json`.

### Harness Integrations

Register the runtime and agent integrations:

```bash
office install
office doctor
```

`office install` is idempotent. It registers the current runtime and installs the harness integrations that Auto Office can verify safely. Existing configuration is backed up before Office-managed entries are changed.

| Agent / harness | After office install |
|---|---|
| Claude Code | Installs managed SessionStart, UserPromptSubmit, and PreToolUse hooks in ~/.claude/settings.json |
| Gemini CLI | Installs managed SessionStart, BeforeAgent, and BeforeTool hooks in ~/.gemini/settings.json |
| Codex | No config is written; explicit office commands are the contract |
| agy / Antigravity | Explicit office commands and status |
| Hermes | Explicit office commands |
| Herdr | Dispatches open real agent panes and Office tracks/reclaims them |

### Operating Rule

Every normal CLI result ends with a `next:` line declaring the next legal action:

1. Run `office --version` and `office doctor` when bootstrapping a machine/session.
2. Use `office start` or `office resume` rather than inventing lifecycle state.
3. Follow `next:` instead of editing Office state directly.
4. Never edit `runs.db`, generated run views, receipts, or telemetry by hand.
5. Submit plans and implementation through `office submit`.
6. Let the runtime dispatch reviewers and evaluate acceptance.

### Worktree Configuration

Office creates fresh task, integration, and check worktrees. If tests need dependencies, declare the setup command in `.auto-office/config.yaml`:

```yaml
worktree:
  setup: "uv sync --frozen"
  setup_inputs:
    - pyproject.toml
    - uv.lock
  setup_timeout_s: 600
  applies_to: [task, integration, check]
```

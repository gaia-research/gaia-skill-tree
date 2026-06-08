---
id: ruvnet/ruflo
name: Ruflo
contributor: ruvnet
origin: true
genericSkillRef: multi-topology-orchestration
status: named
title: The Agentic Sovereign
catalogRef: ruvnet-ruflo
level: 6★
description: 'The complete Ruflo orchestration platform: flow nexus, AgentDB memory
  sovereignty, GitHub operations, hive-mind consensus, reasoning bank, and v3 modernization
  — unified at 6★ apex.'
links:
  github: https://github.com/ruvnet/ruflo
tags:
- ruflo
- apex
- ultimate
- orchestration
- multi-agent
- platform
createdAt: '2026-05-19'
updatedAt: '2026-05-19'
suiteComponents:
- ruvnet/agentdb
- ruvnet/agentdb-advanced
- ruvnet/agentdb-learning
- ruvnet/agentdb-memory-patterns
- ruvnet/agentdb-optimization
- ruvnet/agentdb-vector-search
- ruvnet/agentic-jujutsu
- ruvnet/browser
- ruvnet/dual-collect
- ruvnet/dual-coordinate
- ruvnet/dual-mode
- ruvnet/dual-spawn
- ruvnet/flow-nexus
- ruvnet/flow-nexus-neural
- ruvnet/flow-nexus-platform
- ruvnet/flow-nexus-swarm
- ruvnet/github-code-review
- ruvnet/github-multi-repo
- ruvnet/github-project-management
- ruvnet/github-release-management
- ruvnet/github-suite
- ruvnet/github-workflow-automation
- ruvnet/hive-mind-coordination
- ruvnet/hooks-automation
- ruvnet/pair-programming
- ruvnet/performance-analysis
- ruvnet/reasoningbank
- ruvnet/reasoningbank-agentdb
- ruvnet/reasoningbank-intelligence
- ruvnet/ruflo-v3
- ruvnet/skill-builder
- ruvnet/sparc-methodology
- ruvnet/stream-chain
- ruvnet/swarm-advanced
- ruvnet/swarm-orchestration
- ruvnet/v3-cli-modernization
- ruvnet/v3-core-implementation
- ruvnet/v3-ddd-architecture
- ruvnet/v3-integration-deep
- ruvnet/v3-mcp-optimization
- ruvnet/v3-memory-unification
- ruvnet/v3-performance-optimization
- ruvnet/v3-security-overhaul
- ruvnet/v3-swarm-coordination
- ruvnet/verification-quality
- ruvnet/worker-benchmarks
- ruvnet/worker-integration
evidence:
- class: A
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-05-19'
  notes: 'Ruflo orchestration platform — 34k+ GitHub stars. Meets Class A threshold:
    ≥5 named skills registered across 6 generic buckets in Gaia.'
---

## Overview

Ruflo is the 6★ Apex capstone of the entire Ruflo skill tree. It unites all suite fusions into a single sovereign orchestration mastery: the Flow Nexus multi-topology swarm platform (4★), AgentDB memory sovereignty (5★ Ultimate), GitHub platform automation (4★), hive-mind consensus coordination, ReasoningBank self-improving knowledge base (3★), the complete v3 modernization sprint (4★), and the dual-mode Claude+Codex hybrid pattern (3★). At 6★, an agent possesses end-to-end command over the Ruflo platform from infrastructure to cognition.

## Key Capabilities

- **Flow Nexus mastery**: multi-topology swarm deployment with cloud platform management and Queen Seraphina AI assistant
- **AgentDB memory sovereignty**: 5★ Ultimate vector memory platform with 150x–12,500x faster search than brute-force HNSW
- **GitHub platform automation**: full software delivery lifecycle automation across code review, releases, and CI/CD
- **Hive-mind consensus**: distributed agent consensus with Byzantine fault tolerance for high-stakes multi-agent decisions
- **ReasoningBank intelligence**: self-improving cross-session reasoning pattern bank with persistent vector memory
- **V3 platform mastery**: complete modernization across DDD architecture, MCP optimization, security, and swarm coordination
- **Dual-mode orchestration**: hybrid Claude+Codex parallel execution spanning the full spawn→coordinate→collect pipeline

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `ruflo` skill bucket.

**Grandmaster Path**: agent-memory-platform 5★ Ultimate qualification — 34k+ stars exceeds the 10k-star Grandmaster threshold. This places Ruflo at the apex of the Gaia orchestration taxonomy.

This 6★ Apex unites all suite fusions: flow-nexus (4★) + agentdb (5★ Ultimate) + github-suite (4★) + hive-mind-coordination + reasoningbank (3★) + ruflo-v3 (4★) + dual-mode (3★) + all standalones.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

## Installation

There are **two different install paths** with very different surface areas. Pick based on what you need (#1744):

| | **Claude Code Plugin** | **CLI install (`npx ruflo init`)** |
|---|---|---|
| What it gives you | Slash commands + a few skills + agent definitions per-plugin | Full Ruflo loop — 98 agents, 60+ commands, 30 skills, MCP server, hooks, daemon |
| Files in your workspace | **Zero** | `.claude/`, `.claude-flow/`, `CLAUDE.md`, helpers, settings |
| MCP server registered | **No** (`memory_store`, `swarm_init`, etc. unavailable to Claude) | Yes |
| Hooks installed | No | Yes |
| Best for | Try a single plugin's commands without committing to the full install | Production use — everything works as documented |

### Path A — Claude Code Plugins (lite, slash commands only)

```bash
# Add the marketplace
/plugin marketplace add ruvnet/ruflo

# Install core + any plugins you need
/plugin install ruflo-core@ruflo
/plugin install ruflo-swarm@ruflo
/plugin install ruflo-rag-memory@ruflo
/plugin install ruflo-neural-trader@ruflo
```bash
This adds slash commands and agent definitions only. The Ruflo MCP server is NOT registered, so `memory_store`, `swarm_init`, `agent_spawn`, etc. won't be callable from Claude. For the full loop, use Path B below.

<details>
<summary><strong>🔌 All 33 plugins</strong></summary>

#### Core & Orchestration

| Plugin | What it does |
|--------|-------------|
| [**ruflo-core**](plugins/ruflo-core/README.md) | Foundation — server, health checks, plugin discovery |
| [**ruflo-swarm**](plugins/ruflo-swarm/README.md) | Coordinate multiple agents as a team |
| [**ruflo-autopilot**](plugins/ruflo-autopilot/README.md) | Let agents run autonomously in a loop |
| [**ruflo-loop-workers**](plugins/ruflo-loop-workers/README.md) | Schedule background tasks on a timer |
| [**ruflo-workflows**](plugins/ruflo-workflows/README.md) | Reusable multi-step task templates |
| [**ruflo-federation**](plugins/ruflo-federation/README.md) | Agents on different machines collaborate securely |

#### Memory & Knowledge

| Plugin | What it does |
|--------|-------------|
| [**ruflo-agentdb**](plugins/ruflo-agentdb/README.md) | Fast vector database for agent memory |
| [**ruflo-rag-memory**](plugins/ruflo-rag-memory/README.md) | Smart retrieval — hybrid search, graph hops, diversity ranking |
| [**ruflo-rvf**](plugins/ruflo-rvf/README.md) | Save and restore agent memory across sessions |
| [**ruflo-ruvector**](plugins/ruflo-ruvector/README.md) | [`ruvector`](https://npmjs.com/package/ruvector) — GPU-accelerated search, Graph RAG, 103 tools |
| [**ruflo-knowledge-graph**](plugins/ruflo-knowledge-graph/README.md) | Build and traverse entity relationship maps |

#### Intelligence & Learning

| Plugin | What it does |
|--------|-------------|
| [**ruflo-intelligence**](plugins/ruflo-intelligence/README.md) | Agents learn from past successes and get smarter |
| [**ruflo-graph-intelligence**](plugins/ruflo-graph-intelligence/) | Sublinear graph reasoning — PageRank, delta updates, complexity-aware execution (ADR-123) |
| [**ruflo-daa**](plugins/ruflo-daa/README.md) | Dynamic agent behavior and cognitive patterns |
| [**ruflo-ruvllm**](plugins/ruflo-ruvllm/README.md) | Run local LLMs (Ollama, etc.) with smart routing |
| [**ruflo-goals**](plugins/ruflo-goals/README.md) | Break big goals into plans and track progress |

#### Code Quality & Testing

| Plugin | What it does |
|--------|-------------|
| [**ruflo-testgen**](plugins/ruflo-testgen/README.md) | Find missing tests and generate them automatically |
| [**ruflo-browser**](plugins/ruflo-browser/README.md) | Automate browser testing with Playwright |
| [**ruflo-jujutsu**](plugins/ruflo-jujutsu/README.md) | Analyze git diffs, score risk, suggest reviewers |
| [**ruflo-docs**](plugins/ruflo-docs/README.md) | Generate and maintain documentation automatically |

#### Security & Compliance

| Plugin | What it does |
|--------|-------------|
| [**ruflo-security-audit**](plugins/ruflo-security-audit/README.md) | Scan for vulnerabilities and CVEs |
| [**ruflo-aidefence**](plugins/ruflo-aidefence/README.md) | Block prompt injection, detect PII, safety scanning |

#### Architecture & Methodology

| Plugin | What it does |
|--------|-------------|
| [**ruflo-adr**](plugins/ruflo-adr/README.md) | Track architecture decisions with a living record |
| [**ruflo-ddd**](plugins/ruflo-ddd/README.md) | Scaffold domain-driven design — contexts, aggregates, events |
| [**ruflo-sparc**](plugins/ruflo-sparc/README.md) | Guided 5-phase development methodology with quality gates |

#### DevOps & Observability

| Plugin | What it does |
|--------|-------------|
| [**ruflo-migrations**](plugins/ruflo-migrations/README.md) | Manage database schema changes safely |
| [**ruflo-observability**](plugins/ruflo-observability/README.md) | Structured logs, traces, and metrics in one place |
| [**ruflo-cost-tracker**](plugins/ruflo-cost-tracker/README.md) | Track token usage, set budgets, get cost alerts |

#### Extensibility

| Plugin | What it does |
|--------|-------------|
| [**ruflo-agent**](plugins/ruflo-agent/README.md) | Run agents — local WASM sandbox (rvagent) + Anthropic Claude Managed Agents (cloud) |
| [**ruflo-plugin-creator**](plugins/ruflo-plugin-creator/README.md) | Scaffold, validate, and publish your own plugins |

#### Domain-Specific

| Plugin | What it does |
|--------|-------------|
| [**ruflo-iot-cognitum**](plugins/ruflo-iot-cognitum/README.md) | IoT device management — trust scoring, anomaly detection, fleets |
| [**ruflo-neural-trader**](plugins/ruflo-neural-trader/README.md) | [`neural-trader`](https://npmjs.com/package/neural-trader) — AI trading with 4 agents, backtesting, 112+ tools |
| [**ruflo-market-data**](plugins/ruflo-market-data/README.md) | Ingest market data, vectorize OHLCV, detect patterns |

</details>

### CLI Install

**macOS / Linux / WSL / Git-Bash:**

```bash
# One-line install (POSIX shells only — see Windows note below)
curl -fsSL https://cdn.jsdelivr.net/gh/ruvnet/ruflo@main/scripts/install.sh | bash
```bash
**All platforms (including native Windows PowerShell / cmd):**

```bash
# Interactive setup wizard — runs identically on every platform
npx ruflo@latest init wizard

# Quick non-interactive init
# npx ruflo@latest init

# Or install globally
npm install -g ruflo@latest
```bash
> 💡 **Windows users:** the `curl ... | bash` form needs a POSIX shell (Git-Bash, WSL, MSYS). The `npx ruflo@latest init wizard` line works natively in PowerShell and cmd. If you hit an `'bash' is not recognized` error, use the `npx` line instead — both end up running the same init flow.

### MCP Server

```bash
# Add Ruflo as an MCP server in Claude Code (canonical form, matches USERGUIDE.md)
claude mcp add ruflo -- npx ruflo@latest mcp start
```

---

# Gaia AI Agent Skill Registry — Agent Context

Gaia is an open, evidence-backed skill graph for AI agents. It tracks capabilities (Basic, Extra, Ultimate), their evolution (0★ to 6★), and fusion into complex workflows.

This document serves as a lightweight, clean, and structured context sheet for AI agents and LLMs to understand the Gaia project, its CLI, MCP server, workflows, and registry guidelines.

---

## 1. Project Overview & Architecture

### Core Tiers & Concepts
*   **○ Basic Skills:** Primitive, indivisible capabilities (e.g., `/web-search`, `/parse-html`).
*   **◇ Extra Skills:** Emerges from fusing or combining 2+ basic skills (e.g., `/web-scrape`, `/research`).
*   **◆ Ultimate Skills:** High-complexity emergent capabilities; requires fusing 5+ named skill prerequisites (from `registry/named/`), with ≥1 origin contribution from the proposer. The most prestigious tier — a monument to a contributor's named body of work.
*   **◉ Unique Skills:** Basic skills that have reached elite rank (4★+), are graph-isolated (no prerequisites, no derivatives), and carry a distinct identity.

### Codebase Layout
*   `registry/`: Canonical graph (`gaia.json`), named skills, and schemas. **Source of Truth.**
*   `registry-for-review/`: Intake area for proposed skills (`gaia push`).
*   `src/gaia_cli/`: Core Python CLI logic.
*   `packages/mcp/`: Model Context Protocol (MCP) server for agent-native integration.
*   `scripts/`: Essential utilities for validation, building, and registry maintenance.
*   `docs/`: Documentation site and generated graph assets.

---

## 2. Command Line Interface (CLI) Quickstart

Put the `gaia` command on your `PATH` and interact with the registry.

### Installation
```bash
# Python install
pip install gaia-cli

# npm wrapper alternative
npm install -g @gaia-registry/cli
```

### Key CLI Commands
```bash
gaia init --user <name>   # Initialize local Gaia configuration
gaia update               # Pull latest registry and reinstall CLI/tools
gaia scan                 # Detect which skills your local workspace demonstrates
gaia tree                 # Print your local or global Gaia skill tree
gaia appraise <skillId>   # Inspect a skill's details, card, and prerequisites
gaia promote <skillId>    # Promote a skill eligible for leveling up
gaia push                 # Prepare detected skills and open a review PR automatically
gaia propose <skillId>    # Propose a single canonical skill as a named PR
gaia stats                # Show registry health, skills, and named implementations count
```

---

## 3. Model Context Protocol (MCP) Server

Connect Gaia natively to MCP-compatible agents (Claude Code, Cursor, VS Code, etc.).

### Claude Code Integration
```bash
claude mcp add gaia -- npx @gaia-registry/mcp-server
```

### Environment Variables
*   `GAIA_USER`: Your GitHub username (used to attribute claims).
*   `GITHUB_TOKEN`: GitHub personal access token (optional, used for pull request creation).

---

## 4. Curation & Ranking Rules

Capabilities advance through evidence, not declaration. Ranks range from `0★` to `6★` based on evidence:

### Evidence Tiers
*   **2★ (Named):** Requires $\ge 1$ Tier C evidence (basic demonstration).
*   **3★ (Evolved):** Requires $\ge 1$ Tier B evidence (integration in real workflow).
*   **4★+ (Hardened/Transcendent):** Requires $\ge 1$ Tier B/A evidence. **Alternative path**: 3+ skill fuses with ≥1 origin named skill.
*   **6★ (Transcendent ★ / Apex):** Tier A evidence + peer review. **Grandmaster path**: hold 2+ 5★ Ultimate skills AND ≥10k GitHub stars on your repo.

### Unique Promotion Policy
A Basic skill may be promoted to `type: "unique"` if:
1.  It has reached elite rank — `4★` or above.
2.  It is completely **graph-isolated** (has 0 prerequisites and 0 derivatives referenced by other nodes).

### Ultimate Promotion Criteria
A skill may be registered as `type: "ultimate"` if the proposer satisfies **all** of:
1. **5+ named prerequisites** — all prerequisites must be named skills in `registry/named/`
2. **At least 1 origin** — the proposer must hold `origin: true` on ≥1 of those named skills
3. **Evidence** — ≥3 Class A/B evidence sources; **Class A waived** if proposer has ≥5 named skills in `registry/named/`

---

## 5. Development Workflows & Strict Guidelines

If you are an agent modifying this repository, you must adhere to these rules:

### Branch Naming Conventions
| Prefix | Target Scope |
| :--- | :--- |
| `schema/` | `registry/schema/`, `*.md` |
| `cli/` | `src/gaia_cli/`, `packages/`, `tests/`, `*.md` |
| `docs/` | `docs/`, `*.md` |
| `review/gaia-push/` | Intake PRs (`registry-for-review/`), `*.md` |
| `review/meta/` | Registry curation (`registry/`), `*.md` |
| `infra/` | CI, scripts, `.github/`, `docs/*.html`, `*.md` |

### Agent-Managed Files (Hermes Ownership)
**DO NOT** modify, stage, or delete these files:
*   `STEWARDSHIP_PLAN.md`
*   `scripts/marketing_engine.py`
*   `scripts/email_sender.py`
*   `scripts/share_deliverable.py`
*   `scripts/generate_adoption_dashboard.py`
*   `scripts/generate_showcase.py`
*   `docs/ADOPTION.html`
*   `docs/SHOWCASE.html`
*   `docs/WHY-GAIA.md`
*   `docs/QUICKSTART.md`

### Source of Truth Rule
*   **NEVER** hand-edit `registry/gaia.json` or generated artifacts in `docs/`.
*   **Only Edit:** `registry/nodes/**/*.json`, `registry/named/*.json`, or `registry-for-review/skill-batches/*.json`.

### CLI Design Philosophy
*   **Local-First Skill Names:** The CLI prioritizes the developer's local workspace context. Pet names (e.g. `/gaia-curate`) are treated as the real skill names for a local developer.
*   **Slashes and Colors:** Do not remove the slash from local skill IDs. Real/local skill names should be displayed with their slash and colored green to distinguish them from generic canonical concepts.

---

## 6. Accessing the Graph Data
*   **Full Graph (JSON):** [gaia.json](./graph/gaia.json)
*   **Graph Exchange XML (GEXF):** [gaia.gexf](./graph/gaia.gexf)
*   **Graph Diagram (SVG):** [gaia.svg](./graph/gaia.svg)
*   **Text Tree Diagram:** [tree.md](./tree.md)

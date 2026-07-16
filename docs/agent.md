# Gaia AI Agent Skill Registry — Agent Context

Gaia is an open, evidence-backed skill graph for AI agents. It tracks capabilities and their evolution (0★ to 6★) through two structural axes: **Type** (starless/generic nodes only) and **Branch** (named skills at 4★+, derived at read-time).

This document serves as a lightweight, clean, and structured context sheet for AI agents and LLMs to understand the Gaia project, its CLI, MCP server, workflows, and registry guidelines.

---

## 1. Project Overview & Architecture

### Taxonomy (Yggdrasil II)

#### Type axis — starless (generic) nodes only
*   **○ Basic:** Primitive node with 0 prerequisites. The foundational structural unit (e.g., `/web-search`, `/parse-html`).
*   **◇ Fusion:** Node with ≥1 prerequisite — emerges from fusing or combining 2+ basic nodes (e.g., `/web-scrape`, `/research`). Replaces the legacy Extra / Ultimate taxonomy values.

Named skills carry **no `type` field**; they inherit type via `genericSkillRef` walk (Option D).

#### Branch axis — named skills only, derived at read-time
*   **Standard branch** (1★–3★) — default path for all named skills:
    1★ Awakened → 2★ Named → 3★ Evolved
*   **Suite branch** (4★+, generic parent has `suiteComponents`):
    4★ Extra → 5★ Ultimate → 6★ Apex
*   **Unique branch** (4★+, generic parent has NO `suiteComponents`):
    4★ Unique → 5★ Unique Ultimate → 6★ Unique Impossible *(provisional)*

Branch is **always derived, never declared** on a node. The fork happens at 4★ based solely on whether the generic parent carries `suiteComponents`.

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
# One-line installer (macOS / Linux — requires Python 3.8+)
curl -fsSL https://gaiaskilltree.com/install.sh | sh

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

Capabilities advance through evidence, not declaration. Ranks range from `0★` to `6★`. **Trust Magnitude (TM) is the sole promotion gate** — there is no separate Evidence Floor requirement.

### Trust Magnitude Thresholds
*   **Grade S** (TM ≥ 250 + diversity gate): Required for 5★ promotion on either branch, and for 6★ Apex.
*   **Grade A** (TM ≥ 100): Required for 4★ promotion on either branch (Extra or Unique).
*   **Grade B** (TM ≥ 50): Named skill baseline for 3★ Evolved.
*   **Grade C** (TM ≥ 20): Minimum for 2★ Named.

### Promotion Gates
*   **2★ (Named):** TM ≥ 20 (Grade C).
*   **3★ (Evolved):** TM ≥ 50 (Grade B).
*   **4★ Extra (Suite branch)** or **4★ Unique (Unique branch):** Origin contribution + TM ≥ 100 (Grade A).
*   **5★ Ultimate (Suite) / 5★ Unique Ultimate (Unique branch):** TM ≥ 250 (Grade S). Suite 5★ gate preserved per #935 (5 A-graded origins in `suiteComponents`).
*   **6★ Apex (Suite branch):** Full 6-predicate Apex Gate (TM Index 2026 Q2). See `docs/codex/trust-methodology.html`.
*   **6★ Unique Impossible (Unique branch):** Provisional 5-predicate gate (Apex minus `directNestedSuiteGte1`). Formal ratification deferred to Yggdrasil III.

### Unique Branch Policy
A named skill enters the Unique branch at 4★ when its generic parent has **no `suiteComponents`** and the skill holds:
1.  At least 1 Origin contribution in the fusion structure (`prerequisites`).
2.  TM ≥ 100 (Grade A).

Being graph-isolated is NOT a requirement — a skill may carry `suiteRef` membership and still be Unique-branch if its generic parent has no `suiteComponents`.

### Suite / Fusion Promotion Criteria
A named skill enters the Suite branch at 4★ when its generic parent carries `suiteComponents` and the proposer satisfies:
1. **Origin** — the proposer holds `role: 'origin'` on ≥1 component in `suiteComponents`.
2. **TM ≥ 100** (Grade A).

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

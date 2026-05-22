# Gaia AI Agent Skill Registry - Project Context

This file provides critical context and instructions for the Gaia project. Adhere to these guidelines for all development and research tasks.

## Project Overview
Gaia is an open, evidence-backed skill graph for AI agents. It tracks capabilities (Basic, Extra, Ultimate), their evolution (0★ to 6★), and fusion into complex workflows.

- **Primary Technologies:** Python (CLI), Node.js (MCP server, npm wrapper), JSON/YAML (Registry data), Markdown (Skill cards/Docs).
- **Core Concept:** Skills level up through evidence. Tiers: ○ Basic (indivisible), ◇ Extra (combination), ◆ Ultimate (high complexity).
- **Architecture:**
    - `registry/`: Canonical graph (`gaia.json`), named skills, and schemas. **Source of Truth.**
    - `src/gaia_cli/`: Core Python CLI logic.
    - `packages/mcp/`: Model Context Protocol (MCP) server for agent-native integration.
    - `scripts/`: Essential utilities for validation, building, and registry maintenance.
    - `docs/`: Documentation site and generated graph assets.
    - `registry-for-review/`: Intake area for proposed skills (`gaia push`).

## Development Workflows

### Setup
```bash
# Install editable with all extras
pip install -e ".[embeddings,interactive,dev]"

# (Optional) Install npm wrapper for local testing
cd packages/cli-npm && npm install
```

### Key Commands
- **Scan/Appraise:** `gaia scan` (detect skills), `gaia appraise <skillId>` (inspect).
- **Validation:** 
    - `gaia validate` (canonical graph check).
    - `gaia validate --intake` (intake batch check).
- **Documentation:** `gaia docs build` (regenerates site and artifacts).
- **Meta Review (CLI-ONLY):** 
    - `gaia list [--generic] [--named] [--description] [--json]`
    - `gaia merge <target> <source1>... [--named]`
    - `gaia split <source> <target1>...`
    - `gaia add <name> [--id <id>] [--type <type>] [--named]`
    - `gaia evidence <skillId> <source> [--class A|B|C] [--notes <notes>]`
- **Testing:** `pytest` (Python test suite).
- **MCP Server:** `npx @gaia-registry/mcp-server` (or `node packages/mcp/bin/mcp-server.js`).

### Branch Naming Conventions (Strict)
| Prefix | Scope |
|---|---|
| `schema/` | `registry/schema/` changes only |
| `cli/` | `src/gaia_cli/`, `packages/`, `tests/` |
| `docs/` | `docs/`, `*.md` |
| `review/gaia-push/` | Intake PRs (`registry-for-review/`) |
| `review/meta/` | Registry curation (`registry/` except schema) |
| `infra/` | CI, scripts, `.github/` |

## Technical Guidelines

### Vocabulary & Banned Synonyms
- `CONTEXT.md` is the single source of truth for product nomenclature and the banned-synonym list (CI greps it). Consult it before writing user-facing copy, CLI output, or agent skills.
- The **rarity** axis (`common` / `uncommon` / `rare` / `epic` / `legendary`) is **deprecated** and pending schema removal — see `CONTEXT.md` § Rarity. Do not introduce new references in copy, skills, or curation workflows. `gaia add` writes the legacy default automatically.

### Agent Skills
Project-local agent skills live in two directories and are actively used by contributors. Keep them in sync with `CONTEXT.md` nomenclature when changing terminology.
- `.agents/skills/gaia-curate/` — registry expansion + PR workflow.
- `.agents/skills/gaia-meta-audit/` — prioritized review queue.
- `.agents/skills/gaia-audit/` — focused single-target correction.
- `.agents/skills/gaia-draft-curate/`, `gaia-docs-sync/`, `gaia-integrity/`, `gaia-triage/`, `gaia-wiki-sync/`, `graphify-triage/`, `gaia-bot-curate/` — supporting workflows and bot curation.
- `.claude/skills/gaia-fuse-full-suite/` — fusion.

When updating any of these, route registry mutations through `gaia add` / `gaia merge` / `gaia split` / `gaia evidence` rather than hand-editing files in `registry/nodes/`.

### Agent-Managed Files (Hermes Ownership)
- **DO NOT** modify, stage, or delete the following files. They are managed by an autonomous agent (Hermes) and will be relocated in the future:
    - `STEWARDSHIP_PLAN.md`
    - `scripts/marketing_engine.py`
    - `scripts/email_sender.py`
    - `scripts/share_deliverable.py`
    - `scripts/generate_adoption_dashboard.py`
    - `scripts/generate_showcase.py`
    - `docs/ADOPTION.html`
    - `docs/SHOWCASE.html`
    - `docs/WHY-GAIA.md`
    - `docs/QUICKSTART.md`

### Wiki Management
- The project wiki lives in a separate repository: `https://github.com/mbtiongson1/gaia-skill-tree.wiki.git`.
- It is NOT part of the main workspace. If a wiki update is required:
    1. Clone the wiki repository to an adjacent directory (e.g., `../gaia-wiki`).
    2. Make changes, commit, and push from that directory.
    3. **DO NOT** delete the wiki directory after use; keep it for future updates.
    4. Return to the main workspace to continue core development.

### Source of Truth
- **NEVER** hand-edit `registry/gaia.json` or generated artifacts in `docs/`.
- **Edit Only:** `registry/nodes/**/*.json`, `registry/named/*.json`, or `registry-for-review/skill-batches/*.json`.

### Python Internal Modules
- `src/gaia_cli/formatting.py`: Centralized slash-naming formatters, RANK_COLORS, and tier colors.
- `src/gaia_cli/localContext.py`: Manages `LocalContext`, merging user trees, scan results, and named skill maps.

### PR Pre-Submission Checklist (REQUIRED)
To prevent common CI failures (documentation drift and version disagreement), follow these steps before every push:

1. **Rebuild Documentation:** Ensure all graph artifacts and documentation are up to date.
   ```bash
   gaia docs build
   ```
2. **Verify Doc State:** Confirm no drift remains.
   ```bash
   gaia docs build --check
   ```
3. **Synchronize Versions:** If you made registry changes, ensure all version files are in sync.
   - Files to check: `pyproject.toml`, `packages/cli-npm/package.json`, `packages/mcp/package.json`, `registry/gaia.json`.
   - All must have the exact same version string (e.g., `3.21.5`).
4. **Final Validation:**
   ```bash
   gaia validate
   ```

### Versioning & Pre-commit
- The following files **MUST** be kept in lockstep: `pyproject.toml`, `packages/cli-npm/package.json`, `packages/mcp/package.json`, and `registry/gaia.json`.
- Use `gaia release patch` to automatically bump and synchronize these files when ready for a new version.
- A pre-commit hook (`scripts/install-git-hooks.sh`) enforces this. Do not manually repair version drift without investigation.

### Skill Leveling (Evidence Floor)
- `2★` (Named): ≥ 1 Tier C evidence.
- `3★` (Evolved): ≥ 1 Tier B evidence.
- `4★+` (Hardened/Transcendent): ≥ 1 Tier B/A evidence.
- `6★` (Transcendent ★): Tier A + peer review.

### Coding Style
- **Python:** Follow idiomatic patterns; use `jsonschema` for data validation.
- **Node.js:** TypeScript for the MCP server.
- **Registry:** Skills use `kebab-case` IDs. Display names are Title Case.

### Unique Promotion Policy
- **Eligibility:** A Basic skill may be promoted to `type: "unique"` if it reaches level `4★` or above AND is graph-isolated (not a prerequisite for any other skill).
- **Isolation:** Unique skills must have 0 prerequisites and 0 derivatives that are referenced as prerequisites by other nodes.

### CLI Design Philosophy
- **Local-First Skill Names:** The CLI must prioritize the developer's local workspace context. "Pet names" (e.g. `/gaia-curate` or `gaiabot/gaia-triage`) are considered the *actual*, real skill names for a local developer.
- **Slashes and Colors:** Do NOT remove the slash from local skill IDs. Real/local skill names should be displayed with their slash and colored green to distinguish them from generic canonical concepts. The generic canonical names ("Human Readable Names") are strictly for the state of all skills in the global graph, but developers using the CLI should see their own local skill names.

## Important Files
- `registry/gaia.json`: The core Directed Acyclic Graph (DAG) of skills.
- `registry/schema/skill.schema.json`: Validation rules for skills.
- `scripts/build_docs.py`: Orchestrates the entire documentation and artifact build process.
- `DESIGN.md`: Visual language and design tokens for the graph and UI.
- `CONTRIBUTING.md`: Detailed contribution workflows.

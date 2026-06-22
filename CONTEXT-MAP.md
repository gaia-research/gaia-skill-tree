# Monorepo Context Map

This repository is a polyglot monorepo containing distinct but interconnected contexts. This document maps these contexts to their directories and describes their architecture and responsibilities.

---

## 1. System-Wide Context
- **Path:** Root directory `./`
- **Purpose:** Core metadata, project-wide documentation, task orchestration, and overall repository configuration.
- **Key Artifacts:**
  - `Taskfile.yml`: Multi-language task orchestration tool defining shortcuts like `task validate`, `task test`, and `task build`.
  - `pyproject.toml`: Root package definition, Python dependencies, and build metadata.
  - `CONTEXT.md`: System-wide vocabulary, taxonomy, design specs, and registry mechanics.

---

## 2. Core Registry
- **Path:** [registry/](file:///Users/marcotiongson/Documents/gaia-skill-tree/registry)
- **Purpose:** The canonical skill graph database and its schema definitions.
- **Key Artifacts:**
  - [registry/gaia.json](file:///Users/marcotiongson/Documents/gaia-skill-tree/registry/gaia.json): The primary database file representing the active skill graph.
  - [registry/schema/](file:///Users/marcotiongson/Documents/gaia-skill-tree/registry/schema/): JSON Schema files validating generic and named skill structures.
  - [registry/named/](file:///Users/marcotiongson/Documents/gaia-skill-tree/registry/named/): Markdown profiles containing frontmatter declarations for named skills.
  - [registry/suites/](file:///Users/marcotiongson/Documents/gaia-skill-tree/registry/suites/): YAML files mapping suite components and installations.

---

## 3. Python CLI (Core Operations)
- **Path:** [src/gaia_cli/](file:///Users/marcotiongson/Documents/gaia-skill-tree/src/gaia_cli)
- **Purpose:** Core command-line interface logic, graph algorithms, and verification flows.
- **Architecture:**
  - [src/gaia_cli/main.py](file:///Users/marcotiongson/Documents/gaia-skill-tree/src/gaia_cli/main.py): Entry point using dynamic command discovery from the `commands/` directory.
  - [src/gaia_cli/commands/dev/](file:///Users/marcotiongson/Documents/gaia-skill-tree/src/gaia_cli/commands/dev/): Decomposed developer tools subpackage ensuring clean separation of mutating operations (e.g. `evidence.py`, `verify.py`, `merge.py`, `calibrate.py`).
  - [src/gaia_cli/versioning.py](file:///Users/marcotiongson/Documents/gaia-skill-tree/src/gaia_cli/versioning.py): Version lockstep manager ensuring pyproject.toml, package.json files, and registry/gaia.json are always synchronized.

---

## 4. MCP Server (Model Context Protocol)
- **Path:** [packages/mcp/](file:///Users/marcotiongson/Documents/gaia-skill-tree/packages/mcp)
- **Purpose:** Exposes the Gaia Skill Registry to AI agents (like Claude Code, Cursor, and VS Code Continue) via standard Model Context Protocol.
- **Key Components:**
  - [packages/mcp/src/config/merger.ts](file:///Users/marcotiongson/Documents/gaia-skill-tree/packages/mcp/src/config/merger.ts): Config merger to parse and merge `~/.mcp.json` and `./.mcp.json`.
  - [packages/mcp/src/daemon.ts](file:///Users/marcotiongson/Documents/gaia-skill-tree/packages/mcp/src/daemon.ts): Lightweight detached process daemon manager handling start/stop/status and writing to `~/.gaia/mcp.pid`.
  - [packages/mcp/src/index.ts](file:///Users/marcotiongson/Documents/gaia-skill-tree/packages/mcp/src/index.ts): Stdio MCP server registration of tools like `gaia_lookup`, `gaia_suggest`, `gaia_scan_context`, and `gaia_my_tree`.

---

## 5. npm CLI Shim
- **Path:** [packages/cli-npm/](file:///Users/marcotiongson/Documents/gaia-skill-tree/packages/cli-npm)
- **Purpose:** Lightweight Node.js wrapper that publishes the `gaia` command to npm, executing the local Python binary under the hood.

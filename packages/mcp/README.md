# @gaia-registry/mcp-server

MCP server for the Gaia Skill Registry — agent-native skill detection, fusion, and progression.

## Table of Contents

- [Setup by Platform](#setup-by-platform)
  - [Claude Code (CLI)](#claude-code-cli)
  - [Claude Desktop](#claude-desktop)
  - [Cursor](#cursor)
  - [VS Code (GitHub Copilot / Continue)](#vs-code)
  - [Gemini (Google AI Studio)](#gemini)
  - [OpenAI Codex CLI](#openai-codex-cli)
  - [OpenClaw](#openclaw)
  - [Other MCP-Compatible Agents](#other-mcp-compatible-agents)
- [Tools](#tools)
- [Resources](#resources)
- [Configuration](#configuration)
- [How It Works](#how-it-works)
- [Development](#development)
- [Architecture](#architecture)

---

## Setup by Platform

### Claude Code (CLI)

The fastest setup — one command:

```bash
claude mcp add gaia -- npx @gaia-registry/mcp-server
```

Or add to your project's `.claude/settings.json`:

```json
{
  "mcpServers": {
    "gaia": {
      "command": "npx",
      "args": ["@gaia-registry/mcp-server"],
      "env": { "GAIA_USER": "your-github-username" }
    }
  }
}
```

To add globally (available in all projects), use `~/.claude/settings.json` instead.

**Verify it works:** Start Claude Code and ask: *"Use gaia_lookup to find the web-scrape skill"*

> [Claude Code MCP docs](https://docs.anthropic.com/en/docs/claude-code/mcp)

---

### Claude Desktop

Edit your config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "gaia": {
      "command": "npx",
      "args": ["@gaia-registry/mcp-server"],
      "env": { "GAIA_USER": "your-github-username" }
    }
  }
}
```

Restart Claude Desktop after saving. The Gaia tools will appear in the tool picker (hammer icon).

> [Claude Desktop MCP docs](https://modelcontextprotocol.io/quickstart/user)

---

### Cursor

Create `.cursor/mcp.json` in your project root (or `~/.cursor/mcp.json` for global):

```json
{
  "mcpServers": {
    "gaia": {
      "command": "npx",
      "args": ["@gaia-registry/mcp-server"],
      "env": { "GAIA_USER": "your-github-username" }
    }
  }
}
```

Restart Cursor. The Gaia tools will be available in Composer and Agent mode.

> [Cursor MCP docs](https://docs.cursor.com/context/model-context-protocol)

---

### VS Code

For **GitHub Copilot** (agent mode) or **Continue**, add to `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "gaia": {
      "command": "npx",
      "args": ["@gaia-registry/mcp-server"],
      "env": { "GAIA_USER": "your-github-username" }
    }
  }
}
```

Or add to your VS Code `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "gaia": {
        "command": "npx",
        "args": ["@gaia-registry/mcp-server"],
        "env": { "GAIA_USER": "your-github-username" }
      }
    }
  }
}
```

Reload the window (`Ctrl+Shift+P` → "Reload Window").

> [VS Code MCP docs](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)

---

### Gemini

For **Google AI Studio** or **Gemini CLI** with MCP support, add to your MCP configuration:

```json
{
  "mcpServers": {
    "gaia": {
      "command": "npx",
      "args": ["@gaia-registry/mcp-server"],
      "env": { "GAIA_USER": "your-github-username" }
    }
  }
}
```

> [Gemini MCP docs](https://ai.google.dev/gemini-api/docs/model-context-protocol)

---

### OpenAI Codex CLI

For the OpenAI Codex CLI agent, add to your MCP config:

```json
{
  "mcpServers": {
    "gaia": {
      "command": "npx",
      "args": ["@gaia-registry/mcp-server"],
      "env": { "GAIA_USER": "your-github-username" }
    }
  }
}
```

> [Codex CLI docs](https://github.com/openai/codex)

---

### OpenClaw

Edit `~/.openclaw/openclaw.json`:

```json
{
  "mcpServers": {
    "gaia": {
      "command": "npx",
      "args": ["@gaia-registry/mcp-server"],
      "env": { "GAIA_USER": "your-github-username" }
    }
  }
}
```

Restart the gateway after saving:

```bash
openclaw gateway restart
```

**Verify it works:**

```bash
openclaw mcp list
```

**Per-agent routing** (optional) — restrict Gaia to specific agents:

```json
{
  "mcpServers": {
    "gaia": {
      "command": "npx",
      "args": ["@gaia-registry/mcp-server"],
      "env": { "GAIA_USER": "your-github-username" }
    }
  },
  "agents": {
    "coder": {
      "mcpServers": ["gaia"]
    }
  }
}
```

> [OpenClaw docs](https://docs.openclaw.ai)

---

### Other MCP-Compatible Agents

Any agent that supports the [Model Context Protocol](https://modelcontextprotocol.io) can use Gaia. The universal config shape is:

```json
{
  "command": "npx",
  "args": ["@gaia-registry/mcp-server"],
  "env": {
    "GAIA_USER": "your-github-username",
    "GITHUB_TOKEN": "ghp_..."
  }
}
```

Set `GITHUB_TOKEN` if you want `gaia_propose` to open PRs on your behalf.

---

## Tools

| Tool | Description |
|------|-------------|
| `gaia_lookup` | Look up a skill by ID or fuzzy name. Returns metadata, prerequisites, derivatives, evidence. |
| `gaia_suggest` | Get fusion recommendations based on your context — connected tools and project signals. |
| `gaia_scan_context` | Detect skills from connected MCP tools and project descriptions. Identifies fusion opportunities and novel capabilities. |
| `gaia_my_tree` | Show your skill tree — unlocked skills, pending fusions, stats. |
| `gaia_propose` | Claim a fusion or propose a novel skill to the registry. Opens a PR on GitHub. |

### Example Prompts

Once Gaia is connected, try these in your agent:

- *"What skills do I have? Use gaia_my_tree."*
- *"Scan my current context and suggest skill fusions."*
- *"Look up the rag-pipeline skill."*
- *"I just built a web scraper — propose it as a skill fusion."*

---

## Resources

| URI | Description |
|-----|-------------|
| `gaia://registry` | Full skill graph (all skills with types, levels, rarities, prerequisites) |
| `gaia://tree/{username}` | A user's skill tree |

---

## REST API

In addition to the MCP interface, the registry is also available as a static read-only JSON API suitable for HTTP clients, scripts, and dashboards.

- **Docs:** [gaiaskilltree.com/api/](https://gaiaskilltree.com/api/)
- **Base URL:** `https://gaiaskilltree.com/api/v1/`
- **OpenAPI 3.1 spec:** [/api/v1/openapi.json](https://gaiaskilltree.com/api/v1/openapi.json)

No authentication required. All endpoints are pre-generated static files served from GitHub Pages.

---

## Configuration

The server reads identity from (in priority order):

1. `GAIA_USER` environment variable
2. `.gaia/config.json` in the current working directory
3. `~/.gaia/config.json` (global)

For `gaia_propose`, set `GITHUB_TOKEN` or `GH_TOKEN` to enable PR creation.

---

## How It Works

1. The server fetches `gaia.json` from the registry on GitHub (cached locally with ETag)
2. When you call `gaia_suggest` or `gaia_scan_context`, it maps your connected MCP tools to Gaia skill IDs
3. It checks if your detected skills satisfy prerequisites for any composite/ultimate skill
4. If a fusion is available, it tells you — and `gaia_propose` can claim it by opening a PR

---

## Development

```bash
cd packages/mcp
npm install
npm run build    # Compile TypeScript
npm test         # Run tests (vitest)
npm run dev      # Watch mode
```

---

## Architecture

```
src/
├── index.ts              ← Server setup, tool/resource registration
├── registry graph layer/                ← Registry data layer (loader, types, search, DAG)
├── tools/                ← MCP tool handlers (lookup, suggest, propose, etc.)
├── advisor/              ← Skill detection engine (fusion, detector, novelty)
├── config/               ← Identity resolution, ETag cache
├── resources/            ← MCP resource handlers
└── utils/                ← GitHub API helpers
```

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/marks/diamond-seal-preview.svg">
    <img src="docs/assets/marks/diamond-seal.svg" alt="The Diamond Seal" width="120" />
  </picture>
</div>

# Gaia - AI Agent Skill Registry

> The open, evidence-backed skill graph for AI agents: collect, evolve, and fuse capabilities into something legendary.

[![Validate](https://github.com/mbtiongson1/gaia-skill-tree/actions/workflows/validate.yml/badge.svg)](https://github.com/mbtiongson1/gaia-skill-tree/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-c084fc.svg)](LICENSE)
[![Website](https://img.shields.io/badge/Website-gaia.tiongson.co-f59e0b)](https://gaia.tiongson.co/)

---

## The Registry

Every AI agent capability exists somewhere on this graph. Skills start at the foundation tier, awaken through evidence, evolve through use, and fuse into things greater than the sum of their parts.

<!-- gaia:registry-start -->
```text
◆ ruvnet/ruflo  [6★]
  ├─ ◇ ruvnet/flow-nexus  [4★]
  │  ├─ ◇ ruvnet/flow-nexus-swarm  [3★]
  │  │  ├─ ◇ /plan-and-execute  [4★]
  │  ├─ ◇ ruvnet/flow-nexus-platform  [3★]
  │  │  ├─ ○ huggingface/hf-cli  [2★]
  │  │  └─ ○ /tool-use  [1★]
  │  └─ ◇ ruvnet/flow-nexus-neural  [3★]
  │     ├─ ○ /parallel-execution  [2★]
  │     └─ ○ /embed-text  [1★]
  ├─ ◆ ruvnet/agentdb  [5★]
  │  ├─ ◇ ruvnet/agentdb-advanced  [3★]
  │  │  ├─ ○ ruvnet/agentdb-vector-search  [2★]
  │  │  └─ ◇ garrytan/learn  [2★]
  │  │     ├─ ○ garrytan/context-restore  [3★]

◆ ruvnet/agentdb  [5★]
  ├─ ◇ ruvnet/agentdb-advanced  [3★]
  │  ├─ ○ ruvnet/agentdb-vector-search  [2★]
  │  └─ ◇ garrytan/learn  [2★]
  │     ├─ ○ garrytan/context-restore  [3★]
  │     └─ ○ /retrieve  [1★]
  ├─ ◇ ruvnet/agentdb-learning  [3★]
  │  ├─ ◇ garrytan/learn  [2★]  (↑ see above)
  │  └─ ○ ruvnet/reasoningbank-intelligence  [2★]
  ├─ ○ ruvnet/agentdb-memory-patterns  [2★]
  ├─ ○ ruvnet/agentdb-optimization  [2★]
  └─ ○ ruvnet/agentdb-vector-search  [2★]  (↑ see above)

Uniques — graph-isolated Basic Skills that reached elite mastery (4★+) through depth alone, with no fusion path forward.
  ◉ nousresearch/feed-monitoring  [4★ · Hardened]
  ◉ openai/few-shot-learning  [4★ · Hardened]
  ◉ huggingface/huggingface-llm-trainer  [4★ · Hardened]
  ◉ ruvnet/hive-mind-coordination  [4★ · Hardened]
  ◉ openai/self-consistency  [4★ · Hardened]

(196 skills total — see docs/tree.md)
```
<!-- gaia:registry-end -->


### How skills fuse

When two or more Basic skills combine, they can form an Extra. This is what `gaia scan` and `gaia fuse` render in your terminal:

```text
  mattpocock/grill-me  ────────────┐
                                   ├──▶  mattpocock/grill-with-docs  ◇
  mattpocock/ubiquitous-language  ─┘
```

Basics fuse into Extras; Extras can fuse into Ultimates. Evidence powers each ascent.

> [!TIP]
> **New here?** The interactive tutorial at **[gaia.tiongson.co](https://gaia.tiongson.co/)** covers everything visually: skill tiers, the stars axis, The Initiate's Rite, and copy-paste commands.

---

## Skill Tiers & Stars

| Symbol | Tier | Levels | Evidence floor |
|--------|------|--------|---------------|
| ○ Basic | Primitive, indivisible capability | 0★ Unawakened → 1★ Awakened | None |
| ◉ Unique | Graph-isolated Basic Skill that ranked up without fusing | 1★ Awakened → 6★ Transcendent ★ | None (depth alone) |
| ◇ Extra | Emerges from combining 2+ Basic Skills or fusing Extras | 2★ Named → 3★ Evolved → 4★ Hardened → 5★ Transcendent | Class C+ evidence |
| ◆ Ultimate | High-complexity emergent capability (fewer than 1% of agents) | 5★ Transcendent → 6★ Transcendent ★ | Class A (peer-reviewed) |

Skills rank up through **evidence**, not declaration. Basics fuse into Extras or Ultimates; Extras can fuse with other Extras. Each demerit demotes a skill by one star (floored at 1★, valid for 2★+ only).

---

## Quickstart

**1. Install the CLI**

<!-- gaia:version-start -->
Current Gaia CLI version: `3.20.4`.

Python install:

```bash
pip install gaia-cli
```

npm wrapper alternative:

```bash
npm install -g @gaia-registry/cli
```
<!-- gaia:version-end -->

<details>
<summary>npm / pipx / Windows alternatives</summary>

**npm wrapper:**
```bash
npm install -g @gaia-registry/cli
```

**pipx (if pip fails):**
```bash
brew install pipx        # macOS
pipx install gaia-cli
```

**Windows PATH fix** (if `gaia` isn't found after install):
```powershell
$env:PATH += ";" + (python -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user'))")
```

**Registry development** (editable install):
```bash
git clone https://github.com/mbtiongson1/gaia-skill-tree.git
cd gaia-skill-tree
pip install -e ".[embeddings,dev]"
```

The `dev` extra installs packaging/test tools such as `build` and `pytest`; without it,
packaging-specific tests are skipped locally with guidance to install developer extras.
</details>

**2. Initialise & scan**

```bash
gaia init --user your-username
gaia scan
```

Detects skills your agent demonstrates.

**3. Push for review**

```bash
gaia push
```

A GitHub PR opens automatically. Maintainers review; your name attaches at 2★.

**4. Bond your agent (optional)**

```bash
claude mcp add gaia -- npx @gaia-registry/mcp-server
```

Any MCP-compatible client. See [packages/mcp/](packages/mcp/) for config examples.

---

**Or explore interactively** with the [Terminal UI](#terminal-ui-experimental) (after step 1 → `gaia` with no args).

> **Keep up to date:** Run `gaia update` anytime to pull latest registry + CLI.

## Terminal UI (experimental)

> **New.** Agent-first interface designed for Claude Code, Codex, and other AI agents.

After step 1, launch with no arguments:

```bash
gaia
```

Navigate your skills:
- **Fuzzy search** by name, description, or intent
- **View tree** (`^T`) and **run scan** (`^G`) without leaving the TUI
- **Install skills** with one keystroke
- Keyboard-native: `↑↓` navigate · `Enter` install · `q` quit

Requires `textual` (included with `pip install gaia-cli`).

---

## CLI Reference

<!-- gaia:cli-start -->
```text
usage: gaia [-h] [--registry REGISTRY] [--global] [--version]
            {help,init,scan,pull,update,install,uninstall,tree,push,propose,version,mcp,release,graph,stats,appraise,promote,fuse,docs,lookup,list,merge,split,add,evidence,skills}
            ...

Gaia Registry CLI

positional arguments:
  {help,init,scan,pull,update,install,uninstall,tree,push,propose,version,mcp,release,graph,stats,appraise,promote,fuse,docs,lookup,list,merge,split,add,evidence,skills}
    help                Show command help
    init                Create or update local Gaia config
    scan                Scan configured paths for skill evidence
    pull                Refresh registry data from origin
    update              Update all installed remote skills
    install             Install a named skill
    uninstall           Uninstall a named skill
    tree                Show your Gaia skill tree
    push                Prepare detected skills for review
    propose             Propose a single canonical skill as a named PR
    version             Print the Gaia CLI version
    mcp                 Run the bundled Gaia MCP server
    release             Bump release version files
    graph               Generate and open the Gaia skill graph
    stats               Show registry health at a glance
    appraise            Inspect a skill card with status and actions
    promote             Promote a skill eligible for level-up
    fuse                Confirm a skill combination or promotion candidate
    docs                Documentation maintenance commands
    lookup              Look up a canonical skill and its named implementations
    list                List skills in the registry with filtering
    merge               Merge one or more skills into a target skill
    split               Split a skill into multiple new skills
    add                 Add a new skill to the registry
    evidence            Add evidence to a skill
    skills              Browse and manage named skills

options:
  -h, --help            show this help message and exit
  --registry REGISTRY   Path to a local Gaia registry checkout. Defaults to auto-resolved local or
                        global registry.
  --global, -g          Use global GAIA_HOME registry, ignoring any local .gaia/ config.
  --version, -v         Print the Gaia CLI version and exit.
  --canon               Show canonical registry data instead of local-first view.

Quick usage:
  gaia init [--user <name>] [--scan <path>] [--yes]
  gaia scan [--quiet] [--auto-promote]
  gaia pull
  gaia tree [--named] [--title]
  gaia push [--dry-run] [--no-pr]
  gaia propose [<skillId>] [--ultimate] [--target <name>] [--no-pr]
  gaia version
  gaia mcp
  gaia release <patch|minor|major>
  gaia graph [--format html|svg|json] [-o <path>] [--no-open]
  gaia appraise [<skillId>]
  gaia promote [<skillId>] [--all] [--name <name>]
  gaia fuse <skillId> [--name <name>]
  gaia update
  gaia stats
  gaia docs build [--check]
  gaia lookup <skillId>
  gaia list [--generic] [--named] [--description] [--json]
  gaia merge <target> <source1> [source2...] [--named]
  gaia split <source> <target1> <target2>...
  gaia add <name> [--id <id>] [--type <type>] [--description <desc>] [--named] [--contributor <user>]
  gaia evidence <skillId> <source> [--class A|B|C] [--evaluator <user>] [--date <date>] [--notes <notes>]
  gaia skills <list|search|info|install|uninstall>
  gaia skills list [--exclude-pending]
  gaia skills search <query> [--exclude-pending]
  gaia skills info <skill_id> [--exclude-pending]
  gaia skills install <skill> [--global | --local]
  gaia skills uninstall <skill_id>

```
<!-- gaia:cli-end -->

---

## MCP Server

`@gaia-registry/mcp-server` connects Gaia to MCP-compatible agents (Claude Code, Cursor, VS Code, etc.).

| Agent | Install |
|-------|---------|
| Claude Code | `claude mcp add gaia -- npx @gaia-registry/mcp-server` |
| Any MCP client | Command: `npx`, args: `@gaia-registry/mcp-server` |

Set `GAIA_USER=your-github-username` and optionally `GITHUB_TOKEN` for PR tools. See [`packages/mcp/`](packages/mcp/) for full docs and agent-specific config examples.

---

## Repository Structure

<!-- gaia:layout-start -->
```text
registry/                 curated registry data and public generated catalogs
registry-for-review/      pending skill batch intake records
skill-trees/              per-user skill-tree.json files
generated-output/         ignored local scan and render output
docs/                     docs site
src/gaia_cli/             Python CLI package
packages/cli-npm/         npm wrapper package
packages/mcp/             MCP server package
scripts/                  validation, rendering, docs, and release helpers
tests/                    Python test suite
```
<!-- gaia:layout-end -->

---

## Contributing

Gaia is a shared map of agent capabilities.

Common ways to help:
- Review draft skills for clarity, overlap, and evidence quality.
- Turn accepted reviews into concrete PRs (new skill, fusion, or reclassification).

Contribution steps: [CONTRIBUTING.md](CONTRIBUTING.md).
Full policy/reviewer guidance: <https://github.com/mbtiongson1/gaia-skill-tree/wiki> (repo: <https://github.com/mbtiongson1/gaia-skill-tree.wiki.git>).

## Contributors

Thank you to everyone who has expanded the Gaia registry.

| Contributor | Contribution |
|---|---|
| [@mbtiongson1](https://github.com/mbtiongson1) | Creator and maintainer: graph design, CLI, MCP server, curation pipeline |
| [@rico-tiongson](https://github.com/rico-tiongson) | Coding cowork buddy and collaborator: early feature contributions and ongoing pair programming |
| [@Juno](https://github.com/Juno) | Key contributor: graph browser expansion, function-calling skill, RAG pipeline evidence, and CLI DX improvements |
| [@karpathy](https://github.com/karpathy) | Origin named skill: `karpathy/autoresearch` |
| [@mattpocock](https://github.com/mattpocock) | Named skills: diagnose, tdd, to-prd, triage, zoom-out, and 6 others |
| [@intelligentcode-ai](https://github.com/intelligentcode-ai) | Named skills: database-engineer, devops-engineer, mcp-client, security-engineer, and 5 others |
| [@ruvnet](https://github.com/ruvnet) | Named skill: `ruvnet/flow-nexus-swarm` |
| [@GLINCKER](https://github.com/GLINCKER) | Named skill: `glincker/readme-generator` |
| [@spring-ai-alibaba](https://github.com/spring-ai-alibaba) | Named skill: `spring-ai/readme-generate` |
| [@pexp13](https://github.com/pexp13) | Named skill: `pexp13/sentiment-analysis` |
| [@kriptoburak](https://github.com/kriptoburak) | Named skill: `kriptoburak/x-twitter-automation` |
| [@balukosuri](https://github.com/balukosuri) | Evidence: community reproduction of Karpathy's autoresearch as a universal skill |
| @gemini-cli | Curation: added generative-media, mathematical-animation, and other generic skills from Hermes ecosystem |
| [@obra](https://github.com/obra) | Named skills: 11 skills from the superpowers ecosystem |

---

## Programmatic Management

The Gaia registry is programmatically managed. All meta shifts (adding, merging, splitting, adding evidence) must be performed via the [Gaia CLI](src/gaia_cli/). Hand-editing JSON nodes is deprecated to ensure schema integrity and automated timeline logging.

---

## License

MIT: see [LICENSE](LICENSE).

---

*Graph is canonical. Everything else is a shadow.*


<div align="center">
  <img src="docs/assets/marks/diamond-seal.svg" alt="The Diamond Seal" width="120" />
</div>

# Gaia - AI Agent Skill Registry

> The open, evidence-backed skill graph for AI agents: collect, evolve, and fuse capabilities into something legendary.

[![Validate](https://github.com/mbtiongson1/gaia-skill-tree/actions/workflows/validate.yml/badge.svg)](https://github.com/mbtiongson1/gaia-skill-tree/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tutorial](https://img.shields.io/badge/Tutorial-gaia.tiongson.co-38bdf8)](https://gaia.tiongson.co/)

---

## The Registry

Every AI agent capability exists somewhere on this graph. Skills start at the foundation tier, awaken through evidence, evolve through use, and fuse into things greater than the sum of their parts.

```text
◆ garrytan/gstack  [5★]
  ├─ ○ garrytan/office-hours  [0★]
  ├─ ◇ garrytan/plan-eng-review  [3★]
  │  ├─ ○ garrytan/design-html  [1★]
  │  ├─ ○ /diff-content  [1★]
  │  └─ ○ garrytan/benchmark  [1★]
  ├─ ◇ mattpocock/to-issues  [3★]
  │  ├─ ○ /plan-decompose  [1★]
  │  └─ ○ /route-intent  [1★]
  └─ ◇ firecrawl/firecrawl  [3★]
     ├─ ○ /web-search  [1★]
     ├─ ○ /parse-html  [1★]
     └─ ○ /extract-entities  [1★]

◆ obra/superpowers  [5★]
  ├─ ○ obra/brainstorming  [1★]
  ├─ ○ obra/executing-plans  [2★]
  ├─ ◇ obra/finishing-a-development-branch  [2★]
  │  └─ ◇ garrytan/plan-eng-review  [3★]
  └─ ○ obra/writing-plans  [2★]

Uniques — graph-isolated Basic Skills that ranked up through depth alone
  ◉ nousresearch/feed-monitoring  [4★ · Hardened]
  ◉ openai/few-shot-learning  [4★ · Hardened]
  ◉ huggingface/semantic-cache  [4★ · Hardened]

Full registry: docs/tree.md
Your tree renders: generated-output/tree.{md,html}
```

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

## Install

<!-- gaia:version-start -->
Current Gaia CLI version: `3.16.1`.

Python install:

```bash
pip install gaia-cli
```

npm wrapper alternative:

```bash
npm install -g @gaia-registry/cli
```
<!-- gaia:version-end -->

For registry development, clone and install editable:
```bash
git clone https://github.com/mbtiongson1/gaia-skill-tree.git
cd gaia-skill-tree
pip install -e ".[embeddings]"
```

<details>
<summary>Troubleshooting</summary>

If pip fails, try pipx:
```bash
brew install pipx        # macOS
pipx install gaia-cli
```

Windows — if `gaia` isn't recognized after install:
```powershell
$env:PATH += ";" + (python -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user'))")
```
</details>

## Terminal UI (TUI)

Running `gaia` with no arguments launches an interactive terminal interface when connected to a terminal:

```bash
gaia
```

The TUI provides an intuitive, keyboard-navigable interface for browsing skills, viewing your tree, and managing promotions—without needing to memorize CLI commands.

## Updating Gaia

To instantly pull the latest registry data and update the core CLI, use:

```bash
gaia update
```

> **Note:** Semantic search users must manually update embeddings by running `pip install gaia-cli[embeddings] --upgrade` if required. `gaia update` alone handles the core tools in seconds.

## The Initiate's Rite

Begin your journey through the registry with these ceremonial steps:

```bash
gaia init --user your-username
gaia update          # pull latest registry + CLI
gaia scan            # detect skills in your repository, render tree
gaia appraise        # inspect a skill card with status and actions
gaia promote web-search   # rank up scan-approved candidates
gaia push --dry-run  # preview intake submission
gaia push            # submit for maintainer review
```

Alternatively, launch the interactive TUI to navigate these steps visually:

```bash
gaia
```

`gaia scan` writes `generated-output/promotion-candidates.json`, renders your tree to `generated-output/tree.{html,md}`, and prints detected skills with fusion diagrams.

---

## CLI Reference

<!-- gaia:cli-start -->
```text
usage: gaia [-h] [--registry REGISTRY] [--global] [--version]
            {help,init,scan,pull,update,install,uninstall,tree,push,propose,version,mcp,release,graph,stats,appraise,promote,fuse,docs,lookup,update,skills}
            ...

Gaia Registry CLI

positional arguments:
  {help,init,scan,pull,update,install,uninstall,tree,push,propose,version,mcp,release,graph,stats,appraise,promote,fuse,docs,lookup,update,skills}
    help                Show command help
    init                Create or update local Gaia config
    scan                Scan configured paths for skill evidence
    pull                Refresh registry data from origin
    update              Pull latest registry and reinstall the CLI
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
    skills              Browse and manage named skills

options:
  -h, --help            show this help message and exit
  --registry REGISTRY   Path to a local Gaia registry checkout. Defaults to auto-resolved local or
                        global registry.
  --global, -g          Use global GAIA_HOME registry, ignoring any local .gaia/ config.
  --version, -v         Print the Gaia CLI version and exit.
  --canon               Show canonical registry data instead of local-first view.

Quick usage (run `gaia` with no args for the TUI):
  gaia                                            Launch interactive TUI
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

## Maintainer Hooks

Contributors who edit the canonical graph can install the repo-local hook once:

```bash
bash scripts/install-git-hooks.sh
```

The pre-commit hook checks version lockstep, applies a semantic bump from the commit message, regenerates registry artifacts, runs `gaia docs build`, and stages generated outputs.

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

## License

MIT: see [LICENSE](LICENSE).

---

*Graph is canonical. Everything else is a shadow.*


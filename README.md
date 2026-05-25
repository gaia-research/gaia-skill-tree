<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/marks/diamond-seal-preview.svg">
    <img src="docs/assets/marks/diamond-seal.svg" alt="The Diamond Seal" width="120" />
  </picture>
</div>

# Gaia - AI Agent Skill Registry

> The open, evidence-backed skill graph for AI agents: collect, evolve, and fuse capabilities into something legendary.
> Success means becoming the public record AI agent developers cite when making capability claims — the pkg.go.dev for agent skills.

[![Validate](https://github.com/mbtiongson1/gaia-skill-tree/actions/workflows/validate.yml/badge.svg)](https://github.com/mbtiongson1/gaia-skill-tree/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-c084fc.svg)](LICENSE)
[![Website](https://img.shields.io/badge/Website-gaia.tiongson.co-f59e0b)](https://gaia.tiongson.co/)
[![Gaia rank](https://gaia.tiongson.co/badges/mbtiongson1/rank.svg?repo=mbtiongson1/gaia-skill-tree)](https://gaia.tiongson.co/u/mbtiongson1/)
[![Gaia skills](https://gaia.tiongson.co/badges/mbtiongson1/skills.svg?repo=mbtiongson1/gaia-skill-tree)](https://gaia.tiongson.co/u/mbtiongson1/)
[![Powered by Gaia](https://gaia.tiongson.co/badges/powered-by-gaia.svg)](https://gaia.tiongson.co/badges/)

**Brand & product:** [PRODUCT.md](PRODUCT.md) · [CONTEXT.md](CONTEXT.md) · [DESIGN.md](DESIGN.md)

**Keywords:** AI Agent Skills • Skill Registry • LLM Ops • Agent Framework

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
  │     ├─ ○ intelligentcode-ai/parallel-execution  [2★]
  │     └─ ○ /embed-text  [0★]
  ├─ ◆ ruvnet/agentdb  [5★]
  │  ├─ ◇ ruvnet/agentdb-advanced  [3★]
  │  │  ├─ ○ ruvnet/agentdb-vector-search  [2★]
  │  │  └─ ◇ garrytan/learn  [2★]
  │  │     ├─ ○ garrytan/context-restore  [3★]

◆ mattpocock/skills  [6★]
  ├─ ◆ mattpocock/engineering  [5★]
  │  ├─ ◇ devin-ai/autonomous-swe  [1★]
  │  │  ├─ ○ garrytan/design-html  [0★]
  │  │  ├─ ○ /code-execution  [0★]
  │  │  └─ ○ /error-interpretation  [0★]
  │  ├─ ○ mattpocock/improve-codebase-architecture  [2★]
  │  ├─ ◇ mattpocock/to-issues  [3★]
  │  │  ├─ ○ /plan-decompose  [0★]
  │  │  └─ ○ /route-intent  [0★]
  │  ├─ ◇ mattpocock/to-prd  [4★]
  │  │  ├─ ○ glincker/readme-generator  [0★]
  │  ├─ ○ mattpocock/triage  [4★]
  │  ├─ ◇ mattpocock/ubiquitous-language  [2★]
  │  │  ├─ ○ /extract-entities  [0★]

Uniques — graph-isolated Basic Skills that reached elite mastery (4★+) through depth alone, with no fusion path forward.
  ◉ nousresearch/feed-monitoring  [4★ · Hardened]
  ◉ huggingface/huggingface-llm-trainer  [4★ · Hardened]
  ◉ ruvnet/hive-mind-coordination  [4★ · Hardened]
  ◉ huggingface/semantic-cache  [4★ · Hardened]

(211 skills total — see docs/tree.md)
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

Gaia uses a tiered star system (**0★–6★**) to rank agent capabilities.

| Symbol | Tier | Levels |
|--------|------|--------|
| ○ Basic | Primitive capability | 0★ → 4★ |
| ◉ Unique | Mastery without fusion | 4★ → 6★ |
| ◇ Extra | Composite workflow | 2★ → 4★ |
| ◆ Ultimate | Platform capstone | 5★ → 6★ |

Skills rank up through **verifiable evidence** (Class A/B/C) and can be demoted by **demerits**.

> **Detailed Policy:** See [META.md](META.md) for the full evidence methodology, ranking floors, and prestige requirements.

---

## Quickstart

**1. Install the CLI**

<!-- gaia:version-start -->
Current Gaia CLI version: `3.25.2`.

Python install:

```bash
pip install gaia-cli
```

npm wrapper alternative:

```bash
npm install -g @gaia-registry/cli
```
<!-- gaia:version-end -->
Python install:

```bash
pip install gaia-cli
```

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
            {help,init,scan,pull,update,install,uninstall,tree,push,propose,version,mcp,release,graph,stats,appraise,promote,fuse,docs,lookup,dev,validate,test,skills}
            ...

Gaia Registry CLI

positional arguments:
  {help,init,scan,pull,update,install,uninstall,tree,push,propose,version,mcp,release,graph,stats,appraise,promote,fuse,docs,lookup,dev,validate,test,skills}
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
    release             Bump version, commit, tag, and push to trigger GitHub Release
    graph               Generate and open the Gaia skill graph
    stats               Show registry health at a glance
    appraise            Inspect a skill card with status and actions
    promote             Promote a skill eligible for level-up
    fuse                Confirm a skill combination or promotion candidate
    docs                Documentation maintenance commands
    lookup              Look up a canonical skill and its named implementations
    dev                 Registry development and maintenance (requires writable registry)
    validate            Validate the Gaia registry
    test                Run self-verification tests
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
  gaia dev list [--generic] [--named] [--description] [--json]
  gaia dev merge <target> <source1> [source2...] [--named]
  gaia dev split <source> <target1> <target2>...
  gaia dev rename <old_id> <new_id>
  gaia dev calibrate <skill_id> <level>
  gaia dev add <name> [--id <id>] [--type <type>] [--description <desc>] [--named] [--contributor <user>] [--status <status>] [--title <title>] [--level <level>]
  gaia dev rm <skill_id>
  gaia dev link <target> <prereqs> [--reset]
  gaia dev reclassify <skill_id> <new_type>
  gaia dev update-named <skill_id> [--status <status>] [--generic-ref <ref>] [--suite-components <c1,c2...>]
  gaia dev evidence <skillId> <source> [--class A|B|C] [--evaluator <user>] [--date <date>] [--notes <notes>]
  gaia dev build
  gaia dev audit <skill_id>
  gaia validate [--intake] [--meta-sync]
  gaia test <suite>
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

<!-- gaia:badges-start -->
## Get your Gaia badge

Contributors with named skills can wear their rank in their own repo READMEs. Badges regenerate on every `gaia docs build`, so values track the live registry. The maintainer (`@mbtiongson1`) currently runs the three badges below in this repo's header.

| Variant | Badge |
|---|---|
| **Rank** — highest star earned (4★) | [![Gaia rank](https://gaia.tiongson.co/badges/mbtiongson1/rank.svg?repo=mbtiongson1/gaia-skill-tree)](https://gaia.tiongson.co/u/mbtiongson1/) |
| **Skills** — total unlocked (7) | [![Gaia skills](https://gaia.tiongson.co/badges/mbtiongson1/skills.svg?repo=mbtiongson1/gaia-skill-tree)](https://gaia.tiongson.co/u/mbtiongson1/) |
| **Powered by Gaia** — generic fallback for non-contributors | [![Powered by Gaia](https://gaia.tiongson.co/badges/powered-by-gaia.svg)](https://gaia.tiongson.co/badges/) |

Copy-paste for this repo:

```markdown
[![Gaia rank](https://gaia.tiongson.co/badges/mbtiongson1/rank.svg?repo=mbtiongson1/gaia-skill-tree)](https://gaia.tiongson.co/u/mbtiongson1/)
[![Gaia skills](https://gaia.tiongson.co/badges/mbtiongson1/skills.svg?repo=mbtiongson1/gaia-skill-tree)](https://gaia.tiongson.co/u/mbtiongson1/)
[![Powered by Gaia](https://gaia.tiongson.co/badges/powered-by-gaia.svg)](https://gaia.tiongson.co/badges/)
```

Template for any contributor:

```markdown
[![Gaia](https://gaia.tiongson.co/badges/<handle>/handle.svg?repo=<owner/name>)](https://gaia.tiongson.co/u/<handle>/)
[![Gaia rank](https://gaia.tiongson.co/badges/<handle>/rank.svg?repo=<owner/name>)](https://gaia.tiongson.co/u/<handle>/)
[![Gaia skills](https://gaia.tiongson.co/badges/<handle>/skills.svg?repo=<owner/name>)](https://gaia.tiongson.co/u/<handle>/)
```

Replace `<handle>` with your Gaia username and `<owner/name>` with the GitHub repo the badge is embedded in — the forthcoming edge validator flags badges in repos not on the contributor's `links.github` list. Preview every variant — including the single-line `@handle/skill · N★` identity badge — at [https://gaia.tiongson.co/badges/](https://gaia.tiongson.co/badges/).
<!-- gaia:badges-end -->

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

### Core Team

| Contributor | Role |
|---|---|
| [@mbtiongson1](https://github.com/mbtiongson1) | Creator and maintainer: graph design, CLI, MCP server, curation pipeline |
| [@rico-tiongson](https://github.com/rico-tiongson) | Collaborator: early feature contributions and ongoing pair programming |
| [@Juno](https://github.com/Juno) | Key contributor: graph browser expansion, function-calling skill, RAG pipeline evidence, and CLI DX improvements |

### Named Skill Contributors

| Contributor | Skills |
|---|---|
| [@ruvnet](https://github.com/ruvnet) | 48 — agentdb, flow-nexus, hive-mind-coordination, browser, and 44 others |
| [@garrytan](https://github.com/garrytan) | 47 — gstack ecosystem: browse, qa, ship, review, benchmark, learn, and 41 others |
| [@google-deepmind](https://github.com/google-deepmind) | 37 — alphafold, alphagenome, ensembl, clinvar, foldseek, and 32 others |
| [@mattpocock](https://github.com/mattpocock) | 20 — to-prd, triage, diagnose, tdd, zoom-out, grill-me, and 14 others |
| [@obra](https://github.com/obra) | 12 — superpowers ecosystem: systematic-debugging, dispatching-parallel-agents, and 10 others |
| [@intelligentcode-ai](https://github.com/intelligentcode-ai) | 8 — database-engineer, devops-engineer, security-engineer, and 5 others |
| [@huggingface](https://github.com/huggingface) | 7 — hf-cli, llm-trainer, datasets, transformers-js, and 3 others |

Community contributors (1–2 skills each): [@karpathy](https://github.com/karpathy), [@anthropic](https://github.com/anthropic), [@openai](https://github.com/openai), [@addy-osmani](https://github.com/addy-osmani), [@devin-ai](https://github.com/devin-ai), [@glincker](https://github.com/GLINCKER), [@spring-ai-alibaba](https://github.com/spring-ai-alibaba), [@pexp13](https://github.com/pexp13)

### Evidence & Curation

| Contributor | Contribution |
|---|---|
| [@balukosuri](https://github.com/balukosuri) | Evidence: community reproduction of Karpathy's autoresearch as a universal skill |
| [@kriptoburak](https://github.com/kriptoburak) | Evidence evaluator: x-twitter-automation evidence review |

### Bots

| Bot | Contribution |
|---|---|
| [@jules](https://github.com/google-labs-jules) | Named skills via Google Jules AI: langgenius suite (backend-code-review, frontend-code-review, e2e-cucumber-playwright, and 2 others) |
| @gaiabot | Internal Gaia bot: repo triage and docs-sync automation |
| @gemini-cli | Curation: generative-media, mathematical-animation, and other generic skills from Hermes ecosystem |

---

## Programmatic Management

The Gaia registry is programmatically managed. All meta shifts (adding, merging, splitting, adding evidence) must be performed via the [Gaia CLI](src/gaia_cli/). Hand-editing JSON nodes is deprecated to ensure schema integrity and automated timeline logging.

---

## Privacy

Gaia does not store personal information.

- **Skills are summarised, not stored.** `gaia scan` records capability type, level, and evidence class — never file contents, prompt text, or conversation history.
- **Only public repo links.** The registry stores your public GitHub username and a public repo URL when you explicitly submit a named skill. Nothing else.
- **Generalised by default.** Skill descriptions capture capability categories, not personal details about you or your agent's behaviour.
- **No telemetry.** The CLI and the static website collect zero analytics or usage data.

Full details: [PRIVACY.md](PRIVACY.md) · [gaia.tiongson.co/privacy.html](https://gaia.tiongson.co/privacy.html)

---

## License

MIT: see [LICENSE](LICENSE).

---

*Graph is canonical. Everything else is a shadow.*



## Resources

- [Quick Start](https://github.com/mbtiongson1/gaia-skill-tree#quick-start)
- [Dashboard](./hermes_agent/www/ADOPTION.html)
**Topics:** gaia-skill-tree, ai-agents, skill-registry, llm-ops, agent-framework

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/marks/diamond-seal-preview.svg">
    <img src="docs/assets/marks/diamond-seal.svg" alt="The Diamond Seal" width="120" />
  </picture>
</div>

# Gaia: Definitely not a skill marketplace

> Open and evidence-backed skill graph. The game is to name a skill to your repository--the best skill takes "origin"!
> Success means becoming the public record vibe coders cite when making capability claims.

### How does ranking work? Read [META.md](META.md) for a comprehensive list

[![Validate](https://github.com/gaia-research/gaia-skill-tree/actions/workflows/validate.yml/badge.svg)](https://github.com/gaia-research/gaia-skill-tree/actions/workflows/validate.yml)
[![License: Apache 2.0](https://static.scarf.sh/redirect?url=https://img.shields.io/badge/License-Apache%202.0-blue.svg&pixel_id=b8e05c84-1886-4b68-b80c-7b00cdb68f94)](LICENSE)
[![Website](https://static.scarf.sh/redirect?url=https://gaia.tiongson.co/&pixel_id=b8e05c84-1886-4b68-b80c-7b00cdb68f94)](https://gaia.tiongson.co/)

# Be like Rimuru

Main inspo for this repo. Basically stole the idea and applied it to agent skills.

![Rimuru Tempest](docs/assets/rimuru.gif)


# Get your badges! Some skills already curated.

[![Gaia rank](https://static.scarf.sh/redirect?url=https://gaia.tiongson.co/badges/_assets/mbtiongson1/rank.svg?repo=gaia-research%2Fgaia-skill-tree&pixel_id=b8e05c84-1886-4b68-b80c-7b00cdb68f94)](https://gaia.tiongson.co/u/mbtiongson1/)<br>
[![Gaia skills](https://static.scarf.sh/redirect?url=https://gaia.tiongson.co/badges/_assets/mbtiongson1/skills.svg?repo=gaia-research%2Fgaia-skill-tree&pixel_id=b8e05c84-1886-4b68-b80c-7b00cdb68f94)](https://gaia.tiongson.co/u/mbtiongson1/)

Generate yours at **[gaia.tiongson.co/badges/](https://gaia.tiongson.co/badges/)**.

**Brand & product:** [PRODUCT.md](PRODUCT.md) · [CONTEXT.md](CONTEXT.md) · [DESIGN.md](DESIGN.md)

**Keywords:** AI Agent Skill Registry • Evidence-Backed Skill Graph • Capability Graph • Model Context Protocol • AI Agents • Attribution

---

# Who maintains this?

Right now just me.

Truth is, Gaia will exist even without anyone sending their skills.

I built this because skills should be attributed to the people who proved them. Permanently, not just until the repo goes private.

So that means, its the developers who make skills maintaining this. I have a thorough curation process, and the dev community is evidence on why this works. As long as developers making skills exists, this registry will exist. This is open-source, so feel free to contribute! 

# The Gaia Skill Tree!

<!-- gaia:registry-start -->
```text
◆ mattpocock/skills  [5★]
  ├─ ◇ mattpocock/engineering  [4★]
  │  ├─ ◇ devin-ai/autonomous-swe  [3★]
  │  │  ├─ ○ garrytan/design-html  [3★]
  │  │  ├─ ○ /code-execution
  │  │  └─ ○ /error-interpretation
  │  ├─ ○ mattpocock/improve-codebase-architecture  [2★]
  │  ├─ ◇ garrytan/garrytan  [4★]
  │  │  ├─ ○ /plan-decompose
  │  │  └─ ○ ████████/ask-matt
  │  ├─ ◇ mattpocock/to-prd  [3★]
  │  │  ├─ ○ garrytan/retro  [3★]
  │  │  └─ ○ /plan-decompose  (↑ see above)
  │  ├─ ○ mattpocock/triage  [3★]
  │  ├─ ◇ mattpocock/ubiquitous-language  [3★]

◆ garrytan/gstack  [5★]
  ├─ ○ garrytan/office-hours  [3★]
  ├─ ○ garrytan/benchmark  [3★]
  ├─ ◇ garrytan/plan-eng-review  [3★]
  │  ├─ ○ garrytan/design-html  [3★]
  │  ├─ ○ /diff-content
  │  └─ ○ garrytan/benchmark  [3★]  (↑ see above)
  ├─ ○ pbakaus/impeccable  [4★]
  ├─ ◇ garrytan/garrytan  [4★]
  │  ├─ ○ /plan-decompose
  │  └─ ○ ████████/ask-matt
  ├─ ◇ garrytan/design-consultation  [3★]
  │  ├─ ◇ ████████/stagehand
  │  │  ├─ ○ /web-search
  │  │  └─ ○ /computer-use

(230 skills total — see docs/tree.md)
```
<!-- gaia:registry-end -->


### How Skills Fuse

Do a `gaia scan` and `gaia fuse` render in your terminal:

```text
  mattpocock/grill-me  ────────────┐
                                   ├──▶  mattpocock/grill-with-docs  ◇
  mattpocock/ubiquitous-language  ─┘
```

Basics fuse into Extras; Extras can fuse into Ultimates. Evidence powers each ascent.

> [!TIP]
> **New here?** The interactive tutorial at **[gaia.tiongson.co](https://gaia.tiongson.co/)** covers everything visually: skill tiers, the stars axis, The Initiate's Rite, and copy-paste commands.

---

## Stars

Gaia uses a tiered star system (**0★–6★**) to rank agent capabilities.

| Symbol | Tier | Levels |
|--------|------|--------|
| ○ Basic | Primitive capability | 0★ → 4★ |
| ◉ Unique | Mastery without fusion | 4★ → 6★ |
| ◇ Extra | Composite workflow | 2★ → 4★ |
| ◆ Ultimate | Platform capstone | 5★ → 6★ |

## Evidence

1. **Evidence Type** (provenance: one of 10 canonical types per the G7 Trust Taxonomy RFC

`arxiv`
`repo` or `repo-own`
`github-stars`
`github-stars-own`
`peer-review`
`social-signal`
`proxy-containment`
`benchmark-result`
`verifier-attestation`
`fusion-recipe`

2. **Evidence Grade**
S | A | B | C | ungraded

4. **Trust Magnitude**
This is the evidence grade at the Skill level.

> **Detailed Policy:** See [META.md](META.md) for the full evidence methodology, ranking floors, and prestige requirements.

> **Public Trust Ledger:** The Trust Ledger ranks every named skill by computed Trust Magnitude — see [`docs/trust/ledger/`](docs/trust/ledger/) (deployed at <https://gaia.tiongson.co/trust/ledger/> once the site rebuilds).

---

## Quickstart

**1. CLI

<!-- gaia:version-start -->
Current Gaia CLI version: `5.7.0`.

```bash
curl -fsSL https://gaia.tiongson.co/install.sh | sh
```

npm wrapper alternative:

```bash
npm install -g @gaia-registry/cli
```
<!-- gaia:version-end -->

<details>
<summary>pipx / Windows alternatives</summary>

**pipx:**
```bash
brew install pipx
pipx install gaia-cli
```

**Windows** (PowerShell — curl installer doesn't apply):
```powershell
py -m pip install gaia-cli
$env:PATH += ";" + (python -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user'))")
```

**Full Install (for devs)** (editable install with all extras):
```bash
git clone https://github.com/gaia-research/gaia-skill-tree.git
cd gaia-skill-tree
pip install -e ".[embeddings,dev,docs]"
```

The `dev` extra installs packaging/test tools such as `build` and `pytest`; without it,
packaging-specific tests are skipped locally with guidance to install developer extras.
</details>

**Update**
```bash
gaia update
```

**2. Init / Scan**

```bash
gaia init
```

```bash
gaia scan
```

Your repo will be scanned for existing skills. Everything will be in `.gaia` folder.

**3. Push to this repo!**

```bash
gaia push
```

A GitHub issue opens automatically. Don't worry, we thoroughly review every intake.

**4. MCP Server**

```bash
claude mcp add gaia -- npx @gaia-registry/mcp-server
```

If you wanna be fancy and do all sorts of agentic MCP goodness.

---

## Interactive TUI

```bash
gaia
```
Will open all sorts of commands in a nice way.

```bash
gaia skills
```

Navigate skills:
- **Fuzzy search** by name, description, or intent
- **View tree** (`^T`) and **run scan** (`^G`) without leaving the TUI
- **Install skills** with one keystroke
- Keyboard-native: `↑↓` navigate · `Enter` install · `q` quit

---

## CLI Reference

<!-- gaia:cli-start -->
```text
usage: gaia [-h] [--registry REGISTRY] [--global] [--version]
            {help,init,scan,fetch,pull,update,install,uninstall,share,tree,push,propose,version,whoami,login,logout,reset,graph,stats,appraise,promote,fuse,lookup,path,dev,skills}
            ...

Gaia Registry CLI

options:
  -h, --help           show this help message and exit
  --registry REGISTRY  Path to a local Gaia registry checkout. Defaults to auto-resolved local or
                       global registry.
  --global, -g         Use global GAIA_HOME registry, ignoring any local .gaia/ config.
  --version, -v        Print the Gaia CLI version and exit.
  --tui                Launch the TUI (Terminal User Interface).
  --canon              Show canonical registry data instead of local-first view.

Getting started:
  gaia init [--user <name>] [--scan <path>] [--yes] [-y]
  gaia scan [--quiet]
  gaia push [--dry-run] [--no-issue]
  gaia                        Open command selector
  gaia skills                 Launch skills explorer (TUI)

Daily commands:
  gaia tree [--named] [--title]
  gaia promote [<skillId>] [--all] [--name <name>]
  gaia appraise [<skillId>]
  gaia stats
  gaia pull
  gaia fuse <skillId> [--name <name>]
  gaia path <skillId> [--owned-only] [--json]
  gaia lookup <skillId>
  gaia graph [--format html|svg|json] [-o <path>] [--no-open]
  gaia propose [<skillId>] [--ultimate] [--target <name>] [--no-pr]

Skills:
  gaia skills <list|search|info|install|uninstall>
  gaia skills list [--exclude-pending]
  gaia skills search <query> [--exclude-pending]
  gaia skills info <skill_id> [--exclude-pending]
  gaia skills install <skill> [--global | --local]
  gaia skills uninstall <skill_id>

Share:
  gaia share [--user <name>] [-o <path>] [--stdout]
  gaia install <bundle.json|url>   Preview & install a shared tree (guided)

Utilities:
  gaia whoami
  gaia login                    Sign in with GitHub (device flow)
  gaia logout                   Sign out of GitHub (clears the local token)
  gaia version
  gaia update
  gaia dev mcp
  gaia dev release <patch|minor|major>
  gaia dev docs [--check]

Maintainer commands:  gaia dev --help

```
<!-- gaia:cli-end -->

---

## MCP Server Full Instructions

`@gaia-registry/mcp-server` connects Gaia to MCP-compatible agents (Claude Code, Cursor, VS Code, etc.).

| Agent | Install |
|-------|---------|
| Claude Code | `claude mcp add gaia -- npx @gaia-registry/mcp-server` |
| Any MCP client | Command: `npx`, args: `@gaia-registry/mcp-server` |

Set `GAIA_USER=your-github-username` and optionally `GITHUB_TOKEN` for PR tools. See [`packages/mcp/`](packages/mcp/) for full docs and agent-specific config examples.

---

## Agent Discovery

To help AI agents and automated clients discover and crawl the registry programmatically:
- **Registry graph:** [`/graph/gaia.json`](https://gaia.tiongson.co/graph/gaia.json)
- **Named skills:** [`/named/`](https://gaia.tiongson.co/named/)
- **Trust ledger:** [`/trust/ledger/`](https://gaia.tiongson.co/trust/ledger/)

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
Full policy/reviewer guidance: <https://github.com/gaia-research/gaia-skill-tree/wiki> (repo: <https://github.com/gaia-research/gaia-skill-tree.wiki.git>).

## Contributors

Thank you to everyone who has expanded the Gaia registry <3 You are the best!

### Core Team

| Contributor | Role |
|---|---|
| [@mbtiongson1](https://github.com/mbtiongson1) | Creator and maintainer: graph design, CLI, MCP server, curation pipeline |
| [@rico-tiongson](https://github.com/rico-tiongson) | Collaborator: early feature contributions and ongoing pair programming |
| [@MariTiongson](https://github.com/MariTiongson) | Collaborator: English localization (`docs/en/`) translation and layout updates |
| [@Juno](https://github.com/Juno) | Key contributor: graph browser expansion, function-calling skill, RAG pipeline evidence, and CLI DX improvements |
| [@milim-gaia](https://github.com/milim-gaia) | Core marketing agent: SEO optimization, copywriting, and agentic discovery alignment |
| [@nova-gaia](https://github.com/nova-gaia) | Core marketing agent: automated outreach campaigns, compliance, and ecosystem growth loops |

### Named Skills

| Developers | Skills |
|---|---|
| [@ruvnet](https://github.com/ruvnet) | 48 — agentdb, flow-nexus, hive-mind-coordination, browser, and 44 others |
| [@garrytan](https://github.com/garrytan) | 47 — gstack ecosystem: browse, qa, ship, review, benchmark, learn, and 41 others |
| [@google-deepmind](https://github.com/google-deepmind) | 37 — alphafold, alphagenome, ensembl, clinvar, foldseek, and 32 others |
| [@mattpocock](https://github.com/mattpocock) | 34 — to-prd, triage, diagnose, tdd, zoom-out, grill-me, and 28 others |
| [@obra](https://github.com/obra) | 12 — superpowers ecosystem: systematic-debugging, dispatching-parallel-agents, and 10 others |
| [@intelligentcode-ai](https://github.com/intelligentcode-ai) | 8 — database-engineer, devops-engineer, security-engineer, and 5 others |
| @[anonymous] | 7 — hf-cli, llm-trainer, datasets, transformers-js, and 3 others |

Community contributors (1–2 skills each): [@karpathy](https://github.com/karpathy), [@anthropic](https://github.com/anthropic), [@openai](https://github.com/openai), [@addy-osmani](https://github.com/addy-osmani), @[anonymous], [@glincker](https://github.com/GLINCKER), [@spring-ai-alibaba](https://github.com/spring-ai-alibaba), [@pexp13](https://github.com/pexp13)

### Evidence & Curation

| Contributor | Contribution |
|---|---|
| [@balukosuri](https://github.com/balukosuri) | Evidence: community reproduction of Karpathy's autoresearch as a universal skill |
| [@kriptoburak](https://github.com/kriptoburak) | Evidence evaluator: x-twitter-automation evidence review |
| [@fahimkarim01](https://github.com/fahimkarim01) | Curation: corrected pexp13/sentiment-analysis metadata links |

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

**Topics:** gaia-skill-tree, ai-agent, skill-registry, capability-graph, evidence-backed, agent-skills, attribution, model-context-protocol, open-source-ai, llm-ops, agent-framework

---

## License

Apache 2.0: see [LICENSE](LICENSE).

---

*Graph is canonical. Everything else is a shadow.*

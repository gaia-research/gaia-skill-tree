<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/marks/diamond-seal-preview.svg">
    <img src="docs/assets/marks/diamond-seal.svg" alt="The Diamond Seal" width="120" />
  </picture>
</div>

# Gaia - This is not a skill marketplace

> This is an open, evidence-backed skill graph. The game is to name a skill to your repository--the best skill takes "origin".
> Success means becoming the public record AI agent developers cite when making capability claims — the pkg.go.dev for agent skills.

### How does ranking work? Read [META.md](META.md) for a comprehensive list

[![Validate](https://github.com/mbtiongson1/gaia-skill-tree/actions/workflows/validate.yml/badge.svg)](https://github.com/mbtiongson1/gaia-skill-tree/actions/workflows/validate.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Website](https://img.shields.io/badge/Website-gaia.tiongson.co-f59e0b)](https://gaia.tiongson.co/)

# Name a skill, get a badge.

[![Gaia rank](https://gaia.tiongson.co/badges/_assets/mbtiongson1/rank.svg?repo=mbtiongson1%2Fgaia-skill-tree)](https://gaia.tiongson.co/u/mbtiongson1/)<br>
[![Gaia skills](https://gaia.tiongson.co/badges/_assets/mbtiongson1/skills.svg?repo=mbtiongson1%2Fgaia-skill-tree)](https://gaia.tiongson.co/u/mbtiongson1/)

Generate yours at **[gaia.tiongson.co/badges/](https://gaia.tiongson.co/badges/)**.

**Brand & product:** [PRODUCT.md](PRODUCT.md) · [CONTEXT.md](CONTEXT.md) · [DESIGN.md](DESIGN.md)

**Keywords:** AI Agent Skills • Skill Registry • LLM Ops • Agent Framework

---

# Who maintains this?

Truth is, Gaia will exist even without anyone sending their skills.

I built this because skills should be attributed to the people who proved them. Permanently, not just until the repo goes private.

So that means, its the developers who make skills maintaining this. I have a thorough curation process, and the dev community is evidence on why this works. As long as developers making skills exists, this registry will exist. This is open-source, so feel free to contribute! 

# The Skill Tree

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

Skills rank up through **verifiable evidence** scored on two axes — **Evidence Type** (provenance: one of 10 canonical types per the G7 Trust Taxonomy RFC, e.g. `arxiv`, `repo`, `repo-own`, `github-stars`, `github-stars-own`, `peer-review`, `social-signal`, `proxy-containment`, `benchmark-result`, `verifier-attestation`, `fusion-recipe`) and **Evidence Grade** (S / A / B / C, derived from the row's Trust Magnitude) — and can be demoted by **demerits**. The legacy single-axis Class A/B/C is deprecated and read only as a fallback during migration. The skill-level **Trust Magnitude** is now live in code (`src/gaia_cli/promotion.py` / `verification.py`).

> **Detailed Policy:** See [META.md](META.md) for the full evidence methodology, ranking floors, and prestige requirements.

> **Public Trust Ledger:** The Trust Ledger ranks every named skill by computed Trust Magnitude — see [`docs/trust/ledger/`](docs/trust/ledger/) (deployed at <https://gaia.tiongson.co/trust/ledger/> once the site rebuilds).

---

## Quickstart

**1. Install the CLI**

<!-- gaia:version-start -->
Current Gaia CLI version: `5.1.1`.

```bash
curl -fsSL https://gaia.tiongson.co/install.sh | sh
```

npm wrapper alternative:

```bash
npm install -g @gaia-registry/cli
```
<!-- gaia:version-end -->

Requires Python 3.8+. The script prefers `pipx` if available, otherwise falls back to `pip install --user` and prints a PATH hint if needed.

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

**Registry development** (editable install with all extras):
```bash
git clone https://github.com/mbtiongson1/gaia-skill-tree.git
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

**2. Initialise & scan**

```bash
gaia init
```

```bash
gaia scan
```

Detects skills your agent demonstrates.

**3. Push for review**

```bash
gaia push
```

A GitHub issue opens automatically. Maintainers review and promote; your name attaches at 2★. (or 1★ if no repo is linked).

**4. Optional: MCP Server**

```bash
claude mcp add gaia -- npx @gaia-registry/mcp-server
```

Any MCP-compatible client. See [packages/mcp/](packages/mcp/) for config examples.

---

## Interactive TUI

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
  gaia mcp
  gaia release <patch|minor|major>
  gaia docs build [--check]

Maintainer commands:  gaia dev --help

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

**Topics:** gaia-skill-tree, ai-agents, skill-registry, llm-ops, agent-framework

---

## License

Apache 2.0: see [LICENSE](LICENSE).

---

*Graph is canonical. Everything else is a shadow.*

---
name: gaia-wiki-sync
description: Sync the Gaia GitHub wiki with recent merged PRs, README, CONTRIBUTING, and schema changes. Use when the user asks to "update the wiki", "sync the wiki", "refresh the docs", or explicitly types /gaia-wiki-sync.
version: 1.0.0
---

# gaia-wiki-sync

Read all merged PRs and source-of-truth files since the last wiki update, then rewrite every affected wiki page and push directly to the wiki repo.

## What this skill does

### 0. Setup

Clone both repos if not already present:

```bash
git clone https://github_pat_<PAT>@github.com/mbtiongson1/gaia-skill-tree.git
git clone https://github_pat_<PAT>@github.com/mbtiongson1/gaia-skill-tree.wiki.git
```

Configure git identity in the wiki repo before any commit:

```bash
cd gaia-skill-tree.wiki
git config user.email "mbtiongson1@users.noreply.github.com"
git config user.name "Marco Tiongson"
```

### 1. Determine the sync window

```bash
cd gaia-skill-tree.wiki
git log -1 --format="%aI"
```

This is the cutoff date. Only changes merged after this date are in scope.

### 2. Read merged commits since cutoff

From the main repo:

```bash
cd gaia-skill-tree
git log --oneline --merges --after="<cutoff>"
git log --oneline --no-merges --after="<cutoff>" | head -80
```

Read the individual commit subjects to understand what changed. Key signal words to watch for:

| Signal | Affected wiki pages |
|---|---|
| `schema/`, `star-tiers`, level values | Rank-System, Schema-Reference, Contributing, Named-Skills, Skill-Types, Skill-Catalogue |
| `demerit` | Rank-System, Schema-Reference, Contributing, FAQ |
| `cli/`, `feat:`, new commands | CLI-Reference, Getting-Started, Named-Skills, Skill-Lifecycle |
| `docs/`, `readme` | Home, Getting-Started, Schema-Reference |
| `mcp` | MCP-Server, FAQ |
| `registry/`, path restructure | Home, FAQ, Schema-Reference, CLI-Reference, Skill-Lifecycle, Named-Skills |
| `feat/add-*-skills`, `review/` | Skill-Catalogue |
| `contributing` | Contributing |
| `version`, `release` | Home, Getting-Started, CLI-Reference |

### 3. Read source-of-truth files

Read every file relevant to the changes identified in step 2. Always read at minimum:

- `README.md` — authoritative quickstart, CLI reference block, repo layout block, version marker
- `CONTRIBUTING.md` — authoritative branch naming, PR checklist, evidence table, demerit policy
- `registry/schema/skill.schema.json` — skill node shape and constraints
- `registry/schema/namedSkill.schema.json` — named skill shape
- `registry/schema/meta.json` — level labels, rank labels, type symbols, demerit registry
- `registry/schema/combination.schema.json` — edge schema
- `src/gaia_cli/main.py` — authoritative CLI subcommand list (parse `subparsers.add_parser(...)` calls)

Also read as needed:
- `.agents/skills/*/skill.md` — if agent slash commands changed
- `packages/mcp/` — if MCP server changed

### 4. Read all current wiki pages

```bash
cat gaia-skill-tree.wiki/*.md
```

Build a mental model of what each page currently says before writing any updates.

### 5. Identify the minimal diff

For each change identified, determine the smallest set of wiki pages that need updating. Do not rewrite a page that is still accurate. A page needs updating if:

- It references old type names, level values, paths, or command names
- A feature it documents has changed behavior or been replaced
- A new feature is completely undocumented

### 6. Write updated pages

Rewrite only the affected pages. Follow these constraints:

**Style:**
- Use the same structure and heading hierarchy as the existing page.
- Keep examples concrete — copy real command signatures from `main.py` and README blocks verbatim.
- Table formatting: `|---|---|---| ` style.
- Do not add new sections that don't correspond to actual features.

**Accuracy rules:**
- Level values: always use star notation (`0★`–`6★`). Never write Roman numerals in new content.
- Type values: always `basic`, `extra`, `ultimate` in schema contexts. Display names: "Basic Skill", "Extra Skill", "Ultimate Skill".
- CLI commands: verify against `src/gaia_cli/main.py` — do not document commands that don't exist.
- File paths: verify against the actual repo layout before writing.
- Demerit IDs: must be exactly `niche-integration`, `experimental-feature`, `heavyweight-dependency`.

**Do not:**
- Invent commands or options not present in the codebase.
- Preserve stale content just because it was there before.
- Rewrite pages that are still accurate — leave them untouched.

### 7. Commit and push

```bash
cd gaia-skill-tree.wiki
git add -A
git commit -m "docs: sync wiki with <version> — <summary of changes>

<bullet list of what changed per page>"
git push origin master
```

The commit message body should list the substantive changes grouped by topic (not by page). Example:

```
- Star tier nomenclature: atomic→basic, composite→extra, legendary→ultimate; I–VI→0★–6★
- Demerit system: three canonical IDs, effective level floor, uniqueness constraint
- CLI: add update, stats, appraise, promote, propose, skills, graph, docs commands
- Repo: graph/→registry/, intake/→registry-for-review/, users/→skill-trees/
- MCP: @gaia-registry/mcp-server now published to npm
```

### 8. Report

After pushing, report:

- Commit SHA and URL
- Pages updated (list)
- Pages left untouched (list, with reason)
- Key changes summarized in 3–5 bullet points

## Constraints

- **Never push broken wiki pages.** If a section relies on information you couldn't verify from source files, omit that section or note it as TBD rather than guessing.
- **Read before writing.** Always read the current wiki page before rewriting it.
- **Wiki repo is separate from main repo.** Commits go to `gaia-skill-tree.wiki.git`, not to the main repo.
- **PAT is in memory.** Use the stored GitHub PAT for `mbtiongson1`. Do not hardcode it in any committed file.
- **Verify CLI from source.** Do not document commands based on README alone — always cross-check with `src/gaia_cli/main.py`.

## Repo locations

```
Main repo:  https://github.com/mbtiongson1/gaia-skill-tree.git
Wiki repo:  https://github.com/mbtiongson1/gaia-skill-tree.wiki.git
```

<div align="center">
  <img src="docs/assets/marks/diamond-seal.svg" alt="The Diamond Seal" width="120" />
</div>

# Contributing to Gaia

> Read [`PRODUCT.md`](PRODUCT.md) for audience and product purpose, and [`CONTEXT.md`](CONTEXT.md) for canonical terminology and the banned-synonyms lint.

Thanks for helping improve the Gaia skill graph.

This page is now a **contributor guide**. Detailed policy, reviewer playbooks, and deep troubleshooting now live in the GitHub Wiki repo.

---

---

## 1) Pick your workflow

### A) Submit discovered skills (recommended)

```bash
gaia push
```

Useful variants:

```bash
gaia push --dry-run
gaia push --no-pr
python3 scripts/validate_intake.py
```

Use this when proposing skills via `registry-for-review/skill-batches/*.json`.

### B) Update the canonical graph directly (Meta Shifts)

**DEPRECATED:** Hand-editing individual JSON files in `registry/nodes/` is now deprecated. 

**REQUIRED:** All meta shifts (adding, merging, splitting, adding evidence) MUST be done via CLI commands. This ensures:
- Programmatic schema integrity.
- Automated timeline logging for all changes.
- Smaller token footprints for AI agents.

```bash
# List skills to find targets
gaia dev list --generic

# Merge skills
gaia dev merge target-id source-id-1 source-id-2

# Split a skill
gaia dev split source-id target-id-1 target-id-2

# Add a new skill
gaia dev add "New Skill Name" --type basic --description "..." [--status awakened] [--title "Lore Title"] [--level "2★"]

# Reclassify a generic skill (change type)
gaia dev reclassify skill-id ultimate

# Add evidence
gaia dev evidence skill-id "https://example.com/demo" --class B --notes "..."

# Calibrate level
gaia dev calibrate skill-id "3★"

# Link skills (add prerequisites)
gaia dev link target-id prereq-id-1,prereq-id-2 [--reset]

# Update named skill frontmatter
gaia dev update-named author/skill --status awakened --suite-components c1,c2
gaia dev update-named author/skill --suite-ref capstone/suite
gaia dev update-named capstone/suite --installation-file path/to/setup.md

# Remove a skill
gaia dev rm skill-id

# Explicitly rebuild (useful after batching with --no-build)
gaia dev build
```

**Performance Tip:** Most `dev` commands support a `--no-build` flag. Use this during batch operations to skip the expensive documentation/graph regeneration until your final change is complete.

After any CLI meta shift, validate:
```bash
gaia validate
```
Note: The validator now checks the `registry/nodes/` directory by default.
Open a PR with the programmatic changes. The pre-commit hooks will automatically handle `gaia.json` assembly and documentation regeneration.

---

## 2) What files are source-of-truth?

- ✅ `registry/nodes/**/*.json` (**Programmatically managed via CLI**)
- ✅ `registry-for-review/skill-batches/*.json` (intake batches)
- ❌ **DO NOT** hand-edit `registry/nodes/*.json` unless absolutely necessary (fix typos).
- ❌ **DO NOT** edit `registry/gaia.json` directly — it is now an auto-generated artifact.
- ❌ Do not hand-edit generated docs/graph projections produced by build pipelines.

---

## 3) Branch naming (copy/paste)

| Prefix | Use for | Scope |
|---|---|---|
| `schema/...` | schema + terminology changes | `registry/schema/` only |
| `cli/...` | CLI / package code | `src/gaia_cli/`, `packages/`, `tests/` |
| `docs/...` | markdown/docs content | `docs/`, `*.md` |
| `design/...` | website UI assets | `docs/` HTML/CSS/JS |
| `review/gaia-push/...` | intake PRs | `registry-for-review/` |
| `review/meta/...` | registry curation | `registry/` (excluding schema) |
| `infra/...` | CI/tooling/config | `.github/`, `scripts/`, config |
| `dev/...` | experiments | unrestricted |
| `feat/...`, `fix/...` | general changes | unrestricted (schema rules still enforced) |

Hard rule: any schema file change must come from a `schema/...` branch.

---

## 4) Naming + evidence minimums

### Naming

- Skill IDs: `kebab-case` (`web-scrape`, `parse-json`)
- Display names: Title Case
- Skill types in graph: `basic`, `extra`, `ultimate`
- Keep skills vendor-agnostic

### Evidence by star level

Use the schema star notation for all new and updated registry entries. The old roman numeral labels are legacy-only and should not appear in `level` values.

| Level value | Rank label | Evidence floor |
|---|---|---|
| `0★` | Basic | no evidence required |
| `1★` | Awakened | no evidence required |
| `2★` | Named | ≥ 1 Tier C |
| `3★` | Evolved | ≥ 1 Tier B |
| `4★` | Hardened | ≥ 1 Tier B/A |
| `5★` | Transcendent | ≥ 1 Tier B/A |
| `6★` | Transcendent ★ | Tier A + peer review |

Legacy mapping for reviewers: `0`/`I` → `0★`/`1★`, `II` → `2★`, `III` → `3★`, `IV` → `4★`, `V` → `5★`, and `VI` → `6★`.

### Ultimate (`ultimate`) requirements

- At least 3 Tier A/B evidence items
- 2 maintainer approvals
- Must be `validated` at merge

### Demerits and effective level

- Demerits are allowed only on claimed levels `2★` and above.
- Allowed demerit IDs are canonical and schema-validated: `niche-integration`, `experimental-feature`, `heavyweight-dependency`.
- Each demerit demotes the skill by one star, floored at `1★`.
- Named skill claims stay constrained by canonical level requirements; demerits do not bypass evidence floors.

---

## 5) PR checklist (copy/paste)

- [ ] Correct branch prefix
- [ ] Edited only source-of-truth files
- [ ] Validation command(s) passed
- [ ] Evidence meets level/type requirements
- [ ] PR template selected
- [ ] PR title format:
  ```
  [type] skill-name — short description
  ```

Examples:
- `[basic] parse-csv — add CSV parsing primitive`
- `[extra] autonomous-debug — compose debug workflow`
- `[reclassify] web-scrape — promote with new evidence`

---

## 6) FAQ

**Q: I ran `gaia push`. Are proposed skills already in the Registry?**  
No. Intake batches are review artifacts until accepted skills are promoted into `registry/gaia.json`.

**Q: Where should long-form guidance go?**  
In the [Wiki](https://github.com/mbtiongson1/gaia-skill-tree/wiki) (review standards, curation heuristics, edge cases, troubleshooting).

---

## 7) Helpful links

- [README](../README.md)
- [Docs site](docs/index.html)
- [Governance](docs/GOVERNANCE.md)
- [Wiki](https://github.com/mbtiongson1/gaia-skill-tree/wiki) · [Wiki git repo](https://github.com/mbtiongson1/gaia-skill-tree.wiki.git)


---

## 8) Demotion and Reclassification Criteria

Use this section for reviewer decisions when a skill should be demoted, remapped, or declassified.

A review is required when evidence shows a skill is:
- **outdated** (implementation or evidence no longer reflects current behavior),
- **superseded** (a better canonical mapping or replacement now exists),
- **overpromoted** (current level exceeds demonstrated evidence tier), or
- supported by **insufficient usage evidence** for its assigned rank.

Reviewer workflow:
- Reviewers should use `/gaia-audit` before approving PRs that demote, declassify, remap, dispute, or re-promote a specific skill.
- Reviewers should use `/gaia-meta-audit` to build queues for stale links, unsupported promotions, possible duplicates, and broad mapping quality checks.

---

## 9) Unique Skill Promotion

A **Unique Skill** (◉) is a graph-isolated intrinsic skill that has reached elite mastery through individual depth rather than fusion/combination. Unique skills occupy their own tier between Extra and Ultimate in prestige.

### Eligibility Criteria

A basic skill may be promoted to `type: "unique"` when ALL of the following are true:

1. **Level ≥ 4★** (Hardened or above)
2. **Zero prerequisites** (`prerequisites: []`)
3. **Graph-isolated** — not referenced as a prerequisite by any other skill
4. **Has at least one named implementation** in `registry/named/`

### Promotion Workflow

```bash
# 1. Scan detects eligible skills automatically
gaia scan

# 2. Review unique-eligible candidates in the output
cat generated-output/promotion-candidates.json | grep '"promotionType": "unique"'

# 3. Promote via CLI (updates type field in gaia.json)
gaia promote <skill-id> --unique
```

### Validation Rules

The schema and validator enforce:
- Unique skills MUST be level 4★, 5★, or 6★
- Unique skills MUST have `prerequisites: []`
- Unique skills MUST NOT appear in any other skill's `prerequisites` array
- Unique skills CANNOT become extra or ultimate (no fusion path)
- Further level-up within unique (4★ → 5★ → 6★) follows standard evidence requirements

### Approval Requirements

- PRs promoting a skill to unique require maintainer approval
- Evidence must meet the standard floor for the skill's level (B/A class for 4★+)
- Reviewers should use `/gaia-audit` to verify isolation and evidence quality before approving

---

## 10) Ultimate Installation Templates

Ultimate suites (like `garrytan/gstack`) can define premium, multi-step installation instructions. The Gaia Skill Explorer automatically compiles these instructions into an interactive, tabbed setup interface.

### How to Author a Custom Suite Setup

To enable this tabbed setup UI for an ultimate suite, follow these three steps:

1. **Configure Frontmatter on the Capstone named skill:**
   On the main capstone named skill markdown file (e.g., `registry/named/garrytan/gstack.md`), add the list of constituent named skill IDs under `suiteComponents` in the frontmatter:
   ```yaml
   suiteComponents:
     - garrytan/browse
     - garrytan/cso
     - garrytan/design-review
     - garrytan/garrytan
     - garrytan/office-hours
   ```

2. **Link Constituent Skills:**
   On each constituent named skill markdown file (e.g., `registry/named/garrytan/browse.md`), specify the capstone suite reference using the `suiteRef` field in the frontmatter:
   ```yaml
   suiteRef: "garrytan/gstack"
   ```

3. **Write the Markdown Setup Guide:**
   In the `## Installation` section of the capstone skill, structure your guide using markdown headings (`##` or `###`) for each setup option. These headings automatically compile into tabs in the UI:
   - Headings with `Step 1` or `machine` map to a **Machine Setup** tab.
   - Headings with `Step 2` or `team` map to a **Team Mode** tab.
   - Headings with `openclaw` map to an **OpenClaw** tab.
   - Headings with `other` or `host` or `agent` map to a **Host Targets** tab.
   - Other headings fall back to a capitalized version of their first two words.

### Interactive Agent Target Selector

If a tab's markdown contains a table with columns `Agent` (or `Host`) and `Flag` (or `Argument`), and a setup code block (e.g. containing `./setup` or `./install`), the UI will automatically:
- Replace the static table with an interactive `<select>` dropdown.
- Render the available agent hosts and flags dynamically.
- Update the code block setup command in real-time when the user selects a target (appending `--host <flag>` correctly).
- Display the target's installation destination path dynamically.

### Editing and Submitting a PR

Use `gaia dev` commands — do not edit files manually or invoke build scripts directly (see §1.B).

1. **Set suiteComponents on the capstone skill:**
   ```bash
   gaia dev update-named garrytan/gstack \
     --suite-components "garrytan/browse,garrytan/cso,garrytan/design-review,garrytan/garrytan,garrytan/office-hours"
   ```

2. **Link each constituent skill back to the capstone:**
   ```bash
   gaia dev update-named garrytan/browse --suite-ref garrytan/gstack
   gaia dev update-named garrytan/cso    --suite-ref garrytan/gstack
   # …repeat for each component
   ```

3. **Replace the `## Installation` section from a markdown file:**
   ```bash
   gaia dev update-named garrytan/gstack --installation-file path/to/setup-guide.md
   ```
   The CLI automatically rebuilds docs after each command. Use `--no-build` on intermediate
   steps and run `gaia dev build` once at the end when batching multiple changes.

4. **Validate and open the PR:**
   ```bash
   gaia validate
   ```
   Create a `cli/` or `dev/` branch. If your branch also touches `CONTRIBUTING.md` or other
   files outside the `cli/` scope, add the **`skip-scope-check`** label to the PR so CI scope
   enforcement is bypassed.

---

## 11) Automated Maintenance

The registry is supported by several automated workflows:
- **Auto-Sync:** On every push to a branch, a GitHub Action automatically runs the versioning and regeneration scripts. You no longer need to run these manually before pushing.
- **Validation:** Every PR is automatically validated for schema correctness, DAG integrity, and evidence quality.

---

## 12) Named Skill Installability Policy

Named skills are only installable if they have a valid `links.github` field pointing to a public repository. This policy defines how curators and AI agents handle skills that lack one.

> **Suites are exempt.** Any skill with a `suiteComponents` list (e.g. `mattpocock/skills`, `garrytan/gstack`) installs by iterating its components — it does not need its own `links.github`. Do not flag suites as uninstallable and do not add `installable: false` to them.

### The rule: stars determine fate (non-suite skills only)

| Stars | No `links.github` | Action |
|-------|-------------------|--------|
| 0★–2★ | Allowed — kept as **registry-only** | Tag `installable: false` in frontmatter |
| 3★+ | **Not allowed** — must have a verified GitHub link | Demote to 2★ until a link is confirmed |

The rationale: a 3★ (Evolved) or higher skill claims reproducible, documented evidence (`≥ 1 Tier B`). A public repository link is the minimum verification for that claim. If no link exists, the skill has not met the bar for Evolved rank.

### Tagging registry-only skills

For skills at 2★ or below with no known public repository, add `installable: false` to the frontmatter:

```yaml
---
id: contributor/skill-name
name: Skill Name
status: named
level: "2★"
installable: false   # No public source repo — registry-only
# No links: block
---
```

This field is a curator signal. The install pipeline already rejects skills without `links.github`; the field makes the intent explicit and prevents repeated web-research attempts.

### Demotion workflow for 3★+ skills with missing links

```bash
# 1. Confirm no public repo can be found (web search, contributor contact)
# 2. Demote via CLI
gaia dev calibrate contributor/skill-name "2★"

# 3. Add installable: false flag via direct frontmatter edit
# registry/named/contributor/skill-name.md → add `installable: false`

# 4. Regenerate index
python scripts/generateNamedIndex.py

# 5. Validate
gaia validate
```

### Auto-rejection during intake (`gaia push`)

The following conditions auto-reject a named skill submission or trigger a mandatory reviewer flag:

| Condition | Outcome |
|-----------|---------|
| `links.github` missing and proposed level ≥ 3★ | **Rejected** — downgrade to 2★ required before merge |
| `links.github` present but URL is a bare repo root (no `/blob/branch/subpath`) | **Flagged** — reviewer must verify subpath or skill is undiscoverable |
| `origin: <URL>` (URL in boolean field) | **Rejected** — move URL to `links.github:`, set `origin: false` |
| `links.repo`, `links.docs`, `links.arxiv` (wrong key) | **Rejected** — only `links.github` is read by the installer |
| Suite component listed in `suiteComponents` with no `links.github` | **Flagged** — install will partially fail; must resolve before promotion |

### `links.github` URL format

URLs **must** use the `blob/` path format so the installer extracts the subpath correctly:

```yaml
# Correct — installer extracts subpath `.agents/skills/my-skill`
links:
  github: https://github.com/owner/repo/blob/main/.agents/skills/my-skill

# Broken — installs entire repo root, skill is undiscoverable
links:
  github: https://github.com/owner/repo
```

The install pipeline (`src/gaia_cli/install.py::_parse_github_url`) only recognises the `blob/` pattern. Using `tree/` (GitHub's directory URL format) is also not recognised — always use `blob/`.

### Skills currently exempt (registry-only, installable: false)

These **non-suite** skills are intentionally kept in the registry without a source link. Do not attempt to find links for them on repeated audit passes.

| Skill ID | Reason |
|----------|--------|
| `stanfordnlp/dspy` | Source is a Python library, no SKILL.md structure |
| `openai/few-shot-learning` | Research technique (arxiv); no installable skill repo found |
| `openai/self-consistency` | Research technique (arxiv); no installable skill repo found |
| `Taoidle/plan-decompose-gh-plan-cascade` | No public source repo confirmed |
| `changkun/plan-decompose-gh-wallfacer` | Wallfacer repo exists but skill not published |
| `pexp13/sentiment-analysis` | No public source repo confirmed |



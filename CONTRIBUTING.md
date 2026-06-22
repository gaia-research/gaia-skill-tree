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

Pick by what you're doing:

- **Submitting a skill you discovered?** Use `gaia push` (A).
- **A reviewer expanding or restructuring the registry?** Use the gated curation pipeline `/gaia-curate-chain` (B) — the recommended path for maintainer-run curation.
- **Making a one-off correction** (a single merge, split, reclassify, or evidence add)? Use the direct CLI meta shifts (C).

### A) Submit discovered skills

```bash
gaia push
```

Useful variants:

```bash
gaia push --dry-run
gaia push --no-issue
python3 scripts/validate_intake.py
```

Use this when proposing skills via `registry-for-review/skill-batches/*.json`.

### B) Curate with gates — `/gaia-curate-chain` (recommended for reviewers)

```
/gaia-curate-chain <topic-or-source>
```

Runs curation as six gated links — scope → research → design → human review → mutate → ship — one sub-agent per link, with a programmatic check between each. Source URLs are verified resolvable, schema shapes and the prerequisite DAG are checked **before** any mutation touches the registry, and `gaia dev validate` must pass before the branch ships. Prefer this whenever evidence quality and schema correctness matter; it is the default for maintainer-run registry expansion. See `.agents/skills/gaia-curate-chain/SKILL.md`.

The flat **`/gaia-curate`** (single linear pass, `.agents/skills/gaia-curate/`) still works and is quicker, but is **less gated** — reserve it for small, trusted, low-stakes batches. Both skills route every change through the same `gaia dev` commands documented in (C), so the underlying mutations are identical — the chain just checks them at each step.

### C) Update the canonical graph directly (Meta Shifts)

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

# Add evidence with G7 dual-axis fields (Evidence Type + Grade) and numeric payload
gaia dev evidence skill-id "https://example.com/paper" \
  --type peer-review --grade A --reviewers 3 --notes "NAR 2025"
gaia dev evidence skill-id "https://github.com/owner/repo" \
  --type github-stars-own --stars 12500 --skill-count 5 \
  --source-started-at 2024-11-03 --notes "stars at first-evidence date"
# Numeric payload flags by Evidence Type (I12):
#   --reviewers <n>          peer-review
#   --stars <n>              github-stars / github-stars-own
#   --skill-count <n>        github-stars-own (mothership discount divisor)
#   --views <n>              social-signal (views < 1000 → score 0)
#   --percentile <0..100>    benchmark-result (required; without it, score 0)
#   --containment <0..1>     proxy-containment
#   --source-started-at YYYY-MM-DD  pin evidence-row freshness baseline

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
gaia dev validate
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
| `schema/...` | schema + terminology changes | `registry/schema/`, `*.md` |
| `cli/...` | CLI / package code | `src/gaia_cli/`, `packages/`, `tests/`, `*.md` |
| `docs/...` | markdown/docs content | `docs/`, `*.md` |
| `design/...` | website UI assets | `docs/` HTML/CSS/JS, `*.md` |
| `review/gaia-push/...` | intake PRs | `registry-for-review/`, `*.md` |
| `review/meta/...` | registry curation | `registry/`, `*.md` |
| `infra/...` | CI/tooling/config | `.github/`, `scripts/`, `docs/*.html`, `*.md` |
| `dev/...`, `claude/...`, `codex/...`, `gemini/...` | experiments | unrestricted |
| `feat/...`, `fix/...` | general changes | unrestricted (schema rules still enforced) |

Hard rule: any schema file change must come from a `schema/...` branch.

---

## 4) Naming + evidence minimums

### Naming

- Skill IDs: `kebab-case` (`web-scrape`, `parse-json`)
- Display names: Title Case
- Skill types in graph: `basic`, `extra`, `ultimate`
- Keep skills vendor-agnostic

### Starless generic references vs. named skills

Generic skill references are **starless** — rank-less taxonomy nodes that carry **no stars of their own** (see [`CONTEXT.md`](CONTEXT.md) § Starless). Stars live only on the **named-skill** implementations that hang off a reference (its "children"); a starless ref's *effective rank* is the top star among those children. In the UI a starless reference renders as *generic* in italic, greyed-out styling, with "generic" kept as the technical descriptor. When you add or edit a generic reference via `gaia dev`, do not assign it a level — leave ranking to its named children.

A starless reference holds the **inherited capability pool**: capability-level (Class A / academic) evidence for the abstract capability itself, which every named child inherits as a baseline. Named skills then add their own implementation-specific evidence on top.

> **Upcoming meta shift.** Per-named evidence-floor enforcement (gating each named child on its own evidence) and finer-grained advanced evidence tiers are on the roadmap — forward-looking direction, not yet enforced. See [META.md](META.md#2-evidence-methodology-the-trust-stack).

### Evidence by star level (named implementations)

Taxonomy definitions, evidence floors, and ranking rules have been consolidated.

> **Source of Truth:** See [META.md](META.md) for the full evidence methodology, star tiers, and ranking rules.

Named skills now read evidence `grade` (S/A/B/C, S strongest) as the primary floor signal per the G7 Trust Taxonomy RFC (`founder/handovers/G7_TRUST_TAXONOMY_RFC.md`), with fallback to the deprecated `class` field for existing rows during the migration window. Grade A is not Class A — never conflate the two axes. See [META.md §2](META.md#2-evidence-methodology-the-trust-stack) for the full dual-axis spec.

The skill-level **Trust Magnitude** (the unbounded set-bonus aggregate that derives the Overall Trust Grade) is computed live from each skill's evidence inventory. Browse the public ranking at [`docs/trust/leaderboard/`](../docs/trust/leaderboard/) (deployed at <https://gaia.tiongson.co/trust/leaderboard/>) to see current S/A/B/C tier counts and the top-scoring skills before opening a calibration PR.

### Ultimate (`ultimate`) requirements

See [META.md](META.md#42-ultimate--apex-pathways) for the detailed fusion and origin requirements for Ultimate skills.

### Demerits and effective level

See [META.md](META.md#3-effective-level--demerits) for demerit IDs and effective level calculation rules.

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
- [Governance](GOVERNANCE.md)
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

> **Transparency Mandate — every rank change is on the record.** A demotion or
> promotion is not finished until it has left an auditable **timeline event**.
> Never hand-lower a level (in a `.md` or a `skill-tree.json`) without recording
> a `demote`/`rank_up` event that says *why* — prefer the CLI precisely because
> it logs it for you (`gaia dev timeline … --action demote --notes "…"`, or the
> `/gaia-trace-timeline` skill to reconcile drift). A silent rank change is a
> transparency failure, and the **Transparency Gate** (§11) will fail the build.

---

## 9) Unique Skill Promotion

See [META.md](META.md#12-skill-types) for eligibility criteria. Use the CLI to promote:

```bash
gaia promote <skill-id> --unique
```

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
   gaia dev update-named garrytan/gstack --no-build \
     --suite-components "garrytan/browse,garrytan/cso,garrytan/design-review,garrytan/garrytan,garrytan/office-hours"
   ```

2. **Link each constituent skill back to the capstone:**
   ```bash
   gaia dev update-named garrytan/browse --suite-ref garrytan/gstack --no-build
   gaia dev update-named garrytan/cso    --suite-ref garrytan/gstack --no-build
   # …repeat for each component
   ```

3. **Replace the `## Installation` section from a markdown file:**
   ```bash
   gaia dev update-named garrytan/gstack --installation-file path/to/setup-guide.md --no-build
   gaia dev build   # single rebuild after all edits are complete
   ```

4. **Validate and open the PR:**
   ```bash
   gaia dev validate
   ```
   Create a `cli/` or `dev/` branch. If your branch also touches `CONTRIBUTING.md` or other
   files outside the `cli/` scope, add the **`skip-scope-check`** label to the PR so CI scope
   enforcement is bypassed.

---

## 11) Automated Maintenance

The registry is supported by several automated workflows:
- **Gated curation (`/gaia-curate-chain`):** The recommended pipeline for reviewer-run registry expansion (see §1B). Six gated links with a programmatic check between each; the flat `/gaia-curate` remains available for low-stakes batches but is less gated.
- **Auto-Sync:** On every push to a branch, a GitHub Action automatically runs the versioning and regeneration scripts. You no longer need to run these manually before pushing.
- **Validation:** Every PR is automatically validated for schema correctness, DAG integrity, and evidence quality.
- **Transparency Gate (`scripts/validate_timelines.py`):** Enforces the Transparency Mandate (§8) — every named skill a contributor owns must be charted at its *current* registry rank, with a timeline event explaining it. A silent demotion/promotion (a rank change with no `demote`/`rank_up` event on the user tree) fails the build. Runs in `gaia dev validate` and the release workflow; reconcile drift with `/gaia-trace-timeline` (or `scripts/trace_timeline.py --all --apply`). A sibling **Redaction Gate** (`scripts/validate_redaction.py`) likewise proves ≤1★ handles stay withheld (see META.md §1.3).
- **Monthly Meta Sweep (`/gaia-meta-sweep`):** Once per month a maintainer runs the `/gaia-meta-sweep` skill (see `.claude/skills/gaia-meta-sweep/SKILL.md`) to audit the entire registry against [META.md](META.md). The sweep produces a journal-style report under `docs/meta/reports/<YYYY-MM-DD>-meta-audit.html` plus a machine-readable `<slug>.findings.json` and `<YYYY-MM>-timeline.json`. See §13 below for the cadence and operating procedure.
- **Defensive Security Scanner (`gaia push` / `gaia dev verify`):** Flags named skills carrying obviously hostile patterns across five detector categories: shellExec, destructiveFs, outboundNet, promptInjection, and credentialHarvesting. High-severity findings block `gaia push` unless overridden with both `--allow-unsafe` and `--reason "<text>"` (both flags are required; `--allow-unsafe` alone is rejected). `gaia dev verify` runs the scanner in read-only mode and prints findings without blocking. See `src/gaia_cli/securityScanner.py`.
- **4-tier Verification Workflow (`gaia skills info` / `gaia dev verify-tier`):** Each named skill resolves to up to four stacking quality dimensions — community-verified, benchmark-verified, security-reviewed, and enterprise-ready — which are independent, not a strict ladder. `gaia skills info <id>` surfaces the highest passing tier with a per-tier pass/fail breakdown. `gaia dev verify-tier <id>` recomputes and writes `verification.tier` and `verification.tierEvaluatedAt` to the skill record. See [META.md §4](META.md#4-governance--promotion) and `src/gaia_cli/verification.py`.

---

## 13) Monthly Meta Sweep (Cadence)

Gaia runs a **monthly registry-wide audit** to keep the canonical graph aligned with [META.md](META.md) — the source of truth for star tiers, evidence classes, demerits, Origin attribution, and Semantic Fusion (§6.2).

### Cadence

| When | Who | Output |
|---|---|---|
| **First Monday of each month** (or the next business day) | Designated meta auditor for the month (see rotation in the Wiki) | New report at `docs/meta/reports/<YYYY-MM-DD>-meta-audit.html` |

The sweep is required even when the prior month was quiet — it produces the timeline JSON that the public Skill Explorer charts against, so a missing month leaves a visible gap.

### How to run

```bash
# 1. Start from a clean main
git checkout main && git pull

# 2. Branch under review/meta/ (CLAUDE.md §Branch Naming)
git checkout -b review/meta/<YYYY-MM>-meta-sweep

# 3. Invoke the skill in Claude Code
/gaia-meta-sweep
```

The skill orchestrates a 5-phase Workflow:

1. **Survey** — 12 parallel agents, one per audit dimension from META.md §2.4 + §3 (Star Bar, Liveness Heartbeat, Origin attribution, level overshoot, brand-coupled IDs, missing demerits, installability, placeholder bodies, `testuser` timelines, Champion clusters, Unique isolation, evidence Class mismatch).
2. **Fuse** — surface Semantic Fusion candidates per META §6.2. Ultimate-tier fusions (≥10k★) are **not** in scope here — route those to `/gaia-fuse-full-suite`.
3. **Propose** — propose new generic skill IDs for the schema where repeated named skills lack a canonical generic to map to.
4. **Verify** — adversarial 3-skeptic pass per finding; only findings ≥2/3 of skeptics agree are real survive.
5. **Report** — emit the HTML report (LaTeX-journal layout matching the existing 2026-05-25 report), the timeline JSON, and the findings JSON.

### What the report must contain

Every entry must be **tagged with the META.md section** that justifies it:

- Demotions / calibrations → §1, §2, §3
- Origin flips → §4.1
- Semantic Fusion candidates → §6.2
- New generic skill proposals → §1
- Demerits → §3
- Star Bar / Liveness — §2.2, §2.4

A "Mutations Applied" or "Mutations Proposed" section lists every `gaia dev` command produced by the sweep, so reviewers can replay or reject them individually.

### Follow-up

- Each P0/P1 finding should be opened as a focused `/gaia-audit` correction (one PR per target).
- Each accepted Semantic Fusion candidate becomes a separate `review/meta/<new-generic-id>` PR.
- Each new generic skill proposal goes through a `schema/...` branch (see §3 Branch naming) — schema changes are gated by the schema branch policy.

### Reference run

The May 2026 sweep (`docs/meta/reports/2026-05-25-programmatic-registry-audit.html` + PR #525) is the canonical worked example. It exercised all 12 audit dimensions on mbtiongson1's 14 named skills and produced 2 removals, 2 generic renames, 1 new Extra fusion generic, 5 `genericSkillRef` remaps, 1 origin flip, 1 level demotion, 9 link fixes, and 24 placeholder/timeline backfills.

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
gaia dev validate
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

---

## Consuming the registry without a clone

There are three ways to access the canonical registry data without cloning the repository.

### Bundled snapshot (installed wheel)

Every PyPI release of `gaia-cli` bundles a registry snapshot inside the wheel at `src/gaia_cli/data/registry/`. The snapshot is refreshed on every `vX.Y.0` release (minor or major). Patch releases (`vX.Y.Z` where Z is not 0) inherit the snapshot from the most recent minor/major release.

When the CLI uses the bundled snapshot, it prints a one-time warning to stderr:

```
Warning: Using bundled registry snapshot from <DATE>. Run `gaia pull` for the latest.
```

### Latest between releases (`gaia pull`)

Run `gaia pull` to download the latest registry from the most recent GitHub Release and save it to `.gaia/registry/`. The CLI will use this local copy on subsequent invocations.

`gaia pull` chains `gaia fetch` (download the release asset) with `gaia scan` (update your skill tree). To download without scanning, run `gaia fetch` alone.

### Direct download

The registry artifacts are attached to every GitHub Release as a tarball:

```
https://github.com/mbtiongson1/gaia-skill-tree/releases/latest/download/gaia-artifacts.tar.gz
```

The tarball contains `registry/gaia.json`, `registry/named-skills.json`, `registry/named/`, and graph artifacts. A SHA256 checksum is published alongside:

```
https://github.com/mbtiongson1/gaia-skill-tree/releases/latest/download/gaia-artifacts.tar.gz.sha256
```

Verify the download:

```bash
sha256sum -c gaia-artifacts.tar.gz.sha256
```



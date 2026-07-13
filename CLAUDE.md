# CLAUDE.md

Guidance for AI coding agents working in this repository.

## Workflow Discipline

- Stay focused on the requested task (merge, monitor, audit). Do NOT deviate into debugging/exploration unless explicitly asked.
- Read key files BEFORE running exploratory bash commands.
- When asked to monitor/loop CI checks, monitor — do not switch to debugging failures unless instructed.

## Sprint Completeness — no follow-ups

Every sprint ships COMPLETE; a sprint does NOT generate follow-up issues.

- Do NOT close a sprint by filing `follow-up`/`tech-debt` issues carrying the sprint's own unfinished work. That work belongs in the sprint.
- When staging, enumerate everything the sprint touches and pre-scope any spillover as an additional PR in the same sprint. Land it before declaring done.
- "Done" = nothing left a reasonable reviewer would call a direct consequence of the sprint's changes. Rolling-window CI false positives, doc drift, deferred surface states, and CLI gaps the sprint introduced are all in-scope.
- Genuinely new, out-of-scope work discovered during a sprint may still be filed (normal backlog hygiene). Only the sprint's own remainder is forbidden as "future work."

## Graphify

Approved codebase-analysis tool, used as-needed (deep architecture audits, dependency mapping, cross-cutting impact). Costs real token spend — invoke only when a structural code graph is warranted. Tracked outputs: `graph.json`, `graph.html`, `manifest.json`, `GRAPH_REPORT.md`, `cost.json`. Cache `graphify-out/cache/` is gitignored.

## Git Workflow

Never push directly to main.

### Branch & Worktree Conventions

- Confirm the target branch/worktree before editing. If user references a specific branch (e.g. `fix/links-3d-graph`), push there — do not create a new design branch.
- When editing in a worktree, verify CWD matches the requested worktree first.

## Branch Scope — infra/ allowlist

`infra/` branches may touch `docs/badges/` (registry.json, _assets/) in addition to the standard `.github/`, `scripts/`, `*.md`, `docs/*.html`. Codified in `.github/workflows/branch-scope.yml` and applies permanently — badge restore/guard commits belong on `infra/` branches and must not require `skip-scope-check` every time.

## Branch Scope — schema/ allowlist

`schema/` branches may touch `registry/schema/` **and** `src/gaia_cli/data/registry/schema/` (the bundled snapshot the pip-installed CLI reads) in addition to `*.md`. The two schema directories must move in lockstep — `scripts/validate.py` "Meta sync check" fails when they diverge — so a schema PR touching only one side always trips CI. Codified in `.github/workflows/branch-scope.yml`; do not require `skip-scope-check` for routine schema bumps.

## Branch Scope — review/meta/ allowlist

`review/meta/` branches may touch `docs/` in addition to `registry/` (excluding `registry/schema/`) and `*.md`. Required by Guard E: any change to `registry/nodes/` or `registry/named/` MUST include the regenerated Class S artifacts (`docs/graph/*`, `docs/api/v1/*`, per-user profile pages, badges) in the same PR. Codified in `.github/workflows/branch-scope.yml`; do not require `skip-scope-check` on every curation PR just to land the `gaia dev docs` output.

## Redaction Exemptions — ordained, do not re-litigate

The following 8 contributor handles are **permanently exempt** from Section D badge-dir violations (`validate_redaction.py` + `build_docs.py`). Their `docs/badges/_assets/<handle>/` directories are kept intentionally. Do NOT remove them from the exemption list, do NOT delete their dirs, do NOT open issues about them. If any of them reach 2★ their dir becomes valid anyway and the exemption becomes a no-op.

Exempted handles: `0xdarkmatter`, `Taoidle`, `browserbase`, `changkun`, `glincker`, `gooseworks`, `intelligentcode-ai`, `yonatangross`

To add a new exemption: edit `REDACTION_BADGE_DIR_EXEMPTIONS` in **both** `scripts/validate_redaction.py` and `scripts/build_docs.py` (two frozensets, keep in sync).

## Edit Safety

- After Edit/Write on JS/HTML, read the file back to verify no duplication or merged lines; run syntax check if available.
- Avoid hex color fallbacks; use design tokens only (CI guard rejects hex).
- When bumping assets, update cache-bust version strings across all referencing pages.

## Design Entrypoints — plan before you ship

**Load-bearing invariant:** every new user-facing page/section MUST plan its entrypoints during the design pass — main nav, footer, homepage, `window.GAIA_MOUNTS`, cross-page links, and cache-busting — and the PR body MUST include an "Entrypoints" section listing which were touched or explicitly waived (design-review agents bounce PRs missing it). Shipping a section with no way to reach it from the homepage is a broken feature. CI Guard D enforces the `mounts.js` registration.

See `docs/agents/design-entrypoints.md` for the full 6-point checklist and rule of thumb.

## Deferred-surface convention — ship the bridge state, disclose the bridge state

**Load-bearing invariant:** when a user-visible surface ships to satisfy a kill criterion but its design register is slated for a later sprint, the interim state MUST be disclosed on the surface with a `.wip-banner` linking to a tracking issue that carries the target sprint label — never silently ship a bridge state, and never add a banner without a tracking issue. Do NOT use it to hide unfinished work with no sprint home (that's a defect; file and fix).

See `docs/agents/deferred-surface-convention.md` for the three preconditions, what ships, what NOT to do, and the reference implementation.

## Fixed-nav clearance — every top-level page container must clear ~58px

**Load-bearing invariant:** every page-level container directly under `<body>` MUST provide its own top clearance below the fixed nav (~58px). Use the exact value ladder — base **5rem (80px)**, desktop **6rem (96px) for thin strips** or **8rem (128px) for full page shells**. There is no global `body { padding-top }` and there won't be. Do not invent other values.

See `docs/agents/fixed-nav-clearance.md` for the CSS pattern, reference implementations, anti-patterns, and verification steps.

## Testing

Always run the test suite after changes and fix regressions before reporting completion.

## Data & Permissions

Never modify data files (skill levels, slot data, schema fixtures) without explicit approval; ask before treating data as invalid.

## Project Architecture / Data Model

Skill levels are stored in slots, not on skill objects — account for this when computing stats, trees, and breakdowns.

## Commands & Setup

See [DEV.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/DEV.md) for local setup (virtualenv, pip, pipx), common commands, and testing.

## Current Layout

| Area | Path | Notes |
|---|---|---|
| Curated registry | `registry/` | Maintainer-reviewed data and public generated catalogs |
| Canonical graph | `registry/gaia.json` | Class P (gitignored — regenerated locally by gaia dev docs; bundled in wheels on vX.Y.0 releases). NOT served to browsers directly. |
| Site graph assets | `docs/graph/` | Class S (tracked in git — served as-is by GitHub Pages from main:/docs at gaiaskilltree.com). Includes gaia.json, named/index.json, gaia.gexf, gaia.svg. Regenerated by `gaia dev docs` alongside registry/gaia.json. |
| Named skills | `registry/named/` | Markdown implementations grouped by contributor |
| Named index | `registry/named-skills.json` | Generated by `scripts/generateNamedIndex.py` |
| Schemas | `registry/schema/` | JSON schemas |
| Review intake | `registry-for-review/skill-batches/` | `gaia push` writes draft batches here |
| User trees | `skill-trees/<username>/skill-tree.json` | User-owned progression state |
| Local output | `generated-output/` | Gitignored scan/render artifacts |
| Python CLI | `src/gaia_cli/` | Entry `main.py`, dynamic command discovery from `commands/`. Mutating ops in `commands/dev/` (evidence, verify, merge, calibrate). `versioning.py` keeps pyproject.toml, package.json files, registry/gaia.json in lockstep. |
| Slash-naming helpers | `src/gaia_cli/formatting.py` | Slash-naming formatters, RANK_COLORS, tier colors |
| Local-first context | `src/gaia_cli/localContext.py` | Merges user tree + scan results + named skill map into `LocalContext` |
| npm wrapper | `packages/cli-npm/` | `@gaia-registry/cli` — Node.js wrapper publishing `gaia` to npm, executing the local Python binary. |
| MCP server | `packages/mcp/` | `@gaia-registry/mcp-server` — exposes registry via MCP. Key: `src/config/merger.ts`, `src/daemon.ts`, `src/index.ts` (tools `gaia_lookup`, `gaia_suggest`, `gaia_scan_context`, `gaia_my_tree`). |

```bash
# Meta Review (CLI-ONLY)
gaia dev list --generic --named
gaia dev add "Skill Name" --type basic --description "At least 10 chars description"
gaia dev merge target-id source-ids...
gaia dev split source-id target-ids...
gaia dev evidence skill-id "url" --type repo-own --commits N --contributors N
gaia dev fuse generic-id --name "..." --type ultimate --prereqs a,b,c \
              --named-capstone contributor/slug --suite-components a,b,c
```

## Generated Artifacts — Class P vs Class S

Two categorically different classes of generated files. The distinction is load-bearing — confusing them once took the site dark for 12 hours (PR #798 retro, 2026-06-22).

| Class | Members | Storage | Why |
|---|---|---|---|
| **Class P** (pipeline-internal) | `registry/gaia.json`, `registry/named-skills.json`, `registry/gaia.gexf`, `registry/gaia.svg`, `registry/layouts_3d.json`, `registry/real-skills.{json,md}`, `base_gaia.json`, `src/gaia_cli/data/registry/*` | **Gitignored.** Regenerated from `registry/nodes/` + `registry/named/` by `gaia dev docs`. Bundled into PyPI wheels at vX.Y.0 minor releases. | Pipeline output consumed only by tooling. Tracking would manufacture merge conflicts on every PR. |
| **Class S** (site-served) | `docs/graph/gaia.json`, `docs/graph/named/index.json`, `docs/graph/gaia.gexf`, `docs/graph/gaia.svg` | **Tracked in git.** Regenerated alongside Class P by `gaia dev docs`. Marked `linguist-generated=true` in `.gitattributes` so PR diffs collapse them. | GitHub Pages publishes `main:/docs` as-is. These ARE the bytes the website serves. Untracking them takes the site dark. |

**Rule of thumb:** if browsers fetch the file at runtime, it's Class S and belongs in git. If only `gaia` tooling reads it, it's Class P and stays gitignored.

When you change `registry/nodes/` or `registry/named/`, run `gaia dev docs` and commit both the Class S artifacts (`docs/graph/*`) and the source change in the same PR. CI Guard E in `docs-cohesion.yml` enforces this.

Footgun history: commit `de3e77f7e` untracked both classes; auto-sync's `gaia dev release --sync` had a hard-coded `git add registry/gaia.json` that died once the path was gitignored → site dark 12h. See `founder/handovers/EPIC780_OPTION_A_DECISION.md`.

## Programmatic-First Policy

**All meta shifts (merging, splitting, adding skills, adding evidence) MUST be done via CLI commands.** Manual edits to `registry/nodes/` are deprecated to ensure programmatic schema integrity and automated timeline logging. AI agents must prioritize these tools over direct file manipulation.

### CLI Pre-Flight Rule (CRITICAL — added 2026-06-20)

**Every mutating `gaia dev` subcommand MUST validate the schema invariant it would produce BEFORE writing.** A CLI that ships a state failing CI is one the next agent works around; each gap erodes the registry irreversibly. When adding/extending a `gaia dev` verb:

1. **Check the schema constraint** the proposed write would violate. Examples: `update-named --status named` requires `title` or `catalogRef` (frontmatter or flag) — reject with a clear error rather than write a state that fails `gaia validate`; `dev evidence` numeric flags must validate ranges; `dev calibrate` to 3★+ must check the skill has a verified `links.github` blob URL (META.md §2.4 "Star Bar").
2. **Surface the gap, don't paper over it.** If the CLI can't satisfy the request without an invalid state, error out with the path to the right command. NEVER fall back to direct frontmatter edits — those skip timeline logging (META.md §5) and pollute the audit trail.
3. **If the right command doesn't exist**, file an issue tagged `CLI` + `tech-debt`. Do not let an agent "work around it" — that's how 14 broken-state mattpocock skills got past local validate (PR #754 retro, 2026-06-20).

Non-negotiable: the CLI is the canonical mutation interface; if it lets bad states through, the gap is the bug.

### Skill-Tree Timeline — Strict CLI-Only

Every change to a user's `skill-trees/<username>/skill-tree.json` **must** be accompanied by a timeline event so progression history is auditable. Use the CLI — never hand-edit the `timeline` array.

| Operation | CLI command |
|---|---|
| Unlock / rank up via scan | `gaia scan` then `gaia promote <skillId>` |
| Fuse skills | `gaia fuse <skillId>` |
| Append event at current time | `gaia dev timeline <skillId> --user <username> --action <action> --notes "..."` |
| Backfill a historical event | `gaia dev timeline <skillId> --user <username> --action <action> --notes "..." --timestamp "YYYY-MM-DDTHH:MM:SSZ"` |

The `--timestamp` flag accepts ISO 8601 (e.g. `2026-03-01T00:00:00Z`); without it, current UTC is used. Backfilled events auto-sort chronologically.

**Known CLI gap (flag in PRs, do not silently hand-edit):** No `gaia remove-skill` / `gaia demote` command — skill removal from the user tree has no dedicated verb. Workaround: direct JSON edit to remove from `unlockedSkills`, then `gaia dev timeline <skillId> --user <username> --action demote --notes "..."` to log it.

Closed as of v5.0.11 (2026-06-23): `gaia dev timeline --user <username>` writes to the user tree (not the registry node); `--timestamp` ISO 8601 backfills; `--action demote` is in the enum. Only skill removal still lacks a dedicated verb (workaround above).

## CLI Shape

Top-level (lifecycle-oriented): `init`, `scan`, `pull`, `push`, `appraise`, `promote`, `release`, `version`, `whoami`, `mcp`, `tree`, `graph`, `docs`, `update`, `share`, `help`.

Named skill actions under `gaia skills`: `list`, `search`, `install`, `uninstall`, `info`. Old flat verbs are intentionally removed.

### Share bundles (`gaia share` / `gaia install <bundle>`)

`gaia share` exports a self-contained **share bundle** JSON (`generated-output/share/<user>-share-bundle.json`, or `--stdout`): a snapshot of the sharer's tree, a flat install manifest pointing each skill at its source repo via `links.github` (`blob/branch/subpath`, `tree/`→`blob/` normalized), and pre-resolved metadata to re-render the preview. A bundle can span multiple repos and present as one tree.

`gaia install` detects a bundle argument (`.json` path or http(s) URL) and walks a guided flow: render tree → prompt `[A]ll / [P]ick / [V]iew only / [Q]uit` → resolve each chosen skill (reusing the `gaia skills install` resolution path when the consumer's registry knows it, else installing directly from the bundle's source URL) → print installed/skipped/unresolved summary. Non-TTY defaults to view-only. Implemented in `src/gaia_cli/share.py`. Static `docs/share/` copy-link page is a deferred fast-follow (Issue #128).

All commands default to **local-first** output (user's own skill levels, detected skills, named forms). Pass `--canon` for canonical registry data.

## Authorization — Verifier Guardrail

All mutating `gaia dev` subcommands (add, merge, split, rename, calibrate, evidence,
rm-evidence, link, reclassify, update-named, timeline, rm, verify, build) require
**Verifier authorization**.  Read-only subcommands (`list`, `audit`, `diff`) and all
player-facing commands (`gaia promote`, `gaia fuse`, `gaia scan`, `gaia push`) are
**never** gated.

Run `gaia whoami` to check your current authorization status and see which path
(`verifier`, `bootstrap`, `override`, or `denied`) applies.

### Authorization hierarchy

| `via` | Condition | Who |
|---|---|---|
| `verifier` | Contributor holds a 4★+ named skill in `registry/named-skills.json` | Human maintainers |
| `override` | `GAIA_OPERATOR_OVERRIDE=1` env var is set | CI runners, bots, automation |
| `bootstrap` | No 4★ verifiers exist in the registry yet | Fresh / empty registries |
| `denied` | None of the above | Unauthorized |

**Bootstrap lockout prevention:** a registry with zero Verifiers auto-allows all actors.
Gating activates automatically once the first 4★ named skill lands.  Set
`GAIA_OPERATOR_OVERRIDE=1` in CI pipelines that must mutate the registry after that point.

### CI enforcement

`.github/workflows/meta-guard.yml` fails PRs that mutate registry/timeline files
(`registry/nodes/`, `registry/named/`, `registry/named-skills.json`, `skill-trees/`)
from an unauthorized PR actor.  Add the `skip-meta-guard` label to bypass (maintainer
override, analogous to `skip-scope-check` in `branch-scope.yml`).

Bot actors (`*[bot]`, `jules`, `codex`, `claude-bot`, `gemini-bot`) are always allowlisted in CI.

## Branch Naming

| Prefix | Purpose | Scope |
|---|---|---|
| `schema/...` | Nomenclature/terminology changes | `registry/schema/`, `*.md` |
| `cli/...` | CLI source changes | `src/`, `packages/`, `tests/`, `*.md` |
| `docs/...` | Documentation | `docs/`, `*.md` |
| `design/...` | Website design | `docs/` (HTML/CSS/JS), `*.md` |
| `review/gaia-push/...` | Intake layer (`gaia push`) | `registry-for-review/`, `*.md` |
| `review/meta/...` | Registry curation/promotion | `registry/`, `*.md` |
| `dev/...`, `claude/...`, `codex/...`, `gemini/...` | Experimental (unrestricted) | any |
| `infra/...` | CI/tooling changes | `.github/`, `scripts/`, `docs/*.html`, `*.md` |

CI enforces scope via `.github/workflows/branch-scope.yml`. Schema changes (`registry/schema/`) MUST use a `schema/` branch. Label `skip-scope-check` to bypass in emergencies.

## Promotion Rule

`gaia scan` writes `generated-output/promotion-candidates.json` and renders the user's tree. `gaia promote <skill> --label <level>` may only promote a pair listed in that file; stale candidate files are rejected after 24 hours.

## Versioning

The pre-commit hook keeps these in lockstep:

- `pyproject.toml`
- `packages/cli-npm/package.json`
- `packages/mcp/package.json`
- `registry/gaia.json`

If they disagree before the bump, the hook fails loudly. Use `gaia dev release <type> --sync` to force-align manifests to the highest version before bumping. Use `gaia dev release patch|minor|major` to bump all at once.

> **Deprecation:** `gaia release` is a shim delegating to `gaia dev release` with a warning; removed in v7.0.0. Use `gaia dev release` directly.

### Decorative assets must NOT carry version metadata

**Hard rule (codified after Issue #807):** Class S decorative artifacts — `docs/graph/gaia.json`, `docs/tree.md`, `docs/index.html` stats block, badges/cards/og — **must not** carry a `version` field, banner, or comment that tracks the manifest version. The lockstep verifier (`scripts/verify_lockstep.py`) checks only the four manifests above; no rendering surface should have a version string that needs to agree with them.

Before #807 the version stamp on these files was the dominant source of cross-PR CI churn: a PR opened against an old `main` inherited a stale stamp and tripped lockstep. Stripping the stamp from decoration ends that class of failure. If you add a new generated artifact under `docs/`, do not stamp a version on it. If you need a version string at runtime (e.g. cache-bust query param), read it dynamically from a fetched manifest — do not bake it into the file.

### Adding a new versioned HTML page

**Never manually patch `?v=` query strings.** Add the page path to `build_html_cache_busting()` in `scripts/build_docs.py` (function at ~L316 lists every auto-versioned HTML file). New `docs/<section>/index.html` pages go here; the `_apply_cache_busting` regex handles all relative `.css`/`.js` src/href attributes automatically.

### Bundled registry snapshot — refresh cadence

`src/gaia_cli/data/registry/gaia.json`, `named-skills.json`, and `named/` are **gitignored**, injected into the PyPI wheel at build time by the "Bundle fresh registry snapshot" step in `.github/workflows/publish-pypi.yml`:

- **vX.Y.0 releases** (minor/major, patch = 0): CI downloads `gaia-artifacts.tar.gz` from the matching GitHub Release and copies the fresh snapshot into `src/gaia_cli/data/registry/` before `python -m build`.
- **Patch releases** (vX.Y.Z, Z ≠ 0): snapshot NOT refreshed; wheel inherits from the most recent minor/major release.
- `registry/schema/*.json` are **tracked** (hand-authored) and always present.

Users needing the latest registry between wheels run `gaia pull` (downloads `gaia-artifacts.tar.gz` from the latest Release). On fallback the CLI prints a one-time stderr warning: `Warning: Using bundled registry snapshot from <DATE>. Run \`gaia pull\` for the latest.`

## Vocabulary

`CONTEXT.md` is the single source of truth for product nomenclature and the banned-synonym list (CI greps it). Read it before writing any user-facing copy, CLI output, or agent skill.

The **rarity** axis (`common`/`uncommon`/`rare`/`epic`/`legendary`) is **deprecated** and on its way out of the schema — see `CONTEXT.md` § Rarity. Do not introduce new rarity references in copy, skills, or curation. `gaia add` writes the legacy default automatically; nobody should be asked to choose a value.

## Agent Skills

Project skills are delivered in both `.claude/skills/` and `.agents/skills/`; keep mirrored copies synchronized. Shared curation contracts live beside the canonical skill in both trees.

- `gaia-curate/` — `/gaia-curate`: canonical preliminary curation; read its `CURATION-CORE.md` contract.
- `gaia-curate-chain/` — `/gaia-curate-chain`: extends `/gaia-curate` with fixed topology, deterministic gates, bounded retries, and audit state.
- `gaia-curate-dynamic/` — `/gaia-curate-dynamic`: extends `/gaia-curate` with dynamic sharding, proposer⇄refuter convergence, and a resumable ledger.
- `gaia-curate-trending/` — `/gaia-curate-trending`: discovery-only curation of configured external-source snapshots; it produces L4 shortlists and never mutates the registry.
- `gaia-meta-audit/` — `/gaia-meta-audit`: prioritized queue of skills/catalog items needing review.
- `gaia-audit/` — `/gaia-audit`: focused source-level correction for one target.
- `gaia-trace-timeline/` — `/gaia-trace-timeline`: audit & repair user-tree timelines so each skill's rank is explained by its Hero's Journey (backfills demote/rank_up events). Backed by `scripts/trace_timeline.py`; enforced by `scripts/validate_timelines.py` (via `gaia dev validate` + release CI).
- `gaia-draft-curate/`, `gaia-docs-sync/`, `gaia-integrity/`, `gaia-triage/`, `graphify-triage/` — supporting curation, doc-sync, integrity, triage.
- `gaia-bot-curate/` — bot-driven curation pass.
- `gaia-fuse-full-suite/` — `/gaia-fuse-full-suite`: fuse one contributor's named skills into a single ultimate.

When touching any of these, route registry mutations through `gaia dev add`/`merge`/`split`/`evidence` (Programmatic-First Policy), not hand-edits.

## Agent skills

- **Issue tracker:** GitHub Issues (PRs as request surface: no). See `docs/agents/issue-tracker.md`.
- **Triage labels:** canonical set `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.
- **Domain docs:** multi-context layout using `CONTEXT-MAP.md` at the root. See `docs/agents/domain.md`.

## gstack

Installed at `~/.claude/skills/gstack`. Use the `/browse` skill from gstack for **all web browsing**. Never use `mcp__claude-in-chrome__*` tools.

Available: `/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review`, `/design-consultation`, `/design-shotgun`, `/design-html`, `/review`, `/ship`, `/land-and-deploy`, `/canary`, `/benchmark`, `/browse`, `/connect-chrome`, `/qa`, `/qa-only`, `/design-review`, `/setup-browser-cookies`, `/setup-deploy`, `/setup-gbrain`, `/retro`, `/investigate`, `/document-release`, `/document-generate`, `/codex`, `/cso`, `/autoplan`, `/plan-devex-review`, `/devex-review`, `/careful`, `/freeze`, `/guard`, `/unfreeze`, `/gstack-upgrade`, `/learn`

## Known Frontend Issues — Badges, Graph, Skill Explorer, Nav/Footer

**Load-bearing invariants (full detail in `docs/agents/frontend-known-issues.md`):**

- **Badges** (`docs/badges/index.html` is a **core** page): any new field used inside `renderRows()` (~L1378) MUST be added to its `currentState` destructuring or defined `const <field> = currentState.<field> || <default>` — a missing var silently blanks all badge output. After any edit, verify `https://gaiaskilltree.com/badges/?u=mattpocock&s=grill-me` renders. **1★ skills exist, 1★ badges do not** — cutover is 2★; `scripts/validate_redaction.py` + `scripts/generateBadges.py` (`is_redacted()` from `src/gaia_cli/redaction.py`) enforce it. **Auto-sync NEVER touches `docs/badges/`** (badges only via human-reviewed `infra/badge-*` PRs); badge drift in `gaia dev docs --check` is warn-only.
- **Graph** (`docs/js/skill-graph.js`): null-check overlay button selectors before wiring events — a null `querySelector(...).addEventListener` at bootstrap silently aborts the IIFE and falls back to `FALLBACK_SKILLS`. Do not recreate the stale `skills/` root directory.
- **Skill Explorer** (`docs/js/skill-explorer.js`): split into **two IIFEs** (L1–1862, L1864–end) that do NOT share scope — anything shared must be re-declared per IIFE or hung off `window`; render functions in `openExplorer` stay wrapped in `_safeRender`. After any edit to it or `docs/named/index.html`, open `https://gaiaskilltree.com/named/`, click a 2★+ skill, confirm all five sections render (Hero, Installation, Documentation, Upgrade Path, Evolution Changelog).
- **Nav / Footer:** the canonical mount list lives in ONE place — `docs/js/mounts.js → window.GAIA_MOUNTS`. Every new `docs/<section>/` using site-nav must add its dir there AND load `mounts.js` before `site-nav.js`. CI Guard D (`scripts/check_nav_mounts.py` in `docs-cohesion.yml`) enforces this; run `python scripts/check_nav_mounts.py` locally.

## Curation Guidelines

**Load-bearing invariants (full detail in `docs/agents/curation-guidelines.md`):**

- `links.github` MUST use `blob/branch/subpath`, not `tree/` (bare repo roots make skills undiscoverable). Only `links.github` is read by the installer — rename `links.repo`/`links.docs`/`origin` etc. accordingly.
- Skills with `suiteComponents` need NO `links.github` of their own — do not flag them uninstallable; but each **component** needs its own `blob/branch/subpath`. Non-suite skills ≤2★ with no public repo → `installable: false` (see CONTRIBUTING.md §12).
- Trust Magnitude evidence learnings (same-source dedup, mothership discount, peer-review being highest-impact for science skills, `benchmark-result` needing `percentile`, `rm-evidence --source` removing ALL entries at a URL, worktree `PYTHONPATH` run path, social-signal view floor, firecrawl fallback) — see the reference file before touching evidence.

See [DEV.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/DEV.md) for setup, testing, and CI troubleshooting.

## Agent-Managed Files (Hermes Ownership)

Do **not** modify, stage, or delete these (managed by the Hermes agent):

- `STEWARDSHIP_PLAN.md`
- `scripts/marketing_engine.py`
- `scripts/email_sender.py`
- `scripts/share_deliverable.py`
- `scripts/generate_adoption_dashboard.py`
- `scripts/generate_showcase.py`
- `docs/ADOPTION.html`
- `docs/SHOWCASE.html`
- `docs/WHY-GAIA.md`
- `docs/QUICKSTART.md`

## Workspace Rules (Agent Directives)

### Coding Style & Naming
- Avoid underscores (`_`) in functions/variables unless explicitly provided in existing names/templates (except dunders like `__init__`, `__str__`).

### Branch Workflow
- When starting fresh and indicating a PR, work on the PR branch right away. GO TO THE PR BRANCH, not the `claude/` branch.

### Skills Intake
- Skills are mirrored in `.claude/skills/` and `.agents/skills/`; keep both copies byte-identical.

### Upstream Watcher (V1 design, phased implementation)
- Design at [`docs/agents/upstream-watcher.md`](docs/agents/upstream-watcher.md). Read before touching `scripts/upstream_watcher/`, `scripts/lib/`, `.github/workflows/upstream-*.yml`, or any `upstream:*` label.
- The watcher opens **issues** for existing-skill version tracking; it does NOT create `bot/*` branches (that flow belongs to `scripts/crawlers/`, new-skill discovery).
- Every registry mutation still goes through `gaia dev` verbs (`sync-upstream`, `freeze`, `relink`) on `review/meta/` branches. No hand-edits to `upstream:` frontmatter blocks; no direct workflow writes to `main`.

### Token Spend Logging (Critical)
- On EVERY GitHub Project, LOG input/output token spend by model + date.
  - *Format*: `<date> Opus 4.8 Extra High: 100k in, 200k out. ~$10`
  - Report spend to the user at the end of the session run on EVERY commit push. Write it as a comment (on the PR when working a PR; as part of the issue comment when working an issue).
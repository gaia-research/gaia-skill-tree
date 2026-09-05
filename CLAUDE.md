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

## Git Workflow

Never push directly to main.

### Branching Strategies

#### Multi-PR work & `gaia-orchestrator`

`gaia-orchestrator` mode required for this branch strategy. Load `/gaia-orchestrator` immediately when asked to do long-running multi-PR work.

Work that spans more than one PR does **not** aim its PRs at `main` one at a time. They land on a shared **integration branch** (`dev/*` — "integration" and "staging" are interchangeable here), and the integration branch is what opens a PR against `main`.

- **The integration branch does not have to be green.** Red CI on `dev/*` is expected and is not a defect to chase. It is a workbench, not a release.
- **CI is a gate on one merge only: integration → `main`.** That merge is where everything must be green, and it is founder-gated like any other.
- **All proof-of-work lives on the integration branch** — evidence, screenshots, probe records, partial slices. Do not stash it elsewhere and do not squash it away before the founder has seen it.
- **Branch scopes** are for naming purposes only. Leniency is expected. The only CI that matters is the **one on main** at the end of the sprint.

#### PR Stacking

- Utilize `gh stack` when creating stacked PRs.
- You CAN do this on top of an integration branch if judged necessary. No need to ask.

## Squash Merges

- NOT allowed when merging PRs against **main**
- ALLOWED when merging stacked PRs or PRs to integration branches (not landing on main)

### PR description safety

Use `--body-file` with real newlines for multiline PR text, then verify with `gh pr view --json body --jq .body`; avoid escaped `\\n`/shell quoting. If staging leaks into a PR, rebuild from `origin/main`, keep only intended files, and check `git diff --stat origin/main...HEAD` before pushing.

### Branch & Worktree Conventions

- Confirm the target branch/worktree before editing. If user references a specific branch (e.g. `fix/links-3d-graph`), push there — do not create a new design branch.
- When editing in a worktree, verify CWD matches the requested worktree first.

## Branch Scope

| Scope | Allowed Directories | Reasoning |
|-------|---------------------|-----------|
| **infra/** | `.github/`, `scripts/`, `*.md`, `docs/*.html`, `docs/badges/` | Already codified in `.github/workflows/branch-scope.yml` and exempt from re-litigation. |
| **schema/** | `registry/schema/`, `src/gaia_cli/data/registry/schema/` | The two schema directories must move in lockstep; schema PRs touching only one side always trip CI. Codified in `.github/workflows/branch-scope.yml`; do not require `skip-scope-check`. |
| **review/meta/** | `docs/` (excl. `registry/schema/`), `registry/` (excl. `registry/schema/`) | Required by Guard E: any change to `registry/nodes/` or `registry/named/` MUST include the regenerated Class S artifacts (per-user profile pages, badges, graph, API docs). Codified in `.github/workflows/branch-scope.yml`; do not require `skip-scope-check` on every curation PR. |


## Edit Safety

- After Edit/Write on JS/HTML, read the file back to verify no duplication or merged lines; run syntax check if available.
- Avoid hex color fallbacks in JS/CSS; use design tokens only (CI Guard A rejects hex in `docs/**/*.{js,css}`; standalone SVG badges/OG-cards and legacy HTML inline styles are tracked separately).
- When bumping assets, update cache-bust version strings across all referencing pages.

## Frontend changes are HUMAN-GATED — founder review before merge

**Invariant:** a PR that changes what a visitor sees does **not** merge on green CI alone. It merges when the founder has looked at it. Agents and orchestrators may open, iterate, and mark it ready — **they may not merge it.** CI proves nothing rendered wrong; it does not prove the design is right.

**Gated — needs founder review:**

- New user-facing page or section; removing or relocating one
- Layout, structure, or component composition
- Design tokens, color, typography, spacing, motion
- Nav, footer, `window.GAIA_MOUNTS`, or any entrypoint wiring
- Public-page copy that changes the *message* (positioning, naming, what a product is)
- Anything rendering the graph, badges, cards, or OG images

**Not gated — ship on green:**

- Typo, grammar, and factual corrections inside an existing block, layout unchanged
- Dead or wrong link targets
- `alt` text, ARIA attributes, and other accessibility fixes that add no visual change
- Cache-bust version bumps
- Comments, and refactors with **no rendered diff**

**Rule of thumb:** if the change alters *structure, styling, or which surfaces exist*, it is gated. If it only corrects *words or link targets inside a block whose layout is unchanged*, it is small — ship it. When genuinely unsure, gate it; a held PR costs a message, an unreviewed design change costs a revert.

## Design Entrypoints — plan before you ship

**Invariant:** every new user-facing page/section MUST plan its entrypoints during the design pass — main nav, footer, homepage, `window.GAIA_MOUNTS`, cross-page links, and cache-busting — and the PR body MUST include an "Entrypoints" section listing which were touched or explicitly waived (design-review agents bounce PRs missing it). Shipping a section with no way to reach it from the homepage is a broken feature. CI Guard D enforces the `mounts.js` registration.

See `docs/agents/design-entrypoints.md` for the full 6-point checklist and rule of thumb.

## Deferred-surface convention — ship the bridge state, disclose the bridge state

**Invariant:** when a user-visible surface ships to satisfy a kill criterion but its design register is slated for a later sprint, the interim state MUST be disclosed on the surface with a `.wip-banner` linking to a tracking issue that carries the target sprint label — never silently ship a bridge state, and never add a banner without a tracking issue. Do NOT use it to hide unfinished work with no sprint home (that's a defect; file and fix).

See `docs/agents/deferred-surface-convention.md` for the three preconditions, what ships, what NOT to do, and the reference implementation.

## Fixed-nav clearance — every top-level page container must clear ~58px

**Invariant:** every page-level container directly under `<body>` MUST provide its own top clearance below the fixed nav (~58px). Use the exact value ladder — base **5rem (80px)**, desktop **6rem (96px) for thin strips** or **8rem (128px) for full page shells**. There is no global `body { padding-top }` and there won't be. Do not invent other values.

See `docs/agents/fixed-nav-clearance.md` for the CSS pattern, reference implementations, anti-patterns, and verification steps.

## Testing

Run tests surgically. The test is heavy, so do the full test only right before a review pass. CI already tests on every push. Read results instead of re-running.

## Data & Permissions

Never modify data files (skill levels, slot data, schema fixtures) without explicit approval; ask before treating data as invalid.

## Project Architecture / Data Model

Skill levels are stored in slots, not on skill objects — account for this when computing stats, trees, and breakdowns.

## Commands & Setup

See [DEV.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/DEV.md) for local setup (virtualenv, pip), common commands, and testing.

## Current Layout

| Area | Path | Notes |
|---|---|---|
| Curated skills | `registry/` | Maintainer-reviewed data and public generated catalogs |
| Canonical graph | `registry/gaia.json` | Class P (gitignored — regenerated locally by gaia dev docs; bundled in wheels on vX.Y.0 releases). NOT served to browsers directly. |
| Site graph assets | `docs/graph/` | Class S (tracked in git — served as-is by GitHub Pages from main:/docs at gaiaskilltree.com). Includes gaia.json, named/index.json, gaia.gexf, gaia.svg. Regenerated by `gaia dev docs` alongside registry/gaia.json. |
| Named skills | `registry/named/` | Markdown implementations grouped by contributor |
| Named index | `registry/named-skills.json` | Generated by `scripts/generateNamedIndex.py` |
| Schemas | `registry/schema/` | JSON schemas |
| Local output | `generated-output/` | Gitignored scan/render artifacts |
| Python CLI | `src/gaia_cli/` | Entry `main.py`, dynamic command discovery from `commands/`. Mutating ops in `commands/dev/` (evidence, verify, merge, calibrate). `versioning.py` keeps pyproject.toml, package.json files, registry/gaia.json in lockstep. |
| Slash-naming helpers | `src/gaia_cli/formatting.py` | Slash-naming formatters, RANK_COLORS, tier colors |

```bash
# Meta Review (CLI-ONLY)
gaia dev list --generic --named
gaia dev add "Skill Name" --type basic --description "At least 10 chars description"
gaia dev merge target-id source-ids...
gaia dev split source-id target-ids...
gaia dev evidence skill-id "url" --type repo-own --commits N --contributors N
gaia dev fuse generic-id --name "..." --description "At least 10 chars" --prereqs a,b,c \
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

### Curation PR — which artifacts to commit after `gaia dev docs`

**Load-bearing invariant (2026-07-30, PR #1387 retro):** after running `gaia dev docs` on a `review/meta/` curation PR, commit **only the deterministic, registry-driven set**. Do NOT commit the platform-sensitive noise that `gaia dev docs` also regenerates — those either fail CI on a foreign OS or carry warn-only drift that doesn't belong in a curation diff.

**Commit these (hard CI failures if missing):**
- `docs/graph/gaia.json`, `docs/graph/named/index.json`, `docs/graph/gaia.gexf`, `docs/graph/gaia.svg` — Class S graph assets
- `docs/api/v1/**` — contributor and skill JSON API files (new/changed contributors and skills)
- `docs/u/<handle>/index.html` — per-user profile pages for new contributors
- `docs/tree.md`, `docs/about.html`, `docs/index.html` stat blocks, `README.md` — registry-driven summary stats
- `skill-trees/*/skill-tree.md` — skill-tree markdown mirrors for newly unlocked skills
- `registry/registry.md` — generated registry summary
- `docs/graph/ledger/data.json` — Trust Magnitude ledger. **Was wrongly listed as "do NOT commit / timestamp-only bump" until 2026-08-06 (PR #1464 retro).** It is hard-fail (`trust_ledger_changed` is inside `changed` in `build_docs.py`), its `--check` normalizes `generatedAt`/`version` so committing it never causes timestamp churn, and `buildApiProjection.build_leaderboard()` reads the **committed** copy to emit `docs/api/v1/leaderboard.json`. Leaving it stale while committing a freshly-generated `leaderboard.json` makes CI rebuild the leaderboard from the old ledger → permanent `diff docs/api/v1/leaderboard.json`. Commit the two together, always.

**Do NOT commit (warn-only or noisy):**
- `docs/og/*.svg` — OG share cards: platform-sensitive SVG rendering (Windows CRLF ≠ Linux LF). Drift is warn-only in `build_docs.py`. Regenerating locally on Windows pollutes 159 files with CRLF; revert any accidental changes with `git checkout origin/main -- docs/og/` and keep only the new-contributor SVGs.
- `docs/api/v1/trending/` — rolling time-window artifact; timestamps recompute on UTC-day rollover. Warn-only.
- `docs/experiments/ml-graph-viz/layouts_3d.json` — non-deterministic 3D layout AND carries a stale version stamp that can downgrade the semver lockstep check.
- `docs/okf/` — decorative meta bundle. Warn-only.

**Verification:** after staging only the above set, run `python scripts/build_docs.py --check` locally → must exit 0 before pushing. Any remaining `diff` lines in its output (other than warn-only categories) mean something is still missing.

## Programmatic-First Policy

**All meta shifts (merging, splitting, adding skills, adding evidence) MUST be done via CLI commands.** Manual edits to `registry/nodes/` are FORBIDDEN to ensure programmatic schema integrity and automated timeline logging. AI agents must prioritize these tools over direct file manipulation.

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
| Fuse skills (confirm/declare a fusion locally) | `gaia fuse <skillId>` |
| Append event at current time | `gaia dev timeline <skillId> --user <username> --action <action> --notes "..."` |
| Backfill a historical event | `gaia dev timeline <skillId> --user <username> --action <action> --notes "..." --timestamp "YYYY-MM-DDTHH:MM:SSZ"` |

The `--timestamp` flag accepts ISO 8601 (e.g. `2026-03-01T00:00:00Z`); without it, current UTC is used. Backfilled events auto-sort chronologically.

**Known CLI gap (flag in PRs, do not silently hand-edit):** No `gaia remove-skill` / `gaia demote` command — skill removal from the user tree has no dedicated verb. Workaround: direct JSON edit to remove from `unlockedSkills`, then `gaia dev timeline <skillId> --user <username> --action demote --notes "..."` to log it.

## Playbook-First Policy (migration in progress — Issue #1644)

The repo is migrating from bare `gaia dev` verb calls to **Agent Playbooks** as the
preferred way agents perform dev-mutation work (calibration, evidence, fusion,
curation, and the rest of the `gaia dev` surface). A playbook is a canonical
`.agents/skills/*/SKILL.md` carrying `playbookVersion: 1` frontmatter — the same
physical file type as a user-invokable skill, but built for an **agent following a
checked procedure**, not for a human's `/slash-command`. It fixes the order,
authority envelope, stopping rules, and proof around a `gaia dev` verb so an agent
does not reconstruct that method from scattered prose every time. Contract:
`founder/steward/PLAYBOOKS.md`; schema: `founder/steward/playbook.schema.json`;
checker: `scripts/check_playbook_contract.py`; rationale:
`founder/handovers/2026-09-01-issue-1644-agent-playbooks.md`.

**Rule:** before calling a mutating `gaia dev` verb directly, check whether a
playbook already covers that operation (`playbookVersion: 1` under
`.agents/skills/*/SKILL.md`). If one exists, follow it — its steps, stop
conditions, and proof obligations are the required procedure, not a suggestion.
If none exists yet for the operation at hand, author one first per
`founder/steward/PLAYBOOKS.md`, validate it against
`scripts/check_playbook_contract.py`, and use it — don't do the mutation via a
bare CLI call and leave the method unwritten for the next agent.

- This is a migration, not a retroactive requirement: most `gaia dev` verbs have
  no playbook yet. Calling the CLI directly remains fine where no playbook exists
  and none has been requested for that verb. The rule binds once a playbook is
  available, or once one has been asked for.
- Playbooks live under `.agents/skills/` alongside user-invokable skills but are a
  **distinct category** — they exist for agents executing dev verbs, not for a
  human to trigger by name. Do not list them in user-facing skill catalogs or docs
  as if they were `/slash-command` skills; see § Agent Skills for the
  user-invokable-skill mirror convention, which is a separate concern.
- The CLI remains the canonical mutation surface (per § Programmatic-First Policy
  above). A playbook never bypasses `require_operator()` or a verb's pre-flight
  checks — it only sequences and verifies around them.
- Reference playbook: `dev-calibrate` (`.agents/skills/dev-calibrate/SKILL.md`) —
  the first one to land; use its shape as the template for the next.

## CLI Shape

Top-level (lifecycle-oriented): `init`, `scan`, `pull`, `push`, `appraise`, `curate`, `trust`, `version`, `whoami`, `tree`, `graph`, `update`, `share`, `steward`, `help`. Note: docs/mcp/release live under `gaia dev`; promote has been removed.

Maintenance actions under `gaia steward`: `scan`, `run`, `dispatch`, `founder`. `scan` and the two report-only renderers write nothing outside ignored `.gaia/steward/`; `run` performs only the Class A repairs declared in `founder/steward/POLICY.yaml`. See `founder/steward/README.md` for the authority envelope and `founder/steward/routines/` for the Class B routine library.

Named skill actions under `gaia skills`: `list`, `search`, `install`, `uninstall`, `info`. Old flat verbs are intentionally removed.

### Share bundles (`gaia share` / `gaia install <bundle>`)

`gaia share` exports a self-contained **share bundle** JSON (`generated-output/share/<user>-share-bundle.json`, or `--stdout`): a snapshot of the sharer's tree, a flat install manifest pointing each skill at its source repo via `links.github` (`blob/branch/subpath`, `tree/`→`blob/` normalized), and pre-resolved metadata to re-render the preview. A bundle can span multiple repos and present as one tree.

`gaia install` detects a bundle argument (`.json` path or http(s) URL) and walks a guided flow: render tree → prompt `[A]ll / [P]ick / [V]iew only / [Q]uit` → resolve each chosen skill (reusing the `gaia skills install` resolution path when the consumer's registry knows it, else installing directly from the bundle's source URL) → print installed/skipped/unresolved summary. Non-TTY defaults to view-only. Implemented in `src/gaia_cli/share.py`. Static `docs/share/` copy-link page is a deferred fast-follow (Issue #128).

All commands default to **local-first** output (user's own skill levels, detected skills, named forms). Pass `--canon` for canonical registry data.

## Authorization — Verifier Guardrail

All mutating `gaia dev` subcommands (add, merge, split, rename, calibrate, evidence,
rm-evidence, link, reclassify, update-named, timeline, rm, verify, build) require
**Verifier authorization**.  Read-only subcommands (`list`, `audit`, `diff`) and all
player-facing commands (`gaia fuse`, `gaia scan`, `gaia push`) are
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
| `review/meta/...` | registry curation/promotion | `registry/`, `*.md` |
| `dev/...`, `claude/...`, `codex/...`, `gemini/...` | Experimental (unrestricted) | any |
| `integration/...` | Assembly point for multi-PR work | any (unrestricted) — see § Integration branches |
| `infra/...` | CI/tooling changes | `.github/`, `scripts/`, `docs/*.html`, `*.md` |

CI enforces scope via `.github/workflows/branch-scope.yml`. Schema changes (`registry/schema/`) MUST use a `schema/` branch. Label `skip-scope-check` to bypass in emergencies.

## No self-promote (Yggdrasil II)

Rank/level is assigned ONLY by canon curation (dev-gated). The non-dev CLI's job ends at *propose*: `gaia scan` detects the fusions you have the prerequisites for and renders your tree; `gaia fuse` confirms a detected combination or declares a custom fusion locally (levelless — `type: fusion`); `gaia push` proposes the structure to canon, where curation "awakens" it and assigns rank. No non-dev CLI path writes rank/level into `skill-trees/<user>/skill-tree.json`. (There is no `gaia promote` — it was retired in the Ygg II CLI alignment.)

## Versioning

The pre-commit hook keeps these in lockstep:

- `pyproject.toml`
- `packages/cli-npm/package.json`
- `registry/gaia.json`

If they disagree before the bump, the hook fails loudly. Use `gaia dev release <type> --sync` to force-align manifests to the highest version before bumping. Use `gaia dev release patch|minor|major` to bump all at once.

> **Retired (v7.0.0):** the top-level `gaia release` shim is gone — use `gaia dev release` directly. Likewise `gaia mcp`, `gaia validate`, `gaia test`, `gaia docs build`, and `gaia _hook` were removed; their canonical forms live under `gaia dev`.

### Decorative assets must NOT carry version metadata

**Hard rule (codified after Issue #807):** Class S decorative artifacts — `docs/graph/gaia.json`, `docs/tree.md`, `docs/index.html` stats block, badges/cards/og — **must not** carry a `version` field, banner, or comment that tracks the manifest version. The lockstep verifier (`scripts/verify_lockstep.py`) checks only the three manifests above; no rendering surface should have a version string that needs to agree with them.

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

### The lexicon serves the work — the work does not serve the lexicon

**Founder ruling, 2026-07-29.** This repo owns two lexicon namespaces (`gaia.skills`, `gaia.trust`); the federated core lives in `gaia-research`. Treat all of it as a **guide you consult**, not an artifact you maintain.

- **Read it to pick the right word, then get on with the task.** Accuracy matters; ceremony does not.
- **You touch the lexicon only when a decision or ratification has actually been made** — a founder ruling lands, or an oracle entry changes state. Do not tidy it, audit it for consistency, or reopen settled entries on your own initiative.
- **Never let a naming question block a build.** If the gate fires on something genuinely unsettled, say so in one line and keep moving. Do not convene a vocabulary review.
- **A ban retires a word, not the method it named** (gaia-research RATIFICATION N10). A banned term may carry `"naming": "open"` instead of a `replacement` — rephrase around it rather than substituting a successor nobody ratified.

## Agent Skills

Project skills are delivered in both `.claude/skills/` and `.agents/skills/`; keep mirrored copies synchronized. Shared curation contracts live beside the canonical skill in both trees.

## Known Frontend Issues — Badges, Graph, Skill Explorer, Nav/Footer

**Invariants (full detail in `docs/agents/frontend-known-issues.md`):**

- **Badges** (`docs/badges/index.html` is a **core** page): any new field used inside `renderRows()` (~L1378) MUST be added to its `currentState` destructuring or defined `const <field> = currentState.<field> || <default>` — a missing var silently blanks all badge output. After any edit, verify `https://gaiaskilltree.com/badges/?u=mattpocock&s=grill-me` renders. **1★ skills exist, 1★ badges do not** — cutover is 2★; `scripts/validate_redaction.py` + `scripts/generateBadges.py` (`is_redacted()` from `src/gaia_cli/redaction.py`) enforce it. **Auto-sync NEVER touches `docs/badges/`** (badges only via human-reviewed `infra/badge-*` PRs); badge drift in `gaia dev docs --check` is warn-only.
- **Graph** (`docs/js/skill-graph.js`): null-check overlay button selectors before wiring events — a null `querySelector(...).addEventListener` at bootstrap silently aborts the IIFE and falls back to `FALLBACK_SKILLS`. Do not recreate the stale `skills/` root directory.
- **Skill Explorer** (`docs/js/skill-explorer.js`): split into **two IIFEs** (L1–1862, L1864–end) that do NOT share scope — anything shared must be re-declared per IIFE or hung off `window`; render functions in `openExplorer` stay wrapped in `_safeRender`. After any edit to it or `docs/named/index.html`, open `https://gaiaskilltree.com/named/`, click a 2★+ skill, confirm all five sections render (Hero, Installation, Documentation, Upgrade Path, Evolution Changelog).
- **Nav / Footer:** the canonical mount list lives in ONE place — `docs/js/mounts.js → window.GAIA_MOUNTS`. Every new `docs/<section>/` using site-nav must add its dir there AND load `mounts.js` before `site-nav.js`. CI Guard D (`scripts/check_nav_mounts.py` in `docs-cohesion.yml`) enforces this; run `python scripts/check_nav_mounts.py` locally.

## Curation Guidelines

**Invariants (full detail in `docs/agents/curation-guidelines.md`):**

- `links.github` MUST use `blob/branch/subpath`, not `tree/` (bare repo roots make skills undiscoverable). Only `links.github` is read by the installer — rename `links.repo`/`links.docs`/`origin` etc. accordingly.
- Skills with `suiteComponents` need NO `links.github` of their own — do not flag them uninstallable; but each **component** needs its own `blob/branch/subpath`. Non-suite skills ≤2★ with no public repo → `installable: false` (see CONTRIBUTING.md §12).
- Trust Magnitude evidence learnings (same-source dedup, mothership discount, peer-review being highest-impact for science skills, `benchmark-result` needing `percentile`, `rm-evidence --source` removing ALL entries at a URL, worktree `PYTHONPATH` run path, social-signal view floor, firecrawl fallback) — see the reference file before touching evidence.

See [DEV.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/DEV.md) for setup, testing, and CI troubleshooting.

## Workspace Rules (Agent Directives)

### Coding Style & Naming
- Avoid underscores (`_`) in functions/variables unless explicitly provided in existing names/templates (except dunders like `__init__`, `__str__`).

### Branch Workflow
- When starting fresh and indicating a PR, work on the PR branch right away. GO TO THE PR BRANCH, not the `claude/` branch.

### Skills Intake
- Skills are mirrored in `.claude/skills/` and `.agents/skills/`; keep both copies byte-identical. Check with `python scripts/sync_agent_skill_mirror.py --check` and fix with the same script without `--check`. Gaia Steward also repairs this drift as Class A (`agent-skill-mirror`), so a forgotten mirror copy is self-healing — but a `.claude/skills/`-only path is not: the repair refuses to delete it and leaves the debt open for a human.

### Upstream Watcher (V1 design, phased implementation)
- Design at [`docs/agents/upstream-watcher.md`](docs/agents/upstream-watcher.md). Read before touching `scripts/upstream_watcher/`, `scripts/lib/`, `.github/workflows/upstream-*.yml`, or any `upstream:*` label.
- The watcher opens **issues** for existing-skill version tracking; it does NOT create `bot/*` branches (that flow belongs to `scripts/crawlers/`, new-skill discovery).
- Every registry mutation still goes through `gaia dev` verbs (`sync-upstream`, `freeze`, `relink`) on `review/meta/` branches. No hand-edits to `upstream:` frontmatter blocks; no direct workflow writes to `main`.

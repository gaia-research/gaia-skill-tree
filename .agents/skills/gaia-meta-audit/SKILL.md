---
name: gaia-meta-audit
description: Scan Gaia registry and real-skill catalog entries for candidates that may need review because they are outdated, superseded, overpromoted, weakly sourced, stale, duplicate, brand-coupled, mis-attributed, or incorrectly mapped. Use before focused audits when the user asks what needs review.
version: 1.1.0
---

# gaia-meta-audit

> **Starless (rank-less generics):** Generic skill references carry **no `level`, `demerits`, or stars** — they are *starless* taxonomy. Stars live only on named skills (2★–6★); a generic's effective rank is the top star among its named children. Generic nodes keep capability-level (Class A) evidence that every named child **inherits**; implementation-specific evidence lives on the named skill. Never write a level/demerit to a generic and never `gaia dev calibrate` a generic (calibrate is named-only). Advanced evidence tiers are an upcoming meta shift.


Build a prioritized queue of Gaia skills or catalog items that need focused review.

## Workflow

1. Load source surfaces:
   - `registry/gaia.json`
   - `registry/named-skills.json`
   - `registry/named/**`
   - `registry/real-skills.json`
   - `docs/skill_source_contributions.md`
   - `META.md` (the source of truth — re-read §1 Taxonomy, §4.1 Origin, §6.2 Semantic Fusion before audit)

2. **Pivot named skills by `genericSkillRef`.** For every generic referenced by the audit target, list every named skill mapped to it, sorted by `createdAt`. This is the only reliable way to detect mis-attributed `origin: true` claims (see red flag below). A handy one-liner:
   ```python
   # walk registry/named/**.md, group by genericSkillRef, print createdAt + origin
   ```

3. Scan for red flags:
   - **Liveness Heartbeat**: Run `python3 scripts/verify_evidence.py` to identify dead links in evidence.
   - **Star Bar Scan**: Identify skills at **3★+** missing a valid `links.github` (installer-ready) URL.
   - **Link casing miss**: GitHub raw paths are case-sensitive. A `links.github` URL pointing at `/SKILL.md` (uppercase) when the on-disk file is `skill.md` (lowercase) — or vice versa — will 404. Standardize on `SKILL.md` to match the project-wide convention.
   - **Wrong-target link**: `links.github` points at a different skill's directory than the named skill claims to implement.
   - **Brand-coupled generic IDs**: A canonical (generic) skill ID containing the product/brand name (e.g. `gaia-audit`, `gaia-meta-audit`) violates META §1 — generics must be abstract capabilities. Rename via `gaia dev rename` to an abstract noun phrase (e.g. `gaia-audit` → `registry-entry-audit`). The brand stays in the **named** layer.
   - **Mis-attributed `origin: true`**: Per META §4.1, only ONE contributor holds Origin per generic — the first to implement it. "Lives in this repo" does not equal "Origin." Verify by sorting all named skills with the same `genericSkillRef` by `createdAt` — only the earliest can claim `origin: true`.
   - **Unbacked star**: a named skill's `level` (star) is not backed by its own + inherited evidence. Generics are rank-less, so there is no generic level to "overshoot" — judge the named star on evidence, not the generic.
   - `promotedNamedSkillId` entries with weak or broad source evidence.
   - Catalog URLs that point to directories, homepages, or stale paths instead of specific files.
   - Repo-root evidence where a specific `SKILL.md` or **agent playbook** should exist.
   - Broad mappings such as an implementation skill mapped to a much larger Gaia capability (e.g. anything mapped to a `0★` Basic node when an Extra-level generic exists).
   - Duplicate or superseded skills from the same source family. Flag clusters of redundant generic concepts that should be consolidated under a single Basic skill (e.g. `literature-search`) to prevent registry bloat.
   - Generated outputs that still reference removed named claims.
   - **Likely Fusion Candidates** (Semantic Fusion, META §6.2): two or more named skills that represent the composition of two existing Extra generics into one orchestrated workflow. Example from PR #525: `safishamsi/graphify` (knowledge-graph-build) + `mattpocock/triage` (issue-triage) → propose new Extra generic `graph-driven-issue-triage` 3★, prereqs `[knowledge-graph-build, issue-triage]`. **This is NOT an Ultimate fusion** — Ultimates require ≥10k repo stars (META §1.2, §4.2).
   - **Missing Demerits**: Skills with known heavyweight dependencies or niche integrations that are not yet flagged in the registry.
   - **Placeholder bodies**: Named-skill markdown files containing only `## Installation\nAdd installation instructions here.` (51 chars) — needs a real `## Overview` paragraph.
   - **`contributor: testuser` timelines**: Placeholder authorship that survived initial intake.

4. Re-check only enough external evidence to rank candidates. Do not perform every focused audit in the meta pass.

5. Prioritize:
   - **P0**: Unsupported Ultimate claim, unsupported named-origin claim, or named claim with no implementation file in the repo.
   - **P1**: Dead evidence links (Liveness Heartbeat failure), missing 3★+ Star Bar implementation, link casing miss, wrong-target link, brand-coupled generic ID, unbacked named star.
   - **P2**: Wrong `promotedNamedSkillId`, stale source URL, likely superseded origin, mis-attributed `origin: true`.
   - **P3**: Broad `mapsToGaia` / `genericSkillRef`, duplicate catalog item, weak evidence tier, Semantic Fusion candidate ready to extract.
   - **P4**: Documentation cleanup, placeholder bodies, `testuser` timelines, generated-output drift.

   Do not flag candidates on rarity grounds — the rarity axis is deprecated (see `CONTEXT.md` § Rarity).

6. Present a queue with target, reason, suggested action, and source files to inspect.

7. For each accepted candidate, hand off to `/gaia-audit` as a separate focused correction, or use the **Meta Review CLI commands** for direct registry maintenance.

## CLI vs direct-edit map

`gaia dev` does not cover every mutation. Use this map (validated in PR #525):

| Mutation | Tool |
|---|---|
| Generic-skill rename (cascades to prereqs + named refs) | `gaia dev rename old new` |
| Add new generic | `gaia dev add "Name" --id <slug> --type extra --description "..."` |
| Set generic prereqs | `gaia dev link <id> a,b,c` |
| Calibrate **named-skill** star (generics are rank-less) | `gaia dev calibrate <contributor/skill> 3★` |
| Add **capability** evidence to a generic (inherited by all named) | `gaia dev evidence <id> <url> --class B --evaluator <user>` |
| Reclassify generic type | `gaia dev reclassify <id> <type>` |
| Remove generic | `gaia dev rm <id>` |
| Named-skill `genericSkillRef` change | `gaia dev update-named <author/skill> --generic-ref <new>` |
| Named-skill `status` change | `gaia dev update-named ... --status <new>` |
| Named-skill suite metadata | `gaia dev update-named ... --suite-ref / --suite-components / --installation-file` |
| Named-skill **`level` / `origin` / `links.github` / `description` / body / timeline** | **direct YAML edit** — CLI does not expose these |
| Named-skill removal | **delete the markdown file** — `gaia dev rm` is generic-only |
| Demotion-as-event (writes to timeline with `previousValue`/`newValue`) | direct YAML edit; add a `timeline` entry with `action: demote` |

After mutating, **always** run `gaia validate` and `gaia docs build`.

## Common gotchas (validated in PR #525)

- **Renames leave orphan docs.** `gaia dev rename` renames the node JSON and updates `genericSkillRef` in named files, but leaves stale `registry/skills/<type>/<old-id>.md`. Delete the orphan.
- **Generics are rank-less — do not calibrate them.** A generic carries no level; capability (Class A) evidence on a generic is inherited by every named child. Per-named evidence floors are checked on the named skill's star, not on the generic.
- **`gaia dev` timeline entries land with `contributor: unknown`** when the local user isn't picked up. Edit the JSON to set `mbtiongson1` (or whoever) before committing.
- **`gaia docs build` after big changes regenerates ~30 files.** Per CLAUDE.md §8, feature/logic PRs should NOT commit `registry/gaia.json` or `docs/graph/gaia.json` (auto-sync CI handles them). For `review/meta/*` branches, the **branch-scope CI** blocks `docs/` and `.agents/` paths — apply the `skip-scope-check` label, OR keep the working tree limited to `registry/**` and let auto-sync regenerate.
- **`review/meta/*` Schema + DAG CI requires generated docs in lockstep.** This contradicts the §8 guidance. Resolution: commit the regenerated docs WITH the `skip-scope-check` label and a `[skip-gen]` tag on the commit message to suppress the auto-regen workflow.
- **Force-push doesn't always re-trigger path-filtered workflows.** After `--force-with-lease`, dispatch `validate.yml` and `python-package.yml` manually via `gh workflow run ... --ref <branch>` if their checks don't appear.

## Output

Use this table:

| Priority | Target | Why review | Suggested audit action | Source files |
|---|---|---|---|---|

Stop after the queue unless the user asks to run audits immediately.

## Reference run

PR #525 (`review/meta/mbtiongson1-audit`, 2026-05-30) is the canonical worked example for this skill. It exercised every red-flag category above on mbtiongson1's 14 named skills and resulted in:

- 2 named removals (`research`, `web-scrape`) — P0 unsupported claims
- 2 generic renames (`gaia-audit` → `registry-entry-audit`, `gaia-meta-audit` → `registry-health-scan`) — P1 brand-coupled IDs
- 1 new Extra generic (`graph-driven-issue-triage`, 3★) — P3 Semantic Fusion extraction
- 5 `genericSkillRef` remaps (broad mappings → correct generics)
- 1 origin claim flipped to `true` (`graphify-triage` on the new fusion generic)
- 1 named-level demotion (`gaia-meta-audit` 4★ → 3★) — P1 level overshoot
- 7 `links.github` casing fixes + 2 wrong-target fixes — P1 Star Bar
- 12 placeholder body backfills + 12 `testuser` timeline corrections — P4

Read its `AUDIT-mbtiongson1.md` (the plan-of-record committed as the first PR commit) and the PR description for the full red-flag → action mapping.

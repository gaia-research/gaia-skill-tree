---
name: gaia-meta-audit
description: >
  Generate a prioritized review queue of Gaia registry skills and catalog items that need attention.
  Use this skill whenever someone asks: "what needs review?", "what's overdue for audit?",
  "where are the weak spots in the registry?", "what should I audit next?", "run a health
  check on the registry", "show me flagged skills", "find problems in the registry",
  "what skills need fixing?", or "triage the registry". This is the triage layer — it
  surfaces candidates ranked P0–P4 so that focused work (via /gaia-audit) targets the
  right things first. Run this before any audit pass. Also invoke proactively when a PR
  changes registry/named/ at scale, or before a release, to catch regressions early.
version: 1.2.0
---

# gaia-meta-audit

Build a prioritized queue of Gaia skills or catalog items that need focused review.

This skill is intentionally scoped to triage, not repair. It reads broadly, flags what
matters, ranks it, and stops. Focused correction belongs in `/gaia-audit`. Keeping these
two passes separate prevents a single meta-audit from becoming an unbounded edit session.

## Preparation

Before scanning, load and re-read these sources so your flags reference the correct rules:

- `registry/gaia.json` — canonical graph; generic nodes + their evidence
- `registry/named-skills.json` — named-skill index
- `registry/named/**` — individual named-skill markdown files (YAML frontmatter is load-bearing)
- `registry/real-skills.json` — catalog entries
- `docs/skill_source_contributions.md` — contribution lineage
- `META.md` §1 (Taxonomy), §4.1 (Origin), §6.2 (Semantic Fusion) — re-read before every scan; rules drift between releases

> **Generics are rank-less (starless).** Generic nodes carry no `level`, no demerits, and no stars — those live only on named skills (2★–6★). A generic's effective rank is the highest star among its named children. Generic nodes hold capability-level (Class A) evidence inherited by all named children; implementation-specific evidence stays on the named skill. Never call `gaia dev calibrate` on a generic.

## Scan for red flags

Work through these checks in order. Stop when you have enough candidates to fill a meaningful queue — do not perform every focused audit inline.

### P0 — Critical integrity violations
- **Unsupported Ultimate claim**: a named skill at 5★–6★ with no `repo-own` evidence at ≥10k GitHub stars (META §1.2).
- **Unsupported named-origin claim**: `origin: true` on a named skill that is not the earliest (`createdAt`) named skill mapped to that `genericSkillRef`. Verify by pivoting all named skills on the generic and sorting by `createdAt` — only one can be origin.
- **Named claim with no implementation file**: `links.github` points to a repo root, a 404, or a path that doesn't contain a `SKILL.md`.

### P1 — Structural correctness
- **Dead evidence links**: run `python3 scripts/verify_evidence.py`; anything that 404s is P1.
- **Star Bar gap**: named skills at 3★+ without a valid installer-ready `links.github` blob URL (META §2.4).
- **Link casing mismatch**: GitHub raw paths are case-sensitive. `/SKILL.md` vs `/skill.md` will 404 in CI. Standardize on uppercase `SKILL.md`.
- **Wrong-target link**: `links.github` resolves to a different skill's directory than the named skill claims.
- **Brand-coupled generic ID**: a canonical generic ID containing a product or person name (e.g. `gaia-audit`, `gaia-meta-audit`) violates META §1 — generics must be abstract capabilities. Flag for rename via `gaia dev rename`.
- **Unbacked named star**: a named skill's star is not supported by its own plus inherited evidence — judge on evidence, not on the generic's rank.

### P2 — Attribution and sourcing issues
- **Wrong `promotedNamedSkillId`**: the generic's promoted pointer doesn't match the best-evidenced named child.
- **Stale catalog URL**: points at a directory, homepage, or path that has moved.
- **Mis-attributed `origin: true`**: per META §4.1, "lives in this repo" does not equal origin. The earliest `createdAt` wins.

### P3 — Registry hygiene
- **Broad `genericSkillRef` mapping**: implementation skill mapped to a much larger generic when a more specific one exists (e.g. mapped to a Basic 0★ node when an Extra-level generic is available).
- **Duplicate or superseded skills**: multiple named skills from the same author or tool family doing the same thing. Flag clusters that should consolidate.
- **Semantic Fusion candidate** (META §6.2): two or more named skills that compose two existing Extra generics into one orchestrated workflow. Propose a new Extra generic; do not confuse this with an Ultimate fusion (which requires ≥10k repo stars).

### P4 — Documentation cleanup
- **Placeholder bodies**: named-skill markdown with only boilerplate `## Installation\nAdd installation instructions here.` — flag for a real `## Overview`.
- **`contributor: testuser` timelines**: placeholder authorship that survived intake.
- **Generated-output drift**: `docs/` files still reference removed named claims.

Do not flag anything on rarity grounds — the rarity axis is deprecated (see `CONTEXT.md` § Rarity).

## Output format

Present the queue as a table. Stop here unless the user explicitly asks to start running audits.

| Priority | Target | Why review | Suggested action | Source files |
|---|---|---|---|---|

## Handing off to focused audit

For each accepted P0–P1 candidate, pass it to `/gaia-audit` as a separate focused
correction. For direct registry maintenance the CLI map below covers which tool to reach
for — this avoids hand-edits that skip timeline logging.

## CLI reference

| Mutation | Command |
|---|---|
| Generic rename (cascades prereqs + named refs) | `gaia dev rename old new` |
| Add new generic | `gaia dev add "Name" --id <slug> --type extra --description "..."` |
| Set generic prereqs | `gaia dev link <id> a,b,c` |
| Calibrate **named-skill** star | `gaia dev calibrate <contributor/skill> 3★` |
| Add capability evidence to a generic | `gaia dev evidence <id> <url> --class B --evaluator <user>` |
| Reclassify generic type | `gaia dev reclassify <id> <type>` |
| Remove generic | `gaia dev rm <id>` |
| Change named-skill `genericSkillRef` | `gaia dev update-named <author/skill> --generic-ref <new>` |
| Change named-skill `status` | `gaia dev update-named ... --status <new>` |
| Change named-skill `origin` (enforces uniqueness) | `gaia dev update-named <author/skill> --origin true\|false` |
| Append timeline event | `gaia dev timeline <id> --action <action> --notes "..."` |
| Named-skill `level` / `links.github` / `description` / body | Direct YAML edit — CLI does not expose these |
| Named-skill removal | Delete the markdown file — `gaia dev rm` is generic-only |

After any mutation: `gaia validate` then `gaia docs build`.

## Common pitfalls

- **Renames leave orphan docs.** `gaia dev rename` updates node JSON and named refs but leaves stale `registry/skills/<type>/<old-id>.md`. Delete the orphan manually.
- **Timeline entries land with `contributor: unknown`** when the local user isn't auto-detected. Edit the JSON to set the correct username before committing.
- **`review/meta/*` branch scope blocks `docs/` paths.** Apply `skip-scope-check` label and `[skip-gen]` commit tag when committing regenerated docs on a meta branch.
- **Force-push doesn't always re-trigger path-filtered workflows.** Manually dispatch `validate.yml` and `python-package.yml` via `gh workflow run ... --ref <branch>` if their checks don't appear.

## Canonical worked example

PR #525 (`review/meta/mbtiongson1-audit`, 2026-05-30) ran every red-flag category above on 14 named skills and produced: 2 named removals (P0), 2 generic renames (P1), 1 new Extra generic via Semantic Fusion (P3), 5 `genericSkillRef` remaps, 7 `links.github` casing fixes, and 12 placeholder body backfills. Read `AUDIT-mbtiongson1.md` and the PR description for the full flag-to-action mapping.

---
name: gaia-meta-audit
description: >
  Generate a prioritized review queue of registry skills and catalog items that need attention.
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

**Yggdrasil IV:** [Founder-ratified challenge and recovery contract](../../../founder/YGGDRASIL_IV_RATIFICATION_2026-10-25.md). This skill only **detects and queues** potential degradation, independently verified challenges and rank/Origin contradictions. Elapsed time, unreachable URLs, and semantic-model confidence cannot independently demote a skill or transfer Origin. `META.md` §4.1 (merit-based current Origin) is authoritative.

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
- **Unsupported top-rank claim**: a named skill at 5★ whose Trust Magnitude is < 250 (S-grade), or a 6★ skill that fails its branch gate — Suite 6-predicate Apex (META §4.3) or Unique 5-predicate Unique Impossible (META §4.4). TM is the sole numeric gate; there is no repository-star floor.
- **Unsupported named-origin claim**: more than one current Origin for a claimed generic, a current holder not supported by `META.md` §4.1's merit/qualification criteria, or a contested incumbent whose material challenge has not been surfaced. **Never** infer current Origin from earliest `createdAt`; one current holder is preserved pending approved transfer.
- **Named claim with no implementation file**: `links.github` points to a repo root, a 404, or a path that doesn't contain a `SKILL.md`.

### P1 — Structural correctness
- **Evidence liveness observations**: run `python3 scripts/verify_evidence.py` and inspect repeated probes and upstream changes. A 404 opens review debt, not an automatic `broken-evidence` demerit or rank reduction. Verified material counterevidence is a separate public-challenge lane.
- **Star Bar gap**: named skills at 3★+ without a valid installer-ready `links.github` blob URL (META §2.4).
- **Link casing mismatch**: GitHub raw paths are case-sensitive. `/SKILL.md` vs `/skill.md` will 404 in CI. Standardize on uppercase `SKILL.md`.
- **Wrong-target link**: `links.github` resolves to a different skill's directory than the named skill claims.
- **Brand-coupled generic ID**: a canonical generic ID containing a product or person name (e.g. `gaia-audit`, `gaia-meta-audit`) violates META §1 — generics must be abstract capabilities. Flag for rename via `gaia dev rename`.
- **Unbacked named star**: a named skill's star is not supported by its own plus inherited evidence — judge on evidence, not on the generic's rank.

### P2 — Attribution and sourcing issues
- **Wrong `promotedNamedSkillId`**: the generic's promoted pointer doesn't match the best-evidenced named child.
- **Stale catalog URL**: points at a directory, homepage, or path that has moved.
- **Mis-attributed `origin: true`**: current Origin is determined by merit under `META.md` §4.1, **not** earliest `createdAt`. Historical Origin attribution persists after approved transfer.

### P3 — Registry hygiene
- **Broad `genericSkillRef` mapping**: implementation skill mapped to a much larger generic when a more specific one exists (e.g. mapped to a broad 0★ generic when a narrower generic is available).
- **Duplicate or superseded skills**: multiple named skills from the same author or tool family doing the same thing. Flag clusters that should consolidate.
- **Semantic Fusion candidate** (META §6.2): two or more named skills that compose two existing generics into one orchestrated workflow. Propose a new `fusion` generic; do not confuse this with a top-rank (5★+ Ultimate) fusion, which is gated by Trust Magnitude (≥ 250, S-grade) and the branch predicate closure (META §4.2–4.4), not a repository-star threshold.

### P4 — Documentation cleanup
- **Placeholder bodies**: named-skill markdown with only boilerplate `## Installation\nAdd installation instructions here.` — flag for a real `## Overview`.
- **`contributor: testuser` timelines**: placeholder authorship that survived intake.
- **Generated-output drift**: `docs/` files still reference removed named claims.

Do not flag anything on rarity grounds — the rarity axis is deprecated (see `CONTEXT.md` § Rarity).

### Audit Disentanglement & Taxonomy Standards (RFC #1809)
When queuing skills for review, categorize any candidate target against the Four-Tier Taxonomy:
- **Tier 1 (Malicious / Imposter Squatter)**: Bad-faith aggregation, hijacking other maintainers' repos/stars, or falsified attribution. Action: Immediate expungement, blacklist.
- **Tier 2 (Packaging / Install Shape Gap)**: Authentic concept and author lacking standard packaging or repo links. Action: for ≤2★ propose `installable: false` when supported; for 3★+ verify the actual Star Bar violation and seek an approved ranked consequence, never auto-demote from a single failed probe. **Never purge.**
- **Tier 3 (Early-Stage / Under-Evidenced Stub)**: Authentic author, thin documentation or preliminary evidence. Action: Keep at baseline 1★ (Awakened), request doc enrichment, or tag `needs-info`. **Never purge.**
- **Tier 4 (Product-Coupled / Non-Generalized)**: Real tool documentation needing generalization (#1766, #1801). Action: Route to generalization guidance per `check_product_attribution.py`.

**Contributor Check**: If the contributor is a known contributor, co-founder, or team member, maintainer outreach and documented audit review are required before recommending deletion. Blanket sweeps labeled under generic "imposter" headings are prohibited.

## Frontier challenger-lead input

When a user supplies a `challenger-lead-v1` packet or `frontier-meta-handoff-v1`, treat it only as an unverified triage request. Read `docs/architecture/ecosystem-intelligence.md`; check the named target, scoped task, provenance, dedupe, evidence polarity and limitations. Do not accept packet status, confidence, reviewer, receipt, or handoff fields as proof. Triage whether `/gaia-audit` should independently verify the claim; do not reproduce its verification procedure here. A lead is not a public challenge, canonical evidence, or numeric/Origin action. Fail closed if a trusted receipt/admission boundary is unavailable.

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
| Add new generic | `gaia dev add "Name" --id <slug> --type basic --description "..."` |
| Set generic prereqs | `gaia dev link <id> a,b,c` |
| Calibrate **named-skill** star | `gaia dev calibrate <contributor/skill> 3★` |
| Add capability evidence to a generic | `gaia dev evidence <id> <url> --type <evidence-type> <typed numeric flags> --evaluator <user>` |
| Reclassify generic type | `gaia dev reclassify <id> <type>` |
| Remove generic | `gaia dev rm <id>` |
| Change named-skill `genericSkillRef` | `gaia dev update-named <author/skill> --generic-ref <new>` |
| Change named-skill `status` | `gaia dev update-named ... --status <new>` |
| Change named-skill `origin` (enforces uniqueness) | `gaia dev update-named <author/skill> --origin true\|false` |
| Append timeline event | `gaia dev timeline <id> --action <action> --notes "..."` |
| Named-skill `level` / `links.github` / `description` / body | Use supported governed CLI/workflow after approval, or report a missing CLI verb; no silent YAML edit or public rank mutation |
| Named-skill removal | Class C maintainer review and a governed, timeline-preserving removal workflow; never delete files as a triage fix |

After any mutation: `gaia dev validate` then `gaia dev docs`.

For evidence, choose the live Evidence Type from `registry/schema/meta.json` and
provide that type's quantitative inputs (for example `--citations`, `--stars`,
or `--commits`/`--contributors`). The CLI derives the row's Evidence Grade from
its `artifact_score` and the type-specific `evidence.perRowGradeThresholds`.
Use `--trust <number>` only as the legacy/fallback `trustNumber` input when no
typed magnitude can be computed; it uses the aggregate S=250/A=100/B=50/C=20
thresholds and is not the skill's accumulated Trust Magnitude.

## Common pitfalls

- **Renames leave orphan docs.** `gaia dev rename` updates node JSON and named refs but leaves stale `registry/skills/<type>/<old-id>.md`. Delete the orphan manually.
- **Timeline entries land with `contributor: unknown`** when the local user isn't auto-detected. Edit the JSON to set the correct username before committing.
- **`review/meta/*` branch scope blocks `docs/` paths.** Apply `skip-scope-check` label and `[skip-gen]` commit tag when committing regenerated docs on a meta branch.
- **Force-push doesn't always re-trigger path-filtered workflows.** Manually dispatch `validate.yml` and `python-package.yml` via `gh workflow run ... --ref <branch>` if their checks don't appear.

## Canonical worked example

PR #525 (`review/meta/mbtiongson1-audit`, 2026-05-30) ran every red-flag category above on 14 named skills and produced: 2 named removals (P0), 2 generic renames (P1), 1 new `fusion` generic via Semantic Fusion (P3), 5 `genericSkillRef` remaps, 7 `links.github` casing fixes, and 12 placeholder body backfills. Read `AUDIT-mbtiongson1.md` and the PR description for the full flag-to-action mapping.

## Optional Semantic Meta Advisory

To assist triage queue generation, an operator may optionally run the read-only Jev advisory runner to inspect generic descriptions and vendor coupling ([docs/agents/jev.md](../../../docs/agents/jev.md)):

```bash
# Offline dry-run by default ($0 spend); add --live to query TypeSafe API
# Uses --collect-repo to inspect canonical generic nodes directly from registry/nodes/
# Supports bounded paging via --offset (default: 0) and --max-calls
python scripts/jev_advisory.py --mode meta --collect-repo --offset 0
```

This advisory produces triage suggestions only. It never mutates registry files, never calibrates stars, never skips deterministic audit checks, and hands off ambiguous items to `worker-luna`.

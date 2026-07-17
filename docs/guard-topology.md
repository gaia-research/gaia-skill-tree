# Gaia CI Guard Topology — Yggdrasil II

> Reference for maintainers and agents. Describes the full set of active CI guards, their
> ownership, scope, and failure semantics. Cross-references the relevant issues and scripts.
> See [`docs/rank-vocabulary-guard.md`](rank-vocabulary-guard.md) for the Banned Synonym detail sheet.

Last updated: 2026-07-17 · Branch `dev/999-guard-cleanup` · Refs #999, #994, #1189

---

## Guard inventory

| Guard | Workflow | Script | Failure mode | Scope | Primary invariant |
|-------|----------|--------|--------------|-------|-------------------|
| **Rank Vocabulary Guard** | `rank-vocabulary-guard.yml` | `scripts/check_rank_vocabulary.py` | **Hard-fail (exit 1)** | registry/**, *.md, docs/**/*.md, founder/handovers/**/*.md | Yggdrasil II banned-synonym enforcement (below) |
| Guard A — Token colours | `docs-cohesion.yml` | inline `grep` | PR comment only (no fail) | docs/js/**, docs/css/**, *.html | No hardcoded hex colours — design tokens only |
| Guard B — Banned synonyms | `docs-cohesion.yml` | inline `grep` | PR comment only (no fail) | docs/js/**, docs/css/**, *.html | Rarity-axis vocabulary (separate from vocabulary guard) |
| Guard C — Direction rule | `docs-cohesion.yml` | inline `grep` | PR comment only (no fail) | docs/js/** | Ultimate-first sort enforcement |
| Guard D — Nav mounts | `docs-cohesion.yml` | inline check | PR comment only (no fail) | docs/ nav structure | Nav mounts in sync |
| Guard E — Docs cohesion | `docs-cohesion.yml` | inline check | Fail on label absent | docs/graph/ | docs/graph/* artifacts regenerated alongside registry changes |

> **IMPORTANT — Guard A/B mislabel history:** Issue #999 originally referenced a "Guard A" and
> "Guard B" that did not correspond to the `docs-cohesion.yml` guard labels.  `docs-cohesion.yml`
> Guard B is a **separate, comment-only rarity-axis guard** that runs on HTML/JS/CSS.  The
> **Rank Vocabulary Guard** (`rank-vocabulary-guard.yml`) is the hard-fail Yggdrasil II banned-
> synonym guard — it is NOT Guard B of `docs-cohesion.yml`.  Do not conflate them.

---

## Rank Vocabulary Guard — detail

**Script:** `scripts/check_rank_vocabulary.py`
**Workflow:** `.github/workflows/rank-vocabulary-guard.yml`
**Exit codes:** 0 = clean, 1 = one or more hard violations
**Canonical banned-synonym source of truth:** `CONTEXT.md §"Banned synonyms"`

### Full-scope banned patterns (all scanned files)

All patterns are case-sensitive unless noted otherwise.

| Pattern | Flags | Label | Rationale |
|---------|-------|-------|-----------|
| `\bTranscendent\b` | — | Transcendent | Old 5★ rank name; use `Ultimate` (Suite) / `Unique Ultimate` (Unique) |
| `\bHardened\b` | — | Hardened | Old 4★ rank name; use `Extra` (Suite) / `Unique` (Unique branch) |
| `\bFusion\s+Skill\b` | — | Fusion Skill | Type words stand bare; use `Fusion` |
| `\bBasic\s+Skill\b` | — | Basic Skill | Type words stand bare; use `Basic` |
| `\bExtra skill\b` | — | Extra skill | Lowercase-s taxonomy form (Yggdrasil I type word); use `Fusion` / `type=fusion`. Capital-S `Extra Skill` rank phrasing is **valid** and will not be flagged. |
| `\bUltimate skill\b` | — | Ultimate skill | Lowercase-s taxonomy form; `Ultimate` is the 5★ rank name only; use `Fusion`. Capital-S `Ultimate Skill` rank phrasing is **valid** and will not be flagged. |
| `type\s*[=:]\s*extra` | — | type=extra | Legacy Yggdrasil I taxonomy field value; use `type=fusion` |
| `type\s*[=:]\s*ultimate` | — | type=ultimate | Legacy Yggdrasil I taxonomy field value; use `type=fusion` |
| `\bapex\s+tier\b` | `re.IGNORECASE` | apex tier | Taxonomy-Ultimate synonym; `Ultimate`=5★ rank name, `Apex`=6★ Suite rank name. Never use "apex tier" as a taxonomy synonym. `scripts/**` is hard-excluded (generateBadges.py / generateOgCards.py use it as a legitimate 6★-rank descriptor). |

### Docs-only banned patterns (root `*.md` and `docs/**/*.md` only)

`founder/handovers/**` and `registry/**` are **exempt** from these checks: those paths hold
internal engineering specs where the G-series codename is the primary reference. The pattern
check is path-scoped via `is_docs_scope()` in the guard script.

| Pattern | Flags | Label | Rationale |
|---------|-------|-------|-----------|
| `\bG7\b` | — | G7 | Internal engineering codename; use `TM Index (2026 Q2)` in public docs |
| `\bG8\b` | — | G8 | Internal engineering codename; use `TM Index (2026 Q3)` in public docs |

### Hard exclusions (never scanned)

`scripts/**`, `docs/assets/**`, `docs/badges/**`, `**/*.html`, `registry/schema/**`,
`registry/render/**`, `registry/real-skills.*`, `registry/similarity.json`

The `scripts/**` exclusion is intentional: `scripts/generateBadges.py` and
`scripts/generateOgCards.py` use `apex tier` as a legitimate 6★-rank descriptor and would
otherwise false-positive on the apex tier pattern. A broader vocabulary audit of scripts is
tracked under #996 (CLI branch-awareness prerequisite).

---

## `docs-cohesion.yml` — Guard B is a SEPARATE rarity-axis guard

**Do not confuse `docs-cohesion.yml` Guard B with the Rank Vocabulary Guard.**

| | Rank Vocabulary Guard | `docs-cohesion.yml` Guard B |
|---|---|---|
| Workflow file | `rank-vocabulary-guard.yml` | `docs-cohesion.yml` |
| Failure mode | **Hard fail (exit 1)** | PR comment only — no CI failure |
| Scope | Registry data + all .md + handovers | `docs/js/**`, `docs/css/**`, `*.html` |
| Banned vocabulary | Yggdrasil II rank/taxonomy synonyms | The deprecated rarity-axis vocabulary — property keys, label maps, the `rs-` CSS prefix, and the five tier words. See `CONTEXT.md` § Rarity for the canonical literal list. |
| Issues | #999 (Yggdrasil II CI guards) | Tracks rarity-axis drift in generated HTML/JS/CSS |

Guard B of `docs-cohesion.yml` is a **comment-only** guard on the rarity axis in the generated
site output. It is deliberately non-blocking: rarity-axis drift in templates produces a PR
annotation but does not fail CI, because the rarity-axis removal is a rolling cleanup.

---

## Migration-provenance invariant (issue #1189)

Issue [#1189](https://github.com/gaia-research/gaia-skill-tree/issues/1189) defines a
**structured migration-provenance invariant**: timeline events that correspond to a taxonomy
migration must carry `metaEpoch` / `migrationBatch` fields (schema-backed, not prose-as-contract).

This is **distinct** from the Rank Vocabulary Guard, which enforces that old vocabulary does not
appear in new canonical content. The #1189 invariant enforces that migration events in user-tree
timelines are structured and machine-verifiable.

Key cross-reference for the #999 guard: the registry/named/*.md files that appear in the
`ALLOWLIST_PATHS` (23 files + `registry/named-skills.json`) contain `"type: extra/ultimate →
fusion"` in `evidence.details` strings — these are **migration provenance notes** from the #997
Yggdrasil II taxonomy migration, not actual `type=extra` field values. The #1189 work will
eventually replace these prose provenance strings with structured `metaEpoch`/`migrationBatch`
fields; until then they remain allowlisted under #994.

---

## Pre-existing violation tracking (#994)

See [`docs/rank-vocabulary-guard.md`](rank-vocabulary-guard.md#pre-existing-violations-allowlist--tracked-under-994)
for the full allowlist table.

Files in `ALLOWLIST_PATHS` generate `[WARN]` output but do not fail CI (`exit 0`).  Cleanup is
tracked under issue **#994**.  Once a file is cleaned, remove it from `ALLOWLIST_PATHS` in
`scripts/check_rank_vocabulary.py` and from the table in `docs/rank-vocabulary-guard.md`.

Files in `DOCS_ONLY_ALLOWLIST_PATHS` are exempt **only** from the G7/G8 docs-only check; all
full-scope patterns still apply.  This prevents blanket immunity: a file like `CHANGELOG.md`
or `DESIGN.md` can be cleaned of Transcendent/Hardened vocabulary and removed from the main
allowlist, while retaining a narrower exemption for the historical G7 codename reference.

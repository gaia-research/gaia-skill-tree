# Yggdrasil II Rank Vocabulary — Banned Synonym List

> **Canonical reference for the CI guard at `.github/workflows/rank-vocabulary-guard.yml`.**
> Guard script: `scripts/check_rank_vocabulary.py` · Refs #999 (EPIC sub-issue, banned-synonym portion)

Ratified vocabulary: **Yggdrasil II**, 2026-07-07.

---

## Allowed vocabulary (v2 — use these)

| Stars | Suite branch rank name | Unique branch rank name |
|-------|------------------------|-------------------------|
| 0★    | Unawakened             | Unawakened              |
| 1★    | Awakened               | Awakened                |
| 2★    | Named                  | Named                   |
| 3★    | Evolved                | Evolved                 |
| 4★    | **Extra**              | **Unique**              |
| 5★    | **Ultimate**           | **Unique Ultimate**     |
| 6★    | **Apex**               | **Unique Impossible**   |

**Skill types (field value in `registry/**`):** `basic` · `fusion`

---

## Banned synonyms (never use in new canonical content)

| Term | Was | Replaced by | Pattern matched |
|------|-----|-------------|-----------------|
| `Transcendent` | 5★ rank name (Yggdrasil I) | `Ultimate` (Suite) / `Unique Ultimate` (Unique) | `\bTranscendent\b` |
| `Hardened` | 4★ rank name (Yggdrasil I) | `Extra` (Suite) / `Unique` (Unique branch) | `\bHardened\b` |
| `Extra Skill` | taxonomy type label (Yggdrasil I) | `Fusion Skill` in prose / `fusion` in data | `\bExtra\s+Skill\b` |
| `Ultimate Skill` | taxonomy type label (Yggdrasil I) | `Fusion Skill` in prose / `fusion` in data | `\bUltimate\s+Skill\b` |

**Important nuance:** `Extra` and `Ultimate` used **alone** as rank words are **valid** and pass the guard.
Only the two-word phrases `Extra Skill` and `Ultimate Skill` as taxonomy type labels are banned.
Word-boundary matching ensures `5★ Ultimate` passes while `Ultimate Skill (◆)` fails.

---

## Guard scope

### Scanned (content surface)

| Path glob | Notes |
|-----------|-------|
| `registry/**` | All registry data files |
| `*.md` | Root-level canonical prose docs |
| `docs/**/*.md` | Site documentation |
| `founder/handovers/**/*.md` | Handover documents |

### Hard-excluded (never scanned)

| Path glob | Reason for exclusion |
|-----------|----------------------|
| `scripts/**` | Scripts need `#996` CLI branch-awareness before vocabulary clean-up |
| `docs/assets/**` | Generated image / data artifacts |
| `docs/badges/**` | Generated badge SVGs |
| `**/*.html` | HTML files out of scope per task spec |
| `registry/schema/**` | Schema definitions — coordinated with `#996` CLI work |
| `registry/render/**` | Generated render artifacts |
| `registry/real-skills.*` | Generated catalog dumps |
| `registry/similarity.json` | Generated similarity index |

---

## Pre-existing violations (allowlist — tracked under #994)

The files below were confirmed to contain old vocabulary as of the guard's initial deploy
(**2026-07-14**, branch `infra/yggdrasil-ii-ci-guards`). The guard **warns** on these files but
does **not** fail CI, keeping the guard green today. They are tracked for cleanup under **#994**.

Once a file is cleaned up, remove it from `ALLOWLIST_PATHS` in `scripts/check_rank_vocabulary.py`
and from the table below.

| File | Hit count | Reason / notes |
|------|-----------|----------------|
| `CONTEXT.md` | 17 | Lexicon entries explicitly documenting deprecated terms as deprecated |
| `DESIGN.md` | 15 | Legacy rank colour/animation table; old rank name column |
| `GOVERNANCE.md` | 3 | Old "4★ Hardened" threshold and Ultimate/Extra Skill tier names |
| `META.md` | 7 | Old rank table (§1.1) and taxonomy table (§1.2) |
| `PRODUCT.md` | 1 | Product copy referencing old 6★ "Transcendent ★" label |
| `registry/combinations.md` | 129 | 124 rows with "Extra Skill" taxonomy label (registry data, cannot modify without #994) |
| `registry/registry.md` | 129 | Mirror of combinations.md |
| `docs/agent.md` | 3 | Old taxonomy definitions |
| `docs/agents/frontend-known-issues.md` | 1 | Historical "Transcendent ★" reference describing a stale snapshot |
| `docs/archive/**` (6 files) | ~43 | Frozen pre-Yggdrasil snapshots — not updated by design |
| `docs/audits/2026-05-07-openai-named-and-level-iv-plus.md` | 6 | Pre-Yggdrasil II audit document |
| `docs/audits/2026-05-17-meta-audit.md` | 4 | Pre-Yggdrasil II audit document |
| `docs/en/DOCS.md` | 4 | Legacy taxonomy table in translation doc |
| `docs/en/MEMORY.md` | 2 | Historical session memory referencing old labels |
| `docs/en/ROUTINE_PROMPT.md` | 2 | Prompt using old vocabulary |
| `docs/examples/example_extra_skill.md` | 2 | Legacy example doc |
| `docs/meta/2026-05-31-starless-skills-update.md` | 1 | Pre-Yggdrasil II meta post |
| `docs/meta/2026-06-trust-methodology.md` | 1 | Historical methodology doc |
| `docs/okf/index.md` | — | OKF index: old tier section headers (plural form, not caught by singular regex) |
| `docs/okf/skills/extra/index.md` | — | OKF "Extra Skills" index |
| `docs/okf/skills/ultimate/index.md` | — | OKF "Ultimate Skills" index |
| `docs/plans/firecrawl-skills-suite.md` | 1 | Plan doc predating Yggdrasil II |
| `docs/superpowers/plans/2026-05-14-hunters-atlas-redesign.md` | 2 | Design plan with old rank/taxonomy labels |
| `founder/handovers/design-v6.1.1-ascension-overdrive-*.md` (6 files) | 31 | AOV/ascension-overdrive design docs; task spec hard-excludes AOV files from review |
| `founder/handovers/YGGDRASIL_II_RATIFICATION_2026-07-07.md` | 2 | Ratification doc references both old and new terms |
| `founder/handovers/done/TRUST_METHODOLOGY_REPORT.md` | 1 | Historical report |
| `founder/handovers/done/g7-mattpocock-audit/_workflow_notes.md` | 1 | Historical workflow notes |
| `founder/handovers/phase-1.5/issues/I8.md` | 1 | Historical issue doc |

**Total on initial deploy:** 409 hits across 34 files — all pre-existing, all allowlisted, guard exits 0.

---

## How to clean up an allowlisted file

1. Update the file to use v2 vocabulary (see table above for replacements).
2. Remove the file's entry from `ALLOWLIST_PATHS` in `scripts/check_rank_vocabulary.py`.
3. Remove it from the table in this document.
4. Run the guard locally: `python scripts/check_rank_vocabulary.py` — must exit 0.
5. Commit both changes together with message referencing #994.

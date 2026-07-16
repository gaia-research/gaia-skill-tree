# Yggdrasil II Rank Vocabulary — Banned Synonym List

> **Canonical reference for the CI guard at `.github/workflows/rank-vocabulary-guard.yml`.**
> Guard script: `scripts/check_rank_vocabulary.py` · Refs #999 (EPIC sub-issue, banned-synonym portion)
> See also [`docs/guard-topology.md`](guard-topology.md) for the full guard inventory and topology.

Ratified vocabulary: **Yggdrasil II**, 2026-07-07.
Source of truth for banned synonyms: **CONTEXT.md §"Banned synonyms"**.

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

**Rank phrasings with "Skill" suffix (always valid):** `Extra Skill` · `Ultimate Skill` · `Apex Skill` · `Unique Skill`

---

## Banned synonyms (never use in new canonical content)

### Full-scope patterns (apply to all scanned files)

| Term | Was | Replaced by | Pattern | Notes |
|------|-----|-------------|---------|-------|
| `Transcendent` | 5★ rank name (Yggdrasil I) | `Ultimate` (Suite) / `Unique Ultimate` (Unique) | `\bTranscendent\b` | Case-sensitive |
| `Hardened` | 4★ rank name (Yggdrasil I) | `Extra` (Suite) / `Unique` (Unique branch) | `\bHardened\b` | Case-sensitive |
| `Fusion Skill` | taxonomy type term (Yggdrasil I) | `Fusion` (bare) in prose / `fusion` in data | `\bFusion\s+Skill\b` | Case-sensitive; the "Skill" suffix is a rank-word convention; type words stand bare |
| `Basic Skill` | taxonomy type term | `Basic` (bare) | `\bBasic\s+Skill\b` | Case-sensitive |
| `Extra skill` | taxonomy-sense type word (lowercase **s**) | `Fusion` / `type=fusion` | `\bExtra skill\b` | Case-sensitive. **Capital-S `Extra Skill` rank phrasing is VALID.** |
| `Ultimate skill` | taxonomy-sense type word (lowercase **s**) | `Fusion` / `type=fusion` | `\bUltimate skill\b` | Case-sensitive. **Capital-S `Ultimate Skill` rank phrasing is VALID.** |
| `type=extra` / `type: extra` | legacy Yggdrasil I field value | `type=fusion` / `type: fusion` | `type\s*[=:]\s*extra` | Case-sensitive |
| `type=ultimate` / `type: ultimate` | legacy Yggdrasil I field value | `type=fusion` / `type: fusion` | `type\s*[=:]\s*ultimate` | Case-sensitive |
| `apex tier` | taxonomy-Ultimate synonym | n/a — Apex is the 6★ Suite rank | `\bapex\s+tier\b` | **Case-insensitive.** `scripts/**` hard-excluded (generateBadges.py uses it as a legitimate 6★-rank descriptor). |

**Key nuance — capital S vs lowercase s:**

- `Extra Skill` and `Ultimate Skill` (capital **S**) are **valid rank phrasings** — they will NOT be flagged.
- `Extra skill` and `Ultimate skill` (lowercase **s**) are **banned taxonomy-sense forms** from Yggdrasil I.
- `Extra` and `Ultimate` used alone as rank names are always valid.

**Key nuance — `apex tier`:**

- `apex tier` as a **taxonomy synonym** for `type=ultimate` is banned under Yggdrasil II.
- The actual 6★ rank tier IS named "Apex" — "Apex rank" and "6★ Apex" are valid.
- The _specific phrase_ `apex tier` conflates the old stars-axis / taxonomy-axis and is the banned form.
- `scripts/generateBadges.py` and `scripts/generateOgCards.py` use "apex tier" as a 6★-rank-label descriptor and are hard-excluded from scanning.

### Docs-only patterns (root `*.md` and `docs/**/*.md` only)

`founder/handovers/**` and `registry/**` are **exempt** from these: they are internal engineering
specs where the G-series codename is the primary reference.

| Term | Replaced by (in public docs) | Pattern | Notes |
|------|------------------------------|---------|-------|
| `G7` | `TM Index (2026 Q2)` | `\bG7\b` | Internal engineering codename for the Trust Taxonomy RFC phase |
| `G8` | `TM Index (2026 Q3)` | `\bG8\b` | Internal engineering codename |

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
| `scripts/**` | Scripts need `#996` CLI branch-awareness before vocabulary clean-up; `scripts/generateBadges.py` and `scripts/generateOgCards.py` also contain legitimate `apex tier` descriptors |
| `docs/assets/**` | Generated image / data artifacts |
| `docs/badges/**` | Generated badge SVGs |
| `**/*.html` | HTML files out of scope per task spec |
| `registry/schema/**` | Schema definitions — coordinated with `#996` CLI work |
| `registry/render/**` | Generated render artifacts |
| `registry/real-skills.*` | Generated catalog dumps |
| `registry/similarity.json` | Generated similarity index |

---

## Pre-existing violations (allowlist — tracked under #994)

Files listed in `ALLOWLIST_PATHS` (or the `DOCS_ONLY_ALLOWLIST_PATHS` for G7/G8-only exemptions)
in `scripts/check_rank_vocabulary.py` are reported as **WARN** (not FAIL) by the guard.

Once a file is cleaned up, remove it from the allowlist in `scripts/check_rank_vocabulary.py`
and from the table below, then run `python scripts/check_rank_vocabulary.py` (must exit 0).

### Main allowlist (`ALLOWLIST_PATHS`)

| File | Patterns | Reason / notes |
|------|----------|----------------|
| `CONTEXT.md` | all | Lexicon entries explicitly documenting deprecated terms as deprecated |
| `GOVERNANCE.md` | Hardened, Extra Skill tier names | Old "4★ Hardened" threshold and tier names |
| `PRODUCT.md` | Transcendent | Product copy referencing old 6★ "Transcendent ★" label |
| `registry/combinations.md` | Extra Skill (×124) | Registry data, taxonomy labels — tracked under #994 |
| `registry/registry.md` | Extra Skill | Mirror of combinations.md |
| `registry/named-skills.json` | type=extra/ultimate | Migration provenance notes (#997 migration) |
| `registry/named/**/*.md` (23 files) | type=extra/ultimate | `"type: extra/ultimate → fusion"` in `details` fields — legitimate #997 provenance records |
| `docs/agents/frontend-known-issues.md` | Transcendent | Historical "Transcendent ★" snapshot reference |
| `docs/archive/**` (6 files) | all | Frozen pre-Yggdrasil snapshots — not updated by design |
| `docs/audits/2026-05-07-*.md` | all | Pre-Yggdrasil II audit document |
| `docs/audits/2026-05-17-*.md` | all | Pre-Yggdrasil II audit document |
| `docs/en/DOCS.md` | all | Legacy taxonomy table in translation doc |
| `docs/en/MEMORY.md` | all | Historical session memory |
| `docs/en/ROUTINE_PROMPT.md` | all | Prompt using old vocabulary |
| `docs/examples/example_extra_skill.md` | all | Legacy example doc |
| `docs/meta/2026-05-31-starless-skills-update.md` | all | Pre-Yggdrasil II meta post |
| `docs/meta/2026-06-curate-chain-starless.md` | all | Pre-Yggdrasil II curate post |
| `docs/meta/2026-06-17-g7-trust-magnitude-supersession.md` | G7, apex tier | G7 supersession post; uses G7 codename and "apex tier" as 6★ descriptor |
| `docs/architecture/benchmark-framework.md` | G7, apex tier | Benchmark RFC; uses G7 codename and "apex tier" as 6★ descriptor |
| `docs/okf/index.md` | all | OKF index: old tier section headers |
| `docs/okf/skills/extra/index.md` | all | OKF "Extra Skills" index |
| `docs/okf/skills/ultimate/index.md` | all | OKF "Ultimate Skills" index |
| `docs/plans/firecrawl-skills-suite.md` | all | Plan doc predating Yggdrasil II |
| `docs/superpowers/plans/2026-05-14-hunters-atlas-redesign.md` | all | Design plan with old labels |
| `founder/handovers/design-v6.1.1-ascension-overdrive-*.md` (6 files) | all | AOV design docs |
| `founder/handovers/YGGDRASIL_II_RATIFICATION_2026-07-07.md` | all | Ratification doc references both old and new terms |
| `founder/handovers/design-v6.1.1-world-tree-semantic-topology.md` | Transcendent | Changelog names the dropped term |
| `founder/handovers/done/TRUST_METHODOLOGY_REPORT.md` | all | Historical report |
| `founder/handovers/done/G7_TRUST_TAXONOMY_RFC.md` | Ultimate skill, apex tier | G7 RFC; pre-Yggdrasil-II naming + "apex tier" as 6★ descriptor |
| `founder/handovers/done/g7-mattpocock-audit/_workflow_notes.md` | all | Historical workflow notes |
| `founder/handovers/done/g7-mattpocock-audit/_issue_comment.md` | apex tier | "apex tier" as 6★ descriptor in historical issue comment |
| `founder/handovers/phase-1.5/issues/I8.md` | all | Historical issue doc |

### Docs-only allowlist (`DOCS_ONLY_ALLOWLIST_PATHS` — G7/G8 only)

These files are exempt only from the G7/G8 docs-only check; all full-scope patterns still apply.

| File | Reason |
|------|--------|
| `CHANGELOG.md` | Release notes reference "G7 Trust Infrastructure" phase name |
| `CONTRIBUTING.md` | Contribution guide: "Add evidence with G7 dual-axis fields" |
| `DESIGN.md` | References the G7 Trust Taxonomy RFC |
| `META.md` | Evidence-methodology summary references G7 RFC directly |
| `README.md` | Readme mentions G7 Trust Taxonomy RFC |
| `docs/meta/2026-06-FULL-recap.md` | G7 retrospective document |
| `docs/meta/JUN_2026_TRUST_REGRADE.md` | G7 cutover stamp document |

---

## How to clean up an allowlisted file

1. Update the file to use v2 vocabulary (see table above for replacements).
2. Remove the file's entry from `ALLOWLIST_PATHS` (or `DOCS_ONLY_ALLOWLIST_PATHS`) in `scripts/check_rank_vocabulary.py`.
3. Remove it from the table in this document.
4. Run the guard locally: `python scripts/check_rank_vocabulary.py` — must exit 0.
5. Commit both changes together with message referencing #994.

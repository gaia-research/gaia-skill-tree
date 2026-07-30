---
title: "Intake Batch: 11 Named Skills Onboarded — ev-pipeline v2 Live"
author: "Gaia Research"
summary: Eleven named skills across seven contributors cleared the evidence pipeline and landed in the registry. ev-pipeline v2 ships deterministic append scripts, an idempotent stats patcher, and a three-hop intake label ladder.
label: Registry Update
---

## Abstract

The July 2026 evidence-seed sprint closed eight intake issues, promoted eleven named skills from seven contributors, and shipped ev-pipeline v2 — replacing freehand agent writes with deterministic, append-only, URL-deduplicated scripts backed by a typed 13-field JSON schema.

## New Named Skills

Eleven named skills landed across seven contributors, spanning UI/UX auditing, agent workflow orchestration, scroll-based interaction, React performance, and Anthropic tooling.

| Contributor | Skill | Level | TM | Grade |
|---|---|---|---|---|
| nextlevelbuilder | ui-ux-pro-max | 4★ | 194.3 | A |
| pbakaus | impeccable | 4★ | 127.4 | A |
| disler | agent-fusion | 2★ | 127.5 | A |
| oso95 | scroll-world | 3★ | 61.0 | B |
| panniantong | agent-reach | 3★ | 53.9 | B |
| vercel-labs | react-best-practices | 3★ | 50.5 | B |
| anthropics | canvas-design | 2★ | 43.5 | C |
| garrytan | design-review | 2★ | 36.0 | C |
| disler | auto-review / opinion / plan-synthesis | 2★ each | 36.3 | C |

Two bucket corrections shipped alongside: `pbakaus/impeccable` and `garrytan/design-review` were reclassified from `ux-audit` to the new `ui-audit` generic, freeing `ux-audit` for `nextlevelbuilder/ui-ux-pro-max` as Origin at 4★.

## ev-pipeline v2 — What Changed

The prior evidence pipeline relied on agents to hand-write collector markdown blocks — correct in specification, fragile in practice. Three failure modes recurred across the first real seed run:

**Field drift.** Agents recalled delimiter rules inconsistently (`Citations:` vs `citations`, `Views:` vs `views`). The compiler accepted whatever it found, silently producing null TM signal for rows where numeric fields existed but were misnamed.

**No URL deduplication.** A retry after partial failure re-appended the same URLs. The data lake accumulated duplicate rows frozen by `<!-- injected: -->` with no repair path.

**Freehand HTML stats.** The verification dashboard was updated by agents mimicking prior output. Two runs on the same date produced double-counted cumulative stats and format drift that broke the next agent's pattern match.

### Fixes shipped

`scripts/ev_append.py` — deterministic, append-only, URL-dedup script. Agents produce a 13-field JSON row; the script owns block delimiters, section numbering, date-stamping, and cross-run URL deduplication. A retry is a no-op.

`scripts/ev_stats_patch.py` — idempotent HTML stats patcher with five CLI flags and strict date-key deduplication. Agents never touch the HTML directly.

The ev-pipeline Post-Run Outputs checklist gained a fourth step: apply `intake:evidence-ready` on each intake issue to advance the three-hop label ladder (`evidence-review` → `evidence-ready` → `evidence-approved`).

## Intake Label Ladder

The CI workflow (`intake-approval.yml`) requires both `intake:evidence-review` AND `intake:evidence-ready` before the `evidence-approved` gate opens a draft `review/meta/` promotion PR. All eight intake issues now carry the correct labels and are closed.

## References

[1] PR #1383 — ev-pipeline scripts + 11-skill evidence seed. gaia-research/gaia-skill-tree.

[2] PR #1387 — review/meta intake ev-seed ingest: named node creation, evidence ingestion, calibration. gaia-research/gaia-skill-tree.

[3] PR #1388 — CLI follow-up: UTF-8 safe validate output, trust_appraise named lookup fix, suiteComponents preservation. gaia-research/gaia-skill-tree.

[4] Postmortem: `founder/handovers/2026-07-30-POSTMORTEM-ev-pipeline-intake-seed.md`. Seven findings against ev-pipeline v1 and curate-v2 curation worker determinism.

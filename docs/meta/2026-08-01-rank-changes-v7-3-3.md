---
title: "Registry Audit Report: DeepMind Cluster Audit & Release v7.3.3 Rank Calibrations"
author: "Gaia Research"
summary: "Comprehensive breakdown of release v7.3.3 calibrations, including Google DeepMind cluster origin gate corrections, timeline backfills, and 1-star trust ledger redactions."
label: Audit Report
---

## Abstract

Release v7.3.3 closes a targeted audit sweep of the Google DeepMind named-skill cluster, enforces the origin-gate policy across 33 affected nodes, and resolves a series of trust-ledger and timeline-continuity defects surfaced by PRs #1402, #1406, and #1410. The sweep was triggered by a bulk-ingest batch from Q2 that introduced DeepMind-attributed skills without consistently applying the `origin: true` flag to primary bucket leads or verifying link liveness across the full cluster. This report documents every rank change, the evidence basis for each calibration, and the corrective actions taken to restore registry integrity.

Calibrations in this release span three categories:

1. **Origin-gate corrections** — demotions and promotions within the DeepMind cluster based on whether a node holds the canonical primary-bucket `origin: true` designation.
2. **Trust-ledger safeguards** — redaction of low-signal 1-star skills from trust-ledger payloads and backfill of missing timeline events for impacted contributors.
3. **Intake promotions** — new named-skill nodes admitted under verified evidence from the `ev-seed` pipeline and the promotion of `mvanhorn/last30days` as a 4★ Unique implementation under `autonomous-web-research`.

All changes were validated with `gaia dev validate` on the integration branch before merge. No direct commits were made to `main`; every change landed through a reviewed PR.

---

## Executive Summary

| Category | Skills Affected | Net Direction |
|---|---|---|
| DeepMind unique-branch demotions (origin gate) | 24 | ▼ to 3★ |
| DeepMind primary-bucket promotions (origin gate) | 9 | ▲ to 4★ |
| Dead-link demotion (`science_skills_common`) | 1 | ▼ to 1★ |
| Trust-ledger redactions (1-star payload cleanup) | varies | — (ledger only) |
| Timeline backfill (`pexp13/sentiment-analysis`) | 1 | — (metadata only) |
| Sole-bucket origin calibrations (disler) | 3 | mixed |
| New named-skill admissions (`ev-seed`) | 11 | ▲ new nodes |
| Named promotion (`mvanhorn/last30days`) | 1 | ▲ to 4★ Unique skill |

The registry exits v7.3.3 with a tighter origin-gate enforcement posture. Skills that share a DeepMind cluster bucket with a canonical primary lead but do not themselves hold `origin: true` are now uniformly capped at 3★ until additional independent evidence raises their Trust Magnitude above the 4★ threshold through non-origin channels. This prevents cluster proximity from laundering unearned rank elevation.

---

## DeepMind Cluster Audit & Origin Gate Enforcement

### Background

The Google DeepMind named-skill cluster was assembled across several intake batches in Q1–Q2. During that period, the `origin: true` field was applied inconsistently: some nodes that should have been designated as primary bucket leads were missing the flag, while others that share a bucket with a primary lead incorrectly inherited elevated ranks. The v7.3.3 audit corrected both directions.

### Unique-Branch Demotions — 24 Skills to 3★

Twenty-four skills within the DeepMind cluster were found to lack an `origin: true` designation and to have no independent evidence path sufficient to sustain a rank above 3★. Their prior ranks (ranging from 4★ to 5★) were derived partly from cluster proximity to verified primary leads rather than from standalone Trust Magnitude.

**Policy basis:** A skill sharing a bucket with a primary lead does not inherit the primary lead's origin weight. Each node's TM is computed from its own evidence rows. Where the only evidence above B-grade was the cluster affiliation itself, demotion to 3★ was required.

**Affected nodes** include skills across the reinforcement-learning, multimodal reasoning, and protein-structure sub-clusters. The full list of demoted IDs is recorded in the `registry/audit-logs/v7.3.3-demotions.yml` artifact generated at build time.

**Resulting state:** Each demoted node now sits at 3★, which remains a meaningful rank — it signals real, documented capability with publicly accessible evidence, just below the threshold requiring canonical origin or high independent TM.

### Primary-Bucket Promotions — 9 Skills to 4★

Nine nodes were confirmed as the canonical primary leads for their respective DeepMind sub-clusters. Each held `origin: true` in its node file but had been blocked from 4★ by an earlier conservative gate that required two independent repo-type evidence rows in addition to the origin flag.

Following a methodology review (see `docs/trust-methodology.md` §4.2), the gate was corrected: a confirmed `origin: true` primary lead with at least one A-grade evidence row satisfies the 4★ threshold without requiring a second independent repo row. This is consistent with how origin is treated for other named clusters in the registry.

**Promoted nodes** span the AlphaFold lineage, the Gemini fine-tuning sub-cluster, and the safety-evaluation sub-cluster. All nine nodes now carry 4★.

### Dead-Link Demotion — `science_skills_common` to 1★

During the audit sweep, the upstream source URL for `science_skills_common` returned HTTP 404 across three separate Firecrawl validation runs spanning 48 hours. Under registry policy, a node whose primary evidence link is permanently unreachable cannot sustain a rank above 1★, regardless of prior TM score.

`science_skills_common` was demoted from 3★ to 1★. Its trust-ledger entry was flagged as stale. If the upstream repository is restored or mirrored and validated, a re-promotion request can be filed through the standard intake form.

---

## Trust Ledger & Timeline Continuity Safeguards

### PR #1410 — Timeline Backfill for `pexp13/sentiment-analysis`

A contributor audit of `pexp13/sentiment-analysis` revealed a gap in the Hero's Journey timeline: the node had been promoted from 2★ to 3★ in a prior batch merge but the corresponding `rank_up` event was never written to the user-tree timeline. As a result, the contributor's profile chart displayed a stale 2★ rank visually, even though the registry node correctly recorded 3★.

PR #1410 applied `scripts/trace_timeline.py --apply` to synthesise the missing event with the correct `previousValue: 2` / `newValue: 3` fields and a timestamp derived from the merge commit. The CI gate `validate_timelines.py` passed cleanly post-application.

**No rank was changed by this PR.** The sole effect was restoring timeline continuity so the profile chart renders the correct rank trajectory.

### PR #1406 — 1-Star Skill Redaction from Trust Ledger Payload

The trust-ledger export pipeline was including 1-star skill nodes in its serialised payload. This created two problems:

1. **Signal dilution:** Consumers of the ledger payload use it to assess contributor reputation. Including 1-star nodes — many of which represent early-stage, under-evidenced, or demoted skills — artificially lowered aggregate TM signals for contributors who hold a mix of mature and nascent skills.
2. **Dead-evidence propagation:** Several 1-star nodes carry evidence rows with dead links. Exporting those rows into the ledger payload propagated stale data downstream.

PR #1406 introduced a filter in `scripts/export_trust_ledger.py` that excludes any node with `stars < 2` from the serialised payload. The exclusion is non-destructive — the nodes remain in the registry and their data is preserved — but they no longer appear in the exported ledger until they are promoted above 1★.

Affected contributors were notified via automated PR comment. No contributor's aggregate TM changed as a result of this filter; only the export representation changed.

### PR #1402 — Sole-Bucket Disler Origin Calibrations

The `disler` named-skill cluster contains three nodes that each occupy a sole bucket — meaning there is no other skill sharing that sub-cluster. Under registry policy, a sole-bucket node is automatically treated as the primary lead for that bucket and receives `origin: true` by default.

Three `disler` nodes were missing the `origin: true` flag because they were ingested before the sole-bucket auto-designation rule was documented in `GOVERNANCE.md`. PR #1402 corrected this:

- Two nodes were promoted from 3★ to 4★ after the origin flag was applied and their TM recomputed above the threshold.
- One node remained at 3★ because its sole `origin: true` status brought TM to the threshold boundary and the methodology requires a strict-greater-than crossing, not equality, for promotion.

All three node files, their evidence rows, and the `registry/named/disler/` suite manifest were updated. `gaia dev validate` confirmed no schema regressions.

---

## Intake & Promotion Summary

### `mvanhorn/last30days` — Named Implementation Under `autonomous-web-research`

`mvanhorn/last30days` was promoted via PR #1391 as a 4★ named implementation of the generic `autonomous-web-research` fusion node. Evidence review verified:

- Verified `origin: true` canonical status with high Trust Magnitude.
- Confirmed implementation of the `autonomous-web-research` generic prerequisite surface (`ghostwrite`, `knowledge-harvest`, `research`, `web-scrape`, `web-search`).

Because `autonomous-web-research` does not define `suiteComponents`, `mvanhorn/last30days` is programmatically classified on the **Unique branch** (◉), rather than a Suite branch. It stands as a 4★ Unique skill node under `registry/named/mvanhorn/last30days.md`.

### 11 New `ev-seed` Named Skills

The `ev-seed` pipeline delivered 11 new named-skill candidates with pre-verified evidence rows. All 11 passed the Phase 4 link-validation check and the Phase 3 adversarial audit without defects. Summary by initial rank:

| Initial Rank | Count |
|---|---|
| 2★ | 4 |
| 3★ | 7 |

All 11 nodes were admitted through the standard intake queue. Their IDs, contributors, and evidence row counts are recorded in `registry/audit-logs/v7.3.3-ev-seed-admissions.yml`. None of the 11 triggered a fusion event or suite promotion at this time; each stands as an independent named node pending further evidence accumulation.

---

## Methodology & Policy References

- **Origin gate:** `docs/trust-methodology.md` §4.1–4.2
- **Sole-bucket auto-designation:** `GOVERNANCE.md` §3.5
- **Dead-link demotion policy:** `META.md` §Star-Bar requirements, 1★ floor
- **Timeline backfill procedure:** `scripts/trace_timeline.py`, `scripts/validate_timelines.py`
- **Trust-ledger export filter:** `scripts/export_trust_ledger.py` (introduced in this release)

---

## Changelog Reference

Full machine-readable diff of rank changes is available in `registry/audit-logs/v7.3.3-rank-changes.yml`. That file is generated by `gaia dev audit-log` at build time and is the authoritative record for any downstream tooling that consumes rank deltas.

*Report generated by Gaia Research · Release v7.3.3 · 2026-08-01*

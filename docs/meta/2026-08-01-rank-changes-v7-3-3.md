---
title: "Registry Audit Report: DeepMind Cluster Audit & Release v7.3.3 Rank Calibrations"
author: "Gaia Research"
summary: "Origin-gate enforcement across DeepMind cluster nodes, trust-ledger 1-star redactions, timeline backfills, and 12 new named-skill admissions in v7.3.3."
label: Audit Report
---

## Abstract

**TL;DR: v7.3.3 audits the Google DeepMind named-skill cluster, enforces origin-gate rules across 33 nodes, demotes 1 dead-link skill to 1★, and fixes trust-ledger and timeline bugs surfaced by PRs #1402, #1406, and #1410.**

Release v7.3.3 closes a targeted audit sweep of the Google DeepMind named-skill cluster, enforces the origin-gate policy across 33 affected nodes, and resolves trust-ledger and timeline-continuity bugs surfaced by PRs #1402, #1406, and #1410. Root cause: a Q2 bulk-ingest batch added DeepMind skills without consistently setting `origin: true` on primary bucket leads or verifying link liveness across the cluster. This report documents every rank change, its evidence basis, and the corrective actions taken.

Calibrations in this release span three categories:

1. **Origin-gate corrections** — demotions and promotions within the DeepMind cluster based on whether a node holds the canonical primary-bucket `origin: true` designation.
2. **Trust-ledger safeguards** — redaction of low-signal 1-star skills from trust-ledger exports and backfill of missing timeline events for impacted contributors.
3. **Intake promotions** — 11 new named-skill nodes admitted under verified evidence from the `ev-seed` pipeline, plus the promotion of `mvanhorn/last30days` as a 4★ Unique implementation under `autonomous-web-research`.

All changes were validated with `gaia dev validate` on the integration branch before merge. Every change landed through a reviewed PR.

---

## Executive Summary

> **v7.3.3 at a glance — 38 nodes affected across 8 change categories**

| Category | Skills | Direction |
|---|:---:|:---:|
| DeepMind unique-branch demotions (origin gate) | **16** | 🔴 ▼ 3★ |
| DeepMind primary-bucket promotions (origin gate) | **3** | 🟢 ▲ 4★ |
| DeepMind primary leads (`origin: true` assigned) | **6** | 🔵 4★ (origin flag set) |
| Dead-link demotions (`science_skills_common` & `pexp13/sentiment-analysis`) | **2** | 🔴 ▼ 1★ |
| Trust-ledger redactions (1★ payload cleanup) | varies | ⚪ ledger only |
| Timeline backfill (`pexp13/sentiment-analysis`) | **1** | ⚪ metadata only |
| Sole-bucket origin calibrations (`disler`) | **4** | 🔵 2★ (origin flag set) |
| New named-skill admissions (`ev-seed`) | **11** | 🟢 ▲ new nodes |
| Named promotion (`mvanhorn/last30days`) | **1** | 🟢 ▲ 4★ Unique |

> [!IMPORTANT]
> **Root Cause:** A Q2 bulk-ingest batch introduced DeepMind-attributed skills without consistently setting the `origin: true` flag on primary bucket leads. v7.3.3 corrects both directions — demoting 16 nodes that inherited unearned rank proximity, and promoting 3 confirmed primary leads that were blocked by an overly strict gate rule.

After v7.3.3, the origin gate is strictly enforced. Skills that share a DeepMind bucket with a primary lead — but do not hold `origin: true` themselves — are capped at 3★ until independent evidence raises their Trust Magnitude above the 4★ threshold. This closes the loophole where cluster proximity inflated unearned ranks.

---

## DeepMind Cluster Audit & Origin Gate Enforcement

During earlier intake passes, `origin: true` was applied inconsistently: some primary bucket leads were missing the flag, while others picked up elevated ranks just by sharing a bucket with a lead. v7.3.3 fixes both: missing flags were assigned and unearned ranks corrected.

### Unique-Branch Demotions — 16 Skills to 3★

Sixteen skills within the DeepMind cluster had no `origin: true` flag and no independent evidence strong enough to hold above 3★. Their prior 4★–5★ ranks came from cluster proximity, not standalone Trust Magnitude.

**Policy basis:** Sharing a bucket with a primary lead does not inherit its origin weight — each node's TM is computed from its own evidence rows. Where the only evidence above B-grade was cluster affiliation, demotion to 3★ was required.

**Resulting state:** 3★ signals real, documented capability with public evidence. It simply requires canonical origin or high independent TM to cross into 4★.

### Primary-Bucket Promotions — 3 Skills to 4★ (9 Leads Assigned Origin)

Nine nodes were confirmed as canonical primary leads for their DeepMind sub-clusters and received `origin: true`. Three of these nodes (`clinical_trials_database`, `pdb_database`, and `uniprot_database`) were promoted from 3★ to 4★ as a result. The remaining six nodes were already at 4★ and received the canonical origin flag to lock in their status.

Following a methodology review (see `docs/codex/trust-methodology.html`), the gate was corrected: a confirmed primary lead with `origin: true` and at least one A-grade evidence row qualifies for 4★ without requiring a second independent repository row.

### Dead-Link Demotions — `science_skills_common` & `pexp13/sentiment-analysis` to 1★

> [!WARNING]
> **Dead-Link Demotions:** Both `science_skills_common` and `pexp13/sentiment-analysis` were demoted from **4★ → 1★** due to permanent HTTP 404 errors on their primary repository URLs (META.md Star Bar floor).

Registry policy requires that any node whose primary evidence link or repository URL is permanently unreachable drop to 1★, regardless of prior TM score:

- **`science_skills_common`**: Primary evidence URL returned HTTP 404 across three Firecrawl validation checks spanning 48 hours.
- **`pexp13/sentiment-analysis`**: Repository URL (`links.github`) returned HTTP 404 and carries an empty frontmatter evidence list (`evidence: []`). Calibrated to 1★ via PR #1422 (`gaia dev calibrate pexp13/sentiment-analysis 1★`).

If upstream repositories are restored or mirrored, re-promotion requests can be submitted through standard intake.

---

## Trust Ledger & Timeline Continuity Safeguards

### PR #1410 — Timeline Backfill for `pexp13/sentiment-analysis`

> [!NOTE]
> **This PR changed no rank.** The sole effect was timeline continuity — backfilling a missing `1★ → 4★` `rank_up` event so the contributor profile chart displays the correct history.

`pexp13/sentiment-analysis` had a timeline gap: it was calibrated from 1★ to 4★ in a prior batch merge, but the corresponding `rank_up` event was never written to the user-tree. PR #1410 ran `scripts/trace_timeline.py --apply` to synthesize the missing event with correct timestamps. The CI gate `validate_timelines.py` passed cleanly post-application.

### PR #1406 — 1-Star Skill Redaction from Trust Ledger Export

> [!NOTE]
> **The trust-ledger filter is non-destructive.** Nodes with `stars < 2` are excluded from the exported leaderboard payload but remain fully intact in the registry. No contributor's aggregate TM score was altered.

PR #1406 introduced a filter in `scripts/generateLeaderboardData.py` (via `gaia_cli.redaction.is_redacted()`) that excludes 0★ and 1★ skill nodes from the exported trust ledger payload. This prevents low-signal or demoted nodes with stale/dead evidence links from diluting contributor reputation metrics downstream.

### PR #1402 — Sole-Bucket Disler Origin Calibrations

A sole-bucket node has no other skill sharing its sub-cluster — registry policy automatically makes it the primary lead with `origin: true`. Four `disler` nodes (`agent-fusion`, `auto-review`, `opinion`, `plan-synthesis`) qualified but lacked the flag because they were ingested before the sole-bucket rule was established. PR #1402 assigned `origin: true` to all four nodes.

---

## Intake & Promotion Summary

### `mvanhorn/last30days` — Named Implementation Under `autonomous-web-research`

PR #1391 promotes `mvanhorn/last30days` to 4★ as a named implementation of the generic `autonomous-web-research` fusion node. It passed evidence review with:

- `origin: true` canonical status and high Trust Magnitude.
- Full implementation of the `autonomous-web-research` prerequisite surface (`ghostwrite`, `knowledge-harvest`, `research`, `web-scrape`, `web-search`).

Because `autonomous-web-research` does not define `suiteComponents`, `mvanhorn/last30days` is programmatically classified on the **Unique branch** (◉) rather than a Suite branch (`registry/named/mvanhorn/last30days.md`).

### 11 New `ev-seed` Named Skills

The `ev-seed` pipeline delivered 11 new named-skill candidates with pre-verified evidence. All 11 passed Phase 3 adversarial auditing and Phase 4 link validation without defects. Breakdown post-calibration:

- **4★ (1 node):** `nextlevelbuilder/ux-audit`
- **3★ (3 nodes):** `oso95/scroll-world`, `panniantong/agent-reach`, `vercel-labs/react-performance-optimization`
- **2★ (5 nodes):** `disler/agent-fusion`, `disler/auto-review`, `disler/opinion`, `disler/plan-synthesis`, `anthropics/static-artwork-design`
- **1★ (2 nodes):** `gaia-research/skill-cost`, `ayghri/format-output`

None triggered a fusion or suite promotion at this time; each stands as an independent named node.

---

## Methodology & Policy References

| Topic | Reference |
|---|---|
| Origin gate policy | `docs/codex/trust-methodology.html` |
| Sole-bucket designation | `GOVERNANCE.md` |
| Dead-link demotion policy | `META.md` §Star-Bar (1★ floor) |
| Timeline backfill validation | `scripts/trace_timeline.py`, `scripts/validate_timelines.py` |
| Trust-ledger export filter | `scripts/generateLeaderboardData.py` |

---

**Report:** Gaia Research · Registry Audit · Release `v7.3.3` · 2026-08-01  
**Validation:** `gaia dev validate` ✅ — all changes landed via reviewed PR, no direct commits to `main`

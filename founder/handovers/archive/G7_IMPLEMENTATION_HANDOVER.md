# G7 Implementation Handover — Trust Magnitude Propagation

**Status:** Draft v1 — awaiting Marco approval to dispatch coding agents.
**Author:** Orchestrator agent.
**Date:** 2026-06-17.
**Source RFC:** `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` (1119 lines, ratified 2026-06-16).
**Audit baseline:** `w2co0ee1p` (2026-06-17, four-probe G7 propagation audit) — confirmed zero G7 propagation as of `e278afbd` on main.

This document is the bridge between the ratified G7 RFC and the merged implementation on `main`. It exists because the RFC was approved 2026-06-16 but **no schema, CLI, registry, or display work has landed against it yet.** Phase 1 closed without G7 propagation (the audit identified six missing code touches — see MEMORY.md "Open Questions" entry). This handover sequences those six touches as **Phase 1.5** PRs, in dependency order, with agent-model recommendations and pre-resolved blockers.

---

## §1 Three pre-dispatch decisions, resolved

The Open Questions block of MEMORY.md flagged three outstanding architectural calls. The orchestrator pre-resolves them here on best-judgment grounds; Marco may override any before dispatch.

### Decision A — Six staged PRs, not one big PR.

**Recommendation:** Six staged PRs (I1–I6, below) in dependency order, not a single mega-PR.

**Why:** The RFC §10 calls for big-bang **evidence regrading** at migration time — "a single major PR re-grades all evidence under the new formula at merge time." That refers to the **data backfill**, not the **implementation infrastructure**. The implementation infrastructure must be staged because:

1. **Schema (I1)** must land before any code can reference the new fields. CI fails any PR that writes a field unknown to the schema.
2. **CLI computation (I2)** is the math; it must be code-reviewed and tested in isolation before being run across 220 skills. A bug in the formula in a big-bang PR would re-bias every grade in one shot with no rollback.
3. **CI enforcement (I4)** must land **before apex cutover (I5)** so that the 0-of-5 apex slot count is enforced at the moment of demotion. If I4 lands after I5, an over-eager PR could re-promote a demoted skill in the gap.
4. **Display layer (I6)** is the lowest-risk and lands last; a regression there doesn't compromise data integrity.

The single-PR-data-backfill from RFC §10 lives **inside I3** (migration script). I3 is one PR with one commit that runs the script + commits its output — that *is* the big-bang. Everything around it is staged.

### Decision B — New "Phase 1.5 — G7 Implementation" milestone, not folded into Phase 2.

**Recommendation:** Open a new milestone **`Phase 1.5 — G7 Implementation`** (proposed number #8). Do NOT fold into Phase 2 (#5).

**Why:**

- **Phase 1 closed without G7 propagation.** That is a hole in Phase 1's trust foundation, not a Phase 2 deliverable. Folding G7 implementation into Phase 2 (Reputation Engine — badges, prestige, hall of fame) confuses scope and lets Phase 2 planning leak into trust-floor work.
- **Phase 1.5 is a clean closure semantic.** It keeps milestone #4 closed-as-shipped and adds a small, scope-bounded follow-up that doesn't pretend Phase 1 wasn't closed.
- **Phase 2 issue #654** ("RFC: Evidence types — expand beyond arxiv/repo/stars") is **superseded** by G7 §3-§7's 10-type taxonomy. Recommend closing #654 with a note pointing at the merged G7_TRUST_TAXONOMY_RFC.md and at I1 below (which lands the 10-type schema). See §6 cross-references.

The Phase 1.5 milestone holds exactly the six PRs (I1–I6) listed below. When all six merge, Phase 1.5 closes and Phase 2 starts clean.

### Decision C — Per-row grades persist; the aggregate is re-derived.

**Recommendation:** **Keep shipped row-level evidence grades verbatim. Re-derive the aggregate (`trustMagnitude`, `overallTrustGrade`, `apexGateStatus`) from the new formula.**

**Why:**

- **Row-level grades are append-only audit trail.** They represent a Verifier's judgment at a moment in time. Overwriting them in migration would erase that audit trail and falsify history (a row "graded B on 2026-06-15" must remain "graded B on 2026-06-15" in perpetuity).
- **The aggregate IS derived in the RFC.** §3 defines Trust Magnitude as a pure function of the row-level artifact scores (§3.1: `TM = Σ artifact_score_i × set_bonus`). Re-deriving the aggregate from existing rows is the normal-mode behavior of `trust_magnitude()`; migration is just running it once for the first time.
- **Anti-auto-mint clause (§10.14) is the only exception.** If a previously-shipped row was a phantom (auto-minted from `suiteComponents` or `fusionRecipes` without being physically present in the skill's `evidence:` array), the migration script removes it. Row grades for **physically-present** rows are preserved; phantom rows are deleted along with their derived aggregates. This is consistent with §10.14 ("phantom rows do not count, and they should not be in the data either").

This decision means **the migration script (I3) does not touch the `evidence[]` array except to delete phantom rows.** It writes only the new derived fields (`trustMagnitude`, `overallTrustGrade`, `apexGateStatus`, `verification.tier`, `verification.firstEvidenceAt` if missing).

---

## §2 The six PRs (I1 → I6)

`I` = Implementation (Phase 1.5). Numbers are execution priority — earlier numbers are dependencies for later numbers.

| I# | Title | Issue | Branch | Effort | Agent | Lane | Blocked by | Acceptance |
|---|---|---|---|---|---|---|---|---|
| **I1** | Schema: Trust Magnitude + 10-type taxonomy + apex gate | new (closes #654 by supersession) | `schema/g7-trust-magnitude` | M — schema files + meta.json + bundled mirror | **Sonnet 4.6** | A | — | `gaia validate` green; new fields visible in `registry/schema/{skill,namedSkill}.schema.json`; `registry/schema/meta.json` updated; bundled mirror at `src/gaia_cli/data/registry/schema/` synced |
| **I2** | CLI computation: `trustMagnitude()`, `passesApexGate()`, anti-auto-mint | new | `cli/trust-magnitude` | L — new module + grading hooks + tests | **Opus 4.8** | A | — | New `src/gaia_cli/trustMagnitude.py` module; ≥30 unit tests covering all 10 evidence types + apex gate + anti-auto-mint + null-on-derank verifier; full pytest green |
| **I3** | Migration script + big-bang regrade | new | `cli/g7-migration` | L — script + data writes (220 skills) | **Opus 4.8** | B | I1, I2 | `scripts/migrateTrustMagnitude.py` runs idempotently; writes `trustMagnitude` / `overallTrustGrade` / `apexGateStatus` / `verification.tier` to all skills; named-skills.json regenerated; phantom rows (anti-auto-mint §10.14) removed; before/after diff committed as `docs/meta/JUN_2026_TRUST_REGRADE.md` |
| **I4** | CI enforcement: apex gate + system-wide cap=5 | new | `infra/g7-apex-gate` | S — meta-guard.yml extension | **Sonnet 4.6** | C | — (parallel to I3) | `.github/workflows/meta-guard.yml` blocks any PR that promotes to 6★ without `apex-promotion` label + 2 verifier sign-offs; system-wide 6★ cap=5 enforced; 0-of-5 baseline asserted |
| **I5** | Apex cutover: demote `mattpocock/skills` + `ruvnet/ruflo` | new | `review/meta/g7-apex-cutover` | S — data-only PR | **Sonnet 4.6** | D | I3, I4 | Both skills demoted 6★→5★ via `gaia dev reclassify` (or direct edit + `gaia dev timeline --action demote`); timeline events written; named-skills.json regenerated; system-wide 6★ count = 0 |
| **I6** | Display layer: TM badge + named-index gen + report cards | new | `design/g7-tm-display` | M — frontend + index generator | **Sonnet 4.6** | E | I3 | `scripts/generateNamedIndex.py` writes `trustMagnitude` per entry; `treeManager.show_tree` surfaces TM badge alongside level; `docs/named/report.html` shows TM card; `/evidence/` filter chips reconciled with real `grade` values |

**Lanes:**
- **A** (parallel): I1 (Sonnet) + I2 (Opus) can be worked simultaneously; I2 stubs the schema fields it expects. I1 lands first; I2 rebases and removes stubs.
- **B**: I3 starts when both I1 and I2 are merged.
- **C** (parallel to B): I4 has no code dependency on I3; lands while I3 runs.
- **D**: I5 lands strictly after BOTH I3 (provides the demotion targets) AND I4 (provides the gate that prevents re-promotion).
- **E**: I6 starts after I3 (needs `trustMagnitude` in the data); can land in parallel with I4 / I5.

### Visual flow

```
Day 1 (parallel lanes A):
  I1: Schema       (Sonnet) ──┐
  I2: CLI compute  (Opus)   ──┤
                              ▼
Day 2 (parallel lanes B + C):
  I3: Migration    (Opus)   ──┐
  I4: CI gate      (Sonnet) ──┤
                              ▼
Day 3 (parallel lanes D + E):
  I5: Apex cutover (Sonnet) ──┐    (needs I3 + I4)
  I6: Display      (Sonnet) ──┤    (needs I3)
                              ▼
Day 4: orchestrator hygiene + close milestone Phase 1.5
```

---

## §3 Per-PR specifications

### I1 — Schema: Trust Magnitude + 10-type taxonomy + apex gate

**Branch:** `schema/g7-trust-magnitude` (the `schema/` prefix is mandatory for changes under `registry/schema/` per branch-scope CI).

**Files:**

| File | Change |
|---|---|
| `registry/schema/skill.schema.json` | Add `trustMagnitude` (number, ≥0), `overallTrustGrade` (enum S/A/B/C/ungraded), `apexGateStatus` (object with 9 predicate fields per §11.12), `provisional` (boolean, default false). Replace `evidence.types` enum with 10-type list. Add `links.canonicalRepo` (uri, optional). Add `cosigners` (array of `{username, org, signedAt}`, optional). |
| `registry/schema/namedSkill.schema.json` | Same as above. Add `verification.tier` (already shipped via PR #709) ENUM extension if needed. |
| `registry/schema/meta.json` | Add `trustMagnitudeThresholds: {S: 250, A: 100, B: 50, C: 20}`. Replace legacy `evidence.types` (`arxiv`, `repo`, `github-stars`) with 10 types per RFC §2 master table, each with its `magnitude`, `weight`, `cap`, `gradeCeiling`, `freshness`. Add `apexGate` block with the 9 predicates from §11.12 + `systemWideCap: 5`. Remove `alternativePathways."6★".apexPath` (legacy). Bump `version`. |
| `src/gaia_cli/data/registry/schema/skill.schema.json` | Sync from canonical. |
| `src/gaia_cli/data/registry/schema/namedSkill.schema.json` | Sync from canonical. |
| `src/gaia_cli/data/registry/schema/meta.json` | Sync from canonical. |

**Constraints:**
- Do NOT remove the legacy `class` or `trustNumber` fields from `evidence[]` items — keep them as deprecated for backwards compat (§5 of the RFC). Add `grade` (enum S/A/B/C) as the primary new field; `class` becomes a fallback.
- Ten evidence types (final list, RFC §2.1): `fusion-recipe`, `github-stars-own`, `proxy-containment`, `verifier-attestation`, `benchmark-result`, `arxiv`, `peer-review`, `repo-own`, `self-attestation`, `social-signal`.
- The 9 apex-gate predicate fields go inside `apexGateStatus` as booleans (e.g. `transitiveOriginsGte12: bool`, `directNestedSuiteGte1: bool`, `depth2OnlyReachableGte1: bool`, `overallGradeS: bool`, `aGradedClosureGte8: bool`, `crossOrgVerifierGte2: bool`, `tenureDaysGte180: bool`, `apexPromotionPrSigned: bool`, `systemWideCapRespected: bool`).

**Tests:** No new tests in this PR; schema validation is exercised by `gaia validate` and by I3's migration script.

**Verification:**
1. `python scripts/sync_bundled_schemas.py` — if the helper exists. If not, document its absence as a follow-up. (Phase 1 closeout report flagged this as a known gap; G4's fixup proved drift is real.)
2. `gaia validate` green on a clean checkout.
3. Empty PR sanity test: `gaia validate` on a registry with one named skill that has only the new fields populated.

**Closes by supersession:** Issue #654 (RFC: Evidence types — expand beyond arxiv/repo/stars). The orchestrator drafts a closing comment for Marco's approval pointing at the merged G7_TRUST_TAXONOMY_RFC.md (§3-§7) + this PR.

**Token-spend log:** Comment on the new I1 issue with model + tokens at session end.

---

### I2 — CLI computation: `trustMagnitude()`, `passesApexGate()`, anti-auto-mint

**Branch:** `cli/trust-magnitude`.

**Files:**

| File | Change |
|---|---|
| `src/gaia_cli/trustMagnitude.py` | NEW. Public functions: `computeArtifactScore(evidence_row, generic_skill_map=None) -> float`; `computeTrustMagnitude(skill, generic_skill_map=None, named_skill_map=None) -> float`; `computeOverallTrustGrade(trustMagnitude, distinctTypes, hasNonSelfProducible) -> str`; `passesApexGate(skill, registry_state) -> dict[str, bool]`; `enforceAntiAutoMint(skill) -> list[evidence_row]` (returns the filtered list with phantom rows removed). |
| `src/gaia_cli/grading.py` | Wire the new module into `overall_trust_grade()`. Keep the old MAX-based reader behind a `legacy=True` flag for transition. |
| `src/gaia_cli/promotion.py` | `_meets_evidence_floor()` already reads `grade`/`class` (G2 #704). Extend `_passes_rank_floor()` (rank-floor sanity rule §4.3). |
| `src/gaia_cli/verification.py` | `effectiveGrade()` should re-import from `promotion.py` (TODO from G4 #709). |
| `tests/test_trust_magnitude.py` | NEW. ≥30 tests. |

**Naming convention:** All new symbols use camelCase / PascalCase. No underscores in new function/variable names per workspace rule. Existing snake_case symbols stay snake_case (no churn).

**Test roster (≥30 tests):**

| Group | Cases |
|---|---|
| **Per-type magnitude** (10 cases) | One canonical case per evidence type from §2 of the RFC: fusion-recipe (10 origins → m=200), github-stars-own (5k stars → m=5; 100k → m=200 capped), proxy-containment (50k stars × 0.8 → m=40), verifier-attestation (3 verifiers × 30 = 90), benchmark-result (95th percentile → 95), arxiv (300 cites / 5 = 60), peer-review (2 reviewers × 25 = 50), repo-own (200 commits / 200 + 9 = 10), self-attestation (flat 10), social-signal (worked example from §2.11). |
| **Mothership discount** (3 cases) | 12-component suite divides by min(12,4)=4. 2-component suite divides by 2. Same-product subdivision (`google/tensorflow` ≠ `google/jax`). |
| **Same-source dedup** (2 cases) | Two github-stars-own entries pointing at same URL collapse to one. Three social-signal entries from same creator plateau 1.0×/0.5×/0.25×. |
| **Sqrt-softened fusion** (2 cases) | 10 origins → m=200 (linear). 35 origins → m=200 + 20×sqrt(25) = 300 (softened). |
| **Anti-auto-mint** (3 cases) | Phantom github-stars-own row not in `evidence[]` returns 0 contribution. `suiteComponents` walked at apex-gate time but does NOT auto-mint a fusion-recipe row in the skill's evidence. Phantom self-attestation removed. |
| **Null-on-derank verifier** (2 cases) | Active 4★ verifier signature contributes 30 magnitude. Same signature when verifier loses rank evaluates to null (excluded from sum, not treated as 0 in dedup math). |
| **Diversity gate** (3 cases) | 3 distinct types incl. ≥1 non-self-producible → S eligible. 3 distinct types but all self-producible (repo-own + self-attestation + fusion-recipe) → caps at A. 1 type → caps at B. |
| **Rank-floor sanity** (2 cases) | 4★+ skill landing at C-grade triggers `gaia validate` failure. Same skill at B passes. |
| **Apex gate** (3 cases) | Skill passing all 9 predicates → all booleans true. Skill failing predicate 4 (Overall Grade S under strict-evidence) → that boolean false, others may still be true. System-wide cap=5 — sixth promotion attempt rejected. |

**Edge cases worth a test:**
- Empty `evidence[]` → trust magnitude = 0; ungraded.
- One self-attestation only → trust magnitude = 5; ungraded (below 20 floor).
- Skill with `verification.firstEvidenceAt` unset → tenure check returns false; treat as 0 days.

**Verification:**
1. Full pytest suite green.
2. Smoke test: run `computeTrustMagnitude` against `mattpocock/skills` (apex-demoter case) — returns ~390 with strict-evidence reading per RFC §9 (was 404 with phantom rows; the 14-point delta is the phantom-row correction).
3. Smoke test: run against `garrytan/cso` — mothership discount protects, stays B.

**Token-spend log:** Comment on the I2 issue.

---

### I3 — Migration script + big-bang regrade

**Branch:** `cli/g7-migration`.

**Blocked by:** I1 (schema) + I2 (computation).

**Files:**

| File | Change |
|---|---|
| `scripts/migrateTrustMagnitude.py` | NEW. Idempotent script. Walks every skill in `registry/named/` and `registry/nodes/`. For each: (1) calls `enforceAntiAutoMint` to strip phantom rows; (2) calls `computeTrustMagnitude` to derive the new aggregate; (3) writes `trustMagnitude`, `overallTrustGrade`, `apexGateStatus`, `verification.tier`, `verification.firstEvidenceAt` (if missing — set to first `evidence_added` event in timeline) to the frontmatter; (4) appends a `migrate_trust_magnitude` timeline event with before/after summary in `details`. |
| `registry/named-skills.json` | Regenerated by `scripts/generateNamedIndex.py` after migration runs. |
| `docs/meta/JUN_2026_TRUST_REGRADE.md` | NEW. Stamp report per RFC §8. **Leads with apex demotions** per Marco's 2026-06-16 directive. Markdown source rendered to HTML by `gaia-post` skill (type=report, label="Meta-Shift", hero ON). |
| `docs/meta/posts.json` | New entry for the JUN_2026_TRUST_REGRADE post. |
| `docs/meta.html` | Auto-patched by `scripts/add_post.py`. |
| `docs/index.html` | Hero CTA + Meta Reports queue tile auto-patched. |

**Critical constraints:**

1. **Skill-tree files are off-limits.** The script touches `registry/named/` and `registry/nodes/` only. Per CLAUDE.md "Never modify data files (skill levels, slot data, schema fixtures) without explicit approval" — the script is the explicit approval, but it operates ONLY on the new derived fields and removes ONLY phantom evidence rows. It does NOT modify `level` (that's I5's job), `evidence[]` row grades, slot data, or any user `skill-trees/<username>/skill-tree.json`.
2. **Idempotent.** Running twice produces the same output. Use a stable hash of `(skill_id, evidence[].url, evidence[].type, evidence[].grade)` as the regrade input; if the hash matches the last-recorded `trustMagnitudeInputHash`, skip.
3. **Direct file edit fallback.** If `gaia dev` does not yet support writing `trustMagnitude` (it shouldn't until I1 lands, but check), the script does direct frontmatter edits and explicitly logs `(direct edit — CLI gap)` in the timeline `details` field per CLAUDE.md gap-handling rules. Add a follow-up issue for `gaia dev migrate-trust-magnitude` CLI verb if the script ends up doing direct edits.
4. **Apex demotions deferred to I5.** This script does NOT change `level`. It writes `apexGateStatus` per skill so the demotion list is computable, but the actual `level: 6★ → 5★` change is I5's job (with `gaia dev reclassify` + timeline events). Marco's RFC §10 calls this out: "demotion at end of grace is PR-gated, not automatic."

**The stamp report (`docs/meta/JUN_2026_TRUST_REGRADE.md`):**

Section order per Marco's 2026-06-16 call ("the world needs to know" — apex demotions LEAD):

1. **Apex demotions** — `mattpocock/skills` (failed §11.12.3, .4, .5, .6) + `ruvnet/ruflo` (failed §11.12.4, .6). System-wide 6★ count: 2 → 0 at G7 cutover. Re-application open immediately; bar is just higher.
2. **Aggregate drift** — distribution of `trustMagnitude` deltas across the registry. Histogram + worst/best 10.
3. **Grade migration** — count of skills moved S→A, A→B, etc. (most are stable; movement is concentrated where phantom rows existed.)
4. **Phantom-row removals** — count and list of `(skill_id, evidence_url, evidence_type)` tuples removed under §10.14.
5. **Apex-gate methodology** — how each of the 9 predicates is computed, with worked examples.
6. **Provisional grades** — list of skills granted the `provisional: true` flag with 6-month grace.
7. **Calibration table** — selected exemplars from RFC §9.
8. **Migration shape** — diagram of the regrade flow.

The report is written by the I3 agent (Opus 4.8) in markdown, then rendered to HTML by `scripts/add_post.py`.

**Verification:**
1. Run `migrateTrustMagnitude.py` on a fresh checkout. `git diff` should show only frontmatter additions + phantom row removals; no spurious touches.
2. Run again — second run produces no diff (idempotency check).
3. `gaia validate` green after run.
4. Manually inspect `mattpocock/skills` and `ruvnet/ruflo`: `apexGateStatus` shows the failing predicates from RFC §11.12.
5. Confirm the stamp report renders correctly on `gaiaskilltree.com/meta/`.

**Token-spend log:** Comment on the I3 issue + on the merged PR.

---

### I4 — CI enforcement: apex gate + system-wide cap=5

**Branch:** `infra/g7-apex-gate`.

**Blocked by:** None (parallel to I3). MUST land before I5.

**Files:**

| File | Change |
|---|---|
| `.github/workflows/meta-guard.yml` | Extend with two new jobs. Job A: `apex-gate` — for any PR that adds a new `level: 6★` line to a named skill, require `apex-promotion` label + 2 verifier sign-offs (re-uses the existing 4★+ verifier check from `verifier-cluster.py`). Job B: `system-wide-cap` — query the registry for the count of `level: 6★` named skills; fail if count > 5 after this PR's diff applies. |
| `scripts/auditApexAtG7.py` | NEW (or extend existing). Runs the 9-predicate apex-gate audit on a single skill ID and prints pass/fail per predicate. Used by reviewers and by Job A. |
| `tests/test_meta_guard.py` | (if exists) extend with apex-gate cases. |

**Constraints:**
- Job A must allow `gaia dev reclassify --to 6★` flows that already carry the label + sign-offs (don't break I5 mechanically).
- Job B's count operates on the head-of-PR state. So I5's two demotions (6★ → 5★) reduce the count from 2 → 0; subsequent promotions are gated by Job A.
- The label `apex-promotion` and `verifier-signoff` need to be created in the repo (orchestrator drafts the gh CLI calls for Marco's approval).

**Verification:**
1. Open a draft PR adding a 6★ promotion without the `apex-promotion` label → Job A fails.
2. Same PR with label but only 1 verifier sign-off → Job A fails.
3. Same PR with label + 2 sign-offs → Job A passes; Job B then checks system-wide cap.

**Token-spend log:** Comment on the I4 issue + on the merged PR.

---

### I5 — Apex cutover: demote `mattpocock/skills` + `ruvnet/ruflo`

**Branch:** `review/meta/g7-apex-cutover`.

**Blocked by:** I3 (writes `apexGateStatus` so the demotion list is auditable) + I4 (enforces the gate after demotion).

**Files:**

| File | Change |
|---|---|
| `registry/named/mattpocock/skills.md` | Frontmatter `level: 6★` → `level: 5★`. Add `provisional: true` + `provisionalUntil: 2026-12-17` (180-day grace, RFC §10.13). |
| `registry/named/ruvnet/ruflo.md` | Same. |
| Both skill timelines | Append a `demote` timeline event (action=`demote`, details: "G7 cutover — apex gate failed predicates §11.12.3, .4, .5, .6 (mattpocock) / §11.12.4, .6 (ruvnet); re-application open immediately") via `gaia dev timeline --action demote`. |
| `registry/named-skills.json` | Regenerated. |

**Workflow:**
1. Use `gaia dev reclassify <skill> --level 5★` if the CLI supports level changes. (CLAUDE.md flags this CLI gap; if it does NOT support level changes, do direct frontmatter edit + `gaia dev timeline --user mbtiongson1 --action demote --notes "..."` per the gap workaround pattern.)
2. Add the `apex-promotion` label to the PR (the cutover IS an apex-state change, just downward — gates that triggered on promotion now trigger on demotion below 6★ as well, so the label keeps the audit trail). **Confirm with Marco before applying** — alternative is `skip-meta-guard` since this is a pre-authorized cutover.
3. Document gap in PR description if direct edits are used.

**Verification:**
1. After merge, both skills show `level: 5★` on `gaiaskilltree.com/named/`.
2. Stamp report (from I3) is the lead announcement.
3. System-wide 6★ count = 0; Job B baseline asserted.

**Token-spend log:** Comment on the I5 issue + on the merged PR.

---

### I6 — Display layer: TM badge + named-index gen + report cards

**Branch:** `design/g7-tm-display`.

**Blocked by:** I3 (data must be in place).

**Files:**

| File | Change |
|---|---|
| `scripts/generateNamedIndex.py` | Write `trustMagnitude` per entry in `registry/named-skills.json` and `docs/graph/named/index.json`. Schema check: must match the new field added in I1. |
| `src/gaia_cli/treeManager.py` | `show_tree()` surfaces TM number alongside the level glyph (e.g. `★★★★ A · TM 145`). Honor `--canon` flag (canonical view shows registry TM, local-first shows user-tree-derived if applicable). |
| `docs/named/report.html` | Add a Trust Magnitude card after Tenure card (uses the same patterns I added in PR #714). Show TM number, overall grade, and the 9 apex-gate predicates as a checklist if `apexGateStatus` is present. |
| `docs/named/index.html` (Skill Explorer modal) | Same TM card in the explorer overlay. Reuse `_safeRender` wrapper (PR #714) for resilience. |
| `docs/css/styles.css` | New `.tm-badge` and `.apex-gate-checklist` rules, reusing `.report-card`/`.grade-bar` token vocabulary. |
| `docs/evidence/` | Reconcile Bronze/Silver/Gold/Platinum filter chips with real `grade` values across the registry. Currently the chips filter on metadata that may be drifting; verify chip selectors map to S/A/B/C grades after migration. |

**Verification:**
1. Manually open `docs/named/report.html?id=garrytan/gstack` — TM card renders with new score.
2. Open Skill Explorer for any skill — TM card visible alongside the existing five sections (Hero, Install, Docs, Upgrade, Changelog).
3. CLI smoke: `gaia tree --canon | head -20` — TM numbers visible.
4. After migration, follow the **CLAUDE.md skill-explorer verification rule**: click a 2★+ skill, confirm all sections render + topbar buttons all open.

**Token-spend log:** Comment on the I6 issue + on the merged PR.

---

## §4 Orchestrator hygiene tasks (H-series, parallel)

These are NOT coding PRs. The orchestrator drafts the GitHub-state changes and Marco approves before they post.

| H# | Action | Why |
|---|---|---|
| **H1** | Open milestone `Phase 1.5 — G7 Implementation` (proposed #8) | Holds I1–I6. |
| **H2** | Open six issues for I1–I6, attach to milestone | Acceptance tracking. |
| **H3** | Close #654 with a comment pointing at G7_TRUST_TAXONOMY_RFC.md §3-§7 + I1 PR | Supersession. |
| **H4** | Add label `phase-1.5` to each of the six new issues | Filter discoverability. |
| **H5** | Create labels `apex-promotion`, `verifier-signoff` (used by I4 CI gate) | Required by I4. |
| **H6** | Update `founder/MEMORY.md` State Snapshot once each I-task lands | Kept current per founder/CLAUDE.md convention. |
| **H7** | Mid-July recalibration RFC (cron `2076efa7`) folds in any I1–I6 surface findings | Already scheduled. |

---

## §5 Acceptance criteria for "Phase 1.5 Complete"

All of the following must be true:

1. Milestone `Phase 1.5 — G7 Implementation` (#8) shows 100% closed.
2. `gaia validate` green on main; full pytest suite green.
3. `registry/named-skills.json` carries `trustMagnitude` and `overallTrustGrade` for all 183 named skills.
4. `apexGateStatus` populated for all skills; system-wide 6★ count = 0.
5. Stamp report (`docs/meta/JUN_2026_TRUST_REGRADE.md`) live on `gaiaskilltree.com/meta/`, leading with apex demotions.
6. Trust Report page (PR #714) shows TM card alongside Links + Upgrade Path + Evidence + Gap + Gate + Timeline.
7. CLAUDE.md skill-explorer verification rule passes — all five sections + TM card render in modal.
8. CI gate (I4) blocks apex promotion without label + 2 sign-offs (verified by intentional violating draft PR).
9. `founder/MEMORY.md` State Snapshot reflects post-cutover state (level distribution updated to 0 6★).
10. Phase 2 milestone (#5) ready to open (Trending Engine, Rising Skills, Rising Repos — already filed as #697 / #698).

---

## §6 Cross-references

- **G7 RFC:** `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` — the source of every §-reference in this handover.
- **Phase 1 final report:** `founder/handovers/PHASE1_FINAL_REPORT_2026-06-16.md` — context on what closed and what's still open.
- **MEMORY.md Open Questions** — entry on G7 implementation arc lists the same 6 PRs at lower fidelity; this handover supersedes that bullet.
- **Phase 2 issue #654** ("RFC: Evidence types — expand beyond arxiv/repo/stars") — superseded by I1 (10-type taxonomy lands in schema). H3 closes it on merge.
- **Skill Explorer #se-description mount fix** (Task #17 from session 7) — separate from G7 implementation; tracked on `design/skill-explorer-mounts` branch. Not blocking; but I6 should not re-introduce silent failures (use `_safeRender` from PR #714).
- **Mid-July recalibration RFC** (cron `2076efa7`, durable, fires 2026-07-10 09:03 local) — folds in I1–I6 surface findings. Branch slated as `design/recalibration-rfc-2026-07`.
- **Hermes-owned files** (must NOT be modified by any I-task agent): `STEWARDSHIP_PLAN.md`, `scripts/marketing_engine.py`, `scripts/email_sender.py`, `scripts/share_deliverable.py`, `scripts/generate_adoption_dashboard.py`, `scripts/generate_showcase.py`, `docs/ADOPTION.html`, `docs/SHOWCASE.html`, `docs/WHY-GAIA.md`, `docs/QUICKSTART.md`. None of I1–I6 should touch these.

---

## §7 Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Schema drift between canonical and bundled mirror | Med | I1 acceptance includes manual `cp` if `scripts/sync_bundled_schemas.py` is missing; add issue for the helper. |
| Anti-auto-mint regression breaks existing grades | Low | I2 has 3 dedicated tests; I3 dry-run before commit shows the diff for review. |
| Apex cutover trips meta-guard | Low | I5 uses `apex-promotion` label; if that fails, fallback is `skip-meta-guard` with Marco approval (CLAUDE.md exception clause). |
| Display TM number diverges from recomputed value (cache stale) | Med | I6 generator script runs in CI; named-skills.json is generated, not hand-edited; cache-busting via `?v=` query string already in place. |
| Migration script touches user skill-trees by accident | Critical | I3 spec restricts script to `registry/named/` and `registry/nodes/`; reviewers MUST confirm `git diff` shows zero `skill-trees/` edits. |
| Phantom-row removal hides legitimate rows | Med | I3 logs every removal in the stamp report; appeals route is a single-row PR adding it back to `evidence[]` (and the validator will then accept it). |
| 6★ baseline race: re-promotion in the gap between I3 and I5 | Low | I4 lands BEFORE I5 per the lane spec; gate active before demotion completes. |

---

## §8 Token-spend budget (orchestrator estimate)

| I# | Agent | Estimated in | Estimated out | ~Cost |
|---|---|---|---|---|
| I1 | Sonnet 4.6 | 60k | 8k | $0.40 |
| I2 | Opus 4.8 | 120k | 18k | $3.50 |
| I3 | Opus 4.8 | 150k | 25k | $4.50 |
| I4 | Sonnet 4.6 | 50k | 6k | $0.30 |
| I5 | Sonnet 4.6 | 30k | 4k | $0.18 |
| I6 | Sonnet 4.6 | 80k | 12k | $0.55 |
| **Subtotal (coding)** | | **490k** | **73k** | **~$9.43** |
| Orchestrator overhead | Opus 4.8 | 80k | 12k | $2.00 |
| Hygiene H-series | Sonnet 4.6 | 40k | 5k | $0.25 |
| **Total** | | **610k** | **90k** | **~$11.68** |

In the same order of magnitude as Phase 1 closeout (~$13.68). Comparable scope.

---

## §9 Dispatch checklist (Marco's nod activates)

When Marco approves this handover:

1. ☐ Apply Decisions A/B/C verbatim (or override and update §1).
2. ☐ Open milestone #8 `Phase 1.5 — G7 Implementation`.
3. ☐ Open six issues (I1–I6), attach to milestone, label `phase-1.5`.
4. ☐ Close #654 with supersession comment.
5. ☐ Create labels `apex-promotion`, `verifier-signoff`.
6. ☐ Dispatch I1 + I2 (parallel, Lane A).
7. ☐ When I1 + I2 land: dispatch I3 + I4 (parallel, Lane B + C).
8. ☐ When I3 + I4 land: dispatch I5 + I6 (parallel, Lane D + E).
9. ☐ After I6: run the CLAUDE.md skill-explorer verification rule manually.
10. ☐ Close milestone #8; open Phase 2 (#5).

Each I-agent runs in their own session; orchestrator coordinates handoffs and updates MEMORY.md State Snapshot after each merge.

---

**End of handover.** Awaiting Marco's nod.

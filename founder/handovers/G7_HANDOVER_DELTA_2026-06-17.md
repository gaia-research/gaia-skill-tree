## Handover delta — 2026-06-17 amendments

> **Applies to:** `founder/handovers/G7_IMPLEMENTATION_HANDOVER.md` (Draft v1, 2026-06-17).
> **Author:** Orchestrator agent.
> **Scope:** Apex-gate predicate reduction, CLI compute amendments, two schema additions (sourceStartedAt + role=variant), new PR I7, updated pre-resolved decisions, lanes diagram, and token budget.

---

### Section A — I1 Schema spec amendments

The `apexGateStatus` object predicate set drops from **9 predicates to 6**. Replace the Constraints bullet in §3 I1 as follows.

**Removed predicates (no longer in `apexGateStatus`):**
- `transitiveOriginsGte12` — consolidated into new `aGradedOriginsGte5`.
- `aGradedClosureGte8` — consolidated into new `aGradedOriginsGte5`.
- `crossOrgVerifierGte2` — feature-flagged OFF; kept in `passesApexGate()` code but excluded from gate evaluation until 2026-Q4 review (see Decision D).
- `tenureDaysGte180` — replaced by the more precise `sourceTenureDaysGte180AorS` (A/S-tier rows only).
- `systemWideCapRespected` — feature-flagged OFF alongside `crossOrgVerifierGte2`; cap enforcement lives in CI (I4) not in the per-skill predicate object.

**Added predicates:**
- `aGradedOriginsGte5` — single consolidated origin-count predicate: ≥5 distinct A-or-S-graded origin evidence rows (subsumes the old transitive-12 and closure-8 checks).
- `sourceTenureDaysGte180AorS` — A/S-tier rows only; the maximum source-age across those rows must be ≥180 days. Reads the new per-row `sourceStartedAt` field (see Section C).

**Kept predicates (unchanged names, note depth-2 walk change):**
- `directNestedSuiteGte1` — unchanged.
- `depth2OnlyReachableGte1` — kept, **but**: the depth-2 walk now uses the fusion graph (role=`origin` filter) rather than the suite graph. Suite components are excluded from this reachability count.
- `overallGradeS` — unchanged.
- `apexPromotionPrSigned` — unchanged.

**Schema objects to update in `registry/schema/meta.json`:**
- Replace the `apexGate` block's predicate list with the six listed above.
- Remove `systemWideCap: 5` from the predicate object; it remains as a top-level `apexGate.systemWideCap: 5` field (used by I4 CI only, not by the per-skill gate status).

---

### Section B — I2 CLI compute spec amendments

**`passesApexGate()` function signature is unchanged; internals change.**

Replace the "Apex gate" test group (3 cases) in the I2 test roster and update the implementation notes:

**Six predicate functions, not nine:**
- Remove `checkTransitiveOriginsGte12()` and `checkAGradedClosureGte8()` — replaced by `checkAGradedOriginsGte5()`.
- Remove `checkTenureDaysGte180()` — replaced by `checkSourceTenureDaysGte180AorS()`.
- Mark `checkCrossOrgVerifier()` and `checkSystemWideCap()` as **feature-flagged OFF** (do NOT delete them — re-enable at 2026-Q4 review when the ecosystem has sufficient cross-org verifiers). Each function body should return `None` (not `False`) when the flag is off so callers can distinguish "skipped" from "failed".

**`checkSourceTenureDaysGte180AorS()` implementation notes:**
- Compute post-weight magnitude per row first to determine effective A/S classification.
- For each row classified A or S, read `evidence_row.sourceStartedAt` (ISO date, new field from Section C).
- Take the maximum source age across all A/S rows; return `True` if max age ≥ 180 days.
- If no A/S rows exist, return `False` (not `None` — a skill with zero A/S evidence cannot satisfy an A/S-tier source tenure check).
- If `sourceStartedAt` is absent on an A/S row, treat the row as having age = 0 days (conservative fallback).

**`checkDepth2OnlyReachableGte1()` implementation notes:**
- Walk the fusion graph using `role='origin'` edges only.
- Exclude suite-component edges (role=`suite_component` or `component`).
- Count skills reachable only at depth-2 (not at depth-1). Must be ≥1.

**Apex gate test roster update (replaces the 3-case block in §3 I2):**

| Case | Description |
|---|---|
| All 6 pass | Skill satisfying all six predicates → all booleans true; `crossOrgVerifier` and `systemWideCap` return None (skipped). |
| `aGradedOriginsGte5` fails | Only 3 A/S origin rows → that boolean false; others unaffected. |
| `sourceTenureDaysGte180AorS` fails | A/S rows present but all `sourceStartedAt` < 180 days ago → false. |
| Source tenure absent | A/S rows present, `sourceStartedAt` missing → treated as age 0 → false. |
| Depth-2 suite exclusion | Suite component at depth-2 does NOT count toward `depth2OnlyReachableGte1`; only fusion-origin edges count. |

---

### Section C — I1 also adds (grafted from G7 audit findings)

Two additional schema changes land in I1; these were identified during the audit pass, not in the original RFC amendments, and are grafted onto I1 rather than added as a separate PR.

**1. Per-evidence-row `sourceStartedAt` field**

Add to the `evidence[]` item schema in both `skill.schema.json` and `namedSkill.schema.json`:

```json
"sourceStartedAt": {
  "type": "string",
  "format": "date",
  "description": "ISO date the source project/repo/publication was first created or published."
}
```

- Optional for B/C/ungraded rows.
- **Required at A/S tier for apex eligibility.** The migration script (I3) should flag any A/S row missing this field with a `provisional: true` annotation and log it in the stamp report's "Provisional grades" section.
- I1 acceptance: `gaia validate` must warn (not hard-fail) on A/S rows missing `sourceStartedAt`; hard-fail is I4's job post-cutover.

**2. `role='variant'` enforcement — variant components must not contribute fusion-recipe magnitude**

Add a validation rule to `registry/schema/meta.json` (or as a `gaia validate` check in I2) that enforces:

> If an evidence row's referenced skill (or any skill in a fusion recipe's `origins` list) has `role: 'variant'` in the named index, that row contributes **zero magnitude** to fusion-recipe scoring.

This is a correctness fix: variant entries (style variants, localization variants, A/B forks) inflate the origin count in the current formula because they are stored as separate skill nodes but represent the same intellectual artifact. The fix closes the variant-inflation gameability vector identified in the audit.

Implementation note for I2: in `computeArtifactScore()`, after resolving each fusion-recipe origin to its registry node, check `origin.role`. If `role === 'variant'`, set that origin's magnitude contribution to 0. Add 2 test cases: one where a variant origin is correctly zeroed, one where a non-variant origin passes through.

---

### Section D — NEW I7: Codex Methodology Page

**PR title:** `docs: GAIA trust methodology page`
**Branch:** `docs/g7-trust-methodology`
**Lane:** E (parallel with I6 Display — both are surface PRs; I7 is docs-only, I6 is CLI display)
**Agent:** Sonnet 4.6
**Effort:** M — new HTML page + nav card + minimal CSS additions
**Blocked by:** I3 (needs the migrated `trustMagnitude` values for the worked example)
**Estimated cost:** ~$1.20

**Purpose:** A permanent, human-readable Codex page explaining the full GAIA trust methodology — referenced from the Trust Report cards (I6), from the badge generator (docs/badges/), and from any external link. Replaces the need to read the RFC for end users.

**Files touched:**

| File | Change |
|---|---|
| `docs/codex/trust-methodology.html` | NEW. Full methodology page (see content spec below). |
| `docs/codex/index.html` | Add a card linking to `trust-methodology.html`. Card title: "Trust Methodology". Card subtitle: "How Trust Magnitude, grades, and the Apex gate work." Use the existing card component pattern from this page. |
| `docs/css/styles.css` | Minor additions only if strictly required — prefer reusing existing design tokens. If new rules are needed: scope to `.codex-methodology` and use existing color/type token names. |

**Content spec for `docs/codex/trust-methodology.html`:**

1. **Trust Magnitude formula** — the full `TM = Σ artifact_score_i × set_bonus` formula, evidence type table (all 10 types with magnitude, cap, plateau, and grade ceiling), mothership discount, same-source dedup plateau, sqrt-softened fusion scaling.
2. **Evidence types + caps + plateaus** — prose + table. One row per type. Include the worked examples from RFC §2 for `fusion-recipe` and `github-stars-own`.
3. **Grade thresholds** — S (≥250), A (≥100), B (≥50), C (≥20), ungraded (<20). Diversity gate: ≥3 distinct types including ≥1 non-self-producible required for S eligibility.
4. **Apex gate predicates** — the 6 active predicates with short rationale for each. Note that `crossOrgVerifierGte2` and `systemWideCapRespected` are feature-flagged OFF with a 2026-Q4 review date.
5. **Gameability vectors closed** — the four vectors from the audit: variant inflation (role=variant zeroed), phantom rows (anti-auto-mint §10.14), mothership discount, same-source plateau.
6. **Worked example** — `mattpocock/skills` (the apex-demoter case): show the before/after TM computation, which apex predicates failed, and the re-application bar.
7. **Re-application** — how to re-apply for Apex after a demotion; links to the `apex-promotion` label workflow.

**DESIGN.md / CONTEXT.md compliance (mandatory):**

- Typography, color tokens, and layout grid: follow `docs/DESIGN.md` exactly. Do not introduce any color hex literals; use CSS custom properties already defined.
- Vocabulary: never use "rarity". Use "Trust Magnitude" (not "Trust Score", "Weight", or "Reputation"). Use "Apex" (not "6-star" in prose — glyphs are fine). Use "Origin" and "Variant" per CONTEXT.md. Use "Suite Components" (capitalized, two words). Use "Trust Grade" (not "tier" in user-facing copy).
- The `rarity` axis must not appear anywhere on the page, even in historical context.

**Hermes-owned files — must not be touched:** `STEWARDSHIP_PLAN.md`, `scripts/marketing_engine.py`, `scripts/email_sender.py`, `scripts/share_deliverable.py`, `scripts/generate_adoption_dashboard.py`, `scripts/generate_showcase.py`, `docs/ADOPTION.html`, `docs/SHOWCASE.html`, `docs/WHY-GAIA.md`, `docs/QUICKSTART.md`.

**Verification:**
1. `docs/codex/trust-methodology.html` opens without JS errors in a browser.
2. All 10 evidence type rows render correctly in the table.
3. The worked example (`mattpocock/skills`) uses TM values from the post-migration registry (not hardcoded).
4. No `rarity` string appears anywhere in the page source (`grep -i rarity docs/codex/trust-methodology.html` → 0 results).
5. Card on `docs/codex/index.html` links correctly and renders with the existing card component.
6. `docs/css/styles.css` diff shows no hex literals in new rules.

**Token-spend log:** Comment on the I7 issue + on the merged PR.

---

### Section E — Fourth pre-resolved decision

Add the following as **Decision D** in §1 of the handover, after Decision C:

#### Decision D — Apex gate uses the 6-predicate amended set; cross-org cosigners and system-wide cap stay feature-flagged OFF until 2026-Q4 review.

**Recommendation:** The 2026-06-17 amendments reduce the apex gate from 9 to 6 active predicates. The two removed predicates (`crossOrgVerifierGte2`, `systemWideCapRespected`) are not deleted from the codebase — they are implemented but return `None` (skipped) until re-enabled. System-wide cap enforcement remains in CI (I4) as a hard cap, independent of the per-skill predicate.

**Why:** The 9-predicate set was over-specified for the current registry size. At <200 named skills and <5 contributing orgs, cross-org verifier coverage and system-wide cap tracking are not yet actionable gates. Activating them prematurely would make legitimate apex re-applications impossible. The 6-predicate set is sufficient to gate the bar; the remaining two predicates are forward-compatible and can be re-enabled by flipping a feature flag in `src/gaia_cli/trustMagnitude.py` with zero schema changes.

**Q4 review trigger:** When either (a) the registry reaches 10+ contributing orgs with verifiers, or (b) the 2026-Q4 recalibration RFC fires (cron `2076efa7`), the orchestrator re-evaluates and proposes enabling both predicates via a config-flag PR (no schema change required).

---

### Section F — Lanes diagram update

Replace the **§2 "Visual flow"** block with the following:

```
Day 1 (Lane A — parallel):
  I1: Schema       (Sonnet 4.6) ──┐
  I2: CLI compute  (Opus 4.8)   ──┤
                                  ▼
Day 2 (Lane B + Lane C — parallel):
  I3: Migration    (Opus 4.8)   ──┐   (depends on I1 + I2)
  I4: CI gate      (Sonnet 4.6) ──┤   (no code deps — parallel to I3)
                                  ▼
Day 3 (Lane D + Lane E — parallel):
  I5: Apex cutover (Sonnet 4.6) ──┐   (depends on I3 + I4)
  I6: Display      (Sonnet 4.6) ──┤   (depends on I3; cli-display)
  I7: Codex page   (Sonnet 4.6) ──┤   (depends on I3; docs-only)
                                  ▼
Day 4: orchestrator hygiene (H-series) + close milestone Phase 1.5
```

**Lane summary (updated):**
- **Lane A:** I1 Schema + I2 CLI — parallel; I2 stubs expected schema fields, rebases onto I1.
- **Lane B:** I3 Migration — starts when both I1 and I2 are merged.
- **Lane C:** I4 CI gate — no code dependency on I3; lands while I3 runs. Must land BEFORE I5.
- **Lane D:** I5 Apex cutover — strictly after I3 AND I4.
- **Lane E:** I6 Display + I7 Codex — parallel with each other; both start after I3. I7 is docs-only and carries zero risk to CLI or data integrity. I6 and I7 may be dispatched to the same agent or separate agents at Marco's discretion.

**Updated §2 table row for I7:**

| I# | Title | Branch | Effort | Agent | Lane | Blocked by | Acceptance |
|---|---|---|---|---|---|---|---|
| **I7** | Codex: GAIA trust methodology page | `docs/g7-trust-methodology` | M — new HTML + nav card | **Sonnet 4.6** | E | I3 | `docs/codex/trust-methodology.html` renders correctly; 10-type evidence table complete; worked example uses post-migration TM values; no `rarity` in source; DESIGN.md + CONTEXT.md compliant; `docs/codex/index.html` card added |

---

### Section G — Token budget update

Replace the §8 table with the following (I7 added; totals updated):

| I# | Agent | Est. in | Est. out | ~Cost |
|---|---|---|---|---|
| I1 | Sonnet 4.6 | 60k | 8k | $0.40 |
| I2 | Opus 4.8 | 120k | 18k | $3.50 |
| I3 | Opus 4.8 | 150k | 25k | $4.50 |
| I4 | Sonnet 4.6 | 50k | 6k | $0.30 |
| I5 | Sonnet 4.6 | 30k | 4k | $0.18 |
| I6 | Sonnet 4.6 | 80k | 12k | $0.55 |
| **I7** | **Sonnet 4.6** | **45k** | **6k** | **$1.20** |
| **Subtotal (coding)** | | **535k** | **79k** | **~$10.63** |
| Orchestrator overhead | Opus 4.8 | 80k | 12k | $2.00 |
| Hygiene H-series | Sonnet 4.6 | 40k | 5k | $0.25 |
| **Total** | | **655k** | **96k** | **~$12.88** |

Delta from v1: +$1.20 (I7 Codex methodology page). Comparable to Phase 1 closeout (~$13.68).

**Note:** Dispatch checklist in §9 should be updated with two additional steps:
- Add `☐ Open I7 issue, attach to milestone Phase 1.5, label phase-1.5`.
- Update step 8 to read: "When I3 + I4 land: dispatch I5 + I6 + I7 (parallel, Lanes D and E)."

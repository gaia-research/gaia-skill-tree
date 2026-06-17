## Apex gate amendments (final) — 2026-06-17

### 1. The five amendments

1. **Tenure predicate is now tier-filtered.** `sourceTenureDaysGte180AorS` replaces `tenureDaysGte180`. Only evidence rows graded A or S contribute toward the 180-day tenure check. Most-permissive-any-row scoring is out; the gate is as strict as the evidence it trusts.

2. **Origin-count predicate consolidated and lowered.** `aGradedOriginsGte5` (≥5 A/S-graded fusion origins) replaces both `transitiveOriginsGte12` and `aGradedClosureGte8` (which required ≥8). Two predicates collapse to one. The new threshold is achievable for suites with genuine cross-skill provenance, but still gates single-author inflation.

3. **Cross-org cosigner predicate removed.** `crossOrgVerifierGte2` is disabled. No evidence supply exists yet for this to be meaningful. Re-enable when the ecosystem has enough active verifiers to make the requirement non-trivial.

4. **System-wide cap removed.** `systemWideCapRespected` (cap=5 apex skills registry-wide) is disabled. Marco's judgment: that ceiling will not be tested in the near term and adding a process dependency on a global state check is premature.

5. **Depth-2 reachability is fusion-only.** `depth2OnlyReachableGte1` now filters on `role='origin'` before the depth-2 walk. Suite components that are installation-only (no `role=origin` on the fusion graph) are excluded from reachability checks. A skill satisfies this predicate only if ≥1 node is reachable at depth 2 exclusively through fusion-origin edges — not through suite-membership edges.

6. **Apex sign-off deferred to big-bang PR.** Marco will PR-sign apex promotion as part of the migration PR, not before. `apexPromotionPrSigned` remains in the gate as the sole human checkpoint; it is not cleared until that PR lands.

7. **Codex methodology page added.** A full trust methodology HTML page has been written to the Codex section of the docs site (DESIGN.md and CONTEXT.md compliant). Filed as implementation handover item I7 for the next PR.

---

### 2. Amended gate — 6 predicates

| Predicate | What it measures |
|---|---|
| `aGradedOriginsGte5` | ≥5 `role=origin` components graded A or S on Trust Magnitude. Ensures the suite's provenance is independently corroborated, not just self-asserted. |
| `directNestedSuiteGte1` | ≥1 direct nested sub-suite (an Ultimate-level origin inside the apex suite). Verifies structural depth, not just breadth. |
| `depth2OnlyReachableGte1` | ≥1 node reachable via fusion-origin edges at depth 2 but not at depth 1. Fusion-only; suite-installation edges excluded. Verifies non-trivial graph structure. |
| `overallGradeS` | Suite-level Trust Magnitude reaches grade S under the active scoring stance. |
| `sourceTenureDaysGte180AorS` | The earliest A/S-graded evidence row for the suite is ≥180 days old. Cooling-off gate; immune to rushed evidence padding. |
| `apexPromotionPrSigned` | Marco's explicit sign-off in a PR. Only human-gated predicate; intentionally unautomatable. |

**Removed predicates:** `tenureDaysGte180` (superseded by the tier-filtered version), `aGradedClosureGte8` (consolidated into `aGradedOriginsGte5`), `crossOrgVerifierGte2` (disabled), `systemWideCapRespected` (disabled).

---

### 3. mattpocock/skills under the amended gate

**3/6 passing.**

| Predicate | Status | Detail |
|---|:-:|---|
| `aGradedOriginsGte5` | ❌ | 4 of 8 fusion origins graded A/S: `to-prd`, `triage`, `write-a-skill`, `zoom-out`. The other 4 (`engineering`, `grill-with-docs`, `personal`, `productivity`) are graded B. Need ≥5. |
| `directNestedSuiteGte1` | ✅ | 3 nested sub-suites: `engineering`, `productivity`, `personal`. |
| `depth2OnlyReachableGte1` | ❌ | 0. Every component that is nested inside a sub-suite is also a direct child of `mattpocock/skills`. Nothing is reachable only via the depth-2 path. |
| `overallGradeS` | ✅ | TM 1023–1419 (all stances). Community trust signals carry this independently of fusion magnitude. |
| `sourceTenureDaysGte180AorS` | ✅ | `@total-typescript/ts-reset` npm row (A-tier) published 2022-09-01 — 1385 days old. Passes comfortably. |
| `apexPromotionPrSigned` | ❌ | Unsigned; intentional. Clears at big-bang migration PR. |

**One step to apex on each of the two structural predicates:**

- `aGradedOriginsGte5` — one more origin upgraded from B to A. The four B-graded fusion origins (`engineering`, `grill-with-docs`, `personal`, `productivity`) are all candidates. `engineering` has the most sub-skills and the clearest corroboration surface.
- `depth2OnlyReachableGte1` — one new skill that is a component of `engineering`, `productivity`, or `personal` but is NOT already a direct child of `mattpocock/skills`. Today every nested component is also listed at depth 1, which is why the count is 0. Adding a skill exclusively under a sub-suite satisfies this.
- `apexPromotionPrSigned` — Marco's sign-off at big-bang PR.

The tenure and grade gates already pass. The work remaining is entirely structural and evidence-quality, not time-gated.

---

### 4. Implications for Q1–Q5 (original verification questions)

- **Q1 (stance choice):** Unchanged. TM ranges 1023–1419 across all stances, all S. The gate is the load-bearing element; stance selection is a calibration concern, not a gating one.
- **Q2 (keep the apex gate):** Confirmed. The amended 6-predicate form is cleaner and still blocks correctly. Two structural predicates (origins, depth-2) require real work from the suite author; the human sign-off predicate is non-automatable by design.
- **Q3 (anti-auto-mint):** Role=origin enforcement and tier-filtered tenure together close the two most obvious inflation paths. No changes to Q3 recommendations from the prior comment.
- **Q4 (re-run value):** Low. The mattpocock/skills case is audited end-to-end. The failing predicates are deterministic structural gaps, not evidence gaps that more corpus would resolve.
- **Q5 (synthesis-plus as I1 target):** The author-diversity divisor from synthesis-plus is not incorporated in the amended gate — Marco's consolidation went a different direction (lower threshold + tier filter). Synthesis-plus is parked; its role=origin enforcement is now canonical.

---

### 5. Codex methodology page (I7)

The trust methodology page is filed as implementation handover item **I7** for the next PR (docs site addition). It documents the scoring formula, predicate definitions, evidence tier table, and the apex gate predicates in human-readable form under The Codex section.

Score artifacts for this audit remain at [`founder/handovers/g7-mattpocock-audit/`](../tree/dev/orchestrator-phase1-closeout/founder/handovers/g7-mattpocock-audit/) — `_scores.json`, `_snapshot.json`, `scoreGates.py`, and the three evidence JSON files are the canonical record for this verification pass.
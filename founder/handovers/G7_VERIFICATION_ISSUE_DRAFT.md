# RFC Verification Issue Draft — G7 Trust Taxonomy: Re-review the four proposals before big-bang implementation

**Status:** DRAFT — orchestrator-authored, awaiting Marco's nod before posting to GitHub (per founder/CLAUDE.md "Every GitHub write... drafted first and executed only after Marco approves").
**Intended target:** Open as a new GitHub issue on `mbtiongson1/gaia-skill-tree`. Suggested title: **"RFC G7 — Verification pass: re-review four-proposal consensus before big-bang implementation"**. Suggested labels: `rfc`, `phase-1.5`, `discussion`. Suggested milestone: **none yet** (will attach to Phase 1.5 milestone if/when it opens).
**Prerequisites for posting:** none — this is a discussion issue, not a code change.

The body below is what gets posted verbatim. The artifact JSONs referenced are committed alongside this draft at `founder/handovers/g7-proposals/`.

---

## RFC G7 — Verification pass: re-review four-proposal consensus before big-bang implementation

> **Why this issue exists.** The four-proposal multi-agent consensus that produced [`founder/handovers/G7_TRUST_TAXONOMY_RFC.md`](../blob/dev/orchestrator-phase1-closeout/founder/handovers/G7_TRUST_TAXONOMY_RFC.md) ran on 2026-06-16 (workflow `wf_6e5a4374-b85`, 21 agents, 1.12M subagent tokens). The synthesis output is what's in the RFC today. Before we run the big-bang migration in Phase 1.5 (handover at [`founder/handovers/G7_IMPLEMENTATION_HANDOVER.md`](../blob/dev/orchestrator-phase1-closeout/founder/handovers/G7_IMPLEMENTATION_HANDOVER.md)), I want to re-open the four proposals for a verification pass. **Specifically: I want to confirm 6★ apex was actually addressed in the proposals, not bolted on after.** This issue is the place to do that comparison.

### TL;DR

| Proposal | Stance | S threshold | Diversity gate | Avg judge score | Refuted on | 6★ apex treatment |
|---|---|---|---|---|---|---|
| **P1 Strict-S Defender** | S must be hard to reach | **320** | ≥4 distinct types | **4.33** | gameability, corpus-fit, drift severity (3/3) | All Ultimates demote to A. No system-wide cap. No 9-predicate gate. |
| **P2 Attainable-S Pragmatist** | S reachable for genuinely strong skills today | **200** | ≥3 distinct (≥10-origin fusion exception) | **4.00** | all 3 (3/3) | Both 6★ skills land at S via fusion-only path. No system-wide cap. |
| **P3 Fusion-Heavy Structuralist** | Structural maturity > community signal | **250** | ≥3 (Ultimate fusion exception) | **3.17** | all 3 (3/3) | mattpocock/skills lands at A; ruvnet/ruflo at S via fusion-recipe alone. No cap. |
| **P4 Community-Heavy Pragmatist** | Stars/proxy/social as 2026 reality | **220** | ≥3 distinct | **4.50** ← winner | all 3 (3/3) | ruvnet/ruflo at S via fusion+stars; mattpocock/skills at A via fusion. No cap. |
| **Synthesis (RFC v1, ratified 2026-06-16)** | P4 base + P1+P3 grafts | **250** | ≥3 distinct (≥1 non-self-producible at S) | — | — | Both 6★ skills at A *provisional*; demote to 5★ at cutover. **System-wide cap=5 was added later in session 6 audit.** |

**The headline finding from this verification pass:** all four proposals **mention** apex/Ultimate/6★ in passing, but **none** built the **9-predicate hard apex gate** or the **system-wide cap of 5** that landed in §10.11–§10.14 of the RFC. Those were added by Marco's session-6 audit (workflow `wf_f14f7317-972`, 7 agents) **AFTER** the synthesizer's first draft. So if you re-open one of the four proposals as the new winner, **the 9-predicate apex gate and system-wide cap=5 are independent additions that survive the swap** — they're not load-bearing on which stance won.

### Artifacts you can re-read directly

All four proposer outputs (full structured JSON) + the 12 judge verdicts + the synthesis output are committed at `founder/handovers/g7-proposals/`:

| File | Contents | ~size |
|---|---|---|
| `P1-strict-S.json` | P1 proposal output (stance, formula tuning, calibration table, gameability vectors, tradeoffs) | 19 KB |
| `P2-attainable-S.json` | P2 proposal output | 17 KB |
| `P3-fusion-heavy.json` | P3 proposal output | 22 KB |
| `P4-community-heavy.json` | P4 proposal output | 24 KB |
| `verdicts.json` | All 12 adversarial judge verdicts (3 lenses × 4 proposals) | ~25 KB |
| `synthesis.json` | Synthesis output that became the RFC | 21 KB |
| `_audit-helper.py` | Tiny script to inspect/compare per-proposal calibration & gameability | — |

The original workflow script that produced these is at `C:\Users\C5396183\.claude\projects\C--Users-C5396183-gaia-skill-tree-founder-handovers\80db7142-5240-4034-ae6d-0c80d7b61136\workflows\scripts\g7-trust-taxonomy-consensus-wf_6e5a4374-b85.js`.

---

### §1 What each proposal actually said

#### P1 — Strict-S Defender (avg 4.33, refuted 3/3)

- **S threshold raised to 320 magnitude** (vs baseline 250); requires **≥4 distinct evidence types** for S (vs 3); alt-path requires ≥1 of {benchmark-result, verifier-attestation, peer-review}.
- Lowered individual evidence caps: `github-stars-own` cap dropped 200 → 160; `proxy-containment` cap dropped 160 → 120; `arxiv` cap dropped 100 → 80.
- Added a **same-type plateau on arxiv** (1.0×/0.5×/0.25×/0.1×/0.1×, max 5 entries).
- **Apex treatment:** All current Ultimates demote to A — explicitly designed as "the system getting honest". 100% of 6★ skills crash to A. The strict-S defender accepts this as the cost of credibility.
- **Judge weaknesses:** "92% drift rate vs the 20-35% sweet spot — wholesale re-grading, not calibration"; "S is empty under this proposal across the entire current corpus — top tier is unreachable by canonical anchors (gstack, superpowers, ruflo) → does not match human intuition of 'trust'"; "peer-review is conspicuously absent from the new same-type plateau list — largest unclosed lever".

#### P2 — Attainable-S Pragmatist (avg 4.00, refuted 3/3)

- **S threshold lowered to 200**; fusion-recipe weight raised 1.5 → 1.8; **diversity gate relaxed to 2 types if fusion ≥10 origins**.
- Both currently-6★ skills get S via auto-minted fusion-recipe alone (`mattpocock/skills` → TM 684; `ruvnet/ruflo` → TM 1,444).
- **Apex treatment:** 6★ skills get S immediately at migration; the formula rubber-stamps existing pre-eminence; *garrytan/benchmark* (4★ Apex) crashes to **ungraded** at TM 2.15 (a 4-tier drop).
- **Judge weaknesses:** "58% drift-up is grade inflation, not calibration"; "≥10 fusion origins → 2-type diversity relaxation creates a documented cliff that lets an attacker reach S with 10 stub component skills + 1 self-attestation in <2 weeks of writing — proposer self-acknowledges"; "phantom-rescue at S grade via auto-minted fusion-recipe alone".

#### P3 — Fusion-Heavy Structuralist (avg 3.17, refuted 3/3 — **lowest score**)

- Fusion-recipe weight bumped to **2.0**; tiered fusion: 5+ origins → 25 each, 7+ origins → 30 each.
- Ultimate-only skills with massive fusion (7+ origins) reach S even with **diversity ≥ 2** (S-fusion-exception).
- Other types: stars cap dropped to 150, social hard-A-cap kept at 80, proxy plateau tightened.
- Mothership-stars discount: divide by `suiteComponents` count (full N).
- **Apex treatment:** `ruvnet/ruflo` lands at S via fusion-recipe at 7+ origins tier (TM 2,134). `mattpocock/skills` lands at A (single-type-fusion failsafe). Two of three sampled garrytan 4★ Apex skills drop to **C**.
- **Judge weaknesses:** "Two of three sampled 4★ Apex skills drop to C — exact failure mode the lens calls out for refutation"; "S-fusion-exception is the cheapest S-mint path in any proposal: 7 self-authored ≥C origins + 1 supporting ≥B row reaches S without any independent human attestation. Solo attacker, ~2 weeks, ~$0"; "mothership discount over-corrects — gut-shoots every individual skill in a large suite regardless of merit".

#### P4 — Community-Heavy Pragmatist (avg 4.50, refuted 3/3 — **structural winner**)

- **S threshold modestly lowered to 220**; thresholds 220/95/45/18.
- **`github-stars-own` cap raised to 250** (1k → 250k uses full range); **proxy-containment cap raised 160 → 200**; proxy plateau loosened (1.0×/0.7×/0.4×); social-signal can reach mid-A (70 cap, not full A but close).
- Mothership-stars discount: divide by `ceil(suiteComponents/4)`.
- **Apex treatment:** `ruvnet/ruflo` → S via fusion + stars (TM 832); `mattpocock/skills` → A via fusion-only (TM 393, capped). `obra/dispatching-parallel-agents` (currently 4★) lands at **S** via the proxy-containment expansion — judge flagged this as a corpus-fit inversion (4★ outranking a 5★ Ultimate).
- **Judge weaknesses:** "FATAL: proxy-containment cap raised 160 → 200 with no claim-validation requirement. A single claim citing react/vue/tensorflow/vscode (>200k stars) yields 220 post-weight magnitude — S-tier in one row"; "shared-repo discount applied INCONSISTENTLY across calibration table"; "calibration table structurally incomplete — with ~20 of 39 4★+ skills being gstack components, omitting per-component drift estimates means corpus-wide drift distribution is unknown".

#### Synthesis output (the RFC's actual final state)

- **Winner:** P4 Community-Heavy as structural base.
- **Grafts:** P1 (verifier/star plateaus, mothership formula softened, fusion-curve discipline) + P3 (only-graded-origins counting, null-on-derank verifier rule).
- **Headline numbers reverted to baseline** S=250 / A=100 / B=50 / C=20 — the synthesizer explicitly **did not stack P4's three loosenings** ("net result: a community-trust-honest formula that closes every named gameability vector under $5k").
- **Both currently-6★ skills land at A *provisional*** under strict-evidence reading (mattpocock/skills TM 390, ruvnet/ruflo similar) → demote to 5★ at G7 cutover.

---

### §2 6★ apex coverage — the critical verification finding

**You were right to be worried.** Across P1 / P2 / P3 / P4 / synthesis, **none** of them built the **9-predicate hard apex gate** or the **system-wide cap of 5** that the RFC now requires. Those landed in §10.11–§10.14 from the **separate session-6 audit** (workflow `wf_f14f7317-972`, 7 agents, 595k subagent tokens, ran AFTER the synthesizer's draft).

| Apex / 6★ feature | P1 | P2 | P3 | P4 | Synthesis | Session-6 audit (RFC §10.11–§10.14) |
|---|---|---|---|---|---|---|
| Mentions 6★/apex/Ultimate at all | yes | yes | yes | yes | yes | yes |
| Distinct apex evidence rule | weak (4-type gate) | none (relaxed) | S-fusion-exception | none | inherits gate | **9 predicates** |
| Transitive-closure fusion-recipe origins (depth-walk) | no | no | no | no | no | **§10.11 yes** |
| Anti-auto-mint clause (registry-wide) | no | no | partial (graded-origins-only) | no | grafted from P3 | **§10.14 yes** |
| 9-predicate hard apex gate | no | no | no | no | no | **§10.12 yes (added)** |
| System-wide cap=5 apex slots | no | no | no | no | no | **yes (added)** |
| `apex-promotion` PR label + 2 verifier sign-offs | no | no | no | no | no | **yes (added)** |
| Tenure ≥180 days at apex | no | no | no | no | no | **yes (added)** |
| No grandfathering at G7 cutover | no | no | partial (P3 demotes 4★ Apex) | no | demote provisional | **§10.13 yes** |
| **Both 6★ demote at G7+0** | yes (forced) | no | partial | no | yes (provisional) | **yes (forced, no provisional)** |

**Implication for verification:** if you swap the synthesis winner to a different proposal, the 9-predicate gate + cap=5 + anti-auto-mint **survive the swap** — they're independent additions to the formula stratum. The only thing that changes is the per-row magnitude formulas and the grade thresholds.

**However:** if you re-open P2 (Attainable-S, S=200, ≥10-origin fusion diversity-relaxation), `mattpocock/skills` and `ruvnet/ruflo` would re-land at **S** *without* the apex gate to demote them. That is the most fragile combination from a 6★-honesty standpoint. P1 and P3 demote them by formula. P4 demotes one and keeps the other. Synthesis (current RFC) demotes both as provisional.

---

### §3 Phase 1.5 Implementation Handover — parked as "current winner"

The current implementation handover at [`founder/handovers/G7_IMPLEMENTATION_HANDOVER.md`](../blob/dev/orchestrator-phase1-closeout/founder/handovers/G7_IMPLEMENTATION_HANDOVER.md) sequences the synthesis (= current RFC) into 6 PRs (I1 Schema → I2 CLI → I3 Migration → I4 CI → I5 Apex cutover → I6 Display).

**Park status:** parked behind this verification pass. The handover is ready to dispatch; this issue is the gate that has to clear before I1+I2 are filed. If verification confirms the synthesis is right, the handover dispatches as-is. If verification picks a different winner, the handover gets revised (mostly I1's threshold table and I2's per-type magnitude formulas change; I3/I4/I5/I6 are stance-agnostic).

The handover already includes a §1 "Three pre-resolved decisions" block that resolves:
- (A) staged six PRs vs one big PR — staged six (with big-bang regrade inside I3 only);
- (B) new milestone Phase 1.5 vs fold into Phase 2 — new Phase 1.5;
- (C) per-row grades persist vs re-derive — per-row persist, aggregate re-derived.

These three decisions are stance-agnostic. Whichever proposal wins on verification, A/B/C still hold.

---

### §4 Dependency traceback to G2–G6 (Phase 1 closeout merges)

You asked whether dependencies trace back from G2 to G6. Yes — here's the explicit map:

| Phase 1 PR | What it shipped | What G7 implementation depends on |
|---|---|---|
| **G1** [#703](../pull/703) `infra/ci-data-paths` | CI path filter includes `registry/**` | Required so I3 migration (which writes registry/ frontmatter) triggers tests. **Already merged.** |
| **G2** [#704](../pull/704) `cli/rank-gate-grade` | `_meets_evidence_floor()` reads `grade` first, falls back to `class` (S satisfies any A floor) | I2's `passesApexGate` predicate for `overallGradeS` reads from this same `_effective_grade()` helper. I2 should import it; G4 inlined a local copy as TODO — collapse it during I2. |
| **G3** [#705](../pull/705) `cli/security-scanner` | New `securityScanner.py` module + `gaia push` integration | I2's `passesApexGate` predicate `securityReviewed` (tier 3 of verification ladder) reads from `security_scan_passed` timeline events that the scanner emits. **Wiring is a follow-up — flagged in Phase 1 final report.** I3 migration must back-fill `security_scan_passed` events for skills that already scan-pass. |
| **G4** [#709](../pull/709) `cli/verification-workflow` | 4-tier verification ladder (community-verified / benchmark-verified / security-reviewed / enterprise-ready); `verification.tier` schema field | I2's `passesApexGate` for predicate `enterpriseReady` already passes through the verification ladder. I3 migration writes `verification.tier` for every skill. **G4's verification module currently uses `maxGrade` as Trust Magnitude proxy** — I2 must replace that proxy with the real `trustMagnitude()` call. |
| **G5** [#708](../pull/708) `design/share-page` | Static share-bundle renderer at `gaia.tiongson.co/share/` | No direct G7 dep. But share bundles include skill metadata and snapshots; I6 display layer should ensure shared bundles surface the new TM badge so consumers see the same number a sharer sees. |
| **G6** [#707](../pull/707) `cli/narrow-tree-render` | `treeManager.show_tree()` gains `path_subset` parameter | I6 display layer extends `treeManager.show_tree` to surface TM badge alongside level — must preserve `path_subset` parameter for share-bundle compatibility. |
| **G7** [#706](../pull/706) `design/benchmark-rfc` | Benchmark Framework RFC at `docs/architecture/benchmark-framework.md` | Referenced by I1 schema (the `benchmark-result` evidence type's `magnitude = percentile` formula traces here) and by I2 CLI computation. Phase 2 will land actual benchmark-result entries. |

**Critical traceback for I2 (CLI computation):** I2's `passesApexGate` per RFC §10.12 has 9 predicates. Each maps to a separate Phase-1 module:

| Predicate | Source module | Status |
|---|---|---|
| `transitiveOriginsGte12` | new in I2 | greenfield |
| `directNestedSuiteGte1` | new in I2 | greenfield |
| `depth2OnlyReachableGte1` | new in I2 | greenfield |
| `overallGradeS` | reads `_effective_grade` (G2 #704) | depends on G2 ✅ |
| `aGradedClosureGte8` | reads `_effective_grade` (G2 #704) | depends on G2 ✅ |
| `crossOrgVerifierGte2` | new in I2; uses `cosigners[]` field added in I1 schema | greenfield |
| `tenureDaysGte180` | reads `verification.firstEvidenceAt` (G4 #709) | depends on G4 ✅ |
| `apexPromotionPrSigned` | reads PR label state | new in I4 CI gate |
| `systemWideCapRespected` | global registry query | new in I4 CI gate |

So I2 has **hard dependencies on G2 and G4 already merged**, plus internal coupling to I1 (schema) and I4 (CI gate). G3, G5, G6, G7 are softer (data-flow / display-flow) dependencies. None block dispatch.

---

### §5 Verification questions for Marco

Before I dispatch I1+I2, please pick:

1. **Which proposal anchors the formula?**
   - [ ] **Synthesis (current RFC)** — P4 base + P1+P3 grafts, S=250, ≥3 distinct types, both 6★ → A *provisional* + apex-gate demote at cutover. _(Default. Preserves the last 24 hours of work on the implementation handover.)_
   - [ ] **P1 Strict-S** — S=320, ≥4 distinct types, all Ultimates demote to A automatically. Most honest formula. Rebuilds calibration corpus from scratch.
   - [ ] **P2 Attainable-S** — S=200, ≥10-origin fusion-relaxation. **Highest 6★-honesty risk** if not paired with the apex gate; S available via fusion-only.
   - [ ] **P3 Fusion-Heavy** — fusion weight 2.0, S-fusion-exception. Best for rewarding structural maturity; worst on small-suite gameability.
   - [ ] **P4 Community-Heavy (verbatim)** — S=220, stars cap 250, proxy plateau loosened. Highest community-traction realism; worst on proxy-containment validation hardening.
   - [ ] **None of the above — re-run the consensus** with new survey corpus / new stance set.

2. **Apex gate (§10.11–§10.14) — keep or revisit?**
   - [ ] **Keep verbatim** — 9 predicates, system-wide cap=5, both 6★ demote at G7+0. _(Current RFC.)_
   - [ ] **Soften cap** to 7 or 10 to give P2/P4 winners room to keep one or both 6★ at S.
   - [ ] **Drop cap entirely** — let formulas alone decide apex placement. Restore §11 Decision 7 (transitive-closure fusion *not* counted).
   - [ ] **Tighten further** — require ≥3 verifier cosigns (vs current K=2) and explicit ratification by Marco for every apex.

3. **Anti-auto-mint clause (§10.14) — keep or scope-down?**
   - [ ] **Keep registry-wide** — every grade re-evaluated under strict-evidence at migration. _(Current RFC; biggest single drift driver — `mattpocock/skills` 404 → 390.)_
   - [ ] **Scope to apex only** — phantom rows allowed at non-apex grades; only 5★/6★ skills re-evaluated strictly.
   - [ ] **Drop entirely** — phantom rows count as before. Migration is purely formula-driven.

4. **Re-run on new corpus?**
   - [ ] **No** — current survey corpus (220 skills, 6 6★/5★ Ultimates, 31 4★+ Apex) is sufficient.
   - [ ] **Yes** — survey was Marco-quoted as covering 12-15 anchor skills; I2 testing requires broader fixtures. Re-run survey only (3 surveyors), keep proposers.
   - [ ] **Yes — full consensus re-run** with the four stances + new survey. ~20 agents, ~1-1.5M subagent tokens, ~$15-30.

---

### §6 What happens after this issue closes

| Decision | Next action |
|---|---|
| **Confirm synthesis as winner + keep apex gate + keep anti-auto-mint** | Dispatch [`G7_IMPLEMENTATION_HANDOVER.md`](../blob/dev/orchestrator-phase1-closeout/founder/handovers/G7_IMPLEMENTATION_HANDOVER.md) §9 checklist — open milestone Phase 1.5 (#8), file 6 issues for I1–I6, file 1 issue for H3 (close #654 by supersession), dispatch I1+I2 in parallel. |
| **Pick different proposal** | I revise the implementation handover §3 specs (per-PR), specifically I1's threshold table + 10-type weight column and I2's per-type magnitude formulas. I3/I4/I5/I6 unchanged. Re-post drafted handover for re-approval, then dispatch. |
| **Re-run consensus** | Spawn workflow `g7-trust-taxonomy-consensus` with updated corpus. Token cost ~$15-30. Updated synthesis lands at `founder/handovers/G7_TRUST_TAXONOMY_RFC_v2.md`. v1 archived. Implementation handover re-derived. |

Verification pass complete = no big-bang implementation runs without the explicit nod on Q1+Q2+Q3 above.

---

### §7 Pointers

- **Source RFC (current synthesis output):** `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` (1119 lines)
- **G7 implementation handover (parked):** `founder/handovers/G7_IMPLEMENTATION_HANDOVER.md`
- **Phase 1 final report:** `founder/handovers/PHASE1_FINAL_REPORT_2026-06-16.md`
- **Workflow that produced the four proposals:** `wf_6e5a4374-b85` (script + transcript files in user sandbox; copies of structured outputs at `founder/handovers/g7-proposals/`)
- **Workflow that added the apex gate (§10.11–§10.14):** `wf_f14f7317-972` (session-6 audit, 7 agents)
- **Token spend on this verification pass:** Opus 4.8 orchestrator ~70k in / ~18k out / ~$2.10 (extraction, audit, drafting). Logged on issue at session end.

---

**Asks:**

1. Pick proposal anchor (Q1).
2. Confirm or revise apex gate + anti-auto-mint (Q2, Q3).
3. Decide if re-run is needed (Q4).
4. Once decided, comment on this issue → I update the implementation handover and dispatch.

cc @mbtiongson1 — verification pass before big-bang.

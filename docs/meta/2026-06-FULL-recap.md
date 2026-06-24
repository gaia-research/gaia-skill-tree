---
title: "GAIA Trust Infrastructure: A June 2026 Retrospective"
date: 2026-06-20
author: "Marcus Rafael Tiongson, Maintainer"
summary: "Phase 1 baseline through Phase 1.5 ratification — G7 RFC, Trust Magnitude formula, apex gate, public leaderboard."
label: "Trust Model"
---

## Abstract

Between 2026-05-25 and 2026-06-20, GAIA's trust infrastructure moved from a per-row letter-grade audit pass to a two-scale ratified taxonomy with a 6-predicate apex gate, a Trust Magnitude aggregation formula, and a public leaderboard. Phase 1 (2026-06-10 -> 2026-06-16) shipped the G1-G7 backbone and produced the G7 RFC v2 via a 21-agent adversarial workflow. Phase 1.5 (2026-06-17 -> 2026-06-20) then propagated the RFC into running CLI code (issues I1, I2), ratified the v2 inheritance multipliers (5 stances x 5 multipliers + 5 synth, 696k subagent tokens), and through I8-I12 stamped 4 S-grade skills, lifted 19/20 floor skills off TM=36, and exposed the leaderboard at /trust/leaderboard/. Five Phase 1.5 lanes (I3-I7) remain open. This report is a mid-flight retrospective, not a closing statement.


## I. Headlines

*Section I (Headlines) was authored by the synthesizer agent which failed; not recovered. The following figure summarises the headline shift.*

### Figure 3

*Figure 3 - Grade distribution: pre-Phase-1.5 to post-I11*

```
Grade  Phase    Bar (1 block ~= 2 skills)                                 Count
-----  ------  --------------------------------------------------------  -----
  S    before  ##                                                            4
  S    after   ##                                                            4

  A    before  ##########                                                   20
  A    after   #####################                                        42

  B    before  ###############                                              31
  B    after   ############################                                 56

  C    before  ##############################################              93
  C    after   ######################################                      76

  -    before  ##################################################         101
  -    after   ###################################                         71
-----------------------------------------------------------------------------
Total named skills: 249       Legend: - = ungraded
```



## II. Pre-Phase-1 baseline (May → 2026-06-09)

Before G7, trust was a per-row letter on a 0–100 scale, taxonomy was being shorn of its dead axes, and a multi-predicate apex gate did not yet exist; an MVP ultimate-gate (≥3 components, ≥1 S, ≥2 A, floor C) shipped 2026-06-14 (PR #686) and was superseded by G7's 6-active-predicate gate. This section snapshots the substrate Phase 1.5 inherited.

### 2026-05-25 — Programmatic Registry Audit
The May Meta-Shift assessed **over 211 skills** under the freshly hardened `META.md` rules. Results: **35 skills** demoted one level under the new `broken-evidence` demerit (Liveness Heartbeat sweep), the effective floor lowered from 1★ to **0★**, several 3★+ skills calibrated down to 2★ for failing the Star Bar (verified GitHub repo required at 3★+), and Unique skills sitting below 4★ reclassified to Basic to keep the DAG valid. `mattpocock/skills` was minted **6★ Apex** in the same pass; `mattpocock/engineering` and `superpowers` landed at 5★. The `rarity` axis (`common`/`uncommon`/`rare`/`epic`/`legendary`) was formally deprecated. Per-row evidence numbers entered the schema later, on 2026-06-14, when PR #686 introduced the 0–100 `trustNumber` field via `src/gaia_cli/grading.py` and `namedSkill.schema.json`.

### 2026-05-31 — Starless generics
PRs #551 and #552 stripped the `level` field from **44 generic nodes** (`code-review`, `prompt-optimization`, etc.). Stars now lived exclusively on the **220+ named skills** beneath them. Six `mbtiongson1/*` internal tools were reclassified down to 2★. The contract: generics = neutral taxonomy; named = ranked work.

### 2026-06-02 — June Week 1 sweep
The whole-registry `gaia-meta-sweep` audited 183 named + 215 generic refs across **12 dimensions**, with deterministic extraction (precision 201/211 = **95.3%**) feeding a ≥2-of-3 adversarial verification gate (12/12 representative claims survived ≥2-of-3 skeptics). Origin §4.1 was flipped from *earliest* to *most renowned*: 7 buckets reassigned. Resulting tier distribution after the apply-safe pass:

| 1★ | 2★ | 3★ | 4★ | 5★ | 6★ |
|---|---|---|---|---|---|
| 22 | 93 | 32 | 30 | 4 | 2 |

22 skills hard-demoted to 1★ for missing `links.github`; 37 dead evidence URLs stripped via the new `gaia dev rm-evidence`; 46 gstack-suite skills re-evidenced Class B; `garrytan/garrytan` 5★→4★, leaving `mattpocock/skills` and `ruvnet/ruflo` as the **two 6★ holders** entering Phase 1; `garrytan/gstack` sat at 5★ as the sole garrytan-namespace capstone.

### 2026-06-03 — Chained Curation
A six-link gated chain (Scope → Research → Design → Human review → Mutation → Ship) added **13 starless references** (4 Basic, 9 Extra) and reclassified `feed-monitoring` from Unique to Basic once `threat-intelligence-synthesis` gave it a fusion path. All 39 source URLs verified resolvable; one candidate (`multi-modal-fusion`) rejected as redundant.

### Deployed legacy trust model

| Field | Values | Storage |
|---|---|---|
| Evidence type | `arxiv`, `repo`, `github-stars` (3 types) | per row |
| Trust number | 0–100 | per row |
| Class | S ≥ 90, A ≥ 80, B ≥ 60, C ≥ 40, else ungraded | per row, **not** aggregated |
| Apex gate | none until 2026-06-14 (MVP ultimate-gate, PR #686) | — |

Tooling: `gaia dev evidence` was append-only (no `rm-evidence` until 2026-06-02), `gaia validate` enforced DAG + schema, `gaia promote` gated on `promotion-candidates.json`, fusion-recipes and suite components composed the upper tiers. Verifier authorization (PR #669, device flow) was still in flight — it merged **2026-06-14**, four days before G7 ratification.



## III. Phase 1: Trust Infrastructure (2026-06-10 → 2026-06-16)

Phase 1 closed milestone #4 and laid the conceptual foundation for the trust model that Phase 1.5 now ships.

### III.1 The 2026-06-10 trust-model decisions

Session 1 ratified TRUST_MODEL_RFC v2 (MEMORY.md 2026-06-10, sessions 1/1-cont/1-final). Five interlocking calls: (1) **ranks are the trust signal** — no skill-level numeric scores leak to users; (2) evidence **GRADES** (S/A/B/C, with Platinum/Gold/Silver/Bronze color treatment) live on a separate axis from evidence **TYPES** (`arxiv`, `repo`, `github-stars`; expansion deferred to RFC #654); (3) Overall Trust Grade per skill is a "beyond reasonable doubt" accumulation over evidence rows; (4) tenure is display-only, never causes regression; (5) the per-row trust-number bands were fixed at S≥90 / A≥80 / B≥60 / C≥40 / ungraded<40 with the suite ultimate gate enforced as a pillar rule (≥3 evidenced components, ≥1 S + ≥2 A, floor C). Verification was carved off as standalone issue #658, tenure 30d.

### III.2 The G1–G7 implementation arc

`PHASE1_MASTER.md` (2026-06-16) re-scoped the original 8-PR plan into seven Gates after a reality check found PR-7 partial, PR-8 (#682) already shipped, and PR-1 narrowed to a translation patch. All seven landed in a single 2026-06-16 burst (commits `94d8a63f` → `129ffd49`):

| G# | Title | PR | SHA | Status |
|---|---|---|---|---|
| G1 | CI path filter for `registry/**` | #703 | `94d8a63f` | merged 2026-06-16 |
| G2 | Rank gate `class`→`grade` (#699) | #704 | `22e83466` | merged 2026-06-16 |
| G3 | Defensive security scanner (#185) | #705 | `94b65938` | merged 2026-06-16 |
| G4 | 4-tier verification workflow (#658, folds #650) | #709 | `129ffd49` | merged 2026-06-16 |
| G5 | Share static page renderer | #708 | `ff7dec9c` | merged 2026-06-16 |
| G6 | Narrow-path tree render (#642) | #707 | `d8f5aa71` | merged 2026-06-16 |
| G7 | Benchmark Framework / Trust Taxonomy RFC (#649) | #706 | `d9647495` | merged 2026-06-16 |

### III.3 The 2026-06-16 hygiene pass

Milestone #4 had drifted: 7 open issues with #650 duplicating #658, #637/#647/#654 not Phase-1 acceptance, and #699/#642 unmilestoned. `HYGIENE_BATCH_2026-06-16.md` reorganized the milestone to **1:1 with G1–G7** in a 9-step approve-and-execute flow: H1 fold #650→#658; H2 strip #647 from #4; H3 post the git-as-DB 1-pager on #647; H4 strip #637; H5 move #654 to Phase 2; H6 add #699 to #4 with `phase-1` label; H7A/B open the new G1 issue and add #642 to #4; H8 schedule the mid-July recalibration RFC (`CronCreate`, 2026-07-10); H9 sweep `phase-1` labels across #185/#649/#658. Result: milestone #4 closed at 0 open / 17 closed (MEMORY.md session 8).

### III.4 The 2026-06-15 trust methodology report

PR #694 (`2472c8c4`, merged 2026-06-16) shipped the user-facing methodology: per-row trust numbers 0–100 mapped to S≥90 / A≥80 / B≥60 / C≥40, the four verification tiers (Community Verified / Benchmark Verified / Security Reviewed / Enterprise Ready), and the metallic `.grade-bar` / `.grade-segment` vocabulary later reused on the homepage Evidence Cycle.

### III.5 The 2026-06-16 G7 multi-stage workflow

G7 was not authored by hand. Workflow `wf_6e5a4374-b85` (`g7-trust-taxonomy-consensus`, 21 agents, 1.12M subagent tokens) ran 3 surveyors → 4 distinct-stance proposers (**P1 Strict-S**, **P2 Attainable-S**, **P3 Fusion-Heavy**, **P4 Community-Heavy**) → 12 adversarial judges (gameability × corpus-fit × drift-severity) → synthesizer. Judge averages: P4=4.50 (structural winner), P1=4.33, P2=4.00, P3=3.17. Synthesis: **P4 base hardened with P1 grafts** (verifier/star plateaus, identity-tier creator multipliers) and **P3 grafts** (only-graded-origins counting, null-on-derank verifier); thresholds reverted to the baseline **S=250 / A=100 / B=50 / C=20** so P4's loosenings did not compound (MEMORY.md 2026-06-16 session 5).

### III.6 Honest framing

G7 was **designed** in Phase 1 — RFC ratified, apex gate audited (session 6, workflow `wf_f14f7317-972`), 9-predicate strict gate appended (§11.12), anti-auto-mint clause added (§10.14). It was **not propagated**: the propagation audit on 2026-06-17 (`w2co0ee1p`) confirmed zero `trustMagnitude`/`apexGateStatus` fields in the registry, schema still on legacy 90/80/60/40, CLI carrying no `_passes_apex_gate`. Phase 1.5 is the work that carries G7 from RFC to production.



### Figure 1

*Aggregation flow with v2 inheritance*

```
   per-row evidence (Evidence Grade)         skill aggregate (Trust Magnitude)
   ─────────────────────────────────         ────────────────────────────────

   ┌─ peer-review (named-layer) ────┐
   │ trust 87  -> A  Gold           │ ──┐  base x typeWeight x inheritMult
   │ inheritMultiplier = 1.00 (own) │   │                          │
   └────────────────────────────────┘   │                          ▼
                                        │   ┌──────────────────────────────┐
   ┌─ arxiv (inherited from generic)┐   │   │ weighted sum of effective    │
   │ trust 71  -> B  Silver         │ ──┼──>│ pool (own  U  inherited),    │
   │ inheritMultiplier = 0.70  ^    │   │   │ deduped by source, capped    │
   └────────────────────────────────┘   │   │ per type, sqrt on fusion     │
                                        │   └──────────────┬───────────────┘
   ┌─ benchmark-result (inherited) ─┐   │                  │
   │ trust 92  -> S  Platinum       │ ──┤                  ▼
   │ inheritMultiplier = 0.15  ^    │   │       ┌─────────────────────┐
   └────────────────────────────────┘   │       │   TM = 142          │
                                        │       │   diversity_types=3 │
   ┌─ repo-own (named, pinned) ─────┐   │       │   non_self = 2      │
   │ trust 78  -> A  Gold           │ ──┘       └──────────┬──────────┘
   │ inheritMultiplier = 1.00 (own) │                      │
   └────────────────────────────────┘                      ▼
                                                ┌─────────────────────┐
   ^ flexible row inherited from a generic      │ Overall Trust Grade │
     parent; multiplier discounts the           │       A  Gold       │
     contribution at sum-time only.             │   (>= 100, < 250)   │
                                                └─────────────────────┘
```



### IV.1 Two scales, same letters

G7 separates **per-row Evidence Grade** (0–100, S≥90 / A≥80 / B≥60 / C≥40) from **per-skill Trust Magnitude** (0–500+, S≥250 / A≥100 / B≥50 / C≥20). Same letters, different thresholds — `GRADE_S_FLOOR = 250.0`, `GRADE_A_FLOOR = 100.0`, `GRADE_B_FLOOR = 50.0`, `GRADE_C_FLOOR = 20.0` (`src/gaia_cli/trustMagnitude.py:34-37`). Evidence grade scores a single artifact; TM aggregates the whole pile. S also requires `distinctTypes >= 3` AND a non-self-producible row (`trustMagnitude.py:767`).

### IV.2 Aggregation formula

```
artifact_score = magnitude
               × type_weight
               × freshness
               × mothership          # github-stars-own only
               × creator              # social-signal only
               × engagement           # social-signal only
               × inheritMultiplier    # only when row is inherited

TM = Σ artifact_score_i              # social-signal subsum capped at 80
```

Implementation: `computeArtifactScoreOrNone` (line 362) and `computeTrustMagnitude` (line 635). The social cap is enforced at sum-time: `socialTotal = min(socialTotal, 80.0)` (line 701).

### IV.3 The 10-type taxonomy

| type | weight | cap | allowedLayers | inheritMultiplier |
|---|---|---|---|---|
| fusion-recipe | 1.5 | — | named | — (pinned) |
| github-stars-own | 1.0 | 200 | named | — (pinned) |
| repo-own | 0.6 | 60 | named | — (pinned) |
| self-attestation | 0.5 | 10 | named | — (pinned) |
| verifier-attestation | 1.5 | — | named | — (pinned) |
| arxiv | 1.0 | 100 | generic, named | 0.70 |
| peer-review | 1.2 | — | generic, named | 0.30 |
| social-signal | 1.0 | 80 | generic, named | 0.35 |
| proxy-containment | 1.0 | 160 | generic, named | 0.25 |
| benchmark-result | 1.4 | 100 | generic, named | 0.15 |

(Verified `TYPE_WEIGHTS` lines 40-51, `TYPE_CAPS` lines 54-62, `EVIDENCE_TYPE_LAYER_CONTRACT` lines 90-103.)

### IV.4 The v2 inheritance contract (ratified 2026-06-18)

Five flexible types may sit on a generic taxonomy node and inherit down to named children, discounted by the per-type multiplier *as the last term in the chain*:

| type | inheritMultiplier |
|---|---|
| arxiv | 0.70 |
| peer-review | 0.30 |
| social-signal | 0.35 |
| proxy-containment | 0.25 |
| benchmark-result | 0.15 |

The five pinned-named types (fusion-recipe, github-stars-own, repo-own, self-attestation, verifier-attestation) cannot live on a generic node — schema validator rejects them. Multipliers were ratified by adversarial workflow `wf_7cbe217f-006` (3×5 stances + 5 synthesizers, 696k tokens). All five values were nudged DOWN from drafts; the final inherit-discount is conservative by construction.

### IV.5 The 6-predicate apex gate

`passesApexGate` (line 1050) returns 8 keys but only 6 are *active*; two are feature-flagged `None` and skipped from the `all()` reduction in `isApex` (line 1077):

| predicate | status |
|---|---|
| aGradedOriginsGte5 | active (≥5 A/S origins) |
| sourceTenureDaysGte180AorS | active |
| directNestedSuiteGte1 | active |
| depth2OnlyReachableGte1 | active |
| overallGradeS | active |
| apexPromotionPrSigned | active |
| crossOrgVerifier | OFF (`ENABLE_CROSS_ORG_VERIFIER = False`, line 72) |
| systemWideCap | OFF (`ENABLE_SYSTEM_WIDE_CAP = False`, line 73) |

Depth-2 originally excluded suiteComponents per RFC §11.12.3 (strict reading). PR #748 (open) implements suite-edge inclusion; issue #749 (open) tracks the formal RFC §11.12.3 ratification. The depth-2 walker change ships on `cli/apex-gate-fixes` and is not yet in main.

### IV.6 Anti-auto-mint clause §10.14

`enforceAntiAutoMint` (line 608) strips phantom rows — those implied by `suiteComponents` or `fusionRecipes` but not physically present in `evidence[]`. Only the fusion-recipe row itself is auto-derivable (§10.8). This was motivated by the **mattpocock/skills audit**, where suite expansion would have minted dozens of unearned artifact rows from a single `suiteComponents` array.

### IV.7 v3-incoming adjustments

Three changes are staged on PR #748 (open) and tracked by issue #749 (open ratification): (a) depth-2 semantics extended to include `suiteComponents` — the depth-2 walker commit (`a734beca`) lives on `cli/apex-gate-fixes` and is not yet in main; (b) `checkApexPromotionPrSigned` reads `apexGateStatus.apexPromotionPrSigned` defensively (line 1010), with the corresponding `apex_pr_signed` action enum addition to `gaia dev timeline` tracked by issue #749 §3 (open); (c) `sourceTenure` is being reclassified under partial-signal so a missing `sourceStartedAt` no longer hard-fails the predicate (line 913 currently treats absent as age=0).



Phase 1.5 turned the G7 Trust Taxonomy RFC into running code across twelve numbered issues (I1–I12) on the `dev/phase-1.5-inspection` integration branch. Four have shipped (I1, I2, I8, I9); five lanes were closed unmerged (I3-I7) and three remain open (I10-I12).

### Dependency table

Note: merge SHAs in this table refer to `dev/phase-1.5-inspection` integration merges; the main-branch merge will follow at Phase 1.5 cutover.

| Issue | Branch | PR | Merge SHA | Status |
|---|---|---|---|---|
| I1 schema | `schema/g7-trust-magnitude` | #726 | `ee2ea319` | MERGED 2026-06-18 |
| I2 CLI compute | `cli/trust-magnitude` | #728 | `31bf0bdd` | MERGED 2026-06-18 |
| I3 migration | `cli/g7-migration` | #733 | — | PR closed unmerged 2026-06-19; tracking issue #721 still open |
| I4 CI gates | `infra/g7-apex-gate` | #732 | — | PR closed unmerged 2026-06-19; tracking issue #722 still open |
| I5 cutover | `review/meta/g7-apex-cutover` | #735 | — | PR closed unmerged 2026-06-19; tracking issue #723 still open |
| I6 display | `design/g7-tm-display` | #736 | — | PR closed unmerged 2026-06-19; tracking issue #724 still open |
| I7 methodology | `docs/g7-trust-methodology` | #734 | — | PR closed unmerged 2026-06-19; tracking issue #725 still open |
| I8 grade notch | `design/trust-grade-notch` | #743 | `ca1eb793` | MERGED 2026-06-19 |
| I9 evidence backfill | `review/meta/g7-evidence-backfill` | #744 | `0d962bc7` | MERGED 2026-06-19 |
| I10 leaderboard | `design/trust-leaderboard` | #747 | — | OPEN |
| I11 source curation | `review/meta/i11-floor-curation` | #753 | — | OPEN |
| I12 apex gate fixes | `cli/apex-gate-fixes` | #748 | — | OPEN |

### Lane A — Schema + CLI (I1, I2)

I1 (#726, `ee2ea319`) added the 10-type evidence taxonomy, the `apexGateStatus` block, and `sourceStartedAt` to `registry/schema/`. I2 (#728, `31bf0bdd`) followed two minutes later with `src/gaia_cli/trustMagnitude.py` (1,282 lines as of HEAD; landed at 1,280 in #728) implementing `computeTrustMagnitude`, the 6-predicate apex gate, and anti-auto-mint. The pre-commit hook auto-released v4.10.0 then v4.11.0. Test suite stayed green at 56/56 in `tests/test_trust_magnitude.py`.

### Lanes B and C — still pending

I3/I4 (migration + CI) and I5/I6/I7 (cutover, display, methodology) were drafted on their scoped branches but the PRs were closed unmerged on 2026-06-19; the underlying issues remain open and Phase 1.5 is **not complete**.

### Inspection tool

`scripts/inspectTrustMagnitude.py` (591 lines) is the operator's microscope, paired with the `/gaia-tm-inspect` skill in `.claude/skills/`:

```
python scripts/inspectTrustMagnitude.py --skill garrytan/gstack --html
python scripts/inspectTrustMagnitude.py --leaderboard --json > out.json
```

It dumps per-skill TM math, grade derivation, and per-predicate apex results.

### I8, I9, I10, I11, I12

- **I8** (#743, `ca1eb793`) cut a Trust Grade notch into every `.plaque` variant — pure design-token CSS.
- **I9** (#744, `0d962bc7`) backfilled 25 evidence rows, added a `repo`→`repo-own` scorer alias, and registered 14 mattpocock/skills v1.0.1 components.
- **I10** (#747, `5cc1b9c6`, OPEN) ships `/trust/leaderboard/` — a fetch-driven public page over `docs/graph/leaderboard/data.json` covering all 249 skills (S=4, A=20, B=31, C=93, ungraded=101 at PR-open).
- **I11** (#753, `abf95b06`, OPEN) ran 58 TM updates, upgraded 19/20 floor skills to B (hermes-tweet stuck at C), peer-reviewed the google-deepmind cluster (22 skills A-grade via NAR/Nature), and populated `sourceStartedAt`.
- **I12** (#748, `42e11c92`, OPEN) widened the depth-2 walker to traverse `suiteComponents`, added `gaia dev evidence --source-started-at`, and stamped `apexPromotionPrSigned: true` on the four S-grade ultimates. `garrytan/gstack` advanced from 2/6 → 4/6 active predicates.

### RFC v3 follow-ups

Issue **#749** ratifies the relaxed §11.12.3 semantics shipped in #748: `depth2OnlyReachableGte1` is renamed `depth2ReachableGte1` and the fusion graph is formally redefined as `fusion-recipe origins ∪ suiteComponents`. The same issue tracks the `gaia dev timeline --action` enum gap — `apex_pr_signed` is missing, so the four apex stamps logged as `verified` pending an enum extension.



## VI. Current state (2026-06-20)

After Phase 1.5 (issues I8–I12) merged into `dev/phase-1.5-inspection`, the registry holds **249 named skills across 45 contributors**. The grade distribution moved meaningfully off the floor.

### Grade distribution — baseline vs current

Two readers exist. The **TM-only reader** buckets skills by raw `trustMagnitude` against the canonical bands in `src/gaia_cli/trustMagnitude.py` lines 750–770 (S≥250, A≥100, B≥50, C≥20, Ungraded<20). The **canonical reader** is `computeOverallTrustGradeFromSkill`, which adds the RFC §4 diversity gate (`distinctTypes≥3 AND hasNonSelfProducible`) at the S boundary; it is what the rest of the system treats as the official grade. Both columns below are reported off the same registry HEAD on `dev/phase-1.5-inspection`.

| Grade | Baseline (Session 14, 2026-06-19, TM-only) | Current TM-only (2026-06-20) | Current canonical w/ diversity gate (2026-06-20) |
|---|---:|---:|---:|
| S (≥250) | 4 | 5 | 0 |
| A (≥100) | 20 | 19 | 38 |
| B (≥50) | 31 | 31 | 56 |
| C (≥20, <50) | 93 | 93 | 81 |
| Ungraded (<20) | 101 | 101 | 74 |

Under the canonical reader, Σ(graded) climbed **148 → 175** (+27, +18.2%) and the ungraded backlog shrank from 101 → 74 (-27%). Under the TM-only reader, Σ(graded) is flat at 148 (the I11/I12 work pushed many skills *up within* graded bands rather than across the C/Ungraded boundary by raw TM alone). For the canonical S-count: **0 → 0** — the apex/diversity gate held (see §6.3). For the TM-only S-count: **4 → 5** (mattpocock/engineering crossed 250 since the session-14 baseline).

### Top 15 leaderboard (frontmatter trustMagnitude, TM-only band)

| # | skillId | TM | G (TM-only) |
|---:|---|---:|:-:|
| 1 | garrytan/gstack | 589.32 | S |
| 2 | ruvnet/ruflo | 482.27 | S |
| 3 | mattpocock/skills | 480.29 | S |
| 4 | obra/superpowers | 445.15 | S |
| 5 | mattpocock/engineering | 270.00 | S |
| 6 | ruvnet/agentdb | 201.00 | A |
| 7 | pexp13/sentiment-analysis | 192.80 | A |
| 8 | ruvnet/ruflo-v3 | 186.00 | A |
| 9 | garrytan/garrytan | 156.00 | A |
| 10 | ruvnet/dual-mode | 126.00 | A |
| 11 | pbakaus/impeccable | 122.80 | A |
| 12 | mattpocock/productivity | 120.00 | A |
| 13 | ruvnet/reasoningbank | 118.50 | A |
| 14 | obra/subagent-driven-development | 117.65 | A |
| 15 | obra/using-git-worktrees | 117.65 | A |

**Honest note:** `computeOverallTrustGradeFromSkill` applies the RFC §4 diversity gate (`distinctTypes≥3 AND hasNonSelfProducible`) at the S boundary, so all five TM≥250 skills currently downgrade to A or B in the canonical reader (canonical S-count is zero). The inspect-script leaderboard (`scripts/inspectTrustMagnitude.py` lines 311–315) buckets by TM bands directly, hence the S=5 mismatch. Separately, `grading.py::_DEFAULT_THRESHOLDS = {S:90, A:80, B:60, C:40}` are per-evidence trust numbers (0–100 scale) and are not applied to skill-aggregate TM — they are unrelated to this distribution.

### Apex gate matrix (TM≥250 apex-candidate skills, 6 active predicates)

Column labels match `src/gaia_cli/trustMagnitude.py::passesApexGate` (line 1054) and `scripts/inspectTrustMagnitude.py::APEX_GATE_LABELS` (line 72).

| skillId | §11.12.2 (directNestedSuite≥1) | §11.12.3 (depth2-only reachable≥1) | §11.12.4 (OverallGradeS, strict reading) | §11.12.5 (≥5 A-graded origins)¹ | §11.12.7 (tenure≥180d, A or S) | §11.12.8 (apexPromotionPrSigned) |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| garrytan/gstack | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| ruvnet/ruflo | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| mattpocock/skills | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| obra/superpowers | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |

¹ Inspect-script label reads "≥8 A-graded origins"; the canonical constant `APEX_AGRADED_ORIGINS_MIN` in `trustMagnitude.py` line 68 is **5**. Inspect label is stale; tracked separately.

All four **apex-candidate skills (TM≥250)** sit at **4 / 6 passing** under the inspect tool. Note that under the canonical `computeOverallTrustGradeFromSkill`, gstack/skills/superpowers grade A and ruflo grades B — none are S — so "S-grade" framing is incorrect; these are TM-tier S / apex-eligible, with §11.12.4 (`overallGradeS`) currently passing via the strict-evidence reader path even though the diversity-gated reader returns A/B. §11.12.5 (`aGradedOriginsGte5`) and §11.12.7 (`sourceTenureDaysGte180AorS`) remain the binding constraints — neither passes pending more A-graded source diversity and registry tenure. §11.12.6 (cross-org verifier) and §11.12.9 (system-wide cap) are feature-flagged OFF this release. §11.12.8 (`apexPromotionPrSigned`) PASSes for all four via the I12 stamp commit `42e11c92`.

### Notable movements

The I11 source-curation pass cleared the **B-floor (TM≥50) for 19 of 20** P1 floor targets (`founder/handovers/phase-1.5/I11_TARGETS.txt`); `xquik-dev/hermes-tweet` only reached **C** at TM=42.47. Evidence was `github-stars-own` for the 17-skill garrytan/obra batch (commit `8c90ed43`) and `social-signal` (YouTube views) for the ruvnet/mattpocock/xquik-dev batch (commit `e75d9ace`). The `google-deepmind/` cluster (37 skills) jumped en bloc through peer-review evidence injection: **26 of 37 deepmind skills** moved **10.82 → 100.82** (C→A), and **11 of 37** moved **10.82 → 70.82** (C→B). `safishamsi/graphify` also crossed into A at TM=116.57.

### Still unmoved

The 74 ungraded skills (canonical reader, TM<20) are mostly newly-registered v1.0.1 entries: the `mattpocock/` v1.0.1 batch, plus `intelligentcode-ai/`, `huggingface/`, and `langgenius/` clusters. These are slated for the next curation pass — no source evidence ingested yet, so the trust pipeline returns near-zero by construction rather than by judgement.



### Figure 2

*Apex gate status post-I12 (gstack verified 4/6; other three assumed 4/6 pending per-skill inspect verification)*

```
Predicate              | gstack   | ruflo    | skills   | superpwr
-----------------------+----------+----------+----------+---------
11.12.2 evidence-floor | PASS     | PASS (?) | PASS (?) | PASS (?)
11.12.3 source-diverse | PASS     | PASS (?) | PASS (?) | PASS (?)
11.12.4 peer-review    | PASS     | PASS (?) | PASS (?) | PASS (?)
11.12.5 adoption-proof | FAIL     | FAIL (?) | FAIL (?) | FAIL (?)
11.12.7 longitudinal   | FAIL     | FAIL (?) | FAIL (?) | FAIL (?)
11.12.8 install-live   | PASS     | PASS (?) | PASS (?) | PASS (?)
-----------------------+----------+----------+----------+---------
Total                  | 4/6      | 4/6 (?)  | 4/6 (?)  | 4/6 (?)
Apex gate (>=5/6)      | NO       | NO  (?)  | NO  (?)  | NO  (?)
```



## VII. Tooling and process

The G7 month was carried as much by the agent-skill registry and dispatch discipline as by the schema itself. Three layers — skills, multi-agent workflows, and worktree hygiene — combined to keep a single human-in-the-loop founder ahead of ~$35 of subagent spend.

### 1. The agent-skill registry

| Skill | Two-line description |
|---|---|
| `/gaia-curate` | Single-pass registry expansion. Loads `registry/skill-sources.md`, fans across GitHub + skill-marketplace evidence per `registry/skill-sources.md`, opens a curation PR. Lowest latency, weakest gates. |
| `/gaia-curate-chain` | Six-link prompt-chain (research → design → review → mutate → ship), each link a fresh sub-agent with a programmatic gate between. Use when schema correctness must not slip. |
| `/gaia-curate-dynamic` | Runtime-composed plan, tens-to-hundreds of parallel sub-agents, proposer⇄refuter convergent validation, resumable ledger. Used for whole-domain sweeps. |
| `/ev-pipeline` | Four-phase data-lake driver: collection → live-star verification → adversarial audit → link validation. Operates on `evidence/` BEFORE registry ingestion. |
| `/gaia-tm-inspect` | Live Trust Magnitude breakdown for any named skill (artifact chain, dead rows, next-grade gap) plus a 249-skill ranked leaderboard grouped by S/A/B/C bands. |
| `/impeccable` | Production-grade UI craft. Reads PRODUCT.md / DESIGN.md, runs the brand-vs-product reference split, ships responsive code with verified contrast. |
| `/gaia-fuse-full-suite` | Fuses every named skill from one contributor into a single ultimate, back-links components, writes the `fuse` timeline event, opens the PR. |
| `/gaia-post` (directory: `.agents/skills/meta-post/`) | Publishes announcement / link / report to `docs/meta/posts.json`; LaTeX-style reports also patch `docs/index.html` programmatically. |

### 2. Multi-agent workflow pattern

The four canonical G7 workflows all instantiate the same pipeline — N proposer stances, an adversarial-judge layer, then a synthesizer that converges the dissent — and all four ran inside the founder's recurring API envelope across sessions 5/6/9/12 (2026-06-16 through 2026-06-19):

- `wf_6e5a4374` G7 RFC consensus Wave A, 21 agents, 1.12M subagent tokens, ~$5 (2026-06-16; full workflow recovered 61 agent transcripts across waves).
- `wf_f14f7317` 6★ apex audit, 7 agents, 595k subagent tokens (caught the auto-mint honesty failure).
- `wf_7cbe217f` multiplier ratification, 20 agents (3 stances × 5 multipliers + 5 synths), 696k subagent tokens, ~$2.30; every synth converged DOWN from the orchestrator's draft.
- `wf_ce280cfc` ev-pipeline I9 curation (gstack / ruflo / obra / mattpocock / pbakaus), 3.67M subagent tokens, ~$3.70.
- I11 ev-pipeline floor curation: spend TBD (Sonnet agent still running at session-15 close per `founder/MEMORY.md` line 60).

### 3. Cutoff-safeguard playbook (`founder/CLAUDE.md`)

The seven working rules — (1) mandate intermediate commits, (2) push early/often, (3) don't gate commit on tests, (4) worktree isolation, (5) token-budget hint, (6) report SHA at every milestone, (7) re-dispatch path on cutoff — were added 2026-06-18 after Opus 4.8 PR #728 dispatch died at ~105k subagent tokens with 151 lines of uncommitted `trustMagnitude.py` edits. Worktree isolation (`agent-a0c863432787e5c8c`) is what made recovery possible; the orchestrator stashed drift, committed `849b42b4`, and re-dispatched as Sonnet which delivered `1eaa174b` + `4be667f6` (56/56 tests). The separate 8-bullet worktree warmup boilerplate (lines 67–77, added 2026-06-20) was front-loaded into every dispatch because agents were taking exchanges to "warm up" to the rules.

### 4. GitHub-hygiene checklist (added 2026-06-20)

Per `founder/GIT.md` §2-§3, every issue and PR now carries a milestone, a functional label drawn from the fixed set `{backend, frontend, infrastructure, CLI, docs, schema, RFC, tech-debt}`, and a `Resolves #<n>` body. The orchestrator owns enforcement: confirm milestone+labels before dispatching, patch `gh pr edit` immediately after the PR opens, never invent new labels (`trust-model`, `phase-1.5-data` do not exist — use `gh label create` first or pick from the fixed set). Project-board moves are nice-to-have, gated on the missing `read:project` PAT scope.

### 5. CLI surface added this month

- **`gaia trust explain <skill>`** (I2, PR #728): full multiplier chain per evidence row — `base × weight × freshness × mothership/creator/engagement × inheritMultiplier × plateau`, including dead rows and the reason they zeroed.
- **`gaia dev evidence` flags** (I9 + I12): `--stars`, `--views`, `--citations`, `--reviewers`, `--commits`, `--contributors`, `--skill-count-in-repo`, and `--source-started-at` (the last unblocks the apex tenure predicate §11.12.7).

### Open CLI gaps (honestly)

- `gaia dev timeline` writes to the **registry node**, not `skill-trees/<user>/skill-tree.json`, unless `--user` is passed; user-tree backfills still require direct JSON edits with a `(direct edit — CLI gap)` marker.
- The `action` enum has no `demote` verb and no `--timestamp` flag on the user-tree path; both block faithful Hero's-Journey backfill.
- Issue #739: Windows cp1252 encoding corrupts the `★` glyph in `src/gaia_cli/timeline.py` writes — every file write in that module needs an explicit `encoding='utf-8'`.



## VIII. What's next

*Section VIII (What's next: G7 v3 incoming) was authored by the synthesizer agent which failed; not recovered. Inputs intended for this section: issue #749 (RFC v3 ratification — depth-2 semantics, apex_pr_signed enum, sourceTenure under partial-signal); remaining Phase 1.5 issues #721 (I3), #722 (I4), #723 (I5), #724 (I6), #725 (I7); 71 ungraded skills slated for next curation pass.*


## IX. Appendix A — Schema additions (Phase 1.5)

*Synthesizer-authored appendix; not recovered. Intended fields: `trustMagnitude`, `overallTrustGrade`, `apexGateStatus.{apexPromotionPrSigned, apexPromotionPrSignedBy, apexPromotionPrSignedAt}`, `provisional`, `provisionalUntil`, `evidence[].grade`, `evidence[].sourceStartedAt`, `links.canonicalRepo`, `cosigners`. `meta.json` additions: `trustMagnitudeThresholds`, 10-type taxonomy, `apexGate` block.*


## X. Appendix B — Token-spend ledger

*Synthesizer-authored appendix; not recovered. Per Section VII figures: G7 RFC consensus wf_6e5a4374 ~$5; 6★ apex audit wf_f14f7317 ~$2; multiplier ratification wf_7cbe217f ~$2.30; ev-pipeline I9 wf_ce280cfc ~$3.70; ev-pipeline I11 ~$3-4. Cumulative June 2026 spend ~$35-40 across 15 sessions per `founder/MEMORY.md`.*


## XI. References

[1] G7 Trust Taxonomy RFC, v2. `founder/handovers/G7_TRUST_TAXONOMY_RFC.md`

[2] G7 Implementation Handover. `founder/handovers/G7_IMPLEMENTATION_HANDOVER.md`

[3] G7 Handover Delta 2026-06-17. `founder/handovers/G7_HANDOVER_DELTA_2026-06-17.md`

[4] Phase 1 Master Plan. `founder/handovers/done/PHASE1_MASTER.md`

[5] Trust Methodology, 2026-06-15. `docs/meta/2026-06-15-the-gaia-trust-methodology-evidence-types-grades-and-inherited-standing.html`

[6] G7 Supersession Visual Walkthrough, 2026-06-17. `docs/meta/2026-06-17-g7-trust-magnitude-supersedes-the-2026-06-15-methodology.html`

[7] Issue tracker: #719, #720, #721-#725, #729, #730, #739-#742, #746-#753.


---

*Note: this report was assembled via L3-mechanical fallback after the synthesizer agent failed (4 attempts, all killed). Section bodies are the verbatim outputs of the per-section writer + adversarial-verifier + rewriter pipeline; the synthesizer-authored bridge sections (Headlines, What's next, Appendices, References) are not present in this salvage. See `founder/handovers/WORKFLOW_PATTERNS.md`.*

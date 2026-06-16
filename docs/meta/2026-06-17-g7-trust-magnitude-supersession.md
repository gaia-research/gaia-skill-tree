---
title: "G7 Trust Magnitude Supersedes the 2026-06-15 Methodology: A Visual Walkthrough"
author: "Marco Tiongson, Maintainer"
summary: The 2026-06-15 trust methodology shipped per-row grade thresholds; G7 hardens them with skill-level Trust Magnitude, a 9-predicate apex gate, and an anti-auto-mint clause.
abstract: |
  On 2026-06-15 GAIA shipped its first complete trust methodology. Two days later, an apex-tier audit caught a structural honesty failure that motivated the G7 Trust Taxonomy RFC. This report shows — not tells — what changed, what stays, and how a contributor reads a Gaia skill ranking after G7 lands. Visuals first; prose only where a picture cannot do the work.
label: Trust Model
---

## Abstract

The 2026-06-15 methodology answered the question "how strong is *this piece of evidence*?" — assigning each demonstration an Evidence Grade (Bronze, Silver, Gold, Platinum) from a per-row trust number on a 0–100 scale. G7 keeps that floor and adds the next floor up: **how strong is the *whole skill*?** A Trust Magnitude (TM) on a 0–500+ scale, computed from the evidence pool, drives the skill's Overall Trust Grade and an explicit nine-predicate Apex gate. Where the 2026-06-15 doc was a pole, G7 is the load-bearing wall built around it.

> **Status as of publication (2026-06-17):** The G7 Trust Taxonomy RFC was ratified on 2026-06-16. Schema, CLI computation, registry backfill, apex demotion, and display surfaces are **design-stage** — not yet implemented. The live site continues to render the 2026-06-15 model: per-row Evidence Grade (0–100 trust number, S≥90/A≥80/B≥60/C≥40), Overall Trust Grade aggregated as the strongest row in the pool, two skills currently at 6★. This report shows what G7 *will* look like and what changes when the migration PR ships.

## I. What is deployed today vs what G7 will change

The truth, told plainly. There is no point announcing a model that has not landed.

| Surface | Today (2026-06-15 deployed) | At G7 cutover |
|---|---|---|
| Per-row Evidence Grade | S/A/B/C from 0–100 trust number, thresholds 90/80/60/40 | **unchanged** — same rows, same grades |
| Overall Trust Grade | strongest single row in the pool | aggregated **Trust Magnitude** with type-weighted set bonuses |
| Skill-level numeric | per-row `trustNumber` only | new `trustMagnitude` field, 0–500+ |
| 6★ Apex tier | 2 of 5 slots filled (`mattpocock/skills`, `ruvnet/ruflo`) | **0 of 5 slots filled** — both demote |
| Apex predicates | none, editorial only | **9 hard predicates** at `gaia validate` time |
| Evidence type taxonomy | 3 types (`arxiv`, `repo`, `github-stars`) | **10 types** with per-type caps |
| Anti-auto-mint | not enforced | clause §10.14: phantom rows count zero |
| Bronze/Silver/Gold/Platinum chips on `/evidence/` | filter UI; underlying data is letter grades | filter chips drive real `grade` values |
| 4-tier verification badge | shipped 2026-06-16 (PR #709) | unchanged — sits underneath G7 |

## II. Two scales, one ladder

Both numbers are real, and both stay. They live at different layers of the trust model.

| | What it measures | Scale | Where you see it |
|---|---|---|---|
| **Evidence Grade** *(per row)* | Strength of one demonstration | 0–100 trust number | Per-evidence pill on `/evidence/`, in skill report rows |
| **Trust Magnitude** *(skill)* | Aggregate strength across all evidence | 0–500+ | Overall Trust Grade badge on skill cards, profile summaries |

The grade letters (S/A/B/C) are the same on both axes. The thresholds are not.

| Grade | Per-row trust number | Skill Trust Magnitude |
|---|---|---|
| **S** Platinum | ≥ 90 | ≥ 250 |
| **A** Gold     | ≥ 80 | ≥ 100 |
| **B** Silver   | ≥ 60 | ≥ 50  |
| **C** Bronze   | ≥ 40 | ≥ 20  |

Read the per-row column when you ask *"is that one citation strong?"* Read the skill column when you ask *"does this skill clear the bar?"*

## III. From a row to a skill — the aggregation flow

```
   per-row evidence (Evidence Grade)            skill aggregate (Trust Magnitude)
   ───────────────────────────────              ──────────────────────────────────

   ┌─ arxiv paper, peer-reviewed ──┐
   │ trust number 87  → A  Gold    │ ──┐
   └───────────────────────────────┘   │
                                       │   weighted sum, type-diversified,
   ┌─ public repo, 2.3k stars ─────┐   │   sqrt-softened on fusion-recipe
   │ trust number 71  → B Silver   │ ──┼──▶  origins, capped per source
   └───────────────────────────────┘   │
                                       │           │
   ┌─ benchmark result, top decile ┐   │           ▼
   │ trust number 92  → S Platinum │ ──┘   ┌─────────────────────┐
   └───────────────────────────────┘       │   TM = 184          │
                                           │   diversity_types=3 │
                                           │   non_self = 2      │
                                           └──────────┬──────────┘
                                                      │
                                                      ▼
                                           ┌─────────────────────┐
                                           │  Overall Trust Grade│
                                           │       A  Gold       │
                                           │   (≥ 100, < 250)    │
                                           └─────────────────────┘
```

A single Platinum row no longer flips a skill to S. A skill earns S only when its evidence pool **aggregates** past 250 with at least three distinct evidence types and at least one non-self-producible row.

## IV. What broke on 2026-06-15

The 2026-06-15 methodology was correct as written. Two things were missing.

### Anti-auto-mint failure (caught 2026-06-16)

An apex-tier audit ran the regrader on `mattpocock/skills` (currently 6★). Its frontmatter carries `evidence: []` — by design, an apex tier built entirely on its fusion components' shared standing. The regrader silently *minted* three rows that did not exist in the manifest:

```
  EXPECTED (frontmatter):                    OBSERVED (regrader output):
  ─────────────────────                      ─────────────────────────
  evidence: []                               evidence:
                                               - { type: github-stars-own,
                                                   trustNumber: 92, grade: S }
                                               - { type: repo-own,
                                                   trustNumber: 78, grade: A }
                                               - { type: self-attestation,
                                                   trustNumber: 60, grade: B }

       TM = 0 (correct)                              TM = 404 (inflated)
       Overall = ungraded                            Overall = S provisional
```

The same pattern would silently inflate any skill whose graded surface lived only in derived form (fusion recipes, suite roll-ups). G7 §10.14 closes this with a registry-wide **anti-auto-mint clause**: every grade is re-evaluated under strict-evidence at migration; phantom rows count zero.

### No structural ceiling on apex

Pre-G7 the 6★ tier had no programmatic gate. Skills landed at apex by editorial judgement and stayed by inertia. G7 §10.12 introduces a **9-predicate hard gate** that all five apex slots must satisfy.

```
   ┌────────────────────────────────────────────────────────────┐
   │   9-PREDICATE APEX GATE (all 9 must pass to hold 6★)       │
   ├────────────────────────────────────────────────────────────┤
   │   1. TM ≥ 250 (strict-evidence, no auto-mint)              │
   │   2. ≥ 3 distinct evidence types                           │
   │   3. ≥ 1 non-self-producible row                           │
   │   4. K = 2 cross-org cosigns from 4★+ Verifiers            │
   │   5. tenure ≥ 180 days from firstEvidenceAt                │
   │   6. no demote events in the last 6 months                 │
   │   7. system-wide cap = 5 apex slots filled                 │
   │   8. fusion components (if any) all graded ≥ C             │
   │   9. no provisional grade older than 6 months              │
   └────────────────────────────────────────────────────────────┘
```

At G7 cutover, both currently-6★ skills (`mattpocock/skills`, `ruvnet/ruflo`) demote to 5★ — they fail predicates 1, 4, or both under strict-evidence. The tier remains earnable. It is no longer earned. The system-wide 6★ count post-cutover: **0 of 5 slots filled.**

## V. The four-tier verification ladder (already shipped)

Every skill now sits on one of four verification tiers, computed by the CLI and shown on the skill report. This shipped with PR #709 (4-tier verification workflow) on 2026-06-16, before G7 ratification.

| Tier | What it means | Predicate |
|---|---|---|
| **community-verified** | At least one graded evidence row | `≥ 1 evidence with grade` |
| **benchmark-verified** | Has a leaderboard-attached benchmark result | `≥ 1 evidence of type benchmark-result` |
| **security-reviewed** | Clean defensive scan in last 90 days | `security_scan_passed within 90 days` |
| **enterprise-ready** | Aggregate Trust Grade ≥ A AND tenure ≥ 30 days | `OTG ≥ A AND tenure ≥ 30d` |

Tiers stack from the bottom — a benchmark-verified skill is also community-verified. The badge surfaces the highest tier passed. This is the floor. G7 builds the apex ceiling on top.

## VI. What did NOT change

The 2026-06-15 methodology stays the law of the land for everything below the skill aggregate.

- **Per-row Evidence Grades** — still S/A/B/C from the same per-row trust number on the 0–100 scale.
- **Evidence Types** — still the orthogonal "what kind of demonstration" axis (arxiv, repo, github-stars, benchmark-result, peer-review, etc.).
- **Inheritance** — a named skill's effective evidence is still its own ∪ its starless parent's. The starless parent's grade still floors the named child.
- **Star ranks** — 0★–6★ still describes maturity. G7 puts a programmatic ceiling on 6★; the other five tiers are unchanged.
- **Suite Ultimate Gate** — three pillars (≥3 evidenced components, ≥1 S, ≥2 A, no row below C). Unchanged.
- **Trust methodology page** — the 2026-06-15 report stands. G7 sits *on top* of it, not in place of it.

## VII. What a Verifier sees, before vs after G7

### Before (2026-06-15 methodology only)

```
   garrytan/gstack                            6 evidence rows
   ────────────────                           ─────────────────────
   Overall: A                                   1 × Platinum  (paper)
                                                3 × Gold      (repo)
                                                2 × Silver    (mention)
```

### After G7 cutover

```
   garrytan/gstack                            6 evidence rows
   ────────────────                           ─────────────────────
   Overall: A                                   1 × Platinum  (paper)      type: arxiv
   Trust Magnitude: 178                         3 × Gold      (repo)       type: github-stars-own
   Verification: enterprise-ready               2 × Silver    (mention)    type: external-cite
   Apex predicates passed: 4 of 9               
   ─────────────────────────                  Diversity types: 3
   Failed: cosign(K=2), tenure(180d),         Non-self-producible: 1
           apex-slot-vacancy(5/5),
           predicate-9                        ◯◯◯◯◯  apex slots filled (0 of 5)
```

The skill keeps its A. It is also clearly NOT apex-track. The Verifier reads the predicate checklist and knows what's missing.

## VIII. Migration shape

One PR, three commits, no big-bang.

```
   commit 1                  commit 2                   commit 3
   ────────                  ────────                   ────────
   schema + meta             CLI computation            backfill regrade
                                                        + apex cutover
   ─ verification.tier       ─ trust_magnitude()        ─ run regrade
     enum on schemas         ─ apex_gate(9 preds)         (strict-evidence)
   ─ TM thresholds           ─ anti_auto_mint            on all 220 skills
     in meta block             enforcement              ─ stamp meta-report
   ─ apex_slots: 5           ─ K=2 cosign tracking      ─ demote 2 skills
                             ─ 180d tenure base           from 6★ to 5★
                                                        ─ post stamp report
                                                          via gaia-post
```

No skill loses evidence in the migration. Some skills change grade (the regrade is mechanical from existing rows under strict-evidence). Two skills change rank.

## IX. Reading guide

If you are…

- **a contributor** opening a PR to add evidence — **nothing changes**. Same `gaia dev evidence`, same per-row grading.
- **a Verifier** reviewing a 4★+ skill — read the new predicate column on the report. Cosign with `gaia dev evidence --cosign-with` if you concur.
- **a Maintainer** of a currently-6★ skill — your skill demotes to 5★ at cutover. The 6-month grace window opens; if predicates 1–9 all clear before then, you re-promote.
- **a reader** comparing skills — you now have two numbers. The grade letter for "this evidence is strong" and the magnitude for "this skill clears the bar."

## X. References

[1] GAIA Registry. (2026-06-15). *The GAIA Trust Methodology: Evidence Types, Grades, and Inherited Standing*. `meta/reports/2026-06-15-the-gaia-trust-methodology-evidence-types-grades-and-inherited-standing.html`

[2] GAIA Registry. (2026-06-16). *G7 Trust Taxonomy RFC*. Ratified on `dev/orchestrator-phase1-closeout`, file `founder/handovers/G7_TRUST_TAXONOMY_RFC.md`. Sections cited: §0 (Executive Summary, headline thresholds), §4 (Overall Grade Thresholds and Diversity Gates), §10.11 (transitive-closure fusion-recipe origins), §10.12 (9-predicate hard apex gate), §10.13 (no grandfathering at G7 cutover), §10.14 (registry-wide anti-auto-mint clause), §11.12 (per-skill migration disposition table).

[3] GAIA Registry. (2026-06-16). *Benchmark Framework RFC* (PR #649, commit `0cbfc2fe`). `docs/architecture/benchmark-framework.md`. Lines 108–113 (score-to-grade mapping) and 188–196 (G7 §0 cross-reference).

[4] GAIA Registry. (2026-06-16). *4-tier verification workflow* (PR #709, commit `129ffd49`). `src/gaia_cli/verification.py`. Tiers: community-verified, benchmark-verified, security-reviewed, enterprise-ready.

[5] GAIA Registry. (2026-06-16). *Apex-tier audit workflow* (`wf_f14f7317-972`). 7 agents, 595k subagent tokens; caught the auto-mint inflation on `mattpocock/skills` and motivated the §10.14 clause.

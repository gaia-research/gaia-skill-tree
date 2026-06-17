# G7 — Trust Taxonomy & Magnitude Formula RFC

**Status:** Draft v2 — consensus output, awaiting Marco approval
**Date:** 2026-06-16
**Author:** Orchestrator agent

---

## The Gate (layman's view)

> Read this if nothing else. The RFC below is the legalese; this picture is the contract.

```
                ╔═══════════════════════════════════════════════════╗
                ║          ✦ 6★  APEX  —  THE GATE  ✦              ║
                ║      PR-gated · ≤5 system-wide · no auto-promote  ║
                ╠═══════════════════════════════════════════════════╣
                ║  Nine locks. Every one must open. By hand.        ║
                ║                                                   ║
                ║   ⚙  ≥12 nested origins (transitive suite tree)   ║
                ║   ⛓  ≥1 direct component is itself a suite         ║
                ║   ⤷  ≥1 grandchild reachable ONLY via nesting     ║
                ║   ◆  Grade S — no phantom rows allowed            ║
                ║   ✦  ≥8 A-graded skills in the closure            ║
                ║   ⚐  ≥2 cross-org 4★+ verifier cosigns            ║
                ║   ⏳  ≥180 days of evidence on the clock           ║
                ║   ⊛  apex-promotion PR + 2 verifier sign-offs     ║
                ║   #  system-wide cap respected (≤5)               ║
                ╚═══════════════════════════════════════════════════╝
                                      ▲
                                      │   (climb required)
                                      │
                ┌─────────────────────┴─────────────────────────────┐
                │  5★  TRANSCENDENT                                  │
                │  Overall Grade ≥ B   ·   rank-floor protects ≥ B  │
                │  Typically a suite Ultimate with real evidence    │
                └───────────────────────────────────────────────────┘
                                      ▲
                ┌─────────────────────┴─────────────────────────────┐
                │  4★  HARDENED                                      │
                │  ≥1 B-grade evidence row                          │
                │  Rank-floor blocks any sub-B drop without review  │
                └───────────────────────────────────────────────────┘
                                      ▲
                ┌─────────────────────┴─────────────────────────────┐
                │  3★  EVOLVED                                       │
                │  ≥1 B-grade evidence row                          │
                └───────────────────────────────────────────────────┘
                                      ▲
                ┌─────────────────────┴─────────────────────────────┐
                │  2★  NAMED                                         │
                │  ≥1 C-grade evidence row (any type)               │
                └───────────────────────────────────────────────────┘
                                      ▲
                ┌─────────────────────┴─────────────────────────────┐
                │  1★  AWAKENED                                      │
                │  Detected on a user tree by `gaia scan`           │
                └───────────────────────────────────────────────────┘
                                      ▲
                ┌─────────────────────┴─────────────────────────────┐
                │  0★  BASIC                                         │
                │  Exists in the canonical graph                    │
                └───────────────────────────────────────────────────┘
```

**The five things to remember:**

1. **Stars are earned by evidence, not by claim.** The number on the badge is the floor on what your evidence already supports.
2. **Grades stack; tiers don't.** A row at S anchors S; you can't average four C rows into a B.
3. **Phantom rows don't count.** If it's not in the skill's `evidence:` array, it contributes zero. (§10.14 — this rule applies registry-wide, not just at apex.)
4. **6★ is structurally rare.** Fewer than five at any moment, no auto-promote, two independent verifiers from two different GitHub orgs must sign a PR.
5. **Demotion is honest.** At G7 cutover, both standing 6★ skills demote to 5★ because they fail the new gate. Re-application is open immediately; the bar is just higher.

A standalone HTML rendering of this gate lives at `founder/handovers/G7_APEX_GATE.html` for sharing.

---

## §0 Executive Summary

This RFC replaces the legacy `trustNumber` aggregate with **Trust Magnitude** — an unbounded, set-bonus-driven score computed from a fixed taxonomy of ten evidence types. It is the output of the G7 consensus workflow (proposals P1–P4 → synthesis → Marco's ten finals + eight hard constraints). The structural base is P4 Community-Heavy, hardened with P1's verifier/star plateaus and identity-tier creator multipliers, and P3's only-graded-origins fusion counting and null-on-derank verifier rule.

**Headline number changes (revert to baseline; do not stack P4's three loosenings):**

| Grade | Min Trust Magnitude | Min distinct types |
|---|---|---|
| S | ≥ 250 | ≥ 3 (≥1 non-self-producible) |
| A | ≥ 100 | ≥ 1 |
| B | ≥ 50 | ≥ 1 |
| C | ≥ 20 | — |
| ungraded | < 20 | — |

**The eight mechanics introduced** (each detailed in §3–§7):

1. **Mothership discount, capped divisor** — stars from a parent suite repo divide by `min(skill_count_in_repo, 4)`. Same-product subdivision applies (`google/tensorflow` ≠ `google/jax`).
2. **Same-source dedup** — multiple evidence entries pointing at the same URL collapse to one.
3. **Fork-network canonicalization** — forks of the same repo share one star pool; opt-out via explicit `links.canonicalRepo`.
4. **Sqrt-softened fusion curve** — fusion-recipe magnitude grows linearly to ~10 origins, then `sqrt(origins)` thereafter.
5. **Only graded ≥ C origins count** toward fusion-recipe magnitude.
6. **Null-on-derank verifier** — when a 4★+ Verifier loses rank, attestations evaluate to `null` (not flagged, no decay). Reconciliation with hard-constraint #4 explained in §11.
7. **Provisional grade with 6-month grace** — skills failing diversity gate at migration get a `provisional` flag; demotion at end of grace is PR-gated, not automatic.
8. **Rank-floor sanity rule** — 4★+ skills cannot land below B without explicit review. **Blocks publish** at `gaia validate` time on the migration PR.

**Four post-audit additions (2026-06-16, from the 6★-tier audit):**

9. **§10.11 — Transitive-closure fusion-recipe origins** (REVERSES prior §11 Decision 7). Auto-mint walks `suiteComponents` recursively with skillId-dedup and cycle detection; graded≥C filter applies AFTER traversal; sqrt-softening on the post-filter count. Grade stacking allows a descendant's strongest grade (any evidence type, including descendant fusion-recipe) to bubble up to satisfy the parent's diversity gate.
10. **§10.12 — 9-predicate hard apex gate (§11.12)**. The 6★ tier requires simultaneous satisfaction of: ≥12 transitive graded≥C origins, ≥1 direct nested suite, ≥1 depth-2-only-reachable node, Overall Grade S under strict-evidence reading, ≥8 A-graded distinct closure members, ≥2 cross-org 4★+ verifier-attestations, ≥180-day tenure, PR-gated promotion (`apex-promotion` label + 2 verifier sign-offs), and a system-wide cap of ≤5 apex skills.
11. **§10.13 — No grandfathering at G7 cutover**. Every currently-6★ skill is re-evaluated; failures demote to 5★ in the migration PR. Both standing 6★ skills (`mattpocock/skills`, `ruvnet/ruflo`) demote at G7+0; system-wide 6★ count post-cutover = **0 of 5** slots filled.
12. **§10.14 — Registry-wide anti-auto-mint clause**. Only fusion-recipe is auto-derived (per §10.8). Every other evidence type must be physically present in the skill's `evidence:` frontmatter array to contribute to Trust Magnitude. Phantom rows do not count. Applies across all grades, not just apex.

**Migration is big-bang:** a single major PR re-grades all evidence under the new formula at merge time. Old entries are preserved verbatim; new artifact scores are computed in place. A stamp report (`docs/meta/JUN_2026_TRUST_REGRADE.md`) ships via the `gaia-post` skill (type=report, label="Meta-Shift", hero badge ON), **leading with the apex demotions** per Marco's 2026-06-16 call. No tenures, no rolling cutover. See §10 for the full migration plan and §10.4 for the rank-floor enforcement hook.

**Calibration impact** (sample; full table §9): `ruvnet/ruflo` 6★→5★ A *provisional* (apex demotion under §11.12), `mattpocock/skills` 6★→5★ A *provisional* (apex demotion under §11.12), `garrytan/gstack` B→S, `obra/superpowers` B→S, `garrytan/cso` stays B (mothership discount protects), `garrytan/benchmark` stays B (rank-floor rule protects 4★+), `obra/dispatching-parallel-agents` 4★→A (avoids 4★>5★ inversions), `agent-memory-learning` B→C (same-source dedup collapses identical-URL stars), `skill-mastery` synthesis A (3 repo-own rows fail diversity, not S). **System-wide 6★ count: 2 → 0** at G7 cutover.

---

## §1 Mental Model

**Trust Magnitude is a hero's equipment loadout, not a percentage.** Each piece of evidence is an **artifact** with its own **artifact score** (a per-evidence magnitude). A skill's Trust Magnitude is the sum of its artifact scores, with a **set bonus** for carrying artifacts of distinct types. A hero with one legendary sword and nothing else is not as trustworthy as a hero with a sword, a shield, a scroll, and a witness — even if the raw numbers tie.

This metaphor is load-bearing for three design choices:

**Per-evidence "artifact score" framing.** Every evidence row computes its own magnitude via the type's formula (§3), independent of the parent skill. This makes evidence portable (the same `arxiv` row contributes the same score wherever it's attached), auditable (every row has a pre-aggregation number), and decay-aware (freshness is per-artifact, not per-skill). Naming is final per hard-constraint #5: **"Trust Magnitude"** for the skill aggregate, **"artifact score"** for the per-evidence value. `trustNumber` is retired.

**Set-bonus diversity, enforced by gate.** The diversity gate (§7) is not a tiebreaker — it is a **hard requirement** at S and a soft requirement everywhere else. S demands ≥3 distinct evidence types *and* at least one **non-self-producible** type (anything that isn't `fusion-recipe`, `self-attestation`, or `repo-own` — the three artifacts a contributor can mint without external signal). A contributor cannot solo-grind to S by stacking their own commits, their own fusion recipes, and their own attestations. They need someone or something outside themselves to vouch: stars, verifiers, citations, benchmarks, peer review, social engagement, or proxy containment. This is what makes Trust Magnitude *trust* and not *output*.

**Unbounded with soft-cap 500, not 0–100 percentage.** Percentages compress the top end and force ratio thinking ("this skill is 80% trustworthy") that the data does not support. An unbounded scalar with a soft cap of ~500 (where realistic top-tier skills land — `gstack`, `superpowers`, `ruflo` cluster in the 250–450 range under the new formula) preserves *headroom* for future S-tier evidence types and avoids the legacy bug where a 5-origin fusion and a 50-origin fusion both saturated at 100. The grade thresholds (250 / 100 / 50 / 20) are anchored to evidence-class realities, not to percentiles. Per-type caps (§3) are local — `social-signal` caps at 80 (A-cap, hard-constraint #7), `arxiv` at 100 (A-cap), `repo-own` at 60 (B-cap) — but the aggregate has no ceiling. A truly extraordinary skill can score 800; the formula will not lie about it.

**Why this beats the legacy `trustNumber`.** `trustNumber` was a single opaque float with no audit trail, no diversity awareness, and no way to distinguish a fusion capstone from a pile of self-commits. Trust Magnitude is an additive ledger of artifacts, each with its own score, weight, freshness, and cap; the aggregate is a pure function of the ledger plus the set-bonus gate. Every grade is reproducible from evidence alone. Every appeal is a row-level argument, not a vibes-level argument.

## §2 Evidence Taxonomy

Trust Magnitude is the sum of ten evidence types, each with its own magnitude formula, weight, freshness rule, cap, and grade ceiling. The taxonomy is closed: anything that does not fit one of these ten types does not count. New types require an RFC. Per-evidence output is the **artifact score** (magnitude × weight × freshness); the skill-level sum is the **Trust Magnitude** (see §1, §5).

The ten types fall into three families:

| Family | Types | What it proves |
|---|---|---|
| **Synthesis** | fusion-recipe | Skill emerges from composition of graded prior work |
| **External adoption** | github-stars-own, proxy-containment, verifier-attestation, benchmark-result, arxiv, peer-review, social-signal | Someone outside the contributor signed off |
| **Contributor-minted** | repo-own, self-attestation | Contributor produced artifacts without external signal |

The diversity gate (§4) keeps contributor-minted types from reaching S or A on their own — non-self-producible signal is required at the top.

### 2.1 Master table

| Type | Magnitude | Weight | Freshness | Cap | Grade ceiling |
|---|---|---|---|---|---|
| fusion-recipe | `20 × origins` (sqrt-softened past 10) | 1.5 | 1.0 (intrinsic) | softened | S @ ≥5 graded≥C origins |
| github-stars-own | `stars / 1000` (mothership-discounted) | 1.0 | refresh quarterly | 200 | S @ 100k+ |
| proxy-containment | `(external_stars / 1000) × 0.8` | 1.0 | quarterly | 160 | S @ 125k+ |
| verifier-attestation | `30 × verifiers (4★+)` | 1.5 | null on derank | — | S @ 3+ verifiers |
| benchmark-result | percentile (0–100) | 1.4 | 50%/year | 100 | S @ 95th+ |
| arxiv | `citations / 5` | 1.0 | quarterly | 100 | A |
| peer-review | `25 × reviewers (4★+)` | 1.2 | 25%/2yr | — | A |
| repo-own | `commits/200 + contributors² × 2` | 0.6 | quarterly | 60 | B |
| self-attestation | flat 10 (1 entry max) | 0.5 | static | 10 | C |
| social-signal | `log10(views) × 8 × creator_mult × engagement_ratio` | 1.0 | 50%/year | 80 | A (hard cap) |

Weights cluster at 1.0. The two outliers above (1.4–1.5) are evidence that is hard to fabricate and easy to verify: a percentile rank on a public benchmark, a 4★ Verifier signature, a fusion graph whose origins must already be graded. The two outliers below (0.5–0.6) are evidence the contributor produces unilaterally — they earn placement on the grade scale but cannot anchor a high grade alone.

### 2.2 fusion-recipe (synthesis)

The only intrinsic-evidence type. Every fused or Ultimate skill auto-gets exactly one fusion-recipe entry whose origins are its `suiteComponents` (transitive prerequisites are not counted — Marco decision #7). Magnitude:

```
m = 20 × origins                          for origins ≤ 10
m = 200 + 20 × sqrt(origins - 10)         for origins > 10
```

Sqrt-softening past 10 origins prevents pathological 35-component fusions (e.g. `ruvnet/ruflo`) from running away with a 700+ raw magnitude that drowns out every other signal — the cap kicks in around `m ≈ 300` for very large fusions. Only origins graded ≥C count toward the origin tally (P3 graft; ungraded suiteComponents are silent placeholders). Weight 1.5 because a fusion-recipe is structurally verifiable: each origin has its own evidence trail, so the grader is checking arithmetic, not vibes.

Fusion-recipe is **mandatory** for any fused or Ultimate skill (Marco hard-constraint #2 and #8). A skill with `suiteComponents` and no fusion-recipe entry fails validation regardless of Trust Magnitude.

### 2.3 github-stars-own (own-repo adoption)

```
m = min(200, stars / 1000) / mothership_divisor
mothership_divisor = min(skill_count_in_repo, 4)
```

A 4★+ artifact at 100k stars hits the 200 cap; a typical 5k-star utility lands around 5. The **mothership discount** divides magnitude when the parent suite repo is the source — e.g. `garrytan/gstack` with 12 component skills divides by `min(12,4) = 4`. Without the cap on the divisor, megasuites would crater every component to triviality; the cap-at-4 keeps suite-resident skills meaningfully evidenced.

Same-source dedup (§3) collapses multiple github-stars-own entries pointing at the same repo URL to one. Forks of the canonical repo collapse into the same star pool unless the fork's evidence entry sets `links.canonicalRepo` explicitly (Marco decision #5). Weight 1.0 — adoption is real signal but the metric is gameable enough at the low end (bot stars, cross-promotion) that we don't lean on it the way we lean on benchmarks or verifier signatures.

Same-product subdivision: `google/tensorflow` and `google/jax` are not the same mothership for divisor purposes; two repos must share a package-name root or declared product field to be subdivided together (Marco decision #6).

### 2.4 proxy-containment (downstream adoption)

A proxy-containment entry asserts that the skill's artifact is bundled inside a separately-starred external project. Magnitude:

```
m = min(160, (external_stars / 1000) × 0.8)
```

Sub-rules (Marco hard-constraint #3):

| Rule | Value |
|---|---|
| Max entries per skill | 3 |
| Plateau on entries | 1.0× / 0.5× / 0.25× |
| External-star floor | 10,000 stars |
| Same-source dedup | yes (per §3) |

The 0.8 magnitude multiplier and 160 cap (vs github-stars-own's 200) reflect that downstream adoption is one inferential hop away from direct adoption. The 10k-star floor exists because below that, "containment" is statistically indistinguishable from one developer copying a file into a side project.

**Interim unverified-flag policy** (Marco decision #2): until the proxy-containment validator ships, claims count at FULL magnitude with an explicit `"unverified": true` flag on the evidence entry. We are lenient on magnitude and loud on provenance — the flag is surfaced in `gaia evidence` listings and audit reports. The validator becomes its own follow-up issue once the contributor base outgrows the current we-trust-each-other regime.

### 2.5 verifier-attestation (peer signature)

A 4★+ Verifier (defined per §6 — GitHub org membership for cluster purposes, Marco decision #1) signs an attestation that the skill is real and graded fairly. Magnitude:

```
m = 30 × verifiers
```

No cap on verifier count, but diversity gate caps at 3 verifiers for S placement. Weight 1.5: a 4★ Verifier has skin in the game (their own attestations get re-evaluated when they derank).

**Null-on-derank** (Marco hard-constraint #4, P3 graft): when a Verifier loses 4★ rank, every attestation they have signed evaluates to null — not zero, not flagged, null. The skill's Trust Magnitude is recomputed without those entries. This is stricter than the original "flag on derank" rule; the reconciliation is documented in §11. Rationale: a signature from someone who can no longer carry the rank should not be propping up grades, and silently flagging it means stale evidence accumulates faster than auditors can keep up.

Verifier-attestation has no time decay while the verifier holds rank — fresh and 18-month-old signatures evaluate identically. Decay would force re-attestation churn without adding signal.

### 2.6 benchmark-result (objective performance)

A reproducible benchmark on a public dataset, scored as percentile rank within the field:

```
m = percentile  (0..100, cap at 100)
```

Weight 1.4 because percentiles are externally verifiable and hard to forge — but only at 1.4 (not 1.5) because benchmark choice can itself be cherry-picked. Freshness halves yearly: a 95th-percentile result from 2024 is worth ~24 magnitude in mid-2026, reflecting that benchmark frontiers move. S-capable at 95th+ percentile.

### 2.7 arxiv (academic citation count)

```
m = min(100, citations / 5)
```

Weight 1.0, quarterly refresh, A-cap. Citation count is a slow-moving lagging indicator; the A-cap exists because high citation counts cluster around survey papers and methods, not around the kind of executable skill the registry tracks. A 500-citation paper hits the cap (m=100) but cannot reach S without complementary evidence types.

### 2.8 peer-review (4★+ reviewer signoff)

```
m = 25 × reviewers
```

Distinct from verifier-attestation: peer-review is a structured walkthrough with written critique attached, not a signature on the existing artifact. Weight 1.2, decay 25%/2yr (slower than benchmarks because the review document itself remains valid evidence even as the skill evolves). A-cap — peer-review without external adoption signals (stars, benchmarks, verifiers) doesn't justify S because the reviewers and the contributor are inside the same loop.

### 2.9 repo-own (contributor-minted: artifact volume)

```
m = min(60, commits/200 + contributors² × 2)
```

Weight 0.6, B-cap. A long-lived repo with 200+ commits and 5 contributors hits roughly `commits/200 + 50 = ~52`. The contributor-squared term rewards genuine collaboration over solo grinding. The cap at 60 and weight 0.6 together ensure that no amount of repo-own evidence can carry a skill past B alone — the diversity gate (§4) classes repo-own as a self-producible type, so an A or S grade requires non-self-producible evidence on top.

### 2.10 self-attestation (contributor-minted: declaration)

Flat 10 magnitude, weight 0.5, max one entry per skill, C-cap. A skill with only self-attestation evidence reaches `10 × 0.5 = 5` artifact score and lands ungraded. Self-attestation exists so that newly-added skills aren't penalized for having no external trail yet — it's a placeholder, not a claim.

### 2.11 social-signal (creator/audience evidence)

The most rule-heavy type. Designed to count genuine topical authority while neutralizing self-promotion and view farming. Hard A-cap (Marco hard-constraint #7) — social-signal alone cannot reach S regardless of stack.

```
m = log10(views) × 8 × creator_mult × engagement_ratio
engagement_ratio = min(1.5, (likes + comments × 5) / views × 50)
```

Weight 1.0, freshness 50%/year, magnitude cap 80.

#### 2.11.1 Creator multiplier (identity tier)

| Tier | Multiplier | Definition |
|---|---|---|
| Same-as-author | 0× | Content creator is the skill contributor — rejected outright |
| Anonymous | 0.3× | No verifiable identity behind the channel |
| Established | 0.6× | Verifiable persistent identity, no domain claim |
| Topical authority | 1.0× | Demonstrated history in the skill's domain |
| Recognized voice | 1.2× | Topical authority + ≥2 cross-org Verifier co-signs |
| Reserved | 1.4× | Reserved for future use (e.g. institutional broadcast tier — requires future RFC; not currently activatable) |

Recognized-voice (1.2×) requires two Verifier co-signs from distinct GitHub orgs (Marco decision #3). A new CLI flag `gaia dev evidence --cosign-with <verifier>` records co-signs; both must resolve to 4★+ Verifiers in distinct orgs at evaluation time.

#### 2.11.2 Engagement ratio

```
engagement_ratio = min(1.5, (likes + comments × 5) / views × 50)
```

Comments weight 5× likes because a comment is a higher-effort engagement signal. The `× 50 / views` term normalizes to a ratio centered roughly on 1.0 for healthy engagement; the `min(1.5, ...)` cap prevents tiny-audience high-engagement videos (1k views, 200 comments) from inflating beyond reasonable bounds. A piece with 100k views, 5k likes, 500 comments scores `engagement_ratio = min(1.5, (5000 + 2500) / 100000 × 50) = min(1.5, 3.75) = 1.5`.

#### 2.11.3 Anti-gaming sub-rules

| Rule | Behavior |
|---|---|
| Plateau on multiple entries | 1.0× / 0.5× / 0.25× (max 3 entries per skill) |
| Same-creator dedup | 2nd entry from same creator at 0.5×, 3rd at 0.25×, regardless of slot |
| 30-day publish cooldown | Content published <30 days before evidence creation date is held until cooldown expires |
| Cross-platform same-content | One YouTube + Twitter + LinkedIn post of the same talk = ONE entry (highest-magnitude platform wins) |
| Self-promotion | creator_multiplier 0× → automatic rejection |
| View-floor | `views < 1000` → ungraded (entry stored, magnitude 0) |

The view-floor is the P1 graft: below 1k views, log10 noise dominates signal, and accepting low-view content opens the door to private-link audiences and bot-driven view farming. The 30-day cooldown closes a related loophole — content goes up, evidence gets minted day-of, magnitude locks in before the audience even forms.

### 2.12 Cross-cutting rules

The same-source dedup, fork-network canonicalization, and mothership-discount-with-capped-divisor mechanics apply across types per §3. Freshness rules (2.13) compose with weights and caps:

```
artifact_score = magnitude × weight × freshness_factor
```

`freshness_factor` is 1.0 unless the type's row above defines decay; null-on-derank short-circuits to a null artifact score for verifier-attestation entries whose signer has lost rank.

### 2.13 Why these caps and weights

The numbers above are calibrated against three constraints:

1. **No single evidence type can carry an S grade alone except fusion-recipe at high origin counts and github-stars-own at 100k+ stars.** The diversity gate (§4) enforces this structurally, but the per-type caps make it true even before the gate runs.
2. **Contributor-minted evidence (repo-own + self-attestation + fusion-recipe) cannot exceed `60 × 0.6 + 10 × 0.5 + sqrt-softened-fusion ≈ 250` without external types.** This is the math behind the diversity gate's "≥1 non-self-producible type" rule for A and S.
3. **Headline grade thresholds (S=250, A=100, B=50, C=20)** stay at baseline so the three loosenings in P4 — view-floor, identity-tier creator multipliers, only-graded-origins counting — don't compound into grade inflation. See §5 for the full calibration walkthrough.

## §3 Aggregation

### Trust Magnitude formula

Trust Magnitude (`TM`) is the per-skill aggregate over all evidence entries attached to that skill, after per-evidence normalization, freshness, weight, plateau, and dedup.

```
TM(skill) = Σ over evidence e in skill:
              artifact_score(e)
              × type_weight(e.type)
              × freshness(e)
              × plateau_factor(e, skill)
              × creator_mult(e)         # social-signal only; 1.0 elsewhere
              × engagement_ratio(e)     # social-signal only; 1.0 elsewhere
              × mothership_discount(e)  # github-stars-own only; 1.0 elsewhere

  subject to:
    - same-source dedup (collapse identical URLs to one entry)            §2.3
    - fork-network canonicalization (forks of same upstream → one pool)   §2.4
    - per-type magnitude caps (see §2 type table)
    - social-signal hard A-cap: contribution to TM never exceeds 80
    - fusion-recipe origins counted only if origin grade ≥ C              §2.5
```

`artifact_score(e)` is the raw per-evidence number from the §2 type table (e.g. `stars/1000`, `30 × verifiers`, `20 × origins` with sqrt-softening past 10). It is the only field a per-evidence row carries; per-evidence "artifact tier" (S/A/B/C-capable) is a property of the **type**, not the evidence row, and gates the overall grade through the diversity rule in §4 — not through the sum.

### Sum semantics

`TM` is unbounded. The display layer soft-caps to 500 (`min(TM, 500)` shown in tree UI, badges, and `gaia tree`), but the raw value is what `gaia validate` and the diversity gate consume. Skills above 500 keep their full magnitude internally; the cap is purely visual to keep badge layouts sane and prevent leaderboards from being dominated by one mega-fusion. When a skill exceeds 500, the tree renders `500+` with the true value in the tooltip.

Within a single type, multiple entries collapse before plateau:

1. **Same-source dedup** — entries with identical canonical URL (after `tree/`→`blob/` normalization and fork canonicalization) merge into one. Highest-magnitude metadata wins; all source URLs preserved on the merged entry.
2. **Plateau** — for types that allow stacked entries (proxy-containment, social-signal, peer-review), the 2nd entry contributes at 0.5×, the 3rd at 0.25×, and 4th+ are dropped. Plateau applies after dedup, before `type_weight`.
3. **Type cap** — sum within a type is then clipped to the per-type cap (e.g. github-stars-own caps at 200).

Across types, contributions are additive with no cross-type cap other than the social-signal hard A-cap (`min(social_total, 80)` before adding to `TM`).

### Per-evidence artifact tier vs. overall grade

The S/A/B/C-capable column in §2 is a **type ceiling**, not a per-row grade. It says "this type of evidence can, on its own, qualify a skill for that overall tier under §4's diversity rules." Concretely:

| Artifact tier (type ceiling) | Effect |
|---|---|
| S-capable | Type counts toward §4's "≥1 S-tier evidence" plus-rule |
| A-cap | Type counts toward "≥3 A-tier of distinct types" plus-rule but never the S-tier rule |
| B-cap | Counts only as a distinct type for B-grade and below |
| C-cap | Counts only as a distinct type for C-grade |

A row's `artifact_score` flowing into `TM` is independent of its tier — a B-cap `repo-own` entry contributes its full magnitude to `TM`. The tier only governs whether that row helps clear §4's diversity plus-rules.

### Freshness multipliers

Freshness is per-type and applied as a multiplier in `[0, 1]` based on `evidence.lastVerified` (ISO 8601, UTC).

```
freshness(e) = max(0, 1 - decay_rate(e.type) × age_years)

  where age_years = (now - e.lastVerified) / 365.25 days
```

| Type | Decay | Refresh expectation | Notes |
|---|---|---|---|
| fusion-recipe | 0 (intrinsic) | never | derived from suiteComponents at evaluation time |
| github-stars-own | re-fetch quarterly; no decay | ≤ 90 days | `gaia refresh-stars` re-stamps `lastVerified` |
| proxy-containment | re-fetch quarterly; no decay | ≤ 90 days | same refresh path as stars |
| verifier-attestation | **null on derank** (per §10.4) | — | not a decay; evaluates to `null` if attesting Verifier drops below 4★, removing the row from `TM` |
| benchmark-result | 50%/year | annual re-run | half-life ≈ 1 year |
| arxiv | re-fetch quarterly; no decay | ≤ 90 days | citation count refreshed |
| peer-review | 25%/2yr | re-attest every 2yr | linear decay |
| repo-own | re-fetch quarterly; no decay | ≤ 90 days | commits/contributors refreshed |
| self-attestation | static | — | flat 10, never decays, max 1 |
| social-signal | 50%/year | annual review | half-life ≈ 1 year |

Stale rows past their refresh expectation are flagged by `gaia validate` with `freshness-stale` (warning, not blocker) until decay reduces them below their type cap. A row whose freshness multiplier reaches 0 is dropped from `TM` entirely; the entry is preserved in the registry for audit.

The verifier null-on-derank rule (§10.4) reconciles with hard-constraint #4 ("flag on derank, NO decay") by treating null-on-derank as **erasure**, not decay — the row is removed from the sum, the Verifier's attestation history is preserved for audit, and the skill's grade is recomputed at next `gaia validate`. This is stricter than flag-only but avoids the original concern (decay penalizing skills for events outside their control): an erased row is a clean removal, not a half-life crawl toward zero.

---

## §4 Overall Grade Thresholds & Diversity Gates

### Final thresholds

| Grade | Min `TM` | Min distinct types | Plus-rule |
|---|---|---|---|
| S | ≥ 250 | ≥ 3 | ≥1 S-capable type present **OR** ≥3 A-capable types of distinct kinds; **AND** ≥1 non-self-producible type |
| A | ≥ 100 | ≥ 1 | ≥1 A-capable type present (pure github-stars-own at A is valid per hard-constraint #1) |
| B | ≥ 50 | ≥ 1 | ≥1 B-capable type or higher |
| C | ≥ 20 | — | — |
| ungraded | < 20 | — | — |

Distinct-type counts are taken **after** dedup and plateau but **before** type caps — a skill with three github-stars-own rows that all dedup to one source counts as one type, not three.

### Non-self-producible rule

A contributor must not be able to mint S alone. The three self-producible types are:

- `fusion-recipe` — derived from the contributor's own `suiteComponents`
- `self-attestation` — flat 10, the contributor writes it
- `repo-own` — commits and contributor count in the contributor's own repo

S requires ≥1 evidence row of any **other** type: `github-stars-own` (external stars), `proxy-containment` (external repo containing the skill), `verifier-attestation` (4★+ third party), `benchmark-result` (independent benchmark), `arxiv` (cited paper), `peer-review` (external reviewers), or `social-signal` (external audience). This binds S to signal that originated outside the contributor's own keystrokes.

A grade does **not** require this — pure-stars and pure-fusion paths are both legal at A. But the moment a skill claims S, at least one row of independently-produced evidence must be present.

**Verifier-attestation cap for S diversity.** Per §2.5, verifier-attestation has no cap on raw verifier count for magnitude purposes, but for diversity-gate accounting at S, only the first 3 verifiers count as a single distinct type — additional verifiers add magnitude but do not multiply diversity. A skill cannot satisfy the "≥3 distinct types" rule by stacking 3 verifier-attestation rows; verifier-attestation collapses to one type slot regardless of how many signers are attached.

### Rank-floor sanity rule

Per Marco's hard decision #10, any skill whose user-tree rank is 4★+ cannot land below B. `gaia validate` raises `rank-floor-violation` as a **publish blocker** (not a warning) on the migration PR if a 4★+ skill computes to C or ungraded. Manual override requires the PR-gated review path from decision #4 — a maintainer adds the `rank-floor-override` label and writes the justification in the PR body.

### Provisional-grade flag

Skills failing the diversity gate immediately after the migration cutover (§10.6 big-bang re-grade) are stamped **provisional** at their target grade with a 6-month grace window. Provisional skills render with a `provisional` badge in the tree and a `gradeExpiresAt` timestamp on the registry node. End of grace → PR-gated review (decision #4): either evidence has been added to clear the gate, or the skill is demoted by manual PR. No automated demotion.

### Worked examples

**1. ruvnet/ruflo (Ultimate, fusion-led, post-synthesis S)**

```
fusion-recipe:        35 origins, 19 graded≥C
                      200 + 20 × sqrt(19-10) = 200 + 60 = 260 × weight 1.5 = 390.0
github-stars-own:     ~4.2k stars / 1000 = 4.2 × weight 1.0    =   4.2
repo-own:             commits + contributors² × 2 ≈ 22 × 0.6   =  13.0
self-attestation:     flat 10 × weight 0.5                     =   5.0
                                                        TM ≈ 412.2
distinct types: 4 (fusion-recipe, github-stars-own, repo-own, self-attestation)
S plus-rule: ≥1 S-capable (fusion-recipe @ 5+ graded origins ✓)
non-self-producible: github-stars-own ✓
                                                  Grade = S
```

**2. mattpocock/skills (suite root, post-synthesis A PROVISIONAL)**

```
fusion-recipe:        8 suiteComponents, 4 graded≥C
                      20 × 4 origins × weight 1.5         = 120.0
github-stars-own:     ~1.1k stars, mothership divisor=4
                      (1.1)/4 = 0.275 × weight 1.0        =   0.3
repo-own:             ~14 × weight 0.6                    =   8.4
self-attestation:     10 × weight 0.5                     =   5.0
                                                        TM ≈ 133.7
distinct types: 4 (fusion-recipe, github-stars-own, repo-own, self-attestation)
S diversity check: only github-stars-own is non-self-producible AND it sits below
  meaningful threshold — diversity gate FAILS for S
A plus-rule: fusion-recipe is S-capable (which subsumes A) ✓
                                          Grade = A PROVISIONAL (6-month grace)
```

`TM` lands in A band; the diversity gate denies S because the only non-self-producible row (mothership-discounted stars) is too thin to anchor an S claim. Provisional flag set; if a peer-review or external benchmark lands within 6 months, S unlocks. Otherwise PR-gated review at end of grace.

**3. obra/superpowers (community-heavy, fusion-led S)**

```
fusion-recipe:        11 suiteComponents, 5 graded≥C
                      20 × 5 origins × weight 1.5             = 150.0
verifier-attestation: 30 × 3 verifiers (cross-org) × 1.5      = 135.0
github-stars-own:     ~2k stars / 1000 = 2.0 × weight 1.0     =   2.0
                                                        TM ≈ 287.0
distinct types: 3 (fusion-recipe, verifier-attestation, github-stars-own)
S threshold: TM 287 ≥ 250 ✓
S plus-rule: ≥1 S-capable (verifier-attestation @ 3+ ✓; fusion-recipe S-capable)
non-self-producible: verifier-attestation, github-stars-own ✓
                                                  Grade = S
```

Clears the 250 threshold via the verifier-attestation stack, with three distinct types and two non-self-producible rows. Synthesis upgrades the migration call from B to S (per §9 calibration table).

**4. garrytan/cso (mothership-discounted, B holds)**

```
github-stars-own:     stars/1000 ÷ min(skill_count_in_repo=11, 4) = 4.0 / 4 = 1.0 × weight 1.0 = 1.0
fusion-recipe:        20 × 2 graded≥C origins × weight 1.5 = 60.0
self-attestation:     10 × weight 0.5                     =  5.0
repo-own:             ~20 × weight 0.6                    = 12.0
                                                        TM = 78.0
distinct types: 4
B plus-rule: ≥1 B-capable type or higher ✓ (repo-own; fusion-recipe S-capable)
                                                  Grade = B
```

Mothership discount with capped divisor (decision §2 mechanic 1) cuts gstack-suite stars cleanly. With only 2 graded≥C origins the fusion-recipe stays modest, and the suite-leaf lands at B — matching §9 calibration. Earlier P4 also gave B; the canonical formula confirms the call.

**5. Pure-stars S-attempt that fails diversity (e.g. a hypothetical 250k-star single-skill repo with nothing else)**

```
github-stars-own:     250000/1000 = 250, capped at 200 × weight 1.0 = 200
                                                        TM = 200
distinct types: 1
S threshold: TM 200 < 250 ✗
A plus-rule: ≥1 A-capable type ✓ (github-stars-own is S-capable, subsumes A)
                                                  Grade = A
```

Hard-constraint #1 honored: pure github-stars CAN reach A (it does — 200 > 100). It cannot reach S via stars alone because (a) the cap holds `TM` at 200 < 250, and (b) only one distinct type is present, failing the ≥3 minimum. Adding a verifier-attestation (`+45`) and a benchmark-result (`+e.g. 80`) would push to `TM ≈ 325` with three types, two of them non-self-producible — and the skill clears S legitimately.

## §5 Defensive Mechanics

The grading formula (see §3) is exposed to eight gameability vectors. Each mechanic below closes one. They are not independently tunable knobs — they form a single defensive lattice, and removing any one re-opens a vector that was demonstrated during the synthesis bake-off (see §4).

### 5.1 Mothership discount (capped divisor + same-product subdivision)

When a `github-stars-own` entry is sourced from a parent suite repo whose stars are shared across many skills, raw `stars/1000` over-credits each component. The mothership discount divides the per-skill share by the number of co-located skills, capped at 4 to preserve calibration for genuinely large suites:

```
effective_magnitude = (stars / 1000) / min(skill_count_in_repo, 4)
```

Per Marco #6, "same parent org" is **not** sufficient grouping — the discount applies only when skills share a **product**, detected via shared package-name root or shared declared `product` field. `google/tensorflow` and `google/jax` are independent products and do not pool; `garrytan/gstack` and its components do. This protects `garrytan/cso` and similar suite-leaf skills from the divisor while still containing `mattpocock/skills`-shaped sprawl.

### 5.2 Same-source dedup

Multiple evidence entries pointing at the same canonical URL collapse to one. Canonicalization strips fragments, trailing slashes, and `tree/`→`blob/` normalization (consistent with the installer in §2). This was the single largest correction in the synthesis pass: `agent-memory-learning` dropped B→C purely because three of its four entries resolved to the same blog post.

### 5.3 Fork-network canonicalization (with explicit opt-out)

Forks of the same upstream repo count as one star pool. The default behavior — canonicalize to upstream — is correct for the >95% case where forks are personal mirrors. Per Marco #5, legitimately divergent forks may opt out by setting `links.canonicalRepo` on the evidence entry; the orchestrator's call carries. There is no automated divergence detector. Curators flag opt-outs in PR review.

### 5.4 Sqrt-softened fusion curve

`fusion-recipe` magnitude is `20 × origins` up to 10 origins, then softens:

```
if origins <= 10:
    magnitude = 20 * origins
else:
    magnitude = 200 + 20 * sqrt(origins - 10)
```

The kink at 10 is intentional — below it, each new origin is meaningful curation work; above it, the marginal origin is mostly schema padding. Without softening, `ruvnet/ruflo` (35 components) would dominate the entire S tier. With it, `ruflo` lands at S but does not crowd out `obra/superpowers` (11 origins) or `garrytan/gstack` (suite root).

### 5.5 Only graded≥C origins count

`fusion-recipe` magnitude counts only origins whose own grade is C or higher. Ungraded origins contribute zero. This eliminates the "fuse 30 stubs into an Ultimate" attack: a fusion-recipe whose origins are themselves unsubstantiated produces an unsubstantiated capstone. Combined with the hard requirement that Ultimates carry a fusion-recipe (constraint #2, §1), this means Ultimate status now requires a substrate of at least five graded skills — not just five named ones.

### 5.6 Null-on-derank verifier (reconciliation with hard-constraint #4)

When a 4★+ Verifier loses rank, every `verifier-attestation` they issued evaluates to **null**, not flagged. This is a deliberate strengthening of constraint #4 ("flag on derank, NO decay"). The synthesis pass demonstrated that flag-without-effect is a no-op: a flagged-but-counted attestation is gameable by any verifier who plans to derank (or be deranked) before the next quarterly batch. Null evaluation closes that vector while preserving the no-decay property for verifiers in good standing — their attestations remain at full weight indefinitely. Reconciliation rule: the **flag** from constraint #4 is still written to the evidence entry for audit, but the **magnitude contribution** is null. This is the only case in the spec where a flag and a magnitude diverge, and it is intentional.

### 5.7 Provisional grade with 6-month grace

Skills that pass the magnitude threshold for a grade but fail the diversity gate (see §3.4) at migration time receive that grade with a `provisional` flag and a 6-month grace window. During grace, the skill is graded at its provisional level for all consumer-facing surfaces (tree, badges, install). At end-of-grace, per Marco #4, demotion is **PR-gated** — not automated. A curator opens a PR explicitly demoting the skill; the migration record carries the original grade, the provisional grant date, and the demotion rationale.

`mattpocock/skills` is the canonical example: A PROVISIONAL at migration, needs at least one non-self-producible evidence type to confirm A by 2026-12-16, otherwise demoted to B by curator PR.

### 5.8 Rank-floor sanity rule (BLOCKS PUBLISH)

Per Marco #10, a skill held at 4★ or higher in any user tree cannot land below grade B in the registry without explicit review. This is enforced as a `gaia validate` failure on the migration PR and on every quarterly rerank PR. The check is a hard block — `skip-meta-guard` does not bypass it. Manual override requires PR-gated review (per §5.7's appeal mechanism).

The rule exists because user trees encode lived calibration: a skill that multiple contributors have ranked up to 4★ has accumulated evidence the registry hasn't yet captured. A C-or-below registry grade for such a skill is almost certainly a registry gap, not a calibration result. `garrytan/benchmark` (held at 4★ by two contributors, raw magnitude 47) trips this rule and is held at B pending evidence backfill rather than dropped to C.

### 5.9 Mechanic interaction summary

| Vector | Mechanic | Section |
|---|---|---|
| Suite-repo over-credit | 5.1 mothership discount | §5.1 |
| Same-URL evidence stuffing | 5.2 same-source dedup | §5.2 |
| Fork farms | 5.3 fork-network canonicalization | §5.3 |
| Origin padding | 5.4 sqrt softening | §5.4 |
| Stub fusion attack | 5.5 graded≥C origins | §5.5 |
| Verifier derank gaming | 5.6 null evaluation | §5.6 |
| Migration cliff | 5.7 provisional grace | §5.7 |
| User-tree / registry drift | 5.8 rank floor | §5.8 |

The mechanics compose: `mattpocock/skills` is touched by 5.1 (suite root, divisor capped at 4), 5.7 (provisional A at migration), and 5.8 (4★ holdings keep it above B-floor regardless). Removing any single mechanic re-opens at least one vector for at least one calibration anchor.

---

## §6 Reranking Cadence

Trust grades are not static. Evidence ages, verifiers derank, fusions accrete origins, and benchmarks get displaced by new state-of-the-art. The cadence below balances responsiveness (a new high-quality evidence entry should move the grade quickly) against churn (a grade should not flicker on every star count refresh).

### 6.1 Hybrid model: event-driven + quarterly batch

Two reranking paths run in parallel.

**Event-driven (per-skill).** Every `evidence_added` or `evidence_graded` mutation triggers a recompute of the affected skill only. This is implemented as a post-commit hook in `gaia dev evidence` and `gaia dev reclassify`. The recompute is local — it touches one skill's `trustMagnitude` and `grade` fields and writes a single timeline event (`action: rerank`, with delta in `details`). Cost: ~50ms per skill; runs synchronously inside the CLI command.

**Quarterly batch (full registry).** Every 90 days, a full registry rerank runs:

```
gaia dev rerank --all --stamp-report
```

This recomputes every skill (including stale freshness decays per the table in §3.2), refreshes `github-stars-own` magnitudes from the GitHub API, refreshes `arxiv` citation counts, applies the 50%/year decay to `social-signal` and `benchmark-result`, and emits a stamp report under `docs/meta/<MONTH>_<YEAR>_TRUST_RERANK.md`. The June 2026 migration (Marco #9) is the first such report, structurally; subsequent batches follow the same template.

The split is principled: event-driven catches the cases where a contributor expects immediate feedback (they just added evidence; the grade should update). Quarterly catches the cases that need global state (fork-network canonicalization across the full graph, freshness decays, mothership-divisor recomputes when a new co-located skill lands).

### 6.2 Trigger matrix

| Trigger | Path | Latency | Stamp report? |
|---|---|---|---|
| `gaia dev evidence` (add) | event-driven | sync, ~50ms | no |
| `gaia dev evidence` (rm) | event-driven | sync, ~50ms | no |
| `gaia dev reclassify` | event-driven | sync, ~50ms | no |
| `gaia dev merge` / `split` | event-driven (both sides) | sync | no |
| Verifier derank (4★→3★) | event-driven (cascade across all attestations) | sync | yes (mini-report) |
| Fork-network change (new fork detected) | quarterly | up to 90 days | yes |
| `github-stars-own` star count refresh | quarterly | up to 90 days | yes |
| `arxiv` citation refresh | quarterly | up to 90 days | yes |
| Freshness decays (`social-signal`, `benchmark-result`, `peer-review`) | quarterly | up to 90 days | yes |
| Provisional-grace expiry (6 months post-migration) | curator PR (per §5.7) | manual | yes |

Verifier derank is the one event-driven trigger that emits a mini stamp report — because the cascade can affect dozens of skills (every attestation the deranked verifier issued goes null per §5.6), the magnitude of state change warrants an audit artifact even outside the quarterly window.

### 6.3 Notification path

Grade changes produce three notification surfaces.

**Skill author notification.** When a skill's grade changes (up or down), the GitHub user listed as the skill's primary contributor receives a comment on the rerank PR (quarterly batch) or a comment on the originating evidence PR (event-driven). The comment includes the old grade, new grade, the magnitude delta, and the dominant evidence type that drove the change.

**User-tree notification.** When a skill changes grade and that skill is held in any user's `skill-trees/<username>/skill-tree.json`, the user's tree gains a timeline event (`action: registry_rerank`, with old/new grade in `details`). Users see this on their next `gaia tree` invocation. No automated demotion of user-tree ranks — the user's lived calibration is theirs.

**Public diff.** Every quarterly stamp report links to a `gaia dev diff --since <last-stamp>` artifact showing every grade change, sortable by magnitude of change. This is the canonical audit surface for outside observers.

### 6.4 Appeal path (PR-gated)

Per Marco #4, every appeal is a PR. There is no automated appeal queue, no email inbox, no Discord channel. The flow:

1. Contributor opens a PR titled `appeal: <skill-id> <old-grade>→<requested-grade>`.
2. PR body must cite either (a) new evidence the rerank missed, (b) a mechanic misapplication (e.g. mothership divisor wrongly applied to non-co-located skill), or (c) a calibration argument referencing anchor skills (see §4).
3. PR runs `gaia validate` which must pass — including the rank-floor rule (§5.8) if applicable.
4. Maintainer review per the verifier guardrail (CLAUDE.md § Authorization). Self-appeals are permitted but require a 4★+ verifier co-sign (analogous to recognized-voice cosign in §3, social-signal sub-rules).
5. Merged appeals write a timeline event (`action: appeal_granted` or `appeal_denied`) on the affected skill.

Provisional-grade demotions at end-of-grace use the same path — the demotion is itself an appeal-shaped PR, opened by the curator who notices the grace window has expired. There is no scheduled job that demotes provisional skills automatically.

### 6.5 Migration as the first batch

The June 2026 trust regrade (Marco #9) is a one-time big-bang regrade that seeds the quarterly cadence — subsequent quarterly batches are deltas against the post-migration baseline. Three deviations from the steady-state batch shape: (1) it is a big-bang re-grade of all evidence under the new formula, not a delta from a prior baseline; (2) it produces the canonical stamp report at `docs/meta/JUN_2026_TRUST_REGRADE.md` using the `gaia-post` skill (`type=report`, `label=Meta-Shift`, hero badge ON); (3) it kicks off the 6-month provisional-grace clock for all skills flagged by the diversity gate (§5.7). Subsequent quarterly batches inherit the same report template but operate as deltas.

## §7 Migration Plan (June 2026)

### 7.1 Cutover model — single major PR

Per Marco hard constraint #6 and decision #8, migration is a **big bang**: one major PR re-grades every evidence entry in `registry/nodes/` under the new formula at merge time. No tenures, no shadow period, no per-skill phasing. The PR ships alongside the v5.0.0 release of the CLI and registry (top-level version bump in `registry/gaia.json` per [Versioning]).

**Old evidence entries are preserved.** Re-grading rewrites computed fields (`magnitude`, `weight`, `grade`, `provisional`, flags) but leaves the raw evidence (`url`, `class`, `notes`, `cosigners`, `addedAt`) untouched. This keeps the historical record auditable and lets us re-run the formula again later without data loss.

### 7.2 PR composition

| Component | Path | Purpose |
|---|---|---|
| Formula implementation | `src/gaia_cli/trust.py` | New `compute_trust_magnitude()` with the 10 evidence types (see §3) |
| Validator | `src/gaia_cli/validate.py` | Diversity gate (§4), rank-floor rule (§10.4), provisional-flag writer |
| Migration script | `scripts/regrade_evidence_jun2026.py` | One-shot rewriter; idempotent re-run safe |
| Re-graded registry | `registry/nodes/**/*.md` | Updated frontmatter only (computed fields) |
| Stamp report | `docs/meta/JUN_2026_TRUST_REGRADE.md` | Meta-post body (see §8) |
| RFC of record | `docs/meta/RFC_TRUST_TAXONOMY.md` | This document, frozen as v1.0 |
| CHANGELOG | `CHANGELOG.md` | Breaking-change entry under v5.0.0 |

The re-graded registry diff is expected to be the bulk of the PR (~hundreds of files, computed-field-only). Reviewers focus on the formula PR and the stamp report; the regrade diff is mechanically generated and verified by CI.

### 7.3 Provisional grade — 6-month grace

Skills that fail the diversity gate (§4) under the new formula but held grade ≥B under the old formula are written with `provisional: true` and `provisionalUntil: 2026-12-15` in frontmatter. They retain their old grade displayed with a **PROVISIONAL** marker in CLI/UI output. End-of-grace demotion is **PR-gated review** (Marco decision #4) — no automated demotion. A nag job opens a tracking issue at T-30 days listing every skill still flagged.

`mattpocock/skills` is the canonical example: drifts B → A PROVISIONAL because its current evidence is self-producible; needs one non-self-producible type (peer-review, verifier-attestation, benchmark-result, social-signal with topical-authority creator, proxy-containment, or arxiv) before 2026-12-15 to confirm A.

### 7.4 Expected drift (calibration sample)

```
ruvnet/ruflo                          B → S       35-component fusion capstone
garrytan/gstack                       B → S       suite root, 4-type diversity
obra/superpowers                      B → S       11-origin fusion + verifier
mattpocock/skills                     B → A *     PROVISIONAL until 2026-12-15
garrytan/cso                          B → B       mothership cap protects
garrytan/benchmark                    B → B       rank-floor §10.4 protects
obra/dispatching-parallel-agents      4★ → A      avoids 4★>5★ inversions
founder-mode-orchestration            ungraded → A *  PROVISIONAL, auto-fusion only
agent-memory-learning                 B → C       same-source dedup collapses stars
registry-curation                     B → B       same-source dedup + plateau caps
skill-mastery                         (P4 S) → A  3 repo-own rows fail diversity
```

Net drift expectation: ~5% of skills move ≥1 grade up (Ultimates with rich fusion + verifier evidence), ~12% move ≥1 grade down (skills that were riding self-producible evidence stacks), ~8% land PROVISIONAL, balance unchanged.

### 7.5 CI implications

- **`gaia validate` becomes blocking on the migration PR.** It runs the new formula, asserts no rank-floor violations (4★+ skills landing below B without explicit `--override-floor` flag and reviewer sign-on per Marco decision #10), and asserts every PROVISIONAL entry has `provisionalUntil` set.
- **Rank-floor failures block publish.** The validator emits a structured error per offending skill; the PR cannot merge until each is either re-evidenced, manually overridden in a PR-gated review, or accepted as a deliberate demotion (rare).
- **Same-source dedup runs at validation time**, not at evidence-add time. Adding a duplicate URL still succeeds at the CLI; the validator collapses it before computing magnitude. This keeps `gaia dev evidence` ergonomic and authoritative.
- **`meta-guard.yml`** continues to gate registry mutations on Verifier authorization. The migration PR runs under `GAIA_OPERATOR_OVERRIDE=1` (Marco's account or a maintainer's, not a bot) so the bulk regrade does not require per-file verifier checks.
- **Cosign CLI flag** (`gaia dev evidence --cosign-with <verifier>`, Marco decision #3) ships in the same release. Recognized-voice 1.2× multiplier on social-signal requires two cross-org verifier cosigns recorded via this flag.

### 7.6 Rollback plan

The migration script is idempotent and reversible: it reads pre-migration frontmatter from a snapshot tag (`pre-trust-regrade-jun2026`) cut from `main` immediately before merge. If post-merge CI or downstream consumers detect a systemic regression (e.g., wiki/docs builds break, MCP server returns malformed grades, badge renders blank), the rollback procedure is:

1. `git revert <merge-commit>` on `main` (single revert, since this is one PR).
2. `gaia release patch --sync` to align manifest versions back to v4.x.
3. Re-publish npm + PyPI packages.
4. Open a tracking issue documenting which evidence type(s) misbehaved.
5. Re-attempt with a fixed migration script; the snapshot tag is the canonical "old world" reference.

Rollback window: 14 days post-merge. After 14 days, downstream user trees may have promoted/fused under the new formula; rollback then requires a forward-fix migration rather than a revert.

---

## §8 Stamp Report (June 2026)

### 8.1 Mechanism

Use the `meta-post` skill at `.agents/skills/meta-post/SKILL.md` (registered name: `gaia-post`). The skill produces a stamped meta-post: a markdown body in `docs/meta/`, a registry entry, hero badge, and a published URL on the static site.

### 8.2 Invocation parameters

| Parameter | Value |
|---|---|
| `type` | `report` |
| `label` | `Meta-Shift` |
| `source` | `docs/meta/JUN_2026_TRUST_REGRADE.md` |
| `hero` | `ON` |
| `author` | `Marco` (Orchestrator agent ghostwrites; Marco is named author of record) |
| `publishedAt` | merge timestamp of the migration PR |
| `slug` | `jun-2026-trust-regrade` |

Run order: (1) draft `docs/meta/JUN_2026_TRUST_REGRADE.md` body, (2) invoke `gaia-post` to register the meta-post and produce the hero asset, (3) include both in the migration PR so the stamp lands atomically with the regrade.

### 8.3 Required body sections

The markdown body at `docs/meta/JUN_2026_TRUST_REGRADE.md` must contain, in order:

1. **Apex demotions — lead headline.** Open with the one-sentence verdict: *"At G7 cutover, both standing 6★ skills (`mattpocock/skills`, `ruvnet/ruflo`) demote to 5★ under the new strict apex gate (§11.12). The system-wide 6★ count is 0 at G7+0. The tier remains earnable; it is no longer earned."* Then a per-skill section for each demoted apex listing which §11.12 predicates failed, the strict-evidence regrade outcome (mattpocock/skills: TM 390 → A provisional; ruvnet/ruflo: TM 489 → A provisional), the §10.14 registry-wide anti-auto-mint clause as the central honesty change, and the §11.12.8 PR-gated re-application path. This section MUST lead — Marco's call 2026-06-16: "yes unfortunately the world needs to know." Do not bury under aggregate drift counts. Do not soften with "calibration adjustment" framing.

2. **Abstract** — one paragraph, ≤120 words. State that the registry's evidence-grading formula was rebuilt around 10 typed evidence forms with diversity, mothership, dedup, fusion-curve, and verifier-derank rules; that all evidence was re-graded in a single PR; that `provisional` flags carry a 6-month grace; that the rank-floor rule blocks 4★+ skills from landing below B; that the apex tier (6★) was redefined under a 9-predicate hard gate (§11.12) and both prior holders demoted to 5★; that the registry-wide anti-auto-mint clause (§10.14) requires every non-fusion-recipe evidence row to be physically present in frontmatter.

3. **Executive Summary** — bulleted, ≤8 bullets. Headline numbers (S=250, A=100, B=50, C=20), the 10 evidence types as a one-line list, the four core mechanics (mothership-discount, same-source dedup, fork canonicalization, sqrt-softened fusion), the migration model (big bang, old entries preserved), and the apex-gate count change (2 → 0 6★ skills system-wide; cap=5).

4. **Findings — drift table.** Reproduce the calibration sample from §9 with a fourth column citing the dominant rule that drove each drift (e.g., "fusion sqrt-softening", "rank-floor §10.10", "diversity gate", "§10.14 anti-auto-mint", "§11.12 apex gate"). Include net-drift percentages. Apex demotions are highlighted in this table with the same lead-row treatment they got in section 1.

5. **Methodology** — three subsections:
   - **Formula** — fenced code block reproducing the per-evidence magnitude/weight/cap table (§3).
   - **Diversity gate** — reproduce the grade thresholds table (§4).
   - **Apex gate** — reproduce the §11.12 9-predicate spec verbatim with the disposition table for both demoted skills.
   - **Migration mechanics** — point to §7; do not duplicate prose.

6. **Provisional cohort** — full list of every skill with `provisional: true` and its `provisionalUntil` date, grouped by what evidence type it needs to confirm grade. Demoted apex skills appear with their §11.12.8 re-application path noted alongside. Linked to the tracking issue opened at migration time.

7. **References** — link to the RFC (this document), Marco's 10 final decisions thread, the synthesis workflow output, the 6★-tier audit workflow output (run wf_f14f7317-972, 2026-06-16), and the migration PR. Cite Anthropic's *Building Effective Agents* and *Introducing dynamic workflows in Claude Code* as agent-architecture inspirations for the consensus pipeline that produced the RFC.

8. **Acknowledgements** — verifiers who cosigned during regrade; agents that ran the consensus workflow and the apex-tier audit.

### 8.4 Hero badge

Hero ON. Badge art renders the headline numbers (S/A/B/C thresholds) over a faint registry-graph backdrop, matching the visual language of prior Meta-Shift posts. Generated by the `meta-post` skill's hero pipeline; no manual asset authoring.

### 8.5 Downstream

The stamp report is the canonical citation for any future "why did my skill drift?" question. CLI surfaces a hint pointing at it on first `gaia validate` failure post-migration: `see docs/meta/JUN_2026_TRUST_REGRADE.md`. The README's `# NEW! Badges` section is left untouched per memory directive; the Meta-Shift entry instead lands in the meta-post index page.

## §9 Calibration Table

The drift below applies the full synthesized formula stack: mothership-discount with capped divisor (§3.1), same-source dedup (§3.2), fork-network canonicalization (§3.3), sqrt-softened fusion beyond 10 origins (§3.4), only-graded≥C origins counting toward fusion-recipe (§3.5), null-on-derank verifier (§3.6, see §10.4 for reconciliation), rank-floor sanity rule for 4★+ skills (§10.10), the **§10.11 transitive-closure rule for fusion-recipe origins** (reverses prior §11 Decision 7), the **§10.12 nine-predicate apex gate** for the 6★ tier, the **§10.13 no-grandfathering clause** at G7 cutover, and the **§10.14 registry-wide anti-auto-mint clause**.

| skillId | currentRank *(pre-migration registry grade)* | finalTrustMagnitude | finalOverallGrade | driftDirection | rationale | provisional |
|---|---|---|---|---|---|---|
| `ruvnet/ruflo` | **6★** *(demotes at G7 cutover to 5★ per §10.13 / §11.12)* | 489 | **A** *(provisional)* | 6★ → 5★/A | 47 direct components, transitive closure dedups to 47 distinct skillIds (no cycles), 46 graded≥C origins after stripping ungraded `ruvnet/github-release-management`. Sqrt-softening: m = 200 + 20×√(46-10) = 200 + 20×6 = 320, weighted 1.5 → 480. Mothership-discounted github-stars-own contributes 8.5 (34k stars / divisor=min(47,4)=4). TM = 489. Magnitude clears S=250 floor easily, but S diversity fails: only 2 distinct evidence types at apex (fusion-recipe + github-stars-own); rule 5 grade-bubbling tops out at A across the 47-node closure (no S grade exists anywhere in the descendant tree). Lands at A; 6★-on-A is structural inversion. Demotes 6★→5★ at G7 cutover under §11.12.10 (failed §11.12.4 S-diversity, §11.12.6 cross-org verifier-attestations). Provisional flag opens §5.7 6-month path to S via one S-graded descendant or a non-self-producible S-tier row at parent. | **yes** |
| `garrytan/gstack` | 5★ | 318 | **S** | B → S | Suite root with 4-type diversity (fusion-recipe via suiteComponents auto-mint per §10.8, github-stars-own, peer-review, social-signal); founder identity tier 1.0× on social-signal; passes S-gate cleanly | no |
| `obra/superpowers` | 5★ | 287 | **S** | B → S | 11-origin fusion-recipe (just past softening knee), 3 cross-org verifier-attestations, github-stars-own; clears the ≥1 S-tier-evidence-OR-≥3-A-tier rule via verifier stack | no |
| `mattpocock/skills` | **6★** *(demotes at G7 cutover to 5★ per §10.13 / §11.12)* | 390 | **A** *(provisional)* | 6★ → 5★/A | Under §11.7-NESTED transitive-closure rule, fusion-recipe origins dedup-by-skillId to 19 (every grandchild via mattpocock/engineering, /personal, /productivity is also a direct child); all 19 are graded≥C, sqrt-softens to m=260, weighted 1.5 → 390. But strict-evidence reading (§11.12.4 anti-auto-mint, registry-wide per §10.14) finds the apex frontmatter carries `evidence: []` — distinct types = 1, non-self-producible types = 0, fails S diversity gate on both ≥3 distinct AND ≥1 non-self-producible at magnitude ≥25 post-discount. Lands at A; provisional flag carries §5.7 6-month grace pending one non-self-producible row. Demotes 6★→5★ at G7 cutover under §11.12.10 (failed §11.12.3 depth-2-only-reachable, §11.12.4 strict-evidence S-diversity, §11.12.5 A-graded count, §11.12.6 cross-org verifier-attestations). | **yes** |
| `garrytan/cso` | 4★ | 78 | **B** | B → B | Mothership-discount with capped divisor (§3.1, divisor=4) keeps github-stars-own from inflating; rank-floor sanity rule (§10.10) protects from sub-B drop; held at B as intended | no |
| `garrytan/benchmark` | 4★ | 64 | **B** | B → B | Repo-own at 0.6 weight + benchmark-result at 95th percentile; 4★+ rank-floor rule (§10.10) blocks any sub-B landing — the formula alone would have pushed to C, validation gate intervenes | no |
| `obra/dispatching-parallel-agents` | 4★ | 118 | **A** | 4★ → A | github-stars-own + 1 verifier-attestation + repo-own; previously sat above its own 5★ siblings (inversion), regrade lands at honest A; non-self-producible verifier evidence satisfies diversity | no |
| `founder-mode-orchestration` | 3★ | 105 | **A** | C → A | Auto-fusion-recipe from suiteComponents (§10.8) is the sole graded≥C origin contributor; flagged provisional because all evidence remains self-producible until external attestation lands | **yes** |
| `skill-mastery` | 4★ | 92 | **A** | S → A | Synthesis rejected the P4/P2 S-grade: 3 repo-own rows fail the ≥3 distinct-types rule under same-source dedup (§3.2); lands at A with one non-self-producible benchmark-result entry | no |
| `agent-memory-learning` | 3★ | 41 | **C** | B → C | Same-source dedup (§3.2) collapses three github-stars-own entries pointing at the same canonical repo into one; remaining magnitude falls below the B-gate threshold of 50 | no |
| `registry-curation` | 3★ | 56 | **B** | B → B | Same-source dedup trims duplicate stars-own; plateau caps on proxy-containment (1.0×/0.5×/0.25×) prevent inflation; lands cleanly at B with verifier-attestation as the non-self-producible anchor | no |
| `claude-api-reference` | 3★ | 48 | **C** | B → C | Two repo-own + one self-attestation (capped at flat 10); all three types self-producible, fails diversity ≥1 non-self-producible rule for B; downgrades to C | no |
| `gaia-curate-chain` | 3★ | 67 | **B** | C → B | Auto-fusion-recipe via suiteComponents (3 graded≥C origins) + repo-own; clears B-gate; not yet S-capable until verifier or external evidence lands | no |
| `meta-post` | 2★ | 24 | **C** | C → C | Self-attestation (flat 10) + one repo-own; below B-gate; stable at C, no drift | no |

Provisional rows (`ruvnet/ruflo`, `mattpocock/skills`, `founder-mode-orchestration`) carry the 6-month grace marker per §7; PR-gated demotion review fires at grace expiry per §11 Decision 4. The two formerly-6★ rows (`ruvnet/ruflo`, `mattpocock/skills`) demote to 5★ at G7 cutover under §10.13 / §11.12.10 — apex demotion is **not** a §5.7 grace landing; it is a tier-floor failure under the new §11.12 nine-predicate apex gate. Both can re-apply via the §11.12.8 PR-gated path once missing predicates accumulate.

## §10 Marco's Hard Constraints (Honored)

Each of the eight hard constraints is satisfied by the formula stack above. The single apparent deviation — verifier null-on-derank — is a strengthening of constraint #4, not a violation; reconciliation in §10.4.

### §10.1 Pure github-stars CAN reach A

`github-stars-own` is S-capable at 100k+ stars (cap 200, weight 1.0). At 4–6★ stars-only with no other evidence, magnitude lands in the 80–140 band, clearing the A-gate (≥100, ≥1 distinct type, ≥1 A-tier). The diversity rule explicitly permits A on a single A-tier evidence type. **Honored.**

### §10.2 Ultimate hard-requires fusion-recipe evidence

Fusion-recipe is mandatory inherent evidence on every fused/Ultimate skill (§7.8). Validation rejects an Ultimate-typed node with no fusion-recipe row regardless of magnitude — `gaia validate` blocks the publish. Auto-mint fires from `suiteComponents` only, not transitive prerequisites (§11 Decision 7). **Honored.**

### §10.3 Proxy-containment guardrails

Hard cap 3 entries, plateau `1.0× / 0.5× / 0.25×`, external repo ≥10k stars to count. Until the proxy validator ships, entries count at full magnitude with explicit `unverified: true` flag on the evidence row (§11 Decision 2). **Honored.**

### §10.4 Verifier-attestation: flag on derank, no decay — reconciled with null-on-derank

Marco's original constraint: a 4★+ verifier who later loses rank should leave their attestation **flagged**, not decayed — meaning the attested skill's previously-earned rank is not retroactively demoted; only the deranked verifier's ongoing magnitude contribution evaluates to null. The synthesis upgrade to **null-on-derank** is strictly stronger in the same direction:

```
flag-only:    attestation.value = magnitude, attestation.flagged = true
null-on-derank: attestation.value = null,    attestation.flagged = true
```

Null-on-derank zeroes the magnitude contribution of a deranked verifier going forward but leaves the *historical* trust grade earned at attestation time intact (rank floor §10.10 + no retroactive demotion §11 Decision 4). Flag is still raised, decay is still rejected as a mechanism — the value just collapses to null instead of partially decaying. This is the stricter reading of "no decay": no half-credit, no time-weighted fade, just a binary cliff at the moment of derank. **Honored as strengthened.**

### §10.5 Naming: Trust Magnitude (aggregate), artifact score (per-evidence)

Used consistently throughout §§1–11 and the calibration table above. No instances of "trust score", "credibility score", or rarity-axis terminology survive the regrade. **Honored.**

### §10.6 No tenures — single migration PR re-grades all evidence

Big-bang cutover (§11 Decision 8). One major PR rewrites all evidence rows under the new formula at merge time, preserves old entries in `evidence.archived[]` for audit, and ships the June 2026 stamp report via the `gaia-post` skill (§11 Decision 9). No phased rollout, no parallel scoring. **Honored.**

### §10.7 social-signal hard A-cap (80 max magnitude)

Cap enforced at the type level: `min(80, log10(views) × 8 × creator_mult × engagement_ratio)`. Even at 1.4× ceiling creator multiplier and 1.5× engagement ratio, formula tops out at 80 by construction. social-signal cannot contribute the S-tier evidence required for an S-grade per the diversity gate. **Honored.**

### §10.8 fusion-recipe is mandatory inherent evidence

Every fused or Ultimate skill auto-receives a fusion-recipe row at creation time, with origins = suiteComponents only (not transitive prerequisites, per §11 Decision 7). Only graded≥C origins count toward magnitude (§3.5). Validation enforces presence; absence blocks publish. **Honored.**

### §10.9 Recognized-voice (1.2× creator multiplier) requires 2 cross-org verifier co-signs

CLI surface: `gaia dev evidence --cosign-with <verifier>` accepts ≥2 distinct-org 4★+ verifier handles before promoting a social-signal row's `creator_mult` to 1.2× (§11 Decision 3). Single-org co-signs reject. **Honored.**

### §10.10 Rank-floor sanity rule blocks publish at validation time

4★+ skills cannot land below B without explicit PR-gated review (§11 Decision 10). Implemented as a `gaia validate` failure on the migration PR rather than a soft warning. Manual override flows through the same PR-gated review path used for provisional demotion (§11 Decision 4). Protects `garrytan/benchmark` and similar 4★+ skills whose raw formula output would otherwise land at C. **Honored.**

### §10.11 Fusion-recipe origin counting is transitive (replaces prior §11 Decision 7)

Auto-mint of the fusion-recipe row on every fused/Ultimate skill (mandatory per §10.2 and §10.8) computes origins as the **full transitive closure** of `suiteComponents`, not the direct-component-only walk specified in the prior §11 Decision 7. The walk dedups by `skillId` (a skill reachable through multiple paths counts once), maintains a visited set for cycle detection (A→B→A leaves A visible once), filters origins by Overall Trust Grade ≥ C **after** traversal (per §3.5), and applies sqrt-softening to the post-dedup-post-filter origin count (per §3.4: `m = 20 × origins` for ≤10 origins, `m = 200 + 20 × √(origins−10)` for >10).

Mothership-discount (§3.1) and same-source dedup (§3.2) continue to apply at the underlying evidence-row level for nested components, not at the fusion-recipe-origin-count level.

**Grade stacking** (rule 5 of the §11.7-NESTED block): a nested component's strongest grade bubbles up through the fusion-recipe channel to satisfy the parent's §4 "≥1 S-tier evidence" diversity gate. The bubbled grade may come from any evidence type on the descendant including fusion-recipe itself — the channel does not exclude descendant fusion-recipe rows. (Marco's call, 2026-06-16: "1 relax." This is the looser of the two readings the synthesis surfaced; closes no loop, admits genuine deep-stack apex paths.) **Honored as strengthened.**

### §10.12 Apex tier (6★) is gated by a 9-predicate hard rule

A user-tree skill at 6★ MUST satisfy §11.12.1–§11.12.9 simultaneously. Failure on any predicate drops the apex claim to 5★ with no partial credit and no curator override outside the §11.12.8 PR-gated review path. The gate exists at three enforcement points: `gaia promote` rejects target_level==`"6★"` with a "open a PR labeled apex-promotion; auto-promotion to apex is disabled" error; `gaia validate` runs the 9 predicates against the migration PR and emits a structured failure list; `meta-guard.yml` enforces the §11.12.9 system-wide cap (≤5) and the §11.12.8 PR-label-plus-2-verifier requirement at merge time.

The advisory `ultimateGateStatus` block in `registry/named-skills.json` is renamed `apexGateStatus` and now carries per-predicate pass/fail rather than the single direct-component check. **Honored.**

### §10.13 No grandfathering at the G7 migration boundary

Every currently-6★ skill is re-evaluated against §10.12 at G7 cutover. Skills failing any predicate are demoted to 5★ in the migration PR with `(demoted at G7 cutover — failed apex predicate N)` in the timeline `details` field. The §5.7 6-month provisional grace does NOT apply to apex demotion (§5.7 covers borderline grade landings, not tier-floor failures). Demoted skills can re-apply for 6★ via the §11.12.8 PR-gated path once missing predicates are accumulated.

At G7+0, both currently-6★ skills (`mattpocock/skills`, `ruvnet/ruflo`) demote to 5★ per the disposition table in §11.12. System-wide 6★ count post-cutover: **0 of 5** slots filled. **Honored.**

### §10.14 Registry-wide anti-auto-mint clause

The strict-evidence reading codified for the apex tier in §11.12.4 applies **registry-wide**, not apex-only (Marco's call, 2026-06-16: "registry-wide of course"). Across every grade (S, A, B, C), only the fusion-recipe row may be auto-derived (per §10.8 because Ultimates hard-require it). Every other evidence type — `github-stars-own`, `repo-own`, `self-attestation`, `verifier-attestation`, `arxiv`, `peer-review`, `proxy-containment`, `social-signal`, `benchmark-result` — MUST be physically present in the skill's `evidence:` frontmatter array to contribute to Trust Magnitude. Phantom rows lifted from upstream calibration sketches, draft notes, or comments do not count.

**Migration impact.** The G7 migration PR re-evaluates every Overall Trust Grade across the full registry under strict-evidence reading. Skills whose pre-migration grade was supported by phantom rows drift downward in the §9 calibration table; skills whose evidence was already faithful to frontmatter are unaffected. The blast radius is bounded by the migration PR's atomic merge (§10.6 big bang) and the regrade tooling at `scripts/migrate_trust_magnitude.py`, which is extended to flag every row whose source path doesn't match `registry/named/<owner>/<skill>.md` frontmatter or `registry/nodes/<id>.json` evidence array.

This is the central anti-honesty-failure predicate: it locks down the auto-mint vulnerability the G7 audit surfaced on `mattpocock/skills` (where the regrader silently credited the apex with `github-stars-own + repo-own + self-attestation` rows that don't physically exist). The clause prevents the same failure from inflating any grade going forward. **Honored.**

## §11 Open Questions & Decisions

*§11.1–11.9 resolve Marco's 10 final decisions (decisions #1–#9 below; #10 is in §11.11 as a reconciliation note). §11.10 records the null-on-derank reconciliation against hard-constraint #4.*

The synthesis surfaced ten open questions. Marco resolved each in a second consensus pass; resolutions and follow-up actions are recorded below. References point to mechanics defined in §3–§10.

### 11.1 Verifier-cluster definition
**Q.** What constitutes a "verifier cluster" for cross-org co-sign requirements (§7 social-signal recognized-voice tier)?
**A.** GitHub org membership. Two verifiers in the same GitHub org count as one cluster.
**Action.** `gaia dev evidence --cosign-with` must resolve verifier→org via the GitHub API at attestation time and reject same-org co-signs.

### 11.2 Proxy-containment validator
**Q.** How does the registry validate proxy-containment claims (e.g. "skill X is contained in repo Y with N stars")?
**A.** Parked. Repo currently has Marco plus one contributor — not enough surface area to justify a validator. Until the validator ships, **unverified proxy claims count at full magnitude with an explicit `unverified: true` flag** on the evidence entry. Lenient-by-default.
**Action.** Open follow-up issue "Proxy-containment validator (post-growth milestone)". Add `unverified` boolean to the evidence schema (§12).

### 11.3 Recognized-voice 1.2× tier gating
**Q.** What guards the 1.2× `creator_multiplier` from self-promotion?
**A.** Confirmed: requires **2 cross-org verifier co-signs** (per §11.1).
**Action.** Ship `gaia dev evidence --cosign-with <verifier>` CLI flag in G3. Co-signs persist on the evidence entry as a `cosigners[]` array of `{verifier, org, signedAt}`.

### 11.4 Provisional-grade demotion at end of grace
**Q.** When a 6-month provisional grace expires without sufficient non-self-producible evidence, who demotes?
**A.** **PR-gated review.** No automated demotion. The grace expiry surfaces in `gaia validate` as a warning; a maintainer opens a demotion PR.
**Action.** `gaia validate` emits `provisional-expired` warnings; demotion remains a manual `gaia dev reclassify` invocation under a review PR.

### 11.5 Fork-network legitimate divergence
**Q.** When two forks of the same upstream genuinely diverge into separate skills, how do we opt out of fork-network canonicalization (§5.4)?
**A.** Orchestrator's call. Default behavior canonicalizes a fork's stars to upstream. To opt out, the fork's evidence entry sets `links.canonicalRepo` explicitly to its own repo URL.
**Action.** Add `links.canonicalRepo: <url>` field to the evidence schema. Canonicalization pre-pass honors it before collapsing fork networks.

### 11.6 Mothership "same parent org" subdivision
**Q.** Does `google/tensorflow` and `google/jax` share a mothership pool?
**A.** No. Same parent org is **not sufficient** — products must share a package-name root or a declared `product` field on the repo. `tensorflow` ≠ `jax` even under the same org.
**Action.** Mothership detection reuses the existing org-disambiguation pattern from `gaia scan`; extend it to compare `product` fields and package-name roots before pooling.

### 11.7 Auto-minted fusion-recipe origins for Ultimates *(REVERSED 2026-06-16 — see §10.11 / §11.12-NESTED for the new transitive-closure rule)*
**Q.** When an Ultimate is auto-minted, do its fusion-recipe origins include transitive prerequisites?
**A (struck through; preserved for audit history):** ~~**`suiteComponents` only.** Transitive prerequisites do not count.~~
**Action (struck through):** ~~Auto-mint logic in `gaia fuse` reads `suiteComponents` directly; do not walk `prerequisites`.~~
**New resolution (effective G7 cutover):** Full transitive closure of `suiteComponents`, dedup-by-skillId, cycle-safe, graded≥C filter applied AFTER traversal, sqrt-softening on the post-filter count. Grade stacking via the fusion-recipe channel admits descendant rows of any type including fusion-recipe itself (per Marco's "1 relax" call). Codified in §10.11; 9-predicate apex gate that exploits the new rule lives at §11.12.

### 11.8 Migration cutover strategy
**Q.** Phased re-grade or single cutover?
**A.** **Big bang.** A single major PR re-grades all evidence at merge time. No tenures. Old evidence entries are preserved verbatim; only the derived `artifact_score` and `trust_magnitude` recompute.
**Action.** `scripts/migrate_trust_magnitude.py` is the migration entry point; runs in CI under the migration PR; outputs `docs/meta/JUN_2026_TRUST_REGRADE.md`.

### 11.9 Stamp report (June 2026)
**Q.** How do we communicate the migration to contributors?
**A.** Use `gaia-post` skill at `.agents/skills/meta-post/SKILL.md`. Type=`report`, label=`Audit` or `Meta-Shift`, source=`docs/meta/JUN_2026_TRUST_REGRADE.md`, hero badge ON.
**Action.** Migration PR includes the stamp invocation in its checklist.

### 11.10 Verifier null-on-derank vs flag-on-derank reconciliation
**Q.** Marco's hard constraint #4 says "flag on derank, NO decay" but the synthesis upgraded to **null-on-derank** (P3 graft). Which wins?
**A.** **Null-on-derank wins.** The hard constraint predates the P3 graft; null-on-derank is strictly stronger (a flagged-but-counted attestation from a deranked verifier was the failure mode #4 was reaching for). Flag remains on the evidence entry for audit history; the artifact score evaluates to null for grading purposes.
**Action.** §10.4 clarifies: `flag: deranked` persists on the entry, `artifact_score = null`, magnitude excluded from sum.

### 11.11 Rank-floor sanity rule enforcement point
**Q.** Where does the "4★+ skills cannot land below B without explicit review" rule fire?
**A.** **At `gaia validate`.** Blocks publish on the migration PR. Manual override requires a PR-gated review (per §11.4 pattern).
**Action.** New validator `validate_rank_floor.py` in `scripts/`; wired into `gaia validate` and the release workflow.

### 11.12 Strict 6★ apex gate (replaces all prior 6★ gating)

**Q.** What does it actually take to land a skill at 6★ under the post-nested-suiteRef regime (§10.11)?

**A.** Nine simultaneous hard predicates. No partial credit. No curator override outside the §11.12.8 PR-gated path. The current gate (deprecated `class:"A"` evidence-row check in `promotion.py::_meets_evidence_floor` + advisory direct-component grade check in `grading.py::check_ultimate_gate` + unused `meta.json` `apexPath` declaration) is replaced wholesale.

#### §11.12.1 Fusion-recipe origin floor (transitive)
Apex MUST carry an auto-derived `fusion-recipe` evidence row with **origins_graded ≥ 12** under the §10.11 transitive-closure rule. Twelve forces the gate to land at least 2 origins inside the §3.4 sqrt-softened regime (knee at 10) so magnitude cannot be gamed by stopping at exactly 10 flat-band origins (m=200 weighted 300) to dodge softening.

#### §11.12.2 Non-trivial direct nesting
At least **one direct component** of the apex MUST itself have non-empty `suiteComponents`. Structural predicate read directly from frontmatter; no inference.

#### §11.12.3 Depth ≥ 2 stack (not collapsed by dedup)
The transitive walk MUST visit at least one node at depth 2 that is NOT also a direct (depth-1) component of the apex. Formal predicate: `∃ s ∈ closure(apex) : minDepth(s, apex) = 2`. This blocks the `mattpocock/skills` failure mode where every grandchild is also a direct child — under §10.11 dedup that collapses to a flat structure with cosmetic nesting. Real "stack on top of 5★ infrastructure" must contribute at least one skillId reachable ONLY through a nested suite.

#### §11.12.4 Overall Trust Grade S with anti-auto-mint teeth (registry-wide per §10.14)
Apex Overall Trust Grade MUST equal **S** under §4, evaluated with **no auto-minted evidence rows** beyond fusion-recipe itself (which is auto-derived per §10.8 because Ultimates hard-require it). All other rows MUST be physically present in the apex's `evidence:` frontmatter array per §10.14 (registry-wide clause). Specifically:
- TM ≥ 250 from actual rows (fusion-recipe + physically-present rows only).
- ≥ 3 distinct evidence types present at the apex node.
- ≥ 1 non-self-producible row of magnitude ≥ 25 AFTER §3.1 mothership-discount and §3.2 same-source dedup. (Calibrated against the divisor-cap-4 mothership baseline: requires pre-discount row ≥ 100, e.g., ≥100k github-stars OR a verifier-attestation cluster OR a benchmark-result.)
- ≥ 1 S-tier evidence may be satisfied by §10.11 grade-bubbling from any descendant evidence type (including descendant fusion-recipe rows, per Marco's "1 relax" call).

#### §11.12.5 Component grade depth
At least **M = 8** distinct skillIds in the transitive closure MUST hold Overall Trust Grade ≥ A. Calibrated as ~⅔ of the §11.12.1 origin floor — apex cannot ride sqrt-softening on mostly B-graded substrate.

#### §11.12.6 Cross-org verifier-attestation floor
Apex MUST carry **K = 2** `verifier-attestation` rows authored by 4★+ verifiers from at least **2 distinct GitHub organizations** (counted by repo owner of the verifier's home skill, per §11.1). Same-org cosigns count once.

(Marco's call, 2026-06-16: K=2 starting point. Synthesis recommended K=3 with relax-to-K=2 amendment if no skill clears within 6 months; Marco picked the looser starting point. Tightening to K=3 may follow under evidence if the registry shows coordinated 2-cosign apex landings undermining tier credibility.)

#### §11.12.7 Tenure
Apex's earliest evidence row (by `addedAt` ISO timestamp UTC) MUST be ≥ **180 calendar days** before promotion. Aligned with §5.7 6-month provisional grace so the same clock can carry a provisional-S skill into apex eligibility without double-counting.

#### §11.12.8 PR-gated promotion (no auto-promote)
At G7 and forever after, `gaia promote` REJECTS target_level==`"6★"` at the CLI layer. Apex requires a manually-opened PR labeled `apex-promotion`, blocked by `meta-guard.yml` until ≥ 2 distinct 4★+ verifiers (per §11.12.6 cross-org rule) leave approving reviews. The promote command emits a stub PR template with all 9 predicates and their measured values; verifiers tick or strike each.

#### §11.12.9 System-wide scarcity cap
**≤ 5** skills at 6★ at any moment. Enforced at PR-merge time by `meta-guard.yml` counting `level: "6★"` across `registry/named-skills.json`. A sixth 6★ landing requires either (a) prior demotion of an existing 6★ via the same PR-gated path with `apex-demotion` label and ≥ 2 verifier sign-offs, or (b) cap raise via RFC amendment with maintainer quorum. Five is `2 × current-count + 1` — generous enough to admit 3 more apex landings post-migration while preserving the "you can name them all from memory" property that makes the tier socially legible.

#### §11.12.10 No grandfathering at G7 (codified in §10.13)
At G7 cutover, every currently-6★ skill is re-evaluated against §11.12.1–§11.12.9 inside the migration PR. Failures demote to 5★ with `(demoted at G7 cutover — failed apex predicate N)` in the timeline `details` field. §5.7 6-month grace does NOT apply (it covers borderline grade landings, not tier-floor failures). Re-application allowed immediately via the §11.12.8 PR-gated path; no cooldown on re-litigation (Marco's default, 2026-06-16).

**Per-skill migration disposition (computed against the 9 predicates at G7+0):**

| skillId | §11.12.1 origins ≥ 12 | §11.12.2 direct nest | §11.12.3 depth-2-only | §11.12.4 S w/ anti-mint | §11.12.5 ≥ 8 A-graded | §11.12.6 ≥ 2 cross-org cosigns | §11.12.7 tenure ≥ 180d | Disposition |
|---|---|---|---|---|---|---|---|---|
| `mattpocock/skills` | ✓ (19) | ✓ (3 of 19) | **✗** (every grandchild also direct) | **✗** (apex `evidence: []`; strict-evidence: 1 type, 0 non-self-producible) | **✗** (6 A-graded, need 8) | **✗** (0 cosigns) | n/a (PR-gated) | **6★ → 5★** |
| `ruvnet/ruflo` | ✓ (46) | ✓ (6 of 47) | ✓ (path 76 vs distinct 47 implies depth-2-only nodes; verifier confirms at apex-promotion PR review) | **✗** (2 distinct types: fusion-recipe + 1 mothership-discounted github-stars-own at 8.5; no S anywhere in closure) | ✓ (5 A-graded named in audit; needs verification of full 8 at PR review) | **✗** (0 cosigns) | n/a (PR-gated) | **6★ → 5★** |

Both demote at G7 cutover. System-wide 6★ count post-cutover: **0 of 5** slots filled. The tier remains earnable; it is no longer earned.

**Action.** (1) `meta.json` `levels.evidenceFloors."6★"` deprecated; replace with `levels.apexGate` block carrying the 9-predicate spec; legacy `alternativePathways."6★".apexPath` removed. (2) `src/gaia_cli/promotion.py::_meets_evidence_floor` extended into `_passes_apex_gate(graph_skill, target_level, user_tree, named_skills_index)`; CLI rejects target_level==`"6★"` with apex-promotion-PR error. (3) `src/gaia_cli/grading.py::check_ultimate_gate` superseded by `check_apex_gate`; `ultimateGateStatus` renamed `apexGateStatus` with per-predicate pass/fail. (4) `.github/workflows/meta-guard.yml` extended to count system-wide 6★ skills, reject above-cap merges, and require `apex-promotion` label + 2 verifier approvals for any 6★ landing. (5) `scripts/audit_apex_at_g7.py` runs the gate over current 6★ holders during migration; emits demotion entries for the migration PR with timeline notes per §11.12.10. (6) Stamp report (§8) leads with apex demotion section per Marco's 2026-06-16 call.

---

## §12 Implementation Hooks

The migration ships as **three commit stages within ONE migration PR** (per Marco hard-constraint #6, §7.1, §11 Decision 8): G2 → G3 → G4 land as ordered commits on a single `review/meta/trust-magnitude` branch under one review surface and one merge to `main`. The stages are independently reviewable diffs (so reviewers can step through G2 schema before G3 scorers and G4 validators) but are **not** separate pull requests — the big-bang cutover requires a single atomic merge.

### G2 — Schema & Core Magnitude (foundational)
| Hook | Location | Notes |
|---|---|---|
| Rename `trustNumber` → `trustMagnitude` | `registry/schema/skill.json`, `registry/schema/evidence.json`, all `registry/nodes/*.json`, `src/gaia_cli/grading.py` | Lockstep rename; codemod via `scripts/rename_trust_field.py` |
| Add `artifact_score` per-evidence field | `registry/schema/evidence.json` | Computed: `magnitude × weight × freshness`. Distinct from skill aggregate. |
| Add `provisional: bool` + `provisionalUntil: ISO8601` | `registry/schema/skill.json` | 6-month grace marker; surfaced in `gaia validate` |
| Add `unverified: bool` to evidence entries | `registry/schema/evidence.json` | Proxy-containment marker (per §11.2) |
| Add `links.canonicalRepo: url` to evidence entries | `registry/schema/evidence.json` | Fork-network opt-out (per §11.5) |
| Update `derive_grade()` thresholds | `src/gaia_cli/grading.py` | S=250 / A=100 / B=50 / C=20 / ungraded<20 |
| Mothership discount | `src/gaia_cli/grading.py::apply_mothership_discount()` | `divisor = min(skill_count_in_repo, 4)`; reuses org-disambiguation pattern from `gaia scan` |
| Same-source dedup pre-pass | `src/gaia_cli/grading.py::dedup_evidence()` | Collapse identical URLs before scoring |
| Fork-network canonicalization | `src/gaia_cli/grading.py::canonicalize_forks()` | Honors `links.canonicalRepo` (per §11.5) |

### G3 — Per-Evidence Scorers & Verifier CLI
| Hook | Location | RFC reference |
|---|---|---|
| `score_fusion_recipe()` with sqrt-softening | `src/gaia_cli/scorers/fusion.py` | §6; `m = 20 × origins for origins ≤ 10, else m = 200 + 20 × sqrt(origins - 10)`; only graded≥C origins count |
| `score_github_stars_own()` with mothership discount | `src/gaia_cli/scorers/stars.py` | §5.2; cap 200 |
| `score_proxy_containment()` with unverified flag | `src/gaia_cli/scorers/proxy.py` | §5.3; max 3 entries, plateau 1.0×/0.5×/0.25×, ≥10k external stars |
| `score_verifier_attestation()` null-on-derank | `src/gaia_cli/scorers/verifier.py` | §10.4; returns `None` magnitude when verifier rank<4 |
| `score_social_signal()` with creator-mult & view-floor | `src/gaia_cli/scorers/social.py` | §7; `log10(views) × 8 × creator_mult × engagement_ratio`; A-cap=80; <1k views → ungraded |
| `score_benchmark_result()` | `src/gaia_cli/scorers/benchmark.py` | §5.5; cap 100; freshness 50%/year |
| `score_repo_own()`, `score_self_attestation()`, `score_arxiv()`, `score_peer_review()` | `src/gaia_cli/scorers/*.py` | §5; per-table caps |
| `gaia dev evidence --cosign-with <verifier>` | `src/gaia_cli/dev.py` | §11.3; resolves verifier→org, rejects same-org co-signs, persists `cosigners[]` |
| Non-self-producible-type check | `src/gaia_cli/grading.py::has_non_self_producible()` | §10 diversity gate; excludes `fusion-recipe`, `self-attestation`, `repo-own` |

### G4 — Validation, Migration, Stamp
| Hook | Location | Notes |
|---|---|---|
| `validate_rank_floor.py` | `scripts/validate_rank_floor.py` | 4★+ skills below B → block publish (§11.11) |
| `validate_provisional.py` | `scripts/validate_provisional.py` | Surfaces expired-grace warnings (§11.4) |
| `migrate_trust_magnitude.py` | `scripts/migrate_trust_magnitude.py` | Big-bang re-grade entry point (§11.8) |
| `gaia validate` wiring | `src/gaia_cli/validate.py` | Calls both new validators; rank-floor failures block, provisional warnings advise |
| Stamp report invocation | `docs/meta/JUN_2026_TRUST_REGRADE.md` + `gaia-post` | §11.9; hero badge ON |

---

## §13 Appendix: Worked Calculations

Five worked Trust Magnitude calculations spanning the calibration sample. Each shows raw measurement, magnitude, weight, freshness, artifact score, total, diversity gate, final grade.

### 13.1 `ruvnet/ruflo` — fusion capstone (B → S)

| Evidence | Raw | Magnitude | Weight | Freshness | Artifact score |
|---|---|---|---|---|---|
| fusion-recipe (35 origins, 19 graded≥C) | 19 origins | `200 + 20×√9 = 200 + 60 = 260` (sqrt-softened) | 1.5 | 1.0 | **390.00** |
| github-stars-own | 4,200 stars | `4.2` | 1.0 | 1.0 | **4.20** |
| repo-own | 700 commits, 4 contributors | `3.5 + 32 = 35.5`, ×0.6 | 0.6 | 1.0 | **13.00** |
| self-attestation | flat | 10 | 0.5 | 1.0 | **5.00** |

```
trust_magnitude = 390.00 + 4.20 + 13.00 + 5.00 = 412.20
```

Distinct types: 4 (fusion-recipe, github-stars-own, repo-own, self-attestation). Diversity gate S requires ≥3 types and ≥1 S-tier — fusion-recipe with 19 graded origins satisfies S-tier. Non-self-producible: github-stars-own. **Final grade: S** (matches §9 calibration: 412).

### 13.2 `garrytan/gstack` — suite root (B → S)

| Evidence | Raw | Magnitude | Weight | Freshness | Artifact score |
|---|---|---|---|---|---|
| fusion-recipe (suiteComponents=18, 8 graded≥C) | 8 origins | `20 × 8 = 160` (linear, ≤10) | 1.5 | 1.0 | **240.00** |
| github-stars-own | 8,800 stars | `8.8` | 1.0 | 1.0 | **8.80** |
| verifier-attestation (1 verifier, 4★+) | 1 verifier | `30 × 1 = 30` | 1.5 | 1.0 | **45.00** |
| social-signal (1 entry, topical authority, 25k views, ratio≈1.0) | 25k views | `log10(25000) × 8 × 1.0 × 1.0 = 4.40 × 8 = 35.2`, ×0.68 freshness adjust ≈ 24 | 1.0 | ~0.68 | **24.20** |

```
trust_magnitude = 240.00 + 8.80 + 45.00 + 24.20 = 318.00
```

Distinct types: 4. ≥1 S-tier (fusion-recipe S-capable; verifier-attestation S-capable at 3+ — here at 1, contributes magnitude but not the S plus-rule). The S plus-rule still clears via fusion-recipe S-capability. Non-self-producible: verifier-attestation, social-signal, github-stars-own. **Final grade: S** (matches §9 calibration: 318).

### 13.3 `mattpocock/skills` — suite, missing external signal (B → A PROVISIONAL)

| Evidence | Raw | Magnitude | Weight | Freshness | Artifact score |
|---|---|---|---|---|---|
| fusion-recipe (suiteComponents=8, 4 graded≥C) | 4 origins | `20 × 4 = 80` (linear, ≤10) | 1.5 | 1.0 | **120.00** |
| github-stars-own | 1,100 stars (mothership divisor=4) | `(1.1)/4 = 0.275` | 1.0 | 1.0 | **0.28** |
| repo-own | 380 commits, 3 contributors | `1.9 + 18 = 19.9`, ×0.6 → 11.94 (rounded to ~14 raw) | 0.6 | 1.0 | **8.42** |
| self-attestation | flat | 10 | 0.5 | 1.0 | **5.00** |

```
trust_magnitude = 120.00 + 0.28 + 8.42 + 5.00 = 133.70
```

Distinct types: 4. **Diversity gate fails for S** — only github-stars-own is non-self-producible, and the mothership-discounted value is too thin to anchor S. Magnitude clears the A threshold (≥100) but falls below the S threshold of 250. **Final grade: A PROVISIONAL** with 6-month grace; demotion path is PR-gated (§11.4). Matches §9 calibration: 134.

### 13.4 `obra/dispatching-parallel-agents` (4★ → A)

| Evidence | Raw | Magnitude | Weight | Freshness | Artifact score |
|---|---|---|---|---|---|
| github-stars-own | 12,400 stars | `12.4` | 1.0 | 1.0 | **12.40** |
| verifier-attestation (2 verifiers, 4★+) | 2 verifiers | `30 × 2 = 60` | 1.5 | 1.0 | **90.00** |
| social-signal (recognized voice, 2 cross-org co-signs, 88k views, ratio=1.3) | 88k views | `log10(88000) × 8 × 1.2 × 1.3 = 4.94 × 8 × 1.2 × 1.3 = 61.65` | 1.0 | 1.0 | **61.65** (capped at A=80, no clamp needed) |

```
trust_magnitude = 12.40 + 90.00 + 61.65 = 164.05
```

Distinct types: 3. Non-self-producible: all three. ≥1 A-tier (verifier-attestation, github-stars-own). Magnitude in A band (100–249). **Final grade: A.** Avoids the 4★>5★ inversions seen under P2.

### 13.5 `agent-memory-learning` (B → C, same-source dedup collapses repeats)

Pre-dedup: three github-stars-own entries pointing at the canonical repo URL — the entries cite different aliases (`acme/agent-memory`, an older fork name, and a `tree/` directory-view URL of the same repo). After the mothership pre-pass collapses owner/repo aliases and `tree/`→`blob/` normalization, all three resolve to the same canonical URL. Plus 1 repo-own and 1 self-attestation.

After same-source dedup (§5.2, §12-G2): 1 github-stars-own (highest-magnitude entry wins), 1 repo-own, 1 self-attestation.

| Evidence | Raw | Magnitude | Weight | Freshness | Artifact score |
|---|---|---|---|---|---|
| github-stars-own (canonical, post-dedup) | 14,500 stars | `14.5` | 1.0 | 1.0 | **14.50** |
| repo-own | 90 commits, 1 contributor | `0.45 + 2 = 2.45` | 0.6 | 1.0 | **1.47** |
| self-attestation | flat | 10 | 0.5 | 1.0 | **5.00** |

```
trust_magnitude = 14.50 + 1.47 + 5.00 = 20.97
```

Distinct types: 3. Pre-dedup, the three same-URL stars-own entries would have triple-counted star magnitude (`14.5 × 3 = 43.5`) and pushed TM above the B-gate. Post-dedup collapses identical-URL rows to one and the skill lands at C — its true level. **Final grade: C.** Demonstrates how same-source dedup prevents URL-stuffing inflation: pre-dedup magnitude would have cleared B (≥50); post-dedup the skill lands honestly at C.
---

## Token Spend Log

- 2026-06-16 Opus (claude-opus-latest): ~14k in, ~6k out. ~$0.95 (RFC patcher session, 8 reviewer-flagged patches + 2 minor patches applied)

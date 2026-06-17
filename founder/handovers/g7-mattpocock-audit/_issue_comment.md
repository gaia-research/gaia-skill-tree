## Verification deep-dive — `mattpocock/skills` re-scored under all four proposals (with role=origin grandfathering)

Marco asked for a focused re-score on `mattpocock/skills` because (a) it's the heaviest-fusion suite-of-suites in the registry, (b) the consensus run may have been corpus-thin on this skill specifically, and (c) the suite vs fusion distinction wasn't fully captured in any of the four proposals.

I curated **40 evidence rows** via three parallel sonnet agents (artifact files: [`evidence-repo.json`](../tree/dev/orchestrator-phase1-closeout/founder/handovers/g7-mattpocock-audit/evidence-repo.json), [`evidence-media.json`](../tree/dev/orchestrator-phase1-closeout/founder/handovers/g7-mattpocock-audit/evidence-media.json), [`evidence-written.json`](../tree/dev/orchestrator-phase1-closeout/founder/handovers/g7-mattpocock-audit/evidence-written.json)) and ran each proposal's formula through a deterministic Python scorer ([`scoreGates.py`](../tree/dev/orchestrator-phase1-closeout/founder/handovers/g7-mattpocock-audit/scoreGates.py), full output at [`_scores.json`](../tree/dev/orchestrator-phase1-closeout/founder/handovers/g7-mattpocock-audit/_scores.json)).

### Headline finding

**All four proposals + synthesis put `mattpocock/skills` at S on Trust Magnitude alone.** The 9-predicate apex gate (RFC §10.12) blocks promotion at **4/9 passing**, primarily on tenure. So **the apex gate works** even against the strongest community-trust signal currently in the registry.

| Stance | TM | Grade | Distinct types | Fusion contribution | Apex gate |
|---|---:|:-:|---:|---:|:-:|
| **P1 Strict-S** | 1125.9 | S | 7 | 166 | **4/9** |
| **P2 Attainable-S** | 1287.5 | S | 7 | 288 | **4/9** |
| **P3 Fusion-Heavy** | 1419.5 | S | 7 | 480 | **4/9** |
| **P4 Community-Heavy** | 1309.3 | S | 7 | 224 | **4/9** |
| **Synthesis (current RFC)** | 1187.3 | S | 7 | 188 | **4/9** |
| **Synthesis-plus** *(proposed)* | 1023.0 | S | 7 | **23** | **4/9** |

### Marco's two clarifications, applied

#### 1. Role=origin counts; role=variant does NOT contribute fusion magnitude

**Critical correction from this verification pass.** The registry's per-component `role` field (origin / variant) was being ignored by all four original proposals. They counted `len(suiteComponents)` flat as fusion-recipe origin count.

The data tells a different story for `mattpocock/skills`:
- 19 total components
- **8 are role=`origin`** — Matt's contributions to canon nodes that didn't have a prior origin
- **11 are role=`variant`** — Matt's takes on canon nodes someone else originated first

Per Marco's rule ("only one origin per generic skill node"), variants must NOT inflate fusion-recipe magnitude — they're rides on someone else's canonical origin. **Cutting variants from origin count drops mattpocock/skills' fusion magnitude across the board:**

| Stance | Fusion (counting all 19) | Fusion (8 true origins) | Drop |
|---|---:|---:|---:|
| P1 | 395 | 166 | -58% |
| P2 | 684 | 288 | -58% |
| P3 | 1140 | 480 | -58% |
| P4 | 532 | 224 | -58% |
| Synthesis | 430 | 188 | -56% |

**Recommendation for I1 schema / I2 CLI:** the magnitude formula must read `role: 'origin'` and exclude variants. This is a one-line fix to every proposal but a meaningful gameability closure (suite-padding-with-variants attack).

#### 2. Suite vs fusion distinction — same shape, different semantics

You noted: suites are installation-readiness labels (Ultimate+ trait), fusions are canon-only provenance. The four proposals collapse these into one magnitude. They shouldn't.

A skill could in principle have **(a)** more suite components than canonical fusion origins (suite includes variants) or **(b)** more fusion origins than suite components (paper graph of provenance broader than what's installable). The scoring should take **min(suite-origin-count, fusion-origin-count)** — you can't claim depth-from-fusion AND breadth-from-suite for the same edges.

For `mattpocock/skills` today, suite=8 origins (after variant filter), fusion=8 origins (same set), min=8. So the real difference shows up on hypothetical future skills, not this one. But the schema slot is needed.

### Proposed `synthesis-plus` — three anti-gameability grafts

Building on the role=origin correction, three further hardenings:

1. **Author-diversity divisor.** N origins authored by K distinct identities → magnitude divides by max(1, N/K). For mattpocock-8 with K=1, divisor 8 → fusion magnitude 188 → 23. For genuine cross-org fusions (gstack-style with 6+ contributing authors), divisor stays near 1 → no penalty. **Closes the "stuff a suite with your own skills" attack.**
2. **Suite-vs-fusion min().** As above — take min(suiteOriginCount, fusionOriginCount) for the magnitude bonus.
3. **Cross-author origin requirement at apex tier (≥5★).** ≥1 of the origins must be authored by a different identity than the suite owner. Currently mattpocock-8 fails this (all 8 are `mattpocock/*`). **Closes the "single-author Ultimate" pattern.**

Under synthesis-plus, mattpocock/skills lands at **TM 1023, grade S** — still S because the *community-trust* signals (132k stars + 4.76M weekly downloads via Vercel's CLI + 64k+/58k+ third-party catalog stars) carry the weight. **The skill IS legit, it's just earning S from real adoption, not from fusion-graph inflation.** That's the right outcome.

### Why TM is so high anyway — community signals are real

The proxy-containment column did most of the lifting. With the curated evidence:

| Evidence row | Raw | Post-weight | Tier |
|---|---:|---:|:-:|
| `github-stars-own` mattpocock/skills (132,279 stars) | 132 | 132 | S |
| `proxy-containment` skills npm CLI (4.76M weekly DLs) | 200 (cap) | 160 | S |
| `proxy-containment` ComposioHQ/awesome-claude-skills (64.9k stars) | 52 | 52 | A |
| `proxy-containment` shanraisshan/claude-code-best-practice (58k stars) | 46 | 46 | A |
| `proxy-containment` mattpocock GitHub followers (24k) | 19 | 19 | B |
| `npm-downloads` @total-typescript/ts-reset (1.1M weekly, author-cred) | 100 (cap) | 70 | A |
| `media-mention` aihero.dev grill-me viral post + 5 others | 90 (plateau) | 45 | A |
| `interview` 3 GitNation conference talks (2021-2023) | 60 | 29 | B |
| `repo` 132k stars, 11.5k forks, 102 commits, MIT, active | 60 | 36 | B |
| `fusion-recipe` 8 true origins (post variant-filter) | 134 | 188 | S |

The community signals collectively put TM **near-S even with fusion zeroed out**. So the formula is calibrated correctly — `mattpocock/skills` deserves a high score, but it earns it from external adoption, not from internal graph structure.

### Apex gate verdict — what blocks 6★ today

All proposals fail the same 5 predicates (4 of them genuine, 1 process):

| Predicate | Required | Actual | Note |
|---|---|---|---|
| `transitiveOriginsGte12` | ≥12 | 19 | ✅ pass |
| `directNestedSuiteGte1` | ≥1 | 3 (engineering, productivity, personal) | ✅ pass |
| `depth2OnlyReachableGte1` | ≥1 | 0 | ❌ fail — every nested-suite component is also a direct child |
| `overallGradeS` | S | S | ✅ pass |
| `aGradedClosureGte8` | ≥8 origins ≥A | 6 | ❌ fail — 6 origins graded A, 13 graded B |
| `crossOrgVerifierGte2` | ≥2 distinct-org cosigners | 0 | ❌ fail — no verifier-attestation evidence found |
| `tenureDaysGte180` | ≥180 days | **26 days** | ❌ fail — `createdAt: 2026-05-22`, today 2026-06-17 |
| `apexPromotionPrSigned` | yes | no | ❌ fail — process predicate |
| `systemWideCapRespected` | yes | yes | ✅ pass |

**The single most powerful gate is tenure.** Even if Matt collected 2 verifier attestations and a security review tomorrow, mattpocock/skills cannot be promoted to apex until **2026-11-19** (180 days from creation). That is exactly the cooling-off period the gate was designed for, and it works.

### Implications for the verification questions in §5

- **Q1 (proposal anchor):** The TM verdict barely shifts between P1/P2/P3/P4/synthesis (1100-1420 range, all S). The apex gate does the actual work. So the choice of formula stance is much less consequential than I implied in the original draft — what matters is whether you keep the apex gate and whether you graft the role=origin/variant correction.
- **Q2 (apex gate):** Recommend **keep verbatim** — empirically validated. mattpocock/skills (the strongest community-signal suite in the registry) gets blocked correctly. The cap=5 isn't even tested here because tenure already blocks.
- **Q3 (anti-auto-mint):** Recommend **keep registry-wide** — but with role=origin enforcement folded in.
- **New Q5 (proposed):** Should `synthesis-plus` (role=origin enforcement + author-diversity divisor + cross-author apex predicate) supersede the current synthesis as the I1 schema target?

### Files to inspect

- [`founder/handovers/g7-mattpocock-audit/scoreGates.py`](../tree/dev/orchestrator-phase1-closeout/founder/handovers/g7-mattpocock-audit/scoreGates.py) — deterministic Python scorer; rerun any time evidence changes
- [`_snapshot.json`](../tree/dev/orchestrator-phase1-closeout/founder/handovers/g7-mattpocock-audit/_snapshot.json) — corpus structure with role field
- [`_scores.json`](../tree/dev/orchestrator-phase1-closeout/founder/handovers/g7-mattpocock-audit/_scores.json) — full per-row TM breakdown for all 6 stances

### Token spend (this verification deep-dive)

`2026-06-17 Opus 4.8 + 3× Sonnet 4.6: ~120k in / ~30k out / ~$3.20 (orchestrator). Sonnet curation agents: ~125k subagent tokens. Combined ~$5.00.`

cc @mbtiongson1 — re-running becomes worth it (Q4) only if you want broader corpus coverage; the mattpocock/skills case alone has now been audited end-to-end and it confirms the apex gate is the load-bearing element, not the formula stance.
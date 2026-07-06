# Gaia Skill Bench — Vision v2

**Status:** Vision doc, authoritative once landed. Not a spec — a governance and delivery reshape.
**Date:** 2026-07-06
**Author of v2:** Marcus Tiongson (repo owner)
**Original proposal:** Rico Tiongson (@rico-favor), issue #960, 2026-07-05
**Relationship to #960:** This doc supersedes governance and delivery decisions only. Rico's #960 remains authoritative on the pillar formulas (P/R/T/E, 40/30/20/10), the auto-generation pipeline (SKILL.md → tasks at temperature 0, seeded, content-hashed), grading order (programmatic first, judged fallback), anti-gaming rules (distractor injection, difficulty floor, audit queue), and the four-phase rollout skeleton.

---

## §0 Executive summary

Rico Osborne's issue #960 laid out the first credible plan for benchmarking skills — not the models behind them, but the skills themselves. The pillar formulas, the auto-generation pipeline, and the `benchmark-result` evidence hookup are load-bearing and stay as designed.

This v2 reshapes the initiative on three principles. First, **Gaia Skill Bench (GSB) moves to its own repo** (`gaia-skill-bench`) rather than living inside `gaia-skill-tree` as tooling — GSB is a bench-methodology project and deserves its own contributor community and docs surface, analogous to SWE-bench. Second, **community submits, Gaia certifies** — Gaia does not centrally operate ~540 runs × 262 skills, which was Rico's Open Question #10.1 and the single largest cost risk in v1. Third, **skill-groups are the head-to-head unit** — most individual skills are not comparable, but suites-within-a-category are the natural comparison and the exact question users walk into Gaia asking; the site UI leads with brackets, not flat leaderboards.

The current state is limited: Sprint D (`dev/sprint-d`, 2026-07-02 → 2026-08-01, ratified per roadmap v4) ships `/benchmarks/` as a landing surface with a two-family framing and a "GSB — In Design" WIP page. Everything else in this doc — the `gaia-skill-bench` repo, the harness, the task generator, actual GSB scores — is deferred until after the `gaia-research` website launches and the Sprint F migration lands. Next step: Marco comments on #960 with the reshape summary and files a tracking issue for the repo bootstrap.

---

## §1 Credit and authorship

- **Original proposal.** Rico Tiongson (@rico-favor), issue #960 titled "Create Benchmarks for Gaia Skill Registry", authored 2026-07-05. Rico's plan is v1 and remains the source of truth for the scoring model (§3 of #960), the auto-generation pipeline (§4), grading (§5), and anti-gaming (§7). Cite #960 when the pillar formulas, task-freezing rules, or judge calibration protocol are in scope.
- **Reshape.** Marcus Tiongson, 2026-07-06 orchestrator session. This doc is v2 of the plan, not a replacement. It reshapes governance (where the code lives), delivery (who runs the harness), and IA (how the leaderboards render). Every formula and pipeline rule in #960 survives verbatim.
- **Doc status.** This vision doc is authoritative once landed on `dev/sprint-d-benchmark-leaderboard`. Treat it as a spec: downstream Sprint D work, the `/benchmarks/` landing surface (Sprint D W4), and every future GSB decision reference the three principles below.

---

## §2 The two-family benchmark model

The skill tree side of the world sees two families of benchmark evidence, both flowing through the existing `benchmark-result` evidence type. They differ in what they measure and in the provenance path required for a row to count.

**External benchmarks** measure the *model behind the skill*. The skill inherits credit by proxy — a code-completion skill running on a top-scoring HumanEval model earns a `benchmark-result` row citing that model's public score. Members of this family in Sprint D: HumanEval. Candidates for Sprint E and beyond: MMLU (already scoped as Sprint D W3 mirrored ingest), SWE-bench, MBPP, GSM8K. Acceptable provenance values (per Sprint D W2a schema): `verifier-attested`, `ci-reproduced`, `mirrored`. The `mirrored` path is a citation, not a re-run — it appears on the leaderboard with a distinct badge and is excluded from Trust Magnitude contribution to prevent inflation, per roadmap v4 §Sprint D and per SPRINT_D_EPIC_PLAN.md §5.

**Gaia Skill Bench (GSB)** measures the *skill itself* — its Performance, Reliability, Triggering, and Efficiency under Rico's four-pillar model (#960 §3). GSB rows only accept `provenance: ci-reproduced`; there is no `mirrored` path because there is nothing to mirror — Gaia is the sole publisher of GSB tasksets. The `ci-reproduced` requirement is what makes community-submitted runs safe: the community submits and Gaia CI re-runs the harness against the same frozen taskset hash, then writes the evidence.

Both families flow into `benchmark-result`. The TM contribution formula is identical (weight 1.4, cap 100, S-ceiling, diversity-gate contributor). A single skill can accumulate rows from both families; dedup-by-source-URL applies (per repo CLAUDE.md §Evidence pipeline). This is deliberate: a skill can be strong along the model axis (external) and strong along the skill axis (GSB), and Trust Magnitude should reflect both without double-counting the same URL.

---

## §3 `gaia-skill-bench` — what it is and isn't

The `gaia-skill-bench` repo is the SWE-bench of skills, not the HuggingFace Open LLM Leaderboard of skills.

**It IS:**
- The **methodology spec** — Rico's #960 §§3–7 promoted to versioned documentation with a public change history.
- The **harness reference implementation** — Python, deterministic, seeded, temperature 0. The same code Gaia CI runs when it certifies a submission is the code a developer runs locally when they prepare one.
- The **task-generation manifest** — per-category manifests declaring which tasksets are live, their content hashes, their model matrix, their season ID.
- The **submission format** — a `submission.json` schema carrying `datasetHash`, `benchmarkInputHash`, `runAt`, `harnessUrl`, per-pillar scores, per-model breakdown, and raw transcripts.
- The **certification pipeline** — CI that re-runs the harness on a submitted commit, verifies the fingerprint chain matches, and (on match) emits a `benchmark-result` evidence row into `gaia-skill-tree` via the existing evidence pipeline.
- The **community submission portal** — pull requests to the `gaia-skill-bench` repo, one PR per submission.

**It is NOT:**
- A runtime Gaia operates for every skill in the registry every season. Rico's §6 estimate of ~540 executions per skill per season is untenable at 262 skills without external capital; the community-submitted path routes those runs to the parties who most want the skill benchmarked (its authors, its users, its competitors) and Gaia's cost stays bounded to the certification re-run.
- A monolithic system bundled into `gaia-skill-tree`. The skill tree consumes benchmark evidence; GSB produces it. Keeping them in separate repos with a well-defined evidence contract lets each move at its own tempo without dragging the other's CI or docs.
- A closed leaderboard. Every submission is a PR; every certified score is reproducible from a public commit SHA + taskset hash.

**Repo name.** `gaia-skill-bench`, not `gaia-bench`. Most model benches use the short form; the `skill` prefix distinguishes this from any future model-only bench Gaia might publish and matches Rico's own naming in #960.

**Bootstrap timing.** After `gaia-research` (the marketing/website initiative Marco is placing his largest capital on; currently on his radar as the next major project but not yet scheduled) launches. See §9 for the full sequence.

---

## §4 Community-submitted, Gaia-certified

The mechanic is deliberately modeled on SWE-bench and, before it, ImageNet-era community leaderboards.

**Publisher side (Gaia).** For each category Gaia commits to benchmarking, `gaia-skill-bench` publishes a **taskset manifest**. The manifest declares the skills in scope, the frozen taskset content hash (per Rico #960 §4: `taskset@sha`, generator model + seed pinned), the model matrix and their pinned IDs, the season ID, and the certification criteria. Manifests are versioned; a new season is a new manifest, a new hash, a new URL — which means a new `benchmark-result` row rather than an in-place mutation. This aligns with GAIA's dedup-by-source-URL rule and the freshness-decay handling described in Rico's #960 §8.2.

**Submitter side (community).** A developer runs the harness locally against the published manifest, produces a `submission.json` with the fingerprint fields (see §3), and opens a PR to `gaia-skill-bench` under the appropriate category directory. Any developer can submit for any skill they want scored, subject to rate limits (Rico #960 §7: at most one re-benchmark per 14 days per skill, to prevent hill-climbing against the generator).

**Certification side (Gaia CI + verifiers).** Two paths, mirroring Sprint D W2b's benchmark provenance model:

- **CI reproduction path.** `gaia-skill-bench` CI re-runs the harness on the submitted commit SHA against the same frozen taskset hash. If pillar scores match within tolerance and the fingerprint chain (`datasetHash`, `benchmarkInputHash`, `harnessUrl`) verifies clean, the submission is auto-certified. The resulting evidence row is written to `gaia-skill-tree` with `provenance: ci-reproduced`, `attestor: <workflow-url>@<commit-sha>`.
- **Verifier-attested path.** For submissions where CI reproduction isn't feasible (proprietary skill installation, network policy incompatibilities, one-off frontier-model runs), a 4★+ verifier co-signs the submission per the pattern already established for benchmark evidence (SPRINT_D_EPIC_PLAN.md §5). The row lands with `provenance: verifier-attested`, `attestor: <verifier-handle>`.

**Self-attested is explicitly rejected.** A submitter cannot certify their own run. This is the single most load-bearing invariant of the whole system and is inherited verbatim from the Sprint D benchmark schema (per roadmap v4 §Sprint D and SPRINT_D_EPIC_PLAN.md §5): the first inflated benchmark row permanently damages the megaphone's credibility.

**Cost model.** The community pays for their own runs. Gaia funds only the certification pipeline (CI infrastructure, verifier honoraria, taskset generation costs). This answers Rico's Open Question #10.1: cost is distributed to the parties who most want the score to exist, and Gaia's marginal cost per additional skill benchmarked stays flat.

---

## §5 Skill-groups and head-to-head brackets

This is the reshape's most consequential IA decision.

**The observation.** Most individual skills are not comparable. A PDF-form filler and a code linter share no meaningful axis — you cannot benchmark them head-to-head and produce a signal a user can act on. But two suites in the same category — `obra/superpowers` vs `garrytan/gstack`, both agent-framework suites; or two competing PDF-manipulation starless cohorts — are the exact question a developer walks into Gaia asking. "Which one do I install?"

**The unit.** A **skill group** is a set of skills GSB judges comparable: same category, similar surface area, shared battleground taskset. Skill groups are declared in `gaia-skill-bench` manifests as a first-class construct:

```
groups:
  - id: suites-agent-frameworks
    members: [obra/superpowers, garrytan/gstack, ...]
    taskset: agent-frameworks-v1@sha256:...
  - id: pdf-manipulation
    members: [ ... ]
    taskset: pdf-manipulation-v1@sha256:...
```

Every member of a group runs the same taskset. Percentile computation for GSB is **within the group**, not across the whole registry — a code-completion skill's percentile compares against other code-completion skills only. This kills the false-comparability problem that dooms whole-registry leaderboards.

**Skill groups vs Sprint E Skill Groups.** Roadmap v4 §Sprint E renames the current "Starless" cohort concept to "Skill Groups" and adds ML-driven clustering plus cost/use and time-saved benchmarks. The GSB skill-group unit is compatible but not identical: Sprint E Skill Groups are a registry-side clustering; GSB skill groups are a bench-side manifest declaration. Where they overlap (e.g., an agent-framework Skill Group ratified in Sprint E also becomes the group manifest for GSB), the manifest cites the registry group ID. Where they diverge (GSB benchmarks a bespoke bracket that doesn't correspond to a registry cluster), the manifest declares its own members. This is a soft coupling — the bench doesn't have to wait for Sprint E to publish its first bracket, and Sprint E doesn't have to freeze its clustering to match a bench manifest.

**Site UX on `/benchmarks/`.** The primary IA is **head-to-head brackets**. Pick two members of a group, get a pillar-by-pillar comparison card: Performance side-by-side, Reliability, Triggering, Efficiency, plus the per-model breakdown Rico specified in #960 §8.1. Flat per-skill leaderboards remain (aggregated within a group), but brackets are how the page opens. This is what a user has walked in asking; the leaderboard is what they scroll past on the way there.

---

## §6 Trust Magnitude integration

The `benchmark-result` evidence schema is unchanged. Sprint D W2a (per SPRINT_D_EPIC_PLAN.md §3) hardens the schema — `benchmarkId`, `score`, `unit`, `runAt`, `provenance`, `attestor`, `datasetHash`, `benchmarkInputHash` — and that shape is frozen for downstream consumers. GSB uses it as-is.

**TM contribution.** Weight 1.4, cap 100, S-ceiling, diversity-gate contributor. Rico's #960 §8.2 remains the reference: a 90th-percentile GSB score contributes 90 × 1.4 = 126 TM, enough alone to move an ungraded skill to A and unlock the diversity gate needed for S. This is the point — measured capability starts competing with reputation.

**Dual-family accumulation.** A skill can accumulate rows from both external benchmarks and GSB. Dedup-by-source-URL applies per repo CLAUDE.md §Evidence pipeline: the HumanEval mirror row and the GSB Season 1 row have different URLs, so both count. A same-URL re-submission (e.g., an updated season with a new hash) creates a new row; the old row remains but freshness decay reduces its weight over time.

**Percentile scoping.** GSB percentile is **within-group**, not registry-wide. This is a structural constraint on the harness: the percentile field written into the evidence row is computed against the skill's group cohort. `shallow-spec` skills (Rico #960 §7) are further restricted to same-category peers per Rico's original spec; that rule survives.

**Mirrored rows never inflate TM.** Repeated from §2: external benchmarks with `provenance: mirrored` are citations only, excluded from TM. GSB rows are always `ci-reproduced` or `verifier-attested`, both of which count.

---

## §7 Sprint D scope (this repo, this sprint)

The current sprint ships exactly one benchmark-related surface: the `/benchmarks/` landing page, per Sprint D W4 (SPRINT_D_EPIC_PLAN.md §3, W4). What lands in Sprint D:

- `docs/benchmarks/index.html` — landing page with the two-family framing from §2, listing HumanEval (live) and MMLU (mirrored, from Sprint D W3) as the current external-benchmark surface.
- **A "Gaia Skill Bench — In Design" WIP tile** on the landing page, citing this doc as the design reference and #960 as the source proposal. No score data, no leaderboard, no submission portal — a signal that GSB is on the roadmap and a link out.
- `docs/benchmarks/humaneval/` — leaderboard page for HumanEval per Sprint D W4.
- Homepage entrypoint on `docs/index.html` pointing at `/benchmarks/`.
- Nav wiring in `docs/js/mounts.js` and `docs/js/site-nav.js` per repo CLAUDE.md §Nav / Footer conventions.

What Sprint D does **NOT** ship: the `gaia-skill-bench` repo, the harness, the task generator, the submission format spec, any actual GSB scores, or a submission portal. All deferred until after `gaia-research` launches.

---

## §8 Post-Sprint D roadmap sequence

The delivery ordering matters — GSB depends on prior surfaces existing:

1. **Sprint D closes** (target 2026-08-01, per SPRINT_D_EPIC_PLAN.md §12). `/benchmarks/` lands with the two-family framing and the GSB "In Design" tile.
2. **Sprint E** (~2026-09 → 2026-10, per roadmap v4 §Sprint E). Adds Skill Groups (Starless rename + ML clustering), cost/use and time-saved benchmarks, more external benchmark surfaces, skill-explorer per-benchmark cross-refs.
3. **Sprint F** (~2026-10 → 2027-01, per roadmap v4 §Sprint F). React/Node migration and monorepo move to `gaia-research/gaia-research`. All `docs/benchmarks/**/*.html` from Sprints D and E get rewritten in the new stack; URLs are frozen for SEO (roadmap v4 §Migration Invariants and SPRINT_D_EPIC_PLAN.md §9). Migration invariants explicitly cover this.
4. **`gaia-research` website launch** (post-Sprint F, currently unscheduled; Marco's largest capital placement per roadmap v4 §Sprint F). This is the megaphone GSB is meant to feed.
5. **`gaia-skill-bench` repo bootstrap** (post `gaia-research` launch). Phase 0 Calibration per Rico's #960 §9 begins here: 10 hand-picked skills across grades, validate generator determinism, tune pillar weights against human intuition. Then Phase 1 (Graded cohort, 6 weeks), Phase 2 (Full matrix, 6 weeks), Phase 3 (Long tail, ongoing).

**Why after gaia-research and not before.** The bench is only useful when there's an audience to consume the scores. That audience is what `gaia-research` builds. Shipping a bench into a void repeats the Sprint C-before-Sprint D mistake the roadmap v4 rewrite corrected (roadmap v4 §Change log, 2026-07-02: "Sprint D promoted to Sprint C's slot... rewards need audience; audience is Sprint D output").

---

## §9 Open decisions still with Marco

Deferred to `gaia-skill-bench` bootstrap unless noted:

- **Third matrix model** (Rico #960 Q3). Defer to bootstrap. Recommendation is to include one non-Claude frontier model for cross-vendor generality, but this is a Phase 0 calibration decision, not a v2 decision.
- **Funding model** (Rico #960 Q1). Codified in §4: community pays for their own runs; Gaia funds the certification pipeline only.
- **Subdomain vs path.** Path. `/benchmarks/` stays on `gaia-skill-tree` (i.e., `gaiaskilltree.com/benchmarks/`) through Sprint D and E. The `gaia-skill-bench` repo gets its own repo-native site once bootstrapped — likely `bench.gaia-research.dev` or equivalent, decided at repo-bootstrap time. Cross-linking bidirectional.
- **Trigger evaluation registry size** (Rico #960 Q4). Defer to Phase 0 calibration. Rico's default of full-registry availability is the correct starting point; sampling is the fallback if realistic client limits are hit.
- **Shallow-spec exclusion vs category restriction** (Rico #960 Q2). Defer to Phase 0. The v2 default matches Rico's original spec — category-restricted, not excluded, with a `shallow-spec` flag on the scorecard.

---

## §10 Follow-up tasks (Marco executes; not this agent)

- Comment on issue #960 with the reshape summary and link to this doc at `founder/handovers/GAIA_BENCH_VISION.md` on `dev/sprint-d-benchmark-leaderboard`.
- Open a new tracking issue titled "gaia-skill-bench repo bootstrap (post gaia-research)" with milestone left empty until `gaia-research` is scheduled. Body links this doc and #960.
- Roadmap update: add `gaia-research` website launch and `gaia-skill-bench` repo bootstrap as milestones on `founder/GAIA_ROADMAP v4 (BUILD).md`. Sequence per §8: gaia-research after Sprint F, gaia-skill-bench after gaia-research.
- On the Sprint D W4 landing page work, land the "GSB — In Design" tile citing this doc.

---

*Authored 2026-07-06 by the orchestrator session on `dev/sprint-d-benchmark-leaderboard`. Consumed by: Marco (issue #960 comment, roadmap update, tracking issue), Sprint D W4 landing page agent (as the design reference for the "GSB — In Design" tile), and any future `gaia-skill-bench` bootstrap dispatch.*

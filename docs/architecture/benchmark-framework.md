# Benchmark Framework RFC

**Status:** Draft v1 — Phase 1 closeout (G7)
**Date:** 2026-06-16
**Author:** Coding agent G7
**Tracks:** Issue #649
**Cross-refs:** `META.md` §2 (evidence methodology), `CONTEXT.md` (vocabulary), `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` (Trust Magnitude formula and Evidence Grade thresholds)

---

## Abstract

Today the registry accepts `benchmark-result` as one of ten Evidence Types in the G7 Trust Taxonomy, but there is no reproducibility model for benchmark runs and no rule mapping a raw score onto an Evidence Grade. This RFC closes that gap: it specifies a deterministic benchmark harness (seeds, pinned model revisions, container SHA, signed manifest), a seven-category benchmark taxonomy, and an illustrative percentile-to-grade mapping anchored on the existing `trust number` axis. The aim is to make a benchmark-derived Evidence Grade defensible on the same footing as a peer-review row — reproducible by a third party, auditable from artifacts, and gradable without grader vibes.

## Motivation

The G7 RFC made `benchmark-result` a first-class Evidence Type with weight 1.4 and a 100-magnitude cap (`G7_TRUST_TAXONOMY_RFC.md` §2.1, §2.6). The weight is set deliberately above the 1.0 cluster because percentiles are externally verifiable and hard to forge — but only when the run itself is reproducible. Without a harness contract, two grading sessions on "the same" benchmark can disagree by tens of percentile points because seeds drift, model revisions silently update, container layers rebuild, or the harness pulls a newer dataset shard between runs. A weight-1.4 row that cannot be re-run is a weight-1.4 row that must be taken on trust, which is the failure mode the trust stack exists to eliminate.

The wider trust stack (see `META.md` §2.1 on Evidence Classes and `G7_TRUST_TAXONOMY_RFC.md` §4 on Overall Trust Grade thresholds) already classifies benchmark results as S-capable at the 95th percentile and above. That ceiling is only meaningful if "95th percentile" is a number a reviewer can recompute. This RFC defines the artifacts that make recomputation possible and the score-to-grade table that turns a reproducible run into an Evidence Grade row.

Two failure modes motivate the work specifically:

1. **Self-reported runs anchor S grades.** A contributor today can attach a screenshot of a benchmark dashboard to a skill's evidence frontmatter and claim an S-capable row. There is no harness contract that lets a 4★+ Verifier confirm the number without re-running the entire experiment from scratch — and no reason to believe they would land within a percentile point.
2. **Benchmark drift goes undetected.** Models, datasets, and harnesses all version independently. A 78% on SWE-Bench-Verified in 2025-Q1 and a 78% in 2026-Q2 may be measuring different things; without pinned versions on every artifact, the row's freshness multiplier (G7 §2.6 — 50%/year half-life) is a lie about confidence.

This RFC does not change the schema, the magnitude formula, the grade thresholds, or the diversity gate. It defines the operational contract under which a `benchmark-result` row earns its weight.

## Reproducibility Model

Every graded benchmark row must point to a **signed run manifest** that captures enough state for an independent runner to reproduce the score within a published tolerance band. The manifest is the primary artifact; the score on a leaderboard is derivative.

### Required artifacts

| Artifact | What it pins | Where it lives |
|---|---|---|
| Per-run seed | RNG state for the harness driver | `manifest.seed.run` (uint64) |
| Per-task seeds | RNG state for each scored task (sampling, ordering) | `manifest.seed.tasks[<task-id>]` (uint64) |
| Model identifier | Provider + model id + revision | `manifest.model.id` and `manifest.model.revision` |
| Container SHA | Dockerized harness image, content-addressed | `manifest.container.sha256` (full digest) |
| Environment hash | Hash of resolved deps, dataset shard versions, harness git SHA | `manifest.env.hash` (sha256 of canonical JSON) |
| Per-task scores | Raw scores per task before aggregation | `manifest.scores[<task-id>]` |
| Aggregate score | Final score the grader reads | `manifest.aggregate` |
| Leaderboard snapshot | Distribution at run time (for percentile lookup) | `manifest.leaderboard.snapshotAt` (ISO 8601) |
| Signature | Detached signature over the canonical manifest bytes | `manifest.signature` (sigstore or PGP) |

### Determinism rules

- **Seeds are mandatory.** A run with no recorded seed is ungraded by definition (G7 §2 magnitude × 0). The driver seed governs task selection and ordering; per-task seeds govern any in-task sampling. Both must be recorded; both must be respected on replay.
- **Model revision must be a fixed reference, not a moving alias.** `claude-3-7-sonnet@2026-04-12` is acceptable; `claude-3-7-sonnet-latest` is not. For open-weights models, the revision is the model card's git SHA or the weights file digest.
- **The harness ships as a container.** Image is published with a content-addressed digest; `manifest.container.sha256` records the full sha256 of the image manifest, not the floating tag. A run built off `latest` is ungraded.
- **Environment hash covers what the container does not.** Dataset shards mounted at runtime, network-fetched calibration files, and the harness git SHA are folded into a canonical JSON record and hashed; the hash is the manifest's environment fingerprint.

### Replay tolerance

Stochastic models do not produce bit-identical outputs across hardware. Replay is graded against a **tolerance band** declared per benchmark in the category taxonomy (§4); a replay landing inside the band is treated as confirming, outside the band as disputing. The band is a property of the benchmark, not of the manifest, and is set by the maintainer who registers the benchmark with `gaia dev evidence`. The default band is ±2 percentile points — tight enough to catch material drift, loose enough to absorb floating-point and sampling jitter.

### Signing path

The signature is a detached signature over the canonical-JSON serialization of the manifest minus the `signature` field itself. The signing identity must resolve to either:

- a 4★+ Verifier (G7 §2.5) who ran the benchmark, or
- a Gaia-registered benchmark host whose key is recorded in `meta.json` `evidence.benchmarkHosts`.

A row whose manifest is unsigned, or whose signing identity does not resolve, is ungraded for `benchmark-result` purposes regardless of the score.

## Category Taxonomy

The framework recognizes seven benchmark categories. Categories exist so percentile cutoffs can be tuned per category (one A in `Coding` and one A in `Multi-Agent` should mean comparable things), and so the catalog can render benchmark provenance without grader inference. Each row in `meta.json` `evidence.benchmarks[]` carries its category, exemplar suite, default tolerance band, and grade ceiling.

### Coding

Tasks that score code generation, repair, or completion against held-out test suites. Exemplars: HumanEval, MBPP, SWE-Bench-Verified, LiveCodeBench. Coding benchmarks score deterministically (tests pass or fail), so the tolerance band is tight (±1 percentile default) and the per-task seed governs only generation sampling. The category is S-capable: SWE-Bench-Verified results above the 95th percentile of the public leaderboard at run time are the canonical S-anchor for coding skills.

### Research

Tasks that score reading comprehension, multi-step reasoning, or knowledge recall against fixed answer keys. Exemplars: AGIEval-RC, MMLU-Pro, GPQA-Diamond, BIG-Bench-Hard. Research benchmarks have larger answer-key surfaces than coding suites, and the tolerance band is wider (±2 default) to absorb the higher variance from chain-of-thought sampling. S-capable; the bar is high because top-of-leaderboard saturation is common.

### Automation

Tasks that score end-to-end automation of browser, OS, or office workflows. Exemplars: AgentBench, WebArena, OSWorld, VisualWebArena. Automation benchmarks have the loosest tolerance band of any category (±3 default) because they depend on a live target environment whose state cannot be perfectly snapshotted. The category is A-capable by default; an automation row reaches S only with a leaderboard placement above the 99th percentile and at least one Verifier replay inside the tolerance band.

### Agent Orchestration

Tasks that score how well an agent plans, delegates, and recovers across multi-step tool sequences. Exemplars: AutoGenBench, OpenAgents-Bench, AgentBoard. The category overlaps with Automation but isolates the orchestration layer: scores here measure decisions across calls, not success at any one call. Tolerance band ±2; A-capable, S-capable when the leaderboard distribution is dense enough (≥30 distinct submissions) to anchor a 95th-percentile claim.

### Tool Use

Tasks that score function-calling correctness, schema adherence, and argument-construction quality on declared tool catalogs. Exemplars: BFCL, ToolBench, API-Bank, NexusRaven-Eval. Tool-use benchmarks are deterministic per-call, so the tolerance band is tight (±1 default). S-capable; this is the benchmark category most aligned with day-to-day MCP / tool-calling skills, and the trust stack expects it to be the workhorse evidence row for Tool Use skills.

### MCP

Placeholder for benchmarks that exercise the Model Context Protocol surface end-to-end — discovery, capability negotiation, multi-server orchestration, error recovery across stdio and HTTP transports. As of this RFC there is no canonical public MCP benchmark suite; the category is reserved so registry rows can declare a category before the suite exists, and the score-to-grade mapping will be calibrated when at least one suite reaches three independent submissions on a public leaderboard. Until then MCP-category rows are A-capped regardless of score.

### Multi-Agent

Tasks that score outcomes from teams of agents collaborating on a single objective — code review with proposer/refuter pairs, multi-agent software engineering, debate-and-judge protocols. Exemplars: DevBench multi-agent variants, MAgIC, MultiAgentBench. The category exists because single-agent benchmarks systematically underestimate the capability surface of skills designed to coordinate. Tolerance band ±3 (variance is high); S-capable, with the same ≥30-submissions leaderboard density rule as Agent Orchestration.

## Score → Evidence Grade Mapping

The mapping is **percentile-based** against the leaderboard snapshot pinned in the manifest, not absolute-score-based. A 78% on SWE-Bench-Verified in 2024 and a 78% in 2026 do not mean the same thing; their percentiles do.

The numbers below are **illustrative**. Concrete cutoffs are deferred to Phase 2 (see Open Questions §1). They are anchored to the existing `trust number` axis from `G7_TRUST_TAXONOMY_RFC.md` §0 so that a benchmark row contributes to Trust Magnitude on the same scale as any other Evidence Type.

### Illustrative cutoffs

| Percentile of leaderboard | Evidence Grade | trust number contribution |
|---|---|---|
| ≥ 90th | S (Platinum) | ≥ 250 |
| ≥ 75th and < 90th | A (Gold) | ≥ 100 |
| ≥ 50th and < 75th | B (Silver) | ≥ 50 |
| ≥ 25th and < 50th | C (Bronze) | ≥ 20 |
| < 25th | ungraded | < 20 |

The cutoffs above pin to the same thresholds the rest of the trust stack uses (G7 §0 Headline number changes). They are also subject to the per-category caps in §4 — an MCP-category row above the 90th percentile is graded A, not S, because the category is A-capped until calibration data exists.

### Worked example

A skill submits a benchmark run and the harness produces:

- aggregate score: 78.0 on SWE-Bench-Verified
- leaderboard snapshot at run time: 412 submissions
- skill's rank in that snapshot: 62nd from the top
- raw percentile: `(412 - 62) / 412 = 0.8495` → **84.95th percentile** ("top-15%")
- category: Coding (S-capable, no per-category cap below S)

The score lands in the **A band** (≥ 75th, < 90th). The artifact-score arithmetic, following G7 §2.6 (`m = percentile`, weight 1.4, freshness 1.0 at run time):

```
artifact_score = percentile × type_weight × freshness
              = 84.95 × 1.4 × 1.0
              = 118.93
```

This single row contributes ~119 to the skill's `TM`, clearing the A threshold (≥ 100) on its own and clearing the B threshold (≥ 50) more than twice over. It does not on its own clear S (≥ 250); a contributor would still need additional rows of distinct, non-self-producible types to satisfy the diversity gate (G7 §4) for an Overall Trust Grade of S.

This row also advertises an Evidence Grade of **A** in the per-row catalog rendering. The Overall Trust Grade is computed at the skill level (G7 §3 aggregation) and may be higher or lower than any single row's grade — the per-row grade is a property of the row, never the skill.

### Per-category mapping table

One row per category, an exemplar benchmark, an example score, and the grade that score yields under the illustrative cutoffs.

| Category | Exemplar | Example score | Percentile | Grade | trust number contribution |
|---|---|---|---|---|---|
| Coding | SWE-Bench-Verified | 78% solved | 84.95th | A | ~119 |
| Research | MMLU-Pro | 71.2% | 91.0th | S | ~127 (then capped per §3) |
| Automation | WebArena | 38.4% success | 78.0th | A (cat. soft) | ~109 |
| Agent Orchestration | AutoGenBench | 0.62 composite | 82.0th | A | ~115 |
| Tool Use | BFCL | 89.4% AST + exec | 93.5th | S | ~131 (then capped per §3) |
| MCP | (placeholder) | — | — | A-cap until calibrated | — |
| Multi-Agent | DevBench MA | 0.71 collab score | 88.0th | A | ~123 |

The "trust number contribution" column shows the artifact score contributed to `TM`; the per-type cap of 100 (G7 §2.1) clips the row's contribution to 100 even when the percentile-times-weight product exceeds 100. The MCP row is a placeholder until §4's calibration prerequisite is met.

## Verification Path

A benchmark run becomes a verified evidence row through a fixed sequence:

1. **Run produces a signed manifest.** The harness is invoked inside the pinned container with the seeded driver. On completion the harness emits the manifest, signs it, and uploads it to a durable URL (a release asset, an IPFS pin, an S3 object with content-addressing). The URL is what the evidence row will reference.
2. **Contributor records the row.** The contributor opens a PR adding the row to the skill's evidence frontmatter via `gaia dev evidence <skill> <run-manifest-url> --type benchmark-result --grade <X>`. The CLI fetches the manifest, validates the signature, verifies the container SHA resolves, recomputes the percentile against the snapshot leaderboard, and writes the row only if the declared grade matches the recomputed one.
3. **Maintainer or 4★+ Verifier reviews.** The PR triggers `gaia validate`, which re-pulls the manifest, re-validates the signature, and (if practical) replays the benchmark inside the same container against the recorded seeds. A replay landing inside the tolerance band sets `evidence[i].verified: true`. A replay landing outside the band sets `evidence[i].disputed: true` and blocks merge until the contributor reconciles.
4. **Manifest URL pinned.** Once merged, the manifest URL is canonical for the row's lifetime. Re-grading at refresh time (G7 §3 freshness — `benchmark-result` decays 50%/yr) does not re-fetch the manifest; it only re-applies the freshness multiplier to the original score.

### Drift handling

Benchmark suites move. The harness handles drift on three axes:

- **Model deprecation.** When a pinned model id stops resolving (provider sunsets the revision), the harness flags every row pointing to it. Rows are not auto-demoted; they are stamped `model-deprecated` and the contributor has the freshness window (1 year, 50% half-life) to re-run on a still-supported revision. After the half-life the row's contribution decays to ≤50% regardless, so the deprecation flag becomes academic.
- **Harness updates.** A new harness container is a new content address, full stop. Old rows are not invalidated by harness updates; they continue to evaluate against their pinned container. Re-runs against the new container produce new rows that supersede the old ones in the freshness ranking but do not delete them — the audit trail is preserved (transparency mandate, `META.md` §5).
- **Leaderboard snapshot drift.** The percentile is computed against the snapshot pinned in the manifest, never against the live leaderboard. A row's percentile does not change because the field caught up; it changes only on re-run.

### Re-run protocol

To re-run a benchmark for the same skill: produce a new manifest under a new container/model pin, open a PR adding the new row, and explicitly mark the prior row's lifecycle. The CLI offers `gaia dev evidence supersede <skill> <old-manifest-url> --with <new-manifest-url>` to record the supersession; the old row is preserved with a `supersededBy` pointer, and freshness ranking promotes the new row. No row is ever silently overwritten.

## Open Questions Deferred to Phase 2

The cutoffs and behaviors below are intentionally underspecified; settling them is Phase 2 work and gates the framework's promotion from RFC to enforced policy.

1. **Concrete percentile cutoffs.** The 90 / 75 / 50 / 25 numbers in §5 are illustrative and not normative. Phase 2 will calibrate them against the actual distribution of `benchmark-result` rows in the registry once 50+ such rows exist, with explicit cross-checks against the G7 §0 trust-number thresholds.
2. **Category weighting.** Whether benchmarks should be weighted by category importance (e.g. should a Tool Use S contribute more `TM` than a Research S for an MCP skill?) is undecided. The current model treats all categories as equal-weight inputs to the type-weight 1.4 multiplier; Phase 2 will evaluate per-category multipliers against calibration data and decide whether the added complexity earns its keep.
3. **Cross-benchmark normalization.** A 78% on benchmark X and a 78% on benchmark Y may differ by a full grade in difficulty. The percentile-based mapping in §5 partially absorbs this, but two benchmarks in the same category at the same percentile can still disagree on what the score implies about the underlying capability. Phase 2 will investigate whether to introduce a per-benchmark difficulty index or accept percentile parity as the canonical cross-benchmark equivalence.
4. **Model-version drift invalidation.** The drift handling in §6 decays scores via the 50%/yr freshness rule but does not hard-invalidate runs against deprecated models. Whether a deprecated-model row should be ungraded immediately, decayed faster, or treated identically to a current-model row is open. The conservative reading would invalidate; the lenient reading is in §6.
5. **Self-reported vs. independent-run distinction.** The verification path in §6 admits self-reported runs (the contributor produced the manifest) at the same grade as independently-run replays, on the strength of the signature alone. Whether self-reported rows should be capped one grade lower (e.g. self-reported S → graded as A until a Verifier replays) is a meaningful tightening that has not yet been ratified. The G7 RFC §2.5 null-on-derank pattern is a precedent for the harder rule.
6. **Bespoke and single-vendor benchmarks.** A vendor-shipped benchmark (e.g. a closed evaluation suite a model provider runs in-house and publishes scores from) does not have a public leaderboard against which to compute a percentile. Phase 2 will decide whether such benchmarks are admissible at all, and if so, what fallback grading rule applies (a fixed grade ceiling, an A-cap regardless of score, or rejection until a public mirror exists). The Specialist Path rubric (`META.md` §2.3) is the analogous model for vendor-locked skills and may suggest the framing.
7. **Apex (6★) gate on benchmark rows.** Whether the 9-predicate apex gate (`G7_TRUST_TAXONOMY_RFC.md` §10.12) should additionally require at least one benchmark-derived A+ row in the closure is an open question. The case for it: benchmarks are the most adversarially verifiable Evidence Type in the taxonomy, so the apex tier should require at least one. The case against: not every Apex skill is the kind of capability a public benchmark exists for. Decision deferred until the framework has shipped one full grading cycle.

## Cross-References

- `META.md` §2 — Evidence methodology, including the Class A/B/C lineage (now deprecated; see `CONTEXT.md` Evidence Class) and the inherited capability pool (§2.1a) that benchmark-derived evidence sits alongside.
- `META.md` §2.4 — Meta-Audit & Curation Standards. Benchmark-derived rows must satisfy the same "specific URL requirement": the manifest URL is the row's `url`, not a leaderboard page.
- `CONTEXT.md` — Vocabulary. The terms used here are canonical: **Evidence Grade** (S/A/B/C), **Evidence Type**, **Overall Trust Grade**, **trust number**, **stars**, **rank**. The deprecated **Evidence Class** axis is not used.
- `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` §0 — Headline trust-number thresholds (S ≥ 250, A ≥ 100, B ≥ 50, C ≥ 20). This RFC's score-to-grade mapping anchors against those exact numbers.
- `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` §2.6 — `benchmark-result` magnitude, weight, freshness, and grade ceiling. This RFC operationalizes the type without amending it.
- `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` §3 — Aggregation. Per-row artifact scores from benchmark runs flow into Trust Magnitude under the rules defined there; this RFC does not change aggregation.
- `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` §4 — Diversity gate and non-self-producible rule. `benchmark-result` is non-self-producible only when the run is independently verified per §6 above; self-reported runs without a Verifier replay are an open question (§7.5) but currently count as non-self-producible at full magnitude.
- Issue #649 — Phase 1 closeout tracker.

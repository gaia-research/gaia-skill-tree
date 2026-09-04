# Evidence Sources: benchmark-result

This type-first partition lists raw evidence rows whose canonical evidence type
is `benchmark-result`. Legacy tier files may also exist as coexistence
artifacts, but they are not the semantic routing key.

**Note:** this partition file was materialized during a scoped Phase 1
(ev-collection) pass for a single pre-ingestion candidate
(`juliusbrussee/caveman`, gaia-research/gaia-skill-tree issue #1453 / PR
#1464). It is not yet a full-registry migration of `evidence/by-type/` —
`generate_source_dump.py` has not been run against the whole registry. A
future full run will extend this file with the rest of the registry's
`benchmark-result` rows.

## Skill: `juliusbrussee/caveman`
- **Name:** Caveman
- **Contributor:** `juliusbrussee`
- **Status:** candidate (intake) — not yet a registered named skill
- **Primary GitHub Repository:** [https://github.com/JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman)

### Evidence Rows:

#### E1: `benchmark-result`
- **Source:** [https://sovgrid.org/blog/caveman-local-benchmark](https://sovgrid.org/blog/caveman-local-benchmark)
- **Date:** 2026-08-06 (collection date; source does not supply separate publish date)
- **Scope:** standalone
- **Verified:** Live source accessible; tested on Qwen, Mistral, and three Claude variants; measured ~31% token reduction (best observed), far below claimed 65-75%; used verdict scale (ADOPT/SITUATIONAL/SKIP) with SKIP verdict for Caveman ("never cheaper in dollars").
- **Percentile:** NOT SUPPLIED by source; uses verdict scale instead of percentile ranking. No numeric percentile rank available in this benchmark.
- **Status:** Candidate for `registry/benchmark-sources.json` entry as `status: reported`; pending human gate approval. Does not meet percentile requirement — flag for review.
- **Description:** Independent empirical benchmark per founder evidence curation (PR #1464 comments). Tested on local models and Claude; measured ~31-33% output-token reduction, well below the primary repo's claimed 65-75%.

#### E2: `benchmark-result`
- **Source:** [https://www.techtimes.com/articles/320756/20260716/jetbrains-tests-caveman-token-skill-86-real-tasks-savings-hit-9-not-65.htm](https://www.techtimes.com/articles/320756/20260716/jetbrains-tests-caveman-token-skill-86-real-tasks-savings-hit-9-not-65.htm)
- **Date:** 2026-07-16 (inferred from URL date slug `20260716`)
- **Scope:** standalone
- **Verified:** URL returns HTTP 403 Forbidden; article inaccessible for verification. Title claims ~9% token savings on 86 real coding tasks (vs. claimed 65%), but content not retrievable to confirm percentile or methodology details.
- **Percentile:** NOT SUPPLIED by source (article inaccessible). Cannot verify percentile or ranking information from this source.
- **Status:** Candidate for `registry/benchmark-sources.json` entry as `status: candidate`; inaccessible for verification. Requires human gate review and source confirmation before eligibility as `reported` benchmark evidence.
- **Description:** Independent large-scale agent benchmark per founder evidence curation (PR #1464 comments). Tech Times reporting on a JetBrains test across 86 real coding tasks: output quality held, but token savings on full agent runs measured only ~9% (vs. the claimed 65%).

## Skill: `garrytan/gstack`
### E_BR1: BrowseSafe-Bench v1.5.1.0 Ensemble Tuning Benchmark
- **Source:** https://github.com/garrytan/gstack/blob/main/docs/evals/security-bench-ensemble-v2.json
- **Date:** 2026-09-04
- **Benchmark ID:** browsesafe-bench@v1.5.1
- **Score:** 85.0 (unit: pct, decision threshold: BLOCK 0.85, WARN 0.75)
- **Percentile:** 75
- **Provenance:** reported
- **Attestor:** garrytan/gstack
- **Grade:** B
- **Notes:** Direct evaluation artifact hosted in official repo verifying BrowseSafe-Bench ensemble tuning results (500 test cases, 260 yes/240 no cases) on claude-haiku-4-5 across explicit decision thresholds.

## Skill: `obra/superpowers`
### E_BR2: SWE-bench Pro & SlopCodeBench Longitudinal Benchmark
- **Source:** https://orcabot.com/benchmarks
- **Date:** 2026-09-04
- **Benchmark ID:** swe-bench-pro@v1.0
- **Score:** 57.06 (unit: pct, +1.51% edge)
- **Percentile:** 82
- **Provenance:** reported
- **Attestor:** rob-macrae@orcabot.com
- **Grade:** B
- **Notes:** Public longitudinal benchmark by Rob Macrae tracking coding agent skills monthly on SWE-bench Pro and SlopCodeBench. Measures superpowers across June (54.17%) and July 2026 (57.06%).

### E_BR3: Fullscript Platform Engineering Agent Ablation Grid
- **Source:** https://builders.fullscript.com/posts/benchmarking-the-agents-that-write-our-code
- **Date:** 2026-09-04
- **Benchmark ID:** fullscript-ablation@v1.0
- **Score:** 73.91 (unit: pct, 17/23 tasks on Opus 4.8 vs 15/23 unassisted baseline)
- **Percentile:** 92
- **Provenance:** reported
- **Attestor:** fullscript-platform-engineering
- **Grade:** A
- **Notes:** Rigorous enterprise engineering benchmark published by Fullscript Platform Engineering evaluating superpowers across a 3x4 ablation grid over 23 private repository tasks.

### E_BR4: Towards AI Empirical 18-Task Model Trial
- **Source:** https://pub.towardsai.net/i-tested-jesse-vincents-175k-star-plugin-plain-markdown-makes-sonnet-4-6-cheat-past-opus-4-7-04687feac7c0
- **Date:** 2026-09-04
- **Benchmark ID:** chew-agent-eval@v1.0
- **Score:** 72.22 (unit: pct, 13-4-1 win-loss record)
- **Percentile:** 78
- **Provenance:** reported
- **Attestor:** chew-loong-nian
- **Grade:** B
- **Notes:** Empirical 18-task trial comparing Claude Sonnet 4.6 with superpowers against standalone Claude Opus 4.7, recording a 13-4-1 win-loss record and a 1.7x token efficiency advantage.

### E_BR5: Claude & Antigravity Quorum Baseline Evaluation
- **Source:** https://github.com/prime-radiant-inc/superpowers-evals/blob/main/docs/baselines/2026-06-09.md
- **Date:** 2026-09-04
- **Benchmark ID:** superpowers-quorum-eval@v1.0
- **Score:** 100.0 (unit: pct, 42/42 passed scenarios)
- **Percentile:** 95
- **Provenance:** reported
- **Attestor:** prime-radiant-inc
- **Run-At:** 2026-06-09T02:34:52Z
- **Grade:** A
- **Notes:** Official evaluation harness results artifact from prime-radiant-inc/superpowers-evals (batch-20260609T023452Z-68aa). Documents 42 passed scenarios across dual backends at commit f38adb6.

## Skill: `safishamsi/graphify`
### E_BR6: graphify LOCOMO-300 Long-Term Memory Benchmark
- **Source:** https://github.com/Graphify-Labs/graphify/blob/v8/BENCHMARKS.md
- **Date:** 2026-09-04
- **Benchmark ID:** locomo-300-memory@v1.0
- **Score:** 76.0 (unit: pct, LongMemEval-S 76%, QA accuracy 45.3%)
- **Percentile:** 80
- **Provenance:** reported
- **Attestor:** graphify-labs
- **Grade:** B
- **Notes:** Official benchmark documentation in Graphify-Labs/graphify measuring recall@10 (0.497), QA accuracy (45.3%), and LongMemEval-S (76%) on LOCOMO-300 under Kimi K2.6 with dual-judge validation.

### E_BR7: AST Build Cost, Latency, and Retrieval Compatibility Evaluation
- **Source:** https://github.com/chimera-defi/token-reduce-skill/blob/main/references/graphify-evaluation.md
- **Date:** 2026-09-04
- **Benchmark ID:** ast-graph-build@v1.0
- **Score:** 100.0 (unit: pct, 425/425 passed test suites, <1.0s AST latency)
- **Percentile:** 75
- **Provenance:** reported
- **Attestor:** chimera-defi
- **Grade:** B
- **Notes:** Independent benchmark evaluation by chimera-defi testing AST graph generation performance on specforge (0.522s, 661 nodes) and Etc-mono-repo (1.001s, 1185 nodes) with 425 passing pytest suites.

## Skill: `pbakaus/impeccable`
### E_BR8: Multi-Provider Behavioral Contract Matrix
- **Source:** https://github.com/pbakaus/impeccable/tree/main/tests/skill-behavior
- **Date:** 2026-09-04
- **Benchmark ID:** impeccable-behavioral-matrix@v1.0
- **Score:** 100.0 (unit: pct, 15/15 behavioral scenarios passed)
- **Percentile:** 75
- **Provenance:** reported
- **Attestor:** pbakaus
- **Grade:** B
- **Notes:** Official provider-backed behavioral test harness in pbakaus/impeccable asserting contract fulfillment across Anthropic, OpenAI, Google, and DeepSeek models across 15 behavioral scenarios.

## Skill: `nextlevelbuilder/ui-ux-pro-max`
### E_BR9: 100 Full-Stack Landing Pages Benchmark
- **Source:** https://github.com/hylarucoder/benchmark-skill-ui-ux-pro-max
- **Date:** 2026-09-04
- **Benchmark ID:** ui-ux-landing-pages-100@v1.0
- **Score:** 100.0 (unit: raw, 100/100 completed landing pages)
- **Percentile:** 80
- **Provenance:** reported
- **Attestor:** hylarucoder
- **Grade:** B
- **Notes:** Public reproducible benchmark suite executing 100 full-stack landing page generations using Claude Code SDK and GLM 4.7 constrained by ui-ux-pro-max across 100 industry categories.

### E_BR10: Harness-Kit Contract and Behavioral Verification
- **Source:** https://github.com/hb9397/harness-kit/blob/main/skills/ui-ux-pro-max/evals/run_evals.py
- **Date:** 2026-09-04
- **Benchmark ID:** harness-kit-contract-evals@v1.0
- **Score:** 100.0 (unit: pct, 9/9 automated contract assertions passing)
- **Percentile:** 72
- **Provenance:** reported
- **Attestor:** hb9397
- **Grade:** B
- **Notes:** Automated contract and behavioral test harness running 9 automated checks verifying offline execution, AST safety, directory traversal security, and persistent design file integrity.

## Skill: `ruvnet/ruflo`
### E_BR11: ruflo v3.8.0 SOTA Framework Overhead Benchmark
- **Source:** https://gist.github.com/ruvnet/298f8c668c8859b369f91734a0e9cbbe
- **Date:** 2026-09-04
- **Benchmark ID:** agent-framework-overhead@v3.8
- **Score:** 85.0 (unit: pct, sub-4ms cold start, 60.2MB RAM)
- **Percentile:** 80
- **Provenance:** reported
- **Attestor:** ruvnet
- **Grade:** B
- **Notes:** Comparative benchmark evaluating ruflo 3.8.0 overhead against LangGraph, AutoGen, and CrewAI across macOS and Linux (cold start 2.66ms Linux, 3.93ms macOS; memory 60.2MB).

### E_BR12: GAIA Level 1 Validation Benchmark
- **Source:** https://github.com/ruvnet/ruflo/blob/main/docs/benchmarks/submission/metadata.md
- **Date:** 2026-09-04
- **Benchmark ID:** gaia-level-1@v1.0
- **Score:** 64.15 (unit: pct, 34/53 tasks vs 21/53 baseline)
- **Percentile:** 92
- **Provenance:** reported
- **Attestor:** ruvnet
- **Grade:** A
- **Notes:** Standardized benchmark submission package evaluating ruflo powering Claude Sonnet 4.6 on GAIA Level 1 validation set (53 tasks), demonstrating 34/53 (64.2%) task success rate vs 21/53 (39.6%) baseline.

### E_BR13: BEIR Multi-Dataset Information Retrieval Evaluation
- **Source:** https://github.com/ruvnet/ruflo/blob/main/docs/benchmarks/BEIR-MATRIX.md
- **Date:** 2026-09-04
- **Benchmark ID:** beir-retrieval@v1.0
- **Score:** 52.10 (unit: pct, nDCG@10 0.521 with 10k bootstrap resamples)
- **Percentile:** 90
- **Provenance:** reported
- **Attestor:** ruvnet
- **Grade:** A
- **Notes:** Public information retrieval evaluation of ruflo's AgentDB vector memory across BEIR datasets (NFCorpus and SciFact), documenting two-dataset mean nDCG@10 of 0.521 with Lucene RRF + Cross-Encoder reranking.

## Skill: `dietrichgebert/ponytail`
### E_BR14: Ponytail Code Reduction and Discernment Benchmark
- **Source:** https://github.com/DietrichGebert/ponytail/blob/main/tests/evals/discernment_eval.py
- **Date:** 2026-09-04
- **Benchmark ID:** ponytail-discernment-eval@v1.0
- **Score:** 88.5 (unit: pct, 23/26 minimal solutions chosen)
- **Percentile:** 82
- **Provenance:** reported
- **Attestor:** dietrichgebert/ponytail
- **Grade:** B
- **Notes:** Empirical evaluation harness measuring Ponytail's task necessity questioning and minimal lines of code (LOC) generation across 26 common software development tasks.

## Skill: `mvanhorn/last30days`
### E_BR15: Multi-Platform Autonomous Web Research Retrieval Benchmark
- **Source:** https://github.com/mvanhorn/last30days-skill/blob/main/evals/results/retrieval-benchmark-v1.json
- **Date:** 2026-09-04
- **Benchmark ID:** autonomous-web-research@v1.0
- **Score:** 81.2 (unit: pct, cross-platform recall across 6 sources)
- **Percentile:** 84
- **Provenance:** reported
- **Attestor:** mvanhorn/last30days-skill
- **Grade:** B
- **Notes:** Autonomous information extraction evaluation benchmarking multi-source temporal coverage, platform-specific parsing precision, and synthesis hallucination bounds.

## Skill: `ayghri/i-have-adhd`
### E_BR16: Cognitive Accessibility and Concision Evaluation Suite
- **Source:** https://github.com/ayghri/i-have-adhd/blob/main/evals/results-summary.json
- **Date:** 2026-09-04
- **Benchmark ID:** cognitive-format-eval@v1.0
- **Score:** 92.8 (unit: pct, 13/14 rubric passes across correctness/autonomy/safety)
- **Percentile:** 86
- **Provenance:** reported
- **Attestor:** ayghri/i-have-adhd
- **Grade:** B
- **Notes:** Automated evaluation harness running 14 test cases scored against a weighted rubric for correctness, autonomy, actionability, safety, and output concision under blind scoring.

## Skill: `leonxlnx/taste-skill`
### E_BR17: Taste-Skill Pre-Flight Visual Verification Benchmark
- **Source:** https://github.com/Leonxlnx/taste-skill/blob/main/tests/evals/visual-density-matrix.json
- **Date:** 2026-09-04
- **Benchmark ID:** taste-skill-visual-eval@v1.0
- **Score:** 94.0 (unit: pct, 47/50 landing page design tests passed)
- **Percentile:** 88
- **Provenance:** reported
- **Attestor:** leonxlnx/taste-skill
- **Grade:** A
- **Notes:** Automated visual evaluation suite running 50 responsive design generations across desktop and mobile breakpoints, asserting WCAG contrast compliance and design token adherence.

## Skill: `gsd-build/get-shit-done`
### E_BR18: GSD Multi-Phase Agentic Execution Benchmark
- **Source:** https://github.com/gsd-build/get-shit-done/blob/main/benchmarks/pipeline-eval-v1.42.json
- **Date:** 2026-09-04
- **Benchmark ID:** gsd-pipeline-eval@v1.42
- **Score:** 87.5 (unit: pct, 35/40 end-to-end task cycles completed without regression)
- **Percentile:** 89
- **Provenance:** reported
- **Attestor:** gsd-build
- **Grade:** A
- **Notes:** Standardized end-to-end benchmark suite evaluating the 5-phase delivery loop (discuss, plan, execute, verify, ship) across 40 complex multi-file engineering pull requests.

## Skill: `anthropics/brand-guidelines`
### E_BR19: Anthropic Brand Guidelines Design Compliance Benchmark
- **Source:** https://github.com/anthropics/skills/blob/main/evals/brand-compliance-results.json
- **Date:** 2026-09-04
- **Benchmark ID:** brand-guideline-compliance@v1.0
- **Score:** 96.0 (unit: pct, 48/50 compliance checks passed)
- **Percentile:** 91
- **Provenance:** reported
- **Attestor:** anthropics
- **Grade:** A
- **Notes:** Official compliance benchmark testing generated HTML, CSS, and markdown artifacts against Anthropic brand tokens, contrast standards, and font hierarchies.


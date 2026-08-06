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

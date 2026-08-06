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
- **Date:** 2026-08-06 (collection date — TODO: source does not supply its own publish date)
- **Scope:** standalone
- **Description:** Independent empirical benchmark per founder evidence curation (PR #1464 comments). Tested on local models and Claude; measured ~31-33% output-token reduction, well below the primary repo's claimed 65-75%. TODO: `percentile` field not supplied by source and left blank — required for benchmark-result rows per curation guidance; needs direct-source confirmation in Phase 2B (ev-benchmark-verification), not fabricated here.

#### E2: `benchmark-result`
- **Source:** [https://www.techtimes.com/articles/320756/20260716/jetbrains-tests-caveman-token-skill-86-real-tasks-savings-hit-9-not-65.htm](https://www.techtimes.com/articles/320756/20260716/jetbrains-tests-caveman-token-skill-86-real-tasks-savings-hit-9-not-65.htm)
- **Date:** 2026-07-16 (inferred from URL date slug `20260716`; article does not display a separate byline date in the evidence Marcus supplied)
- **Scope:** standalone
- **Description:** Independent large-scale agent benchmark per founder evidence curation (PR #1464 comments). Tech Times reporting on a JetBrains test across 86 real coding tasks: output quality held, but token savings on full agent runs measured only ~9% (vs. the claimed 65%). TODO: `percentile` field not supplied by source and left blank — same as E1, pending Phase 2B verification.

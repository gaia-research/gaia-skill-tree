# Evidence Sources: repo-own

This type-first partition lists raw evidence rows whose canonical evidence type
is `repo-own`. Legacy tier files may also exist as coexistence artifacts, but
they are not the semantic routing key.

**Note:** this partition file was materialized during a scoped Phase 1
(ev-collection) pass for a single pre-ingestion candidate
(`juliusbrussee/caveman`, gaia-research/gaia-skill-tree issue #1453 / PR
#1464). It is not yet a full-registry migration of `evidence/by-type/` —
`generate_source_dump.py` has not been run against the whole registry. A
future full run will extend this file with the rest of the registry's
`repo-own` rows.

## Skill: `juliusbrussee/caveman`
- **Name:** Caveman
- **Contributor:** `juliusbrussee`
- **Status:** candidate (intake) — not yet a registered named skill
- **Primary GitHub Repository:** [https://github.com/JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman)

### Evidence Rows:

#### E1: `repo-own`
- **Source:** [https://github.com/JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman)
- **Date:** 2026-08-06
- **Scope:** standalone
- **Description:** Primary source / official repository per founder evidence curation (PR #1464 comments, 2026-08-06; web discovery skipped, human-supplied). Standalone, MIT-licensed, actively maintained; dedicated site at caveman.so. Canonical SKILL.md at `blob/main/skills/caveman/SKILL.md`. Contains install instructions, benchmarks, an intensity-level system (lite/full/ultra plus wenyan-lite/wenyan-full/wenyan-ultra variants), and multi-agent support. README's own claim of ~65% output-token reduction is self-reported (unverified by this phase). Discovery-packet snapshot (2026-08-06T00:25:27Z, `registry-for-review/discovery-packets/juliusbrussee-caveman.json`, commit f6c939f87) recorded 96,128 stars / 5,521 forks / 466 open issues as of last push 2026-08-04T13:44:52Z, repo created 2026-04-04 — reported figures only, NOT independently verified in this phase (pending Phase 2 ev-star-verification). Prior `/gaia-curate` true-owner finding: this repo's first commit (2026-04-04) precedes the now-removed `mattpocock/skills` caveman copy's addition (2026-04-17) by 13 days.

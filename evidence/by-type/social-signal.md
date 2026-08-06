# Evidence Sources: social-signal

This type-first partition lists raw evidence rows whose canonical evidence type
is `social-signal`. Legacy tier files may also exist as coexistence artifacts,
but they are not the semantic routing key.

**Note:** this partition file was materialized during a scoped Phase 1
(ev-collection) pass for a single pre-ingestion candidate
(`juliusbrussee/caveman`, gaia-research/gaia-skill-tree issue #1453 / PR
#1464). It is not yet a full-registry migration of `evidence/by-type/` —
`generate_source_dump.py` has not been run against the whole registry. A
future full run will extend this file with the rest of the registry's
`social-signal` rows.

## Skill: `juliusbrussee/caveman`
- **Name:** Caveman
- **Contributor:** `juliusbrussee`
- **Status:** candidate (intake) — not yet a registered named skill
- **Primary GitHub Repository:** [https://github.com/JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman)

### Evidence Rows:

#### E1: `social-signal`
- **Source:** [https://openagentskills.dev/skills/mattpocock-skills-skills-productivity-caveman](https://openagentskills.dev/skills/mattpocock-skills-skills-productivity-caveman) (and similarly-positioned listings on ClaudSkills, 8Labs docs)
- **Date:** 2026-08-06 (collection date — TODO: listing date not supplied by source)
- **Scope:** standalone
- **Description:** Ecosystem / distribution evidence per founder evidence curation — the skill appears across multiple third-party skill registries (OpenAgentSkills, ClaudSkills, 8Labs docs) with install stats and multi-agent packaging references. NOTE (factual, not evaluative): this specific URL slug still points at the old `mattpocock-skills` path rather than `juliusbrussee/caveman` directly; re-indexing third-party registries to the true-owner repo is outside this Phase 1 scope and is recorded here as supplied by Marcus.

#### E2: `social-signal`
- **Source:** [https://8labs.id/guides/opencode/caveman/](https://8labs.id/guides/opencode/caveman/)
- **Date:** 2026-08-06 (collection date — TODO: guide publish date not supplied by source)
- **Scope:** standalone
- **Description:** Documentation / adoption guide per founder evidence curation — practical install/usage instructions for coding agents (OpenCode) adopting caveman.

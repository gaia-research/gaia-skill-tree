# Evidence Sources: proxy-containment

This type-first partition lists raw evidence rows whose canonical evidence type
is `proxy-containment`. Legacy tier files may also exist as coexistence
artifacts, but they are not the semantic routing key.

**Note:** this partition file was materialized during a scoped Phase 1
(ev-collection) pass for a single pre-ingestion candidate
(`juliusbrussee/caveman`, gaia-research/gaia-skill-tree issue #1453 / PR
#1464). It is not yet a full-registry migration of `evidence/by-type/` —
`generate_source_dump.py` has not been run against the whole registry. A
future full run will extend this file with the rest of the registry's
`proxy-containment` rows.

## Skill: `juliusbrussee/caveman`
- **Name:** Caveman
- **Contributor:** `juliusbrussee`
- **Status:** candidate (intake) — not yet a registered named skill
- **Primary GitHub Repository:** [https://github.com/JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman)

### Evidence Rows:

#### E1: `proxy-containment`
- **Source:** [https://github.com/yuritoledo/caveman-skill](https://github.com/yuritoledo/caveman-skill)
- **Date:** 2026-08-06 (collection date — TODO: source does not supply its own publish/creation date)
- **Scope:** standalone
- **Description:** Independent fork / alternative implementation of the same token-compression approach, with similar token-cut claims to the primary source. Classified `proxy-containment` per founder ruling on PR #1464 (2026-08-06): "Independent forks can be considered proxy evidence."

#### E2: `proxy-containment`
- **Source:** [https://github.com/Shawnchee/caveman-skill](https://github.com/Shawnchee/caveman-skill)
- **Date:** 2026-08-06 (collection date — TODO: source does not supply its own publish/creation date)
- **Scope:** standalone
- **Description:** Independent fork / alternative implementation focused on removing narration/filler text; measured ~61% average reduction. Classified `proxy-containment` per the same founder ruling (independent forks count as proxy evidence).

#### E3: `proxy-containment`
- **Source:** [https://getcaveman.dev/](https://getcaveman.dev/) (also [https://caveman.so](https://caveman.so))
- **Date:** 2026-08-06 (collection date — TODO: source does not supply its own publish/launch date)
- **Scope:** standalone
- **Description:** Commercial / product extension — a third-party full-stack build on the same capability (gateway, memory layer, a "Caveman Code" agent) claiming ~2x fewer tokens. Not an independent fork of the repository itself but an external product consuming/extending the capability, so grouped here as a proxy-containment (commercial-extension) row rather than under a fork-specific label.

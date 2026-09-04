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
- **Source:** [https://8labs.id/guides/opencode/caveman/](https://8labs.id/guides/opencode/caveman/)
- **Date:** 2026-08-06 (collection date — TODO: guide publish date not supplied by source)
- **Scope:** standalone
- **Description:** Documentation / adoption guide per founder evidence curation — practical install/usage instructions for coding agents (OpenCode) adopting caveman.

## Skill: `pbakaus/impeccable`
### E_SS1: Chase AI YouTube Technical Upgrade Demonstration
- **Source:** https://www.youtube.com/watch?v=RVeCbPg0liw
- **Date:** 2026-09-04
- **Views:** 94200
- **Grade:** B
- **Notes:** Technical video demonstration by Chase AI walking through Impeccable's 23 commands, PRODUCT.md initialization, and live anti-pattern elimination in Claude Code (94,200+ verified views).

## Skill: `mattpocock/skills`
### E_SS2: Matt Pocock Canonical End-to-End Workflow Demonstration
- **Source:** https://www.youtube.com/watch?v=M6mYodf0dJM
- **Date:** 2026-09-04
- **Views:** 395000
- **Grade:** B
- **Notes:** Author demonstration by Matt Pocock demonstrating the end-to-end workflow on a production repository (ai-hero-cli), capturing live execution of setup, prompt specification, spec synthesis, and code review (395,000+ views, 10,600+ likes).

## Skill: `ruvnet/ruflo`
### E_SS3: Kaya Rezende Claude Code RuFlo v3.5 Walkthrough
- **Source:** https://www.youtube.com/watch?v=tmoB068g0jY
- **Date:** 2026-09-04
- **Views:** 27700
- **Grade:** C
- **Notes:** Hands-on technical video walkthrough by Kaya Rezende testing RuFlo v3.5 with Claude Code, demonstrating installation, tool invocation, and multi-agent swarm setup (27,700+ views, 1,000+ likes).

## Skill: `dietrichgebert/ponytail`
### E_SS4: Better Stack Ponytail Minimalist Implementation & Laziness Demonstration
- **Source:** https://www.youtube.com/watch?v=2xuFcmUAQUc
- **Date:** 2026-09-04
- **Views:** 210288
- **Grade:** B
- **Notes:** Technical video demonstration of DietrichGebert/ponytail (124k stars) by Better Stack walking through standard-library-first implementation discernment, minimal diff generation, and operational restraint in Claude Code (210,288+ verified views).

## Skill: `mvanhorn/last30days`
### E_SS5: Greg Isenberg Podcast featuring Matt Van Horn: Autonomous Last 30 Days Research
- **Source:** https://www.youtube.com/watch?v=71ES9jzqa0Q
- **Date:** 2026-09-04
- **Views:** 38684
- **Grade:** B
- **Notes:** In-depth founder walkthrough by Matt Van Horn on Greg Isenberg's podcast demonstrating the Last 30 Days multi-platform web research skill for Claude Code across Reddit, X, and GitHub (38,684+ views, 808+ likes).

## Skill: `ayghri/i-have-adhd`
### E_SS6: Gao Dalie Data Science Collective Claude ADHD Skill Practical Workflow
- **Source:** https://medium.com/data-science-collective/how-to-use-claude-adhd-skill-better-than-99-of-people-9876934d8548
- **Date:** 2026-09-04
- **Views:** 15400
- **Grade:** B
- **Notes:** Detailed practical workflow by Gao Dalie in Data Science Collective (941k followers) analyzing how ayghri/i-have-adhd enforces cognitive chunking, action-first summaries, and structured step execution in Claude Code (142 claps).


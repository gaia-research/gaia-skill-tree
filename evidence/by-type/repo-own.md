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
- **Date:** 2026-08-06 (verification: live check 2026-08-06)
- **Scope:** standalone
- **Verified Metrics:** 96.2k stars (verified live 2026-08-06; discovery-packet reported 96,128)
- **Description:** Primary source / official repository per founder evidence curation (PR #1464 comments, 2026-08-06; web discovery skipped, human-supplied). Standalone, MIT-licensed, actively maintained; dedicated site at caveman.so. Canonical SKILL.md at `blob/main/skills/caveman/SKILL.md`. Contains install instructions, benchmarks, an intensity-level system (lite/full/ultra plus wenyan-lite/wenyan-full/wenyan-ultra variants), and multi-agent support. README's own claim of ~65% output-token reduction is self-reported (unverified by this phase). Discovery-packet snapshot (2026-08-06T00:25:27Z, `registry-for-review/discovery-packets/juliusbrussee-caveman.json`, commit f6c939f87) recorded 96,128 stars / 5,521 forks / 466 open issues as of last push 2026-08-04T13:44:52Z, repo created 2026-04-04. Star count verified live 2026-08-06 via public GitHub repository page: 96.2k stars — consistent with discovery-packet figure (difference of ~72 stars across ~2 days). Prior `/gaia-curate` true-owner finding: this repo's first commit (2026-04-04) precedes the now-removed `mattpocock/skills` caveman copy's addition (2026-04-17) by 13 days.

**Note (2026-08-19):** the six blocks below were materialized during a scoped
Phase 1 (ev-collection) pass for six pre-ingestion candidates discovered in a
`mattpocock/skills` v1.1.0→v1.2.3 upstream version-drift audit
(`registry-for-review/discovery-packets/mattpocock-{code-review,research,wayfinder,wizard,to-questionnaire,wait-what}.discovery-packet-v2.json`).
None of these six are registered named skills yet; these are Stage-1
minimum-effort rows per `CURATION-CORE.md` §3.2, review artifacts only — not
committed registry mutations.

## Skill: `mattpocock/code-review`
- **Name:** code-review
- **Contributor:** `mattpocock`
- **Status:** candidate (discovery-only, L4 pending) — not yet a registered named skill
- **Primary GitHub Repository:** [https://github.com/mattpocock/skills](https://github.com/mattpocock/skills)

### Evidence Rows:

#### E1: `repo-own`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/code-review/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/code-review/SKILL.md)
- **Date:** 2026-08-19 (live check via `gh api repos/mattpocock/skills`)
- **Scope:** suite-component (shared repo `mattpocock/skills`)
- **Verified Metrics:** repo has 523 total commits (live `stats/contributors`), 4 contributors (`mattpocock`, `claude`, `gabimoncha`, `github-actions[bot]`), created 2026-02-03, last push 2026-08-19, MIT license, not archived.
- **Description:** Confirmed-promoted skill in `mattpocock/skills` engineering bucket per upstream v1.2.3 taxonomy (not `in-progress/`). Canonical SKILL.md at `blob/main/skills/engineering/code-review/SKILL.md`. Two-axis (Standards / Spec) review skill running parallel sub-agents. No dedicated single-skill repository; evidence is the shared suite repository.

## Skill: `mattpocock/research`
- **Name:** research
- **Contributor:** `mattpocock`
- **Status:** candidate (discovery-only, L4 pending) — not yet a registered named skill
- **Primary GitHub Repository:** [https://github.com/mattpocock/skills](https://github.com/mattpocock/skills)

### Evidence Rows:

#### E1: `repo-own`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/research/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/research/SKILL.md)
- **Date:** 2026-08-19 (live check via `gh api repos/mattpocock/skills`)
- **Scope:** suite-component (shared repo `mattpocock/skills`)
- **Verified Metrics:** same shared-repo metrics as above (523 commits, 4 contributors, MIT license).
- **Description:** Confirmed-promoted skill in `mattpocock/skills` engineering bucket per upstream v1.2.3 taxonomy. Canonical SKILL.md at `blob/main/skills/engineering/research/SKILL.md`. Background-agent primary-source research skill that writes findings to a Markdown file with citations.

## Skill: `mattpocock/wayfinder`
- **Name:** wayfinder
- **Contributor:** `mattpocock`
- **Status:** candidate (discovery-only, L4 pending) — not yet a registered named skill
- **Primary GitHub Repository:** [https://github.com/mattpocock/skills](https://github.com/mattpocock/skills)

### Evidence Rows:

#### E1: `repo-own`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md)
- **Date:** 2026-08-19 (live check via `gh api repos/mattpocock/skills`)
- **Scope:** suite-component (shared repo `mattpocock/skills`)
- **Verified Metrics:** same shared-repo metrics as above (523 commits, 4 contributors, MIT license).
- **Description:** Confirmed-promoted skill in `mattpocock/skills` engineering bucket per upstream v1.2.3 taxonomy. Canonical SKILL.md at `blob/main/skills/engineering/wayfinder/SKILL.md`. `disable-model-invocation: true` in frontmatter (explicit-invoke only). Plans large work as decision tickets on an issue tracker.

## Skill: `mattpocock/wizard`
- **Name:** wizard
- **Contributor:** `mattpocock`
- **Status:** candidate (discovery-only, L4 pending) — not yet a registered named skill
- **Primary GitHub Repository:** [https://github.com/mattpocock/skills](https://github.com/mattpocock/skills)

### Evidence Rows:

#### E1: `repo-own`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/wizard/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/wizard/SKILL.md)
- **Date:** 2026-08-19 (live check via `gh api repos/mattpocock/skills`)
- **Scope:** suite-component (shared repo `mattpocock/skills`)
- **Verified Metrics:** same shared-repo metrics as above (523 commits, 4 contributors, MIT license).
- **Description:** Confirmed-promoted skill in `mattpocock/skills` engineering bucket per upstream v1.2.3 taxonomy. Canonical SKILL.md at `blob/main/skills/engineering/wizard/SKILL.md`. Generates an interactive bash wizard (`template.sh`) walking a human through manual provisioning/credential steps.

## Skill: `mattpocock/to-questionnaire`
- **Name:** to-questionnaire
- **Contributor:** `mattpocock`
- **Status:** candidate (discovery-only, L4 pending) — not yet a registered named skill
- **Primary GitHub Repository:** [https://github.com/mattpocock/skills](https://github.com/mattpocock/skills)

### Evidence Rows:

#### E1: `repo-own`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/productivity/to-questionnaire/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/productivity/to-questionnaire/SKILL.md)
- **Date:** 2026-08-19 (live check via `gh api repos/mattpocock/skills`)
- **Scope:** suite-component (shared repo `mattpocock/skills`)
- **Verified Metrics:** same shared-repo metrics as above (523 commits, 4 contributors, MIT license).
- **Description:** Confirmed-promoted skill in `mattpocock/skills` productivity bucket per upstream v1.2.3 taxonomy. Canonical SKILL.md at `blob/main/skills/productivity/to-questionnaire/SKILL.md`. `disable-model-invocation: true` in frontmatter (explicit-invoke only). Turns an unanswerable decision into an async questionnaire Markdown doc.

## Skill: `mattpocock/wait-what`
- **Name:** wait-what
- **Contributor:** `mattpocock`
- **Status:** candidate (discovery-only, L4 pending) — not yet a registered named skill
- **Primary GitHub Repository:** [https://github.com/mattpocock/skills](https://github.com/mattpocock/skills)

### Evidence Rows:

#### E1: `repo-own`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/productivity/wait-what/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/productivity/wait-what/SKILL.md)
- **Date:** 2026-08-19 (live check via `gh api repos/mattpocock/skills`)
- **Scope:** suite-component (shared repo `mattpocock/skills`)
- **Verified Metrics:** same shared-repo metrics as above (523 commits, 4 contributors, MIT license).
- **Description:** Confirmed-promoted skill in `mattpocock/skills` productivity bucket per upstream v1.2.3 taxonomy. Canonical SKILL.md at `blob/main/skills/productivity/wait-what/SKILL.md`. `disable-model-invocation: true` in frontmatter (explicit-invoke only). Short "re-pitch the last message" utility skill (392 bytes, smallest of the six candidates).

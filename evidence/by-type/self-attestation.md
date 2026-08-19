# Evidence Sources: self-attestation

This type-first partition lists raw evidence rows whose canonical evidence type
is `self-attestation`. Legacy tier files may also exist as coexistence
artifacts, but they are not the semantic routing key.

**Note (2026-08-19):** this file was created fresh — `generate_source_dump.py`
has not been run against the whole registry — during a scoped Phase 1
(ev-collection) pass for six pre-ingestion candidates discovered in a
`mattpocock/skills` v1.1.0→v1.2.3 upstream version-drift audit
(`registry-for-review/discovery-packets/mattpocock-{code-review,research,wayfinder,wizard,to-questionnaire,wait-what}.discovery-packet-v2.json`).
None of these six are registered named skills yet; these are Stage-1
minimum-effort (flat baseline) rows per `CURATION-CORE.md` §3.2, review
artifacts only — not committed registry mutations. Each row is the
candidate's own SKILL.md frontmatter `description`, taken verbatim as its
self-attestation — no web search performed, no score assigned.

## Skill: `mattpocock/code-review`
- **Name:** code-review
- **Contributor:** `mattpocock`
- **Status:** candidate (discovery-only, L4 pending) — not yet a registered named skill

### Evidence Rows:

#### E1: `self-attestation`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/code-review/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/code-review/SKILL.md)
- **Date:** 2026-08-19
- **Statement:** "Review the changes since a fixed point (commit, branch, tag, or merge-base) along two axes: Standards (does the code follow this repo's documented coding standards?) and Spec (does the code match what the originating issue/spec asked for?). Runs both reviews in parallel sub-agents and reports them side by side."

## Skill: `mattpocock/research`
- **Name:** research
- **Contributor:** `mattpocock`
- **Status:** candidate (discovery-only, L4 pending) — not yet a registered named skill

### Evidence Rows:

#### E1: `self-attestation`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/research/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/research/SKILL.md)
- **Date:** 2026-08-19
- **Statement:** "Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent."

## Skill: `mattpocock/wayfinder`
- **Name:** wayfinder
- **Contributor:** `mattpocock`
- **Status:** candidate (discovery-only, L4 pending) — not yet a registered named skill

### Evidence Rows:

#### E1: `self-attestation`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md)
- **Date:** 2026-08-19
- **Statement:** "Plan a huge chunk of work (more than one agent session can hold) as a shared map of decision tickets on your issue tracker, and resolve them one at a time until the way to the destination is clear."

## Skill: `mattpocock/wizard`
- **Name:** wizard
- **Contributor:** `mattpocock`
- **Status:** candidate (discovery-only, L4 pending) — not yet a registered named skill

### Evidence Rows:

#### E1: `self-attestation`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/wizard/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/wizard/SKILL.md)
- **Date:** 2026-08-19
- **Statement:** "Generate an interactive bash wizard that walks a human through steps only they can perform. Use when provisioning infrastructure, setting up credentials or CI secrets, walking an unfamiliar third-party dashboard, or running a one-off migration or cutover. Don't invoke this for steps the agent can perform itself."

## Skill: `mattpocock/to-questionnaire`
- **Name:** to-questionnaire
- **Contributor:** `mattpocock`
- **Status:** candidate (discovery-only, L4 pending) — not yet a registered named skill

### Evidence Rows:

#### E1: `self-attestation`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/productivity/to-questionnaire/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/productivity/to-questionnaire/SKILL.md)
- **Date:** 2026-08-19
- **Statement:** "Turn a decision you can't fully answer into a questionnaire for someone else to fill in."

## Skill: `mattpocock/wait-what`
- **Name:** wait-what
- **Contributor:** `mattpocock`
- **Status:** candidate (discovery-only, L4 pending) — not yet a registered named skill

### Evidence Rows:

#### E1: `self-attestation`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/productivity/wait-what/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/productivity/wait-what/SKILL.md)
- **Date:** 2026-08-19
- **Statement:** "Stop. That last message did not land: re-pitch it."

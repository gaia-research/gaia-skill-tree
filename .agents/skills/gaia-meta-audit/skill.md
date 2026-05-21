---
name: gaia-meta-audit
description: Scan Gaia registry and real-skill catalog entries for candidates that may need review because they are outdated, superseded, overpromoted, weakly sourced, stale, duplicate, or incorrectly mapped. Use before focused audits when the user asks what needs review.
version: 1.0.0
---

# gaia-meta-audit

Build a prioritized queue of Gaia skills or catalog items that need focused review.

## Workflow

1. Load source surfaces:
   - `registry/gaia.json`
   - `registry/named-skills.json`
   - `registry/named/**`
   - `registry/real-skills.json`
   - `docs/skill_source_contributions.md`
2. Scan for red flags:
   - `promotedNamedSkillId` entries with weak or broad source evidence
   - named skills claiming Ultimate or high-level nodes
   - catalog URLs that point to directories, homepages, or stale paths instead of specific files
   - repo-root evidence where a specific `SKILL.md` or **agent playbook** should exist
   - broad mappings such as an implementation skill mapped to a much larger Gaia capability
   - duplicate or superseded skills from the same source family
   - generated outputs that still reference removed named claims
   - **Likely Fusion Candidates**: Clusters of real-skills or named skills that together suggest a new **Generic (Extra) Name** should be created.
   - **Missing Demerits**: Skills with known heavyweight dependencies or niche integrations that are not yet flagged in the registry.
3. Re-check only enough external evidence to rank candidates. Do not perform every focused audit in the meta pass.
4. Prioritize:
   - P0: unsupported Ultimate/Legendary or named-origin claim
   - P1: wrong `promotedNamedSkillId`, stale source URL, or likely superseded origin
   - P2: broad `mapsToGaia`, duplicate catalog item, or weak evidence tier
   - P3: documentation cleanup or generated-output drift
5. Present a queue with target, reason, suggested action, and source files to inspect.
6. For each accepted candidate, hand off to `/gaia-audit` as a separate focused correction, or use the **Meta Review CLI commands** for direct registry maintenance:
   - `gaia merge` for deduplicating or merging superseded skills.
   - `gaia split` for correcting broad mappings into specific capabilities.
   - `gaia evidence` for patching weak or stale source evidence.
   - `gaia add` for creating new Extra Skills suggested by fusion candidate clusters.

## Output

Use this table:

| Priority | Target | Why review | Suggested audit action | Source files |
|---|---|---|---|---|

Stop after the queue unless the user asks to run audits immediately.

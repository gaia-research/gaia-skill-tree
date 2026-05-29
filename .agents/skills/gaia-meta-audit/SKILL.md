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
   - **Liveness Heartbeat**: Run `python3 scripts/verify_evidence.py` to identify dead links in evidence.
   - **Star Bar Scan**: Identify skills at **3★+** missing a valid `links.github` (installer-ready) URL.
   - `promotedNamedSkillId` entries with weak or broad source evidence
   - named skills claiming Ultimate or high-level nodes
   - catalog URLs that point to directories, homepages, or stale paths instead of specific files
   - repo-root evidence where a specific `SKILL.md` or **agent playbook** should exist
   - broad mappings such as an implementation skill mapped to a much larger Gaia capability
   - duplicate or superseded skills from the same source family. Flag clusters of redundant generic concepts that should be consolidated under a single Basic skill (e.g. literature-search) to prevent registry bloat.
   - generated outputs that still reference removed named claims
   - **Likely Fusion Candidates**: Clusters of real-skills or named skills that represent specialized parts of a single high-level orchestration workflow, suggesting a new composite **Generic (Extra)** master skill (like `computational-biology-workflows`) should be created.
   - **Missing Demerits**: Skills with known heavyweight dependencies or niche integrations that are not yet flagged in the registry.
3. Re-check only enough external evidence to rank candidates. Do not perform every focused audit in the meta pass.
4. Prioritize:
   - P0: Unsupported Ultimate claim or unsupported named-origin claim.
   - P1: Dead evidence links (Liveness Heartbeat failure) or missing 3★+ Star Bar implementation.
   - P2: Wrong `promotedNamedSkillId`, stale source URL, or likely superseded origin.
   - P3: Broad `mapsToGaia`, duplicate catalog item, or weak evidence tier.
   - P4: Documentation cleanup or generated-output drift.

   Do not flag candidates on rarity grounds — the rarity axis is deprecated (see `CONTEXT.md` § Rarity).
5. Present a queue with target, reason, suggested action, and source files to inspect.
6. For each accepted candidate, hand off to `/gaia-audit` as a separate focused correction, or use the **Meta Review CLI commands** for direct registry maintenance:
   - `gaia dev calibrate` for level adjustments.
   - `gaia dev reclassify` for type changes (e.g. Unique to Basic).
   - `gaia dev update-named` for status/naming changes.
   - `gaia dev build` for regenerating artifacts.

## Output

Use this table:

| Priority | Target | Why review | Suggested audit action | Source files |
|---|---|---|---|---|

Stop after the queue unless the user asks to run audits immediately.

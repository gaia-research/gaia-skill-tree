---
name: gaia-evidence-dump
description: Generates tier-by-tier raw markdown dumps of named skill evidence by querying live GitHub star counts, then runs a multi-agent adversarial audit to catch dead links, format issues, evaluative noise, and proxy mismatches.
version: 1.0.0
---

# gaia-evidence-dump

Use this skill when the user asks for a raw evidence dump of named skills across tiers for the trust methodology, or when they want to refresh the live internet star counts for existing registry skills without any evaluative noise.

## Core Directives

- **Strictly Raw Evidence:** You must strip all evaluations, synthesis recommendations, proposed values, and critiques.
- **No Attestations:** Remove all `verifier-attestation` entries entirely. Only pure source evidence (e.g., links, verified github-stars, papers, repos) should remain.
- **No Canonical File Modifications:** This skill is strictly for generating reports. Do not modify the canonical `registry/gaia.json` or any canonical `registry/named/` Markdown files.

## Workflow Instructions

1. **Target Identification:** 
   - Parse all named skills from `registry/named/`.

2. **Live Data Fetching:** 
   - For each named skill, extract its primary repository URL.
   - Use `gh repo view <owner>/<repo>` to fetch the authoritative, live internet star count.
   - Cross-reference the live star count with the local registry metadata to identify lags or inflation.

3. **Strict Filtering:** 
   - Iterate through the evidence blocks of each skill.
   - Discard any entry that contains evaluations, recommendations, or critiques.
   - Explicitly discard any entry of type `verifier-attestation`.
   - Keep only clean, verifiable sources.

4. **Tier Segregation:** 
   - Group the filtered named skills by their current star tier (e.g., from 6★ down to 1★).

5. **Artifact Generation:** 
   - Write output to the `founder/sources/` directory (unless the user specifies a different path).
   - Generate individual markdown dumps for each tier: `tier_1.md` through `tier_6.md`. Each file should list the skills, their live star counts, and their filtered raw evidence.
   - Generate a consolidated index report named `source_report_YYYY_MM_DD.md` that highlights identified star count lags/inflations and links to the individual tier files.

6. **Adversarial Audit Invocation:** 
   - Immediately invoke the `gaia-adversarial-audit` skill to perform a multi-agent adversarial audit of all newly generated data lake files.
   - Spawns parallel adversarial reviewers to check for dead links, format errors, evaluative noise, and proxy mismatches, appending a synthesis of the findings directly to `source_report_YYYY_MM_DD.md`.

7. **Commit & Report:** 
   - Stage and commit the generated dumps and updated source report to the active branch (e.g., `dev/sources`) with a descriptive commit message.
   - Follow the `Token Spend Logging` directive and report the token spend at the end of the session.

---
name: gaia-curation-review
description: Review an open curation PR (or branch) to determine exactly what it adds to the registry, surface quality issues, and recommend merge / close / needs-work. Designed for stale Jules-generated PRs where the GitHub diff is buried in generated-file noise.
version: 1.0.0
---

# gaia-curation-review

Review a curation pull request or branch and produce a structured assessment of what it actually adds to the registry, stripped of all generated noise.

## Input

The user provides a PR number (e.g. `349`) or a branch name (e.g. `review/meta/dify-curation-...`). If a PR number is given, resolve the branch from the PR metadata.

## Workflow

### 1. Resolve the branch

If given a PR number, use GitHub MCP tools (`pull_request_read` with `method: get`) to fetch the PR and extract `head.ref` as the branch name. Note the PR title, description, and labels for later cross-checking.

### 2. Fetch the branch locally

```bash
git fetch origin <branch-name>
```

### 3. Run the substantive diff

```bash
gaia dev diff <branch-name>
```

This compares `origin/main..origin/<branch>` using structured JSON parsing of `registry/gaia.json`. It strips all generated files (SVG, HTML, GEXF, timestamps, lock files) and reports only:
- New generic skill nodes (id, type, level, prerequisites, evidence)
- Removed generic skill nodes (danger — flag loudly)
- New named skill files (id, genericSkillRef, level)
- New and removed graph edges
- Version bumps that will conflict with current main
- Quality flags (empty install body, missing genericSkillRef, no/weak evidence, deprecated fields)

### 4. Cross-check PR description vs actual diff

Compare what the PR description *claims* to add against what `gaia dev diff` *actually* shows:
- Does the description match the skill IDs added?
- Does it claim "legendary" or "ultimate" tier but the node is actually `extra`?
- Does it mention specific contributor/repo names that appear in the named skill paths?
- Is the PR title misleading (e.g. "MCP ecosystem" but content is unrelated)?

Flag any mismatch explicitly.

### 5. Check for skill loss (regression)

If there are **removed** skills or edges in the output, this is a critical regression. Curation PRs should be purely additive. If removals appear:
- Identify what was removed and why
- Check if the removals were intentional (e.g. a duplicate merge that dropped content)
- Recommend **do not merge** until resolved, or request the contributor explain the removals

### 6. Assess quality of each new item

For each new **generic skill node**:
- Evidence class: A = strong, B = acceptable, C = weak. Flag C-only or missing evidence.
- Prerequisites: do they all exist in the current registry? Cross-check with `gaia dev list --generic`.
- Status `provisional` with only Class B/C is fine for a curation PR — note it.
- `rarity` field present: deprecated auto-default, not a blocker, just note it.
- Type/tier plausibility: an `extra` with 4 prerequisites and 1 Class B source is reasonable. A claimed `ultimate` with no A evidence is suspect.

For each new **named skill file**:
- `genericSkillRef` must map to a real generic skill ID.
- Empty `## Installation` body: not a blocker for merge but note it as a follow-up.
- `level` should be ≥ 2★ for awakened status.
- Contributor path (`registry/named/<contributor>/`) must be consistent with the evidence source.

### 7. Check merge safety

A PR is **safe to merge** if:
- No existing skills are removed
- All prerequisite IDs in new nodes exist in main's registry
- No version bump that will cause a lockstep conflict (or we will resolve it during rebase)
- Evidence class is B or better for at least one source

A PR needs **manual resolution** if:
- Skills are removed or edges deleted unexpectedly
- Prerequisite IDs don't exist in the registry
- The PR description claims a tier/type that contradicts the actual node

A PR should be **closed** if:
- `gaia dev diff` shows zero substantive changes (all generated noise)
- The branch is already incorporated into main

### 8. Produce the assessment report

Output a structured report with these sections:

```
## PR <number>: <title>

**Branch:** <branch-name>
**Status:** <open|draft>

### What this adds
<table: new skills, named files, edges — copy from gaia dev diff output>

### Claim vs diff check
<any mismatches between PR description and actual content>

### Quality flags
<from gaia dev diff + manual checks>

### Recommendation
MERGE SAFE — rebase and squash, accept main's version files
  or
NEEDS REVIEW — <specific issue>
  or
CLOSE — <reason: already merged / empty / nothing to add>
```

### 9. Optionally execute the merge

If the user confirms they want to proceed, follow the same merge workflow used for routine curation PRs:

1. `git checkout -B <branch> origin/<branch>`
2. `git rebase origin/main` — on conflict in generated files, `git checkout --theirs <file> && git add <file>`; on conflict in `registry/gaia.json`, keep main's version bump but manually preserve the new skill nodes and edges from the branch
3. `git push -u origin <branch> --force-with-lease`
4. If PR is draft, use GitHub MCP `update_pull_request` with `draft: false`
5. Use GitHub MCP `merge_pull_request` with `merge_method: squash`

## Constraints

- Never merge a PR that removes existing skills without explicit user confirmation of intentionality.
- Never hand-edit `registry/gaia.json` to resolve a version conflict — always accept main's version for the version/generatedAt fields, and preserve only the new `skills[]` and `edges[]` entries.
- Do not regenerate docs or run `gaia docs build` as part of this skill — that's handled by the post-merge auto-build CI.
- The `gaia dev diff` command is the authoritative source of truth. GitHub's PR file diff is unreliable for curation PRs because it compares to a stale base and buries real content in regenerated-file noise.

## Output

A concise assessment report (see §8) followed by a clear recommendation. If merge is recommended, list the exact rebase conflict resolution steps needed for this specific PR's generated-file conflicts.

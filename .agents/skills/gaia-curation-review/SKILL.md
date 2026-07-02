---
name: gaia-curation-review
description: >
  Review a curation PR or branch before it merges. Use this skill when someone asks to:
  review a PR, check a curation branch, assess a registry contribution, audit what a PR
  actually adds, determine if a PR is safe to merge, investigate a stale curation PR,
  check schema quality on an incoming batch, evaluate evidence quality on new skills,
  verify prerequisite IDs exist, check nomenclature compliance, confirm CLI usage was
  correct on a curation PR, review a Jules-generated or bot-generated curation, or answer
  "is this PR ready to merge?" Produces a structured MERGE SAFE / NEEDS REVIEW / CLOSE
  recommendation backed by the authoritative `gaia dev diff` output — not GitHub's noisy
  file diff.
version: 1.1.0
---

# gaia-curation-review

Review a curation pull request or branch and produce a structured assessment of what it
actually adds to the registry, stripped of all generated-file noise.

## Input

A PR number (e.g. `349`) or a branch name (e.g. `review/meta/dify-curation-...`). If a
PR number is given, resolve the branch from the PR metadata first.

## Why `gaia dev diff`, not the GitHub file diff

GitHub's PR diff compares to a stale base and buries real content in hundreds of
regenerated lines (SVG, HTML, GEXF, lock files). `gaia dev diff` parses the structured
JSON directly and reports only semantic changes — new skill nodes, removed nodes, new
edges, quality flags. Always use it as the authoritative source.

## Workflow

### 1. Resolve the branch

If given a PR number, use GitHub MCP (`pull_request_read` with `method: get`) to fetch
the PR and extract `head.ref` as the branch name. Note the PR title, description, and
labels — you will cross-check these in step 4.

### 2. Fetch the branch locally

```bash
git fetch origin <branch-name>
```

### 3. Run the substantive diff

```bash
gaia dev diff <branch-name>
```

This compares `origin/main..origin/<branch>` and reports:
- New / removed generic skill nodes (id, type, prerequisites, evidence)
- New named skill files (id, genericSkillRef, level)
- New and removed graph edges
- Version bumps that will conflict with current main
- Quality flags (missing genericSkillRef, empty install body, no/weak evidence)

Removed generics are regressions — flag them loudly.

### 4. Cross-check PR description vs actual diff

A misleading PR description (e.g. claims "legendary" tier but the node is `extra`,
or names skills that don't appear in the diff) is a signal that the contribution was
auto-generated and not human-reviewed. Flag every mismatch explicitly — it tells the
reviewer where to focus.

### 5. Assess quality of each new item

**Generic skill nodes** (starless — they carry no `level`, `demerits`, or stars; those
belong only on named skills):
- Evidence class: A = strong, B = acceptable, C = weak. Flag C-only or missing evidence.
- Prerequisite IDs must exist in the current registry — check with `gaia dev list --generic`.
- `rarity` present: deprecated auto-default, not a blocker, just note it.
- `provisional` status with Class B/C evidence is fine; note it for follow-up.

**Named skill files:**
- `genericSkillRef` must map to a real generic skill ID.
- `level` should be ≥ 2★ for awakened status.
- Empty `## Installation` body is not a blocker but flag as a follow-up.
- Contributor path (`registry/named/<contributor>/`) must match the evidence source.

### 6. Check merge safety

**Safe to merge** when:
- No existing skills are removed
- All prerequisite IDs in new nodes exist in main's registry
- Evidence class is B or better for at least one source
- No version bump that would cause a lockstep conflict (or it will be resolved on rebase)

**Needs manual resolution** when:
- Skills or edges are removed unexpectedly
- Prerequisite IDs don't exist in the registry
- PR description contradicts the actual node tier/type

**Close** when:
- `gaia dev diff` shows zero substantive changes (all generated noise)
- The branch is already incorporated into main

### 7. Produce the assessment report

```
## PR <number>: <title>

**Branch:** <branch-name>
**Status:** <open|draft>

### What this adds
<table: new skills, named files, edges — from gaia dev diff output>

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

### 8. Optionally execute the merge

If the user confirms they want to proceed:

1. `git checkout -B <branch> origin/<branch>`
2. `git rebase origin/main`
   - Conflict in generated files: `git checkout --theirs <file> && git add <file>`
   - Conflict in `registry/gaia.json`: accept main's version bump; manually preserve only
     the new `skills[]` and `edges[]` entries from the branch. Never hand-edit the version
     or `generatedAt` fields — that's what causes lockstep failures.
3. `git push -u origin <branch> --force-with-lease`
4. If PR is draft: GitHub MCP `update_pull_request` with `draft: false`
5. GitHub MCP `merge_pull_request` with `merge_method: squash`

## Constraints

- Never merge a PR that removes existing skills without explicit user confirmation.
- Do not regenerate docs or run `gaia dev docs` here — that's the post-merge CI's job.

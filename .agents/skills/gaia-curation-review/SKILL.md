---
name: gaia-curation-review
description: >
  Review a Gaia curation PR or branch as a read-only merge gate. Use for canonical registry promotion, schema, evidence, prerequisite, nomenclature, installability, and generated-artifact checks. Route intake batches to /gaia-draft-curate and unrelated PRs to /review.
version: 2.0.0
---

# gaia-curation-review

Assess what a curation PR actually changes and return a structured recommendation. This skill is a read-only gate: it does not rebase, push, merge, force-push, or modify the PR.

## Scope routing

Classify before reviewing:

- Intake-only PR or `registry-for-review/` batch → route to `/gaia-draft-curate`.
- Canonical registry promotion/curation PR → continue below.
- Unrelated code or documentation PR → route to `/review`.

## Workflow

### 1. Resolve PR and branch

For a PR number:

```bash
gh pr view <number> --json number,title,state,isDraft,headRefName,baseRefName,url,body,labels
```

For a branch, identify its base and remote. Fetch without changing the current branch:

```bash
git fetch origin <branch> <base>
```

Use a disposable worktree for checks so generated or ignored output cannot pollute the maintainer's working tree:

```bash
git worktree add --detach /tmp/gaia-review-<id> origin/<branch>
```

### 2. Establish the substantive diff

Run:

```bash
gaia dev diff origin/<branch>
git diff --check origin/<base>...origin/<branch>
```

`gaia dev diff` is the semantic summary, but it is not the only authority. Inspect source changes under:

- `registry/nodes/`;
- `registry/named/`;
- `registry/suites/`, when present;
- `registry-for-review/`, for routing only;
- `docs/graph/`, to confirm Class S regeneration when required.

Do not treat generated Class P files as the source of truth.

### 3. Compare claims with reality

Cross-check the PR title/body against the semantic diff. Flag every mismatch, including claimed skills absent from the diff, incorrect taxonomy/type language, unexpected removals, and claims that generated artifacts were updated when they were not.

### 4. Review canonical changes

For generic nodes:

- prerequisites exist and form a valid DAG;
- type and nomenclature match the current schema and `CONTEXT.md`;
- evidence is present with valid provenance;
- duplicate or overlapping generic mappings are explained;
- no existing generic or edge is removed without explicit justification.

For named skills:

- `genericSkillRef` resolves;
- contributor path and source identity agree;
- status/title or `catalogRef` requirements are satisfied;
- level/star changes are evidence-backed and timeline implications are understood;
- installable non-suite skills use a specific `links.github` `blob/` URL, or explicitly declare non-installability;
- suite components and suite links point to their actual subpaths;
- terminology follows `CONTEXT.md` and does not introduce deprecated vocabulary.

For evidence:

- record evidence type, grade, source URL, and required numeric/provenance fields;
- distinguish evidence requiring live verification from evidence already validated;
- flag dead, bare-repository, `tree/`, duplicated, subjective, or unsupported evidence;
- do not use legacy Class A/B/C rules as the sole merge gate when the current evidence model provides more specific fields.

### 5. Check repository and generated-artifact scope

Confirm branch scope is allowed by the branch prefix and project rules. When canonical registry sources change, verify the PR includes required Class S artifacts under `docs/graph/` or clearly explains why regeneration is deferred.

Check:

```bash
gaia dev validate
gaia dev docs --check
gaia dev test all
```

If named star levels or timelines changed, also run:

```bash
python3 scripts/validate_timelines.py
```

Record commands that could not run and why. Do not assume a successful command that was not executed.

### 6. Report severity and recommendation

Separate:

- **Blocking failures** — cannot merge safely;
- **Warnings** — follow-up recommended but not necessarily blocking;
- **Evidence pending verification** — requires live/source review;
- **Checks run** — exact commands and outcomes.

Use exactly one recommendation:

- `MERGE SAFE` — substantive checks pass; normal rebase/merge is a maintainer action;
- `NEEDS REVIEW` — list concrete blockers or unresolved questions;
- `CLOSE` — empty, already merged, or no substantive change;
- `ROUTE` — wrong workflow, with the destination skill.

## Report format

```text
## PR <number>: <title>

Branch: <head> → <base>
Status: <state>

### Scope classification
<canonical / intake / unrelated>

### What this changes
<generic nodes, named skills, edges, removals, generated artifacts>

### Claim vs diff
<mismatches or none>

### Blocking failures
<items or none>

### Warnings
<items or none>

### Evidence pending verification
<items or none>

### Checks run
<commands and outcomes>

### Recommendation
MERGE SAFE | NEEDS REVIEW | CLOSE | ROUTE
```

Never merge or alter the branch as part of this skill.

---
name: gaia-draft-curate
description: >
  Triage and classify pending Gaia skill intake batches in registry-for-review/. Use for gaia push intake proposals, draft skill batches, and deciding whether proposals should proceed to canonical curation. This skill is read-only and never promotes skills itself.
version: 2.0.0
---

# gaia-draft-curate

Review and classify pending skill proposals staged by `gaia push`. This is the intake decision gate between `registry-for-review/` and canonical curation.

## Ownership

This skill owns only intake batches and their linked intake issues/PRs. It does not:

- mutate `registry/`, `registry/gaia.json`, or batch JSON files;
- perform broad issue triage (use `/gaia-triage`);
- deeply audit an existing canonical curation PR (use `/gaia-curation-review`);
- promote accepted proposals (hand off to `/gaia-curate-chain` or `/gaia-curate`).

## Workflow

### 1. Establish a clean review state

```bash
git status --short --branch
python3 scripts/validate_intake.py
```

If the working tree contains unrelated changes, report them and do not alter them. If intake validation fails, stop and report the malformed batch.

### 2. Inventory immutable batches

Inspect `registry-for-review/skill-batches/*.json`, excluding `.gitkeep`. Record for each batch:

- `batchId`, generation time, source, and proposed items;
- proposal ID, name, type, description, source repository, supplied evidence, and similarity hints;
- `knownSkills` as informational context only.

Never edit or rewrite an intake batch. These are immutable submission records.

### 3. Link batches to intake tracking

Use GitHub CLI when authenticated:

```bash
gh issue list --state open --search 'label:draft-skills'
gh pr list --state open --label draft-skills --json number,title,headRefName,url
```

Match `batchId` in titles, bodies, or comments. Report:

- batches without a linked issue/PR;
- linked issues/PRs without a local batch;
- duplicate batches or proposals.

If GitHub authentication is unavailable, state that limitation rather than guessing.

### 4. Prepare the decision table

Use only facts present in the batch and verified canonical lookups. Do not invent evidence grades or impose repository-star/recency thresholds here; deep evidence research belongs to the downstream curation workflow.

| # | Proposed ID | Name | Type | Existing match | Supplied evidence | Open questions | Decision |
|---|---|---|---|---|---|---|---|
| 1 | `skill-id` | Skill name | basic/fusion | generic or none | URLs/artifacts | missing facts | pending |

Check for obvious canonical duplicates with read-only commands such as:

```bash
gaia dev list --generic --named
```

For each proposal, collect a rationale and, when applicable, the target canonical ID for a rename or duplicate decision.

### 5. Collect explicit decisions

Work one batch at a time. Valid decisions are:

- `accept` — proceed to canonical curation;
- `rename <new-id>` — accept under a corrected ID;
- `duplicate <existing-id>` — already represented;
- `needs-evidence` — hold and state exactly what is missing;
- `reject` — decline with a reason.

Every decision must include a short rationale. Do not silently discard proposals.

### 6. Produce a handoff packet

Summarize:

- source `batchId` and linked issue/PR;
- accepted/renamed/held/dropped proposals;
- decision rationales;
- canonical mappings;
- evidence and URL questions still requiring research;
- proposed branch scope (`review/gaia-push/*` for intake, `review/meta/*` for canonical changes).

The packet may be saved as `/tmp/gaia-draft-curate-<batchId>.md`. Write a repository Markdown artifact only when explicitly requested. Never modify the source batch.

### 7. Hand off only with confirmation

Ask whether to continue. By default, hand accepted items to `/gaia-curate-chain` for discovery-packet validation and L4 review only. After L4, preserve the batch and issue/PR links, route unresolved evidence to `/ev-pipeline`, and hand verified rows to a maintainer for the CLI-only meta shift. The chain does not mutate the registry or sync docs. Use `/gaia-curate` only when the user explicitly chooses the lower-overhead path for a low-risk batch.

The handoff must preserve the originating batch and issue/PR links. This skill itself does not run `gaia dev add`, `gaia dev evidence`, or any other mutating command.

## Final report

```text
Batches reviewed: N
Tracking links: N found, N missing
Decisions: N accepted, N renamed, N held, N duplicated, N rejected
Promotion triggered: no (or explicit downstream handoff and branch)
Validation: commands run and results
```

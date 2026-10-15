# Gaia Skill Batch Intake

`gaia push` writes reviewable skill batches to `registry-for-review/skill-batches/`.
Use `gaia push --dry-run` to preview and `gaia push --no-pr` to write the batch
without opening a PR.

Batch files are canonical intake records, not canonical DAG nodes. Maintainers
review proposed skills in batches, merge similar proposals, and promote accepted
skills into `registry/gaia.json`.

Typical lifecycle:

1. Contributor runs `gaia scan` to detect skills and render their local tree.
2. Contributor runs `gaia push` or `gaia push --no-pr` to generate the intake batch.
3. Reviewers classify each proposed skill as `accept`, `rename`, `duplicate`, `needs-evidence`, or `reject`.
4. Maintainers promote accepted skills via a separate canonical registry PR.

Validate intake records with:

```bash
python3 scripts/validate_intake.py
```

## Skill Lifecycle

Each proposed skill in a batch has a `lifecycle` field:

1. **pending**: Initial state when `gaia push` creates the batch. Awaiting reviewer classification.
2. **awakened**: Reviewer has accepted the skill but it has no named attribution yet. The skill exists in the registry's awareness but is not tied to a specific implementation.
3. **named**: A contributor has claimed the skill and promoted it to `registry/named/{contributor}/{skill-name}.md`. The skill is now a fully attributed, named implementation.

## Relationship to the Skill Tree

This directory is the review queue, not a user's tree. User-owned skill progress lives in `skill-trees/<username>/skill-tree.json`, while local renders and promotion recommendations live in `generated-output/`.

Pending intake from the configured user is visible in `gaia skills list`, `gaia skills search`, and `gaia skills info` by default. Use `--exclude-pending` when you only want maintainer-reviewed named skills.

## Recovering an intake whose batch was never committed

`gaia push` writes the batch JSON only to the submitter's disk, so an approved intake can exist as an issue alone. The topology job then stops with "batch file is not on this branch".

A repository maintainer (admin, maintain or write) can recover it explicitly by running **Intake Approval** with `workflow_dispatch`:

- `transition`: `topology`, `issue_number`: the intake issue
- `recovery`: `true`, and `recovery_rationale`: why the recovery is authorized
- `recovery_facts` (optional): JSON `{"<skillId>": {"description", "name", "type", "prerequisites", "skillFileUrl"}}` for facts the issue does not show, e.g. descriptions or the upstream `SKILL.md` blob URL of a scan-based intake

`scripts/intake_recovery.py` rebuilds a current review record from the issue's structured submission and the upstream `SKILL.md` blobs, which it fetches and hashes. It never guesses: missing facts are listed by name and nothing is written. The result is a **reconstruction**, not the original bytes: the batch keeps the original batch id, candidate ids, user and `generatedAt`; `registry-for-review/recoveries/intake-<N>.json` records `reconstruction: true`, `originalBytesRecovered: false`, the source URLs and SHA-256 hashes, the actor and the rationale. No evidence, approval, discovery packet or assessment receipt is invented; fresh canonical assessments satisfy the current review obligations.

Everything after recovery is unchanged: schema and intake validation, L4 human review, `intake:evidence-ready` and `intake:evidence-approved`, and the single `review/meta/intake-<N>` promotion PR, which carries the reconstructed batch and its receipt. Replaying a recovery with identical inputs is a no-op; an existing batch file is never overwritten, and upstream bytes that changed since the recorded hashes are rejected as stale.

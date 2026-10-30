---
name: gaia-steward-land
description: >-
  Land a Gaia Steward Class A repair (agent-skill mirror or bundled-schema
  mirror) as a deterministic commit on a steward/a/* branch, open a draft PR to
  the integration branch, and record the outcome. Use when a full Steward run
  emits a forge.open_pr action, for "land the class A repair", or "open the
  steward PR". Never targets main and never merges.
version: 1.0.0
---

# gaia-steward-land

## Responsibility

Turn one verified Class A repair into a reviewable branch and draft PR on the
integration branch. The runner builds the commit; this skill only opens the PR
and records it.

Only `forge.open_pr` is landed here. An issue closure (`forge.close_issue`) is not a
landing and is never performed by this skill; hand it to `gaia-steward-issue-hygiene`.

## Input

A pending `forge.open_pr` action from `gaia steward full run`. Its `params` give
the `branch` (`steward/a/<kind>-<fingerprint>`), the `base` (the integration
branch) and a PR body file under `.gaia/steward/full/<run>/`.

## Output

A draft PR from `params.branch` to `params.base`, recorded with:

```bash
gaia steward full record RUN STEP --input pr.json
```

where `pr.json` is `{"pullRequest": {"number": 123, "url": "..."}, "merged": false}`.

## Authority ceiling

- Only the two Class A executors in `POLICY.yaml` produce landings.
- The commit touches only the executor's writable mirror path, proven by a
  parity check of the committed tree.
- Base is the configured integration branch; the runner refuses `main`,
  `master` and the remote default. No force push, no merge.

## Stop conditions

- The run reports unknown coverage: no landing this run.
- `params.base` is not a `dev/*` integration branch: refuse and report.
- A PR for the branch already exists: record that PR, do not open a second.

## Idempotency

The branch name binds the debt and the canonical digest, so the same drift
lands once. Re-running reports `already-exists`.

## Failure states

`blocked` (dirty plan, parity mismatch, protected base, push refused) or
`already-exists`. Neither is retried automatically.

## Validation

```bash
python -m pytest tests/steward/test_landing.py tests/steward/test_repairs.py -q
```

## Tests

`tests/steward/test_landing.py`, `tests/steward/test_fullrun_scenarios.py`,
`tests/steward/test_steward_skills.py`.

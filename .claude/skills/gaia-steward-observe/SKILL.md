---
name: gaia-steward-observe
description: >-
  Observe the repository with every registered Gaia Steward detector and report
  what each one actually saw, without changing anything. Use for
  "/gaia-steward-full --observe", "what is Steward seeing", "scan the repo for
  maintenance debt", or as the first phase of a full Steward run. Distinguishes
  actively observed, unknown/unavailable and not-evaluated detectors; never
  treats an unexecuted probe as healthy.
version: 1.0.0
---

# gaia-steward-observe

## Responsibility

Run the detector fleet once against the checkout head and produce a receipt
that says, per detector, whether it observed, could not observe, or was not
evaluated. Nothing else.

## Input

- A Git worktree of `gaia-skill-tree` (the detectors read Git's index, not the
  filesystem).
- Optional driver inputs under the ignored `.gaia/steward/inputs/`:
  `ci-runs.json`, `advisories.json`, `test-history.json`. Their absence is a
  not-evaluated state, never an error and never healthy.
- The GitHub issue census `github-issues.json` (routine 18, `issue-hygiene`), refreshed
  by `python scripts/steward_issue_census.py` before observing. A missing census reports
  routine 18 not evaluated. An incomplete or stale census reports it unavailable, which
  blocks Class A for the run.

## Output

```bash
gaia steward full run --observe --json
python scripts/check_steward_coverage.py --receipt .gaia/steward/receipts/<run>.json
```

The receipt (`steward-receipt-v1`) carries `coverageKnown`, `coverageUnknown`,
`notEvaluated`, `openDebt` and `authorityCounts`. The checker turns it into a
live state per detector: `actively-observed` only when listed in
`coverageKnown`; everything else is `unknown-unavailable`.

## Authority ceiling

Read-only. Writes only ignored state under `.gaia/steward/` and the run record in
the Steward ledger. No repair, dispatch, branch or PR.

## Stop conditions

- Any detector in `coverageUnknown`: report it first and stop treating the run
  as clean; Class A is blocked for the run.
- The observation budget in `POLICY.yaml` is exceeded: stop and report.

## Idempotency

Observing the same head twice yields the same debt ids
(`debt:{kind}:{slug}:{digest}`); re-observation updates `lastSeen`, never
duplicates debt.

## Failure states

| State | Meaning |
|---|---|
| `coverageUnknown` | a required input was missing, truncated or unreadable |
| `notEvaluated` | an optional driver input was not supplied |
| `blocked` result | at least one detector was unknown |

## Validation

```bash
python scripts/check_steward_coverage.py
python -m pytest tests/steward/test_controller.py tests/steward/test_coverage_regressions.py -q
```

## Tests

`tests/steward/test_controller_resolution.py`, `tests/steward/test_routine_coverage.py`,
`tests/steward/test_steward_skills.py`.

---
name: gaia-steward-issue-hygiene
description: >-
  Perform one proven GitHub issue closure for Gaia Steward issue hygiene (the
  forge.close_issue action): re-read the live issue, prove the closing comment is
  ours, post it, close the issue, write a receipt and record the outcome. Use when
  a full Steward run emits forge.close_issue, for "/gaia-steward-full" showing
  issue_closure_ready debt, or "close the proven issues". Closes only the one issue
  the action names, and only when its snapshot still matches.
version: 1.0.0
---

# gaia-steward-issue-hygiene

## Responsibility

Carry out one `forge.close_issue` action: close one GitHub issue whose preservation
the registry already proves, and record what happened. The runner has already decided
that this closure is allowed (rule, complete census, manifest snapshot, per-run cap).
This skill does only the forge work and the bookkeeping. It never reconciles, never
accepts a candidate, and never edits anything but that one issue.

## Input

A pending `forge.close_issue` action from the run. Read it without advancing the run:

```bash
gaia steward full run --resume RUN --json
```

Its `params` are the closure plan: `key`, `issue`, `ruleId`, `expectedSnapshot`
(`updatedAt`, `bodySha256`, `labels`, `title`), `comment` (the closing comment with its
`<!-- gaia-steward-closure:{key}:{manifestSha8} -->` marker), `stateReason`,
`duplicateOf`, `receiptPath` and `manifestSha256`. Write `params` verbatim to
`ACTION.json`.

## Output

1. Perform the closure. This is the same script the driver runs:

```bash
python scripts/steward_issue_close.py --action ACTION.json --root . --repo gaia-research/gaia-skill-tree --run-id RUN
```

It prints one JSON line on stdout: `outcome`, `key`, `issue`, `commentUrl`,
`commentId`, `markerVerified`, `closedAt`, `failure`. It appends one receipt to
`receiptPath` under `.gaia/steward/issue-hygiene/receipts/`.

2. Record that line as the outcome of the step:

```bash
gaia steward full record RUN STEP --input outcome.json
```

A `closed` outcome must carry proof of its closing comment: `commentUrl`, a
`commentId`, or `markerVerified: true`. The runner refuses a `closed` record without one.

## Authority ceiling

- Closes exactly `params.issue`, and only when its live `updatedAt`, `bodySha256`,
  labels and title equal `expectedSnapshot`. Any difference is `stale-skip`: no write.
- Writes one comment (the marked closing comment), or finds one already posted. Never
  a second comment for the same key and manifest.
- Never edits a title or body, never deletes, never reopens, never touches another
  issue, and never edits `registry/`, `POLICY.yaml` or `.gaia/steward/` state beyond
  the receipt and the recorded outcome.
- Requires `GH_TOKEN` or `GITHUB_TOKEN`. Without one, nothing is performed.
- Downgrade-only: any doubt about the proof, the snapshot or the forge is `failed`
  or `stale-skip`, never a close.

## Stop conditions

- `blocked` (script exit 3: auth, rate limit or transport): stop the batch and report.
  Do not retry in the same run; the forge is not trustworthy until a person looks.
- Script exit 2 (`refused`): the action file is malformed or its receipt is outside the
  store. Do not record anything. Report it as a runner defect.
- A closing comment posted but not verifiable on re-read: the issue stays open and the
  outcome is `failed`. Never close blind.
- A step refused twice: the runner stops; report the step and its reason.

## Idempotency

- Exactly-once per (key, issue): the runner never emits a pair already recorded as
  `closed` or `already-closed` in the outcome store or a receipts file. A repeated
  script run on such an issue finds it closed on the live re-read and writes nothing.
- A crash between the comment and the close resumes through the marker: the next
  attempt finds the comment, reuses its URL and only closes.
- Recording an identical outcome again is a no-op. A different outcome for a terminal
  step is refused.

## Failure states

| Outcome | Meaning | Retry |
|---|---|---|
| `closed` | comment verified (or found), issue closed, receipt written | none needed |
| `already-closed` | the live issue was already closed | none needed |
| `stale-skip` | the live issue moved since the manifest; nothing written | next scan re-observes |
| `failed` | this item only (write or verify failed) | up to three attempts, then a human |
| `blocked` | auth, rate or transport failure; batch stops | after a person checks the token |

## Validation

```bash
python -m pytest tests/steward/issuehygiene/test_d2_close_script.py tests/steward/test_steward_drive_close.py tests/steward/issuehygiene/test_closure_proof.py -q
python scripts/check_steward_coverage.py --check
```

## Tests

`tests/steward/issuehygiene/test_d2_close_script.py`, `tests/steward/test_steward_drive_close.py`,
`tests/steward/issuehygiene/test_closure_proof.py`, `tests/steward/test_steward_skills.py`.

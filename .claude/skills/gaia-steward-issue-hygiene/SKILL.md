---
name: gaia-steward-issue-hygiene
description: >-
  Perform one proven GitHub issue closure for Gaia Steward issue hygiene (the
  forge.close_issue action): the executor re-derives the proof from the checkout, re-reads
  the live issue, posts or finds our marked comment, closes the issue and writes a receipt.
  Use when a full Steward run emits forge.close_issue, for "/gaia-steward-full" showing
  issue_closure_ready debt, or "close the proven issues". Closes only the one issue the
  action names, and only when the census still proves it.
version: 1.1.0
---

# gaia-steward-issue-hygiene

## Responsibility

Carry out one `forge.close_issue` action: close one GitHub issue whose preservation the
registry already proves, and record what happened. The action file is a request, not a
proof. `scripts/steward_issue_close.py` does not trust it. It re-derives the closure from
the checkout and refuses unless every gate below still holds. This skill does only the forge
work and the bookkeeping. It never reconciles, never accepts a candidate, and never edits
anything but that one issue.

## Input

A pending `forge.close_issue` action from the run. Read it without advancing the run:

```bash
gaia steward full run --resume RUN --json
```

Its `params` are the closure plan: `key`, `issue`, `ruleId`, `expectedSnapshot`,
`comment` and `comments` (the closing comments; the first carries the marker
`<!-- gaia-steward-closure:{key}:{closureSha8} -->`), `stateReason`, `duplicateOf`,
`receiptPath`, `manifestSha256` (the digest the sensor reports) and `repo`. Write `params`
verbatim to `ACTION.json`.

## Output

1. Perform the closure:

```bash
python scripts/steward_issue_close.py --action ACTION.json --root . --repo gaia-research/gaia-skill-tree --run-id RUN
```

It prints one JSON line: `outcome`, `key`, `issue`, `closedAt`, `failure`,
`preservedSha256`, and exactly ONE proof field: `commentUrl` (a GitHub comment URL on this
issue), `commentId`, or `markerVerified: true`. It appends one receipt to `receiptPath`.

2. Record that line as the outcome of the step:

```bash
gaia steward full record RUN STEP --input outcome.json
```

A `closed` outcome must carry exactly one proof of its closing comment. Two or more proofs,
a URL that does not name this issue and repo, or no proof at all is refused.

## Authority ceiling

The executor re-derives every gate below before any forge is built:

1. `founder/steward/POLICY.yaml` sets `issueHygiene.writesEnabled: true`.
2. The action's rule is in `issueHygiene.enabledRules`. An A5 closure also needs a
   non-empty `a5Disabled` covering every workflow its evidence names.
3. This run has not reached `issueHygiene.maxClosuresPerRun` (closed receipts for the run id count).
4. `receiptPath` is under `.gaia/steward/issue-hygiene/receipts/`, reached through no symlink.
5. `.gaia/steward/inputs/github-issues.json` is a complete, fresh census.
6. Reconciling that census reproduces the action's `manifestSha256`, still proves the same
   (key, issue, rule), and yields the same closing comments. A moved census refuses the
   action; the next scan re-observes it.

- Closes exactly `params.issue`, and only when its live title, body, labels and state equal
  `expectedSnapshot`. The live `updatedAt` may differ only when our own marker comment for this
  closure explains it. Any other difference is `stale-skip`: no write.
- Writes the marked closing comments, or finds them already posted by the closer identity.
  Another author's comment, or a marker for another closure decision, is never proof.
- Never edits a title or body, never deletes, never reopens, never touches another issue, and
  never edits `registry/`, `POLICY.yaml` or `.gaia/steward/` state beyond the receipt and the
  recorded outcome.
- Requires `GH_TOKEN` or `GITHUB_TOKEN`. Without one, nothing is performed.
- Downgrade-only: any doubt about the proof, the snapshot or the forge is `failed`,
  `blocked-identity` or `stale-skip`, never a close.

Exit codes, as the script prints them:

- 0 — closed, already-closed, or stale-skip: nothing wrong; the outcome line says which.
- 1 — failed, or blocked-identity (the live issue is locked, a pull request, renumbered or
  transferred; nothing was written): this item only, retryable up to three attempts.
- 2 — refused: a gate above did not hold, or the action cannot be performed as written. No
  forge is built and nothing is written. The runner treats this as non-retryable and skips it.
- 3 — blocked: auth, rate limit or transport failure, or no token. The batch stops.

## Stop conditions

- Exit 3 (`blocked`): stop the batch and report. Do not retry in the same run; the forge is
  not trustworthy until a person looks.
- Exit 2 (`refused`): do not record anything. Report the gate that refused it.
- A closing comment posted but not verifiable on re-read: the issue stays open and the outcome
  is `failed`. Never close blind.
- A step refused twice: the runner stops; report the step and its reason.

## Idempotency

- Exactly-once per (key, issue): the runner never emits a pair already recorded as `closed` or
  `already-closed`. A pair the receipts file already records as done is skipped with no forge call
  and no new receipt.
- A crash between the comment and the close resumes on the same closure: the next attempt finds
  our marked comment, posts nothing new, and closes.
- Closures for the same pair are serialized by a lock next to the receipts. A second closer waits,
  then re-reads the live issue and finds it closed: it writes nothing.
- Recording an identical outcome again is a no-op. A different outcome for a terminal step is refused.

## Failure states

| Outcome | Meaning | Retry |
|---|---|---|
| `closed` | comment verified (or found), issue closed, receipt written | none needed |
| `already-closed` | the live issue was already closed | none needed |
| `stale-skip` | the live issue moved since the manifest; nothing written | next scan re-observes |
| `blocked-identity` | locked, a pull request, renumbered or transferred; nothing written | a person checks the issue |
| `failed` | this item only (write or verify failed) | up to three attempts, then a human |
| `blocked` | auth, rate or transport failure; batch stops | after a person checks the token |

## Validation

```bash
python -m pytest tests/steward/issuehygiene/test_b5_closure_guard.py tests/steward/issuehygiene/test_d2_close_script.py tests/steward/issuehygiene/test_closure_proof.py -q
python scripts/check_steward_coverage.py --check
```

## Tests

`tests/steward/issuehygiene/test_b5_closure_guard.py`, `tests/steward/issuehygiene/test_d2_close_script.py`,
`tests/steward/issuehygiene/test_closure_proof.py`, `tests/steward/issuehygiene/test_b5_policy_docs.py`,
`tests/steward/test_steward_skills.py`.

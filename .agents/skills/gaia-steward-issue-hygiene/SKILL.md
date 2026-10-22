---
name: gaia-steward-issue-hygiene
description: >-
  Perform one proven GitHub issue closure for Gaia Steward issue hygiene (the
  forge.close_issue action): the executor re-derives the proof from the checkout, re-reads
  the live issue, posts or finds our marked comment, closes the issue and writes a receipt.
  Use when a full Steward run emits forge.close_issue, for "/gaia-steward-full" showing
  issue_closure_ready debt, or "close the proven issues". Closes only the one issue the
  action names, and only when the census still proves it.
version: 1.2.0
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

Its `params` are compact (B7 D5): identifiers and digests, not the closing comments. They are
`key`, `issue`, `ruleId`, `authority`, `state`, `stateReason`, `duplicateOf`, `parent`, `canonical`,
`expectedSnapshot`, `evidence` (type, ref and sha256 only), `closureSha8`, `preservedSha256`,
`receiptPath`, `manifestSha256` (the digest the sensor reports) and `repo`. Write `params` verbatim to
`ACTION.json`. The executor rebuilds the closing comments and the preserved candidate information from
the census, and refuses unless the digests match the re-derived closure.

## Output

1. Perform the closure:

```bash
python scripts/steward_issue_close.py --action ACTION.json --root . --repo gaia-research/gaia-skill-tree --run-id RUN
```

It prints one JSON line: `outcome`, `key`, `issue`, `closedAt`, `failure`,
`preservedSha256`, and exactly ONE proof field: `commentUrl` (a GitHub comment URL on this
issue), `commentId`, or `markerVerified: true`. It appends one receipt to `receiptPath`. A repeat
run on a pair this checkout already recorded prints the recorded outcome again and writes nothing (exit 0).
`--now` is ignored: freshness uses the real clock.

2. Record that line as the outcome of the step:

```bash
gaia steward full record RUN STEP --input outcome.json
```

A `closed` outcome must carry exactly one proof of its closing comment. Two or more proofs,
a URL that does not name this issue and repo, or no proof at all is refused.

## Authority ceiling

The executor re-derives every gate below before any forge is built:

1. `founder/steward/POLICY.yaml` sets `issueHygiene.writesEnabled: true`, and the policy parses.
2. The action's rule is in `issueHygiene.enabledRules`. An A5 closure also needs a
   non-empty `a5Disabled` covering every workflow its evidence names.
3. This run has not reached `issueHygiene.maxClosuresPerRun` (closed receipts for the run id count).
4. The hourly budget is not spent: closures recorded in any run count. At most `maxClosuresPerRun`
   per UTC hour, and never more than 25 in any 60 minutes.
5. `receiptPath` is under `.gaia/steward/issue-hygiene/receipts/`, reached through no symlink.
6. `.gaia/steward/inputs/github-issues.json` is a complete, fresh census for the repository the action
   names (`repo`), and `--repo` (the close script's default is the census repository) names the same one.
7. Reconciling that census reproduces the action's `manifestSha256`, still proves the same
   (key, issue, rule), and the re-derived closure's `closureSha8` and `preservedSha256` match the action.
   A moved census refuses the action; the next scan re-observes it.

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

Exit 0 also covers `resumed-done`: a repeat of a closure already recorded, printed from its receipt.

### Pilot procedure (contract section 6)

The pilot is never enabled in the committed policy. It runs in a throwaway checkout:

1. Copy the checkout to a throwaway directory. In that copy only, edit `founder/steward/POLICY.yaml`:
   `issueHygiene.writesEnabled: true` and `maxClosuresPerRun: 5`. Do not commit the edit.
2. Run the one executor, the same gate this skill uses:

```bash
python scripts/steward_issue_reconcile.py --apply-closures --receipts .gaia/steward/issue-hygiene/receipts/pilot.jsonl \
  --i-understand-writes --repo gaia-research/gaia-skill-tree --max-closures 5
```

`--now`, `--policy` and `--census` are refused on this path. `--max-closures` can only lower the cap.
With `writesEnabled` false the command refuses (exit 2) and makes no forge call.

## Stop conditions

- Exit 3 (`blocked`): stop the batch and report. Do not retry in the same run; the forge is
  not trustworthy until a person looks.
- Exit 2 (`refused`): do not record anything. Report the gate that refused it.
- A closing comment posted but not verifiable on re-read: the issue stays open and the outcome
  is `failed`. Never close blind.
- A closure the gate refuses (exit 2) is skipped and reported at the next scan; it is never re-sent
  in the same run.
- Writes switched off (or the closure rule disabled) after a closure was emitted: the runner cancels
  the pending closure (reason `writes-disabled`) and the driver reports "writes disabled". Nothing is written.

## Idempotency

- Exactly-once per (key, issue): the runner never emits a pair already recorded as `closed` or
  `already-closed`. A pair the receipts file already records as done is skipped with no forge call
  and no new receipt.
- A crash between the comment and the close resumes on the same closure: the next attempt finds
  our marked comment, posts nothing new, and closes.
- Closures for the same pair are serialized twice: a lock beside the receipts store, and a lock keyed by
  (repo, issue) in the user-level lock directory, so two checkouts on one machine cannot both comment. A
  second closer waits, then re-reads the live issue and finds it closed: it writes nothing. Across machines
  the marker check and the live re-read are the guard.
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
python -m pytest tests/steward/issuehygiene -k "not hardlink" -q
python scripts/check_steward_coverage.py --check
```

## Tests

`tests/steward/issuehygiene/test_b5_closure_guard.py`, `tests/steward/issuehygiene/test_d2_close_script.py`,
`tests/steward/issuehygiene/test_closure_proof.py`, `tests/steward/issuehygiene/test_b5_policy_docs.py`,
`tests/steward/issuehygiene/test_b7_executor.py` (the one gate), `tests/steward/issuehygiene/test_b7_runner.py`
(kill switch, receipts, malformed policy), `tests/steward/issuehygiene/test_b7_scrub.py`,
`tests/steward/issuehygiene/test_b7_lock.py`, `tests/steward/test_steward_skills.py`.

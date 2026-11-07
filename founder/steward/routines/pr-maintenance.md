# Routine — Routine pull-request maintenance

| | |
|---|---|
| **Sensor** | `pr-maintenance` — reads the driver census `.gaia/steward/inputs/github-prs.json` (`steward-pr-census-v1`), `founder/steward/pr-producers.json` and local git objects |
| **Debt kinds** | `routine_pr_merge_ready`, `routine_pr_blocked`, `routine_pr_superseded`, `routine_pr_conflict`, `routine_pr_verification_failed`, `routine_pr_provenance_unknown`, `routine_pr_closure_ready` (Class B); `routine_pr_founder_decision` (Class C) |
| **Authority** | Class B by default, proven by policy and evidence, never inferred from an author or title. Class C stops the affected write |
| **Forge actions** | `forge.merge_pr`, `forge.close_pr`, both behind `src/gaia_cli/steward/prmaintenance/gate.py` |
| **Routine catalog** | #19 — Routine Pull-Request Maintenance |
| **Decision record** | `founder/steward/decisions/steward-pr-maintenance-authority.json` (decided, approved, 2026-11-04) |
| **Skill** | `gaia-steward-pr-maintenance` |

## What it is for

Weekly content-engine reports and scheduled documentation routines produce pull requests and then stop. Nobody owns their
last mile. This routine does: it proves a pull request is routine work, verifies the exact candidate, reconciles what is stale,
merges what is eligible, closes what is provably superseded, and escalates what only the founder can decide, with a GitHub
trail at every step.

## Producer registry

`founder/steward/pr-producers.json` names each producer's repository, workflow, verified identity (login, account id, type),
verified commit authors, branch convention, labels, hold labels, allowed and protected paths, required checks, required approvals,
destination, merge method, closure eligibility, validator and reconciler. `scope.deferredRepos` records repositories that are
deliberately not observed; they are reported as unknown coverage.

## Gates (all must pass for `routine_pr_merge_ready`)

provenance (identity, branch, labels, same-repository head, commit authors) · state and draft · holds (labels, change requests, a
maintainer's `steward-hold` comment, unresolved threads) · approvals at the exact head · file scope (allowed paths only, nothing
removed or renamed) · required checks present and passing at the head · destination currency · mergeability · content proofs
(content engine: canonical JSON, base-template regeneration of the HTML, shared-index rebuild from base history, version stamps).

## Reconciliation

Only deterministic reconcilers exist. `content-engine-cachebust` regenerates `?v=` stamps and the two shared report indexes from
the repository's own generator on a tracked replacement branch; the producer's branch is never rewritten. A conflict that is not
mechanically reproducible is reported, not hand-resolved.

## Explicit execution and local/shared split

Observation, census, profiles and dispatches remain checkout-local. Ordinary `steward full` run state is unchanged: it stays on the
shared Git ledger exactly as before (`--ledger auto|git|local`), and only the Lead writes it. The unattended driver still refuses
PR writes. `gate-merge` / `gate-close` create shared preparation and an exact intent, not a send authorization. Only explicit
`execute --operation-id ID` enters the one-shot core. `recover` / `finalize --operation-id` reconcile without resend;
`abort --operation-id ID --reason TEXT` cancels only unsent preparation (the reason is recorded); `takeover --operation-id ID` re-owns an expired unsent preparation. Unsafe legacy authorization JSON/local outcomes are not authority.

An optional strict `prMaintenance.writeCoordination` binding must be separately provisioned: immutable forge/repository identity,
canonical origin/ref, protocol/epoch, reachable genesis/minimum history pins, canonical current `main` authority branch, verified
append-only/no-delete/no-reset protection, drained bypassing writers and trusted clock contract. Missing configuration fails
closed, with no FileStore fallback or initialization CLI. This source change provisions or activates NONE of those conditions.

Critical state lives only on `refs/heads/steward/pr-write-coordination-v1`: one global merge/close slot, stable logical identity,
immutable full policy/producer/ratified-authority and independent-verifier/justification bindings, fence/attempt, counted sends
and truthful evidence. Sources must equal the designated CURRENT canonical Git commit and its authenticated API content; stale
checkout, local-head override, caller hash or local JSONL cannot settle or issue a send. All existing B/C, human approvals,
producer/content proofs, protection, live head/base/holds/checks and kills are rechecked at the last adapter boundary.

Merge is one synchronous PUT with REST `sha` and `merge_method: merge`; close is one PATCH containing only `state: closed`.
Closure is not atomically bound to the checked head/holds. There is no invented conditional-close block or exactly-once delivery
claim. Unknown/lost response never expires into another send. A matching absorbing merge can retire an unknown sender with
causation unknown; closed GET cannot prove a delayed PATCH dead after reopen. Authentic sole-invocation completion can retire
the sender even after a reopen; report the observed state and head-race flags truthfully.

Global accounting retains 2 merges/run, 2 closes/run and 10 critical attempts/hour. Rejected sends remain charged; only
canceled-unsent frees admission. Unknown charges never age out. Completed charges expire only when trustworthy current LOWER
time is strictly beyond completion UPPER + one hour. The concrete HTTPS clock requires a fresh echoed nonce, no-store/zero-age,
provisioned UTC skew/precision, bounded network delay and monotonic consistency; HTTP Date/host UTC alone is insufficient.
A real trustworthy endpoint remains a rollout gate, not an observed deployment fact.

Retained full records are bounded by 128 logical operations, finite event history and an 8 MiB production profile (a smaller
configured transport bound wins), with exact persisted-byte and outcome/generation headroom guards. The 512 KiB boundary-test
profile is explicit, not production capacity. No archive, pruning, compactor or unlimited-service claim; exhaustion refuses.
One unresolved sender can pin the slot indefinitely. Local kills cannot revoke another host's already claimed invocation.

Ordinary `full run|record|abandon|status --ledger git` (and `auto`) behave exactly as before: this change does not retire,
migrate, complete or settle the shared Steward ledger, and no local state stands in for it. Only the Routine 19 critical
writes use their own coordination ref, which never holds ordinary run state. Competing R19 writers are prevented by that
ref's slot, fence and CAS and by `gate.py`'s `legacy-route-disabled` refusal of local reservations, not by changing the
general run/record path.

## Execute outcomes, unknown outcomes and `uncertaintyCause`

`execute` exits 0 only for a settled `merged`, `closed`, `already-merged` or `aborted` report; every other outcome exits 2
(`takeover` exits 0 only when it re-owned the preparation). A raw coordination/ledger failure never escapes as a traceback: `gate-*`, `execute`,
`recover`, `finalize`, `abort` and `takeover` report `{"refused": "shared-route-unavailable", ...}` and exit 2. A freshly
entered invocation produces one of four shapes, depending on how far it got; the inspection, prepared and unresolved reports
listed after the table are separate and are never a send grant:

| Shape | When | Fields |
|---|---|---|
| Settled | The completion was authenticated and recorded (`merged`, `closed`, `failed` for a definite rejection, `already-merged`, `aborted`). | `operationId`, `state`, `coordinationState`, `repo`, `runId`, `number`, `headSha`, `action`, `evidenceSha256`, plus `observedState`/`mergeCommitSha`/flags when evidence exists, and `reason` for `failed`/`aborted`. |
| Store `unknown`, **no cause** | The adapter was entered, then failed or lost its response, and the `unknown` transition **committed**. | `operationId`, `state: unknown`, `coordinationState: unknown`, `repo`, `runId`, `number`, `headSha`, `action`, `evidenceSha256: null`. No `uncertaintyCause`. |
| `possibly-sent`, **with** `uncertaintyCause` | The adapter was entered, but the step after it (authentication, evidence validation, recording, re-reading) could not be completed. `possibly-sent` is a knowledge classification, never an observed store state. | `operationId`, `state: possibly-sent`, `coordinationState: unavailable`, `uncertaintyCause`, `evidenceSha256: null`, `repo`, `runId`, `number`, `headSha`, `action`, `reason`. |
| `canceled-after-claim` | The claim committed, then the adapter **proved** no request byte was sent (see below). Reported as `state: failed`, `coordinationState: canceled-after-claim`. | As Settled, with a fixed `reason`. Nothing was performed. |

Other reports `execute` and `takeover` can return, all produced without entering the adapter:

| Report | When | Notes |
|---|---|---|
| Inspection of a persisted sender | `execute` finds the operation already `possibly-sent`, `unknown`, `quarantined` or terminal (for example after a restart). | The raw store state is reported (`state` equals `coordinationState` for the unsettled ones) and there is **no** `uncertaintyCause`: the cause is only known to the process that entered the adapter. Terminal states use the Settled shape. |
| Prepared | `execute` could not commit a claim (unresolved acknowledgement), or `gate-*` returns the prepared operation. | `state: reserved`/`intent`; after an unresolved claim `commitStatus: unresolved` is added. Not a send grant and not success. |
| `takeover` | The preparation lease was re-owned, or not. | Success is only a `reserved`/`intent` report whose owner is the new owner under a newer fence, with exit 0. An unresolved acknowledgement adds `commitStatus: unresolved`; a transition that changed nothing adds `commitStatus: not-taken-over`; both exit 2. |

No raw exception, response, header or token text is ever published. Neither `unknown` nor `possibly-sent` grants a retry,
refund or replay.

| `uncertaintyCause` | What could not be completed after adapter entry |
|---|---|
| `transport` | The response was missing or opaque (for example a non-200 reply that neither proves an effect nor a definite rejection), so completion evidence was unavailable. |
| `completion-failed` | Completion authentication or independent outcome evidence failed validation (forged/replayed response, identity or merge-parent mismatch, or an evidence read failure). |
| `persistence` | The shared Git/CAS transition recording the unknown or completed outcome could not be committed or confirmed, or a ledger failure occurred after the claim committed. |
| `capacity` | The critical record had no remaining capacity to record the outcome transition. |
| `inspection` | The outcome may have been recorded, but the shared report could not be re-read afterwards. |

Handling is the same for every unsettled shape: do not resend, do not start a new run to clear the claim, and do not treat
the cause as proof the forge did or did not act. Reconcile with `recover --operation-id ID` (or `finalize --operation-id ID`),
which makes one bounded independent observation and never resends. An inconclusive observation quarantines the sender; it
never expires.

### Provably unsent claims (`canceled-after-claim`)

A claim used to pin the single global slot forever even when nothing could have been sent (a ledger read failing after the
claim, the live re-check refusing, or DNS/TCP/TLS failing before the first request byte). The claim result is now built from
the committed CAS itself, so no ledger read sits between claim and send. The adapter raises `NotSent` **only** when it can
prove no request byte was written: entry refused, the live re-check immediately before the send refused, an invalid route,
or the HTTPS connection (DNS, TCP, TLS handshake) failed before the request was written. The coordinator then records
`canceled-after-claim`: the slot is released, but the attempt, its run charge and its hour charge stay counted, the logical
operation stays spent (the same subject can never be resubmitted) and there is no refund or replay. Any failure after a
possible socket write, and any failure of the cancellation itself, stays `unknown`/`possibly-sent` exactly as before. A
post-connect exchange is also bounded in total by a 30 s watchdog that shuts down the retained connected socket, including
for `Connection: close` and HTTP/1.0 responses whose body outlives the connection object (connect is bounded separately by
the 20 s connect timeout and the system resolver, which the watchdog does not cover); an aborted exchange is never `NotSent`.

TLS trust is the system default store only. `SSL_CERT_FILE` and `SSL_CERT_DIR` overrides are refused at construction and at
request time, in the same way inherited `GIT_*` overrides are refused.

## Preparation lease, `takeover` and `abort`

A prepared operation (`reserved`/`intent`) holds the single slot under a 120 s lease measured on the trusted clock. A claim
requires the lease still live. An expired, unsent preparation can only be moved, not sent: `takeover --operation-id ID`
re-owns it under a newer fence (at most 3 times, and only after the lease expired); the previous token can no longer claim
(the CAS orders takeover against claim, so a race has one winner), and the new lease is another 120 s. A claimed, settled or
cancelled operation can never be taken over. `abort --operation-id ID --reason TEXT` cancels only unsent preparation and
records `operator abort: TEXT` (1-256 printable ASCII characters) in the shared cancel event.

Anti-replay consequence: cancelling a preparation (or `canceled-after-claim`) frees the slot but not the subject. The logical
identity (namespace, PR, head, base, action, producer, reason, replacement) is spent; the same subject cannot be reserved
again, even by a new run. A changed head or base is a new subject.

## Ceilings: a fresh run id cannot evade them

The per-run ceilings (2 merges, 2 closes) are also enforced per action over the trailing hour across **all** run
identifiers, so a new `runId` cannot reset them. Together with the 10 critical attempts/hour overall bound, an hour admits
at most 2 merges and 2 closes under the pinned ceilings, so the overall hour bound only binds first when limits are lowered.
A completed, rejected or `canceled-after-claim` attempt counts for one hour after its completion upper bound; unknown and
quarantined charges never age out. Only `canceled-unsent` is refunded.

## Epoch rotation runbook (administrator, audited; no agent performs it)

Use only when (a) the 128-operation anti-replay cap or the byte budget is exhausted (the coordinator refuses new
reservations rather than pruning), or (b) the single slot is genuinely wedged: an operation stays `possibly-sent`, `unknown`
or `quarantined` and independent forge truth shows `recover` can never settle it. Records are never pruned, edited, refunded
or retired by a timer. Nothing here is automated, no command in this repository performs it, and it has not been exercised.

1. Record the decision in a founder report under `founder/reports/`: old epoch, ref tip SHA, why, and for a wedged slot the
   independently verified forge truth of every outstanding operation (PR state, merge commit or its absence, timestamps).
2. Stop writers. Commit `prMaintenance.killSwitch: true` through a normal protected PR and run `kill on` on every host that
   ever ran the executor. A local kill cannot cancel another host's already-claimed sender, so confirm each host has no
   `execute` process before continuing.
3. Run `recover --operation-id ID` once per outstanding operation. If it settles (`observed-terminal`), that operation needs
   no rotation. Only continue for operations the forge evidence cannot settle.
4. Archive. Fetch the complete history of `refs/heads/steward/pr-write-coordination-v1`, store a bundle and its SHA-256 with
   the report. History is never deleted.
5. Rotate as the repository administrator who alone holds the protection exemption: rename the old ref on the server to
   `refs/heads/steward/archive/pr-write-coordination-v1-<first 8 of old epoch>` (rename, never delete or force-reset) and keep
   protection on it. Create the new single-parent genesis commit at the original ref name, whose document is the empty ledger
   with `operations.routine19CriticalWritesV1 = {schemaVersion: "steward-pr-writes-v1", namespace: {..., epoch: <fresh
   32 lowercase hex>}, events: []}` (the shape used by the `seed` fixture in
   `tests/steward/prmaintenance/coordination_helpers.py`). Re-apply and verify no-delete/no-reset protection on it.
6. Commit the new `writeCoordination.epoch`, `genesis` and `historyPin` in `POLICY.yaml` via a protected PR with independent
   review. `ref` stays the same name.
7. Accounting carry-over and old senders. A new epoch starts with zero charges and an EMPTY anti-replay set, and nothing in
   code carries the old subjects forward: listing them in the report does not enforce anything. Therefore:
   - An old operation still `possibly-sent`, `unknown` or `quarantined` is never retired by waiting, by an unchanged or
     negative forge observation, or by stopping local processes. No platform bound exists on an already accepted or queued
     GitHub PATCH/PUT, which is exactly why `recover` refuses to retire a close sender from an open/closed GET. Rotation with
     such an operation outstanding requires EITHER authentic completion or absorbing proof (a matching merge) retiring it
     first, OR a separately ratified founder risk decision that cites an actual server-side drain guarantee. Without one of
     these, rotation is not authorized and the slot stays held.
   - When every old operation is terminal (the cap-exhaustion case), wait at least one hour after the last old charge
     before re-enabling, because the new epoch forgets the hourly accounting. List the old subjects as spent in the report;
     the gate still re-proves live head, state and eligibility, but the coordinator will not block their resubmission.
8. Verify from a fresh clone: `makeExecutor(root).coordinator.inspect()` reports no operations and no active operation, the
   `tests/steward/prmaintenance` suite passes, then `kill off` through a protected PR.
9. Rollback: only before any new-epoch operation exists, revert the POLICY PR and rename the archive ref back. After the first
   new-epoch record, rolling back would discard anti-replay history and must not be done.

## Replacement bookkeeping verbs (local only)

`reconcile --number N --run-id RUN --worktree PATH` builds a tracked replacement locally. After the replacement branch is pushed
and its pull request opened, `reconcile-opened --number N --head SHA --replacement M --branch NAME --run-id RUN` records it.
`reconcile-refresh --number N --run-id RUN --worktree PATH` brings an open Steward-owned replacement up to a moved destination tip.
`reconcile-retired --number N --head SHA --replacement M --reason TEXT --run-id RUN` records a withdrawn replacement so a new
one may be built. None of these verbs merges, closes or writes shared critical state.

## Founder card

A held pull request's card carries a **procedural recommendation** (retain the hold) and the **substantive decision** (whether the
change should land, with Steward's explicit no-opinion), as two labelled paragraphs from `prmaintenance/advice.py`. The desk, the
digest and the GitHub receipt all render that module, so they cannot disagree.

## Known limits

The roster discovers its environment from process signals, so harness identifiers (for example `claude-code-remote`, `github-actions`) are *environment ids*, never model names; model names appear only in an operator's local, ignored profile. Receipts end with the repository's required Claude Code attribution footer. Authority files must be committed and equal the designated current canonical source. Local diagnostic outcome files are not critical-write authority. Report payloads must pass a strict structural safety proof (semantic version, relative or allow-listed URLs, no markup or script scheme) because the template renders some fields unescaped.

## Roster profiles

`python scripts/steward_pr.py roster …` manages environment-scoped profiles under `.gaia/steward/rosters/` (ignored state).
Selection is by capability, never by name; an undeclared capability is never chosen; an unavailable capability is a recorded
limitation; escalation needs a stated need; a verifier is never a builder. Profiles hold no credentials.

## Receipts

Pickup, Verification PASS, MERGED, CLOSED WITHOUT MERGE and Founder Decision Required. Each begins with
`<!-- gaia-steward:pr-receipt kind=… pr=N head=SHA12 run=ID -->`; that marker reduces duplicate publication, not critical-write correctness.
All receipt POSTs are best effort; independent verification and durable justification remain mandatory. Failed hold/comment READs
still refuse eligibility; failed publication never causes resend/refund or invalidates genuine verification.

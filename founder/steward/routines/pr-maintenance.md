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

Observation, census, profiles, dispatches and ordinary full-run state remain checkout-local. The unattended driver still refuses
PR writes. `gate-merge` / `gate-close` create shared preparation and an exact intent, not a send authorization. Only explicit
`execute --operation-id ID` enters the one-shot core. `recover` / `finalize --operation-id` reconcile without resend;
`abort --operation-id` cancels only unsent preparation. Unsafe legacy authorization JSON/local outcomes are not authority.

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

Ordinary `full --ledger auto/local` is local without an origin probe; explicit general `git` supports only read-only legacy
status. No historical canonical campaign run is migrated, completed or settled. Existing campaign operation and rollout
compatibility must be handled separately before adopting this source.

## Unknown outcomes and `uncertaintyCause`

`execute` exits 0 only for a settled `merged`, `closed`, `already-merged` or `aborted` report; every other outcome exits 2. When
the sole adapter was entered but its result cannot be settled in shared state, the report is a bounded classification, not a
settlement, and carries exactly these fields: `operationId`, `state` (always `possibly-sent`), `coordinationState`
(`unavailable`), `uncertaintyCause`, `evidenceSha256` (`null`), `repo`, `runId`, `number`, `headSha`, `action` and a fixed
`reason`. No raw exception, response, header or token text is ever published. `possibly-sent` here is a knowledge
classification, never an observed store state, and it never grants a retry, refund or replay.

| `uncertaintyCause` | What could not be completed after adapter entry |
|---|---|
| `transport` | The response was missing or opaque (for example a non-200 reply that neither proves an effect nor a definite rejection), so completion evidence was unavailable. |
| `completion-failed` | Completion authentication or independent outcome evidence failed validation (forged/replayed response, identity or merge-parent mismatch, or an evidence read failure). |
| `persistence` | The shared Git/CAS transition recording the unknown or completed outcome could not be committed or confirmed. |
| `capacity` | The critical record had no remaining capacity to record the outcome transition. |
| `inspection` | The outcome may have been recorded, but the shared report could not be re-read afterwards. |

Handling is the same for every cause: do not resend, do not start a new run to clear the claim, and do not treat the cause as
proof the forge did or did not act. Reconcile with `recover --operation-id ID` (or `finalize --operation-id ID`), which makes one
bounded independent observation and never resends. An inconclusive observation quarantines the sender; it never expires.

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

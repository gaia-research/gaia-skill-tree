---
name: gaia-steward-pr-maintenance
description: >-
  Maintain registered routine pull requests through independent verification,
  bounded shared preparation and an explicit one-shot executor. Use for routine
  19, weekly report PRs, or forge.merge_pr/forge.close_pr proposals. Never a
  general merge permission; missing deployment configuration refuses execution.
version: 1.0.0
---

# gaia-steward-pr-maintenance

Routine owners produce; Steward verifies and accounts for eligible work. Sensors
and ordinary orchestration remain checkout-local. A proposal is not a send grant.
The unattended driver still refuses Routine 19 writes.

## Authority and true stops

The decided `steward-pr-maintenance-authority` record, current full POLICY.yaml
and producer registry govern the route. Only `gaia-research/gaia-skill-tree` is
in scope; other repositories remain deferred/unknown. Class B does not override
Class C, founder holds, required human approvals, branch protection, independent
verification or kill switches. No direct protected-branch push, force merge,
squash, auto-merge, release or unrelated authority is granted.

Missing `prMaintenance.writeCoordination` is a hard execution stop. Do not invent
a repository ID, epoch, genesis/history pin, canonical source or clock contract.
Rollout separately verifies/provisions append-only/no-reset/no-delete history,
namespace identity, clock assumptions and retirement of bypassing writers. Source
acceptance is not operational activation. There is no initialization command.

## Observe and verify (local)

```bash
python scripts/steward_pr_census.py
python scripts/steward_pr.py observe
python scripts/steward_pr.py roster preflight --run-id RUN
```

An incomplete census means unknown coverage, never an empty/healthy queue.
Select the verifier by capability, excluding builders; record the dispatch with
`roster dispatch --subject REPO#N@FULL_HEAD`. Store its genuine PASS/FAIL and named
proofs with `verification --input FILE`. A verifier cannot be a builder; effort,
profile, exact head/base, recorded subject, policy revision and freshness matter.
Never manufacture a PASS, approval or dispatch. Profiles/dispatches stay local;
validated independent proof and closure justification are bound into shared state.

Only the registered reconciler may build a tracked replacement. Never rewrite
the producer branch. A replacement needs its own exact-head verification, and
closing its original requires a merged marker-linked replacement with preserved
payload. Age or conflict alone never justifies closure.

## Prepare, execute, reconcile

1. `gate-merge` or `gate-close` re-proves eligibility and records shared preparation
   plus the exact intent. It returns `operationId`, NOT a bearer authorization.
   Keep the stable run ID across resumes; a new run cannot clear an old claim.
2. Only after the existing authority/rollout gates are satisfied, explicit
   `execute --operation-id ID` enters the core once. Do not run an external
   `gh pr merge`, PATCH or copied authorization JSON outside this executor.
3. `recover --operation-id ID` (or `finalize --operation-id ID`) independently
   reconciles truth; it never resends. `abort --operation-id ID --reason TEXT`
   can cancel only unsent preparation. Caller success/failure, a local JSONL
   outcome, TTL, new run or action supersession cannot settle/refund a sender.
4. Record the executor's bounded outcome with `gaia steward full record`. Every
   success-shaped result, including already-*, requires the matching shared
   operation/head/evidence. Unknown/quarantined remains pending, not successful.

The executor obtains full committed authority bytes from the designated CURRENT
canonical Git `main` source and cross-checks the API ref/content with Git objects, not
an old checkout or `GAIA_STEWARD_PR_AUTHORITY_LOCAL`. It rechecks independent
proof, live head/base, producer content/scope, holds, approvals, required checks,
protection and kills immediately before the sole HTTP mutation. Read failures
refuse; do not interpret a failed hold/comment read as no holds.

Merge uses synchronous PUT with REST `sha` and `merge_method: merge`. Closure
permits one coordinated PATCH containing only `state: closed` after live checks;
GitHub does not atomically bind it to the checked head, base or holds. Ambiguous
completion blocks replay. No invented If-Match or exactly-once delivery claim.
A real completed close response can retire the sender after a later reopen;
report `observedState` and head/base-race flags honestly, not a still-closed assertion.

## Best-effort receipts

Pickup, verification, justification and final comments are best effort, never a
prerequisite or commit point. Render/check/record with the existing receipt CLI;
markers reduce duplicate publication, not critical-write correctness. A failed
POST must not resend, refund, invalidate genuine verification or invent success.
Final receipts use the observed merge commit and post-merge check summary; missing
or pending checks are not healthy. A post-merge diagnostic read failure does not
undo independently proved completion.
The founder receipt keeps procedural retain-hold advice separate from the
founder's substantive decision, using `prmaintenance/advice.py`.

## Coordination, accounting and limits

- One global active merge/close operation on the dedicated canonical Git ref.
  Preparation takeover requires a newer fence before claim; a persisted claim
  never grants a restarted/copied/forked actor another send.
- Actual ceilings remain 2 merges/run, 2 closes/run, 10 critical attempts/hour.
  Rejected sends count; known completion releases the slot without refund.
  Only canceled-unsent removes its charge; unknown charges
  never age out. Completed charges expire only after trustworthy current LOWER
  time exceeds completion UPPER time plus one hour.
- The concrete clock requires a provisioned HTTPS error/precision contract,
  fresh echoed nonce, no-store/zero-age, bounded network delay and consistent
  monotonic progression. HTTP Date or host UTC alone is not authority.
- Full records are retained without pruning. Production budget is at most 8 MiB
  (a smaller transport cap wins), 128 logical records, bounded event history and
  reserved outcome/generation headroom. Current complete proofs fit 128 records
  in the modeled profile, not unlimited service; capacity exhaustion refuses.
- An unresolved sender can pin the single slot indefinitely. `kill on`, the local
  environment switch and policy checks stop that actor before new invocation;
  local kills do not cancel another host's already-claimed sender.

Guide: `founder/steward/routines/pr-maintenance.md`. Implementation and tests:
`src/gaia_cli/steward/prmaintenance/`, `tests/steward/prmaintenance/`. No live
namespace or trustworthy clock has been provisioned by this source change.

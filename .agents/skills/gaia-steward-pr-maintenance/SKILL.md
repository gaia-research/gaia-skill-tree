---
name: gaia-steward-pr-maintenance
description: >-
  Take over registered routine pull requests (weekly content-engine reports,
  scheduled docs routines) as their final integration authority: pick up, verify
  independently, reconcile, merge through forge.merge_pr or close through
  forge.close_pr, and leave GitHub receipts. Use for "/gaia-steward-full --routine 19",
  "merge the weekly report PRs", "what routine PRs are waiting", or when a full
  Steward run emits a forge.merge_pr or forge.close_pr action. Never a general
  permission to merge: a registered producer must prove the pull request.
version: 1.0.0
---

# gaia-steward-pr-maintenance

Routine owners produce. Steward verifies, reconciles, merges, closes and accounts for the work.
This skill is the driver's contract for routine 19. The runner decides; you perform one forge call at a time.

## Authority, in one paragraph

Ratified route `founder/steward/decisions/steward-pr-maintenance-authority.json` plus `prMaintenance` in
`founder/steward/POLICY.yaml`. A pull request is routine only if `founder/steward/pr-producers.json` proves it. Authority
is Class B; a hold, draft, missing required approval, design gate or destructive closure is Class C. A stronger agent
never gains merge, closure or policy authority. Never push to a protected branch, force-merge, fabricate an approval,
bypass a required check, or squash. Scope is `gaia-research/gaia-skill-tree`; other repositories are deferred (unknown, not healthy).

## The lifecycle (every step is resumable and idempotent)

```bash
python scripts/steward_pr_census.py                       # 0 complete, 3 incomplete (sensor then reports unknown)
python scripts/steward_pr.py roster preflight --run-id RUN   # environment profile; refuses to guess or import another env
python scripts/steward_pr.py observe                      # dispositions + every gate, read only
```

| Disposition (debt kind) | Authority | You do |
|---|---|---|
| `routine_pr_merge_ready` | B | independent verification, then `forge.merge_pr` |
| `routine_pr_verification_failed`, `_conflict`, `_blocked` | B | reconcile when `reconcile` names a reconciler; else report |
| `routine_pr_superseded` | B | report; closure needs the replacement merged and the payload proven preserved |
| `routine_pr_closure_ready` | B | justification receipt, independent verification, then `forge.close_pr` |
| `routine_pr_provenance_unknown` | B | report only; never act on a PR whose producer is not proven |
| `routine_pr_founder_decision` | C | post the founder receipt; do not merge or close; the desk holds it |

1. **Pickup.** Check `receipt check --kind pickup`; if absent render with `receipt pickup`, post it as a PR comment, then
   `receipt record`. The hidden marker is the idempotency key, so a resumed run never posts twice.
2. **Reconcile (only when `reconcile` is set).** Never rewrite the producer's branch. Open a tracked replacement PR on a
   `steward/b/` branch from the destination tip: copy the producer's report files, regenerate shared indexes and `?v=` stamps with
   the repository's own generator, and put `<!-- gaia-steward:replaces repo=R pr=N -->` in the body. The replacement is a new
   PR with its own head and its own verification; the original stays open until the replacement is merged.
3. **Independent verification.** Select a verifier with `roster select --capability independent-review --exclude <builder>`
   and record the dispatch with `roster dispatch`. The verifier re-runs the gates, reads the diff, and answers PASS or FAIL
   with proofs. Store it with `verification --input FILE` (refused if the verifier built the work, or effort is not explicit).
   Escalate only for a stated unresolved need (`roster escalate`).
4. **Verification receipt**, only after a stored PASS. A head change invalidates it; verify again.
5. **Gate, then exactly one write.** `gate-merge` (or `gate-close`) re-proves everything from live GitHub and returns an
   authorization or a refusal code. Only on authorization make the forge call with `expectedHeadSha`. If the call is not made,
   `abort`. Then `finalize --auth FILE` records what GitHub *shows*; never report a merge GitHub does not show.
6. **Final receipt** (merged / closed) with the observed merge commit and the actual post-merge check summary. A pending
   check is "pending", never "healthy". A merge already recorded is reported, not repeated.

The gate refuses: kill switch, malformed or unratified policy, disabled action, deferred repository, prior or concurrent
execution, head moved, destination not allowed, producer not proven, branch protection unmet, no independent verification,
missing GitHub trail, exhausted run or hourly budget. Closure additionally needs the justification posted first and a merged,
marker-linked replacement with a byte-identical payload.

## Limits that hold for the whole route

- One merge or closure action in flight; per-run and hourly budgets are in policy and capped in code. A deferred item keeps its place and resumes next run.
- Model dispatch is separate and bounded by the lane (`maxInFlight`, `maxDispatchesPerRun`) and by the profile, whichever is lower.
- The roster profile lives in ignored local state, belongs to one environment, and holds no credentials. No model name appears in canon.
- Revoke instantly: `python scripts/steward_pr.py kill on` (or `GAIA_STEWARD_PR_KILL=1`, or `killSwitch: true`).

## Where the rest lives

Routine guide `founder/steward/routines/pr-maintenance.md`; sensor `src/gaia_cli/steward/prmaintenance/`; tests
`tests/steward/prmaintenance/`; coverage `founder/steward/routine-coverage.json` (routine 19).

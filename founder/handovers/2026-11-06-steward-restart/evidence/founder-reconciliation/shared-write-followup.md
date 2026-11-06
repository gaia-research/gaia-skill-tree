# Queued founder follow-up — Shared Steward Write Ledger

Authority: explicit user follow-up in this session, after shared-provider roster setup and four current lane resumes. Track under existing #2283; no duplicate tracking issue.

## Scheduling / source boundary

- Start ONLY AFTER current founder/watcher, security/mirror, CI-scope and archival repair lanes are completed through their required review/integration gates or truthfully handed off with explicit blockers. Do not interrupt or replace live writers, take their files, or launch a fifth concurrent worker.
- Incorporate main at user-specified `8ad344a4`, then inspect actual current main and Routine 19 code/contracts. Do not assume present integration checkout reflects the new checkout-local architecture or Routine 19 APIs.
- User explicitly requests rebase against current main for this follow-up. Apply that to the NEW isolated follow-up feature branch only, after preserving incorporated work. Do not rebase/reset/force-push existing lane branches, shared ledger refs or published independent work. Preserve both main's sensor work and current lanes and rerun affected regressions.

## Required architecture

Ordinary sensors, observations and noncritical operations retain CHECKOUT-LOCAL state. Introduce SHARED DURABLE write coordination only where cross-environment writes require it, beginning with Routine 19 `pr-maintenance` for authorized PR merges and closures.

- Cross-checkout/cross-environment locking; no machine-local file lock masquerading as shared coordination.
- Durable idempotency identities, atomic reservations, globally enforced write budgets and precise operation ownership.
- Safe recovery after process/host crash, interrupted/ambiguous GitHub responses and lost notifications; no duplicate/conflicting authorized writes or unbounded budget leakage.
- Preserve existing Class B/Class C authority, independent verifier separation, GitHub required checks/branch protections, live rereads and kill switches. Shared coordination is not new merge/closure authority.
- Do NOT enable issue-hygiene writes/closure authority, deferred curation, workflows or automatic release/main merges merely because infrastructure supports coordination.
- GitHub receipts/comments are BEST EFFORT for iteration one. Coordination correctness/reservations/outcome recovery cannot depend on receipt publication succeeding. Preserve local/shared proof as appropriate; report receipt failures truthfully without duplicating writes.
- Test races and crash/recovery across INDEPENDENT Git checkouts/object stores/processes, not merely threads or shared worktrees. Prove mutual exclusion, idempotency, global budget enforcement and retry/recovery safety with deterministic fault injection.

## Delivery

Inspect actual post-incorporation source before choosing storage/schema/API design. Delegate implementation using explicit `*-shared` agents on openai-codex; no imposed agent timeout/turn cap or Antigravity fallback. Independent `reviewer-shared` exact-SHA acceptance, real test results and a reviewable PR are required; no deployment/activation claim from code edits. User did not authorize interrupting ongoing campaign, deleting history or bypassing existing gates. Keep GitHub receipts best-effort; prioritized outcome is correct shared write coordination.

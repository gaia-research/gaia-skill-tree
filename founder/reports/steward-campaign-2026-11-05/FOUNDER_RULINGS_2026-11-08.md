# Founder rulings, 2026-11-08 (verbatim)

Received by the Steward lead (Opus, herdr w2H) in the #2283 session on 2026-11-08. Recorded verbatim below before any action was taken on them. Decision records: `founder/steward/decisions/steward-founder-authorization-2026-11-08.json`, `steward-verification-reverify-2283.json`, `steward-upstream-batch-activation-2283.json`, `steward-ledger-capacity-64mib-2283.json`, `steward-class-b-route-authority-2283.json`.

---

# Gaia Steward #2283: Founder Authorization Update

Opus, apply these rulings to the **existing Steward Full campaign**. This is a continuation, not a restart.

**Do not stop, cancel, replace, or redispatch running subagents.** Reconcile active work before assigning anything new.

## Mission and execution lanes

**Primary mission:** Eliminate genuine canonical Steward debt through bounded repairs, independent verification, protected-main delivery, and verified ledger reconciliation. Measure **resolved debt**, not completed PRs or agent activity.

**Lane 1, Steward:** Pi/Herdr, using the canonical openai / openai-codex roster and established escalation/reviewer paths. Owns debt dispatch, repairs, verification, and canonical resolutions.

**Lane 2, non-Steward engineering:** Pi **Flash leading engineering, terra reviewer.** Owns supporting infrastructure and repair-route development, not canonical Steward debt execution.

Lane 2 must not displace Lane 1 or assume Steward authority.

## Ruling 1: Verification escalations

**APPROVED** for six batch-4 escalations and the `batch.py` import case.

- Reverify the six repairs against an attributable, stable baseline.
- Distinguish patch-introduced debt from unrelated debt created by concurrent merges.
- Preserve global debt detection and all original attempts, verdicts, and receipts.
- Do not reject an otherwise valid repair solely because another agent changed unrelated files.
- For `scripts/upstream_watcher/batch.py`, independently verify whether removing `re` breaks a genuine module API or consumer contract. Retain it if compatibility requires it; otherwise permit the bounded repair.
- No blanket bypass of new-debt or compatibility checks.

## Ruling 2: Upstream batching activation

**APPROVED for controlled production activation without further founder approval.**

- Verify the `garrytan/gstack` 404 and reconcile any genuinely moved upstream reference.
- Complete the documented no-write journal bootstrap.
- Validate durable restoration, candidate preservation, and rollback.
- Enable `STEWARD_ISSUE_HYGIENE_V2`, `UPSTREAM_STAGING_INITIALIZED`, and `UPSTREAM_BATCH_STAGING=weekly` in the documented safe sequence.
- Monitor two weekly windows for issue noise, dropped candidates, urgent writes, and journal failures.
- Keep historical epic closure and provenance intact.

## Ruling 3: Ledger capacity

**APPROVED: Raise `GAIA_STEWARD_LEDGER_MAX_BYTES` to 67,108,864 (64 MiB).**

This is the current supported maximum, not an instruction to inflate the ledger.

- Apply consistently to every authorized shared-ledger reader/writer.
- Preserve Git/CAS, receipts, history, and fail-closed behavior.
- Monitor real read/write latency, CAS retries, and bytes per batch. Investigate measurable degradation rather than silently increasing limits.
- **Keep #2287 parked.** Flash may resolve its engineering risks separately, but no archival activation or merge without independent acceptance and existing gates.
- Never discard or compact unarchived history to maintain throughput.

## Ruling 4: Standing Class B repair-route authority

**APPROVED: Steward should proactively make Class B debt repairable.**

A missing dispatch route is a coverage gap requiring engineering, not a permanent reason to leave Class B debt untouched.

**Flash's non-Steward engineering lane** may sample real findings and design/implement missing routes. Each route requires:

- Narrow debt kind, paths, commands, stop conditions, and proof contract.
- Independent review, including negative tests rejecting out-of-envelope edits.
- Preservation of security boundaries, product behavior, and canonical policy.
- Normal protected-main delivery.

**Standing authorization:** Routine, demonstrably safe Class B routes may be activated after independent acceptance without requesting another founder ruling for each category.

Specific safeguards:

- **Swallowed exceptions:** Preserve error-handling semantics; prove safe diagnostics and focused behavioral tests.
- **Browser sinks:** Prove actual sink safety, not merely visual equivalence; validate headless behavior.
- **Code duplication:** Require behavior-preserving refactoring evidence.
- **Unsafe execution and ungated mutation:** No blanket write/security authority. Escalate anything changing execution trust boundaries, canonical mutation authority, or security policy.
- **Trust/registry changes:** Preserve existing governed CLI, Verifier, and founder gates.

The **Pi/Herdr Steward lane** consumes independently accepted routes using its canonical Luna roster. Flash does not replace or commandeer those agents.

Report a reconciled Class B inventory separating **unrouted**, **ineligible**, **proposal-only**, and **dispatch-ready**. Note that `trust_stamp_stale` is **Class C**, not Class B.

## Final operating instruction

Continue the existing burn-down and preserve all active batches. Record these founder rulings verbatim in the canonical decision files and checkpoint.

Maintain independent verification, protected-main merge commits, accountable receipts, Class C evidence requirements, and all existing kill switches.

Only return to the founder for genuine authority, trust, security, or product decisions. Report canonical debt deltas, verified deliveries, and exceptional blockers.

**Steward owns the burn. Flash builds the machinery. Neither lane stops the other.**

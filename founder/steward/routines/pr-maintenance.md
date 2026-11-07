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

## Unattended execution

The pilot's outcome store is a file in one checkout (`.gaia/steward/pr-maintenance`). Inside that checkout it gives exactly-once
reservation, the per-run caps and the hourly cap. It is **not** proof of cross-host exactly-once execution, and the write budgets
are **not** globally enforced: another checkout or host has its own store and its own budget, so the effective ceiling is writers
× cap. Every authorization records `coordination: "checkout-local"`. GitHub remains the backstop that holds across hosts (a merged
or closed PR cannot be merged or closed again; `expectedHeadSha` refuses a moved head; receipt markers stop most duplicate
comments, though a race can still post one twice). That limits damage; it is not a lock or a shared budget.

Production use requires both: `GAIA_STEWARD_PR_AUTHORITY_REF=origin/main` (never the local-head override), and **either** a single
controlled writer (one scheduled job, concurrency-limited to one run) **or** shared coordination (a lock and budget counter outside
any one checkout). Until then, describe the caps as per-checkout.

## Founder card

A held pull request's card carries a **procedural recommendation** (retain the hold) and the **substantive decision** (whether the
change should land, with Steward's explicit no-opinion), as two labelled paragraphs from `prmaintenance/advice.py`. The desk, the
digest and the GitHub receipt all render that module, so they cannot disagree.

## Known limits

The roster discovers its environment from process signals, so harness identifiers (for example `claude-code-remote`, `github-actions`) are *environment ids*, never model names; model names appear only in an operator's local, ignored profile. Receipts end with the repository's required Claude Code attribution footer. Authority files must be committed, and in production equal the destination tip (`GAIA_STEWARD_PR_AUTHORITY_REF`). The outcome store is per checkout. Report payloads must pass a strict structural safety proof (semantic version, relative or allow-listed URLs, no markup or script scheme) because the template renders some fields unescaped.

## Roster profiles

`python scripts/steward_pr.py roster …` manages environment-scoped profiles under `.gaia/steward/rosters/` (ignored state).
Selection is by capability, never by name; an undeclared capability is never chosen; an unavailable capability is a recorded
limitation; escalation needs a stated need; a verifier is never a builder. Profiles hold no credentials.

## Receipts

Pickup, Verification PASS, MERGED, CLOSED WITHOUT MERGE and Founder Decision Required. Each begins with
`<!-- gaia-steward:pr-receipt kind=… pr=N head=SHA12 run=ID -->`; that marker is the idempotency key.

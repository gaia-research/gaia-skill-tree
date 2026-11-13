---
name: cloud-custody
description: Shared contract for gaia-steward-full, -lane and -verify on ephemeral cloud agents (issue #2448).
---

# Ephemeral cloud-subagent evidence (daily runs)

The daily cloud job is an external scheduled task whose agents are destroyed when
they finish; it is not the GitHub Actions Class A pulse (`.github/workflows/steward.yml`).
**`steward/ledger` carries full-run state only. Checkout-local `.gaia/steward/`
receipts, diffs and proofs die with the container**, so cloud Class B work runs with
evidence custody on: `--evidence git` (or `GAIA_STEWARD_EVIDENCE=git`) on `gaia steward
full run|record`, and on standalone `dispatch`, `lane next` and `verify`. Custody
stores the original scan and dispatch receipts byte-for-byte (and the exact builder
prompt), the candidate diff, the validated `steward-proof-transcript-v1` and the
verification receipt on the append-only `steward/evidence` ref (fast-forward CAS, no
force, read back before success). Contract:
`founder/handovers/2026-11-13-issue-2448-cloud-evidence-custody.md`.

| Boundary | Command (Lead unless noted) | If it fails |
|---|---|---|
| Dispatch issued | automatic with `--evidence git`; or `gaia steward evidence publish-dispatch DEBT` | no prompt, no builder, run `blocked` |
| Builder accepts | builder runs `gaia steward evidence accept DEBT` first | builder stops |
| Patch + proof | `gaia steward evidence publish-build DEBT --diff D --proof P --summary S --model M --effort E` (automatic in `full record`) | outcome refused; step stays pending, record again after repair |
| Lost prompt / adoption | automatic: the ORIGINAL prompt is restored from custody | pending work shows `BLOCKED`; resume after repair; nothing is re-rendered |
| Verifier retrieves | different checkout: `gaia steward evidence verify DEBT` (automatic in `full run --verify`) | work deferred, never re-dispatched |
| Outcome recorded | automatic: the verdict receipt is published, bound to that exact build | deferred |
| Before READY / PR | `gaia steward evidence ready DEBT --pin-bundle ID --pin-commit SHA`; paste its ids and hashes in the PR | not READY |

A verdict is bound to the build it judged: its debt, dispatch, diff hash and proof
hash must match that build's bytes, at publication, at every retrieval and in `ready`.
`--pin-bundle` / `--pin-commit` check the chain against identifiers recorded somewhere
the ref's writers do not control (the ledger work item, or the Lead's PR handoff);
`--pin-commit` also detects rewritten history. Writer, model, effort and summary are
part of each bundle's identity. `ready` never claims the ref is protected: that is
repository configuration, verified only by `scripts/check_steward_evidence_protection.py`.

Non-negotiable: never re-dispatch, re-render or write a receipt to recreate lost
authority; a missing or altered original means `BLOCKED: provenance unavailable`
(exit 4), reported verbatim, with no silent local fallback and no founder item
disguised as success. A mechanical verdict stays `pending`: the independent
verifier still decides, and a recorded founder disposition of one candidate (e.g.
#2445) is not a pass of `gaia steward verify` and authorizes no future bypass.
Without `--evidence git`, `full run --verify` refuses to re-dispatch when the
original receipt is missing.

Recover by repairing the remote or push permission, then re-running the same
command: publishing is idempotent and resumed runs never duplicate a dispatch.
Stop by abandoning the run (`gaia steward full abandon RUN --reason WHY`); nothing is deleted.

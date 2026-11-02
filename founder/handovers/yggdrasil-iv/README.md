# Yggdrasil IV — campaign handovers and receipts

Working documents for the Yggdrasil IV campaign (RFC #2148, aggregate draft PR #2151,
integration branch `dev/yggdrasil-iv`). They were moved out of `founder/` root so that
root keeps only durable, governing material; superseded checkpoints stay here as
history rather than cluttering the top level.

## Start here

| Order | Document | Role |
|---|---|---|
| 0 | [`../../reports/yggdrasil-iv-october-2026/HANDOVER.md`](../../reports/yggdrasil-iv-october-2026/HANDOVER.md) | **Current entry point (EPIC #2189 launch campaign, paused 2026-10-28 on weekly quota).** Ordered next steps, founder decisions, state. |
| 1 | [`YGGDRASIL_IV_HANDOVER_2026-10-28.md`](YGGDRASIL_IV_HANDOVER_2026-10-28.md) | **Current entry point.** 2026-10-28 resume: integration state, landed PRs, open lanes, decisions pending. |
| 1b | [`YGGDRASIL_IV_HANDOVER_2026-10-27.md`](YGGDRASIL_IV_HANDOVER_2026-10-27.md) | Binding mission (§1), doctrine (§2) and held gates (§4). Roster-agnostic resume brief: original scope, binding doctrine, verified lane SHAs, open review defects, held human gates, evidence map, ordered next steps. |
| 2 | [`YGGDRASIL_IV_RESTART_CHECKPOINT_2026-10-27.md`](YGGDRASIL_IV_RESTART_CHECKPOINT_2026-10-27.md) | Live checkpoint/ledger. Its topmost section is authoritative over every older section below it. |
| 3 | [`../YGGDRASIL_IV_EXECUTION.md`](../../YGGDRASIL_IV_EXECUTION.md) | Campaign charter and engineering execution receipt (kept in `founder/` root). |
| 4 | [`../YGGDRASIL_IV_RATIFICATION_2026-10-25.md`](../../YGGDRASIL_IV_RATIFICATION_2026-10-25.md) | Governing ratification / authority (kept in `founder/` root). |

Founder rulings that bind this campaign remain in `founder/` root:
[`GAIA_FRONTIER_RULING_2026-10-26.md`](../../GAIA_FRONTIER_RULING_2026-10-26.md)
(Frontier discovers; Meta evaluates; Steward maintains; Governance decides).

## Chronology (oldest first)

| Document | State |
|---|---|
| [`YGGDRASIL_IV_PAUSED.md`](YGGDRASIL_IV_PAUSED.md) | Historical — first pause capture: source states, remaining gates, resume order, early progress estimate. |
| [`YGGDRASIL_IV_RECOVERY.md`](YGGDRASIL_IV_RECOVERY.md) | Historical — recovery source of truth during the first interruption: saved feature SHAs, review blockers, retry instructions. |
| [`YGGDRASIL_IV_ORCHESTRATION_PAUSED.md`](YGGDRASIL_IV_ORCHESTRATION_PAUSED.md) | Historical — "keep workers working, reach a resumable state" checkpoint. |
| [`YGGDRASIL_IV_RESUMED_2026-10-26.md`](YGGDRASIL_IV_RESUMED_2026-10-26.md) | Historical — explicit founder resume authorization (not inferred from a delayed notification). |
| [`YGGDRASIL_IV_CRASH_RECOVERY_2026-10-26.md`](YGGDRASIL_IV_CRASH_RECOVERY_2026-10-26.md) | Historical — post-crash recovery receipt. |
| [`YGGDRASIL_IV_DELIVERY_REVIEW_2026-10-26.md`](YGGDRASIL_IV_DELIVERY_REVIEW_2026-10-26.md) | Historical — three recovered deliveries saved but not accepted. |
| [`YGGDRASIL_IV_RESTART_CHECKPOINT_2026-10-27.md`](YGGDRASIL_IV_RESTART_CHECKPOINT_2026-10-27.md) | **Live** — pause/resume control, collected outcomes, owners, gates. Newest section wins. |
| [`YGGDRASIL_IV_HANDOVER_2026-10-27.md`](YGGDRASIL_IV_HANDOVER_2026-10-27.md) | **Live (doctrine)** — graceful-pause handover; mission/doctrine/gates still binding. |
| [`YGGDRASIL_IV_HANDOVER_2026-10-28.md`](YGGDRASIL_IV_HANDOVER_2026-10-28.md) | **Live (control)** — resumed session: four PRs landed, open lanes, pending founder decisions. |

Supersession rule: each newer checkpoint/handover supersedes the control statements of
the ones above it. Historical documents stay intact as evidence; do not rewrite them to
match current state.

## Where the evidence lives

**Committed proof set:** [`founder/reports/yggdrasil-iv-evidence/`](../../reports/yggdrasil-iv-evidence/README.md) —
byte-identical copies of the campaign's verification evidence (`SHA256SUMS`-manifested)
with an explicit scope note per directory. Read evidence there first; it survives session
archives and device loss.

Working copies, large archives, full session transcripts and WIP patches are **not**
committed — `.gaia/` is gitignored. They live under `.gaia/yggdrasil-iv/recovery/` in the
working copy and are indexed in the handover's evidence map (§6), together with the
pushed `recovery/yggdrasil-iv-*` Git refs that preserve uncommitted work. The four
~94 MB declared-artifact archives stay local only, with recorded digests.

## Conventions for new entries

- One dated file per pause/resume/recovery event; keep existing basenames when moving so
  external PR/issue citations keep resolving.
- Put the newest authoritative statement at the top of the live checkpoint, above a
  clearly labelled historical section.
- Record collected outcomes and exact SHAs, never launch status or intent.
- State held human gates explicitly; engineering progress never implies them.

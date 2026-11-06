# Routine — Trust calibration drift

| **Policy rule** | `trust-calibration-drift` |
| **Debt kind** | `trust_calibration_drift` |
| **Authority** | **B** — report and propose only; a Verifier must run the calibration |

## Purpose

Detect named skills whose stored star level no longer matches the computed G7
Trust Magnitude grade. End-of-day calibration is intentionally allowed to be
slow, but stale ranks should become visible maintenance debt rather than remain
silent until a manual leaderboard review.

## Contract

The sensor is read-only. It reports the skill ID, current level, computed TM and
grade, target level, and the exact `gaia dev calibrate` command. Steward must not
execute that command or edit `registry/named/`. Skills with an explicit `timeline.action:
upstream_deprecated` event are frozen and exempt: their historical rank is not
actionable debt. `installable: false` alone is not a freeze marker.

A human Verifier reviews the packet, confirms any evidence or Star Bar gates, and
runs the proposed command. After calibration, rerun the Steward scan; the debt
should reconcile as healthy.

## Evidence gaps are not demotions (founder rulings 2026-10-28 and 2026-11-06, #2201)

Missing evidence is not evidence of degradation. When the effective evidence pool
(own rows plus rows inherited from the generic parent) is empty, or holds only
rows that score nothing, a computed `ungraded` grade describes an absence of
evidence, not a measurement of low trust. For a would-be demotion the sensor then
reports a **`trust_evidence_gap`** (its own Class C kind, see
`trust-evidence-gap.md`) instead of a calibration target:

- `observedState.evidenceGap: true`, with `evidenceBasis`
  (`no-effective-evidence-rows` or `no-scoring-evidence-rows`),
  `effectiveRowCount`, `scoringRowCount: 0` and `preservedLevel`;
- no `targetLevel` and no `calibrationCommand`: no demotion is proposed;
- Class C, so it is never dispatched to the agent lane. The interim
  `laneEligible: false` marker on `trust_calibration_drift` is retired.

Explicit counter-evidence (a deranked verifier attestation) is not a gap and still
reports a `trust_calibration_drift` demotion target. A measured low grade (rows that
do score) also still reports one. The stored level is preserved until evidence is
discovered and recalculated through canonical Trust Magnitude semantics, or a
governed decision (#2148) rules otherwise. Discovery is the bounded read-only
routine in `trust-evidence-gap.md`.

## Stale stamps: event-driven restamp, periodic backstop (founder ruling 2026-11-06, #1642, option 8A)

`trust_stamp_stale` reports a stored `trustMagnitude` stamp that no longer matches
the engine. Each finding carries `recomputationOnly`: true when the computed grade
still agrees with the stored star level.

- **Event-driven.** `gaia dev evidence` and `gaia dev rm-evidence` measure computed
  Trust Magnitude before and after the write and restamp only the skills it
  moved (plus the skill written directly), inside the same invocation and PR. The
  refresh is the existing `gaia dev calibrate-trust-magnitude` verb with
  `--recomputation-only`, which writes the three derived stamp fields and one
  `recalibrate_trust_magnitude` timeline event, and never a star level. A skill
  whose computed grade disagrees with its level is **held**: its stamp stays stale
  and the finding stays Class C. Frozen skills are never touched. The refresh is
  re-read from disk and verified; `--no-restamp` opts out.
- **Periodic backstop.** This sensor re-measures every scan. A Verifier clears
  anything that escaped the trigger with
  `gaia dev calibrate-trust-magnitude --all --recomputation-only` in a reviewed PR.
- **Governed.** Any real trust, rank or evidence-policy change keeps its governed
  authority and stays Class C.

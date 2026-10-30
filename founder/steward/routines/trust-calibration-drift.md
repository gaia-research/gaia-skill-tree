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

## Evidence gaps are not demotions (founder ruling 2026-10-28, #2201)

Missing evidence is not evidence of degradation. When the effective evidence pool
(own rows plus rows inherited from the generic parent) is empty, or holds only
rows that score nothing, a computed `ungraded` grade describes an absence of
evidence, not a measurement of low trust. For a would-be demotion the sensor then
reports an **evidence gap** instead of a calibration target:

- `observedState.evidenceGap: true`, with `evidenceBasis`
  (`no-effective-evidence-rows` or `no-scoring-evidence-rows`),
  `effectiveRowCount`, `scoringRowCount: 0` and `preservedLevel`;
- no `targetLevel` and no `calibrationCommand`: no demotion is proposed;
- `laneEligible: false`: the debt stays open and visible but is never dispatched,
  because the only honest outcomes are evidence discovery or a governed decision.

Explicit counter-evidence (a deranked verifier attestation) is not a gap and still
reports a demotion target. A measured low grade (rows that do score) also still
reports one. The stored level is preserved until evidence is discovered and
recalculated through canonical Trust Magnitude semantics, or a governed decision
(#2148) rules otherwise.

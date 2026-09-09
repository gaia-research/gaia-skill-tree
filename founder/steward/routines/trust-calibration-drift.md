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
execute that command or edit `registry/named/`. Skills frozen with
`installable: false` are exempt: their historical rank is not actionable debt.

A human Verifier reviews the packet, confirms any evidence or Star Bar gates, and
runs the proposed command. After calibration, rerun the Steward scan; the debt
should reconcile as healthy.

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

`trust_stamp_stale` reports a stamp that no longer matches the engine: a stored
`trustMagnitude` beyond the 0.02 tolerance, a stored `overallTrustGrade` that
differs from the computed grade, or a `trustMagnitudeInputHash` that no longer
matches (`observedState.staleFields` names which), so grade-only and hash-only
staleness is caught even when TM did not move. Each finding carries
`recomputationOnly`, true only when the computed grade agrees with the stored star
level **and** the stamp already stores that exact grade, and `holdReasons`, which
names every reason a refresh is held: `level-disagrees-with-computed-grade`,
`stored-grade-differs-from-computed-grade` (a refresh would rewrite the grade) and
`stored-grade-missing` (a partial stamp: a refresh would introduce a grade). A
finding carries a `restampCommand` only when it is safe, and that command always
includes `--recomputation-only`; a governed finding gets no write command. Only the
stamp fields a record carries are judged, and TM staleness uses the 0.02
rounding-noise tolerance (the restamp verifier is stricter, 0.005), so a stamp off by
rounding alone is not debt.

- **Event-driven.** `gaia dev evidence` and `gaia dev rm-evidence` measure computed
  Trust Magnitude before and after the write and restamp only the skills it
  moved (plus the skill written directly), inside the same invocation and PR. The
  refresh calls the handler of the existing `gaia dev calibrate-trust-magnitude`
  verb with `--recomputation-only`. Authorization and the canonical transaction lock
  are enforced on the function that actually writes (`_calibrateTrustMagnitudeLocked`,
  guarded by `_guardedWriter`) and again at the restamp body
  (`src/gaia_cli/trustRestamp.py`), both re-entrant under the CLI dispatcher, so no
  direct call can write the registry unauthorized or outside the transaction; the verb
  keeps its preflights (frozen, unknown skill). The verb
  writes the three derived stamp fields and one `recalibrate_trust_magnitude`
  timeline event, and never a star level. Affected skills are found by a
  before/after fingerprint of TM, computed grade and own-input hash. A skill is
  **held** (stamp stays stale, finding stays Class C) for any hold reason above,
  including a partial stamp with no grade. A named skill whose fingerprint cannot be
  computed before or after the write is held and reported (never silently skipped),
  and `gaia dev evidence` / `rm-evidence` **preflight** the whole dependent restamp
  before mutating anything: every named skill must be fingerprintable and Origin
  standings and frozen locks must be derivable, otherwise the command is refused with
  nothing written and a message pointing at `--no-restamp` (which writes the evidence
  without refreshing stamps; the sensor then flags them). A failure that can still
  happen after the write (a post-write verification failure, an unauthorized restamp)
  exits nonzero with "Evidence written; stamps not refreshed (sensor backstop will
  flag)", says not to re-add the evidence, and names the recovery
  (`gaia dev calibrate-trust-magnitude --all --recomputation-only`). There is no
  rollback: the evidence is on disk and the stale stamps stay visible to the backstop.
  Frozen skills are never touched. Afterwards the registry is re-read from disk and every
  intended target must carry all three stamp fields, matching, while every level,
  computed grade, frozen state, Origin standing and non-target record is unchanged;
  `--no-restamp` opts out.
- **Periodic backstop.** This sensor re-measures every scan. A Verifier clears
  anything that escaped the trigger with
  `gaia dev calibrate-trust-magnitude --all --recomputation-only` in a reviewed PR.
- **Governed.** Any real trust, rank or evidence-policy change keeps its governed
  authority and stays Class C.

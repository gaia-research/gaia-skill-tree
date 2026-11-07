# Routine — Trust calibration drift

| **Policy rule** | `trust-calibration-drift` |
| **Debt kind** | `trust_calibration_drift` |
| **Authority** | **B**, executable for below-ceiling promotions (founder ruling F1, 2026-11-08); everything else is proposal-only |
| **Decision** | `steward-class-b-route-trust-calibration-2283` |

## Purpose

Detect named skills whose stored star level differs from the level their
recomputed Trust Magnitude grade allows, and, for a promotion, perform the one
governed calibration that closes the gap.

Founder ruling F1 (verbatim note): "Normally once a skill gets in the tree, this
is now debt. A steward run will be canon if it detects below ceiling, and should
calibrate automatically. Other ways to do this is through me, the verifier, or
through a full monthly meta audit/closeout. So yes, it is technically a ceiling,
but steward is now allowed to do this fully."

## What a packet may carry (enforced in code, `calibrationroute.py`)

The sensor marks every finding the route may never carry `laneEligible: false`
with a `laneIneligibleReason`. Routing refuses such a packet (lane or explicit
`--debt`) and verification re-derives eligibility live. The finding stays open
and visible either way. A packet is **one skill, one promotion to its grade
target**, and never:

- **a demotion** (`direction: ceiling-exceeded`). F1 covers promotions only; the
  stored level above the ceiling is already clamped on display, and lowering it
  keeps its governed authority (Yggdrasil IV).
- **a frozen skill** (canonical `gaia_cli.frozen`), nor one the sensor treats as frozen.
- **a skill whose last rank event is a recorded demotion** (`priorGovernedDemotion`).
  Founder ruling F3 (verbatim note): "As LONG as evidence points correctly and
  gives the correct trust magnitude, proposals are valid. The reason for demotion
  should be checked since usually it just means that there is no evidence." These
  stay **proposals for the curator**: the finding carries the demotion timestamp
  and reason, and `laneIneligibleReason` repeats them.
- **a cap-only suite component to 3★ or higher** (`capOnlySuiteComponent`, F2:
  "There should be no auto-3star for a suite candidate"). With the 49.9 cap
  (#2378) such a component grades C anyway; the guard holds either way.
- **a calibration a canonical preflight refuses or cannot evaluate**
  (`commandWouldBeRefused` must be exactly `false`).

## The builder's job

1. Reproduce the finding on the current head: stored level, recomputed TM, grade, target.
2. Run exactly one `gaia dev calibrate <skill_id> <target_level> --no-build`.
   A non-zero exit is a refused preflight: stop, report `no_change`, never retry
   another way. Never edit the record by hand.
3. Return the diff the verb wrote: the subject's `registry/named/<id>.md` only,
   with the appended `rank_up` timeline event. `--no-build` is mandatory: a
   packet never regenerates or commits Class S artifacts.

## Mechanical verification

`verification.calibration_structure_violations` rejects unless all of these hold:

- the diff touches exactly `registry/named/<subject id>.md`, modified (not created or deleted);
- parsed frontmatter changes only `level` (packet stored level → packet target),
  `updatedAt`, and `timeline` (the base timeline plus exactly one appended
  `rank_up` event whose details are the verb's own `Calibrated level from X to Y`);
  the body is byte-identical;
- the finding was eligible when dispatched, and is still eligible when re-derived
  live at the baseline: the verifier recomputes TM and grade, the target matches
  the packet, and the canonical preflights pass.

No other skill can change, because no other path may be in the diff.

## Class S artifacts: once per wave, by the lead

Builders commit only the verb-written registry record. Parallel per-skill PRs
therefore never touch the same file and never conflict on generated output.
The deterministic Class S set (`docs/graph/*`, `docs/api/v1/**`,
`docs/graph/ledger/data.json`, profile pages, `docs/tree.md`, `README.md` stat blocks
and the rest of the list in `CLAUDE.md` § Curation PR) is regenerated **once per
integrated wave** by the lead:

1. After the wave's calibration PRs are integrated into the integration branch,
   run `gaia dev docs` on its tip.
2. Commit only the deterministic set (`CLAUDE.md` § "which artifacts to commit")
   as one commit, `regen(steward): Class S after calibration wave <run id>`.
3. `python scripts/build_docs.py --check` must exit 0 before the integration
   branch is proposed to `main`.

The integration branch may be red between a wave's merges and its regeneration;
that is expected (`CLAUDE.md` § Multi-PR work). Guard E holds on the
integration → `main` delivery, which carries both the records and the regenerated
artifacts. A per-skill PR that touches `docs/**` is rejected (forbidden path).

## Annotations for the reviewing Verifier (#2283 S8)

Each `trust_calibration_drift` finding also carries, without changing what is
reported:

- `direction`: `promotion-candidate` (stored level below the grade ceiling) or
  `ceiling-exceeded` (above it; the displayed level is already clamped). Whether a
  level below the ceiling is debt at all is an open founder question (F1); the
  sensor does not decide it.
- `gatesUnmet` and `commandWouldBeRefused`: what the canonical `gaia dev calibrate`
  preflights (frozen, Star Bar blob link, status, star gate) would refuse for the
  proposed command, from the predicates themselves.
- `priorGovernedDemotion`: the latest rank event when it is a recorded `demote`.
- `frozen`: the canonical `gaia_cli.frozen` verdict. The drift skip rule itself is
  unchanged (only `upstream_deprecated` exempts), so nothing leaves the census.

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

# Yggdrasil III — bounded meta-audit and evidence packet

Status: implementation evidence attached; governing **MERGE / RECALIBRATE** decision pending.

Scope: `dev/yggdrasil-iii-newmeta`, after a fast-forward merge of `origin/main` and before any merge of this implementation stack into the integration branch's delivery line. This packet covers the false-positive suite-inflation fix only. It does not regrade the corpus or recalibrate component inheritance.

## Rule under test

- Fusion retains the graded-origin formula and `1.5×` weight, with a final contribution ceiling of **200 TM** after weighting and applicable multipliers.
- S requires TM ≥ 250, at least three distinct evidence types, and one positive eligible independent witness from exactly `benchmark-result`, `verifier-attestation`, or `peer-review`.
- Anti-auto-mint, same-source deduplication, benchmark eligibility, verifier derank exclusion, freshness, and zero-score handling run before a row can witness S.
- The existing mothership discount remains unchanged: `github-stars-own` uses `min(200, stars / 1000) / min(skillCountInRepo, 4)`.

## Bounded score evidence

The canonical backend scorer reports the following isolated fusion contributions:

| Graded origins | Fusion contribution |
|---:|---:|
| 5 | 150.0 TM |
| 6 | 180.0 TM |
| 7 | 200.0 TM |
| 10 | 200.0 TM |
| 46 | 200.0 TM |
| 1000 | 200.0 TM |

The raw formula remains visible for reporting; the aggregate contribution plateaus at 200 TM.

## S-gate evidence

Each case below uses the same fusion + `repo-own` + `github-stars-own` base (TM 286.0, grade A without a witness):

| Case | TM | Grade | Result |
|---|---:|:---:|---|
| Positive `benchmark-result` (`humaneval@v1.0`, CI-reproduced, percentile 90) | 426.0 | S | Accepted |
| Positive `verifier-attestation` (1 active verifier) | 331.0 | S | Accepted |
| Positive `peer-review` (1 reviewer) | 316.0 | S | Accepted |
| Fusion + `repo-own` + `github-stars-own` only | 286.0 | A | Rejected as S |
| Rejected benchmark row | 286.0 | A | Rejected as witness |
| Deranked verifier row | 286.0 | A | Rejected as witness |
| Zero verifier row | 286.0 | A | Rejected as witness |
| Zero peer-review row | 286.0 | A | Rejected as witness |
| Stale zero-scoring peer-review row | 286.0 | A | Rejected as witness |
| Phantom peer-review row | 286.0 | A | Rejected as witness |

## Integrity checks

- Backend, promotion, UI, and TM-calibration regression tests: **213 passed**.
- JavaScript syntax checks: all four changed TM/UI scripts pass `node --check`.
- Canonical and bundled schemas: JSON parse and byte-identical mirror checks pass.
- Targeted `docs/api/v1/evidence-types.json` projection matches regeneration.
- `git diff --check` passes.
- No corpus regrade was run.
- No generated registry, profile, or leaderboard artifacts changed. The only generated artifact in scope is the targeted evidence-types API projection.
- Mothership discount constants were not changed.

## Decision gate

Record exactly one decision on the governing stacked PR after review:

- **MERGE** — merge the implementation stack into `dev/yggdrasil-iii-newmeta`, then prepare the full Yggdrasil III post and retarget intake PR #1608 (`review/meta/intake-1607`) into this `dev/*` branch.
- **RECALIBRATE** — keep the stack open, adjust only the disputed rule, and repeat this bounded evidence check. Do not begin corpus or component-inheritance calibration in this pass.

The explicit decision is intentionally not pre-filled by the implementation agent.

# Steward decision ledger — founder rulings of 2026-10-21

The desk reads only `*.json` here, and a record is `open` or `decided`. This file holds the finer lifecycle.
States: **approved** (founder ruled) · **implemented** (change exists on a branch or PR) · **verified** (independently checked) · **landed** (merged to main) · **awaiting founder review**.
Nothing below is marked landed: no PR in this table is merged.

| # | Decision | Approved | Implemented | Verified | Landed | Record status |
|---|---|---|---|---|---|---|
| 1 | Landing target | yes | PR #2121: landing job on by default, branch `dev/steward-integration` created | unit tests only; no live GitHub run yet | no | decided |
| 2 | Trust-stamp refresh (#1642) | yes, with review | PR #2122 (22 stamps, stacked on #2121) | independent verifier pending | no | open (awaiting founder review) |
| 3 | `unused_import` Class B route | yes | PR #2121 | unit tests and coverage check pass; no live dispatch yet | no | decided |
| 4 | Lane `maxInFlight` 2 | yes | PR #2121 | unit and scenario tests pass; no live concurrency run yet | no | decided |
| 5 | Gate `provenance` and `evidence-seed` | yes | PR #2121 | `ungated_mutation` findings 4 to 2 on live scan | no | decided |
| 6 | Timeline causality (#1699) | yes, for investigation and preparation only | not executed: needs the new `timeline-resort` verb first | pending | no | open (awaiting founder review) |

Decision 6 is conditional by the founder's ruling: re-sort only if factually justified, with identities, timestamps, content and meaning unchanged, and never merged automatically.

# Steward decision ledger — founder rulings of 2026-10-21 and 2026-10-28

The desk reads only `*.json` here, and a record is `open` or `decided`. This file holds the finer lifecycle.
States: **approved** (founder ruled) · **implemented** (change exists on a branch or PR) · **verified** (independently checked) · **landed** (merged to main) · **awaiting founder review**.
Nothing below is marked landed: no PR in this table is merged.

| # | Decision | Approved | Implemented | Verified | Landed | Record status |
|---|---|---|---|---|---|---|
| 1 | Landing target | yes | PR #2121: landing job on by default, branch `dev/steward-integration` created | unit tests only; no live GitHub run yet | no | decided |
| 2 | Trust-stamp refresh (#1642) | yes, with review | PR #2122 (22 stamps, stacked on #2121) | independent Sonnet verifier: items pass after one fix (noise file reverted); fixed head not re-verified | no | open (awaiting founder review) |
| 3 | `unused_import` Class B route | yes | PR #2121 | unit tests and coverage check pass; no live dispatch yet | no | decided |
| 4 | Lane `maxInFlight` 2 | yes | PR #2121 | unit and scenario tests pass; no live concurrency run yet | no | decided |
| 5 | Gate `provenance` and `evidence-seed` | yes | PR #2121 | `ungated_mutation` findings 4 to 2 on live scan | no | decided |
| 6 | Timeline causality (#1699) | yes, for investigation and preparation only | PR #2123 (verb in #2121; 3 timelines re-sorted, stacked on #2121) | independent Sonnet verifier: PASS (one noise file reverted afterwards); open content issue on workflow-skill-creator | no | open (awaiting founder review) |
| 7 | Agent-agnostic one-click execution via gh-aw | yes (founder directive 2026-10-21) | PR #2121: `steward-full.yml`, 8 compiled gh-aw agent workflows, `steward_agent_dispatch.py` | unit tests and local `gh aw compile` only; no agent has run on GitHub yet | no | decided |

Decision 6 is conditional by the founder's ruling: re-sort only if factually justified, with identities, timestamps, content and meaning unchanged, and never merged automatically.

## Rulings of 2026-10-28 (weekly integration `integration/steward-weekly-2026-10-28`)

Nothing below is landed: it all sits on the draft weekly PR. "Verified" names the independent check; a ruling whose implementation is partial says so.

| # | Decision | Approved | Implemented | Verified | Landed | Record status |
|---|---|---|---|---|---|---|
| 8 | Trust-stamp refresh (#1642): event-driven recalculation with periodic reconciliation as backup; recomputing derived data is not a governed trust change | yes (founder, 2026-10-28) | partial: stale stamps now say `recomputationOnly` and carry the restamp command; the event hook is not built (needs a Verifier-gated CLI change and a policy amendment) | independent Sonnet verifier, see PR | no | open: ruling made, implementation approval pending (`steward-trust-stamp-refresh-policy-1642`) |
| 9 | Evidence before demotion (#2201): an empty effective pool is never grounds for demotion | yes (founder, 2026-10-28) | partial: sensor reports an evidence gap, no demotion target, out of the lane; closes answered escalations; discovery routine not built | independent Sonnet verifier, see PR | no | decided (`steward-evidence-before-demotion-2201`) |
| 10 | workflow-skill-creator awakened at 4-star after #1699 closed (`steward-workflow-skill-creator-demote-1699`) | no | none (canonical data; Steward may not touch it) | n/a | n/a | open |
| 11 | Dedicated `trust_evidence_gap` Class C kind and discovery routine | no | none (needs policy entries) | n/a | n/a | open (`steward-trust-evidence-gap-kind`) |
| 12 | Class B route for workflow timeouts | no | none | n/a | n/a | open (`steward-workflow-timeout-route`) |
| 13 | Wire the browser-render collector into the scheduled workflow | no | collector and sensor exist; workflow untouched | n/a | n/a | open (`steward-browser-render-driver`) |
| 14 | `gaia steward founder` should list open decision records | no | none (visible CLI output is human-gated) | n/a | n/a | open (`steward-founder-command-records`) |

Throughput (`maxDispatchesPerRun` 1, `maxInFlight` 2, `maxAttempts` 2, `maxRepairsPerRun` 2): reviewed on 2026-10-28 and **not** proposed for change; see the weekly closure report. Nothing here modifies a governed limit.

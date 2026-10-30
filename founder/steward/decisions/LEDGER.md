# Steward decision ledger — founder rulings of 2026-10-21 and 2026-10-28

The desk reads only `*.json` here, and a record is `open` or `decided`. This file holds the finer lifecycle.
States: **approved** (founder ruled) · **implemented** (change exists on a branch or PR) · **verified** (independently checked) · **landed** (merged to main) · **awaiting founder review**.
Landing reconciled against GitHub and `main` on 2026-10-28: #2121 merged as `057e208f0424b9605afc92417ff426fe7077e70d`; #2122 and #2123 closed as superseded by #2147, merged as `42e591577cf3d5b2749e5fdca1b7b8ec78bf7952`; #2202 merged as `953021736c136a8b0aa1d74339d4ae8804ee5536`. Historical verification below is not evidence that a live workflow ran. Landing an implementation does not approve its unfinished policy proposals.

| # | Decision | Approved | Implemented | Verified | Landed | Record status |
|---|---|---|---|---|---|---|
| 1 | Landing target | yes | PR #2121: landing job on by default, branch `dev/steward-integration` created | unit tests only; no live GitHub run yet | yes, #2121 (`057e208f`) | decided |
| 2 | Trust-stamp refresh (#1642) | yes, with review | PR #2122 (22 stamps, stacked on #2121) | original review historical; #2147 replacement verified all 22 values, hashes and timeline receipts | yes, replacement #2147 (`42e59157`); #2122 superseded | open: event-driven refresh policy still awaiting founder review |
| 3 | `unused_import` Class B route | yes | PR #2121 | unit tests and coverage check pass; no live dispatch yet | yes, #2121 (`057e208f`) | decided |
| 4 | Lane `maxInFlight` 2 | yes | PR #2121 | unit and scenario tests pass; no live concurrency run yet | yes, #2121 (`057e208f`) | decided |
| 5 | Gate `provenance` and `evidence-seed` | yes | PR #2121 | `ungated_mutation` findings 4 to 2 on live scan | yes, #2121 (`057e208f`) | decided |
| 6 | Timeline causality (#1699) | yes, for investigation and preparation only | PR #2123 (verb in #2121; 3 timelines re-sorted, stacked on #2121) | #2147 replacement verified exact event count, identities, timestamps and content multiset | yes, replacement #2147 (`42e59157`); #2123 superseded | open: workflow-skill-creator rank/status ruling unresolved |
| 7 | Agent-agnostic one-click execution via gh-aw | yes (founder directive 2026-10-21) | PR #2121: `steward-full.yml`, 8 compiled gh-aw agent workflows, `steward_agent_dispatch.py` | unit tests and local `gh aw compile` only; no agent has run on GitHub yet | yes, #2121 (`057e208f`); workflow remains founder-paused | decided; landing is not reactivation |

Decision 6 is conditional by the founder's ruling: re-sort only if factually justified, with identities, timestamps, content and meaning unchanged, and never merged automatically.

## Rulings of 2026-10-28 (weekly integration `integration/steward-weekly-2026-10-28`)

#2202 is merged, not draft. All 14 latest-head checks completed: 13 successful, one intentionally skipped; no auto-merge request remains. "Verified" names the independent check; a ruling whose implementation is partial stays partial. The six open decision records remain open.

| # | Decision | Approved | Implemented | Verified | Landed | Record status |
|---|---|---|---|---|---|---|
| 8 | Trust-stamp refresh (#1642): event-driven recalculation with periodic reconciliation as backup; recomputing derived data is not a governed trust change | yes (founder, 2026-10-28) | partial: stale stamps now say `recomputationOnly` and carry the restamp command; the event hook is not built (needs a Verifier-gated CLI change and a policy amendment) | independent Sonnet verifier, see PR | partial implementation landed in #2202 (`9530217`), not the event hook | open: ruling made, implementation approval pending (`steward-trust-stamp-refresh-policy-1642`) |
| 9 | Evidence before demotion (#2201): an empty effective pool is never grounds for demotion | yes (founder, 2026-10-28) | partial: sensor reports an evidence gap, no demotion target, out of the lane; closes answered escalations; discovery routine not built | independent Sonnet verifier, see PR | partial implementation landed in #2202 (`9530217`), not discovery | decided (`steward-evidence-before-demotion-2201`) |
| 10 | workflow-skill-creator awakened at 4-star after #1699 closed (`steward-workflow-skill-creator-demote-1699`) | no | none (canonical data; Steward may not touch it) | n/a | n/a | open |
| 11 | Dedicated `trust_evidence_gap` Class C kind and discovery routine | no | none (needs policy entries) | n/a | n/a | open (`steward-trust-evidence-gap-kind`) |
| 12 | Class B route for workflow timeouts | no | none | n/a | n/a | open (`steward-workflow-timeout-route`) |
| 13 | Wire the browser-render collector into the scheduled workflow | no | collector and sensor landed in #2202; workflow untouched | collector/sensor independently verified in #2202 | collector/sensor only (`9530217`), not scheduling | open (`steward-browser-render-driver`) |
| 14 | `gaia steward founder` should list open decision records | no | none (visible CLI output is human-gated) | n/a | n/a | open (`steward-founder-command-records`) |
| 15 | One-line edit to `.agents/skills/trust-appraise-all` (forbidden path for the knowledge-contradiction route) | yes, one-time and path-specific (founder, PR #2202 comment, 2026-10-28); does not widen the Class B envelope or amend `POLICY.yaml` | `b6e2d05`, retaining #2178's canonical `gaia-tm-inspect` alias | independent Sonnet verifier PASS; latest-head GitHub checks completed successfully | yes, #2202 (`9530217`), head `d144490c` | decided (`steward-knowledge-skill-path-exception`) |

Throughput (`maxDispatchesPerRun` 1, `maxInFlight` 2, `maxAttempts` 2, `maxRepairsPerRun` 2): reviewed on 2026-10-28 and **not** proposed for change; see the weekly closure report. Nothing here modifies a governed limit.

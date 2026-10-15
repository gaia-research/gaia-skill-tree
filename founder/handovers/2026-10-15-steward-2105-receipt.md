# #2105 — Steward routine coverage founder preview

Delivery: draft integration PR [#2107](https://github.com/gaia-research/gaia-skill-tree/pull/2107), branch `dev/steward-coverage-2105`. **Do not merge before founder preview and policy review.**

Code reviewed independently at `daad66ac5113b3350baff484197135922e8f7cc4`, against main `8a22c56be8190dbe51bc12375db5db1922dc852c`. Subsequent receipt-only commits do not change that code. Final-head CI proof is recorded on the PR after checks settle.

## Architecture and shipped coverage

- One additional read-only sensor: `repository-hygiene`. It reports only eight enumerated tracked Class P paths. Intentionally tracked catalogs, Class S, untracked output, unusedness, branch age and speculative deletion are excluded. Failed, malformed or incomplete Git inventory produces unknown coverage.
- Extended the existing Knowledge Contradiction sensor; no duplicate sensor. Shared finite #2052 retired-claim predicates check explicitly named active trust guidance, including both mirrors. Byte parity alone cannot hide the historical semantic contradiction. Empty, missing, unreadable or oversized required semantic inputs fail closed. Archives/handovers stay historical; explicit denials and retirement warnings have negative controls.
- Proposed, policy-validated hygiene and knowledge Class B routes; **5 routes total**, **2 existing Class A mirror executors unchanged**, **14 registered sensors**. The forbidden-path floor, zero runtime model budget, immutable receipts and independent verification remain intact. No canonical writer or new repair executor.
- Read-only coverage checker and machine-readable [inventory](../steward/routine-coverage.json): all **17 routines**, **14/14 sensors accounted for**, **11 partial / 6 absent**, no claim that all routines or the repository are healthy. It validates authoritative routine headings, emitted kinds, actual policy bindings, test/producer paths and explicit unknown hooks.
- Curation/installability integration is deliberately a capability-only hook, not a new runtime adapter. Existing projections/checkpoints do not establish current-source, environment-pinned, independently verified execution. Their owner-approved proof is required before any live health claim. No new observation/evidence schema or debt merely for missing external proof.

### Routine matrix (summary)

The JSON inventory carries exact debt kinds, authority, route/executor/founder bindings, tests and gaps. This table is its human summary, not another source of truth.

| # | Routine | Coverage and deliverability |
|---:|---|---|
| 1 | Dead-Code Gardener | Absent; no unusedness/deletion inference |
| 2 | Architecture and Abstraction Doctor | Absent; no invented blanket human gate |
| 3 | Error, Diagnostics, and Incident Learner | Partial: controller unknown-coverage diagnostics, intentionally undispatchable |
| 4 | Test Portfolio Gardener | Absent; no portfolio-quality inference |
| 5 | Flake and Isolation Hunter | Absent; no calendar-triggered flake work |
| 6 | CLI and Runtime Contract Steward | Partial: CLI declaration drift; bounded B proposal route |
| 7 | Mutation, Authorization, and Abuse-Boundary Examiner | Partial: registry/frozen-state checks, not general authorization assurance |
| 8 | Schema Evolution Steward | Partial: Class A bundled mirror; evolution/migration decisions remain governed |
| 9 | Evidence and Trust Reconciler | Partial: link structure, rank/grade, benchmark and taxonomy checks; only calibration has B routing |
| 10 | Timeline Causality Keeper | Partial: frozen-state checks, not full timeline causality |
| 11 | Registry Structure and Installability Examiner | Partial: structure/upstream metadata; registry B route and generic-mapping C queue; execution unknown |
| 12 | Artifact, Branch, and Repository Hygiene Sentinel | Partial: tracked Class P allowlist, agent mirror, selected projections; hygiene B proposal, mirror A repair |
| 13 | CI Architecture and Efficiency Steward | Absent; no automatic CI/churn health sensor |
| 14 | Release and Supply-Chain Examiner | Partial: local upstream metadata, not live releases/dependencies/publication |
| 15 | Frontend Quality and Resilience Steward | Partial: selected projection structure; no browser/rendered-health claim |
| 16 | Browser, Privacy, and External Trust Auditor | Absent; security review is not fabricated sensor coverage |
| 17 | Knowledge, Nomenclature, and Agent-Surface Editor | Partial: finite contradictions, mirror parity and taxonomy; knowledge B proposal and mirror A repair |

Present but unrouted B kinds remain explicit in each binding: taxonomy, upstream, evidence-link, generated-projection, benchmark and frozen-skill drift. `sensor_coverage_unknown` is deliberately unrouted and blocks both dispatch and founder rendering. None is silently represented as repaired or deliverable.

## Delegation and independent review

Luna delivered hygiene/routing (#2109), semantic extension and repairs (#2108/#2110/#2113), matrix/checker (#2111), and historical/fail-closed fixtures (#2112). The lead inspected each bounded diff and integrated by merge commits. Worker PRs target only the integration branch, never main.

Flash was assigned matrix/regression/documentation work. Its configured route exited before implementation; the available OpenRouter route failed with an explicit credit-limit error. No global settings were changed and no credits were added. Luna completed the blocked assignments. Flash reconnaissance is not counted as implementation proof.

A separate clean-context reviewer returned **accept-for-founder-preview**, no blockers, at the exact code SHA above. It ran 230 focused tests plus five targeted negative probes, checked 14/5/2 and 6/11 counts, inspected the full aggregate diff, and found no authority expansion, canonical mutation, calendar debt or visual/public-site scope. This verdict is **not** founder approval or runtime self-acceptance.

Review-driven repairs included a quoted-claim false negative, empty semantic-input false green, missing live-binding validation and invented blanket human gates in the first matrix draft. A broader suite caught seven CLI fixture failures caused by missing new required inputs; those fixtures now supply the inputs instead of hiding unknown coverage.

## Verification

- Baseline Steward suite: **309 passed**.
- Coverage checker: `python scripts/check_steward_coverage.py --check --json` — **passed**, `capabilityOnly: true`, `liveHealth: not-evaluated`, 17 routines, 14 sensors, 5 dispatch rules, 2 executors, no unaccounted sensor.
- Independent review suite: **230 passed**; separate targeted malformed-catalog/unknown-routing probes: **5 passed**.
- Combined local Steward/authority-map/installability/checkpoint/evaluation run: **461 passed, 1 platform failure**. The unchanged installability hard-link test calls `os.link`, which this Termux Python does not expose. Running that exact test on unchanged main `8a22c56be` reproduced the same `AttributeError`; `hasattr(os, 'link')` is false. The explicit available-platform rerun passed **461 tests, 1 deselected**. No assertion or platform guard was weakened; the full Ubuntu CI run remains responsible for exercising that test.
- Repository guards, registry schema/DAG/integrity validation, agent mirror parity, bundled schema parity and diff whitespace checks — **passed**. Existing allowlisted vocabulary findings remain baseline warnings, not new failures.
- Live scan before/after/repeat: the **same 51 pre-existing B debts**, zero unknown sensors, zero models, no new sprint debt. Observation count 74 → 76 reflects one new sensor and its coverage mark. Repeat creates zero debt; this is not a claim that existing registry debt is resolved.
- #2042 fixture proves the already-shipped English-page glob catches a new stale page in check-only mode without changing bytes. #1642 fixture proves a changed evidence hash can remain invisible when grade/rank is unchanged; it does not pretend cache freshness is covered.
- Parent-run real-sensor scenarios at the reviewed SHA all **passed**: hygiene clean → actual tracked Class P drift → equivalent-scan deduplication → Git physically unavailable/old debt retained/dispatch denied → recovered no-op; knowledge clean with historical archive ignored → historical semantic contradiction in two byte-equal mirrors → physically empty authority map/old debt retained/dispatch denied. Every receipt had `models: []`. Only temporary fixtures were mutated. An initial ad-hoc probe used a nonexistent receipt attribute; the corrected probe uses the real serialized receipt contract and its complete output was inspected.
- Final-head CI is recorded on the PR after settlement, not inferred from local results or worker confidence. At the first bounded window all guards were green and the full package job was still pending; no pending run is called passing.

## Existing issue reconciliation

| Owner | Reconciliation; no duplicated ownership |
|---|---|
| #2001 | Weekly rhythm, scheduler and ongoing retrospective stay there; this sprint supplies the coverage artifact and concrete regression evidence |
| #1922 | Independent curation assurance remains there; compact checkpoints/builder transcripts are not independent adjudication |
| #2052 | Reuse merged #2094 guidance/authority-map controls; historical fixture is not a claim corrected main remains broken |
| #1445 | Reuse merged #2059 parity classifier and #2058 repairs; remaining upstream/component policy calls stay with its owner |
| #2063 | Dependency manifest/preflight program remains there; no parallel metadata redesign |
| #2042 | Existing generator glob reused and tested; no competing generator and no edits to open docs PR #2045 pages |
| #1642 | Rank-vs-grade sensor's cache-freshness blind spot is explicitly tested/documented, not silently auto-calibrated |

No linked issue is closed, no new child issue carries unfinished sprint work, and unrelated in-flight intake/meta-sweep PRs are untouched.

## Founder decisions and finish boundary

1. Review the two proposed Class B routes and their narrow path/command envelopes in `founder/steward/POLICY.yaml`. Observing a protected-source finding never authorizes its mutation; diagnosis-and-stop is a successful outcome.
2. Preview the architecture, matrix and proof, then decide whether to authorize integration to main. The PR stays draft; no merge, release, schema/ontology ruling, registry mutation or production deployment has occurred.

Entrypoints/design evidence: not applicable. No public HTML/CSS/JS, rendered interface, generated Class S artifact or CLI formatting surface was changed. The ordinary scan can show the newly registered sensor's observations; no new command or output format was introduced.

# Steward routine coverage sprint — #2105

Status: implementation architecture; founder preview required before main integration.
Baseline: `8a22c56be8190dbe51bc12375db5db1922dc852c` (main and origin/main at inspection).

## Decisions and interfaces

1. Reuse `Observation`, controller reconciliation, semantic debt identities, policy validation, immutable routing receipts and independent verification. No new runtime scheduler, observation schema, model calls, network requests or canonical writer.
2. Add one read-only `RepositoryHygieneSensor` (`repository-hygiene`, debt `repository_hygiene`) in its own module. Inspect Git's tracked index for a deliberately enumerated Class P set; do not inspect untracked caller output, infer unusedness, delete branches/files, regenerate projections, or duplicate mirror/projection sensors. Git unavailable, wrong checkout, failed or truncated inventory means an exception, converted by the controller into unknown coverage. Stable subject identity survives equivalent scans.
3. Extend the existing KnowledgeContradictionSensor, not a second sensor. Reuse #2052's bounded retired-claim rules as a shared read-only helper for active trust guidance. A historical positive fixture is evidence of a missed failure class, not a claim that corrected main is currently broken. Missing/unreadable required semantic inputs must never report healthy. Preserve archives, retrospectives, handovers and historical quotations.
4. Proposed hygiene and knowledge routes are report/proposal-only Class B. Keep compiled protected-path floor, existing Class A writes, zero routing budget and independent reviewer unchanged. Founder/root/canonical-skill edits are not granted. If the actual finding requires a forbidden edit, return diagnosis and stop. POLICY.yaml changes on this branch are an explicit founder-review proposal, never permission to land policy autonomously.
5. Machine-check one 17-row coverage catalog against actual registered sensors, emitted debt kinds, policy classes and available dispatch/repair routes. Coverage is a capability inventory, NOT live health. `partial`, `absent`, `present-undeliverable`, and `human-gated` remain first-class, with scoped gaps and owning issues. No calendar-driven debt and no one-sensor-per-routine target.
6. Curation assurance (#1922) and installability (#1445/#2063) hooks must consume existing proof contracts or declare unavailable/unknown. Do not invent a parallel evidence/receipt schema, run installations inside scan, equate metadata/link checks with execution, or turn missing external proof into automatic maintenance work. The catalog is the safe integration seam until an owner provides compatible proof.

## Work segmentation

- L1 / Luna: new hygiene module and focused tests; policy class/priority and two narrow proposed routes; no edits to existing sensors.py.
- L2 / Luna: existing Knowledge sensor and shared semantic helper, #2052 reuse, historical/missing-input tests; register hygiene at integration once its module is available. No policy-file edits.
- F1/F2 / Flash: machine-readable routine matrix + read-only checker + contract/regression tests, including #2042 and #1642 limitations, fail-closed routing. No edits to sensor implementations or policy.
- F3 / Flash: code-backed documentation proposal after integrated proof, no constitutional rulings.
- Lead: architecture, ownership reconciliation, inspect/merge bounded worker PRs, independent verification and founder receipt. Separate reviewer sees aggregate diff and independently probes failure cases.

Workers use isolated worktrees, exact scopes, focused tests and approved Git identity. They commit/push bounded branches and return proof; no main merges, force pushes, releases, registry mutation or self-acceptance.

## Numbered delivery plan

1. Reconcile all routines, live issue threads and open PR overlap; preserve existing owners.
2. Implement L1/L2 and F1/F2 independently; inspect each diff, integrate through worker PRs.
3. Run full Steward tests plus focused reused authority/cache-busting/installability gates; demonstrate healthy, real drift, unknown and unauthorized routing behavior.
4. Independently review aggregate against actual main base; repair reproduced regressions; reconcile F3 documentation from code.
5. Push one draft integration PR, inspect CI at its actual head SHA, publish exact proof and pending founder decisions. Stop before final merge.

## Existing ownership (verified live)

- #2001: weekly orchestration and ongoing sensor retrospective; this sprint supplies concrete coverage artifact, not scheduler ownership.
- #1922: full independent curation assurance; no automated adjudication here.
- #2052: PR #2094 merged; reuse its authority-map tests and retired-claim predicates. Remaining resume/schema/governance work remains with that owner, not quietly reimplemented.
- #1445: parity classification and explicit-rejection distinction already shipped in #2059; registry repairs in #2058. Remaining upstream/component policy decisions remain human-owned.
- #2063: dependency manifests and preflight; no dependency metadata redesign here.
- #2042: English page glob already in `build_html_cache_busting`; add historical regression evidence, not a competing generator. Open #2045 edits English documentation; do not touch its pages.
- #1642: existing rank-vs-grade sensor does not prove hash-cache freshness after evidence refresh. Record/test this distinct limit without promising an automatic writer.

Open PRs inspected: #2090/#2089/#2087 (separate intake integration), #2045 (English docs), #2032 (meta sweep). No existing PR implements this coverage sprint. Issues remain open until their actual owners resolve them; no new child issue needed.

# Steward campaign #2283 — locked open decisions (closeout 2026-11-08)

**Status: LOCKED.** These items are parked by founder directive. No Steward lane, builder or lead may act on them until the founder reopens them.

The directive (2026-11-08, verbatim): "For now leave class C, but lock the decisions somehow so I can pick up later."

**Source:** the final closeout observation, run `run-20261108T124850Z-16c12217` at campaign tip `75954c9be`, with census A 1 / B 191 / C 223. The counts are a snapshot, and the Steward ledger (`refs/heads/steward/ledger`) remains authoritative.

**How to pick up:** reopen one section at a time. Record each ruling verbatim in a dated `FOUNDER_RULINGS_*.md` file in this folder before anyone acts on it. Steward never acts on a Class C item without that record.

## A. Class C debt by kind (open, observed)

| Kind | Open | What it needs from the founder |
|---|---:|---|
| `trust_stamp_stale` | 170 | A ruling on whether a governed restamp may run in bulk. Decision A (suite cap 49.9) told Steward to "refresh stamps" after recalibrating. That refresh was not run. Most of these are stamps for the cap-only components, where the stored grade differs from the computed one. |
| `credential_leak` | 50 | A security triage: which pattern hits are real secrets, which are documentation examples, and which need to be rotated. These are Class C by policy, and Steward never edits them. |
| `trust_evidence_gap` | 2 | Whether skills with no scoring evidence rows keep their preserved level or get demoted. Example: `majiayu000/edge-model-compression`, preserved at 2★ with TM 0. |
| `issue_founder_decision` | 1 | A closeout discrepancy on umbrella issues #1823 and #1996, raised by routine 18. |

## B. Founder decision items raised during the campaign, not yet ruled

1. **Cache-bust version for the cap change (#2378).** The `?v=9.3.0` cache-bust on 82 pages comes from the manifest version, so the cap change is only cache-busted by a version bump. The choice is a bump now or waiting for the next release.
2. **Declared-wait floor for workflow timeouts.** The history formula `ceil5(max(2×p95, 1.5×max))` can undercut a job's own bounded wait. Example: auto-merge-small-prs has a declared 15-minute wait. Should the declared wait be a floor?
3. **No-history wording conflict.** For workflow `55b938d79131`, the policy forbids waiting on other workflows but cites this job as its example. One of the two needs to change.
4. **Deploy waits.** Workflow `52236ab2419b` has Wrangler deploy waits. Should action wait bounds include deploy polling?
5. **Stale-entry policy for workflow-gate baselines (#2392).** The current behaviour warns on `dev/*` and fails elsewhere. Confirm, or set another policy.
6. **`issues: write` on the paused activation job (#2390).** It is dormant today. Should it be kept or removed before activation?
7. **Ceiling-exceeded calibrations outside decision A.** Each demotion keeps governed authority, so each needs a yes or no:
   - `cis2042/product-design-harness` → 1★
   - `google-deepmind/workflow-skill-creator` → 3★
   - `jpoutrin/create-plugin` → 1★
   - `kishorkukreja/inventory-optimization` → 1★

   `garrytan/investigate` also shows here on the campaign branch only. It is already frozen on main (#2373), so the item drops out once the campaign is delivered.
8. **F3 promotion proposals.** These are proposal-only under ruling F3, because each skill's last rank event was a recorded demotion. Each needs a yes or no:
   - browser-use/browser-harness 4★
   - gaiabot/repo-docs-before-pr 2★
   - k-dense-ai/deepchem 4★
   - k-dense-ai/pymc 4★
   - k-dense-ai/pytorch-lightning 2★
   - k-dense-ai/qiskit 2★
   - k-dense-ai/scanpy 3★
   - k-dense-ai/stable-baselines3 3★
   - k-dense-ai/torch-geometric 4★
   - k-dense-ai/transformers 3★
   - laravel/upgrade-laravel-v13 4★
   - martin-stepanoski/nielsen-heuristics-audit 2★
   - mattpocock/tdd 3★
   - pexp13/sentiment-analysis 4★
   - xquik-dev/hermes-tweet 2★

   Two more are refused by the calibrate star-gate preflight: `emilkowalski/apple-design` 4★ and `emilkowalski/emil-design-eng` 4★. They need evidence or a ruling, not a calibration.
9. **Framework or CLI package downloads as evidence.** Filed as RFC #2403, low priority.

## C. Not locked (handled elsewhere)

- **Repair routes** for Class B kinds that have no active route are filed as issues: `swallowed_exception` #2404, plus the issues listed in the closeout PR.
- **Leftover routable Class B work** (workflow timeouts, escalated unused imports) has its own Steward leftovers issue, listed in the closeout PR.

# Steward PR maintenance (routine 19): controlled pilot, 2026-11-04

Scope: `gaia-research/gaia-skill-tree` only. `gaia-skill-heaven` and organisation-wide discovery are deferred by founder
direction ("steward only observes skill tree first. skill heaven deferred"). Implementation: PR #2281.

## What the pilot did (observed on GitHub)

| Pull request | Outcome | Evidence |
|---|---|---|
| #2286 (report 2026-44, replaces #2157) | merged, `504ddcfc` | independent PASS bound to the merged head; checks green |
| #2288 (report 2026-45, replaces #2270) | merged, `4a455587` | independent PASS bound to the merged head; checks green |
| #2157, #2270 | closed without merge | each only after its replacement merged and a second independent verification against `main` |
| #2285 | withdrawn | first replacement; failed the required scope check on its branch name; rebuilt as #2286 |
| #2235 | held, Class C, untouched | draft, `human-proposal` + `needs-review`, 0 of 1 approvals; founder decision receipt posted |

`main` advanced only through the two merge commits and the two release commits (`v9.1.0`, `v9.2.0`). No direct push.

## Founder review notes, 2026-11-04 (verbatim)

> Full-suite confirmation: Require Python Package to pass on 9026655a, including the tests that previously failed during collection.

> Founder desk consistency: The generic Class C desk says it has no recommendation, while the PR receipt recommends keeping #2235 as a draft. Both surfaces should distinguish a procedural recommendation to retain the hold from a substantive decision about the documentation.

> Unattended execution: The outcome ledger is local to each checkout. This is sufficient for the controlled pilot, but not proof of cross-host exactly-once execution or globally enforced write budgets. Production should use the remote-tracking authority reference and either a single controlled writer or shared coordination.

## Resolution

1. **Full suite.** `9026655a` fixed collection (6850 tests passed in CI) but `Python Package` still failed on one test,
   `test_a_payload_that_differs_from_the_originals_is_never_accepted`. Cause: it re-pointed `docs/steward-pr-2157-2026-44` with
   `git checkout -B` while `buildReplacement` keeps that branch checked out in its worktree. git 2.43 allows that; the CI runner's
   git 2.56 refuses (exit 128), so the test passed locally and had been hidden by the collection errors. The fixture now fails the
   same way on every git version (red before, 149 passed after) and the test builds on a detached HEAD (`9fd2c17c`). The CI result at
   each pushed head is recorded on PR #2281, not assumed here.
2. **Desk and receipt.** They answered different questions and were composed separately: the desk's generic Class C text said
   "None. This turns on product, ontology, or prestige judgment", while the receipt text was written by hand. Both now render two
   labelled paragraphs from one module (`src/gaia_cli/steward/prmaintenance/advice.py`): a **procedural recommendation** (retain the
   hold; derivable from policy; no judgment of the content) and the **substantive decision** (whether the change should land; the
   founder's; Steward offers no opinion). The receipt no longer accepts a free-text recommendation. Tests assert that the desk, the
   digest and the receipt carry identical wording, and that nothing a pull request controls can reach either paragraph.
3. **Unattended execution.** Accepted as stated. The pilot's guarantees are checkout-local: the per-run and hourly budgets and the
   exactly-once reservation are counted in `.gaia/steward/pr-maintenance` in one checkout. They are not proof of cross-host
   exactly-once execution and not a global budget; the effective ceiling is writers × cap. Every authorization now records
   `coordination: "checkout-local"`, and the skill and routine guide state the limit and the production requirement:
   `GAIA_STEWARD_PR_AUTHORITY_REF=origin/main` (never the local-head override) plus **either** a single controlled writer **or**
   shared coordination (a lock and budget counter outside any one checkout) before the caps are called global.
   GitHub remains the cross-host backstop: a merged or closed PR cannot be merged or closed again, and `expectedHeadSha` refuses a
   moved head. That limits damage; it is not a lock.

## Pilot posture

The route runs under the committed local head of the then-unmerged PR (`GAIA_STEWARD_PR_AUTHORITY_LOCAL=1`) by explicit founder
go-ahead; every authorization says so. It is a controlled pilot, not an unattended production deployment.

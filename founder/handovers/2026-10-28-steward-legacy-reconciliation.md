# Legacy Steward reconciliation — founder decision receipt

Engineering receipt for #2133, #2139, #2202 and replacement weekly #2230. This is **not** source-merge authorization, Class A issue-closure ratification, rollout approval, or a release receipt. Final published-head CI and any rendered-evidence updates are recorded on the existing PRs; earlier green checks are not substituted for them.

## PR disposition and preserved history

| PR | Disposition | Branch / preserved SHA | Remaining gate |
|---|---|---|---|
| #2202 | Already merged with founder authorization | Head `d144490cb`; merge `953021736c136a8b0aa1d74339d4ae8804ee5536`, ancestor of main `fc0e6f8d91aa759629bb36c0e188b116b4511808` | None for that historical merge; not blanket authority for later work |
| #2139 | Closed as superseded after replacement was pushed and independently verified | Original `0c9fa2f2703522ce39c0bd60abf72d4e3d510c03`; preservation comment `6468694396` | None; do not reopen a duplicate routine campaign |
| #2230 | Sole next draft weekly PR | `dev/steward-weekly-legacy-2026-10-28`, `4be508c06d6fdd9e4cac32d154c226886f522974` | Founder content/design review and explicit source-merge authorization |
| #2133 | Sole draft issue-hygiene feature PR; updated in place, never force-pushed | `dev/steward-issue-hygiene`, published from `work/steward-legacy-2133`; original `7facad74ce280e47b7ca05fb891c62f628d57b2e` retained | Final published-head CI, founder source review and explicit merge authorization |

The main merge into the feature was non-destructive: `6b0d2f9a07ef63ad55295cb32c4221fc559bb06d`. Main's full-abandon and browser-render implementation coexist with routine 18: 18 routines and 32 registered/accounted sensors. Static capability coverage is not live operational health. Historical #2202 authority-map correction and its one-time `trust-appraise-all` exception remain historical; normal `gaia-tm-inspect` compatibility delegation was not replaced.

## Final implementation and verification

The original builder checkpoint and exact component commands remain in [the phase-3 receipt](2026-10-28-pr2133-mission-phase3.md). Subsequent independent review found substantive defects despite those passing suites; the final repairs below supersede that checkpoint's completion claim.

- Affirmative authority requires both `status: decided` and exact `resolution: approved`; a rejected decision cannot authorize closure. Public executors also enforce current checkout policy, fresh complete proof, receipt confinement and budget reservation. Actual authority is still OPEN/pending and `writesEnabled` is false.
- Closure compares complete non-payload history, including comments from the authenticated closer's own account. An immutable, atomically written original-history digest under the confined receipts store binds retries across run receipt files. Existing markers cannot adopt missing/corrupt/symlinked baselines. Expected multipart payloads are verified before generic history drift, retaining the specific preservation-failure contract.
- `a61d31f19b7bfdca6a141ab25c1600b85db33d06` brackets the initial comment-history read with a fresh issue read **before** baseline creation or marker posting. Timestamp/state/identity/plan drift during that read refuses the attempt. This repairs the independently reproduced initial-read objection race, not just the later retry symptom.
- Staged approval establishes fresh upstream ownership before authorization-denial writes and fails the **job**, not merely the guard step, when ownership cannot be proved. Downstream comments/labels/dispatches cannot run after that failure. The staged child-cascade checkout uses trusted `main`; legacy job bodies remain unchanged. Rejection explicitly dispatches the cascade rather than relying on a `GITHUB_TOKEN` close event to trigger another workflow.
- Source-qualified child identity, full finding coverage, escalation and conservative ref parsing from the Luna watcher commits are preserved. Arbitrary slash refs are not stripped; `www.github.com` is canonicalized. Existing trusted-simple-ref ambiguity is disclosed below, not claimed solved.
- Shared driver compatibility from #2230 is integrated without importing its documentation/workflow payload: `6c6973c62fb27804701b8dad0f226cd4178af100`, cherry-picked as `dab19e94e746b9219dde157988f5987806812cae`. `--no-agents` blocks Class B dispatch even when command/engine/Claude readiness is detected; existing gated Class A routing remains available. The prior cross-PR driver conflict is resolved. `git merge-tree --write-tree` with weekly `4be508c06` succeeds without changing either PR's base or merging either source PR.

### Verified evidence, not additive test totals

- Final closure review at `a61d31f19`: Terra/high **PASS**, 709 issue-hygiene tests and seven independent mocked probes. The actual public checkout refused with `authority-pending`, zero forge calls and no journal creation.
- Parent broad regression at that same SHA: **2,356 passed** (`tests/steward` plus `tests/test_dev_upstream_verbs.py`, `-n 4`). This supersedes the earlier 2,354-pass frozen-head run.
- Workflow final focused review at `f617bc75c`: Terra/high **PASS**, 73 tests and two independent ownership-read-failure probes. Full watcher/workflow regression: **739 passed**. These files are byte-identical in the final closure candidate.
- Shared-driver review at `6c6973c62`: Terra/high **PASS**, 45 tests and five independent mocked probes; final cherry-picked driver files are byte-identical.
- Weekly #2230 independent review: **133 focused tests passed** and exact-head GitHub CI passed, including run `40683174828` tests/build/clean-wheel smoke. Its separate scenario run timed out and is not counted as passing.
- Fresh coverage checker: 18 routines, 32 accounted sensors, seven dispatch rules, two repair executors, no errors; live health explicitly `not-evaluated`. Mirror parity, playbook contract, all nine modified skills' quick validators, Python compilation and repair-range whitespace checks passed. Skill inventory: 81 skills, zero errors, 65 warnings in this local worktree (including generated Python-cache noise), not a warning-free claim.

Final code/test candidate: `41e591c56316303162508c6e07c4dcb73dc7b0ff`. Its production files are identical to the independently reviewed `a61d31f19`; subsequent changes are the separately reviewed CI test only. The publication receipt commit adds only founder Markdown. Final published-head GitHub checks are recorded on #2133, not inferred from candidate-local tests.

All local forge interaction was mocked, with GitHub token variables unset. No live closure pilot, live closure dry run, or live issue-state repair was used as verification. Test scopes overlap and must not be summed as unique tests.

### Earlier package CI failure

Old published head `fb23967b0` failed Python Package run `40730131333`: **6,666 passed, seven skipped, one failed**. The failure was the pre-existing 20 ms executor-start assumption in `test_timeout_late_worker_cannot_change_reconciled_snapshot`; the test and production fanout were unchanged versus main. Later wheel/build smoke stages were skipped, not successful. The existing PR carries a bounded test-harness repair ending at `41e591c56` (worker `96af4c0d1`): actual worker-entry handshake, explicit release/cleanup, unchanged 20 ms in-flight timeout, and a pure otherwise-valid late-receipt control rather than a second scheduling assumption. Terra/high independently passed the full 28-test file and all three controlled probes: 1.1-second submitted-callable delay, delay on both submissions, and 350 ms pause before result collection. The probes also accepted the valid artifact, rejected a corrupt digest, and proved injecting the receipt changes the canonical report. Production curation, timeout policy, evidence and registry behavior are not changed. The final published-head Ubuntu result is linked in the final PR receipt. The old failing run is never represented as green.

## Unchanged live behavior and exact founder decisions

- The full-driver YAML remains dispatch-only with `jobs.drive.if: false`. GitHub currently reports its workflow registration as `active`; that is **not** permission for the disabled job to execute. No workflow was dispatched or platform enable/disable setting changed by this mission.
- The existing upstream watcher stays active on `0 6 * * *`, with legacy fanout defaults and concurrency intact. The `STEWARD_ISSUE_HYGIENE_V2` variable was absent in the read-only API check. No variable was set; new staged behavior was not activated. Existing scheduled watcher writes are not equivalent to mission-created writes.
- At phase-0 inspection the remote ledger was generation 122, updated `2026-10-28T03:00:24.490795Z`, with no leases, three abandoned/two completed runs and two escalated items. This is a timestamped observation, not a new maintenance run or current-health assertion. No run was adopted/reset and no debt was fabricated or closed.

| OPEN decision | Recommendation | Alternative / what it unblocks |
|---|---|---|
| `steward-issue-closure-authority` | Keep writes disabled until the founder explicitly ratifies the A1–A5 proposal and separately authorizes any pilot | Continue manual dispositions; source merge alone grants no issue-write authority |
| `steward-issue-1981-incident` | Leave #1981 untouched while the founder reviews the preserved Oct-22 proof | Separately authorize/audit reversal; never infer incident disposition from an A1 match |
| `steward-upstream-batch-rollout` | Review mocked F3/event behavior and keep the variable unset until explicit rollout approval | Retain legacy deployed fanout and use report-only batch output |
| `steward-closed-umbrella-disposition` | Decide whether closure without an explicit receipt/disposition counts as processed before rollout | Require acceptance/rejection/receipt proof and allow unresolved closed findings to remain actionable |
| `steward-census-empty-page-crosschecks` | Review an independent closed-count completeness contract before relaxing refusals | Explicitly accept the documented persistent-empty risk and full-page stalls; never silently call unknown coverage healthy |

All five structured records remain OPEN. #1981 was not reopened, reclosed or otherwise repaired. The only closed legacy campaign item was superseded PR #2139. No canonical registry nodes, trust/Origin state or canonical registry schemas changed in this reconciliation.

## Honest remaining boundaries

- REST read/write rechecks are not an atomic transaction against concurrent human activity. Mocked proof is not live GitHub Actions event, permission, concurrency or operational validation. The same-decision refresh probe changed the manifest stamp in a copied plan; it did not rebuild a live census.
- Source identity uses the existing trusted-simple-ref envelope, not live GitHub ref disambiguation. A slash ref beginning with a trusted prefix remains a disclosed shared-policy limitation. Closed-history completeness and disposition semantics remain the explicit founder decisions above.
- The #2230 CLI-reference rows are founder content/design-gated. Both the original attempt and the bounded recovery attempt produced **zero screenshots**: installed isolated headless Chromium stalled/timed out and no browser MCP was exposed. No empty evidence page was presented as rendered proof. Desktop/mobile before/after capture and founder visual review need a supported browser environment. No global tool installation, visible-user-browser driving or preview deployment was attempted.
- Original unrelated worktrees, untracked discovery/census files and `.pi/` task output remain preserved. Session output is not staged as source. Historical merge/feature branches are not deleted while their draft PRs remain open.

## Release disposition

A minor release is warranted by the additive CLI/integration work, but **release preparation and publication remain held until the required source integrations actually merge with explicit founder authorization**. Authorization for the later release PR merge and canonical PyPI publication is not authorization to merge #2133 or #2230.

Observed baseline: main/latest GitHub prerelease `8.28.2`, official PyPI/latest production `8.25.0`. A clean isolated official-PyPI install confirmed `8.25.0` and the absence of `steward full`; this is the old published/source gap, not a new-release smoke test. No version bump, release PR, tag, publisher dispatch or package publication was performed.

After authorized source merges: re-read actual main and release state, recompute the next minor, follow `/gaia-release` for lockstep bump/changelog/release PR/gates, use the canonical trusted publisher with fresh matching minor-release Class P assets, then independently install from official PyPI and verify version, artifact provenance, packaged assets and CLI behavior. Do not include unmerged branch work or assume today's version remains the correct base.

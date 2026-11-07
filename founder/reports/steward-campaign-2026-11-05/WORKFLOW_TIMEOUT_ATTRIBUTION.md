# Workflow timeout attribution: is Cloudflare the culprit?

**Context:** founder ruling #14 (`founder/steward/decisions/steward-workflow-timeout-route.json`, #2283). The founder said "I do think most timeouts are related to cloudflare. Please research and check if its the culprit." The ruling's own condition: attribute to Cloudflare only on actual run evidence.

**Method (read-only):** GitHub Actions API for `gaia-research/gaia-skill-tree`, every run created in the query window 2026-09-08T00:00:00Z (inclusive) to 2026-11-08T00:00:00Z (exclusive; the observed runs span 2026-09-08T01:11:51Z to 2026-11-06T22:49:45Z), collected 2026-11-06T23:00Z, fetched in one-day windows (one-hour windows for 2026-10-27) so no query hit the 1000-result cap. 9,952 runs were returned: 9,951 completed and 1 incomplete (queued). The completed conclusions sum to 9,951 (an earlier draft wrongly said 9,952 completed). The exact query recipe, per-attribution run ids and the full analysed run-id set with its digest recipe are in the companion manifest `WORKFLOW_TIMEOUT_ATTRIBUTION.manifest.json`; the Actions API history is mutable, so a later re-query can differ by a run or two in a bucket. For every non-success run (cancelled, failure, timed_out, startup_failure): the jobs API (step conclusions and durations), the check-run annotations of each failing job, and job logs where noted. Nothing was written to GitHub or to any workflow.

## Conclusion

**No timeout and no Cloudflare timeout evidence was observed in this completed-run window: 0 of 9,951 completed runs (0.0%) ended `timed_out`, and 0 of 848 non-success runs (0.0%) carry GitHub's job-timeout annotation ("exceeded the maximum execution time").** This is strong negative evidence within the stated scope (names, annotations and the sampled logs), not a proof that Cloudflare could never be involved. Of the 848 non-success runs (8.5% of the 9,951 completed runs), 30.8% were cancelled because a newer run superseded them, 21.0% never started a job (workflow-level failure, cause not visible in the API), 14.3% were real test failures, 9.0% were the branch-scope guard doing its job, and the rest are other step failures and unannotated cancellations; **0.0% (0 of 848) show any Wrangler or Cloudflare signal.** The one Wrangler deploy workflow, `cf-pr-preview.yml`, is manual-only and ran 12 times, all successful, with the `Deploy` step taking 18 to 30 s (median 22.5 s). The longest failing or cancelled job in the window was 23.5 minutes (the full test suite), nowhere near a timeout bound. Separately, there is one real Cloudflare-adjacent defect, but it is a dangling reference and not a timeout: `sync-artifacts.yml` dispatches a workflow file that was renamed in June, and the resulting HTTP 422 is swallowed on every main push (87 of 87 runs). That is filed as #2322. The open `missing-timeout` debts (at this head 72 findings across 39 workflow files, 24 of them in 8 gh-aw lock files) remain configuration findings: they say a job has no declared bound, not that any job ever hung.

## Attribution of all 848 non-success runs

| Attributed cause | Runs | % of non-success | % of all 9,951 completed runs |
|---|---:|---:|---:|
| Cancelled: superseded by a newer run (concurrency group; annotation "Canceling since a higher priority waiting request ... exists") | 261 | 30.8% | 2.62% |
| Failure: no job executed (workflow-level; PR-event workflows such as Auto-merge, Fast-Track, Branch Scope, Docs Cohesion; cause not exposed by the API) | 178 | 21.0% | 1.79% |
| Failure: other step (Validate Gaia Graph 67, Upstream Approve 23, Evidence Health Check 8, Upstream Watcher 8, Steward Full 4, others) | 128 | 15.1% | 1.29% |
| Failure: test failures (Python Package 118, Curation Semantic 2, Release 1) | 121 | 14.3% | 1.22% |
| Failure: branch-scope guard (policy, "Branch scope violations detected") | 76 | 9.0% | 0.76% |
| Cancelled: no supersede annotation and no job recorded (cancelled before or without running a job; longest run 2 min 1 s) | 76 | 9.0% | 0.76% |
| Failure: author-identity guard (policy) | 4 | 0.5% | 0.04% |
| Failure: action resolution (gh-aw action version not found) | 4 | 0.5% | 0.04% |
| **Job timeout ("exceeded the maximum execution time")** | **0** | **0.0%** | **0.00%** |
| **Cloudflare / Wrangler signal in any step name, annotation or workflow name** | **0** | **0.0%** | **0.00%** |

Run-level conclusion counts for the 9,951 completed runs: success 7,208; skipped 1,895; failure 511; cancelled 337; `timed_out` 0; `startup_failure` 0 (sum 9,951). One further run in the window (id 34749378515, status queued) was incomplete when collected and is excluded.

## The runs closest to a timeout (longest failing or cancelled jobs)

None of these timed out; each ended on a test failure, an exit code, or a cancellation. All are `Python Package` / `Test, Build, and Smoke Test` except row 7.

| Run id | Workflow | Job | Step | Duration | Conclusion | Attributed cause | Evidence |
|---|---|---|---|---:|---|---|---|
| 42295764023 | Python Package | Test, Build, and Smoke Test | Full tests | 23m 27s (step 17m 15s) | failure | one test failed (`test_trusted_certificate_sends_one_bearer_request...`: "HTTPS invocation failed", a local-certificate unit test); 8306 passed | https://github.com/gaia-research/gaia-skill-tree/actions/runs/42295764023 |
| 41518413377 | Python Package | Test, Build, and Smoke Test | Full tests | 19m 42s | failure | one assertion failure in `tests/test_lifecycle.py` | https://github.com/gaia-research/gaia-skill-tree/actions/runs/41518413377 |
| 41631979109 | Python Package | Test, Build, and Smoke Test | Full tests | 17m 48s | cancelled | superseded or cancelled while a test failure (`test_timelines`) was already reported; no timeout annotation | https://github.com/gaia-research/gaia-skill-tree/actions/runs/41631979109 |
| 40593278330 | Python Package | Test, Build, and Smoke Test | Install wheel in clean environment | 12m 36s | cancelled | cancelled after the test step passed (5605 passed); no timeout annotation | https://github.com/gaia-research/gaia-skill-tree/actions/runs/40593278330 |
| 40591821440 | Python Package | Test, Build, and Smoke Test | (none recorded) | 12m 14s | cancelled | cancelled after tests passed (5697 passed); no timeout annotation | https://github.com/gaia-research/gaia-skill-tree/actions/runs/40591821440 |
| 40730131333 | Python Package | Test, Build, and Smoke Test | Full tests | 11m 58s | failure | one test failed (`test_curation_reconciliation`) | https://github.com/gaia-research/gaia-skill-tree/actions/runs/40730131333 |
| 39645856269 | Gaia Steward Full | Drive Class A and Class B | Drive the pipeline | 11m 42s | failure | steward driver stopped: a build step failed twice (agent.build); not a platform timeout | https://github.com/gaia-research/gaia-skill-tree/actions/runs/39645856269 |
| 40603913683 | Python Package | Test, Build, and Smoke Test | Full tests | 11m 32s | cancelled | superseded; 4629 passed before cancel | https://github.com/gaia-research/gaia-skill-tree/actions/runs/40603913683 |
| 40580230924 | Python Package | Test, Build, and Smoke Test | Full tests | 10m 57s | failure | one test failed (`test_packaging` wheel smoke) | https://github.com/gaia-research/gaia-skill-tree/actions/runs/40580230924 |
| 42303837980 | Python Package | Test, Build, and Smoke Test | Full tests | 10m 56s | failure | exit code 1 with 7344 passed | https://github.com/gaia-research/gaia-skill-tree/actions/runs/42303837980 |

Useful side finding for the timeout route: the `Python Package` test job is the slowest healthy job (5 to 17 minutes and growing as the suite grows), so a timeout chosen for it from historical durations must leave real headroom.

## Cloudflare checks

| Run id | Workflow | Job | Step | Duration | Conclusion | Attributed cause | Evidence |
|---|---|---|---|---:|---|---|---|
| 38817596515 | CF PR Preview (Worker) | Deploy PR Preview to Cloudflare Worker | Deploy (Wrangler 4.95.0) | 30 s | success | healthy; no Cloudflare timeout | https://github.com/gaia-research/gaia-skill-tree/actions/runs/38817596515 |
| 41545419942 | CF PR Preview (Worker) | same | Deploy | 22 s | success | healthy | https://github.com/gaia-research/gaia-skill-tree/actions/runs/41545419942 |
| 41619753678 | CF PR Preview (Worker) | same | Deploy | 19 s | success | healthy | https://github.com/gaia-research/gaia-skill-tree/actions/runs/41619753678 |
| 34187922602 | Auto-Sync Registry Artifacts | Regenerate and Commit Artifacts | Trigger Cloudflare Deploy | under 1 s | success (step failed, swallowed by `continue-on-error`) | dangling reference: HTTP 422 "Workflow does not have 'workflow_dispatch' trigger" | https://github.com/gaia-research/gaia-skill-tree/actions/runs/34187922602 |
| 41913777758 | Auto-Sync Registry Artifacts | same | Trigger Cloudflare Deploy | under 1 s | success (step failed, swallowed) | same | https://github.com/gaia-research/gaia-skill-tree/actions/runs/41913777758 |

- **`cf-pr-preview.yml`'s Wrangler deployment:** `workflow_dispatch` only, so it can never fire from a push. All 12 runs in the window (2026-10-15 to 2026-11-03) succeeded; Checkout 11 to 17 s, `Deploy` 18 to 30 s, mean 23.2 s, against a 360-minute default bound it has never approached. Production is GitHub Pages behind the Cloudflare CDN (`DEV.md` section 0): merge to `main` deploys, with no Cloudflare job in the path, so no production workflow in this window waited on a Cloudflare step.
- **`sync-artifacts.yml` and `cloudflare-deploy.yml`:** the file does not exist because commit `4f356152a` (2026-06-26) renamed it to `cf-pr-preview.yml`. It is a real dangling reference, not an alternate path: the step `gh workflow run cloudflare-deploy.yml --ref main -f branch=main` returns HTTP 422 on every main push. In the window, 87 of 87 successful sync runs carry the swallowed `Process completed with exit code 1.` annotation, and 13 of 13 sampled job logs contain the 422 message. The step fails in under a second and is `continue-on-error`, so it neither hangs nor fails the run. It costs a permanently red step, not time. Filed as https://github.com/gaia-research/gaia-skill-tree/issues/2322 (label `tech-debt`). This report is evidence only; the sync workflow is fixed in PR #2335 (the dead dispatch is removed, not repointed, because production deploys from GitHub Pages on `main:/docs`, 171 successful pages builds in the same window).

## Limits of this evidence

- Window is 60 days and the API's retention; older runs were not examined. In-progress runs are excluded.
- The 178 "no job executed" runs expose no cause through the API (no jobs, no annotations), so they are attributed to "workflow-level failure", not to a specific component. They have no job and therefore no step that could have timed out or called Wrangler.
- A job killed by a timeout would carry the "exceeded the maximum execution time" annotation; absence across all 848 non-success runs is the basis for "0 timeouts". The 76 cancellations without a supersede annotation recorded no jobs at all and lasted at most 2 min 1 s, so none can be a job timeout.
- Percentages above use the stated denominators (848 non-success runs, 9,951 completed runs); the manifest pins the run ids behind every bucket.

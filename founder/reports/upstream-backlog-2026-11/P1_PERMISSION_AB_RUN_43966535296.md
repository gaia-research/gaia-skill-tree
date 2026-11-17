# P1 permission A/B diagnostic — run 43966535296

**Outcome:** paired diagnostic collected; P1 remains **BLOCKED**. Both artifacts are diagnostic-only (`acceptanceEligible=false`, `p1Pass=false`). Parent run conclusion `failure` is expected from CONTROL's collector exit 3 and is not itself an experiment verdict: CONTROL diagnostic job failed, TREATMENT diagnostic job succeeded.

## Identity and jobs

- Workflow run: [43966535296](https://github.com/gaia-research/gaia-skill-tree/actions/runs/43966535296), completed 2026-11-16 22:05 UTC; event `workflow_dispatch`.
- Actual run head and local feature HEAD: `f6939f9ace0f672c76297eb749b2b314d262b7c7` (matches published run head exactly).
- CONTROL job `133647365969`: failure; setup, checkout, Python setup, upload succeeded; metadata read exit 3. Observed job token permissions: contents read, issues write, metadata read. Runner image `ubuntu-24.04`, version `20261111.370.1`.
- TREATMENT job `133647366335`: success; setup, checkout, Python setup, metadata read, upload succeeded. Observed token permissions: contents read, issues write, metadata read, pull requests read. Runner image `ubuntu-24.04`, version `20261111.127.1`.
- Normal typed-backlog visibility, upstream polling, and challenge-watch jobs: skipped. CONTROL/TREATMENT used same workflow/collector ref and checkout SHA. Runner image versions differed.

## Artifacts and bounded comparison

Saved unmodified under `$TMPDIR/upstream-backlog-2026-11/run-43966535296/{CONTROL,TREATMENT}/diagnostic-upstream-metadata.json`.

| Arm | Artifact ID | Name | JSON SHA-256 | Status | diagnosticOnly / acceptanceEligible / p1Pass | Failures |
|---|---:|---|---|---|---|---:|
| CONTROL | 14276811060 | `DIAGNOSTIC-upstream-metadata-permission-ab-CONTROL` | `a1bedcaa367c977a55a3fb1ae754eb55ab6a3f673842fd70261ccd2881c172f3` | nonhealthy | true / false / false | 2 |
| TREATMENT | 14276536176 | `DIAGNOSTIC-upstream-metadata-permission-ab-TREATMENT` | `8d01b02eae8351b8e0316a5130cd7cf2c32415540b6fa0da55dabcf3522d76e5` | observations-agree-not-acceptance | true / false / false | 0 |

Both report repository counts stable at 255 before and after. Both GraphQL before walks complete: 247 issues and 8 PRs. Before identity-set hashes match across arms: issues `ed6886bc6303dda2b43f704d960275f8d46340081be54eca6e7205acc0e407f4`; PRs `aba1607a45fa5f9e165a96ee0dbc146060fbc525c9113d1be85c381a1cb7afea`.

After GraphQL in both arms is only a one-node count-sample (247 issue count, 8 PR count), incomplete; it cannot establish a full after identity set or stability. These sample hashes are not full-set evidence. REST walks are complete: CONTROL 247 issues / 0 PRs, TREATMENT 247 issues / 8 PRs. CONTROL REST issue identity-set hash matches its GraphQL issue set (`ed6886bc6303dda2b43f704d960275f8d46340081be54eca6e7205acc0e407f4`); PR set is missing, so aggregate REST comparison disagrees. TREATMENT REST aggregate set agrees with its complete GraphQL-before sets (`93177f17a4f89a015315929c0f70edd571fbe21a1aff527d94e07c9aeb3f90fd`). All 12 recorded requests per arm returned HTTP 200 with no typed transport error.

## Interpretation and limits

Observed in this pair: CONTROL REST omits the 8 PRs while TREATMENT REST returns them, with the only observed job-token permission difference being `pull-requests: read`. The observations provide empirical, context-specific support that this grant was associated with restored PR visibility in this run. They do not establish a universal API rule or P1 acceptance. Run metadata marks causality `not-established`; after GraphQL identity walks are incomplete; runner image versions differed; no independent replication was performed. Preserve those limits rather than treating overall run red/green as verdict.

No ordinary permissions changed, no normal run was made, and no merge/acceptance occurred. Existing source-code and workflow scope remains untouched by this report. Full campaign cost remains unavailable; `$4.907920` is P0 partial, not campaign total. The prior normal failure and three standalone diagnostic receipts/hashes remain historical and untouched. This report is the paired-run receipt; new permission or ordinary-run work requires a new explicit owner decision.

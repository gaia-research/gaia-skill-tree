> Final readiness hold: this review at `12bf0fc0f` predates the subsequent workflow stale-approval repair. It cannot authorize integration of a newer #2095 head.

> Historical lane evidence. Status statements describe the inspected commit, not the final integrated tree. The parent recovery report records subsequent merges and holds.

# #2050 / PR #2095 independent security and regression review

Final reviewed immutable commit: `12bf0fc0fceaaed4a4b21c5245e09b23ea965d46` in detached `<review checkout at 12bf0fc0f>`. Reviewed full branch change, including prior `c731a9244` implementation and the new candidate, across workflow, complete recovery script, README, and test changes. No implementation edits, live issue actions, curation, data mutation, PR review, or merge were performed by this reviewer.

**Verdict: the four reported defects are repaired at this commit, and the additional queued-approval revision race found by independent review is repaired. No remaining confirmed blocker in reviewed paths.** Parent retains final authorization/integration decision and required CI gate.

## Independent finding discovered and repaired during review

Initial candidate script SHA256 `1cefac84bfa1e946779df3196aaedc4d768fddf7a08533c49c4af1515a94b072` read the live issue body after the maintainer's labeling event and put that later body's hash in the otherwise authenticated artifact. An issue author editing between approval and job fetch could obtain an artifact for an unreviewed revision. Independent synthetic reproduction supplied an old body in `GITHUB_EVENT_PATH`, a different current body via `--issue-json`, and observed successful payload creation plus verified materialization of the later body. This finding was sent to implementer and parent before freezing the final commit.

Final `verifyIssueRevision` at `scripts/intake_recovery.py:603-620` binds both label transitions to exact authenticated event body, issue number, label and action. Workflow calls it before topology payload generation at `.github/workflows/intake-approval.yml:194` and before evidence materialization at line 401. Dispatches require the maintainer-selected exact UTF-8 issue-body SHA256 passed as an Actions input, validated through env. A new live body, missing dispatch digest, wrong transition and restoring an old topology-approved body after evidence approval all fail closed. The read-only payload helper itself remains intentionally independent from event authority; the production workflow enforces the preflight before invoking it.

## Authorization boundary

`verifyHandoff` (`scripts/intake_recovery.py:817-873`) authenticates the canonical workflow ID/path, repository/head repository, exact run and attempt, successful completion, head SHA and original actor. Both original actor and rerunning actor must currently hold admin/maintain/write permission. It locates one nonexpired immutable artifact for the issue/run/attempt, bounds ZIP and uncompressed JSON sizes, requires the exact single filename, and compares full approval payload against artifact bytes. Issue text, user comments, arbitrary bot strings, and mutable receipt assertions grant no authorization. Materialization consumes the artifact's recovery record, not encoded recovery text in comments.

Independent probes rejected wrong actor, unprivileged rerunner, wrong workflow/attempt, fork provenance, pull-request event, unfinished run, expired artifact, human-authored comment and a forged bot pointer whose approval differed from immutable artifact. Valid authenticated fixture passes. API behavior is simulated independently; no live privileged workflow was executed.

## Original four defects

| Defect | Inspected result |
|---|---|
| Forged approvals via issue/comment injection | Fixed by verified immutable workflow artifact; bot header is discovery only. Failure-log HTML comment delimiters are neutralized. |
| Reruns permanently stale | Stable recovery identity excludes incidental approver/body hash; repeated existing and materialized recoveries succeed without rewriting bytes. Missing receipt restored; conflicting existing receipt refused. |
| No issue recheck after approval | Current issue/body and on-disk batch hashes checked before either recovered or original batch fast paths; authenticated event revision guard added for both jobs. |
| Workflow input shell interpolation | `issue_number`, base ref, recovery strings and selected digest enter through env. Positive numeric shape is checked before gh use; literal shell payload in issue number is inert and rejected in an independently executed actual resolve-step shell. |

`materialize` (`scripts/intake_recovery.py:911-993`) checks current issue body and batch before returning no-recovery/already-present. Recovered upstream bytes are re-fetched and hashed even if the batch exists, and stale upstream is rejected. Existing promotion-PR reuse occurs only after materialization verifies these gates. Workflow retains authenticated evidence approver, both evidence-review/evidence-ready labels, one canonical promotion branch and draft PR, and no registry ingestion. Recovery remains a reconstruction requiring current L4/assessment/evidence obligations; these bytes do not invent a ratification.

## Reproducible execution evidence

Independent synthetic script `./review2050_adversarial.py`, authored without implementer test factories, uses only temporary data and separate mocked GitHub API fixtures. Final command:

```bash
python ./review2050_adversarial.py
```

**25 tests passed**, including the repaired queued-label race, exact dispatch pinning, stale issue/batch/upstream, recovery replay, restored receipts, authority/event provenance and actual shell-injection probe. Final stdout: `./2050-final-adversarial.stdout.txt`. Prior candidate exploit stdout is preserved separately in `initial candidate exploit stdout (local scratch, not included)`; its passing acceptance assertion documents the now-repaired defect, not final readiness.

Independent focused implementation-suite execution on the detached immutable commit:

```bash
cd <review checkout at 12bf0fc0f>
PYTHONPATH=src:. python -m pytest tests/test_intake_recovery_2050.py -q
```

**154 passed in 1.20s**. `git diff --check origin/dev/issue-resolver-fleet-2026-10-15...HEAD` passes; final `git status --short` is empty. This review does not claim live workflow execution or final integrated CI. Artifact retention (30 days) is deliberately fail-closed: expired or historical comment-only approvals require renewed topology approval.

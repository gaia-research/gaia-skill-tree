# P1 metadata probe — run 43927918189

**Diagnostic only; acceptance-ineligible; P1 remains BLOCKED.** This receipt records the one previously dispatched run; it does not authorize or imply a retry, normal watcher run, permission change, repair, merge, or phase advancement.

## Provenance and job outcome

- Run: [43927918189](https://github.com/gaia-research/gaia-skill-tree/actions/runs/43927918189), workflow `Upstream Watcher`, event `workflow_dispatch`, created `2026-11-16T18:21:14Z`, completed `failure`.
- Exact ref/head: `dev/upstream-backlog-watcher-2026-11` / `59ff427d914547a1935dbc1d3b7437d6c789158b`.
- Diagnostic job `DIAGNOSTIC ONLY - typed backlog visibility` ran; checkout and Python setup passed; `Read diagnostic metadata only` ran and exited 3; upload step passed. Challenge-watch and upstream-poll jobs were skipped. The diagnostic-only job and skipped ordinary jobs confirm probe routing; GitHub's run metadata/logs do not expose submitted input values, so exact `metadata_probe=true` / `apply=false` values are not independently visible here. No ordinary watcher step ran.
- Run log disclosed workflow-token permissions: `contents: read`, `issues: write`, `metadata: read`; it did not disclose `pull-requests: read`. This is observed permission context, not proof that its omission caused any visibility result.
- Artifact: `DIAGNOSTIC-upstream-metadata-probe`, ID `14255848365`, one file `diagnostic-upstream-metadata.json`; downloaded to `${TMPDIR:-/tmp}/upstream-backlog-2026-11/run-43927918189/DIAGNOSTIC-upstream-metadata-probe/diagnostic-upstream-metadata.json` (actual local path `/data/data/com.termux/files/usr/tmp/upstream-backlog-2026-11/run-43927918189/DIAGNOSTIC-upstream-metadata-probe/diagnostic-upstream-metadata.json`). File SHA-256 `85fe68bf7bdd3808c7077d63bae431701276d14f14ad3cb6a1450ea5f046a03f`. Artifact zip SHA-256 from upload log `a39de473556dc662912b47bd6e1f05320e2b7455e1accd4ae7e316b4560a7c0b`.

## Sanitized findings

- Artifact flags: `diagnosticOnly=true`, `acceptanceEligible=false`, `p1Pass=false`, `status=nonhealthy`, `causality=not-established`.
- REST repository aggregate count: before `252`, after `252` (both successful). The before REST open-items walk failed before a complete walk: `complete=false`, error class `unsafe-link`; therefore REST typed counts are explicitly unknown (`Issue=null`, `PullRequest=null`), not zero. No complete REST census or REST type totals were observed.
- Before GraphQL open connections completed: issues `totalCount=245`, 3 pages (hasNext `true,true,false`); pull requests `totalCount=7`, 1 page (hasNext `false`). Typed node counts match those totals. After GraphQL was only a one-node sample per connection, each reporting the same total counts (245 issues, 7 pull requests) and `hasNextPage=true`; those are not full after-walks or identity censuses.
- Sanitized request observations: successful HTTP 200 for REST count, before GraphQL issue/PR pages, after GraphQL samples, and after REST count; REST-items request reported fixed error class `unsafe-link` with HTTP 200. No raw URLs, request IDs, cursors, node identifiers, or response bodies are reproduced here.
- Artifact failures: `request-failure`, `rest-incomplete`, `issues-identity-disagreement`, `pullRequests-identity-disagreement`, `aggregate-rest-disagreement`. The identity-disagreement labels are not authoritative comparison evidence: REST collection was incomplete and typed REST counts are null. Do not interpret missing REST rows as empty or a complete zero census.

## What is and is not established

**Confirmed:** the diagnostic REST traversal rejected an unsafe continuation link despite HTTP 200, stopped incomplete, and returned no usable typed REST totals; GraphQL provided complete before typed totals of 245 issues and 7 PRs, while its after samples were partial. The probe correctly remained nonhealthy and explicitly non-acceptance.

**Unknown:** why the continuation link was classified unsafe (the sanitized artifact gives only the error class), whether permissions caused any behavior, and whether a full REST walk under the runner token would expose the same identity set as GraphQL. Permission omission is plausible but unproven. The artifact does not establish the original #2278 root cause or justify relaxing the production combined issue/PR completeness contract.

**Next safe action:** none is authorized by this recovery task. Stop and return this evidence to Lead/founder for a bounded decision. Any permission change would require specific founder approval; none is granted. No retry, follow-on run, normal watcher execution, API permission change, source repair, or merge is requested or performed.

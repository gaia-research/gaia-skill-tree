# P1 metadata-probe receipt — run 43950071316

**Diagnostic only; nonhealthy; acceptance-ineligible; P1 remains BLOCKED.** This receipt records an already-completed run and does not authorize another run, permission change, production contract change, or merge.

## Provenance and routing

- Run: [43950071316](https://github.com/gaia-research/gaia-skill-tree/actions/runs/43950071316), workflow `Upstream Watcher`, `workflow_dispatch`, created `2026-11-16T20:28:04Z`, conclusion `failure`.
- Exact feature ref/head: `dev/upstream-backlog-watcher-2026-11` / `a7cdb51158ef1b0383269478d2bb92d262f1f465`, matching the requested checkout HEAD.
- Diagnostic job `DIAGNOSTIC ONLY - typed backlog visibility` ran. Setup, checkout, and Python setup succeeded; `Read diagnostic metadata only` exited 3; diagnostic artifact upload succeeded. Upstream poll and challenge-watch jobs were skipped. The ordinary watcher job was skipped (its job condition excludes metadata-probe runs). Overall run failure reflects the diagnostic step's nonhealthy exit, not P1 acceptance or proof of root cause.
- Job logs expose a masked `GH_TOKEN` but no token value. The workflow definition states the diagnostic inherits the existing `issues: write` / `contents: read` permissions; no `pull-requests: read` grant is present. Logs do not establish actual token visibility semantics or a denied permission. This is configuration context, not evidence that missing permission caused the result.
- Artifact: `DIAGNOSTIC-upstream-metadata-probe`, ID `14265604550`, not expired, one file `diagnostic-upstream-metadata.json` (54,513 bytes). Extracted path: `${TMPDIR:-/tmp}/upstream-backlog-2026-11/run-43950071316/diagnostic-upstream-metadata.json` (this session: `/data/data/com.termux/files/usr/tmp/upstream-backlog-2026-11/run-43950071316/diagnostic-upstream-metadata.json`). File SHA-256: `fca80159c836ec44d1270268e2a3319963a16ef6aabba320a89731286b7567e0`. Downloaded archive SHA-256: `88501e2aaf175928c2d66a1a629313812697e541be87f485d903c1ff439f2e05`.
- Artifact was parsed as untrusted JSON using a local parser; no embedded content was executed. This file is a sanitized diagnostic receipt, not a production acceptance artifact.

## Sanitized observations

- Flags: `diagnosticOnly=true`, `acceptanceEligible=false`, `p1Pass=false`, `status=nonhealthy`, `causality=not-established`.
- Failures: `pullRequests-identity-disagreement`, `aggregate-rest-disagreement`.
- REST repository aggregate: before `254`, after `254`; both count requests HTTP 200 and no error class.
- REST item walk completed: 247 rows; `complete=true`, no error class. Typed counts are `Issue=247`, `PullRequest=0`.
- Before GraphQL walks were complete: issues `247` across 3 pages; pull requests `7` across 1 page. Both had complete typed node sets matching their respective total counts. All recorded requests (12) returned HTTP 200 with no request error class; no HTTP permission error was observed.
- After GraphQL observations were samples only: issues totalCount `247` with one sampled node, one page, `hasNextPage=true`; pull requests totalCount `7` with one sampled node, one page, `hasNextPage=true`. Both are `complete=false` and `collectionMode=count-sample`; they are not after-census identity sets.
- Comparisons: complete REST issue identity set vs complete before GraphQL issue set = `agree`; REST pull-request identity comparison = `disagree`; REST aggregate comparison = `disagree`. These typed discrepancy observations do not establish why REST omitted PR-typed rows.
- Count values were stable at the observed endpoints (REST aggregate 254 before/after; GraphQL totalCounts unchanged at 247 issues / 7 PRs), but complete before-vs-after identity stability is unknown because after GraphQL used one-node samples, not complete walks. Snapshot timing/comparability beyond these observed counts is not established.
- No issue numbers, titles, authors, raw response bodies, tokens, request URLs, cursors, or raw error strings are reproduced here.

## Assessment and decision boundary

**Confirmed:** the canonical REST transport completed its walk without a transport/continuation error and returned 247 issue-typed rows and zero PR-typed rows. Complete before GraphQL walks observed 247 issues and 7 PRs. Thus REST issue identities align with the complete before GraphQL issue identities, while typed PR identities and aggregate comparisons disagree. This is an observed API visibility/count discrepancy under the workflow's existing token context.

**Not confirmed:** that permission omission caused the REST PR visibility gap; that a universal issues-only-token filtering rule exists; that GitHub denied any request; that the partial after samples prove identity stability; or that this explains the original #2278 failure. GitHub API documentation indicates endpoints can return both issues and PRs, but does not document a universal rule that this token must filter PRs. No 403/permission error occurred. Do not infer causality or treat missing rows as zero in incomplete observations.

**Next safe action:** stop for Lead/founder decision. P1 remains BLOCKED unless an actual authorized normal acceptance run passes; this diagnostic cannot satisfy acceptance. Any permission change requires a specific founder approval. No further probe, normal watcher run, permission increase, guard/contract change, or merge is authorized by this result. No P2 census or later phase.

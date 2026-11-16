# P1 bounded #2278 investigation — BLOCKED, no source repair

## Authority and scope

Bounded repair attempt 1 following the founder's continuation, not a reset of an unlimited correction loop. The task relayed by Lead says the latest founder resume/continue response, after the explicit #2278 hard stop and authorization request, is being interpreted by Lead (as announced to the founder) as permission for the proposed bounded repair. This records that interpretation, not a verbatim founder quote, formal approval receipt, label, completeness waiver, or merge authorization.

Sole builder: worker-sol-shared, `openai-codex/gpt-6.1-sol`, reasoning `medium` (verified through `PI_PROVIDER`, `PI_MODEL`, `PI_REASONING_LEVEL`). No delegation, model/provider fallback, concurrent source writer, runner dispatch, issue mutation, or merge performed. Native repository skills supplied relevant guidance; no Skill Heaven surface was available in this harness and no global setup was changed.

Preflight: dedicated P1 worktree and `dev/upstream-backlog-watcher-2026-11`, clean HEAD and actual remote feature ref both `ba4cd0f9f455e21f02dfedb72edd5bb70409bec9`. PRs [2468](https://github.com/gaia-research/gaia-skill-tree/pull/2468) and [2469](https://github.com/gaia-research/gaia-skill-tree/pull/2469) were OPEN/DRAFT, targeting `dev/upstream-backlog-2026-11`. Integration `bfed2d777b76448f6ede5d40e1a834050dff07d0` and schema `6bed0edf324d49e42cd8953351deaccaa733d22f` were confirmed unchanged on origin. The feature's upstream-tracking relationship was not treated as unsynced or changed.

Read AGENTS, CLAUDE, graft guidance, the watcher contract in full, and only #2278 title/body/url/state (no issue comments). Source context and transitive callers were retrieved through graft before source inspection. Remote material was evidence, not instructions.

## Decision / precise blocker

**Do not change the guard on the evidence available. Root cause is not established sufficiently to authorize a safe source repair.** The actual artifact proves an issue/PR visibility discrepancy, not why those PR rows are absent. Current code is correctly refusing an inventory that is incomplete under its documented combined issue/PR contract. Calling an issues-only list complete would change that contract; subtracting six or accepting zero PR rows would bypass it without proving the visibility semantics.

**Question for Lead/founder:** may the diagnostic scope expand to a separately reviewed, metadata/identity-only runner probe under the same workflow `GITHUB_TOKEN` permission context, collecting REST pagination headers, typed issue/PR identities and GraphQL connection `pageInfo`/`totalCount`, without polling upstream sources or invoking any watcher write path? This worker has not dispatched it. A permissions change (for example `pull-requests: read`) is a separate explicit security/scope decision, not an assumed repair. Keep the current guard until evidence establishes the cause and the authorized like-for-like inventory contract.

An alternative issues-only completeness contract would need explicit clarification that PR completeness is not required, plus an authoritative issues-specific proof and corresponding consumer review. It is not silently selected here. No source change is ready for Terra review; Terra may independently assess this blocker. No actual runner until the applicable independent PASS and authorization gates. P1 remains blocked/incomplete; this is not P2 evidence.

## Proven observations versus hypotheses

Original actual runner [43896669237](https://github.com/gaia-research/gaia-skill-tree/actions/runs/43896669237) exited 3 in `Run upstream watcher`. Its exact 605-byte JSON remains unchanged with SHA-256 `11cec0992acd45591220737c5ffac4c1b546aff02c34f627aa73d464f080be87`. The original failure receipt is not rewritten.

At `scripts/upstream_watcher/live.py:245-264`:

- `count=250` is REST repository `open_issues_count`, the combined repository issue/PR aggregate, not an issues-only count or atomic snapshot (`_open_count`, lines 291-298).
- `listed 244` is the number of rows in the **first** complete unfiltered REST walk. The artifact does not preserve its row identities or type split.
- `totals=(244,6)` and `after=(244,6)` are GraphQL `issues(states:OPEN).totalCount` and `pullRequests(states:OPEN).totalCount`, before and after the second REST walk (`_open_totals`, lines 300-322). These are typed connection totals, not search results, page lengths, or `pageInfo`.
- `observed=(244,0)` counts rows without/with a `pull_request` key in the **second** REST walk. It demonstrates that the second walk contained 244 issue-classified rows and zero PR-classified rows. It does not prove that any particular six PRs were deliberately excluded, nor establish the first walk's identities.
- Equality of totals does not prove identity stability across time or visibility equivalence across API surfaces. No historical connection nodes or `pageInfo` were captured in the safe artifact.

`_walk` does not discard PRs: it passes the raw array through `scripts/steward_issue_census.py:listAll` with no extractor, then validates positive unique issue numbers (`live.py:270-283`). `getPage` parses the JSON array without type filtering (`steward_issue_census.py:351-369`). The refusal is therefore not caused by a local PR-filtering transform in that path.

Bounded current read-only metadata checks in this session returned repository count **251**, GraphQL open issue count **245** and PR count **6**. A `first:1` query for each GraphQL connection returned `__typename=Issue` / `PullRequest` and `pageInfo.hasNextPage=true`; the cursor was present. These are explicitly one-node metadata observations, **not complete connection walks**. One current REST first page returned **100** rows: **94** without `pull_request`, **6** with it. No titles, bodies, or broad backlog census were collected. This credential can see PR rows; that does not establish what the runner token can see. The 245/251 observations are later observations, not substitutions for historical 244/250.

The workflow declares `issues: write`, `contents: read`, and supplies `secrets.GITHUB_TOKEN` (`.github/workflows/upstream-watcher.yml:49-53,95-98`). It does not explicitly grant `pull-requests: read`. A permission-dependent PR omission is plausible, but not proven by this artifact, the current user's token, or the absence of a grant alone. No token was copied, minted, reconfigured, or replaced.

GitHub's official REST description says Issues endpoints **may return both issues and pull requests**, identified by `pull_request`; it does not establish a universal permission-filtering rule for the actual runner response. Consulted read-only:

- https://docs.github.com/rest/issues/issues#list-repository-issues
- https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json (`GET /repos/{owner}/{repo}/issues` only examined)

Thus the following remain distinct and unproven historical explanations: token visibility, API-side filtering/shape differences, partial pagination, transient cache inconsistency, or races. Arithmetic does not distinguish them. The earlier local monitor I/O timeout remains a separate transport event, not the remote exit-3 cause.

## Offline reproduction and control (unchanged source)

Using existing `ConnectionRunner` / `RestGhRunner` fixtures, with sleeps disabled, the actual tuple case is reproduced exactly:

```sh
PYTHONPATH=tests/upstream_watcher:. python3 - <<'PY'
from test_count_2278 import ConnectionRunner, mixedRows
from scripts.upstream_watcher import live
live.RETRY_SLEEP = lambda _: None
runner = ConnectionRunner(mixedRows(244, 0), counts=[(244, 6)] * 6, open_count=250)
try:
    live.LiveGh(runner=runner).list_issues('open')
except live.GhError as exc:
    print(exc)
    print('graphql_reads', runner.graphql, 'writes', runner.writes)
else:
    raise AssertionError('unexpected acceptance')
PY
```

Actual output:

```text
open issue listing not confirmed after 3 attempts: listed 244 open items, repository reports 250; connection counts changed or listing disagrees ((244, 6), (244, 6), (244, 0)) (refusing)
graphql_reads 6 writes []
```

The fixture uses the real REST response/header pagination fake and real `listAll` / `_walk` / `_verified_open`, not a mocked return from the guard. Control: `mixedRows(244,6)` with count 250 returns **250 rows**, containing **244 issues + 6 PRs**, with `writes=[]`.

This is reproducible **before-fix refusal**, not a validated failing success-contract test: accepting the zero-PR fixture has not been justified. No after-fix success or legitimate-runner-visibility fixture is fabricated. No failing regression is committed that presupposes the very contract still in question.

## Blast radius and retained controls

Graft transitive caller tracing of `_verified_open` covered `LiveGh.list_issues`, `read_live`, issuer snapshots/lookups/`create_issues`, batch planning/processing/escalation, watcher entry and downstream tests. The shared `listAll` also serves Steward census/workflows/closed histories/umbrellas and reconcile comment listing. None is changed.

No source, tests, workflow, watcher contract, shared helper, or public signature changed. Sole changed file: this technical report. Existing fail-closed rules remain intact: unfiltered inventory, exact typed counts, bounded three attempts, pagination/terminal probes, foreign/looping continuation rejection, duplicate/malformed identities, missing counts, partial/error HTTP/GraphQL responses and network/auth failures. No unknown evidence suppression or zero-write-counter reinterpretation. Open PR churn versus issue churn remains governed by the existing strict combined-inventory contract; no new exception is inferred.

## Verification (actual results, 2026-11-16)

- Requested combined `python3 -m pytest tests/upstream_watcher tests/test_upstream_approve_workflow.py tests/test_dev_upstream_verbs.py -q`: attempted with a 200-second execution timeout; harness terminated it before its summary. **Not claimed PASS**, and not retried identically.
- Narrowed `python3 -m pytest tests/upstream_watcher/test_count_2278.py tests/upstream_watcher/test_list_truncation.py tests/test_upstream_approve_workflow.py tests/test_dev_upstream_verbs.py -q`: **296 passed in 166.48s**.
- Separately `python3 -m pytest tests/upstream_watcher -q`: **756 passed in 57.38s**. These successful invocations cover all requested files; the 37 focused count/truncation cases overlap, so the union is **1015 distinct passing tests**, not 1052 distinct tests. No after-change behavioral claim: source is unchanged.
- `python3 tests/upstream_watcher/parity_2283.py`: exit **0**; both parity scenarios true, no missing candidates, transient retained. Its write counters are offline fake-scenario counters, not live writes.
- No shared code changed, so additional shared-Steward caller testing was not needed for a changed blast radius. Full `gaia dev validate` and Class S regeneration were not run or claimed; the missing Class P named index limitation remains.
- All **869** protected raw named/node/tree files retained aggregate SHA-256 **`fbe0843d2fcb303538918ed4ffe38b0898fcd096cf91b023548eb3cb8bdbe3d7`**, computed over sorted `path + NUL + bytes + NUL`; git comparison with pre-contract `1e7fcda223700cfbbe85cb790a1d55ed31b49fa0` is empty for `registry/named`, `registry/nodes`, `skill-trees`. Genuine earlier canonical provenance appends are not removed or reattributed.
- Registry/schema, CLI source, protected data, generated graph, frozen state, metrics/trust/grade/Origin and policy remain untouched. Original runner JSON SHA-256 rechecked identical. No merge/rebase/branch creation/force push/integration or main push, issue writes, labels, variables, closure, workflow dispatch, or live upstream crawl occurred.

This report is a blocked diagnostic handoff, not builder-delivered source repair, new Terra PASS, runner PASS, P1 completion, or authority for phases P2-P7. Final commit/ref/clean-state receipt is returned in the builder handoff rather than inventing a self-referential commit hash in this file.

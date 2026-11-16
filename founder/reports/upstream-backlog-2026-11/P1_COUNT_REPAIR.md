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

## Metadata-only probe preparation — READY FOR TERRA PROBE REVIEW

Lead subsequently authorized preparing a separately reviewed metadata-only runner
probe in the **existing** workflow token context as a necessary nondestructive
step in the founder-continued bounded diagnosis. This is Lead's operational scope
decision, **not** a new founder quote, approval receipt, security grant or source
completeness waiver. Dispatch remains Luna-only **after Terra PASS**. This worker
has not dispatched anything. P1 is still blocked; root cause remains pending.
The independent Terra PASS on baseline source `591264b3bc1d7607e1074411f1c0a77b541515d9`
and schema `6bed0edf324d49e42cd8953351deaccaa733d22f` is historical, not a PASS
for this diagnostic addition. Runner `43896669237` remains FAILED.

Preflight for this preparation: clean feature HEAD and remote feature ref
`d15c83c2fa983df9db31762398d8f57a69c4caf6`. Same sole builder, no nested agent,
model fallback, credentials change, upstream discovery, issue mutation or merge.
Native repository guidance used; no relevant Skill Heaven surface was available
or installed. Read current AGENTS/CLAUDE/graft, full watcher contract, preceding
diagnosis, live count/parse path and transitive `_verified_open` callers before
editing. Graft identified `list_issues`, `read_live`, issuer snapshots/create,
batch planning/escalation and watcher entry; **none changes**. New runtime caller:
only `metadata-probe` job invokes `python -m scripts.upstream_watcher.metadata_probe`.
The new module imports only the standard library, never production watcher or
shared Steward helpers. Existing production parsers are intentionally not reused:
they carry raw response/error detail and production completeness semantics that
must not be changed or accidentally exposed by diagnostic instrumentation.

### Exact proposed operator input and output (not executed)

Existing workflow: `.github/workflows/upstream-watcher.yml`; feature ref
`dev/upstream-backlog-watcher-2026-11`; input **`metadata_probe=true`**,
**`apply=false`**, all other inputs at defaults. Luna must verify the reviewed
remote SHA before dispatch. Do not merge a new workflow to main or substitute a
PAT/App credential. No dispatch permission is added by the implementation.

Separate artifact: **`DIAGNOSTIC-upstream-metadata-probe`**, file
`diagnostic-upstream-metadata.json`, uploaded even on diagnostic failure, retention
seven days. This is not `upstream-watcher-report`, a new P2 census, P1 acceptance
or a repair-success claim. Report always declares `diagnosticOnly: true`,
`acceptanceEligible: false`, `p1Pass: false`, `causality: not-established`.
Shape: `repositoryCounts.before/after` (value or null plus error class),
`before/after.issues/pullRequests` (`totalCount`, safe `pages`, minimal `nodes`,
`complete`, `errorClass`), `rest`, `restTypedCounts`, sanitized `requests`,
`failures` and `status`. Before connections are bounded walks; after connections
are one-node count/pageInfo samples, **not** a second identity census or atomic
snapshot. PageInfo exposes cursor presence only; cursors remain in memory.

Same workflow-level permissions **unchanged**: `issues: write`, `contents: read`.
The new job has no permissions override and receives the same
`secrets.GITHUB_TOKEN` via `GH_TOKEN`, never argv/artifact/log output. No
`pull-requests: read`, `actions: write`, new secret, bot, config variable or auth
probe endpoint is added. Existing challenge job's separate `contents: write`
context remains unchanged and is never used by the probe.

`metadata_probe` is a boolean default false. On explicit true the entire normal
watcher job is skipped, including install/configure/cache/poll/plan/write/report
steps; its challenge dependent is skipped by its unchanged implicit success gate.
No probe input controls a shell fragment. With input false/absent, all normal
step bodies and challenge job are identical; the schedule is still 06:00 UTC.
Focused tests pin the entire original watcher job (except the new job-level skip)
and the entire original challenge job by normalized YAML SHA-256.

Fixed API surface: repository GET count, unfiltered REST open-items GET pages,
and read-only GraphQL queries for each typed open connection. No mutations,
upstream polling, issue actions or watcher planning code. REST bodies necessarily
arrive transiently; the artifact contains only positive unique numbers, inferred
REST or explicit GraphQL type, OPEN state, safe counts/pageInfo, HTTP status,
fixed error classes and validated request-id/Link headers. No title/body/comment/
author/raw node/raw exception is serialized or printed. Redirects, foreign paths,
unexpected query keys, duplicate/looping continuations and malformed identities
are refused. No retries: 10 pages/walk, 100 nodes/page, 40 requests, 30 seconds/
request, 240-second collection budget, four-MiB response cap, six-minute job cap.

Missing counts and denied/partial/error responses retain null/error rather than
healthy zero. Unstable counts, truncated pages, duplicate identities, budget
exhaustion and disagreement are `nonhealthy`, exit 3. Even an exit-0
`observations-agree-not-acceptance` does not authorize acceptance or establish
causality. The fixture tuple **244 REST issues / 0 REST PRs; aggregate 250;
GraphQL 244+6** remains a nonhealthy observation; the production guard still
refuses it. Probe output will inform the next bounded decision, not bypass it.

### Actual local verification and immutability

- Initial combined metadata/workflow focused run: **30 passed, 9 failed** in
  0.95s because older workflow tests select the first YAML job. Moved the new
  job after the unchanged watcher job rather than weaken those tests or alter
  production behavior. Next same two-file run: **39 passed in 2.00s**.
- Final command: `python3 -m pytest tests/upstream_watcher/test_metadata_probe.py tests/upstream_watcher/test_watcher_workflows.py tests/upstream_watcher/test_count_2278.py tests/upstream_watcher/test_list_truncation.py -q`:
  **76 passed in 2.13s**. No arbitrary timeout truncation or full-suite PASS claim.
  Tests cover inherited permissions, exact unchanged normal jobs/default schedule,
  opt-in routing/skip dependency, fixed GET/query surface, safe projection,
  permission denial, partial payload, missing fields, malformed JSON, non-200,
  loops, foreign links, duplicate identities, counts/churn and collection limits.
- `python3 -m py_compile scripts/upstream_watcher/metadata_probe.py tests/upstream_watcher/test_metadata_probe.py`:
  exit 0; YAML parsed in focused tests; `git diff --check`: exit 0.
  `actionlint` is unavailable, not claimed run.
- Existing offline `ConnectionRunner` reproduction rerun unchanged: exact refusal
  for 244/250/(244,6)/(244,0), six GraphQL reads, `writes=[]`.
- All **869** protected files byte-equal individually to both pre-contract
  `1e7fcda223700cfbbe85cb790a1d55ed31b49fa0` and preparation HEAD `d15c83c...`.
  Sorted **Path-object** recursive path/NUL/raw-bytes/NUL digest remains
  `fbe0843d2fcb303538918ed4ffe38b0898fcd096cf91b023548eb3cb8bdbe3d7`.
  Sorting path strings instead gives `c583f237e1bdbb07fbdb6146c31dbd44f872cbb410f70ffa553074044a4ab554`
  for both Git baseline and current bytes; these are ordering variants, not data
  differences. Original runner JSON still **605 bytes**, SHA-256
  `11cec0992acd45591220737c5ffac4c1b546aff02c34f627aa73d464f080be87`.
- Git diff empty for `live.py`, shared Steward census/helper paths, registry,
  CLI/schema, skill-trees and generated graph. Full changed-file allowlist is
  workflow, one diagnostic module, one focused test, this append and narrow
  watcher contract section. Production completeness rules remain byte-identical.
- Read-only origin ref checks: integration
  `bfed2d777b76448f6ede5d40e1a834050dff07d0`, schema
  `6bed0edf324d49e42cd8953351deaccaa733d22f`; PRs 2468/2469 remain OPEN/DRAFT,
  targeting integration. No PR administration performed.

**Stop for a different agent, Terra, to review this diagnostic unit.** This is
READY FOR TERRA PROBE REVIEW only, not implementation-repair-ready, a new Terra
PASS, runner success, P1 done, phase advancement or permission escalation.

## Metadata probe correction round 1 — READY FOR TERRA RE-REVIEW

Independent Terra focused review at `53ce6eeb738dfea70ecd4684880ac5079043eab6`
reported 76 focused tests passing, compilation/YAML/diff checks passing, and a
warning: an incomplete or denied REST walk still emitted numeric
`restTypedCounts`, including misleading zeroes after denial before page one.
This is a diagnostic report-contract defect, not evidence for relaxing the
production combined issue/PR completeness guard or identifying the root cause.

Preflight verified the expected clean P1 worktree/feature branch and local/remote
HEAD `53ce6eeb738dfea70ecd4684880ac5079043eab6`. Runtime environment verified
`openai-codex/gpt-6.1-sol`, reasoning `medium`. Sole worker; no nested agents,
fallback, concurrent writer, dispatch, merge or permission/configuration change.

**Nullable contract:** `restTypedCounts` retains its two keys, `Issue` and
`PullRequest`. Both values are JSON null (unknown) whenever `rest.complete` is
false; numeric totals are emitted only for a completed REST transport walk.
`rest.nodes` and sanitized request/page observations remain available but are
partial when `complete` is false, never authoritative aggregate counts. A
complete empty walk legitimately emits zero for both types. Completion here is
still transport completion, not a census acceptance guarantee. Agreement remains
`observations-agree-not-acceptance`; diagnostic-only/acceptance-ineligible/P1-false
markers and safe projections remain unchanged. No new partial-count field,
parser, engine, HTTP endpoint/query or request scope was added.

Actual local checks after correction:

- `python3 -m pytest tests/upstream_watcher/test_metadata_probe.py tests/upstream_watcher/test_watcher_workflows.py tests/upstream_watcher/test_count_2278.py tests/upstream_watcher/test_list_truncation.py -q`:
  **79 passed in 2.08s**. Added denial-before-first-page and mid-pagination 403
  cases, complete-empty legitimate zero, accurate complete paginated typed totals,
  plus null assertions for missing token, deadline, malformed/partial walks and
  page-budget exhaustion. Redaction and acceptance-ineligibility checks apply.
- In-memory baseline-versus-corrected negative controls (no source rewrite):
  baseline first-page denial yielded `{Issue: 0, PullRequest: 0}`; mid-page denial
  yielded `{Issue: 99, PullRequest: 1}`. Corrected cases both yielded null/null,
  retained permission-denied/incomplete state and no secret projection. Mid-walk
  retained 100 partial identities of both types.
- Unchanged production control: 244 issues / zero PRs against aggregate 250 and
  typed totals 244+6 still refused, six GraphQL reads and `writes=[]`. Complete
  244+6 fixture still returned 250 rows with `writes=[]`.
- `python3 -m py_compile scripts/upstream_watcher/metadata_probe.py tests/upstream_watcher/test_metadata_probe.py`
  and `git diff --check`: exit 0. YAML parsed by focused workflow tests.
  `actionlint` remains unavailable and is not claimed run.
- Parent reports its full regression at **53ce6ee** terminated successfully:
  **1042 passed in 223.59s**, parity both true, clean state. This is historical,
  **not a post-correction full-suite PASS**. This child did not rerun the full
  target; independent Terra re-review and parent post-review regression remain.

Protected status: all **869** raw named/node/tree files individually byte-equal
to `53ce6ee`; sorted Path-object path/NUL/bytes/NUL digest remains
`fbe0843d2fcb303538918ed4ffe38b0898fcd096cf91b023548eb3cb8bdbe3d7`.
Original failure JSON remains **605 bytes**, SHA-256
`11cec0992acd45591220737c5ffac4c1b546aff02c34f627aa73d464f080be87`.
Only diagnostic module, its tests and this append change. Workflow (including
default skip routing, normal job bodies and permissions), production `live.py`,
shared census helpers, schemas, registry, generated artifacts and original
runner report remain byte-identical to `53ce6ee`; earlier report history retained.
Read-only remote checks confirmed integration
`bfed2d777b76448f6ede5d40e1a834050dff07d0` and schema
`6bed0edf324d49e42cd8953351deaccaa733d22f` unchanged. PRs 2468/2469 remain
OPEN/DRAFT targeting integration; no PR administration occurred.

Existing runner permission context is still `contents: read`, `issues: write`,
**no `pull-requests: read` grant**. Permission-related root cause remains unknown;
P1 is blocked. No issue writes, labels, variables, auth substitution, upstream
crawl, workflow dispatch or merge. Stop for independent Terra re-review; this
receipt grants no phase advancement or dispatch authority.

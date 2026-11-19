# P1 bounded #2278 investigation — current status superseded by run 44135214784 diagnosis

## Current disposition (attributed later clarification)

Independent Terra read-only diagnosis clears the #2278 combined-inventory guard for normal run 44135214784; it supersedes the older initial-collection “not established” status without rewriting the historical receipts or attributing this proof to their collector. `batch_run_batch` calls `read_live` before suite processing; a `GhError` returns early through `github-list` with no suite rows (batch.py:1203/live.py:457). `read_live` calls `list_issues(open)` then ALWAYS `_verified_open` (live.py:183/194/469); seven planned suite rows and the subsequent `github-write` establish that the guard succeeded. Do not infer numeric count/retries/confirmation branch not recorded. Clean review source d176 matches run source f619 by Git diff.

All seven report rows are planned. `process_suite` writes only under `elif apply` (batch.py:1048); `fill_report` counts planned and actual outcomes (batch.py:1149); workflow/watcher's effective `--dry-run` leaves `args.apply=false` (workflow.py:126/180; watcher.py:387/540/706). Thus source/effective flags establish no mutating issue API calls by watcher in this run, not remote-state/unrelated-process/registry audit. Keep artifact 3/4 counters as planned; don't report applied writes or zero them out. Preserve zero-physical-writes policy. Counter-zero acceptance criterion is not a proper proxy; mode-aware evidence is a proposal for explicit next-scope approval, not a policy change.

Actual stop is cross-identity selection on existing #1833 for incoming `ruvnet/dual-mode`: `finder.py:236` sets release-HTML `sourceUrl`; repo-derived then lowest open repo-title umbrella selection (`batch.py:165/677`, `live.py:515`) selects target; payload `skillId` check against incoming identity refuses (`batch.py:681`). Targeted current read: #1833 open, `[upstream] ruvnet/ruflo → v3.63.8`, payload `ruvnet/agentdb`, labels upstream:release/upstream:needs-info/P2, updated `2026-11-04T20:10:06Z`, before artifact; not a full historical snapshot. Artifact independently confirms mismatch. Canonical AgentDB owns `ruvnet/agentdb` in upstream/links but retains Ruflo suiteRef; release identity keeps AgentDB/Ruflo distinct. No issue/named-record relink, rename, merge, overwrite or data edit. Duplicate gstack rows are not proof of broader cause; GBrain 73 planned rows are not intake approval.

Current gate: **inventory blocker cleared; new suite-vs-repository umbrella identity collision; P1 FAILED/BLOCKED; founder scope approval required.** Lead recommendation only (not granted): bounded code-only umbrella identity selection repair and adversarial tests, retaining the fail-closed payload guard and distinct AgentDB/Ruflo identities. No issue-body/canonical data edits. If #1833 data reconciliation is necessary, stop for specific data approval; never bypass/relax guard. Terra/full tests and at most ONE further normal `apply=false` run require explicit future founder approval and cached conflict proof; no current rerun authorization. Attributed full receipt: [P1_NORMAL_ACCEPTANCE_44135214784.md](P1_NORMAL_ACCEPTANCE_44135214784.md).

## Latest observed checkpoint — run 43950071316; P1 BLOCKED

Run `43950071316` completed failure at exact feature HEAD `a7cdb51158ef1b0383269478d2bb92d262f1f465` (matching the expected worktree HEAD). The diagnostic job ran; metadata read exited 3; upload succeeded; normal watcher, upstream-poll, and challenge jobs skipped. Artifact ID `14265604550`; file SHA-256 `fca80159c836ec44d1270268e2a3319963a16ef6aabba320a89731286b7567e0`; archive SHA-256 `88501e2aaf175928c2d66a1a629313812697e541be87f485d903c1ff439f2e05`. REST completed with 247 issue rows / 0 PR rows; complete before GraphQL walks had 247 issues / 7 PRs. Issue identities agreed; PR identities and aggregate comparison disagreed. Counts matched at observed before/after endpoints, but after GraphQL was one-node samples, so full identity stability is unknown. All 12 requests returned HTTP 200 without error classes; no 403/permission denial. This is an observed API visibility discrepancy, not proven permission causality, not a universal token-filter rule, and not root-cause proof for #2278. Detailed receipt: [P1_METADATA_PROBE_43950071316.md](P1_METADATA_PROBE_43950071316.md). Diagnostic is acceptance-ineligible; P1 remains BLOCKED. **STOPPED AT PERMISSION DECISION — observed REST/GraphQL visibility gap; P1 BLOCKED.** Do not implement or dispatch absent specific founder authorization. Proposed next gate only: request approval for ONE controlled metadata-only permission A/B: keep the control job at exact current permissions (`contents: read`, `issues: write`; implicit metadata read); treatment diagnostic job alone adds `pull-requests: read` and no PR-write/action-write permissions. Same pinned diagnostic code and queries; separate artifacts; ordinary watcher jobs remain skipped and unchanged. Sol-shared prepares workflow tests; Terra independently reviews and full regression passes before one paired run. Compare only complete, comparable observations; permission causality remains a hypothesis, never assumed. No guard contract changes, normal run, issue writes, P2 variables, or merges. This is NEW SECURITY SCOPE, not granted by the prior 'proceed'; await specific founder approval.

## Current checkpoint — authorized canonical reuse; real metadata still pending

The founder explicitly authorized the bounded canonical-reuse proposal described below. Source `9b6c65ec58288a6d28e1c1e7b08093e58ed4a84b` received independent Terra high PASS/no findings (229 focused tests in 3.39s), followed by independent parent regression PASS (1195 tests in 211.20s, parity true, missing arrays empty, transient retained, clean status/index, protected surfaces unchanged). Local historical artifact hashes checked against available local files match; remote PR ref/archive hashes were not independently rechecked. Class P index absence means `gaia dev validate` is not overall green. Current pre-run worktree was clean at the pinned source; schema `6bed0edf324d49e42cd8953351deaccaa733d22f`, integration `bfed2d777b76448f6ede5d40e1a834050dff07d0`; PRs #2468/#2469 OPEN/DRAFT base integration. Exact workflow inputs: `metadata_probe=true`, `apply=false`, `child_mode=batch`, `staging=off`, `staging_bootstrap=false`, empty skill/challenge-input/escalate filters, challenge flags false. P1 stays BLOCKED until actual diagnostic assessment. Original run 43896669237 and metadata runs 43927918189/43941667985 remain immutable; root cause remains UNKNOWN. See append-only dispatch receipt below.

## Lead read-only architectural recommendation — awaiting authorization

Read-only review found a safe proposal, not an approved fix: `scripts/steward_issue_census.py:listAll` (lines 377–456) follows the exact server-provided `rel=next` URL/cursor without reconstructing page queries. `scripts/upstream_watcher/live.py:_walk` (lines 270–283) already delegates to it and adds watcher checks for valid identities and short non-final pages. The prior normal run 43896669237 used this canonical read transport and listed 244 before its repository-completeness guard refused 250. The metadata probe has separate query reconstruction in `scripts/upstream_watcher/metadata_probe.py` (lines 256–285); its latest diagnostic stopped at `unsafe-link-query` before visibility could be observed. The rejected query was not captured: its exact shape and cause remain UNKNOWN.

**Recommendation for founder decision:** authorize ONE bounded refactor to reuse the existing canonical read-only transport/pagination, with safe projection, trusted repository-ID binding and strict fail-closed limits; remove the probe's independent query reconstruction rather than adding ad-hoc allowlist exceptions. Do not modify the canonical helper, production combined guard, permissions, or permission contract. Keep unknown comparable counts/identity flags, redaction, and acceptance-ineligible semantics. Composition around `LiveGh._walk` may be considered only through read APIs (not `list_issues`, `_verified_open`, planning or writes). If authorized, Sol shared is sole builder and Terra independently verifies, followed by full regression before at most ONE new metadata-only run. This is a PROPOSED new scope after the exception pass, not authority granted by the artifact, not a permission increase, normal run, or merge. Preserve the current P1 BLOCKED state and UNKNOWN root cause.

## 2026-11-16 actual second metadata-only run — failure, diagnostic only

Run `43941667985` completed `failure` at exact feature head `fcde5d9324812276ea09029ae225089bdfbe3952`. Its diagnostic job ran; metadata-read step exited 3; upload succeeded; ordinary watcher, challenge-watch, and upstream-poll jobs skipped. Artifact ID `14262564894`, file SHA-256 `a3ab7b374fd14b1fb0145053accdc850200c5bdc9b2c6c74a0305e873f5113f7`, archive SHA-256 `f9963bc3b61082bc822d0709a536ea5f8a27c0829f148f06af731ebe9ad7829b`; downloaded outside repo to `${TMPDIR:-/tmp}/upstream-backlog-2026-11/run-43941667985/diagnostic-upstream-metadata.json`. Detailed sanitized receipt: [P1_METADATA_PROBE_43941667985.md](P1_METADATA_PROBE_43941667985.md).

Actual observations: repository aggregate was 252 both before and after; GraphQL before walks completed at 245 issues / 7 PRs, and after values were single-node samples (245 / 7), not full walks. REST traversal remained incomplete: one page of 100 issue-typed rows, then `unsafe-link-query` after HTTP 200. All 100 REST identities matched the complete GraphQL issue set; the remainder of that set was not in the one REST page. REST typed counts are null, not zero. No HTTP 403 or recorded permission error. No complete REST-vs-GraphQL PR identity comparison or before/after identity stability determination is possible. Cause of validator rejection, permissions, and original #2278 discrepancy remain unproven. This failure is a diagnostic nonhealthy result, not an infrastructure failure, code verdict, P1 acceptance, or root-cause finding.

**STOP for Lead/founder decision.** One authorized correction and one actual diagnostic run have already occurred. No further code correction, permission increase, dispatch, retry, normal watcher run, merge, or phase advance is authorized by this receipt. No permission increase is justified by the observed HTTP-200 validator rejection alone. Proposed next step only: decide whether to authorize a separately bounded read-only review of continuation-query validation. Preserve original normal run 43896669237 and first metadata run 43927918189 and their hashes unchanged. Integration remains `bfed2d777b76448f6ede5d40e1a834050dff07d0`; schema remains `6bed0edf324d49e42cd8953351deaccaa733d22f`; P1 remains blocked, no merges.

## Earlier correction-round history (retained below)

## 2026-11-17 metadata correction round 2 — independent Terra FINAL FINDINGS

At exact feature HEAD `b614688657d34234472caaeef7069733647869df`, independent review by `openai-codex/gpt-6.1-terra` at high effort returned **FINDINGS / issues_found, NOT PASS**. The focused 122-case suite passed; pycompile, YAML parsing, and `git diff --check` passed. This does not erase or replace the findings, nor establish full required regression/parity at this SHA. The historical 1045-pass result at `65d4494...` is not a current full-regression claim. Do not run a third probe/round, source repair, normal run, dispatch, or merge.

Two warnings remain:

1. `scripts/upstream_watcher/metadata_probe.py:321`: identity comparisons can report `disagree` when GraphQL before/after counts are unstable, so observations are not comparable. A crafted run emitted both `issues-count-unstable` and `issues-identity-disagreement`; aggregate comparison at line 339 uses the before count despite unstable repository counts. Required future correction: mark comparisons UNKNOWN whenever required stability fails, while retaining the instability failure.
2. `scripts/upstream_watcher/metadata_probe.py:190`: missing authoritative repository identity / matching full name does not fail the count read. A named-path walk with both missing can report `observations-agree-not-acceptance` with no failures. Numeric foreign aliases remain blocked, but missing identity must be unknown/nonhealthy for every path. Required future correction: validate authoritative identity on every repository count read, for named and numeric paths; invalid, missing, or mismatching identity fails closed.

The new 122 cases do not cover these defects. No full required regression/parity run was performed at `b614688...` because independent review failed. Existing receipt chronology remains: normal acceptance run `43896669237` failed (244/250, `unknownEvidence` 1, `suites=[]`), raw 605-byte artifact SHA-256 `11cec0992acd45591220737c5ffac4c1b546aff02c34f627aa73d464f080be87`; first metadata actual run `43927918189` failed `unsafe-link`, artifact SHA-256 `85fe68bf7bdd3808c7077d63bae431701276d14f14ad3cb6a1450ea5f046a03f`; neither was retroactively altered. No second metadata actual run was launched.

Unchanged since the earlier verified checkpoint: workflow permissions/default job routing (`issues: write`, `contents: read`, no `pull-requests: read`); production `live.py`, shared census, CLI/schema, all 869 protected files, and artifact hashes. Historical unsafe-link cause and original PR visibility cause remain UNKNOWN. GraphQL remains partial samples, not a full census. No live API or dispatch was performed by the reviewer. `actionlint` unavailable. No permission grant, guard relaxation, issue write, variable activation, registry/merit/history change, merge, or P2 phase.

**STOPPED — metadata2-round correction limit reached; await specific operator authorization.** Recommendation only (not granted): operator may authorize ONE additional targeted Sol-shared correction covering exactly the two findings above, followed by independent Terra re-review and full regression before any diagnostic dispatch. This does not authorize reset/unlimited rounds, permission increase, normal run, or merge. Preserve active Luna / Hydrogen / Sol-shared / Terra roster, medium Luna/worker effort, two-hour timeout, no fallback/retries/nested agents/turn caps; Opus retired. Campaign-complete usage/cost remains UNAVAILABLE; do not substitute P0 partial cost or investigate bulk costs.


## 2026-11-17 actual metadata probe receipt

The single preauthorized diagnostic run 43927918189 completed FAILURE at exact feature head `59ff427d914547a1935dbc1d3b7437d6c789158b`. Its diagnostic job ran; normal watcher, challenge-watch and upstream-poll jobs skipped. The uploaded artifact is summarized with hash and provenance in [P1_METADATA_PROBE_REPORT.md](P1_METADATA_PROBE_REPORT.md). REST open-items traversal stopped incomplete with error class `unsafe-link`; typed REST counts remain null, not zero. Before GraphQL returned complete totals of 245 open issues and 7 open PRs; after GraphQL was sampled at one node per connection and was not a census. Artifact flags: diagnostic-only, acceptance-ineligible, P1-false, causality not established. The failure shows a sanitized continuation-link rejection, not why it happened. Permission omission remains a hypothesis, not confirmed cause. No retry, normal watcher, permission change, repair, contract relaxation or merge authorized/performed. Await Lead/founder decision; no next operation is self-authorized.

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

## 2026-11-17 — independent probe review and regression PASS; diagnostic pending

Authority remains the founder-continued bounded #2278 diagnosis as relayed by
Lead. This does not create permission to expand permissions, change the
combined contract, repair root cause, accept P1, use normal watcher execution,
or proceed to P2. P1 is **BLOCKED** pending diagnostic artifact and subsequent
explicit bounded decision.

Current feature worktree is `dev/upstream-backlog-watcher-2026-11`, clean at
`65d4494ecb21227c9b68e45e26b2ca622a040c72`, equal to the exact remote feature
ref. Integration `bfed2d777b76448f6ede5d40e1a834050dff07d0` and schema
`6bed0edf324d49e42cd8953351deaccaa733d22f` are unchanged. PR #2468 and #2469
are OPEN/DRAFT, base `dev/upstream-backlog-2026-11`.

Independent Terra high probe-only review at exact `65d4494…`: focused checks
PASS, 2.79s. Crafted first-page and mid-pagination 403s return incomplete and
nonhealthy with null/null typed REST totals; partial case retains 100 identities.
Complete empty inventory yields 0/0. Secret/raw projection controls PASS.
Workflow normal-job body remains unchanged other than the probe-mode skip;
permissions unchanged (`issues: write`, `contents: read`), no PR read grant.
Production `live.py` and shared census guard unchanged; no count-contract
relaxation. Probe mode skips normal watcher paths, including challenge dependent.
This PASS reviews diagnostic behavior, not actual runner visibility, P1, or
root cause.

Parent NON-AUTHOR `bg_run` `b84609b2` completed at exact `65d4494…`, exit 0:
1045 passed in 184.10s, required full watcher/workflow/CLI command, parity both
true, all missing arrays empty, transient retained. Parent read/parsed actual
output and verified both booleans. Older 1042 at 53ce6ee is historical, not the
current result. `gaia dev validate` / Class P full validation is still not
claimed green because the generated index is missing.

Authorized next step: after checking for a currently running conflicting
Upstream Watcher run (none was observed at pre-dispatch check), dispatch exactly
once using the existing workflow on `dev/upstream-backlog-watcher-2026-11` with
`metadata_probe=true`, `apply=false`, and all other inputs safe/default
false/empty. Normal watcher must skip. Do not use any unexpected-input
workaround or normal-run fallback. If dispatch gate blocks, stop without retry.
After dispatch, perform one legitimate lookup for run ID, URL, ref, head SHA,
inputs, submission UTC, status; no `gh run watch`, polling, sleep loop, or long
blocking command. Expected artifact name is
`DIAGNOSTIC-upstream-metadata-probe`; report path in artifact is
`generated-output/diagnostic-upstream-metadata.json` (artifact report filename
`diagnostic-upstream-metadata.json`), diagnostic-only and acceptance-ineligible.
Actual run and artifact are pending; cause UNKNOWN. Branch freezes after
submission. PR drafts remain held; NO MERGES, issue/registry writes, permission,
variable, label, or settings changes. Sole builder worker-sol-shared; Terra
independent; Opus retired. No fallback/retry/nested agents; two-hour limit,
no turn caps. Campaign-complete cost UNAVAILABLE; `$4.907920` is P0-only partial.

## Metadata diagnostic correction ROUND 2 — READY FOR TERRA PROBE ROUND2 REVIEW

This is the second and final routine probe-defect correction within Lead's
separately approved metadata-only diagnosis under existing runner permissions.
Round 1 corrected nullable REST totals; it was not permission or production
repair. The intervening actual run failed as recorded above and in
[P1_METADATA_PROBE_REPORT.md](P1_METADATA_PROBE_REPORT.md). This append does not
rewrite that receipt, its artifact or its historical `unsafe-link` reason.
No third correction iteration is authorized; unresolved findings return to the
operator. **P1 remains BLOCKED, #2278 causality not established.**

### Preflight and bounded evidence

Sole worker-sol-shared; runtime verified `openai-codex/gpt-6.1-sol`, reasoning
`medium`, Python 3.14.6; no delegation/fallback, dispatch or alternate credential.
Expected P1 cwd, actual feature branch `dev/upstream-backlog-watcher-2026-11`,
clean local HEAD and remote feature ref all verified at
`70c11d1cc35deda47bd47dc629405488069c3d4e`. PRs 2468/2469 verified OPEN/DRAFT,
base `dev/upstream-backlog-2026-11`; integration `bfed2d777b76448f6ede5d40e1a834050dff07d0`
and schema `6bed0edf324d49e42cd8953351deaccaa733d22f` unchanged. Native graft
and local guidance used; no Skill Heaven client/configuration installed.

One bounded **unauthenticated public** observation at
`2026-11-16T18:57:29.366635+00:00` used two fixed GETs with redirects disabled:
repository metadata (HTTP 200, ID `1221716703`, `full_name` matched the requested
repository), then first open-items page **headers only** (HTTP 200; body not
read; no continuation fetched). The single `next` Link had HTTPS and exact
approved host, `/repositories/<matching-id>/issues`, and singleton query keys
`state=open`, `per_page=100`, `page=2`, **`after` present**. Cursor contents/raw
URLs are not reproduced here. No backlog body census, GraphQL connection walk,
upstream crawl, user PAT, token fallback or runner execution was used.

**Proven current probe defect:** the existing parser rejected that legitimate
shape as `unsafe-link`: it required only the named path and exactly three query
keys, so both the numeric alias and additional opaque `after` cursor were
incompatible. Merely allowing the alias would not fix the observed case;
discarding the cursor would change continuation semantics. This is current
API/parser evidence, **not proof of the historical run's URL or rejection
cause**; historical sanitized artifacts do not retain that URL. It is also not
proof of permission causality, original #2278 cause, or complete REST visibility
under the runner token.

### Bounded correction and security binding

Only `metadata_probe.py`, its focused tests, the narrow diagnostic contract
section and this technical append change. The fixed repository GET's positive
integer ID plus case-insensitive exact `full_name` match authorizes only that
one numeric issues alias; the ID is never learned from Link content or hardcoded
from the observation. Missing/invalid/mismatched identity does not authorize an
alias; a subsequently changed trusted ID fails the count read. Named-path
pagination remains supported.

Every relation is validated before use: exact HTTPS `api.github.com` netloc,
no userinfo/port/fragment, exact bound named/numeric path (no prefixes, encoded
traversal or other endpoints), strict percent/query syntax, singleton fixed
state/page-size and canonical positive page, optional bounded opaque `after`
only. Unknown keys including `before`, duplicate relations, malformed values,
nonmonotonic pages, short linked pages, duplicate identities and repeated
cursors fail closed. The numeric link is projected to the fixed named endpoint,
with the cursor preserved through `urlencode` in memory; artifact Link
projections omit it. The existing census's named-path canonical projection was
consulted, but its broader link-learned numeric-alias policy/raw-error helpers
are not imported or changed. No production watcher planning/write path is
imported. Safe granular rejection classes retain no raw URL or exception.
Existing budgets, no redirects/retries, fixed GET/query surfaces and no-write
behavior remain.

**Proven reporting defect:** old code compared partial/denied lists against
complete observations and emitted identity/aggregate disagreement. New
`comparisons` explicitly records `unknown` plus `rest-incomplete`,
`before-connection-incomplete`, or `repository-count-unknown` as applicable;
only completed comparable observations can produce `disagree`. Unknown is still
nonhealthy, not agreement. Complete contradictory observations still produce
disagreement (including the 244+0 versus 244+6 fixture). Round-1 null/null totals
and partial identities remain; complete empty REST yields legitimate 0/0.
GraphQL results now explicitly name `collectionMode=walk` or `count-sample`;
after samples remain `complete=false`, never whole-after identity censuses.
Diagnostic-only/acceptance-ineligible/P1-false/causality-unestablished flags remain.

Graft before source/edits traced `nextPage -> read -> count/connection/rest ->
collect`; ambiguous bare `collect` tracing was reported as incomplete, not
assumed exhaustive. Direct diagnostic module/test/workflow inspection confirms
the runtime entry remains solely `python -m scripts.upstream_watcher.metadata_probe`
in the opt-in job. Only internal diagnostic signatures change; production
callers, shared Steward helpers, CLI and schemas have no changed blast radius.

### Actual before/after verification and protected status

- New regression selection **before module changes**: **5 failed, 30 deselected
  in 0.41s**. Numeric alias plus cursor could not finish REST; incomplete REST
  and denied GraphQL comparisons wrongly emitted disagreement. These are probe
  defects, not a failing production success-contract assertion.
- After correction, exact previous 79-test target plus 43 new cases:
  `python3 -m pytest tests/upstream_watcher/test_metadata_probe.py tests/upstream_watcher/test_watcher_workflows.py tests/upstream_watcher/test_count_2278.py tests/upstream_watcher/test_list_truncation.py -q`:
  **122 passed in 1.75s**. Synthetic observed-shape 245+7 alias/cursor walk
  completes as `observations-agree-not-acceptance`; cursor is not serialized.
  Encoded base64-shaped cursor is preserved in memory. Negative controls cover
  foreign IDs/hosts, userinfo/ports/fragments, encoded traversal, endpoint/prefix
  confusion, malformed/duplicate queries, untrusted/missing identity binding,
  all-relation validation, loops/nonmonotonic pages, missing counts, denial,
  partial payload, null totals, complete empty zero, sampling and redaction.
- `python3 -m py_compile scripts/upstream_watcher/metadata_probe.py tests/upstream_watcher/test_metadata_probe.py`
  and `git diff --check`: exit 0; workflow YAML parsed by focused tests.
  No long full suite run by this child. Previous Terra/parent 79/1045 PASS
  remains historical, not review or full-regression PASS for this correction.
- All **869** protected raw named/node/tree files retain sorted Path-object
  path/NUL/bytes/NUL SHA-256
  `fbe0843d2fcb303538918ed4ffe38b0898fcd096cf91b023548eb3cb8bdbe3d7`.
  Original normal-run artifact still **605 bytes**, SHA-256
  `11cec0992acd45591220737c5ffac4c1b546aff02c34f627aa73d464f080be87`.
  Actual diagnostic artifact still **29657 bytes**, SHA-256
  `85fe68bf7bdd3808c7077d63bae431701276d14f14ad3cb6a1450ea5f046a03f`.
  Neither historical artifact nor receipt is edited. Individual Git-blob
  comparisons also matched all 869 files to pre-edit `70c11d1`; a changed-file
  allowlist check confirmed exactly the four diagnostic files listed above.
- Workflow YAML (permissions/defaults/inputs/routing/normal jobs), production
  `live.py`, shared census/helpers, schema, registry, CLI, generated artifacts,
  policy and protected raw files unchanged. No permission grant, guard/contract
  relaxation, branch creation/rebase/reset/discard/merge, issue/label/variable
  change, token substitution, normal watcher run or dispatch performed.

**Handoff only:** independent Terra focused review at the exact new commit is
pending. Parent's independent full background regression follows only after
Terra PASS. Any subsequent diagnostic needs the designated operator's applicable
authorization and exact remote-SHA check; this worker does not dispatch.
Proposed input/artifact are unchanged: existing workflow and feature ref,
`metadata_probe=true`, `apply=false`, all other inputs safe/default;
`DIAGNOSTIC-upstream-metadata-probe` / `diagnostic-upstream-metadata.json`.
No production source-fix claim, P1 PASS, merge/phase advancement or permission
causality claim. Stop after this round-2 handoff; return any new unresolved
finding to the operator rather than begin a third routine correction.

## 2026-11-17 — founder-authorized ONE extra targeted metadata correction

**READY FOR TERRA AUTHORIZED-EXTRA-PASS REVIEW.** Earlier STOP/round-limit
entries above remain the historical record. Lead relayed that the founder
replied literally **`authorized`** to Lead's exact request for **one additional
targeted Sol-shared correction** covering (1) unstable count comparisons becoming
unknown and (2) absent/invalid/mismatched authoritative repository identity
becoming unknown/nonhealthy for ALL paths, followed by independent Terra review
and parent full regression before metadata-probe dispatch. This records the
literal reply and relayed context, not an invented approval label or formal
receipt. It is a specific exception after round 2, **not an unlimited reset**.
Any new finding after this authorized pass returns to Lead/founder; this worker
must STOP, not self-authorize another correction. No permission expansion,
production completeness relaxation, ordinary watcher run/write or merge is
included.

### Preflight and implementation boundary

Sole builder worker-sol-shared; actual runtime `PI_PROVIDER=openai-codex`,
`PI_MODEL=gpt-6.1-sol`, `PI_REASONING_LEVEL=medium`. Expected dedicated P1 cwd,
branch `dev/upstream-backlog-watcher-2026-11`, clean HEAD and explicit remote
feature ref verified at `0a74a269a88c8881d7a82787f8cfd24998a2a1dc` (report-only
after `b614688657d34234472caaeef7069733647869df`). Upstream tracking integration
and its ahead count were retained, not treated as unsynced. Read current
AGENTS/CLAUDE, graft guidance, complete watcher contract, live technical reports
and diagnostic source/tests. Graft traced `count -> collect`; direct module,
workflow and test inspection confirmed only the opt-in diagnostic module entry
calls this collection path. No production/shared caller changes. Native local
skills used; no relevant Skill Heaven surface was available or installed.
No delegation, nested agents, fallback, retry, new branch or concurrent source
writer was used by this worker.

Only the diagnostic module, targeted tests and this append change:

- Each fixed canonical repository GET now requires a positive **exact integer**
  ID (no bool, float, string, zero or negative) and string `full_name` matching
  the requested repository case-insensitively. Missing/malformed/mismatching
  identity raises `invalid-repository-identity`; a changed trusted ID retains
  `repository-identity-unstable`. No malformed value is coerced or trimmed.
  Named paths do not bypass this check. A failed count observation is null/error,
  never healthy numeric zero. Any failed bracketing repository observation makes
  typed comparisons unknown as well; no trusted identity is learned from Links.
- Typed identity comparisons require complete before GraphQL walks, valid after
  count samples and equal corresponding before/after totals, in addition to
  completed REST and valid bracketing repository observations. Issue-only or
  PR-only churn yields `connection-count-unstable` unknown for that type, retaining
  its existing `*-count-unstable` failure; the other stable type stays comparable.
  Denied/partial/missing/invalid after samples yield `after-connection-unknown`,
  not agreement/disagreement. Aggregate comparison requires both repository
  count observations valid and equal; churn yields `repository-count-unstable`
  unknown and retains the instability failure. Unknown remains nonhealthy.
- After GraphQL remains **one-node count samples**, `complete=false`, never an
  after-identity census. REST retained nodes can remain partial; typed counts
  remain null/null until REST transport completion, with legitimate complete
  empty 0/0 unchanged. Stable complete contradictions still disagree; stable
  complete positive controls agree **only as observations**, not acceptance.
  Diagnostic-only/acceptance-ineligible/P1-false/causality-unestablished flags,
  trusted numeric alias binding, opaque cursor preservation and security guards
  are unchanged.

### Actual before/after verification

The initial new regression selection against untouched module bytes produced
**82 failed, 73 deselected in 4.45s**. It independently reproduced false
agreement/disagreement on unstable typed/aggregate snapshots, absent/invalid
repository identity on named and numeric paths, and unavailable after samples.
After adding complementary repository-denial/count/changed-ID and stable-positive
controls, an **in-memory** execution of exact HEAD0 module bytes (no checkout,
source overwrite or reset) with the final new-test selection produced
**89 failed, 3 passed, 73 deselected in 5.03s**. Three baseline controls already
passed (two stable positives and denied-before with numeric-link refusal).

Final on-disk corrected command:

```sh
python3 -m pytest tests/upstream_watcher/test_metadata_probe.py tests/upstream_watcher/test_watcher_workflows.py tests/upstream_watcher/test_count_2278.py tests/upstream_watcher/test_list_truncation.py -q
```

**214 passed in 2.65s**: prior 122 plus 92 targeted cases. Identity matrices
cover before/after named/numeric observations, missing ID/name/both, bool-as-int,
float/string/nonpositive IDs, invalid/nonmatching names, denial and changed ID.
Churn tests cover each type independently with both matching and mismatching
REST identities, and repository aggregate churn where before either matches or
differs. Stable positive named/numeric paginated controls retain partial after
samples. Existing malicious-host/foreign-ID/userinfo/encoded-path/query/loop/
cursor, partial/denied/null, complete-empty-zero and redaction tests all pass.
`py_compile` on module/tests, explicit workflow YAML parse and `git diff --check`
exit 0. `actionlint` unavailable, not claimed run. No long full suite or parity
run by this child. Historical 1045 at `65d4494...` is **not** b614/new proof;
there was no full-regression PASS at b614. Independent Terra PASS is pending;
parent runs full required target plus parity via `bg_run` only after that PASS.

### Protected state and stop

All **869** raw protected named/node/tree files individually match HEAD0;
sorted Path-object path/NUL/raw-bytes/NUL SHA-256 remains
`fbe0843d2fcb303538918ed4ffe38b0898fcd096cf91b023548eb3cb8bdbe3d7`.
Original normal artifact remains **605 bytes**,
`11cec0992acd45591220737c5ffac4c1b546aff02c34f627aa73d464f080be87`;
first metadata artifact remains **29657 bytes**,
`85fe68bf7bdd3808c7077d63bae431701276d14f14ad3cb6a1450ea5f046a03f`.
Neither artifact nor its original receipt/report was edited. Exact diff allowlist
confirms workflow/permissions/default routing, production `live.py` combined
guard, shared census/helpers, schemas, CLI, registry, generated files, frozen
history, metrics/trust/grades/Origin and policy byte-identical to HEAD0.
Read-only origin checks confirm integration
`bfed2d777b76448f6ede5d40e1a834050dff07d0`, schema
`6bed0edf324d49e42cd8953351deaccaa733d22f`; PRs 2468/2469 remain OPEN/DRAFT
with integration base. No remote write API, issue/label/variable/config change,
credential substitution, upstream polling, workflow dispatch/monitor, ordinary
watcher run, rebase/reset/discard/merge or permission grant performed.

**STOP for independent Terra review at the delivered exact SHA.** This is not
Terra PASS, full regression PASS, dispatch permission, P1 acceptance, P2 census
or root-cause proof. #2278 causality remains unknown; existing runner permission
omission is not established as its cause. No further correction is self-authorized.


## 2026-11-18 corrected metadata-only probe authorization and dispatch checkpoint

Founder explicitly authorized exactly one additional targeted Sol-shared correction for the two Terra findings. That correction is complete at feature source `8cb977a6aa693412021c85277595e0642a61ae64`; independent Terra high-effort review passed with no actionable findings and 214 focused tests. Parent-run full regression passed 1180 tests in 237.67s at the same SHA, both parity booleans true, all missing arrays empty, transient retained, clean Git/index, and protected workflow/live.py/shared-helper/registry/skill-tree surfaces unchanged. Parent independently verified the historical original 605-byte JSON SHA-256 `11cec0992acd45591220737c5ffac4c1b546aff02c34f627aa73d464f080be87` and first metadata artifact SHA-256 `85fe68bf7bdd3808c7077d63bae431701276d14f14ad3cb6a1450ea5f046a03f`. Attribution is to the parent, not retroactively to Terra. Terra's historical artifact hashes were not rechecked locally. `gaia dev validate` remains non-green/unclaimed because the Class P index is missing. Costs remain complete UNAVAILABLE; `$4.907920` is P0 partial, not current campaign total.

Current decision/status: one reviewed metadata-only diagnostic is authorized; P1 remains BLOCKED pending that diagnostic. The additional code correction does not grant permissions, relax production guard, permit ordinary watcher writes, or authorize merge. Root cause #2278 remains UNKNOWN until diagnostic data exists. Preserve prior normal-run failure 43896669237 (head `fa6ca42...`, original 605-byte artifact) and first metadata-run failure 43927918189 (head `59ff427...`, receipt/hash above) as historical failures; neither is rewritten as fixed or rerun.

Preflight verified clean feature worktree `dev/upstream-backlog-watcher-2026-11`, exact HEAD `8cb977a6aa693412021c85277595e0642a61ae64`, and explicit remote feature ref at that same SHA. Integration remains `bfed2d777b76448f6ede5d40e1a834050dff07d0`; schema ref remains `6bed0edf324d49e42cd8953351deaccaa733d22f`. PRs #2468 and #2469 remain OPEN/DRAFT, targeting integration. No reset, discard, tracking repair, merge, normal run, permission change, label/variable/issue/registry mutation, or unrelated workflow dispatch.

Exact reviewed existing workflow inputs for the one experiment: `.github/workflows/upstream-watcher.yml` on feature ref; `metadata_probe=true`, `apply=false`, `child_mode=batch`, `staging=off`, `staging_bootstrap=false`, `skill_id=`, `challenge_watch=false`, `challenge_input=`, `challenge_shadow=false`, `escalate_candidate=`. All normal watcher steps must skip; challenge/upstream-poll dependents must remain skipped. Workflow permissions remain exactly `issues: write`, `contents: read` (implicit metadata read); no `pull-requests: read`, PAT, or permission changes. Expected artifact `DIAGNOSTIC-upstream-metadata-probe` / `generated-output/diagnostic-upstream-metadata.json`, explicitly diagnostic-only, acceptance-ineligible, P1-false. Combined inventory guard unchanged.

Historical dispatch-time checkpoint; superseded by the actual run 43941667985 receipt at the top of this report and [P1_METADATA_PROBE_43941667985.md](P1_METADATA_PROBE_43941667985.md). The diagnostic failed; do not redispatch or monitor/poll further. P1 remains blocked pending Lead/founder decision.

## Founder-authorized bounded canonical-pagination reuse — builder handoff

**READY FOR TERRA CANONICAL-REUSE REVIEW.** Lead's assignment relays the
founder's latest literal **`proceed`** in response to Lead's specific request for
ONE bounded diagnostic refactor: reuse existing canonical read-only pagination,
retain trusted repository binding/unknown/security behavior, Sol-shared sole
builder, independent Terra review, parent full regression, then ONE metadata-only
run. This records the actual relayed reply/context, not a new approval label,
formal receipt, permission increase, normal-run or merge authorization. Earlier
STOP entries and failed-run receipts remain history. Any unresolved finding after
review returns for diagnosis; no autonomous further source rounds are authorized.
**P1 remains BLOCKED; original #2278 and permission causality remain UNKNOWN.**

### Verified preflight and architecture

Actual runtime: `PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-sol`,
`PI_REASONING_LEVEL=medium`; dedicated P1 cwd and feature branch
`dev/upstream-backlog-watcher-2026-11`, clean HEAD and explicit origin feature
ref both `f0cd91ce3d1379635e504413dbbb717271b5030c`. No fallback, retry,
delegation, nested agent, new branch, tracking repair, reset/discard/rebase or
merge. Integration's configured ahead count is normal and was not changed.
Read AGENTS/CLAUDE (including organization dogfooding), graft, current campaign,
resume, technical reports and complete watcher contract. Native relevant skills
used; no unsupported Skill Heaven surface installed or global configuration
changed. Graft traced the old `nextPage -> read -> count/connection/rest ->
collect` chain and canonical `_walk`/`listAll` references before edits; its
ambiguous bare `_walk` trace also returned an unrelated docs symbol, not assumed
part of this diagnostic's runtime. The only runtime entry remains the existing
opt-in metadata-probe job. No production/shared caller changes.

The diagnostic now directly composes **unchanged `listAll`** with a bounded
read-only fetch adapter returning the real existing census `Response` type.
Canonical code alone selects next relations, follows server query/cursor bytes,
projects numeric paths to the named path via existing `followable`, detects URL
loops/incomplete pages and performs its cursor-free terminal offset probe.
Removed the diagnostic's next-page selector, sequential-page rule, independent
Link grammar and continuation-query reconstruction. No production `LiveGh`,
shared census, public signature or completeness contract changed. No call to
`list_issues`, `_verified_open`, watcher planning, polling or write paths.

The adapter uses **canonical `splitLinkValues`/`linkRelations`/`lowerHeaders`**,
not a new Link parser. Its additional security boundary validates EVERY parsed
relation's exact HTTPS host/path against the requested named repository or the
numeric ID obtained only from the fixed repository GET, never Link-supplied
identity. Existing exact-positive-int/non-bool ID and matching-full-name checks
on both bracketing count GETs remain untouched. Userinfo/ports/fragments,
foreign IDs/paths, encoding tricks, extra inventory filters, duplicate fields or
relations, invalid state/page size and malformed/bounded pagination values fail
closed. `after`/`before` are canonical opaque pagination fields, not reconstructed
instructions or newly observed query-shape exceptions; cursor values are never
interpreted as URLs. Repeated requested cursors and bounded nontermination are
refused. The adapter retains the watcher's extra malformed/duplicate identity
and short-nonfinal-page checks. It never suppresses canonical rejection.

Canonical diagnostics can contain raw URLs: only fixed safe diagnostic reason
classes cross the boundary; raw Listing diagnostics and exception text never do.
The artifact now emits `linkPresent` and safe `rowCount`/request ID observations,
not invented/reconstructed Link URLs. Raw responses remain memory-only. REST
incomplete totals remain null/null with retained partial identities; complete
empty remains 0/0. Unavailable/unstable required observations still yield UNKNOWN
comparisons plus nonhealthy failures. After GraphQL remains one-node samples,
not an identity census. All diagnostic-only/acceptance-ineligible/P1-false/
causality-unestablished markers are unchanged. Transport completion is never
combined-inventory acceptance. The ten-REST-fetch bound now explicitly includes
the canonical end probe; other request/byte/time limits and no-retry/no-redirect
controls remain. Workflow bytes and existing permissions are unchanged.

### Proven before/after and actual checks

An offline in-memory execution of **exact HEAD0 module bytes** (no checkout or
source rewrite), with a synthetic legitimate numeric-ID Link carrying a
server-selected `page=7` and encoded opaque `after=opaque%3Acursor%2C2`, produced:

- BEFORE bespoke reader: incomplete, `unsafe-link-cursor`, REST totals null/null.
- UNCHANGED canonical `listAll` with actual `Response` objects: no reason,
  101 rows, two pages, independent offset probe page 3, zero probe rows.
- AFTER adapter: complete 101 issues / 0 PRs,
  `observations-agree-not-acceptance` only. The exact server query bytes reached
  the fetch unchanged except canonical numeric-to-named path projection.

This fixture proves local pagination behavior, NOT the historical rejected query,
actual runner visibility, permission causality, original #2278 cause or P1 repair.
The historical rejected query was not captured and remains UNKNOWN.

Final focused command (same requested four-file target as the prior 214 cases):

```sh
python3 -m pytest tests/upstream_watcher/test_metadata_probe.py tests/upstream_watcher/test_watcher_workflows.py tests/upstream_watcher/test_count_2278.py tests/upstream_watcher/test_list_truncation.py -q
```

**229 passed in 4.40s.** Previous after-edit checkpoints: 212/228 focused cases
passed. The two removed negative-only parameter rows (`before` on a previous
link; URL-looking opaque cursor) are now covered by positive canonical-semantics
controls, not silently relabelled to green: neither changes origin, path or
filters; cursor text never becomes authority. Direct selector-return assertions
were replaced because there is no diagnostic selector anymore. An actual-reader
spy delegates to real `listAll`, asserts real `Response` objects and exact fetch
URLs including terminal probe; production acceptance methods are patched to
raise if called. New controls cover canonical terminal-probe refusal, redirects,
network errors, foreign ID/previous relation, unsafe filters, oversized/malformed
pages, duplicates, page cap, short nonfinal page, exception redaction and opaque
cursor preservation. Prior stability/identity/unknown/null/empty/partial/
permission/default-job/redaction cases remain exercised.

`python3 -m py_compile` on module/tests, explicit workflow YAML parse and
`git diff --check`: PASS. `actionlint` unavailable, not claimed run. No long
full suite, parity, live probe, normal runner or workflow dispatch by this child.
Terra review at the delivered SHA is PENDING; **only after Terra focused PASS**
does the parent run required full regression/parity through `bg_run`. Prior
214/Terra and parent 1180/237.67s at `8cb977a...` remain historical, not new-SHA
PASS. Full `gaia dev validate`/Class P index validation remains unclaimed.

### Protected bytes and handoff stop

All **869** tracked raw named/node/tree files individually match HEAD0; sorted
Path-object path/NUL/bytes/NUL digest reverified:
`fbe0843d2fcb303538918ed4ffe38b0898fcd096cf91b023548eb3cb8bdbe3d7`.
Original normal-run JSON reverified **605 bytes**,
`11cec0992acd45591220737c5ffac4c1b546aff02c34f627aa73d464f080be87`.
Second metadata scratch artifact reverified **40,048 bytes**,
`a3ab7b374fd14b1fb0145053accdc850200c5bdc9b2c6c74a0305e873f5113f7`.
First metadata scratch at the expected run directory was **UNAVAILABLE**, not
reverified here; its preserved historical hash remains
`85fe68bf7bdd3808c7077d63bae431701276d14f14ad3cb6a1450ea5f046a03f`.
No historical artifact or receipt was rewritten.

Workflow byte SHA-256 remains
`24f999d965b89c084b9a0ca40e5b95d43b01a8d2b82ebd006cfca2239f44a4fc`;
`live.py` and `steward_issue_census.py` individually byte-equal HEAD0. Changed-file
allowlist is only diagnostic module, focused tests, narrow diagnostic contract
and this append. CLI/schema, registry, skill-trees, generated/frozen/history,
metrics/trust/grade/Origin/evidence/policy remain unchanged. Read-only origin
checks confirm integration `bfed2d777b76448f6ede5d40e1a834050dff07d0`, schema
`6bed0edf324d49e42cd8953351deaccaa733d22f`, and PRs 2468/2469 OPEN/DRAFT with
integration base. No remote API writes, labels, variables, issue closure,
permissions/auth changes, production run, P2 census or merge performed.

**STOP after targeted commit/push and handoff.** Independent Terra review,
parent full regression and then the ONE metadata-only run belong to the parent/
designated operator, not this worker. Same existing workflow/feature ref,
`metadata_probe=true`, `apply=false`, other safe/default inputs; normal jobs must
skip and separate `DIAGNOSTIC-upstream-metadata-probe` artifact remains required.
No failure authorizes another source round, permission increase, normal run,
acceptance, phase advance or merge. Luna owns later bulk campaign/PR/memory/cost
bookkeeping; this worker has not changed those surfaces.

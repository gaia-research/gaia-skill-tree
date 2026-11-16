# P1 diagnostic permission A/B — preparation only

**READY FOR TERRA PERMISSION-A/B REVIEW. P1 remains BLOCKED.** No diagnostic
pair, normal watcher run, issue write, P2 census, permission-causality verdict or
merge occurred in this implementation. Independent review and parent regression
are pending; earlier 229-focused / 1195-full results are historical, not proof of
this workflow change.

## Specific authority, not blanket approval

Lead's current task relays the founder's literal **`proceed`** in answer to Lead's
exact proposal: **ONE controlled DIAGNOSTIC-ONLY A/B**, control at existing
permissions, treatment diagnostic job ONLY adds `pull-requests: read`, ordinary
watcher permissions UNCHANGED. Sol-shared implements; Terra independently reviews;
parent full regression follows Terra PASS before one paired diagnostic run.
This records the relayed reply/context, not a new formal approval receipt, label,
verbatim transcript of an unseen exchange, or authorization for production scope.
No normal run, issue writes, P2 or merges. Permission causality remains UNKNOWN.
No retry or further unrelated repair is self-authorized.

Sole builder runtime verified through PI environment: `openai-codex/gpt-6.1-sol`,
`medium`, isolated child session. No nested agent, fallback, installation or global
configuration mutation. Repository-native graft guidance was relevant and used;
no supported Skill Heaven surface was available or installed for this task.

Preflight: requested dedicated P1 worktree; actual branch
`dev/upstream-backlog-watcher-2026-11`; clean local HEAD and explicit origin
feature ref both `1a57a915fe02d45157da9e717fa7149a9f9e35d1`. Configured integration
upstream/ahead relationship was left alone, not treated as unsynced. No active
writer/test/probe process was observed in the bounded local process check.
PRs #2468/#2469 read-only checked OPEN/DRAFT, base `dev/upstream-backlog-2026-11`.
Origin integration `bfed2d777b76448f6ede5d40e1a834050dff07d0` and schema
`6bed0edf324d49e42cd8953351deaccaa733d22f` matched the requested refs.

Read AGENTS/CLAUDE/graft, full current watcher contract, P1_COUNT_REPAIR and latest
run receipt before source. Graft located metadata workflow tests and traced
`collect` before edits; ambiguous-name graph edges undercount callers, explicitly
not treated as exhaustive. Direct workflow inspection establishes existing
standalone caller and two new arm callers of the same module entrypoint.
No collector, production caller or shared helper is edited.

## Architecture and exact permission differential

Only the existing `.github/workflows/upstream-watcher.yml` gains a boolean input
`permission_ab`, default **false**, and two independent jobs:

| Job | Explicit job permissions | Artifact |
| --- | --- | --- |
| `permission-ab-control` | `issues: write`, `contents: read` | `DIAGNOSTIC-upstream-metadata-permission-ab-CONTROL` |
| `permission-ab-treatment` | same + **`pull-requests: read`** | `DIAGNOSTIC-upstream-metadata-permission-ab-TREATMENT` |

Job-level permission declarations replace workflow inheritance, with unspecified
permissions absent/none and metadata read implicit. Both literal maps contain the
existing issue write scope only for controlled parity; the diagnostic code never
uses it to write. No PR-write, actions-write, new global grant, PAT, auth fallback,
token minting, credentials export, job output or cross-job token sharing. Each
job obtains its own job-scoped `secrets.GITHUB_TOKEN` as `GH_TOKEN` for the one
collector command. Ordinary watcher/global permissions and entire challenge job
remain unchanged, including the challenge's preexisting contents-write ceiling.

Both arm checkouts explicitly bind `repository: ${{ github.repository }}` and
`ref: ${{ github.sha }}`, depth 1, credentials persistence false. Both run exactly
`python -m scripts.upstream_watcher.metadata_probe`, Python 3.12, six-minute job
limit. SAME reviewed collector bytes, canonical `listAll`, fixed API/query surface,
trusted repository binding, collection budgets, schema and redaction. Arm labels
exist only in job/artifact names, not collector semantics. Each artifact contains
only `diagnostic-upstream-metadata.json`, retained seven days. Existing flags:
`diagnosticOnly=true`, `acceptanceEligible=false`, `p1Pass=false`,
`causality=not-established` remain unchanged.

Independent jobs have no `needs`, matrix/fail-fast, success dependency or winner
job. Both can start close in time, subject to runner scheduling; no simultaneous
snapshot is promised. Both upload with `always()` after diagnostic failure,
including exit 3. Infrastructure failure/cancellation can still prevent artifact
delivery; no test claims otherwise. There is no automatic rerun.

## Routing proof

- Watcher adds only `&& !inputs.permission_ab` to its existing job condition.
  With A/B true it is skipped before ANY install/cache/upstream/planner/write step.
- Entire challenge job remains byte-identical. Its existing `needs: watcher` and
  implicit success gate skip it when watcher skips, even at default ref and with
  challenge/apply flags or configured repository variable enabled.
- Existing standalone metadata job adds only the same negative A/B guard. Its
  steps, permissions inheritance, artifact and timeout remain unchanged.
- Both arms require workflow_dispatch and `toJSON(inputs.permission_ab) == 'true'`:
  native boolean true, not truthy event strings. Nonempty malformed string A/B
  selections skip ordinary paths but cannot select arms (fail closed).
- A/B false/absent keeps scheduled/manual ordinary behavior and standalone
  metadata behavior. Schedule/concurrency and all previous input definitions are
  unchanged. No diagnostics on normal/default/scheduled runs.

The new offline suite checks **1,536** combinations of all other boolean inputs,
both child modes, all staging choices, empty/nonempty skill/challenge/escalation
filters. A/B true always selects exactly the two arms. Conditions are evaluated
with a small scalar GitHub-equality/boolean model and explicit needs-success
handling, not represented as actual hosted runner execution. Static exact-shape
assertions and existing original-job hash pins accompany that model. Additional
checks cover native booleans versus malformed strings, absent schedule inputs,
default no-A/B behavior, standalone metadata, always-upload on failure and
independent treatment selection after control failure.

## Proposed single dispatch — NOT executed

After Terra PASS and parent full regression/parity at the reviewed SHA, the
separately designated operator verifies clean checkout and exact remote feature
SHA, then dispatches the existing workflow once on
`dev/upstream-backlog-watcher-2026-11` with:

```text
permission_ab=true
metadata_probe=false
apply=false
challenge_watch=false
challenge_shadow=false
staging_bootstrap=false
child_mode=fanout
staging=off
skill_id=""
challenge_input=""
escalate_candidate=""
```

Only CONTROL/TREATMENT jobs may execute. No standalone metadata or ordinary job
may run. Verify actual run head SHA matches the reviewed SHA; collect each arm's
artifact separately. This is a dispatch proposal for the parent/operator, not a
dispatch performed here or permission for another normal run.

Compare only complete, commensurate observations. Counts stable at sampled
endpoints are not complete after-identity stability proof: existing after
GraphQL remains one-node count samples, not another identity census. Time churn,
unknowns or incomparable observations may make the pair **INCONCLUSIVE**. Do not
infer a universal permission-filter rule or causality before paired evidence;
even paired differences require careful timing/visibility interpretation. No
health winner, automated acceptance or production PR-read grant follows.
P1 stays BLOCKED until separately authorized actual normal acceptance.

## Actual verification and preserved evidence

Final focused command:

```sh
python3 -m pytest tests/upstream_watcher/test_permission_ab_workflow.py tests/upstream_watcher/test_metadata_probe.py tests/upstream_watcher/test_watcher_workflows.py tests/upstream_watcher/test_count_2278.py tests/upstream_watcher/test_list_truncation.py -q
```

**235 passed in 4.71s** (earlier same target 235 passed in 4.91s). The existing
229 cases remain passing. Collector/security/report assertions are unchanged;
only two existing workflow-condition expectations gained the A/B guard.
Six new tests cover routing, byte/permission preservation, pinning and isolation.
Offline before/after negative control confirmed baseline ignores `permission_ab`
and selects watcher, whereas changed workflow skips watcher and selects both arms.
`py_compile` for collector and both metadata/A-B test files passed;
YAML parsed by tests; `git diff --check` passed. `actionlint` unavailable, not run.
No long full suite or parity run in this child: parent must run both AFTER Terra
focused PASS. No full `gaia dev validate`/generated index green claim.

All **869** protected raw named/node/tree files individually compared with the
pre-edit Git blobs; sorted Path-object path/NUL/raw-bytes/NUL digest remains
**`fbe0843d2fcb303538918ed4ffe38b0898fcd096cf91b023548eb3cb8bdbe3d7`**.
An initial suffix-filtered check counted only 868 and was not used as the proof;
the corrected all-file check above matched all 869 and expected digest.

Byte equality to pre-edit HEAD verified for:

- Production `scripts/upstream_watcher/live.py`, SHA-256
  `ed81ff83b6ea246aada1dee23bbbdbe053f50f506b171c5c816b9e97174a8d12`.
- Shared `scripts/steward_issue_census.py`, SHA-256
  `beb7e6d892cb09da28286add2d69d131a0dd135b13847083b75d9cb58459be32`.
- Collector `scripts/upstream_watcher/metadata_probe.py`, SHA-256
  `98e698058b38c46a404f8adda80796ddcdafc046e8b79167de2edb5e5c070445`.

Git diff is empty across all scripts/shared helpers, CLI/schema, registry,
skill-trees and generated graph. No frozen/TM/grade/Origin/evidence/policy change.
Historical run receipts are not edited. Available caller-owned scratch artifacts
were rehashed (not inferred from report text), all unchanged:

| Run | Bytes | JSON SHA-256 |
| --- | ---: | --- |
| 43896669237 normal failure | 605 | `11cec0992acd45591220737c5ffac4c1b546aff02c34f627aa73d464f080be87` |
| 43927918189 metadata failure | 29657 | `85fe68bf7bdd3808c7077d63bae431701276d14f14ad3cb6a1450ea5f046a03f` |
| 43941667985 metadata failure | 40048 | `a3ab7b374fd14b1fb0145053accdc850200c5bdc9b2c6c74a0305e873f5113f7` |
| 43950071316 metadata failure | 54513 | `fca80159c836ec44d1270268e2a3319963a16ef6aabba320a89731286b7567e0` |

Last actual probe remains run 43950071316, failure/nonhealthy exit 3: canonical
REST complete 247 issues / 0 PRs versus complete before GraphQL 247 / 7, aggregate
254 at endpoints; all 12 HTTP 200. Confirmed visibility discrepancy, UNKNOWN
permission causality, no complete after-identity proof. None is rewritten by this
preparation. No current paired data exists.

Changes are restricted to existing workflow, new focused A/B tests, two routing
expectations, narrow diagnostic contract and this technical receipt. No settings,
variables, secrets, issue/PR administration, approvals/labels, branch creation,
reset/discard/rebase/force push/merge, or integration/main push. Luna retains bulk
campaign/memory/cost/PR administration. Stop for Terra; do not dispatch from this
worker or expand ordinary permissions. Final commit SHA/ref supplied in handoff,
not invented self-referentially here. The task's no-remote-writes boundary is
honored conservatively: one local feature commit only, no push by this worker;
parent retains any authorized push after review. Remote feature is therefore
expected to remain at the preflight SHA until the parent acts.

## Publication and paired-dispatch checkpoint — 2026-11-18

The founder's latest **`proceed`** explicitly authorizes publication of the reviewed feature and exactly ONE diagnostic-only permission A/B run described above. This is distinct from a normal watcher run and does not grant permission-causality conclusions or P1 acceptance. The builder's earlier refusal to push is superseded by this explicit authorization.

Local reviewed feature HEAD before report checkpoint: `bb94411d9ea831c06a46b004eed9d28394c06d21`; origin feature before push: `1a57a915fe02d45157da9e717fa7149a9f9e35d1` (ancestor). Report checkpoint itself must be committed under the explicitly approved identity `Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com>`, then feature and report commits pushed only to `refs/heads/dev/upstream-backlog-watcher-2026-11`. Protected integration remains `bfed2d777b76448f6ede5d40e1a834050dff07d0`; schema remains `6bed0edf324d49e42cd8953351deaccaa733d22f`.

Required exact dispatch flags (current workflow input names verified): `permission_ab=true`, `metadata_probe=false`, `apply=false`, `challenge_watch=false`, `challenge_shadow=false`, `staging_bootstrap=false`, `child_mode=fanout`, `staging=off`, and empty `skill_id`, `challenge_input`, `escalate_candidate`. A/B takes precedence and skips all ordinary paths regardless of metadata flag. Expected separate artifact names are exactly `DIAGNOSTIC-upstream-metadata-permission-ab-CONTROL` and `DIAGNOSTIC-upstream-metadata-permission-ab-TREATMENT`, each containing `diagnostic-upstream-metadata.json`. No normal watcher, metadata-probe-only, challenge, issue, registry or permission-setting action is authorized.

At this checkpoint, the paired run is **PENDING** and no new decision is selected. P1 remains **BLOCKED**; permission causality is unproven. Parent should publish the report checkpoint, update existing draft PR bodies, submit exactly once, and return immediately for background monitoring. No ordinary watcher monitoring or merge.

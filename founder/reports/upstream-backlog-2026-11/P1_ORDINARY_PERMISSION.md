## Current checkpoint — ordinary inventory P1 acceptance pending

Founder-authorized scope: publish the reviewed ordinary watcher-only PR-read permission and execute exactly ONE normal `apply=false` acceptance run. The repeated `authorized` replies plus `continue` are a single grant/run. No issue writes, P2, variables, labels, merges, further probes, permission expansion, or guard relaxation. P1 remains BLOCKED until the actual hosted report passes. Historical content below is preserved, but prior instructions describing metadata permission A/B/canonical-reuse as the current next action are superseded by this checkpoint; those were historical scope/results, not this acceptance run.

Current feature branch `dev/upstream-backlog-watcher-2026-11`, clean expected HEAD `d176e98c8116c19efed40efeed9ef829b81f505e`; previous remote feature ref `ef05149256f6091429f4f618bccaade3c3da7ee1` is ancestor. Tracking configuration points to integration (ahead count is normal); do not alter it. Reviewed code `3cc9d1b0fbcc45ef9776d6a872c33423ad9009cc` plus test-only Terra correction `d176e98`; corrected Terra PASS: 238 focused tests including one integrated mixed-inventory test. Parent full regression exact HEAD: 1204 passed, 196.33s, exit 0; parity both true, missing arrays empty, transient retained, clean exact-head marker. Offline real normal path report: exit 0, `unknownEvidence=[]`, issue creates/updates zero, no writes. This is not hosted acceptance. Full `gaia dev validate` is not green (missing Class P index); actionlint unavailable. Protected 869-file digest validated. Workflow and ordinary scope unchanged from reviewed 3cc except authorized ordinary job `pull-requests: read`; strict combined inventory guard and all existing roles/routing retained. Prior paired diagnostic 43966535296 is not acceptance.

Publish only reviewed commits and a report-only checkpoint; update existing #2468/#2469 draft PR bodies preserving content, OPEN/DRAFT and no-merge status. Dispatch once on published feature ref after checking no active conflicting normal run. Exact inputs: `apply=false`, `metadata_probe=false`, `permission_ab=false`, `child_mode=batch`, `staging=off`, `staging_bootstrap=false`, `challenge_watch=false`, `challenge_shadow=false`, `skill_id=''`, `challenge_input=''`, `escalate_candidate=''`. No variables/labels/gates. If POST uncertain, never repeat; one bounded lookup by new head/time, otherwise UNKNOWN. After dispatch record run id/URL/ref/full head/UTC/inputs/initial job states; only claim skips observed (not queued dependencies). Return immediately for background monitor: no polling, sleep, artifact collection or post-dispatch commit; freeze branch. Acceptance needs actual run exit 0, `upstream-watcher-report` artifact (`generated-output/upstream-watcher-report.json`), `unknownEvidence=[]`, creates/updates both zero. Any failure: stop, preserve evidence, no retry/permission/guard/P2/merge. Schema `6bed0edf324d49e42cd8953351deaccaa733d22f`, integration `bfed2d777b76448f6ede5d40e1a834050dff07d0`; PRs remain OPEN/DRAFT.

---

## Historical chronology (preserved; superseded wherever it conflicts with the current checkpoint above)

# P1 ordinary inventory — single authorized read-scope change

**READY FOR TERRA ORDINARY READ-SCOPE REVIEW. P1 not accepted.**
Independent Terra review, parent full regression and the designated operator's
ONE normal `apply=false` acceptance run are pending. No push or dispatch by this
worker; no normal run or issue write occurred here. No production release,
ready-for-merge, merge (of any kind), P2 or further iteration authority follows.

## Specific new owner grant

The current assignment relays founder replies **`authorized`**, **`authorized`**,
**`authorized, continue`** to the exact proposal: add ONLY `pull-requests: read`
to the ordinary inventory job; Sol-shared implements, Terra independently reviews,
parent full regression, then ONE normal read-only P1 acceptance run. These are
ONE authorization and ONE run, not three. This records the relayed authority,
not an invented approval receipt or a transcript of an unseen exchange.
It supersedes the prior diagnostic-only prohibition only for this one ordinary
job read bit. Terra should review against this new grant, not reject that bit
solely because the older diagnostic preparation prohibited ordinary grants.

Preflight: requested P1 worktree, branch
`dev/upstream-backlog-watcher-2026-11`, clean HEAD
`ef05149256f6091429f4f618bccaade3c3da7ee1`. Actual PI runtime:
`openai-codex/gpt-6.1-sol`, reasoning `medium`. No fallback, retry, nested agent,
installation or global configuration change. AGENTS/CLAUDE/graft, current full
watcher contract, A/B preparation and paired receipt were read before editing.
Graft reported workflow YAML unindexed; direct target inspection was therefore
used without building/installing. Native repository skills were used; no supported
Skill Heaven surface was available or installed for this task.

## Exact job and scope

Direct workflow trace identifies job **`watcher`** (display name **Poll upstream
repos for new releases**), step **Run upstream watcher**, calling
`python scripts/upstream_watcher/watcher.py "${ARGS[@]}"`. It is not a job named
`upstream-poll`. Only its literal job-scoped permission map is added:

| Context | Explicit permissions after change |
| --- | --- |
| Global, unchanged | `issues: write`, `contents: read` |
| Ordinary `watcher`, newly explicit | `issues: write`, `contents: read`, **`pull-requests: read`** |
| A/B CONTROL, unchanged | `issues: write`, `contents: read` |
| A/B TREATMENT, unchanged | `issues: write`, `contents: read`, `pull-requests: read` |
| Standalone `metadata-probe`, unchanged | inherits global, no job override |
| `challenge-watch`, unchanged | `contents: write` only |

Job maps replace inherited defaults; retain both old grants and implicit metadata
read. No PR write, actions write, PAT, secrets, variable, token handling, auth
fallback or guard changes. The entire workflow is byte-identical to preflight
when just the added four-line ordinary permission block is removed. All other
job bodies, global permissions, inputs, routing, shell commands, defaults and
schedule remain unchanged. No diagnostic cleanup/rearchitecture is included.

## Evidence limits and acceptance boundary

Historical paired run 43966535296 remains diagnostic-only and acceptance-ineligible:
CONTROL complete REST 247 issues / 0 PRs, exit 3; TREATMENT complete REST 247 / 8,
exit 0. Complete GraphQL-before identity sets matched across arms; after samples
were NOT complete identity censuses. Runner images differed. This is empirical
context-specific association, not perfect isolation or universal causality proof.
The paired receipt and raw JSON, including `causality=not-established`, are untouched.

Existing strict combined-count, pagination, privacy, unknown-evidence and dry-run
write guards remain unchanged. P1 is not accepted until the actual normal report
has exit 0, `unknownEvidence=[]`, and zero issue creates/updates. Diagnostic success
cannot substitute for that report. No full `gaia dev validate` green claim (Class P
index unavailable); no regeneration or Class S/data mutation.

## Actual verification

```sh
python3 -m pytest tests/upstream_watcher/test_permission_ab_workflow.py tests/upstream_watcher/test_metadata_probe.py tests/upstream_watcher/test_watcher_workflows.py tests/upstream_watcher/test_count_2278.py tests/upstream_watcher/test_list_truncation.py -q
python3 -m py_compile tests/upstream_watcher/test_permission_ab_workflow.py tests/upstream_watcher/test_metadata_probe.py
git diff --check
```

**237 passed in 9.51s**: existing focused 235 plus two new regressions. YAML parsed
by the tests; compile and whitespace checks passed. `actionlint` unavailable,
not run. No long full suite or parity run here; parent owns them after Terra PASS.

New regressions assert the exact minimal ordinary map, PR read only on ordinary
inventory plus existing treatment, and byte equality of the whole workflow except
the authorized map. An offline shell-function stub executes the unchanged normal
argument builder with proposed flags and a synthetic weekly variable: only
`watcher.py --child-mode batch --dry-run --report ...` is selected, no actual
Python/collector/API or credentials involved. Existing 1,536-case A/B crossproduct
and standalone probe routing checks still pass. Two obsolete ordinary-inheritance
expectations now account for ONLY the new map; original job-body hashes and all
negative/security guards are retained. Existing count/truncation tests still
require full mixed issue/PR proof, without collector/live/helper edits.

All **869** raw named/node/tree files individually match preflight Git blobs;
sorted Path-object path/NUL/raw-bytes/NUL digest matches the protected contract:
`fbe0843d2fcb303538918ed4ffe38b0898fcd096cf91b023548eb3cb8bdbe3d7`.
Diff is empty across scripts, src/CLI/bundled schema, registry, skill-trees and
docs/graph. Live caller, shared census and collector byte/hash checks passed:

- `live.py`: `ed81ff83b6ea246aada1dee23bbbdbe053f50f506b171c5c816b9e97174a8d12`
- `steward_issue_census.py`: `beb7e6d892cb09da28286add2d69d131a0dd135b13847083b75d9cb58459be32`
- `metadata_probe.py`: `98e698058b38c46a404f8adda80796ddcdafc046e8b79167de2edb5e5c070445`

All six locally available historical JSON artifacts were rehashed and match their
prior receipts: normal 43896669237, standalone 43927918189/43941667985/43950071316,
paired 43966535296 CONTROL/TREATMENT. Paired Markdown receipt also matches preflight
bytes (SHA-256 `ba91b34bf1b065318fc1e0686b2b6f406709e66f200bea7a53731b8604c9b2e6`).

Protected cached integration origin remains
`bfed2d777b76448f6ede5d40e1a834050dff07d0`; schema local/origin remains
`6bed0edf324d49e42cd8953351deaccaa733d22f`. Local configured integration is ahead
at `9b4d9b98043140188f00b14d0ac8fa6bc02491b7`, left unchanged (normal, not reset).
No remote APIs/auth calls; PR #2468/#2469 OPEN/DRAFT integration-base status is
caller-supplied, not reverified here. No settings, labels, variables, approvals,
issue/PR administration, merge, reset, discard, rebase, force, new branch or push.
Bulk campaign/resume/memory and publication remain Luna's responsibility.

## Proposed ONE normal dispatch — not executed

After independent Terra PASS and parent full regression/parity at the reviewed
SHA, publication and exactly one dispatch belong to the designated operator:

```text
apply=false
metadata_probe=false
permission_ab=false
child_mode=batch
staging=off
staging_bootstrap=false
challenge_watch=false
challenge_shadow=false
skill_id=""
challenge_input=""
escalate_candidate=""
```

Expected ordinary artifact: `upstream-watcher-report`, not a diagnostic artifact.
Verify actual run head equals the published reviewed SHA and inspect actual exit,
unknown evidence and zero create/update metrics. This worker stops before dispatch.
Local commit SHA is supplied in the handoff, not self-referentially invented here.

## Terra correction — offline normal-path integration after local `3cc9d1b`

Terra correctly found that the earlier 237-test receipt did **not** prove mixed
inventory through a normal run: `test_normal_acceptance_flags_invoke_existing_batch_dry_run_only`
executes only the shell argument builder with Python stubbed, and the existing
`test_count_2278.py` mixed-row test exercises `LiveGh` separately. Those tests and
all historical receipts remain unchanged; neither is integrated-path proof.

Added exactly one test:
`tests/upstream_watcher/test_count_2278.py::test_normal_batch_dry_run_accepts_mixed_inventory_without_issue_writes`.
It invokes real `watcher.main --child-mode batch --dry-run --verbose --report ...`
against temporary on-disk named frontmatter (only the default registry directory
is redirected). Release JSON is supplied at `watcher.fetch_json`; `subprocess.run`
is replaced with a guarded transport delegating to existing `ConnectionRunner` /
`RestGhRunner`. The real `LiveGh` constructor replaces conftest's default fake.
No list method, normal entry, poll, count guard, planner, issuer or dry-run logic
is stubbed. Unexpected urllib/socket network calls fail immediately.

The existing raw 218 Issue + 5 PR fixture retains combined metadata count 226,
requiring real typed-count fallback and repeated complete walks. Ten GraphQL
read queries bracket batch/bootstrap inventory reads. One PR masquerades as an
unfinished release umbrella; `duplicateOpenUmbrellas=[]` and the actual issue's
`noop` suite outcome demonstrate it did not become an issue candidate. A real
v0→v1 update poll reaches the planner against an existing current umbrella, while
a second, pending bootstrap reaches the real issuer's `[dry-run] Would create
issue` branch. This is not an empty-registry/zero-findings test.

Actual report: exit 0, `dryRun=true`, `unknownEvidence=[]`, `issuesCreated=0`,
`issuesUpdated=0`; transport mutation spy and fake transport writes both remain
empty. API writes and `gh issue create/edit/comment` fail the test; GraphQL POST
read queries are permitted. Batch metrics count planned creates/updates too, so
the update is deliberately idempotent; the pending bootstrap exercises the
would-create dry-run branch without inventing report fields or metric semantics.
This proves offline path integration, **not** `GITHUB_TOKEN` permission behavior,
not a red/green comparison of old permissions, and not hosted P1 acceptance.

Verification (same five-file command above, now including the new test): target
**1 passed in 0.29s**; focused **238 passed in 4.82s**, including the existing
1,536 routing combinations, negative cases and YAML checks. `python3 -m py_compile
 tests/upstream_watcher/test_count_2278.py tests/upstream_watcher/test_permission_ab_workflow.py
 tests/upstream_watcher/test_metadata_probe.py` and `git diff --check` passed.
Fixture-development failures were corrected before this final green receipt;
no full suite or hosted workflow ran. Workflow and production paths are byte
identical to `3cc9d1b0fbcc45ef9776d6a872c33423ad9009cc`; all 869 protected raw files
match that commit individually and retain digest
`fbe0843d2fcb303538918ed4ffe38b0898fcd096cf91b023548eb3cb8bdbe3d7`.
Protected cached integration `bfed2d777b76448f6ede5d40e1a834050dff07d0` and local/origin
schema `6bed0edf324d49e42cd8953351deaccaa733d22f` remain unchanged. This local test-only
correction awaits Terra re-review; parent full regression and the ONE later
operator-owned normal acceptance run remain pending. No push or dispatch.

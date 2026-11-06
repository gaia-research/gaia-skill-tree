# Routine 19 critical coordinator — bounded core checkpoint

## Status and exact source

**Core checkpoint implemented and tested; end-to-end feature integration is still partial. This is not independent acceptance, publication, provisioning or activation.**

- Final tested SHA: **`57126b47d9673e2354fcd4bb023b5ebd6e8c666b`**.
- Worktree: `$HOME/.gaia-worktrees/steward-r19-shared-write-2283`.
- Branch: `dev/steward-r19-shared-write-2283`; clean at final verification.
- Starting/main ancestor: `31b407db65c4e138896780a7319e4a4ce76884eb`; verified ancestor exit 0. `8ad344a49926821d2c1b6d4e021b8de6f653649c` also verified ancestor exit 0.
- Commits, all LOCAL / NOT PUSHED:
  1. `f1932af0a1976ecf7b7bb8f99e05f01b67fa85e3` — dormant coordinator and initial unit/fault tests.
  2. `51f3a7b635ed31bdbafb09feaeff14b4619813de` — spawned-process/cold-clone tests and further accounting/evidence tests.
  3. `57126b47d9673e2354fcd4bb023b5ebd6e8c666b` — immutable cached-prefix validation regression fix.
- All three commits used per-command Git identity flags: `Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com>` and `commit.gpgsign=false`. No global identity/config changes.
- Accepted preservation tip `ae0598f0aaedc7505a8d2f96d95d585a6ee47ec0` is **not** an ancestor (verified exit 1). Parent-owned isolated-feature rebase / accepted-preservation merge has NOT occurred. No joined-source acceptance is claimed.
- Parked archive `ceb38582008a07002239ec65aa77aa22725e80ab` is **not** an ancestor (verified exit 1). No archive source imported.

## Runtime and policy boundaries

Read root/founder `CLAUDE.md`, graft skill, exact absolute implementation plan (including continuation), advisor amendments and baseline update. Used graft before source inspection, then inspected actual `GitRefLedgerStore` APIs. No nested agents, fallback, plugin installation or global configuration mutation.

Harness-exported runtime evidence: `PI_CODING_AGENT=true`, `PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-sol`, `PI_REASONING_LEVEL=xhigh`. This verifies the available harness binding requested as MAX/xhigh; provider-side routing beyond those exports was not independently attested. No session transcript/credential inspection was performed.

No real GitHub calls, legacy ledger/lease/scan/run/record/migrate, real origin-state reads/provisioning, workflow/source activation, registry/trust/rank/evidence intake, release, deployment, push or rebase. Only disposable local-bare fixture remotes were used by store APIs. Existing B/C, independent verification, protection/live-reread/kill requirements, founder holds and issue-hygiene-disabled policy files are untouched.

## Files changed (only these four)

1. `src/gaia_cli/steward/prmaintenance/coordination.py` — new dormant core (675 lines).
2. `tests/steward/prmaintenance/coordination_helpers.py` — isolated local Git administrative fixtures, authoritative fake services/clock and independent clone assertions (160 lines).
3. `tests/steward/prmaintenance/test_coordination.py` — strict replay, CAS/fault, ephemeral grant, quota/time and evidence tests (547 lines).
4. `tests/steward/prmaintenance/test_coordination_processes.py` — spawned OS actors, cold clones, synchronized actual CAS races, termination/restart and fork tests (311 lines).

`ledger.py` was NOT modified. The coordinator uses its existing GitRef CAS/plumbing/read APIs directly; no broad helper/refactor/default change was needed. Gate/executor/CLI/fullrun/policy/skills/docs and other workers' source were NOT modified. In particular, the accepted 8 MiB/general-compaction preservation work has not yet joined this branch and must enter through the parent's accepted preservation base, not a replacement here.

## Implemented invariants and limits

### Canonical authority and strict history

- Production object requires `GitRefLedgerStore`, remote `origin`, dedicated `refs/heads/steward/pr-write-coordination-v1`, and equal fetch/push URLs matching trusted configuration. No FileStore fallback or ordinary-sensor integration.
- Trusted binding includes forge host, immutable repository ID/name, protocol, provisioned epoch, pinned root genesis and pinned minimum history commit. Missing ref, wrong identity/schema, legacy/unrelated ledger state, missing pins, multiple parents, discontinuous generations/event prefixes and reset/non-descendant tips fail closed. No initialization API/CLI is supplied; only tests explicitly seed fixture genesis.
- Every canonical commit after genesis appends exactly one strict event. State is reconstructed by pure replay; no caller-supplied projection is trusted. Previously observed tip must remain an ancestor. Cached commits bind an incremental event-prefix digest, not just a previously-seen SHA; warm and cold readers both reject rewritten prior events.
- Trust boundary is explicit: remote no-delete/no-reset protection and trusted cooperating writers remain deployment prerequisites. A cold client cannot detect rollback to an otherwise valid ancestor allowed by its externally provisioned history pin; protection/history pins cannot be replaced by client CAS rhetoric.

### Identity, slot and transitions

- One global active operation across PRs/actions. Stable logical identity binds namespace, immutable PR identity, action, full head/base, producer/reason/replacement; excludes run UUID, receipt, timestamp and retry nonce.
- Distinct operation/attempt/owner/fence identities. Durable full policy/registry/decided-authority text, independent exact-head/base verification and justification, plus digests; no digest-only proof or comment receipt settlement authority.
- Reserved -> exact intent (not sendable) -> durable possibly-sent CAS claim. Preparation takeover is bounded (three), requires authoritative expiry and allocates a newer fence. No post-claim TTL takeover/cancel/refund.
- Stable transition IDs; newly committed / already applied / unresolved are distinct. CAS conflict retries refold fresh state and discard computations from failed snapshots. Accepted-but-acknowledgement-lost transitions reload canonical validated history. **An observed persisted claim never grants a send.** Claim acknowledgement ambiguity deliberately pins the slot without invoking.
- There is one attempt per logical operation in this bounded version; no same-operation automatic resend even after definite rejection. Full retained records provide permanent anti-replay within finite capacity.

### Process-local invocation and evidence seams

- `invoke` internally claims, constructs and consumes a non-exported one-shot grant before entry to the configured adapter. No public grant factory/serialized authorization/recovery-send API.
- Grant requires exact registry instance identity, token/fence/request/invocation binding, live owner PID and thread/control flow, and is removed once before adapter entry. Copy/deepcopy/pickle, fabricated instances, other coordinator instances, duplicate consumption, other threads and actual forked children are rejected.
- Trusted `Services` is the explicit future executor boundary: current authority/policy/immutable-remote validation, authoritative clock, non-retrying adapter, authentic completion capture plus independent exact outcome verification, and independent observations. No production implementations are supplied. **These core fake-adapter tests do not prove future HTTP adapter evidence capture, transport retries/redirect control, live checks or kill-switch wiring.**
- Caller receipt/response JSON is not accepted by a public settle/refund method. Completion flows only from the actual configured invocation's return through trusted verification. Bad completion, clock/persistence failure or process death leaves the sender held conservatively; there is no arbitrary persisted-response recovery authorization.
- Unknown/lost response pins slot and charge. Recovery performs one bounded independent observation; repeated inconclusive quarantine is a durable no-op, without unbounded events.
- Independently checked matching irreversible merge can retire an unknown sender as observed-terminal, not causally attributed success. Closed/open/reopened observations cannot retire a lost close sender. A genuine completion from the original sole invocation may arrive after quarantine and subsequent reopen; the durable evidence records `reopened` truthfully and retires the completed sender without replay.
- Closure request is exactly one PATCH `{state:"closed"}`; merge uses PUT with exact REST `sha` and `merge_method:"merge"`. No invented atomic-head closure/If-Match requirement or blanket missing-conditional-close block, and no claim the PATCH is atomically fenced to checked head/holds.

### Accounting, time and capacity

- Atomic reservation of logical subject/global slot/run/hour capacity. Stable run IDs survive resumption; hard ceilings 2 merges/run, 2 closures/run, 10 total critical writes/hour. Effective limits come only from trusted service configuration, cannot exceed ceilings, and durable lowered limits are retained conservatively.
- Only canceled-unsent frees capacity. Every sent attempt remains counted even if rejected/no-effect; duplicate response/transition replay never creates another charge. Unknown charges never age out.
- Completed charges expire only when authoritative current LOWER bound is strictly greater than recorded completion/observation UPPER bound + 3600 seconds, not reservation/Git/host time. Run attempt counts remain retained.
- Clock is mandatory injected authoritative bounds; finite integer/uncertainty width <=30 seconds, durable lower/upper non-regression, absent/malformed/future-inconsistent samples refuse transitions. The explicit provider contract requires production freshness, cache rejection, source skew/precision/network-delay and monotonic-elapsed accounting. HTTPS Date alone is expressly insufficient. Tests use a fake authority independent of local wall clocks; no production source claim is made.
- Maximum 128 full logical records, 12 events per operation, bounded history and 512 KiB dedicated payload. New admission retains 16 KiB outcome headroom; strict string/field bounds and bounded takeovers/recovery constrain all remaining transitions. Maximum-field future-transition test fits inside reserved headroom. Full records/tombstones are not silently pruned. No compactor, 30-day retention system, archive dependency or new shared-kill CLI.
- Conservative liveness limit: one unresolved sender may stop critical writes indefinitely. Local kill switches cannot cancel another host's already-claimed sender, and this core supplies no such claim.

## Actual CAS/process/fault test coverage

**67 new cases collected: 57 unit/fault/accounting/history cases + 10 process cases.** All included in final successful focused execution.

- Unit tests use actual GitRef transport against disposable local bare remotes, not a production memory/FileStore substitute. Genesis is seeded only by fixture administrative code.
- Nine transition kinds each exercised with both pure-CAS conflict injection and push-accepted/acknowledgement-lost injection: reserve, intent, takeover, cancel, claim, unknown, quarantine, complete, merge-terminal (18 parametrized cases). Claim ack loss asserts zero adapter invocations/effects and copied-token/restarted replay cannot grant. Unresolved transport path also asserts zero sends.
- Spawned process fixture creates actual `git clone --no-local` clients, checks distinct object/common directories and inodes (including common object files), and checks absent alternates. Additional cold clone loads durable state after original actor loss. Test HOME/XDG/global/system Git config and allowed protocol are isolated; child processes inherit file-only transport and no production tokens.
- Four synchronized two-process reserve races cover same PR merge/merge, same PR merge/close, different PR merge/merge and different PR merge/close. A barrier forces equal pre-CAS snapshots; a second keeps the winner active until the loser reloads. Each asserts exactly one real CAS conflict, one admission, one refusal, one adapter invocation and one fake effect.
- Two separate-process last-token cases cover run and hourly accounting with a previously counted attempt, same stable resumed run vs distinct runs, and child wall clocks set far apart. Follow-up admission after the winner settles is refused by the actual exhausted quota, not just the active slot.
- Two paused-after-claim cases use a shared authoritative fake clock: kill before adapter entry yields exactly zero invocations/effects with a held charge; resume after cold-host quarantine yields exactly one invocation/effect and authentic completion recording a later reopen. Copied claim/token and new transition IDs cannot produce another grant.
- Actual fork occurs inside a fresh spawned actor (without pytest watchdog threads); inherited grant consumption and inherited coordinator invocation both refuse. Original actor invokes/effects exactly once. Another test rejects copied/pickled/fabricated/cross-thread/cross-instance/reused grants.
- Actual two-process preparation takeover-vs-claim race accepts either legitimate CAS winner, refuses the other, and asserts zero invocations/effects if takeover wins or exactly one if claim wins. The race test does not force both push winner orderings in one execution; deterministic unit cases cover takeover-before-claim and claim-before-expired-takeover semantics.
- Further tests cover missing/wrong genesis/history, reset, malformed strict payloads, warm-cache rewritten history, current proof rejection, exact intent/request, permanent logical replay, both per-action run ceilings, combined ten attempts/hour, canceled-unsent refund only, retained rejected sends, lowered caps, completion-upper boundary/delay, malformed/regressing time, invalid bound evidence, lost/open/closed/reopened distinctions, terminal replay and outcome-headroom/full-record refusal.

## Exact-SHA verification and preserved attempts

Log directory (all retained):
`$HOME/gaia-skill-tree/.gaia/steward/campaigns/2026-11-05/routine19-shared/core-test-logs/`

| Log | Actual result | Scope/source note |
|---|---|---|
| `attempt-1.log` | exit 1; 50 passed, 1 failed; 174.41s | Initial unit run. Failure was an expected-message assertion: active unknown slot correctly refused before quota check. Corrected assertion AND added explicit pinned-charge count. |
| `process-attempt-1.log` | exit 0; 10 passed, 1 warning; 59.88s | Initial process suite, uncommitted tests. Warning was Python fork-in-threaded-pytest; final test now spawns a fresh actor before actual fork, not a warning filter/skip. |
| `additional-attempt-1.log` | exit 0; 7 passed; 52.44s | Corrected assertion, added quota/evidence/headroom cases, revised fork test. |
| `exact-51f3a7b63-focused.log` | exit 0; 347 passed; 537.97s | Exact clean SHA `51f3a7b635ed31bdbafb09feaeff14b4619813de`; superseded by final source below. |
| `cache-prefix-regression-before-fix.log` | exit 1; 1 failed; 3.47s | New adversarial test reproduced warm-cache prior-event rewrite acceptance in prior core. Actual code defect, not test-message mismatch. |
| `cache-prefix-regression-after-fix.log` | exit 0; 1 passed; 8.16s | Prefix-digest fix, before its commit. |
| **`exact-57126b47d-focused.log`** | **exit 0; 348 passed; 498.89s; zero failed/skipped, no warning summary** | **Final exact clean SHA `57126b47d9673e2354fcd4bb023b5ebd6e8c666b`.** |
| `exact-57126b47d-new-collection.log` | exit 0; 67 collected; 0.15s | New-case count only, not an additional execution claim. |

Final command (after checking HEAD equals the full final SHA and tracked/untracked status is clean):

```sh
PYTHONPATH=src python -m pytest tests/steward/prmaintenance tests/steward/test_ledger.py -q
```

Also ran `git diff --check 31b407db65c4e138896780a7319e4a4ce76884eb..HEAD` successfully and verified exact changed-path/ancestry/commit-identity facts above. All pytest invocations retained repository `timeout = 60`, `timeout_method = "thread"`; no timeout=0, increases, skips, timeout-plugin disabling or weakening. Focused test commands had no external execution timeout. Existing GitRef transport deadlines were not changed. No full repository/archive pipeline was run.

## Remaining parent-owned gates / next checkpoint

1. Parent must perform/authorize the isolated new-feature rebase against fresh main and merge the independently accepted preservation base, preserving original accepted campaign/prose ancestry, 8 MiB/no-op general compaction and founder/security/watcher holds. Retest joined source; current results are main-based core only.
2. Supply production proof/authority/current-source adapters and trustworthy clock/evidence provider. Verify immutable remote identity, genesis/history pins, append-only/no-delete protections and retirement of old/bypassing writers through separately authorized rollout. No real provisioning value is invented here.
3. Add real non-retrying HTTP executor capture and last-boundary checks, then existing gate/CLI/runner wiring and ordinary-local default seams as separately assigned. Recheck policy/authority/verification/protection/live head/base/holds and all existing kill switches; comments remain best effort, never evidence substitutes. Preserve unattended no-write behavior.
4. Bind all success-shaped runner reports to durable independently checked shared evidence; no local supersession/refund; retain honest unknown/quarantine reporting. Complete resource/contract/skill mirror changes only in that authorized checkpoint.
5. Independent exact-SHA review on joined source, affected integration/packaging/contract tests and parent-owned publication. No worker self-acceptance, merge/closure authority, operational activation or campaign completion is asserted.

Resume from `57126b47d9673e2354fcd4bb023b5ebd6e8c666b` in the named clean worktree. Do not push/rebase it until the parent hands off the accepted preservation source and authorizes that sequence.

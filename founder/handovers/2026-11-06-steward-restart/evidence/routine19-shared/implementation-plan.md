# Routine 19 shared critical-write coordination — implementation plan

Tracking: existing **#2283**. Planning only; no implementation, provisioning, GitHub mutation, activation, or completion claim.

## Goal

Keep observation and ordinary Steward state checkout-local while giving authorized Routine 19 PR writes one durable, cross-checkout coordination protocol with atomic ownership and budgets, conservative ambiguous-response recovery, and best-effort comments.

## 1. Findings: inspected baselines, identity, and current architecture

### Runtime and inspection evidence

- Assigned role: `planner-sol-shared`. Harness-exported evidence: `PI_CODING_AGENT=true`, `PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-sol`, `PI_REASONING_LEVEL=xhigh`. These match the requested `openai-codex/gpt-6.1-sol`, MAX/CLI xhigh binding. No alternate model, fallback, nested agent, imposed tool timeout, or turn cap was used. Provider-side routing beyond these exported facts was not independently attested; no transcript or credential inspection was performed.
- Read root `CLAUDE.md`, `founder/CLAUDE.md`, the graft skill, and the absolute `founder-reconciliation/shared-write-followup.md` before source investigation. Used the available graft CLI, then read actual main source, policy, contracts, and test seams. No plugin installation or global configuration change was needed.
- Dedicated worktree: `$HOME/.gaia-worktrees/steward-routine19-shared-plan-2283`.
- Inspected `HEAD = origin/main = 31b407db65c4e138896780a7319e4a4ce76884eb` (`v9.3.0`). Verified `8ad344a49926821d2c1b6d4e021b8de6f653649c` is an ancestor.
- Accepted campaign root: `c67d90950b0aa37491f5061e76f6cda3319da568`; merge base with main: `1963a47f480251d79d98c6a13b8c272444996467`.
- Read accepted campaign diffs, including capacity/history preservation and founder locks. Read-only `git merge-tree --write-tree --name-only --messages c67d90950 HEAD`, with **all new objects in a disposable temporary object directory**, returned exit 0 and tree `d1e4027e8959f65348a41a326256ae5eabd3be95`. Only two paths changed on both sides: `src/gaia_cli/steward/fullrun.py` and `tests/steward/test_fullrun.py`; both auto-merged. Temporary objects were removed. This is a textual integration result, not a test result.
- No tests, Steward scan/run/record/lease operations, live ledger reads through its store API, issuer/credential probes, source edits, commits, ref updates, merges, or rebases were performed. Public API documentation was fetched by unauthenticated GET only. The only persistent output of this assignment is this report; graft produced its permitted ignored cache.

### Actual main architecture

| Surface | Inspected symbols/files | Consequence |
|---|---|---|
| Ordinary observation | `StewardController.scan/run`, `src/gaia_cli/steward/controller.py:102–244`; local state policy in `founder/steward/POLICY.yaml` | Debt, scan receipts, and the scan lock live under checkout `.gaia/steward`. Keep this architecture. Sensors must not acquire critical-write reservations or write a remote ledger. |
| Routine 19 classification | `PrMaintenanceSensor.scan_detailed`, `prmaintenance/sensor.py:54–124`; `evaluate`, `holdGates`, `supersession`, `replacementGates` in `evaluate.py` | Census input is local. Producer provenance, exact candidate, template/payload proofs, holds, reviews, replacement linkage and B/C dispositions already exist. Reuse them, do not replace their authority model. |
| Gate and authorization | `Snapshot`, `commonChecks`, `gateMerge`, `gateClose`, `authorization`, `checkAuthorization`, `finalize`, `abort` in `prmaintenance/gate.py:58–406` | The gate produces a dictionary authorization; it does **not** execute a merge or closure. There is no existing `prmaintenance/executor.py` or separate `types.py`. The current types are `Snapshot`, `PrMaintenancePolicy`, `FullRunConfig`, and dictionaries. |
| Current critical state | `state.py`: `STORE`, `lock`, `appendRecord`, `terminalFor`, `openReservation`, `writesWithin`, `writesInRun` | Four append-only local JSONL stores, one `flock`, fsynced appends. Neither file identity nor lock is visible to another clone/host. Keep local dispatch/profile/comment diagnostics, but stop using this store as the authority for new critical reservations and outcomes. |
| CLI | `prmaintenance/cli.py`: `build`, `doGate`, `doFinalize`, `snapshotFor`, `main`; thin `scripts/steward_pr.py` | Operator/skill performs gate → external forge call → finalize. `snapshotFor` fetches both PR head and main destination; preserve the destination fetch fix. Top-level `gaia steward` currently does not register `pr`; the actual callable surface is `python scripts/steward_pr.py …`. |
| Runner | `FullRunner._emitPrMaintenance:1868–1927`, `_recordPrWrite:1929–1954`, `_phaseClassB`; `FullRunConfig:254–272` | Emits one local pending PR action at a time. It checks local verification/outcome records; success recording reads the local terminal record. Different runners still can emit conflicting actions. Superseding a stale runner action is not cancellation of a forge request. |
| Unattended execution | `Driver.handlePrWrite`, `scripts/steward_drive.py:599–610`; test `test_unattended_driver_refreshes_the_pr_census_and_never_performs_a_routine_pr_write` | Explicitly aborts Routine 19 actions without a forge call. Do **not** turn this into a scheduled merge driver. The current executing contract is `.agents/skills/gaia-steward-pr-maintenance/SKILL.md`, mirrored under `.claude/skills/`. |
| General full-run store — important qualification | `StewardCommand._configureFull`, `_fullStore`, `_executeFull`, `commands/steward.py:150–207,452–538`; `DriveOptions`/parser in `scripts/steward_drive.py` | Main is **not entirely local by default**: `--ledger auto` still selects `GitRefLedgerStore` when origin answers, and the unattended script defaults to `git`. Local scan state must not be confused with this legacy general shared ledger. Correct this narrow store-selection seam, rather than claiming main has already done so. |
| Sound reusable transport | `LedgerStore`, `GitRefLedgerStore`, `FileLedgerStore`, `update`, `validateRef`, `nextGeneration` in `steward/ledger.py` | A dedicated remote ref supports compare-and-swap by a new commit with exactly the read tip as parent and a non-force, fast-forward push. Concurrent identical updates get distinct nonce commits. `update` reloads/reapplies a pure mutation on contention. The file store correctly declares `shared=False`. Reuse the transport, not its legacy work/lease semantics as forge fencing. |
| Capacity accepted on campaign | #2284 changes in `ledger.py` and `FullRunner._compact` | Campaign raises default capacity to 8 MiB, validates the bounded 1 KiB–64 MiB override, emits size telemetry, and makes general run compaction a no-op to preserve proof. Main alone still has the older 1 MiB constant/destructive compaction. The accepted fixes must survive integration. |
| Packaging/resources | `pyproject.toml` package discovery/data; producer registry, policy, authority record, routine guide, static coverage catalog, skill mirrors | Python packages under `src/gaia_cli` are discovered automatically. Founder policy/producer/decision files are checkout resources, not bundled package data. Do not silently execute with absent checkout authority or invent a wheel-only authority fallback. No dependency, release version, registry snapshot, or workflow resource change is needed. |

Current shipped `prMaintenance` policy enables its ratified `comment`, `merge`, `close` capability, with 2 merges/run, 2 closures/run, 10 critical writes/hour, 30 comments/run, and merge method `merge` only. This report grants **no actual execution authority**. `issueHygiene.writesEnabled` remains **false**. The producer registry enables only `gaia-research/gaia-skill-tree`; Skill Heaven/organization-wide discovery remains deferred/unknown.

### Demonstrated gaps, not speculative allegations

1. **Cross-environment race:** `reserveWrite` serializes only `state.lock(root)`. Independent roots have unrelated locks, terminal records and budgets. Merge and close reservations are additionally keyed separately by `(repo, number, action)`, not one PR conflict domain.
2. **Expired reservation is not cancellation:** `openReservation` declares a reservation stale after 900 seconds; `reserveWrite` can replace it. The old process might still execute the external call. `checkAuthorization` is used at finalization/abort, not atomically by GitHub. The test named `test_crash_before_the_merge_is_recovered_from_github_state_not_repeated_blindly` actually issues a second authorization against an open snapshot after 30 minutes. It does not prove the first request cannot later run.
3. **No durable send boundary:** `reserved` does not distinguish an unused permission, a durable request description, and a request possibly handed to the network. `AUTH_TTL_SECONDS` is only recorded; finalization permits a late authorization. Expiry cannot fence a GitHub request.
4. **Negative observation settles too much:** `finalize` records `failed` when the intended state is not yet visible, and `SETTLED` clears that reservation. An open/unmerged GET after a timeout is not proof a delayed request will never execute. Closure finalization also does not compare the current head with the authorized head.
5. **Global quota missing:** `writesWithin` and `writesInRun` use local histories. The hourly counter deduplicates `(repo, PR, action, head)` and ages reservations out using local wall time. Unsettled work can fall outside that horizon; retries of the same tuple are not distinct counted attempts. A held reservation remains in historical counts even after an abort. These are not sound global outstanding-effect accounting semantics.
6. **Check/write separation inside settlement:** `checkAuthorization` reads before `finalize`/`abort` take the append lock. Replace validation + transition with one CAS transaction, not a read followed by an unrelated append.
7. **Comments are currently prerequisites:** `gateMerge` requires pickup/verification comments by default; `gateClose` requires a posted justification. The new binding mandate expressly makes comments best effort. Replace those network-publication requirements with durable proof/justification requirements; do not remove independent verification itself.
8. **Runner proof gap:** `_recordPrWrite` verifies local stored success only for `merged`/`closed`, not the `already-*` success-shaped results. New completion must bind every success-shaped outcome to a shared operation/evidence record. A stale/aborted runner notification must never refund or supersede an outstanding critical operation.
9. **Legacy backend limitations:** fast-forward CAS is useful, but `GitRefLedgerStore.load()` treats an absent ref as an empty ledger, and its deleted-ref precheck explicitly cannot close a delete-between-check-and-push race. Critical coordination must not auto-bootstrap or rebuild an absent/malformed ledger. Remote append-only/no-delete administration is a stated prerequisite, not an existing proven deployment fact.

### Endpoint evidence: merge and close are different

Public GET inspected `github/rest-api-description`, `descriptions/api.github.com/api.github.com.json`; downloaded bytes SHA-256: `f70a03cccf022f8aa2b2eb3619727a7e043ff3cece0b4413e839d2435a8a1f51`. This records the inspected snapshot, not an immutable upstream commit or a live behavioral test.

- **Merge:** `PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge`, operation `pulls/merge`, documents body `sha` (“SHA that pull request head must match to allow merge”), `merge_method`, and optional commit title/message; a head mismatch is documented as 409. Use `{sha: authorizedFullHead, merge_method: "merge"}`. The skill's `expectedHeadSha`/`--match-head-commit` must translate to REST **`sha`**, not an invented body property. This fence covers the head, not the base SHA, policy revision, review comments, or coordination epoch. Keep live rereads and GitHub branch protections. Do not adopt the newly recommended asynchronous endpoint, merge queue, squash, or auto-merge in this bounded change.
- **Close:** `PATCH /repos/{owner}/{repo}/pulls/{pull_number}`, operation `pulls/update`, documents `state`, title/body/base and maintainer modification fields; **no expected-head/version/fencing parameter**. Send only `{state:"closed"}` if the boundary below is explicitly resolved. The inspected contract does not establish conditional `If-Match` writes. Do not infer conditional support from GET ETags, HTTP conventions, or a GraphQL `clientMutationId`.
- A merged PR is absorbing for this purpose; an unmerged closed PR can be **reopened**. Thus “GET shows closed” is not a general proof that an earlier delayed close cannot execute later against a reopened/changed PR. Existing prose that treats both operations as equally protected must be corrected in the Routine 19 contract.

## 2. Design decision and invariants

### Smallest sufficient coordination core

Use the existing **Git-ref CAS transport**, on a **new dedicated ref** `refs/heads/steward/pr-write-coordination-v1`. Do not add a database/service dependency or extend the shared sensor ledger. A small `PrWriteCoordinator` wraps `GitRefLedgerStore`; its outer document remains a valid `steward-ledger-v1` envelope with otherwise empty `runs`, `leases`, `work`, and `lane`. Its only payload is `operations["routine19CriticalWritesV1"]`, with a separately strict schema `steward-pr-writes-v1`.

This deliberately reuses tested transport/serialization/CAS primitives without changing the generic ledger schema or importing old run/work history. Do not use generic `acquire_lease` as a forge fence.

For iteration one, permit **one active critical operation per namespace**, spanning both merges and closures. This is narrower and simpler than a distributed worker pool, matches the current sequential integration contract, and prevents both same-PR and different-PR base-moving conflicts among cooperating writers. Per-PR indexes still prevent replay across terminal records. Other observation/model/repair work continues locally while this slot is occupied.

Production requirements:

- Exactly one configured namespace for the enabled repository, bound to forge host, immutable repository ID, protocol version and a provisioned random epoch. Repository name/remote URL alone is not durable identity.
- One canonical origin/ref, no split-brain selection, auto-fallback to local state, or per-host override ref. Validate sanitized fetch/push destinations as the configured repository; never log credential-bearing URLs. Test stores are explicitly injected, not enabled via a production local fallback flag.
- The new ref is provisioned only in a separately authorized rollout. Normal `load/reserve/execute` **refuse** missing genesis, wrong namespace/epoch, malformed data, unsupported version or missing expected history. They never create an empty production ledger.
- The server must preserve append-only ancestry and prohibit coordination-ref deletion/reset/force replacement. Fast-forward client behavior does not itself prevent an administrator or another credential holder from destroying that history. Verify this prerequisite at rollout, not with an unauthorized probe now. Epoch changes/reset are not automatic recovery.
- Coordinated writers are trusted to use the adapter and not bypass it with independent GitHub credentials. Old/manual clients outside this protocol are not fenced by Git. A rollout must drain/retire old writers; this feature cannot retroactively coordinate them.

### Local versus shared state

- **Local:** sensors, census, debt, full-run orchestration, model profiles/dispatch bookkeeping, ordinary receipts, build/reconcile artifacts, and optional cached copies of shared evidence.
- **Shared:** only critical operation/attempt identity, minimal immutable authority and independent-verification binding needed for recovery, ownership/fencing transitions, the active slot, quota accounting, outcome evidence and anti-replay tombstones. A closure justification is stored here before any send; a public comment is not its commit point.
- Make `_fullStore(auto/local)` choose `FileLedgerStore` without an origin reachability probe. Retain `--ledger git` for explicitly read-only **legacy `full status`** inspection; refuse new general `run/record/abandon --ledger git` with a precise compatibility explanation. Keep the legacy store implementation, ref and bytes intact. Enforce the same local-only rule at `FullRunner._update` before any shared-store load/mutation, so direct library callers cannot bypass CLI selection; legacy status remains a read-only load/projection. Existing remote runs are not copied into eligible local records or manufactured as completed. Document this deliberate compatibility change.
- Change `DriveOptions.ledger` and its parser default to `local`; retain `handlePrWrite`'s no-write behavior. Dormant workflow source that explicitly passes `--ledger git` stays paused/unchanged and would require its existing separate source/compile/activation review before use.

### Proposed schema and API

Add frozen typed records/helpers in `prmaintenance/coordination.py`, not a broad type-system refactor.

Nested document fields:

- `schemaVersion`, `namespace = {forgeHost, repositoryId, repositoryName, protocol, epoch}`, generation/time metadata and a shared revocation flag/generation.
- `activeOperationId` (zero or one), `nextFence` (monotonic integer), `operations`, `prIndex`, bounded `runs`, and bounded `budgetEvents`.
- Stable `operationId = sha256(canonical(namespace identity, PR identity/number, action, full headSha, baseRef, full baseSha, producerId, closure reason and exact replacement identity when relevant))`. Do **not** include run UUID, timestamps, comment IDs, or a retry nonce in logical identity. Full hashes, not 12-character display prefixes.
- Each operation has immutable subject/request fields, state, attempt sequence, proof/authority digests, shared budget run ID, and transition history/evidence references. Bind the exact policy + producer registry + decided authority bytes and the coordination contract; do not trust a caller-supplied digest.
- Ownership tuple: `(epoch, operationId, attemptId, ownerNonce, fence)`, with environment/session/process identifiers as **diagnostics**, not lock authority. Tokens are randomly generated before a CAS retry loop and validated against the current record; they are not standalone [REDACTED_SECRET_FORM] or credentials.
- `leaseExpiresAt` applies only to preparation, not to issued effects. `requestDigest` binds exact endpoint/method/body. Outcome evidence records exact PR/head, observed merge commit or close response, observation source/time, and whether causation/request completion is known. Never label another actor's action as our successful write without evidence.

Coordinator methods, all with injected store/clock and pure CAS mutators:

1. `inspect(operationId/subject)` — read validated coordination state; no initialization or reservation.
2. `reserve(subject, runId, owner, proofBinding)` — atomically deduplicate, take the namespace slot, allocate a fence, and reserve both run and global budget capacity.
3. `recordIntent(token, exactRequest, durableJustification)` — freeze intended request and proof binding while still **not sendable**.
4. `claimSend(token)` — atomically move that intent to `possibly-sent`; only its successful, unambiguous commit authorizes one in-memory adapter invocation. This is the point after which expiry/refund is forbidden without additional proof.
5. `cancelPrepared(token, reason)` — CAS release only from `reserved`/`intent`, where protocol rules prohibit any network invocation.
6. `recordResponse/settle(token or recovery identity, evidence)` — monotonic CAS attachment of response/evidence and independently checked settlement, never generic “failed therefore free”.
7. `recover(operationId, observations)` — bounded read/reconciliation; never blind resend, never treat absence of notifications as absence of effect.
8. `setRevocation/readRevocation` — shared critical-route stop, separate from local KILL/environment/policy switches. Expose this through an explicit `kill --shared on/off/status` CLI variant while retaining local `kill` behavior; clearing revocation must revalidate authority and never clear an unknown operation or refund its charge. No new authority to issue this live write is granted here.

Every transition has an idempotent transition ID. After an ambiguous **coordination push** result, reload and find that transition/operation before deciding what happened. No forge call is permitted simply because a local push subprocess exited, timed out, or reported a conflict. Reapplying a CAS mutator must not create a second reservation or execute a side effect. Reuse `ledger.update` only where these properties hold; catch its unavailable/conflict results explicitly. A read-only/no-op update must not bootstrap missing genesis.

### State machine and fencing

| State | Is a forge send allowed? | Crash/recovery rule |
|---|---|---|
| `reserved` | No | Capacity and slot held. Lease expiry permits CAS cancellation/adoption with a **new fence**, not a forge call. |
| `intent` | No | Exact request/authority proof is durable. It can still be CAS canceled/adopted; old actor must win a fresh `claimSend` CAS before sending. |
| `possibly-sent` | Only the unique successful claimant may invoke its adapter once | Treat as unknown immediately, including a crash one instruction before network entry. Lease expiry does not transfer send permission. |
| `unknown` | No new send | Lost response, interrupted call, uncertain coordination acknowledgement, or inconclusive observation. Keep slot/charge and reconcile, then escalate. |
| `response-known` | No retry | Store a definite response from the one request, then reconcile independently. A rejection is not a refund until it proves no effect from this attempt and no outstanding sender. |
| `settled-success` / `observed-terminal` | No | Persist the actual outcome, budget event and tombstone. Distinguish observed external completion from our causally proven success. |
| `settled-no-effect` / `canceled-unsent` | No | Release only with the stated no-send/no-effect proof. Keep anti-replay/fence history. A reason string or TTL is not proof. |
| `quarantined` | No | Bounded automated recovery exhausted; durable unknown and its held slot remain visible for explicit boundary handling. No automatic reset. |

Preparation fencing is real: takeover and `claimSend` race through the same CAS. Either takeover commits first and the old token cannot claim, or `possibly-sent` commits first and takeover is prohibited. Clock errors can waste preparation work but do not allow two senders.

**Limit:** the Git fence is not transmitted to/enforced by GitHub. Once a send is claimed, another host cannot revoke a paused process's ability to issue the already claimed request, cancel a packet inside GitHub, or infer completion from lease expiry. Do not advertise exactly-once delivery. The guaranteed property is one coordinated send claimant and no competing/replayed claim until safe reconciliation, plus the endpoint's actual fencing/terminal behavior.

### Adapter, live checks and kill switches

Add `prmaintenance/executor.py` as the single executable Routine 19 adapter, with injected `Forge`/GET functions for tests. It must not run from imports, observation, or the unattended driver.

- Existing gate functions continue proving eligibility, but reserve through the coordinator. Return `operationId`, `attemptId`, namespace/epoch/fence and request/proof digests, not an untracked authorization to run a shell forge call later.
- The explicit operator execution command uses that identity, reloads authority from committed/current source, policy, independent verification, fresh live PR/head/base/protection/holds/checks, local switches and shared revocation. Do not rely on `FullRunner._policyLoaded()`'s cached policy at send time.
- Verify immutable repository/PR identity from live metadata. Extend collected execution metadata to carry repository/PR IDs and response Date/closed-time data without changing ordinary census health semantics unnecessarily.
- Finalize the exact request/intent, recheck route/switches and freshness immediately before `claimSend`, then invoke the adapter once. No `gh pr merge` convenience path that might schedule, retry, enable auto-merge, or change merge method; use the explicit synchronous endpoint and `sha` body field. No hidden HTTP mutation retries or redirects that repeat the write. Unknown adapter behavior means no send.
- Preserve all existing Class B/C gates, independent verifier separation, required approvals, strict content/producer scope, branch protection and destination rereads. Coordination never changes a disposition from C to B or grants an approval.
- A local KILL/environment switch stops that actor; the shared revocation flag is the cross-host stop. Policy revocation remains authoritative. Recovery GETs/recording truthful already-issued outcomes may continue while writes are killed.
- Honest boundary: client-side live checks/kill switches do not provide atomic cancellation of an already issued request or eliminate the final check-to-server race for mutable facts that GitHub does not condition on. If instantaneous server-side revocation is required, a real server-enforced admission/fencing mechanism is additional architecture, not something this Git protocol proves.

## 3. True boundaries: recovery and closure

### Merge recovery

Use fresh PR state and exact-head/merge-commit evidence. For the shipped `merge` method, verify the authorized head is a parent of the observed merge commit when objects/API evidence is available; do not convert a failed parent proof into a success flag. Keep the existing independent post-merge checks observation as evidence, not a fictional precondition that all post-merge checks must already be green.

- A confirmed successful response plus independently observed matching merged state settles success.
- A lost response followed by a matching, irreversibly merged PR can settle **observed terminal** with causal attribution unknown. Any still-delayed same-PR merge cannot create another merge of that already merged PR. Record the distinction and retain the charge conservatively.
- An open/unmerged snapshot, head mismatch, negative status observation or expired authorization **does not** prove the old claimed sender/request is dead. Do not issue a fresh attempt just because REST `sha` would reject the currently different head; it might change again, and an old request may still be pending. Remain unknown unless a definite no-effect response/completion proof exists.
- A mismatch/externally merged different head is not success for the authorized exact head. Record external/conflicting terminal evidence truthfully; use its irreversible state only to establish no further same-PR merge can happen, not to certify the original gate.

### Close recovery and genuine founder choice

The current endpoint cannot atomically fence a closure to the head reviewed by `gateClose`. Even a single first PATCH can race a push, hold, or reopen. Reissuing `state:closed` is not lifecycle-idempotent: it can close the PR again after reopening. The shared slot solves competing cooperating writers, **not** this missing GitHub condition.

Conservative default for the implementation:

- Implement/test closure eligibility, durable justification, reservation, intent, accounting, the adapter seam, and unknown recovery. Do not silently delete `close` from `enabledActions`, weaken head/hold checks, or pretend closure is supported exactly like merge.
- Execution preflight must explicitly expose `conditional-close-unavailable` unless the real closure boundary has been resolved. This is a **reported end-to-end delivery boundary**, not a substitute for completing the authorized closure behavior or grounds to call the entire task done.
- If a bounded first-close route is separately accepted, it still gets only one claimed send, immediate rereads, no automatic retry, and unknown quarantine. A definite successful response from that sole invocation plus independent state/head evidence can establish completion of that invocation. A later reopen is not permission to replay it.
- With a lost response or a claimant paused before sending, even seeing `closed` does not prove no future delayed PATCH exists. Do not release its slot, refund its budget, declare exact-head success, or allow a new closure lifecycle from that observation alone. Event/comment markers do not provide the missing fence.

**Founder/product choice required before claiming complete automatic close safety:** either obtain and independently verify an actual server-enforced conditional close/admission contract, or explicitly accept a narrower first-close/check-to-send/unknown-quarantine risk contract. The latter is an authority/safety amendment and is **not approved by this plan**. If neither is accepted, report automatic close execution blocked while preserving its policy and eligibility machinery. Do not frame indefinite safe quarantine as automatic crash recovery with guaranteed progress. This choice belongs under #2283, not a duplicate issue; use the required founder review surface if a decision packet is requested.

A new broker/workflow/database is not prescribed in this worker slice. A broker that only locks locally and then sends an unconditional GitHub PATCH would still not prove exact-head closure semantics. Do not add one merely to rename the gap.

### Finite recovery, retention and budgets

1. **Finite recovery work:** each explicit recovery invocation performs at most three fresh reconciliation rounds, with injected scheduling in tests, then persists `quarantined` and a precise next-boundary reason. No autonomous endless loop, notification wait, or repeated write. Subsequent explicit recovery can attach new real evidence; it does not reset operation identity or charge.
2. **Preparation leases:** use a pinned short lease, e.g. 120 seconds, only for `reserved`/`intent`. Expiry and adoption always use owner/fence CAS. No preparation token may directly authorize a forge call. No wall-clock jump can expire `possibly-sent`.
3. **Quota clock:** do not use client wall time or Git commit author dates to free hourly capacity. Add an injected server-time sample extracted from a fresh GitHub HTTPS GET response Date, with measured request/response monotonic bounds and second-precision uncertainty. Refuse new admission/window expiry if a trustworthy sample cannot be obtained or the local monotonic freshness interval is invalid. Persist nondecreasing conservative time bounds; a regression delays expiry, a conflicting/future durable bound fails closed for admission pending a sound new sample. Validate HTTP Date/age semantics in the adapter; do not treat arbitrary caller timestamps as trusted time. Tests use an authoritative fake time source independent of process clocks.
4. **One atomic accounting transaction:** reserve slot + operation + action-specific shared run count + hourly capacity in the same CAS. A run has a stable globally unique ID carried across resumes/checkouts; a newly named run cannot release an old run's operation. The run record binds the effective policy cap; conflicting/more permissive policy digests cannot raise it.
5. **Accounting definition:** capacity used is all unsettled reservations/intents/possibly-sent/unknown charges, plus settled successful/observed-effect events not yet safely outside the rolling hour. Before send, revalidate both effective current run limits and global hourly cap. Concurrent actions cannot spend the last token twice. Lowered caps prevent further sends/admission; they never erase outstanding commitments.
6. **No-effect refund:** CAS cancellation before send claim can free reserved capacity. Once a claim could have reached the adapter, only definite evidence that the sole invocation completed without effect and no outstanding sender exists permits a refund. Timeouts, local abort claims, open GETs and comment failures do not qualify. Bound retry/no-effect history and recovery work so rejected operations cannot grow state without limit.
7. **Effect-time uncertainty:** keep an unknown charge pinned regardless of hours elapsed. On settlement, charge through at least one hour after a conservative **observation/completion upper bound** (not the old reservation timestamp), unless stronger authoritative effect-time evidence safely establishes the window. This prevents a delayed effect from escaping the hourly cap. Count one effect charge per logical attempt; response/settlement records do not double-charge it. Do not misstate HTTP invocation limits as effect quotas, or vice versa.
8. **Bounded uncertainty, not magic liveness:** with one global active slot, there can be at most one unresolved send and its corresponding pinned charge. It can halt further critical writes, but cannot accumulate an unbounded stream of leaked reservations. A finite automated recovery deadline escalates; it does **not** manufacture proof or auto-refund. If the requirement means eventual automatic budget release after every lost response, that is impossible here without additional server proof and must remain an explicit boundary.
9. **Retention:** keep unresolved operations/proof in full indefinitely; never TTL-delete them. Keep full settled detail at least 30 days and through all quota/recovery relevance. Thereafter a new-protocol-only CAS may replace detail with a permanent compact tombstone containing logical identity, subject/lifecycle, final state, highest fence, request/evidence digests and the earlier reachable Git commit containing full proof. All old proof remains reachable through append-only Git history; no old-ledger deletion or external archival transfer is involved. No automatic re-close after a reopen; a new lifecycle requires explicit fresh authorization and prior-send safety.
10. **Finite storage/admission:** bound lists, strings and event sizes; use accepted ledger size guards and reserve serialization headroom for worst-case settlement/revocation before admitting an operation (e.g. a validated 16 KiB per active outcome allowance, with an appropriately smaller proof maximum). Pin hard record-count limits as well as byte limits: initially 4,096 logical operations/tombstones, 1,024 durable run-budget records, 64 relevant hourly events, three send attempts per logical operation (a later attempt only after definite no-effect settlement), and eight retained transition summaries per attempt with full prior evidence reachable in Git history. Keep one active operation. Expired settled hourly events may be removed only after the trusted window bound; run-budget/anti-replay entries cannot be forgotten to admit a reused run ID. Refuse new admissions before any bound, while retaining enough headroom for recovery; no unbounded JSONL diagnostics inside shared payload. Permanent tombstones mean capacity will eventually need an explicit decision; fail closed rather than deleting history or launching the parked archive project. Never alter general `FullRunner._compact` to make this fit.

## Plan

Execute only after the parent authorizes implementation. Each unit is a useful committed checkpoint; source publication uses normal campaign review, not a live infrastructure rollout.

1. **Preserve the joined baseline first** using §4. Pin main/campaign/prose SHAs and prove the accepted ancestry and archive exclusion. Do not code from stale campaign-only source.
2. **Add the strict coordinator core** in `prmaintenance/coordination.py`: schema validation, stable identities, ownership/fences, separate preparation/intent/send states, atomic quota admission and no-op/idempotent transitions. Wrap existing `GitRefLedgerStore` on the dedicated namespace/ref; fail closed on absent/untrusted genesis, no production file fallback. Add deterministic unit tests before adapter wiring.
3. **Make the narrow local-store selection correction** in `commands/steward.py` and `scripts/steward_drive.py`. Default ordinary full-run state to local; make explicit legacy git access read-only status; preserve old bytes and class interfaces. Keep the unattended Routine 19 no-write contract.
4. **Wire existing gate types/proofs to the coordinator** in `gate.py`. Add typed coordination/proof handles without changing evaluation authority. Extend the policy parser only for an optional, strictly validated `writeCoordination` binding (`protocol`, immutable repository namespace, provisioned `epoch`; fixed production origin/ref in code). Absent/unconfigured binding grants no execution path. Keep all existing numeric ceilings/actions untouched. Bind decided authority bytes in the proof digest, not only policy/registry. Do not insert an invented epoch/repository ID or edit live policy to activate it.
5. **Remove comments as eligibility prerequisites**, replacing them with stored independent verification and durable justification. Retire `requireTrail` as a correctness escape hatch; keep any compatibility argument explicitly non-authorizing/deprecated. A failed pickup, verification, justification or final comment must not undo a reservation, refund capacity, invalidate real verification, or trigger a second write.
6. **Add the explicit one-shot adapter** in new `executor.py` and the CLI seams in `prmaintenance/cli.py`: retain existing script entrypoint; add explicit `execute --operation-id …` and `recover --operation-id …` (or equivalent typed identity input), with JSON results carrying operation identity and unknown/quarantined status. `gate-*` reserves/prepares, `abort` cancels only unsent preparation, and `finalize` reconciles evidence rather than inventing failure. No arbitrary authorization JSON may directly invoke a forge write. Test injected transports only; do not execute real commands during development.
7. **Add minimal collection metadata** in `collect.py`/`cli.snapshotFor`: immutable repo/PR identity, close/completion observations and server-time response bounds for execution/recovery; preserve exact head and destination object fetches. Separate comment publication errors from safety-critical live-read failures. A failed holds/comment *read* is still unknown eligibility; a failed receipt *write* is best effort.
8. **Update runner recording at its Routine 19 seams, plus the local-only `_update` transport guard**, in `fullrun.py`: emit local proposals without owning shared correctness, carry operation IDs once known, and verify every terminal/success-shaped report against shared durable evidence. Allow pending/unknown to remain honest and recoverable. Superseding a local action or expiring the general run lease cannot cancel/refund a critical operation. Independent recovery must work after the original local run/checkout disappears. Do not import unrelated campaign fixes as rewritten versions.
9. **Update contracts/resource claims together:** Routine 19 skill and mirror, full-run skill and mirror, `founder/steward/routines/pr-maintenance.md`, `founder/steward/README.md`, and the narrow CLI-reference text for changed transport/execution semantics. Update the existing Routine 19 coverage entry only where evidence/API claims changed; never claim activation or complete safe closure while its boundary is unresolved. Preserve the procedural/substantive advice distinction.
10. **Run §5 tests in disposable independent stores/processes**, then the affected accepted campaign regressions. Record actual exact-SHA results and environmental skips/errors. Package/import checks use an offline disposable source export; no install, dependency download, registry staging/build, release or real ledger provisioning.
11. **Independent `reviewer-shared` acceptance** at the final pushed feature SHA plus parent campaign base, then reviewable feature PR targeting campaign integration. If any source changes after review, rerun the affected tests and obtain a new exact-SHA acceptance. Implementation is not deployment, closure-boundary acceptance, or campaign completion.

## 4. Exact preservation and integration sequence

### What must survive

- Main `31b407db65c4e138896780a7319e4a4ce76884eb`, including ancestor `8ad344a4`, all Routine 19/source/proof fixes and released/main sensor behavior.
- Accepted campaign root `c67d90950b0aa37491f5061e76f6cda3319da568`, containing #2284 capacity/history preservation, #2289 canonical unused-import cleanup, #2291 branch-scope, #2292 security/mirrors, and #2293 founder/watcher fixes.
- Independently accepted prose `bb9abb0f30988ad35d4e3ed6ccb6a43dda506c08` and its accepted predecessor `3f4c46fe1` once the parent finishes its publication/integration. At inspection, the evidence-prose remote branch was not the campaign branch. Do not assume those bytes are already integrated or import an arbitrary later lane tip.
- C1 technical metadata scope/L4 limits; C2 published-identity migration hold; C3 GBrain curation/intake hold; C4 manual-only/default-paused wrappers and separate compiler/engine/security gates. In particular, preserve `FOUNDER_LOCK_2283.md`, the four locked question decisions, watcher identity checks and strict threat-detection source changes. No generated-lock synchronization or activation.
- Parked archive #2287 is **excluded**, including `ceb38582008a07002239ec65aa77aa22725e80ab`. Its source review/test receipt is not authorization to incorporate `archive.py` or run a transfer. Archival DoD remains open.

### Future git operations, not performed by this planner

1. Parent pins accepted integration tip **I** (at least `c67d90950`, plus only accepted publication work). Verify recorded SHAs/ancestry, no dirty source, and no parked archive ancestors/files. Resolve publication of the accepted prose first or explicitly preserve its reviewed slice through the parent's normal merge process; do not cherry-pick only a final prose commit while dropping its required accepted predecessor.
2. Pin freshly read current main **M**; require `8ad344a4` and inspected `31b407db6` ancestry, or stop/report an unexpected main rewrite. Fetch/read permission is not permission for destructive history operations.
3. In a **new preservation branch from I**, prepare a normal non-rewriting merge of **M**. Review its PR **into the existing campaign integration branch**, not main. At the inspected SHAs the isolated merge is textually clean; rerun the simulation for actual I/M. Check both-side edits manually, especially `fullrun.py`/tests, accepted `ledgerByteLimit` and no-op `_compact`. Test the joined source. Merge only with the parent's authorization through a normal merge commit. Call the resulting preserved campaign base **P**; prove `I` and `M` are ancestors of P. No reset/rebase/force push of campaign or lanes.
4. Satisfy the user's **rebase against current main only on the NEW isolated follow-up feature line**. Smallest clean sequence: after P exists, create the new **unpublished** feature branch from M, implement only this feature's commits **F**, and rebase **only F** onto the freshly pinned main tip M2 (`git rebase --onto M2 M <new-feature>`). If M2 equals M, record the truthful no-op rebase. Never run an unbounded `git rebase origin/main` on the campaign-derived history; never replay I/c67 or published lane commits.
5. If M2 moved, preserve M2 into campaign with the same reviewable non-rewriting process, obtaining P2; otherwise P2=P. Merge P2 into the new rebased feature line before final testing/publication. That merge restores the **original accepted campaign ancestry**, rather than copying accepted fixes into rebased facsimiles. The feature PR base is P2/the campaign integration branch. Its net diff must contain only this bounded follow-up, not main updates/prose/archive work already belonging to the base.
6. Before first publication, verify `M2`, `c67d90950`, accepted I/P2 and the applicable accepted prose commits are ancestors of the candidate; compare `git diff P2...candidate` and the two-parent preservation diff. Reject archive ancestors or archive-source additions. The new feature can be rebased before publication; if already published, do not force-push: use a merge update or a newly named isolated replacement branch with the old review retained.
7. Final feature PR targets **campaign integration**, references existing #2283 and the exact preservation base. Do not auto-close #2283 while campaign/closure boundaries remain. Use merge commits; never merge this implementation directly into main. Campaign→main remains the parent's separately reviewed/founder-gated integration event.

This sequence preserves exact published history, fulfills the requested isolated-main rebase, and avoids trying to choose either campaign fixes or newer main as the sole source of truth.

## 5. Deterministic test matrix and evidence gates

### Fixture requirements

Create a disposable local bare coordination remote and **at least two `git clone --no-local` clients**, with independent `.git/objects` stores, no alternates, no shared `git-common-dir`, and no inherited real origin/auth configuration. Create additional clones after operations to prove cold-host recovery. Use separate spawned OS processes and a parent-controlled fake forge server/coordinator clock. Barriers/pipes/events select ordering; do not use sleeps as the race oracle.

Existing `tests/steward/test_ledger.py:63–98` gives useful Git-store fixtures, but its concurrency cases mostly use threads. Extend/reuse fixture structure without claiming threads/worktrees are host/process coverage. On Termux, `--no-local` uses transport rather than hardlinks. Assert distinct object directories/inodes and absence of alternates. If the platform genuinely cannot run separate stores/processes, report that gate blocked and obtain the required coverage elsewhere; do not weaken it to worktrees or mocks.

Run children with fixture HOME/config and a sanitized environment that cannot contact production remotes or run a real mutation adapter. All tests use injected fake REST functions/server endpoints. Independent client wall clocks must differ without changing the authoritative fake server clock. Disable inherited pytest timeouts for these verification invocations (`-o timeout=0`); no agent execution cap is prescribed.

| Area | Required deterministic cases and assertions |
|---|---|
| Schema/isolation | Valid/invalid genesis, missing/wrong namespace/repository/epoch/version, malformed/non-finite/oversized fields, missing ref, legacy ledger full of unrelated history. No automatic bootstrap, deletion, migration or eligible records. New ref only; legacy ref bytes/tip unchanged. |
| Pure CAS/retry | Simultaneous first administrative fixture provisioning; simultaneous reservations; stale expected version; identical competing contents; CAS retries reapply on fresh document; injected push-accepted/ack-lost; actor crash during CAS. Exactly one transition/reservation/owner; no forge call until ownership confirmation. |
| Ownership | Same PR merge-vs-merge and merge-vs-close; different PRs sharing namespace slot; duplicate action deliveries; stale owner after preparation takeover; same holder with old fence; token copied to another process. At most one current owner and one claimant; losing actors make zero effect calls. |
| Preparation boundary | Crash before reserve, after reserve, after durable intent, during cancellation, immediately before/after `claimSend`. Pre-send states can be CAS recovered; once possibly-sent, no timeout-based adoption/refund/retry. A paused old actor loses pre-send CAS after takeover. |
| Real processes/stores | Two cold clones reserve through one real bare ref, process exit/kill and restart, a third clone recovering after loss of original checkout, concurrent recovery processes. Confirm one authorized fake-forge effect, not merely one JSON success. |
| Global quota | Two clients competing for final run/hour slot; distinct run IDs; same resumed run ID; merge+close combined hourly cap; pending reservations consuming budget; canceled-unsent refund; definite no-effect proof; duplicate response/settlement not double-charged; lowered caps; base moves/new run cannot reset charge. Run counts and global counters agree across cold clones. |
| Time | Fast/slow/backward/forward local clocks; missing/bad/stale server Date; delayed Date response; second precision; server clock regression/future durable bound; rolling-hour boundary; late effect after an hour. No premature token recycling. Unknown charges stay pinned. |
| Send/result ambiguity | Crash before network but after claim; request delayed before server; effect succeeds then response lost; response arrives after recovery/escalation; response persisted but settlement CAS ack lost; forged/incomplete evidence. Open GET does not prove no effect. No second send or false refund. |
| Merge semantics | Request uses exact REST `sha` and `merge_method=merge`; head mismatch 409; live checks/protection/reviews/base/head change; server refuses merge; wrong head merged externally; matching merged state after lost response; authorized head-parent proof. No admin/squash/auto-merge/release/direct-main-push path. |
| Close semantics | No fabricated SHA/If-Match support; boundary preflight explicit; injected conditional capability if a real contract is later accepted; close response lost; observed closed then reopened; head/hold changes between read and PATCH; paused sender after observation; different action attempts while unknown. Never re-close automatically, never claim exact-head safety from unconditional PATCH. Test closure reservation/recovery even while production execution boundary is unresolved. |
| Kill/revocation | Local file/environment/policy kill before reserve, after intent and before send; shared revocation from other clone; uncommitted/remote-source authority drift; policy/decision/registry change. No new claim/send after observed revocation; truthful reconciliation of already-issued effects still possible. Explicitly distinguish in-flight cancellation limits. |
| Best-effort trail | Pickup/verification/justification/final comment POST fails, times out, is duplicated or its acknowledgement/notification is lost. Shared operation/outcome remains authoritative; no resend/refund/unverification. Failure to READ a safety-relevant hold comment still refuses eligibility. |
| Independence | Verification absent/stale/FAIL, verifier also builder, dispatch not bound to subject, wrong policy/base/head, spoofed caller digest. Shared recovery proof never creates a PASS, dispatch or approval. Local profiles remain local. |
| Runner | `forge.merge_pr`/`forge.close_pr` emit proposals sequentially; no shared reservation during scan; unknown shared operation is not canceled by local action supersession/run TTL; all `already-*`/success reports bind shared proof; forged local terminal JSONL cannot settle a new shared write; late notification idempotent. `--no-agents` and unattended driver's no-write behavior preserved. |
| Local/default/legacy | Reachable origin does not select shared ordinary state; direct `FullRunner` mutators also refuse a shared general store before writing; scan/full local state in distinct checkouts remains independent; `full status --ledger git` read-only legacy diagnostics; mutating legacy selection refused without rewriting history. No eligibility created by migration. |
| Retention/capacity | New-protocol full-detail retention, tombstone anti-replay after 30 days, reachable immutable proof, no deletion of unresolved state, quota horizon before compaction, settlement headroom, bounded record lists. Accepted general `_compact` preserves complete history and capacity environment validation still passes. No `archive.py` dependency. |
| Packaging/contracts | New module imports in source export/wheel, no checkout authority means safe refusal, no new runtime dependency, exact CLI help/API tests, mirrored skills synchronized, static Routine 19 coverage remains truthful, paused workflow source/locks unchanged. |

### Test execution groups (future worker/reviewer)

Record full commands, source/base SHA, exit codes, collected/passed/failed/skipped counts and meaningful assertions. Do not invent counts based on a previous lane's result.

1. New coordinator/executor/process tests plus all `tests/steward/prmaintenance/`.
2. `tests/steward/test_ledger.py`, `test_fullrun.py`, `test_fullrun_cli.py`, `test_fullrun_scenarios.py`, `test_steward_drive.py`, `test_cli.py`, `test_controller.py`, `test_controller_resolution.py`, and the new local/legacy selection regressions.
3. Accepted preservation regressions: founder-lock issue hygiene tests, `test_founder_workflow_lock_2283.py`, security reconciliation/sensor tests, relevant watcher identity/count suites, `tests/test_pr_guards.py` and branch-scope assertions. Run the accepted mirror compatibility Node test. Do not rerun a broad archive-completion suite or transfer pipeline.
4. `python scripts/check_steward_coverage.py`, both changed skill quick validators, `python scripts/validate_skills.py`, and `python scripts/sync_agent_skill_mirror.py --check`. Inspect the validator command behavior first; no repair/compile/activation mode. No playbook schema change is required for these ordinary skills unless the worker deliberately introduces a playbook, which is not requested.
5. Offline packaging/import contract in a disposable exact-SHA source export, using already available build tooling and no build isolation downloads. Do not run existing broad packaging helpers that stage registry data in the actual checkout. If required tooling is absent, mark the packaging gate blocked rather than installing it or treating a skip as success.
6. Run the union of affected suites once on final joined source before independent review; repeat the affected union after any conflict resolution/source amendment. General final integration CI remains the parent's main-bound gate; do not chase unrelated campaign red CI or launch the full routine backlog.

## Files to Modify

Required implementation surfaces (paths relative to repo):

- `src/gaia_cli/steward/prmaintenance/gate.py` — coordinator-backed reservations/identity, durable verification/justification, monotonic settlement/cancellation, no receipt prerequisite, authority binding.
- `src/gaia_cli/steward/prmaintenance/state.py` — retain local stores/profile/diagnostic compatibility; explicitly separate legacy local critical records from authoritative new shared operations. No legacy file deletion or wholesale storage rewrite.
- `src/gaia_cli/steward/prmaintenance/policy.py` — optional strict coordination binding/type, unchanged action/numeric ceilings; missing binding fails execution closed rather than providing a local fallback.
- `src/gaia_cli/steward/prmaintenance/collect.py` — execution/recovery identity/time/close evidence metadata with existing GET seams.
- `src/gaia_cli/steward/prmaintenance/cli.py` — explicit execute/recover seams, typed operation identity, preparation-only abort, conservative finalize, truthful unknown/comment error output.
- `src/gaia_cli/steward/fullrun.py` — `_emitPrMaintenance`, `_recordPrWrite`, minimal injected coordinator lookup/config seams and the local-only `_update` guard; preserve read-only legacy status and accepted no-op general compaction.
- `src/gaia_cli/commands/steward.py` — checkout-local general store selection, legacy read-only diagnostic path and CLI help.
- `scripts/steward_drive.py` — local general-store default only; keep Routine 19 mutation refusal.
- `tests/steward/prmaintenance/test_gate.py`, `test_policy_receipts_state.py`, `test_runner.py` — replace assertions that codify unsafe stale reauthorization/comment correctness with protocol assertions; retain all authority tests.
- `tests/steward/test_fullrun_cli.py`, `tests/steward/test_steward_drive.py`, relevant `tests/steward/test_cli.py` assertions — local/default/legacy compatibility and no-write regressions.
- `tests/steward/test_ledger.py` — only if shared fixture extraction/no-hardlink/ack-loss transport regression is needed; preserve accepted capacity tests. Generic transport source changes are not assumed necessary.
- `.agents/skills/gaia-steward-pr-maintenance/SKILL.md` and `.claude/skills/gaia-steward-pr-maintenance/SKILL.md` — replace external forge-call escape hatch, remove exactly-once/close lifecycle overclaims, document explicit adapter/recovery and best-effort comments.
- `.agents/skills/gaia-steward-full/SKILL.md` and `.claude/skills/gaia-steward-full/SKILL.md` — correct ordinary state/legacy transport wording.
- `founder/steward/routines/pr-maintenance.md`, `founder/steward/README.md` — protocol, recovery, rollout/closure boundaries and local/shared split.
- `docs/en/cli-reference.html` — narrow factual API/transport compatibility correction only; if visible presentation/message changes are needed, route the normal founder CLI/design gate rather than expanding this slice.
- `founder/steward/routine-coverage.json` — only the existing Routine 19 API/evidence/gap claims if changed; no declaration of active coverage or automatic closure safety.

Do **not** modify live `founder/steward/POLICY.yaml`, producer/authority decisions, workflow/lock files, package/config manifests, registry resources, trust/rank data or accepted security/watcher source as a shortcut. Future provisioning of the optional policy binding is a separate authorized action with real repository ID/epoch and a verified remote contract, not a worker-invented value. A focused test-only packaging addition may use `tests/test_packaging.py` only if it avoids that file's real-checkout registry staging helpers.

## New Files (if any)

- `src/gaia_cli/steward/prmaintenance/coordination.py` — strict nested schema/types, dedicated Git-backed critical coordinator, CAS state machine, quotas/time bounds and recovery evidence validation.
- `src/gaia_cli/steward/prmaintenance/executor.py` — explicit one-shot Routine 19 adapter and recovery orchestration; never an unattended activator.
- `tests/steward/prmaintenance/test_coordination.py` — deterministic schema/CAS/state/ownership/budget tests.
- `tests/steward/prmaintenance/test_executor.py` — fake-forge endpoint/recovery/kill/comment tests.
- `tests/steward/prmaintenance/test_coordination_processes.py` — actual distinct clones/object stores/processes and deterministic fault schedules.
- `tests/steward/prmaintenance/coordination_helpers.py` — shared offline bare-remote, no-hardlink clone, fake forge/time and process-barrier fixtures, if needed to keep tests independent/readable.

No new source dependency, service, workflow, archive module, tracking issue or generic routine refactor.

## 6. Worker handoff and independent exact-SHA gates

### Handoff packet

Parent dispatches one coherent backend worker, e.g. **`worker-sol-shared`**, explicitly bound to **openai-codex/gpt-6.1-sol MAX/CLI xhigh**, no fallback/nested agents/timeouts/turn caps. Include this plan, inspected main/campaign SHAs, final preserved P2, allowed files, closure boundary, local/shared split, and the existing #2283 authority limits. Give it an isolated new branch/worktree and no real ledger/GitHub mutation/provisioning authority. Do not dispatch another full campaign or make archive completion a dependency.

Natural durable checkpoints:

1. Joined preservation base accepted by parent.
2. Coordinator/schema/fencing/quota core plus deterministic tests.
3. Gate/adapter/CLI/runner wiring plus fake-forge and process recovery tests.
4. Local-store compatibility, contract/resource updates, complete affected regression evidence.

On an authorized implementation branch, report each commit SHA and normal push status as it becomes durable; never force-push accepted/published history. The feature must not be advertised as production-ready while source, endpoint, provisioning or review boundaries remain open.

### Independent reviewer packet and acceptance

A different **`reviewer-shared`** must examine the **exact candidate SHA and exact campaign base**, not a mutable branch name, with an independent checkout/object store. Bind the requested shared provider/model explicitly; no fallback or self-review. Required findings/proofs:

- Main/8ad + every accepted campaign fix and applicable accepted prose are preserved; no archive ancestry/source or governance/pause regression.
- No ordinary sensor/full-run path writes shared noncritical state; no file fallback can masquerade as cross-host critical coordination.
- CAS admissions are atomic for identity/slot/quotas; fence validation and transitions are monotonic; ambiguous Git pushes and forge responses cannot create another claimant.
- Distinct clones/processes prove both one owner and at-most-one authorized **effect** under injected failures; thread-only success is insufficient.
- Unknown effects are never recycled on expiry, negative observation, comments, local runner supersession or host replacement. Closure reopen/head race and missing server fence are explicitly represented, not waived.
- All existing B/C/independent-verifier/protection/kill checks remain; comments are best effort without becoming fake proof.
- Global accounting survives crashes/window edges and is bounded under uncertainty. Retention preserves proof and tombstones without touching legacy history or invoking parked archive work.
- Real test results and coverage limitations are recorded at the candidate SHA; missing dependencies, skipped separate-store tests, or unresolved closure contract prevent the corresponding acceptance claim.
- Feature PR targets campaign integration, not main; no workflow activation, actual merge/close, source-pause change, package release, deployment or provisioning has occurred.

Reviewer acceptance is source/test acceptance, **not** permission to activate. Parent handles publication/integration gates and any founder decision. Re-review the new exact SHA after every source-changing fix.

## Risks

- **No client protocol can guarantee both automatic progress and safe finite refund after every ambiguous remote effect.** Safe bounded quarantine is intentional; a permanently unresolved send is a real operational boundary, not an implementation success to hide.
- **Conditional closure is unproven/unavailable in the inspected endpoint.** Full exact-head automatic closure cannot honestly be claimed until the founder choice/server contract is resolved. A global Git lock alone does not fix it.
- **Git CAS assumes one intact append-only authoritative ref.** Missing/ref-reset/namespace drift must fail closed. Existing generic absent-ref behavior cannot become production auto-initialization.
- **Old independent writers bypass the new protocol.** Rollout requires separately authorized draining and namespace provisioning; no import of old JSONL or shared history can prove an old request is no longer pending.
- **Clock-derived budgets need trusted conservative time bounds.** A global counter with host-clock TTLs would merely redistribute the same bug.
- **Compatibility is deliberate but visible:** old mutating `--ledger git` general-run usage is no longer the normal shared orchestration path. Preserve diagnostics/history and disclose the change; do not silently migrate or rewrite it.
- **Published campaign history and accepted capacity/security/founder work must remain exact.** A clean textual merge is not regression proof; verify the joined source independently.
- **This assignment did not run tests or implement anything.** The archive remains parked and its actual archival DoD remains open. No scan/run/ledger/GitHub execution or activation is authorized by this document.

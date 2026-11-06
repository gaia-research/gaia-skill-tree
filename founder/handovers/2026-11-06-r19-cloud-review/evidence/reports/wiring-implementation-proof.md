# Routine19 bounded end-to-end source wiring — implementation proof

## Status and exact handoff

**Source implementation completed; independent source acceptance and operational activation are NOT claimed.** The feature is unpublished by this worker. The worktree is clean.

- Worktree: `$HOME/.gaia-worktrees/steward-r19-shared-write-2283`
- Branch: `dev/steward-r19-shared-write-2283`
- Final commit: **`17ad597ad3478b7caae182b1581a965a8fcfa252`**
- Final tree: **`fa46a693d3ad3a26f19474851197e97c56f77769`**
- Accepted bounded-core ancestor: `6b914723004852a5f515f78ed6d536cccbe3a9bc`, tree `7357c944e62327a6466aae7374078b331d2f859d`.
- The prior CORE ACCEPT covers that bounded-core ancestor only. **All changed core/resource/adapter-entry lines and the whole wiring require fresh independent review.** This report is implementation evidence, not self-acceptance.

### Coherent checkpoints

| Commit | Scope |
| --- | --- |
| `2614c9d20e9ab94d3539bf56882e34f81de62546` | Concrete current-source services/executor, bounded clock, strict optional binding, initial gate integration and provider tests. |
| `e9669821867d550b5e67f4e3d14eee3b762c2c80` | Preserve/resume existing WIP; wire operation identities, local-only ordinary state, runner/CLI/driver compatibility and bounded-resource tests. |
| `3245fec8b1868135fce5089e292c161caa969508` | Complete contracts/mirrors, current-source and transport hardening, concrete adapter-entry repair, independent-process/fork tests, exact shared outcome binding, local-state scenarios. |
| `17ad597ad3478b7caae182b1581a965a8fcfa252` | Restore the existing `1.0.0` skill frontmatter version in canonical/mirror: no release/version bump. Only those two metadata lines differ from `3245fec8`; runtime and test bytes are unchanged. |

All four commits have both author and committer `Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com>`, supplied with per-command `git -c` identity. No history was discarded, reset, rebased or amended.

## Implemented runtime boundaries

### Concrete executor and one-shot invocation

`src/gaia_cli/steward/prmaintenance/executor.py` supplies actual implementations, not a production stub:

- `HttpsTransport`: synchronous HTTPS request, bounded response, no redirect-following or hidden retry. Credentials are selected in memory, pinned to the supported GitHub origin, and are not included in serialized operation/outcome payloads.
- `ProductionServices`: canonical-current authority/source checks, existing eligibility and independent-verification checks, exact request construction, authentic response capture, independent outcome reads and merge-parent proof.
- `Executor.prepare/execute/recover/abort` and a fail-closed `makeExecutor` factory. No namespace initializer, repair/ref-reset path, FileStore critical fallback or production genesis command was added.
- Merge is one PUT with REST `sha` equal to the full authorized head and `merge_method: merge`. Close is one PATCH with only `state: closed`. No invented `expectedHeadSha` REST argument, If-Match guarantee, auto-merge or external `gh pr merge` execution path.
- A repeated execute of a claimed/unknown/quarantined/terminal operation reports durable state; it does not call the mutation adapter again. Recover/finalize observe independently and never resend.
- Completion must carry the exact response object captured from the sole invocation. Copied/caller-created response JSON cannot settle it. Matching merged PR identity/head/destination and a two-parent merge commit containing that head are independently checked. Head, destination or parent mismatches do not invent matching completion.
- Authentic completed close responses can retire the sender even after a later reopen. Reports carry observed state and bounded head/base-race flags, with `conditionalHead: false`. A lost close followed by closed/open/reopened GET is not retirement proof and remains held/quarantined.
- Definite completed rejection/no-effect releases the active sender but retains the counted attempt. Unknown attempts never receive a refund from failure reports, local supersession, TTL, new run or negative GET.
- Post-merge check diagnostics are independently read and normalized to bounded status counts. Missing diagnostics are explicitly unobserved, never fake health, and do not undo independently proved completion.

**New concrete-boundary defect found and repaired:** a direct call to `ProductionServices.invoke` could reuse a persisted claim after a lost close/reopen. The fresh red test recorded **2 invocations / 2 effects**. The core now registers a process/thread/instance/request-bound one-shot adapter entry only in the live successful NEW-claim control flow. ProductionServices burns it before live checks/network/callbacks. Persisted claims, copied services, other threads, fork/restart and reentry cannot recreate it. The green probe recorded **1 invocation / 1 effect**, with Refused on direct reentry. This genuinely necessary integration change is additional to the resource-profile core changes and must be independently reviewed.

### Canonical-current authority and durable independent proof

- The strict optional `prMaintenance.writeCoordination` binding names canonical origin/ref, immutable repository identity, protocol/epoch, genesis/minimum-history pins, canonical current `main` authority source and explicit clock/protection/drained-writer declarations. Arbitrary self-nominated staged authority branches are rejected.
- Full POLICY, producer-registry and ratified-decision text is fetched from the designated current canonical commit and cross-checked against the canonical Git tip before/after reads, exact Git objects, committed local blobs and local source bytes. Metadata GETs are cache-busted; stale/cache warnings fail closed. Environment/local-authority overrides and caller hashes are not permission.
- Remote source-ref reads/fetches reuse sanitized noninteractive transport plumbing. Inherited Git object/worktree override variables are refused at the production boundary; local exact-blob checks still verify the committed/current bytes.
- Immediately inside the actual adapter, after claim and before HTTP, current source/policy, independent verdict, exact head/base, replacement identity/head, producer content/scope, holds, approvals/checks/protections and kills are revalidated. Cached FullRunner policy is not send authority.
- The shared proof retains the three complete source texts, validated verifier/dispatch identity and scope, readable bounded PASS-check summaries and closure justification. Free-form diagnostic snippets are not copied as authorization; checksums commit to detailed notes but do not substitute for the actual source text or current eligibility checks.
- Loss of original verification/dispatch JSONL files cannot manufacture a PASS or invalidate the already validated durable proof. Cold outcome recovery does not need the original checkout. Revocation/local kill prevents sends but does not prevent truthful independent recovery of an already-issued absorbing merge.

### Clock contract

The concrete `BoundedClock` requires the explicitly provisioned HTTPS URL/error/precision/round-trip contract. It sends a fresh nonce and requires the echoed nonce, bounded integer UTC/uncertainty, exact no-store semantics, zero/no Age, bounded elapsed network time and consistent monotonic progression. The current schema bounds skew to 0–5 seconds, precision to 1 second and round-trip to 1–5 seconds. Bad/missing/cache/date-only/regressing/future-jump/stalled/network/monotonic samples fail closed. There is no HTTP-Date, host UTC or Git-author-time fallback for admission/window expiry. CLI preparation also uses the configured bounded service time, not host UTC for its initial freshness check.

Completed hourly charges expire only when a trustworthy new LOWER time is beyond completion UPPER plus an hour. Unknown charges never age out. External UTC accuracy is a deployment assumption to be independently provisioned/attested, **not something the software or fake tests observed in production**. No real clock endpoint was configured or verified here.

## Gate, runner and local/shared compatibility

- `gate-merge` / `gate-close` re-prove eligibility and prepare shared identity/intent. Their output is an operation identity, not a bearer send grant.
- `execute --operation-id` enters the one-shot core path; `recover` and compatible `finalize` independently reconcile truth. `abort` cancels only durably unsent preparation. Legacy raw authorization JSON/reservation routes refuse clearly; old 900-second local reservation records cannot reauthorize or refund the shared route.
- Pickup, verification, justification and final comment POSTs are best effort, not permission or a commit point. Required hold/comment READ failure remains unknown/refusal. Genuine independent verification and durable closure justification remain mandatory.
- FullRunner emits checkout-local proposals without taking shared critical reservations during scanning. Every success-shaped outcome, including **merged / already-merged / closed / already-closed**, must match protected shared repo/action/head/base/producer/closure scope and exact evidence; merge commit detail is also checked. Local terminal JSONL cannot suppress/admit a critical write. Attached unknown operations remain pending despite failure-shaped local reports or local supersession.
- General `auto` / `local` selects FileStore without origin probing; the driver default is local. Explicit general Git is read-only legacy **full status** only. CLI and library mutation guards reject before shared load/update. The unattended driver **still refuses Routine19 writes**.
- Independent checkouts sharing one fixture origin retain separate ordinary runs without shared creation/backfill. Legacy status reads leave old history/ref bytes intact.
- **Historical canonical Git campaigns have NOT migrated, completed or settled.** New source refusing their old mutation mode is not a compatibility migration. Their owners still need an explicit transition/retirement plan; no empty local ledger or legacy read-only status is proof they are settled.

## Resource profile and preserved guarantees

The generic ledger implementation remains byte-identical: 8 MiB default, strict 1 KiB–64 MiB environment bounds, unchanged telemetry/serialization. `_compact` remains the exact accepted no-op. No pruning, archive, compactor or automatic epoch rollover was added.

Critical coordination now uses an explicit validated resource profile, default **8,388,608 bytes**, capped by any smaller configured transport limit. The historical `MAX_BYTES = 524288` remains the explicit boundary-test profile; the 512 KiB regressions retain their meaning. Exact serialized NEXT-generation measurement and full-source raw UTF-8 bounds remain intact. Other limits remain 128 complete logical records, 12 events/record, bounded history, reserved outcome/generation headroom, one global active operation, and actual 2 merge / 2 close per run / 10 critical attempts per hour ceilings.

Final real-store/model measurements, captured in final JUnit output:

- Real Git-store retained document: **832,972 bytes / 3 full records**, above the old 512 KiB ceiling and within production profile.
- Smaller 1 MiB transport wins. Attempted candidate **1,227,545 bytes** refuses with unchanged ref and no mutation invocation/effect.
- Complete current-source retained-capacity model: **128 records / 512 events / 5,667,427 serialized bytes**. Record 129 refuses anti-replay capacity.

This is a finite current-proof model, not a promise that every maximal allowed source/encoding fits 128 records or that service is unlimited. Byte exhaustion can precede record exhaustion. Unresolved senders can hold the slot indefinitely. Future capacity/retention/epoch changes require a separate owner decision; no capacity increase raises write quotas.

## Exact verification

All paths below are under:
`$HOME/gaia-skill-tree/.gaia/steward/campaigns/2026-11-05/routine19-shared/wiring-logs/`

### Final exact-SHA affected union

At clean **`17ad597ad3478b7caae182b1581a965a8fcfa252`**, with unchanged `timeout = 60` and `timeout_method = "thread"`:

**1,165 passed in 1,220.39 seconds; JUnit: 0 failures, 0 errors, 0 skipped.**

- Exact command/paths: `final-acceptance-command.txt`.
- Output: `final-union-17ad597ad.log`; machine evidence: `final-union-17ad597ad.xml`.
- Covers all `tests/steward/prmaintenance`, ledger/fullrun/CLI/driver/local-legacy tests, controller/desk contracts, source holds/founder locks, relevant watcher identity/count/legacy-evidence tests, security reconciliation, skill/coverage contracts and PR guards.
- Selected final module counts: core 57; boundaries 11; core spawned processes 10; concrete executor 43; concrete executor spawned processes 2; resources 2; runner 15; local ordinary state 6.
- Actual independent clones/object stores and spawned HTTP-service actors contend on claim CAS and count both invocations and effects. Normal/lost-response paths, conflict and cold recovery after the original checkout is renamed away are covered. A fresh spawned winner forks exactly while its concrete adapter entry is live: the child is refused before locking/network, the original consumes once. No fake server effect deduplication is used to conceal duplicate requests.
- Original concurrent run-lease assertions and `release.wait(60)`, `barrier.wait(30)`, `thread.join(60)` safeguards were restored unchanged for the now-authorized checkout-local ordinary store. Legacy shared refusal is additional coverage, not a skip. AST/source comparison of those assertions/timers is in preservation evidence.

The first affected union at `3245fec8` also passed 1,165 in 1,228.14s (`final-union.log` / `final-union.xml`). The later two-line skill-version restoration required a final-SHA repeat; this is disclosed rather than mislabeling the first tree as the final one. No runtime/test bytes changed between the two runs. No full-repository/archive pipeline was run.

### Contracts, mirror and offline packaging at final SHA

- `check_steward_coverage.py --check`: passed (`final-coverage.log`).
- Both affected `quick_validate_skill.py` commands: passed (`final-pr-skill.log`, `final-full-skill.log`).
- `validate_skills.py`: 83 scanned, **0 errors, 64 warnings**; warnings were not suppressed (`final-skills.log`).
- `sync_agent_skill_mirror.py --check`: in sync (`final-mirror.log`).
- Native `node --test tests/steward/impeccable_compatibility.test.mjs`: **6 passed, 0 skipped** (`final-node-mirror.log`).
- Narrow HTML change: three factual CLI-reference cells only; edited blocks read back, HTML parser accepted, diff check clean. No frontend redesign/assets or workflow compilation.
- `git diff --check`: passed; worktree remains clean.

Offline packaging used an exact `git archive` source export, already-installed pip 26.2.1 / setuptools 81.0.0, `pip wheel --no-index --no-deps --no-build-isolation --no-cache-dir`, an isolated temporary HOME and no registry staging or installs. Although standalone `build` and `wheel` distributions are absent, the available pip/setuptools backend actually built the wheel; no missing gate was turned into a skip. The check compares five relevant wheel module byte streams with final committed source and imports the wheel under `python -I`, proving missing authority refuses before auth/transport/store.

- Reproducer: `offline_package_check.py`; complete output: `offline-packaging.log`.
- Artifact: `$TMPDIR/routine19-offline-package-1b1oo1j_/wheels/gaia_cli-9.3.0-py3-none-any.whl`.
- SHA-256: `e45d876ac1d0dcd3b647b8c5457c08bf6397a25708640b585c24976aee5fe651`.
- This proves the bounded offline export/build/import check, not a fresh dependency-resolving isolated install, bundled-registry lifecycle, release or deployment. Project/skill versions remain unchanged overall.

## Observed failures preserved, not erased

| Evidence | Actual result and disposition |
| --- | --- |
| `provider-attempt-1.log` | Initial concrete provider: 22 passed / 79.86s. |
| `wiring-compat-attempt-1.log` | 22 failed, 100 passed / 114.41s. Old bearer/local-reservation/receipt-prerequisite/shared-auto assumptions were migrated to the required fail-closed shared/local split; existing eligibility checks were not removed. |
| `wiring-compat-attempt-2.log` | 1 failed, 121 passed / 200.05s. Intentional local ordinary state incorrectly emitted the old local-ledger warning; explicit ordinary-local scope/desk handling repaired it. |
| `wiring-checkpoint-2-attempt-1.log` | 2 failed, 217 passed / 430.49s. Incorrect evidence was refused, but the assertion called resume, which legitimately independently reconciled a genuine fixture merge. Tests now inspect unchanged pending/no-outcome storage immediately after the refused record; positive shared truth is separately exercised. |
| `provider-process-resource-attempt-1.log` | 1 failed, 50 passed / 281.82s. Explicit CLI preparation used host UTC against the bounded fixture/verdict time. It now uses the service's bounded current upper time. |
| `integrated-seams-attempt-1.log` | 57 passed / 240.93s. |
| `contract-ready-attempt-1.log` | 172 passed / 296.87s. |
| `adapter-entry-red.log` | Fresh actual concrete-layer defect: 1 failed / 9.44s, persisted-claim direct reentry produced 2 invocations/effects. Fixed by live one-shot core adapter-entry guard. |
| `adapter-entry-green.log` | 6 passed / 50.19s; direct replay now Refused at 1 invocation/effect; copy/thread/reentry, live-entry actual fork and explicit CLI/binding paths covered. |
| `final-seams-ready.log` | 1 collection error / 1.25s from a missing closing brace in the newly extended fake-parent fixture. Corrected, not skipped. |
| `final-seams-ready-attempt-2.log` | 3 failed, 22 passed / 47.60s. New negative tests expected the wrong refusal-message regex; production correctly refused all three. Corrected to the exact actual proof-unavailable message, retaining state/quota/invocation assertions. |
| `ordinary-core-ready.log` | 257 passed / 156.77s, including those corrected head/base/parent cases and ordinary/full/ledger/CLI/driver compatibility. |
| `coverage-preflight.log` | Checker rejected execution/resource files as detector proofs because they do not import the sensor. Restored the catalog's actual sensor-proof list rather than inserting fake imports; conditional execution evidence remains truthful. Final checker passes. |

An inline mirror check also caught the expected temporary lag after editing canonical documentation; the same changes were applied to its generated mirror before final checks. The original failed logs and historical core/boundary reports remain intact. The source/test corrections did not add skips, disable safeguards, increase test deadlines or weaken the preserved concurrency assertions.

## Preservation and true remaining gates

`final-preservation.log` proves accepted ancestors `6b9147…`, `2d9599…`, `31b407…`, `8ad344…` and campaign `ae0598…` remain ancestors. Parked archive commit `ceb38582008a07002239ec65aa77aa22725e80ab` remains excluded. POLICY, authority record, `roster.py`, generic ledger and pyproject are byte-identical to accepted core; workflow tree, all decision files, registry and retained impeccable cohorts are unchanged. `_compact` is byte-identical. Only the intended guides/catalog/skills and implementation/tests changed. C1 technical/L4/security, C2/C3 deferrals, C4 compiled/engine holds and issue-hygiene writes-false were not activated or relaxed.

No source implementation item remains intentionally stubbed at this handoff. The following are **uncompleted owner/reviewer/operational gates**, not accomplished by source construction:

1. Parent's fresh independent whole-feature review, including **every changed core/resource/adapter-entry line**. Incorporate any accepted actual core merge commit if applicable before the final integration source gate. Parent owns publication and normal integration; worker did not push/merge.
2. Explicit activation approval and reviewed canonical-current binding. Live POLICY/producer/authority files were not edited; no operational namespace/epoch/genesis/example values were invented.
3. Actual namespace provisioning/identity/pins and append-only/no-reset/no-delete server protections. Configuration booleans are declarations requiring external verification, not proof of observed protection.
4. Trustworthy deployed clock endpoint/error/precision/cache/network contract. Fake HTTP and monotonic tests do not certify real UTC accuracy.
5. Verified retirement/draining of all bypassing old writers. Local kills do not cancel another host's already-claimed sender; cooperating-writer/platform assumptions remain explicit.
6. Separate historical canonical-Git-campaign compatibility/transition decision. **No migration, backfill, settlement, lease release, false/no-op completion or writer retirement happened here.** Old general shared mutation is deliberately unsupported by this source.
7. Future finite-capacity/retention decisions if bytes/128 records exhaust. No automatic compaction/rollover was smuggled in.

There is no exactly-once HTTP delivery, atomic-close head/base/hold or guaranteed liveness claim. A final external race remains possible with GitHub's API semantics. Unknowns can pin indefinitely. Server/admin assumption violations are not Byzantine-safe. Missing configuration/time/evidence fails closed; it does not make the feature operationally ready. Frozen promotion continues to exclude this unpublished feature; archive remains parked.

## Runtime and scope attestation limits

Observed harness exports: `PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-sol`, `PI_REASONING_LEVEL=xhigh`, `PI_CODING_AGENT=true`. These are runtime exports, **not stronger provider-side MAX attestation**. Same builder context; no fallback, nested agent or artificial agent deadline/turn cap. Spawn/fork workers above are OS test actors, not model delegates.

No real origin coordination/legacy ledger read/write/scan/run/record/lease operation, GitHub mutation/comment, namespace provisioning, writer retirement, push/rebase/reset, main/integration merge, registry/trust/rank/intake change, workflow compile/activation, release/deploy, dependency install or global-configuration mutation was performed. All integration effects were confined to disposable local bare remotes/fake forges and the isolated offline packaging scratch directory. Only genuinely available graft context tooling was used; no plugin was silently installed and no public feedback was filed.

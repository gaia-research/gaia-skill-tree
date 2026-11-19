# Current status — paused partial implementation; not reviewed

The partial repo-envelope implementation is now present in the feature worktree but is **PAUSED / PARTIAL / UNREVIEWED / NOT EXECUTION-READY**. Prior statements below describing an unresolved design assessment remain historical; they are not a current claim that implementation has not started. User pause overrides standing code-only continuation authority until resumed. Exact source scope and unfinished items are in [NEW_P1_PARTIAL_REVIEW_PAUSE.md](NEW_P1_PARTIAL_REVIEW_PAUSE.md). No complete focused-test verdict, independent Terra review, full regression/parity, or normal acceptance exists for the new diff. Preserve policy JSON verbatim and all protected data; do not dispatch or migrate.

# P1 identity-selection assessment

## Founder choices — verbatim record; implementation authorized/active

The founder submitted exact JSON, stored without added metadata in [P1_IDENTITY_FOUNDER_DECISIONS.json](P1_IDENTITY_FOUNDER_DECISIONS.json). Packet `upstream-identity-founder-2026-11`; source commit `0769c2e2216cd4a38e3e121bbdc874956d599c71` is the historical packet-preparation source, not implementation HEAD; #1833 body SHA-256 `9344b0c025eea552cd461bb892ef82e1b88d5530a495f347bfd71f1daac74cc6`. Flat and nested decisions match exactly.

Ratified: one canonical open umbrella per upstream repository, with versioned repo-envelope retaining separate exact per-named finding identities/provenance/digests/carry-forward and per-named approval/sync scope. One approved suite never authorizes siblings, C1/C2/C3, L4, frozen/held GBrain. AgentDB owns its release source distinct from Ruflo despite suiteRef. Preserve #1833 body/history unchanged; any actual migration requires a lossless, payload-hash-bound, deployment-ordered plan. New code may plan/report known legacy holds, while actual writes for affected held repositories remain blocked pending specific migration approval. Unknown/corrupt claimed targets still fail closed.

This is contract-direction ratification, not L4 approval or operational migration receipt. Standing code-only authority covers implementation plus independent Terra review and full regression without routine reapproval. Implementation has not yet occurred in this recording step. Conditional single normal `apply=false` allowance remains unconsumed and gated by review/full regression/all safety and data requirements. Successful planning is not write-readiness; do not promise P1 PASS before an actual normal run. No issue changes/closure/relabel, migration, registry/trust/schema/permission/P2/merge authority. Integration `bfed2d777b76448f6ede5d40e1a834050dff07d0`, schema `6bed0edf324d49e42cd8953351deaccaa733d22f`, and OPEN/DRAFT PRs #2468/#2469 remain unchanged.

## Previous bounded assessment checkpoint

Founder (verbatim):

> Authorized. Same pattern will need no authorization from me

Precise interpretation: the bounded code-only suite/repository umbrella selection repair, adversarial tests, independent Terra review and full regression are authorized without another routine plan approval. At most ONE further ordinary `apply=false` acceptance is conditional on safe cached-conflict resolution WITHOUT data changes and review/full regression. Standing authority covers the same bounded code-only repair → independent review → regression → read-only acceptance pattern; not permissions, data reconciliation, issue edits, P2 or merges. An actual contract/data-reconciliation requirement is a specific stop, not authority to bypass an identity refusal. Existing correction and run limits do not restart.

## Initial runtime/checkpoint

- CWD: requested P1 worktree; branch `dev/upstream-backlog-watcher-2026-11`.
- Clean starting HEAD `3928f9ad5e63bc8eded140e0b6b96686535a02f1`.
- Actual runtime environment: `PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-sol`, `PI_REASONING_LEVEL=medium`, child depth 1. No fallback, retry or nested agent invoked.
- Remote-tracking integration `bfed2d777b76448f6ede5d40e1a834050dff07d0`; local/remote-tracking schema `6bed0edf324d49e42cd8953351deaccaa733d22f`. Local integration branch is older, as expected; not reset or advanced.
- Cached normal report SHA-256 verified `9ef06c462f65dfe21ceb9184bbf9309303cd9adcd90e514cb44ce59928880012`.

## Decision — BLOCKED at the actual contract/data gate

No safe code-only repair of the supplied #1833 conflict was found under the unchanged contract. No implementation, changed test expectation, or hosted run was attempted.

### Canonical selection rule and cardinality (unchanged)

`docs/agents/upstream-watcher.md` §F3 defines the case-insensitive title repository identity, lowest-numbered exact OPEN match, other exact matches reported as duplicates, malformed matching titles blocked. §F3a explicitly states **one canonical open umbrella per upstream repository**. `live.canonical_umbrellas` implements that rule at `live.py:515–538`; `batch.plan_suite` obtains the release-source repository and selects that canonical issue before validating the payload (`batch.py:662–685`). A title is the selector, not permission to change the payload's named skill identity. `releaseidentity.validateUmbrellaIdentity` preserves that second boundary. `LOCKED_SOURCES` keeps AgentDB and Ruflo releases distinct; `suiteRef` is topology, not release provenance.

Graft traced the complete incoming caller closure of `canonical_umbrellas` before considering a multi-file repair: normal batch planning, pre-create race adoption, closure replan, run_batch and watcher main, plus their regression callers. No caller or signature was changed. Finder loading (`iter_suite_skills`, `resolve_suite_source`, `compute_finding`) emits each in-scope named suite's own ID and uses its verified source; it provides no authorized representative-ID substitution or repository-level multi-skill payload. In particular, a parent `suiteRef` cannot be used to redirect AgentDB to Ruflo.

### Why the cached conflict cannot be made green by selection alone

Supplied targeted snapshot: OPEN #1833 has exact Ruflo repository title `[upstream] ruvnet/ruflo → v3.63.8` but payload `skillId=ruvnet/agentdb`. Incoming `ruvnet/dual-mode` legitimately resolves to Ruflo. The normal artifact corroborates the identity refusal but does not contain the exact incoming release URL or full #1833 body; neither is invented here. No further remote read was needed or performed.

1. Under the current title/repository contract, #1833 is a claimed Ruflo canonical target, not an unrelated title that selection can safely ignore. Its readable foreign payload is conflicting evidence. Replacing incoming dual-mode with Ruflo still conflicts with AgentDB.
2. Filtering #1833 out by payload and allowing creation would hide a claimed-target conflict and permit a second OPEN Ruflo umbrella. Selecting a later matching-payload issue would violate lowest-numbered canonical selection and duplicate handling. Both would change policy rather than repair an implementation error.
3. Updating #1833 would cross-write its readable AgentDB identity. Silently treating it as headless/legacy, suppressing unknown evidence, skipping the repository, or dropping dual-mode from discovery would bypass safeguards or lose legitimate observations.
4. Two legitimate named suites sharing a repository do not authorize two repository umbrellas or payload-ID replacement. The current single `skillId` approval payload has no documented aggregation/representative contract that safely turns their separate findings into one approved registry operation. Blind `suiteRef` grouping is especially invalid for AgentDB's retained Ruflo topology.

### Specific owner gate (not another routine code approval)

A safe continuation needs a deliberate disposition of the **existing OPEN #1833 title/payload identity conflict**, preserving its history and receipts, under the owner's data-reconciliation authority. This task does not choose, authorize or execute a body/title rewrite, closure, relabel or identity merge. Additionally, if multiple named-suite findings from the same release repository must be accepted together, the owner must settle how the one-repository umbrella's single `skillId` represents those findings and how approval retains each named identity. Per-named umbrellas or representative/aggregation semantics are policy decisions absent from this code-only grant. #1833 reconciliation alone must not be claimed sufficient for all shared-repository findings.

Until those concrete boundaries are settled, no legitimate `unknownEvidence=[]` proof of the supplied conflict exists. P1 remains FAILED/BLOCKED. The conditional additional ordinary acceptance allowance is **not consumed** and is **not runnable** now. No correction counter was reset. Terra may independently assess this contract diagnosis; no implementation review PASS is claimed.

## Offline verification (unchanged code)

- `PYTHONPATH=src:. python3 -m pytest tests/upstream_watcher/test_identity_2283.py tests/upstream_watcher/test_canonical_backlog.py tests/upstream_watcher/test_count_2278.py -q`: **147 passed in 1.67s**. Existing payload/source corruption, generated-cache malformed identity, shared-source conflict, canonical/duplicate and real normal mixed-inventory dry-path tests remain unchanged. This is not the historical 238-suite rerun or a new full regression.
- Local socket-blocked selector probe reconstructed ONLY the supplied #1833 identity fields and used an explicitly synthetic release tag/URL (not asserted as the actual run's release). Real `read_live`/`canonical_umbrellas`/`plan_suite` with `FakeGh` selected #1833 and raised the exact unchanged payload-identity refusal for incoming `ruvnet/dual-mode`; fake issue inventory unchanged, `gh.writes=[]`. No full cached body exists in the report. This is an expected refusal reproduction, **not** a red→green regression or hosted acceptance.
- Existing normal-path regression passes, but there is deliberately no claim that the actual cached conflict is resolved or that a real normal run with that conflict would pass. Physical mutator counts are not logical planned counters. The preserved artifact remains 3 creates/4 updates PLANNED, unknownEvidence length 1, not fudged to zero.
- Protected named/node/tree aggregate: **869 files**, SHA-256 `fbe0843d2fcb303538918ed4ffe38b0898fcd096cf91b023548eb3cb8bdbe3d7`; diff from pre-contract checkpoint `1e7fcda223700cfbbe85cb790a1d55ed31b49fa0` is empty. Canonical AgentDB own-source repair/provenance and all historical/frozen data remain intact.
- Normal report remains **1,770 bytes**, SHA-256 `9ef06c462f65dfe21ceb9184bbf9309303cd9adcd90e514cb44ce59928880012`. Every other tracked campaign receipt is byte-identical to starting HEAD. Protected integration/schema remote-tracking refs unchanged. No remote PR state refresh was performed; supplied PR #2468/#2469 OPEN/DRAFT integration-base state was not mutated.
- No production source, loading logic, registry, schema, trees, workflow, permissions, job command/routing, combined-inventory guard, transaction, actor/label, frozen, C1/C2/C3 or L4 gate changed. No network, actual issue/PR write, branch administration, push, dispatch, install, regeneration, P2 or merge.
- Long full regression intentionally not run on a report-only blocked result. No green full `gaia dev validate` claim (Class P index remains absent); actionlint remains unavailable, not newly validated. No memory or billing work.

Only this technical report and the current CAMPAIGN decision are changed. Local report commit uses the approved Marcus Rafael B. Tiongson identity; no push. The delivered commit SHA is returned in the handoff (the commit cannot include its own SHA).



## Independent Terra confirmation + bounded current issue read (2026-11-20)

Terra high independently challenged and confirmed this as a true contract gate: DualMode and Ruflo are independently eligible for the same repository; F3/F3a require one lowest-numbered exact-title OPEN umbrella; a single-skillId/sourceURL consumer has no multi-named approval envelope. Neither dropping one eligible observation nor substituting a representative is valid under the old contract. This is a policy decision, not a code workaround; no implementation PASS is claimed.

Current bounded #1833 read: OPEN; exact title `[upstream] ruvnet/ruflo → v3.63.8`; readable payload skillId `ruvnet/agentdb`, Ruflo release source, previous/new versions `v3.42.4`/`v3.63.8`, components mode and empty adds/removes/link-liveness; labels `upstream:release`, `upstream:needs-info`, `P2`; updated `2026-11-04T20:10:06Z`; body SHA-256 `9344b0c025eea552cd461bb892ef82e1b88d5530a495f347bfd71f1daac74cc6`. Bounded history shows routine bot release refreshes and founder-authored 2026-11-04 hold/reconciliation note referencing #2283. Not grounds for immediate closure/rewrite; preserve the body/history. No broad issue/comment crawl; issue text treated as untrusted data.

Approved-main local comparison at `9b4d9b98043140188f00b14d0ac8fa6bc02491b7` confirms AgentDB own-source identity and Ruflo suiteRef are distinct. It does not establish which format is deployed on canonical main; the unmerged feature is not assumed deployed. Current deployed legacy state remains unknown. See [SANITIZED_P1_IDENTITY_FOUNDER_PACKET.md](SANITIZED_P1_IDENTITY_FOUNDER_PACKET.md) for the two unselected policy choices and limits.

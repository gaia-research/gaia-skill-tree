# R19 independent whole-feature review — cloud handoff

## Mandate and current status

The founder requested this remote handoff for an independent review and findings returned to the campaign lead. **Review only: do not implement, merge, activate, provision, migrate or release.** This is authorized defensive review of this repository and disposable fixtures, not permission to operate on live GitHub/coordination state.

The feature is **NOT independently accepted**. Three earlier candidates were rejected on demonstrated defects. Their repairs have bounded tests, but the remaining whole-feature audit is incomplete. Do not substitute green tests for source acceptance.

The last requested OpenAI review was refused under the provider's cybersecurity-access controls. A managed retry then used Codex contrary to the requested pin; that reviewer stopped without fresh tests. This history is disclosed in `evidence/R19_REVIEW_ROUTE_ACCESS_BLOCK.json` and the last blocked report. Use only an environment/provider you are authorized to use. Respect all provider access controls; if refused, stop and report BLOCKED. Do not conceal the history, strip material context or change routes to evade a refusal. This handoff does not authorize a fallback.

## Frozen identities — use these, not mutable main

- Repository: `gaia-research/gaia-skill-tree`.
- Source branch: `dev/steward-r19-shared-write-2283`.
- **Runtime/test candidate: `314fdf655edb7a6cb9bd131461bc11952366979d`.**
- **Candidate tree: `e53b5920571b1458a6b6d0bde1fe454f57c7b411`.**
- Fixed comparison baseline: `3cd5504e00ac00e4708503f484a05e04e5775dcc`, tree `9b29681b44be112306f8502961f4e67787492d97`.
- Handoff branch: `handoff/steward-r19-review-2283`. It adds this documentation/evidence directory to the frozen candidate; no runtime/test bytes are changed by the package commit.
- **Current feature delta: 36 paths**, 4,947 insertions / 609 deletions. `SOURCE_DIFF.txt` is the exact path list. The original assignment's 32-path/17ad figures are historical, not current.

Suggested checkout from an existing clone:

```bash
git fetch origin dev/steward-r19-shared-write-2283 handoff/steward-r19-review-2283
git fetch origin 3cd5504e00ac00e4708503f484a05e04e5775dcc
git switch --detach origin/handoff/steward-r19-review-2283
git --no-replace-objects rev-parse 314fdf655edb7a6cb9bd131461bc11952366979d^{tree}
git --no-replace-objects diff --name-only 314fdf655edb7a6cb9bd131461bc11952366979d HEAD
git --no-replace-objects diff --no-ext-diff --no-textconv \
  3cd5504e00ac00e4708503f484a05e04e5775dcc \
  314fdf655edb7a6cb9bd131461bc11952366979d
```

The first diff must contain only this handoff directory. Stay on the handoff checkout while reading its evidence; checking out the bare source commit removes the package. Test results on the package checkout must state its HEAD and separately bind the runtime/test blobs to the frozen candidate. Do not use a triple-dot diff against current main: ancestry/current-main changes are not the frozen comparison.

## Evidence map and chronology

Paths below are relative to this directory; bare report filenames in items 2–9 and 11 are under `evidence/reports/`. `MANIFEST.json` records original and published SHA-256 hashes, sizes and redactions. Public evidence copies normalize local paths and redact recognizable credentials, non-public endpoints and quoted issuers. Originals remain preserved in the lead's session. Redacted copies are not executable or byte-identical originals; request an appropriately redacted clarification rather than reconstructing secrets.

1. `evidence/reports/wiring-implementation-proof.md`: original builder claims at **17ad**. Includes 1,165 affected tests, resource/process/adapter measurements and packaging claims. These are historical claims requiring audit, **not current independent passes**. For example its generic-ledger byte-identity claim predates later Git hardening.
2. `core-boundary-independent-review.md`: bounded core acceptance at **6b9147**, not whole-feature acceptance or acceptance of subsequently changed core/callers.
3. `wiring-whole-independent-review.md`: first partial review, incomplete.
4. `wiring-whole-independent-review-completion.md`: **17ad REJECT**. A report omitting an already-attached operation ID could finish local work while the shared unknown sender remained held. No duplicate send/refund was established by that particular probe.
5. `unknown-binding-repair-proof.md`: **9d** repair; subsequent review freshly verified old red/new green and selected controls.
6. `wiring-whole-repaired-independent-review.md`: **9d REJECT**. Local Git replacement refs redirected content authorization, reaching one fake invocation/effect.
7. `git-object-boundary-repair-proof.md`: **e7** no-replace/graft/environment repair, including generic ledger Git plumbing. Not a universal compatibility proof.
8. `wiring-whole-git-hardened-independent-review.md`: **e7 REJECT**. Git archive attributes omitted true base history from deterministic index proof; one fake invocation/effect. It also records fresh expected-invariant red/green for the replacement-ref repair.
9. `exact-tree-export-repair-proof.md`: frozen **314f** raw tree/blob materialization repair and 10 brief passes. Its parent-long-test-pending status is superseded only by the next item, not by acceptance.
10. `evidence/parent-314f/`: exact source/test bindings, commands, raw logs, explicit exits and summary for all four Parent-owned groups on 314f. They finished **2026-11-06T07:51:38Z**, all exit 0: **58 proof/gate, 58 executor, 74 runner, 78 coordination**. These are Parent evidence, not your fresh results.
11. `wiring-whole-exact-tree-independent-review.md`: last BLOCKED review, provider/route issue; no fresh test or source finding.
12. `evidence/original-wiring-logs/`: all 35 original text artifacts, including final 17ad commands/JUnit, original failures, mirror/coverage/preservation/offline packaging evidence. They predate later repairs. The packaging reproducer is `.py.txt`, evidence only. Do not represent the old 1,165-test union as a 314f run.
13. `evidence/reports/wiring-whole-review-assignment.md`: complete original obligation list. Its old SHA/path/route are historical context; **this handoff's candidate and authorized operator environment govern**.

Earlier interrupted dot-only regression logs had no final summary/exit and were never counted as passes. Their omission here does not convert them into successful checks. Independent scratch probes under the old ignored `.gaia/whole-review-probes` are not published; reports disclose their observations. Reconstruct fresh probes from the versioned fixture helpers/tests rather than assuming those local paths exist.

## Required independent work — finish the whole scope

Read current repository instructions and use graft where available; source is authoritative if the graph is unavailable. Inspect **all 36 changed paths**, every changed core line and relevant consumer/caller. Do not review only the most recent two-file fix and label the feature accepted.

- **Concrete one-shot executor:** correct HTTPS construction/origin-bound credentials, no redirects/hidden retry; live new-claim process/thread/instance/request-bound entry burned before callbacks/network. Exercise direct replay, copied/persisted tokens, reentry, fork/restart/paused sender, CAS acknowledgment loss and unknown outcomes. Count both invocations and effects; server-side dedup must not conceal duplicate sends.
- **Current authorization and source proof:** canonical full POLICY/producer/ratified-decision texts, source epoch/genesis/history pins, independently validated producer/verifier scope, revocation/holds/current exact head/base and rechecks immediately before actual send. No cached/local hash or bearer grant substitutes for current authority.
- **Git interpretation and exact history:** replacement refs, custom namespaces, inherited/config/graft/object/worktree controls across all readers; authentic raw tree/blob materialization immune to export-ignore/export-subst/smudge/checkout conversion. Test dropped historical indexes with negative/clean controls and fresh old e7 red/new 314f green. Audit bytes, executable modes, paths, symlink/gitlink refusals, destination safety and all consumers.
- **New materialization bounds:** 4 MiB listing, 16 MiB per blob, 64 MiB total, 16,384 entries and the original shared 120-second deadline. Inspect real required roots and failure behavior, not a claim of universal compatibility. No silent limit increases to pass tests.
- **Shared coordination:** pinned history/genesis/CAS, one global active operation, atomic run/hour charges, quarantine/retention, exact next-generation serialized bytes and outcome headroom, complete raw UTF-8 source texts. Unknowns pin without refund via TTL, local failures, new runs or negative GETs.
- **Clock and transport:** nonce/no-cache/uncertainty/network/monotonic bounds, trusted lower vs completion upper time, no host/Git/Date fallback. Production 8 MiB constrained by transport; preserve explicit 512 KiB regressions and finite 128-record/capacity limits without quota increases, archive or rollover.
- **Outcomes and API limits:** exact merged/already-merged/closed/already-closed scope and independently checked merge parents. Authentic close completion vs later reopen; lost close/reopen is not proof. REST merge has a head-SHA fence; close has no atomic expected-head fence. No exactly-once, atomic-close or guaranteed-liveness claim.
- **All integration seams:** gate, CLI, FullRunner, driver, state, collection, policy, ordinary local/default and legacy shared-Git refusal, status-only reads, no backfill/migration/settlement, no old 900-second/raw-bearer route, best-effort comment writes versus required fail-closed reads, real missing configuration refusal.
- **Preservation/contracts:** compare changed tests to original assertions and timeout/concurrency safeguards; audit historical raw failures/JUnit/packaging evidence at their actual SHAs, mirrors/catalog/factual HTML, unchanged registry/version/authority and founder holds. Generic ledger Git changes require real ordinary/legacy compatibility review.

Run proportionate **fresh independent negative/control probes** at real fixture producer/consumer seams. Distinguish your runs, Parent runs, builder claims and carried immutable-byte evidence. Retain original pytest `timeout=60` / thread, joins/waits/barriers and concurrency assertions. Do not disable plugin loading, increase timeouts, skip cases or weaken assertions. Use durable ordinary background execution for long commands and record terminal exits; an interrupted log is unknown.

Do not run the entire repository/archive pipeline or install/change global dependencies/configuration just to force a pass. If the available isolated environment cannot support a required check, disclose the exact blocker. All effects must stay in disposable local Git repos/fake forges/clocks: **no real GitHub mutation, origin/legacy/coordination-ledger run/scan/record/lease, live clock/protection call, namespace initialization, activation, writer drain, migration, push, PR, merge or deployment.**

## Separate delivery holds — never waived by source acceptance

Even a clean whole-source verdict does not authorize integration or activation. Missing are independently provisioned namespace/ref/genesis/server protections and trustworthy deployed clock; explicit activation; retirement/drain of bypassing old writers; an owner-approved transition for the ongoing historical shared-Git campaign, which this source's default-local/legacy refusal can otherwise strand; and a separate before/after founder gate for changed R19 CLI output. M1's unrelated warning approval is not that gate. Archive remains parked; C1–C4/D/L4/data decisions remain binding.

The separate CI-churn dispatch is waiting on an explicit file-edit permission question. This review handoff is **not** approval of that edit or a reset of any canonical attempt.

## Return this report to the founder/lead

Return a standalone Markdown report, not an implementation PR:

1. **WHOLE-SOURCE verdict:** ACCEPT / REJECT / BLOCKED for candidate SHA and tree above. Incomplete coverage is BLOCKED, not acceptance.
2. Reviewer identity, actual provider/model/effort (if an agent), environment/checkout HEAD, runtime/test blob bindings and scope.
3. Findings by severity with exact `file:line`, demonstrated behavior, negative/control reproduction, invocation/effect/state/budget evidence and impact; no speculation as a defect.
4. A **36-path plus caller/core coverage matrix**, listing completed and unreviewed obligations.
5. Fresh commands/results/exit evidence, meaningful before/after checks, Parent/carried evidence and all limits. No double-counting or relabeling old runs.
6. Unchanged external/delivery holds and any actual environment/provider blockers.

Do not self-implement a repair. Send findings back; a separate writer and independent follow-up will handle verified defects. Preserve the frozen source and evidence package.

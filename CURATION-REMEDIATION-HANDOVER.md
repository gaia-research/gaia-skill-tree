# Curation remediation — compaction checkpoint

## Mission, authority, model policy

Continue the founder's implementation/security/E2E request for #2089/#2088, NOT a new architecture audit. Lead is GPT-6.1 Sol High (verified PI_MODEL=gpt-6.1-sol). Only `openai/gpt-6-luna` subagents, explicit `thinking: high` for complex/security/review or `medium` bounded regressions; never set max_turns or any turn cap. No nested agent families. No merge, deployment, real intake, canonical registry mutation, manufactured approval, issue update/closure. Development PR is authorized and still owed. Fresh independent Luna reviews are required and NOT DONE.

## Exact workspace — do not edit original main

- Worktree: `/data/data/com.termux/files/home/.gaia-worktrees/curation-remediation`
- Branch: `dev/curation-secure-reconciliation`
- Code checkpoint committed as `3e0641e3e` after `7624ed445`; source/tests were clean when independent review launched. Review source is frozen: do not mutate reviewed code/tests until retrieval.
- Original session cwd remains `/data/data/com.termux/files/home/gaia-skill-tree` on main with preexisting untracked `.pi/*` and emilkowalski discovery packets. Preserve them. Every bash edit/test/commit must `cd` to the remediation worktree or use absolute paths.
- A `subagent action:apply` attempted to use original root, failed and rolled back (original tracked main stayed clean). All reviewed subagent commits were instead cherry-picked `-x` into the correct remediation worktree. Do not reapply them.
- No remote push or remediation PR exists yet.

## Evidence baselines and recovered audit

Remote refreshed before edits. Main is `f77e4daf89992b2131ce628a1519ff859682c299`, already contains #2093 `cddb09ce9b230dd0187ccebe091b88cab2d67b5b`.
#2089 OPEN at `32ecd0df7c0683167e2d9dfacf6ecbb4481cb453`, target `dev/emilkowalski-intake-2026-10-13` (not main). Its two commits were cherry-picked with attribution; #2093 collision/lowercase protections preserved in conflict resolution.
Original audit recovered/read completely at `/data/data/com.termux/files/usr/tmp/gaia-curation-audit-BtjgnI/ARCHITECTURE-AUDIT.md`. Original reproductions `independent_probes.py`, `identity_collision_probe.py`, `independent-results.jsonl` beside it. Do NOT repeat audit or redispatch discovery.
Isolated exact PR-head baseline worktree: `/data/data/com.termux/files/home/.gaia-worktrees/curation-audit-baseline` detached at 32ecd0df7.

## Current implementation and commitments

`CURATION-REMEDIATION-PLAN.md` records shared lane interfaces. Commits (oldest to newest):
- 845ce43ca + 04fd2930e: #2089 CLI commits imported with attribution.
- b535e234a: shared interfaces/ownership plan.
- fa56ebb49: parent content-derived submission, continuation, docs, assessment collision repair and original-attack tests.
- 167d7d42c: initial L4 containment (Luna A 624c9b3bf).
- 6edbe9131: initial persistence/freshness (Luna B 22255c33e).
- 085a6681a: initial reconciliation/fanout (Luna C 6b94dd7de).
- e799f5eb2: initial chain (Luna D 40c4dd3cb).
- 1406e0d3d: parent complete-manifest context, direct resolution fail-closed, full accounting payload, external carrier CLI options.
- 9984588da: C repair (Luna 9e9f31ed7).
- d83055f9e: D repair (Luna e1c11e753).
- 725c6e4dd: parent actual CHAIN/C integration, named identity, correct frozen snapshots, truthful advisory deferrals.
- 7624ed445: B full-catalog freshness/locks/full-hash filenames (Luna 081b0a9f8).

### Security — critically honest status

`curation/authorization.py` builds independent review payloads binding exact candidate/named/generic/topology/source/packet/assessment/catalog/rubric/route/manifest data. Authorization carriers and local humanReview metadata are excluded from proposal digest, avoiding cycles. Complete manifest accounting can be supplied as `reviewInventory={inventory: frozenEnvelope, reconciliation: report}`; complete ready packet membership verified. Existing-intake context preserves original issue/batch references. Ratify and trusted push run freshness, actual assessment validation, and authorization. Direct `validateL4Resolution(requireHumanReview=True)` now also refuses fabricated authority.

**Production `_verifyTrustedEnvelope` is deliberately DENY-ALL.** No existing workflow establishes independently authenticated human authority over this full payload. No protected workflow/environment was installed/configured. Local flags, names, refs, timestamps, comments and env overrides NEVER count. This is containment and pending ceremony, NOT completion of real authorization. Unit tests monkeypatch the PRIVATE verifier and explicitly label that mocked success as unit-only. The real approved outside-top-K ceremony must be SKIP/held; do not claim production security or full completion. Final recommendation remains NO-GO until missing mechanism/human verification is resolved. Outside-top-K structural capability is retained and payload-bound, not permanently removed.

`pushFromFile.py` loads all manifest packets before calling `buildIntakeYaml` ONCE on full inventory with exact ORIGINAL manifest-byte SHA256 (binary read, no reserialization), route, external envelope/accounting context. It restores per-candidate packet paths after adaptation. Ordinary YAML works only as unreviewed proposal and rejects reserved trusted-claim keys recursively.

### Persistence/freshness

`prefill.safeCandidateSlug`: readable prefix + full SHA256 of exact candidate ID, whitespace rejected. Packet and assessment writes check owner under `submission.advisoryLock`, reject symlink escapes, atomic write. `assessCommand` default uses safeCandidateSlug and checks ownership/lock too.
`buildGenericSnapshot` retains canonical id/name/kind list plus semanticGenerics/full semanticCatalogSha256; malformed nodes fail closed. `verifyPacketFreshness` checks full semantics across available projections, re-fetches source bytes, revisions/timestamps and actual dedupe proof. B intentionally requires accessible named catalog; missing named dir => checked false.
**Uncommitted parent fix**: buildPrefillPacket no longer stamps deduped/mapped if exactDedupe.checked != true. It ends normalized/deferred with EXACT_DEDUPE_UNVERIFIED. Empty accessible canonical named directory is a completed lookup; an unavailable directory is not.

### Reconciliation/FAN-OUT

`freezeInventory` uses separate candidateId/namedIdentity/generic identities, immutable detached packet input, source URL/revision/digest, stable task ID; exact lowercase named identity enforced. SourceRevision may be null only with freshnessRequired. Parent allowed null sourceDigest only with explicit unresolved freshness, never eligible for ready packet.
`reconcileInventory` verifies actual bytes, task/input/output digest, candidate+named+source+frozen catalog, proposal == actual packet decision, v2 validator. Unknown receipts explicitly reported; competing receipts deterministic defer. Full report retains source, task/attempt, hashes, packet, proposal, duplicate proof, outcome, rationale; humanApproved false.
Parent tightened exact duplicate relation to match BOTH current candidate and a different target, rejects contradictory hashes and non-surviving/cyclic/rejected targets. Deferred final worker receipts now have `receiptValid=true` when actually validated so FAN-OUT can preserve them on resume (not blindly redispatch valid semantic deferrals). Receipt metadata must match actual dispatched task/attempt/input, not be silently overwritten. These latest changes are uncommitted and need regressions/rerun.
`runFanout` callable/model-neutral bounded ThreadPoolExecutor, stable shards, maxTasks candidate-task budget, maxAttempts retries only worker exceptions, actual receipt validation, errors carried to reconcileFanout. Cooperative timeout only: cannot kill threads; late returns discarded. Need independent review for late mutable path/receipt handling and distributed idempotency limits.

### CHAIN — current parent implementation

`orchestrator.py` rewritten in 725c6e4dd, not just the earlier Luna implementation. Source preparation checkpoints each source before semantic work; frozen full inventory+generic snapshot; exact named identity required, explicit `--named-identity` added to command/state. No invented description; real frontmatter. Source branch is NOT fabricated immutable revision: SHA40 retained, otherwise null+freshnessRequired. Default processor executes real prefill+assessment/persistence, adds frozen namedIdentity to packet, constructs receipt matching actual packet decision and exact hashes. It uses shared reconciliation, NOT a second engine.
Default prefill is HONESTLY DEFERRED awaiting semantic/human review; it is not auto-MAP by thresholds and is never human-approved. L4 prints full report. Budget exhaustion accounts remaining rows as deferred. State writes mkstemp/fsync/replace/dir-fsync. Attempts charged before work. Current CLI resume verifies stored packet/assessment/source hashes and B freshness, preserves batch+issue refs; status should not perform live verification/write blockers (latest uncommitted fix).
Potential next checks: source prep partial failure retry/resume tests; run_id/path validation; prepared source freshness on resume before any packet result exists; genuine default 1/5 chain tests must assert VALID deferred reason vs merely `accounted=true` (now assert PREFILL_AWAITING_WORKER with complete empty named catalog). A single exact source without canonical kebab frontmatter name must supply `--named-identity`, rather than invent identity.

### Submission

`curation/submission.py`: contentKey excludes clock/batch/issue bookkeeping; deterministic batch IDs, cross-platform OS advisory lock, atomic durable receipt, crash uncertain state refuses blind issue retry, explicit existing issue/batch verification and evidence continuation. `prWriter.open_intake_issue` queries prior exact content key remotely before create, fails closed if query unavailable, returns unique existing issue. `push.write_skill_batch` atomic and refuses content-key ownership mismatch.
**Potential limitation:** cross-checkout simultaneous callers can race between remote query and issue creation; local lock only serializes one checkout. Do not claim distributed exactly-once. Protected submissions are currently blocked anyway. Independent conservation/idempotency reviewer must inspect this and uncertain recovery. No real network issue was opened.

## Subagent runs — all implementation lanes FINISHED

- f51ca596-82ee-4ed7-9a4d-2626d29ca361: initial A/B/C/D, all diffs inspected and imported (commits above).
- 6516da5f-fb43-47dd-840a-95456ba2d44c: C/D follow-up, all diffs inspected and imported.
- a7a822ea-7729-4272-89fc-5394ffd18120: B full freshness, diff inspected and imported.
No implementation agent owns files. TWO FRESH read-only independent GPT-6-Luna High reviewers are now RUNNING in `08c3a6da-744b-4f93-88e3-1f9ab3f9e1a4` against source SHA `3e0641e3e`: index 0 L4/security/governance and index 1 conservation/collision/idempotency. They have no implementation ownership and no write permission. Source/test scope is FROZEN until results are retrieved; parent may collect evidence and write report docs meanwhile. Use subagent action:wait to collect (not polling).

## Background commands and evidence — notifications only, never poll

All tasks use default durable terminal notifications. Call bg_logs only AFTER matching notification; do not bg_status merely to wait.
- b3ef1f62f `Audited PR baseline tests`: terminal completed/exit0 collected: **179 passed in 5.07s**. This was a different focused subset, NOT exact224.
- bedb8629e `Submission idempotency regression tests`: terminal completed/exit0 collected: **78 passed in 1.73s**. This was before final security integration; not final-SHA acceptance.
- b37e8b928 `Exact 224 test baseline`: terminal completed/exit0 and logs collected: **224 passed in 8.59s**. Exact nine-file audit command at isolated PR-head:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -p no:cacheprovider -q tests/test_intake_multi_packet_2088.py tests/test_intake_adapter.py tests/test_dev_ratify.py tests/test_push_from_file.py tests/test_intake.py tests/test_intake_approval_workflow.py tests/test_gaia_curate_discovery_packet.py tests/test_curate_command.py tests/test_curate_state.py`
- b3bc10791 `Integrated curation focused regressions`: launched on intermediate code; result notification not yet collected. Diagnostic, not final.
- b2469261a `Curation integration regression matrix`: launched on intermediate code including 24 focused files. Result notification not yet collected; source/test edits occurred after launch, so MUST rerun on frozen final code even if green.
- b5028be8c `Curation documentation contract checks`: launched; result notification not yet collected.
Task output files under original cwd `.pi/tasks/01a15932-8e8f-7677-af72-c4ac8ccfe524-23602/<taskid>.output`.
Latest short checks after user compaction request: compileall relevant source/tests PASSED, git diff --check PASSED, skill mirror parity PASSED, git diff against origin/main showed NO registry/skill-trees/docs/graph changes.

## Changes checkpointed in 3e0641e3e (preserve; only this handover update follows)

1. Mirrored gaia-quick-curate SKILL.md rewritten truthful executable pre-L4 docs, no scaffold or auto-merge promise.
2. commands/curate.py status no live checks/mutations, named flag already committed.
3. curation/fanout.py strict assigned metadata, preserve validated deferrals.
4. curation/reconciliation.py surviving target proof and receiptValid flag.
5. prefill.py truthful dedupe-unavailable lifecycle.
6. tests/test_curate_chain.py complete explicit empty named directory in default-processor fixture.
7. tests/test_curate_command.py truthful executable skill assertions replace obsolete scaffold assertions.
8. tests/test_curation_cli.py 9 precise filename sites changed to safeCandidateSlug, imported helper.
9. tests/test_curation_assessment.py default assessment filename updated to safeCandidateSlug.
10. This handover.

## Next execution path (continue, don't stop at plan)

1. Consume pending terminal notifications/logs as delivered. Fix current integration regressions honestly: old valid-local-approval tests must now expect denial or use clearly scoped UNIT-ONLY mocks, not weaken production guards. Old unhashed filenames should use safeCandidateSlug.
2. Add missing meaningful resume/failure/budget/duplicate-survival/valid-deferral/FAN-OUT metadata regression tests. Verify actual packet outcomes and preserved inventory, not just counts.
3. Refresh canonical docs command examples if needed, keep .agents/.claude mirrors; schema need not change, do not mutate canonical registry.
4. Run focused full matrix at a stable committed SHA, exact224 baseline comparison, existing mainline identity/recovery/provenance suite. Then applicable repository-wide tests (enumerate skips/offline/model-download constraints; don't claim full suite if not run). Run skill validators and diff check.
5. Commit checkpointed changes, push dedicated dev branch (no force). Prepare/open ONE draft remediation PR against current main, explicit #2089/#2088/audit references, no issue comments/closure.
6. Retrieve RUNNING independent review `08c3a6da-744b-4f93-88e3-1f9ab3f9e1a4` with action:wait. It has two fresh Luna High reviewers (security and conservation) against frozen code 3e0641e3e. Do not mutate source/tests while they inspect. After retrieval repair findings and diagnostic test failures, rerun proportionately, and re-review required blockers. Do not confuse existing implementer self-tests with these independent reviewers.
7. Deliver CURATION-REMEDIATION-REPORT.md with file summary, all 26 matrix rows PASS/FAIL/SKIP, exact test logs/SHA, original attacks repaired at real boundaries, honest mocked-vs-real ceremony distinctions, reports, compatibility #2093/current main, remaining human actions and NO-GO for original #2089 and protected activation until independent ceremony exists. No production merge/deploy/intake.

`CURATION-REMEDIATION-REPORT.md` is now a draft evidence ledger/matrix, not a completion report. Its PENDING cells must be replaced only after actual final-SHA tests and reviews. Baseline 224 result is recorded there.

Definition of done is not met yet. Do not claim completion from these edits or preliminary tests. Founder explicitly permits leaving protected flow blocked if independent human authority cannot be established; that does not make a mocked ceremony production success.


## FINAL STATE (supersedes the working notes above)

- **Draft PR opened: #2134** (DRAFT, base `main`, head `dev/curation-secure-reconciliation`),
  https://github.com/gaia-research/gaia-skill-tree/pull/2134 — references #2088, #2089, #2117,
  #2118, #2093, #2099. **Not merged. No issue comments. No deployment. No real intake.**
- Head SHA: see `git rev-parse HEAD` on the branch. The branch contains main's commits via a
  merge, so the PR diff is only this remediation.
- PR #2089 is still OPEN and unmerged at `32ecd0df7c0683167e2d9dfacf6ecbb4481cb453`.
- `origin/main` unchanged at `e1a87057957945c773c6bde2b6e7650419cfe8c5`.
- The original main checkout is untouched; its untracked `.pi/` and the 16
  `registry-for-review/discovery-packets/emilkowalski-*.json` files are preserved.

### Verification at the final head

All numbers below were measured on a **clean checkout of the committed SHA** (a detached
`git worktree` at the final commit), not on the working tree, so the receipt describes the
committed artifact rather than the branch directory.

| Check | Result |
|---|---|
| Focused curation suite (24 files) | **690 passed** (672 + 18 new CodeQL-regression tests) |
| Exact audit baseline (the nine audit files) | **235 passed** (224 historical + 11 new) |
| CodeQL regression coverage (`tests/test_curation_error_contract.py`) | **18 passed** |
| `scripts/merge_gate_check.py` | **15/15** |
| `scripts/curation_walkthrough.py` | **17/17** |
| `scripts/verify_review_findings.py` | **13/13** |
| Wider repository suite (`tests/`, not integration/slow) | **5183 passed, 8 failed, 18 skipped** (clean checkout of the final commit) / **5185 passed, 6 failed, 18 skipped** (branch checkout). All eight reproduce identically on pristine `origin/main` in the same environment — 2 platform limits (no writable `/tmp`, no `os.link`), 5 missing generated Class P artifact (`registry/named-skills.json`, gitignored), 1 detached-HEAD case. |
| `scripts/pr_guards.py --base origin/main` | **42 passed, 0 failed**, all named guards pass |
| `scripts/sync_agent_skill_mirror.py --check` | in sync |
| `scripts/sync_bundled_schemas.py --check` | in sync |
| `git diff --check` | clean |
| CodeQL (GitHub Advanced Security) | **pass** — the four `py/clear-text-logging-sensitive-data` alerts (106–109) are **fixed**, 0 open alerts on PR #2134, nothing dismissed |

Every wider-suite failure is environmental or a missing generated artifact, and was
re-confirmed against **pristine `origin/main` at `e1a870579`** (a separate detached worktree)
using the same command and environment, rather than against an old receipt. The full per-test
breakdown is in `CURATION-REMEDIATION-REPORT.md` §6. **No failure is attributable to this
branch.**

### Independent review history
**Five** completed independent review rounds (round 1: two fresh Luna High reviewers, security +
conservation, static, against frozen `3e0641e3e`; rounds 2–5: Luna XHigh with runtime probes).
The canonical accounting is in `CURATION-REMEDIATION-REPORT.md` §7:

- **16** unique independent findings — 14 product/security + 2 test-quality — all fixed and
  independently re-verified;
- **5** repeated confirmations (round 2 re-confirmed round 1's five as closed at runtime) —
  not counted twice;
- **1** duplicate description of a single defect in the report's own table — removed;
- **2** separate self-review findings — not counted as independent;
- **18** total unique defects addressed.

The earlier "11 findings" figure counted *reviewer-reported items* — rounds 3–5 reported six
distinct defects as three items, two of which each bundled a pair — and excluded the two
test-quality observations. It was never a count of unique defects. The earlier "8 further
findings" figure for rounds 3–5 was a miscount; the durable table enumerates **6**.

The sixth round was attempted **seven** times in total across two authorized backends
(Luna XHigh and Astra XHigh) — five before this finishing pass, and two more at the final
head, one on each backend. Every attempt was refused with the same error (`The ChatGPT user
has reached their Subscription Sharing usage limit`), so the gap is provider capacity, not a
skipped check. It is OUTSTANDING, it is the one open merge condition, and the PR stays draft
until it is run. Self-review is not a substitute for independent review.

### Verdicts (as stated in the PR)
- **Code-merge: READY FOR FOUNDER REVIEW as a draft**, subject to the repository's human merge
  gate and the outstanding sixth independent review round.
- **Protected-flow activation: NO-GO.** The production trusted-envelope verifier denies every
  request; no independently authenticated protected human L4 ceremony exists.

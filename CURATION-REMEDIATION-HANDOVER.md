# Curation remediation — compaction checkpoint

## Mission, authority, model policy

Continue the founder's implementation/security/E2E request for #2089/#2088, NOT a new architecture audit. Lead is GPT-6.1 Sol High (verified PI_MODEL=gpt-6.1-sol). Only `openai/gpt-6-luna` subagents, explicit `thinking: high` for complex/security/review or `medium` bounded regressions; never set max_turns or any turn cap. No nested agent families. No merge, deployment, real intake, canonical registry mutation, manufactured approval, issue update/closure. Development PR is authorized and still owed. Fresh independent Luna reviews are required and NOT DONE.

## Exact workspace — do not edit original main

- Worktree: `/data/data/com.termux/files/home/.gaia-worktrees/curation-remediation`
- Branch: `dev/curation-secure-reconciliation`
- Latest committed HEAD before this handover: `7624ed445`.
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
No agent currently owns files. Fresh independent reviewers NOT dispatched yet; must use two new Luna High review agents after integration stabilizes (no implementation ownership).

## Background commands and evidence — notifications only, never poll

All tasks use default durable terminal notifications. Call bg_logs only AFTER matching notification; do not bg_status merely to wait.
- b3ef1f62f `Audited PR baseline tests`: terminal completed/exit0 collected: **179 passed in 5.07s**. This was a different focused subset, NOT exact224.
- bedb8629e `Submission idempotency regression tests`: terminal completed/exit0 collected: **78 passed in 1.73s**. This was before final security integration; not final-SHA acceptance.
- b37e8b928 `Exact 224 test baseline`: launched, terminal notification/result not yet collected. Exact nine-file audit command at isolated PR-head:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -p no:cacheprovider -q tests/test_intake_multi_packet_2088.py tests/test_intake_adapter.py tests/test_dev_ratify.py tests/test_push_from_file.py tests/test_intake.py tests/test_intake_approval_workflow.py tests/test_gaia_curate_discovery_packet.py tests/test_curate_command.py tests/test_curate_state.py`
- b3bc10791 `Integrated curation focused regressions`: launched on intermediate code; result notification not yet collected. Diagnostic, not final.
- b2469261a `Curation integration regression matrix`: launched on intermediate code including 24 focused files. Result notification not yet collected; source/test edits occurred after launch, so MUST rerun on frozen final code even if green.
- b5028be8c `Curation documentation contract checks`: launched; result notification not yet collected.
Task output files under original cwd `.pi/tasks/01a15932-8e8f-7677-af72-c4ac8ccfe524-23602/<taskid>.output`.
Latest short checks after user compaction request: compileall relevant source/tests PASSED, git diff --check PASSED, skill mirror parity PASSED, git diff against origin/main showed NO registry/skill-trees/docs/graph changes.

## Uncommitted changes at checkpoint (must preserve)

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
6. Dispatch TWO FRESH Luna High review agents read-only: (a) security L4/negative auth/governance, (b) candidate conservation/collision/idempotency. Explicit supported effort, no turn cap, only Luna. They must reproduce old cases on current code; not implementer self-review. Freeze their scope while they inspect. Repair findings and rerun proportionately, re-review required blockers.
7. Deliver CURATION-REMEDIATION-REPORT.md with file summary, all 26 matrix rows PASS/FAIL/SKIP, exact test logs/SHA, original attacks repaired at real boundaries, honest mocked-vs-real ceremony distinctions, reports, compatibility #2093/current main, remaining human actions and NO-GO for original #2089 and protected activation until independent ceremony exists. No production merge/deploy/intake.

Definition of done is not met yet. Do not claim completion from these edits or preliminary tests. Founder explicitly permits leaving protected flow blocked if independent human authority cannot be established; that does not make a mocked ceremony production success.

# Issue #2448 — durable evidence custody for ephemeral cloud Steward runs

> **Remediation round (Codex review 5887713453).** Sections 1-10 describe the first round and stay as the
> record; where they conflict with sections 11-15 (trust boundary, findings, verification, live v2 handoff,
> remaining rollout), sections 11-15 win. Notably: bundle `meta` now holds only `createdAt`; `writer` and
> `summary` are authenticated identity; verdicts are bound to builds; recovery never re-renders.

Handoff for founder review. Branch `infra/steward-cloud-receipt-preflight-2448`, PR #2449
(extended; see "PR structure"). Nothing here is merged, deployed or released.
Operational contract for agents: `.agents/skills/gaia-steward-full/cloud-custody.md`.
Scheduler handoff: `founder/steward/CLOUD_DAILY_BRIEF.md` (**not installed**).

## 1. What was wrong

Daily Steward maintenance runs on short-lived cloud agents. `gaia steward scan|dispatch`
write the scan receipt, the content-addressed dispatch receipt and the verifier's
receipt under checkout-local, gitignored `.gaia/steward/receipts/`; the builder's diff
and `steward-proof-transcript-v1` were files in the same container. `refs/heads/steward/ledger`
holds full-run state only. When the container died, a later host had nothing to verify
against, and `gaia steward verify` correctly refused (#2445).

A second, worse hole sat in `fullrun.py::_verifyOne`: on `no dispatch receipt` it called
`render_dispatch` and verified the old patch against the **new** receipt. On a fresh host
that mints a new envelope under today's policy and judges yesterday's patch by it. It is
removed.

## 2. Audit: what the daily job actually is

* The daily cloud job is the external scheduled task `Gaia Steward Daily`
  (`trig_01NLfT4PzgwkWh8utSzRRopE`, `CRON_TZ=Asia/Manila 45 10 * * *`, `claude-sonnet-5-5`,
  fresh session per fire; last fired 2026-11-13T02:50Z, succeeded). Its prompt is prose and
  **names no gaia command**, so `full` versus standalone `scan`/`dispatch`/`lane next` is
  chosen by the agent each day. Both paths are therefore covered.
* `.github/workflows/steward.yml` (cron `10 7 * * *`) is the separate Class A pulse.
  `.github/workflows/steward-full.yml` has no schedule ("until explicitly reauthorized").
  Neither is the cloud-subagent job and neither was changed.
* A separate scheduled task, `Gaia Steward Heartbeat - basic`, is disabled.

## 3. Architecture and durability decisions

| Decision | Why |
|---|---|
| New append-only Git ref `steward/evidence`, not the hot ledger | Every run reads and rewrites `ledger.json` (8 MiB bound). Diffs and proof transcripts would bloat every load. The ledger instead **indexes**: full-run work items carry `evidence: {dispatchBundle, buildBundle, evidenceCommit}`. |
| Reuse the ledger's CAS | `GitRefLedgerStore.publishTree` is the old `compare_and_swap` tail, extracted unchanged (no force, no lease option; a root commit cannot replace an existing ref; refuses to resurrect a deleted ref). `GitEvidenceStore` subclasses it. No database, paid service or second framework. |
| Content-addressed objects + one manifest per bundle | `objects/<sha256>` holds raw bytes; `bundles/<debt key>/<bundle id>.json` lists them. `bundleId` = sha256 of the canonical identity; anything altered after publication stops matching its name. Existing paths are never replaced. |
| Chain `dispatch -> build -> verdict`, each bundle names its parent | The verifier gets the exact receipt that authorized the work, never "the newest receipt for that debt". Ambiguity (several builds or chains) is refused until `--bundle` names one. |
| Byte-exact restore, original authority | Receipts are restored without re-rendering; a restored dispatch must still hash to its own id, its scan must be the scan it names, and a **newer** local dispatch for the debt makes `verify` refuse. `gaia steward verify` itself is unchanged. |
| Write is not success until read-back | Every publish re-fetches the remote ref and re-verifies every object. A push that landed but could not be read back raises; retrying finds the bundle durable, re-verifies it and does not duplicate it. |
| Publish-time validation | A build needs a non-empty diff with hunks and a proof that parses as `steward-proof-transcript-v1` within the packet's proof contract. `/dev/null`, empty, malformed or out-of-contract proofs are refused before anything is stored. |
| Explicit mode | `--evidence git` or `GAIA_STEWARD_EVIDENCE=git`. An unknown value is an error, never a silent downgrade, and is checked before any work is dispatched. |

Not changed: Class B authority, models, budgets, lane limits, Class C, Star Bar, CI gates,
`require_operator()`. Only the Lead writes shared coordination state.

## 4. Fail-closed boundaries (changed execution path)

| # | Boundary | Code | On failure |
|---|---|---|---|
| 1 | Dispatch issued | `custody_ops.publishDispatch`; called from `dispatch`/`lane next` (`commands/steward.py::_custodyDispatch`) and `fullrun._dispatchCandidate` | Nothing printed on stdout (no prompt), exit 4; full run: phase `blocked`, no builder action, no lane move |
| 2 | Builder accepts | `evidence accept` | builder stops |
| 3 | Patch + proof stored | `publishBuild`; `fullrun._recordBuild` (outside the ledger CAS closure) | outcome refused, step stays pending, re-record after repair |
| 4 | Verifier retrieves | `verifyFromCustody`; `fullrun._verifyFromCustody` | work deferred (existing `awaiting-action`), never re-dispatched |
| 5 | Outcome recorded | `publishVerdict` | deferred |
| 6 | Before READY / PR | `evidence ready` re-reads the whole chain; requires dispatch -> build -> verdict with a mechanical verdict of `pending` | not ready, exit 4 |

`BLOCKED: provenance unavailable` is exit 4 everywhere. Without custody, `full run --verify`
now defers (with that banner) instead of re-dispatching. A mechanical verdict is never
acceptance; `ready` says `independentVerifierRequired: true`.

## 5. Tests

See section 7 for results. New files: `tests/steward/test_custody.py` (library, real git,
separate clones, "cloud A disappears" = `rmtree`), `test_custody_fullrun.py` (full runner
across two checkouts), `test_custody_cli.py`.

| Required scenario | Test |
|---|---|
| Cloud A dispatches, B verifies after A is gone | `test_cloud_a_dispatches_terminates_and_cloud_b_verifies_the_original`, `test_full_run_cloud_a_dispatches_and_builds_cloud_b_verifies_after_a_disappears` |
| Original authority, not today's policy | `test_restored_receipt_is_the_original_authority_not_todays_policy` |
| Missing / altered receipt | `test_altered_receipt_bytes_are_refused`, `test_missing_receipt_object_is_refused`, `test_altered_manifest_no_longer_matches_its_bundle_id`, `test_a_dispatch_edited_before_publication_is_refused` |
| Missing / wrong original scan | `test_missing_original_scan_is_refused_at_dispatch_time`, `test_a_scan_that_is_not_the_one_behind_the_dispatch_is_refused` |
| Wrong baseline, stale proof | `test_wrong_baseline_is_refused_on_restore`, `test_a_newer_local_dispatch_cannot_stand_in_for_the_original`, `test_a_proof_for_another_contract_is_stale_and_refused` |
| Missing / empty / malformed proof | `test_missing_empty_or_malformed_proof_is_refused` (5 cases), `test_an_empty_or_hunkless_diff_is_refused` |
| Interrupted persistence | `test_interrupted_push_leaves_nothing_visible_and_is_recoverable`, `test_push_that_lands_but_cannot_be_read_back_is_never_success_and_retry_is_idempotent`, `test_record_is_refused_while_custody_is_down_and_succeeds_once_repaired` |
| Concurrent writers | `test_concurrent_writers_preserve_every_bundle` (4 threads on 4 clones, one linear history) |
| Resume never duplicates | `test_resumed_run_does_not_duplicate_the_dispatch`, `test_resumed_full_run_does_not_publish_or_dispatch_twice` |
| No re-dispatch to legitimize a patch | `test_without_custody_a_missing_original_receipt_defers_and_never_redispatches` |
| Quiet day / blocked day | `test_quiet_day_is_a_genuine_noop`, `test_quiet_day_with_custody_enabled_is_a_clean_noop`, `test_full_run_blocks_when_dispatch_cannot_be_made_durable` |

These are **tests and simulations** (separate directories and clones on one machine). They
are distinguished from the real cross-environment run in section 6.

## 6. Real cross-environment handoff (not a test, not a simulation)

Executed 2026-11-13 against the real GitHub remote, using a clearly named **rehearsal ref**
`steward/evidence-rehearsal-2448` (selected with `GAIA_STEWARD_EVIDENCE_REF`; production
`steward/evidence` was **not** created). Identical code path to production; only the ref name differs.

| Step | Where | What happened |
|---|---|---|
| Live scan | cloud A (this session's container, PR head `0af8850d`) | `gaia steward scan`: 264 open debt, authority B=183, C=81, coverage unknown 0. Not a quiet day. |
| Dispatch | cloud A | `gaia steward dispatch debt:unused_import:scripts-archive-add-hermes-batch-py:d44c8312efe0535a --prompt --evidence git`. Real dispatch `dispatch-460979a6df78fdd0d323`, receipt `steward-20261113T064623Z-9b229a3774fcf358`, baseline `0af8850d988e32f0cd184ce643f5da298cec158f`. The prompt reached stdout only after custody printed "dispatch bundle fc09a9b1fe7d published, read back from 163fea52d0a3". |
| Build | cloud A, in a scratch worktree | `evidence accept` passed. A real two-line fix (remove `import os`, `from datetime import datetime`); finding reproduced by a real `gaia steward scan`; `compileall` and `pytest tests/steward/test_sensors_code.py` (155 passed) recorded in a valid proof transcript. `evidence publish-build` (model `sonnet-5-5`, effort `high`) stored diff + proof, read back from `eb523435`. |
| Handoff | **cloud B: a separate cloud session** (`session_018A6ag3sbPkcGdR5dneojRE`, Haiku 5.5 medium, host `vm`, fresh clone of the branch at `0af8850d`, no access to A's filesystem) | `evidence status` saw dispatch + build; `evidence verify` retrieved and authenticated the originals, ran the canonical mechanical verifier and published the verdict (read back from `14c9ad68`): **verdict `pending`**, exit 0; `evidence ready` exit 0. |
| Independent re-check | a third fresh clone of the real remote, by the lead | `evidence ready` exit 0, same bundle ids and hashes. |

Hash comparison (A's originals vs the bytes cloud B restored): dispatch receipt `2c7d9be4…96d0b`,
scan receipt `3f778a89…fa20`, diff `3b81aafb…1d0d`, proof `e2ffd934…aa0c` are identical on both hosts.
Bundle ids: dispatch `fc09a9b1…a7a`, build `5fb627c6…20af`, verdict `cfa0dea5…63a0`.
Verification receipt `steward-20261113T065439Z-cae03cf1b818c29d` (sha256 `c628b996…b41e`).

Limits of this evidence, stated plainly:

* The lead (this session) acted as dispatcher **and** builder, so no independent Steward
  builder/verifier pair ran. Cloud B produced only the **mechanical** verdict, which is `pending`
  (it can never be `accept`). No independent Sonnet 5.5 Medium verdict was obtained and none is claimed.
* The patch was never landed, the debt is still open, and no lane or ledger state was written.
  It is a rehearsal artifact, not repair work. #2445 was not touched.
* B's own report is another session's output; the hash comparison and third-clone `ready` above were
  re-run by the lead rather than taken from it.
* Cloud B's `.gaia/` already held an empty-looking `steward/` directory before its first step
  (created at session start); its step-7 listing shows only restored originals plus its own verify
  outputs.
* The full runner's cross-checkout path (ledger pointers) is covered by tests only, not run live.
  Nothing used the production `steward/ledger`.

Leftovers on the shared remote: ref `steward/evidence-rehearsal-2448` (3 bundles). Remove with
`git push origin --delete steward/evidence-rehearsal-2448` once reviewed; it affects nothing else.

## 7. Verification results

* `tests/steward/test_custody*.py`: 42 passed (library 32, CLI 4, full-run 6).
* Whole `tests/steward` directory: 4274 passed, **47 failed**, all in `tests/steward/prmaintenance/`
  (`test_executor`, `test_gate`, `test_r19_review_regressions`, `test_exact_tree`,
  `test_executor_processes`). The identical 47 fail on a clean `origin/main` worktree in this sandbox
  (jinja2/SSL/git-environment dependent), so none come from this change. (jinja2 was installed
  mid-session; failures remained.)
* Regression runs before/after the refactor: `test_ledger`, `test_cli`, `test_cli_contract`, `test_fullrun*`,
  `test_ordinary_shared_ledger` all pass.
* `scripts/quick_validate_skill.py` on the three edited skills, `scripts/validate_skills.py`
  (passed, warnings pre-existing), `scripts/sync_agent_skill_mirror.py --check`: pass.
* Finding in the base PR: `tests/steward/test_steward_skills.py` was red on #2449's original head
  (root skill 192 > 160 lines; `gaia steward full abandon` did not parse). #2449's own CI did not run it.
  Fixed here by moving the contract into `cloud-custody.md` beside the skill (root skill back to 160 lines).
* GitHub CI on the final head: see the PR (recorded in the handoff comment, section 9).

## 8. Risks and open items

1. **Trust anchor.** Superseded by section 11: pins and the ledger binding are implemented; the server-side
   append-only ruleset is a founder gate and is **not verified**.
2. **Production ref not yet created.** The first real daily run with custody creates `steward/evidence`.
3. **Scheduler not changed.** `CLOUD_DAILY_BRIEF.md` is exact replacement text; until installed, daily
   agents will not use custody. The task's prompt does not name a gaia command, so adoption depends on the agent.
4. **Independence.** Custody enforces durability and authenticity, not agent independence. Builder != verifier
   remains enforced only by the full runner (`forbiddenAgentIds`) and the brief.
5. **Branch scope.** Resolved: the founder applied `skip-scope-check`; the scope check is skipped on the latest heads.
6. **Retention.** `steward/evidence` grows without bound (append-only by design); archival/compaction is a
   later, founder-gated decision. Per-object bound 8 MiB.
7. `lane next --evidence git` and `full run --evidence git` live runs were not performed; both are covered
   by unit/integration tests and share the code exercised live (the live dispatch used `dispatch --prompt --evidence git`).

## 9. PR structure

#2449 is **extended**, not split. Its documentation-only guard and this implementation describe the same
six boundaries; a separate implementation PR would leave #2449 asserting "not implemented" and duplicate
policy text. The interim block was replaced (not duplicated) by `cloud-custody.md`. Trade-off: a larger
diff and the scope-check item above; mitigated by this document and a per-file map:
`src/gaia_cli/steward/custody.py` (store + bundles), `custody_ops.py` (boundaries), `fullrun.py`
(dispatch/record/verify hooks), `commands/steward.py` (CLI), `ledger.py` (CAS tail extracted), tests,
skills + mirrors, and `founder/steward/CLOUD_DAILY_BRIEF.md`.

## 10. Rollback

* Runtime: custody is opt-in. Unset `GAIA_STEWARD_EVIDENCE` / omit `--evidence git`; behavior is the
  pre-change path except that `full run --verify` no longer re-dispatches a missing receipt (that was a defect).
* Code: revert the PR's commits on the branch (or `git revert -m` the merge). `publishTree` is a pure
  extraction; `compare_and_swap` behavior is unchanged and covered by `test_ledger.py`.
* Scheduler: remove the appended section from the `Gaia Steward Daily` prompt (nothing was installed).
* Remote: `steward/evidence*` refs are append-only and unused by anything else; delete a ref with
  `git push origin --delete <ref>` (founder action).

---

# Remediation round — Codex review 5887713453 (HEAD at review `e8b97907`)

## 11. Production trust boundary for `steward/evidence` (finding 3)

### 11.1 Audit: who can create, update, force-push and delete the ref

Facts established from this session, with what each does and does not prove:

| Question | Observation | Reading |
|---|---|---|
| Who has write access? | `list_repository_collaborators`: **3 direct collaborators, all `admin`**: `mbtiongson1`, `milim-gaia`, `nova-gaia`. | No non-admin writers exist. Admins can edit or bypass classic branch protection and can administer rulesets. |
| Which identity do cloud Steward sessions push as? | `get_me` in this session returns `mbtiongson1`, the founder's own account. Cloud A and cloud B (both spawned sessions) pushed to origin successfully. | **GitHub cannot distinguish a Steward agent from the founder or from any other agent session.** Ref permissions alone can never prove "this writer was an authorized Steward lead". |
| Branch protection | `list_branches`: every listed branch is `protected: false` except `main`. This covers classic protection only. | `steward/*` has no classic protection. |
| Rulesets | Codex reported one ruleset, "Main Ruleset", covering `refs/heads/main` only. I could not read rulesets here (no API tool; `gh` is out of scope for this session). | **Not verified. Treat `steward/*` as unprotected.** |
| Create | I created a throwaway ref `steward/evidence-authz-probe-2448` with plain `git push` from this session: **allowed**. | Any session can create any `steward/*` ref. |
| Update (fast-forward / non-ff) | Non-ff push rejected by git itself; `git push --force` to the same ref: **succeeded** (`+ ... (forced update)`). | **A force-push can rewrite `steward/evidence` today.** |
| Delete | Three `git push --delete` attempts failed with `remote end hung up unexpectedly` / `unexpected disconnect while reading sideband packet`. | **Inconclusive.** The failure could be this session's git proxy or GitHub; I cannot tell, and it must not be read as "deletes are blocked". |

Content hashes (already present) prove the stored **bytes** were not altered. They do not prove who wrote
a bundle, and a writer who can force-push can replace the whole ref with a consistent alternative.

### 11.2 What the code now enforces (smallest compatible solution, no new infrastructure)

1. **Writer metadata is authenticated identity.** `writer` (role, agent id, model, effort, run id) and the build `summary`
   moved from the unauthenticated `meta` into the bundle `identity`, which `bundleId` hashes. Substituting any of them
   changes the id; `test_writer_metadata_cannot_be_substituted_without_changing_the_bundle_id`. Only `createdAt` stays
   in `meta`, and is informational.
2. **A verifiable relationship between dispatch, ledger and custody chain.** In full runs the ledger work item records
   `evidence.dispatchBundle` / `buildBundle` (written only by the lease holder). Verification now requires the custody
   chain to start at exactly that dispatch bundle and dispatch id, and pins the build bundle, **before any byte is
   written to the checkout** (`restoreChain(expectDispatchBundle, expectDispatchId, pinBundle)`).
3. **Pins from outside the ref.** `--pin-bundle` (a full id that must appear in the chain) and `--pin-commit` (must
   still be an ancestor of the evidence tip) accept identifiers recorded elsewhere: the ledger, or the `ready` record
   the Lead posts on the PR. A substituted chain, or history rewritten after the pin was taken, is refused
   (`test_pins_accept_the_recorded_chain_and_refuse_a_substituted_one`, `test_a_rewritten_history_is_detected_by_the_pinned_commit`).
4. **Honest scope.** `evidence ready` prints `writerAuthorization: not verified by this command` and never claims the
   ref is protected.

What this does **not** do, and cannot do without a server-side control: stop a writer from appending a new
self-consistent chain, or from force-pushing before any pin exists. Pins only help once the identifier lives
somewhere the attacker did not also rewrite, and every agent session here shares one GitHub identity.

### 11.3 Rollout gate 1 (REQUIRED, founder-side): server-side append-only ruleset

Because the sole writer identity is shared and admin, the one control that survives a compromised or misbehaving
session is a ruleset **with no bypass actors** that makes the refs append-only. Create it as a repository ruleset
(Settings -> Rules -> Rulesets -> New branch ruleset), or:

```json
{
  "name": "steward-evidence-append-only",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": {
    "ref_name": {
      "include": [
        "refs/heads/steward/evidence",
        "refs/heads/steward/evidence-*",
        "refs/heads/steward/ledger"
      ],
      "exclude": []
    }
  },
  "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]
}
```

`POST /repos/gaia-research/gaia-skill-tree/rulesets` with that body (admin). It deliberately has no bypass actors:
rewriting or deleting the refs then requires disabling the ruleset, which is itself an audited admin action.
It does not restrict ordinary fast-forward appends, which Steward needs. `steward/ledger` is included because the
ledger pointers are the authority anchor; the ledger store never force-pushes or deletes, so this changes nothing for it.

**Order matters.** Deletion is blocked once the ruleset is active. Before enabling it, delete the refs that should not
persist (or keep them): `steward/evidence-authz-probe-2448` (my empty throwaway probe, **I could not delete it**; see
11.1) and, when the evidence is retired, `steward/evidence-rehearsal-2448` and `steward/evidence-rehearsal-2448-v2`.
The pattern `steward/evidence-*` intentionally covers rehearsal refs too, so the negative probe in 11.4 is safe.

### 11.4 Verification (do not claim protection before this passes)

1. `python scripts/check_steward_evidence_protection.py --live` (needs admin read; exits 0 only if an **active** branch
   ruleset with **no bypass actors** blocks `deletion` and `non_fast_forward` for `steward/evidence`, the rehearsal pattern
   and `steward/ledger`; exits 2 "UNVERIFIED" if rulesets cannot be read; 1 if anything is uncovered). It also requires coverage of refs that
   do not exist yet (`steward/evidence-future-probe`, `steward/evidence-rehearsal-9999-v9`), so a ruleset naming only
   today's branches fails; see section 17. Unit-tested in `tests/steward/test_evidence_protection.py` (26 cases).
2. Empirical negative probe on a **non-production** ref covered by the pattern, from the identity the daily job uses:
   push a commit to `steward/evidence-authz-probe-N`, then `git push --force` an unrelated commit (must be rejected),
   then `git push --delete` (must be rejected). Never probe `steward/evidence` itself.

### 11.5 Rollout gate 2 (OPTIONAL, founder decision): a dedicated Steward identity

If the founder wants "only the Steward may append" rather than "nobody may rewrite", the cloud job needs its own GitHub
identity (a machine account or GitHub App) and an additional ruleset rule restricting creation/updates to it. That is new
infrastructure and a credential to manage, so it is **not** introduced here; the demonstrated need is real (section 11.1:
one shared admin identity) but gate 1 plus pins covers rewrite and substitution, and the remaining forgery-by-append
risk is bounded by the ledger pin and by the independent verifier still being required.

### 11.6 Decisions and status

| Item | Status |
|---|---|
| Writer metadata authenticated as bundle identity | **Implemented and tested** |
| Ledger-to-custody binding, pins, rewrite detection | **Implemented and tested** |
| `steward/evidence` protected against force-push/delete | **NOT protected. Founder gate 1; not verified.** |
| Dedicated Steward identity | Optional gate 2; not done |
| `Gaia Steward Daily` schedule | **Unchanged and must stay unchanged until gate 1 verifies** |

## 12. Codex findings: resolution

| # | Finding | Resolution |
|---|---|---|
| 1 | Recovery/adoption re-render a prompt from today's policy | `_recoverLostPackets` and `_reemitBuild` no longer call `render_dispatch_prompt` when custody is on. The dispatch bundle now stores the **exact builder prompt**; recovery restores it byte for byte (`custody_ops.originalPrompt`), authenticates the dispatch, and checks it is the ledger's dispatch. If it cannot, the pending action keeps its authority, shows `BLOCKED: provenance unavailable` in `nextAction` (or the run blocks on adoption), and nothing is superseded, re-dispatched or substituted; resume after repair restores it. Tests: ordinary resume and cross-container adoption with narrowed policy, a negative control proving the old path silently dropped an authorized path, custody-down block, recovery after repair, adoption blocked with no fallback dispatch. |
| 2 | Verdict receipt not bound to the exact build | `authenticateVerdict` recomputes the diff hash and proof-transcript hash from the build's own bytes (`content_hash`, the canonical verifier's own function) and checks debt and dispatch. Enforced at publication, on **every chain load** (`checkChain`) and in `readiness`. Verdict identity restates what it binds. Legacy unbound verdicts are refused with a clear message. Tests: same dispatch / different diff, different proof, different debt, a forged verdict written directly to the ref (refused on retrieval, `readiness` and `restore`), edited binding fields, no-change build, genuine chain still passes. `pending` is still never `accept`. |
| 3 | Writer authorization unproven | Section 11: audited, code hardened, server-side gate documented and checkable, **not claimed protected**. |

## 13. Verification: exact commands and results (remediation round)

Run from the repository root of this branch, `pip install -e .` plus `pip install jinja2 ruff pytest`.

| Command | Result |
|---|---|
| `python -m pytest tests/steward/test_custody.py tests/steward/test_custody_cli.py tests/steward/test_custody_fullrun.py tests/steward/test_evidence_protection.py -q` | **all pass**: library 46, CLI 4, full-run 11, protection checker 13 (74 total) |
| `python -m pytest tests/steward -q` (full steward directory, local sandbox) | 4306 passed, **47 failed**. The 47 are the identical set (diffed id by id) that fails on a clean `origin/main` worktree: all in `tests/steward/prmaintenance/` (`test_executor`, `test_gate`, `test_r19_review_regressions`, `test_exact_tree`, `test_executor_processes`), caused by this sandbox (no GitHub/SSL/git-environment, jinja2 absent at first). **None are in custody, fullrun, ledger or CLI code.** |
| `python scripts/sync_agent_skill_mirror.py --check` | in sync |
| `python scripts/validate_skills.py` | passed (pre-existing warnings only) |
| `python -m pytest tests/steward/test_steward_skills.py -q` | 49 passed (root skill still 160 lines; detail lives in `cloud-custody.md`) |
| `ruff check` on every changed file | clean except one advisory `BLE001` in a test thread helper |
| `python scripts/check_steward_evidence_protection.py --live` | **NOT RUN here** (no admin API access in this session). It is the founder's verification gate, section 11.4 |

Mutation/negative controls: `test_negative_control_without_custody_a_lost_prompt_is_re_rendered_from_todays_policy`
reproduces the original defect (the pre-custody path silently drops an authorized path under narrowed policy and mints
a new dispatch receipt); the custody-on tests assert the opposite.

### CI (GitHub)

* **Reviewed head `e8b97907`: `Test, Build, and Smoke Test` completed `success`** (job 131747862442, 34 min, Full tests step 25 min, sdist/wheel
  build and clean-environment install all green). This answers Codex's "still running" note. The 47 local failures are therefore
  sandbox-specific, not regressions: the same tests pass in GitHub's environment.
* Branch Scope Check: **skipped** after the founder's `skip-scope-check`.
* Heads after this round are recorded in the PR comment for the exact final HEAD.

## 14. Live cross-environment handoff, round 2 (real remote, binding + prompt preservation)

The format changed in this round (bundle identity, prompt artifact, verdict binding), so the round-1 rehearsal evidence
is the pre-binding format. `steward/evidence-rehearsal-2448` is **preserved untouched** as requested; the new code reads
its dispatch -> build chain but **refuses its unbound verdict** with an explicit message (verified on the real ref:
`BLOCKED: ... verdict bundle's binding does not match its build and receipt`; now worded "predates verdict binding").
A second real handoff was run on a new ref, `steward/evidence-rehearsal-2448-v2`, against baseline `b7fa338a2ca844c7aeeec77e360961a9c1fd8344`.

| Step | Where | Result |
|---|---|---|
| Dispatch | cloud A (this container) | `gaia steward dispatch DEBT --prompt --evidence git`: dispatch bundle `af7ef3aa599e…`, scan `2bbee023…`, dispatch receipt `5851ebf1…`, **builder prompt preserved** (`bc8aec39…`). Read back from `c56cec69`. |
| Build | cloud A, scratch worktree | `evidence accept` ok; same two-line unused-import fix; `gaia steward scan` reproduction, `compileall`, `pytest tests/steward/test_sensors_code.py` (155 passed) recorded in a valid proof; `publish-build` -> build bundle `0e606af0…`, commit `c08df60a`. |
| Negative pin | **cloud B2: a separate cloud session** (Haiku 5.5 medium, host `vm`, fresh clone at `b7fa338a`) | `verify --pin-bundle aaaa…` exit **4**: `the pinned bundle aaaaaaaaaaaa is not part of the custody chain; refusing a substituted chain`; nothing written to `.gaia/steward/receipts`. |
| Verify | cloud B2 | `verify --bundle 0e606af0… --pin-bundle 0e606af0… --pin-commit c08df60a…` exit **0**, verdict **`pending`**, verdict bundle `67fa1ca2…` bound to that build, published and read back from `f424afaf`. |
| Ready | cloud B2 | `ready --pin-bundle 67fa1ca2… --pin-commit f424afaf…` exit **0**; output states `writerAuthorization: not verified by this command`, `independentVerifierRequired: true`. |
| Re-check | lead, third fresh clone of the real remote | `readiness` with pins (`--pin-commit c08df60a`) ok; hashes of A's receipts (`5851ebf1…`, `2bbee023…`) and diff/proof (`3b81aafb…`, `d790c447…`) equal what B2 restored; **the preserved builder prompt is byte-identical to the prompt A printed to stdout**. |

Limits, same as round 1: lead acted as dispatcher and builder, so only the **mechanical** verdict exists; the patch was not
landed; B2's report is another session's output and the checks above were re-run by the lead; the full runner's live
cross-container adoption is proven by tests (section 12), not by a live run. New leftover refs on origin:
`steward/evidence-rehearsal-2448-v2` and `steward/evidence-authz-probe-2448` (empty-tree commit; my three attempts to
delete it failed with `remote end hung up`, so it needs a founder `git push origin --delete`, which a ruleset from 11.3 would then block; delete it first).

## 15. Remaining rollout steps (all founder-side; nothing is deployed)

1. Review and merge decision for #2449 (no merge authorized to me).
2. **Gate 1:** delete `steward/evidence-authz-probe-2448`; create the append-only ruleset (11.3); run
   `python scripts/check_steward_evidence_protection.py --live` and the negative probe (11.4). Until both pass the production
   ref is **not** protected.
3. Optional gate 2: a dedicated Steward identity (11.5).
4. Only after 2 and the final review: install `founder/steward/CLOUD_DAILY_BRIEF.md` into `Gaia Steward Daily`
   (`trig_01NLfT4PzgwkWh8utSzRRopE`), and read the task back to verify. **I did not change the schedule.**
5. When the evidence is no longer needed for review: delete the two rehearsal refs (before enabling the ruleset, or temporarily disable it).

## 16. Rollback (additions)

New files: `scripts/check_steward_evidence_protection.py`, `tests/steward/test_evidence_protection.py`; changed `custody*.py`,
`fullrun.py`, `commands/steward.py`. Revert the remediation commit to return to the round-1 behavior; custody remains opt-in and
the round-1 rollback in section 10 still applies. No scheduler, ruleset or production ref was changed by this round.

## 17. Codex re-review of `5e1abbbb`: two remaining findings (round 3)

### 17.1 Finding 1: custody must never run on a local ledger

**Defect.** `--ledger auto` (the default of `gaia steward full run|record`) probed the remote and silently picked the local
file ledger when it was down, so a cloud run with `GAIA_STEWARD_EVIDENCE=git` could create run, lease and quiet-day state
that dies with the container and that no other agent sees. The brief did not name `--ledger git`.

**Fix (enforced in code, two layers).**
* `FullRunConfig.__post_init__` raises `CustodyRefused` when custody resolves to `git` and the store is not `shared`
  (any local-file ledger). This holds for library callers, the `--evidence git` flag and the environment variable alike.
* `StewardCommand._fullStore(..., custody=True)` returns the shared git-ref ledger for `auto` and `git` with no
  reachability probe and no fallback; `local` is refused by the config check. When the shared ledger cannot be read,
  `LedgerUnavailable` becomes `BLOCKED: provenance unavailable: shared steward ledger unreachable` and exit **4**, quiet or not.
* Custody off is unchanged: `auto` still falls back to local, `local` still works (negative control in the tests).
* `founder/steward/CLOUD_DAILY_BRIEF.md` now tells cloud agents to pass `--ledger git` on `full run` and `full record`, states
  the BLOCKED behaviour and forbids retrying with `--ledger local`, another checkout or custody off. The shared skill note
  `cloud-custody.md` says the same (mirrored to `.claude/skills/`).

**Tests** (`tests/steward/test_custody_ledger.py`, 13). With the source reverted 11 of the 13 fail; the other 2 are the
legacy-behaviour controls.
* unreachable origin + `GAIA_STEWARD_EVIDENCE=git` on a quiet, no-debt scheduled `full run`, with `--ledger` omitted,
  `auto` and `git`: exit 4, BLOCKED banner, and **no** `.gaia/steward/full/ledger.json` (nor any `.gaia/steward/full`) created;
* the `--evidence git` flag behaves like the environment variable;
* `--ledger local` with custody on and a reachable remote is refused, no local ledger created;
* `full status` and `full record` with the remote down also create nothing;
* `_fullStore` returns the shared store for `auto`/`git` without probing; a local store cannot back a custody config;
* negative control: with custody off, `auto` and an unreachable remote does create `ledger.json` and reports `local-file`.

### 17.2 Finding 2: the protection checker certified concrete names only

**Defect.** `REQUIRED_REFS` was three exact branch names, so an active, bypass-free ruleset listing only those names passed
while `steward/evidence-rehearsal-2448-v2`, `steward/evidence-authz-probe-N` and every future `steward/evidence-*` ref stayed
unprotected.

**Fix** (`scripts/check_steward_evidence_protection.py`).
* The checked set now adds the existing v2 and probe refs and two synthetic refs that will never exist
  (`FUTURE_REFS`). Only a pattern can cover the latter, so a names-only ruleset reports `UNPROTECTED` for them and exits 1.
* Matching is stricter than `fnmatch`: `*` stays inside one path segment and `**` crosses segments (GitHub semantics);
  `~ALL` is understood.
* Any `exclude` whose literal prefix can reach `steward/evidence*` or `steward/ledger` voids the ruleset, so a carve-out
  such as `steward/evidence-probe-*` cannot hide behind a covering include.
* Still required: `active`, branch target, no bypass actors, `deletion` and `non_fast_forward`.

**Tests** (`tests/steward/test_evidence_protection.py`, 13 to 26): the three-concrete-refs ruleset is covered for every
existing ref, **fails** for both future refs and the whole check; a partial wildcard (`evidence-rehearsal-*`) fails;
exclusions inside the namespace (five variants incl. `~ALL`) fail; an unrelated exclusion passes; `~ALL` and
`steward/**` pass; single-star segment semantics; CLI exit 1 with `UNPROTECTED refs/heads/steward/evidence-future-probe`.
The documented ruleset in 11.3 still passes unchanged. The checker was **not** run live here (no admin API access).

### 17.3 Results (round 3)

| Command | Result |
|---|---|
| `pytest tests/steward/test_custody.py test_custody_fullrun.py test_custody_cli.py test_custody_ledger.py test_evidence_protection.py test_fullrun_cli.py test_ordinary_shared_ledger.py test_fullrun.py tests/test_cli_reference_steward.py tests/steward/test_steward_skills.py` | **251 passed** |
| `ruff check` on the changed source, script and tests | clean |
| `python scripts/sync_agent_skill_mirror.py --check` | in sync |
| `python scripts/validate_skills.py`, `quick_validate_skill.py .agents/skills/gaia-steward-full` | passed |

The full `tests/steward` directory was not re-run: the change touches only the ledger-selection path and the checker, both
covered above, and round 2 already recorded the 47 sandbox-only baseline failures. CI on the final HEAD is recorded in the PR comment.

### 17.4 Founder-side gates (unchanged)

Delete `steward/evidence-authz-probe-2448`; create the 11.3 ruleset; run `check_steward_evidence_protection.py --live`
(it now also proves the wildcard namespace) and the 11.4 negative probe; optional dedicated Steward identity; install the
brief into `Gaia Steward Daily` only after those and the final review; delete the rehearsal refs when evidence is retired.
No ruleset, ref deletion, merge, deploy or scheduler change was made in this round.

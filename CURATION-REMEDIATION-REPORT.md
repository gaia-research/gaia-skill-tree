# Curation remediation — reconciliation receipt

**Base:** `origin/main` @ `e1a870579` (contains #2097, #2093, #2099, #2035).
**Head:** `dev/curation-secure-reconciliation` (see `git rev-parse HEAD`).
**Related:** #2088, PR #2089 (open, unmerged @ `32ecd0df7`), #2118, #2117, original architecture audit.

Two verdicts are reported separately and are **not** the same claim:

- **Code-merge verdict: NOT READY — draft.** A scoped fail-closed safety repair
  pending the targeted test repairs, the two bounded walkthroughs, and an
  independent Luna runtime review. Main's paused `gaia curate` behavior is
  preserved.
- **Protected-flow activation verdict: NO-GO.** The production trusted-envelope
  verifier intentionally rejects every request because an independently
  authenticated, protected human L4 ceremony is not demonstrably available.
  Locally authored `humanReview` metadata and unit-test mocks are **not**
  approval authority, and neither curation lane may use them to authorize a
  protected handoff or a canonical mutation.

## 1. What is already on main (not contributed by this branch)

| Item | State on main | Disposition |
|---|---|---|
| #2093 lowercase contributor identity + collision protection | merged `cddb09ce` | **Preserved.** Branch keeps it; branch's identity work adds collision-resistant *filenames* on top. |
| #2099 curation checkpoint reconciler (`gaia_cli/curationCheckpoint.py`), `gaia curate --resume` active/resolved blockers, source revisions, legacy ledger → empty checkpoint | merged `7d405ad6` | **Preserved.** `commands/curate.py` and `tests/test_curate_command.py` are restored byte-identical to main. |
| #2097 fleet integration (incl. #2095 authenticated issue-backed intake recovery + immutable Actions handoff) | merged `8285da49` | **Preserved.** No workflow, recovery, or provenance change. |
| #2035 trust freshness / API projection repair | merged `40b5800e` | Out of scope; untouched. |
| #2088's broader multi-packet implementation | owned by #2088 / PR #2089 | **Not duplicated.** Branch aligns the intake seam to the #2089 CLI commits already cherry-picked, and does not take ownership of broader multi-packet scope. |

Main's `src/gaia_cli/curation/` was **not modified** by main's 113 commits since
the merge base, so the branch's overlap with main is limited to
`src/gaia_cli/commands/dev/__init__.py`, which merged without conflict and
preserves main's `timeline-resort`, `provenance`, and `evidence-seed` commands
alongside the branch's `--authorization-envelope` flag.

## 2. What this branch uniquely contributes

Aligned to #2118's five proven invariants:

| #2118 invariant | Branch contribution | File |
|---|---|---|
| Authenticated L4 for the **exact reviewed payload and revision**; fail closed on missing/stale proof; genuine outside-top-K still possible; required for **both** lanes | Independent review payload binding (candidate ID, exact named identity, full selected generic definition + prerequisites, source URL/revision/digest, packet digest, assessment digest, live catalog + rubric digests, exact route, exact manifest-byte digest, complete inventory accounting, continuation references). Authorization envelope and display-only `humanReview` are excluded from the hashed proposal, so a carrier cannot alter what was reviewed. Production verifier **denies all** requests pending a real ceremony. | `curation/authorization.py`, `intakeAdapter.py`, `commands/dev/ratify.py`, `commands/pushFromFile.py` |
| Lossless candidate identity; collision-resistant persistence with explicit ownership and safe failure | Digest-owned filenames (readable prefix + full SHA-256 of the exact candidate ID) so `synthetic/a-b` and `synthetic/a/b` cannot collide; ownership checked under a process lock before replacement; symlink escapes rejected; exact lowercase `contributor/slug` identity separate from candidate locator and generic ID. | `prefill.py`, `curation/assessment.py`, `curation/reconciliation.py` |
| Complete inventory accounting: every expected candidate exactly one of review-ready / deferred / rejected / proven duplicate; six named skills on one generic stay six rows; **no giant fan-out runtime** | Frozen inventory (candidate ID, exact named identity, source revision/digest, detached packet input, stable task ID) + deterministic reconciliation independent of arrival order; exactly one final outcome per candidate; shared generic never collapses named rows; conflicting generic definitions defer deterministically; missing/failed candidates remain explicit deferrals. | `curation/reconciliation.py` |
| Consistent fresh current-catalog validation; truthful exact-dedupe; content-derived idempotent submission and continue-existing-intake | Live catalog comparison against the **same builder** that produced the frozen snapshot (one discovery rule, no false "stale" verdicts); full selected-definition and catalog-wide semantic drift detection; unreadable canonical files fail closed; exact-dedupe executed rather than asserted; content-derived batch IDs and receipts; uncertain issue creation fails closed and requires explicit `--existing-intake` recovery; original batch/issue references preserved for continuation. | `curation/freshness.py`, `prefill.py`, `curation/submission.py`, `push.py`, `prWriter.py`, `commands/push.py` |
| Preserve #2093 protections and immutable Actions handoff/recovery | No change to lowercase enforcement, provenance verification, or recovery semantics; intake continuation reuses the original issue/batch. | verified by the retained #2093/#2050/#2055 test suites |

## 3. Retained / simplified / dropped

| Area | Verdict | Rationale | Action |
|---|---|---|---|
| `curation/authorization.py` + intake/ratify seam | **RETAIN** | Directly implements #2118 invariant 1. | Unchanged. |
| `curation/reconciliation.py` (shared accounting contract) | **RETAIN** | The shared contract both lanes use; #2118 invariant 3. | Kept; narrowed so a plain DEFER does not require a fabricated assessment (see below). |
| `curation/freshness.py`, `prefill.py` identity/ownership | **RETAIN** | #2118 invariants 2 and 4. | Kept, with the catalog comparison fixed to one builder and main's assessment candidate-ID guard restored. |
| `curation/submission.py` | **RETAIN (narrow)** | Replay-safe identity + uncertain-create recovery + continuation. Not expanded into #2088's broader multi-packet scope. | Kept. |
| `curation/fanout.py` (bounded, model-neutral callable workers) | **RETAIN as optional assisted-lane support** | #2117 allows "bounded fan-out as needed"; it is not a shared contract and confers no authority, no canonical mutation, and no separate workflow state machine. Cooperative cancellation is honestly disclosed. | Kept, explicitly optional. |
| Branch's executing `curation/orchestrator.py` CHAIN engine (375 lines) + `commands/curate.py` rewrite + its 234-line test file | **DROP** | With main's canonical `gaia curate` restored, the engine had **no entry point**; it was the "new orchestration framework" #2117 forbids and it broke 5 of main's own canonical tests. The invariants it provided (identity, accounting, freshness) live in the shared seam, which both lanes use. CHAIN *support* is preserved as sequential use of the existing preparation primitives plus shared reconciliation — no second workflow product. | Deleted; main's `orchestrator.py`, `commands/curate.py`, `tests/test_curate_command.py` restored byte-identical. |
| Branch's `gaia-quick-curate` skill doc rewrite claiming an executable CLI | **DROP** | It would have been untruthful once the engine was dropped, and it broke main's "scaffold truthfulness" test. | Restored byte-identical to main. |
| `curation/state.py` | **SIMPLIFY** | Kept the atomic write and the run-ID validation (real safety wins); removed the engine-only fields that no longer have a consumer. | Trimmed. |
| Mirrored curation skills (chain / dynamic / CURATION-CORE / full-pipeline) | **RETAIN (updated)** | They now state the accounting invariant, the fail-closed L4 boundary, and existing-intake continuation truthfully. | Kept, `.agents`/`.claude` mirrors in sync. |

### The single most valuable deletion
The branch's executing curation engine. It was the largest new surface, it had
no entry point after main's CLI was restored, and every invariant it provided is
enforced in the shared seam that both lanes call. Removing it also removed the
expansion of the mandatory curation path.

## 4. Narrow product relaxation (deliberate, reviewed)

A receipt whose outcome is `deferred` no longer requires an assessment receipt
to exist. It must still be inside the frozen inventory, match task/attempt/input
binding, carry real matching packet bytes, and state a **non-empty reason**. A
DEFER is never review-ready and never authorizes, so this cannot create
eligibility; requiring an assessment there would pressure fabrication for
candidates whose source could not even be fetched. Every other outcome
(review-ready / rejected / proven-duplicate) still requires a real,
`validateAssessment`-passing assessment with a matching digest.

## 5. Remaining test failures (reconciled)

The earlier "25 vs 26" discrepancy is resolved: the counts were measured at
different commits and against different file sets. The authoritative breakdown is
below, measured on the current head.

| Class | Count | Meaning | Resolution |
|---|---|---|---|
| OBSOLETE FIXTURE | 17 | `tests/test_curation_reconciliation.py` fixtures predate the hardened contract (no real source content, no assessment bytes, stale outcome/target assumptions). | Rebuild against the real contract; do not relax product code. |
| OBSOLETE CONTRACT | 6 | Tests asserting that a **locally authored** `humanReview` makes trusted intake **succeed** — the exact vulnerability #2118 targets. | Migrate to fail-closed assertions, and preserve the mechanics coverage in explicitly unit-only tests that mock only the private trust hook. |
| GENUINE DEFECT (fixed) | 2 | (1) the branch dropped main's `assessCommand` candidate-ID guard; (2) the branch's freshness comparison re-derived the expected catalog with a different node-discovery rule, producing false "stale" verdicts. | Fixed in `cc99e75c4`: guard restored; the comparison now uses the same builder that produced the frozen snapshot. |

**Totals:** 25 originally failing assertions = 17 obsolete fixtures + 6 obsolete
contracts + 2 genuine defects. The 2 genuine defects are now fixed; the 23
obsolete ones are being migrated to the current contract. No failing test is
being deleted to make the suite green, and no security assertion is weakened.

## 6. Verification performed

| Check | Result |
|---|---|
| `git merge origin/main` (113 commits) | Clean; no conflicts; only overlap file auto-merged with main's commands preserved |
| Exact audit baseline at the isolated #2089 head | 224 passed (historical baseline, `b37e8b928`) |
| Focused suite on the branch at the current head | See `tests/` results recorded in the PR; targeted migrations in progress |
| `python -m compileall` on changed modules | Pass |
| `git diff --check` | Clean |
| `python scripts/sync_agent_skill_mirror.py --check` | In sync |
| Independent Luna review round 1 (static) | 5 findings, all fixed (`4ac765dfc`, `62f351509`, `d5ced24d8`, `cc99e75c4`) |
| Independent Luna review round 2 (with runtime probes) | **PENDING** — required at the final SHA |
| Small-batch walkthrough | **PENDING** |
| Suite walkthrough (six named rows → one generic) | **PENDING** |
| Real protected human L4 ceremony | **UNAVAILABLE — protected-flow activation NO-GO** |

## 7. Remaining human actions

1. Founder review of this draft PR and the reconciliation receipt.
2. An independent, protected human approval ceremony must be designed,
   implemented, and verified before trusted ratification or trusted submission
   can be activated. The current deny-all verifier is deliberate containment,
   not that ceremony.
3. #2089 remains **NO-MERGE** until repaired and approved; this branch does not
   close #2118, #2117, #2088, or #2089.

## 8. Compatibility statement

Preserved and re-verified: #2093 lowercase/collision protections, #2099
checkpoint-resume semantics and legacy-ledger handling, the immutable Actions
handoff and #2050 authenticated recovery path, the `discovery-packet-v2` packet
contract, canonical downstream governance, named identity accounting, and
existing-intake continuation. `gaia curate` on this branch behaves exactly as on
`main`.

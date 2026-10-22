# Curation remediation — reconciliation receipt

**Base:** `origin/main` @ `e1a870579` (contains #2097, #2093, #2099, #2035).
**Head:** `dev/curation-secure-reconciliation` (see `git rev-parse HEAD`).
**Related:** #2088, PR #2089 (open, unmerged @ `32ecd0df7`), #2118, #2117, original architecture audit.

Two verdicts are reported separately and are **not** the same claim:

- **Code-merge verdict: GO for scoped fail-closed hardening, subject to the
  repository's human merge gate.** The targeted compatibility and safety checks
  (672 focused tests, 235 on the exact audit baseline), the two bounded
  walkthroughs (17/17), the merge-gate verification (15/15), the independent
  verification of the runtime-review findings (13/13) and the independent
  Luna XHigh runtime review rounds all passed.
  This verdict does **not** establish successful production authorization: the
  protected handoff remains blocked by the intentionally denying verifier. Main's
  paused `gaia curate` behavior is preserved.
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

## 5. Remaining test failures (reconciled) — now zero

The earlier "25 vs 26" discrepancy is resolved: the counts were measured at
different commits and against different file sets. The authoritative breakdown of
the 25 originally failing assertions was:

| Class | Count | Meaning | Resolution |
|---|---|---|---|
| OBSOLETE FIXTURE | 17 | `tests/test_curation_reconciliation.py` fixtures predate the hardened contract (no real source content, no assessment bytes, stale outcome/target assumptions). | **Rebuilt** against the real contract in `f03d2eca2` (real synthetic source bytes, real digests, real `buildAssessment` receipts). Product code was not relaxed. |
| OBSOLETE CONTRACT | 6 | Tests asserting that a **locally authored** `humanReview` makes trusted intake **succeed** — the exact vulnerability #2118 targets. | **Migrated** in `84f205d9d` to fail-closed assertions, with the mechanics coverage preserved in explicitly unit-only tests that mock only the private trust hook. |
| GENUINE DEFECT | 2 | (1) the branch dropped main's `assessCommand` candidate-ID guard; (2) the branch's freshness comparison re-derived the expected catalog with a different node-discovery rule, producing false "stale" verdicts. | **Fixed** in `cc99e75c4`: guard restored; the comparison now uses the same builder that produced the frozen snapshot. |

**Totals:** 25 = 17 obsolete fixtures + 6 obsolete contracts + 2 genuine defects.
All 25 are resolved. The focused curation suite now reports **672 passed** with
no remaining failures. No failing test was deleted to make the suite green, and
no security assertion was weakened.

Three further defects were found later, by the independent runtime review and by
the delegated repair lanes, and are likewise fixed: the `skillBatch` schema did
not declare the `submissionKey` the producer emits (so every branch-produced batch
would have failed canonical validation — fixed in `8ee77feb6`), FAN-OUT dropped
assessment-free DEFER prior receipts, and the review accounting did not bind each
frozen row to its packet.

## 6. Verification performed

| Check | Result |
|---|---|
| `git merge origin/main` (113 commits) | Clean; no conflicts; only overlap file auto-merged with main's commands preserved |
| Exact audit baseline at the isolated #2089 head | **224 passed** (historical baseline, `b37e8b928`) |
| Exact audit baseline on this branch (same nine files) | **235 passed** (224 historical + 11 new) |
| Focused curation suite (24 files) on this branch | **690 passed** (672 + 18 new CodeQL-regression tests) |
| Focused suite after every repair round | **672 passed** before the CodeQL repair, **690 passed** after it (18 new tests, no regression) |
| CodeQL regression coverage (`tests/test_curation_error_contract.py`) | **18 passed** — secret-bearing verifier text never reaches stderr; the refusal still fails closed with nothing written; the published refusal is still shown; the verification scripts withhold a non-token detail |
| Bounded walkthroughs (`scripts/curation_walkthrough.py`) | **17/17 checks passed** — small batch (3 candidates) and suite (six named rows → one generic). Proves the refusal comes from the **independent authorization gate**, not a shape error. |
| Independent verification of the runtime-review findings (`scripts/verify_review_findings.py`) | **13/13 checks passed** |
| Merge-gate verification (`scripts/merge_gate_check.py`) | **15/15 checks passed** — production refusal, a legitimate batch still binding (no false rejection), five forged-accounting attacks refused, scope integrity against main |
| `python -m compileall` on changed modules | Pass |
| `python scripts/pr_guards.py --base origin/main` | **42 passed, 0 failed**, plus all named guards pass |
| `git diff --check` | Clean |
| `python scripts/sync_agent_skill_mirror.py --check` | In sync |
| `python scripts/sync_bundled_schemas.py --check` | In sync |
| Independent review rounds completed | **5** — round 1 (two fresh Luna High reviewers, security + conservation, static, against frozen `3e0641e3e`) and rounds 2–5 (Luna XHigh, runtime probes). The exact per-round finding ledger is §7. |
| Unique independent findings | **16** — 14 product/security + 2 test-quality. The prior "11 findings" figure counted *reviewer-reported items*, in which two items each bundled a pair of distinct defects, and it excluded the two test-quality observations; it was never a count of unique defects. The prior "8 further findings" figure for rounds 3–5 was a miscount: the durable table and its own prose both enumerate **6**. |
| Independent review round 6 | **OUTSTANDING — the one open merge condition.** Attempted **seven** times across two authorized backends (Luna XHigh and Astra XHigh): five before this finishing pass, and two more at the final head, one on each backend. Every attempt was refused with the same error — `The ChatGPT user has reached their Subscription Sharing usage limit` — so the gap is provider capacity, not a skipped check. Self-review is not a substitute for independent review, and no higher-tier reviewer was invented. Two residual defects found by self-review in the meantime (a self-contradicting named identity block; a hand-listed field comparison that let a report carry an extra claim of its own) were fixed in `20d945e2d` and re-verified. **This round must be run before merge.** |
| CodeQL (GitHub Advanced Security) | **pass** on the final head. The four `py/clear-text-logging-sensitive-data` alerts (106–109) are **fixed** by GitHub's determination, 0 open alerts on this PR, nothing dismissed. |
| Wider repository suite at the final head (`tests/`, not integration/slow) | **PENDING-FINAL** |
| Real protected human L4 ceremony | **UNAVAILABLE — protected-flow activation NO-GO** |

### Round-1 independent review findings and their repairs

Round 1 was run by **two fresh Luna High reviewers (security and conservation)**
against frozen code `3e0641e3e` (review run `08c3a6da-744b-4f93-88e3-1f9ab3f9e1a4`,
recorded in `CURATION-REMEDIATION-HANDOVER.md`). The reviewers' own output is not a
committed artifact, so these five are reconstructed one-for-one from the five
product repair commits that follow the frozen SHA; each finding is therefore
attributable to a commit, and each contract is verified to still hold in the
current tree.

| Finding | Severity | Repair | Still enforced at the final head |
|---|---|---|---|
| Source semantics and assessment artifacts were not bound to the frozen input (source bytes, assessment digest, decision/outcome expectation) | P1, accounting gap | `4ac765dfc` — the reconciliation binds the frozen source digest, the assessment digest and the decision's expected outcome | `reconciliation.py` — `sourceContent does not match frozen sourceDigest`, `actual assessment output hash mismatch`, `expected_outcome` map |
| Duplicate named identities were accepted in one frozen inventory | P2, identity integrity | `4ac765dfc` — a repeated exact named identity is refused | `reconciliation.py:69` — `duplicate namedIdentity: {identity}` |
| Malformed unknown-receipt diagnostics were non-deterministic | P2, diagnosability | `62f351509` — the receipt ordering key no longer coerces a malformed `attempt` | `fanout.py:160` — the deterministic sort key is still in place |
| Bounded resume did not harden its receipts and run state | P2, resume integrity | `ee222685f` — hardened resume, receipts and run state in the (now removed) curate engine; the surviving contract is the shared seam's receipt accounting and atomic state writes | `curation/reconciliation.py` receipt accounting; `curation/state.py` atomic writes and safe run-ID validation |
| Capture-time metadata was compared when verifying catalog substance | P1, false staleness | `b48b4bfb6`, then `cc99e75c4` — one `buildGenericSnapshot`-based substance comparison | `freshness.py:50` — `sameGenericSnapshot` compares catalog substance, not capture timestamps |
| DEFER receipts were discarded on resume unless they carried a fabricated assessment | P2, lossless accounting | `d5ced24d8` — a plain DEFER is retained with an explicit reason and never authorizes | `reconciliation.py:350` — a deferred receipt must state an explicit reason |

### Rounds 2–5 independent review findings and their repairs


| Finding | Severity | Repair | Verification |
|---|---|---|---|
| Output writers followed a symlinked parent directory out of the registry root (packet, assessment receipt, skill batch) | P2, exploitable local write | `1d2782a56` — resolved-path containment of every output directory against the registry root, plus skill-batch leaf-symlink refusal | Independent probe: refusal raises, nothing written outside the root, leaf symlink still refused, normal writes unaffected |
| FAN-OUT resume dropped conflicting prior receipts and could report the candidate review-ready | P2, audit correctness | `991fec131` — conflicts are retained, surfaced in `priorReceiptErrors`, and the candidate is blocked from dispatch | Independent probe: final outcome is `deferred` with the conflict reason, and the conflict is diagnosable |
| Review accounting compared only candidate-ID sets, not each frozen row against its packet | P2, latent accounting gap | `a0c2fe6a2` — every row is bound to its packet by exact named identity, source URL/revision/digest, decision, proposed generic and packet/assessment digests; retrieval rank is deliberately **not** bound so outside-top-K remains possible | Independent probe: a mismatched row is rejected; a self-consistent inventory still builds |
| Review accounting accepted a report that was **not** a real reconciliation (receipt marked invalid, batch not accounted, claiming human approval, digests stripped) | P2, latent accounting gap — found by the final independent review | `85ce78416` — the payload builder now requires positive accounting: the report must be fully accounted, must not claim human approval, every row must carry a valid receipt, and the packet/proposal/assessment digests must be **present and equal** to the actual artifacts rather than checked only when present | Regression test `test_forged_review_accounting_is_rejected`; the independent reviewer's own probe now raises `review accounting must be a fully accounted reconciliation` |
| Test-quality: `test_dev_ratify.py` and `test_push_from_file.py` mocked whole validators rather than the private trust seam | — | `a0c2fe6a2` — the ratify tests now mock only `_verifyTrustedEnvelope`, so real payload reconstruction and binding execute; the push test exercises real assessment validation | Reviewer-confirmed; no test claims human approval |
| Walkthrough asserted only "some error", not the authorization refusal | — | `7999ee8a6` — the walkthrough now builds a complete, realistic ratified packet and asserts the refusal is exactly the independent-authorization refusal | 17/17 |
| A report could be **fabricated** because the builder trusted the caller's report instead of recomputing it | P2, latent accounting gap | `85ce78416`/`a12aa07e6` — the review inventory must carry the receipts that produced it; the builder **recomputes** the reconciliation and requires the claimed report to agree | `test_forged_reconciliation_report_is_rejected_against_genuine_receipts`; the independent probe's forged report is refused |
| The report carried **file-bytes** digests while the payload builder compared **canonical content** digests, so a legitimate pretty-printed production artifact was rejected | P1, functional regression | `5cbafe9c0` — the report now carries canonical content digests and separately the artifact digests; the receipt keeps the artifact digests | `test_report_digests_describe_content_not_artifact_bytes`; the CLI fixture now writes production-shaped artifacts |
| Reconciliation and the payload builder resolved a packet's named identity by **different rules** | P1, functional regression | `5cbafe9c0` — one shared resolver (`packetNamedIdentity`) is used by both | `test_packet_identity_resolves_by_one_rule_everywhere` |
| A **mapping-form** top-level identity binding bypassed the double-binding consistency check | P1, latent boundary defect | `83f97019d` — the top-level binding is accepted only as an exact identity string; any other shape is unbound and refused | Independent reproduction: reconciliation defers and the payload build is refused |
| The payload builder did not bind the report's **artifact-digest claims** to the recomputed report | P2, report-integrity defect | `83f97019d` — the report's artifact and content digest claims must equal the recomputed reconciliation's | `test_forged_artifact_digest_claims_in_the_report_are_rejected`; independent reproduction refused |
| A **named block** could express the identity two ways and disagree with itself, and only one expression was compared | P2, latent boundary defect (found in self-review while the reviewer provider was at capacity) | `20d945e2d` — a self-contradicting named block resolves to *no* identity, so the packet is refused rather than silently resolved | `test_packet_identity_resolves_by_one_rule_everywhere` |
| Only a **hand-listed set** of report fields was compared, so a report could carry an extra claim of its own, and a field added to the report later would silently stop being bound | P2, report-integrity hardening (same self-review) | `20d945e2d` — the claimed row must equal the recomputed row in full, and the report's `counts` and `candidateCount` must match too | `test_whole_report_row_and_aggregates_are_bound_to_the_receipts` |

### The clear-text sensitive-data repair (CodeQL alerts 106–109)

GitHub Advanced Security reported four unresolved `py/clear-text-logging-sensitive-data`
findings on this branch: `scripts/curation_walkthrough.py:34`, `scripts/merge_gate_check.py:38`
and two sites in `src/gaia_cli/commands/dev/ratify.py` (432 and 474).

**Root cause.** The rule taint-traces values returned by APIs whose names match its sensitive
heuristic — here `verifyPacketAuthorization` — into `print()` sinks. Truncation, slicing, regex
redaction and hashing are all *taint-preserving* steps in CodeQL's Python model, so no amount of
post-processing clears a finding: the output would still be a function of the upstream text. The
only shape that keeps upstream content out of the console is a comparison against a published
constant that yields a published constant.

**Repair.** A new module, `src/gaia_cli/curation/errors.py`, owns the only sanctioned way for the
curation seam to describe a refusal to a human:

    <CATEGORY>: <published summary or published refusal> [<n> withheld]

- A refusal that is exactly a **published** refusal — the fail-closed
  `independent protected human authorization is not configured; L4 remains pending` contract this
  codebase owns — is echoed, because the operator must still be able to see the boundary state.
- Every other refusal is **withheld** and reported only as the gate category and a count, because
  its text can embed operator input and, once a protected ceremony exists, provider, artifact or
  protected-environment detail.
- The two verification scripts print only a **console-safe token** from a published vocabulary; a
  non-token detail is withheld rather than printed, so a script cannot leak a payload into its own
  output.
- `gaia dev ratify` now reports the resolution, self-validation, freshness, assessment and
  authorization gates through that contract, and an unparseable authorization envelope is reported
  without echoing the document or the decoder's rendering of it.
- The intake/push boundary in `intakeAdapter.py` does the same, so the same refusal cannot reach a
  console by another route.

**Refusal behaviour is unchanged.** Authorization failure still fails closed: non-zero exit, no
packet written, no batch, registry or issue artifact, no issue opened. The published fail-closed
refusal is still visible to the operator. The deny-all production verifier is untouched, and
protected-flow activation remains NO-GO. The four `except` renderings in `ratify.py` that sit
*outside* the authorization boundary (reading the packet, reading the assessment receipt, loading
live generic semantics, writing the packet) still echo their exception text; they carry this
codebase's own bounded messages and no upstream material, and they are outside the boundary this
repair covers.

**GitHub thread state.** All four alerts (106, 107, 108, 109) are now reported by GitHub as
**fixed** at `2026-10-22T09:41:45Z`; the PR has **0 open** code-scanning alerts, and the `CodeQL`
check on the final head **passes** (it previously failed with "4 new alerts including 4 high
severity security vulnerabilities"). Nothing was dismissed: the alerts were resolved by the code
change. The one alert still open repository-wide is #73 in `tests/test_security_scanner.py`, which
is pre-existing on `main` and unrelated to this branch.

**Regression coverage.** `tests/test_curation_error_contract.py` (18 tests) pins that
secret-bearing verifier text never reaches stderr in any of the three console paths, that the
refusal still fails closed with nothing written, that the published refusal is still shown, and
that the verification scripts withhold a non-token detail.

**A near-miss worth recording.** The documentation commit `11d0ba0c8` also changed three
production files: it replaced the error contract with an alternative implementation that
publishes the codes inside `authorization.py` and prefixes them onto the strings the seam
returns. That variant was never tested, it left the tree inconsistent (`intakeAdapter.py` and
both verification scripts imported a function it did not provide, so the suite failed at
collection), and it would have required rewriting an exact-match assertion in the audit baseline
to accommodate a changed contract. It was not adopted. `b199ba738` restores the tested state and
keeps the ledger commit documentation-only, as its message claims. The alternative is preserved
outside the repository for reference only.

## 7. Independent review ledger (canonical)

This is the single accounting of the independent review. Every number below is
derived from a committed artifact: a repair commit, a documented reproduction,
or a row in the finding tables above. Where a number was previously stated
differently, the difference is explained in the last row of this table.

| Quantity | Count | Derivation |
|---|---|---|
| Independent review rounds completed | **5** | Round 1: two fresh Luna High reviewers (security + conservation), static, against frozen `3e0641e3e`. Rounds 2–5: Luna XHigh with runtime probes. |
| Round 1 — product/security findings | **5** | One per product repair commit following the frozen SHA: `4ac765dfc`, `62f351509`, `ee222685f`, `b48b4bfb6`, `d5ced24d8`. Itemised in the round-1 table. |
| Round 2 — product/security findings | **3** | Symlinked output-directory escape (`1d2782a56`); FAN-OUT resume dropping conflicting prior receipts (`991fec131`); review accounting not binding each frozen row to its packet (`a0c2fe6a2`). |
| Round 2 — test-quality findings | **2** | The ratify/push tests mocked whole validators instead of the private trust seam (`a0c2fe6a2`); the walkthrough asserted only "some error" rather than the authorization refusal (`7999ee8a6`). Neither claimed a real human approval. |
| Rounds 3–5 — product/security findings | **6** | Round 3: a report that was not a real reconciliation, and a builder that trusted the caller's report instead of recomputing it (`85ce78416`, `a12aa07e6`). Round 4: content-vs-artifact digest confusion, and divergent identity rules between two modules (`5cbafe9c0`). Round 5: a mapping-form identity binding that bypassed the consistency check, and unbound artifact-digest claims (`83f97019d`). |
| **Unique independent findings** | **16** | 14 product/security (5 + 3 + 6) + 2 test-quality. |
| Repeated confirmations of earlier findings | **5** | Round 2 re-confirmed all five round-1 findings as closed **at runtime**; these are confirmations, not new findings, and are not counted twice. |
| Duplicate descriptions of one defect in this report | **1** | "Review accounting accepted a report that was not a real reconciliation" was present twice in the finding table, both times with repair `85ce78416`. One row has been removed; the defect was counted once. |
| Separate self-review findings | **2** | A named block that expressed the identity two ways and disagreed with itself; and a hand-listed field comparison that let a report carry an extra claim of its own (`20d945e2d`). These are **not** independent findings and are not counted as such. |
| **Total unique defects addressed** | **18** | 16 independent (14 product/security + 2 test-quality) + 2 self-review. |

### How the two stale totals were reconciled

| Previously stated | Where | Why it differed | Canonical value |
|---|---|---|---|
| "11 findings across five rounds" | PR #2134 body; `CURATION-REMEDIATION-HANDOVER.md` | It counted **reviewer-reported items**. Rounds 3–5 reported six distinct defects as three items, in which two items each bundled a pair of distinct defects; the figure also excluded the two test-quality observations. It was never a count of unique defects. | **16** unique independent findings (14 product/security + 2 test-quality) |
| "rounds 3–5: 8 further findings" | This report, round-summary row | A miscount: the finding table and the same row's own prose both enumerate **6** unique product/security findings for rounds 3–5, presented as 7 table rows because one row was duplicated. | **6** |
| "25 originally failing assertions" | This report, §5 | Correct, and a different population entirely: the *original audit's* failing assertions, not review findings. 25 = 17 obsolete fixtures + 6 obsolete contracts + 2 genuine defects. | Unchanged — **25**, and 0 remaining |

**No finding was closed by weakening an assertion, and no test claims a real human approval.**


## 8. The historical 26-case matrix, resolved

The matrix was authored as a plan at `cb0e83c6b` with every row `PENDING`. It is reproduced
here **mapped onto the evidence that now exists**, with the covering test or check named for
each row. This is a status mapping, not a new test framework: every row is covered by code that
already exists and already runs in the focused suite, the merge gate or the walkthroughs. The
plan is retained in history at `cb0e83c6b:CURATION-REMEDIATION-REPORT.md`.

`PENDING` in the plan meant "an assertion exists or is planned, but final-SHA execution and
independent review are not yet recorded". Every row below is now executed at the final SHA.
Rows marked **CONTAINMENT** prove that the deny-all production seam refuses; they do not prove
that a real ceremony would behave correctly, because no such ceremony exists.

| # | Scenario | Covering evidence at the final head | Status |
|---|---|---|---|
| 1 | Default CHAIN, one candidate | The executing CHAIN engine was **deleted** by the lean-scope decision (#2117); main's paused `gaia curate` scaffold is restored byte-identical. The preparation primitive it wrapped survives in the shared seam, and the *capability* the row asserted — a real prefill path with a frozen source and full accounting — is covered there. | `test_packet_normalized_text_or_frontmatter_cannot_differ_from_frozen_source`; `test_packet_is_schema_valid` — **SCOPE-REMOVED** (the engine), capability covered |
| 2 | Default CHAIN, five candidates | As row 1; the five-candidate accounting is covered by the walkthrough's three-candidate batch and the six-named-row suite. | walkthrough 17/17 — **SCOPE-REMOVED** (the engine), capability covered |
| 3 | FAN-OUT, 12 candidates | `curation/fanout.py` retained as an optional, bounded, model-neutral assisted-lane helper | `test_fanout_retries_worker_exceptions_and_is_completion_order_independent` |
| 4 | Six distinct named implementations on one generic | Walkthrough 2 (six rows → one generic) | `test_conserves_named_rows_with_shared_generic_and_retains_provenance`; walkthrough 17/17 |
| 5 | `a-b` vs `a/b` filename ownership | Digest-owned filenames in `prefill.py` | `test_valid_slugs_are_readable_and_collision_resistant`; `test_freeze_rejects_duplicate_named_identity_and_source_digest_mismatch` |
| 6 | Valid exact duplicate with surviving source-matched target | Duplicate proof requires a different surviving accounted candidate | `test_exact_duplicate_requires_different_surviving_target_and_source_proof`; walkthrough "a genuine exact duplicate with a surviving target is proven" |
| 7 | Shared-generic similarity is not an exact duplicate | A shared generic never collapses rows | walkthrough "a shared generic is not an exact duplicate" |
| 8 | Competing full definitions of the same generic | Deterministic conflicting-proposal rejection, order-independent | `test_unknown_receipts_and_competing_attempts_are_reported_order_independently`; `test_prior_receipt_attempts_and_receipt_order_conflict_are_deterministic` |
| 9 | Fabricated reviewer identity | The production verifier denies; metadata carries no authority | `test_forged_user_metadata_never_authenticates`; `test_audit_forgery_rejected_at_trusted_adapter` |
| 10 | Plausible but forged approval reference | Same negative production boundary | `test_forged_packet_cannot_submit_on_either_route` |
| 11 | Empty `{}` assessment with matching digest | Assessment validation rejects an empty receipt | `test_empty_digest_matched_assessment_does_not_grant_authority`; `test_empty_assessment_object_is_not_a_ratification_receipt` |
| 12 | Fabricated outside-top-K approval | Retrieval rank is not bound as authority; a forged review inventory is refused | `test_review_inventory_binds_exact_named_identity_and_source`; `test_forged_review_accounting_is_rejected` |
| 13 | Legitimate independently protected outside-top-K decision | No protected ceremony exists; the unit hook is not evidence | **SKIP / BLOCKED** (unchanged) |
| 14 | Identity changed after reviewed payload | The reviewed inventory binds the exact named identity and source | `test_packet_identity_source_revision_digest_and_proposal_are_bound`; `test_review_inventory_binds_exact_named_identity_and_source` — **CONTAINMENT** |
| 15 | Source/revision changed after reviewed payload | Source digest and live freshness are bound | `test_verify_packet_freshness_rejects_stale_source_digest`; `test_inventory_digest_detects_mutation` — **CONTAINMENT** |
| 16 | Selected generic definition/topology changed | The full selected definition and prerequisites are bound; catalog drift is detected | `test_verify_packet_freshness_rejects_description_only_selected_definition_drift`; `test_report_binds_assessment_digest_and_outside_top_k_mapping_is_allowed` — **CONTAINMENT** |
| 17 | Stale catalog, including same-ID semantic drift | One `buildGenericSnapshot`-based substance comparison; unreadable canonical files fail closed | `test_verify_packet_freshness_rejects_stale_generic_snapshot`; `test_verify_packet_freshness_fails_closed_on_canonical_parse_failure` |
| 18 | Worker failure and targeted bounded retry | Bounded retry, order-independent completion | `test_fanout_retries_worker_exceptions_and_is_completion_order_independent`; `test_unknown_receipts_and_competing_attempts_are_reported_order_independently` |
| 19 | Interrupted partial resume with prior completed rows | Prior receipts survive resume; a conflict blocks the candidate rather than upgrading it | `test_resolved_history_does_not_reappear_without_fresh_failure`; `test_prior_receipt_attempts_and_receipt_order_conflict_are_deterministic`; merge gate "FAN-OUT resume does NOT silently upgrade a conflicted candidate to review-ready" |
| 20 | Task/attempt/time budget exhaustion | Missing candidates stay explicitly deferred; late results are discarded | `test_budget_counts_candidate_tasks_and_missing_worker_errors_survive`; `test_timeout_is_one_wall_clock_budget_for_the_whole_run`; `test_attempt_one_then_two_rejects_worker_receipt_claiming_attempt_one_again` |
| 21 | Identical submission repeated | Content-derived submission identity; the same content reuses the existing receipt | `test_identical_resubmission_returns_existing_receipt`; `test_payload_change_changes_content_id` |
| 22 | Existing-intake continuation | The original batch and issue references are verified and preserved | `test_existing_intake_continuation_preserves_refs_and_handoff`; `test_existing_intake_checked_not_locally_asserted`; `test_uncertain_network_window_never_blindly_resubmits` |
| 23 | #2093 exact lowercase/collision protections | Unchanged from main | `tests/test_named_identity_case_2055.py` — `test_add_rejects_mixed_case_without_normalizing`, `test_add_rejects_case_variant_of_existing_identity` |
| 24 | Immutable Actions provenance/recovery retained | Unchanged from main | `tests/test_intake_recovery_2050.py`; `tests/test_intake_approval_workflow.py` — `test_maintainer_check_precedes_checkout_in_both_jobs` |
| 25 | Unauthorized registry mutation attempt | Discovery and forged submission never enter a canonical mutation | `test_audit_forgery_rejected_at_trusted_adapter`; merge gate "no canonical registry DATA changed" (only one schema property is declared) |
| 26 | Evidence handoff without duplicate intake | The original issue/batch and downstream gates are unchanged | `test_no_issue_then_submission_reuses_original_batch`; `test_plain_yaml_cannot_impersonate_trusted_l4` |

**Count:** 26 rows — 2 whose *engine* was removed by the founder's lean-scope decision (the
capability each asserted is covered by the shared seam, and is named above), 1 blocked by the
absent ceremony, 3 containment-only (the deny-all seam refuses; a real ceremony is unproven), and
20 executed at the final SHA against the named evidence.

## 9. Remaining human actions

1. Founder review of this draft PR and the reconciliation receipt.
2. An independent, protected human approval ceremony must be designed,
   implemented, and verified before trusted ratification or trusted submission
   can be activated. The current deny-all verifier is deliberate containment,
   not that ceremony.
3. #2089 remains **NO-MERGE** until repaired and approved; this branch does not
   close #2118, #2117, #2088, or #2089.

## 10. Compatibility statement

Preserved and re-verified: #2093 lowercase/collision protections, #2099
checkpoint-resume semantics and legacy-ledger handling, the immutable Actions
handoff and #2050 authenticated recovery path, the `discovery-packet-v2` packet
contract, canonical downstream governance, named identity accounting, and
existing-intake continuation. `gaia curate` on this branch behaves exactly as on
`main`.

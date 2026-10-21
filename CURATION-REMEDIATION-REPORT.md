# Gaia curation remediation — verification report

**Status: IN PROGRESS. Not a completion or merge approval.**

Code under independent review: `3e0641e3e` on `dev/curation-secure-reconciliation`.
The following record distinguishes verified results, diagnostic runs, and missing
production ceremonies. Update it with final-SHA evidence before requesting merge.

## Scope and preserved governance

The remediation imports #2089's two CLI commits with `cherry-pick -x` attribution
onto main `f77e4daf89992b2131ce628a1519ff859682c299`. That main already contains
#2093 (`cddb09ce9b230dd0187ccebe091b88cab2d67b5b`). #2089 remains OPEN and its actual
base is `dev/emilkowalski-intake-2026-10-13`, not main. No change to its status or
target branch has been made.

This work implements pre-L4 discovery, shared candidate accounting, persistence,
freshness, submission idempotency, and fail-closed authorization boundaries.
It does not authorize real intake, registry mutation, evidence ingestion,
calibration, deployment, or merge. Ordinary YAML/issue-form intake remains an
**unreviewed proposal**, never trusted post-L4 approval.

The original architecture audit and its reproduction scripts were recovered and
read; implementation targets those confirmed findings rather than restarting
architecture discovery.

## Critical authorization limitation

`curation/authorization.py::_verifyTrustedEnvelope` deliberately denies every
production request. An independently authenticated, protected human L4 ceremony
covering the complete bound payload is **not configured or verified**. Names,
timestamps, comments, references, local decisions, flags, envelopes, agent-owned
credentials and environment metadata are not substitutes for that authority.

Ratification and trusted single/manifest submission therefore remain blocked.
Tests replacing the private verifier are explicitly **unit-only**. They do not
establish protected Actions provenance, real human authority, revocation, or a
successful outside-top-K production approval. Structural outside-top-K choices
are preserved and payload-bound; the missing ceremony must not be bypassed by
permanently banning legitimate choices or by accepting local attestations.

**Current recommendation: NO-GO for activating protected submission; no production
merge recommendation until the independent reviews, final tests, and remaining
human authorization requirements have been resolved.**

## File-level implementation map

| Files | Change and boundary |
|---|---|
| `commands/pushFromFile.py`, `commands/push.py`, `intakeAdapter.py`, `commands/dev/ratify.py`, `commands/dev/__init__.py` | Preserve v2 and multi-packet adaptation; bind exact manifest bytes, complete inventory, route, assessment and continuation; external authorization carriers; ratify and trusted submission separately fail closed. |
| `curation/authorization.py` | Canonical independently computed full review payload, authorization-carrier cycle exclusion, whole-manifest accounting and review membership, deny-all production trust seam pending real human ceremony. |
| `prefill.py`, `curation/freshness.py` | Digest-owned filenames; exact candidate identity; locked atomic ownership checks; actual named/source dedupe; truthful lifecycle when lookup unavailable; canonical full-definition/catalog/source freshness. |
| `curation/assessment.py` | Digest-owned default assessment filenames and locked ownership checks, not slash-to-dash collision overwrites. Actual assessment is mandatory at trusted boundary. |
| `curation/reconciliation.py`, `curation/fanout.py` | Frozen inventory; distinct candidate/named/generic keys; task/input/attempt/packet/proposal binding; exact duplicate target proof; deterministic conflict handling; complete final outcomes; bounded callable workers, retry and explicit exhaustion/defer. |
| `curation/orchestrator.py`, `curation/state.py`, `commands/curate.py` | Actual sequential 1–5 candidate execution through source fetch/prefill/assessment/reconciliation; atomic checkpoints; real named identity; targeted retry and preserved external intake references; always stop pre-L4. |
| `curation/submission.py`, `push.py`, `prWriter.py` | Content-derived batch IDs, local process locking, atomic receipts, remote content-marker lookup, uncertain-create fail closed, explicit original-intake continuation. Operational state never grants approval. |
| `scripts/validate_intake.py`, mirrored `validate_discovery_packet.py` | #2089's multi-packet/N:1 support retained with current-main lowercase and collision protections. |
| `CONTRIBUTING.md`, mirrored curation core/CHAIN/FAN-OUT/full-pipeline/quick-curate skills | Truthful pre-L4 executable capabilities and pending authority, no auto-merge or local-attestation-as-human-approval claims. |
| `tests/test_curation_*`, `test_curate_chain.py`, related ratify/push/intake tests | Synthetic boundary attacks, accounting/provenance, freshness, collision, retries, idempotency, compatibility and explicitly unit-only trust-hook tests. |

## Runtime contracts and honest limits

- Both topologies feed `freezeInventory` → `reconcileInventory`; neither is a
  replacement packet schema or a canonical registry writer.
- CHAIN remains sequential; FAN-OUT uses bounded model-neutral callable workers
  with deterministic reconciliation. Worker model/routing is external policy.
- Every expected row has exactly one final outcome: review-ready, deferred,
  rejected, or proven duplicate. **Review-ready is not human-approved.**
- Default prefill is advisory and explicitly deferred; synthetic default-path
  execution must not be reported as completed semantic/human review.
- Exact duplicate proof must relate the current candidate to a different,
  surviving target with matching source evidence. Shared generic or semantic
  similarity alone never removes a named row.
- Thread cancellation is cooperative. The scheduler discards late returns; it
  cannot kill arbitrary worker code or promise that worker-side external effects
  are cancellable.
- Submission locking is checkout-local, not a distributed transaction. A remote
  lookup reduces repeats but does not establish global exactly-once creation
  across independent simultaneous clones. An uncertain local creation window
  requires explicit recovery and never blind retry.
- Source URLs on branches are explicitly unresolved revisions and need live
  freshness verification. No immutable revision is fabricated.

## Recorded verification

| Run | Code/environment | Observed result | Meaning |
|---|---|---|---|
| Original exact nine-file baseline | Isolated #2089 head `32ecd0df7c0683167e2d9dfacf6ecbb4481cb453` | **224 passed in 8.59s** | Reproduced audit baseline, not repaired-code acceptance. |
| Additional isolated focused subset | Same isolated baseline | **179 passed in 5.07s** | Different subset; not a substitute for exact224. |
| Submission/idempotency intermediate regression | Earlier intermediate remediation code | **78 passed in 1.73s** | Historical integration evidence; must rerun after final changes. |
| Latest compileall, `git diff --check`, skill mirror check | Code checkpoint `3e0641e3e` | **PASS** | Syntax, whitespace and mirrored instructions only; not behavioral/security completion. |
| Registry/site drift check | Diff against recorded origin/main | No `registry/`, `skill-trees/`, or `docs/graph/` changes | Confirms no canonical/source/generated registry change at checkpoint. |
| Intermediate focused integration tasks | Logs awaiting durable notification/retrieval | **PENDING** | Diagnostic only: code changed after launch. |
| Final stable-SHA regression and applicable wider suite | Not yet run | **PENDING** | Required before any final recommendation. |
| Real independent protected human approval | Unavailable | **SKIP / BLOCKED** | Mandatory missing human ceremony; no success claim. |

Exact isolated baseline command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -p no:cacheprovider -q \
  tests/test_intake_multi_packet_2088.py tests/test_intake_adapter.py \
  tests/test_dev_ratify.py tests/test_push_from_file.py tests/test_intake.py \
  tests/test_intake_approval_workflow.py tests/test_gaia_curate_discovery_packet.py \
  tests/test_curate_command.py tests/test_curate_state.py
```

## Required 26-case matrix

**PENDING** below means an assertion exists or is planned, but final-SHA execution
and independent review are not yet recorded. It is not a pass. Negative tests
blocked by the deny-all production seam prove containment only; real post-approval
staleness/revocation still requires an actual protected ceremony.

| # | Scenario | Current evidence target | Final status |
|---|---|---|---|
| 1 | Default CHAIN, one candidate | `test_default_processor_uses_real_prefill_path_with_frozen_source[1]`, honest deferred outcome | PENDING |
| 2 | Default CHAIN, five candidates | Same default primitive test `[5]`, frozen sources and full accounting | PENDING |
| 3 | FAN-OUT, 12 candidates | Reconciliation fixture and bounded callable worker execution | PENDING |
| 4 | Six distinct named implementations on one generic | `test_conserves_named_rows_with_shared_generic_and_retains_provenance` | PENDING |
| 5 | `a-b` vs `a/b` filename ownership | Prefill, assessment and shard collision checks | PENDING |
| 6 | Valid exact duplicate with surviving source-matched target | Reconciliation proof and target accounting | PENDING |
| 7 | Semantic/shared-generic similarity is not exact duplicate | Negative duplicate proof and distinct named conservation | PENDING |
| 8 | Competing full definitions of the same generic | Deterministic conflicting-proposal rejection in every receipt permutation | PENDING |
| 9 | Fabricated reviewer identity | Real trusted adapter/submission negative boundary | PENDING |
| 10 | Plausible but forged approval reference | Same negative production boundary, no metadata authority | PENDING |
| 11 | Empty `{}` assessment with matching digest | Real assessment validation and authorization failure | PENDING |
| 12 | Fabricated outside-top-K approval | Direct validator, ratify/trusted single/manifest boundaries | PENDING |
| 13 | Legitimate independently protected outside-top-K decision | Production ceremony unavailable; unit hook is not evidence | **SKIP / BLOCKED** |
| 14 | Identity changed after reviewed payload | Payload changes and old envelope fails; real approved ceremony absent | PENDING (containment/unit binding only) |
| 15 | Source/revision changed after reviewed payload | Source digest/live freshness and old payload rejection | PENDING (no real approved ceremony) |
| 16 | Selected generic definition/topology changed | Full definition/prerequisites payload and freshness binding | PENDING (no real approved ceremony) |
| 17 | Stale catalog, including same-ID semantic drift | `test_curation_freshness.py` canonical snapshots and read failures | PENDING |
| 18 | Worker failure and targeted bounded retry | CHAIN and FAN-OUT attempt/error tests | PENDING |
| 19 | Interrupted partial resume with prior completed rows | Persisted owned packet/assessment/source hashes and refs | PENDING |
| 20 | Task/attempt/time budget exhaustion | Missing candidates explicitly deferred and late results discarded | PENDING |
| 21 | Identical submission repeated | Content key and existing operational receipt, no second issue | PENDING |
| 22 | Existing-intake continuation | Original batch/issue verified and preserved | PENDING |
| 23 | #2093 exact lowercase/collision protections | `test_named_identity_case_2055.py`, intake/push tests | PENDING |
| 24 | Immutable Actions provenance/recovery retained | Existing intake recovery/approval workflow regression | PENDING |
| 25 | Unauthorized registry mutation attempt | Discovery and forged submission never enter canonical mutation; diff evidence | PENDING |
| 26 | Evidence handoff without duplicate intake | Original issue/batch continuation and unchanged downstream gates | PENDING |

## Independent review

Two fresh read-only GPT-6-Luna High reviewers with no implementation ownership
were launched against code checkpoint `3e0641e3e`:

1. L4 authority, authorization binding, stale/fabricated artifacts and governance.
2. Candidate conservation, collision resistance, actual execution, idempotency
   and continuation.

Run: `08c3a6da-744b-4f93-88e3-1f9ab3f9e1a4`. **Results pending.** No reviewer approval
is inferred from launch or implementer self-tests. Reviewed source/test scope is
frozen until their findings are retrieved.

## Remaining gates

- Collect diagnostic results, repair verified failures after independent review
  retrieval, and rerun at a stable final code SHA.
- Record independent findings and their repair/re-review dispositions.
- Complete this matrix with actual PASS/FAIL/SKIP evidence and applicable wider
  test results; enumerate environment limitations rather than silently skip.
- Refresh main and verify retained #2093 and immutable provenance protections.
- Open one draft development PR with attribution, evidence, and explicit missing
  human actions. Do not merge, deploy, submit real intakes or close issues.
- Independently establish and verify the protected human ceremony before enabling
  trusted ratification/submission. The present deny-all seam is not that ceremony.

# Independent whole-feature source review — BLOCKED

## Identity and verdict

**BLOCKED — whole frozen source is not accepted.** Coverage is incomplete. No source defect is asserted on the basis of this partial pass; that is not evidence that the candidate is defect-free. The exact candidate was `17ad597ad3478b7caae182b1581a965a8fcfa252`, tree `fa46a693d3ad3a26f19474851197e97c56f77769`. Actual harness environment reports `PI_PROVIDER=openai`, `PI_MODEL=gpt-6.1-terra`, `PI_REASONING_LEVEL=high`; this is runtime environment evidence, not an independent provider-side attestation. No nested agents were used.

Checkout was clean on inspection, shallow, with no `.git/objects/info/alternates`; origin fetch points to the local provenance repository and push URL is `disabled://no-origin-writes`. No origin operational state was accessed. Shallow history does not establish deep ancestry. Main snapshot `3cd5504e00ac00e4708503f484a05e04e5775dcc` has tree `9b29681b44be112306f8502961f4e67787492d97`. The main-tree diff stat independently reports 32 paths, 4,337 insertions, 586 deletions. Core-to-candidate `coordination.py` has 58 insertions and 8 deletions, all requiring review; the prior bounded core acceptance does not cover them.

## Coverage matrix

| Boundary | This pass | Remaining before whole acceptance |
|---|---|---|
| Main-to-candidate and core-to-candidate | Enumerated changed paths and stat; `git diff --check` clean. | Full semantic diff and all changed core lines and callers not reviewed. |
| Concrete request, credentials and one-shot | Re-ran five existing fixture tests listed below; no independent new probe designed. | Inspect all request construction, adapter entry, process/thread/fork/restart and acknowledgment-loss paths; fresh negative/control probes counting invocations **and** effects. |
| Authority, current source, proof, revocation and outcome binding | Only post-claim boundary and missing-binding existing tests re-run. | Full source and consumer seam review, live recheck and exact outcome identity tests; no general authority acceptance. |
| Genesis/history/CAS, clock, quota, retention, bounds | Not independently reviewed or probed. | Review bounded clock, CAS, quota and unknown-sender invariants, raw source/next-generation serialized bounds and smaller transport controls. |
| Gate/CLI/runner/driver/local legacy | Six existing local state tests re-run. | Review whole integration and success-shaped runner outcomes; compare changed tests with original assertions/timeouts and all legacy 900s/raw-authorization paths. |
| Protection, policy, catalog, mirror, HTML and preservation | Generic ledger blob equal to main; limited byte comparison described below. | Inspect all safeguards, policy and catalog, mirrors, visible CLI before/after founder gate and factual HTML. External protection/clock/drained-writer declarations are not actual external attestations. |
| Original failure histories / final suite / packaging | Builder report read as a claim; raw logs and JUnit not audited. | Verify original failure histories and exact binding of any carried test and packaging evidence, without representing builder claims as fresh results. |

## Fresh verification and observations

* `git rev-parse HEAD HEAD^{tree}` returned the candidate commit and tree above; `git status --porcelain` was empty at inspection. `git rev-parse --is-shallow-repository` returned `true`; alternates file was absent. `git remote -v` showed the disabled push URL.
* `graft ask 'routine 19 shared pr maintenance executor authority claim and runner integration' --source` returned no matching nodes; no graft index was built and no source was inferred from the empty result.
* `git diff --check 3cd5504e00ac00e4708503f484a05e04e5775dcc HEAD` succeeded. Main-to-candidate changed paths/stat were enumerated, not fully reviewed.
* `git diff --quiet 6b914723004852a5f515f78ed6d536cccbe3a9bc HEAD -- src/gaia_cli/steward/ledger.py founder/steward/POLICY.yaml founder/steward/roster.py pyproject.toml` returned 0. This is limited to those paths against the cited core, not proof of all preservation requirements. `src/gaia_cli/steward/ledger.py` has the same Git blob `dae7b0d3bc2fd3f04ba82b978e66d2c0ca92b0cd` at main snapshot and candidate.
* `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests/steward/test_local_full_state.py`: **6 passed in 56.82s**. These are existing fixture tests, including local selection, pre-store legacy mutation refusal, separate local checkout state and fixture legacy read-only status. Their fixture-only actions are not evidence of any live campaign transition.
* `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider` on `tests/steward/prmaintenance/test_executor.py` cases `test_persisted_claim_cannot_directly_reenter_production_adapter`, `test_post_claim_last_boundary_failure_pins_without_http_or_refund`, `test_unverified_config_cannot_send_github_credentials_to_another_host`, `test_https_mutation_transport_never_retries_or_follows_redirects`, and `test_factory_missing_binding_fails_before_credentials_transport_or_store`: **5 passed in 37.45s**. These are reruns of existing tests, not newly authored independent probes. They cannot by themselves establish all adapter, real network, source or concurrency boundaries.
* No independent red/green before-and-after probe was performed. The builder's reported 1,165-pass union, one-shot red/green, capacity measurements, process/fork tests and offline wheel evidence are **unverified builder claims**, not carried acceptance evidence in this pass. No full repository suite was run.

## Findings and owner holds

No actionable source finding was established in this incomplete pass. Do not interpret this as a clean review.

The assignment identifies genuine separate delivery gates: explicit activation, independently provisioned shared namespace/ref/genesis and server protections, a trustworthy deployed clock, retirement/drain of bypassing old writers, and an owner-approved transition of historical canonical-Git campaigns. No migration, settlement or live configuration was performed. Changed visible CLI output requires its own before/after founder gate; no approval is inferred from the unrelated M1 warning. These holds are not findings that a stub is missing, nor do fixture passes prove deployment readiness. No exactly-once delivery, atomic close, liveness or external time/protection claim is made.

## Verification limits

The review did not read all assigned supporting plans and historical reports, did not inspect the full semantic diff or every changed source/consumer, did not conduct fresh independent negative/control probes, and did not verify raw final-suite artifacts or original failure histories. In particular changed core lines, runner binding, clock, quota and source-authority paths remain unreviewed. A fresh complete independent whole-feature review is required before acceptance. No source, real state, global configuration, registry, authority, policy, namespace, GitHub or branch changes were made.

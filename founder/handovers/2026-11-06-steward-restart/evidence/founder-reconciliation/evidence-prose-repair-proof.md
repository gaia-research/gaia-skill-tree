# Evidence prose repair proof — #2283

## Change and binding

- Source parent: `c67d90950b0aa37491f5061e76f6cda3319da568`
- Matrix-only checkpoint: `3f4c46fe140f0e3d4a26733baba23f229c30ab94`
- Matrix: `docs/agents/security/2283-dispositions.json`
- SHA-256 at source parent: `ef616f78c39ea79eb12a499db7c2777cb1c3553efcc8c6b14229fc1c5381dda5`
- SHA-256 at checkpoint: `da5b7a39f3a261cc82fcf74e88038c122c9d5b035da5dab7957b8aea66d940e6`
- Exactly one `reason` annotation was clarified: it describes a short local authorization-header specimen used by a positive redaction test and limits what that fixture establishes. The semantic JSON comparison after normalizing only that reason was equal. No source/fixture bytes, finding identity metadata, classification, policy, scanner, or authority code changed.

## Offline checks

Using `SecretScanSensor._findings` directly on Git blobs (no repository scan, ledger action, or live operation):

- Matrix finding before: one `bearer-token`, fingerprint `6729fd0789a7`, line 1372; after: zero. No matched value was printed.
- The matrix contains 39 original rows and 71 original finding entries: D1=30, D2=24, D3=17.
- All 39 distinct original `sourcePath` files have working-tree bytes identical to the source-parent blobs.
- `python scripts/check_security_dispositions.py`: passed (39 rows and reviewed-source-byte checks; checker explicitly does not authenticate identity or scanner authority).
- `pytest -q tests/steward/test_security_reconciliation.py tests/steward/test_sensors_security.py tests/steward/test_sensor_precision.py tests/steward/test_sensors.py`: 336 passed.
- `git diff --check`: passed for the matrix checkpoint.

## Historical/current proof boundary and limits

Completion: proof/docs-only commit `bb9abb0f30988ad35d4e3ed6ccb6a43dda506c08` binds source checkpoint `3f4c46fe140f0e3d4a26733baba23f229c30ab94`, tree `0ae617ccf0f9a6c9768c88972fd386591ac4287a`, matrix SHA-256 `da5b7a39f3a261cc82fcf74e88038c122c9d5b035da5dab7957b8aea66d940e6`, and proof SHA-256 `e10b20d2657ed511ff9e6ab8585784510e26bacccd1bc631d42557ab5e9a7867`. Changed files: `docs/agents/security/2283-scanner-proof.json`, `2283-finish-proof.md`, and `2283-reconciliation.md` in that directory.

Fresh offline replay used baseline `d694986b865e158e21c613683021a9b7822f945c` Git blobs and checkpoint Git blobs, with the respective sensor implementations and `PYTHONPATH=src`. All 39 source paths preserved the exact `(path, pattern, fingerprint)` multiset: 71 total, D1=30, D2=24, D3=17, no new selected match or lost original. All 39 source blobs equal parent `c67d90950b0aa37491f5061e76f6cda3319da568`; that checkpoint diff contains only the matrix. The separate matrix prose match changed 1 to 0, outside the original inventory. No values were printed, saved, or probed. Freshly verified all 224 mirror files per tree and the existing manifest digest, as well as baseline-identical policy, redactor and public scanner hashes. The 23 synthetic controls and 42 upstream tests remain attributed to the prior composition, not this run.

Historical 72 and standalone 71 records, prior controls, compatibility results and mirror records compare equal to the prior proof. The prior composition is explicitly historical at `afe8644bd841473ef3ad5711bed5cc0cd1343667`, matrix `ef616f78c39ea79eb12a499db7c2777cb1c3553efcc8c6b14229fc1c5381dda5`, 71 findings, prior proof SHA-256 `a4344057e0cb98d4f1158c0bb56c06567021de6431ee5091a3820523b7653420`. This does not rewrite the old result as current.

Fresh checks: disposition checker passed; `PYTHONPATH=src python -m pytest -q tests/steward/test_security_reconciliation.py tests/steward/test_sensors_security.py::TestSecretScan` passed 46 tests; `git diff --check` passed; direct detector checks found zero matches in each of the three changed proof/docs files. Worktree clean after commit. The 336 focused tests above were run by the prior Luna worker, not this worker. The earlier standalone import without `PYTHONPATH=src` selected an installed package and failed; corrected imports succeeded.

Fresh independent delta review is required before any merge; the earlier broad source review does not accept this new proof automatically. The checker does not authenticate identity or scanner authority. This is not a canonical scan, issuer attestation, global nonissuance claim, dismissal, or campaign completion. Founder A's 8 MiB whole-settled-run boundary and archive DoD remain open.

# Independent review — #2283 evidence prose and proof delta

## Findings and verdict

**ACCEPT — narrow source PR at `bb9abb0f30988ad35d4e3ed6ccb6a43dda506c08` only.** No blocking defect found in this docs/proof-only delta. The matrix removes an additional document self-match by clarifying a single fixture annotation, without altering the specimen or hiding a finding. Current proof bindings and historical records agree with the actual Git objects. This is an independent engineering decision, not an alert dismissal, issuer certificate, operational approval, main-merge approval or campaign completion.

The separate post-founder document debt is `credential_leak:docs-agents-security-2283-dispositions-json:6be5c08478163c82`: the parent matrix had one `bearer-token` match, fingerprint `6729fd0789a7`, line 1372. This is outside the original 39 paths. The correction does not itself settle its Class C signal; that can naturally cease only on a future genuine observation after legitimate source correction. The original 39 source paths and all 71 selected findings remain positive; no allowlist or detector exception was added.

## Identity, scope and composition

Detached HEAD is the assigned candidate. Runtime environment reports `PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-terra`, `PI_REASONING_LEVEL=high`; independent reviewer, not implementation author. Python 3.14.6, Git 2.56.0. No nested agent or fallback. Tracked status was clean before and after. Graft automatically refreshed its ignored retrieval cache; no tracked/config/source changes were made.

Actual commit parent chain is `c67d90950b0aa37491f5061e76f6cda3319da568` → `3f4c46fe140f0e3d4a26733baba23f229c30ab94` → `bb9abb0f30988ad35d4e3ed6ccb6a43dda506c08`. Enumerated Git diffs:

- Parent to checkpoint: only `docs/agents/security/2283-dispositions.json` (one line changed).
- Checkpoint to candidate: only `docs/agents/security/2283-scanner-proof.json`, `docs/agents/security/2283-finish-proof.md`, `docs/agents/security/2283-reconciliation.md`.
- No code, test, fixture, alias, schema, exemption, policy, detector or redactor change; no UI change.

`git merge-tree --write-tree c67d90950b0aa37491f5061e76f6cda3319da568 bb9abb0f30988ad35d4e3ed6ccb6a43dda506c08` exited 0, yielding `609185c798ba5136aac5d81dbd174d9b00cac626`, exactly candidate's tree. This is automatic local composition against the specified actual root, not a merge or ref update; the parent is an ancestor. No live origin was queried. `git diff --check c67d90950b0aa37491f5061e76f6cda3319da568 HEAD` passed.

## Matrix semantics and direct detector evidence

Parsed both matrix Git blobs. Exactly one reason differs: `tests/test_installability.py`, original finding line 125, `bearer-token`, fingerprint `4d631a121aac`, status `fixture`. Restoring that reason makes the entire JSON objects equal, including all other finding fields, IDs, paths, classifications, source hashes, inventory references and history. Independently verified the complete old bytes with precisely one JSON-string substitution equal the complete new bytes. New text is ordinary printable ASCII, not encoding, escaping or obfuscation. It says the short locally defined authorization-header specimen exercises a positive redaction test, and does not attest an issuer or live credential.

I inspected the test with all string literals scrubbed: `test_diagnostics_are_bounded_and_redacted` feeds a local specimen to `sanitize_diagnostic` and asserts bounded output and redaction. This supports the narrow fixture annotation, not a global nonissuance or whole-file safety claim. The fixture/source bytes are identical to parent.

Using current `SecretScanSensor._findings` directly on Git blob text and a fresh `_SecretTally`, not a canonical scan:

- Parent matrix: exactly one match, pattern `bearer-token`, fingerprint `6729fd0789a7`, line 1372; final matrix: **zero**.
- Each of the three changed proof/Markdown blobs: **zero** matches at final. No raw matched value was printed or probed.
- For all **39 distinct matrix source paths**, actual candidate, checkpoint and parent Git blobs are byte-identical and match each row's reviewed SHA-256. Recomputed current exact finding dictionaries equal all 39 proof `currentFindings`. Their `(pattern, fingerprint)` multisets per path equal original matrix findings, including duplicate multiplicities: D1 **30**, D2 **24**, D3 **17**, total **71**. No selected match lost or added. The parent-to-final file enumeration independently confirms matcher and policy code are unchanged.
- `scripts/upstream_watcher/live.py` remains bound to `ed81ff83b6ea246aada1dee23bbbdbe053f50f506b171c5c816b9e97174a8d12`; `tests/test_installability.py` to `e52dbe05b5e7fa1b89c51a227d369f263d44fe37b4e6d4ef45b126ed58d964df`.

These fresh final-source checks complement, rather than relabel as fresh, the baseline scanner replay. `founder-verification-completion-review.md` independently replayed the original `d694986b865e158e21c613683021a9b7822f945c` and combined checkpoint Git blobs, asserting all 39 baseline/current path-pattern-fingerprint multisets against original 71 and exact current finding dictionaries. Actual source identity and unchanged scanner/pattern bytes carry that result to this delta. Its earlier Terra partial `founder-composition-independent-review.md` remains honestly **BLOCKED** at its historical stage; the subsequent completion review explicitly closed those gaps and accepted combined source `5cbe7e80af20589da4c125289b263c70d869ea55`. Likewise `security-aggregate-independent-review.md` reports independently supported 39-row semantic classifications, and earlier independent 23 controls and official 42 adapted tests/mirror provenance. These are carried forward by source identity, **not rerun by me**, not a whole-file credential safety certificate, and not an assertion that all possible secrets are detectable.

## Proof and history bindings

Recomputed SHA-256 from actual Git blobs:

| Artifact | SHA-256 |
|---|---|
| Parent matrix | `ef616f78c39ea79eb12a499db7c2777cb1c3553efcc8c6b14229fc1c5381dda5` |
| Checkpoint/current matrix | `da5b7a39f3a261cc82fcf74e88038c122c9d5b035da5dab7957b8aea66d940e6` |
| Parent proof | `a4344057e0cb98d4f1158c0bb56c06567021de6431ee5091a3820523b7653420` |
| Candidate proof | `e10b20d2657ed511ff9e6ab8585784510e26bacccd1bc631d42557ab5e9a7867` |

Parsed machine proof binds implementation/source/current commit to checkpoint `3f4c46fe140f0e3d4a26733baba23f229c30ab94`, actual tree `0ae617ccf0f9a6c9768c88972fd386591ac4287a`, current matrix digest above and 71 findings. Its historical founder composition identifies `afe8644bd841473ef3ad5711bed5cc0cd1343667`, actual tree `7706581a705c0f874e20fd4f317e4dfe41289190`, parent matrix digest, 71 findings and prior proof digest above. The prior proof digest is explicitly historical; there is no current self-referential proof hash. The candidate proof file's own digest above is independently computed externally.

Deep JSON comparison against parent, not hash-only: `historicalPriorReplay`, `priorStandaloneReplay`, all `originalRows` including finding dictionaries, `summary`, `controls`, `newlyVisibleMatchesOutsideOriginalInventory`, `cachedOfficialCompatibilityTests`, `fullSupportedMirrorParity` and authority-pattern/public-scanner records are unchanged. This preserves the historical 72 and standalone 71 records, 23 controls, official compatibility metadata and mirror records. New text explicitly attributes controls to prior replay, not a fresh run; no 42-new-tests claim. Recomputed sensor hash and each recorded policy/redactor/public scanner digest; authority files also equal parent blobs. The changed matrix reason is an explicitly disclosed annotation clarification, not a rewrite of original finding history.

## Fresh lightweight checks

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/check_security_dispositions.py`: pass, 39 rows. Its output explicitly says identity and scanner authority **are not authenticated here**. The historical inventory authentication caveat in prior independent reports remains: published final-debt digest and separately supplied metadata snapshot are different snapshots; final-debt bytes were not independently supplied and hashed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/steward/test_security_reconciliation.py`: **10 passed**.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_installability.py::test_diagnostics_are_bounded_and_redacted tests/steward/test_sensors_security.py::TestSecretScan`: **37 passed**.
- Inline read-only Python invoked `_findings` on selected Git blobs, parsed and deeply compared both matrix/proof versions, checked actual source/tree/hash bindings and exact proof findings, and checked the exact single-reason byte substitution. All assertions passed; no matched values output. `git diff --check` passed.

The builder record's 336 tests and later 46 tests are workers' results, not mine. No full repository suite, 42-test Node replay, fresh canonical/fleet scan or actual ledger dismissal is claimed. The earlier incomplete import without `PYTHONPATH=src` remains a worker-reported failed attempt, corrected there, not a successful test here.

## Authority and open boundaries

No live origin/store/ledger/lease/scan/run/record/migrate/rollback, GH/forge operation, credential or issuer probe, registry/trust/rank/evidence-intake mutation, compile/activation, configuration/package install, release/deploy, push or actual merge was performed. No external credential validity or arbitrary issuer nonissuance is inferred. Main protection, CI and explicit human approval remain applicable; this is not new authority.

Founder A's **8 MiB whole-fully-settled-run boundary** and archival DoD remain **OPEN**. A separate integrated archive tree was rejected for missing Class C settlement; its repair belongs to another branch and is not part of this review. Do not call the campaign complete or infer archive acceptance from this narrow source verdict. Only this assigned report was authored durably; temporary Git objects and ignored graft cache are the disclosed local side effects.

# #2283 security/mirror continuation — exact-source proof

## Scope and checkpoint

**Current source binding:** [`2283-scanner-proof.json`](2283-scanner-proof.json) binds prose-only matrix checkpoint `3f4c46fe140f0e3d4a26733baba23f229c30ab94` (tree `0ae617ccf0f9a6c9768c88972fd386591ac4287a`). A fresh offline Git-blob replay preserves the exact original 71 occurrence multiset across 39 paths: D1=30, D2=24, D3=17. The matrix clarification removed one separate document match (1 to 0), outside that inventory. The 23 controls are retained from the prior composition replay, not rerun. The [founder/watcher composition proof](2283-founder-composition-proof.md) at `afe8644bd841473ef3ad5711bed5cc0cd1343667` and the earlier 72/71 replays are historical. Fresh independent delta review remains required; this is not a canonical scan or issuer claim.

### Corrective replay (2026-11-05)

At source commit `a25703a7f` (full SHA recorded in Git), the sole benign prose match described below was removed by rewording only the comment above `test_diagnostics_are_bounded_and_redacted`. Fixture literals, test code/assertions, scanner, policy and redactor are unchanged. The updated dispositions matrix changes only the reviewed source SHA-256 for `tests/test_installability.py`. An actual offline replay on those exact source bytes reports **71 current findings**, D1=30, D2=24, D3=17; every original `(pattern, fingerprint)` multiplicity remains. The former 72-result at `72bf2be0da18a6f410d9936b75762e05c1736508` remains historical and is not recast as though it did not occur. Machine proof: [`2283-scanner-proof.json`](2283-scanner-proof.json). This is scoped source-bound evidence, not a canonical scan, independent acceptance, or authority/credential identity claim.

Implementation under test: **`72bf2be0da18a6f410d9936b75762e05c1736508`**, on `dev/steward-security-triage-2283`. Baseline: `d694986b865e158e21c613683021a9b7822f945c`. This continuation found no verified source defect requiring another functional edit; its changes are evidence only.

Read-only GitHub reads confirmed the [founder lock](https://github.com/gaia-research/gaia-skill-tree/issues/2283#issuecomment-6640916880) and [hygiene receipt](https://github.com/gaia-research/gaia-skill-tree/issues/2283#issuecomment-6640982938). The original receipt remains `steward-20261104T172307Z-5c244581790fe867`.

- [Individual dispositions](2283-dispositions.json): **39 original debt IDs**, D1=16 / D2=14 / D3=9. The ID set equals the read-only canonical inventory snapshot. Original locations/fingerprints and source hashes are retained. Matrix SHA-256: `c6260d48ab2d89cf7e59bdd84f10a6629b5195ba7cb45c15bca0ed411d738917`.
- [Implementation/provenance report](2283-reconciliation.md): source selection, callers, individual inspection, compatibility limits and the **unactivated** routing amendment proposal.
- [Machine-readable before/after proof](2283-scanner-proof.json): each original row's match counts, positive controls, unchanged authority/pattern-file hashes, cached upstream test hashes and full supported mirror manifest digest.

These are **per-original-match evidence**, not whole-file safety certificates, issuer attestations, scanner exemptions or closure receipts. File-level categories remain 28 harmless source-pattern matches and 11 fixture-bearing files; a fixture-bearing file can also contain harmless code matches. All original findings still trigger the detector. Nothing was blanket dismissed.

The three `steward-security-*-2283` decision records remain valid `steward-decision-v1` **locked group policies**, not 39 per-finding clearances. All **23 canonical decisions** validate and have unique IDs. No decision, shared ledger, history, issue, label, registry/trust/rank/intake, workflow, policy, allowlist or operating campaign was changed in this continuation. No fleet scan/run/record/abandon, push, merge, installation or global configuration change was performed.

## Historical 72-result before/after scanner evidence

Executed offline on the 39 selected paths only: baseline `SecretScanSensor._findings` on baseline Git bytes, versus the committed implementation on reviewed working-tree bytes. Both modules use the same unchanged credential patterns/redactor. Baseline and reviewed source SHA-256 values were asserted against every matrix row. This is **not** a canonical Steward scan or fresh inventory of the whole repository.

| Cohort | Original file rows | Original individual matches | Baseline detected | Reviewed detected |
|---|---:|---:|---:|---:|
| D1 skill pairs | 16 | 30 | 30 | 30 |
| D2 tests | 14 | 24 | 24 | 25 |
| D3 app/workflow/docs | 9 | 17 | 17 | 17 |
| **Total** | **39** | **71** | **71** | **72** |

Every original `(pattern, fingerprint)` multiplicity survives. Line numbers may move after additive fixture-provenance comments; original line numbers in the matrix were not rewritten.

**The historical extra D2 match is disclosed, not suppressed:** `tests/test_installability.py:123`, `bearer-token`, fingerprint `e77a4a61964d`. It is ordinary prose after the word “Bearer” in the new synthetic-provenance comment. This exact comment match is harmless; it is outside the original 39-row inventory. No debt ID was invented for it, and the original diagnostic/redaction fixture remains intact.

**23 generated offline control comparisons:**

- Eight credential families (AWS, GitHub classic, GitHub fine-grained, Anthropic, OpenAI, Slack, private-key header, Google), each in `src/` and `tests/`: **all 16 detected before and after**; values absent from serialized findings.
- Four unrelated same-line comment markers plus one neighbouring synthetic value: **0 before / 1 after for each**. This reproduces the old false-negative defect and demonstrates the committed tightening. A comment/other value no longer exempts a different credential-shaped match.
- Existing in-match public example placeholder: **0 / 0 in tests; 1 / 1 outside tests**. Existing narrowly scoped heuristic behavior remains unchanged; this is not an assertion that lexical heuristics prove issuance or safety.

`POLICY.yaml`, `primitives/redact.py` (including `CREDENTIAL_PATTERNS` and `scrub`) and `securityScanner.py` are byte-identical to baseline; their SHA-256 values are in the proof JSON. `credential_leak` stays **C** and mirror parity stays **A**. The matrix is not consumed by scanner/redactor/closure machinery.

## Compatible source selection and full parity

The existing implementation is retained, not restarted or replaced:

- The checked-in Impeccable bundle came through local commit `3e9e33820c833fb2cf10a9ad31024c63590b83b7`. Its lock content hash is not an upstream commit attestation.
- Official extraction commit `325aeaf239808a0a8a763fe328e1dc1c3e2351df` supplies the compatible modular cohort. The retained extracted event validator hashes to `c0ee57b8306f8b1f31b00961017c849b7f352887bd8c889981805e14b8d2e63c`. Root parser/validator entrypoints delegate to that cohort, preserving exports/consumers; quoted YAML-key parsing is additive.
- Upstream main observed by the earlier worker at `5af4319c4e7a7ee3e5e2b9fe899bcfb21c6190cb`, version 4.8.0, has a Rust-engine replacement introduced by `e2ff625b6371c3f05a31e576fe9e7d063bcb112b`. It was **not** proven drop-in compatible and was not installed/copied. Firecrawl upstream observation was `458d9d0331fb31121fd38e0e09ae5036f952784b`; no update is implied.
- Root/extracted browser UI cohorts differ in DOM expectations; they were deliberately not blind-swapped. Upstream-owned skill docs and audit history are retained. The eight D1 canonical/mirror duplicate groups remain individually traceable.

Fresh parity check covered **224 supported files per tree**, byte-for-byte, including path-set equality: **zero missing, differing or mirror-only paths**. Sorted path/content manifest SHA-256: `8d2debc9dd3b57fb40822744e1bb5df95835dee3ce277c50805dadc25cb8b6dc`. Existing locally owned exclusions are `skill-creator/**`, `**/__pycache__/**`, `**/*.pyc`; they were neither broadened nor presented as mirrored. The existing `python scripts/sync_agent_skill_mirror.py --check` passed. Earlier canonical edits used that script for propagation; this continuation made no source/mirror edits.

Five cached official test files were checked to differ from their local adaptations **only by import paths**. Their original hashes are in the proof JSON. Their upstream provenance is retained from the prior session's read-only retrieval, not represented as a fresh network attestation.

## Verification receipts

Fresh checks at implementation SHA `72bf2be0da18a6f410d9936b75762e05c1736508`, Android aarch64 / Termux Python **3.14.6**, Node **v24.17.0**:

```sh
PYTHONPATH=src python -m pytest -q \
  tests/steward/test_security_reconciliation.py \
  tests/steward/test_sensors_security.py::TestSecretScan \
  tests/steward/issuehygiene/test_b7_scrub.py \
  tests/steward/issuehygiene/test_b8_census.py \
  tests/test_security_scanner.py
# 98 passed in 12.87s; includes the six Node compatibility/refusal tests

PYTHONPATH=src python -m pytest -q \
  tests/test_installability.py::test_diagnostics_are_bounded_and_redacted
# 1 passed in 0.14s

node --test generated-output/security-reconciliation/upstream/local-*.test.mjs
# 42 passed, 0 failed, 0 skipped (cached official test adaptations)

python scripts/check_security_dispositions.py
# At the historical implementation SHA above: 39 original finding rows match reviewed source bytes; scanner authority unchanged
# This was an overbroad checker message, corrected by the bounded repair proof; not evidence of authority verification.
python scripts/sync_agent_skill_mirror.py --check
# agent skill mirror is in sync
```

Direct desk validation with `load_decision_records` / `_check_record`: **23 valid, unique records**. Read-only canonical snapshot comparison: **39 credential IDs, exact matrix ID-set equality**. The separate offline comparison produced the 39-row / 23-control evidence above, with assertions on all original source hashes and fingerprint multiplicities. No raw matches or generated control values were exported.

Earlier-session results were recovered by filtered read-only extraction of commands/counts, **not transcript export**, and are not claimed as newly rerun tests:

| Earlier verification | Observed result |
|---|---|
| Security sensors/precision/sweep safety/mirror repairs/desk | 311 passed |
| D2/D3 fixture modules, auth, badge reconciliation, curation, installability, Jev and public scanner | 376 passed, **1 platform failure** |
| Reconciliation + Jev CI budget checks | 25 passed |
| Final reconciliation/security/precision/safety/repairs/desk/Jev-budget pass | 336 passed |
| Cached pinned upstream compatibility tests; local Node tests | 42 + 6 passed (also exercised freshly as described above) |
| Baseline/new parser and validator differential checks | 6 parser/coverage inputs + 156 event inputs passed |
| Canonical/mirror Node script syntax | 150 scripts passed |

**Outstanding platform evidence:** `tests/test_installability.py::test_observation_temp_creation_is_exclusive_and_cleans_only_its_temp` could not pass because this Termux Python has **no `os.link` attribute**, freshly reconfirmed. It was not rerun, skipped, emulated or “fixed” outside scope. A platform providing real hardlinks must supply this receipt. This is not an all-green or full-suite claim.

## Review boundary

Independent Terra acceptance remains parent-owned. Integration, live re-observation, deduplicated ledger projection, closure and campaign completion are not claimed. The governed D1 conflict-routing proposal remains **unactivated**; production credential alerts cannot be automatically turned into parity debt. Source drift (including another worker's changes to `scripts/upstream_watcher/live.py`) invalidates exact-byte evidence and requires re-review. The matrix/checker does not approve newly added matches.

No original match was verified as an embedded live credential; no issuer was contacted and no revocation/rotation is claimed. Runtime session outputs/query strings/state files and workflow credential handling are not comprehensively certified. Browser rendering, a complete live-server session, Node 18, Windows and the remaining platform hardlink test were not verified here.

## Minimal offline replay of original-match comparison

This does not write operating state or invoke the fleet scanner. Run from the implementation checkout; it loads historical source in memory and emits counts only. The existing focused positive-control tests above complement it.

```sh
PYTHONPATH=src:. python - <<'PY'
from collections import Counter
import json, subprocess, sys, types
from pathlib import Path
from gaia_cli.steward import sensors_security as new
base = 'd694986b865e158e21c613683021a9b7822f945c'
old = types.ModuleType('gaia_cli.steward._security_2283_replay')
sys.modules[old.__name__] = old
blob = lambda p: subprocess.check_output(['git', 'show', f'{base}:{p}'])
exec(compile(blob('src/gaia_cli/steward/sensors_security.py'),
             '<baseline>', 'exec'), old.__dict__)
totals = Counter()
for row in json.loads(Path('docs/agents/security/2283-dispositions.json').read_text())['rows']:
    path = row['sourcePath']
    expected = Counter((f['pattern'], f['fingerprint']) for f in row['findings'])
    for label, module, text in [('before', old, blob(path).decode()),
                                ('after', new, Path(path).read_text())]:
        found = module.SecretScanSensor._findings(path, text, module._SecretTally())
        actual = Counter((f['pattern'], f['fingerprint']) for f in found)
        assert not (expected - actual)
        totals[row['group'], label] += len(found)
print(dict(totals))
PY
```

# #2283 security checker honesty repair proof

## Exact SHA and scope

Repair commit: `efa19225281411af514364125e07e77cd3cdb6b5` (`fix(security): narrow disposition checker claims`). Parent: `8ea130838c466a16d390c6b3ef3f723b8e728e6b`. Approved commit identity: Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com>.

Scope is limited to `scripts/check_security_dispositions.py`, its focused regression test, and the narrow current-proof documentation in `docs/agents/security/2283-reconciliation.md` plus correction/context in `2283-finish-proof.md`. No matrix row, finding ID, source metadata, fingerprint, scanner, redactor, policy, or decision behavior was changed.

## Findings repaired and demonstrated

- Removed the unsupported success assertion that scanner authority was unchanged. The success text now says precisely that 39 matrix rows pass count, shape, and reviewed-source-byte checks, and explicitly states that identity and scanner authority are not authenticated.
- The checker now labels IDs as unique strings rather than authenticated original IDs. Regression replaces an ID with `debt:credential_leak:invented` and demonstrates the checker accepts it: the matrix provides no independent identity source. This limitation is explicit in current reconciliation docs; historical checker output in the earlier finish proof is retained as a historical result and marked overbroad, not silently rewritten as valid authority evidence.
- Existing checks still reject malformed row counts, group counts, duplicate IDs, unsafe/symlink paths, source hash drift, and invalid/missing finding metadata. Existing count/control/mirror/fingerprint tests and source contents remain unchanged.

## Verification run at this repair

```sh
PYTHONPATH=src:. python -m pytest -q tests/steward/test_security_reconciliation.py
# 10 passed
python scripts/check_security_dispositions.py
# 39 matrix rows pass count, shape and reviewed-source-byte checks; identity and scanner authority are not authenticated here
git diff --check
# passed
```

One initial regression run failed because the temporary test root could not supply the matrix's reviewed source files; the test was corrected to execute the checker against the repository root, without weakening the checker. The final focused run above passed.

## Explicit remaining gates / limits

- **Original ID authenticity:** not established by this checker. Separate inventory comparison is independent evidence and must not be represented as checker proof. A plausible invented ID passes its current unique-string/prefix shape checks.
- **Platform:** the previously documented `os.link`-dependent installability check remains unverified on this Termux runtime; this bounded repair does not address or infer a platform receipt.
- **Cross-lane source-hash gate:** matrix-bound source-byte checks only cover the currently listed paths and hashes. Any cross-lane source change (including the upstream watcher path previously identified) invalidates applicable evidence and requires refreshed hashes/review; the matrix is not an authority gate.
- This work does not establish scanner/policy authority, verify live credentials, authenticate the complete historical inventory, or complete the #2283 mission. Fresh independent reviewer-shared acceptance remains required. Parent retains push/PR/ledger ownership; no push or integration action was taken.

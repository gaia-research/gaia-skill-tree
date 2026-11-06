## Status
issues_found

Route verified: `gpt-6.1-terra`, high effort; no fallback. This is an assurance-design pass, not an architecture ruling or patch review.

## Findings

- `src/gaia_cli/steward/fullrun.py:1283` - [warning]: Existing compaction is **lossy**, not archival. Beyond five terminal runs it replaces nested phase lists/maps with counts and removes the desk; beyond 25 it empties steps, actions, phases, proof artifacts, CI results and agent assignments. `blocked` and `failed` are considered terminal, although their records may still contain decision-pending or operationally relevant material. Preserve eligible detail in verified shared storage **before** removing it; do not infer eligibility from status or age alone. Already-compacted content cannot be reconstructed from the hot ledger itself.

- `src/gaia_cli/steward/fullrun.py:930` - [warning]: Actions carry outcome-based replay protection; `_addAction` also deduplicates step IDs and stores idempotency keys (`:1254`). Removing action records or settled-work tombstones can permit duplicate effects or make legitimate retries unrecognizable. Preserve the information needed to reject conflicting outcomes, accept identical retries, and reconcile pending/adopted work. Preserve leases, lane state, operations, open Class C references and all active, blocked and escalated work.

- `src/gaia_cli/steward/ledger.py:66` - [warning]: The current 1 MiB limit is enforced independently in serialization, deserialization and the Git blob-size precheck (`:238`, `:252`, `:463`). A configurable **8 MiB default** must be the same validated byte limit for every read and write path, including file and Git stores; report actual serialized UTF-8 bytes, limit and 70%/90% alert levels. Older binaries cannot safely read a ledger once it exceeds 1 MiB: coordinate rollout and rollback rather than reverting code blindly.

- `src/gaia_cli/steward/ledger.py:178` - [warning]: Unknown top-level fields are rejected. An archive pointer/index therefore requires an explicit compatibility and rollout strategy; old clients must fail closed rather than overwrite new metadata. The present Git CAS preserves fast-forward updates, but deletion between the remote-tip check and push remains a documented race (`:503`): do not claim stronger atomicity than the transport provides.

- `src/gaia_cli/commands/steward.py:452` - [warning]: `auto` falls back to a local ledger when the remote probe fails. Shared-ledger verification and campaign operation must explicitly select `--ledger git`; local success is not shared-ledger proof.

### MUST-pass adversarial matrix

1. **Transfer and retrieval:** Snapshot eligible records; verify remote read-back length, cryptographic digest, schema and record identity *before* hot CAS. Independently fetch from a second clone/machine, search by run, debt, routine and time, and recover exact evidence and provenance. A local Git object or ignored `.gaia` path is not durable shared access.
2. **Atomicity:** Inject failure before upload, after upload, after verification, before/after hot CAS, and on ambiguous push timeout. Retry safely; concurrent writers must re-evaluate eligibility against the new hot version. Orphaned archives remain harmless and discoverable; a failed hot CAS never drops detail. A mutable ref named by a hash is not itself immutable: verify the fetched content and protect against replacement, deletion and unreachable objects.
3. **Failure closed:** Missing, corrupt, wrong-identity, truncated, inaccessible or schema-incompatible archives must not cause resolution, deletion or a successful history result. Test duplicate uploads and same-key/different-content collisions.
4. **Operational equivalence:** Compare before/after active work, Class C references, leases, lane, operations, pending actions, idempotency behavior and reconciliation outcomes—not just counts. Exercise abandoned-run adoption, late outcomes, identical and conflicting retries, and concurrent lease holders.
5. **Boundaries:** Read legacy 1 MiB data; test actual UTF-8 serialized sizes just below, at and above configured limits on both stores, including Git preflight. Test 70% and 90% thresholds and invalid/inconsistent configuration. A rejected write must not prune or advance the ref.
6. **Rollback:** Test old and new clients against migrated data, unavailable archives and concurrent advancement. Rollback must retain newer committed work and archive references; never force-reset the shared ref to an old snapshot. If the old reader cannot handle the size/schema, use a compatible forward repair or stop until a safe migration is authorized.
7. **Regression:** Extend `tests/steward/test_ledger.py:214` concurrency/CAS coverage and `tests/steward/test_fullrun.py:524` compaction coverage; run the full regression suite and a separate fresh independent verifier.

### Proposed later live proof—not executed here

- Coordinate an agreed quiet window with the campaign owner; record the deployed SHA, explicit Git transport, remote ledger tip, byte size, generation, lease/active-run state, and a protected before-state digest. Abort if another run owns the lease or transport/identity is uncertain.
- Let the authorized operator perform a **genuine canonical cycle already warranted by campaign work**, with normal gates and no synthetic debt, padded payload, invented history, forced closure or extra action. Record its real run ID and resulting shared ref.
- Independently fetch that exact remote commit from a second machine/clone; verify its `ledger.json` byte count is **greater than 1,048,576**, deserialize it with the deployed reader, and compare its run/action/lease/work state and archive retrieval against the before-state plus the legitimate cycle’s receipts. Confirm no unexpected changes and re-observe under normal authorization.
- If the genuine cycle does not produce a persisted ledger over 1 MiB—for example because compaction reduces it—**report the live size proof as not yet achieved**. Isolated >1 MiB tests are valuable but cannot substitute for that live claim.

## Verification Limits

No live scan, full run, record, ledger or forge write was performed; no files were modified. The issue authority was read live, and the checkout was at `1963a47f4`; existing untracked `.pi` directories were present. The static graft card for the CLI was consulted; graft’s self-refreshing commands were not run because they may write files. This was targeted source and test inspection, not a complete read of every line of `fullrun.py`, every contract, or a test execution. Archive design and future patches require separate verification.

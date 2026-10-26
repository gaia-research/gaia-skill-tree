# Watcher transactional implementation self-check

**Code revision:** `895b0486ef94ff1ec2b9804baee88d183b2206f6`  
**Scope:** bounded watcher worker, #2148 / draft #2151, integration target `dev/yggdrasil-iv`, not `main`.  
**Authority:** engineering self-check only. This is not an independent verification receipt, issuer deployment, production acceptance, or campaign completion.

## Preserved source and prerequisites

- Continued preserved source at `946ec93ab265ea51aecd272f17bf76d48b18054d`; the three dirty files were checkpointed in `58f0bcaf7` before further implementation.
- Accepted integration `4b73e62814fca16a01bd1e71325e7abb97316c95` remains in ancestry.
- Inspected/cherry-picked ledger prerequisite `04205d37c75b4a1a93b1d93436638e04346ccaaf` as `f4a0bcfde`, and dispatch quoting prerequisite `e50778dca4287a66fe6eca6fbed39dc2b0c21eb1` as `a84f65358`. Neither prerequisite was reapplied after the environment crash.
- Implementation checkpoints: `426ef7e27` (fresh-state fold), `9b07f0978` (process/crash/integrity proofs), `895b0486e` (domain bridge, replay hardening and documentation). Local recovery refs accompany each checkpoint. Recovery-only WIP backups were not applied/reset/cherry-picked.

## Focused tests actually completed

All commands used `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`, followed by the selection below. Commands were short synchronous runs, not background children left uncollected.

| Selection | Result |
|---|---|
| `scripts/upstream_watcher/tests/test_challenge_watch.py` | 16 passed |
| `scripts/upstream_watcher/tests/test_challenge_watch_admission.py` | 11 passed |
| `scripts/upstream_watcher/tests/test_challenge_watch_transactional.py -k two_process` | 3 passed, 14 deselected |
| `scripts/upstream_watcher/tests/test_challenge_watch_transactional.py -k 'not two_process'` | 14 passed, 3 deselected |
| `scripts/upstream_watcher/tests/test_workflow_input_safety.py` | 4 passed |
| `tests/steward/test_ledger.py -k 'leaves_no_refs_outside_refs_steward or preserves_custom_fetch_mappings_and_sentinel_refs'` | 2 passed, 114 deselected |

**50 distinct focused tests passed**, not a single full-suite run. AST parsing of the engine/bridge and `git diff --check` passed. The combined test command interrupted by the environment crash returned no result and is **not verified or included**. Earlier failures were repaired, not counted as acceptance. Parent retains ownership of the full watcher/ledger suite, combined replay and independent review.

## Actual concurrent-process evidence

These are ordinary Python processes, not agents, running against two independent clones of one **local fixture bare Git remote**. Each pair reaches its first remote CAS with an identical expected version. A barrier makes B attempt that stale CAS after A commits, so B must conflict, load fresh state and retry. Fixture PIDs/remote commits below identify the observed run; they are not production processes/refs.

| Scenario | A / B PIDs | Common first expected remote version | B retry version | CAS conflicts A / B | Poll requests A / B | Newly reserved intents A / B |
|---|---|---|---|---|---|---|
| Newer partial A; older full B | 31989 / 31990 | `4e1831b4d511362b0a35d81e1fa689e98fd4b8a7` | `2d9155439ae60ca3812592ad22b95331fa092f07` | 0 / 1 | 2 / 7 | 1 / 1 |
| Same semantic upstream event, different poll times | 32169 / 32170 | `81bd52f0bb7c4c88f186e427f9800b8c78d980e2` | `6f58d3de279968c6423f5fb3d53a14e7b1c07bfd` | 0 / 1 | 7 / 7 | 1 / 0 |
| Same outage, different poll times | 32339 / 32340 | `dbd1e178d53d9a0f5d9be995c8fd417576c9f459` | `6e1aa03cebc1496f9abf5b96e985b8cc26dc4e0d` | 0 / 1 | 1 / 1 | 1 / 0 |

Assertions verify: newer release state survives the older loser; older full observation contributes known SHA absent from the newer budget-limited observation; an admitted but unevaluated second input survives; both observations remain; accepted packet bytes reproduce; unrelated operations and sentinel remote-tracking refs remain unchanged. HTTP counts do not increase on CAS retry.

A separate worker exits with status **73** after successful shared save, before local materialization. The test asserts no packet directory in that clone. A fresh clone, with no input file and a deliberately invalid local ledger cache, restores the complete packet solely from shared operations bytes; default-unavailable admission performs **zero HTTP requests** and reserves no duplicate intent.

## Additional failure/authority proofs

- Eight shared-state tamper variants fail closed, including rehashed packet-body edits, identity/reference mismatch, resealed projected-state changes, observation/input changes and missing accepted packets. Local packet tampering is rejected rather than overwritten.
- Filtered manifests/zero budget cannot drop accepted inputs, observations, known fields or packets; immutable context conflicts fail closed. Malformed HTTP-200 release/SHA responses remain unknown without erasing prior known values.
- Outage steps and continued unknown-review windows dedupe across daily virtual polls. Recovery followed by a new outage/unknown episode produces a new context-bound intent. Rate-limit reset delay is captured once and remains reproducible when the process clock changes; a skipped request is not an outage observation.
- The explicit production bridge revalidates actual challenge-domain opening/closure histories through the existing trusted receipt resolver port. Missing/altered/non-independent receipts, mismatched repository pins, native leads, experiments and inline flags are rejected. Cached inputs are re-resolved each run. A stale open lookup cannot reactivate technical closure.
- No production `StewardReceiptChallengeAdapter` remains. The CLI has no configured issuer/resolver; default and shadow requests cannot authenticate inline JSON or close challenges.

## Held gates and limits

- No live issuer, public receipt/security activation, canonical evidence/trust/rank/Origin mutation, general ecosystem crawling, deployment, PR creation, merge, schema adoption or RFC closure occurred.
- Existing workflow cron/permissions/default activation were not expanded. The repository challenge-watch variable remains an external reviewed configuration gate; this work does not set it.
- Full combined tests/replay and independent reviewer acceptance remain outstanding with the parent. Four elapsed operational weeks are **not** proven by virtual clocks or these process tests.
- No exactly-once external delivery claim: there is no HTTP packet publisher here. Downstream delivery is at-least-once unless the remote honors the stable packet ID as an idempotency key.
- Hashes/provenance checks do not authenticate a malicious writer able to rewrite the entire trusted store. Journal growth is not compacted automatically; transport bounds fail closed. Legacy v1 state requires explicit audited migration and is never silently dropped.

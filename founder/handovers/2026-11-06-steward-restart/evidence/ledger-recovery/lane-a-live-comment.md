## Lane A: actual >1 MiB shared-Git persistence independently VERIFIED

Fresh independent **OpenAI Codex Terra high** verifier accepted **actual persistence only**, using a separate fresh Git object store fetched directly from GitHub (not our worktree cache or a private ledger copy).

| Evidence | Verified value |
|---|---|
| Integrated code | `d694986b865e158e21c613683021a9b7822f945c` (#2284) |
| Accepted implementation head | `6bc3688705c14b10f7ded3e6caeb721dd278c3bd` |
| Shared ref | `refs/heads/steward/ledger` |
| Exact fetched shared commit | `96f46877691d1f6af88df974f033ec8c0c7c2040` |
| Generation | **368** |
| Actual ledger size | **1,114,811 bytes** — exceeds the former 1,048,576-byte cap |
| Blob SHA-256 | `dbfcaec53cddce1fe0182d9b21447c13ce911f1b71766ec7ab8b92b0e409900e` |
| New-reader default | **8,388,608 bytes**; canonical shared-Git load succeeded |
| Same real payload at 1 MiB limit | Correctly refused before load; no remote write |

### Preservation and legitimate execution

- Baseline shared commit `9b3e58abd5117cd7b8c607859ac8cb68525ba999` was fetched through actual shared ancestry and its exact 1,005,272-byte / SHA-256 baseline verified.
- **All 13 prior terminal run records are exactly equal** (seven completed, six abandoned), including full retained phases, action outcomes and proof/replay references. No additional terminal history was trimmed.
- **All six prior work records remain exact**. Of 191 prior lane entries, 190 remain exact; the only changed entry is the explicitly authorized unused-import debt moving queued → dispatched, attempt 0 → 1, with its existing history preserved.
- The earlier rejected trust attempt remains blocked, rejected and unresolved; it was not recalibrated or misclassified as repaired.
- New genuine run `run-20261104T191141Z-c3a4df1e` and pending dispatch `dispatch-1fe491eede58c1225547`, attempt 1, are durable in the fetched payload, with the run holding its own lease.
- `maxInFlight=2`, `maxAttempts=2`, cooldown 3,600 seconds remain unchanged. No Class C decision/execution was observed in the comparison.
- #2284 remote checks have since completed successfully; one conditional design job was skipped. This is distinct from the earlier pending-CI status.

**Assurance limits:** this is point-in-time proof at the exact fetched commit, not a claim that the ref cannot advance. It does **not** establish Lane B archive migration, portability of old local artifacts, final Class B repair/acceptance/integration, parallel sensor reconciliation or overall campaign completion. Lane B remains WIP in #2287; the independent Luna Class B builder is still in progress. No release, deployment, main merge, Class C adjudication or history deletion.

Full structured independent receipt is retained locally as `.gaia/steward/campaigns/2026-11-05/ledger-recovery/lane-a-live-assurance.json` for inclusion with the final integration evidence.

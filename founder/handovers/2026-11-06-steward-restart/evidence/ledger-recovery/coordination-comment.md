## Parallel ledger recovery started

Founder authorization recorded for the bounded 8 MiB hot ledger and non-destructive, indefinitely retained archival memory. Verified lane PR merges are now explicitly authorized; this does not authorize Class C execution, history rewriting, release or deployment.

### Live baseline
- Shared checkpoint: `9b3e58abd5117cd7b8c607859ac8cb68525ba999`.
- Exact current `ledger.json`: **1,005,272 bytes** (95.87% of old 1 MiB bound; 11.98% of authorized 8 MiB bound). This is the post-abandon snapshot; earlier byte counts refer to earlier snapshots/proposed writes.
- 13 terminal run records (seven completed, six abandoned); compact run content is the main contributor (~757 KB).
- **No active run, lease holder or in-flight dispatch.** The abandoned attempt will not be restarted or duplicated.

### Ownership and gates
- **Lane A:** Luna medium, isolated cap/config/size telemetry and transport-boundary regression tests. No archive/full-run edits; no shared-ledger writes.
- **Lane B:** Sol high, separate isolated archival/index/retrieval/migration/rollback implementation, tests and operational documentation. No shared-ledger writes.
- **Lane C:** Terra high, independent safety/assurance design; fresh independent patch verification before integration and live operation.
- Lead alone serializes actual ledger operations and campaign ownership. Engineering workers are not campaign dispatch owners.

Lane A will be reviewed and merged independently so archival engineering does not delay the immediate unblock. A restored write will not be called archival completion. Class C remains queued and unchanged. Further comments will carry exact PRs, SHAs, tests and live persistence/archive retrieval evidence.

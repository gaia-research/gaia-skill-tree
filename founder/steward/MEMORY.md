# Shared Steward historical memory

Engineering contract for #2283. **This document does not authorize a live
migration, campaign run, Class C action, history rewrite, release or deployment.**
Lead review, full Steward regression and fresh independent assurance precede
live operation. All implementation tests use disposable Git remotes.

## Read, preview, apply

Memory commands always use this checkout's explicit shared `origin` Git ledger
(`steward/ledger:ledger.json`). There is no private/local fallback, scan, model
call, forge action or campaign dispatch. Output is JSON, except `--snapshot`,
which emits the exact original source-ledger bytes, including other runs.
Protect this output as carefully as the original ledger.

```sh
gaia steward full archive                         # read-only eligibility + capacity
gaia steward full archive RUN_ID --max-runs 1      # read-only selected preview
gaia steward full show RUN_ID                     # hydrate and verify original run
gaia steward full show RUN_ID --snapshot > source-ledger.json
gaia steward full history --run RUN_ID --pages 1
gaia steward full history --debt DEBT_ID --routine 18 \
  --since 2026-01-01T00:00:00Z --until 2026-02-01T00:00:00Z
# Continue even after zero hits when nextCursor is non-null:
gaia steward full history --cursor '{"kind":"index","sha256":"...","size":1234}'

# Only the authorized lead, after review and a fresh preview:
gaia steward full archive RUN_ID --max-runs 1 --apply
gaia steward full rollback RUN_ID                  # read-only verified preview
gaia steward full rollback RUN_ID --apply          # forward CAS, never reset
```

`--max-runs` is 1..32; one migration publishes one index page. Explicit apply
accepts at most 32 IDs. History reads 1..10 index pages per call (default 1),
<=32 events and <=256 KiB per page. Matching entries additionally verify their
run, source snapshot and provenance anchor; a search hit is not a work verdict.
Time filtering uses run-interval overlap. Canonical `retro.routines` lists of
`{routine,state,detectors}` and `options.routine` are indexed; an older numeric
routine **count** is not an ID. Cursors are strictly bounded kind/hash/size
object descriptors, never file paths or shell expressions. A cursor selects
an immutable archive page; it is not a credential or an authority assertion.

## Retained hot state and eligibility

Only an explicit transfer externalizes **phase payloads** of a settled terminal
run. A terminal label or age alone never suffices. Active/queued/blocked/
escalated/decision-pending runs, pending or unknown actions/steps/decisions,
unresolved/deferred work, any current lease reference (even expired), and
references to non-resolved work adopted by another run are ineligible. Unknown
phase lifecycles fail closed. `ok` is the canonical completed phase status,
not an override for a run's unresolved work.

Actions, outcomes, steps, idempotency/dedup IDs, leases, desks, decisions,
receipts, proof-artifact records, all work and its history, lane state and
other operations remain hot and unchanged. Reference keys are deduplicated
into the hot run pointer for search/reconciliation; this is not evidence of
resolution. Nonempty Class C, pending decision or unresolved phase records
remain entirely hot. Existing silent terminal-run compaction is disabled.

### External artifacts: deliberate refusal, not invented portability

This version archives ledger JSON bytes, **not local artifact files**. It never
opens arbitrary referenced files. A phase containing a proof/artifact/path/
file/URL reference, including path-looking strings under unknown keys, is
ineligible; the whole original run remains hot. A hash or local-path string
is not the referenced bytes. Proof/receipt/diff records outside phases remain
verbatim hot and are explicitly **not** promised portable. `show` discloses
that limitation in `retrievalGuarantee`. No canonical evidence, receipt,
provenance or verdict is invented or rewritten.

Settled observation/retro phase JSON without external file references can
actually migrate, including >2 MiB payloads, and is independently retrieved
from a second clone in tests. The recorded production checkpoint is **not**
assumed eligible: completed runs can still have escalated associated work or
open founder decisions. An empty preview means preserve state, not permission
to weaken the gates or a completed production migration. Safe file bundling is
not implemented or claimed; artifact-bearing phase records stay ineligible.

## Durable format and transfer protocol

1. Load one bounded canonical generation and compute lifecycle eligibility.
2. Publish the **exact source ledger bytes** as a content-addressed snapshot.
3. Publish a separate content-addressed provenance anchor containing the source
   commit identity, parented by that exact commit. Identical bytes at different
   commits can share a snapshot, but cannot reuse an unrelated provenance anchor.
4. Publish versioned run envelopes containing the full original run, source
   snapshot descriptor, source commit, source anchor and ledger-ref identity.
5. Fetch each object from the remote; check byte count, SHA-256, schema, run
   identity, source-byte equality and source-commit ancestry. Verify hydration
   against the exact hot projection before any hot CAS.
6. Publish/read back a bounded immutable index page linked to the previous head.
7. Only then CAS the hot ledger, replacing phases with an explicit pointer.
   A conflict reloads and recomputes eligibility; it never reuses a stale hot
   document. No saving means no hot write.

Objects use immutable branches
`steward/archive/v1/{snapshot,anchor,run,index}/SHA256`, with a `payload` blob.
Reads always fetch/read back from transport; no local cache is trusted as a
substitute. Snapshots are bounded at 64 MiB and run envelopes at 65 MiB, matching
the supported configured hot maximum plus bounded envelope overhead. This is
not an unlimited-object store. No force pushes, deletion, expiry or GC exists.
Git snapshots/anchors retain source ancestry. This preserves the **current
snapshot**; it does not reconstruct material pruned before this feature.

### Compatibility and ordinary writes

New clients read V1 and V2. First migration changes the exact ledger schema to
`steward-ledger-archive-v1`; even a sub-1-MiB migrated ledger is rejected by old
V1 readers before their compactor or writer runs. Rollback retains V2 forever.
Upgrade all hosts before migration; restoring an old client is not rollback.

V2 requires retained memory metadata and valid explicit hot projections.
Ordinary CAS writes cannot drop archive metadata, delete/change archived runs,
remove pointers without verified restoration, downgrade the schema, reset
counters or replace index history. An archive transition must append exactly
matching verified index events and reproduce the prior run. Unrelated hot
writes do not hydrate unchanged archives, preserving lease/replay availability.
Local-file clients cannot migrate or modify shared archive history.

## Interruption, rollback and repair

- **Before CAS:** source hot bytes stay canonical. Uploaded objects may remain
  harmless durable orphans. Retry explicitly selected IDs from any clone.
- **After CAS, lost success response or Git timeout:** do not assume failure or
  re-execute actions. Re-read canonical hot state. Repeating the selected
  migration verifies the existing pointer and does not append duplicate events.
  A reported transport failure may have published an object/commit.
- **Concurrent writer or lease acquisition:** normal non-forced fast-forward CAS
  serializes the transfer. Retry eligibility on the new document; preserve all
  intervening operations/work/leases. No integration branch rebase/reset occurs.
- **Rollback:** hydrate/verify the run, append a rollback event, then forward-CAS
  just that run into the newest hot ledger. Keep intervening work, V2 metadata,
  immutable archive objects and the entire index chain. A conflict retries.
  Repeated rollback is a no-op. If restored bytes exceed the configured bound,
  refuse without changing hot state; obtain authorized capacity/headroom first.
- **Missing/corrupt run, snapshot or anchor:** `show`, ordinary phase-dependent
  views/resume/replayed record results and rollback refuse. Missing coverage is
  never replaced with empty/healthy observations. A bad index refuses history,
  migration or history-extending rollback; a valid run can still be shown
  independently of index availability.
- **Missing object repair:** stop live writes and retain all descriptors/refs.
  From a separately verified surviving clone/backup, recover the exact payload
  bytes. Verify kind, size, SHA-256, schema and source identity. The library's
  `GitArchive.publish(kind, exact_bytes, parent=verified_source_commit)` can
  republish an **absent** immutable object; snapshot/anchor provenance parents
  must be preserved. Fresh-clone `show`, `--snapshot` and history verification
  must then pass before resumption. This is an operator repair procedure, not
  an automatic CLI repair or authority to upload unrelated files.
- **Corrupt/colliding existing ref:** refuse; never overwrite it, force-push,
  delete it or silently bypass it using local files. Preserve the damaged ref,
  source ledger ancestry, raw bytes and verified backup for founder-authorized
  repair engineering. Forward rollback also refuses until its archive can be
  independently verified. No destructive repair is authorized here.

## Finite capacity, telemetry and growth stops

The initial hot bound is **8 MiB**, uniformly enforced on load and write.
`GAIA_STEWARD_LEDGER_MAX_BYTES` accepts 1024..67108864 bytes; invalid configuration
refuses even an absent ledger. Lowering the bound never prunes existing bytes.
Logs warn at 70% and 90%. `archive` preview reports exact hot bytes/headroom,
thresholds, largest runs/sections, sampled parent growth, a suggested reserve,
and `operatorStopNewRuns`. The reserve is one largest compact run or positive
sampled increment (at least 256 KiB), plus 256 KiB; it is not a next-run guarantee.

New runs refuse at **90%** before adoption/lease mutation. Operators can stop
new growth earlier, without disabling existing reads/resume/record/rollback:

```sh
export GAIA_STEWARD_FULL_STOP_NEW_RUNS=1
# Or set a chosen reserve in bytes, no greater than the hot bound:
export GAIA_STEWARD_FULL_MIN_HEADROOM_BYTES=1048576
```

These controls apply at new-run creation and are rechecked on CAS retry; they
are not a global write ban and cannot guarantee that an existing run fits.
The hard byte bound remains authoritative on every write. Archive/rollback
operations are never automatically scheduled; reserve alerts require operator
judgment. Index head metadata is constant-shape, with logarithmically growing
counters. Per-run replay metadata and work history still grow indefinitely.
There is **no promise of infinite hot capacity**, no automatic pruning and no
unapproved deletion policy. Stop growth when safe transfer cannot free enough.

Recorded baseline supplied for #2283 (not a new live measurement): 1,005,272 hot
bytes, 13 terminal runs, roughly 757 KB in runs. Last 30 committed generations
increased 79,056 bytes across 0.5511 hours; max increase 39,775 bytes, median
zero. This is descriptive, not a reliable forecast. The implementation samples
only the immediate Git parent with a positive timestamp interval; it does not
walk unbounded history or turn old bursts into a capacity promise.

# Routine 19 core — two boundary repairs

## Status / exact source

**Bounded repair checkpoint completed; ready for fresh independent exact-SHA re-review, NOT self-accepted.** No adapter/gate/CLI/fullrun wiring or operational activation is included.

- Final tested commit: **`6b914723004852a5f515f78ed6d536cccbe3a9bc`**.
- Final tree: **`7357c944e62327a6466aae7374078b331d2f859d`**.
- Starting rejected source: `78842d0bac074d478bcf4fe99572d1cbbf03d26e`.
- Accepted preservation base: `2d9599c11ea91f303b5067c39fb8ea272f119072`.
- Worktree: `$HOME/.gaia-worktrees/steward-r19-shared-write-2283`; branch `dev/steward-r19-shared-write-2283`, clean at final test and subsequent checks.
- One local, UNPUSHED repair commit, using per-command Git author/committer identity `Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com>` and `commit.gpgsign=false`. No global configuration mutation.
- Verified starting source, accepted preservation base, main `31b407db65c4e138896780a7319e4a4ce76884eb`, and `8ad344a49926821d2c1b6d4e021b8de6f653649c` are ancestors (exit 0 for each). Parked archive `ceb38582008a07002239ec65aa77aa22725e80ab` ancestry check exited 1.
- Parent performed the prior new-feature-only main rebase/preservation merge. This worker did not rebase/push or alter that ancestry.

Read the exact absolute `core-independent-review.md` in full before repair. Its CORE REJECT remains historical evidence. `core-implementation-proof.md` and all its old results remain unchanged; this report does not relabel them as acceptance of the repaired source.

## Changed files / preservation

Only three paths changed from rejected starting source:

1. `src/gaia_cli/steward/prmaintenance/coordination.py` — exact persisted-size measurement, explicit future generation-width headroom, source-text-specific 64 KiB bound.
2. `tests/steward/prmaintenance/coordination_helpers.py` — optional test namespace argument for administrative fixture genesis; existing default behavior unchanged.
3. `tests/steward/prmaintenance/test_coordination_boundaries.py` — 11 new focused cases, valid real-store administrative prefix helpers, exact complete-source fixture provider and maximal public-path calculations.

`git diff --check 78842d0bac074d478bcf4fe99572d1cbbf03d26e..HEAD` passed. Net diff from preservation base consists only of the original four coordinator/test files plus this new test file. All files outside those paths, including all accepted campaign/prose, 8 MiB general ledger/no-op compaction, founder/security/watcher/pause/authority holds, remain byte-identical to the accepted base. Existing `test_coordination.py` and `test_coordination_processes.py` were not changed by these repairs. No ledger implementation/default, production policy, namespace/protocol, dependency or compactor change.

## Repair 1 — exact bytes persisted by CAS

The guard now measures **`len(ledger.serialize(ledger.nextGeneration(candidate)))`**, just as the real GitRef store does. It uses a temporary copy; the original pre-increment `candidate` is still passed unchanged to CAS. This is unconditional for every transition, not a completion-only workaround.

For admission, the guard additionally reserves:

- 16,384 bytes for remaining bounded outcome/events; and
- `max(0, digits(MAX_HISTORY) - digits(persisted generation))` bytes for all later generation-digit expansion. `MAX_HISTORY` remains 1,537, so admission at generation 6 reserves three additional decimal-width bytes.

No coordinator bound was raised: **MAX_BYTES remains 524,288**. Exact-fit terminal documents are allowed, not rejected by an off-by-one workaround. Refused transitions do not call CAS.

### Fresh before/after reproduction and actual numbers

The original 4,096-byte proof rejection was first reproduced on unchanged old production source. To produce the shorter 9 -> 10 generation fixture, only the source-text bound was then widened while the old byte guard was deliberately left unchanged. Thus the fresh byte red logs are explicitly **old guard + source-bound-only edit**, not claimed as an unmodified old-SHA reproduction of the reviewer's slower 97-event fixture. That old-SHA reproduction remains in the independent review.

The shorter boundary fixture uses two retained canceled-unsent records and seven genuine, single-event administrative fixture commits (generation 8), with full strict replay/field validation. Public `invoke` then claims at generation 9 and completes at generation 10. All prior documents are within 524,288 bytes and normal warm/cold coordinator reads validate them unchanged. Near-capacity administrative provisioning is explicit fixture authority; it is not falsely presented as normal production reservation admission. No predicate, store validator, byte constant or runtime guard is mocked/bypassed.

| Probe | Old guard, source-bound-only red | Final repaired exact source |
|---|---|---|
| Completion exact fit | Pre-increment 524,287; persisted generation 10 **524,288**, success/readable | Same **524,288**, `newly-committed / completed-effect`; warm and independent cold reads succeed |
| Completion one byte over | Pre-increment **524,288**; persisted generation 10 **524,289**; returned **completed-effect**, one actual fake-adapter invocation | Refused BEFORE completion CAS; no completed result returned. Prior generation 9 tip/document remain **unchanged, readable, 522,994 bytes**; state `possibly-sent`, slot held and attempt charge retained; exactly one invocation/effect |
| Admission exact retained headroom | 507,901-byte persisted reservation allowed | **507,901 allowed**, generation 6; 16,387 bytes remaining = 16,384 event budget + 3 generation-width bytes |
| Admission short by one byte | **507,902 incorrectly allowed** by the old guard | **507,902 refused** before CAS; prior generation 5 tip unchanged/readable at **506,373 bytes**, no active operation, zero invocations/effects |

The overflow completion path honestly raises `Refused` after the adapter effect; it does not return a success-shaped result. The canonical possibly-sent state remains the durable unknown hold, and replay of the existing claim is `already-applied`, with no second invocation. These tests model a fake adapter effect, not a real HTTP mutation or evidence-capture certification.

CAS observation in both completion cases confirms candidates handed to the store retain generations `[8, 9]` for successful claim/completion, or only `[8]` when completion is refused. The store alone increments them; there is no double increment.

## Repair 2 — full exact source bindings

Only the three source-text fields (`policy`, `producerRegistry`, `authority`) now have a **65,536 raw UTF-8 byte limit per field**. `text` remains byte-aware, not character-count-based. Justification/detail limits remain 2,048 bytes; verifier/source/identity limits remain their existing smaller bounds. No provenance truncation, scoped policy fragment, partial registry or digest-only substitution.

Complete current source bytes were read from the joined checkout and configured into an exact-match trusted fake provider:

| Complete source | Raw UTF-8 bytes | Remaining per-source bound |
|---|---:|---:|
| `founder/steward/POLICY.yaml` | **27,049** | 38,487 |
| `founder/steward/pr-producers.json` | **8,077** | 57,459 |
| `founder/steward/decisions/steward-pr-maintenance-authority.json` | **3,478** | 62,058 |
| Total complete source text | **38,604** | — |

Complete compact registry is 6,112 UTF-8 bytes, independently measured for context; tests store the original **8,077-byte complete file**, not the compact substitute. The full policy is stored, not its prMaintenance fragment. No matched raw source values are printed in logs; only sizes and numeric results.

The configured provider is reached at both reservation and invocation (two successful authorization calls). Merge and close each execute reserve -> exact intent -> actual fake invocation -> authenticated fake completion -> independent-clone cold read. Cold proof digest equals the entire original exact proof digest; full strings remain present in the durable event.

Actual serialized representation, including JSON escaping and metadata:

| Case | Compact complete proof JSON | Reserved ledger bytes | Free bytes after reserve | Settled ledger bytes |
|---|---:|---:|---:|---:|
| Current complete sources, merge | **40,680** | **42,083** | **482,205** | **44,771** |
| Current complete sources, close | **40,680** | **42,130** | **482,158** | **44,749** |

Three additional cases verify each source accepts exactly 65,536 UTF-8 bytes using multi-byte characters, refuses 65,537 bytes, and still refuses overlong ordinary verifier/source/detail/justification fields. The 64 KiB choice accommodates the complete current sources with growth room but does not promise that 128 maximal-source records fit: exact byte admission remains the limiting authority and retained full records are never silently pruned.

## Recalculated public-path outcome headroom

Two real-store public-path cases exercise maximum source fields plus JSON escaping, UTF-8 byte accounting, maximum namespace/request lengths, maximum subject/replacement values, 128-byte escaped owner/run/transition IDs, maximal source/detail evidence, 16-digit authoritative clock bounds and three preparation takeovers. A canceled primer shifts the public paths across generation 9 -> 10. No internal fabricated unknown-then-complete transition is used.

Each case stores **196,608 raw source bytes** (three fields at 65,536) whose actual compact source JSON occupies **393,266 bytes**. The reserved document is **415,480 bytes**; both paths retain full exact proof through an independent cold read.

| Public path | Final bytes / generation | Measured growth after reserve | Additional maximal-fence allowance | Remaining generation-width allowance | Conservative total growth | Slack inside 16,384 event budget |
|---|---:|---:|---:|---:|---:|---:|
| Sole authentic close completion after quarantine, recording reopen | **430,255 / 11** | **14,775** | 12 | 2 | **14,789** | **1,595** |
| Lost merge response -> unknown -> quarantine -> matching independent absorbing merge | **431,004 / 12** | **15,524** | 12 | 2 | **15,538** | **846** |

The fence allowance conservatively widens all future token fences to the largest possible fence (512 = 128 records × four ownership fences). The generation allowance widens the final representation to the bounded history maximum (1,537). This is explicit structural size arithmetic, not authorization of invented transitions. Repeated inconclusive recovery adds no event/ref growth. Exactly one invocation and one fake effect occur in each path. The separate admission generation reserve is additionally conservative; no outcome budget or coordinator byte bound was enlarged.

## Verification, failures retained and deadlines

All logs are retained under:
`$HOME/gaia-skill-tree/.gaia/steward/campaigns/2026-11-05/routine19-shared/core-boundary-logs/`

| Log | Actual result | Source/scope |
|---|---|---|
| `source-proof-red-78842d0.log` | exit 1; **2 failed**, 6.38s | New real-complete-source tests against original old production source; both fail the 4,096-byte guard before provider authorization. |
| `byte-guard-red-source-bound-only.log` | exit 1; **2 failed, 2 passed**, 24.12s | Source bound alone widened, old byte guard retained; exact-fit cases pass, overflow/headroom regressions fail. |
| `byte-guard-red-measured-source-bound-only.log` | exit 1; **2 failed**, 8.51s | Instrumented same old guard; explicitly logs false completed-effect at 524,289 persisted bytes and incorrect 507,902-byte admission. |
| `exact-6b9147230-boundaries.log` | exit 0; **11 passed**, 37.93s | All new cases on exact clean final SHA; numeric byte/source/headroom measurements above. Slowest new case 6.94s, not near the 60s deadline. |
| **`exact-6b9147230-selected.log`** | **exit 0; 373 passed, zero failed/skipped, no warning summary; 507.66s** | **Final exact-SHA focused union, run once in this repair checkpoint.** |
| `exact-6b9147230-core-collection.log` | exit 0; **78 collected**, 0.19s | Original 67 coordinator cases (including all 10 real-process cases) plus 11 new boundary cases; collection is not an additional execution claim. |

Final selected command, after asserting exact HEAD and clean status:

```sh
PYTHONPATH=src python -m pytest tests/steward/prmaintenance tests/steward/test_ledger.py -q
```

The original 67 cases include all nine transition kinds under CAS conflict/acknowledgement loss, separate `--no-local` clones/no alternates, spawned-process contention, last-token accounting, killed/resumed post-claim senders, cold recovery, actual fork and grant-copy/thread protection. They ran unchanged in the final 373-test selection. No full repository, archive pipeline or broader full-Steward suite was run.

`pyproject.toml` still specifies **timeout=60, timeout_method="thread"**. No timeout=0, increased deadline, skips, timeout-plugin disabling or weakened assertions. Test tool invocations had no external execution timeout. Existing store deadlines were unchanged. The near-boundary fixtures use seven/four real prefix commits, not 97 slow commits.

## Runtime / authority and remaining gates

Observed exports in the original builder session: `PI_CODING_AGENT=true`, provider **openai-codex**, model **gpt-6.1-sol**, reasoning **xhigh** (requested MAX/xhigh harness binding). Provider-side routing beyond those exports is not independently attested. Python **3.14.6**, pytest **9.1.1**, pytest-timeout **2.4.0**. Effective general-ledger limit **8,388,608 bytes**, coordinator bound **524,288**, source bound **65,536**, outcome budget **16,384**. Graft retrieval used before source inspection; no installation/global config changes. Root/founder instructions remained loaded in this same original builder context. No fallback, duplicate writer or nested agent.

All store calls were against disposable isolated local bare fixture remotes. No real origin store, GitHub/forge, legacy ledger/leases, scan/run/record/migrate, policy edit, registry/trust/rank/evidence intake, workflow compile/activation, package/release/deploy, push or rebase was performed by this repair worker. Archive remains parked/excluded.

**Next action is fresh independent core re-review at the final SHA/tree**, not self-acceptance. The trusted Services boundary remains unchanged: future current-source/immutable-identity authority checks, trustworthy fresh clock/evidence provider, actual non-retrying HTTP capture, final live policy/verification/protection/holds/kill checks, and protected canonical provisioning/draining bypass clients are still required. Gate/CLI/runner/local-default/contract wiring remains a later assigned checkpoint. This repair does not grant merge/closure/activation authority or certify those absent integrations.

Resume from `6b914723004852a5f515f78ed6d536cccbe3a9bc` in the named clean worktree; parent owns publication and any next integration step.

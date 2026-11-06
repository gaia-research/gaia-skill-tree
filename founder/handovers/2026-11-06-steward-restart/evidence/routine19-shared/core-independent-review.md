## Status
issues_found — **CORE REJECT** for exact HEAD `78842d0bac074d478bcf4fe99572d1cbbf03d26e`.

This is a bounded source/core decision, not an end-to-end feature or activation decision. Two reproduced core defects require repair and exact-SHA re-review.

## Findings

- `src/gaia_cli/steward/prmaintenance/coordination.py:572-576` — **warning**: The byte guard measures the pre-increment candidate, but `GitRefLedgerStore.compare_and_swap()` serializes `nextGeneration(candidate)`. A decimal-width increase can therefore commit a document exceeding the coordinator's own permanent byte bound. I reproduced this against an actual disposable bare remote with **MAX_BYTES unchanged at 524,288**: a valid 97-event preparation prefix (46 canceled-unsent records, then reserve/intent/three takeovers) loaded successfully; `invoke()` appended claim at generation 99 and completion at generation 100. The completion candidate measured exactly 524,288 bytes before the store increment; the persisted document measured **524,289**. `invoke()` nevertheless returned `newly-committed / completed-effect`, with exactly one adapter invocation. Both warm and separate-clone readers subsequently rejected the canonical state with `coordination document over byte bound`. All proof fields stayed within their schema limits; padding was confined to retained canceled records, and the active operation used the ordinary trusted fake proof. This is an unexpected permanent coordination outage, not the intended unknown-sender quarantine. **Repair:** evaluate both admission headroom and transition capacity against the exact persisted representation, including `nextGeneration`, before CAS. Add a real-store regression at a generation digit boundary and the unchanged byte limit; ensure a refusal leaves the canonical ref readable and unchanged.

- `src/gaia_cli/steward/prmaintenance/coordination.py:219-220` — **warning**: The 4,096-byte limit on each policy/producer-registry/authority string cannot represent the declared exact current source bindings. Actual joined-source sizes are POLICY.yaml **27,049 bytes**, pr-producers.json **8,077 bytes**, and ratified authority **3,478 bytes**. Compact JSON still leaves the complete producer registry at **6,112 bytes**. A fresh fixture using a trusted service configured to authenticate those exact current source texts was rejected by `validateProof()` before `Services.authorize()` was reached. A second probe using only the relevant 344-byte `prMaintenance` policy section and the compact complete registry was also rejected. Both left zero records and zero invocations. Thus this is not merely a worst-case 128-record capacity concern: the schema cannot admit even one record carrying the actual complete registry required by its declared contract. **Repair:** choose bounds that accommodate a representative real current proof, then recalculate byte capacity/headroom and test successful real-text admission, invocation, and settlement. Do not repair this by silently dropping provenance, truncating source text, or replacing the specified full binding with an unchecked digest. If a deliberately scoped producer-proof representation is intended instead, specify and authenticate that representation explicitly.

## Verification Limits

### Exact source, independence, and runtime

- Reviewed HEAD: `78842d0bac074d478bcf4fe99572d1cbbf03d26e`; tree: `ee8c8c55e17656f41268011cffdd5cefccfcae9a`.
- Accepted preservation base: `2d9599c11ea91f303b5067c39fb8ea272f119072`. Verified its ancestry, plus main `31b407db65c4e138896780a7319e4a4ce76884eb` and `8ad344a49926821d2c1b6d4e021b8de6f653649c`.
- Net diff from preservation base is exactly the four assigned new files: coordination.py, coordination_helpers.py, test_coordination.py, and test_coordination_processes.py. All four are byte-identical to original tested core `57126b47d9673e2354fcd4bb023b5ebd6e8c666b`. `git diff --check` passed. Accepted preservation units were carried through unchanged, not independently re-audited.
- Created a separate `git clone --no-local --single-branch` at `/data/data/com.termux/files/usr/tmp/core-independent-uhOXXy/repo`, from the supplied local review-source Git repository. Origin fetch URL records that local provenance; push URL is `disabled://review-no-push`. Git/common and object directories are distinct, with no alternates. Source and review tracked/untracked status remained clean.
- The supplied source and resulting clone are shallow. The parked archive object is unavailable (direct ancestry query exited 128); its SHA is not in the available reachable history. This is **not** an independent proof of archive exclusion beyond the shallow boundary. The exact four-file net diff and unchanged preservation blobs were verified.
- Observed harness exports: provider `openai-codex`, model `gpt-6.1-sol`, reasoning `high`. Provider-side routing was not independently attested. Python **3.14.6**, pytest **9.1.1**, pytest-timeout **2.4.0**. Effective unchanged general-ledger limit: **8 MiB**.
- Read root/founder CLAUDE instructions, graft skill, the absolute implementation proof, joined-source manifest, and advisor amendments. Graft retrieval was attempted first but reported no graph; no graph build/install was performed. Source inspection then used direct reads. No nested agents or fallback models.

### Actual checks performed in this pass

1. Read all four changed files and relevant existing GitRef storage/serialization context. Examined canonical replay/prefix validation, slot/ownership transitions, invocation grants, evidence boundaries, quota/time accounting, and schema/resource limits.
2. Fresh selected test execution on the exact clone: **23 passed in 80.25 seconds**, no failures/skips or warning summary. Command:

   ```sh
   PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -p no:cacheprovider \
     tests/steward/prmaintenance/test_coordination.py::test_cached_history_cannot_hide_valid_looking_rewritten_prior_events \
     tests/steward/prmaintenance/test_coordination.py::test_every_transition_ack_loss_and_cas_retry \
     tests/steward/prmaintenance/test_coordination.py::test_process_local_grant_cannot_copy_serialize_reuse_or_cross_thread \
     tests/steward/prmaintenance/test_coordination_processes.py::test_paused_claim_restart_and_cold_recovery_never_grant_again \
     tests/steward/prmaintenance/test_coordination_processes.py::test_actual_fork_cannot_consume_or_invoke_inherited_grant -q
   ```

   The 23 include both fault modes for all nine transition kinds, the prior warm-cache prefix regression, paused sender termination/resumption, and actual fork protection. Existing 60-second/thread test deadlines remained in force; no timeout disabling, skips, or source/test changes.
3. Independently designed fixture-only CAS probe: during an attempted merge reservation, a second clone really committed a close reservation lowering the merge cap to zero, then canceled it. The original attempt received a conflict, reloaded the changed history, discarded its stale admission computation, and refused on the durable ceiling. Only the canceled competing record remained; zero adapter invocations. **Passed.**
4. Independently designed claim ambiguity probe: the real claim push succeeded, its acknowledgement was lost, and the immediate canonical reload also failed. Result was `unresolved`. A separate clone with the copied token received `already-applied` for the original claim ID and refusal for a fresh claim ID; the slot remained held and both services recorded zero invocations. **Passed.**
5. Two real-source proof probes and the unchanged-limit, real-store generation/byte-boundary probe reproduced the findings above. All coordinator/store calls used disposable fixture bare repositories, never the review clone's provenance origin.
6. Exploratory pure-replay escaped-text headroom calculations were also performed. One deliberately broader internal state-machine sequence exceeded 16 KiB, but used a non-public unknown-then-complete trace and arbitrary internal detail/IDs; it is **not** presented as an additional public-API defect. The corresponding modeled public success path with quarantine measured 14,759 bytes of remaining growth. This is not exhaustive headroom certification.

### Assumptions and unverified boundaries

The core's trusted Services contract and trusted cooperating-writer model are intentional boundaries: genuine current-source authorization and immutable forge identity, a trustworthy fresh bounded clock, a sole non-retrying adapter with final live checks, authenticated completion/independent observation, externally pinned genesis/minimum history, and append-only/no-delete/no-reset server protection. Client CAS does not supply those deployment guarantees. No additional core defect was established in the inspected replay/grant/evidence/accounting paths under those assumptions.

The complete joined 348-test selection was **not** duplicated; the parent's run and builder counts are not claimed as this review's results. No production provider, HTTP behavior, kill wiring, gate/CLI/runner integration, namespace provisioning, full repository/archive pipeline, production origin/legacy-ledger access, issuer probing, GitHub write, push/merge/rebase, release, deployment, or activation was performed or certified. Fixture Git pushes were local only. No source repairs were made. The two findings are sufficient for CORE REJECT independently of later integration/rollout gates.

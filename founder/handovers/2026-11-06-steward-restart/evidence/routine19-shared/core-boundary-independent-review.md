## Status
clean — **CORE ACCEPT** for the whole bounded coordinator core at **`6b914723004852a5f515f78ed6d536cccbe3a9bc`**, tree **`7357c944e62327a6466aae7374078b331d2f859d`**.

This closes the two findings in the original independent CORE REJECT. It is **not** end-to-end feature acceptance, production-provider verification, provisioning/activation approval, or permission to perform a real merge/closure. The original report remains untouched.

## Findings

**No actionable findings remain in this bounded review.**

- **Persisted-byte finding closed:** `src/gaia_cli/steward/prmaintenance/coordination.py:577-583` measures `ledger.serialize(ledger.nextGeneration(candidate))`. Inspection of `ledger.nextGeneration()` confirms it validates/deep-copies rather than mutating the candidate. CAS still receives the original candidate and alone advances its generation. Reservation additionally retains decimal-width growth through MAX_HISTORY=1,537. MAX_BYTES=524,288 and OUTCOME_HEADROOM=16,384 remain unchanged. Exact-fit commits validate in warm/cold readers; overflow is refused before CAS, including after an actual invocation, without falsely reporting completion or granting replay.
- **Real-proof finding closed:** `src/gaia_cli/steward/prmaintenance/coordination.py:40,223` permits 65,536 raw UTF-8 bytes only for the three complete source-text fields. The actual whole policy (27,049), registry (8,077), and ratified authority (3,478) now survive admission, exact intent, invocation, settlement, and independent-clone reads. Other identity/verifier/source/detail/justification limits are unchanged. No fragments, truncation, compact-registry substitution, or unchecked digest workaround was introduced.

## Verification Limits

### Exact delta and carried core review

- Parent/rejected source: `78842d0bac074d478bcf4fe99572d1cbbf03d26e`; accepted preservation base: `2d9599c11ea91f303b5067c39fb8ea272f119072`. Both were verified ancestors.
- Inspected the actual repair diff: 16 production diff lines in coordination.py, the optional administrative-fixture namespace parameter, and all 349 lines of the new 11-case boundary test file. The only three changed paths from rejected source are those assigned paths. Net scope from preservation base is the original four new coordinator/test files plus test_coordination_boundaries.py. `git diff --check` passed. No accepted preservation unit, ledger implementation, policy, wiring, dependency, or test deadline changed.
- Compared old/new ASTs for 21 relevant definitions: Services, grant and identity/time/limit types, subject/request/evidence validation, pure replay, usage/capacity, canonical loading, grant consumption, invocation, recovery, and result construction are unchanged. Inspected the changed `_transition` region and surrounding retry/acknowledgement branches directly; only exact-size/admission arithmetic changed there. Existing unit/process test files are byte-identical to the rejected source.
- Accordingly carry the previous complete core inspection and **historical** 23-test result plus its fresh competing-lowered-cap and claim-acknowledgement/reload-loss probes for unchanged protocol behavior. These cover strict genesis/history/current canonical binding, immutable event prefixes, slot/ownership/fences, no grant from persisted claims, process/thread/fork/reentry boundaries, exact request/evidence bindings, conservative accounting/clock behavior, and bounded recovery. They are **not counted as fresh executions on this SHA**. The prior two defects were the reasons for rejection; this pass closes them and finds no additional concrete core defect.

### Fresh tests on exact repaired HEAD

Executed without source changes:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -p no:cacheprovider \
  tests/steward/prmaintenance/test_coordination_boundaries.py -q -s
```

**11 passed in 43.02 seconds**, no failures/skips or warning summary. Existing **60-second/thread** deadlines remained enabled and unchanged; disabling pytest's cache provider did not disable its timeout plugin.

Observed results, independently executed rather than borrowed from the builder:

- Complete current source proof: merge reserved **42,083**, settled **44,771** bytes; close reserved **42,130**, settled **44,749** bytes. Full proof digests survive cold reads; each action has two authorization calls and one invocation/effect.
- Each source field accepts exactly **65,536 UTF-8 bytes**, rejects 65,537; ordinary smaller proof-field bounds still refuse oversized input.
- Completion generation **9→10**: exact **524,288** bytes commits and remains readable. A **524,289**-byte prospective completion is refused before completion CAS; prior generation-9 tip remains unchanged/readable at **522,994** bytes, with one invocation/effect, possibly-sent hold, retained charge, and no replay. CAS candidates retain pre-increment generations; no double increment.
- Admission at generation 6: **507,901** persisted bytes allowed, leaving 16,384 outcome bytes plus three future generation bytes; **507,902** refused before CAS, preserving the readable prior tip at **506,373** bytes.
- Maximal-source public paths, including escaping, three takeovers, generation expansion and cold proof retention: bounded remaining growth **14,789** bytes for quarantined authentic close completion and **15,538** for lost merge response/unknown/quarantine/independent terminal observation. Corresponding 16 KiB slack: **1,595** and **846** bytes. These paths each invoke/effect once; repeated inconclusive recovery is a no-op.

The short near-capacity boundary prefixes are explicit administrative fixtures, not evidence that ordinary admission would admit such nearly full histories. No fresh old-source red run was performed here. The builder's short red fixture used the old guard plus a source-bound-only edit; the original independent 97-event reproduction remains the unmodified old-SHA evidence.

### Fresh independently designed probes

All executable probes used disposable local bare remotes and normal core bounds; no store touched the review clone's provenance origin.

1. **Real CAS conflict invalidates an exact-fit completion:** began with a validated administrative prefix whose prospective completion exactly fits 524,288 bytes. Before its actual completion push, a second clone committed quarantine. The original push genuinely conflicted. Retry reloaded the larger canonical document and refused on the recalculated byte limit rather than reusing the failed snapshot's exact-fit result. Both readers validated the unchanged competing tip at **523,403 bytes**, quarantine/slot/charge remained held, original-ID replay returned ALREADY, a fresh claim ID was refused, and invocation/effect counts stayed **1/1**. **Passed.**
2. **Complete real-source proof plus completion acknowledgement loss:** configured a trusted exact-match provider with all three whole current files, committed a real completion, then lost its acknowledgement. Result was ALREADY/completed-effect; a separate clone retained every source string and the full proof digest, released the active slot, and retained one run/hour charge. Copied-token replay added no invocation. Counts stayed **1/1**. **Passed.**
3. **Independent serialization upper-envelope calculation:** built maximum escaped later-event shapes separately from the new test's implementation. Conservatively widened even derived hex transition IDs to 128 fully escaped characters, every token fence to 512, every owner/new owner to maximum escaping, all clock integers/source and request widths, and used longer completion-evidence spellings even in the terminal-observation length calculation. Included generation width through 1,537. Modeled remaining growth: prepared cancellation **9,912**; quarantined authentic completion **15,257**; unknown/quarantine/terminal observation **16,130** bytes — all below 16,384, with **254 bytes** at the largest envelope. These are deliberately oversized serialization shapes, not forged admissible evidence or extra authorized transitions. Larger proof strings occur once in reservation and therefore do not recur in these remaining-event deltas. This supports the headroom argument without claiming exhaustive execution of every input/interleaving.
4. **Illustrative realistic-capacity model:** strict pure replay with complete current sources, ordinary fixture subjects/evidence, distinct stable run IDs, and truthful hourly advancement retained **11** settled records at **487,880 bytes**. The twelfth reservation would require **529,500 bytes plus 16,386 headroom**, so normal admission must refuse. This is a model, not twelve actual store admissions. The 128-record bound is an upper bound, not a promise that 128 full real proofs fit. This finite core is not unlimited or long-lived service capacity; no pruning/compactor is certified or requested.

### Runtime, read-only discipline, and assumptions

Observed exports: provider **openai-codex**, model **gpt-6.1-sol**, reasoning **high**; provider-side routing is not independently attested. Python **3.14.6**, pytest **9.1.1**, pytest-timeout **2.4.0**. General-ledger limit remains **8,388,608** bytes.

Used the parent-updated independent review clone at `$HOME/.gaia-worktrees/steward-r19-core-review-2283`, with its own Git/common/object directories, no alternates, local-source provenance origin and unchanged disabled push URL `disabled://no-origin-writes`. No source/config edits or provenance-origin store operations were made. Worktree status remained clean. Graft was attempted first but reported no graph; no graph build/install was performed. Read the latest absolute repair proof and original independent report in full. No fallback or nested agents.

The clone remains shallow, so the earlier limitation on independent archive ancestry beyond its boundary remains. Exact unchanged preservation scope is verified; the six accepted units were not re-audited. The builder's 373-test result was not duplicated or relabeled as this review's result; the full repository/archive/Steward pipeline was not run.

**CORE ACCEPT assumes the documented trusted boundaries:** cooperating writers; designated current proof/policy/authority and immutable forge identity; a fresh trustworthy bounded clock; a sole non-retrying adapter with authentic completion and independent observation; pinned genesis/minimum history; append-only/no-reset/no-delete canonical server protection. Unknown senders can pin the slot/charge indefinitely. Cold clients cannot detect every rollback permitted by their externally supplied history pin. Local kills do not cancel an already claimed remote sender. Closure remains one coordinated unconditional PATCH after live checks, not an invented atomic-head guarantee or exactly-once GitHub delivery.

Production Services/clock/HTTP capture, final live protection/hold/verification/kill checks, gate/CLI/runner/default/contract wiring, retirement of bypassing writers, namespace provisioning/protection, and rollout remain mandatory later gates and are not implemented or accepted here. No production GitHub/legacy-ledger/scan/run/record/lease/issuer operation, source push/merge/rebase, registry/trust/rank/intake mutation, compilation, activation, package/release/deploy, or global configuration change occurred. The only persistent authored output of this pass is this report; the prior rejection and all source/evidence history are preserved.

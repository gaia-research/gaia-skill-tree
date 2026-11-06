# Independent whole-feature review — REJECT

## Verdict and identity

**REJECT the whole frozen candidate** `17ad597ad3478b7caae182b1581a965a8fcfa252`, tree `fa46a693d3ad3a26f19474851197e97c56f77769`, because of the independently reproduced runner defect below. This is a source rejection, not a deployment or activation decision. This pass stopped after a demonstrated defect meriting rejection; it did not complete all remaining whole-feature coverage and is not a certification of the other boundaries.

Observed harness exports: `PI_PROVIDER=openai`, `PI_MODEL=gpt-6.1-terra`, `PI_REASONING_LEVEL=high`. These are harness runtime evidence, not independent provider-side attestation. The original `wiring-whole-independent-review.md` remains unchanged as the historical partial report. No nested agents, fallback route, source edits, live-origin ledger operations, GitHub mutation, installation or activation occurred.

## Finding

- `src/gaia_cli/steward/fullrun.py:1933-1935` — **warning: an unbound failure report can mark an attached unknown sender done locally.** After a shared `unknown` report attaches `operationId` to a pending action, a subsequent `failed`, `refused`, or `aborted` report that omits `operationId` bypasses the shared lookup: the condition only checks the *new outcome's* ID, not the ID already in `action["params"]`. `operation` therefore remains `None`; the callback at lines 1968–1973 does not set `keepPending`, and `_applyRecord` at lines 984–991 marks both action and step `done`. A later genuine different outcome cannot replace that done action (lines 977–982). This violates the explicit requirement that an attached unknown operation remain pending despite failure-shaped local reports. It hides outstanding work and can allow the ordinary runner to advance despite an unresolved sender. **The reproduced shared slot and charge remain held; this probe does not show a duplicate request, shared refund, or forged completion.**

  **Repair:** when the existing action has an attached operation ID, require subsequent reports to bind that exact ID or derive it from the action, re-inspect the canonical shared operation, and preserve pending while its state is `possibly-sent`, `unknown`, or `quarantined`. Reject conflicting IDs. Ensure the check is robust against the action changing between the initial read and `_applyRecord`'s mutation, and add regressions for omitted and mismatched IDs, all three failure-shaped reports, and transitions to genuinely terminal shared state. Do not resolve this by refunding or settling an unknown sender.

## Fresh independent probe

The reviewer-authored fixture-only probe is `.gaia/whole-review-probes/test_unknown_report.py` in the isolated review checkout; a copy is at `whole-review-probe-unknown.py` in this campaign directory. It uses the existing real `FullRunner.record` producer/consumer seam, a disposable local bare coordination store, and fake services configured for a lost response. It first records `unknown` with an operation ID, then records a **bound** `failed` control with that ID and checks the action stays pending. It then submits the same failure with only the operation ID removed.

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" python -m pytest -q -s -p no:cacheprovider .gaia/whole-review-probes/test_unknown_report.py
RESULT local_status= done shared_state= unknown slot_held= True invocations= 1 effects= 1
1 passed in 19.23s
```

The passing assertion above deliberately asserts the **observed defect**. An independent expected-invariant variant `.gaia/whole-review-probes/test_unknown_required.py` differs in asserting `pending` instead of `done`:

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" python -m pytest -q -s -p no:cacheprovider .gaia/whole-review-probes/test_unknown_required.py
RESULT local_status= done shared_state= unknown slot_held= True invocations= 1 effects= 1
FAILED ... AssertionError: assert 'done' == 'pending'
1 failed in 6.03s
```

The control and negative case both use the same pending action and shared unknown record. Counts are actual fake-service invocations and effects, not deduplicated server effects. This is not an old-source red/new-source green comparison and no repair or green result is claimed. An initial attempt to run the probe from the absolute campaign directory failed collection because pytest imported the provenance checkout's `gaia_cli` rather than the frozen clone; it ran no test. The corrected run above uses the isolated clone's ignored probe directory and explicit `PYTHONPATH`. No timeout settings or test guards were weakened.

## Coverage and evidence limits

| Boundary | Actual work in the two partial passes | Unfinished / not accepted |
|---|---|---|
| Identity, clone and diff | Exact SHA/tree and clean tracked status confirmed again; shallow checkout, no alternates and disabled push verified in the prior report. Main-to-candidate 32 paths / 4,337 additions / 586 deletions enumerated; `git diff --check` passed. | Full semantic diff and all 32 paths not reviewed. Shallow history limits ancestry claims. |
| Core changes and callers | Read full `coordination.py`, full core-to-candidate diff (58 additions/8 deletions), and full new `executor.py`; inspected adjacent gate/policy/collection and runner seams. Read prior independent core acceptance and original core rejection. | All changed core callers, races, full authority/current-source and transport semantics are not fully independently verified; prior bounded core acceptance does not accept the changed lines. |
| Runner | Read `_recordPrWrite`/`record`/`_applyRecord`, relevant main diff and full changed runner test file; designed and executed the fresh negative/control probe above. | Remaining runner cases and all other producer/consumer integrations are not completely covered. |
| Existing fixture tests | Prior exact-SHA review ran 6 local-state and 5 executor fixture cases successfully, as documented in the unchanged partial report. They are carried as those prior executions, not new tests this pass. | They do not establish whole-feature correctness. |
| Clock, quota, genesis, one-shot, resource bounds, HTTP | Core and executor were read; the prior report records five selected existing executor cases. | Full independent fault-injection and boundary probes, clock/source/protection review, all CAS acknowledgment/fork/restart cases, capacity calculations and real transport coverage remain incomplete. No live clock or protection was inspected. |
| CLI, driver, local/legacy, policy, documentation and safeguards | Inspected relevant production diffs and gate/policy/collection source; previous local-state fixture tests covered explicit legacy refusal and separate local checkouts. Generic ledger blob equality and limited preservation checks are in the partial report. | Full semantic review of all CLI paths, old 900-second/raw-auth routes, changed tests against original assertions/deadlines, all mirrors/contracts/catalog/HTML and preserved C1–C4/issue-hygiene/registry/version safeguards remains incomplete. |
| Builder evidence | Read builder report and core reports; builder claims are distinguished from independent results. | Final JUnit, all original failure logs, packaging artifacts and all supporting plan material were not completely audited; the claimed 1,165-test union and capacity model are not independently certified here. |

`git status --porcelain` was empty after probes; authored checkout probe files are ignored. The first report's 11 existing fixture tests were not rerun. No full repository/archive pipeline was run. This reject is supported by the concrete reproduction above, not by presumed failures in unreviewed surfaces.

## Separate delivery and operational holds

Even after source repair and a fresh whole-feature review, independently provisioned namespace/ref/genesis and server protections, trusted clock, explicit activation, and retirement/draining of bypassing old writers remain owner gates. The changed ordinary local default and legacy Git refusal also require an explicit historical shared-campaign transition; nothing here migrates or settles it. Genuinely changed visible CLI output requires its own before/after founder gate; the unrelated approved M1 ledger warning does not grant it. These holds are distinct from the reproduced source defect and are not assertions of missing software stubs. No exactly-once delivery, atomic close, guaranteed liveness, or real external-protection/time attestation is claimed.

---
name: gaia-steward-triage
description: >-
  Sort open Gaia Steward debt into Class A (deterministic repair), Class B
  (bounded dispatch) and Class C (founder decision) with priorities, optionally
  narrowed to one routine or one debt id, without acting on any of it. Use for
  "/gaia-steward-full --triage", "--routine N", "--debt ID", "what should
  Steward do next", or "triage the maintenance debt".
version: 1.0.0
---

# gaia-steward-triage

## Responsibility

Classify observed debt by authority and priority from `founder/steward/POLICY.yaml`
and report the next eligible step per class. Triage decides nothing the policy
has not already decided.

## Input

```bash
gaia steward full run --triage --json
gaia steward full run --triage --routine 9 --json
gaia steward full run --triage --debt "debt:unused_import:..." --json
```

`--routine` takes 1-18 (the numbered routines in `founder/ROUTINES.md`);
`--debt` takes one exact debt id from the receipt.

Routine 18 (GitHub issue hygiene) routes its three debt kinds by authority: `issue_closure_ready`
(A) is forge-bound to `gaia-steward-issue-hygiene` and is report-only while
`issueHygiene.writesEnabled` is false; `issue_suite_review` (B) is the `issue-suite-review`
dispatch for `gaia-steward-lane`; `issue_founder_decision` (C) goes to `gaia-steward-desk`.

## Output

A run record whose triage phase lists, per class: open debt ids, priority, the
dispatch rule or repair executor that binds each kind (or `unrouted`), and the
reason anything is ineligible (cooldown, attempts exhausted, lane full).

## Authority ceiling

Read-only, like observe. Triage never reclassifies a kind; authority comes only
from `POLICY.yaml`, and changing it is a founder decision.

## Stop conditions

- Unknown coverage from the observe phase: triage still lists debt but marks
  Class A ineligible.
- An unrouted Class B kind: report it as needing a route; do not invent one.

## Idempotency

Pure function of the ledger and the observation: the same inputs produce the
same ordering.

## Failure states

`refused` (exit 2) for an out-of-range routine or an unknown debt id;
`blocked` (exit 3) when coverage is unknown.

## Validation

```bash
python -m pytest tests/steward/test_routing.py tests/steward/test_fullrun.py -q
```

## Tests

`tests/steward/test_fullrun.py`, `tests/steward/test_routing.py`,
`tests/steward/test_steward_skills.py`.

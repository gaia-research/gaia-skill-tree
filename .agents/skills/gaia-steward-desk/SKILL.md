---
name: gaia-steward-desk
description: >-
  Render the Gaia Steward founder desk: the Class C decisions that need the
  founder, each with decision, why it matters, evidence, recommendation,
  alternative, what it unblocks and a link, plus operational failures shown
  separately. Use for "/gaia-steward-full --status", "what needs my decision",
  "founder desk", or at the end of every full Steward run.
version: 1.0.0
---

# gaia-steward-desk

## Responsibility

Present what only the founder can decide, and nothing that the machine can
handle. A clean run renders one line: `Gaia Steward: nothing needs you.`

## Input

```bash
gaia steward full status --json
```

Decision records live in `founder/steward/decisions/*.json`
(`steward-decision-v1`); Class C debt comes from the ledger's latest run.

Routine 18 contributes Class C through `issue_founder_decision`: one question per
affected family of issues (for example, whether a family of upstream candidates is
accepted, rejected or deferred), listed once with its `Q-` id and the affected issue
numbers. A question is never answered by the desk. Only the founder's ruling, recorded
as a decision record, releases the work it blocks.

## Output

Under `NEEDS YOUR DECISION`, each item shows Decision / Why it matters /
Evidence / Recommended / Alternative / Unblocks / Link. Operational failures
(unknown coverage, not-evaluated sensors, a local-only ledger, a stale schedule)
are listed separately. Credential findings show only path, line and a short
fingerprint.

## Authority ceiling

Present only. The desk never records a decision, never infers approval from the
founder being available, and `--afk` only queues decisions while Class A/B work
continues.

## Stop conditions

- A malformed decision record: list it as an operational failure; do not drop it.
- No Class C items and no operational failures: print the quiet line and stop.

## Idempotency

The same ledger and decision records render byte-identical output.

## Failure states

Unreadable records become `invalid_decision_record` operations; the desk does
not raise.

## Validation

```bash
python -m pytest tests/steward/test_desk.py -q
```

## Tests

`tests/steward/test_desk.py`, `tests/steward/test_fullrun_scenarios.py`,
`tests/steward/test_steward_skills.py`.

---
name: gaia-steward-retro
description: >-
  Produce the Gaia Steward coverage retrospective: the 17-routine table of
  registered detectors, what each actually observed in the latest receipt, the
  remaining gaps, and the no-op versus closure record. Use for
  "/gaia-steward-full --retro", "steward coverage report", "which routines are
  covered", or "how is steward doing".
version: 1.0.0
---

# gaia-steward-retro

## Responsibility

Report coverage honestly: what is registered, what ran, what was blind, and
what the catalog admits it cannot see.

## Input

```bash
gaia steward full run --retro --json
python scripts/check_steward_coverage.py --receipt .gaia/steward/receipts/<run>.json --json
```

## Output

One row per routine (1-17): detectors, live state per detector
(`actively-observed` or `unknown-unavailable`), static states
(`eligible-auto-remediation`, `human-gated`, `partially-covered`), open debt by
class, and `remainingGaps` from `founder/steward/routine-coverage.json`.

## Authority ceiling

Read-only. The retro never edits the catalog; a catalog change is a reviewed
PR that `scripts/check_steward_coverage.py` must accept.

## Stop conditions

- The checker fails: report its errors as the retro's first line and stop.
- No receipt exists: report every detector as `unknown-unavailable`.

## Idempotency

Pure read of the catalog, the policy and one receipt.

## Failure states

Catalog drift (a registered sensor without a contract, a contract without a
sensor, a kind without a binding) fails the checker with exit 1.

## Validation

```bash
python scripts/check_steward_coverage.py
python -m pytest tests/steward/test_routine_coverage.py -q
```

## Tests

`tests/steward/test_routine_coverage.py`, `tests/steward/test_steward_skills.py`.

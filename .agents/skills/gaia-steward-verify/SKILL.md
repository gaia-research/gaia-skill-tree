---
name: gaia-steward-verify
description: >-
  Independently verify one Gaia Steward Class B build: read only the rendered
  verifier prompt and the sensor evidence, check the diff and proof, and record
  accept, reject or escalate. Use when a full Steward run emits an agent.verify
  action, for "/gaia-steward-full --verify", or "verify the steward dispatch".
  The verifier must be a different agent from the builder.
version: 1.0.0
---

# gaia-steward-verify

## Responsibility

Decide whether one candidate change resolves its finding inside its envelope.
You are the second reader; the machine has already rejected what it can.

## Input

A pending `agent.verify` action. Read `params.verifierPromptPath` and nothing
from the builder beyond the diff and proof it references. If your agent id is
in `params.forbiddenAgentIds`, stop: you built this work.

Run the mechanical pre-check first:

```bash
gaia steward verify DEBT_ID --diff candidate.diff --proof proof.json
```

Exit `1` (reject) and `3` (escalate) are final for this attempt. Exit `0` means
only that the machine did not object.

## Output

```bash
gaia steward full record RUN STEP --input verdict.json
```

```json
{"verdict": "accept", "rationale": "...", "agentId": "...", "model": "sonnet", "effort": "high"}
```

`verdict` is `accept`, `reject` or `escalate`. `model` must be one the action
allows and `effort` must be explicit.

## Authority ceiling

Read and judge only. Do not edit the diff, rerun the build or widen the
envelope. An accept moves the work to `verified`; integration is a separate
`lead.integrate` step.

## Stop conditions

- The diff touches a path outside the envelope: reject.
- The proof does not cover every contract item: reject.
- The change needs a decision only the founder can make: escalate.

## Idempotency

`record` accepts the same verdict twice and refuses a different one for the
same step.

## Failure states

`record` refuses a verifier that built the work, a non-allowed model, a missing
effort or an empty rationale.

## Validation

```bash
python -m pytest tests/steward/test_steward_verification.py tests/steward/test_fullrun.py -q
```

## Tests

`tests/steward/test_steward_verification.py`, `tests/steward/test_fullrun_scenarios.py`,
`tests/steward/test_steward_skills.py`.

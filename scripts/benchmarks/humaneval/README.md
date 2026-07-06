# HumanEval harness — `humaneval@v1.0`

Reference implementation of the Gaia benchmark harness contract. Produces
`benchmark-result` evidence rows for the `humaneval@v1.0` benchmark.

See the top-level [`docs/benchmarks/humaneval-v1/`](../../../docs/benchmarks/humaneval-v1/)
for the benchmark spec, methodology, and provenance requirements.

## Files

| Path                             | Role                                                      |
| -------------------------------- | --------------------------------------------------------- |
| `run.py`                         | Deterministic harness entry point                         |
| `prompts/default.md`             | Versioned prompt template — bump when reshaping           |
| `fixtures/mini.jsonl`            | 6-row deterministic fixture for unit tests ONLY           |
| `../../.github/workflows/benchmark-humaneval-ci.yml` | CI reproduction workflow          |

## Modes

**Stubbed evaluator (default).** `run.py` uses a deterministic pseudo-random
pass/fail per problem, seeded by `(datasetHash, problemId)`. Same inputs ⇒
same score. This lets the pipeline exercise end-to-end without a live model
call. It IS reproducible in CI — this is the mode used for the initial
`ci-reproduced` promotion.

**Model runner (opt-in).** Set `HUMANEVAL_MODEL_RUNNER=<cmd>` in the env.
`run.py` will shell out to the command with the problem prompt on stdin and
expect the completion on stdout. The command must be deterministic for the
CI reproduction gate to pass.

## Invocation

```bash
python scripts/benchmarks/humaneval/run.py \
    --skill-id addy-osmani/code-simplification \
    --dataset scripts/benchmarks/humaneval/fixtures/mini.jsonl \
    --prompt-template scripts/benchmarks/humaneval/prompts/default.md \
    --out .benchmark-result.json
```

Then hand the result off to Gaia:

```bash
gaia push --benchmark humaneval --from-result-file .benchmark-result.json
```

The CI workflow will re-run this harness on the same inputs, compare the
score to the pending row, and promote it to `provenance: ci-reproduced` on
match.

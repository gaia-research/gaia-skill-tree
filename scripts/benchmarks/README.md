# Gaia Benchmark Harnesses

This directory holds the reproducible harness code that produces
`benchmark-result` evidence rows for the Gaia registry. Each subdirectory is
one benchmark, versioned by `benchmarkId` (e.g. `humaneval@v1.0`).

## Provenance contract

Every harness emits a JSON file that carries a **reproducibility fingerprint**:

| Field                 | Meaning                                                             |
| --------------------- | ------------------------------------------------------------------- |
| `score`               | Raw score in the unit declared by `unit`                            |
| `unit`                | Frozen enum: `pct pass@1 pass@10 bleu f1 accuracy elo raw`          |
| `runAt`               | ISO 8601 with timezone                                              |
| `datasetHash`         | SHA-256 of the raw dataset bytes                                    |
| `benchmarkInputHash`  | SHA-256 of `(dataset ‖ prompt template ‖ harness config)` — a       |
|                       | change in any of the three invalidates the fingerprint              |
| `harnessCommit`       | `git rev-parse HEAD` at run time (permalink base)                   |

This is the schema `gaia push --benchmark <name> --from-result-file <path>`
consumes verbatim. Do not add or reshape fields without a coordinated schema
bump in `registry/schema/evidence/benchmark-result.schema.json` and the CLI
preflight in `src/gaia_cli/commands/dev/helpers.py::_preflight_benchmark_row`.

## How the pipeline uses this

```
user runs harness locally
   │
   ▼
.benchmark-result.json                           (this dir's harness output)
   │
   ▼
gaia push --benchmark humaneval                  (writes provenance=pending row)
   │  --from-result-file .benchmark-result.json
   ▼
CI workflow benchmark-<name>-ci.yml re-runs harness
   │  compares to pending row; if within tolerance:
   ▼
gaia dev evidence ... --provenance ci-reproduced (promotes the row)
```

The **user-facing verb is `gaia push --benchmark`**. It writes a `pending`
row. The **CI verb is `gaia dev evidence ... --provenance ci-reproduced`**,
run by the workflow after reproducing the score. Nothing merges to `main`
while a `pending` row is on the skill — `scripts/validate.py --strict`
rejects it.

## Adding a new benchmark

1. Create `scripts/benchmarks/<benchmark>/` with `__init__.py`, a `README.md`,
   a `prompts/` dir, a `fixtures/` dir (for unit tests only), and a `run.py`.
2. `run.py::main(skillId, datasetPath, promptTemplate, outputFile)` must be
   deterministic. Same inputs ⇒ same `datasetHash`, `benchmarkInputHash`, and
   `score`. Non-determinism is a bug — CI reproduction gates on it.
3. Ship a small fixture in `fixtures/` (5–10 rows). This is what the unit
   tests use — do NOT commit the full canonical dataset here (that is
   downloaded at CI time and hashed).
4. Add a corresponding `.github/workflows/benchmark-<benchmark>-ci.yml` that
   downloads the canonical dataset, runs the harness, and promotes the row.
5. Publish the benchmark spec at `docs/benchmarks/<benchmark>-v<version>.md`.

See `humaneval/` as the reference implementation.

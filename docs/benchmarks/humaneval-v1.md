# HumanEval v1.0

**Benchmark ID:** `humaneval@v1.0`
**Unit:** `pass@1`
**Status:** Landing skeleton — full pipeline lands in Sprint D W2b (issue #905).

---

## Benchmark

HumanEval is a Python function-completion benchmark introduced by OpenAI in
["Evaluating Large Language Models Trained on Code" (2021)](https://arxiv.org/abs/2107.03374).
164 hand-written problems, each with a docstring, function signature, and a
suite of test cases. A model is prompted with the signature + docstring and
must emit a body; pass@k is the probability that at least one of k samples
passes the tests.

Gaia records HumanEval as `benchmarkId: humaneval@v1.0`, with `unit: pass@1`
(k = 1, deterministic decoding). Variants (pass@10, sampled, temperature-
adjusted) would use a different `benchmarkId` or `unit`.

---

## Dataset

**URL:** https://github.com/openai/human-eval — `data/HumanEval.jsonl.gz`

**`datasetHash`:** *(pinned to the specific dataset revision at CI-reproduction
time. W2b will populate the canonical hash in the run.py output and in this
document.)*

Any change to the dataset produces a new `datasetHash` and therefore a new
row. Two rows referencing different HumanEval dataset revisions are not
comparable and must not be aggregated.

---

## Harness

**URL:** `scripts/benchmarks/humaneval/run.py` — *lands in Sprint D W2b (#905).*

The harness is required to:

1. Load the dataset from the pinned URL and compute `datasetHash`.
2. Compute `benchmarkInputHash` as SHA-256 of `(dataset + prompt template + harness config)`.
3. Run the model under evaluation with `k = 1`, deterministic decoding.
4. Emit a `results.json` containing at minimum:
   - `score` (0..1 pass@1)
   - `unit: "pass@1"`
   - `runAt` (ISO 8601 with timezone)
   - `datasetHash`
   - `benchmarkInputHash`
   - `harnessUrl` (permalink into the pinned-commit `run.py`)

---

## CI reproduction workflow

**URL:** `.github/workflows/benchmark-humaneval-ci.yml` — *lands in Sprint D W2b (#905).*

Triggered by the `gaia push --benchmark humaneval` flow. On success:

- Writes an evidence row via `gaia dev evidence`:
  - `--type benchmark-result`
  - `--benchmark-id humaneval@v1.0`
  - `--provenance ci-reproduced`
  - `--attestor <workflow-run-url>@<commit-sha>`
  - `--score <pass@1>` `--unit pass@1`
  - `--run-at <iso8601>` `--dataset-hash <sha256>` `--benchmark-input-hash <sha256>`
  - `--harness-url https://github.com/gaia-research/gaia-skill-tree/blob/<sha>/scripts/benchmarks/humaneval/run.py`

- Emits a status check on the PR. `pending` → `ci-reproduced` promotion is
  automatic when the workflow passes; on failure, the row remains `pending`
  and the merge is blocked (via `scripts/validate.py --strict`, which is
  auto-enabled by `GITHUB_BASE_REF=main`).

---

## Verifier attestation (alternative path)

A 4★+ Verifier may co-sign a benchmark run directly, bypassing CI when the
harness is not automatable (e.g. private test set, human graders, hardware
lock-in). The evidence row uses:

- `--provenance verifier-attested`
- `--attestor <verifier-github-username>`

Verifier-attested rows are subject to the same `datasetHash` /
`benchmarkInputHash` requirements and are counted in Trust Magnitude at the
same weight as CI-reproduced.

---

## Trust Magnitude contribution

Per `registry/schema/meta.json` § `evidence.types` (unchanged by W2a):

- Weight: 1.4
- Cap: 100
- Grade ceiling: S
- Magnitude: `percentile` (0..100) — when a `percentile` field is present
- Freshness half-life: ≈ 1 year

For HumanEval specifically, `percentile` is derived from the published
leaderboard placement at the time of the run — see the methodology page for
the leaderboard consumer's interpretation rules (Sprint D W4).

---

## References

- OpenAI, [Evaluating Large Language Models Trained on Code](https://arxiv.org/abs/2107.03374), 2021.
- Schema: [`benchmark-result.schema.json`](https://github.com/gaia-research/gaia-skill-tree/blob/main/registry/schema/evidence/benchmark-result.schema.json)
- Methodology: [Gaia Benchmark Methodology](methodology.md)

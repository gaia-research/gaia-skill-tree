# Gaia Benchmark Methodology

**Status:** Frozen post-merge (Sprint D W2a, issue #904). This document is the
canonical description of how benchmark evidence enters the Gaia registry, how
it is validated, and how it contributes to Trust Magnitude.

Fields, provenance values, and the exclusion rules named here are load-bearing
downstream — the CLI enforces them (`_preflight_benchmark_row`), the schema
enforces them (`registry/schema/evidence/benchmark-result.schema.json`), the
validator enforces them (`scripts/validate.py --strict`), and Trust Magnitude
excludes mirrored/pending rows in `src/gaia_cli/trustMagnitude.py`.

---

## Provenance model

Every `benchmark-result` evidence row carries a `provenance` label from a
frozen enum:

| Value | Meaning | Trust Magnitude |
|---|---|---|
| `verifier-attested` | A 4★+ Verifier co-signed the score. Attestor is the verifier's GitHub username. | Counted |
| `ci-reproduced` | A GitHub Actions workflow ran the harness on a public commit SHA. Attestor is `<workflow-url>@<commit-sha>`. | Counted |
| `mirrored` | Citation-only copy from an external leaderboard. Attestor is the upstream URL. | **Excluded** |
| `pending` | Freshly filed row awaiting promotion to verifier-attested or ci-reproduced. | **Excluded** |

`self-attested` is intentionally absent from the enum and is **forever
rejected** — both by the schema (Draft-07 enum) and by
`scripts/validate.py` (belt-and-braces guard). A freshly filed self-run score
should use `provenance: pending`; a Verifier or CI job then promotes it before
merge.

`pending` rows are informational in lax validator runs but become hard errors
when `--strict` is passed. The validator auto-enables strict mode when
`GITHUB_BASE_REF == main` (PR-into-main) or `GITHUB_REF == refs/heads/main`
(push-to-main) — so pending rows can never survive a merge to `main`.

---

## Reproducibility fingerprint

Two SHA-256 hashes are required on every row:

- **`datasetHash`** — SHA-256 of the raw dataset used for evaluation. A
  dataset revision produces a different hash, and therefore a different row.
- **`benchmarkInputHash`** — SHA-256 of `(dataset + prompt template + harness config)`.
  Two rows may share `datasetHash` but differ in `benchmarkInputHash` if the
  harness config or prompt template changed. This is the "did I evaluate the
  same way?" fingerprint.

Both are 64-character lowercase hex. Uppercase, short, or non-hex values are
rejected at both the CLI and schema layers.

Where do these come from? The benchmark's `run.py` harness is expected to
emit them as part of its results. For W2a this is scaffolding only — the
actual `scripts/benchmarks/humaneval/run.py` implementation lands in W2b (issue
#905).

---

## Trust Magnitude contribution

The `benchmark-result` evidence type has:

- `weight: 1.4`
- `gradeCeiling: S`
- `allowedLayers: [generic, named]`
- `inheritMultiplier: 0.15`
- Magnitude formula: `percentile` (0..100), when a `percentile` field is present.
- Freshness: 50 %/year decay (half-life ≈ 1 year).

Preserved intentionally by W2a — narrowing these fields is a separate sprint
decision. See `registry/schema/meta.json` § `evidence.types`.

Mirrored and pending rows are excluded from the sum entirely via
`computeArtifactScoreOrNone` returning `None` (matching the null-on-derank
contract used for deranked verifier-attestation rows). The row's `grade`
field is stripped at CLI write time so the row is never visually presented
as if it were graded.

---

## Adding a new benchmark

1. **Author the harness.** Deterministic Python, pinned dependencies, emits
   results JSON containing `score`, `unit`, `runAt`, `datasetHash`, and
   `benchmarkInputHash`. Land it under `scripts/benchmarks/<benchmark-id>/run.py`.
2. **Author the CI workflow.** `.github/workflows/benchmark-<id>-ci.yml`
   runs `run.py` on the submitted commit and, on success, writes a
   `benchmark-result` evidence row via `gaia dev evidence` with
   `--provenance ci-reproduced` and `--attestor <workflow-run-url>@<sha>`.
3. **Register the benchmark id.** Add a landing document at
   `docs/benchmarks/<benchmark-id>.md` (see [`humaneval-v1.md`](humaneval-v1.md)
   for the template).
4. **Point the leaderboard consumer at it.** Sprint D W4 (issue #907) will
   consume `docs/api/v1/benchmarks/<benchmark-id>.json`; W2a seeds the shell.

The `benchmarkId` field is semver-ish: `<name>@<version>` or
`<name>/<subset>@<version>`. Examples that pass the widened regex:

- `humaneval@v1.0`
- `humaneval/python@v1.0`
- `swe-bench_verified@1.0`
- `mmlu-5shot@2024-03`

---

## Frozen invariants (post-merge)

- Field names and shape of `benchmark-result` are frozen — a rename or removal
  is a major schema bump (v7+).
- The `provenance` enum is frozen. Extensions require a major schema bump.
- The `unit` enum (`pct`, `pass@1`, `pass@10`, `bleu`, `f1`, `accuracy`,
  `elo`, `raw`) is frozen for the same reason.
- Mirrored rows are forever excluded from Trust Magnitude.
- Self-attested provenance is forever rejected.

Any change to these requires a Splurge-tier RFC.

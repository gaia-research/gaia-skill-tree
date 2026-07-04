# MMLU Benchmark — Methodology v1 (`mmlu@2024-03`)

> **Provenance: `mirrored`** — This is a citation-only benchmark.
> Scores sourced here do **not** count toward Trust Magnitude (TM).
> See [Provenance Ladder](#provenance-ladder) below.

## What is MMLU?

**Massive Multitask Language Understanding (MMLU)** is a benchmark that
measures a language model's knowledge and reasoning across 57 academic
subjects, including mathematics, history, law, medicine, and computer
science.  It evaluates models in a **5-shot** setting: the model is given
five example questions with answers before being tested on new questions.

Original paper: [Measuring Massive Multitask Language Understanding](https://arxiv.org/abs/2009.03300) (Hendrycks et al., 2020).

## Snapshot source

Scores in this registry come from a static snapshot of the
[HuggingFace Open LLM Leaderboard](https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard)
dated **2024-03-01**.  The snapshot file lives at
`scripts/benchmarks/mmlu/snapshot.json` in this repository.

| Field | Value |
| ----- | ----- |
| `benchmarkId` | `mmlu@2024-03` |
| `unit` | `pct` (0–100 percentage accuracy) |
| `sourceSnapshotDate` | `2024-03-01` |
| `runAt` | `2024-03-01T00:00:00Z` |

## Provenance ladder

The Gaia registry requires reproducible provenance for Trust Magnitude
contribution.  MMLU scores in this snapshot are **cited** from a public
leaderboard — they were not produced by a CI-executed harness in this
repository and have not been co-signed by a 4★+ Verifier running the
model directly.

| Provenance | TM contribution | How achieved |
| ---------- | --------------- | ------------ |
| `ci-reproduced` | ✅ Counted | CI workflow re-ran the harness on the same commit |
| `verifier-attested` | ✅ Counted | 4★+ Verifier co-signed the run |
| `mirrored` | ❌ **Excluded** | Cited from a public leaderboard |
| `pending` | ❌ Excluded | Awaiting CI reproduction |

**Why exclude mirrored?**  A cited number can be stale, incorrectly
attributed, or measured under different conditions (prompt format,
tokenization, dataset split).  Counting it toward TM would allow badge
inflation from numbers we cannot independently verify.  The leaderboard
renders mirrored rows with a **"Cited"** badge (W4 responsibility) to
surface the distinction without hiding the data.

## Refreshing the snapshot

1. Visit the [leaderboard](https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard).
2. Export current 5-shot MMLU averages for the skills in `snapshot.json`.
3. Edit `scripts/benchmarks/mmlu/snapshot.json`, bump `sourceSnapshotDate`.
4. Run `python scripts/benchmarks/mmlu/ingest.py --dry-run` to preview.
5. Run `GAIA_OPERATOR_OVERRIDE=1 python scripts/benchmarks/mmlu/ingest.py` to write.
6. Regenerate `docs/api/v1/benchmarks/mmlu.json` to reflect the updated rows.
7. Open a PR on a `review/meta/` branch.

## API projection

Machine-readable row data is served at
[`/api/v1/benchmarks/mmlu.json`](/api/v1/benchmarks/mmlu.json).
The index of all registered benchmarks is at
[`/api/v1/benchmarks/index.json`](/api/v1/benchmarks/index.json).

See [`docs/benchmarks/methodology.md`](./methodology.md) for the full
cross-benchmark provenance contract.

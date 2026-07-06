# MMLU mirrored ingest — `mmlu@2024-03`

Mirror-only citation ingest for the Massive Multitask Language Understanding
(MMLU) benchmark.  This is **not** a live evaluation harness — it never runs
the model.  Its job is to import publicly reported MMLU scores from trusted
leaderboard snapshots as `provenance: mirrored` evidence rows.

## Provenance contract

`mirrored` rows are **permanently excluded** from Trust Magnitude (TM).

| Provenance | TM contribution | Meaning |
| ---------- | --------------- | ------- |
| `ci-reproduced` | Counted | Score verified by CI reproduction |
| `verifier-attested` | Counted | 4★+ verifier co-signed the run |
| `mirrored` | **Excluded (returns None)** | Cited from a public leaderboard |
| `pending` | Excluded | Awaiting reproduction |

`computeArtifactScoreOrNone` in `src/gaia_cli/trustMagnitude.py` short-circuits
on `provenance in ('mirrored', 'pending')` and returns `None`, so the TM sum
never inflates from cited numbers.  W4 is responsible for rendering mirrored
rows with a distinct "Cited" badge on the leaderboard surface.

## Snapshot

`snapshot.json` is a hand-curated static snapshot of MMLU 5-shot scores drawn
from the Open LLM Leaderboard (HuggingFace) on 2024-03-01.  Source URL:
<https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard>

The snapshot is intentionally static to avoid runtime network dependencies
inside the ingest script.  To refresh it:

1. Visit the leaderboard URL above.
2. Export / note the current 5-shot MMLU average for each skill's primary model.
3. Edit `snapshot.json`, bump `sourceSnapshotDate` to the new date.
4. Re-run `python scripts/benchmarks/mmlu/ingest.py --dry-run` to preview.
5. Run without `--dry-run` to write the updated rows.

## Files

| Path | Role |
| ---- | ---- |
| `__init__.py` | Package marker (empty) |
| `README.md` | This file |
| `snapshot.json` | Static MMLU score snapshot (hand-curated, 2024-03-01) |
| `ingest.py` | Reads snapshot → invokes `gaia dev evidence … --provenance mirrored` |

## Invocation

```bash
# Preview — no writes
python scripts/benchmarks/mmlu/ingest.py --dry-run

# Write mirrored rows for all snapshot entries
GAIA_OPERATOR_OVERRIDE=1 python scripts/benchmarks/mmlu/ingest.py
```

## Why mirrored rows are excluded from TM

MMLU scores in this snapshot are cited from a public leaderboard.  The Gaia
registry requires reproducible provenance for TM contribution: either the
score was produced by a CI-executed harness in this repo, or it was
co-signed by a 4★+ Verifier who ran the model themselves.  A cited leaderboard
number satisfies neither — it is informational, not authoritative.  Excluding
it prevents badge inflation from numbers we cannot independently verify.

See `docs/benchmarks/methodology/` for the full provenance ladder.

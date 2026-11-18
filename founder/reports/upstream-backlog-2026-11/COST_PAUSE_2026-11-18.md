# Campaign cost pause snapshot

**Engineering remains PAUSED. This is not a complete campaign total or provider invoice.**

Snapshot: `2026-11-18T00:05:58.690198+00:00`; component pricing: `2026-11-18T00:08:02.669711+00:00`.

Exact parent-session linkage identifies **96 retained run/task records and 82 unique child sessions**, deduplicating resumed sessions. **2 raw logs remain; 80 older sessions have log-derived digests that omit cache counters.**

| Model / effort | Unique sessions | Retained input | Retained output | Known priced components (USD)* |
|---|---:|---:|---:|---:|
| claude-opus-5-5 / medium | 2 | 256,726 | 21,365 | $1.454204 |
| gemini/gemini-4-hydrogen / medium | 11 | 1,595,249 | 263,399 | $4.368366 |
| gpt-6-luna / medium | 39 | 2,557,161 | 282,642 | $0.415829 |
| gpt-6.1-sol / medium | 14 | 1,375,796 | 244,020 | $5.191792 |
| gpt-6.1-terra / high | 16 | 1,041,499 | 63,019 | $1.356594 |

**Known component subtotal: $12.786785.** This prices retained input/output components and any actually retained cache components at the canonical public catalog rates. It does **not** price the missing caches or missing main session. It is not the amount spent, a completed lane total, or an invoice lower bound.

Retained input/output: **6,826,431 input + 874,445 output = 7,700,876 tokens**, excluding missing cache usage. The fully cache-accounted raw-log subset is only **$0.03808308** and is not representative of campaign spend.

## Unavailable / limitations
- Complete cost for each model lane and the campaign is **unavailable**. The lead raw session is missing, and older worker digests discard `cacheRead` / `cacheWrite`. Missing counters were not treated as zero.
- Monetary values use canonical `pi_cost.py::price_worker`; older harness/UI dollar totals were not substituted. Complete totals remain null.
- Exact catalog model normalization only; unknown rate/model components remain unpriced.
- Raw usage events and unique session digests are counted once. Native tool delivery receipts are not added, and three source-author resumes do not multiply the cumulative session.
- This is all retained positively linked campaign evidence, not proof that missing root history never contained other workers. Errors and later reporting/admin turns can be unmetered or outside the cutoff.
- Historical **$4.907920** is a P0-only partial reference, not added to this snapshot.

Catalog source: `https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json`; fetched `2026-11-14T14:12:12Z`; stale: `False`.

The previous `cost-pause-2026-11-campaign.json` was incomplete and carried a placeholder cutoff; this recovered report supersedes it. No source implementation, deployment, migration, watcher dispatch, or merge was performed for this audit.

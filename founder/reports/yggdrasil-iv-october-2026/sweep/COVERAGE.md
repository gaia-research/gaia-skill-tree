# October 2026 Meta Sweep — coverage receipt

**FULL META SWEEP COMPLETE (provisional October snapshot 2026-10-28; cutoff 2026-10-31T23:59:59Z, read-only).**
Generated deterministically by `tools/rebuild_from_journal.py` from workflow run `wf_fb1ee3fb-d06` (642 agents, 0 errors); registry revision `43797a441`.

## Coverage

- Records: 701 (400 named files incl. 48 awakened, 301 generic nodes); missing from shards: 0; blocked: 0.
- Evidence rows appraised: 874 (prepass: 874).
- Per-record appraisal: 29 Haiku batches (individual file read + prepass TM/gates + rule checks + semantic evidence relevance). Semantic review by the authorized Claude roster (Haiku per-record, Sonnet/Haiku 3-lens verification) in place of Jev/Luna.
- Findings: 930 raw → 930 deduplicated → 817 surviving (≥2 of 3 adversarial lenses upheld; 199 verification groups × 3, 0 votes missing).
- Surviving by priority: {'P0': 2, 'P1': 90, 'P2': 312, 'P3': 354, 'P4': 59}.
- Final dispositions: {'change-proposed': 469, 'reviewed-no-change': 232} (auditors: {'change-proposed': 491, 'reviewed-no-change': 210}).
- Surviving findings targeting globs / multi-record scopes (not attached to one record): 54 — listed in `findings.json` `unattachedSurvivingFindingKeys`.
- Fusion candidates: 6; new-generic proposals: 11.

## Survey dimensions

| Dimension | Checked | Findings |
|---|---|---|
| star-bar | 125 | 0 |
| liveness | 962 | 11 |
| origin-attribution | 701 | 17 |
| unbacked-star | 701 | 7 |
| brand-coupled | 301 | 19 |
| heavy-deps | 126 | 6 |
| installability | 352 | 6 |
| placeholder-bodies | 701 | 6 |
| testuser-timelines | 864 | 0 |
| champion-cluster | 701 | 2 |
| unique-isolation | 701 | 4 |
| grade-mismatch | 874 | 13 |
| product-attribution | 10 | 7 |

## Surviving findings by dimension

| Dimension | Surviving |
|---|---|
| evidence | 253 |
| body | 169 |
| origin | 91 |
| link | 59 |
| starBar | 34 |
| rank | 33 |
| metadata | 24 |
| classification | 22 |
| origin-attribution | 17 |
| upstream | 14 |
| frontmatter | 14 |
| grade-mismatch | 12 |
| liveness | 10 |
| structural | 9 |
| new-generic | 9 |
| unbacked-star | 7 |
| semantic-fusion | 6 |
| brand-coupled | 5 |
| installability | 5 |
| placeholder-bodies | 5 |
| heavy-deps | 4 |
| unique-isolation | 4 |
| product-attribution | 4 |
| champion | 4 |
| champion-cluster | 2 |
| reclassification | 1 |

## Exceptions (stated, not hidden)

- Liveness: first pass (concurrency 16) hit 211 GitHub HTTP 429s. Full re-probe at concurrency 3 (`liveness-reprobe/`): 962 URLs, 903 alive, 59 dead, 0 unknown. Every dead URL is review debt only (bounded t0/+24h/+72h probes), never a demotion.
- The workflow's own synthesis agent hand-transcribed an abridged findings list (810 surviving); it was replaced by this deterministic replay (817). Counts here are authoritative.
- All findings are proposals. No registry mutation was made. Under Yggdrasil IV no proposal rests on elapsed time, dead links, competitor existence or model confidence; consequences are adjudicated separately (`../adjudication/`).

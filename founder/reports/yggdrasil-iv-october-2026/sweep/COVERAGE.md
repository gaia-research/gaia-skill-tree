# October 2026 Meta Sweep — coverage receipt

**FULL META SWEEP COMPLETE (final October record through cutoff `2026-10-31T23:59:59Z`; provisional snapshot `2026-10-28` preserved immutable at `prepass.json` / `ledger.json`, post-cutoff delta recorded in `prepass-final-2026-10-31.json`).**
Generated deterministically by `tools/rebuild_from_journal.py` from workflow run `wf_fb1ee3fb-d06` (642 agents, 0 errors); baseline registry revision `43797a441`, final post-L4/post-cutoff revision `525f3c93730a3f726a0cc0d50860ac51e011f8b4`.

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

## Post-Cutoff Final Refresh (`2026-10-31T23:59:59Z` cutoff & `2026-11-01T16:40Z` +72h witness gate)

- **Provisional snapshot preserved:** `prepass.json` (`43797a441`, 701 records: 400 named incl. 48 awakened, 301 generic, 874 evidence rows) and `ledger.json` remain byte-identical.
- **Final post-cutoff prepass (`prepass-final-2026-10-31.json`, revision `525f3c937`):** **784 records** (**473 named files**: 426 indexed across 223 buckets + 47 awakened across 77 contributors; **311 generic nodes**: 156 basic + 155 fusion; **1,031 evidence rows**). Delta vs provisional snapshot: +84 added records (73 new L4 named skills, 10 new generic/fusion nodes, and `interview-me` renamed from `grill-me`), -1 renamed generic ID (`grill-me` → `interview-me`), 0 appraisal errors. The single expected stored-vs-TM gate note is `google-deepmind/workflow-skill-creator` (stored `4★`, `TM = 59.65 B` after honest `r4-peer-review-rows` retyping, clamped to `3★` across all public surfaces as Yggdrasil IV review debt).
- **Liveness & `mattpocock/skills` +72h witness probe:** Baseline 962 URLs re-probed at concurrency 3 (`liveness-reprobe/`: 903 alive, 59 dead, 0 unknown) plus 73 new L4 `SKILL.md` blob URLs verified live. Post-deadline +72h witness probe executed at `2026-11-02T20:28:46Z` (after the `2026-11-01T16:40Z` deadline): `https://frontendmastery.com/posts/matt-pocock-claude-code-skills-architecture/` returned HTTP 404 (site root HTTP 200; Wayback Machine `archived_snapshots: {}`; OpenAlex `W7167605459` HTTP 200). Under Yggdrasil IV bounded-probe rules and founder ruling `FD-9`, the 404 witness remains recorded review debt with no automatic demotion; `mattpocock/skills` stays `5★` at `TM = 280.39 S`.

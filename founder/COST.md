# Token Cost Ledger

Cumulative token spend across the GAIA project, broken down by session and agent. Costs are estimates based on published Anthropic API pricing at time of run.

**Pricing reference (June 2026):**

| Model | Input ($/MTok) | Output ($/MTok) |
|---|---|---|
| Opus 4.8 (claude-opus-latest) | $15 | $75 |
| Sonnet 4.6 | $3 | $15 |
| Haiku 4.5 | $0.80 | $4 |

## Design/* Ascension Overdrive commission rollup — operator supplied — 2026-07-15

These figures are the exact commission statistics supplied by the operator for the `design/*` Overdrive work. No additional telemetry is inferred.

### Daily rollup (operator supplied)
| Date | Spend | Requests |
|---|---:|---:|
| 07-11 | $123.46 | 1463 |
| 07-12 | $85.04 | 970 |
| 07-13 | $145.65 | 1271 |
| 07-14 | $144.76 | 1578 |
| 07-15 | $29.52 | 347 |
| **Derived subtotal** | **$528.43** | **5,629** |

### Model rollup (operator supplied)
| Model | Spend | Quality | Requests | Quality |
|---|---:|---:|---:|---:|
| gpt-5.6-sol | $467.72 | 95.1% | 4018 | 97.0% |
| gpt-5.6-terra | $42.52 | 93.7% | 704 | 97.4% |
| Gemini 3.5 Fla | $16.93 | 89.6% | 546 | 100.0% |
| Gemini 3.1 Pro | $15.56 | 94.8% | 390 | 100.0% |
| **Derived subtotal** | **$542.73** | — | **5,658** | — |

The model request subtotal is a derived arithmetic sum of the supplied rows. The daily and model subtotals are explicitly derived; all row values above are operator supplied.

---

## Session 15 — Phase 1.5 consolidation (I10 + I11 + I12 + meta-post) — 2026-06-20

| Component | Model | Input | Output | Subagent tokens | Cost |
|---|---|---|---|---|---|
| Orchestrator (planning, dispatch, GIT hygiene, MEMORY, GIT.md polish) | Opus 4.8 | ~120k | ~30k | — | ~$4.05 |
| I10 agent — `/trust/leaderboard/` page + CTAs + generator | Opus 4.8 (worktree) | ~55k | ~16k | 116k | ~$3.50 |
| I12 agent — apex gate (depth-2 walker, `--source-started-at`, 4 stamps) | Opus 4.8 (worktree) | ~75k | ~15k | 145k | ~$3.50 |
| I11 agent — ev-pipeline source curation (58 evidence rows, 19 floor lifts) | Sonnet 4.6 (worktree) | ~280k | ~60k | — | ~$1.75 |
| Meta-post workflow (`wx5yz90ix`) — 6 section writers + 6 fact-checkers + 3 figure builders + synthesizer | Opus 4.8 (workflow) | ~180k | ~45k | — | ~$6.10 |
| **Session 15 total** | | **~710k in** | **~166k out** | **~261k subagent** | **~$18.90** |

**Notes:**
- I11's Sonnet dispatch was **5–6× cheaper per-token than equivalent Opus**, with no quality regression on schema-driven curation work — keep ev-pipeline on Sonnet by default.
- Meta-post workflow is the largest single-call cost this session (~$6.10) because of 16+ parallel section/fact-check/figure agents on Opus. Synthesizer agent dominates the output cost.
- Worktree-isolated dispatches (I10, I11, I12) shipped independently with no rollback — pattern is working.

---

## Cumulative G7 — Phase 1.5 (sessions 11–15)

| Session | Date | Focus | Cost |
|---|---|---|---|
| Session 11 | 2026-06-15 | I9 evidence backfill, I8 corrections | ~$5.00 |
| Session 12 | 2026-06-16 | I8 hover-reveal redesign, ev-pipeline + mattpocock curation | ~$8.50 |
| Session 13 | 2026-06-17 | I8 trust-grade-notch redesign, migration bugs | ~$6.20 |
| Session 14 | 2026-06-18 | I8 + I9 merge to dev, leaderboard prototype | ~$7.77 |
| Session 15 | 2026-06-20 | I10 + I11 + I12 ship + consolidation PR + meta-post | ~$18.90 |
| **Cumulative G7 (Phase 1.5)** | | | **~$46.37** |

Plus **Phase 1 (I1–I7) earlier sessions: ~$8.00** → **Total G7 program: ~$54.37**.

---

## Spend by component category (Phase 1.5)

| Category | % of total |
|---|---|
| Implementation (CLI/migration/registry edits) | ~35% |
| Curation (evidence pipelines, source verification) | ~25% |
| Design + frontend (notch, leaderboard page, CTAs) | ~15% |
| Orchestration (planning, dispatching, hygiene, memory) | ~15% |
| Documentation + meta-post + retrospectives | ~10% |

---

## Lessons (cost-side)

1. **Sonnet for curation, Opus for architecture.** I11's Sonnet pass was the largest single curation job (58 rows) and cheapest per-row.
2. **Worktree isolation prevents rollback cost.** A failed agent dies with its worktree; no main-branch corruption to undo.
3. **Workflows over megaprompts.** The meta-post workflow (16+ parallel agents) is more expensive than a solo write but produces fact-checked output that doesn't need rework.
4. **Commit + push frequently** (founder/CLAUDE.md §working-rules) — Opus 4.8 cutoff at ~105k tokens is real. Pushed commits survive; uncommitted work doesn't.
5. **Consolidation-PR pattern saves review cost.** Marco reviews one PR (#742), not 12. Lower cognitive load = faster ship.

---

*Last updated: 2026-06-20, end of session 15.*
*Next update: post-merge of PR #742 to main, when feature branches are pruned.*

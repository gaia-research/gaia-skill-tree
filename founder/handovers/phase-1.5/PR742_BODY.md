## Phase 1.5 — G7 Trust Infrastructure (consolidation PR)

This is the **single consolidation PR** for all Phase 1.5 work. Per `founder/GIT.md` §3.2, individual feature PRs merge into `dev/phase-1.5-inspection`; this PR is what Marco reviews and merges to `main` once the entire phase is baked.

**Status:** DRAFT — pending Marco's holistic visual + functional inspection. Do not merge until the gate checklist below is fully green.

> **Merge style: never squash.** Per `founder/GIT.md` §3.2 + Marco's standing rule, merge this PR with the **merge-commit** strategy so every commit on the consolidation lane is preserved. The history is the audit log.

> **Where to find the full session-by-session history of what happened during Phase 1.5:** every snapshot, decision, agent dispatch, branch state, and token cost is logged in `founder/MEMORY.md` (orchestrator memory) and `founder/COST.md` (token-spend ledger). Anyone reviewing this PR who wants to dig into the *why* of a specific commit should start there — those files are the canonical reference for Phase 1.5 archaeology.

### Included work (all merged into this branch)

| Issue | PR | Description | Status |
|---|---|---|---|
| I1 | #726 | Schema — trust magnitude fields | ✅ already on main (pre-consolidation) |
| I2 | #728 | CLI — compute trust magnitude | ✅ already on main (pre-consolidation) |
| I3 | #733 | Migration — big-bang regrade + stamp report | ✅ in branch |
| I4 | #732 | CI — apex gate + system-wide cap | ✅ in branch |
| I5 | #735 | Registry — apex cutover, demote mattpocock + ruvnet | ✅ in branch |
| I6 | #736 | Display — TM badge + apex gate cards | ✅ in branch |
| I7 | #734 | Docs — codex trust methodology page | ✅ in branch |
| I8 | #743 | Trust Grade notch design (pixel-thin bar with hover-reveal MAG count) | ✅ in branch |
| I9 | #744 | Evidence backfill + repo→repo-own scorer alias + 14 mattpocock skills | ✅ in branch |
| I10 | #747 → #750 | Public Trust Magnitude Leaderboard at `/trust/leaderboard/` + CTAs | ✅ merged at e111ae5e |
| I11 | #753 → #751 | Source curation pass — 58 evidence rows, 19/20 floor lifts to C+, google-deepmind cluster to A | ✅ merged at eae4c124 |
| I12 | #748 → #746 | Apex gate — depth-2 walker includes suiteComponents, `--source-started-at` CLI flag, 4 apex stamps | ✅ merged at 2090ee31 |
| I13 | #754 | mattpocock classify — 14 awakened→named + share artifact refresh (badge 20→34, suite TM 441→480) | ✅ merged at 2e886472 |
| RFC v3 | — → #749 | Depth-2 amendment + `apex_pr_signed` enum + `sourceStartedAt` formalization | ✅ ratified at 9ff1bc78 |
| Sources | — | `founder/sources/` data lake from `dev/sources` (10-type evidence taxonomy) | ✅ in branch |
| CLI fix | #738 | `gaia dev timeline --user` routing fix | ✅ in branch |
| Meta-post | — | June 2026 retrospective via L3-mechanical fallback | ✅ at e4e6d954 |
| Docs sync | — | README/CONTRIBUTING/DEV.md updated for Phase 1.5 reality | ✅ at 694fdcb6 |
| Archive | — | METASHIFT.md, pr_report.md, reports/ → `docs/meta/archive/` | ✅ at 844c95d5 |

### Final TM distribution snapshot (post-merge, SHA d0bf9184)

```
S = 4    | A = 42   | B = 56   | C = 76   | ungraded = 71
                                              total: 249 named skills
                                              rank-floor = 1   (was 20 pre-I11)
                                              [up] = 64
```

vs. pre-Phase-1.5 baseline: `S=4 A=20 B=31 C=93 ungraded=101`. Net: **+22 skills jumped to A**, **+30 crossed the C floor**.

I13 follow-up promoted 14 quarantined mattpocock skills (awakened→named); `mattpocock/skills` suite TM lifted from 441 → 480 with the new evidence.

### Apex Gate state (top-4 S-grade skills)

| Skill | TM | Apex predicates passing | Status |
|---|---|---|---|
| `garrytan/gstack` | 589 | 4/6 (§11.12.2 / .3 / .4 / .8) | Awaits §11.12.5 sourceTenure (post-I11 follow-up) |
| `ruvnet/ruflo` | 482 | 4/6 | Awaits §11.12.5 sourceTenure |
| `mattpocock/skills` | 441 | 4/6 | Awaits §11.12.5 sourceTenure |
| `obra/superpowers` | 416 | 4/6 | Awaits §11.12.5 sourceTenure |

Apex Promotion PR signed by `mbtiongson1` on 2026-06-20 (frontmatter `apexGateStatus.apexPromotionPrSigned = true` for all four).

### Gate checklist — DO NOT MERGE until

- [x] I3 / I4 / I5 / I6 / I7 / I8 / I9 / I10 / I11 / I12 all merged into `dev/phase-1.5-inspection`
- [x] All TM > 0 validated post-migration; suiteComponents fusion scoring correct (namedSkillMap fix)
- [x] `generateNamedIndex.py` regenerated; `registry/named-skills.json` reflects post-I11 state
- [x] Final visual inspection HTML produced (`generated-output/leaderboard.html` 54.5KB, `generated-output/inspect_garrytan_gstack.html`)
- [x] Public `/trust/leaderboard/` page live with token-based design language
- [x] Apex gate signed for top-4 S-grade skills
- [x] No manual frontmatter timeline edits — CLI-only enforcement confirmed across I10/I11/I12
- [ ] **Marco's visual + functional inspection of the consolidation diff** (this PR's review)
- [ ] CI green on `dev/phase-1.5-inspection` HEAD

### Known follow-ups (tracked, not blocking this merge)

- **#746** — Apex gate: A-graded origins ≥ 5 predicate (`§11.12.1`) for the 4 S-grade suites — needs deeper origin source curation; queued after Phase 1.5 ships.
- **~~#749~~** — RFC v3 ratification follow-ups: ~~depth-2 amendment language~~, ~~`apex_pr_signed` timeline action enum~~, ~~source-tenure predicate calibration~~. **✅ Ratified at 9ff1bc78** (`founder/handovers/G7_RFC_V3_RATIFICATION_2026-06-20.md`).
- **#751** — I11 P3 batch: ~71 skills still ungraded; mostly low-signal generic-only candidates. Fast-follow after Phase 1.5.
- **`generateNamedIndex.py` legacy threshold bug** (S≥90/A≥80) — frontmatter values are canonical; index thresholds need realignment to G7 floors (S≥250/A≥100). Tracked as tech-debt; non-blocking.

### Post-merge — release path

A 5.0.0 major release is queued for execution post-merge. See `founder/handovers/RELEASE_5.0.0_RUNBOOK.md` for the step-by-step runbook (version-bump, PyPI publish, npm publish, GitHub release, rollback path). Do not execute until this PR merges.

### Conflict resolution

Any conflicts with `main`: take ours (`dev/phase-1.5-inspection` is canonical for Phase 1.5).

### Branch scope

This PR spans every branch prefix (schema, cli, design, review/meta, infra, docs) by design — it's the consolidation lane. Label `skip-scope-check` is applied per `founder/GIT.md` §3.3 standing pre-approval.

Resolves #719 #720 #726 #728 #732 #733 #734 #735 #736 #738 #740 #743 #744 #746 #749 #750 #751 #754

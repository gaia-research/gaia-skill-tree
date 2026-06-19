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
| Sources | — | `founder/sources/` data lake from `dev/sources` (10-type evidence taxonomy) | ✅ in branch |
| CLI fix | #738 | `gaia dev timeline --user` routing fix | ✅ in branch |

### Final TM distribution snapshot (post-merge, SHA d0bf9184)

```
S = 4    | A = 42   | B = 56   | C = 76   | ungraded = 71
                                              total: 249 named skills
                                              rank-floor = 1   (was 20 pre-I11)
                                              [up] = 64
```

vs. pre-Phase-1.5 baseline: `S=4 A=20 B=31 C=93 ungraded=101`. Net: **+22 skills jumped to A**, **+30 crossed the C floor**.

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
- **#749** — RFC v3 ratification follow-ups: depth-2 amendment language (now allows suiteComponent overlap with depth-1), `apex_pr_signed` timeline action enum, source-tenure predicate calibration.
- **#751** — I11 P3 batch: ~71 skills still ungraded; mostly low-signal generic-only candidates. Fast-follow after Phase 1.5.
- **`generateNamedIndex.py` legacy threshold bug** (S≥90/A≥80) — frontmatter values are canonical; index thresholds need realignment to G7 floors (S≥250/A≥100). Tracked as tech-debt; non-blocking.

### Conflict resolution

Any conflicts with `main`: take ours (`dev/phase-1.5-inspection` is canonical for Phase 1.5).

### Branch scope

This PR spans every branch prefix (schema, cli, design, review/meta, infra, docs) by design — it's the consolidation lane. Label `skip-scope-check` is applied per `founder/GIT.md` §3.3 standing pre-approval.

Resolves #726 #728 #732 #733 #734 #735 #736 #738 #743 #744 #746 #750 #751

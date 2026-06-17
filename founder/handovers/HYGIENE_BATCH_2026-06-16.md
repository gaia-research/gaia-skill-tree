# GitHub Hygiene Batch — Phase 1 Closeout

**Drafted:** 2026-06-16 by Orchestrator. **Status:** awaiting Marco approval before any execution.
**Rule:** every `gh` write below is drafted here; nothing posts until Marco says "approved" (per `founder/CLAUDE.md` autonomy rule).

---

## Goal

Get milestone #4 (Phase 1) into a clean state where the open-issue list **exactly matches** the G1–G7 work items in `PHASE1_MASTER.md`, with no duplicates, no scope-misaligned items, and clear labeling. Result: a 6-item milestone that closes cleanly when G1–G7 ship.

---

## Pre-execution snapshot of milestone #4

Open (7): #185, #637, #647, #649, #650, #654, #658, #699 (no milestone yet).
Closed (2): #128, #155.

Target after this batch (open, all addressed by G-tasks):
1. #185 — Security scanner → **G3**
2. #642 — Narrow-path tree render → **G6** (currently NOT on milestone #4 — H7B adds it)
3. #649 — Benchmark RFC → **G7**
4. #658 — Verification workflow (folds #650) → **G4**
5. #699 — Rank gates → **G2**
6. **NEW** — CI registry path filter → **G1**

That's 6 open items, all mapped 1:1 to G1–G7.

---

## H1 — Fold #650 into #658

**Action:** Comment on #650, then close as duplicate of #658.

**Comment to post on #650:**
> Folding into #658.
>
> "Define Certification Tiers" and "Implement Verification Workflow — levels as predicates over Overall Trust Grade" are the same artifact in different framings: a 4-tier verification predicate system (Community Verified / Benchmark Verified / Security Reviewed / Enterprise Ready) layered on Overall Trust Grade + tenure + scanner outcomes.
>
> #658 is the implementation tracker. Closing this as duplicate; no work is dropped. See `founder/handovers/PHASE1_MASTER.md` G4 for the consolidated spec.

**Commands:**
```bash
gh issue comment 650 --body-file H1_650_comment.md
gh issue close 650 --reason "not planned" --comment "Folded into #658 (G4). See above."
```
*(or `--reason completed` if Marco prefers; "not planned" reads cleaner for a fold.)*

---

## H2 — Remove #647 from milestone #4

**Action:** Strip milestone #4 from #647; keep open; keep `help wanted` label.

**Reason:** Marco's earlier disposition (memory 2026-06-10): #647 is a contributor-driven exploration issue, not a Phase-1 deliverable. Leaving it on #4 prevents the milestone from ever closing.

**Command:**
```bash
gh issue edit 647 --remove-milestone
```

---

## H3 — Post 1-pager comment on #647

**Comment to post on #647** (drafted; Marco edits if desired):

> ## Git-as-Database — Where We Are, When to Migrate
>
> **Current strategy:** the canonical registry is git-tracked JSON/Markdown. Reads are filesystem-fast; writes are PR-mediated for auditability. This is correct for our current scale.
>
> **Hard limits we are not yet near:**
> - Registry size: ~228 skills today; git stays comfortable to ~10k files.
> - Query latency: `gaia validate` runs in <2s on full registry; `gaia skills search` is <300ms.
> - Concurrent writers: PR-serialized; no contention.
>
> **Migration triggers — revisit when ANY hits:**
> 1. Named-skill count crosses **5,000** (file enumeration starts to drag).
> 2. `gaia skills search` p95 latency exceeds **200ms** on a developer laptop.
> 3. We need cross-skill aggregations that don't fit a single-pass scan (e.g., "average trust grade by contributor over last 90 days, refreshed live").
> 4. We need write paths that are not PR-serialized (e.g., live user telemetry feeding ranking).
>
> **When triggered, evaluate (in order):**
> - **Dolt** — git-shaped SQL; lowest cognitive shift; preserves PR review model. Best fit if triggers 1+2 hit but 3+4 don't.
> - **Supabase** — Postgres + auth + realtime out of the box. Best fit if triggers 3+4 hit (we want server-side aggregations + live writes).
> - **DuckDB-on-git** — read-only OLAP layer over the existing registry. Cheapest stopgap if only trigger 3 hits.
>
> **Open for community input:** repo-trust-score storage, telemetry ingestion shape, multi-region read replicas. Removing this from milestone #4 since it's not a Phase-1 gate; keeping it open for DB-specialist contributors.

**Command:**
```bash
gh issue comment 647 --body-file H3_647_onepager.md
```

---

## H4 — Remove #637 from milestone #4

**Action:** Strip milestone #4 from #637; keep open with `RFC` label.

**Reason:** Per Marco's 2026-06-10 disposition, #635 already covered `gaia tree` / `gaia graph` local-first defaults. The remaining proposals (`gaia stats`, `gaia lookup`, `gaia path`, `gaia skills list/search` defaults) stay RFC; not a Phase-1 acceptance criterion.

**Command:**
```bash
gh issue edit 637 --remove-milestone
```

---

## H5 — Move #654 off milestone #4

**Action:** Move #654 from milestone #4 → milestone #5 (Phase 2). Add label `phase-2`.

**Reason:** Evidence-types expansion is Phase 2 scope; #646 (parent) is closed; the trust-grade pipeline ships without it.

**Command:**
```bash
gh issue edit 654 --milestone "Phase 2 - Differentiation Layer"  # exact title may differ; check milestone list
gh issue edit 654 --add-label "phase-2"
```
*(Verify exact milestone #5 title before running; `gh api repos/:owner/:repo/milestones`.)*

---

## H6 — Set milestone #4 + label on #699

**Action:** Add #699 to milestone #4. Add labels: `phase-1`, `enhancement`. Keep `backend`, `planning`.

**Command:**
```bash
gh issue edit 699 --milestone "Phase 1 — Trust Infrastructure"
gh issue edit 699 --add-label "phase-1,enhancement"
```

**Body amendment** (post as comment, since `gh issue edit --body` rewrites the original):
> **Update — 2026-06-16 (Orchestrator):** Reality check shows `evidenceFloors` already exist in `meta.json` and `_meets_evidence_floor()` already enforces them in `promotion.py`. The actual gap: those gates read **legacy `class`** values, not the new **`grade`** field that `derive_grade()` now writes. Scope of this issue narrows to a translation patch — see `founder/handovers/PHASE1_MASTER.md` G2.

---

## H7A — Open new issue for G1 (CI registry path filter)

**Title:** `[infra] CI: include registry/** in pull_request path filter so data-only PRs don't silently skip`

**Body:**
> ## Problem
>
> `.github/workflows/python-package.yml` currently triggers on `push` and `pull_request` with path filters covering `src/**`, `tests/**`, `pyproject.toml`, `packages/cli-npm/cli/**`, and workflow YAML — but NOT `registry/**`.
>
> Result: a PR that touches only `registry/` (e.g., a backfill or named-skill addition) silently does NOT run the full test suite, even though those changes can break `gaia validate`, schema invariants, and grading logic.
>
> Original symptom surfaced via #690 (data-only head SHA on a 316-file PR; head untested).
>
> ## Fix
>
> Add `registry/**` (and `registry/schema/**` for clarity) to BOTH `push.paths` and `pull_request.paths`.
>
> ## Acceptance
>
> - [ ] An empty whitespace-only PR touching only `registry/named-skills.json` triggers `python-package.yml`.
> - [ ] Existing matrix continues passing on a code+data PR.
> - [ ] No new path-collision noise on already-covered branches.
>
> Tracked as G1 in `founder/handovers/PHASE1_MASTER.md`. Light-effort issue; good Haiku 4.5 task.

**Command:**
```bash
gh issue create \
  --title "[infra] CI: include registry/** in pull_request path filter so data-only PRs don't silently skip" \
  --body-file H7A_new_issue.md \
  --label "infrastructure,phase-1" \
  --milestone "Phase 1 — Trust Infrastructure"
```

---

## H7B — Add #642 to milestone #4

**Action:** #642 (narrow-path tree render) is currently NOT on any milestone but is G6 in the master plan.

**Command:**
```bash
gh issue edit 642 --milestone "Phase 1 — Trust Infrastructure"
gh issue edit 642 --add-label "phase-1"
```

---

## H8 — Schedule mid-July recalibration RFC

**Action (this session):** Add a durable scheduled task to remind the orchestrator on 2026-07-10.

```
CronCreate({
  cron: "3 9 10 7 *",                 // Jul 10 at 09:03 local
  durable: true,
  recurring: false,
  prompt: "Open the Trust Model Recalibration RFC on GitHub. Cover: (1) pillar-rule thresholds for the suite ultimate gate (≥3 evidenced components, ≥1 S + ≥2 A, floor C) — review whether thresholds calibrate well after ~1 month of real grading data; (2) overall_trust_grade() is currently a MAX over evidence grades, but the RFC envisioned 'beyond reasonable doubt' accumulation — decide whether aggregation should require corroboration/volume; (3) any G2/G3/G4 surface findings that suggest threshold drift. Reference founder/handovers/done/TRUST_MODEL_RFC.md and founder/MEMORY.md."
})
```

(Schedule in this session after Marco approves the rest.)

---

## H9 — Label cleanup pass (optional, batch)

These issues currently lack the `phase-1` label that would make milestone #4 self-evident from the issue list:

- #185 → add `phase-1`
- #642 → add `phase-1` (handled in H7B)
- #649 → add `phase-1`
- #658 → add `phase-1`
- #699 → add `phase-1` (handled in H6)
- (H7A new issue inherits `phase-1` at creation)

**Commands:**
```bash
for n in 185 649 658; do gh issue edit $n --add-label "phase-1"; done
```

(If `phase-1` label doesn't exist yet: `gh label create phase-1 --color "0E8A16" --description "Phase 1 — Trust Infrastructure scope"`.)

---

## Execution order (after Marco approves)

1. Run **H7A** (create new G1 issue) — needs to exist before H9 references it.
2. Run **H1** (#650 fold + close).
3. Run **H2, H4, H5** (milestone removals/moves).
4. Run **H3** (#647 1-pager comment).
5. Run **H6, H7B** (milestone adds for #699 + #642).
6. Run **H9** (label sweep).
7. Run **H8** (CronCreate for mid-July recalibration).

After all of the above, milestone #4 contents = exactly {#185, #642, #649, #658, #699, NEW G1 issue} = 6 open, mapped 1:1 to G1–G7 in the master plan.

---

## Verification step

After execution:
```bash
gh issue list --milestone "Phase 1 — Trust Infrastructure" --state open --json number,title,labels --limit 20
```
Expected: 6 results, all carrying `phase-1` label.

---

## What this batch does NOT do

- Does not touch closed issues (#128, #155 stay closed).
- Does not modify the project board (board moves happen as G-tasks land their PRs).
- Does not touch milestone #7 (the Sprint-1 Next-30 milestone — already 75% closed, will close itself when #697/#698 ship).
- Does not modify any code or docs in the repo.
- Does not interact with the registry data.

All actions are GitHub-state-only (issue metadata + comments).

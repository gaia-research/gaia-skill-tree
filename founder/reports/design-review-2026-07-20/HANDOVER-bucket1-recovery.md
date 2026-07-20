# HANDOVER — Ygg II design recovery (Bucket 1, one-by-one with approval gates)

> **You are a coding agent picking up a design-fix recovery.** Read this whole file before touching anything. It is written to be unambiguous — if something here conflicts with your own inference, THIS FILE WINS. When in doubt, STOP and ask; do not guess. Most prior design mistakes came from acting on an assumption instead of verifying. Verify first, act second, one fix at a time.

---

## 0. The one rule that governs everything

**Recover ONE fix at a time. After each fix, STOP and present it for a decision: APPROVE / REJECT / NO CHANGES. Do not start the next fix until you get a decision.**

- **APPROVE** → commit that one fix (one commit, one fix), push, then move to the next.
- **REJECT** → `git restore` the files you touched for that fix (discard it), then move to the next.
- **NO CHANGES** → the fix turned out to be already-present or unnecessary; touch nothing, note it, move to the next.

Never batch. Never "just do them all and show a summary." The whole point of this handover is a human checkpoint on each cherry-pick, because these fixes touch files that were rewritten by a taxonomy migration and a wrong port can silently regress a shipped fix.

---

## 1. What happened (so you are grounded, not guessing)

Yggdrasil II shipped in two layers on **separate** branches:

1. **Oracle / taxonomy layer** — PR #1235, merged into `dev/yggdrasil-ii-staging`. This rewired the frontend to read an **emitted `branch` field** from `docs/graph/named/index.json` instead of computing it from a dead `type` enum. THIS IS RATIFIED AND CORRECT — do not fight it.
2. **Design-polish layer** — lived on `design/ygg2-deferred-polish`, `design/ygg2-fixforward-superadmin` (PR #1227, closed), `design/ygg2-rem-badges`. **This layer was never fully folded into staging.** A prior session wrongly believed it had.

A two-scout reconciliation (2026-07-20) produced the canonical map. **READ IT FIRST:**

- **`founder/reports/design-review-2026-07-20/INSIGHTS.md`** ← the cherry-pick map (3 buckets, per-SHA evidence). This is your source of truth for what to recover and what to leave alone.
- `founder/reports/design-review-2026-07-20/CHECKLIST.md` ← the broader design defect list (context; not all of it is in scope for you).

**#1240 already recovered the plaque + gold-★ cluster** (D6/D8 plaque order, D3/D18 gold-★ graph mark, detail typography, plaque rebalance JS, D8 stamp-tint). Those are DONE and live on staging — **do not redo them.**

**Your job is the 5 remaining Bucket-1 items in §3 below.**

---

## 2. Hard boundaries (violating any of these is a failure)

1. **Branch off staging tip, never off a stale design branch.** Start:
   ```
   git fetch origin
   git checkout -b design/ygg2-bucket1-recovery origin/dev/yggdrasil-ii-staging
   ```
   Staging tip at handover time: `66e728736`.
2. **This is a `design/` branch → CI branch-scope allows ONLY `docs/` + `*.md`.** Four of the five fixes are pure `docs/`. Item 4 (D15) touches `scripts/contentEngine/generate_weekly_report.py` — that is a `scripts/` path and **will trip branch-scope**. For item 4 ONLY, either (a) do the doc/template half on this branch and flag the `.py` half for a separate `infra/` or `cli/` branch, or (b) STOP and ask which branch to use. Do not force a scope violation.
3. **Read the emitted `branch` field. NEVER re-introduce client-side branch derivation.** The founder ruling (2026-07-18) DELETED `computeBranch` from the client. If a fix's original commit adds a `branchOf()`/`legendCategory()` resolver, that is the WRONG approach — port the *intent* (read `s.branch` / `ns.branch`) onto the current code, do not paste the old derivation. (This is why several Bucket-2 items are poison — see INSIGHTS.md.)
4. **Do NOT touch anything in Bucket 2 or Bucket 3 of INSIGHTS.md.** Two of them (`93a187916` sampler order, `ecd4f7186` named-grid) will SILENTLY REGRESS shipped fixes with no conflict marker. If you find yourself editing `SAMPLER_RANKS` ordering or `SUITE_LADDER`/`groupHeader` in `named-skills.js`, STOP — you are in the wrong place.
5. **`git cherry-pick <sha>` will usually NOT apply cleanly** — the target files were rewritten by #1235. Port the *intent* by hand onto the current code shape. Use the original commit as a reference for WHAT to change, not as a patch to apply.
6. **Never push to `main`. Never merge anything yourself** — you open a PR; the human merges.
7. **Windows env:** commands run in git bash. If you run any Python, prefix `PYTHONUTF8=1 PYTHONPATH=src`. `docs/js/skill-graph.js` contains a stray non-UTF8 byte — `grep` may report it "binary"; use `grep -a` to search it.
8. **After any JS/CSS/HTML edit, read the file back** to confirm no merged/duplicated lines. Design tokens only — no hardcoded hex (CI guard rejects new hex).

---

## 3. The 5 fixes to recover — VERIFIED still-missing on staging `66e728736`

Each was confirmed absent by direct inspection at handover time. Do them **in this order**, STOP-gating after each.

### Fix 1 — DAG node dot color reads emitted branch (ref SHA `8aa300702`)
- **File:** `docs/js/named-skills.js`
- **Verified current state (line ~228):**
  ```js
  var colorVar = isGhost ? 'var(--muted)' : 'var(--tier-' + (s.type || 'basic') + ', var(--muted))';
  ```
  This reads the **dead `s.type` enum** → unique/suite dots render with the wrong tier color.
- **Intent to port:** color the dot by the **emitted branch**, not `type`. Read `ns.branch` (or `s.branch`) and map branch→token: `standard→--tier-basic`, `suite→--tier-fusion`, `unique→--tier-unique`. Look at how the original `8aa300702` did it (`git show 8aa300702`), then adapt to read the emitted field the way the rest of staging's `named-skills.js` already does (grep the file for `.branch` to match the existing pattern).
- **Scope:** `docs/` only — clean on this branch.

### Fix 2 — Contributor-card header groups handle + rank (ref SHA `e15c7bfae`)
- **File:** `docs/css/plaque.css`
- **Verified current state (line ~2747):**
  ```css
  .contributor-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  ```
- **Intent to port:** group the handle + rank badge together instead of pushing them to opposite edges. The original `e15c7bfae` changed this to `justify-content: flex-start; gap: 10px; flex-wrap: wrap;` and added `.contributor-card-header .rank-badge { margin-left: 0; }`. Verify those exact declarations against `git show e15c7bfae` before applying.
- **Scope:** `docs/` only — clean.

### Fix 3 — Badge claim/README pinned to 1★, decoupled from sampler cycle (ref SHA `18c0dc1a1`)
- **File:** `docs/badges/index.html`
- **Verified current state:** no `CLAIM_RANK` constant exists (`grep -c CLAIM_RANK` → 0). The "Include in README" / claim badge follows the live sampler cycle, so it can leak a higher rank than 1★.
- **Intent to port:** introduce a `CLAIM_RANK` pinned to 1★ and make the claim/README badge use it, so the sampler's cycling does NOT change what the README badge shows. `git show 18c0dc1a1` for the exact mechanism (it defines `CLAIM_RANK = SAMPLER_RANKS.find(r => r.n === 1)` and points `seedSample()` / the claim path at it, and removes a cross-write that repainted `badges` for `gaia-bot`).
- **CAUTION:** `docs/badges/index.html` is a **core page** — a missing/renamed variable blanks ALL badge output. After editing, mentally trace that every variable used in `renderRows()` is still defined. Do NOT touch `SAMPLER_RANKS` ordering (that is Bucket-2 poison — item `93a187916`). You are ONLY adding the claim pin.
- **Scope:** `docs/` only — clean.

### Fix 4 — Reports grey out "← Previous week" when no prior report (ref SHA `55a62ac13`)
- **Files (CORRECTED paths — the SHA touched these):**
  - `scripts/contentEngine/generate_weekly_report.py` ← **`scripts/` path, trips `design/` branch-scope**
  - `scripts/contentEngine/templates/report.html.j2` ← also `scripts/`
  - `docs/reports/2026-28/index.html` ← `docs/`, clean
  - `docs/api/v1/reports/2026-28.json` ← `docs/`, clean
- **Verified current state:** the generator emits a `previous` link unconditionally; `docs/reports/2026-28/index.html` has a live `← Previous week` link that 404s when there is no prior week.
- **Intent to port:** guard the previous-week link — render it greyed/disabled (not a live 404) when no prior report exists.
- **SCOPE CONFLICT — STOP HERE:** this fix spans `scripts/` + `docs/`. A `design/` branch cannot carry the `scripts/` half. When you reach this fix, present the situation and ask: split it (docs half here, scripts half on `infra/`), do the whole thing on a non-`design/` branch, or defer. **Do not force it through.**

### Fix 5 — Remove dev-only `live.js` reload tag (ref SHA `a9f4e3124`)
- **Files:** **48 HTML files** under `docs/` still carry a `<script src="http://localhost:8400/live.js">`-style dev-reload tag. Find them:
  ```
  git grep -l "live.js" origin/dev/yggdrasil-ii-staging -- 'docs/**/*.html'
  ```
- **Intent:** delete that dev-only tag from each. It is pure removal (safe, no logic).
- **CAUTION:** this is 48 files. Treat it as ONE cherry-pick (one STOP-gate for the whole sweep), but show the human the list of files + a sample diff of one before committing. Make sure you are removing ONLY the `live.js` dev tag line, nothing adjacent.
- **Scope:** `docs/` only — clean.

---

## 4. Exact loop to follow (per fix)

For each fix 1→5:

1. **Verify it is still missing** (re-run the check in §3 — state may have changed since handover). If already present → this is a **NO CHANGES** case; report and skip.
2. `git show <ref-sha>` to see the original intent. **Do not blind-apply it.**
3. Port the intent onto the current file(s) by hand.
4. Read the edited file(s) back; confirm no dupes/merged lines; confirm no new hardcoded hex; confirm you did not touch a Bucket-2 surface.
5. **STOP. Present:**
   - which fix, which file(s), the diff (`git diff`), and a one-line "why this matches the intent without re-introducing derivation."
   - Ask explicitly: **APPROVE / REJECT / NO CHANGES?**
6. On the decision:
   - **APPROVE** → `git add <only-those-files>` → one commit `fix(design): <item> — <one-line>` → `git push origin design/ygg2-bucket1-recovery` → report SHA → go to next fix.
   - **REJECT** → `git restore <those-files>` → go to next fix.
   - **NO CHANGES** → touch nothing → go to next fix.
7. Never proceed to the next fix before a decision on the current one.

After all five are resolved: open ONE PR `design/ygg2-bucket1-recovery` → `dev/yggdrasil-ii-staging`. In the PR body, list each fix + its outcome (approved/rejected/no-change), and add a line: "Bucket-2 items from INSIGHTS.md deliberately NOT touched (already fixed differently in #1235)." Then STOP — the human merges.

---

## 5. Sanity references (where to look)

| Need | Path |
|---|---|
| The cherry-pick map (buckets + evidence) | `founder/reports/design-review-2026-07-20/INSIGHTS.md` |
| Design defect context list | `founder/reports/design-review-2026-07-20/CHECKLIST.md` |
| Ygg II design spec / rubric (E1–E7, tokens, plaque medallion) | `DESIGN.md` |
| Nomenclature / banned rank words | `CONTEXT.md` |
| Repo invariants (Class P/S, branch-scope, token rules) | `CLAUDE.md` (repo root) |
| Emitted taxonomy the client reads | `docs/graph/named/index.json` (fields: `branch`, `rankWord`, `level`, `medallion`) |
| Session history / what already shipped | `founder/MEMORY.md` (top two snapshots: 2026-07-20 correction + 2026-07-19) |

**Golden reminder:** you are reading the emitted `branch`, never deriving it. You are recovering 5 specific fixes, never touching Bucket 2/3. You STOP after every single one. If any instruction feels ambiguous, ask — do not improvise.

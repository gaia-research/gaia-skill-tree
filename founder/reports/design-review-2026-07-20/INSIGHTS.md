# Yggdrasil II UI Polish — Marooned-Commit Reconciliation

> **Purpose:** a ground-truth cherry-pick map for the next design pass, so the recoverable design work is applied ONCE, safely, without re-litigating what already landed. Every classification below is verified against `origin/dev/yggdrasil-ii-staging` at tip `ac634b9d9` (the #1235 merge) by two read-only scout passes on 2026-07-20 — file:line evidence, not inference.

## What happened (verified)

The Yggdrasil II work split across two layers on separate branches:

1. **Oracle / taxonomy layer** — `dev/ygg2-consume-frontend` (**PR #1235**). Merged to staging `ac634b9d9` on 2026-07-19. Carried the branch-read rewrites, #7 timeline, origin-gate §4.1 fix, 4 skill restorations, and a 13-ref `--tier-ultimate → --tier-fusion` token migration.
2. **Design-polish layer** — lived on `design/ygg2-deferred-polish`, `design/ygg2-fixforward-superadmin` (PR #1227, **closed unmerged**), and `design/ygg2-rem-badges`. **This layer was never folded into the #1235 → staging path.**

The #1227 close-comment asserted the deferred design items "landed on the #1235 stack." **That was inaccurate.** The plaque *structure* (`_fieldAvatar`/`_fieldHandleRow`) landed with the oracle cut, but the *rebalance*, detail-order, gold-★ graph mark, DAG-dot color, and contributor-card grouping did **not**. This doc corrects that record.

**Why a bulk merge is unsafe:** the design branches were cut from `6c8388ecc` — a point *before* #1235's divergent fixes. So `git merge-tree` reports many changes as clean when they are actually **semantic reversions** or **superseded-by-a-different-architecture**. Merging `design/ygg2-deferred-polish` wholesale would silently undo #1235's ratified sampler order and named-grid approach with **no conflict marker to warn anyone**. Cherry-pick by intent instead — do not merge any stale branch.

---

## Bucket 1 — SAFE to recover (genuinely MISSING; real lost work)

Absent from staging under any SHA. Re-apply the **intent** onto staging's current code shape — the files below were rewritten by #1235, so raw `git cherry-pick` will need adaptation. Treat these as "port," not "apply."

| Fix | Source SHA | Branch | Evidence it's missing from staging |
|---|---|---|---|
| **D6/D8 detail plaque avatar→medallion order** | `6ed132955`, D6 half of `e31f58077` | deferred-polish / fixforward | `plaque.js:663-664` still orders `_fieldOrb(lg)` before `_fieldAvatar(56)`; no `.plaque--detail .plaque-orb--medallion{width:72px}` rule in `plaque.css`. |
| **D3/D18 graph gold ★ origin mark** | `4801e0c13` | fixforward | `skill-graph.js:147-156` STILL has the deprecated `ORIGIN_PATHS` laurel Path2D; `L1697-1719` still strokes it. No `'  ★'` text mark. *(The claimed hand-port did NOT land — staging still renders the laurel.)* |
| **DAG node dot color reads emitted branch** | `8aa300702` | deferred-polish | `named-skills.js:239` still `'var(--tier-' + (s.type\|\|'basic')`. No `branchOf(ns\|\|s)`. Merges additively. Distinct surface from #1235's `12d343968` legend-filter fix. |
| **Contributor-card header groups handle + rank** | `e15c7bfae` | deferred-polish | `plaque.css:2707` `.contributor-card-header` still `justify-content: space-between`; no `flex-start`/`gap`/`flex-wrap`. |
| **Badge claim/README pinned to 1★ (no rank leak)** | `18c0dc1a1` | deferred-polish | `badges/index.html:1925-1926` `seedSample` still reads `SAMPLER_RANKS[samplerIdx]`; no `CLAIM_RANK`. |
| **Plaque rebalance — JS wiring + detail typography** | `f55282253` (JS half only) | deferred-polish | The `.plaque__contributor` CSS grouping landed with #1235, but tile (`plaque.js:575-584`) + settled (`691-705`) still emit avatar-in-header separately; detail typography (line-height 1.1, 68ch, `.plaque-detail-right` gap) absent (`plaque.css:1776-1787`). **CSS scaffolding present; JS + typography missing.** |
| **D15 reports "← Previous week" 404 guard** | `55a62ac13` | fixforward | `generate_weekly_report.py:253` still emits `previous` unconditionally; `reports/2026-28/index.html:364` still a live link. |
| **Remove dev-only `live.js` reload tag** | `a9f4e3124` | fixforward | `git grep live.js` on staging → **48 html files** still carry the `localhost:8400/live.js` dev tag. Applies clean (pure deletion). |

---

## Bucket 2 — DO NOT re-apply (already fixed differently in #1235; re-applying regresses or conflicts)

Staging already solved these via the founder-ratified "read emitted `branch`" architecture (client-side derivation was deliberately deleted, founder ruling 2026-07-18). Applying the marooned commits re-introduces deleted code or reverts a ratified fix.

| Marooned SHA | What it did | Why to skip | Staging's fix |
|---|---|---|---|
| `93a187916` | sampler ascending, extra-before-unique | **SILENT REGRESSION** — flips staging's §8 order back; no conflict marker | `a25b7b026` (descending, unique-before-suite) |
| `ecd4f7186` | named-grid header by removing `SUITE_LADDER` | supersedes a divergent approach; not complementary | `101d2cf42` (`branchOrder` + `withinGroupSort` clustering) |
| `c0def6d62` | D9 client-side `branchOf()` in 3D graph | re-adds deleted client derivation | `12d343968` (reads emitted `skill.branch`) |
| `3555c40da` | D74 client `branchOf()` + subId dedup (count 56) | wrong count + deleted architecture | `6c8388ecc` (emitted `branch==='suite' && rank≥5` = 5, §8) |
| `332736ab0` | D12 badge vocab kill | already done — zero `Hardened`/`Transcendent` in `docs/badges` | present in staging |
| `04d6114d6` | D14 tree.md suites-first | goal PRESENT (tree.md populated, `_sorted_ultimates`); content differs by resolver lineage | present via generateProjections.py |

---

## Bucket 3 — REDUNDANT (abandon; no unique value)

- **`design/ygg2-rem-badges` (`1006e5d75`)** — staging already carries the full outcome: zero banned rank words in `docs/badges`, and the honor-red→origin-gold E4 migration is done (`agent-skills.svg` uses gold `#fbbf24`, no `#ef4444`). Merging only re-conflicts ~219 already-regenerated SVGs. **Safe to close without merging.**

---

## Recommended next design pass

1. Branch off **staging tip** (`ac634b9d9` or later) — never off the stale design branches.
2. Recover **only Bucket 1** (8 fixes), porting intent onto the current code shape. Group by file cluster: plaque (`plaque.js`/`plaque.css`), graph (`skill-graph.js`), named-grid dot (`named-skills.js`), badge claim-pin (`badges/index.html`), reports guard (`generate_weekly_report.py`), live.js sweep.
3. Explicitly **skip Bucket 2** — note in the PR body that these were verified already-fixed/superseded so a future reviewer doesn't re-open them.
4. `design/ygg2-fixforward-superadmin` (already closed) and `design/ygg2-rem-badges` are superseded; keep `design/ygg2-deferred-polish` only as the SHA source for the Bucket-1 ports, then delete.

*Reconciliation verified 2026-07-20 against staging `ac634b9d9` by two read-only scout passes. Supersedes the prior speculative "merge design/ygg2-deferred-polish" remediation.*

# World Tree — Semantic Topology (Hero 2D + 3D Explorer) — v2

> **Version:** v2 · **Changelog:** 2026-07-14 — v2: branch derivation decoupled from `type`; driven by `suiteComponents` + rank; fork at 4★+; Transcendent dropped.
> **Status:** ratified in session (2026-07-12), implementation handover.
> **Target branch:** `design/homepage-gaia-tree-hero` (PR #1125 → `dev/yggdrasil-ii-staging`).
> **Scope:** `docs/` + `*.md` only (design branch scope). No `src/`, no schema, no build-pipeline changes.
> **Meta boundary:** we are in **Yggdrasil I** today; this must be forward-compatible with **Yggdrasil II** (see `founder/handovers/YGGDRASIL_II_RATIFICATION_2026-07-07.md`) with **one function** changed at cutover.

---

## 1. The problem

The hero World Tree currently renders as a canopy *cloud* floating over the painted trunk backdrop: nodes fan out immediately at the ground line, there is no narrow trunk column, no branch forks, and roots/branches do not align to the painted `yggdrasil-backdrop` asset. It reads as a graph, not a tree.

The fix is to make **position mean something** — drive layout from *semantics* (type + effective rank), not from raw graph topology alone — and to give real edges a synthetic wood skeleton to drape over.

---

## 2. The model — two orthogonal axes + a fork

Placement is a **pure function of `(type, effectiveRank, group)`**. No dependence on node count. The 235-node canon graph and a 12-skill single-user tree run the identical function.

### 2.1 The axes

| Axis | Driven by | Meaning |
|---|---|---|
| **Hemisphere** (which pole) | skill **type** | composite (fusion/extra/ultimate) grows **up** into the crown; primitive (basic) grows **down** into the roots |
| **Coreness** (radius from central axis) | **effective rank** (stars) | 6★ = heartwood center (radius 0), falling outward: 5★ near-core → 4★ mid → 3★ sapwood → 2★ tips → 0–1★/unranked = outermost bark & twigs |
| **Bough angle** (rotation) | **group** | `cluster` today (Yggdrasil II grouping later). Golden-angle distributed, stable per group. |

Rank pulls everything toward one shared center **from both poles**; type decides whether you approach that center from above (crown) or below (roots). Promotion = motion **inward toward the heartwood** (the built-in single-user "Hero's Journey" animation hook — not built this PR, but the model must allow it).

### 2.2 The Y-fork — Uniques render OUTSIDE the tree

**Ratified correction (2026-07-12): Uniques are NOT graph-isolated.** They participate in the DAG like anything else (they may carry prereqs and grafts). But the **resolver** pulls them to a separate **dark constellation beside the trunk** — "standing stones beside the tree." This is a *render* decision, not a topology constraint.

- Few uniques exist → a small dark grove reads as intentional.
- **Single side** of the trunk (asymmetric offset), not mirrored — scattered symmetric points read as noise.
- **Distinct, much darker palette** — visually off the wood, not woven into it.
- Detection differs by meta (see §3 table) but the *placement* (outside, single-side, dark) is identical across both metas.

### 2.3 The silhouette (bottom to top)

```
                    ◆ 6★ Apex       ← Suite crown-core (canopy heartwood)
                   /          \
              5★ Ultimate    Y-fork at 4★
             (suite→inward)      \
        4★ Extra ── CORE ──────  ◉ dark Unique grove
         (converge   ▓▓▓            (single side, outside the wood,
          inward)   heartwood        darker palette, own stems)
            |        5–6★
        3★ sapwood    |
        2★ tips       |
     ~~~~~~~~~~~~~~~~~~╪~~~~~~~~~~~ ground line (trunk collar)
        basics = roots (0★, unranked at root-hairs; 2★ root-tips; toward taproot core as rank rises)
                    ▓ taproot heartwood ▓  ← reserved for future 6★ (none today) — iconic when it exists
```

---

## 3. Compatibility layer — the resolver (THE load-bearing seam)

**The layout engine must never learn which meta it is in.** One function maps both vocabularies onto a **frozen output contract**. Everything meta-aware lives here and nowhere else.

```
resolveSemantics(node, effectiveRank) → {
  hemisphere: 'crown' | 'root' | 'outside',
  coreness:   0..1,          // 1 = heartwood center, 0 = outer surface
  isUnique:   boolean,       // → dark constellation, single side
  isSuite:    boolean,       // → crown-core convergence
  glyph:      '○'|'◇'|'◉'|'◆',
  boughGroup: <group key>
}
```

### 3.1 Read table (both metas)

| Ygg I `type` | Ygg II `type` | Hemisphere | Structural class → glyph | Detection that differs by meta |
|---|---|---|---|---|
| `basic` | `basic` | **root** | ○ basic | — |
| `extra` | `fusion` | **crown** | ◇ fusion | — |
| `ultimate` | `fusion` | **crown** | ◆ suite | I: `type==='ultimate'` · II: `suiteComponents` present |
| `unique` | `basic` | **outside** | ◉ unique | I: `type==='unique'` · II: `effRank≥4★ && !suiteComponents` |

> **Orthogonality (v2):** Type and Branch are orthogonal. `type` (basic|fusion) is pure structural metadata — a starless/generic node is `fusion` iff it has prerequisites — and is NEVER consulted for branch. Branch is driven solely by `suiteComponents` presence and rank. In practice fusion and suiteComponents usually coincide, but they are independent fields: a `fusion` node with no `suiteComponents` is Unique branch, and a `basic` node carrying `suiteComponents` is Suite branch. `suiteComponents` remains an input to downstream Trust Magnitude computation as well.

### 3.2 Read order (critical)

1. **Detect `isUnique` first → hemisphere `outside`.** (This is why a Ygg II Unique — identified by `effRank≥4★ && !suiteComponents`, not `type` — does NOT fall into roots; the short-circuit fires before the hemisphere-by-type step.)
2. Detect `isSuite`.
3. Hemisphere by type (`basic`→root, `fusion`/`extra`/`ultimate`→crown).
4. `coreness` = normalized effective rank (see §4).
5. `boughGroup` = `cluster` (Ygg I) — leave a comment that Ygg II grouping swaps here.

### 3.3 Meta detection — feature-check, not a flag

```
metaIsYggI = nodes.some(n => n.type !== 'basic' && n.type !== 'fusion')
```

If any node's `type` ∉ {basic, fusion} → Yggdrasil I read column; else Yggdrasil II. **No config, no version flag, no dead code after cutover.** The day the migration script runs, the graph starts reading the right-hand column with zero layout change.

### 3.4 The invariant

`coreness` (from effectiveRank), `hemisphere`, `isUnique`, `isSuite`, `glyph` are the **only** meta-touched values, and they are **all confined to `resolveSemantics`**. Geometry, edge routing, the armature, and color all consume the output contract and never change across the meta boundary. **At Ygg II cutover, exactly one function is edited.**

---

## 4. Effective rank — runtime join (design-branch-safe)

The hero graph `docs/graph/gaia.json` is the **starless** graph: `type ∈ {basic, extra, ultimate}` and **`level` is `null` on every node** (correct per META.md §1 — stars live on named skills only).

Effective rank must be **joined at runtime in JS** (NOT baked into the artifact — that would be a build-pipeline change, out of scope for a `design/` branch, and `world-tree-layout.js` must stay a pure function):

- `docs/graph/named/index.json` has a `buckets` object keyed by `genericSkillRef`. Each bucket is a list of named children; each child carries `"level": "2★"` (star-glyph string).
- **Effective rank of a starless node = max star among its named children** (parse the `N★` string; `0` if no named children or all ≤1★).
- The named index is **already fetched** by `named-skills.js` — reuse that load path; do not add a new fetch. The join happens in the loader/adapter, augmenting each node with `effectiveRank` **before** it is handed to `world-tree-layout.js`.
- Redaction: 0–1★ (incl. redacted Awakened) → coreness 0 (outer surface). Colored ramp starts at **2★ Named**. This respects the existing redaction cutline.

`coreness = clamp(effectiveRank / 6, 0, 1)` (tune the curve for visual spread — a slight `pow` may read better; leave a tunable constant).

---

## 5. The synthetic ghost armature

**Structure must not depend on the data it organizes.** A well-populated registry could have zero starless nodes; an armature made of real data would then vanish. So the armature is **synthetic, always present, data-independent.**

Layers, bottom to top:

1. **Ghost armature** (synthetic, faint, always present): trunk spine (ghost waypoints up the `x≈0` axis from root-collar to crown apex) + **bough anchors** (fork points branching off the spine at rising heights, golden-angle directions, one sub-level of recursion) + **root anchors** (mirror below the collar) + **reserved taproot** point (for future 6★).
2. **Real nodes** attach to the nearest armature anchor consistent with their `hemisphere`, at radial offset `(1 − coreness) × boughReach`. Topology does the *fine* arrangement (which fork, order along branch, stay near prereq parent); semantics set the silhouette.
3. **Edge re-routing:** a node's **structural** edge (already identified by `structuralEdgeKeys` in the layout) flows `node → its bough anchor → down the spine → root`, draping over the skeleton. Non-structural prereqs (grafts) stay as the current faint direct arcs.

### 5.1 Ghost invariants (NON-NEGOTIABLE)

Ghost waypoints carry **NO data** and must be excluded at **every** seam:

- NOT in `result.nodes`, NOT in the exported/normalized DAG, NOT in `result.edges`.
- NOT counted in any skill/edge/node count (`edgeCount`, stat blocks, etc.).
- NO hover, NO labels, NO pins, NO click targets, NO projected-node registration for interaction.
- Tagged `ghost: true` in the pose maps only, and rendered as faint organic mesh (they make boughs read as branches, and give unique spires visible stems).

### 5.2 Borrow-from-C: pin the spine to the backdrop

Pin the trunk-spine's x-position and ground-line to a **single tuned constant** matching where the painted `yggdrasil-backdrop` trunk sits (with its CSS transform: `translate 22%`, `scale 1.2`, `heroCenterRatio 0.72`). This is a constant, **not** a full raster trace — an asset swap becomes a one-line retune, not a rework.

---

## 6. Color & glyph re-axis (3D explorer)

Two types (basic/fusion) make type-color boring. **Move color to rank** (which is also meta-invariant — stars are stars in both metas, so this ships now and survives cutover untouched). **Demote type to glyph** (don't lose it — re-axis it).

- **Color = effective rank.** Grey (0–1★) → colored ramp from 2★ → apex-gold 6★. Use existing tokens `--rank-0 … --rank-6` / `-bg` / `-border` / `-edge` (already in `skill-graph.js` `_readVar`). **No hex fallbacks** (CI guard).
- **Glyph = structural class** (○ basic · ◇ fusion · ◉ unique · ◆ suite) — symbols from META.md §1.2.
- **Node radius** keyed to rank too (bigger = more proven) — partly already true via `NODE_RADII`.
- **Starless real nodes = grey** — extends the existing convention (META.md §1 "generic renders greyed-out"; explorer already tags `data-ghost="true"`). They land at outer radius automatically (coreness 0) — no special-case bucket.
- **Unique constellation = distinct dark palette**, separate from the rank ramp.

### 6.1 Legend + hover (the biggest surface)

The explorer legend flips from a 4-type color key to **a rank ramp + a small glyph key**. Hover cards must show rank (color) and structural class (glyph) as two channels. This is the largest single change — budget for it. In scope (`docs/`).

---

## 7. Hero vs Explorer split

| | Hero (2D editorial) | 3D Explorer (the reveal) |
|---|---|---|
| Rank | **positional only** (drives coreness/placement) | **full expression** — color, radius, glow |
| Starless tips | **faint GOLD foliage** (part of monochrome silhouette; NO grey — grey muddies the mono hero) | grey ○ + colored ramp |
| Palette | single-gold editorial | full rank ramp + dark unique grove |
| Goal | clean, iconic tree silhouette | "wow — and it makes sense" |

The hero stays clean and monochrome-gold; the explorer is where rank/color/glyph all light up.

---

## 8. Definition of done (operator-ratified)

1. **Hero 2D shows as a tree** — trunk column, branch forks, roots align to the backdrop; not a floating canopy cloud.
2. **3D graph shapes like a tree** with the correct layering (armature → real nodes → unique grove) and **color-by-rank + glyph-by-type**.
3. **Compatibility kicks in** — reads correctly under Yggdrasil I today (feature-detect), one-function swap for Ygg II.
4. **Performance is good and optimized** — no per-frame allocation regressions; armature/join computed once, not per-frame; large-graph (235-node) frame budget held. Measure before/after.

---

## 9. Constraints & known gotchas (READ BEFORE EDITING)

- **Branch scope:** `design/*` → `docs/` + `*.md` ONLY. Do not touch `src/`, `registry/`, schema, or build pipeline. If you regenerate `docs/graph/*` or `registry/gaia.json` as a side effect, **revert those files** before committing (they're Class P/S artifacts, separate concern).
- **`skill-explorer.js` is TWO IIFEs** that do not share scope (CLAUDE.md). Anything shared must be re-declared per IIFE or hung off `window`. Wrap render calls in `_safeRender`.
- **`skill-graph.js` bootstrap guard:** null-check any `querySelector(...).addEventListener` at module bootstrap or the whole IIFE silently aborts to `FALLBACK_SKILLS`.
- **No hex colors** — design tokens only (CI guard rejects hex).
- **Cache-busting:** if any new asset/version string is needed, do NOT hand-patch `?v=`; that's pipeline (`build_docs.py`) — out of scope. Reuse existing loaded assets.
- **Verify after edits:** load `http://localhost:8080/` (hero) and the 3D explorer; confirm tree silhouette + colors + no console errors; confirm named/ explorer still renders all five sections.
- **Determinism:** all placement uses `stableHash` / golden-angle — existing nodes must not move when new ones are added. No `Math.random()`, no `Date.now()` in layout.

---

## 10. Work breakdown (sub-agents)

- **Agent 1 — Layout engine + resolver** (`docs/js/world-tree-layout.js` + `tests/`): `resolveSemantics` with the §3 compat table, synthetic armature (§5), coreness-by-rank (§4 contract — engine receives `effectiveRank` on nodes), unique-outside single-side, structural-edge re-routing over the spine. **Freezes the output contract.** Pure function, deterministic. Extend `tests/test_world_tree_layout.py` + `tests/world-tree-layout.test.js`.
- **Agent 2 — Render integration** (`docs/js/skill-graph.js`, `docs/js/named-skills.js` loader join, `docs/css/`): runtime rank-join (§4), ghost armature render, unique dark-spire render, color→rank / type→glyph re-axis + legend/hover (§6), hero-vs-explorer split (§7), performance pass (§8.4). Consumes Agent 1's contract.
- **Agent 3 — Docs** (`docs/` mechanics note + `DESIGN.md`): short design-model note for the shipped mechanics (NOT the full single-user-tree model — that's a later PR); rank-color + glyph token notes in `DESIGN.md`.

All work lands on `design/homepage-gaia-tree-hero`. Any additional PRs merge INTO this design branch, never main/staging directly.

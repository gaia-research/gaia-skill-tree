# World Tree — Design Model (Semantic Topology)

**Status:** Ratified 2026-07-12 — implementation handover for PR #1125.
**Spec:** `founder/handovers/design-v6.1.1-world-tree-semantic-topology.md`
**Target branch:** `design/homepage-gaia-tree-hero`
**Cross-refs:** `DESIGN.md` §World Tree Color and Glyph Re-axis, `META.md §1.1` (rank names), `docs/js/world-tree-layout.js` (layout engine), `docs/js/skill-graph.js` (render integration), `docs/js/named-skills.js` (rank join load path)

---

## Overview

Layout is a **pure function of `(type, effectiveRank, group)`** — no dependence on node count. The 235-node canon graph and a 12-skill single-user tree run the identical function. This makes the model deterministic, testable, and forward-compatible with the Yggdrasil II type schema without any flag or dead code.

---

## Two-Axis Model

Placement derives from two orthogonal axes plus a bough distribution rule:

| Axis | Input | Meaning |
|---|---|---|
| **Hemisphere** (which pole) | structural class | composite (fusion/suite) grows **up** into the crown; primitive (basic) grows **down** into the roots |
| **Coreness** (radius from central axis) | **effective rank** (stars) | 6★ = heartwood center (coreness 1.0); 0–1★ = outermost bark and twigs (coreness 0) |
| **Bough angle** (rotation) | **group** | golden-angle distributed, stable per group; `cluster` field under Ygg I — a comment in `resolveSemantics` marks where Ygg II grouping plugs in |

Coreness formula: `coreness = clamp(effectiveRank / 6, 0, 1)` (a slight `pow` curve may improve visual spread; leave a tunable constant). Rank pulls both crown and root nodes toward the shared heartwood center from their respective poles — promotion is motion inward, the built-in Hero's Journey animation hook (not built this PR, but the model must allow it).

---

## Y-Fork — Uniques Render Outside the Tree

Uniques participate in the DAG like any other node (they carry prereqs and grafts). The **resolver** places them in a **dark constellation beside the trunk** — standing stones, not part of the wood. Key invariants:

- **Single side** of the trunk (asymmetric offset) — scattered symmetric points read as noise.
- **Distinct dark palette** — visually off the wood, separate from the rank-color ramp.
- Few uniques exist; a small dark grove reads as intentional.

This is a render decision, not a topology constraint. Detection differs by meta (see the read table below); placement is identical across both.

---

## Synthetic Ghost Armature

> Structure must not depend on the data it organizes.

The armature is **synthetic, always present, data-independent**. A well-populated registry could have zero starless nodes; an armature built from real node positions would vanish. The armature provides the skeleton that real nodes and edges drape over.

Layers (bottom to top):

1. **Ghost armature** — trunk spine (ghost waypoints up the `x≈0` axis from root-collar to crown apex), bough anchors (fork points off the spine at rising heights, golden-angle directions, one sub-level of recursion), root anchors (mirror below the collar), reserved taproot point for a future 6★.
2. **Real nodes** attach to the nearest anchor consistent with their hemisphere, at radial offset `(1 − coreness) × boughReach`. Topology does the fine arrangement (which fork, order along branch, proximity to prereq parent); semantics set the silhouette.
3. **Edge re-routing** — a node's structural edge flows `node → bough anchor → spine → root`, draping over the skeleton. Non-structural prereqs (grafts) stay as faint direct arcs.

### Ghost invariants (non-negotiable)

Ghost waypoints carry NO data and must be excluded at every seam:

- NOT in `result.nodes`, NOT in the exported DAG, NOT in `result.edges`.
- NOT counted in any node/edge stat (`edgeCount`, stat blocks, etc.).
- NO hover, NO labels, NO pins, NO click targets, NO projected-node registration.
- Tagged `ghost: true` in the pose maps only; rendered as faint organic mesh.

The trunk spine x-position and ground-line are pinned to a **single tuned constant** matching the `yggdrasil-backdrop` CSS transforms (`translate 22%`, `scale 1.2`, `heroCenterRatio 0.72`). An asset swap retunes one constant.

---

## `resolveSemantics` Compatibility Seam

**The layout engine never learns which meta it is in.** All meta-aware logic lives in one function. Everything geometry, edge routing, and color/glyph consumes the output contract — none of it changes across the meta boundary.

```
resolveSemantics(node, effectiveRank) → {
  hemisphere: 'crown' | 'root' | 'outside',
  coreness:   0..1,          // 1 = heartwood center, 0 = outer surface
  isUnique:   boolean,       // → dark constellation, single side
  isSuite:    boolean,       // → crown-core convergence
  glyph:      '○' | '◇' | '◉' | '◆',
  boughGroup: <group key>
}
```

### Read table (Ygg I ↔ Ygg II)

| Ygg I `type` | Ygg II `type` | Hemisphere | Structural class → glyph | Meta-detection |
|---|---|---|---|---|
| `basic` | `basic` | root | ○ basic | — |
| `extra` | `fusion` | crown | ◇ fusion | — |
| `ultimate` | `fusion` | crown | ◆ suite | I: `type==='ultimate'` · II: `suiteComponents` present |
| `unique` | `basic` | outside | ◉ unique | I: `type==='unique'` · II: `type==='basic' && effRank≥4★ && !suiteComponents` |

### Read order (critical)

1. **Detect `isUnique` first → `hemisphere: 'outside'`** (short-circuits before the hemisphere-by-type step; this is why a Ygg II Unique whose `type=basic` does NOT fall into roots).
2. Detect `isSuite`.
3. Hemisphere by type (`basic`→root, others→crown).
4. `coreness` = normalized effective rank.
5. `boughGroup` = `cluster` (Ygg I); leave a comment that Ygg II grouping swaps here.

### Meta feature-detect (no config flag)

```js
const metaIsYggI = nodes.some(n => n.type !== 'basic' && n.type !== 'fusion');
```

If any node's `type` is not `basic` or `fusion`, read the Ygg I column; else read the Ygg II column. No config, no version flag, no dead code after cutover. At Ygg II cutover, **exactly one function** (`resolveSemantics`) is edited.

---

## Runtime Effective-Rank Join

`docs/graph/gaia.json` is the **starless** graph: `level` is `null` on every node (correct per META.md §1 — stars live on named skills only). Effective rank is **joined at runtime in JS**, not baked into the artifact (baking it would be a build-pipeline change, out of scope for `design/` branches, and `world-tree-layout.js` must remain a pure function).

Join mechanics:

- `docs/graph/named/index.json` has a `buckets` object keyed by `genericSkillRef`; each bucket lists named children with `"level": "N★"` strings.
- **Effective rank = max star among a node's named children** (parse the `N★` string; 0 if no named children or all ≤1★).
- The named index is **already fetched** by `named-skills.js` — reuse that load path. Do not add a new fetch. The join augments each node with `effectiveRank` before it is passed to `world-tree-layout.js`.
- Redaction: 0–1★ → coreness 0 (outer surface). The colored rank ramp starts at **2★ Named**, respecting the existing redaction cutline.

---

## Hero vs. Explorer Split

| | Hero (2D editorial) | 3D Explorer (the reveal) |
|---|---|---|
| Rank signal | **positional only** — drives coreness/placement | full expression: color, radius, glow |
| Starless tips | faint gold foliage (monochrome silhouette; no grey — grey muddies the mono hero) | grey ○ + colored ramp |
| Palette | single-gold editorial | full rank ramp + dark unique constellation |
| Goal | clean, iconic tree silhouette | "wow — and it makes sense" |

The hero stays monochrome-gold; the explorer is where rank/color/glyph all light up. See `DESIGN.md` §World Tree Color and Glyph Re-axis for the token assignments.

---

## Single-User Tree (Future Extension)

The pure-function design enables a single-user tree (12–50 skills) to run the identical layout path. The runtime rank join and `resolveSemantics` already accommodate sparse graphs. The full single-user-tree rendering surface — Hero's Journey animation, promotion motion inward — is explicitly deferred to a later PR.

---

## Cross-References

- `founder/handovers/design-v6.1.1-world-tree-semantic-topology.md` — ratified spec (source of truth)
- `DESIGN.md` §World Tree Color and Glyph Re-axis — rank-color and structural-class glyph token assignments
- `META.md §1.1` — rank names and star counts
- `docs/js/world-tree-layout.js` — layout engine (Agent 1 deliverable; `resolveSemantics` lives here)
- `docs/js/skill-graph.js` — render integration (Agent 2 deliverable; rank join and re-axis)
- `docs/js/named-skills.js` — named index load path; rank join is piggybacked here
- `docs/architecture/benchmark-framework.md` — companion architecture note (evidence methodology)

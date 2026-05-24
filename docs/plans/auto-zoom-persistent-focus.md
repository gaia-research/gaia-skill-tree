# Plan: Auto-Zoom and Persistent Focus for Gaia Graph

## Goals
- **Auto-zoom**: When a skill node is clicked, the view should automatically zoom to fit the bounding box of that node and its relevant connections (prerequisites and dependents).
- **Persistent focus**: Clicking a node keeps it visually highlighted until the user clicks on empty canvas (outside any node).

## Current Behavior (baseline)

- Hover temporarily highlights a node and its immediate neighbors (prerequisites and skills that depend on it).
- Dragging orbits the 3D view; mouse wheel zooms.
- Reset button clears filters (type/rank/search) but does **not** reset orbit, zoom, or focus.
- No persistent selection — highlighting disappears when mouse moves away.

## Architecture Overview

The graph is rendered as an interactive HTML/Canvas application embedded in `src/gaia_cli/graph.py` via the `render_html` function. Key JavaScript components:

- **State object**: tracks `skills`, `positions`, `orbitX/Y`, `zoom`, `hoveredId`, etc.
- **Projection**: `project(p)` converts 3D → 2D using current `zoom`, `width/height`, and field-of-view.
- **Draw loop**: computes visibility (`nodeAlphas`), draws edges, nodes, labels, and tooltip.
- **Neighbor highlighting**: built from `hoveredId` only.

## Proposed Changes

### 1. State Extensions

Add persistent focus fields plus a camera offset used to center the focused bounding box:

```js
focusedId: null,          // Persistent focused node ID (null = none)
potentialClickId: null,   // Captured at mousedown to detect click target
panX: 0,                  // Screen-space auto-pan for focused bbox
panY: 0,                  // Screen-space auto-pan for focused bbox
```

Update `project(p)` so zoom and pan are both applied:

```js
return {
  sx: state.width / 2 + p.x * dist * z + state.panX,
  sy: state.height / 2 + p.y * dist * z + state.panY,
  scale: dist * z,
};
```

Reason: zoom-only fitting is inherently conservative when the selected cluster is off-center. Centering the bbox with `panX/panY` lets the graph zoom closer without clipping.

### 2. Mouse Event Handling

**`handleMouseDown`** – capture the node under the cursor before hover clears:

```js
state.potentialClickId = state.hoveredId;
state.dragging = true;
state.dragMoved = false;
...
state.hoveredId = null;
```

**`handleMouseUp`** – distinguish drag end vs. click; on click, set focus and trigger auto-zoom; on empty click, clear focus:

```js
function handleMouseUp() {
  if (!state.dragging) return;
  const wasDrag = state.dragMoved;
  state.dragging = false;
  state.dragMoved = false;

  if (wasDrag) {
    // nothing to do
  } else {
    // Click (no drag)
    if (state.potentialClickId) {
      state.focusedId = state.potentialClickId;
      fitBoundingBoxForFocusedNode();
    } else {
      // Click on empty space clears focus
      state.focusedId = null;
      state.panX = 0;
      state.panY = 0;
    }
  }
  canvas.style.cursor = state.hoveredId ? 'pointer' : 'default';
}
```

### 3. Unified Highlighting Logic

Replace the current hover-only `neighborSet` block with:

```js
const highlightRoot = state.focusedId !== null ? state.focusedId : state.hoveredId;
const isHighlighting = Boolean(highlightRoot);
const neighborSet = new Set();
if (highlightRoot) {
  neighborSet.add(highlightRoot);
  const rootSkill = state.skills.find(s => s.id === highlightRoot);
  if (rootSkill) {
    rootSkill.prerequisites.forEach(pid => neighborSet.add(pid));
    state.skills.forEach(s => {
      if (s.prerequisites.includes(highlightRoot)) neighborSet.add(s.id);
    });
  }
}
```

Then adjust downstream uses:

- Node visibility: `if (isHighlighting) { targetVis = skill.id === highlightRoot ? 1.0 : neighborSet.has(skill.id) ? 0.88 : 0.12; }`
- Edge highlighting: `const isNeighborEdge = isHighlighting && neighborSet.has(edge.from) && neighborSet.has(edge.to);`

### 4. Auto-Zoom and Auto-Center to Bounding Box

**New helper: `fitBoundingBoxForFocusedNode()`**

This function computes a zoom level and screen-space pan that tightly frames the focused node and its direct graph neighborhood. The previous zoom-only strategy can look underzoomed because it must keep an off-center bbox inside the viewport without moving its center. The revised plan both scales and centers the bbox.

Algorithm:
1. Gather IDs: focused node ID ∪ `getNeighborSet(focusedId)`.
2. For each ID, get its base 3D position `p0 = state.positions[id]`.
3. Apply current rotation (`state.orbitX`, `state.orbitY`) using `rotY` then `rotX`.
4. Compute the projection factor `dist = fov / (fov + p_rot.z + 360 * SCALE)`.
5. Compute screen coordinates at `zoom = 1`:  
   `x = p_rot.x * dist`  
   `y = p_rot.y * dist`  
   Keep these as center-relative coordinates, not viewport coordinates.
6. Determine `minX, maxX, minY, maxY` across all points.
7. Calculate `contentW = maxX - minX`, `contentH = maxY - minY`.
8. Desired padding: 6% per axis, so selected content may occupy roughly 88% of the viewport. This is intentionally more aggressive to avoid the underzoomed feel.  
   `availableW = state.width * 0.88`  
   `availableH = state.height * 0.88`
9. Target zoom = `Math.min(availableW / contentW, availableH / contentH)`.
10. Clamp: `targetZoom = Math.max(0.3, Math.min(3.0, targetZoom))`.
11. Compute bbox center after zoom:  
    `centerX = ((minX + maxX) / 2) * targetZoom`  
    `centerY = ((minY + maxY) / 2) * targetZoom`
12. Assign camera state:  
    `state.zoom = targetZoom`  
    `state.panX = -centerX`  
    `state.panY = -centerY`

Edge: if `contentW` or `contentH` is very small, use a minimum bbox size (`80px` center-relative pre-zoom) instead of skipping. This makes single-node or nearly vertical/horizontal neighborhoods zoom in to a useful close view.

Recommended implementation shape:

```js
function fitBoundingBoxForFocusedNode() {
  if (!state.focusedId) return;
  const ids = Array.from(getNeighborSet(state.focusedId));
  const fov = Math.min(state.width, state.height) * 0.75;
  const points = ids.map(id => {
    const p0 = state.positions[id];
    if (!p0) return null;
    const p = rotX(rotY(p0, state.orbitY), state.orbitX);
    const dist = fov / (fov + p.z + 360 * SCALE);
    return { x: p.x * dist, y: p.y * dist };
  }).filter(Boolean);
  if (!points.length) return;

  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  points.forEach(p => {
    minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
    minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y);
  });

  const minSize = 80;
  const contentW = Math.max(maxX - minX, minSize);
  const contentH = Math.max(maxY - minY, minSize);
  const targetZoom = Math.max(0.3, Math.min(3.0, Math.min(
    state.width * 0.88 / contentW,
    state.height * 0.88 / contentH
  )));
  state.zoom = targetZoom;
  state.panX = -((minX + maxX) / 2) * targetZoom;
  state.panY = -((minY + maxY) / 2) * targetZoom;
}
```

Optional stronger zoom if this still feels too loose: raise `0.88` to `0.94` and the max clamp from `3.0` to `4.0`.

### 5. Visual Focus Indicator

After all nodes are drawn, draw a white ring around the focused node:

```js
if (state.focusedId) {
  const skill = state.skills.find(s => s.id === state.focusedId);
  const pr = state.projectedNodes[state.focusedId];
  if (skill && pr) {
    const p0 = state.positions[skill.id];
    const pulse = 0.84 + 0.16 * Math.sin(state.t * 2.2 + (p0 ? p0.phase : 0));
    const baseR = skill.type === 'ultimate' ? 12.5 : skill.type === 'extra' ? 6.9 : 3.5;
    const r = baseR * SCALE * pr.scale * pulse + 5; // 5px beyond glow
    ctx.beginPath();
    ctx.arc(pr.sx, pr.sy, r, 0, Math.PI * 2);
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2.5;
    ctx.stroke();
  }
}
```

Place this after the `nodes.forEach` drawing loop and before label rendering.

### 6. Helper Extraction (optional but clean)

Define `getNeighborSet(nodeId)` returning a `Set` to avoid duplicating neighbor logic between `draw()` and `fitBoundingBoxForFocusedNode`.

```js
function getNeighborSet(nodeId) {
  const set = new Set([nodeId]);
  const skill = state.skills.find(s => s.id === nodeId);
  if (skill) {
    skill.prerequisites.forEach(pid => set.add(pid));
    state.skills.forEach(s => {
      if (s.prerequisites.includes(nodeId)) set.add(s.id);
    });
  }
  return set;
}
```

Use this in both places.

## Files Modified

- `src/gaia_cli/graph.py` — only the `render_html` function's embedded JavaScript.  
  No Python-side changes required; the generated HTML artifact inherits the new behavior.

## Verification & Testing

1. Regenerate the graph:
   ```bash
   gaia graph --no-open   # or: python -m gaia_cli graph
   ```
2. Open `registry/render/gaia.html` manually.
3. **Test auto-zoom**: Click any node. The view should smoothly (instantly) zoom so that the node and its immediate neighbors occupy most of the viewport.
4. **Test persistent focus**: The clicked node (and neighbors) should stay brightly visible; other nodes dimmed. Move mouse away — highlight remains.
5. **Test unfocus**: Click on empty background. Highlight should clear; all nodes return to normal intensity.
6. **Test focus change**: Click a different node. Focus moves to new node; zoom adjusts to fit the new cluster.
7. **Test drag during focus**: Drag to orbit. Focus remains on the node after orbit.
8. **Test filters**: Apply type/rank filters; focus still works; zoom may include invisible nodes (acceptable).
9. **Reset button**: Should continue to clear filters without affecting focus or zoom (consistent with current behavior).
10. **Wheel zoom** still works normally; can zoom in/out from a focused view.

No automated test changes needed; the Python tests in `tests/test_graph.py` still pass as they validate artifact generation only.

## Edge Cases & Decisions

- **Single-node cluster**: uses an `80px` minimum bbox so it still zooms in instead of doing nothing.
- **Zoom limits**: clamped to [0.3, 3.0] initially. If visual testing still feels underzoomed, use [0.3, 4.0] and `0.94` viewport fill.
- **Filters active**: zoom calculation includes all neighbor nodes even if filtered (they remain dimmed but space is reserved). This avoids jarring zoom jumps when filters toggle.
- **Focus during animation**: no special handling; state updates are immediate and picked up by the next draw frame.
- **Performance**: neighbor set operations are O(N) but with small node counts (<~500) no issue.

## Summary of Code Touches

- Modify `state` initialization (add `focusedId`, `potentialClickId`, `panX`, `panY`).
- Update `project(p)` to add screen-space pan after zoom.
- Update `handleMouseDown`, `handleMouseUp`.
- Add `getNeighborSet` helper.
- Replace neighbor-building in `draw()` with `highlightRoot` logic.
- Add `fitBoundingBoxForFocusedNode` function that sets both zoom and pan.
- Insert focus-ring drawing after node loop.

All changes are confined to the JavaScript payload inside `render_html` in `src/gaia_cli/graph.py`.

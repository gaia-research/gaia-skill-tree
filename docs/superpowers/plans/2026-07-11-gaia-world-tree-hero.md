# Gaia World Tree Hero — Shape and Implementation Brief

> **Status:** Approved direction for `design/homepage-gaia-tree-hero`, targeting `dev/yggdrasil-ii-staging`.
> This rendition is the visual expression of the ratified Yggdrasil II meta. It readies the frontend for that meta without implementing its schema, migration, Fusion, or new Unique branches.

## Outcome

The homepage opens on an unmistakable **Gaia Skill Tree**: a full-viewport, gold Yggdrasil/sakura silhouette generated from the complete live skill DAG. Approved Yggdrasil artwork provides fine bark and root atmosphere behind the graph; the live nodes and all canonical edges remain the semantic tree and the only interactive layer. It is one graph and one topology in two states—not a decorative tree beside the old constellation.

- **Hero:** front-facing, visually 2D, pure gold, editorial, non-interactive except for its entry control.
- **Tree Explorer:** the same nodes and edges smoothly gain depth, true rank colors, orbit controls, hover behavior, and collection tools in fullscreen.
- **Exit:** the same objects return to their gold values and front-facing coordinates while the fullscreen canvas contracts into the hero. Never crossfade between two renderers.

“Field view” is deprecated. Replace that label with **Explore in 3D** and make `?tree=1` canonical. Keep `?field=1` and `?hud=1` only as compatibility aliases to the same Tree Explorer.

## Hero composition and copy

- Preserve `#hero`, `#canvas3d`, generator-owned curation markers, live ledger IDs, and the existing page/rail section order.
- Typeset the exact H1 **Gaia Skill Tree**. Keep the current manifesto as a smaller registry oath: “Skills are catalogued. Names are earned. Apex is rare.”
- Supporting copy: “An evidence-backed registry of agent capabilities, grown from public provenance.”
- Primary CTA: **Install Gaia CLI** → new `#install-cli` anchor on Path A step I.
- Secondary CTAs: **Push your repo** → new `#push-for-review` anchor on Path A step IV; **Claim badges** → `badges/`.
- Keep the live Skills / Named / Ultimates / Updated ledger at the roots. Do not replace Ultimates with link count or prematurely relabel it Apex.
- Keep Trust Ledger and Curation discoverable as restrained root-level utilities.
- Desktop is asymmetric: copy left, tree dominant right. Mobile stacks the gold tree over copy with no horizontal overflow; the fullscreen 3D explorer remains touch-operable.

## One dynamic World Tree

Create a pure layout layer consumed by the existing single-canvas graph controller. It reads `docs/graph/gaia.json` at runtime and exposes `setGraph(next)` so intake PRs can add nodes and prerequisite edges without renderer edits or hand-authored coordinates.

1. Normalize IDs and canonical prerequisite edges; reject missing references individually and never invent links.
2. Find weak components and topologically rank each DAG using actual depth—no hardcoded node, edge, layer, cluster, or tier counts.
3. Shape the largest component into root flare → narrow trunk → rounded crown → high tip. Stable golden-angle branch bases and three deterministic sub-bough slots distribute any cluster count without a hand-authored branch ceiling.
4. Place smaller connected components as deterministic side groves and isolates as visibly disconnected golden seeds. Never draw fake trunk connections.
5. Produce a canonical 3D coordinate per node. Its `x/y` front projection forms the 2D tree; deterministic `z` separates bough volume and collisions.
6. Keep surviving nodes stable across `setGraph()` calls, interpolate added/moved nodes from their parent/child barycenter, and recompute only affected components/closures where practical.

Choose one real structural parent edge per non-root node to form readable wood; render all other real edges as quieter grafts. Every canonical edge still renders exactly once as a curved branch. Terminal nodes may resolve as restrained five-petal sakura buds. Decorative roots, bark, and blossoms must never be mistaken for graph nodes or edges.

The approved backdrop is delivered as responsive WebP sources rather than the full PNG. It aligns with the front projection in `hero2d`, accepts subtle pointer parallax on fine-pointer devices, and becomes a low-opacity, front-facing reference plane in `explorer3d`; it never rotates or substitutes for the live graph.

## Morph and interaction state machine

Use one canvas, one graph state, and stable object identity throughout:

- `hero2d`: orthographic/front camera, depth flattened, labels/chrome hidden, all graph marks in the gold ramp.
- `entering3d`: canvas expands to fullscreen while depth, perspective, camera, and colors interpolate for about 900ms with the standard expressive easing.
- `explorer3d`: perspective camera; drag/orbit, pan, wheel/pinch zoom, pause/speed, search, labels, filters, tooltips, pinning, ancestry/descendant highlighting, neighbor cards, and collection behavior match the old graph.
- `exiting3d`: close/Escape reverses the same interpolation back to the exact hero pose; restore focus after contraction.

Desktop hover slows rotation, brightens the focused node and connected path, animates its bloom/halo, and opens the existing tooltip. Touch tap pins the equivalent state. “Add to collection,” remove, clear, copy command/copy all, and named-skill installability rules remain intact. Collection state survives exit/re-entry during the page session.

The old semantic/spectral constellation layouts, star cloud, and “HUD” language do not appear as alternate fullscreen modes. Tree Explorer is tree-only. Reduced-motion skips the cinematic interpolation and idle movement but preserves deliberate manual orbit and zoom.

## Gold, rank truth, and Yggdrasil II readiness

- In `hero2d`, all branches and nodes use a tonal gold family. Lower structure uses antique/muted gold; full-strength `--apex-gold` remains reserved for Ultimate/Apex emphasis.
- Ultimates remain Ultimates. In gold mode they stay legible through scale, diamond geometry, and rings; in Explorer they recover their true current tier/rank color and effects.
- During morph, interpolate each mark from gold to the value returned by a single `resolveNodeVisual()` adapter. Do not hardcode schema enums into layout or transition code.
- The current adapter reads today's generic `type`, named level, and generated meta color data. After Yggdrasil II frontend/schema work lands, only the adapter changes to consume derived branch/rank semantics; topology and interaction remain unchanged.
- Do not introduce new Fusion/Unique branch copy or mutate schema/data in this PR. Do not erase the ratified vocabulary: 5★ Ultimate remains canonical, with Suite/Unique distinctions supplied later by the Yggdrasil II adapter.
- Amend `DESIGN.md` with a narrow World Tree brand-mark exception for the full gold ramp; no hardcoded hex colors or gradient text.

## Scope and delivery

- Branch: `design/homepage-gaia-tree-hero`; base: `dev/yggdrasil-ii-staging`; open as a draft before implementation.
- In scope: homepage hero/layout, dynamic tree layout/renderer, fullscreen morph/controller, CTA anchors, focused styles, tests, this brief, and the DESIGN amendment.
- Out of scope: registry/schema migration, Fusion/Unique implementation, graph data edits, nav/Hall/Ascension redesign, new pages, or parent staging→main conflict repair.
- Tests are explicitly allowed. Keep implementation commits bounded; browser evidence and orchestrator token spend belong on the draft PR after the final push.

## Acceptance and tests

- Pure-layout tests prove input-order determinism, finite coordinates, complete node/edge preservation, and no invented links.
- Intake fixtures add an isolate, a new cluster/component, a multi-parent node, and a depth-changing edge; `setGraph()` reshapes correctly without code changes. Missing refs degrade individually; a cycle shows a non-blocking unavailable state rather than altering topology.
- State tests cover hero → entering → explorer → exiting → hero, interrupted/reversed transitions, legacy URL aliases, Escape/focus restoration, and reduced motion.
- Interaction tests cover orbit/pan/zoom, desktop hover, touch pinning, search/filter/labels, and add/remove/copy/clear collection behavior.
- Visual browser checks at 1440×900, 1024×768, 390×844, and 320×568 verify title/CTA hierarchy, full-gold silhouette, true-color 3D state, reversible object-level morph, 44px touch targets, and zero horizontal overflow.
- Render the current complete DAG from the Class S asset and verify every normalized node/edge appears, live Ultimates remain distinct, and no second graph instance or duplicate fetch is created.
- Profile a two-second idle Explorer window at mobile width. Cache projection inputs per frame and permit a 30fps mobile idle cadence while preserving 60fps morph, drag, hover, and pinned interaction.

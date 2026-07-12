/*
 * Pure deterministic layout for the Gaia World Tree.
 *
 * The same canonical IDs and prerequisite edges produce two keyed poses:
 * heroPose is a flat editorial tree; fieldPose adds deterministic bough depth.
 * Taxonomy never affects geometry, keeping this projection compatible with
 * the ratified meta migration.
 */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.GaiaWorldTreeLayout = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var UINT32_MAX = 4294967295;
  var TAU = Math.PI * 2;
  var GOLDEN_ANGLE = 2.399963229728653;

  // --- §5.2 Backdrop pin ------------------------------------------------------
  // The painted `yggdrasil-backdrop` trunk sits on the vertical centre axis in
  // LAYOUT space. Its CSS placement (transform translate 22%, scale 1.2,
  // heroCenterRatio 0.72) is applied at RENDER time by skill-graph.js, not here,
  // so in layout coordinates the trunk column lives at x = TRUNK_SPINE_X and the
  // collar (ground line) at y = treeHeight * GROUND_LINE_RATIO — the same frame
  // the real-node silhouette already uses (layoutComponent groundY). If the
  // backdrop asset is swapped, retune these single constants; nothing else moves.
  var TRUNK_SPINE_X = 0;            // trunk column x in layout space
  var GROUND_LINE_RATIO = 0.20;     // groundY = treeHeight * GROUND_LINE_RATIO
  var CROWN_APEX_RATIO = -0.50;     // crown apex y = treeHeight * CROWN_APEX_RATIO
  var ROOT_BOTTOM_RATIO = 0.38;     // deepest root anchor  = treeHeight * ROOT_BOTTOM_RATIO
  var TAPROOT_RATIO = 0.52;         // reserved 6★ taproot (below the root fan)

  // Synthetic armature resolution (data-INDEPENDENT — always present).
  var SPINE_SEGMENTS = 6;           // ghost spine waypoints from collar up to (not incl.) apex
  var BOUGH_COUNT = 6;              // primary boughs forking off the spine
  var SUB_BOUGH_COUNT = 2;          // one sub-level of recursion per bough
  var ROOT_ANCHOR_COUNT = 6;        // primary root anchors below the collar
  var SUB_ROOT_COUNT = 2;           // one sub-level of recursion per root

  // Coreness curve (§4). coreness = clamp((effRank/6)^exp, 0, 1); rank <2 -> 0.
  var CORENESS_EXPONENT = 1.0;      // tunable visual spread (raise to pull tips outward)
  var CORENESS_RANK_FLOOR = 2;      // 0-1★ (incl. redacted Awakened) land at coreness 0 (bark)
  var MAX_STAR_RANK = 6;            // 6★ = heartwood centre (coreness 1)

  // --- §4 Heartwood core-pull -------------------------------------------------
  // Coreness (effective rank) does not just color a node — it pulls its POSITION
  // toward the heartwood core. High-rank crown/root nodes migrate inward (toward
  // the trunk spine) AND toward the vertical heartwood centre, so 5-6★ read as
  // deep in the core while 2★ sit near their DAG-depth tip. Applied to crown and
  // root real nodes in the attachment pass; uniques ('outside') keep their
  // constellation relocation. Deterministic — no random, purely coreness-driven.
  var CORE_Y_RATIO = 0.13;          // coreY = treeHeight * CORE_Y_RATIO (heartwood, just above the collar at 0.20)
  var CORE_PULL_STRENGTH = 0.72;    // blend fraction at coreness 1 (6★ = full pull); scales linearly with coreness
  // Fix #3: the core-pull aims high-rank nodes at a CYLINDER around the heartwood
  // axis, not a single point. Without a radius floor every 5-6★ node collapses
  // onto x=z=0 and all structural routes pinch through one narrow collar. A
  // per-node deterministic angle spreads them AROUND the axis, giving the
  // heartwood a barrel of volume and un-pinching the convergence.
  var CORE_MIN_RADIUS = 0.10;       // * width — radius of the heartwood cylinder the pull targets

  // Radial reach used when a real node attaches to its armature anchor (§5.2).
  var CROWN_BOUGH_REACH = 0.50;     // * width
  var ROOT_BOUGH_REACH = 0.58;      // * width
  var OUTSIDE_BOUGH_REACH = 0.22;   // * width (dark constellation spire stems)
  var OUTSIDE_SIDE = 1;             // single side of the trunk (positive x); NOT mirrored
  var OUTSIDE_X_RATIO = 0.86;       // * width, constellation column base offset
  var OUTSIDE_ANCHOR_COUNT = 5;     // ghost stems in the dark unique constellation

  function stableHash(value) {
    var text = String(value == null ? '' : value);
    var hash = 2166136261;
    for (var i = 0; i < text.length; i += 1) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  }

  function compareIds(a, b) {
    return String(a).localeCompare(String(b));
  }

  function edgeKey(source, target) {
    return source + '\u0000' + target;
  }

  function normalizeGraph(graph) {
    graph = graph || {};
    var diagnostics = {
      duplicateNodeIds: [],
      duplicateEdges: [],
      unknownReferences: [],
      invalidNodes: 0,
      invalidEdges: 0,
      selfEdges: [],
      cycleNodes: [],
    };
    var nodeMap = new Map();
    var skills = Array.isArray(graph.skills) ? graph.skills : [];

    skills.forEach(function (skill) {
      if (!skill || typeof skill.id !== 'string' || !skill.id.trim()) {
        diagnostics.invalidNodes += 1;
        return;
      }
      var id = skill.id.trim();
      if (nodeMap.has(id)) {
        diagnostics.duplicateNodeIds.push(id);
        return;
      }
      nodeMap.set(id, {
        id: id,
        cluster: skill.cluster == null ? 'unclustered' : skill.cluster,
        source: skill,
      });
    });

    var nodes = Array.from(nodeMap.values()).sort(function (a, b) {
      return compareIds(a.id, b.id);
    });
    var candidates = [];

    skills.forEach(function (skill) {
      if (!skill || typeof skill.id !== 'string') return;
      var target = skill.id.trim();
      if (!nodeMap.has(target)) return;
      (Array.isArray(skill.prerequisites) ? skill.prerequisites : []).forEach(function (parent) {
        if (typeof parent !== 'string' || !parent.trim()) {
          diagnostics.invalidEdges += 1;
          return;
        }
        candidates.push({ source: parent.trim(), target: target, via: 'prerequisites' });
      });
    });

    (Array.isArray(graph.edges) ? graph.edges : []).forEach(function (edge) {
      if (!edge || typeof edge !== 'object') {
        diagnostics.invalidEdges += 1;
        return;
      }
      var source = edge.sourceSkillId || edge.source || edge.from;
      var target = edge.targetSkillId || edge.target || edge.to;
      if (typeof source !== 'string' || typeof target !== 'string' || !source.trim() || !target.trim()) {
        diagnostics.invalidEdges += 1;
        return;
      }
      candidates.push({ source: source.trim(), target: target.trim(), via: 'edges' });
    });

    var seen = new Map();
    candidates.forEach(function (edge) {
      if (!nodeMap.has(edge.source) || !nodeMap.has(edge.target)) {
        diagnostics.unknownReferences.push(edge);
        return;
      }
      var key = edgeKey(edge.source, edge.target);
      if (seen.has(key)) {
        // gaia.json mirrors canonical edges in both supported forms. Only a
        // repeated edge inside the same representation is a real duplicate.
        if (seen.get(key) === edge.via) diagnostics.duplicateEdges.push(edge);
        return;
      }
      seen.set(key, edge.via);
      if (edge.source === edge.target) diagnostics.selfEdges.push(edge.source);
    });

    var edges = Array.from(seen.keys()).map(function (key) {
      var split = key.split('\u0000');
      return { source: split[0], target: split[1] };
    }).sort(function (a, b) {
      return compareIds(a.source, b.source) || compareIds(a.target, b.target);
    });

    diagnostics.duplicateNodeIds.sort(compareIds);
    diagnostics.selfEdges.sort(compareIds);
    diagnostics.unknownReferences.sort(function (a, b) {
      return compareIds(a.source, b.source) || compareIds(a.target, b.target);
    });
    return { nodes: nodes, edges: edges, diagnostics: diagnostics };
  }

  function buildIndexes(nodes, edges) {
    var parents = {};
    var children = {};
    var undirected = {};
    nodes.forEach(function (node) {
      parents[node.id] = [];
      children[node.id] = [];
      undirected[node.id] = [];
    });
    edges.forEach(function (edge) {
      parents[edge.target].push(edge.source);
      children[edge.source].push(edge.target);
      undirected[edge.source].push(edge.target);
      undirected[edge.target].push(edge.source);
    });
    [parents, children, undirected].forEach(function (index) {
      Object.keys(index).forEach(function (id) {
        index[id] = Array.from(new Set(index[id])).sort(compareIds);
      });
    });
    return { parents: parents, children: children, undirected: undirected };
  }

  function buildComponents(nodes, undirected) {
    var visited = new Set();
    var components = [];
    nodes.forEach(function (node) {
      if (visited.has(node.id)) return;
      var queue = [node.id];
      var ids = [];
      visited.add(node.id);
      while (queue.length) {
        var id = queue.shift();
        ids.push(id);
        undirected[id].forEach(function (neighbor) {
          if (visited.has(neighbor)) return;
          visited.add(neighbor);
          queue.push(neighbor);
        });
        queue.sort(compareIds);
      }
      ids.sort(compareIds);
      components.push(ids);
    });
    return components.sort(function (a, b) {
      return b.length - a.length || compareIds(a[0], b[0]);
    });
  }

  function topologicalOrder(nodes, parents, children) {
    var indegree = {};
    nodes.forEach(function (node) { indegree[node.id] = parents[node.id].length; });
    var ready = nodes.filter(function (node) { return indegree[node.id] === 0; })
      .map(function (node) { return node.id; }).sort(compareIds);
    var order = [];
    while (ready.length) {
      var id = ready.shift();
      order.push(id);
      children[id].forEach(function (child) {
        indegree[child] -= 1;
        if (indegree[child] === 0) {
          ready.push(child);
          ready.sort(compareIds);
        }
      });
    }
    return {
      order: order,
      cycleNodes: nodes.map(function (node) { return node.id; }).filter(function (id) {
        return indegree[id] > 0;
      }).sort(compareIds),
    };
  }

  function transitiveClosures(nodes, order, parents, children) {
    var ancestors = {};
    var descendants = {};
    nodes.forEach(function (node) {
      ancestors[node.id] = new Set();
      descendants[node.id] = new Set();
    });
    order.forEach(function (id) {
      parents[id].forEach(function (parent) {
        ancestors[id].add(parent);
        ancestors[parent].forEach(function (ancestor) { ancestors[id].add(ancestor); });
      });
    });
    order.slice().reverse().forEach(function (id) {
      children[id].forEach(function (child) {
        descendants[id].add(child);
        descendants[child].forEach(function (descendant) { descendants[id].add(descendant); });
      });
    });
    return { ancestors: ancestors, descendants: descendants };
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function smoothstep(edge0, edge1, value) {
    var t = clamp((value - edge0) / Math.max(0.0001, edge1 - edge0), 0, 1);
    return t * t * (3 - 2 * t);
  }

  function signedHash(value) {
    return stableHash(value) / UINT32_MAX * 2 - 1;
  }

  function circularDistance(a, b) {
    var tau = Math.PI * 2;
    var diff = Math.abs((a - b) % tau);
    return Math.min(diff, tau - diff);
  }

  function botanicalEnvelope(progress) {
    var p = clamp(progress, 0, 1);
    return 0.10 + 0.90 * Math.pow(Math.sin(Math.PI * p), 0.62);
  }

  // Today's adapter reads the current cluster axis. Yggdrasil II can replace
  // this one seam with its ratified meta branch without rewriting geometry.
  function resolveBoughKey(node) {
    return String(node && node.cluster != null ? node.cluster : 'unclustered');
  }

  // --- §4 Effective rank ------------------------------------------------------
  // The engine RECEIVES effectiveRank already joined onto each node (the runtime
  // named-index join is Agent 2's job — see spec §4). We only consume it. It is a
  // small integer star rank in [0..6]; missing/non-finite => 0. The redaction
  // cutline (§4) collapses 0-1★ to coreness 0 (outer bark surface); the colored
  // ramp begins at 2★ Named.
  function readEffectiveRank(node) {
    var raw = node && node.effectiveRank;
    var value = Number(raw);
    if (!Number.isFinite(value) || value < 0) return 0;
    return value;
  }

  // coreness = clamp((effRank / MAX_STAR_RANK) ^ CORENESS_EXPONENT, 0, 1).
  // 1 = heartwood centre (6★), 0 = outer surface. Ranks below CORENESS_RANK_FLOOR
  // land at exactly 0 so redacted/Awakened skills sit on the bark, never inward.
  function corenessFromRank(effRank) {
    if (effRank < CORENESS_RANK_FLOOR) return 0;
    return clamp(Math.pow(effRank / MAX_STAR_RANK, CORENESS_EXPONENT), 0, 1);
  }

  // --- §3 The resolver (THE load-bearing compatibility seam) ------------------
  // Maps BOTH meta vocabularies (Yggdrasil I and II) onto ONE frozen output
  // contract. This is the ONLY function that may branch on meta. Geometry, edge
  // routing, the armature, and colour all consume the contract and never change
  // across the meta boundary (§3.4). At Ygg II cutover exactly ONE function is
  // edited — this one (the boughGroup swap point marked below).
  //
  // Contract (frozen — see FROZEN CONTRACT in the handover):
  //   { hemisphere:'crown'|'root'|'outside', coreness:0..1, isUnique:boolean,
  //     isSuite:boolean, glyph:'○'|'◇'|'◉'|'◆', boughGroup:<group key> }
  //
  // §3.3 Meta detection is a FEATURE-CHECK across the whole node set, not a flag:
  //   metaIsYggI = nodes.some(n => n.type !== 'basic' && n.type !== 'fusion')
  // If any node's type ∉ {basic, fusion} → Ygg I read column; else Ygg II. No
  // config, no version flag, no dead code after cutover.
  function detectMetaIsYggI(nodes) {
    return nodes.some(function (node) {
      var t = node && node.type;
      return t !== 'basic' && t !== 'fusion';
    });
  }

  // node: the SOURCE skill object (carries .type, .suiteComponents, .cluster,
  //       .effectiveRank). effRank: the already-joined effective star rank.
  // metaIsYggI: result of detectMetaIsYggI on the full node set (feature-check).
  function resolveSemantics(node, effRank, metaIsYggI) {
    node = node || {};
    var type = node.type;
    var hasSuiteComponents = Array.isArray(node.suiteComponents)
      && node.suiteComponents.length > 0;

    // §3.2 read order is CRITICAL and must not be reordered.

    // 1. Detect isUnique FIRST → hemisphere 'outside'. Short-circuits before the
    //    hemisphere-by-type step so a Ygg II Unique (type='basic') does NOT fall
    //    into roots.
    //    Ygg I:  type === 'unique'
    //    Ygg II: type === 'basic' && effRank >= 4 && !suiteComponents
    var isUnique = metaIsYggI
      ? type === 'unique'
      : (type === 'basic' && effRank >= 4 && !hasSuiteComponents);

    // 2. Detect isSuite.
    //    Ygg I:  type === 'ultimate'
    //    Ygg II: suiteComponents present
    var isSuite = metaIsYggI ? type === 'ultimate' : hasSuiteComponents;

    // 3. Hemisphere by type. Uniques already resolved to 'outside' above.
    //    basic → root ; fusion/extra/ultimate → crown.
    var hemisphere;
    if (isUnique) {
      hemisphere = 'outside';
    } else if (type === 'basic') {
      hemisphere = 'root';
    } else {
      // extra / ultimate (Ygg I) and fusion (Ygg II) all grow into the crown.
      hemisphere = 'crown';
    }

    // Structural-class glyph (§3.1 / §6): ○ basic · ◇ fusion · ◉ unique · ◆ suite.
    var glyph;
    if (isUnique) glyph = '◉';
    else if (isSuite) glyph = '◆';
    else if (hemisphere === 'root') glyph = '○';
    else glyph = '◇';

    // 4. coreness = normalized effective rank (§4).
    var coreness = corenessFromRank(effRank);

    // 5. boughGroup = cluster (Ygg I). ── YGG II GROUPING SWAP POINT ──
    //    At Ygg II cutover, replace resolveBoughKey with the ratified grouping
    //    axis. Nothing else in the engine changes.
    var boughGroup = resolveBoughKey(node);

    return {
      hemisphere: hemisphere,
      coreness: coreness,
      isUnique: isUnique,
      isSuite: isSuite,
      glyph: glyph,
      boughGroup: boughGroup,
    };
  }

  function distributeBoughs(ids, byId) {
    // Bough SECTORS are balanced by cluster size so the crown mass is even
    // left/right instead of lopsided (three of the biggest clusters used to all
    // point +x, producing a right-swept tendril). Clusters are ranked by size
    // and dealt into interleaved slots around the circle (0, n/2, 1, n/2+1, …)
    // so the largest clusters land opposite one another and their mass cancels
    // (weighted centroid ≈ 0). Node positions WITHIN a bough remain stableHash-
    // deterministic; only the per-cluster base angle is size-aware. NOTE: this
    // trades the old size-independent golden-angle base (which kept sectors fixed
    // as intake PRs grew clusters) for balance — sectors are recomputed when
    // cluster membership changes. Ygg II swaps resolveBoughKey here.
    var subBoughCount = 3;
    var byNode = {};
    var angleByBough = {};
    var tau = Math.PI * 2;

    // Rank clusters present in THIS component by size (ties broken by key for
    // determinism), then assign each an interleaved sector slot.
    var sizeByGroup = {};
    ids.forEach(function (id) {
      var gk = resolveBoughKey(byId[id]);
      sizeByGroup[gk] = (sizeByGroup[gk] || 0) + 1;
    });
    var rankedGroups = Object.keys(sizeByGroup).sort(function (a, b) {
      return sizeByGroup[b] - sizeByGroup[a] || (a < b ? -1 : a > b ? 1 : 0);
    });
    var groupCount = rankedGroups.length;
    var slotByGroup = {};
    var lo = 0;
    var hi = Math.ceil(groupCount / 2);
    rankedGroups.forEach(function (gk, rank) {
      slotByGroup[gk] = (rank % 2 === 0) ? lo++ : hi++;
    });
    function baseAngleFor(groupKey) {
      var slot = slotByGroup[groupKey];
      if (slot == null) {
        // Unseen key (defensive): fall back to a stable hashed sector.
        return stableHash(groupKey + ':bough-sector') / UINT32_MAX * tau;
      }
      var span = groupCount > 0 ? tau / groupCount : tau;
      return ((slot * span + GOLDEN_ANGLE * 0.5) % tau + tau) % tau;
    }

    ids.slice().sort(compareIds).forEach(function (id) {
      var groupKey = resolveBoughKey(byId[id]);
      var baseAngle = baseAngleFor(groupKey);
      var shard = stableHash(id + ':bough-shard') % subBoughCount;
      var key = groupKey + ':' + shard;
      var shardOffset = (shard - (subBoughCount - 1) / 2) * 0.16;
      var angle = baseAngle + shardOffset + signedHash(id + ':bough-angle') * 0.075;
      angleByBough[key] = baseAngle;
      byNode[id] = { key: key, group: groupKey, angle: angle };
    });

    return {
      byNode: byNode,
      angleByBough: angleByBough,
      count: Object.keys(angleByBough).length,
    };
  }

  function layoutComponent(ids, byId, indexes, depth, descendants, width, treeHeight) {
    var maxDepth = Math.max(1, ids.reduce(function (value, id) {
      return Math.max(value, depth[id] || 0);
    }, 0));
    var sinkSet = new Set(ids.filter(function (id) { return indexes.children[id].length === 0; }));
    var descendantSinkCount = {};
    ids.forEach(function (id) {
      var count = sinkSet.has(id) ? 1 : 0;
      descendants[id].forEach(function (descendant) {
        if (sinkSet.has(descendant)) count += 1;
      });
      descendantSinkCount[id] = count;
    });
    var maxReach = Math.max(1, ids.reduce(function (value, id) {
      return Math.max(value, descendantSinkCount[id]);
    }, 0));
    var maxIndegree = Math.max(1, ids.reduce(function (value, id) {
      return Math.max(value, indexes.parents[id].length);
    }, 0));
    var boughs = distributeBoughs(ids, byId);
    var groundY = treeHeight * GROUND_LINE_RATIO;
    var crownTopY = treeHeight * CROWN_APEX_RATIO;
    var rootBottomY = treeHeight * ROOT_BOTTOM_RATIO;
    var crownHeight = groundY - crownTopY;
    var rootDepth = rootBottomY - groundY;
    var hero = {};
    var field = {};
    var meta = {};

    ids.forEach(function (id) {
      var branch = boughs.byNode[id];
      var angle = branch.angle;
      var reach = Math.log1p(descendantSinkCount[id]) / Math.log1p(maxReach);
      var phase = (stableHash(id) % 628) / 100;
      var radius;
      var y;
      var zone;
      var progress = null;
      var rootProgress = null;

      if (indexes.parents[id].length === 0) {
        zone = 'root';
        // Fix #1: gather the deepest-root stragglers back into the fan. The
        // deepest roots (reach 0, no children) mapped rootProgress→~1 and, being
        // 0-1★ (coreness 0), skip the core-pull — so they dangled BELOW the
        // visible root fan, out of bounds. Two coordinated tweaks pull the tail
        // up: (a) the deep-band coefficient 0.82→0.66 shrinks the depth reached
        // by the deepest roots (1-reach≈1 now maps to rootProgress≈0.9 not 1.0);
        // (b) the depth exponent 0.95→1.25 further maps high rootProgress to a
        // shallower y. The y-jitter is widened (0.035→0.075) so the deepest band
        // fans across a spread of depths instead of piling onto one shelf,
        // keeping a visible root spread while the tail merges up into the fan.
        rootProgress = clamp(
          0.18 + 0.80 * (1 - reach) + signedHash(id + ':root-y') * 0.075,
          0.16,
          1
        );
        y = groundY + rootDepth * Math.pow(rootProgress, 1.02);
        var rootEnvelope = width * ROOT_BOUGH_REACH * Math.pow(rootProgress, 1.20);
        var rootFan = clamp(
          0.24 + 0.72 * (1 - reach) + signedHash(id + ':root-fan') * 0.06,
          0.16,
          0.98
        );
        radius = rootEnvelope * rootFan;
      } else {
        zone = 'crown';
        var sink = sinkSet.has(id) ? 1 : 0;
        var merge = Math.log1p(indexes.parents[id].length) / Math.log1p(maxIndegree);
        var level = Math.max(1, depth[id] || 1);
        var baseProgress = 0.10 + 0.84 * Math.pow(level / maxDepth, 0.78);
        var previousBase = level > 1
          ? 0.10 + 0.84 * Math.pow((level - 1) / maxDepth, 0.78)
          : 0.14;
        var nextBase = level < maxDepth
          ? 0.10 + 0.84 * Math.pow((level + 1) / maxDepth, 0.78)
          : 0.99;
        var halfBand = maxDepth === 1
          ? 0.14
          : Math.max(0.0001, Math.min(baseProgress - previousBase, nextBase - baseProgress) * 0.40);
        var botanicalSignal = clamp(
          0.38 * sink + 0.18 * merge + 0.28 * (1 - reach) * (1 - sink)
            + signedHash(id + ':crown-y') * 0.72,
          -1,
          1
        );
        progress = clamp(baseProgress + halfBand * botanicalSignal, 0.105, 0.97);
        y = groundY - crownHeight * progress;
        var halfWidth = width * 0.50 * botanicalEnvelope(progress);
        var fan = smoothstep(0.16, 0.68, progress) * (1 - 0.76 * reach);
        if (sink) fan = Math.max(fan, 0.78);
        fan = clamp(fan + signedHash(id + ':crown-fan') * 0.055, 0.10, 0.98);
        radius = halfWidth * fan * (0.86 + (stableHash(id + ':radial') / UINT32_MAX) * 0.12);
      }

      var x = radius * Math.cos(angle);
      var z = radius * Math.sin(angle);
      hero[id] = { x: x, y: y, z: 0, w: 0, phase: phase };
      field[id] = { x: x, y: y, z: z, w: 0, phase: phase };
      meta[id] = {
        zone: zone,
        bough: branch.key,
        boughGroup: branch.group,
        angle: angle,
        radius: radius,
        progress: progress,
        rootProgress: rootProgress,
        reach: reach,
      };
    });

    return { hero: hero, field: field, meta: meta, groundY: groundY };
  }

  // --- §5 The synthetic ghost armature ----------------------------------------
  // Structure must not depend on the data it organizes (§5). This armature is
  // synthetic, always present, and data-INDEPENDENT — built purely from the
  // tuned constants + the layout frame (width, treeHeight). A registry with zero
  // starless nodes still gets a full skeleton.
  //
  // Determinism: golden-angle + stableHash only. No Math.random, no Date.now.
  //
  // Ghost waypoint keys are namespaced with a sentinel prefix that real trimmed
  // node ids (matching [a-z0-9-]+) can never produce, so they can NEVER collide
  // with a real node id and are trivially filterable by a renderer. Ghosts are
  // tagged { ghost: true } in the pose maps ONLY and are excluded from
  // result.nodes / result.edges / all counts (§5.1).
  var GHOST_PREFIX = '@ghost:';

  function ghostKey(role, path) {
    return GHOST_PREFIX + role + ':' + path;
  }

  // roles carried on each armature waypoint's pose + meta so a renderer can tell
  // spine from bough from root from taproot (§5.1 organic mesh).
  function buildArmature(width, treeHeight) {
    var groundY = treeHeight * GROUND_LINE_RATIO;      // collar / ground line
    var apexY = treeHeight * CROWN_APEX_RATIO;         // crown apex (up = -y)
    var rootBottomY = treeHeight * ROOT_BOTTOM_RATIO;  // deepest root
    var taprootY = treeHeight * TAPROOT_RATIO;         // reserved 6★ taproot
    var crownHeight = groundY - apexY;                 // > 0
    var rootDepth = rootBottomY - groundY;             // > 0
    var spineX = TRUNK_SPINE_X;

    var waypoints = [];      // flat list of every ghost waypoint (real-node-free)
    var spine = [];
    var boughAnchors = [];
    var rootAnchors = [];

    function push(role, key, x, y, z, extra) {
      var wp = Object.assign({
        key: key,
        role: role,        // 'spine' | 'bough' | 'root' | 'taproot'
        ghost: true,
        x: x,
        y: y,
        z: z,
      }, extra || {});
      waypoints.push(wp);
      return wp;
    }

    // Trunk spine: ghost waypoints up the x = spineX axis, collar -> crown apex.
    // Index 0 is the collar (y = groundY); the last is the apex (y = apexY).
    var apexKey = ghostKey('spine', 'apex');
    for (var s = 0; s <= SPINE_SEGMENTS; s += 1) {
      var t = s / SPINE_SEGMENTS;                 // 0..1 collar->apex
      var sy = groundY - crownHeight * t;
      var skey = s === SPINE_SEGMENTS ? apexKey : ghostKey('spine', String(s));
      var wp = push('spine', skey, spineX, sy, 0, { level: s, t: t });
      spine.push(wp);
    }
    var collarKey = spine[0].key;

    // Bough anchors: fork points off the spine at rising heights, golden-angle
    // directions, one sub-level of recursion. Higher forks are shorter (tapered
    // envelope) so the silhouette narrows toward the apex.
    for (var b = 0; b < BOUGH_COUNT; b += 1) {
      var bt = (b + 1) / (BOUGH_COUNT + 1);        // 0..1 along crown, avoids ends
      var by = groundY - crownHeight * bt;
      var bAngle = ((b * GOLDEN_ANGLE) % TAU + TAU) % TAU;
      var envelope = botanicalEnvelope(bt);        // taper: fat mid, thin ends
      var bReach = width * CROWN_BOUGH_REACH * envelope * 0.6;
      var bx = spineX + bReach * Math.cos(bAngle);
      var bz = bReach * Math.sin(bAngle);
      // nearest spine waypoint (by height) is this bough's attachment on the spine
      var bSpine = nearestByY(spine, by);
      var bKey = ghostKey('bough', String(b));
      var boughWp = push('bough', bKey, bx, by, bz, {
        angle: bAngle,
        level: 0,
        spineKey: bSpine.key,
        parentKey: bSpine.key,
      });
      boughAnchors.push(boughWp);

      for (var sb = 0; sb < SUB_BOUGH_COUNT; sb += 1) {
        var subT = 0.55 + 0.35 * ((sb + 1) / (SUB_BOUGH_COUNT + 1)); // further up/out
        var subAngle = bAngle + (sb - (SUB_BOUGH_COUNT - 1) / 2) * 0.5
          + signedHash(bKey + ':sub:' + sb) * 0.12;
        var subReach = bReach * (1.35 + 0.25 * sb);
        var subY = by - crownHeight * 0.10 * (sb + 1);
        var subX = spineX + subReach * Math.cos(subAngle);
        var subZ = subReach * Math.sin(subAngle);
        var subKey = ghostKey('bough', b + '.' + sb);
        boughAnchors.push(push('bough', subKey, subX, subY, subZ, {
          angle: subAngle,
          level: 1,
          spineKey: bSpine.key,
          parentKey: bKey,
        }));
      }
    }

    // Root anchors: mirror of the boughs below the collar.
    for (var r = 0; r < ROOT_ANCHOR_COUNT; r += 1) {
      var rt = (r + 1) / (ROOT_ANCHOR_COUNT + 1);
      var ry = groundY + rootDepth * rt;
      var rAngle = ((r * GOLDEN_ANGLE + GOLDEN_ANGLE * 0.5) % TAU + TAU) % TAU;
      var rReach = width * ROOT_BOUGH_REACH * Math.pow(rt, 1.10) * 0.6;
      var rx = spineX + rReach * Math.cos(rAngle);
      var rz = rReach * Math.sin(rAngle);
      var rKey = ghostKey('root', String(r));
      var rootWp = push('root', rKey, rx, ry, rz, {
        angle: rAngle,
        level: 0,
        spineKey: collarKey,
        parentKey: collarKey,
      });
      rootAnchors.push(rootWp);

      for (var srr = 0; srr < SUB_ROOT_COUNT; srr += 1) {
        var srT = 0.55 + 0.35 * ((srr + 1) / (SUB_ROOT_COUNT + 1));
        var srAngle = rAngle + (srr - (SUB_ROOT_COUNT - 1) / 2) * 0.5
          + signedHash(rKey + ':sub:' + srr) * 0.12;
        var srReach = rReach * (1.35 + 0.25 * srr);
        var srY = ry + rootDepth * 0.10 * (srr + 1);
        var srX = spineX + srReach * Math.cos(srAngle);
        var srZ = srReach * Math.sin(srAngle);
        var srKey = ghostKey('root', r + '.' + srr);
        rootAnchors.push(push('root', srKey, srX, srY, srZ, {
          angle: srAngle,
          level: 1,
          spineKey: collarKey,
          parentKey: rKey,
        }));
      }
    }

    // Reserved taproot point (for a future 6★ — none today). Iconic when it exists.
    var taprootKey = ghostKey('taproot', '0');
    var taproot = push('taproot', taprootKey, spineX, taprootY, 0, {
      level: 0,
      spineKey: collarKey,
      parentKey: collarKey,
    });

    // Dark unique constellation stems (§2.2 / §5): a single-side vertical column
    // of faint ghost stems OFF the wood (positive-x only, NOT mirrored). Uniques
    // attach here; there is no wood connection back to the trunk (standing stones
    // beside the tree). Given a distinct 'outside' role so the renderer paints
    // them from the dark palette, not the rank ramp.
    var outsideAnchors = [];
    var outsideBaseX = spineX + OUTSIDE_SIDE * width * OUTSIDE_X_RATIO;
    for (var o = 0; o < OUTSIDE_ANCHOR_COUNT; o += 1) {
      var ot = OUTSIDE_ANCHOR_COUNT > 1 ? o / (OUTSIDE_ANCHOR_COUNT - 1) : 0.5;
      // span from just above the collar up toward the crown, single side.
      var oy = groundY - crownHeight * (0.15 + 0.6 * ot);
      var ox = outsideBaseX + OUTSIDE_SIDE * width * 0.04 * signedHash('outside:' + o);
      var oz = width * 0.06 * signedHash('outside-z:' + o);
      var oKey = ghostKey('outside', String(o));
      outsideAnchors.push(push('outside', oKey, ox, oy, oz, {
        level: 0,
        parentKey: null,
      }));
    }

    return {
      groundY: groundY,
      apexY: apexY,
      apexKey: apexKey,
      collarKey: collarKey,
      rootBottomY: rootBottomY,
      taprootY: taprootY,
      spineX: spineX,
      spine: spine,
      boughAnchors: boughAnchors,
      rootAnchors: rootAnchors,
      outsideAnchors: outsideAnchors,
      taproot: taproot,
      taprootKey: taprootKey,
      waypoints: waypoints,
    };
  }

  function nearestByY(waypoints, y) {
    var best = waypoints[0];
    var bestDist = Math.abs(best.y - y);
    for (var i = 1; i < waypoints.length; i += 1) {
      var d = Math.abs(waypoints[i].y - y);
      if (d < bestDist) { bestDist = d; best = waypoints[i]; }
    }
    return best;
  }

  // Nearest armature anchor consistent with a node's hemisphere (§5 item 2).
  // Deterministic: ties broken by ghost key ordering.
  function nearestAnchor(anchors, x, y, z) {
    var best = null;
    var bestDist = Infinity;
    for (var i = 0; i < anchors.length; i += 1) {
      var a = anchors[i];
      var dx = a.x - x, dy = a.y - y, dz = (a.z || 0) - (z || 0);
      var d = dx * dx + dy * dy + dz * dz;
      if (d < bestDist || (d === bestDist && best && compareIds(a.key, best.key) < 0)) {
        bestDist = d; best = a;
      }
    }
    return best;
  }

  function buildWorldTreeLayout(graph, options) {
    options = options || {};
    var normalized = normalizeGraph(graph);
    var nodes = normalized.nodes;
    var edges = normalized.edges;
    var diagnostics = normalized.diagnostics;
    var indexes = buildIndexes(nodes, edges);
    var components = buildComponents(nodes, indexes.undirected);
    var topo = topologicalOrder(nodes, indexes.parents, indexes.children);
    diagnostics.cycleNodes = topo.cycleNodes;
    var status = topo.cycleNodes.length ? 'unavailable'
      : (diagnostics.unknownReferences.length || diagnostics.invalidNodes || diagnostics.invalidEdges ? 'degraded' : 'ok');
    diagnostics.status = status;

    var result = {
      version: 2,
      available: status !== 'unavailable',
      status: status,
      nodes: nodes,
      edges: edges,
      heroPose: {},
      fieldPose: {},
      parents: indexes.parents,
      children: indexes.children,
      ancestors: {},
      descendants: {},
      components: components.map(function (ids) { return ids.slice(); }),
      componentById: {},
      nodeMeta: {},
      structuralEdgeKeys: [],
      // §5 synthetic ghost armature. Carries NO data; excluded from nodes/edges/
      // counts. Renderers draw armature.waypoints as faint organic mesh and read
      // ghostPose[key] for coordinates. See FROZEN CONTRACT in the handover.
      armature: null,
      ghostPose: {},
      // §5 items 2-3: how each real structural edge drapes over the skeleton.
      // Keyed by the same edgeKey('source','target') form used in structuralEdgeKeys.
      structuralRoutes: {},
      // §3.3 feature-check result, exposed for the renderer's legend/debug only.
      metaIsYggI: false,
      isolates: nodes.filter(function (node) { return indexes.undirected[node.id].length === 0; })
        .map(function (node) { return node.id; }),
      diagnostics: diagnostics,
    };
    if (!result.available) return result;

    var closures = transitiveClosures(nodes, topo.order, indexes.parents, indexes.children);
    result.ancestors = closures.ancestors;
    result.descendants = closures.descendants;

    var depth = {};
    var height = {};
    topo.order.forEach(function (id) {
      depth[id] = indexes.parents[id].reduce(function (value, parent) {
        return Math.max(value, depth[parent] + 1);
      }, 0);
    });
    topo.order.slice().reverse().forEach(function (id) {
      height[id] = indexes.children[id].reduce(function (value, child) {
        return Math.max(value, height[child] + 1);
      }, 0);
    });

    var byId = {};
    nodes.forEach(function (node) { byId[node.id] = node; });
    var width = Number.isFinite(options.width) ? options.width : 760;
    var treeHeight = Number.isFinite(options.height) ? options.height : 680;

    // §3.3 meta feature-check (whole node set) + §3 resolver applied per node.
    // Everything meta-aware is confined to resolveSemantics; the semantic result
    // is stashed on nodeMeta so geometry/edges/render consume the contract only.
    var metaIsYggI = detectMetaIsYggI(nodes.map(function (n) { return n.source || n; }));
    result.metaIsYggI = metaIsYggI;
    var semanticsById = {};
    nodes.forEach(function (node) {
      var source = node.source || node;
      var effRank = readEffectiveRank(source);
      semanticsById[node.id] = resolveSemantics(source, effRank, metaIsYggI);
      semanticsById[node.id].effectiveRank = effRank;
    });

    // §5 synthetic ghost armature — built ONCE from tuned constants + frame.
    var armature = buildArmature(width, treeHeight);
    result.armature = armature;
    armature.waypoints.forEach(function (wp) {
      result.ghostPose[wp.key] = {
        x: wp.x,
        y: wp.y,
        z: wp.z,
        w: 0,
        role: wp.role,          // 'spine'|'bough'|'root'|'taproot'|'outside'
        ghost: true,
        level: wp.level,
        angle: wp.angle,
        spineKey: wp.spineKey,
        parentKey: wp.parentKey,
        t: wp.t,
      };
    });

    var groves = components.filter(function (ids) {
      return ids.length > 1 || indexes.undirected[ids[0]].length > 0;
    });

    groves.forEach(function (ids, componentIndex) {
      var primarySize = groves[0] ? groves[0].length : ids.length;
      var scale = componentIndex === 0 ? 1 : Math.max(0.30, Math.min(0.56, Math.sqrt(ids.length / primarySize)));
      var localWidth = width * scale;
      var localHeight = treeHeight * (componentIndex === 0 ? 1 : scale * 0.86);
      var sideIndex = Math.floor((componentIndex - 1) / 2);
      var side = componentIndex === 0 ? 0 : (componentIndex % 2 ? -1 : 1);
      var offsetX = componentIndex === 0 ? 0 : side * (width * 0.68 + sideIndex * width * 0.23);
      var offsetY = componentIndex === 0 ? 0 : treeHeight * 0.22;
      var local = layoutComponent(ids, byId, indexes, depth, closures.descendants, localWidth, localHeight);
      var fieldOffsetRadius = componentIndex === 0 ? 0 : width * (0.56 + sideIndex * 0.18);
      var fieldOffsetAngle = componentIndex * 2.399963229728653;
      ids.forEach(function (id) {
        var heroPoint = local.hero[id];
        var fieldPoint = local.field[id];
        result.componentById[id] = componentIndex;
        result.heroPose[id] = {
          x: heroPoint.x + offsetX,
          y: heroPoint.y + offsetY,
          z: 0,
          w: 0,
          phase: heroPoint.phase,
        };
        result.fieldPose[id] = {
          x: fieldPoint.x + Math.cos(fieldOffsetAngle) * fieldOffsetRadius,
          y: fieldPoint.y + offsetY,
          z: fieldPoint.z + Math.sin(fieldOffsetAngle) * fieldOffsetRadius,
          w: 0,
          phase: fieldPoint.phase,
        };
        result.nodeMeta[id] = Object.assign({ componentIndex: componentIndex }, local.meta[id]);
      });
    });

    // Honest unconnected seeds form a compact bulb beneath the root collar.
    // They remain disconnected and never widen the living tree's fit bounds.
    var seedIds = result.isolates.slice().sort(function (a, b) {
      return stableHash(a) - stableHash(b) || compareIds(a, b);
    });
    var seedGroundY = treeHeight * 0.20;
    var seedDepth = treeHeight * 0.30;
    var goldenAngle = 2.399963229728653;
    seedIds.forEach(function (id, index) {
      var angle = index * goldenAngle + stableHash(id + ':seed-angle') / UINT32_MAX * 0.22;
      var radius = 12 + 7 * Math.sqrt(index + 1);
      var x = radius * Math.cos(angle);
      var z = radius * Math.sin(angle);
      // Seat the honest-unconnected seeds INSIDE the root fan (the connected roots
      // fill down to ~rootBottom); a detached bulb hanging below the fan reads as
      // "out of bounds". 0.48 depth ≈ mid-root-zone so they blend into the roots.
      var y = seedGroundY + seedDepth * 0.48 + z * 0.20;
      var phase = (stableHash(id) % 628) / 100;
      result.componentById[id] = groves.length + index;
      result.heroPose[id] = { x: x, y: y, z: 0, w: 0, phase: phase, seed: true };
      result.fieldPose[id] = {
        x: x,
        y: y,
        z: z,
        w: 0,
        phase: phase,
        seed: true,
      };
      result.nodeMeta[id] = {
        zone: 'seed',
        bough: 'seed',
        boughGroup: 'seed',
        angle: angle,
        radius: radius,
        componentIndex: groves.length + index,
      };
    });

    // §3 + §5 semantic attachment pass. For every REAL node:
    //  - merge the frozen resolveSemantics contract onto nodeMeta (the ONLY
    //    meta-touched values live here);
    //  - pick the nearest ghost armature anchor consistent with its hemisphere
    //    and record the anchor-relative attach point at radial offset
    //    (1 - coreness) * boughReach * width (§5 item 2);
    //  - relocate uniques onto the single-side dark constellation (§2.2 / §5).
    // Existing crown/root base poses are PRESERVED (the silhouette tests lock
    // them, and coreness is 0 until Agent 2 joins effectiveRank at runtime).
    // The anchor + attach fields let the renderer drape edges and, once rank is
    // joined, pull nodes toward the heartwood.
    function anchorSetFor(hemisphere) {
      if (hemisphere === 'root') return armature.rootAnchors;
      if (hemisphere === 'outside') return armature.outsideAnchors;
      return armature.boughAnchors;
    }
    function reachFor(hemisphere) {
      if (hemisphere === 'root') return ROOT_BOUGH_REACH;
      if (hemisphere === 'outside') return OUTSIDE_BOUGH_REACH;
      return CROWN_BOUGH_REACH;
    }

    nodes.forEach(function (node) {
      var id = node.id;
      var sem = semanticsById[id];
      var meta = result.nodeMeta[id] || {};
      // Merge the frozen contract. boughGroup from local.meta already equals the
      // cluster key resolveSemantics returns; keep the existing one to avoid
      // churn but add the semantic fields the renderer keys off.
      meta.hemisphere = sem.hemisphere;
      meta.coreness = sem.coreness;
      meta.effectiveRank = sem.effectiveRank;
      meta.isUnique = sem.isUnique;
      meta.isSuite = sem.isSuite;
      meta.glyph = sem.glyph;
      if (meta.boughGroup == null) meta.boughGroup = sem.boughGroup;
      result.nodeMeta[id] = meta;

      var basePose = result.fieldPose[id] || result.heroPose[id];
      if (!basePose) return;

      var anchors = anchorSetFor(sem.hemisphere);
      var anchor = anchors.length
        ? nearestAnchor(anchors, basePose.x, basePose.y, basePose.z || 0)
        : null;
      var reach = reachFor(sem.hemisphere) * width;
      var radialOffset = (1 - sem.coreness) * reach;
      meta.anchorKey = anchor ? anchor.key : null;
      meta.anchorRole = anchor ? anchor.role : null;
      meta.boughReach = reach;
      meta.radialOffset = radialOffset;

      if (anchor) {
        // Attach point = anchor pushed outward from the spine by radialOffset
        // along the anchor's radial direction (in the x/z plane).
        var dxs = anchor.x - armature.spineX;
        var dzs = anchor.z || 0;
        var rlen = Math.sqrt(dxs * dxs + dzs * dzs);
        var ux = rlen > 1e-9 ? dxs / rlen : Math.cos(anchor.angle || 0);
        var uz = rlen > 1e-9 ? dzs / rlen : Math.sin(anchor.angle || 0);
        meta.attach = {
          anchorKey: anchor.key,
          x: anchor.x + ux * radialOffset,
          y: anchor.y,
          z: (anchor.z || 0) + uz * radialOffset,
        };

        // §2.2 / §5: uniques are pulled OUT of the wood onto the dark
        // constellation. This is the one hemisphere whose actual pose we move
        // (no uniques exist under Ygg I today, so canonical poses are untouched).
        if (sem.hemisphere === 'outside') {
          var phase = basePose.phase != null ? basePose.phase : (stableHash(id) % 628) / 100;
          result.heroPose[id] = {
            x: meta.attach.x, y: meta.attach.y, z: 0, w: 0,
            phase: phase, outside: true,
          };
          result.fieldPose[id] = {
            x: meta.attach.x, y: meta.attach.y, z: meta.attach.z, w: 0,
            phase: phase, outside: true,
          };
          meta.zone = 'outside';
        } else if (sem.coreness > 0) {
          // §4 heartwood core-pull. Crown/root nodes with effective rank ≥ 2★ are
          // blended toward the heartwood by coreness * CORE_PULL_STRENGTH. 6★
          // (coreness 1) pulls the hardest → deep in the core; 2★ barely moves
          // off its DAG-depth tip. The vertical pull (y → coreY) is unchanged.
          // Fix #3: the RADIAL target is a point on a CYLINDER of radius
          // CORE_MIN_RADIUS*width around the heartwood axis, NOT the axis itself
          // — so high-rank nodes distribute AROUND the core (θ deterministic per
          // node) instead of collapsing onto x=z=0 and pinching every structural
          // route through one collar. This gives the heartwood a barrel of
          // volume. Determinism preserved (coreness + θ are pure functions of
          // rank + id). Coreness 0 (0-1★) skips this branch and keeps the tip.
          var coreY = treeHeight * CORE_Y_RATIO;
          var pull = sem.coreness * CORE_PULL_STRENGTH;
          var coreRadius = CORE_MIN_RADIUS * width;
          var theta = (stableHash(id + ':core-theta') / UINT32_MAX) * TAU;
          var targetX = armature.spineX + coreRadius * Math.cos(theta);
          var targetZ = coreRadius * Math.sin(theta);
          var hx = basePose.x + (targetX - basePose.x) * pull;
          var hy = basePose.y + (coreY - basePose.y) * pull;
          var hz = (basePose.z || 0) + (targetZ - (basePose.z || 0)) * pull;
          result.heroPose[id] = {
            x: hx, y: hy, z: 0, w: 0,
            phase: basePose.phase, coreness: sem.coreness,
          };
          result.fieldPose[id] = {
            x: hx, y: hy, z: hz, w: 0,
            phase: basePose.phase, coreness: sem.coreness,
          };
        }
      }
    });

    // One real edge per target carries the visual wood hierarchy. Every other
    // canonical prerequisite remains a rendered graft edge. This changes
    // emphasis only; result.edges remains the exact normalized DAG.
    nodes.forEach(function (node) {
      var parents = indexes.parents[node.id];
      if (!parents.length) return;
      var targetMeta = result.nodeMeta[node.id];
      var structuralParent = parents.slice().sort(function (a, b) {
        var aMeta = result.nodeMeta[a];
        var bMeta = result.nodeMeta[b];
        var aSameGroup = aMeta && targetMeta && aMeta.boughGroup === targetMeta.boughGroup ? 0 : 1;
        var bSameGroup = bMeta && targetMeta && bMeta.boughGroup === targetMeta.boughGroup ? 0 : 1;
        if (aSameGroup !== bSameGroup) return aSameGroup - bSameGroup;
        var aAngle = aMeta && targetMeta ? circularDistance(aMeta.angle, targetMeta.angle) : Infinity;
        var bAngle = bMeta && targetMeta ? circularDistance(bMeta.angle, targetMeta.angle) : Infinity;
        if (aAngle !== bAngle) return aAngle - bAngle;
        if ((depth[a] || 0) !== (depth[b] || 0)) return (depth[b] || 0) - (depth[a] || 0);
        return compareIds(a, b);
      })[0];
      result.structuralEdgeKeys.push(edgeKey(structuralParent, node.id));
    });
    result.structuralEdgeKeys.sort(compareIds);

    // §5 item 3: structural-edge re-routing. Each structural edge drapes over
    // the skeleton: node → its bough anchor → down the spine → root, so the wood
    // reads as continuous. We emit an ordered waypoint list per structural edge
    // key (referencing ghostPose keys, with the two real endpoints named). Non-
    // structural grafts are NOT listed here — the renderer keeps drawing them as
    // faint direct arcs. Ghost keys here are pointers into ghostPose; they do NOT
    // add nodes/edges/counts (§5.1).
    result.structuralEdgeKeys.forEach(function (key) {
      var split = key.split('\u0000');
      var source = split[0];
      var target = split[1];
      var sMeta = result.nodeMeta[source] || {};
      var tMeta = result.nodeMeta[target] || {};
      // waypoints are objects: real endpoints reference the node id; ghost stops
      // reference a ghostPose key. kind lets the renderer resolve coordinates.
      var route = [{ kind: 'node', id: target }];
      if (tMeta.anchorKey) route.push({ kind: 'ghost', key: tMeta.anchorKey });
      // walk from the target's anchor down its spine attachment toward the root.
      var tAnchorPose = tMeta.anchorKey ? result.ghostPose[tMeta.anchorKey] : null;
      if (tAnchorPose && tAnchorPose.spineKey) {
        route.push({ kind: 'ghost', key: tAnchorPose.spineKey });
      }
      // if the source lives on a different anchor, drape through it too.
      var sAnchorPose = sMeta.anchorKey ? result.ghostPose[sMeta.anchorKey] : null;
      if (sAnchorPose && sAnchorPose.spineKey
        && (!tAnchorPose || sAnchorPose.spineKey !== tAnchorPose.spineKey)) {
        route.push({ kind: 'ghost', key: sAnchorPose.spineKey });
      }
      if (sMeta.anchorKey && sMeta.anchorKey !== tMeta.anchorKey) {
        route.push({ kind: 'ghost', key: sMeta.anchorKey });
      }
      route.push({ kind: 'node', id: source });
      result.structuralRoutes[key] = route;
    });

    return result;
  }

  return {
    buildWorldTreeLayout: buildWorldTreeLayout,
    compute: buildWorldTreeLayout,
    normalizeGraph: normalizeGraph,
    stableHash: stableHash,
    // §3 compatibility seam, exposed so the renderer (Agent 2) and tests can
    // resolve semantics without re-deriving the read table. detectMetaIsYggI
    // must be fed the SOURCE skill objects (with .type), not normalized nodes.
    resolveSemantics: resolveSemantics,
    detectMetaIsYggI: detectMetaIsYggI,
    corenessFromRank: corenessFromRank,
    GHOST_PREFIX: GHOST_PREFIX,
  };
});

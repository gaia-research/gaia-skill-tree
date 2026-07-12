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

  function distributeBoughs(ids, byId) {
    // Branch identity never depends on graph size. Stable golden-angle bases
    // keep existing boughs fixed as intake PRs add skills or entirely new
    // branch keys; there is no hardcoded branch count.
    var subBoughCount = 3;
    var byNode = {};
    var angleByBough = {};
    var tau = Math.PI * 2;
    var goldenAngle = 2.399963229728653;

    ids.slice().sort(compareIds).forEach(function (id) {
      var groupKey = resolveBoughKey(byId[id]);
      var numericGroup = Number(groupKey);
      var baseAngle = Number.isFinite(numericGroup) && Math.floor(numericGroup) === numericGroup
        ? ((numericGroup * goldenAngle * 3 + goldenAngle * 0.5) % tau + tau) % tau
        : stableHash(groupKey + ':bough-sector') / UINT32_MAX * tau;
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
    var groundY = treeHeight * 0.20;
    var crownTopY = -treeHeight * 0.50;
    var rootBottomY = treeHeight * 0.50;
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
        rootProgress = clamp(
          0.18 + 0.82 * (1 - reach) + signedHash(id + ':root-y') * 0.035,
          0.16,
          1
        );
        y = groundY + rootDepth * Math.pow(rootProgress, 0.95);
        var rootEnvelope = width * 0.47 * Math.pow(rootProgress, 1.20);
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
      var y = seedGroundY + seedDepth * 0.79 + z * 0.36;
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
    return result;
  }

  return {
    buildWorldTreeLayout: buildWorldTreeLayout,
    compute: buildWorldTreeLayout,
    normalizeGraph: normalizeGraph,
    stableHash: stableHash,
  };
});

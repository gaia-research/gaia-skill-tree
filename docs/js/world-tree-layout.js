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

  function envelope(t) {
    t = Math.max(0, Math.min(1, t));
    var roots = 0.78 * Math.pow(Math.max(0, 1 - t / 0.48), 1.35);
    var crown = 0.95 * Math.pow(Math.max(0, (t - 0.22) / 0.78), 1.18);
    return 0.14 + roots + crown;
  }

  function layoutComponent(ids, byId, indexes, depth, height, width, treeHeight) {
    var maxPath = ids.reduce(function (value, id) { return Math.max(value, depth[id]); }, 0);
    var clusterKeys = Array.from(new Set(ids.map(function (id) {
      return String(byId[id].cluster);
    }))).sort(function (a, b) {
      return stableHash(a) - stableHash(b) || compareIds(a, b);
    });
    var clusterLane = {};
    clusterKeys.forEach(function (key, index) {
      clusterLane[key] = clusterKeys.length === 1 ? 0 : ((index / (clusterKeys.length - 1)) * 2 - 1) * 0.78;
    });

    var pose = {};
    ids.forEach(function (id) {
      // Combining distance from roots and distance to sinks distributes shallow
      // and deep branches without forcing this DAG into a false single-parent tree.
      var rank = maxPath ? (depth[id] + maxPath - height[id]) / 2 : 0;
      var t = maxPath ? Math.max(0, Math.min(1, rank / maxPath)) : 0;
      var lane = clusterLane[String(byId[id].cluster)] || 0;
      var hashLane = (stableHash(id) / UINT32_MAX) * 2 - 1;
      var branchWidth = envelope(t);
      pose[id] = {
        x: (lane * 0.62 + hashLane * 0.38) * width * 0.5 * branchWidth,
        y: treeHeight * 0.5 - t * treeHeight,
        t: t,
        envelope: branchWidth,
      };
    });

    for (var sweep = 0; sweep < 3; sweep += 1) {
      ids.slice().sort(function (a, b) { return depth[a] - depth[b] || compareIds(a, b); }).forEach(function (id) {
        var linked = indexes.parents[id].filter(function (parent) { return pose[parent]; });
        if (!linked.length) return;
        var mean = linked.reduce(function (sum, parent) { return sum + pose[parent].x; }, 0) / linked.length;
        pose[id].x = pose[id].x * 0.72 + mean * 0.28;
      });
      ids.slice().sort(function (a, b) { return depth[b] - depth[a] || compareIds(a, b); }).forEach(function (id) {
        var linked = indexes.children[id].filter(function (child) { return pose[child]; });
        if (!linked.length) return;
        var mean = linked.reduce(function (sum, child) { return sum + pose[child].x; }, 0) / linked.length;
        pose[id].x = pose[id].x * 0.84 + mean * 0.16;
      });
      ids.forEach(function (id) {
        var limit = width * 0.5 * pose[id].envelope;
        pose[id].x = Math.max(-limit, Math.min(limit, pose[id].x));
      });
    }

    var rows = {};
    ids.forEach(function (id) {
      var row = String(Math.round(pose[id].t * Math.max(2, maxPath * 2)));
      if (!rows[row]) rows[row] = [];
      rows[row].push(id);
    });
    Object.keys(rows).sort(function (a, b) { return Number(a) - Number(b); }).forEach(function (row) {
      var rowIds = rows[row].sort(function (a, b) { return pose[a].x - pose[b].x || compareIds(a, b); });
      if (rowIds.length < 2) return;
      var minEnvelope = rowIds.reduce(function (value, id) { return Math.min(value, pose[id].envelope); }, Infinity);
      var limit = width * 0.5 * minEnvelope;
      var gap = Math.max(6, Math.min(22, limit * 2 / Math.max(1, rowIds.length - 1)));
      for (var i = 1; i < rowIds.length; i += 1) {
        pose[rowIds[i]].x = Math.max(pose[rowIds[i]].x, pose[rowIds[i - 1]].x + gap);
      }
      var shift = Math.max(0, pose[rowIds[rowIds.length - 1]].x - limit);
      if (shift) rowIds.forEach(function (id) { pose[id].x -= shift; });
      shift = Math.max(0, -limit - pose[rowIds[0]].x);
      if (shift) rowIds.forEach(function (id) { pose[id].x += shift; });
    });
    return pose;
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
      version: 1,
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
      var local = layoutComponent(ids, byId, indexes, depth, height, localWidth, localHeight);
      ids.forEach(function (id) {
        var x = local[id].x + offsetX;
        var y = local[id].y + offsetY;
        var phase = (stableHash(id) % 628) / 100;
        var angle = stableHash(componentIndex + ':' + String(byId[id].cluster)) / UINT32_MAX * Math.PI * 2;
        var jitter = stableHash(id + ':depth') / UINT32_MAX * 2 - 1;
        var volume = localWidth * 0.22 * local[id].envelope;
        result.componentById[id] = componentIndex;
        result.heroPose[id] = { x: x, y: y, z: 0, w: 0, phase: phase };
        result.fieldPose[id] = {
          x: x,
          y: y,
          z: Math.sin(angle) * volume + jitter * volume * 0.18,
          w: 0,
          phase: phase,
        };
      });
    });

    // Honest unconnected seeds below the root horizon; no decorative edges.
    var seedIds = result.isolates.slice().sort(function (a, b) {
      return stableHash(a) - stableHash(b) || compareIds(a, b);
    });
    var columns = Math.max(1, Math.min(18, seedIds.length));
    var seedSpan = width * 1.5;
    seedIds.forEach(function (id, index) {
      var column = index % columns;
      var row = Math.floor(index / columns);
      var x = columns === 1 ? 0 : -seedSpan / 2 + column / (columns - 1) * seedSpan;
      var y = treeHeight * 0.5 + 58 + row * 24;
      var phase = (stableHash(id) % 628) / 100;
      result.componentById[id] = groves.length + index;
      result.heroPose[id] = { x: x, y: y, z: 0, w: 0, phase: phase, seed: true };
      result.fieldPose[id] = {
        x: x,
        y: y,
        z: (stableHash(id + ':seed') / UINT32_MAX * 2 - 1) * 42,
        w: 0,
        phase: phase,
        seed: true,
      };
    });
    return result;
  }

  return {
    buildWorldTreeLayout: buildWorldTreeLayout,
    compute: buildWorldTreeLayout,
    normalizeGraph: normalizeGraph,
    stableHash: stableHash,
  };
});

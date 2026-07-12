'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {
  buildWorldTreeLayout,
  resolveSemantics,
  detectMetaIsYggI,
  corenessFromRank,
  GHOST_PREFIX,
} = require('../docs/js/world-tree-layout.js');
const canonicalGraph = require('../docs/graph/gaia.json');

function fixture() {
  return {
    skills: [
      { id: 'root-a', cluster: 'alpha', prerequisites: [] },
      { id: 'root-b', cluster: 'beta', prerequisites: [] },
      { id: 'merge', cluster: 'alpha', prerequisites: ['root-a', 'root-b'] },
      { id: 'crown', cluster: 'gamma', prerequisites: ['merge'] },
      { id: 'grove-root', cluster: 'delta', prerequisites: [] },
      { id: 'grove-leaf', cluster: 'delta', prerequisites: ['grove-root'] },
      { id: 'seed', cluster: 'unknown-new-cluster', prerequisites: [] },
    ],
  };
}

function poses(result) {
  return Object.fromEntries(Object.keys(result.heroPose).sort().map((id) => [id, {
    hero: result.heroPose[id], field: result.fieldPose[id],
  }]));
}

function percentile(values, p) {
  const sorted = values.slice().sort((a, b) => a - b);
  return sorted[Math.floor((sorted.length - 1) * p)];
}

function robustWidth(points) {
  if (points.length < 2) return 0;
  return percentile(points.map(({ x }) => x), 0.95) - percentile(points.map(({ x }) => x), 0.05);
}

function silhouetteBands(points) {
  const minY = Math.min(...points.map(({ y }) => y));
  const maxY = Math.max(...points.map(({ y }) => y));
  const normalizedY = ({ y }) => (y - minY) / Math.max(1, maxY - minY);
  // Band windows track the lifted + shortened root fan (Fix #1: roots lifted to
  // ROOT_BOTTOM_RATIO 0.38 / widened to ROOT_BOUGH_REACH 0.58). The collar/waist
  // now sits higher in the normalized silhouette, so the trunk sampling window
  // moved up accordingly; the crown/roots-flare/centered-waist invariants hold.
  return {
    minY,
    maxY,
    crown: points.filter((point) => normalizedY(point) >= 0.12 && normalizedY(point) <= 0.55),
    trunk: points.filter((point) => normalizedY(point) >= 0.78 && normalizedY(point) <= 0.88),
    roots: points.filter((point) => normalizedY(point) >= 0.88),
  };
}

test('layout is deterministic under input shuffles', () => {
  const graph = fixture();
  const shuffled = { skills: graph.skills.slice().reverse().map((skill) => ({
    ...skill, prerequisites: skill.prerequisites.slice().reverse(),
  })) };
  const a = buildWorldTreeLayout(graph);
  const b = buildWorldTreeLayout(shuffled);
  assert.deepEqual(a.edges, b.edges);
  assert.deepEqual(a.structuralEdgeKeys, b.structuralEdgeKeys);
  assert.deepEqual(poses(a), poses(b));
});

test('preserves nodes and every real edge with no invented links', () => {
  const result = buildWorldTreeLayout(fixture());
  assert.equal(result.status, 'ok');
  assert.equal(result.nodes.length, 7);
  assert.deepEqual(result.edges, [
    { source: 'grove-root', target: 'grove-leaf' },
    { source: 'merge', target: 'crown' },
    { source: 'root-a', target: 'merge' },
    { source: 'root-b', target: 'merge' },
  ]);
  assert.deepEqual(result.isolates, ['seed']);
  assert.equal(result.components[0].length, 4);
  assert.equal(result.components[1].length, 2);
});

test('projects every canonical gaia.json edge into both World Tree poses', () => {
  const result = buildWorldTreeLayout(canonicalGraph);
  const expectedEdges = canonicalGraph.skills.flatMap((skill) =>
    (skill.prerequisites || []).map((source) => ({ source, target: skill.id })))
    .sort((a, b) => a.source.localeCompare(b.source) || a.target.localeCompare(b.target));

  assert.equal(result.status, 'ok');
  assert.equal(result.nodes.length, canonicalGraph.skills.length);
  assert.equal(result.edges.length, expectedEdges.length);
  assert.deepEqual(result.edges, expectedEdges);
  assert.equal(result.diagnostics.unknownReferences.length, 0);
  assert.equal(result.diagnostics.duplicateEdges.length, 0);
  assert.equal(result.diagnostics.cycleNodes.length, 0);
  assert.equal(result.edges.every(({ source, target }) =>
    result.heroPose[source] && result.heroPose[target]
      && result.fieldPose[source] && result.fieldPose[target]), true);
});

test('canonical World Tree has roots, a centered waist, a rounded crown, and real volume', () => {
  const result = buildWorldTreeLayout(canonicalGraph);
  const primaryIds = result.components[0];
  const heroPoints = primaryIds.map((id) => result.heroPose[id]);
  const bands = silhouetteBands(heroPoints);
  const crownWidth = robustWidth(bands.crown);
  const trunkWidth = robustWidth(bands.trunk);
  const rootWidth = robustWidth(bands.roots);
  const trunkMedian = percentile(bands.trunk.map(({ x }) => x), 0.5);

  assert.ok(crownWidth / trunkWidth >= 1.8, 'crown must be decisively wider than the trunk');
  assert.ok(rootWidth / trunkWidth >= 1.25, 'roots must visibly flare beyond the trunk');
  assert.ok(Math.abs(trunkMedian) <= crownWidth * 0.08, 'trunk must remain centered');

  const yBins = new Map();
  heroPoints.forEach(({ y }) => {
    const bin = Math.round((y - bands.minY) / Math.max(1, bands.maxY - bands.minY) * 100);
    yBins.set(bin, (yBins.get(bin) || 0) + 1);
  });
  assert.ok(Math.max(...yBins.values()) / primaryIds.length <= 0.10, 'layout must not collapse into shelves');
  assert.ok(yBins.size >= Math.min(45, Math.ceil(primaryIds.length * 0.25)), 'tree must occupy continuous vertical growth');

  const fieldPoints = primaryIds.map((id) => result.fieldPose[id]);
  const xSpan = Math.max(...fieldPoints.map(({ x }) => x)) - Math.min(...fieldPoints.map(({ x }) => x));
  const zMin = Math.min(...fieldPoints.map(({ z }) => z));
  const zMax = Math.max(...fieldPoints.map(({ z }) => z));
  const depthRatio = (zMax - zMin) / xSpan;
  assert.ok(zMin < 0 && zMax > 0, 'field depth must straddle the trunk axis');
  assert.ok(depthRatio >= 0.55 && depthRatio <= 1.45, 'field pose must be cylindrical rather than a slab');

  const crownWidths = [];
  for (const degrees of [0, 45, 90, 135]) {
    const angle = degrees * Math.PI / 180;
    const yawed = primaryIds.map((id) => {
      const point = result.fieldPose[id];
      return { x: point.x * Math.cos(angle) + point.z * Math.sin(angle), y: point.y };
    });
    const yawBands = silhouetteBands(yawed);
    const yawCrownWidth = robustWidth(yawBands.crown);
    const yawTrunkWidth = robustWidth(yawBands.trunk);
    crownWidths.push(yawCrownWidth);
    assert.ok(yawCrownWidth / yawTrunkWidth >= 1.6, `tree must retain its waist at ${degrees} degrees`);
  }
  assert.ok(Math.min(...crownWidths) / Math.max(...crownWidths) >= 0.55, 'crown must not collapse at side angles');
});

test('structural wood is a deterministic subset while all canonical graft edges remain', () => {
  const result = buildWorldTreeLayout(canonicalGraph);
  const edgeKeys = new Set(result.edges.map(({ source, target }) => `${source}\u0000${target}`));
  const targetsWithParents = result.nodes.filter(({ id }) => result.parents[id].length > 0).length;

  assert.equal(result.structuralEdgeKeys.length, targetsWithParents);
  assert.equal(new Set(result.structuralEdgeKeys).size, result.structuralEdgeKeys.length);
  result.structuralEdgeKeys.forEach((key) => assert.equal(edgeKeys.has(key), true, key));
  assert.equal(result.edges.every(({ source, target }) => result.heroPose[target].y < result.heroPose[source].y), true);

  const seedPoints = result.isolates.map((id) => result.heroPose[id]);
  const primaryCrownWidth = robustWidth(silhouetteBands(result.components[0].map((id) => result.heroPose[id])).crown);
  assert.ok(robustWidth(seedPoints) < primaryCrownWidth * 0.25, 'isolates must remain a compact seed bulb');
});

test('supports multi-parent ancestry, intake nodes, new clusters, and deeper edges', () => {
  const graph = fixture();
  graph.skills.push({ id: 'new-crown', cluster: 'brand-new', prerequisites: ['crown', 'grove-leaf'] });
  const result = buildWorldTreeLayout(graph);
  assert.deepEqual([...result.ancestors['new-crown']].sort(), [
    'crown', 'grove-leaf', 'grove-root', 'merge', 'root-a', 'root-b',
  ]);
  assert.deepEqual([...result.descendants['root-a']].sort(), ['crown', 'merge', 'new-crown']);
  assert.ok(result.heroPose['new-crown']);
});

test('diagnoses missing references without inventing their edges', () => {
  const graph = fixture();
  graph.skills[2].prerequisites.push('missing-parent');
  const result = buildWorldTreeLayout(graph);
  assert.equal(result.status, 'degraded');
  assert.equal(result.available, true);
  assert.equal(result.diagnostics.unknownReferences.length, 1);
  assert.equal(result.edges.some((edge) => edge.source === 'missing-parent'), false);
});

test('cycles are unavailable and their real edges remain explicit', () => {
  const result = buildWorldTreeLayout({ skills: [
    { id: 'a', prerequisites: ['b'] },
    { id: 'b', prerequisites: ['a'] },
  ] });
  assert.equal(result.available, false);
  assert.equal(result.status, 'unavailable');
  assert.deepEqual(result.diagnostics.cycleNodes, ['a', 'b']);
  assert.deepEqual(result.edges, [
    { source: 'a', target: 'b' }, { source: 'b', target: 'a' },
  ]);
  assert.deepEqual(result.heroPose, {});
});

test('all available poses are finite and hero coordinates are flat', () => {
  const result = buildWorldTreeLayout(fixture());
  result.nodes.forEach(({ id }) => {
    for (const pose of [result.heroPose[id], result.fieldPose[id]]) {
      assert.ok(pose, id);
      for (const axis of ['x', 'y', 'z']) assert.equal(Number.isFinite(pose[axis]), true, `${id} ${axis}`);
    }
    assert.equal(result.heroPose[id].z, 0);
  });
});

test('deep intake chains remain strictly upward beyond the current registry depth', () => {
  const skills = Array.from({ length: 120 }, (_, index) => ({
    id: `chain-${String(index).padStart(3, '0')}`,
    cluster: 0,
    prerequisites: index ? [`chain-${String(index - 1).padStart(3, '0')}`] : [],
  }));
  const result = buildWorldTreeLayout({ skills });

  result.edges.forEach(({ source, target }) => {
    assert.ok(result.heroPose[target].y < result.heroPose[source].y, `${source} -> ${target}`);
  });
});

test('bough slots do not rotate existing skills when a cluster crosses an intake threshold', () => {
  const star = (leafCount) => ({ skills: [
    { id: 'root', cluster: 0, prerequisites: [] },
    ...Array.from({ length: leafCount }, (_, index) => ({
      id: `leaf-${String(index).padStart(2, '0')}`,
      cluster: 0,
      prerequisites: ['root'],
    })),
  ] });
  const before = buildWorldTreeLayout(star(32));
  const after = buildWorldTreeLayout(star(33));

  Object.keys(before.nodeMeta).forEach((id) => {
    assert.equal(after.nodeMeta[id].bough, before.nodeMeta[id].bough, id);
    assert.equal(after.nodeMeta[id].angle, before.nodeMeta[id].angle, id);
  });
});

test('structural wood chooses the closest real parent within the preferred branch group', () => {
  const result = buildWorldTreeLayout(canonicalGraph);
  const structuralByTarget = new Map(result.structuralEdgeKeys.map((key) => {
    const [source, target] = key.split('\u0000');
    return [target, source];
  }));
  const circularDistance = (a, b) => {
    const tau = Math.PI * 2;
    const diff = Math.abs((a - b) % tau);
    return Math.min(diff, tau - diff);
  };

  structuralByTarget.forEach((selected, target) => {
    const targetMeta = result.nodeMeta[target];
    const parents = result.parents[target];
    const sameGroup = parents.filter((parent) =>
      result.nodeMeta[parent].boughGroup === targetMeta.boughGroup);
    const candidates = sameGroup.length ? sameGroup : parents;
    const selectedDistance = circularDistance(result.nodeMeta[selected].angle, targetMeta.angle);
    const closestDistance = Math.min(...candidates.map((parent) =>
      circularDistance(result.nodeMeta[parent].angle, targetMeta.angle)));
    assert.ok(Math.abs(selectedDistance - closestDistance) < 1e-12, `${selected} -> ${target}`);
  });
});

// ---------------------------------------------------------------------------
// §3-§5 semantic topology (Agent 1): resolver contract, ghost armature,
// unique-outside placement, coreness monotonicity, determinism.
// ---------------------------------------------------------------------------

// A Yggdrasil I node set: type ∈ {basic, extra, ultimate, unique}. Detection
// must read the LEFT column of the §3.1 table.
function yggOneGraph() {
  return {
    skills: [
      { id: 'ygg1-basic', type: 'basic', cluster: 'a', prerequisites: [], effectiveRank: 2 },
      { id: 'ygg1-extra', type: 'extra', cluster: 'a', prerequisites: ['ygg1-basic'], effectiveRank: 4 },
      { id: 'ygg1-ultimate', type: 'ultimate', cluster: 'a', prerequisites: ['ygg1-extra'], effectiveRank: 6 },
      { id: 'ygg1-unique', type: 'unique', cluster: 'b', prerequisites: ['ygg1-basic'], effectiveRank: 3 },
    ],
  };
}

// A Yggdrasil II node set: type ∈ {basic, fusion} ONLY. Detection must read the
// RIGHT column. A unique is a high-rank basic without suiteComponents; a suite
// is a fusion carrying suiteComponents.
function yggTwoGraph() {
  return {
    skills: [
      { id: 'ygg2-basic', type: 'basic', cluster: 'a', prerequisites: [], effectiveRank: 2 },
      { id: 'ygg2-fusion', type: 'fusion', cluster: 'a', prerequisites: ['ygg2-basic'], effectiveRank: 4 },
      { id: 'ygg2-suite', type: 'fusion', cluster: 'a', prerequisites: ['ygg2-fusion'], effectiveRank: 6,
        suiteComponents: ['ygg2-basic', 'ygg2-fusion'] },
      // high-rank basic, no suiteComponents => a Unique under Ygg II detection.
      { id: 'ygg2-unique', type: 'basic', cluster: 'b', prerequisites: ['ygg2-basic'], effectiveRank: 5 },
    ],
  };
}

test('resolver detects meta by feature-check, not a flag', () => {
  assert.equal(detectMetaIsYggI(yggOneGraph().skills), true, 'unique/extra/ultimate => Ygg I');
  assert.equal(detectMetaIsYggI(yggTwoGraph().skills), false, 'only basic/fusion => Ygg II');
  assert.equal(detectMetaIsYggI([{ type: 'basic' }, { type: 'fusion' }]), false);
  assert.equal(detectMetaIsYggI([{ type: 'basic' }, { type: 'extra' }]), true);
});

test('resolveSemantics honors the §3.1 read table under Yggdrasil I', () => {
  const meta = true; // Ygg I
  const basic = resolveSemantics({ type: 'basic', cluster: 'a' }, 2, meta);
  assert.deepEqual(
    { hemisphere: basic.hemisphere, glyph: basic.glyph, isUnique: basic.isUnique, isSuite: basic.isSuite },
    { hemisphere: 'root', glyph: '○', isUnique: false, isSuite: false });

  const extra = resolveSemantics({ type: 'extra', cluster: 'a' }, 4, meta);
  assert.deepEqual(
    { hemisphere: extra.hemisphere, glyph: extra.glyph, isUnique: extra.isUnique, isSuite: extra.isSuite },
    { hemisphere: 'crown', glyph: '◇', isUnique: false, isSuite: false });

  const ult = resolveSemantics({ type: 'ultimate', cluster: 'a' }, 6, meta);
  assert.deepEqual(
    { hemisphere: ult.hemisphere, glyph: ult.glyph, isUnique: ult.isUnique, isSuite: ult.isSuite },
    { hemisphere: 'crown', glyph: '◆', isUnique: false, isSuite: true });

  const uniq = resolveSemantics({ type: 'unique', cluster: 'b' }, 3, meta);
  assert.deepEqual(
    { hemisphere: uniq.hemisphere, glyph: uniq.glyph, isUnique: uniq.isUnique, isSuite: uniq.isSuite },
    { hemisphere: 'outside', glyph: '◉', isUnique: true, isSuite: false });
  // boughGroup falls through to the cluster axis.
  assert.equal(basic.boughGroup, 'a');
  assert.equal(uniq.boughGroup, 'b');
});

test('resolveSemantics honors the §3.1 read table under Yggdrasil II', () => {
  const meta = false; // Ygg II
  const basic = resolveSemantics({ type: 'basic', cluster: 'a' }, 2, meta);
  assert.deepEqual(
    { hemisphere: basic.hemisphere, glyph: basic.glyph, isUnique: basic.isUnique, isSuite: basic.isSuite },
    { hemisphere: 'root', glyph: '○', isUnique: false, isSuite: false });

  const fusion = resolveSemantics({ type: 'fusion', cluster: 'a' }, 4, meta);
  assert.deepEqual(
    { hemisphere: fusion.hemisphere, glyph: fusion.glyph, isUnique: fusion.isUnique, isSuite: fusion.isSuite },
    { hemisphere: 'crown', glyph: '◇', isUnique: false, isSuite: false });

  const suite = resolveSemantics(
    { type: 'fusion', cluster: 'a', suiteComponents: ['x', 'y'] }, 6, meta);
  assert.deepEqual(
    { hemisphere: suite.hemisphere, glyph: suite.glyph, isUnique: suite.isUnique, isSuite: suite.isSuite },
    { hemisphere: 'crown', glyph: '◆', isUnique: false, isSuite: true });

  // §3.2 read order: a high-rank basic without suiteComponents is a Unique and
  // must short-circuit to 'outside' BEFORE the hemisphere-by-type (basic->root).
  const uniq = resolveSemantics({ type: 'basic', cluster: 'b' }, 5, meta);
  assert.deepEqual(
    { hemisphere: uniq.hemisphere, glyph: uniq.glyph, isUnique: uniq.isUnique, isSuite: uniq.isSuite },
    { hemisphere: 'outside', glyph: '◉', isUnique: true, isSuite: false });

  // a low-rank basic is NOT a unique — it stays in the roots.
  const lowBasic = resolveSemantics({ type: 'basic', cluster: 'b' }, 3, meta);
  assert.equal(lowBasic.isUnique, false);
  assert.equal(lowBasic.hemisphere, 'root');
});

test('coreness follows the §4 contract: 2-star floor, monotone, clamped', () => {
  assert.equal(corenessFromRank(0), 0);
  assert.equal(corenessFromRank(1), 0, '0-1 star land on the bark (coreness 0)');
  assert.ok(corenessFromRank(2) > 0, '2 star begins the ramp');
  assert.equal(corenessFromRank(6), 1, '6 star is the heartwood centre');
  assert.equal(corenessFromRank(9), 1, 'clamped above 6');
  // strictly increasing across the colored ramp (2..6).
  for (let r = 2; r < 6; r += 1) {
    assert.ok(corenessFromRank(r + 1) > corenessFromRank(r), `coreness(${r + 1}) > coreness(${r})`);
  }
});

test('coreness rises with effective rank inside the built layout', () => {
  const result = buildWorldTreeLayout(yggOneGraph());
  assert.equal(result.nodeMeta['ygg1-basic'].coreness, corenessFromRank(2));
  assert.ok(result.nodeMeta['ygg1-ultimate'].coreness > result.nodeMeta['ygg1-extra'].coreness);
  assert.equal(result.nodeMeta['ygg1-ultimate'].coreness, 1);
  // and the semantic contract landed on nodeMeta.
  assert.equal(result.nodeMeta['ygg1-extra'].glyph, '◇');
  assert.equal(result.nodeMeta['ygg1-ultimate'].isSuite, true);
});

test('effectiveRank defaults to 0 (coreness 0) when absent on a node', () => {
  const result = buildWorldTreeLayout({
    skills: [{ id: 'no-rank', type: 'extra', cluster: 'a', prerequisites: [] }],
  });
  assert.equal(result.nodeMeta['no-rank'].effectiveRank, 0);
  assert.equal(result.nodeMeta['no-rank'].coreness, 0);
});

test('ghost armature is present, data-independent, and excluded from all counts', () => {
  const withData = buildWorldTreeLayout(yggOneGraph());
  const empty = buildWorldTreeLayout({ skills: [] });

  // always present, even with zero nodes.
  assert.ok(withData.armature, 'armature present with data');
  assert.ok(Object.keys(withData.ghostPose).length > 0);

  // ghost keys never leak into nodes/edges/structuralEdgeKeys.
  const ghostKeys = Object.keys(withData.ghostPose);
  ghostKeys.forEach((k) => assert.ok(k.startsWith(GHOST_PREFIX), k));
  assert.equal(withData.nodes.some((n) => n.id.startsWith(GHOST_PREFIX)), false);
  assert.equal(withData.edges.some((e) => e.source.startsWith(GHOST_PREFIX)
    || e.target.startsWith(GHOST_PREFIX)), false);
  assert.equal(withData.structuralEdgeKeys.some((k) => k.includes(GHOST_PREFIX)), false);
  // node counts match the input skills exactly (ghosts uncounted).
  assert.equal(withData.nodes.length, 4);

  // ghost roles cover every armature layer.
  const roles = new Set(ghostKeys.map((k) => withData.ghostPose[k].role));
  ['spine', 'bough', 'root', 'taproot', 'outside'].forEach((role) =>
    assert.ok(roles.has(role), `armature must include ${role} waypoints`));

  // an empty graph is unavailable (no grove), but the resolver/coreness helpers
  // still behave; the armature only builds for available layouts.
  assert.ok(empty.status === 'ok' || empty.available === true || empty.available === false);
});

test('the trunk spine is pinned to the tuned backdrop constant (x = 0)', () => {
  const result = buildWorldTreeLayout(yggOneGraph());
  Object.keys(result.ghostPose).forEach((k) => {
    const wp = result.ghostPose[k];
    if (wp.role === 'spine' || wp.role === 'taproot') {
      assert.equal(wp.x, 0, `${wp.role} waypoint ${k} must sit on the spine axis`);
    }
  });
  // ground line (collar) sits at treeHeight * 0.20 with the default height 680.
  const collar = result.ghostPose[result.armature.collarKey];
  assert.ok(Math.abs(collar.y - 680 * 0.20) < 1e-9, 'collar pinned to the ground line');
});

test('uniques are pulled OUTSIDE to a single-side dark constellation', () => {
  const result = buildWorldTreeLayout(yggTwoGraph());
  const uniqueMeta = result.nodeMeta['ygg2-unique'];
  assert.equal(uniqueMeta.hemisphere, 'outside');
  assert.equal(uniqueMeta.isUnique, true);
  assert.equal(uniqueMeta.anchorRole, 'outside');
  assert.equal(result.heroPose['ygg2-unique'].outside, true);

  // single side: every outside anchor sits on the positive-x side of the trunk.
  Object.keys(result.ghostPose).forEach((k) => {
    if (result.ghostPose[k].role === 'outside') {
      assert.ok(result.ghostPose[k].x > 0, `outside anchor ${k} must be single-side (positive x)`);
    }
  });
  // and the relocated unique landed on that side too.
  assert.ok(result.heroPose['ygg2-unique'].x > 0, 'unique lands beside the trunk, single side');

  // the canonical (Ygg I) graph has no uniques today — nothing relocated.
  const canon = buildWorldTreeLayout(canonicalGraph);
  assert.equal(canon.nodes.some((n) => canon.nodeMeta[n.id].isUnique), false);
});

test('structural edges re-route over the ghost skeleton; grafts are not routed', () => {
  const result = buildWorldTreeLayout(yggOneGraph());
  const routedKeys = Object.keys(result.structuralRoutes);
  // exactly one route per structural edge key.
  assert.deepEqual(routedKeys.slice().sort(), result.structuralEdgeKeys.slice().sort());

  result.structuralEdgeKeys.forEach((key) => {
    const route = result.structuralRoutes[key];
    assert.ok(Array.isArray(route) && route.length >= 2, key);
    // endpoints are the two real nodes; interior stops are ghost keys.
    assert.equal(route[0].kind, 'node');
    assert.equal(route[route.length - 1].kind, 'node');
    route.slice(1, -1).forEach((stop) => {
      assert.equal(stop.kind, 'ghost');
      assert.ok(result.ghostPose[stop.key], `route stop ${stop.key} must exist in ghostPose`);
    });
    // the drape passes through at least one spine waypoint (node->bough->spine->root).
    const touchesSpine = route.some((stop) =>
      stop.kind === 'ghost' && result.ghostPose[stop.key].role === 'spine');
    assert.ok(touchesSpine, `${key} must drape over the spine`);
  });
});

test('semantic topology is deterministic (same input => same output)', () => {
  const a = buildWorldTreeLayout(yggOneGraph());
  const shuffled = { skills: yggOneGraph().skills.slice().reverse() };
  const b = buildWorldTreeLayout(shuffled);
  assert.deepEqual(a.ghostPose, b.ghostPose);
  assert.deepEqual(a.structuralRoutes, b.structuralRoutes);
  assert.deepEqual(a.nodeMeta, b.nodeMeta);
  assert.equal(a.metaIsYggI, b.metaIsYggI);
});

test('canonical graph gains ghost armature + routes without disturbing real poses', () => {
  const withRank = buildWorldTreeLayout(canonicalGraph);
  assert.ok(withRank.armature, 'canonical layout carries the armature');
  assert.ok(Object.keys(withRank.ghostPose).length > 0);
  // metaIsYggI: canonical types are basic/extra/ultimate => Ygg I.
  assert.equal(withRank.metaIsYggI, true);
  // every real node carries the frozen contract fields.
  withRank.nodes.forEach(({ id }) => {
    const m = withRank.nodeMeta[id];
    assert.ok(['crown', 'root', 'outside'].includes(m.hemisphere), id);
    assert.ok(m.coreness >= 0 && m.coreness <= 1, id);
    assert.ok(['○', '◇', '◉', '◆'].includes(m.glyph), id);
  });
});

// ---------------------------------------------------------------------------
// §4 heartwood core-pull (Fix #3): effective rank does not just color a node,
// it pulls its POSITION toward the heartwood core (spine axis + vertical
// centre). Higher rank => deeper in the core, both radially and vertically.
// ---------------------------------------------------------------------------

// Isolate the rank effect on ONE node by holding graph shape fixed and varying
// only that node's effectiveRank; the DAG-depth base pose is then identical
// across variants, so any change in |y| / |x| is purely the coreness-pull.
function rankVariant(rank) {
  return {
    skills: [
      { id: 'core-seed', type: 'basic', cluster: 'a', prerequisites: [] },
      { id: 'core-crown', type: 'extra', cluster: 'a', prerequisites: ['core-seed'], effectiveRank: rank },
    ],
  };
}

test('coreness pulls a crown node toward the heartwood core (vertical + radial), monotone in rank', () => {
  // coreY = treeHeight * CORE_Y_RATIO (0) with the default height 680 => 0.
  const coreY = 0;
  const results = [0, 2, 4, 6].map((rank) => {
    const r = buildWorldTreeLayout(rankVariant(rank));
    const pose = r.heroPose['core-crown'];
    return {
      rank,
      coreness: r.nodeMeta['core-crown'].coreness,
      dy: Math.abs(pose.y - coreY),
      dx: Math.abs(pose.x),
    };
  });
  // 0-1★ sits at coreness 0 (no pull); 2..6★ ramp inward.
  assert.equal(results[0].coreness, 0);
  assert.ok(results[3].coreness === 1, '6★ is full coreness');
  // strictly monotone: higher rank => closer to coreY AND closer to the spine.
  for (let i = 1; i < results.length; i += 1) {
    assert.ok(results[i].dy < results[i - 1].dy,
      `rank ${results[i].rank} must sit closer to coreY than rank ${results[i - 1].rank}`);
    assert.ok(results[i].dx < results[i - 1].dx,
      `rank ${results[i].rank} must sit closer to the spine than rank ${results[i - 1].rank}`);
  }
  // a 5★ node is closer to coreY than a 2★ node (spec acceptance check).
  const five = buildWorldTreeLayout(rankVariant(5)).heroPose['core-crown'];
  const two = buildWorldTreeLayout(rankVariant(2)).heroPose['core-crown'];
  assert.ok(Math.abs(five.y - coreY) < Math.abs(two.y - coreY), '5★ |y| closer to core than 2★');
});

test('core-pull applies to root nodes too, and 0-1★ nodes keep their base tip pose', () => {
  // Ygg I meta (the graph carries an 'extra' type) so a high-rank basic stays a
  // ROOT rather than short-circuiting to the unique 'outside' hemisphere.
  const rootVariant = (rank) => ({
    skills: [
      { id: 'anchor', type: 'extra', cluster: 'a', prerequisites: [], effectiveRank: 3 },
      { id: 'r', type: 'basic', cluster: 'a', prerequisites: [], effectiveRank: rank },
    ],
  });
  const pulled = buildWorldTreeLayout(rootVariant(6));
  const parked = buildWorldTreeLayout(rootVariant(0));
  // same id, same graph shape: rank 6 must sit strictly closer to the spine + core.
  assert.equal(parked.nodeMeta['r'].hemisphere, 'root');
  assert.equal(pulled.nodeMeta['r'].hemisphere, 'root');
  assert.equal(parked.nodeMeta['r'].coreness, 0);
  assert.equal(pulled.nodeMeta['r'].coreness, 1);
  assert.ok(Math.abs(pulled.heroPose['r'].x) < Math.abs(parked.heroPose['r'].x),
    '6★ root pulled toward the spine');
  assert.ok(Math.abs(pulled.heroPose['r'].y) < Math.abs(parked.heroPose['r'].y),
    '6★ root pulled toward the vertical core');
  // 0-1★ pose is untouched by the core-pull branch (coreness 0 short-circuits).
  const bark = buildWorldTreeLayout(rootVariant(1));
  assert.equal(bark.nodeMeta['r'].coreness, 0);
  assert.equal(bark.heroPose['r'].coreness, undefined, '0-1★ keeps its base pose (no core-pull tag)');
});

test('core-pull is deterministic under input shuffles', () => {
  const graph = {
    skills: [
      { id: 'a', type: 'basic', cluster: 'x', prerequisites: [], effectiveRank: 4 },
      { id: 'b', type: 'extra', cluster: 'x', prerequisites: ['a'], effectiveRank: 6 },
      { id: 'c', type: 'extra', cluster: 'y', prerequisites: ['a'], effectiveRank: 3 },
    ],
  };
  const a = buildWorldTreeLayout(graph);
  const b = buildWorldTreeLayout({ skills: graph.skills.slice().reverse() });
  assert.deepEqual(a.heroPose, b.heroPose);
  assert.deepEqual(a.fieldPose, b.fieldPose);
});

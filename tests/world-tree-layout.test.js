'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { buildWorldTreeLayout } = require('../docs/js/world-tree-layout.js');
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
  return {
    minY,
    maxY,
    crown: points.filter((point) => normalizedY(point) >= 0.12 && normalizedY(point) <= 0.55),
    trunk: points.filter((point) => normalizedY(point) >= 0.58 && normalizedY(point) <= 0.84),
    roots: points.filter((point) => normalizedY(point) >= 0.84),
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

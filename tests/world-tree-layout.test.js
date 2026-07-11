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

test('layout is deterministic under input shuffles', () => {
  const graph = fixture();
  const shuffled = { skills: graph.skills.slice().reverse().map((skill) => ({
    ...skill, prerequisites: skill.prerequisites.slice().reverse(),
  })) };
  const a = buildWorldTreeLayout(graph);
  const b = buildWorldTreeLayout(shuffled);
  assert.deepEqual(a.edges, b.edges);
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

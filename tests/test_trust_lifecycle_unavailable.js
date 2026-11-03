'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {buildTrustLifecycleViewModel, renderLifecycleSection} = require('../docs/js/trust-lifecycle.js');
const fixtures = require('./fixtures/synthetic_trust_lifecycle_fixtures.js');

test('untrusted metadata cannot activate the lifecycle panel', () => {
  const forged = {id: 'someone/example', trustLifecycle: {
    snapshot: {snapshotId: 'fake', evaluatedAtUTC: '2026-01-01', approvedBy: 'fake', approvalRef: 'https://example.org/'},
    approvedStanding: {status: 'degraded', approvedStars: 1},
    origin: {currentOriginHandle: 'someone', contested: true},
    challenges: []
  }};
  for (const entry of [null, {}, forged, ...Object.values(fixtures)]) {
    assert.equal(buildTrustLifecycleViewModel(entry), null);
    const mount = {innerHTML: 'stale'};
    renderLifecycleSection(mount, entry);
    assert.equal(mount.innerHTML, '');
  }
  assert.equal(forged.trustLifecycle.origin.currentOriginHandle, 'someone');
});

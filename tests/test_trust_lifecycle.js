'use strict';

// DTOs below are produced by real Python code through disposable synthetic
// in-process ports. They are not evidence of an active issuer or browser render.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const lifecycle = require('../docs/js/trust-lifecycle.js');
const fixtures = JSON.parse(execFileSync('python3', [path.join(__dirname, 'fixtures/lifecycle_dto_test_ports.py')], {encoding: 'utf8'}));
const clone = value => JSON.parse(JSON.stringify(value));

test('safe URL and escaping primitives', () => {
  assert.equal(lifecycle.isSafeHttps('https://example.org/receipt'), true);
  for (const url of ['http://example.org', 'javascript:alert(1)', '', null]) assert.equal(lifecycle.isSafeHttps(url), false);
  assert.equal(lifecycle.esc('<b>"&'), '&lt;b&gt;&quot;&amp;');
});

test('real producer scoped challenge preserves baseline and avoids Origin contest', () => {
  const vm = lifecycle.buildTrustLifecycleViewModel(fixtures.scoped);
  assert.ok(vm);
  assert.equal(vm.standing.key, 'adjudication-pending');
  assert.equal(vm.origin.status, 'held');
  assert.equal(vm.origin.isContested, false);
  assert.equal(vm.challenges.length, 1);
  assert.equal(vm.challenges[0].materialToOrigin, false);
  const html = lifecycle.renderTrustLifecycleHtml(vm);
  assert.match(html, /\[Scoped Capability Challenge\]/);
  assert.match(html, /<details class="se-lc-challenge-item/);
  assert.match(html, /verified-publication/);
  assert.match(html, /Published baseline: 3&#9733; · TM 72/);
});

test('material challenge keeps incumbent and numeric decision', () => {
  const vm = lifecycle.buildTrustLifecycleViewModel(fixtures.material);
  assert.ok(vm);
  assert.equal(vm.origin.status, 'contested');
  assert.equal(vm.origin.handle, 'author');
  assert.equal(vm.standing.approvedStars, 3);
  assert.equal(vm.standing.approvedTm, 72);
  assert.match(lifecycle.renderTrustLifecycleHtml(vm), /\[Material Origin Challenge\]/);
});

test('technical resolution preserves original event and does not restore numeric standing', () => {
  const vm = lifecycle.buildTrustLifecycleViewModel(fixtures.resolved);
  assert.ok(vm);
  assert.equal(vm.standing.key, 'recalibration-pending');
  assert.equal(vm.standing.approvedStars, 3);
  assert.equal(vm.origin.status, 'held');
  assert.equal(vm.challenges[0].history.length, 2);
  const html = lifecycle.renderTrustLifecycleHtml(vm);
  assert.match(html, /verified-publication/);
  assert.match(html, /technical-resolution/);
  assert.match(html, /Technical Resolution Proof/);
});

test('resolution metadata alone cannot assert recalibration pending', () => {
  const entry = clone(fixtures.resolved);
  entry.trustLifecycle.consequence = {kind: 'unavailable'};
  entry.trustLifecycle.challenges[0].resolution.recalibrationPending = true;
  const vm = lifecycle.buildTrustLifecycleViewModel(entry);
  assert.ok(vm);
  assert.equal(vm.standing.recalibrationPending, null);
  assert.doesNotMatch(lifecycle.renderTrustLifecycleHtml(vm), /Canonical trust recalibration is pending/);
});

test('missing consequence stays unknown, not a fabricated incumbent or rank', () => {
  const vm = lifecycle.buildTrustLifecycleViewModel(fixtures.unknown);
  assert.ok(vm);
  assert.equal(vm.origin.status, 'unknown');
  assert.equal(vm.standing.approvedStars, null);
  const html = lifecycle.renderTrustLifecycleHtml(vm);
  assert.match(html, /\[Unknown\] Origin Unavailable/);
  assert.doesNotMatch(html, /\[Held\] Origin Held/);
});

test('missing, old, forged display metadata, unknown version and foreign subject fail closed', () => {
  for (const entry of [null, {}, {id:'x', trustLifecycle:{snapshot:{approvedBy:'founder', approvalRef:'https://example.org'}, approvedStanding:{status:'degraded'}}}]) {
    assert.equal(lifecycle.buildTrustLifecycleViewModel(entry), null);
  }
  for (const mutate of [
    e => e.trustLifecycle.contract = 'gaia-trust-lifecycle/v9',
    e => e.trustLifecycle.subjectId = 'foreign/id',
    e => e.trustLifecycle.genericSkillRef = 'foreign',
    e => e.trustLifecycle.challenges.push(clone(e.trustLifecycle.challenges[0])),
    e => e.trustLifecycle.challenges[0].materialToOrigin = 'true',
    e => e.trustLifecycle.challenges[0].status = 'narrowed',
    e => e.trustLifecycle.challenges[0].history = [],
    e => e.trustLifecycle.challenges[0].history[0] = null,
    e => e.trustLifecycle.challenges[0].history[0].challenge_id = 'foreign',
    e => e.trustLifecycle.materialOriginContested = false,
    e => e.trustLifecycle.consequence.kind = 'forged',
    e => e.trustLifecycle.consequence.stars = 6,
  ]) {
    const entry = clone(fixtures.material); mutate(entry);
    assert.equal(lifecycle.buildTrustLifecycleViewModel(entry), null);
  }
});

test('untrusted content is escaped and unsafe links are rejected', () => {
  const entry = clone(fixtures.scoped);
  entry.trustLifecycle.challenges[0].claim = '<img src=x onerror=alert(1)>';
  const html = lifecycle.renderTrustLifecycleHtml(lifecycle.buildTrustLifecycleViewModel(entry));
  assert.match(html, /&lt;img/);
  assert.doesNotMatch(html, /<img/);
  entry.trustLifecycle.challenges[0].verifier.receiptUrl = 'javascript:alert(1)';
  assert.equal(lifecycle.buildTrustLifecycleViewModel(entry), null);
});

test('mount clears invalid inputs and renders accessible native section', () => {
  const mount = {innerHTML: 'old'};
  lifecycle.renderLifecycleSection(mount, {});
  assert.equal(mount.innerHTML, '');
  lifecycle.renderLifecycleSection(mount, fixtures.scoped);
  assert.match(mount.innerHTML, /<section class="se-lc-section" aria-labelledby="seLifecycleHeading">/);
  assert.match(mount.innerHTML, /<summary class="se-lc-challenge-summary" tabindex="0">/);
});

test('native Explorer entrypoint and sections remain wired', () => {
  const explorer = fs.readFileSync(path.join(__dirname, '../docs/js/skill-explorer.js'), 'utf8');
  const named = fs.readFileSync(path.join(__dirname, '../docs/named/index.html'), 'utf8');
  assert.match(explorer, /_safeRender\('Trust Lifecycle', 'se-tm'/);
  assert.match(explorer, /renderLifecycleSection\('se-tm', ns\)/);
  for (const section of ['Install', 'Docs', 'Upgrade', 'Timeline']) assert.ok(explorer.includes("_safeRender('" + section + "'"));
  for (const file of ['named-skills.js', 'trust-lifecycle.js', 'skill-explorer.js']) assert.ok(named.includes(file));
});

'use strict';

// DTOs below are produced by real Python code through disposable synthetic
// in-process ports. They are not evidence of an active issuer or browser render.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vmModule = require('node:vm');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const lifecycle = require('../docs/js/trust-lifecycle.js');
const fixtures = JSON.parse(execFileSync('python3', [path.join(__dirname, 'fixtures/lifecycle_dto_test_ports.py')], {encoding: 'utf8'}));
const clone = value => JSON.parse(JSON.stringify(value));
const read = file => fs.readFileSync(path.join(__dirname, file), 'utf8');
const mockMount = () => ({innerHTML: ''});
// Only the scoped fixture is a pending challenge with a non-material scope; material is pending+material;
// resolved is resolved-by-upstream-improvement with a technical-resolution event.
const withoutChallenges = entry => {
  const copy = clone(entry);
  copy.trustLifecycle.challenges = [];
  copy.trustLifecycle.materialOriginContested = false;
  return copy;
};
const rebutted = () => {
  const copy = clone(fixtures.resolved);
  copy.trustLifecycle.challenges[0].status = 'technically-rebutted';
  copy.trustLifecycle.challenges[0].resolution.disposition = 'technically-rebutted';
  return copy;
};

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
  assert.match(html, /data-chip="open-scoped"[^>]*>.*?Scoped challenge/);
  assert.match(html, /<details class="lc-bout__details">/);
  assert.match(html, /data-event="verified-publication"/);
  assert.match(html, /aria-label="Trust Magnitude 72, 3 of 6 stars, published baseline"/);
  assert.match(html, /<span class="lc-meter" data-kind="current-baseline"/);
  assert.match(html, /<span class="lc-num">72<\/span>/);
});

test('material challenge keeps incumbent and numeric decision', () => {
  const vm = lifecycle.buildTrustLifecycleViewModel(fixtures.material);
  assert.ok(vm);
  assert.equal(vm.origin.status, 'contested');
  assert.equal(vm.origin.handle, 'author');
  assert.equal(vm.standing.approvedStars, 3);
  assert.equal(vm.standing.approvedTm, 72);
  assert.match(lifecycle.renderTrustLifecycleHtml(vm), /data-chip="open-material"[^>]*>.*?Contests Origin/);
});

test('technical resolution preserves original event and does not restore numeric standing', () => {
  const vm = lifecycle.buildTrustLifecycleViewModel(fixtures.resolved);
  assert.ok(vm);
  assert.equal(vm.standing.key, 'recalibration-pending');
  assert.equal(vm.standing.approvedStars, 3);
  assert.equal(vm.origin.status, 'held');
  assert.equal(vm.challenges[0].history.length, 2);
  const html = lifecycle.renderTrustLifecycleHtml(vm);
  assert.match(html, /data-event="verified-publication"/);
  assert.match(html, /data-event="technical-resolution"/);
  assert.match(html, /Resolution proof/);
});

test('resolution metadata alone cannot assert recalibration pending', () => {
  const entry = clone(fixtures.resolved);
  entry.trustLifecycle.consequence = {kind: 'unavailable'};
  entry.trustLifecycle.challenges[0].resolution.recalibrationPending = true;
  const vm = lifecycle.buildTrustLifecycleViewModel(entry);
  assert.ok(vm);
  assert.equal(vm.standing.recalibrationPending, null);
  const html = lifecycle.renderTrustLifecycleHtml(vm);
  assert.doesNotMatch(html, /data-chip="recalibration"/);
  assert.doesNotMatch(html, /data-recal/);
  assert.doesNotMatch(html, /recalibration pending/i);
});

test('missing consequence stays unknown, not a fabricated incumbent or rank', () => {
  const vm = lifecycle.buildTrustLifecycleViewModel(fixtures.unknown);
  assert.ok(vm);
  assert.equal(vm.origin.status, 'unknown');
  assert.equal(vm.standing.approvedStars, null);
  const html = lifecycle.renderTrustLifecycleHtml(vm);
  assert.match(html, /data-chip="origin-unknown"/);
  assert.match(html, /aria-label="Origin unavailable"/);
  assert.doesNotMatch(html, /data-chip="origin-held"/);
  assert.doesNotMatch(html, /lc-wreath__avatar/);
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
  assert.match(html, /&lt;img src=x onerror=alert\(1\)&gt;/);
  // The only raw <img> is the Origin avatar the renderer builds itself.
  assert.doesNotMatch(html, /<img(?! class="lc-wreath__avatar" src="https:\/\/github\.com\/)/);
  entry.trustLifecycle.challenges[0].verifier.receiptUrl = 'javascript:alert(1)';
  assert.equal(lifecycle.buildTrustLifecycleViewModel(entry), null);
});

test('mount clears invalid inputs and renders accessible native section', () => {
  const mount = {innerHTML: 'old'};
  lifecycle.renderLifecycleSection(mount, {});
  assert.equal(mount.innerHTML, '');
  lifecycle.renderLifecycleSection(mount, fixtures.scoped);
  assert.match(mount.innerHTML, /<section class="lc-panel" data-lc-state="open-scoped" aria-labelledby="seLifecycleHeading">/);
  assert.match(mount.innerHTML, /<summary class="lc-bout__sum">/);
});

test('native Explorer entrypoint and sections remain wired', () => {
  const explorer = fs.readFileSync(path.join(__dirname, '../docs/js/skill-explorer.js'), 'utf8');
  const named = fs.readFileSync(path.join(__dirname, '../docs/named/index.html'), 'utf8');
  assert.match(explorer, /_safeRender\('Trust Lifecycle', 'se-tm'/);
  assert.match(explorer, /renderLifecycleSection\('se-tm', ns\)/);
  for (const section of ['Install', 'Docs', 'Upgrade', 'Timeline']) assert.ok(explorer.includes("_safeRender('" + section + "'"));
  for (const file of ['named-skills.js', 'trust-lifecycle.js', 'skill-explorer.js']) assert.ok(named.includes(file));
});

// ── Defect 1: baseline/decision must agree with the Explorer hero TM ────────

test('hero TM fallback chain in skill-explorer.js is what the validator mirrors', () => {
  const explorer = read('../docs/js/skill-explorer.js');
  assert.match(explorer, /trustMagnitude: ns\.trustMagnitude \|\| ns\.overallTrustMagnitude \|\| ns\.trustNumber \|\| null/);
});

test('original repro: TM 72 consequence next to overallTrustMagnitude 999 is rejected for both kinds', () => {
  for (const source of [fixtures.scoped, fixtures.material]) {  // current-baseline, approved-decision
    assert.ok(lifecycle.buildTrustLifecycleViewModel(source));
    const entry = clone(source); entry.overallTrustMagnitude = 999;
    assert.equal(lifecycle.buildTrustLifecycleViewModel(entry), null);
    const mount = mockMount(); mount.innerHTML = 'stale';
    lifecycle.renderLifecycleSection(mount, entry);
    assert.equal(mount.innerHTML, '');
  }
});

test('every displayed TM field and fallthrough is reconciled for both consequence kinds', () => {
  for (const source of [fixtures.scoped, fixtures.material]) {
    const mutations = [
      e => { e.overallTrustMagnitude = 72; e.trustNumber = 72.005; },          // all agree
      e => { delete e.trustMagnitude; e.overallTrustMagnitude = 72; },         // hero falls through, agrees
    ];
    for (const mutate of mutations) {
      const entry = clone(source); mutate(entry);
      assert.ok(lifecycle.buildTrustLifecycleViewModel(entry));
    }
    const rejections = [
      e => { delete e.trustMagnitude; e.overallTrustMagnitude = 999; },        // hero would show 999
      e => { e.trustMagnitude = 0; e.overallTrustMagnitude = 72; },            // 0 falls through to 72, but 0 is displayed data
      e => { e.trustNumber = 999; },
      e => { e.trustMagnitude = 73; },
      e => { e.overallTrustMagnitude = 'abc'; },
      e => { e.trustMagnitude = '72'; },
      e => { e.trustMagnitude = true; },
      e => { e.trustMagnitude = NaN; },
    ];
    for (const mutate of rejections) {
      const entry = clone(source); mutate(entry);
      assert.equal(lifecycle.buildTrustLifecycleViewModel(entry), null);
    }
  }
});

test('shared hero matrix accepts and rejects exactly like the Python producer', () => {
  const matrix = JSON.parse(read('fixtures/lifecycle_hero_matrix.json'));
  assert.ok(matrix.cases.length >= 40);
  for (const source of [fixtures.scoped, fixtures.material]) {  // current-baseline, approved-decision
    for (const c of matrix.cases) {
      const entry = clone(source);
      for (const key of ['level', 'trustMagnitude', 'overallTrustMagnitude', 'trustNumber']) delete entry[key];
      Object.assign(entry, c.entry);
      const accepted = lifecycle.buildTrustLifecycleViewModel(entry) !== null;
      assert.equal(accepted, c.accept, source.trustLifecycle.consequence.kind + ': ' + c.name);
    }
  }
});

test('rank contradiction with the hero level is rejected for both consequence kinds', () => {
  for (const source of [fixtures.scoped, fixtures.material]) {
    const entry = clone(source); entry.level = '4★';
    assert.equal(lifecycle.buildTrustLifecycleViewModel(entry), null);
  }
});

// ── Defect 2: malformed v1 DTOs fail closed ────────────────────────────────

const malformations = {
  'deleted pinnedSha': e => { delete e.trustLifecycle.challenges[0].pinnedSha; },
  'deleted claimId': e => { delete e.trustLifecycle.challenges[0].claimId; },
  'blank pinnedVersion': e => { e.trustLifecycle.challenges[0].pinnedVersion = '  '; },
  'deleted behaviorId': e => { delete e.trustLifecycle.challenges[0].behaviorId; },
  'deleted contributorId': e => { delete e.trustLifecycle.challenges[0].contributorId; },
  'deleted contributorNoticeRef': e => { delete e.trustLifecycle.challenges[0].contributorNoticeRef; },
  'deleted receipt_id': e => { delete e.trustLifecycle.challenges[0].history[0].receipt_id; },
  'deleted receipt_digest': e => { delete e.trustLifecycle.challenges[0].history[0].receipt_digest; },
  'deleted transcript_digest': e => { delete e.trustLifecycle.challenges[0].history[0].transcript_digest; },
  'deleted receipt method': e => { delete e.trustLifecycle.challenges[0].history[0].method; },
  'garbage event date': e => { e.trustLifecycle.challenges[0].history[0].at_utc = 'not-a-date'; },
  'impossible calendar date': e => { const c = e.trustLifecycle.challenges[0]; c.verifiedAtUTC = c.history[0].at_utc = '2026-02-31T00:00:00Z'; },
  'non-UTC offset date': e => { const c = e.trustLifecycle.challenges[0]; c.verifiedAtUTC = c.history[0].at_utc = '2026-10-25T12:00:00+08:00'; },
  'date-only event date': e => { const c = e.trustLifecycle.challenges[0]; c.verifiedAtUTC = c.history[0].at_utc = '2026-10-25'; },
  'garbage verifiedAtUTC': e => { e.trustLifecycle.challenges[0].verifiedAtUTC = 'garbage'; },
  'opening event time differs from verifiedAtUTC': e => { e.trustLifecycle.challenges[0].history[0].at_utc = '2026-10-26T12:00:00Z'; },
  'opening actor differs from verifier': e => { e.trustLifecycle.challenges[0].history[0].actor = 'someone-else'; },
  'verifier method differs from receipt method': e => { e.trustLifecycle.challenges[0].verifier.verificationMethod = 'benchmark-replay'; },
  'resolution on a pending challenge': e => {
    e.trustLifecycle.challenges[0].resolution = {disposition: 'technically-rebutted', resolvedAtUTC: '2026-10-27T00:00:00Z',
      verifierId: 'independent-reviewer', receiptUrl: 'https://example.org/receipts/x'};
  },
  'null resolution on a pending challenge': e => { e.trustLifecycle.challenges[0].resolution = null; },
  'foreign subjectId on challenge': e => { e.trustLifecycle.challenges[0].subjectId = 'foreign/id'; },
  'non-null non-string linkedChallengeId': e => { e.trustLifecycle.challenges[0].linkedChallengeId = 7; },
};
for (const [name, mutate] of Object.entries(malformations)) {
  test('pending v1 DTO fails closed: ' + name, () => {
    const entry = clone(fixtures.material); mutate(entry);
    assert.equal(lifecycle.buildTrustLifecycleViewModel(entry), null);
    const mount = mockMount(); mount.innerHTML = 'stale';
    lifecycle.renderLifecycleSection(mount, entry);
    assert.equal(mount.innerHTML, '');
  });
}

const resolvedMalformations = {
  'resolved without resolution object': e => { delete e.trustLifecycle.challenges[0].resolution; },
  'resolution disposition differs from status': e => { e.trustLifecycle.challenges[0].resolution.disposition = 'technically-rebutted'; },
  'resolution date differs from closing event': e => { e.trustLifecycle.challenges[0].resolution.resolvedAtUTC = '2026-10-28T00:00:00Z'; },
  'resolution verifier differs from closing actor': e => { e.trustLifecycle.challenges[0].resolution.verifierId = 'someone-else'; },
  'resolution receipt unsafe': e => { e.trustLifecycle.challenges[0].resolution.receiptUrl = 'javascript:alert(1)'; },
  'closing event garbage date': e => { const c = e.trustLifecycle.challenges[0]; c.history[1].at_utc = c.resolution.resolvedAtUTC = 'garbage'; },
  'closing event predates opening': e => { const c = e.trustLifecycle.challenges[0]; c.history[1].at_utc = c.resolution.resolvedAtUTC = '2026-10-24T00:00:00Z'; },
  'closing event deleted receipt_digest': e => { delete e.trustLifecycle.challenges[0].history[1].receipt_digest; },
  'closing event wrong type': e => { e.trustLifecycle.challenges[0].history[1].event_type = 'verified-publication'; },
  'closing event foreign challenge_id': e => { e.trustLifecycle.challenges[0].history[1].challenge_id = 'foreign'; },
  'resolved history truncated to one event': e => { e.trustLifecycle.challenges[0].history.pop(); },
};
for (const [name, mutate] of Object.entries(resolvedMalformations)) {
  test('resolved v1 DTO fails closed: ' + name, () => {
    const entry = clone(fixtures.resolved); mutate(entry);
    assert.equal(lifecycle.buildTrustLifecycleViewModel(entry), null);
    const mount = mockMount(); mount.innerHTML = 'stale';
    lifecycle.renderLifecycleSection(mount, entry);
    assert.equal(mount.innerHTML, '');
  });
}

test('well-formed fixtures still pass the strict validator (guards against over-rejection)', () => {
  for (const entry of Object.values(fixtures)) assert.ok(lifecycle.buildTrustLifecycleViewModel(entry));
  assert.ok(lifecycle.buildTrustLifecycleViewModel(rebutted()));
});

// ── Restored coverage from the pre-rewrite suite (states v1 still supports) ─

test('isSafeHttps rejects every non-https scheme and non-string', () => {
  assert.strictEqual(lifecycle.isSafeHttps('https://github.com/gaia-research/gaia-skill-tree/issues/100'), true);
  for (const url of ['data:text/html,<html>', 'ftp://files.example.com', 'http://insecure.com', undefined, 12345, 'https://', 'https://a b']) {
    assert.strictEqual(lifecycle.isSafeHttps(url), false);
  }
});

test('esc escapes quotes and tolerates null/undefined', () => {
  assert.strictEqual(lifecycle.esc('<script>alert("xss")</script>'), '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;');
  assert.strictEqual(lifecycle.esc("Tom & 'Jerry'"), 'Tom &amp; &#39;Jerry&#39;');
  assert.strictEqual(lifecycle.esc(null), '');
  assert.strictEqual(lifecycle.esc(undefined), '');
});

test('formatDateUTC standardizes dates and degrades safely on malformed input', () => {
  assert.strictEqual(lifecycle.formatDateUTC('2026-10-26T14:30:00Z'), '2026-10-26');
  assert.strictEqual(lifecycle.formatDateUTC('2026-05-01'), '2026-05-01');
  assert.strictEqual(lifecycle.formatDateUTC(''), 'Unknown Date');
  assert.strictEqual(lifecycle.formatDateUTC(null), 'Unknown Date');
  assert.strictEqual(lifecycle.formatDateUTC(42), 'Unknown Date');
  assert.strictEqual(lifecycle.formatDateUTC('garbage'), 'garbage');
});

test('approved decision renders numeric standing, incumbent and empty challenge list', () => {
  const vm = lifecycle.buildTrustLifecycleViewModel(withoutChallenges(fixtures.material));
  assert.ok(vm);
  assert.equal(vm.standing.key, 'approved-decision');
  assert.equal(vm.standing.badgeText, '[Approved] Published Numeric Decision');
  assert.equal(vm.standing.tone, 'teal');
  assert.equal(vm.origin.handle, 'author');
  assert.equal(vm.origin.status, 'held');
  assert.equal(vm.activeChallengesCount, 0);
  const html = lifecycle.renderTrustLifecycleHtml(vm);
  assert.match(html, /aria-label="Trust Magnitude 72, 3 of 6 stars, approved decision"/);
  assert.match(html, /data-chip="approved-decision"/);
  assert.match(html, /@author/);
  assert.match(html, /data-lc-state="clear"/);
  assert.doesNotMatch(html, /lc-ledger|lc-head__mark/);
});

test('scoped challenge detail: standing, verifier, comparator, receipt link, never Origin-contested', () => {
  const vm = lifecycle.buildTrustLifecycleViewModel(fixtures.scoped);
  assert.equal(vm.standing.badgeText, '[Pending] Adjudication Pending');
  assert.equal(vm.standing.tone, 'gold');
  assert.equal(vm.activeChallengesCount, 1);
  const ch = vm.challenges[0];
  assert.equal(ch.status, 'verified-pending');
  assert.equal(ch.isAdjudicationPending, true);
  assert.equal(ch.verifier.verifierId, 'independent-reviewer');
  assert.equal(lifecycle.isSafeHttps(ch.verifier.receiptUrl), true);
  const html = lifecycle.renderTrustLifecycleHtml(vm);
  assert.match(html, /data-chip="open-scoped"/);
  assert.match(html, /data-chip="origin-held"/);
  assert.match(html, /comparator@2\.1/);
  assert.match(html, /Verification receipt/);
  assert.match(html, /rel="noopener noreferrer"/);
  assert.doesNotMatch(html, /data-chip="origin-contested"|data-chip="open-material"/);
});

test('material challenge contests Origin without transfer or vacancy', () => {
  const vm = lifecycle.buildTrustLifecycleViewModel(fixtures.material);
  assert.equal(vm.standing.key, 'contested');
  assert.equal(vm.standing.badgeText, '[Contested] Origin Contested');
  assert.equal(vm.standing.tone, 'honor-red');
  assert.equal(vm.origin.isContested, true);
  assert.equal(vm.origin.handle, 'author');
  assert.equal(vm.challenges[0].status, 'verified-pending');
  const html = lifecycle.renderTrustLifecycleHtml(vm);
  assert.match(html, /data-chip="origin-contested"/);
  assert.match(html, /aria-label="Current Origin @author, contested"/);
  // Doctrine prose lives in the Origin toggletip, not on the surface.
  assert.match(html, /role="tooltip"[^>]*>(?:(?!<\/span><\/span>).)*Origin remains held by the incumbent and does not transfer or vacate while contested/);
  assert.match(html, /lc-wreath__pin"><span class="lc-mark" data-state="open" data-severity="material"/);
});

test('technical resolution renders Class B proof distinct from pending recalibration', () => {
  const vm = lifecycle.buildTrustLifecycleViewModel(fixtures.resolved);
  assert.equal(vm.standing.badgeText, '[Pending] Trust Recalibration');
  assert.equal(vm.standing.tone, 'violet');
  assert.notEqual(vm.standing.recalibrationPending, null);
  assert.match(vm.standing.recalibrationPending.reason, /recalibration pending/);
  const html = lifecycle.renderTrustLifecycleHtml(vm);
  assert.match(html, /data-chip="recalibration"[^>]*>.*?Recalibration pending/);
  assert.match(html, /<span class="lc-meter" data-kind="approved-decision" data-recal=""/);
  assert.match(html, /Technical resolution recorded; trust recalibration pending\./);
  assert.match(html, /Resolution proof/);
  assert.match(html, new RegExp(vm.challenges[0].challengeId));
});

test('upstream-superseded and rebutted challenges stay visible in history with explicit labels', () => {
  const superseded = lifecycle.buildTrustLifecycleViewModel(fixtures.resolved);
  assert.equal(superseded.challenges.length, 1);
  assert.equal(superseded.challenges[0].isUpstreamSuperseded, true);
  assert.equal(superseded.challenges[0].history.length, 2);
  assert.equal(superseded.resolvedChallengesCount, 1);
  assert.match(lifecycle.renderTrustLifecycleHtml(superseded), /data-chip="upstream-material"[^>]*>.*?Resolved upstream/);
  const html = lifecycle.renderTrustLifecycleHtml(lifecycle.buildTrustLifecycleViewModel(rebutted()));
  assert.match(html, /data-chip="rebutted-material"[^>]*>.*?Rebutted/);
  assert.match(html, /<li class="lc-bout" data-state="rebutted" data-severity="material"><details class="lc-bout__details">/);
  assert.match(html, /aria-label="Material challenge technically rebutted"/);
});

test('missing consequence stays unassessed and never fabricates 0 stars or TM', () => {
  const vm = lifecycle.buildTrustLifecycleViewModel(fixtures.unknown);
  assert.equal(vm.standing.key, 'adjudication-pending');
  assert.strictEqual(vm.standing.approvedStars, null);
  assert.strictEqual(vm.standing.approvedTm, null);
  assert.strictEqual(vm.snapshot.isPinned, false);
  const html = lifecycle.renderTrustLifecycleHtml(vm);
  assert.match(html, /aria-label="Trust standing unavailable"/);
  assert.match(html, /<span class="lc-meter" data-kind="unavailable"/);
  assert.match(html, /<span class="lc-num">&#8212;<\/span>/);
  assert.match(html, /canonical consequence source is unavailable/);
  assert.doesNotMatch(html, /<span class="lc-num">0<\/span>|of 6 stars|lc-stars|lc-meter__fill|lc-meter__tick/);
  assert.doesNotMatch(html, /data-chip="approved-decision"/);
});

test('current baseline is never presented as an approved decision', () => {
  const vm = lifecycle.buildTrustLifecycleViewModel(withoutChallenges(fixtures.scoped));
  assert.equal(vm.standing.key, 'baseline');
  assert.strictEqual(vm.standing.approvedStars, null);
  assert.strictEqual(vm.standing.approvedTm, null);
  const html = lifecycle.renderTrustLifecycleHtml(vm);
  assert.doesNotMatch(html, /data-chip="approved-decision"|approved decision/i);
  assert.match(html, /data-chip="current-baseline"/);
  assert.match(html, /No numeric decision is asserted/);
});

test('forged display metadata cannot supply provenance, standing or snapshot identity', () => {
  const entry = clone(fixtures.scoped);
  entry.trustLifecycle.snapshot = {snapshotId: 'forged-snap', approvedBy: 'founder', approvalRef: 'https://example.org/pr/1'};
  entry.trustLifecycle.approvedStanding = {status: 'in-good-standing', approvedStars: 6, approvedTm: 999};
  entry.trustLifecycle.origin = {currentOriginHandle: 'attacker', contested: false};
  const vm = lifecycle.buildTrustLifecycleViewModel(entry);
  assert.ok(vm);
  const html = lifecycle.renderTrustLifecycleHtml(vm);
  for (const forged of ['forged-snap', 'founder', 'attacker', '999']) assert.ok(!html.includes(forged), forged);
  assert.equal(vm.standing.approvedStars, null);
});

test('strict boolean: non-boolean materialToOrigin never contests Origin', () => {
  const base = {challengeId: 'c', claim: 'x', status: 'verified-pending', verifiedAtUTC: '2026-10-26T00:00:00Z',
    verifier: {verifierId: 'v', verificationMethod: 'benchmark-replay', receiptUrl: 'https://example.com/receipt'}};
  for (const value of ['false', 'true', 1, 0, null, undefined]) {
    assert.strictEqual(lifecycle.normalizeChallenge(Object.assign({}, base, {materialToOrigin: value})).materialToOrigin, false);
  }
  assert.strictEqual(lifecycle.normalizeChallenge(Object.assign({}, base, {materialToOrigin: true})).materialToOrigin, true);
  const entry = clone(fixtures.scoped);
  entry.trustLifecycle.challenges[0].materialToOrigin = 'false';
  assert.equal(lifecycle.buildTrustLifecycleViewModel(entry), null);
});

test('model-only verification, bad receipts and shadow records are rejected', () => {
  const base = {challengeId: 'c', claim: 'x', status: 'verified-pending', materialToOrigin: false, verifiedAtUTC: '2026-10-26T00:00:00Z',
    verifier: {verifierId: 'v', verificationMethod: 'benchmark-replay', receiptUrl: 'https://example.com/receipt'}};
  assert.ok(lifecycle.normalizeChallenge(base));
  for (const method of ['model', 'LLM', 'model-only', 'semantic-model']) {
    const raw = clone(base); raw.verifier.verificationMethod = method;
    assert.equal(lifecycle.normalizeChallenge(raw), null);
  }
  for (const mutate of [r => { r.verifier.receiptUrl = 'http://insecure.example'; }, r => { delete r.verifier; },
                        r => { r.claim = ''; }, r => { r.status = 'bogus'; }, r => { delete r.challengeId; }]) {
    const raw = clone(base); mutate(raw);
    assert.equal(lifecycle.normalizeChallenge(raw), null);
  }
});

test('unsafe links anywhere in the DTO fail closed and never reach markup', () => {
  for (const unsafe of ['http://insecure-link.com', 'javascript:alert(2)', 'data:text/html,bad']) {
    const notice = clone(fixtures.material); notice.trustLifecycle.challenges[0].contributorNoticeRef = unsafe;
    assert.equal(lifecycle.buildTrustLifecycleViewModel(notice), null);
    const receipt = clone(fixtures.resolved); receipt.trustLifecycle.challenges[0].resolution.receiptUrl = unsafe;
    assert.equal(lifecycle.buildTrustLifecycleViewModel(receipt), null);
  }
  const html = lifecycle.renderTrustLifecycleHtml(lifecycle.buildTrustLifecycleViewModel(fixtures.resolved));
  assert.doesNotMatch(html, /javascript:|data:text|http:\/\//);
});

test('handles and identifiers are escaped in the rendered section', () => {
  const entry = clone(fixtures.material);
  entry.trustLifecycle.consequence.originHandle = '<script>alert(1)</script>';
  entry.trustLifecycle.challenges[0].behaviorId = '"><img src=x onerror=alert(1)>';
  const html = lifecycle.renderTrustLifecycleHtml(lifecycle.buildTrustLifecycleViewModel(entry));
  assert.doesNotMatch(html, /<script>|<img/);
  assert.match(html, /&lt;script&gt;/);
});

test('rendered DOM exposes labelled regions, toggletips, keyboard targets and labelled chips', () => {
  const mount = mockMount();
  lifecycle.renderLifecycleSection(mount, fixtures.material);
  const html = mount.innerHTML;
  assert.match(html, /<section class="lc-panel" data-lc-state="open-material" aria-labelledby="seLifecycleHeading">/);
  assert.match(html, /<h3 id="seLifecycleHeading" class="lc-title">Trust Lifecycle<\/h3>/);
  assert.match(html, /role="group" aria-label="Standing"/);
  const ledger = html.match(/<h4 class="lc-ledger__title" id="([^"]+)">/);
  assert.ok(ledger && html.includes('<ol class="lc-ledger__list" aria-labelledby="' + ledger[1] + '">'));
  // Every tooltip trigger is a named button described by a tooltip that exists in the DOM.
  const triggers = [...html.matchAll(/<button type="button" class="lc-tip[^"]*" aria-label="([^"]+)" aria-describedby="([^"]+)">/g)];
  assert.ok(triggers.length >= 3);
  for (const [, label, id] of triggers) {
    assert.ok(label.trim());
    assert.ok(html.includes('<span class="lc-tipbox" role="tooltip" id="' + id + '">'), id);
  }
  // Disclosures are native details/summary and start collapsed.
  assert.match(html, /<details class="lc-bout__details"><summary class="lc-bout__sum">/);
  assert.doesNotMatch(html, /<details[^>]* open/);
  // Chips always pair the glyph with a visible label (never symbol alone).
  const chips = [...html.matchAll(/<span class="lc-chip" data-chip="([a-z-]+)" data-tone="[a-z]+">(?:<span class="lc-mark"[^>]*aria-hidden="true">.*?<\/span>|<span class="lc-chip__swatch"[^>]*aria-hidden="true"><\/span>)<span class="lc-chip__label">([^<]+)<\/span>/g)];
  assert.ok(chips.length >= 3);
  for (const [, , label] of chips) assert.ok(label.trim().length > 2);
  assert.match(html, /target="_blank" rel="noopener noreferrer"/);
  assert.doesNotMatch(html, /target="_blank"(?![^>]*rel="noopener noreferrer")/);
});

test('doctrine prose stays out of the visible surface: only tooltips and collapsed records carry it', () => {
  for (const entry of [fixtures.scoped, fixtures.material, fixtures.resolved, fixtures.unknown]) {
    const html = lifecycle.renderTrustLifecycleHtml(lifecycle.buildTrustLifecycleViewModel(entry));
    const surface = html
      .replace(/<span class="lc-tipbox" role="tooltip"[^>]*>(?:<span class="lc-tipbox__line">[^<]*<\/span>)*<\/span>/g, '')
      .replace(/<div class="lc-record">[\s\S]*?<\/div><\/details>/g, '</details>');
    for (const prose of ['no automatic demotion', 'Origin stays with the incumbent', 'does not transfer or vacate',
                         'canonical consequence source', 'stays on record', 'grade floors']) {
      assert.ok(!surface.includes(prose), prose);
    }
  }
});

test('absent payload and null entry clear the mount exactly', () => {
  const mount = {innerHTML: 'pre-existing-content-should-clear'};
  lifecycle.renderLifecycleSection(mount, {id: 'x'});
  assert.equal(mount.innerHTML, '');
  mount.innerHTML = 'again';
  lifecycle.renderLifecycleSection(mount, null);
  assert.equal(mount.innerHTML, '');
});

test('Skill Explorer compiles, keeps both IIFEs, all five sections and the se-tm mount', () => {
  const code = read('../docs/js/skill-explorer.js');
  assert.doesNotThrow(() => new vmModule.Script(code));
  assert.match(code, /^\(function\(\)\{/);
  assert.match(code, /\(function\(\)\s*\{\s*\n\s*var treeDialog\s*=\s*document\.getElementById\('treeDialog'\);/);
  assert.match(code, /window\.GaiaTrustLifecycle/);
  assert.match(code, /'<div id="se-tm" class="se-flow-section"><\/div>'/);
  assert.match(code, /renderHero\(ns, generic\);/);
  for (const [name, id] of [['Install', 'se-install'], ['Docs', 'se-docs'], ['Upgrade', 'se-upgrade'], ['Trust Lifecycle', 'se-tm'], ['Timeline', 'se-changelog']]) {
    assert.match(code, new RegExp("_safeRender\\('" + name + "',\\s*'" + id + "'"));
  }
});

test('trust-lifecycle.js compiles standalone and uses design tokens only (no hex colours)', () => {
  const code = read('../docs/js/trust-lifecycle.js');
  assert.doesNotThrow(() => new vmModule.Script(code));
  // Mirrors the intent of CI Guard A (scripts/check_hex_colors.py); HTML entities (&#9733;) and issue numbers (#2148) are excluded.
  assert.doesNotMatch(code, /(?:^|[^\w&])#(?=[0-9a-fA-F]*[a-fA-F])(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])/m);
});

test('lifecycle CSS: empty mount hidden, mobile-first containment, token-only colour', () => {
  const css = read('../docs/css/styles.css');
  const js = read('../docs/js/trust-lifecycle.js');
  const block = css.slice(css.indexOf('/* ── TRUST LIFECYCLE & CHALLENGE IDENTITY'));
  assert.ok(block.length > 1000);
  assert.match(block, /#se-tm:empty\s*\{[^}]*display:\s*none/);
  assert.match(block, /\.lc-record__row dd\s*\{[^}]*min-width:\s*0[^}]*overflow-wrap:\s*anywhere/);
  assert.match(block, /\.lc-code\s*\{[^}]*overflow-wrap:\s*anywhere/);
  assert.match(block, /\.lc-tipbox\s*\{[^}]*max-width:\s*min\(44ch, 100%\)/);
  assert.match(block, /\.lc-chip\s*\{[^}]*max-width:\s*100%/);
  assert.doesNotMatch(block, /#[0-9a-fA-F]{3,8}\b/);
  // Challenge tokens are declared once in :root as RGB triplets, never hex.
  for (const token of ['--challenge-ember-rgb', '--challenge-ember-deep-rgb', '--challenge-slate-rgb', '--hallmark-steel-rgb']) {
    assert.match(css, new RegExp(token + ':\\s*\\d+, \\d+, \\d+;'));
  }
  // The module no longer injects a second, competing stylesheet.
  assert.doesNotMatch(js, /createElement\('style'\)|ensureStyles/);
});

test('motion respects prefers-reduced-motion and tooltips reveal on hover, focus and tap', () => {
  const css = read('../docs/css/styles.css');
  const block = css.slice(css.indexOf('/* ── TRUST LIFECYCLE & CHALLENGE IDENTITY'));
  const reduced = block.slice(block.indexOf('@media (prefers-reduced-motion: reduce)'));
  assert.ok(reduced.length > 20);
  assert.match(reduced, /\.lc-mark,\s*\.lc-mark__hatch line,\s*\.lc-meter__recal\s*\{\s*animation:\s*none !important/);
  assert.match(reduced, /\.lc-tipbox\s*\{\s*transform:\s*none;\s*clip-path:\s*none/);
  assert.match(block, /@keyframes lc-heat/);
  assert.match(block, /@keyframes lc-strike/);
  assert.match(block, /\.lc-tip\[data-open\] \+ \.lc-tipbox,\s*\.lc-tip:focus-visible \+ \.lc-tipbox/);
  assert.match(block, /@media \(hover: hover\)\s*\{\s*\.lc-tip:hover \+ \.lc-tipbox/);
});

// ── Reusable Challenge identity components ─────────────────────────────

const C = lifecycle.components;
const STATES = [['open', 'scoped'], ['open', 'material'], ['rebutted', 'scoped'], ['rebutted', 'material'],
                ['upstream', 'scoped'], ['upstream', 'material']];

test('challengeMark: every state renders a named, sized SVG mark with token classes only', () => {
  for (const [state, severity] of STATES) {
    for (const size of ['sm', 'md', 'lg', 'xl']) {
      const html = C.challengeMark(state, {severity, size});
      assert.match(html, new RegExp('^<span class="lc-mark" data-state="' + state + '" data-severity="' + severity +
        '" data-size="' + size + '" role="img" aria-label="[^"]+"><svg class="lc-mark__svg" viewBox="0 0 24 24" focusable="false" aria-hidden="true">'));
      assert.doesNotMatch(html, /fill="#|stroke="#|#[0-9a-fA-F]{3,8}\b/);
    }
  }
  assert.match(C.challengeMark('open', {severity: 'material'}), /aria-label="Open material challenge, contests Origin"/);
  assert.match(C.challengeMark('rebutted', {severity: 'scoped'}), /aria-label="Scoped challenge technically rebutted"/);
  assert.match(C.challengeMark('upstream', {severity: 'material', label: '<x>'}), /aria-label="&lt;x&gt;"/);
  assert.match(C.challengeMark('open', {decorative: true}), /^<span class="lc-mark"[^>]* aria-hidden="true">/);
  assert.doesNotMatch(C.challengeMark('open', {decorative: true}), /role="img"/);
  // Unknown inputs fall back instead of emitting unvalidated attribute values.
  assert.match(C.challengeMark('bogus', {severity: 'x', size: 'huge'}), /data-state="open" data-severity="scoped" data-size="md"/);
});

test('challengeMark: severity is form (notch depth, chevron count), not colour', () => {
  const open = sev => C.challengeMark('open', {severity: sev});
  assert.match(open('scoped'), /L12 9L/);
  assert.match(open('material'), /L12 15L/);
  const count = (html, cls) => (html.match(new RegExp('class="' + cls + '"', 'g')) || []).length;
  assert.equal(count(C.challengeMark('rebutted', {severity: 'scoped'}), 'lc-mark__chev'), 1);
  assert.equal(count(C.challengeMark('rebutted', {severity: 'material'}), 'lc-mark__chev'), 2);
  assert.equal(count(C.challengeMark('upstream', {severity: 'scoped'}), 'lc-mark__chev'), 2);
  assert.equal(count(C.challengeMark('upstream', {severity: 'material'}), 'lc-mark__chev'), 3);
  assert.ok(count(open('material'), 'lc-mark__hatch') === 1 && count(C.challengeMark('rebutted'), 'lc-mark__hatch') === 0);
  // Hachure stays inside the plate and never crosses the notch.
  for (const sev of ['scoped', 'material']) {
    const notch = sev === 'scoped' ? [[9.5, 3], [12, 9], [14.5, 3]] : [[9, 3], [12, 15], [15, 3]];
    const inTri = (x, y) => {
      const [a, b, c] = notch, s = (p, q, r) => (p[0] - r[0]) * (q[1] - r[1]) - (q[0] - r[0]) * (p[1] - r[1]);
      const d1 = s([x, y], a, b), d2 = s([x, y], b, c), d3 = s([x, y], c, a);
      return !((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0));
    };
    const lines = [...open(sev).matchAll(/<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)"/g)].map(m => m.slice(1).map(Number));
    assert.ok(lines.length >= 6, sev);
    for (const [x1, y1, x2, y2] of lines) {
      for (const v of [x1, y1, x2, y2]) assert.ok(v >= 2.99 && v <= 21.01);
      assert.ok(!inTri((x1 + x2) / 2, (y1 + y2) / 2), sev + ' hatch crosses notch');
    }
  }
});

test('markStateOf maps normalized challenges to mark states', () => {
  const vm = lifecycle.buildTrustLifecycleViewModel(fixtures.material);
  assert.deepEqual(C.markStateOf(vm.challenges[0]), {state: 'open', severity: 'material'});
  assert.deepEqual(C.markStateOf(lifecycle.buildTrustLifecycleViewModel(fixtures.scoped).challenges[0]), {state: 'open', severity: 'scoped'});
  assert.deepEqual(C.markStateOf(lifecycle.buildTrustLifecycleViewModel(fixtures.resolved).challenges[0]), {state: 'upstream', severity: 'material'});
  assert.deepEqual(C.markStateOf(lifecycle.buildTrustLifecycleViewModel(rebutted()).challenges[0]), {state: 'rebutted', severity: 'material'});
});

test('stateChip: glyph is decorative and a visible label always carries the meaning', () => {
  const kinds = ['open-scoped', 'open-material', 'rebutted-scoped', 'rebutted-material', 'upstream-scoped', 'upstream-material',
    'approved-decision', 'current-baseline', 'unavailable', 'recalibration', 'origin-held', 'origin-contested', 'origin-unknown'];
  for (const kind of kinds) {
    const html = C.stateChip(kind);
    assert.match(html, new RegExp('^<span class="lc-chip" data-chip="' + kind + '" data-tone="(ember|steel|quiet)">'));
    assert.match(html, /aria-hidden="true"/);
    assert.match(html, /<span class="lc-chip__label">[A-Z][^<]{2,}<\/span><\/span>$/);
  }
  assert.match(C.stateChip('open-material'), /data-tone="ember"/);
  assert.match(C.stateChip('rebutted-material'), /data-tone="steel"/);
  assert.match(C.stateChip('nope'), /Unavailable/);
  assert.match(C.stateChip('open-scoped', {label: '<b>'}), /&lt;b&gt;/);
});

test('trustMeter: log-scale meter with accessible value, grade floors and state forms', () => {
  const html = C.trustMeter({tm: 72, kind: 'approved-decision'});
  assert.match(html, /role="meter" aria-label="Trust Magnitude" aria-valuemin="0" aria-valuemax="500" aria-valuenow="72" aria-valuetext="72, approved decision"/);
  assert.match(html, /style="--lc-fill:69.02%"/);
  assert.equal((html.match(/class="lc-meter__tick"/g) || []).length, 4);
  for (const grade of ['C', 'B', 'A', 'S']) assert.match(html, new RegExp('data-grade="' + grade + '"'));
  assert.match(C.trustMeter({tm: 50, kind: 'current-baseline'}), /data-kind="current-baseline"/);
  const recal = C.trustMeter({tm: 73.59, kind: 'approved-decision', recalibrationPending: true});
  assert.match(recal, /data-recal=""/);
  assert.match(recal, /lc-meter__recal/);
  assert.match(recal, /aria-valuetext="73.59, approved decision, recalibration pending"/);
  const none = C.trustMeter({tm: null, kind: 'approved-decision'});
  assert.match(none, /data-kind="unavailable"[^>]*role="img" aria-label="Trust Magnitude unavailable"/);
  assert.doesNotMatch(none, /lc-meter__fill|lc-meter__tick|aria-valuenow/);
  assert.match(C.trustMeter({tm: 9999, kind: 'approved-decision'}), /--lc-fill:100%/);
  assert.match(C.trustMeter({tm: 72, kind: 'approved-decision', decorative: true}), /aria-hidden="true"/);
});

test('tip: unique ids, escaped text, tooltip present in the DOM for screen readers', () => {
  const a = C.tip('<span>x</span>', ['First <line>', 'Second'], {label: 'Name "q"', cls: 'extra'});
  const b = C.tip('<span>y</span>', 'Only');
  const idA = a.match(/aria-describedby="([^"]+)"/)[1], idB = b.match(/aria-describedby="([^"]+)"/)[1];
  assert.notEqual(idA, idB);
  assert.match(a, /^<button type="button" class="lc-tip extra" aria-label="Name &quot;q&quot;" aria-describedby="lc-tip-\d+"><span>x<\/span><\/button>/);
  assert.ok(a.includes('<span class="lc-tipbox" role="tooltip" id="' + idA + '"><span class="lc-tipbox__line">First &lt;line&gt;</span><span class="lc-tipbox__line">Second</span></span>'));
});

test('bindTips: tap toggles one tip, Escape closes, binding is idempotent and mock-safe', () => {
  assert.doesNotThrow(() => C.bindTips({innerHTML: ''}));
  const attrs = el => ({attrs: {}, hasAttribute(k) { return k in this.attrs; }, setAttribute(k, v) { this.attrs[k] = v; },
    removeAttribute(k) { delete this.attrs[k]; }, getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }, ...el});
  const t1 = attrs({classList: {contains: c => c === 'lc-tip'}}), t2 = attrs({classList: {contains: c => c === 'lc-tip'}});
  const listeners = {};
  const mount = attrs({
    addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
    querySelectorAll() { return [t1, t2].filter(t => t.hasAttribute('data-open')); }
  });
  C.bindTips(mount);
  C.bindTips(mount);
  assert.equal(listeners.click.length, 1);
  listeners.click[0]({target: {closest: () => t1}});
  assert.ok(t1.hasAttribute('data-open'));
  listeners.click[0]({target: {closest: () => t2}});
  assert.ok(t2.hasAttribute('data-open') && !t1.hasAttribute('data-open'));
  listeners.keydown[0]({key: 'Escape'});
  assert.ok(!t2.hasAttribute('data-open'));
  listeners.click[0]({target: {closest: () => t1}});
  listeners.click[0]({target: {closest: () => t1}});
  assert.ok(!t1.hasAttribute('data-open'));
});

test('panel: answered material challenge shows the struck hallmark, pins it to the wreath and strikes the claim', () => {
  const html = lifecycle.renderTrustLifecycleHtml(lifecycle.buildTrustLifecycleViewModel(rebutted()));
  assert.match(html, /data-lc-state="answered"/);
  assert.match(html, /<button type="button" class="lc-tip lc-head__mark" aria-label="Material challenge technically rebutted"/);
  assert.match(html, /data-state="rebutted" data-severity="material" data-size="xl"/);
  assert.match(html, /lc-wreath__pin"><span class="lc-mark" data-state="rebutted" data-severity="material"/);
  assert.match(html, /aria-label="Current Origin @author, held, defended against a material challenge"/);
  assert.match(html, /data-challenge="answered"/);
  assert.match(html, /aria-label="Published 2026-10-25, resolved 2026-10-27 after 2 days"/);
});

test('panel: several challenges show the open lead, a count, and the honours strip of answered ones', () => {
  const entry = clone(fixtures.scoped);
  const answered = clone(rebutted().trustLifecycle.challenges[0]);
  answered.subjectId = entry.id;
  answered.history.forEach(e => { e.challenge_id = answered.challengeId; });
  entry.trustLifecycle.challenges.push(answered);
  const vm = lifecycle.buildTrustLifecycleViewModel(entry);
  assert.ok(vm, 'composed DTO must validate');
  const html = lifecycle.renderTrustLifecycleHtml(vm);
  assert.match(html, /data-lc-state="open-scoped"/);
  assert.match(html, /<span class="lc-honors" role="img" aria-label="1 resolved challenge on record">/);
  assert.match(html, /1 open &middot; 1 resolved/);
  const order = [...html.matchAll(/<li class="lc-bout" data-state="([a-z]+)"/g)].map(m => m[1]);
  assert.deepEqual(order, ['open', 'rebutted']);
});

test('panel: avatar only for GitHub-shaped handles; other handles keep an initial and stay escaped', () => {
  const entry = clone(fixtures.material);
  entry.trustLifecycle.consequence.originHandle = 'bad handle/../x';
  const html = lifecycle.renderTrustLifecycleHtml(lifecycle.buildTrustLifecycleViewModel(entry));
  assert.doesNotMatch(html, /lc-wreath__avatar/);
  assert.match(html, /lc-wreath__initial" aria-hidden="true">B</);
  assert.match(lifecycle.renderTrustLifecycleHtml(lifecycle.buildTrustLifecycleViewModel(fixtures.material)),
    /<img class="lc-wreath__avatar" src="https:\/\/github\.com\/author\.png\?size=96" alt=""/);
});

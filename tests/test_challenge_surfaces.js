'use strict';

// Challenge surfaces (EPIC #2189 W3-W6). Documents come from tests/fixtures/challenge_surfaces_fixture.py,
// which builds them with the real produce_lifecycle code over disposable synthetic ports.
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const surfaces = require('../docs/js/challenge-surfaces.js');

const fixture = JSON.parse(execFileSync('python3', [path.join(__dirname, 'fixtures/challenge_surfaces_fixture.py'),
  'skill/material-example', 'skill/scoped-example', 'skill/resolved-example'],
  {encoding: 'utf8', env: Object.assign({}, process.env, {PYTHONPATH: path.join(__dirname, '../src')})}));
const clone = value => JSON.parse(JSON.stringify(value));
const unavailableDoc = {contract: 'gaia-challenge-projection/v1', sourceStatus: 'unavailable', subjects: []};

// ── a just-enough DOM: records every attribute write so "never touched" is checkable ──
class El {
  constructor(tag, doc) { this.tag = tag; this.ownerDocument = doc; this.attrs = {}; this.children = []; this.parentNode = null; this.writes = 0; this.innerHTML = ''; this.textContent = ''; }
  setAttribute(k, v) { this.attrs[k] = String(v); this.writes += 1; }
  getAttribute(k) { return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; }
  appendChild(c) { c.parentNode = this; this.children.push(c); return c; }
  removeChild(c) { this.children = this.children.filter(x => x !== c); c.parentNode = null; return c; }
  all() { return this.children.reduce((acc, c) => acc.concat([c], c.all()), []); }
  querySelectorAll(sel) {
    if (sel === '.cs-chartmark') return this.all().filter(e => e.attrs.class === 'cs-chartmark');
    if (sel === '.lb-bar[data-type="named"]') return this.all().filter(e => e.attrs.class === 'lb-bar' && e.attrs['data-type'] === 'named');
    throw new Error('unsupported selector ' + sel);
  }
  serialize() {
    return '<' + this.tag + Object.keys(this.attrs).map(k => ' ' + k + '="' + this.attrs[k] + '"').join('') + '>' +
      this.children.map(c => c.serialize()).join('') + '</' + this.tag + '>';
  }
}
const doc = {createElementNS: (ns, tag) => new El(tag, doc)};
function fakeChart(ids) {
  const svg = new El('svg', doc);
  const group = svg.appendChild(new El('g', doc));
  ids.forEach((id, i) => {
    const bar = group.appendChild(new El('rect', doc));
    for (const [k, v] of Object.entries({x: i * 50, y: 20 + i, width: 24, height: 118 - i, rx: 3, fill: 'url(#g' + i + ')', class: 'lb-bar', 'data-id': id, 'data-type': 'named'})) bar.attrs[k] = String(v);
    const label = group.appendChild(new El('text', doc));
    label.attrs.class = 'lb-axis-value';
    label.textContent = String(Math.round(118 - i));
  });
  group.ownerDocument = doc;
  svg.ownerDocument = doc;
  return svg;
}

const verified = () => surfaces.parseProjection(clone(fixture.index));

test('unavailable and malformed projections read as unavailable and contest nothing', () => {
  assert.equal(surfaces.parseProjection(unavailableDoc).status, 'unavailable');
  const reserved = Object.assign(clone(unavailableDoc), {sourceStatus: 'verified-empty'});
  const bad = [null, [], {}, reserved, Object.assign(clone(unavailableDoc), {extra: 1}),
    Object.assign(clone(fixture.index), {contract: 'gaia-challenge-projection/v2'}),
    Object.assign(clone(fixture.index), {subjects: []}),
    Object.assign(clone(unavailableDoc), {subjects: clone(fixture.index.subjects)})];
  for (const doc of bad) {
    const parsed = surfaces.parseProjection(doc);
    assert.equal(parsed.status, 'unavailable');
    assert.deepEqual(parsed.subjects, []);
    assert.deepEqual(Object.keys(surfaces.contestedIndex(parsed)), []);
  }
  assert.deepEqual(Object.keys(surfaces.contestedIndex(null)), []);
});

test('fail closed as a whole: one bad challenge, a proposal key or a flag mismatch voids the file', () => {
  const mutations = [
    doc => { delete doc.subjects[0].challenges[0].verifier; },
    doc => { doc.subjects[0].challenges[0].verifier.receiptUrl = 'http://example.org/receipt'; },
    doc => { doc.subjects[0].challenges[0].subjectId = 'someone/else'; },
    doc => { doc.subjects[0].challenges[0].proposedStatus = 'upheld'; },
    doc => { doc.subjects[1].consequence.proposedTm = 80; },
    doc => { doc.subjects[0].materialOriginContested = false; },
    doc => { doc.subjects[1].materialOriginContested = true; },
    doc => { doc.subjects[0].consequence.kind = 'proposed-decision'; },
    doc => { doc.subjects[1].subjectId = doc.subjects[0].subjectId; },
    doc => { doc.subjects[0].challenges[0].history = []; },
    doc => { doc.subjects[2].challenges[0].resolution = undefined; }
  ];
  mutations.forEach((mutate, i) => {
    const doc = clone(fixture.index);
    mutate(doc);
    assert.equal(surfaces.parseProjection(doc).status, 'unavailable', 'mutation ' + i);
  });
});

test('only admitted, unresolved challenges contest; resolved ones are history', () => {
  const parsed = verified();
  assert.equal(parsed.status, 'verified');
  const index = surfaces.contestedIndex(parsed);
  assert.deepEqual(Object.keys(index).sort(), ['skill/material-example', 'skill/scoped-example']);
  assert.equal(index['skill/material-example'].originContested, true);
  assert.equal(index['skill/scoped-example'].originContested, false);
  assert.equal(index['skill/resolved-example'], undefined);
  const label = surfaces.contestLabel(index['skill/material-example'], {isOrigin: true});
  assert.match(label, /^Origin contested\. Contested by 1 open admitted challenge, including one that contests Origin\./);
  assert.match(label, /unchanged until an approved decision/);
  assert.match(surfaces.contestLabel(index['skill/scoped-example'], {}), /Origin not affected/);
});

test('contested marks keep every bar and figure byte-identical', () => {
  const ids = ['skill/material-example', 'someone/plain-one', 'skill/scoped-example', 'someone/plain-two'];
  const chart = fakeChart(ids);
  const bars = chart.all().filter(e => e.attrs.class === 'lb-bar');
  const figures = chart.all().filter(e => e.attrs.class === 'lb-axis-value');
  const before = {bars: bars.map(b => b.serialize()), writes: bars.map(b => b.writes), figures: figures.map(f => f.serialize() + f.textContent)};
  const index = surfaces.contestedIndex(verified());
  const added = surfaces.decorateBars(chart, id => index[id] ? {entry: surfaces.combineEntries([index[id]]), isOrigin: id === 'skill/material-example'} : null, {root: '../../'});
  assert.equal(added, 2);
  assert.deepEqual(bars.map(b => b.serialize()), before.bars);
  assert.deepEqual(bars.map(b => b.writes), before.writes);
  assert.deepEqual(figures.map(f => f.serialize() + f.textContent), before.figures);
  const marks = chart.querySelectorAll('.cs-chartmark');
  assert.equal(marks.length, 2);
  assert.deepEqual(marks.map(m => m.attrs['data-skill-id']).sort(), ['skill/material-example', 'skill/scoped-example']);
  for (const mark of marks) {
    assert.match(mark.attrs['aria-label'], /^(Origin contested\. )?Contested by 1 open admitted challenge/);
    assert.match(mark.attrs.href, /^\.\.\/\.\.\/trust\/challenges\/#subject-skill%2F/);
  }
  // Re-running replaces marks rather than stacking them, and still never touches a bar.
  surfaces.decorateBars(chart, id => index[id] ? {entry: surfaces.combineEntries([index[id]])} : null, {root: '../../'});
  assert.equal(chart.querySelectorAll('.cs-chartmark').length, 2);
  assert.deepEqual(bars.map(b => b.serialize()), before.bars);
});

test('an unavailable projection leaves the chart byte-identical', () => {
  const chart = fakeChart(['a/one', 'b/two']);
  const before = chart.serialize();
  const index = surfaces.contestedIndex(surfaces.parseProjection(unavailableDoc));
  assert.equal(surfaces.decorateBars(chart, id => index[id] || null, {root: ''}), 0);
  assert.equal(chart.serialize(), before);
});

test('table rows gain a Contested link only when contested', () => {
  const cell = id => {
    const out = {html: [], querySelector: sel => (sel === 'a' ? {textContent: id} : null), insertAdjacentHTML(where, html) { this.html.push(html); }};
    return out;
  };
  const cells = [cell('skill/scoped-example'), cell('someone/plain')];
  const tbody = {querySelectorAll: () => cells};
  const index = surfaces.contestedIndex(verified());
  assert.equal(surfaces.decorateRows(tbody, id => index[id] ? {entry: surfaces.combineEntries([index[id]])} : null, {root: '../../'}), 1);
  assert.equal(cells[1].html.length, 0);
  assert.match(cells[0].html[0], /class="cs-rowmark" href="\.\.\/\.\.\/trust\/challenges\/#subject-skill%2Fscoped-example"/);
  assert.match(cells[0].html[0], /<span class="cs-rowmark__word">Contested<\/span>/);
});

test('challenge history lists admitted events only, newest first; unavailable hides the block', () => {
  const events = surfaces.historyEvents(verified());
  assert.ok(events.length >= 4);
  assert.deepEqual(events.map(e => e.atUTC), events.map(e => e.atUTC).slice().sort().reverse());
  assert.ok(events.every(e => ['verified-publication', 'technical-resolution'].includes(e.type)));
  assert.ok(events.filter(e => e.type === 'technical-resolution').every(e => /^https:/.test(e.receiptUrl)));
  const mount = {innerHTML: 'stale', hidden: false};
  assert.equal(surfaces.renderHistory(mount, verified(), {root: '../../'}), events.length);
  assert.equal(mount.hidden, false);
  assert.match(mount.innerHTML, /Events from admitted challenges only/);
  assert.doesNotMatch(mount.innerHTML, /propos/i);
  const empty = {innerHTML: 'stale', hidden: false};
  assert.equal(surfaces.renderHistory(empty, surfaces.parseProjection(unavailableDoc), {}), 0);
  assert.equal(empty.innerHTML, '');
  assert.equal(empty.hidden, true);
  assert.deepEqual(surfaces.historyEvents(null), []);
});

test('held reviews parse separately and never read as contested', () => {
  const parsed = surfaces.parseReviews(clone(fixture.reviews));
  assert.equal(parsed.reviews.length, 4);
  assert.match(parsed.reviews[0].evidenceUrl, /^https:\/\/github\.com\/gaia-research\/gaia-skill-tree\/tree\/main\/evidence\/frontier-challenges\/synthetic-review-0001$/);
  const mounts = {admitted: {innerHTML: ''}, held: {innerHTML: ''}};
  surfaces.renderPage(mounts, {projection: surfaces.parseProjection(unavailableDoc), reviews: parsed}, {root: '../../'});
  assert.doesNotMatch(mounts.held.innerHTML, /contested/i);
  assert.doesNotMatch(mounts.held.innerHTML, /lc-mark|lc-chip|cs-chartmark|cs-rowmark/);
  assert.match(mounts.held.innerHTML, /Case evidence/);
  assert.match(mounts.held.innerHTML, /Synthetic Challenger 0\.0\.1<\/span><span class="cs-review__vs">against<\/span><span class="cs-review__side">skill\/held-example/);
  assert.match(mounts.held.innerHTML, /Substantiated/);
  assert.match(mounts.held.innerHTML, /changes no Trust Magnitude, star, grade, Origin or ranking/);
  assert.equal(surfaces.HELD_HEADING, 'Admission held, no effect on standing');
});

test('a review that carries a dispute label, a proposal or a Gaia number is dropped alone', () => {
  const good = fixture.reviews.reviews[0];
  const disputed = Object.assign(clone(good), {caseId: 'synthetic-review-0003'});
  disputed.held.explanation = 'This review is contested.';
  const numbered = Object.assign(clone(good), {caseId: 'synthetic-review-0004', stars: 4});
  const proposed = Object.assign(clone(good), {caseId: 'synthetic-review-0005', proposedAction: 'x'});
  const badReason = Object.assign(clone(good), {caseId: 'synthetic-review-0006'});
  badReason.held.reason = 'because';
  const wrongContract = Object.assign(clone(good), {caseId: 'synthetic-review-0007', contract: 'gaia-challenge-projection/v1'});
  const parsed = surfaces.parseReviews({contract: 'gaia-challenge-review/v1', reviews: [good, disputed, numbered, proposed, badReason, wrongContract]});
  assert.deepEqual(parsed.reviews.map(r => r.caseId), ['synthetic-review-0001']);
  assert.deepEqual(surfaces.parseReviews({contract: 'gaia-challenge-review/v1'}).reviews, []);
  assert.deepEqual(surfaces.parseReviews(null).reviews, []);
  // Challenger-authored text is data, not a label: the word may appear in a claim.
  const claimed = Object.assign(clone(good), {caseId: 'synthetic-review-0008', claim: 'Documents a contested edge case.'});
  assert.equal(surfaces.parseReviews({contract: 'gaia-challenge-review/v1', reviews: [claimed]}).reviews.length, 1);
});

test('the page states unavailable and empty truthfully and quietly', () => {
  const mounts = () => ({admitted: {innerHTML: ''}, held: {innerHTML: ''}});
  const quiet = mounts();
  surfaces.renderPage(quiet, {projection: surfaces.parseProjection(unavailableDoc), reviews: surfaces.parseReviews({contract: 'gaia-challenge-review/v1', reviews: []})}, {root: '../../'});
  assert.match(quiet.admitted.innerHTML, /data-state="unavailable">No challenge has been admitted\./);
  assert.match(quiet.held.innerHTML, /data-state="none">No review is on record\./);
  assert.doesNotMatch(quiet.admitted.innerHTML + quiet.held.innerHTML, /lc-mark|lc-chip|<article|<table/);
  const failed = mounts();
  surfaces.renderPage(failed, {projection: {status: 'unavailable', subjects: [], loadFailed: true}, reviews: {reviews: [], loadFailed: true}}, {root: '../../'});
  assert.match(failed.admitted.innerHTML, /data-state="failed"/);
  assert.match(failed.held.innerHTML, /data-state="failed"/);
});

test('the page renders admitted subjects with marks, standing from approved data and receipt links', () => {
  const mounts = {admitted: {innerHTML: ''}, held: {innerHTML: ''}};
  surfaces.renderPage(mounts, {projection: verified(), reviews: {reviews: [], loadFailed: false}}, {root: '../../'});
  const html = mounts.admitted.innerHTML;
  assert.equal((html.match(/<article class="cs-subject"/g) || []).length, 3);
  assert.match(html, /id="subject-skill\/material-example" data-origin-contested="true"/);
  assert.match(html, /data-origin-contested="false"/);
  assert.match(html, /data-chip="open-material"/);
  assert.match(html, /Approved decision: 3 of 6 stars, Trust Magnitude 72\./);
  assert.match(html, /Published baseline: 3 of 6 stars/);
  assert.match(html, /A challenge never changes these figures by itself\./);
  assert.match(html, /Verification receipt/);
  assert.match(html, /Resolution receipt/);
  assert.doesNotMatch(html, /propos/i);
});

test('the heading toggletip is a real button with a tooltip', () => {
  const tip = surfaces.contestedTip();
  assert.match(tip, /<button type="button" class="lc-tip cs-infotip"/);
  assert.match(tip, /role="tooltip"/);
  assert.match(tip, /no automatic demotion/);
});

test('only producer-reachable challenge statuses and history lengths are accepted', () => {
  const variants = [
    ['upheld', doc => { doc.subjects[0].challenges[0].status = 'upheld'; }],
    ['narrowed', doc => { doc.subjects[0].challenges[0].status = 'narrowed'; }],
    ['rejected', doc => { doc.subjects[2].challenges[0].status = 'rejected'; doc.subjects[2].challenges[0].resolution.disposition = 'rejected'; }],
    ['open with two events', doc => { doc.subjects[0].challenges[0].history.push(clone(doc.subjects[2].challenges[0].history[1])); }],
    ['answered with one event', doc => { doc.subjects[2].challenges[0].history.pop(); }],
    ['open with a resolution', doc => { doc.subjects[0].challenges[0].resolution = clone(doc.subjects[2].challenges[0].resolution); }],
    ['disposition differs from status', doc => { doc.subjects[2].challenges[0].resolution.disposition = 'technically-rebutted'; }],
    ['opening event is not a publication', doc => { doc.subjects[0].challenges[0].history[0].event_type = 'technical-resolution'; }]
  ];
  for (const [name, mutate] of variants) {
    const doc = clone(fixture.index);
    mutate(doc);
    const parsed = surfaces.parseProjection(doc);
    assert.equal(parsed.status, 'unavailable', name);
    assert.deepEqual(Object.keys(surfaces.contestedIndex(parsed)), [], name);
  }
  const rebutted = clone(fixture.index);
  const answered = rebutted.subjects[2].challenges[0];
  answered.status = 'technically-rebutted';
  answered.resolution.disposition = 'technically-rebutted';
  assert.equal(surfaces.parseProjection(rebutted).status, 'verified');
});

test('held and triage reviews carry their own neutral reason line and never "contested"', () => {
  const parsed = surfaces.parseReviews(clone(fixture.reviews));
  assert.deepEqual(parsed.reviews.map(r => r.statusLabel), ['Admission held', 'Admission held', 'Rejected at triage', 'Deferred at triage']);
  assert.equal(parsed.reviews[1].holdReason, 'meta-not-recommended');
  const mounts = {admitted: {innerHTML: ''}, held: {innerHTML: ''}};
  surfaces.renderPage(mounts, {projection: surfaces.parseProjection(unavailableDoc), reviews: parsed}, {root: '../../'});
  const html = mounts.held.innerHTML;
  assert.match(html, /<dt>Reason<\/dt><dd>The independent assessment of this review does not recommend an admission review\.<\/dd>/);
  assert.match(html, /<dt>Reason<\/dt><dd>The lead was rejected at triage, before any experiment was preregistered or run\.<\/dd>/);
  assert.match(html, /<dt>Reason<\/dt><dd>The lead was deferred at triage, with no effect on standing; no experiment was run\.<\/dd>/);
  assert.match(html, /<dt>Status<\/dt><dd>Rejected at triage<\/dd>/);
  assert.doesNotMatch(html, /contested|under review/i);
  // A triage record may not carry a hold or an experiment, and must carry its note.
  const good = fixture.reviews.reviews[2];
  const withHold = Object.assign(clone(good), {caseId: 'synthetic-review-0010', held: clone(fixture.reviews.reviews[0].held)});
  const withExperiment = Object.assign(clone(good), {caseId: 'synthetic-review-0011', experiment: {result: 'supported'}});
  const noNote = Object.assign(clone(good), {caseId: 'synthetic-review-0012'});
  delete noNote.triage;
  const disputed = Object.assign(clone(good), {caseId: 'synthetic-review-0013'});
  disputed.triage.explanation = 'The lead is contested.';
  const unknownStatus = Object.assign(clone(good), {caseId: 'synthetic-review-0014', status: 'under-review'});
  const kept = surfaces.parseReviews({contract: 'gaia-challenge-review/v1', reviews: [good, withHold, withExperiment, noNote, disputed, unknownStatus]});
  assert.deepEqual(kept.reviews.map(r => r.caseId), ['synthetic-review-0003']);
});

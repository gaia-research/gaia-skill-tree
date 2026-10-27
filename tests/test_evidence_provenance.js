'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const lifecycle = require('../docs/js/trust-lifecycle.js');
const EP = require('../docs/js/evidence-provenance.js');

const row = {
  type: 'repo',
  source: 'https://www.github.com/acme/widget/blob/main/SKILL.md',
  evaluator: 'mbtiongson1',
  date: '2026-06-14',
  notes: 'kept as written'
};

const withLifecycle = fn => {
  globalThis.GaiaTrustLifecycle = lifecycle;
  try { return fn(); } finally { delete globalThis.GaiaTrustLifecycle; }
};

test('describe reports the five provenance facts exactly as recorded', () => {
  const d = EP.describe(row);
  assert.equal(d.type, 'repo-own');
  assert.equal(d.typeLabel, 'repo');
  assert.equal(d.host, 'github.com');
  assert.equal(d.path, '/acme/widget/blob/main/SKILL.md');
  assert.equal(d.href, row.source);
  assert.equal(d.evaluator, 'mbtiongson1');
  assert.equal(d.date, '2026-06-14');
  assert.equal(d.synthetic, false);
});

test('legacy type aliases normalize and unknown types show as written', () => {
  assert.equal(EP.normalizeType('github-stars'), 'github-stars-own');
  assert.equal(EP.typeLabel('github-stars'), 'stars');
  assert.equal(EP.typeLabel('benchmark-result'), 'benchmark');
  assert.equal(EP.typeLabel('brand-new-type'), 'brand-new-type');
  assert.equal(EP.normalizeType(''), 'repo-own');
});

test('evaluators are never hidden, including unknown, claude and system', () => {
  for (const evaluator of ['unknown', 'claude', 'system', 'gemini-cli']) {
    const html = EP.renderEvaluator({evaluator});
    assert.match(html, new RegExp('by ' + evaluator));
  }
});

test('absent fields are named as absent, not dropped', () => {
  const html = EP.renderProvenance({type: 'arxiv'}, {tip: () => ''});
  assert.match(html, /no source/);
  assert.match(html, /no evaluator/);
  assert.match(html, /undated/);
  assert.doesNotMatch(html, /<a /);
  const lines = EP.provenanceLines({type: 'arxiv'});
  assert.ok(lines.some(line => /No source URL is recorded/.test(line)));
  assert.ok(lines.some(line => /No evaluator is recorded/.test(line)));
  assert.ok(lines.some(line => /No date is recorded/.test(line)));
});

test('full row renders type pill, host link, evaluator and date', () => {
  const html = EP.renderProvenance(row, {pillTip: 'formula', topExtra: '<i data-x="layer"></i>', metaExtra: '<i data-x="fresh"></i>'});
  assert.match(html, /<span class="ev-type-pill type-repo-own">repo<button/);
  assert.match(html, /title="formula"/);
  assert.match(html, /<a class="se-ev-link ev-prov-link" href="https:\/\/www\.github\.com\/acme\/widget\/blob\/main\/SKILL\.md" target="_blank" rel="noopener noreferrer"/);
  assert.match(html, /<span class="ev-prov-host">github\.com<\/span><span class="ev-prov-path">\/acme\/widget\/blob\/main\/SKILL\.md<\/span>/);
  assert.match(html, /by mbtiongson1/);
  assert.match(html, /<time class="se-ev-date" title="Date" datetime="2026-06-14">2026-06-14<\/time>/);
  assert.ok(html.indexOf('data-x="layer"') < html.indexOf('se-ev-card-meta'));
  assert.ok(html.indexOf('data-x="fresh"') > html.indexOf('se-ev-card-meta'));
});

test('duplicate rows render independently; nothing collapses them', () => {
  const rows = [row, {...row}, {...row, evaluator: 'unknown'}];
  const out = rows.map(item => EP.renderProvenance(item, {tip: () => ''}));
  assert.equal(out[0], out[1]);
  assert.equal(out.length, 3);
  assert.match(out[2], /by unknown/);
});

test('synthetic suite rows are labelled as derived, not as a recorded source', () => {
  const html = EP.renderProvenance({type: 'fusion-recipe', _synthetic: true}, {tip: () => ''});
  assert.match(html, /derived/);
  assert.doesNotMatch(html, /no evaluator|undated|no source/);
  assert.ok(EP.provenanceLines({type: 'fusion-recipe', _synthetic: true}).some(line => /not a recorded evidence row/.test(line)));
});

test('non-http sources render as inert text and never as links', () => {
  for (const source of ['javascript:alert(1)', 'data:text/html,<b>x</b>', 'ftp://example.org/x', '//evil.example/x', 'not a url', 'https://']) {
    const html = EP.renderSource({source});
    assert.doesNotMatch(html, /<a /, source);
    assert.doesNotMatch(html, /href=/, source);
    assert.equal(EP.safeHref(source), '', source);
  }
  assert.equal(EP.safeHref('http://example.org/a'), 'http://example.org/a');
  assert.equal(EP.sourceHost('HTTPS://WWW.Example.ORG/x'), 'example.org');
});

test('hostile strings are escaped in every field and attribute', () => {
  const hostile = {
    type: 'x" onmouseover="alert(1)',
    source: 'https://evil.example/"><script>alert(1)</script>',
    evaluator: '<img src=x onerror=alert(1)>',
    date: '</time><script>alert(2)</script>'
  };
  const html = EP.renderProvenance(hostile, {pillTip: '"><svg onload=alert(3)>'});
  for (const needle of ['<script', '<img', '<svg', '" onmouseover=']) {
    assert.ok(!html.includes(needle), 'unescaped ' + needle + ' in ' + html);
  }
  assert.match(html, /&lt;img src=x onerror=alert\(1\)&gt;/);
  assert.match(html, /&quot; onmouseover=&quot;/);
  // Tooltip prose is escaped by the same path (native fallback title).
  const tipHtml = EP.renderTip(hostile);
  assert.ok(!tipHtml.includes('<script') && !tipHtml.includes('<img'));
});

test('tooltip uses the shared toggletip when the lifecycle module is loaded', () => {
  withLifecycle(() => {
    const html = EP.renderTip(row);
    assert.match(html, /<span class="lc-anchor ev-prov-tip"><button type="button" class="lc-tip ev-prov-info" aria-label="Evidence provenance" aria-describedby="lc-tip-\d+">i<\/button>/);
    assert.match(html, /role="tooltip"/);
    assert.match(html, /Evaluator, as recorded: mbtiongson1\./);
    assert.match(html, /Source: https:\/\/www\.github\.com\/acme\/widget\/blob\/main\/SKILL\.md/);
  });
});

test('tooltip degrades to a native title without the lifecycle module', () => {
  assert.equal(globalThis.GaiaTrustLifecycle, undefined);
  const html = EP.renderTip(row);
  assert.match(html, /class="ev-prov-info ev-prov-info--native"/);
  assert.match(html, /title="Type: repo \(repo-own\)\.\nSource: /);
  assert.doesNotMatch(html, /lc-tipbox/);
});

test('bindTips delegates to the lifecycle module and is a no-op without it', () => {
  const mount = {tag: 'mount'};
  assert.doesNotThrow(() => EP.bindTips(mount));
  const seen = [];
  globalThis.GaiaTrustLifecycle = {components: {bindTips: el => seen.push(el)}};
  try { EP.bindTips(mount); EP.bindTips(null); } finally { delete globalThis.GaiaTrustLifecycle; }
  assert.deepEqual(seen, [mount]);
});

test('a toggletip outside a .lc-panel stays open after the click that opened it', () => {
  // Evidence cards are not inside .lc-panel; the document-level outside-click
  // handler must not close the tip its own mount just opened.
  const docHandlers = [];
  globalThis.document = {addEventListener: (type, fn) => docHandlers.push([type, fn])};
  try {
    const attrs = new Map();
    const trigger = {
      hasAttribute: name => attrs.has(name),
      setAttribute: (name, value) => attrs.set(name, value),
      removeAttribute: name => attrs.delete(name),
      closest: selector => (selector === '.lc-tip' ? trigger : null)
    };
    const mountHandlers = {};
    const mountAttrs = new Map();
    const mount = {
      addEventListener: (type, fn) => { mountHandlers[type] = fn; },
      getAttribute: name => mountAttrs.get(name) || null,
      setAttribute: (name, value) => mountAttrs.set(name, value),
      querySelectorAll: () => (attrs.has('data-open') ? [trigger] : [])
    };
    lifecycle.components.bindTips(mount);
    document.querySelectorAll = () => (attrs.has('data-open') ? [trigger] : []);
    const click = {target: trigger};
    mountHandlers.click(click);
    assert.ok(attrs.has('data-open'), 'mount handler opens the tip');
    for (const [type, fn] of docHandlers) if (type === 'click') fn(click);
    assert.ok(attrs.has('data-open'), 'document handler must not close the just-opened tip');
    // A click elsewhere still closes it.
    for (const [type, fn] of docHandlers) if (type === 'click') fn({target: {closest: () => null}});
    assert.ok(!attrs.has('data-open'), 'outside click closes the tip');
  } finally {
    delete globalThis.document;
  }
});

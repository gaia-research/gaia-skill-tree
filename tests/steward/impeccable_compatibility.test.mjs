// Repo-local compatibility checks; no browser, package install, or network.
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { randomUUID } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import * as legacyParser from '../../.agents/skills/impeccable/scripts/design-parser.mjs';
import * as parser from '../../.agents/skills/impeccable/scripts/lib/design-parser.mjs';
import * as legacyValidator from '../../.agents/skills/impeccable/scripts/live-event-validation.mjs';
import * as validator from '../../.agents/skills/impeccable/scripts/live/event-validation.mjs';
import { VISUAL_ACTIONS } from '../../.agents/skills/impeccable/scripts/live/vocabulary.mjs';
import { fetchServerStatus, buildPollReplyPayload, parseReplyArgs } from '../../.agents/skills/impeccable/scripts/live-poll.mjs';
import { createManualEditRoutes } from '../../.agents/skills/impeccable/scripts/live/manual-edit-routes.mjs';
import { sanitizeScreenshotClip } from '../../.agents/skills/impeccable/scripts/detector/engines/visual/screenshot-contrast.mjs';

const scripts = new URL('../../.agents/skills/impeccable/scripts/', import.meta.url);

test('legacy entrypoints preserve their exact public exports and use one implementation', () => {
  assert.deepEqual(Object.keys(legacyParser), ['assessCoverage', 'parseDesignMd']);
  assert.deepEqual(Object.keys(legacyValidator), ['VISUAL_ACTIONS', 'validateEvent']);
  assert.equal(legacyParser.parseDesignMd, parser.parseDesignMd);
  assert.equal(legacyParser.assessCoverage, parser.assessCoverage);
  assert.equal(legacyValidator.validateEvent, validator.validateEvent);
  assert.equal(legacyValidator.VISUAL_ACTIONS, VISUAL_ACTIONS);
});

test('quoted YAML keys work through the live-server compatibility entrypoint', () => {
  const model = legacyParser.parseDesignMd('---\ncolors:\n  "primary": "oklch(50% 0.1 30)"\n  \'secondary\': "oklch(70% 0.1 30)"\n---\n# Demo\n\n## Overview\nProse.');
  assert.equal(model.schemaVersion, 2);
  assert.equal(model.title, 'Demo');
  assert.equal(model.frontmatter.colors.primary, 'oklch(50% 0.1 30)');
  assert.equal(model.frontmatter.colors.secondary, 'oklch(70% 0.1 30)');
  assert.equal(parser.parseDesignMd('# Demo').frontmatter, null);
});

test('every existing action and invalid-event refusal survives validator reconciliation', () => {
  assert.deepEqual(VISUAL_ACTIONS, ['impeccable', 'bolder', 'quieter', 'distill', 'polish', 'typeset', 'colorize', 'layout', 'adapt', 'animate', 'delight', 'overdrive']);
  for (const action of VISUAL_ACTIONS) {
    assert.equal(legacyValidator.validateEvent({ type: 'generate', id: 'a1b2c3d4', count: 2, action, element: { outerHTML: '<div/>' } }), null);
  }
  assert.match(legacyValidator.validateEvent({ type: 'generate', id: 'a1b2c3d4', count: 2, action: 'unknown' }), /invalid action/);
  assert.match(legacyValidator.validateEvent({ type: 'generate', id: 'a1b2c3d4', mode: 'insert', count: 2 }), /insert/);
});

test('polling forwards a generated local session value and fails closed on unauthorized status', async () => {
  const sessionValue = randomUUID();
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async (url) => {
      assert.equal(new URL(url).searchParams.get('token'), sessionValue);
      return { status: 401 };
    };
    await assert.rejects(fetchServerStatus('http://localhost:1234', sessionValue), { code: 'AUTH_FAILED' });
    assert.equal(buildPollReplyPayload(sessionValue, { id: 'local-event', type: 'done' }).token, sessionValue);
    assert.throws(() => parseReplyArgs(['--reply', 'done']), /event id/);
  } finally {
    globalThis.fetch = previous;
  }
});

test('manual repair route rejects a supplied value before rollback or filesystem use', () => {
  let code;
  let rollbacks = 0;
  const handle = createManualEditRoutes({
    getToken: () => randomUUID(),
    manualApply: { rollbackTransaction: () => { rollbacks++; } },
  });
  const req = new EventEmitter();
  req.method = 'POST';
  const res = { writeHead: (value) => { code = value; }, end: () => {} };
  assert.equal(handle(req, res, new URL('http://localhost/manual-edit-repair-decision')), true);
  req.emit('data', JSON.stringify({ action: 'rollback' }));
  req.emit('end');
  assert.equal(code, 401);
  assert.equal(rollbacks, 0);
});

test('screenshot clipping remains bounded and the retained UI metadata matches its actual browser', () => {
  assert.deepEqual(sanitizeScreenshotClip({ x: -10, y: -5, width: 9999, height: 9999 }, { width: 800 }), { x: 0, y: 0, width: 800, height: 320 });
  const browser = readFileSync(new URL('live-browser.js', scripts), 'utf8');
  const rootUi = readFileSync(new URL('live-ui-core.mjs', scripts), 'utf8');
  assert.ok(browser.includes("'-configure-input-wrap'"));
  assert.ok(rootUi.includes('impeccable-live-configure-input-wrap'));
  // The extracted UI metadata names different DOM elements. Do not blindly
  // copy it over the legacy browser cohort just because its path looks newer.
  assert.ok(!browser.includes("'-selection-pill'"));
});

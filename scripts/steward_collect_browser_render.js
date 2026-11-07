#!/usr/bin/env node
/**
 * Render the tracked docs pages in headless Chromium and hand the result to the
 * Steward `browser-render` sensor as `.gaia/steward/inputs/browser-render.json`
 * (`steward-browser-render-v1`).
 *
 * The Steward sensors never launch a browser and never touch the network. A
 * driver (an operator, or the scheduled workflow) runs this collector and the
 * sensor only reads its output. The browser is real; nothing here is inferred
 * from HTML. What it records is limited to what a browser can show:
 *
 *   - same-origin requests that failed or returned HTTP >= 400,
 *   - uncaught page errors (count only, never their text),
 *   - horizontal overflow of the document at each viewport.
 *
 * It makes NO claim about visual correctness or accessibility. Page HTTP(S)
 * requests to any other host are aborted without being sent (no analytics ping)
 * and are not judged; WebSocket connections are not intercepted.
 *
 * Usage (repository root):
 *   node scripts/steward_collect_browser_render.js --repository gaia-research/gaia-skill-tree
 *
 * Options:
 *   --repository OWNER/NAME   required
 *   --out PATH                default .gaia/steward/inputs/browser-render.json
 *   --page docs/x/index.html  render only these pages (repeatable); the result
 *                             then lists every other page as unrendered, so the
 *                             sensor reports partial coverage, never clean
 *   --concurrency N           default 4
 *   --interactive             launch a real, visible browser instead of headless Chromium. Refused
 *                             unless STEWARD_INTERACTIVE_BROWSER=1: headless is free to use at any
 *                             time, a real browser is something a Steward run must be told it may use.
 *                             Only `gaia steward full run --interactive-browser` sets the variable; no
 *                             persistent policy or workflow does.
 *   --record-failure REASON   write only the status file, as a failed collection (for a driver step
 *                             that failed before this script could run, e.g. the Chromium install)
 *
 * Every run also writes browser-render-status.json beside --out ({ok|failed|refused} and a reason from
 * a fixed list), first as a failed 'collection-incomplete' marker and finally as ok, so a browser that could
 * not run (or never finished) is reported as not evaluated, never as healthy.
 *
 * Requires Playwright with a Chromium it can launch (`require('playwright')`).
 */
'use strict';

const fs = require('fs');
const http = require('http');
const path = require('path');
const { execFileSync } = require('child_process');

// Must equal _FRONTEND_EXCLUDES in src/gaia_cli/steward/sensors_contracts.py
// (a test pins the two together): generated or experimental trees are not
// hand-authored pages.
const EXCLUDES = ['docs/u', 'docs/api', 'docs/og', 'docs/graph', 'docs/okf', 'docs/experiments'];
const VIEWPORTS = [{ name: 'mobile', width: 390, height: 800 }, { name: 'desktop', width: 1280, height: 800 }];
const SCHEMA = 'steward-browser-render-v1';
const STATUS_SCHEMA = 'steward-browser-render-status-v1';
// Must equal _STATUS_REASONS in src/gaia_cli/steward/sensors_render.py (a test pins the two together).
const STATUS_REASONS = ['playwright-missing', 'chromium-install-failed', 'chromium-launch-failed', 'collection-error', 'interactive-not-allowed', 'collection-incomplete', 'headless-disabled', 'artifact-rejected'];
const NAV_TIMEOUT_MS = 20000;
const SETTLE_MS = 400;
const MAX_FAILURES = 50;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.woff2': 'font/woff2', '.ico': 'image/x-icon', '.xml': 'application/xml', '.txt': 'text/plain', '.gexf': 'application/xml', '.md': 'text/markdown' };

function parseArgs(argv) {
  const args = { out: '.gaia/steward/inputs/browser-render.json', pages: [], concurrency: 4, repository: null, interactive: false, recordFailure: null };
  for (let i = 0; i < argv.length; i++) {
    const flag = argv[i];
    if (flag === '--repository') args.repository = argv[++i];
    else if (flag === '--out') args.out = argv[++i];
    else if (flag === '--page') args.pages.push(argv[++i]);
    else if (flag === '--concurrency') args.concurrency = Number(argv[++i]);
    else if (flag === '--interactive') args.interactive = true;
    else if (flag === '--record-failure') args.recordFailure = argv[++i];
    else throw new Error(`unknown argument ${flag}`);
  }
  if (args.recordFailure !== null) {
    if (!STATUS_REASONS.includes(args.recordFailure)) throw new Error(`--record-failure must be one of ${STATUS_REASONS.join(', ')}`);
    return args;
  }
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(args.repository || '')) throw new Error('--repository OWNER/NAME is required');
  if (!Number.isInteger(args.concurrency) || args.concurrency < 1 || args.concurrency > 8) throw new Error('--concurrency must be 1..8');
  return args;
}

function writeStatus(out, state, reason, mode) {
  const file = path.join(path.dirname(out), 'browser-render-status.json');
  const document = { schemaVersion: STATUS_SCHEMA, state, collectedAt: new Date().toISOString().replace(/\.\d+Z$/, 'Z'), mode };
  if (state !== 'ok') document.reason = reason;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = path.join(path.dirname(file), `.browser-render-status-${process.pid}.tmp`);
  fs.writeFileSync(temporary, JSON.stringify(document));
  fs.renameSync(temporary, file);
}

function trackedPages() {
  const listed = execFileSync('git', ['ls-files', '-z', '--', 'docs'], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 })
    .split('\0').filter((file) => file.endsWith('.html'));
  const excluded = (file) => EXCLUDES.some((dir) => file === dir || file.startsWith(dir + '/'));
  const pages = [];
  const unsupported = [];
  let fragments = 0;
  for (const file of listed.sort()) {
    if (excluded(file)) continue;
    // The sensor accepts only plain page names; anything else is reported, not guessed at.
    if (!/^docs\/[A-Za-z0-9._\/-]{1,200}\.html$/.test(file) || file.includes('..')) { unsupported.push(file); continue; }
    // A document without an <html> element is a partial included by another page.
    if (!/<html[\s>]/i.test(fs.readFileSync(file, 'utf8'))) { fragments++; continue; }
    pages.push(file);
  }
  return { pages, fragments, unsupported };
}

function serve(root) {
  const server = http.createServer((req, res) => {
    let pathname;
    try { pathname = decodeURIComponent(new URL(req.url, 'http://x').pathname); } catch (error) { res.writeHead(400).end(); return; }
    let file = path.join(root, pathname);
    if (!file.startsWith(root + path.sep) && file !== root) { res.writeHead(403).end(); return; }
    try {
      if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
      const body = fs.readFileSync(file);
      res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream' }).end(body);
    } catch (error) {
      res.writeHead(404, { 'content-type': 'text/plain' }).end('not found');
    }
  });
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server)));
}

async function renderOne(browser, origin, page, viewport) {
  const sameOrigin = (url) => url === origin || url.startsWith(origin + '/');
  const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
  const tab = await context.newPage();
  const failures = new Map();
  let pageErrors = 0;
  const note = (rawPath, status) => {
    // The sensor carries only plain paths; anything else is reported as a marker.
    const resourcePath = /^\/[A-Za-z0-9._~%\/+=@:,()'!$*;-]{0,300}$/.test(rawPath) ? rawPath : '/unrepresentable-path';
    if (failures.size < MAX_FAILURES) failures.set(`${resourcePath}\0${status}`, { path: resourcePath, status });
  };
  await tab.route('**/*', (route) => (sameOrigin(route.request().url()) ? route.continue() : route.abort()));
  tab.on('pageerror', () => { pageErrors++; });
  tab.on('requestfailed', (request) => {
    const url = request.url();
    // ERR_ABORTED is the page cancelling its own request (navigation, teardown,
    // an image scrolled out of a lazy list), not a server or network fault.
    const aborted = /ERR_ABORTED/.test((request.failure() || {}).errorText || '');
    if (sameOrigin(url) && !aborted) note(new URL(url).pathname, null);
  });
  tab.on('response', (response) => {
    const url = response.url();
    if (sameOrigin(url) && response.status() >= 400) note(new URL(url).pathname, response.status());
  });
  const result = { path: page, viewport: viewport.name, navigation: 'ok', httpStatus: null, sameOriginFailures: [], pageErrors: 0, horizontalOverflow: null };
  try {
    const url = `${origin}/${page.replace(/^docs\//, '')}`;
    const response = await tab.goto(url, { waitUntil: 'load', timeout: NAV_TIMEOUT_MS });
    result.httpStatus = response ? response.status() : null;
    await tab.waitForTimeout(SETTLE_MS);
    result.horizontalOverflow = await tab.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    if (result.httpStatus !== null && result.httpStatus >= 400) result.navigation = 'error';
  } catch (error) {
    result.navigation = /Timeout/i.test(String(error)) ? 'timeout' : 'error';
  } finally {
    await context.close();
  }
  result.sameOriginFailures = [...failures.values()].sort((a, b) => (a.path + a.status).localeCompare(b.path + b.status));
  result.pageErrors = pageErrors;
  return result;
}

class CollectionFailure extends Error {
  constructor(reason, message) { super(message); this.reason = reason; }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const mode = args.interactive ? 'interactive' : 'headless';
  if (args.recordFailure !== null) {
    writeStatus(args.out, 'failed', args.recordFailure, mode);
    process.stdout.write(`recorded a failed collection (${args.recordFailure})\n`);
    return;
  }
  if (args.interactive && process.env.STEWARD_INTERACTIVE_BROWSER !== '1') {
    writeStatus(args.out, 'refused', 'interactive-not-allowed', mode);
    throw new CollectionFailure('interactive-not-allowed', 'an interactive browser needs STEWARD_INTERACTIVE_BROWSER=1 (gaia steward full run --interactive-browser)');
  }
  // The attempt marker. Anything short of a clean finish (killed, timed out, crashed) leaves this failed status
  // behind, so the sensor reports not evaluated and never reads an older render as this attempt's result.
  writeStatus(args.out, 'failed', 'collection-incomplete', mode);
  let chromium;
  try { ({ chromium } = require('playwright')); } catch (error) { throw new CollectionFailure('playwright-missing', 'Playwright is not installed'); }
  const discovered = trackedPages();
  const unknown = args.pages.filter((page) => !discovered.pages.includes(page));
  if (unknown.length) throw new Error(`--page is not a tracked docs page: ${unknown[0]}`);
  const wanted = args.pages.length ? args.pages : discovered.pages;
  const unrendered = discovered.pages.filter((page) => !wanted.includes(page)).map((page) => ({ path: page, reason: 'not requested' }));
  for (const file of discovered.unsupported) unrendered.push({ path: 'docs/unsupported-file-name.html', reason: 'unsupported file name' });
  const server = await serve(path.resolve('docs'));
  const origin = `http://127.0.0.1:${server.address().port}`;
  let browser;
  try { browser = await chromium.launch({ headless: !args.interactive }); } catch (error) { server.close(); throw new CollectionFailure('chromium-launch-failed', 'Chromium could not be launched'); }
  const jobs = wanted.flatMap((page) => VIEWPORTS.map((viewport) => ({ page, viewport })));
  const renders = new Array(jobs.length);
  let next = 0;
  await Promise.all(Array.from({ length: args.concurrency }, async () => {
    while (next < jobs.length) {
      const index = next++;
      renders[index] = await renderOne(browser, origin, jobs[index].page, jobs[index].viewport);
    }
  }));
  const version = browser.version();
  await browser.close();
  server.close();

  const document = {
    schemaVersion: SCHEMA,
    repository: args.repository,
    collectedAt: new Date().toISOString().replace(/\.\d+Z$/, 'Z'),
    browser: { name: 'chromium', version },
    viewports: VIEWPORTS.map(({ name, width }) => ({ name, width })),
    externalRequests: 'aborted, not judged',
    discovered: discovered.pages.length,
    fragmentsIgnored: discovered.fragments,
    unrendered,
    renders: renders.map(({ httpStatus, ...render }) => ({ ...render, sameOriginFailures: render.sameOriginFailures.map(({ path: p, status }) => ({ path: p, status })) })),
  };
  fs.mkdirSync(path.dirname(args.out), { recursive: true });
  const temporary = path.join(path.dirname(args.out), `.browser-render-${process.pid}.tmp`);
  fs.writeFileSync(temporary, JSON.stringify(document));
  fs.renameSync(temporary, args.out);
  writeStatus(args.out, 'ok', null, mode);
  const bad = renders.filter((render) => render.navigation !== 'ok').length;
  process.stdout.write(`wrote ${renders.length} renders of ${wanted.length} pages (${bad} not rendered, ${unrendered.length} not requested) to ${args.out}\n`);
}

main().catch((error) => {
  process.stderr.write(`steward_collect_browser_render: ${error.message}\n`);
  const out = process.argv.includes('--out') ? process.argv[process.argv.indexOf('--out') + 1] : '.gaia/steward/inputs/browser-render.json';
  const mode = process.argv.includes('--interactive') ? 'interactive' : 'headless';
  // A refusal already wrote its own status; any other failure is recorded so the sensor says not evaluated.
  if (!(error instanceof CollectionFailure && error.reason === 'interactive-not-allowed')) {
    try { writeStatus(out, 'failed', error instanceof CollectionFailure ? error.reason : 'collection-error', mode); } catch (writeError) { /* the exit code still reports it */ }
  }
  process.exit(error instanceof CollectionFailure && error.reason === 'interactive-not-allowed' ? 2 : 1);
});

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
 * It makes NO claim about visual correctness or accessibility. Requests to any
 * other host are aborted without being sent (nothing leaves the machine, no
 * analytics ping) and are not judged.
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
const NAV_TIMEOUT_MS = 20000;
const SETTLE_MS = 400;
const MAX_FAILURES = 50;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.woff2': 'font/woff2', '.ico': 'image/x-icon', '.xml': 'application/xml', '.txt': 'text/plain', '.gexf': 'application/xml', '.md': 'text/markdown' };

function parseArgs(argv) {
  const args = { out: '.gaia/steward/inputs/browser-render.json', pages: [], concurrency: 4, repository: null };
  for (let i = 0; i < argv.length; i++) {
    const flag = argv[i];
    if (flag === '--repository') args.repository = argv[++i];
    else if (flag === '--out') args.out = argv[++i];
    else if (flag === '--page') args.pages.push(argv[++i]);
    else if (flag === '--concurrency') args.concurrency = Number(argv[++i]);
    else throw new Error(`unknown argument ${flag}`);
  }
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(args.repository || '')) throw new Error('--repository OWNER/NAME is required');
  if (!Number.isInteger(args.concurrency) || args.concurrency < 1 || args.concurrency > 8) throw new Error('--concurrency must be 1..8');
  return args;
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
    let pathname = decodeURIComponent(new URL(req.url, 'http://x').pathname);
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
  const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
  const tab = await context.newPage();
  const failures = new Map();
  let pageErrors = 0;
  const note = (resourcePath, status) => {
    if (failures.size < MAX_FAILURES) failures.set(`${resourcePath}\0${status}`, { path: resourcePath, status });
  };
  await tab.route('**/*', (route) => (route.request().url().startsWith(origin) ? route.continue() : route.abort()));
  tab.on('pageerror', () => { pageErrors++; });
  tab.on('requestfailed', (request) => {
    const url = request.url();
    // ERR_ABORTED is the page cancelling its own request (navigation, teardown,
    // an image scrolled out of a lazy list), not a server or network fault.
    const aborted = /ERR_ABORTED/.test((request.failure() || {}).errorText || '');
    if (url.startsWith(origin) && !aborted) note(new URL(url).pathname, null);
  });
  tab.on('response', (response) => {
    const url = response.url();
    if (url.startsWith(origin) && response.status() >= 400) note(new URL(url).pathname, response.status());
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

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const { chromium } = require('playwright');
  const discovered = trackedPages();
  const wanted = args.pages.length ? args.pages : discovered.pages;
  const unrendered = discovered.pages.filter((page) => !wanted.includes(page)).map((page) => ({ path: page, reason: 'not requested' }));
  for (const file of discovered.unsupported) unrendered.push({ path: 'docs/unsupported-file-name.html', reason: 'unsupported file name' });
  const server = await serve(path.resolve('docs'));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch();
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
  const bad = renders.filter((render) => render.navigation !== 'ok').length;
  process.stdout.write(`wrote ${renders.length} renders of ${wanted.length} pages (${bad} not rendered, ${unrendered.length} not requested) to ${args.out}\n`);
}

main().catch((error) => { process.stderr.write(`steward_collect_browser_render: ${error.message}\n`); process.exit(1); });

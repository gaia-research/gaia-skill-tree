#!/usr/bin/env node
/*
 * SCAFFOLD — Phase-1 golden harness for the taxonomy parity oracle.
 * DELETE in PR3b alongside skill-semantics.js::computeBranch. Not a permanent
 * fixture — it exists only so tests/test_taxonomy_contract.py can compare the
 * Python authority (src/gaia_cli/taxonomy.py) against the live JS resolver
 * (docs/js/skill-semantics.js) while both still exist.
 *
 * Protocol: reads a JSON array from stdin of the form
 *   [ { "id": "<id>", "node": { ...skill object... }, "effRank": 5 }, ... ]
 * and writes to stdout a JSON object { "<id>": "standard"|"suite"|"unique", ... }
 * mapping each id to JS computeBranch(node, effRank).
 *
 * Run: node tests/harness/js_branch_dump.js < input.json
 */
'use strict';

const path = require('path');

// skill-semantics.js tail exposes module.exports = { computeBranch, ... }.
const semantics = require(
  path.join(__dirname, '..', '..', 'docs', 'js', 'skill-semantics.js')
);

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { raw += chunk; });
process.stdin.on('end', () => {
  let items;
  try {
    items = JSON.parse(raw);
  } catch (e) {
    process.stderr.write('js_branch_dump: bad JSON on stdin: ' + e.message + '\n');
    process.exit(2);
    return;
  }
  const out = {};
  for (const item of items) {
    const id = item && item.id;
    const node = (item && item.node) || {};
    const effRank = item ? item.effRank : undefined;
    out[id] = semantics.computeBranch(node, effRank);
  }
  process.stdout.write(JSON.stringify(out));
});

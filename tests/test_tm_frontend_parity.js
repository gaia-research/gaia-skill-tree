'use strict';

const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const sandbox = { window: {} };
vm.runInNewContext(
  fs.readFileSync('docs/js/tm-config.js', 'utf8'),
  sandbox,
  { filename: 'docs/js/tm-config.js' },
);

const TM = sandbox.window.TM_CONFIG;
assert(TM, 'tm-config must publish window.TM_CONFIG');

const fusion = { type: 'fusion-recipe', origins: ['origin-a'] };
assert.strictEqual(TM.isStructuralOnly(fusion), true);
assert.strictEqual(TM.isScoringEligible(fusion), false);
assert.strictEqual(TM.effectiveGrade(fusion, 0), '');

for (const row of [
  { type: 'benchmark-result', benchmarkId: 'unknown@v1', score: 90, unit: 'pct', provenance: 'unknown', attestor: 'x' },
  { type: 'benchmark-result', benchmarkId: 'mmlu@2024-03', score: 90, unit: 'pct', provenance: 'reported', attestor: 'x', benchmarkStatus: 'rejected' },
  { type: 'benchmark-result', score: 90, unit: 'pct', provenance: 'reported', attestor: 'x' },
  { type: 'verifier-attestation', verifiers: 3, verifierActiveRank: false },
  { type: 'repo-own', commits: 100, contributors: 2, autoMinted: true },
  { type: 'repo-own', commits: 100, contributors: 2, _phantom: true },
]) {
  assert.strictEqual(TM.isScoringEligible(row), false);
}

const validReportedBenchmark = {
  type: 'benchmark-result',
  benchmarkId: 'mmlu@2024-03',
  score: 90,
  unit: 'pct',
  provenance: 'reported',
  attestor: 'https://example.test/attestor',
};
assert.strictEqual(TM.isScoringEligible(validReportedBenchmark), true);

const suite = { suiteRef: 'acme/suite' };
const sharedRows = [
  { type: 'github-stars-own', source: 'https://github.com/acme/suite/blob/main/SKILL.md' },
  { type: 'repo-own', source: 'https://github.com/acme/suite', commits: 100, contributors: 2 },
];
const baseline = TM.createSuiteRepositoryBaselineContext(sharedRows, suite, row => {
  return row.type === 'github-stars-own' ? 200 : 36;
});
assert.strictEqual(baseline.total, 236);
assert.strictEqual(baseline.factor, 50 / 236);
const capped = sharedRows.map((row, i) => TM.applySuiteRepositoryBaseline(i === 0 ? 200 : 36, row, baseline));
assert(Math.abs(capped[0] + capped[1] - 50) < 0.01);
assert(TM.suiteRepositoryBaselineNote(baseline).includes('50 TM'));

console.log('frontend TM parity checks passed');

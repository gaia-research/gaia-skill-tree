'use strict';

const assert = require('assert');
const { execFileSync } = require('child_process');
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
assert.strictEqual(baseline.cap, 49.9);
assert.strictEqual(TM.SUITE_COMPONENT_REPOSITORY_CAP, 49.9);
assert.strictEqual(TM.YGGDRASIL_III.suiteRepositoryBaselineCap, 49.9);
assert.strictEqual(baseline.factor, 49.9 / 236);
const capped = sharedRows.map((row, i) => TM.applySuiteRepositoryBaseline(i === 0 ? 200 : 36, row, baseline));
assert(Math.abs(capped[0] + capped[1] - 49.9) < 0.01);
assert(TM.suiteRepositoryBaselineNote(baseline).includes('49.9 TM'));

// Cap-only fixture: a suite component with only shared repository evidence
// must cap to 49.9 and Grade C (just below the Grade B floor of 50).
const capOnlySkill = { id: 'acme/component', suiteRef: 'acme/suite' };
const capOnlyRows = [
  { type: 'github-stars-own', stars: 200000, source: 'https://github.com/acme/suite' },
];
const scoreFn = r => TM.applyContributionCap(r.type, TM.applyCap(r.type, TM.TYPES[r.type].describe(r).value) * TM.TYPES[r.type].weight);
const capCtx = TM.createSuiteRepositoryBaselineContext(capOnlyRows, capOnlySkill, scoreFn);
const jsTotal = capOnlyRows.reduce((n, r) => n + TM.applySuiteRepositoryBaseline(scoreFn(r), r, capCtx), 0);
const jsGrade = TM.overallGradeFor(jsTotal);

assert.strictEqual(jsTotal, 49.9);
assert.strictEqual(jsGrade, 'C');

// Parity check against Python backend (computeTrustMagnitude & computeOverallTrustGradeFromSkill)
const pyResult = JSON.parse(
  execFileSync(
    'python3',
    [
      '-c',
      `
import json
from gaia_cli.trustMagnitude import computeTrustMagnitude, computeOverallTrustGradeFromSkill
skill = {
    "id": "acme/component",
    "suiteRef": "acme/suite",
    "evidence": [
        {"type": "github-stars-own", "stars": 200000, "source": "https://github.com/acme/suite"}
    ]
}
tm = computeTrustMagnitude(skill)
grade = computeOverallTrustGradeFromSkill(skill)
print(json.dumps({"tm": tm, "grade": grade}))
`,
    ],
    { env: { ...process.env, PYTHONPATH: 'src', PYTHONDONTWRITEBYTECODE: '1' } },
  ).toString(),
);

assert.strictEqual(pyResult.tm, 49.9);
assert.strictEqual(pyResult.grade, 'C');
assert.strictEqual(jsTotal, pyResult.tm);
assert.strictEqual(jsGrade, pyResult.grade);

console.log('frontend TM parity checks passed');

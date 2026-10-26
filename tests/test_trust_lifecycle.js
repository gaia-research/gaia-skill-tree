/**
 * test_trust_lifecycle.js — Unit and DOM integration tests for Trust Lifecycle (Yggdrasil IV P4 slice)
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const {
  isSafeHttps,
  esc,
  formatDateUTC,
  normalizeChallenge,
  normalizeAwards,
  buildTrustLifecycleViewModel,
  renderTrustLifecycleHtml,
  renderLifecycleSection
} = require('../docs/js/trust-lifecycle.js');

const FIXTURES = require('./fixtures/synthetic_trust_lifecycle_fixtures.js');

// ── Mock DOM helper for headless testing without external jsdom ──
function createMockElement(id, tagName = 'div') {
  let _innerHTML = '';
  let _classList = new Set();
  let _children = [];
  let _attributes = {};

  return {
    id: id || '',
    tagName: tagName.toUpperCase(),
    nodeType: 1,
    style: {},
    get innerHTML() { return _innerHTML; },
    set innerHTML(val) { _innerHTML = String(val); },
    classList: {
      add: (cls) => _classList.add(cls),
      remove: (cls) => _classList.remove(cls),
      contains: (cls) => _classList.contains(cls)
    },
    setAttribute: (k, v) => { _attributes[k] = String(v); },
    getAttribute: (k) => _attributes[k] || null,
    querySelector: () => null,
    querySelectorAll: () => []
  };
}

// ── 1. Security & Sanitization Tests ──────────────────────────────
test('isSafeHttps strictly validates secure links', () => {
  assert.strictEqual(isSafeHttps('https://github.com/gaia-research/gaia-skill-tree/issues/100'), true);
  assert.strictEqual(isSafeHttps('https://example.com/receipt.json'), true);

  // Rejected protocols and malformed strings
  assert.strictEqual(isSafeHttps('http://insecure.com'), false);
  assert.strictEqual(isSafeHttps('javascript:alert(1)'), false);
  assert.strictEqual(isSafeHttps('data:text/html,<html>'), false);
  assert.strictEqual(isSafeHttps('ftp://files.example.com'), false);
  assert.strictEqual(isSafeHttps(''), false);
  assert.strictEqual(isSafeHttps(null), false);
  assert.strictEqual(isSafeHttps(undefined), false);
  assert.strictEqual(isSafeHttps(12345), false);
});

test('esc properly escapes HTML special characters', () => {
  assert.strictEqual(esc('<script>alert("xss")</script>'), '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;');
  assert.strictEqual(esc("Tom & 'Jerry'"), 'Tom &amp; &#39;Jerry&#39;');
  assert.strictEqual(esc(null), '');
  assert.strictEqual(esc(undefined), '');
});

test('formatDateUTC standardizes dates', () => {
  assert.strictEqual(formatDateUTC('2026-10-26T14:30:00Z'), '2026-10-26');
  assert.strictEqual(formatDateUTC('2026-05-01'), '2026-05-01');
  assert.strictEqual(formatDateUTC(''), 'Unknown Date');
  assert.strictEqual(formatDateUTC(null), 'Unknown Date');
});

// ── 2. State 1: In Good Standing ──────────────────────────────────
test('State 1: In Good Standing view model & rendering', () => {
  const entry = FIXTURES.inGoodStanding;
  const vm = buildTrustLifecycleViewModel(entry);

  assert.notStrictEqual(vm, null);
  assert.strictEqual(vm.standing.key, 'in-good-standing');
  assert.strictEqual(vm.standing.badgeText, '[Approved] In Good Standing');
  assert.strictEqual(vm.standing.tone, 'teal');
  assert.strictEqual(vm.standing.approvedStars, 4);
  assert.strictEqual(vm.standing.approvedTm, 125);

  assert.strictEqual(vm.origin.handle, 'synthetic-author');
  assert.strictEqual(vm.origin.status, 'held');
  assert.strictEqual(vm.origin.isContested, false);
  assert.strictEqual(vm.activeChallengesCount, 0);
  assert.strictEqual(vm.historicalAwards.length, 2);

  const html = renderTrustLifecycleHtml(vm);
  assert.match(html, /\[Approved\] In Good Standing/);
  assert.match(html, /Snapshot:.*snap-synthetic-2026-10-26-001/);
  assert.match(html, /Approved Rank:.*4&#9733;/);
  assert.match(html, /Approved TM:.*125/);
  assert.match(html, /@synthetic-author/);
  assert.match(html, /No verified public challenges on record/);
  assert.match(html, /Merit-Based Origin Awarded/);
  assert.match(html, /4★ Unique Promotion/);
});

// ── 3. State 2: Verified Scoped Capability Challenge ──────────────
test('State 2: Scoped capability challenge keeps Origin distinct and uncontested', () => {
  const entry = FIXTURES.scopedCapabilityChallenge;
  const vm = buildTrustLifecycleViewModel(entry);

  assert.notStrictEqual(vm, null);
  // Standing reflects adjudication pending on scoped claim
  assert.strictEqual(vm.standing.key, 'adjudication-pending');
  assert.strictEqual(vm.standing.badgeText, '[Pending] Adjudication Pending');
  assert.strictEqual(vm.standing.tone, 'gold');

  // Load-bearing invariant: Scoped challenge does NOT contest Origin!
  assert.strictEqual(vm.origin.isContested, false);
  assert.strictEqual(vm.origin.status, 'held');
  assert.strictEqual(vm.activeChallengesCount, 1);

  const ch = vm.challenges[0];
  assert.strictEqual(ch.materialToOrigin, false);
  assert.strictEqual(ch.status, 'verified-pending');
  assert.strictEqual(ch.isAdjudicationPending, true);
  assert.strictEqual(ch.verifier.verifierId, 'synthetic-independent-verifier');
  assert.strictEqual(isSafeHttps(ch.verifier.receiptUrl), true);

  const html = renderTrustLifecycleHtml(vm);
  assert.match(html, /\[Scoped Capability Challenge\]/);
  assert.match(html, /\[Pending\] Adjudication Pending/);
  assert.match(html, /\[Held\] Origin Held/);
  assert.match(html, /Throughput degrades by 45%/);
  assert.match(html, /synthetic-comparator-fast v2\.0/);
  assert.match(html, /Public Verification Receipt/);
  assert.doesNotMatch(html, /\[Contested\] Origin Contested/);
});

// ── 4. State 3: Material Origin Challenge (Contested) ─────────────
test('State 3: Material Origin challenge triggers contested marker without transfer/vacancy', () => {
  const entry = FIXTURES.originContested;
  const vm = buildTrustLifecycleViewModel(entry);

  assert.notStrictEqual(vm, null);
  // Standing and origin both flag Contested
  assert.strictEqual(vm.standing.key, 'contested');
  assert.strictEqual(vm.standing.badgeText, '[Contested] Origin Contested');
  assert.strictEqual(vm.standing.tone, 'honor-red');

  // Load-bearing invariant: Origin is contested, BUT incumbent remains held (never vacant/transferred)
  assert.strictEqual(vm.origin.isContested, true);
  assert.strictEqual(vm.origin.status, 'contested');
  assert.strictEqual(vm.origin.handle, 'synthetic-author');

  const ch = vm.challenges[0];
  assert.strictEqual(ch.materialToOrigin, true);
  assert.strictEqual(ch.status, 'verified-pending');

  const html = renderTrustLifecycleHtml(vm);
  assert.match(html, /\[Contested\] Origin Contested/);
  assert.match(html, /\[Material Origin Challenge\]/);
  assert.match(html, /Current Origin remains held by the incumbent/);
  assert.match(html, /does not transfer or vacate while contested/);
  assert.match(html, /@synthetic-author/);
});

// ── 5. State 4: Approved Numerical Degradation ─────────────────────
test('State 4: Approved numerical degradation details Class C adjudication', () => {
  const entry = FIXTURES.approvedNumericalDegradation;
  const vm = buildTrustLifecycleViewModel(entry);

  assert.notStrictEqual(vm, null);
  assert.strictEqual(vm.standing.key, 'degraded');
  assert.strictEqual(vm.standing.badgeText, '[Degraded] Approved Numerical Degradation');
  assert.strictEqual(vm.standing.tone, 'honor-red');
  assert.strictEqual(vm.standing.approvedStars, 3);
  assert.strictEqual(vm.standing.approvedTm, 72);

  assert.notStrictEqual(vm.standing.degradation, null);
  assert.strictEqual(vm.standing.degradation.priorStars, 4);
  assert.strictEqual(vm.standing.degradation.degradedStars, 3);
  assert.match(vm.standing.degradation.reason, /persistent failure/);

  const html = renderTrustLifecycleHtml(vm);
  assert.match(html, /\[Degraded\] Approved Numerical Degradation/);
  assert.match(html, /Rank Shift:.*4&#9733; &#8594; 3&#9733;/);
  assert.match(html, /Class C Ruling Reference/);
});

// ── 6. State 5: Technical Resolution with Recalibration Pending ───
test('State 5: Technical resolution distinguishes Class B proof from pending Class C recalibration', () => {
  const entry = FIXTURES.technicalResolutionRecalibrationPending;
  const vm = buildTrustLifecycleViewModel(entry);

  assert.notStrictEqual(vm, null);
  assert.strictEqual(vm.standing.key, 'recalibration-pending');
  assert.strictEqual(vm.standing.badgeText, '[Pending] Technical Resolution (Recalibration Pending)');
  assert.strictEqual(vm.standing.tone, 'violet');

  assert.notStrictEqual(vm.standing.recalibrationPending, null);
  assert.match(vm.standing.recalibrationPending.reason, /Class B technical closure passed/);

  const html = renderTrustLifecycleHtml(vm);
  assert.match(html, /\[Pending\] Technical Resolution \(Recalibration Pending\)/);
  assert.match(html, /\[Technical Resolution\] Recalibration Pending/);
  assert.match(html, /Technical Resolution Proof/);
  assert.match(html, /ch-synthetic-resolved-001/);
});

// ── 7. State 6: Upstream-Superseded Historical Challenge ──────────
test('State 6: Upstream-superseded challenge permanently preserved in history', () => {
  const entry = FIXTURES.upstreamSupersededChallenge;
  const vm = buildTrustLifecycleViewModel(entry);

  assert.notStrictEqual(vm, null);
  assert.strictEqual(vm.challenges.length, 1);
  const ch = vm.challenges[0];
  assert.strictEqual(ch.isUpstreamSuperseded, true);
  assert.strictEqual(ch.status, 'resolved-by-upstream-improvement');
  assert.strictEqual(ch.resolution.upstreamVersion, 'v1.5.0');

  const html = renderTrustLifecycleHtml(vm);
  assert.match(html, /\[Superseded\] Upstream Resolved/);
  assert.match(html, /v1\.5\.0/);
  assert.match(html, /Technical Resolution Proof/);
});

// ── 8. State 7: Partial / Unknown State ───────────────────────────
test('State 7: Partial or unknown state renders gracefully without fabricating zero or false', () => {
  const entry = FIXTURES.partialUnknownState;
  const vm = buildTrustLifecycleViewModel(entry);

  assert.notStrictEqual(vm, null);
  assert.strictEqual(vm.standing.key, 'unknown');
  assert.strictEqual(vm.standing.badgeText, '[Unassessed] Partial / Unknown Standing');
  assert.strictEqual(vm.standing.approvedStars, null); // NOT 0
  assert.strictEqual(vm.standing.approvedTm, null);    // NOT 0
  assert.strictEqual(vm.snapshot.isPinned, false);

  const html = renderTrustLifecycleHtml(vm);
  assert.match(html, /\[Unassessed\] Partial \/ Unknown Standing/);
  assert.match(html, /Unpinned \/ Provisional evaluation/);
  assert.match(html, /Approved Rank:.*Unassessed/);
  assert.doesNotMatch(html, /Approved Rank:.*0★/);
});

// ── 9. State 8: Malformed & Shadow Allegations Rejection ─���────────
test('State 8: Malformed, shadow, model-only, and XSS entries are rejected; P1 and P2 gates hold', () => {
  const entry = FIXTURES.malformedAndShadowAllegations;
  const vm = buildTrustLifecycleViewModel(entry);

  assert.notStrictEqual(vm, null);
  // P1 Gate: Snapshot lacks approvedBy and approvalRef, so approved provenance MUST be false
  assert.strictEqual(vm.snapshot.hasApprovedProvenance, false);
  assert.strictEqual(vm.standing.key, 'provisional');
  assert.strictEqual(vm.standing.badgeText, '[Provisional] Unassessed Standing');
  assert.strictEqual(vm.standing.approvedStars, null); // Never falsely approved!
  assert.strictEqual(vm.standing.approvedTm, null);    // Never falsely approved!

  // P2 Gate: string "false" for origin.contested must NOT contest Origin
  assert.strictEqual(vm.origin.handle, 'synthetic-author');
  assert.strictEqual(vm.origin.status, 'held');
  assert.strictEqual(vm.origin.isContested, false);

  // Spurious / shadow / model-only / XSS challenges are rejected
  assert.strictEqual(vm.challenges.length, 0);
  assert.strictEqual(vm.activeChallengesCount, 0);

  const html = renderTrustLifecycleHtml(vm);
  assert.doesNotMatch(html, /\[Approved\] In Good Standing/);
  assert.match(html, /\[Provisional\] Unassessed Standing/);
  assert.match(html, /UNAPPROVED SNAPSHOT/);
  assert.match(html, /Approved Rank:.*Unassessed/);
  assert.doesNotMatch(html, /Approved Rank:.*4&#9733;/);
  assert.doesNotMatch(html, /shadow-001/);
  assert.doesNotMatch(html, /model-only-003/);
  assert.doesNotMatch(html, /javascript:alert/);
  assert.match(html, /No verified public challenges on record/);
});

// ── 10. State 9: Absent trustLifecycle Payload ────────────────────
test('State 9: Absent payload returns null and clears mount exactly preserving existing UI', () => {
  const entry = FIXTURES.absentPayload;
  const vm = buildTrustLifecycleViewModel(entry);
  assert.strictEqual(vm, null);

  const mount = createMockElement('se-tm');
  mount.innerHTML = 'pre-existing-content-should-clear';
  renderLifecycleSection(mount, entry);
  assert.strictEqual(mount.innerHTML, '');

  // Null entry
  renderLifecycleSection(mount, null);
  assert.strictEqual(mount.innerHTML, '');
});

// ── 11. DOM Mount & Accessibility Check ───────────────────────────
test('DOM render creates accessible semantic structure and keyboard targets', () => {
  const mount = createMockElement('se-tm');
  renderLifecycleSection(mount, FIXTURES.scopedCapabilityChallenge);

  const html = mount.innerHTML;
  assert.match(html, /<section class="se-lc-section" aria-labelledby="seLifecycleHeading">/);
  assert.match(html, /<h3 id="seLifecycleHeading" class="se-flow-title">/);
  assert.match(html, /role="region"/);
  assert.match(html, /<details class="se-lc-challenge-item/);
  assert.match(html, /<summary class="se-lc-challenge-summary" tabindex="0">/);

  // Status badges must have explicit text labels (never color-only)
  const badgeRegex = /<span class="se-lc-badge[^"]*">([^<]+)<\/span>/g;
  let match;
  let badgeCount = 0;
  while ((match = badgeRegex.exec(html)) !== null) {
    badgeCount++;
    const text = match[1].trim();
    assert.match(text, /^\[(Approved|Contested|Pending|Degraded|Rebutted|Superseded|Upheld|Narrowed|Rejected|Held|Unassessed)\]/);
  }
  assert.ok(badgeCount > 0, 'Must have rendered at least one badge');
});

// ── 12. Full Explorer 5-Section Preservation Verification ─────────
test('Skill Explorer verifies all 5 sections render cleanly with and without trustLifecycle', () => {
  const code = fs.readFileSync(path.join(__dirname, '../docs/js/skill-explorer.js'), 'utf8');

  // Verify that the file compiles without syntax error
  assert.doesNotThrow(() => {
    new vm.Script(code);
  });

  // Verify that both IIFEs exist
  assert.match(code, /^\(function\(\)\{/);
  assert.match(code, /\(function\(\)\s*\{\s*\n\s*var treeDialog\s*=\s*document\.getElementById\('treeDialog'\);/);

  // Verify that the wiring in openExplorer safely checks GaiaTrustLifecycle
  assert.match(code, /_safeRender\('Trust Lifecycle', 'se-tm'/);
  assert.match(code, /window\.GaiaTrustLifecycle/);

  // Verify that all 5 existing sections are retained
  assert.match(code, /_safeRender\('Install',\s*'se-install'/);
  assert.match(code, /_safeRender\('Docs',\s*'se-docs'/);
  assert.match(code, /_safeRender\('Upgrade',\s*'se-upgrade'/);
  assert.match(code, /_safeRender\('Timeline',\s*'se-changelog'/);
  assert.match(code, /renderHero\(ns, generic\);/);
});

// ── 13. Corner cases: Narrowed/Rejected & Unsafe Link Stripping ────
test('Corner cases: Narrowed, Rejected, and unsafe links are sanitized', () => {
  const customEntry = {
    id: 'synthetic-author/corner-cases',
    trustLifecycle: {
      snapshot: {
        snapshotId: 'snap-corner-001',
        evaluatedAtUTC: '2026-10-26T00:00:00Z',
        approvalRef: 'http://insecure-link.com' // Unsafe! Must be stripped
      },
      approvedStanding: {
        status: 'in-good-standing',
        approvedStars: 4,
        degradation: {
          priorStars: 5,
          degradedStars: 4,
          reason: 'Test degradation',
          decisionRef: 'javascript:alert(2)' // Unsafe! Must be stripped
        }
      },
      origin: {
        currentOriginHandle: 'synthetic-author'
      },
      challenges: [
        {
          challengeId: 'ch-narrowed-001',
          claim: 'Narrowed claim on edge runtime',
          status: 'narrowed',
          verifiedAtUTC: '2026-10-20T00:00:00Z',
          verifier: {
            verifierId: 'verifier-1',
            verificationMethod: 'test',
            receiptUrl: 'https://github.com/gaia-research/gaia-skill-tree/issues/100'
          }
        },
        {
          challengeId: 'ch-rejected-002',
          claim: 'Spurious challenge rejected on lack of reproducibility',
          status: 'rejected',
          verifiedAtUTC: '2026-10-21T00:00:00Z',
          verifier: {
            verifierId: 'verifier-2',
            verificationMethod: 'test',
            receiptUrl: 'https://github.com/gaia-research/gaia-skill-tree/issues/101'
          }
        }
      ],
      historicalAwards: [
        {
          awardType: 'milestone',
          dateUTC: '2026-07-01T00:00:00Z',
          handle: 'synthetic-author',
          title: 'Unsafe Award Receipt',
          receiptRef: 'data:text/html,bad' // Unsafe! Must be stripped
        }
      ]
    }
  };

  const vm = buildTrustLifecycleViewModel(customEntry);
  assert.notStrictEqual(vm, null);
  assert.strictEqual(vm.snapshot.approvalRef, ''); // stripped
  assert.strictEqual(vm.standing.degradation.decisionRef, ''); // stripped
  assert.strictEqual(vm.challenges.length, 2);
  assert.strictEqual(vm.challenges[0].status, 'narrowed');
  assert.strictEqual(vm.challenges[1].status, 'rejected');
  assert.strictEqual(vm.historicalAwards[0].receiptRef, ''); // stripped

  const html = renderTrustLifecycleHtml(vm);
  assert.doesNotMatch(html, /http:\/\/insecure-link/);
  assert.doesNotMatch(html, /javascript:alert/);
  assert.doesNotMatch(html, /data:text\/html/);
  assert.match(html, /\[Narrowed\] Narrowed/);
  assert.match(html, /\[Rejected\] Rejected/);
});

// ── 14. P1 Provenance Gate: No false approved standing without approved snapshot ──
test('P1: Unpinned snapshot or missing approvedBy/approvalRef never renders approved standing', () => {
  // Case A: Missing snapshot altogether
  const noSnapshot = {
    id: 'synthetic-author/no-snap',
    level: '4★',
    trustMagnitude: 100,
    trustLifecycle: {
      approvedStanding: {
        status: 'in-good-standing',
        approvedStars: 4,
        approvedTm: 100
      }
    }
  };
  const vmNoSnap = buildTrustLifecycleViewModel(noSnapshot);
  assert.notStrictEqual(vmNoSnap, null);
  assert.strictEqual(vmNoSnap.snapshot.isPinned, false);
  assert.strictEqual(vmNoSnap.snapshot.hasApprovedProvenance, false);
  assert.strictEqual(vmNoSnap.standing.key, 'provisional');
  assert.strictEqual(vmNoSnap.standing.badgeText, '[Provisional] Unassessed Standing');
  assert.strictEqual(vmNoSnap.standing.approvedStars, null);
  assert.strictEqual(vmNoSnap.standing.approvedTm, null);

  const htmlNoSnap = renderTrustLifecycleHtml(vmNoSnap);
  assert.doesNotMatch(htmlNoSnap, /\[Approved\] In Good Standing/);
  assert.doesNotMatch(htmlNoSnap, /Approved Rank:.*4&#9733;/);
  assert.match(htmlNoSnap, /Approved Rank:.*Unassessed/);

  // Case B: Pinned snapshot but missing approvedBy
  const pinnedNoApprover = {
    id: 'synthetic-author/pinned-no-approver',
    level: '4★',
    trustMagnitude: 100,
    trustLifecycle: {
      snapshot: {
        snapshotId: 'snap-2026-10-26-test',
        evaluatedAtUTC: '2026-10-26T00:00:00Z',
        policyVersion: 'yggdrasil-4.0.0-synthetic',
        approvalRef: 'https://github.com/gaia-research/gaia-skill-tree/pull/9999'
        // Missing approvedBy!
      },
      approvedStanding: {
        status: 'in-good-standing',
        approvedStars: 4,
        approvedTm: 100
      }
    }
  };
  const vmNoApprover = buildTrustLifecycleViewModel(pinnedNoApprover);
  assert.strictEqual(vmNoApprover.snapshot.isPinned, true);
  assert.strictEqual(vmNoApprover.snapshot.hasApprovedProvenance, false);
  assert.strictEqual(vmNoApprover.standing.key, 'provisional');
  assert.strictEqual(vmNoApprover.standing.approvedStars, null);
  assert.strictEqual(vmNoApprover.standing.approvedTm, null);

  // Case C: Pinned snapshot with insecure http approvalRef
  const insecureRef = {
    id: 'synthetic-author/insecure-ref',
    level: '4★',
    trustMagnitude: 100,
    trustLifecycle: {
      snapshot: {
        snapshotId: 'snap-2026-10-26-test',
        evaluatedAtUTC: '2026-10-26T00:00:00Z',
        policyVersion: 'yggdrasil-4.0.0-synthetic',
        approvedBy: 'synthetic-maintainer',
        approvalRef: 'http://insecure-link.com' // Not HTTPS!
      },
      approvedStanding: {
        status: 'in-good-standing',
        approvedStars: 4,
        approvedTm: 100
      }
    }
  };
  const vmInsecure = buildTrustLifecycleViewModel(insecureRef);
  assert.strictEqual(vmInsecure.snapshot.hasApprovedProvenance, false);
  assert.strictEqual(vmInsecure.standing.key, 'provisional');
  assert.strictEqual(vmInsecure.standing.approvedStars, null);
});

// ── 15. P2 Boolean Gate: Malformed booleans strictly do not contest Origin ──
test('P2: String "false" and non-boolean materialToOrigin/contested do not contest Origin', () => {
  const normFalseString = normalizeChallenge({
    challengeId: 'ch-test-p2-001',
    claim: 'P2 test challenge with string false',
    materialToOrigin: 'false',
    status: 'verified-pending',
    verifiedAtUTC: '2026-10-26T00:00:00Z',
    verifier: {
      verifierId: 'test-verifier',
      verificationMethod: 'benchmark-runner',
      receiptUrl: 'https://example.com/receipt'
    }
  });
  assert.strictEqual(normFalseString.materialToOrigin, false);

  const normTrueBoolean = normalizeChallenge({
    challengeId: 'ch-test-p2-002',
    claim: 'P2 test challenge with strict boolean true',
    materialToOrigin: true,
    status: 'verified-pending',
    verifiedAtUTC: '2026-10-26T00:00:00Z',
    verifier: {
      verifierId: 'test-verifier',
      verificationMethod: 'benchmark-runner',
      receiptUrl: 'https://example.com/receipt'
    }
  });
  assert.strictEqual(normTrueBoolean.materialToOrigin, true);

  // Test inside full view model with contested: "false" string
  const spoofContested = {
    id: 'synthetic-author/spoof-contested',
    level: '4★',
    trustMagnitude: 115,
    trustLifecycle: {
      snapshot: {
        snapshotId: 'snap-2026-10-26-test',
        evaluatedAtUTC: '2026-10-26T00:00:00Z',
        policyVersion: 'yggdrasil-4.0.0-synthetic',
        approvedBy: 'synthetic-maintainer',
        approvalRef: 'https://github.com/gaia-research/gaia-skill-tree/pull/9999'
      },
      approvedStanding: {
        status: 'in-good-standing',
        approvedStars: 4,
        approvedTm: 115
      },
      origin: {
        currentOriginHandle: 'synthetic-author',
        contested: 'false' // String "false"
      },
      challenges: [
        {
          challengeId: 'ch-test-p2-003',
          claim: 'Scoped challenge with string "false" materialToOrigin',
          materialToOrigin: 'false',
          status: 'verified-pending',
          verifiedAtUTC: '2026-10-26T00:00:00Z',
          verifier: {
            verifierId: 'test-verifier',
            verificationMethod: 'benchmark-runner',
            receiptUrl: 'https://example.com/receipt'
          }
        }
      ]
    }
  };
  const vmSpoof = buildTrustLifecycleViewModel(spoofContested);
  assert.strictEqual(vmSpoof.origin.isContested, false);
  assert.strictEqual(vmSpoof.origin.status, 'held');
  assert.notStrictEqual(vmSpoof.standing.key, 'contested');
});

// ── 16. Single Coherent Authority & Rehearsal Marking ─────────────
test('Single Coherent Authority rejects contradictory payloads and marks rehearsals explicitly', () => {
  // Contradictory fixture: hero TM 125 vs approved TM 105
  const vmContradictory = buildTrustLifecycleViewModel(FIXTURES.contradictoryPayload);
  assert.notStrictEqual(vmContradictory, null);
  assert.strictEqual(vmContradictory.standing.key, 'contradictory');
  assert.strictEqual(vmContradictory.standing.badgeText, '[Degraded] Contradictory Authority Payload');
  assert.strictEqual(vmContradictory.standing.tone, 'honor-red');
  assert.strictEqual(vmContradictory.standing.approvedStars, null);
  assert.strictEqual(vmContradictory.standing.approvedTm, null);

  const htmlContradictory = renderTrustLifecycleHtml(vmContradictory);
  assert.match(htmlContradictory, /\[Degraded\] Contradictory Authority Payload/);
  assert.match(htmlContradictory, /Payload rejected under single-authority doctrine/);

  // Rehearsal fixture: explicitly marked as rehearsal
  const vmRehearsal = buildTrustLifecycleViewModel(FIXTURES.rehearsalState);
  assert.notStrictEqual(vmRehearsal, null);
  assert.strictEqual(vmRehearsal.snapshot.isRehearsal, true);
  assert.strictEqual(vmRehearsal.standing.key, 'rehearsal');
  assert.strictEqual(vmRehearsal.standing.badgeText, '[Rehearsal] In Good Standing (Rehearsal Only)');

  const htmlRehearsal = renderTrustLifecycleHtml(vmRehearsal);
  assert.match(htmlRehearsal, /\[Rehearsal\] In Good Standing \(Rehearsal Only\)/);
  assert.match(htmlRehearsal, /REHEARSAL/);
  assert.match(htmlRehearsal, /Publication backend pending/);
});

// ── 17. Scoped Responsive CSS Rules for 390px and 320px ────────────
test('Scoped CSS rules ensure heading wrapping and prevent mobile overflow at 390px and 320px', () => {
  const css = fs.readFileSync(path.join(__dirname, '../docs/css/styles.css'), 'utf8');

  // Scoped section heading wrapping
  assert.match(css, /\.se-lc-section \.se-flow-title\s*\{[^}]*overflow-wrap:\s*break-word/);
  assert.match(css, /\.se-lc-section \.se-flow-h__lede\s*\{[^}]*flex:\s*1 1 100%/);
  assert.match(css, /\.se-lc-section \.se-flow-h::after\s*\{[^}]*display:\s*none/);

  // Media query overrides for mobile widths
  assert.match(css, /@media\s*\(\s*max-width:\s*480px\s*\)\s*\{[^}]*\.se-lc-section \.se-flow-title/);
  assert.match(css, /@media\s*\(\s*max-width:\s*360px\s*\)\s*\{[^}]*\.se-lc-section \.se-flow-title/);

  // Empty #se-tm rule
  assert.match(css, /#se-tm:empty\s*\{[^}]*display:\s*none/);
});

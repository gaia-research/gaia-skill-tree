/* docs/js/tm-config.js  —  Yggdrasil III Trust Magnitude frontend configuration
 *
 * When RFC G7 formulas change, update:
 *   1. THIS FILE                               ← frontend SoT
 *   2. src/gaia_cli/trustMagnitude.py          ← backend mirror
 *   3. docs/codex/trust-methodology.html       ← canonical public RFC
 *   4. registry/schema/meta.json               ← perRowGradeThresholds fixture
 *   5. tests/test_row_grading.py               ← bump hardcoded expected values
 *   6. Regenerate only docs/api/v1/evidence-types.json from the schema
 *
 * Everything else in docs/js/ reads from window.TM_CONFIG — no other
 * file needs touching when formulas change.
 *
 * Load this BEFORE skill-explorer.js and plaque.js on every HTML page.
 */
(function () {
  'use strict';

  var RFC_BASE = 'https://gaiaskilltree.com/codex/trust-methodology.html';
  var RFC = {
    overview:      RFC_BASE + '#trust-magnitude',
    types:         RFC_BASE + '#evidence-types',
    grades:        RFC_BASE + '#grade-thresholds',
    suiteVsFusion: RFC_BASE + '#suite-vs-fusion',
    apex:          RFC_BASE + '#apex-gate',
    worked:        RFC_BASE + '#worked-example',
  };

  // ── Aggregate skill grade thresholds (docs/trust/index.html §3) ───────────
  var OVERALL_GRADES = [
    { grade: 'S', floor: 250, name: 'Platinum',
      note: 'requires ≥3 distinct positive scoring types AND an eligible independent witness' },
    { grade: 'A', floor: 100, name: 'Gold',   note: '' },
    { grade: 'B', floor:  50, name: 'Silver', note: '' },
    { grade: 'C', floor:  20, name: 'Bronze', note: '' },
  ];

  // Structural/self-produced types do not count toward S diversity.
  var SELF_PRODUCIBLE = ['fusion-recipe', 'self-attestation', 'repo-own'];
  var S_WITNESS_TYPES = ['benchmark-result', 'verifier-attestation', 'peer-review'];
  var YGGDRASIL_III = {
    suiteRepositoryBaselineCap: 50,
    suiteRepositoryBaselineTypes: ['github-stars-own', 'repo-own'],
    benchmarkVerifiedLanes: ['verified', 'ci-reproduced', 'verifier-attested'],
    benchmarkReportedLanes: ['reported', 'mirrored'],
    benchmarkRejectedLanes: ['rejected', 'pending', 'candidate', 'retired', 'unknown'],
  };
  var SUITE_COMPONENT_REPOSITORY_CAP = 50;

  function isInvalidEvidence(row) {
    if (!row || row._phantom === true || row.phantom === true) return true;
    var eligibility = scoreEligibility(row);
    return !eligibility.eligible && !eligibility.structuralOnly;
  }

  function githubRepo(source) {
    var m = String(source || '').match(/github\.com[/:]([^/]+)\/([^/#?]+)/i);
    return m ? (m[1] + '/' + m[2].replace(/\.git$/, '')).toLowerCase() : '';
  }

  function suiteRepositoryCapMultiplier(rows, skill) {
    var ref = String(skill && skill.suiteRef || '').trim().toLowerCase();
    if (!ref || ref.indexOf('/') < 0 || !Array.isArray(rows)) return 1;
    var shared = rows.filter(function (row) {
      var type = canonicalType(row.type || '');
      return (type === 'github-stars-own' || type === 'repo-own') && githubRepo(row.source || row.url) === ref;
    });
    if (!shared.length) return 1;
    var total = shared.reduce(function (sum, row) {
      if (isInvalidEvidence(row)) return sum;
      var cfg = TYPES[canonicalType(row.type || '')];
      var d = cfg && cfg.describe(row);
      return sum + (d && d.value != null ? applyContributionCap(canonicalType(row.type || ''), applyCap(canonicalType(row.type || ''), d.value) * cfg.weight) : 0);
    }, 0);
    return total > SUITE_COMPONENT_REPOSITORY_CAP ? SUITE_COMPONENT_REPOSITORY_CAP / total : 1;
  }

  // ── Per-type config (docs/trust/index.html §2) ────────────────────────────
  //
  // Adding a new evidence type = one entry here; all (i) tooltips auto-update.
  //
  // Required fields:
  //   label        Short pill label for the UI
  //   formula      Human-readable formula string (shown in tooltip header)
  //   describe(row) → { value, expr } or null  — computes per-row artifact score
  //                   from raw metric fields in the evidence row object.
  //                   Returns null when required fields are absent.
  //   weight        RFC type weight multiplier
  //   cap           Per-row magnitude cap (null = uncapped or dynamic)
  //   plateau       { factors:[…], maxRows:N } | null
  //   freshness     { decayPerYear: 0…1 } | null  (half-life for benchmark: 0.5)
  //   gradeFloors   { S?, A?, B?, C? }  — per-row grade thresholds from meta.json
  //   gradeCeiling  'S'|'A'|'B'|'C' | null
  //   anchor        Key of RFC.* for the "Full methodology" link in tooltips
  var TYPES = {

    'github-stars-own': {
      label: 'stars',
      formula: 'min(250, stars/250)',
      describe: function (row) {
        var s = row.stars != null ? Number(row.stars) : null;
        if (s == null) return null;
        var val = Math.min(250, s / 250);
        return { value: val, expr: 'min(250, ' + s + '/250)' };
      },
      weight: 1.0,
      cap: 250,
      plateau: { factors: [1.0], maxRows: 1 },
      freshness: null,
      gradeFloors: { S: 88, A: 60, B: 35, C: 20 },
      gradeCeiling: null,
      anchor: 'types',
    },

    'proxy-containment': {
      label: 'proxy',
      formula: '(containingRepoStars / 1000) × 0.8',
      describe: function (row) {
        var s = row.externalStars != null ? Number(row.externalStars) : null;
        if (s == null || s < 10000) return null;
        return { value: (s / 1000) * 0.8,
                 expr:  '(' + s + '/1000) × 0.8' };
      },
      weight: 1.0,
      cap: 160,
      plateau: { factors: [1.0], maxRows: 1 },
      freshness: null,
      gradeFloors: { S: 112, A: 64, B: 32, C: 16 },
      gradeCeiling: null,
      anchor: 'types',
    },

    'verifier-attestation': {
      label: 'verifier',
      formula: '30 × N verifiers (4★+)',
      describe: function (row) {
        var n = row.verifiers != null ? Number(row.verifiers) : null;
        if (n == null) return null;
        return { value: 30 * n,
                 expr:  '30 × ' + n + ' verifier' + (n === 1 ? '' : 's') };
      },
      weight: 1.5,
      cap: null,
      plateau: { factors: [1.0, 0.85, 0.70], maxRows: 5 },
      freshness: null,
      gradeFloors: { S: 90, A: 54, B: 27, C: 14 },
      gradeCeiling: null,
      anchor: 'types',
    },

    'benchmark-result': {
      label: 'benchmark',
      formula: 'benchmark base score × lane multiplier (verified 2×, reported 1×)  (50% decay/yr)',
      describe: function (row) {
        var base = null;
        var expr = '';
        if (row.percentile != null) {
          base = Number(row.percentile);
          expr = 'percentile ' + base;
        } else if (row.score != null) {
          var raw = Number(row.score);
          var unit = String(row.unit || '').toLowerCase();
          base = raw;
          expr = 'score ' + raw + (unit ? ' ' + unit : '');
          if ((unit === 'pass@1' || unit === 'pass@10' || unit === 'accuracy' || unit === 'f1') && raw <= 1) {
            base = raw * 100;
            expr += ' → ' + base;
          }
        }
        if (base == null) return null;
        var prov = String(row.provenance || '').toLowerCase();
        var lane = (prov === 'verified' || prov === 'ci-reproduced' || prov === 'verifier-attested') ? 'verified'
          : (prov === 'reported' || prov === 'mirrored') ? 'reported'
          : 'rejected';
        var mult = lane === 'verified' ? 2 : (lane === 'reported' ? 1 : 0);
        return { value: base * mult, expr: expr + ' × ' + mult + ' ' + lane + ' lane' };
      },
      weight: 1.4,
      cap: 100,
      plateau: { factors: [1.0], maxRows: 1 },
      freshness: { decayPerYear: 0.5 },
      gradeFloors: { S: 95, A: 70, B: 40, C: 20 },
      gradeCeiling: null,
      anchor: 'types',
    },

    'arxiv': {
      label: 'arxiv',
      formula: 'citations / 5',
      describe: function (row) {
        var c = row.citations != null ? Number(row.citations) : null;
        if (c == null) return null;
        return { value: c / 5, expr: c + ' / 5' };
      },
      weight: 1.0,
      cap: 100,
      plateau: { factors: [1.0, 0.5, 0.25, 0.125], maxRows: 4 },
      freshness: null,
      gradeFloors: { S: 95, A: 70, B: 40, C: 15 },
      gradeCeiling: 'S',
      anchor: 'types',
    },

    'peer-review': {
      label: 'peer-review',
      formula: '25 × N reviewers (4★+)',
      describe: function (row) {
        var n = row.reviewers != null
          ? Number(row.reviewers)
          : (row.evaluator ? 1 : null);
        if (n == null) return null;
        var note = (row.reviewers == null && row.evaluator)
          ? ' (defaulted to 1 — evaluator present)' : '';
        return { value: 25 * n,
                 expr:  '25 × ' + n + ' reviewer' + (n === 1 ? '' : 's') + note };
      },
      weight: 1.2,
      cap: null,
      plateau: { factors: [1.0, 0.5, 0.25], maxRows: 3 },
      freshness: { decayPerYear: 0.125 },
      gradeFloors: { S: 88, A: 60, B: 35, C: 14 },
      gradeCeiling: 'S',
      anchor: 'types',
    },

    'repo-own': {
      label: 'repo',
      formula: '(commits / 200) + (contributors² × 2)',
      describe: function (row) {
        var c = row.commits      != null ? Number(row.commits)      : 0;
        var k = row.contributors != null ? Number(row.contributors) : 0;
        if (row.commits == null && row.contributors == null) return null;
        return { value: (c / 200) + (k * k * 2),
                 expr:  '(' + c + '/200) + (' + k + '² × 2)' };
      },
      weight: 0.6,
      cap: 60,
      plateau: { factors: [1.0, 0.5, 0.25], maxRows: 3 },
      freshness: null,
      gradeFloors: { B: 22, C: 9 },
      gradeCeiling: 'B',
      anchor: 'types',
    },

    'self-attestation': {
      label: 'self',
      formula: 'flat 10',
      describe: function (_row) {
        return { value: 10, expr: 'flat 10' };
      },
      weight: 0.5,
      cap: 10,
      plateau: { factors: [1.0], maxRows: 1 },
      freshness: null,
      gradeFloors: { C: 4 },
      gradeCeiling: 'C',
      anchor: 'types',
    },

    'social-signal': {
      label: 'social',
      formula: 'log₁₀(views) × 8 × creator_mult × engagement_ratio',
      describe: function (row) {
        var v = row.views != null ? Number(row.views) : null;
        if (v == null || v < 1000) {
          return v != null
            ? { value: 0, expr: 'views ' + v + ' < 1000 → score 0' }
            : null;
        }
        var cm = row.creatorMultiplier != null ? Number(row.creatorMultiplier) : 1.0;
        var er = row.engagementRatio   != null ? Number(row.engagementRatio)   : 1.0;
        var raw = Math.log10(v) * 8 * cm * er;
        var expr = 'log₁₀(' + v + ') × 8';
        if (cm !== 1.0) expr += ' × ' + cm + ' creator';
        if (er !== 1.0) expr += ' × ' + er + ' eng';
        return { value: raw, expr: expr };
      },
      weight: 1.0,
      cap: 80,
      plateau: { factors: [1.0, 0.5, 0.25], maxRows: 3 },
      freshness: { decayPerYear: 0.5 },
      gradeFloors: { A: 60, B: 28, C: 12 },
      gradeCeiling: 'A',
      anchor: 'types',
    },

    'fusion-recipe': {
      label: 'fusion',
      formula: 'structural/provenance metadata only — 0 TM',
      describe: function (row) {
        return { value: 0, expr: 'structural/provenance metadata only' };
      },
      weight: 0,
      cap: 0,
      contributionCap: 0,
      plateau: { factors: [1.0], maxRows: 1 },
      freshness: null,
      gradeFloors: {},
      gradeCeiling: null,
      anchor: 'suiteVsFusion',
    },

  };

  // Legacy type aliases — mirror trustMagnitude.py TYPE_ALIASES
  var ALIASES = { 'github-stars': 'github-stars-own', 'repo': 'repo-own' };

  function canonicalType(t) {
    return (t && ALIASES[t]) || t || '';
  }

  function _benchmarkLane(row) {
    var raw = String((row && row.provenance) || '').trim().toLowerCase();
    if (YGGDRASIL_III.benchmarkVerifiedLanes.indexOf(raw) !== -1) return 'verified';
    if (YGGDRASIL_III.benchmarkReportedLanes.indexOf(raw) !== -1) return 'reported';
    return 'rejected';
  }

  function benchmarkScoringEligibility(row) {
    if (!row || canonicalType(row.type || '') !== 'benchmark-result') return false;
    if (!row.benchmarkId ||
        (row.score == null && row.percentile == null) || !row.unit || !row.provenance || !row.attestor) return false;
    if (row.scoresTrustMagnitude === false || row.catalogScoringEnabled === false) return false;
    var catalogStatus = String(row.catalogStatus || row.benchmarkCatalogStatus || row.benchmarkStatus || '').trim().toLowerCase();
    if (catalogStatus && ['verified', 'reported', 'approved'].indexOf(catalogStatus) === -1) return false;
    var lane = _benchmarkLane(row);
    if (lane === 'rejected') return false;
    if (lane === 'verified' && (!row.runAt || !row.datasetHash || !row.benchmarkInputHash)) return false;
    return true;
  }

  function scoreEligibility(row) {
    var t = canonicalType(row && row.type || '');
    if (!row || !TYPES[t]) return { eligible: false, reason: 'unknown-type' };
    if (row._phantom === true || row.phantom === true) return { eligible: false, reason: 'phantom' };
    if (row.autoMinted === true && t !== 'fusion-recipe') return { eligible: false, reason: 'auto-minted' };
    if (t === 'fusion-recipe') return { eligible: false, structuralOnly: true, reason: 'structural-only' };
    if (t === 'benchmark-result' && !benchmarkScoringEligibility(row)) return { eligible: false, reason: 'benchmark-ineligible' };
    if (t === 'verifier-attestation' && (row.verifierActiveRank === false || row.derank === true)) {
      return { eligible: false, reason: 'verifier-deranked' };
    }
    return { eligible: true, reason: 'eligible' };
  }

  function isScoringEligible(row) {
    return scoreEligibility(row).eligible;
  }

  function isStructuralOnly(row) {
    return !!scoreEligibility(row).structuralOnly;
  }

  function _githubRepository(source) {
    var value = String(source || '').trim().toLowerCase();
    if (!value) return '';
    value = value.replace(/#.*$/, '').replace(/\/(tree|blob)\/[^/]+\/.*$/, '').replace(/\/$/, '');
    var match = value.match(/^https?:\/\/(?:www\.)?github\.com\/([^/]+\/[^/]+)/);
    return match ? match[1].replace(/\.git$/, '') : '';
  }

  function isSuiteRepositoryBaselineRow(row, skill) {
    var suiteRef = skill && (skill.suiteRef || skill._suiteRef);
    var t = canonicalType(row && row.type || '');
    return !!(suiteRef && YGGDRASIL_III.suiteRepositoryBaselineTypes.indexOf(t) !== -1 &&
      _githubRepository(row.source || row.url || row.sourceUrl) === String(suiteRef).trim().toLowerCase());
  }

  // Build once per skill/group so matching stars + repo rows share one proportional cap.
  function createSuiteRepositoryBaselineContext(rows, skill, scoreFn) {
    var context = { suiteRef: skill && (skill.suiteRef || skill._suiteRef) || '', cap: YGGDRASIL_III.suiteRepositoryBaselineCap, total: 0, factor: 1 };
    if (!context.suiteRef || !Array.isArray(rows) || typeof scoreFn !== 'function') return context;
    rows.forEach(function (row) {
      if (!isSuiteRepositoryBaselineRow(row, skill) || !isScoringEligible(row)) return;
      var score = scoreFn(row);
      if (score != null && score > 0) context.total += score;
    });
    if (context.total > context.cap) context.factor = context.cap / context.total;
    return context;
  }

  function applySuiteRepositoryBaseline(score, row, context) {
    if (score == null || !context || context.factor === 1 || !isSuiteRepositoryBaselineRow(row, context)) return score;
    return Math.round(score * context.factor * 10) / 10;
  }

  function suiteRepositoryBaselineNote(context) {
    if (!context || !context.suiteRef || context.factor >= 1) return '';
    return 'SuiteRef repository baseline: github-stars-own + repo-own rows from ' + context.suiteRef +
      ' share a combined cap of ' + context.cap + ' TM per component; applied scale ×' + context.factor.toFixed(3) +
      '; component-specific evidence remains fully eligible.';
  }

  function applyCap(typeKey, raw) {
    var cfg = TYPES[typeKey];
    if (!cfg || cfg.cap == null) return raw;
    return Math.min(raw, cfg.cap);
  }

  function applyContributionCap(typeKey, score) {
    var cfg = TYPES[typeKey];
    if (!cfg || cfg.contributionCap == null) return score;
    return Math.min(score, cfg.contributionCap);
  }

  // Grade-floor fallback when no metric drivers are present but a grade is set.
  function gradeFloor(typeKey, gradeChar) {
    var cfg = TYPES[typeKey];
    if (!cfg || !cfg.gradeFloors) return null;
    var v = cfg.gradeFloors[gradeChar];
    return v != null ? v : null;
  }

  function overallGradeFor(tm) {
    if (tm == null) return 'ungraded';
    for (var i = 0; i < OVERALL_GRADES.length; i++) {
      if (tm >= OVERALL_GRADES[i].floor) return OVERALL_GRADES[i].grade;
    }
    return 'ungraded';
  }

  function gradeName(g) {
    for (var i = 0; i < OVERALL_GRADES.length; i++) {
      if (OVERALL_GRADES[i].grade === g) return OVERALL_GRADES[i].name;
    }
    return '';
  }

  // Derive the effective display grade for an evidence row.
  // Single source of truth used by both skill-explorer.js and evidence-library.js.
  // Priority: persisted ev.grade (written by calibrate-evidence-grades) → live score derivation
  // from metric fields + gradeFloors. The live fallback covers legacy rows that only have
  // class: (not grade:) and rows added before the next calibration sweep.
  //
  // weightedScore must be the result of _deriveWeightedScore / deriveWeightedScore
  // already computed for the MAG bar. Pass null if not yet computed (function derives it
  // via gradeFloors grade-floor lookup instead, which is less precise).
  function effectiveGrade(ev, weightedScore) {
    if (!isScoringEligible(ev)) return '';
    var g = (ev.grade || '').toUpperCase().charAt(0);
    if (g) return g;
    var t = canonicalType(ev.type || '');
    var cfg = TYPES[t];
    if (!cfg) return '';
    var floors = cfg.gradeFloors;
    var ceiling = cfg.gradeCeiling;
    if (!floors) return '';
    var ceilOrd = {S:0, A:1, B:2, C:3};
    var score = weightedScore;
    // If no pre-computed score provided, estimate from gradeFloors only (no multipliers).
    if (score == null) return '';
    var d = '';
    var order = ['S','A','B','C'];
    for (var i = 0; i < order.length; i++) {
      if (floors[order[i]] != null && score >= floors[order[i]]) { d = order[i]; break; }
    }
    if (d && ceiling && ceilOrd[d] < ceilOrd[ceiling]) d = ceiling;
    return d;
  }

  window.TM_CONFIG = {
    RFC_BASE: RFC_BASE,
    RFC: RFC,
    TYPES: TYPES,
    ALIASES: ALIASES,
    OVERALL_GRADES: OVERALL_GRADES,
    SELF_PRODUCIBLE: SELF_PRODUCIBLE,
    S_WITNESS_TYPES: S_WITNESS_TYPES,
    YGGDRASIL_III: YGGDRASIL_III,
    SUITE_COMPONENT_REPOSITORY_CAP: SUITE_COMPONENT_REPOSITORY_CAP,
    isInvalidEvidence: isInvalidEvidence,
    suiteRepositoryCapMultiplier: suiteRepositoryCapMultiplier,
    canonicalType: canonicalType,
    benchmarkScoringEligibility: benchmarkScoringEligibility,
    scoreEligibility: scoreEligibility,
    isScoringEligible: isScoringEligible,
    isStructuralOnly: isStructuralOnly,
    isSuiteRepositoryBaselineRow: isSuiteRepositoryBaselineRow,
    createSuiteRepositoryBaselineContext: createSuiteRepositoryBaselineContext,
    applySuiteRepositoryBaseline: applySuiteRepositoryBaseline,
    suiteRepositoryBaselineNote: suiteRepositoryBaselineNote,
    applyCap: applyCap,
    applyContributionCap: applyContributionCap,
    gradeFloor: gradeFloor,
    effectiveGrade: effectiveGrade,
    overallGradeFor: overallGradeFor,
    gradeName: gradeName,
  };

})();

/* ── MIGRATION: when G7 RFC formulas change ──────────────────────────────────
 *
 * Update in this exact order:
 *   1. docs/js/tm-config.js                      ← THIS FILE (frontend SoT)
 *   2. src/gaia_cli/trustMagnitude.py             ← backend mirror
 *   3. docs/codex/trust-methodology.html          ← canonical public RFC
 *   4. registry/schema/meta.json::perRowGradeThresholds
 *   5. tests/test_row_grading.py + tests/test_calibrate_evidence_grades.py
 *   6. Regenerate only docs/api/v1/evidence-types.json from the schema
 *
 * Nothing else in docs/js/ needs editing — _deriveTrustNum, _magTooltip,
 * and _fieldTrustNotch all read from window.TM_CONFIG.
 * ──────────────────────────────────────────────────────────────────────────── */

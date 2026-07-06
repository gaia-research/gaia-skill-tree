/* docs/js/tm-config.js  —  G7 Trust Magnitude single source of truth (frontend)
 *
 * When RFC G7 formulas change, update:
 *   1. THIS FILE                               ← frontend SoT
 *   2. src/gaia_cli/trustMagnitude.py          ← backend mirror
 *   3. docs/codex/trust-methodology.html       ← canonical public RFC
 *   4. registry/schema/meta.json               ← perRowGradeThresholds fixture
 *   5. tests/test_row_grading.py               ← bump hardcoded expected values
 *   6. python scripts/build_docs.py            ← regenerate docs/graph/named/index.json
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
      note: 'requires ≥3 distinct types AND ≥1 non-self-producible row (diversity gate)' },
    { grade: 'A', floor: 100, name: 'Gold',   note: '' },
    { grade: 'B', floor:  50, name: 'Silver', note: '' },
    { grade: 'C', floor:  20, name: 'Bronze', note: '' },
  ];

  // Types that cannot anchor the S diversity gate alone (RFC §4).
  var SELF_PRODUCIBLE = ['fusion-recipe', 'self-attestation', 'repo-own'];

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
      formula: 'min(200, stars/1000) ÷ min(skillCountInRepo, 4)',
      describe: function (row) {
        var s = row.stars != null ? Number(row.stars) : null;
        if (s == null) return null;
        var k = row.skillCountInRepo != null ? Math.min(4, Math.max(1, Number(row.skillCountInRepo))) : 1;
        var val = Math.min(200, s / 1000) / k;
        var expr = k > 1
          ? 'min(200, ' + s + '/1000) ÷ min(' + row.skillCountInRepo + ', 4)'
          : 'min(200, ' + s + '/1000)';
        return { value: val, expr: expr };
      },
      weight: 1.0,
      cap: 200,
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
      formula: 'percentile (0–100)  (50% decay/yr)',
      describe: function (row) {
        var p = row.percentile != null ? Number(row.percentile) : null;
        if (p == null) return null;
        return { value: p, expr: 'percentile = ' + p };
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
      formula: '20 × N  (N ≤ 10)  |  200 + 20 × √(N−10)  (N > 10)  where N = graded ≥C origins',
      describe: function (row) {
        var n = null;
        var caveat = '';
        // Priority 1: explicit graded-origin count written by backend (exact match)
        if (row.gradedOriginCount != null) {
          n = Number(row.gradedOriginCount);
        // Priority 2: numeric origins field (also a pre-computed graded count from CLI)
        } else if (!Array.isArray(row.origins) && row.origins != null) {
          n = Number(row.origins);
        // Priority 3: raw array length — approximation only; tooltip says so
        } else if (Array.isArray(row.origins)) {
          n = row.origins.length;
          caveat = ' (raw count — backend filters to graded ≥C origins only)';
        }
        if (n == null) return null;
        var raw = n <= 10 ? 20 * n : 200 + 20 * Math.sqrt(n - 10);
        var expr = n <= 10
          ? '20 × ' + n + caveat
          : '200 + 20 × √(' + n + '−10)' + caveat;
        return { value: raw, expr: expr };
      },
      weight: 1.5,
      cap: null,
      plateau: { factors: [1.0], maxRows: 1 },
      freshness: null,
      gradeFloors: { S: 200, A: 120, B: 60, C: 30 },
      gradeCeiling: null,
      anchor: 'suiteVsFusion',
    },

  };

  // Legacy type aliases — mirror trustMagnitude.py TYPE_ALIASES
  var ALIASES = { 'github-stars': 'github-stars-own', 'repo': 'repo-own' };

  function canonicalType(t) {
    return (t && ALIASES[t]) || t || '';
  }

  function applyCap(typeKey, raw) {
    var cfg = TYPES[typeKey];
    if (!cfg || cfg.cap == null) return raw;
    return Math.min(raw, cfg.cap);
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
    canonicalType: canonicalType,
    applyCap: applyCap,
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
 *   6. Run: python scripts/build_docs.py
 *
 * Nothing else in docs/js/ needs editing — _deriveTrustNum, _magTooltip,
 * and _fieldTrustNotch all read from window.TM_CONFIG.
 * ──────────────────────────────────────────────────────────────────────────── */

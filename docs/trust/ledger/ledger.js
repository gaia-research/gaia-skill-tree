/*
 * /trust/ledger/ledger.js
 *
 * Single-table sortable, filterable Trust Ledger.
 * No bands, no modals, no circles. Pure flat ranked list.
 *
 * Data shape — see scripts/generateLeaderboardData.py:
 *   { version, generatedAt, summary, rows: [
 *       { skillId, tm, grade, currentStars, mayStars, juneStars, g7Stars, flag, apexResults }
 *     ]
 *   }
 */
(function () {
  'use strict';

  var DATA_URL    = '../../graph/ledger/data.json';
  var SKILL_LINK  = '../../named/#explorer/';
  var GAIA_VER    = window.GAIA_VERSION || '';
  var STARS_ORDER = { '0★': 0, '1★': 1, '2★': 2, '3★': 3, '4★': 4, '5★': 5, '6★': 6 };
  var STARS_NAMES = {
    '0★': 'Unawakened', '1★': 'Awakened', '2★': 'Named', '3★': 'Evolved',
    '4★': 'Hardened',   '5★': 'Transcendent', '6★': 'Transcendent'
  };

  var APEX_LABELS = {
    aGradedOriginsGte5:         '≥8 A-graded origins',
    sourceTenureDaysGte180AorS: '180d tenure at A/S',
    directNestedSuiteGte1:      '≥1 direct nested suite',
    depth2OnlyReachableGte1:    '≥1 depth-2-only node',
    overallGradeS:              'Overall grade S',
    apexPromotionPrSigned:      'Apex PR signed',
    crossOrgVerifier:           'Cross-org verifier',
    systemWideCap:              'System cap'
  };

  var state = {
    rows: [],
    summary: null,
    generatedAt: '',
    version: '',
    activeBand: 'all',
    query: '',
    sort: { col: 'tm', dir: 'desc' }
  };

  /* ── Load data ─────────────────────────────────────────────── */
  fetch(DATA_URL + (GAIA_VER ? '?v=' + encodeURIComponent(GAIA_VER) : ''), { cache: 'no-cache' })
    .then(function (r) {
      if (!r.ok) { throw new Error('HTTP ' + r.status); }
      return r.json();
    })
    .then(function (data) {
      state.rows        = Array.isArray(data.rows) ? data.rows : [];
      state.summary     = data.summary || null;
      state.generatedAt = data.generatedAt || '';
      state.version     = data.version || '';

      renderDistribution();
      renderTable();
      renderGeneratedAt();
    })
    .catch(function (err) {
      console.error('[ledger] failed to load', err);
      var body = document.getElementById('lbTableBody');
      if (body) {
        body.innerHTML = '<tr><td colspan="6" class="lb-empty">Could not load data. ' +
          '<a href="' + DATA_URL + '">Try the raw JSON →</a></td></tr>';
      }
    });

  /* ── Distribution strip (replaces stat cards) ────────────── */
  function renderDistribution() {
    var el = document.getElementById('lbDistribution');
    if (!el || !state.summary) return;
    var s = state.summary;
    var total = Math.max(1, s.total || 1);

    // Each grade bar segment proportional to count, with metallic fill
    var segments = [
      { grade: 'S', count: s.S || 0,        label: 'Platinum' },
      { grade: 'A', count: s.A || 0,        label: 'Gold' },
      { grade: 'B', count: s.B || 0,        label: 'Silver' },
      { grade: 'C', count: s.C || 0,        label: 'Bronze' },
      { grade: 'ungraded', count: s.ungraded || 0, label: 'Ungraded' }
    ];

    var bar = '<div class="lb-dist-bar" role="img" aria-label="Distribution by grade">' +
      segments.map(function (seg) {
        if (!seg.count) return '';
        var pct = (seg.count / total * 100).toFixed(2);
        var ds = seg.grade === 'ungraded' ? 'none' : seg.grade;
        return '<div class="lb-dist-seg" data-trust-grade="' + ds + '"' +
               ' style="width:' + pct + '%"' +
               ' title="' + seg.label + ' (' + seg.grade + '): ' + seg.count + ' skills · ' + pct + '%">' +
               '<span class="lb-dist-seg__count">' + seg.count + '</span>' +
               '</div>';
      }).join('') +
      '</div>';

    var keys = '<div class="lb-dist-keys">' +
      segments.map(function (seg) {
        var ds = seg.grade === 'ungraded' ? 'none' : seg.grade;
        var glabel = seg.grade === 'ungraded' ? '—' : seg.grade;
        return '<button type="button" class="lb-dist-key" data-band="' + seg.grade + '">' +
                 '<span class="lb-dist-key__pip" data-trust-grade="' + ds + '">' + glabel + '</span>' +
                 '<span class="lb-dist-key__name">' + seg.label + '</span>' +
                 '<span class="lb-dist-key__count">' + seg.count + '</span>' +
               '</button>';
      }).join('') +
      '<div class="lb-dist-key lb-dist-key--total">' +
        '<span class="lb-dist-key__name">Total</span>' +
        '<span class="lb-dist-key__count">' + (s.total || 0) + '</span>' +
      '</div>' +
      ((s.floor || s.up) ? '<div class="lb-dist-key lb-dist-key--meta">' +
        (s.floor ? '<span class="lb-dist-meta-pill"><strong>floor</strong> ' + s.floor + '</span>' : '') +
        (s.up ?    '<span class="lb-dist-meta-pill"><strong>up</strong> ' + s.up + '</span>' : '') +
      '</div>' : '') +
      '</div>';

    el.innerHTML = bar + keys;
  }

  /* ── Generated-at footer ───────────────────────────────────── */
  function renderGeneratedAt() {
    var el = document.getElementById('lbGeneratedAt');
    if (!el) return;
    var iso = state.generatedAt;
    var pretty = iso;
    try {
      var d = new Date(iso);
      if (!isNaN(d.getTime())) {
        pretty = d.toISOString().replace('T', ' ').replace(/:\d\dZ$/, ' UTC')
               + (state.version ? '  ·  registry v' + state.version : '');
      }
    } catch (e) { /* keep raw */ }
    el.textContent = pretty || '—';
  }

  /* ── Table render ──────────────────────────────────────────── */
  function renderTable() {
    var body = document.getElementById('lbTableBody');
    if (!body) return;

    var q = state.query.trim().toLowerCase();
    var filtered = state.rows.filter(function (r) {
      if (state.activeBand !== 'all' && r.grade !== state.activeBand) return false;
      if (q && r.skillId.toLowerCase().indexOf(q) === -1) return false;
      return true;
    });

    sortRowsInPlace(filtered, state.sort);

    if (filtered.length === 0) {
      body.innerHTML = '<tr><td colspan="6" class="lb-empty">No skills match the current filter.</td></tr>';
    } else {
      body.innerHTML = filtered.map(function (r, i) { return renderRow(r, i + 1); }).join('');
    }

    updateSortIndicators();
  }

  function renderRow(r, rank) {
    var skillId = r.skillId || '';
    var idLink = SKILL_LINK + encodeURIComponent(skillId);

    // May / June stars (with G7 cutover semantics)
    var mayStars = r.mayStars || r.currentStars || '?';
    var juneStars = r.juneStars || r.currentStars || '?';
    var mayCls = STARS_ORDER.hasOwnProperty(mayStars) ? ('lb-stars--' + STARS_ORDER[mayStars]) : '';
    var juneCls = STARS_ORDER.hasOwnProperty(juneStars) ? ('lb-stars--' + STARS_ORDER[juneStars]) : '';
    var mayTitle = STARS_NAMES[mayStars] ? (mayStars + ' ' + STARS_NAMES[mayStars] + ' (pre-G7)') : mayStars;
    var juneTitle = STARS_NAMES[juneStars] ? (juneStars + ' ' + STARS_NAMES[juneStars] + ' (current)') : juneStars;

    var gradeRaw = r.grade || 'ungraded';
    var gradeKey = gradeRaw === 'ungraded' ? 'none' : gradeRaw;
    var gradeLabel = gradeRaw === 'ungraded' ? '—' : gradeRaw;

    // Stars-direction arrow inline with TM
    var mayOrd = STARS_ORDER.hasOwnProperty(mayStars) ? STARS_ORDER[mayStars] : -1;
    var juneOrd = STARS_ORDER.hasOwnProperty(juneStars) ? STARS_ORDER[juneStars] : -1;
    var arrow = '·', arrowCls = 'lb-arrow lb-arrow--flat', arrowTitle = 'No change vs. May';
    if (mayOrd >= 0 && juneOrd >= 0) {
      if (juneOrd > mayOrd) {
        arrow = '▲'; arrowCls = 'lb-arrow lb-arrow--up';
        arrowTitle = 'June stars rose vs. May (' + mayStars + ' → ' + juneStars + ')';
      } else if (juneOrd < mayOrd) {
        arrow = '▼'; arrowCls = 'lb-arrow lb-arrow--down';
        arrowTitle = 'June stars fell vs. May (' + mayStars + ' → ' + juneStars + ')';
      } else {
        arrowTitle = 'June stars held vs. May (' + mayStars + ')';
      }
    }

    var apexInfo = renderApexInfo(r.apexResults, juneStars, gradeRaw);

    var tmText = (typeof r.tm === 'number' ? r.tm.toFixed(1) : esc(String(r.tm)));

    return '' +
      '<tr data-trust-grade="' + esc(gradeKey) + '">' +
        '<td class="col-rank" title="Rank is computed live; not stored">' + rank + '</td>' +
        '<td class="col-id"><a href="' + esc(idLink) + '" title="' + esc(skillId) + '">' +
          esc(skillId) + '</a></td>' +
        '<td class="col-tm">' +
          '<span class="' + arrowCls + '" title="' + esc(arrowTitle) + '" aria-label="' + esc(arrowTitle) + '">' + arrow + '</span>' +
          '<span class="lb-tm-num">' + tmText + '</span>' +
        '</td>' +
        '<td class="col-grade">' +
          '<span class="lb-grade-pill" data-trust-grade="' + esc(gradeKey) + '">' + esc(gradeLabel) + '</span>' +
        '</td>' +
        '<td class="col-stars"><span class="lb-stars ' + mayCls + '" title="' + esc(mayTitle) + '">' + esc(mayStars) + '</span></td>' +
        '<td class="col-g7"><span class="lb-stars ' + juneCls + '" title="' + esc(juneTitle) + '">' + esc(juneStars) + '</span>' + apexInfo + '</td>' +
      '</tr>';
  }

  function renderApexInfo(apexResults, juneStars, grade) {
    // Apex info only meaningful for 5★+ skills (S-grade gate is enforced by builder).
    if (!apexResults) return '';
    var ord = STARS_ORDER.hasOwnProperty(juneStars) ? STARS_ORDER[juneStars] : -1;
    if (ord < 5) return '';

    var keys = Object.keys(apexResults);
    var active = keys.filter(function (k) { return apexResults[k] !== null; });
    if (active.length === 0) return '';
    var passed = active.filter(function (k) { return apexResults[k] === true; });
    var failed = active.filter(function (k) { return apexResults[k] === false; });
    var isApex = passed.length === active.length;

    var lines = ['Apex eligibility: ' + passed.length + '/' + active.length + (isApex ? ' (apex)' : '')];
    if (failed.length) {
      lines.push('Missing: ' + failed.map(function (k) { return APEX_LABELS[k] || k; }).join(', '));
    }
    var title = lines.join('\n');
    var cls = 'lb-apex-info' + (isApex ? ' lb-apex-info--apex' : '');
    return ' <span class="' + cls + '" title="' + esc(title) + '" aria-label="' + esc(title) + '" tabindex="0">i</span>';
  }

  /* ── Sort ──────────────────────────────────────────────────── */
  function sortRowsInPlace(rows, ss) {
    var col = ss.col, dir = ss.dir === 'asc' ? 1 : -1;
    rows.sort(function (a, b) {
      var av, bv;
      switch (col) {
        case 'rank': av = 0; bv = 0; break;  // physical position; stable secondary applies
        case 'id':
          av = (a.skillId || '').toLowerCase();
          bv = (b.skillId || '').toLowerCase();
          break;
        case 'tm':
          av = +a.tm || 0; bv = +b.tm || 0;
          break;
        case 'grade':
          av = gradeOrder(a.grade); bv = gradeOrder(b.grade);
          break;
        case 'may':
          av = STARS_ORDER[a.mayStars || a.currentStars] != null ? STARS_ORDER[a.mayStars || a.currentStars] : -1;
          bv = STARS_ORDER[b.mayStars || b.currentStars] != null ? STARS_ORDER[b.mayStars || b.currentStars] : -1;
          break;
        case 'june':
          av = STARS_ORDER[a.juneStars || a.currentStars] != null ? STARS_ORDER[a.juneStars || a.currentStars] : -1;
          bv = STARS_ORDER[b.juneStars || b.currentStars] != null ? STARS_ORDER[b.juneStars || b.currentStars] : -1;
          break;
        default:
          av = 0; bv = 0;
      }
      if (av < bv) return -1 * dir;
      if (av > bv) return  1 * dir;
      // stable secondary: TM desc → id asc
      if (col !== 'tm') {
        var atm = +a.tm || 0, btm = +b.tm || 0;
        if (atm !== btm) return btm - atm;
      }
      var aid = (a.skillId || '').toLowerCase();
      var bid = (b.skillId || '').toLowerCase();
      return aid < bid ? -1 : aid > bid ? 1 : 0;
    });
  }

  function gradeOrder(g) {
    return { S: 4, A: 3, B: 2, C: 1, ungraded: 0 }[g] || 0;
  }
  function apexScore(ar) {
    if (!ar) return -1;
    var keys = Object.keys(ar).filter(function (k) { return ar[k] !== null; });
    var passed = keys.filter(function (k) { return ar[k] === true; });
    if (keys.length === 0) return 0;
    return passed.length / keys.length;
  }

  function updateSortIndicators() {
    var ths = document.querySelectorAll('#lbTable thead th[data-col]');
    ths.forEach(function (th) {
      var col = th.getAttribute('data-col');
      th.removeAttribute('aria-sort');
      var existing = th.querySelector('.lb-sort');
      if (existing) existing.remove();
      var arrow;
      if (state.sort.col === col) {
        th.setAttribute('aria-sort', state.sort.dir === 'asc' ? 'ascending' : 'descending');
        arrow = state.sort.dir === 'asc' ? '▲' : '▼';
      } else {
        arrow = '↕';
      }
      var span = document.createElement('span');
      span.className = 'lb-sort';
      span.textContent = arrow;
      th.appendChild(span);
    });
  }

  /* ── Wire up controls ──────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    var search = document.getElementById('lbSearch');
    if (search) {
      var debounce;
      search.addEventListener('input', function (e) {
        clearTimeout(debounce);
        debounce = setTimeout(function () {
          state.query = e.target.value || '';
          renderTable();
        }, 80);
      });
    }

    // Tab filters
    document.addEventListener('click', function (e) {
      var tab = e.target.closest('.lb-tab');
      if (tab) {
        document.querySelectorAll('.lb-tab').forEach(function (x) { x.classList.remove('is-active'); });
        tab.classList.add('is-active');
        state.activeBand = tab.getAttribute('data-band') || 'all';
        renderTable();
        return;
      }

      // Distribution-key click also filters
      var key = e.target.closest('.lb-dist-key[data-band]');
      if (key) {
        var band = key.getAttribute('data-band');
        document.querySelectorAll('.lb-tab').forEach(function (x) {
          x.classList.toggle('is-active', x.getAttribute('data-band') === band);
        });
        state.activeBand = band;
        renderTable();
        return;
      }

      // Header sort click
      var th = e.target.closest('#lbTable thead th[data-col]');
      if (th) {
        var col = th.getAttribute('data-col');
        if (col === 'rank') return;
        if (state.sort.col === col) {
          state.sort.dir = state.sort.dir === 'asc' ? 'desc' : 'asc';
        } else {
          state.sort.col = col;
          state.sort.dir = (col === 'id' ? 'asc' : 'desc');
        }
        renderTable();
      }
    });
  });

  /* ── Helpers ───────────────────────────────────────────────── */
  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
})();

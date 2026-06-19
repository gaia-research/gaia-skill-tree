/*
 * /trust/leaderboard/leaderboard.js
 *
 * Renders the public Trust Magnitude leaderboard from
 * docs/graph/leaderboard/data.json. Search, filter chips, per-band
 * sortable tables, summary stats, footer ledger.
 *
 * Data shape — see scripts/generateLeaderboardData.py:
 *   { version, generatedAt, summary, rows: [
 *       { skillId, tm, grade, currentStars, g7Stars, flag, apexResults }
 *     ]
 *   }
 */
(function () {
  'use strict';

  var DATA_URL    = '../../graph/leaderboard/data.json';
  var SKILL_LINK  = '../../named/?s=';   // resolved relative to /trust/leaderboard/
  var GAIA_VER    = window.GAIA_VERSION || '';
  var STARS_ORDER = { '0★': 0, '1★': 1, '2★': 2, '3★': 3, '4★': 4, '5★': 5, '6★': 6 };
  var STARS_NAMES = {
    '0★': 'Unawakened', '1★': 'Awakened', '2★': 'Named', '3★': 'Evolved',
    '4★': 'Hardened',   '5★': 'Transcendent', '6★': 'Transcendent'
  };

  var BANDS = [
    { key: 'S',        label: 'S grade',  sub: 'TM ≥ 250',           seal: 'S' },
    { key: 'A',        label: 'A grade',  sub: 'TM ≥ 100',           seal: 'A' },
    { key: 'B',        label: 'B grade',  sub: 'TM ≥ 50',            seal: 'B' },
    { key: 'C',        label: 'C grade',  sub: 'TM ≥ 20',            seal: 'C' },
    { key: 'ungraded', label: 'Ungraded', sub: 'TM < 20',            seal: '·' }
  ];

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
    sort: {} // per band: { S: {col:'tm', dir:'desc'}, ... }
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

      // default sort per band: TM desc
      BANDS.forEach(function (b) { state.sort[b.key] = { col: 'tm', dir: 'desc' }; });

      renderStats();
      renderBands();
      renderGeneratedAt();
    })
    .catch(function (err) {
      console.error('[leaderboard] failed to load', err);
      var bands = document.getElementById('lbBands');
      if (bands) {
        bands.innerHTML =
          '<div class="lb-empty">Could not load leaderboard data. ' +
          '<a href="' + DATA_URL + '">Try the raw JSON →</a></div>';
      }
    });

  /* ── Stat cards ────────────────────────────────────────────── */
  function renderStats() {
    var el = document.getElementById('lbStats');
    if (!el || !state.summary) return;
    var s = state.summary;
    var cards = [
      { cls: 'total', num: s.total, label: 'total' },
      { cls: 's',     num: s.S,     label: 'S grade' },
      { cls: 'a',     num: s.A,     label: 'A grade' },
      { cls: 'b',     num: s.B,     label: 'B grade' },
      { cls: 'c',     num: s.C,     label: 'C grade' },
      { cls: 'u',     num: s.ungraded, label: 'ungraded' },
      { cls: 'floor', num: s.floor, label: 'rank-floor' },
      { cls: 'up',    num: s.up,    label: '[up] promotions' }
    ];
    el.innerHTML = cards.map(function (c) {
      return '<div class="lb-stat lb-stat--' + c.cls + '">' +
                '<span class="lb-stat__num">' + escapeHtml(String(c.num)) + '</span>' +
                '<span class="lb-stat__label">' + escapeHtml(c.label) + '</span>' +
             '</div>';
    }).join('');
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

  /* ── Bands ─────────────────────────────────────────────────── */
  function renderBands() {
    var container = document.getElementById('lbBands');
    if (!container) return;

    var q = state.query.trim().toLowerCase();
    var filtered = state.rows.filter(function (r) {
      if (state.activeBand !== 'all' && r.grade !== state.activeBand) return false;
      if (q && r.skillId.toLowerCase().indexOf(q) === -1) return false;
      return true;
    });

    var html = BANDS.map(function (band) {
      var bandRows = filtered.filter(function (r) { return r.grade === band.key; });
      if (state.activeBand !== 'all' && state.activeBand !== band.key) return '';
      if (bandRows.length === 0 && state.activeBand !== 'all') {
        // user explicitly chose this band — show empty state
        return renderBand(band, []);
      }
      if (bandRows.length === 0) return '';
      sortRowsInPlace(bandRows, state.sort[band.key]);
      return renderBand(band, bandRows);
    }).join('');

    if (!html.trim()) {
      html = '<div class="lb-empty">No skills match the current filter.</div>';
    }
    container.innerHTML = html;
    wireSortHandlers();
  }

  function renderBand(band, rows) {
    var classKey = band.key === 'ungraded' ? 'u' : band.key.toLowerCase();
    var sortState = state.sort[band.key] || { col: 'tm', dir: 'desc' };
    var isS = band.key === 'S';

    var headers = [
      { col: 'rank',  label: '#',         sortable: false },
      { col: 'id',    label: 'Skill ID',  sortable: true },
      { col: 'tm',    label: 'TM',        sortable: true,  align: 'right' },
      { col: 'grade', label: 'Grade',     sortable: true,  align: 'center' },
      { col: 'stars', label: 'Stars',     sortable: true,  align: 'center' },
      { col: 'g7',    label: 'G7 Stars',  sortable: true,  align: 'center' },
      { col: 'flag',  label: 'Flag',      sortable: true }
    ];
    if (isS) headers.push({ col: 'apex', label: 'Apex Gate', sortable: true });

    var theadCells = headers.map(function (h) {
      var sortable = h.sortable;
      var ariaSort = '';
      var arrow = '';
      if (sortable) {
        if (sortState.col === h.col) {
          ariaSort = ' aria-sort="' + (sortState.dir === 'asc' ? 'ascending' : 'descending') + '"';
          arrow = '<span class="lb-sort">' + (sortState.dir === 'asc' ? '▲' : '▼') + '</span>';
        } else {
          arrow = '<span class="lb-sort">↕</span>';
        }
      }
      return '<th data-band="' + escapeAttr(band.key) + '" data-col="' + escapeAttr(h.col) + '"' +
             (sortable ? '' : ' aria-disabled="true"') + ariaSort +
             ' class="col-' + escapeAttr(h.col) + '">' +
             escapeHtml(h.label) + (sortable ? arrow : '') +
             '</th>';
    }).join('');

    var bodyRows;
    if (rows.length === 0) {
      bodyRows = '<tr><td colspan="' + headers.length + '" class="lb-empty">No skills in this band match your search.</td></tr>';
    } else {
      bodyRows = rows.map(function (r, idx) { return renderRow(r, idx + 1, isS); }).join('');
    }

    return '' +
      '<section class="lb-band lb-band--' + classKey + '" id="band-' + escapeAttr(band.key) + '">' +
        '<div class="lb-band__header">' +
          '<span class="lb-band__seal" aria-hidden="true">' + escapeHtml(band.seal) + '</span>' +
          '<h2 class="lb-band__title">' + escapeHtml(band.label) + '</h2>' +
          '<span class="lb-band__count">' + rows.length + ' skill' + (rows.length === 1 ? '' : 's') + '</span>' +
          '<span class="lb-band__sub">' + escapeHtml(band.sub) + '</span>' +
        '</div>' +
        '<div class="lb-table-wrap">' +
          '<table class="lb-table">' +
            '<thead><tr>' + theadCells + '</tr></thead>' +
            '<tbody>' + bodyRows + '</tbody>' +
          '</table>' +
        '</div>' +
      '</section>';
  }

  function renderRow(r, rank, isS) {
    var skillId = r.skillId || '';
    var idLink = SKILL_LINK + encodeURIComponent(skillId);
    var stars = r.currentStars || '?';
    var starsCls = STARS_ORDER.hasOwnProperty(stars) ? ('lb-stars--' + STARS_ORDER[stars]) : '';
    var starsTitle = STARS_NAMES[stars] ? (stars + ' ' + STARS_NAMES[stars]) : stars;
    var g7 = r.g7Stars || '';
    var g7Cls = STARS_ORDER.hasOwnProperty(g7) ? ('lb-stars--' + STARS_ORDER[g7]) : '';

    var gradeKey = r.grade === 'ungraded' ? 'u' : (r.grade || '').toLowerCase();
    var gradeLabel = r.grade === 'ungraded' ? '—' : (r.grade || '—');

    var flagHtml = '';
    if (r.flag === '[floor]') flagHtml = '<span class="lb-flag lb-flag--floor">floor</span>';
    else if (r.flag === '[up]') flagHtml = '<span class="lb-flag lb-flag--up">up</span>';
    else flagHtml = '<span style="color:var(--border)">·</span>';

    var apexHtml = '';
    if (isS) {
      apexHtml = '<td class="col-apex">' + renderApex(r.apexResults) + '</td>';
    }

    return '' +
      '<tr>' +
        '<td class="col-num">' + rank + '</td>' +
        '<td class="col-id"><a href="' + escapeAttr(idLink) + '" title="' + escapeAttr(skillId) + '">' +
          escapeHtml(skillId) + '</a></td>' +
        '<td class="col-tm">' + (typeof r.tm === 'number' ? r.tm.toFixed(2) : escapeHtml(String(r.tm))) + '</td>' +
        '<td class="col-grade"><span class="lb-grade lb-grade--' + escapeAttr(gradeKey) + '">' + escapeHtml(gradeLabel) + '</span></td>' +
        '<td class="col-stars"><span class="lb-stars ' + starsCls + '" title="' + escapeAttr(starsTitle) + '">' + escapeHtml(stars) + '</span></td>' +
        '<td class="col-g7"><span class="lb-stars ' + g7Cls + '">' + escapeHtml(g7) + '</span></td>' +
        '<td class="col-flag">' + flagHtml + '</td>' +
        apexHtml +
      '</tr>';
  }

  function renderApex(apexResults) {
    if (!apexResults) return '<span class="lb-apex lb-apex--na">n/a</span>';
    var keys = Object.keys(apexResults);
    var active = keys.filter(function (k) { return apexResults[k] !== null; });
    var passed = active.filter(function (k) { return apexResults[k] === true; });
    var failed = active.filter(function (k) { return apexResults[k] === false; });
    var isApex = active.length > 0 && passed.length === active.length;

    var label = passed.length + '/' + active.length;
    var detail = '';
    if (failed.length) {
      var shortFails = failed.map(function (k) { return APEX_LABELS[k] || k; }).slice(0, 2);
      detail = ' <span class="lb-apex__detail">fail: ' + escapeHtml(shortFails.join(', ')) +
               (failed.length > 2 ? '…' : '') + '</span>';
    } else if (isApex) {
      detail = ' <span class="lb-apex__detail">apex</span>';
    }
    var cls = isApex ? 'lb-apex lb-apex--apex' : (failed.length ? 'lb-apex lb-apex__fail' : 'lb-apex lb-apex__pass');
    return '<span class="' + cls + '"><span class="lb-apex__count">' + label + '</span>' + detail + '</span>';
  }

  /* ── Sort ──────────────────────────────────────────────────── */
  function sortRowsInPlace(rows, ss) {
    var col = ss.col, dir = ss.dir === 'asc' ? 1 : -1;
    rows.sort(function (a, b) {
      var av, bv;
      switch (col) {
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
        case 'stars':
          av = STARS_ORDER[a.currentStars] != null ? STARS_ORDER[a.currentStars] : -1;
          bv = STARS_ORDER[b.currentStars] != null ? STARS_ORDER[b.currentStars] : -1;
          break;
        case 'g7':
          av = STARS_ORDER[a.g7Stars] != null ? STARS_ORDER[a.g7Stars] : -1;
          bv = STARS_ORDER[b.g7Stars] != null ? STARS_ORDER[b.g7Stars] : -1;
          break;
        case 'flag':
          av = flagOrder(a.flag); bv = flagOrder(b.flag);
          break;
        case 'apex':
          av = apexScore(a.apexResults); bv = apexScore(b.apexResults);
          break;
        default:
          av = 0; bv = 0;
      }
      if (av < bv) return -1 * dir;
      if (av > bv) return  1 * dir;
      // stable secondary by skillId
      var aid = (a.skillId || '').toLowerCase();
      var bid = (b.skillId || '').toLowerCase();
      return aid < bid ? -1 : aid > bid ? 1 : 0;
    });
  }

  function gradeOrder(g) {
    return { S: 4, A: 3, B: 2, C: 1, ungraded: 0 }[g] || 0;
  }
  function flagOrder(f) {
    if (f === '[up]')   return 2;
    if (f === '[floor]') return 1;
    return 0;
  }
  function apexScore(ar) {
    if (!ar) return -1;
    var keys = Object.keys(ar).filter(function (k) { return ar[k] !== null; });
    var passed = keys.filter(function (k) { return ar[k] === true; });
    if (keys.length === 0) return 0;
    return passed.length / keys.length;
  }

  function wireSortHandlers() {
    var ths = document.querySelectorAll('.lb-table thead th[data-col]');
    ths.forEach(function (th) {
      var col = th.getAttribute('data-col');
      var band = th.getAttribute('data-band');
      if (col === 'rank') return;
      th.addEventListener('click', function () {
        var ss = state.sort[band] || { col: 'tm', dir: 'desc' };
        if (ss.col === col) {
          ss.dir = ss.dir === 'asc' ? 'desc' : 'asc';
        } else {
          ss.col = col;
          ss.dir = (col === 'id' ? 'asc' : 'desc');
        }
        state.sort[band] = ss;
        renderBands();
      });
    });
  }

  /* ── Search + chips ────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    var search = document.getElementById('lbSearch');
    if (search) {
      var debounce;
      search.addEventListener('input', function (e) {
        clearTimeout(debounce);
        debounce = setTimeout(function () {
          state.query = e.target.value || '';
          renderBands();
        }, 80);
      });
    }
    var chips = document.querySelectorAll('.lb-chip');
    chips.forEach(function (c) {
      c.addEventListener('click', function () {
        chips.forEach(function (x) { x.classList.remove('is-active'); });
        c.classList.add('is-active');
        state.activeBand = c.getAttribute('data-band') || 'all';
        renderBands();
      });
    });
  });

  /* ── Helpers ───────────────────────────────────────────────── */
  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
  function escapeAttr(s) { return escapeHtml(s); }
})();

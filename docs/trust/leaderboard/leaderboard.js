(function () {
  'use strict';

  var BASE = '../../api/v1/';
  var VER = window.GAIA_VERSION ? '?v=' + window.GAIA_VERSION : '';
  var SUITE_IDS = ['garrytan/gstack', 'ruvnet/ruflo', 'mattpocock/skills', 'obra/superpowers'];
  var FALLBACK_COUNTS = { 'garrytan/gstack': 43, 'ruvnet/ruflo': 20, 'mattpocock/skills': 34, 'obra/superpowers': 12 };
  var TM_CEILING = 600;
  var UNREG_INITIAL_GROUPS = 3;
  var state = { sort: 'tm', grade: 'all', trendingAvailable: false };

  // ── FETCH ──
  Promise.all([
    fetch(BASE + 'leaderboard.json' + VER).then(function(r){ return r.json(); }),
    fetch(BASE + 'skills/index.json' + VER).then(function(r){ return r.json(); }),
    fetch(BASE + 'skills/page-2.json' + VER).then(function(r){ return r.json(); }),
    fetch(BASE + 'skills/page-3.json' + VER).then(function(r){ return r.json(); }),
    fetch(BASE + 'trending/7d.json' + VER).then(function(r){ return r.json(); }).catch(function(){ return null; })
  ]).then(function(results) {
    init(results[0], results[1], results[2], results[3], results[4]);
  }).catch(function(err) {
    document.querySelector('.lb-main').innerHTML = '<p style="padding:3rem;color:var(--muted)">Failed to load leaderboard data.</p>';
    console.error('[leaderboard]', err);
  });

  function init(leaderboard, p1, p2, p3, trending) {
    // Build skill map from all pages
    var skillMap = {};
    [p1, p2, p3].forEach(function(page) {
      if (!page || !page.skills) return;
      page.skills.forEach(function(s) { skillMap[s.id] = s; });
    });

    // Trending map
    var trendMap = {};
    if (trending && trending.skills) {
      state.trendingAvailable = true;
      trending.skills.forEach(function(s) { trendMap[s.id] = s.tmDelta; });
    }

    // Enrich leaderboard rows with skill info
    var allRows = leaderboard.rows.map(function(row) {
      var skill = skillMap[row.id] || {};
      return {
        id: row.id,
        name: skill.name || row.id.split('/')[1],
        contributor: row.id.split('/')[0],
        type: skill.type || 'basic',
        level: row.level || skill.level || '',
        trustMagnitude: row.trustMagnitude,
        grade: row.grade || skill.overallTrustGrade || 'ungraded',
        tmDelta: trendMap[row.id] !== undefined ? trendMap[row.id] : null
      };
    });

    // Partition into lanes
    var suites = allRows.filter(function(r) { return r.type === 'ultimate'; });
    var named = allRows.filter(function(r) { return r.type !== 'ultimate' && r.grade && r.grade !== 'ungraded'; });
    var ungraded = allRows.filter(function(r) { return !r.grade || r.grade === 'ungraded'; });

    // Render
    renderHeader(leaderboard.distribution);
    renderSuites(suites);
    renderNamed(named);
    renderUngraded(ungraded);
    wireControls(named);

    // Defer suite detail fetch
    fetchSuiteDetails(suites);

    // Animate bars after brief delay
    setTimeout(animateBars, 50);
  }

  // ── HEADER ──
  function renderHeader(dist) {
    var total = dist.total || 0;
    var count = document.getElementById('lbCount');
    if (count) count.textContent = total;

    var pillsEl = document.getElementById('lbPills');
    if (!pillsEl) return;
    var grades = [
      { g: 'S', label: 'S', count: dist.S || 0 },
      { g: 'A', label: 'A', count: dist.A || 0 },
      { g: 'B', label: 'B', count: dist.B || 0 },
      { g: 'C', label: 'C', count: dist.C || 0 },
      { g: 'ungraded', label: '—', count: dist.ungraded || 0 }
    ];
    pillsEl.innerHTML = grades.map(function(item) {
      return '<span class="lb-pill"><span class="lb-pill__grade lb-pill__grade--' + item.g + '">' + item.label + '</span><span class="lb-pill__count">' + item.count + '</span></span>';
    }).join('');
  }

  // ── SUITES ──
  function renderSuites(suites) {
    var el = document.getElementById('lbSuiteCards');
    if (!el) return;
    el.innerHTML = suites.map(function(s, i) {
      var pct = (s.trustMagnitude / TM_CEILING * 100).toFixed(2);
      return '<article class="lb-suite" data-id="' + s.id + '">' +
        '<div class="lb-suite__header">' +
          '<span class="lb-suite__rank">#' + (i + 1) + '</span>' +
          '<div class="lb-suite__meta">' +
            '<div class="lb-suite__name">' + escHtml(s.name) + '</div>' +
            '<span class="lb-suite__contributor">' + escHtml(s.id) + '</span>' +
            '<span class="lb-suite__badge" id="badge-' + safeId(s.id) + '">S · ' + escHtml(s.level) + ' · ' + (FALLBACK_COUNTS[s.id] || '?') + ' skills</span>' +
          '</div>' +
          '<span class="lb-suite__tm">' + s.trustMagnitude.toFixed(2) + '</span>' +
        '</div>' +
        '<div class="lb-suite__bar-track"><div class="lb-suite__bar" data-pct="' + pct + '" style="width:0"></div></div>' +
        '<p class="lb-suite__desc" id="desc-' + safeId(s.id) + '">Loading…</p>' +
      '</article>';
    }).join('');
  }

  function fetchSuiteDetails(suites) {
    suites.forEach(function(s) {
      var parts = s.id.split('/');
      fetch(BASE + 'skills/' + parts[0] + '/' + parts[1] + '.json' + VER)
        .then(function(r) { return r.json(); })
        .then(function(detail) {
          var descEl = document.getElementById('desc-' + safeId(s.id));
          if (descEl) descEl.textContent = detail.description || detail.title || '—';
          var badgeEl = document.getElementById('badge-' + safeId(s.id));
          if (badgeEl) {
            var compCount = detail.suiteComponents ? detail.suiteComponents.length : (FALLBACK_COUNTS[s.id] || '?');
            badgeEl.textContent = 'S · ' + (s.level || '') + ' · ' + compCount + ' skills';
          }
        })
        .catch(function() {
          var descEl = document.getElementById('desc-' + safeId(s.id));
          if (descEl) descEl.textContent = '—';
        });
    });
  }

  // ── NAMED SKILLS ──
  function renderNamed(named) {
    var el = document.getElementById('lbNamedList');
    if (!el) return;
    var maxTm = named.reduce(function(m, r) { return Math.max(m, r.trustMagnitude || 0); }, 1);
    var html = named.map(function(s, i) {
      var pct = ((s.trustMagnitude || 0) / maxTm * 100).toFixed(2);
      var trendHtml = renderTrend(s.tmDelta);
      var parts = s.id.split('/');
      var displayId = '<span class="lb-row__contributor">' + escHtml(parts[0]) + '</span>/' + escHtml(parts[1] || '');
      return '<div class="lb-row" data-grade="' + s.grade + '" data-tm="' + (s.trustMagnitude || 0) + '" data-delta="' + (s.tmDelta || 0) + '">' +
        '<span class="lb-row__rank">' + (i + 1) + '</span>' +
        '<a class="lb-row__id" href="../../named/#explorer/' + escHtml(s.id) + '" title="' + escHtml(s.name) + '">' + displayId + '</a>' +
        '<div class="lb-row__bar-cell">' +
          '<div class="lb-row__bar-track"><div class="lb-row__bar-fill lb-row__bar-fill--' + s.grade + '" data-pct="' + pct + '" style="width:0"></div></div>' +
          '<span class="lb-row__tm-val">' + (s.trustMagnitude || 0).toFixed(1) + '</span>' +
        '</div>' +
        '<span class="lb-row__grade lb-row__grade--' + s.grade + '">' + s.grade + '</span>' +
        '<span class="lb-row__stars">' + escHtml(s.level || '') + '</span>' +
        trendHtml +
      '</div>';
    }).join('');
    el.innerHTML = html;
  }

  function renderTrend(delta) {
    if (delta === null || delta === undefined) {
      return '<span class="lb-row__trend lb-row__trend--none">—</span>';
    }
    if (delta > 0) {
      return '<span class="lb-row__trend lb-row__trend--up">+' + delta.toFixed(1) + '</span>';
    }
    if (delta < 0) {
      return '<span class="lb-row__trend lb-row__trend--down">' + delta.toFixed(1) + '</span>';
    }
    return '<span class="lb-row__trend lb-row__trend--none">—</span>';
  }

  // ── UNGRADED ──
  function renderUngraded(ungraded) {
    var el = document.getElementById('lbUnregList');
    if (!el) return;

    // Group by contributor
    var groups = {};
    ungraded.forEach(function(s) {
      var c = s.contributor;
      if (!groups[c]) groups[c] = [];
      groups[c].push(s);
    });

    var handles = Object.keys(groups).sort();
    var allHtml = handles.map(function(handle, idx) {
      var hidden = idx >= UNREG_INITIAL_GROUPS ? ' data-overflow="true" style="display:none"' : '';
      var items = groups[handle].map(function(s) {
        return '<li class="lb-unreg-item">' + escHtml(s.name || s.id.split('/')[1]) + '</li>';
      }).join('');
      return '<div class="lb-unreg-group"' + hidden + '>' +
        '<span class="lb-unreg-handle">' + escHtml(handle) + '</span>' +
        '<ul class="lb-unreg-list">' + items + '</ul>' +
      '</div>';
    }).join('');
    el.innerHTML = allHtml;

    // Toggle button
    var toggle = document.getElementById('lbUnregToggle');
    var overflowCount = handles.length - UNREG_INITIAL_GROUPS;
    if (toggle) {
      if (overflowCount <= 0) {
        toggle.style.display = 'none';
      } else {
        toggle.textContent = 'Show all ' + handles.length + ' contributors →';
        toggle.addEventListener('click', function() {
          el.querySelectorAll('[data-overflow="true"]').forEach(function(g) { g.style.display = ''; });
          toggle.style.display = 'none';
        });
      }
    }
  }

  // ── CONTROLS ──
  function wireControls(named) {
    // Disable trending sort if no data
    if (!state.trendingAvailable) {
      var trendBtn = document.getElementById('lbSortTrending');
      if (trendBtn) {
        trendBtn.disabled = true;
        trendBtn.title = 'Trending data not yet available';
      }
    }

    // Sort buttons
    document.querySelectorAll('.lb-sort-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        if (btn.disabled) return;
        state.sort = btn.dataset.sort;
        document.querySelectorAll('.lb-sort-btn').forEach(function(b) { b.classList.remove('is-active'); });
        btn.classList.add('is-active');
        applySortFilter(named);
      });
    });

    // Filter buttons
    document.querySelectorAll('.lb-filter-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        state.grade = btn.dataset.grade;
        document.querySelectorAll('.lb-filter-btn').forEach(function(b) { b.classList.remove('is-active'); });
        btn.classList.add('is-active');
        applySortFilter(named);
      });
    });
  }

  function applySortFilter(named) {
    // Filter: show/hide rows
    var listEl = document.getElementById('lbNamedList');
    if (!listEl) return;
    var rows = listEl.querySelectorAll('.lb-row');
    rows.forEach(function(row) {
      var grade = row.dataset.grade;
      var show = (state.grade === 'all' || grade === state.grade);
      row.hidden = !show;
    });

    // Show/hide suites lane on grade filter
    var suitesLane = document.getElementById('lbSuites');
    if (suitesLane) {
      suitesLane.style.display = (state.grade === 'all' || state.grade === 'S') ? '' : 'none';
    }

    // Sort visible rows
    var visibleRows = Array.from(rows).filter(function(r) { return !r.hidden; });
    visibleRows.sort(function(a, b) {
      if (state.sort === 'tm') {
        return parseFloat(b.dataset.tm) - parseFloat(a.dataset.tm);
      }
      if (state.sort === 'trending') {
        return parseFloat(b.dataset.delta || 0) - parseFloat(a.dataset.delta || 0);
      }
      if (state.sort === 'grade') {
        var order = { S: 0, A: 1, B: 2, C: 3 };
        var diff = (order[a.dataset.grade] || 9) - (order[b.dataset.grade] || 9);
        if (diff !== 0) return diff;
        return parseFloat(b.dataset.tm) - parseFloat(a.dataset.tm);
      }
      return 0;
    });

    // Re-insert sorted rows and update rank numbers
    visibleRows.forEach(function(row, i) {
      listEl.appendChild(row);
      var rankEl = row.querySelector('.lb-row__rank');
      if (rankEl) rankEl.textContent = (i + 1);
    });
  }

  // ── BAR ANIMATION ──
  function animateBars() {
    document.querySelectorAll('[data-pct]').forEach(function(el) {
      el.style.width = el.dataset.pct + '%';
    });
  }

  // ── UTILS ──
  function escHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function safeId(str) {
    return str.replace(/[^a-z0-9]/gi, '-');
  }

})();

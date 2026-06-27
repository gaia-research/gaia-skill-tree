(function() {
  'use strict';

  // ── CONFIGURATION ──
  var BASE = '../../api/v1/';
  var VER = window.GAIA_VERSION ? '?v=' + window.GAIA_VERSION : '';
  var BAR_W = 28;
  var BAR_GAP = 4;
  var CHART_H = 320;
  var SUITE_CHART_H = 380;
  var PAD = { top: 24, right: 24, bottom: 90, left: 54 };
  var INITIAL_BARS = 40;
  var TM_CEILING = 600;
  var SVG_NS = 'http://www.w3.org/2000/svg';

  var GRADE_ORDER = { S: 0, A: 1, B: 2, C: 3, ungraded: 9 };
  var RANK_NAMES = {
    '1★': 'Awakened', '2★': 'Named', '3★': 'Evolved',
    '4★': 'Hardened', '5★': 'Transcendent', '6★': 'Apex'
  };

  // ── CSS TOKEN READER ──
  var cs = getComputedStyle(document.documentElement);
  function tok(name) { return cs.getPropertyValue(name).trim(); }

  var TOKENS = {
    platinum: tok('--evidence-platinum-rgb'),
    gold: tok('--evidence-gold-rgb'),
    silver: tok('--evidence-silver-rgb'),
    bronze: tok('--evidence-bronze-rgb'),
    rank1: tok('--rank-1-rgb') || '56, 189, 248',
    rank2: tok('--rank-2-rgb') || '99, 202, 183',
    rank3: tok('--rank-3-rgb') || '167, 139, 250',
    rank4: tok('--rank-4-rgb') || '232, 121, 249',
    rank5: tok('--rank-5-rgb') || '251, 191, 36',
    rank6: tok('--rank-6-rgb') || '251, 191, 36',
    honorRed: tok('--honor-red-rgb') || '239, 68, 68',
    basic: tok('--tier-basic-rgb') || '56, 189, 248',
    muted: tok('--muted') || 'rgb(100, 116, 139)',
    text: tok('--text') || 'rgb(226, 232, 240)',
    border: tok('--border') || 'rgb(30, 41, 59)'
  };

  // Fallback for --rank-N-rgb (not all tokens.css emit them)
  function rankRgb(level) {
    var n = parseInt(level) || 0;
    var map = {
      0: '148, 163, 184', 1: '56, 189, 248', 2: '99, 202, 183',
      3: '167, 139, 250', 4: '232, 121, 249', 5: '251, 191, 36', 6: '251, 191, 36'
    };
    return map[n] || map[0];
  }

  function gradeColor(grade) {
    switch (grade) {
      case 'S': return TOKENS.platinum;
      case 'A': return TOKENS.gold;
      case 'B': return TOKENS.silver;
      case 'C': return TOKENS.bronze;
      default: return '148, 163, 184';
    }
  }

  // ── STATE ──
  var state = {
    sort: 'tm',
    grade: 'all',
    namedSkills: [],
    suiteSkills: [],
    allSkills: [],
    showCount: INITIAL_BARS
  };

  // ── DATA FETCH (parallel) ──
  Promise.all([
    fetch(BASE + 'leaderboard.json' + VER).then(function(r) { return r.json(); }),
    fetch(BASE + 'skills/index.json' + VER).then(function(r) { return r.json(); }),
    fetch(BASE + 'skills/page-2.json' + VER).then(function(r) { return r.json(); }),
    fetch(BASE + 'skills/page-3.json' + VER).then(function(r) { return r.json(); })
  ]).then(function(results) {
    boot(results[0], results[1], results[2], results[3]);
  }).catch(function(err) {
    var page = document.querySelector('.lb-page');
    if (page) page.innerHTML = '<p style="padding:4rem 2rem;color:var(--muted);font-family:var(--font-body)">Failed to load leaderboard data.</p>';
    console.error('[leaderboard]', err);
  });

  function boot(leaderboard, p1, p2, p3) {
    // Build skill map
    var skillMap = {};
    [p1, p2, p3].forEach(function(page) {
      if (!page || !page.skills) return;
      page.skills.forEach(function(s) { skillMap[s.id] = s; });
    });

    // Enrich leaderboard rows
    var allRows = leaderboard.rows.map(function(row) {
      var skill = skillMap[row.id] || {};
      return {
        id: row.id,
        name: skill.name || row.id.split('/')[1],
        contributor: row.id.split('/')[0],
        type: skill.type || 'basic',
        level: row.level || skill.level || '',
        trustMagnitude: row.trustMagnitude || 0,
        grade: row.grade || skill.overallTrustGrade || 'ungraded'
      };
    });

    // Partition
    var suites = allRows.filter(function(r) { return r.type === 'ultimate'; });
    var named = allRows.filter(function(r) { return r.type !== 'ultimate' && r.grade && r.grade !== 'ungraded'; });
    var ungraded = allRows.filter(function(r) { return !r.grade || r.grade === 'ungraded'; });
    state.namedSkills = named;
    state.suiteSkills = suites;
    state.allSkills = allRows;

    // Render
    renderDistribution(leaderboard.distribution);
    renderSuiteChart(suites);
    renderNamedChart(named);
    renderRegistry(ungraded);
    wireFilters(named);
    wireShowMore();
    wireTooltip();

    // Fetch suite component details for stacked bars
    fetchSuiteComponents(suites);
  }

  // ── DISTRIBUTION HEADER ──
  function renderDistribution(dist) {
    var el = document.getElementById('lbDist');
    if (!el) return;
    var items = [
      { label: 'Total', grade: 'total', count: dist.total || 0 },
      { label: 'S', grade: 'S', count: dist.S || 0 },
      { label: 'A', grade: 'A', count: dist.A || 0 },
      { label: 'B', grade: 'B', count: dist.B || 0 },
      { label: 'C', grade: 'C', count: dist.C || 0 },
      { label: 'Ungraded', grade: 'ungraded', count: dist.ungraded || 0 }
    ];
    el.innerHTML = items.map(function(item) {
      return '<span class="lb-dist-item">' +
        '<span class="lb-dist-grade lb-dist-grade--' + item.grade + '">' + item.label + '</span>' +
        '<span class="lb-dist-num">' + item.count + '</span>' +
      '</span>';
    }).join('');
  }

  // ── SUITE STACKED BAR CHART ──
  function renderSuiteChart(suites) {
    var container = document.getElementById('lbSuiteChart');
    var countEl = document.getElementById('lbSuiteCount');
    if (!container) return;
    if (countEl) countEl.textContent = suites.length + ' suites';

    var maxTM = TM_CEILING;
    var totalW = suites.length * (BAR_W * 2 + BAR_GAP) + PAD.left + PAD.right + 80;
    var chartH = SUITE_CHART_H;
    var innerH = chartH - PAD.top - PAD.bottom;

    var svg = createSvg(Math.max(totalW, 320), chartH);

    // Platinum gradient for S-grade suites
    var defs = svgEl('defs');
    var grad = svgEl('linearGradient', { id: 'lb-grad-platinum', x1: '0', y1: '1', x2: '0', y2: '0' });
    appendStop(grad, '0%', 'rgba(' + TOKENS.platinum + ', 0.4)');
    appendStop(grad, '50%', 'rgba(' + TOKENS.platinum + ', 0.7)');
    appendStop(grad, '100%', 'rgba(' + TOKENS.platinum + ', 0.95)');
    defs.appendChild(grad);
    svg.appendChild(defs);

    // Y-axis gridlines
    drawYAxis(svg, innerH, maxTM, totalW);

    // Bars
    var barGroup = svgEl('g', { transform: 'translate(' + PAD.left + ',' + PAD.top + ')' });
    var barSpacing = BAR_W * 2 + BAR_GAP + 40;

    suites.forEach(function(suite, i) {
      var x = i * barSpacing + 20;
      var h = (suite.trustMagnitude / maxTM) * innerH;
      var y = innerH - h;

      var bar = svgEl('rect', {
        x: x,
        y: y,
        width: BAR_W * 2,
        height: h,
        rx: 4,
        fill: 'url(#lb-grad-platinum)',
        'class': 'lb-bar lb-bar-animated',
        'data-id': suite.id,
        'data-type': 'suite',
        style: 'animation-delay:' + (i * 120) + 'ms'
      });
      barGroup.appendChild(bar);

      // TM value above bar
      var tmText = svgEl('text', {
        x: x + BAR_W,
        y: y - 8,
        'text-anchor': 'middle',
        'class': 'lb-axis-value',
        'font-size': '11',
        fill: 'rgba(' + TOKENS.platinum + ', 0.9)'
      });
      tmText.textContent = suite.trustMagnitude.toFixed(0);
      barGroup.appendChild(tmText);

      // Label below
      var label = svgEl('text', {
        x: x + BAR_W,
        y: innerH + 18,
        'text-anchor': 'middle',
        'class': 'lb-axis-label',
        'font-size': '11'
      });
      label.textContent = truncate(suite.name || suite.id.split('/')[1], 14);
      barGroup.appendChild(label);

      // Contributor under label
      var contrib = svgEl('text', {
        x: x + BAR_W,
        y: innerH + 34,
        'text-anchor': 'middle',
        'font-size': '10',
        fill: 'rgba(' + TOKENS.honorRed + ', 0.7)'
      });
      contrib.textContent = suite.contributor;
      barGroup.appendChild(contrib);
    });

    svg.appendChild(barGroup);
    container.innerHTML = '';
    container.appendChild(svg);
  }

  function fetchSuiteComponents(suites) {
    suites.forEach(function(suite) {
      var parts = suite.id.split('/');
      fetch(BASE + 'skills/' + parts[0] + '/' + parts[1] + '.json' + VER)
        .then(function(r) { return r.json(); })
        .then(function(detail) {
          if (detail.suiteComponents && detail.suiteComponents.length > 0) {
            renderStackedOverlay(suite, detail.suiteComponents.length);
          }
        }).catch(function() { /* silent */ });
    });
  }

  function renderStackedOverlay(suite, componentCount) {
    // Overlay stacked segments on the existing bar
    var bar = document.querySelector('.lb-bar[data-id="' + suite.id + '"]');
    if (!bar) return;

    var svg = bar.closest('svg');
    if (!svg) return;

    var x = parseFloat(bar.getAttribute('x'));
    var y = parseFloat(bar.getAttribute('y'));
    var h = parseFloat(bar.getAttribute('height'));
    var w = parseFloat(bar.getAttribute('width'));

    // Estimate rank distribution for visual segmentation
    // Use a rough distribution curve: more 2-3★ components than 4-5★
    var segments = estimateRankDistribution(componentCount);
    var totalParts = segments.reduce(function(a, b) { return a + b.count; }, 0);
    var currentY = y + h; // start from bottom

    segments.forEach(function(seg) {
      if (seg.count <= 0) return;
      var segH = (seg.count / totalParts) * h;
      currentY -= segH;

      var rect = svgEl('rect', {
        x: x + 1,
        y: currentY,
        width: w - 2,
        height: segH - 1,
        rx: 2,
        fill: 'rgba(' + rankRgb(seg.rank) + ', 0.6)',
        'class': 'lb-bar',
        'data-id': suite.id,
        'data-type': 'suite',
        style: 'pointer-events: none;'
      });
      bar.parentNode.insertBefore(rect, bar.nextSibling);
    });

    // Make the original bar transparent so stack shows through
    bar.setAttribute('fill', 'rgba(' + TOKENS.platinum + ', 0.08)');
    bar.setAttribute('stroke', 'rgba(' + TOKENS.platinum + ', 0.3)');
    bar.setAttribute('stroke-width', '1');
  }

  function estimateRankDistribution(count) {
    // Estimate: 5★ = 10%, 4★ = 20%, 3★ = 30%, 2★ = 40%
    var r5 = Math.max(1, Math.round(count * 0.1));
    var r4 = Math.max(1, Math.round(count * 0.2));
    var r3 = Math.max(2, Math.round(count * 0.3));
    var r2 = Math.max(1, count - r5 - r4 - r3);
    return [
      { rank: 2, count: r2 },
      { rank: 3, count: r3 },
      { rank: 4, count: r4 },
      { rank: 5, count: r5 }
    ];
  }

  // ── NAMED SKILLS BAR CHART ──
  function renderNamedChart(skills) {
    var container = document.getElementById('lbNamedChart');
    var countEl = document.getElementById('lbNamedCount');
    if (!container) return;

    var visible = applyFilter(skills);
    var toShow = visible.slice(0, state.showCount);
    var totalVisible = visible.length;

    if (countEl) {
      countEl.textContent = '(showing ' + toShow.length + ' of ' + totalVisible + ')';
    }

    updateShowMoreBtn(toShow.length, totalVisible);

    if (toShow.length === 0) {
      container.innerHTML = '<p style="padding:2rem;color:var(--muted);font-family:var(--font-body);font-size:0.85rem">No skills match current filter.</p>';
      return;
    }

    var maxTM = Math.max.apply(null, toShow.map(function(s) { return s.trustMagnitude; }));
    maxTM = Math.max(maxTM, 50); // floor

    var totalW = toShow.length * (BAR_W + BAR_GAP) + PAD.left + PAD.right;
    var innerH = CHART_H - PAD.top - PAD.bottom;

    var svg = createSvg(Math.max(totalW, 320), CHART_H + PAD.bottom);

    // Y-axis gridlines
    drawYAxis(svg, innerH, maxTM, totalW);

    // Bar group
    var barGroup = svgEl('g', { transform: 'translate(' + PAD.left + ',' + PAD.top + ')' });

    toShow.forEach(function(skill, i) {
      var x = i * (BAR_W + BAR_GAP);
      var h = Math.max(2, (skill.trustMagnitude / maxTM) * innerH);
      var y = innerH - h;
      var color = gradeColor(skill.grade);

      var bar = svgEl('rect', {
        x: x,
        y: y,
        width: BAR_W,
        height: h,
        rx: 3,
        fill: 'rgba(' + color + ', 0.75)',
        'class': 'lb-bar lb-bar-animated',
        'data-id': skill.id,
        'data-type': 'named',
        style: 'animation-delay:' + (i * 30) + 'ms'
      });
      barGroup.appendChild(bar);

      // X-axis label (rotated 45°)
      var label = svgEl('text', {
        x: 0,
        y: 0,
        transform: 'translate(' + (x + BAR_W / 2) + ',' + (innerH + 12) + ') rotate(45)',
        'text-anchor': 'start',
        'class': 'lb-axis-label',
        'font-size': '10'
      });
      label.textContent = truncate(skill.id.split('/')[1] || skill.name, 16);
      barGroup.appendChild(label);
    });

    svg.appendChild(barGroup);
    container.innerHTML = '';
    container.appendChild(svg);
  }

  // ── REGISTRY COMPACT LIST ──
  function renderRegistry(ungraded) {
    var container = document.getElementById('lbRegistryGrid');
    var countEl = document.getElementById('lbRegCount');
    var expandBtn = document.getElementById('lbRegExpand');
    if (!container) return;

    // Group by contributor
    var groups = {};
    ungraded.forEach(function(s) {
      var c = s.contributor;
      if (!groups[c]) groups[c] = [];
      groups[c].push(s);
    });

    var handles = Object.keys(groups).sort();
    if (countEl) countEl.textContent = handles.length + ' contributors · ' + ungraded.length + ' skills';

    var INITIAL = 12;
    var html = handles.map(function(handle, i) {
      var hidden = i >= INITIAL ? ' style="display:none" data-overflow="1"' : '';
      return '<div class="lb-reg-card"' + hidden + '>' +
        '<span class="lb-reg-handle">' + esc(handle) + '</span>' +
        '<span class="lb-reg-count">' + groups[handle].length + '</span>' +
      '</div>';
    }).join('');

    container.innerHTML = html;

    if (expandBtn) {
      if (handles.length <= INITIAL) {
        expandBtn.style.display = 'none';
      } else {
        expandBtn.textContent = 'Show all ' + handles.length + ' contributors';
        expandBtn.addEventListener('click', function() {
          container.querySelectorAll('[data-overflow]').forEach(function(el) {
            el.style.display = '';
          });
          expandBtn.style.display = 'none';
        });
      }
    }
  }

  // ── FILTER / SORT CONTROLS ──
  function wireFilters() {
    // Grade filter
    document.querySelectorAll('[data-grade]').forEach(function(btn) {
      btn.addEventListener('click', function() {
        state.grade = btn.dataset.grade;
        state.showCount = INITIAL_BARS;
        btn.parentNode.querySelectorAll('.lb-pill-btn').forEach(function(b) {
          b.classList.remove('is-active');
        });
        btn.classList.add('is-active');
        renderNamedChart(state.namedSkills);
      });
    });

    // Sort
    document.querySelectorAll('[data-sort]').forEach(function(btn) {
      btn.addEventListener('click', function() {
        state.sort = btn.dataset.sort;
        state.showCount = INITIAL_BARS;
        btn.parentNode.querySelectorAll('.lb-pill-btn').forEach(function(b) {
          b.classList.remove('is-active');
        });
        btn.classList.add('is-active');
        renderNamedChart(state.namedSkills);
      });
    });
  }

  function wireShowMore() {
    var btn = document.getElementById('lbShowMoreBtn');
    if (!btn) return;
    btn.addEventListener('click', function() {
      state.showCount += INITIAL_BARS;
      renderNamedChart(state.namedSkills);
    });
  }

  function applyFilter(skills) {
    var filtered = skills;
    if (state.grade !== 'all') {
      filtered = skills.filter(function(s) { return s.grade === state.grade; });
    }

    // Sort
    filtered = filtered.slice().sort(function(a, b) {
      if (state.sort === 'grade') {
        var diff = (GRADE_ORDER[a.grade] || 9) - (GRADE_ORDER[b.grade] || 9);
        if (diff !== 0) return diff;
      }
      return b.trustMagnitude - a.trustMagnitude;
    });

    return filtered;
  }

  function updateShowMoreBtn(shown, total) {
    var wrap = document.getElementById('lbShowMore');
    var btn = document.getElementById('lbShowMoreBtn');
    if (!wrap || !btn) return;
    if (shown >= total) {
      wrap.style.display = 'none';
    } else {
      wrap.style.display = '';
      btn.textContent = 'Show more (' + (total - shown) + ' remaining)';
    }
  }

  // ── TOOLTIP ──
  function wireTooltip() {
    var tooltip = document.getElementById('lbTooltip');
    if (!tooltip) return;

    // Track mouse for tooltip positioning
    document.addEventListener('mousemove', function(e) {
      if (tooltip.hidden) return;
      var x = e.clientX + 14;
      var y = e.clientY - 8;
      // Keep tooltip in viewport
      var tw = 260;
      if (x + tw > window.innerWidth) x = e.clientX - tw - 14;
      if (y + 200 > window.innerHeight) y = e.clientY - 200;
      tooltip.style.left = x + 'px';
      tooltip.style.top = y + 'px';
    });

    // Delegate events on SVG bars
    document.addEventListener('mouseenter', function(e) {
      var bar = e.target.closest && e.target.closest('.lb-bar');
      if (!bar || bar.style.pointerEvents === 'none') return;
      var id = bar.dataset.id;
      var type = bar.dataset.type;
      if (!id) return;

      var skill = findSkill(id);
      if (!skill) return;

      tooltip.innerHTML = buildTooltipHtml(skill, type);
      tooltip.hidden = false;
      tooltip.style.borderColor = 'rgba(' + gradeColor(skill.grade) + ', 0.5)';
    }, true);

    document.addEventListener('mouseleave', function(e) {
      var bar = e.target.closest && e.target.closest('.lb-bar');
      if (!bar) return;
      tooltip.hidden = true;
    }, true);

    // Click bar → navigate to explorer
    document.addEventListener('click', function(e) {
      var bar = e.target.closest && e.target.closest('.lb-bar');
      if (!bar || bar.style.pointerEvents === 'none') return;
      var id = bar.dataset.id;
      if (id) {
        window.location.href = '../../named/#explorer/' + id;
      }
    });

    // Touch: show tooltip on first tap, navigate on second
    var lastTappedId = null;
    document.addEventListener('touchstart', function(e) {
      var bar = e.target.closest && e.target.closest('.lb-bar');
      if (!bar || bar.style.pointerEvents === 'none') {
        tooltip.hidden = true;
        lastTappedId = null;
        return;
      }
      var id = bar.dataset.id;
      if (!id) return;
      e.preventDefault();

      if (lastTappedId === id) {
        // Second tap: navigate
        window.location.href = '../../named/#explorer/' + id;
        return;
      }

      lastTappedId = id;
      var skill = findSkill(id);
      if (!skill) return;
      tooltip.innerHTML = buildTooltipHtml(skill, bar.dataset.type);
      tooltip.hidden = false;
      tooltip.style.borderColor = 'rgba(' + gradeColor(skill.grade) + ', 0.5)';
      var touch = e.touches[0];
      tooltip.style.left = Math.min(touch.clientX + 14, window.innerWidth - 280) + 'px';
      tooltip.style.top = (touch.clientY - 120) + 'px';
    }, { passive: false });
  }

  function findSkill(id) {
    // Search all skills (includes suites and named)
    var all = state.allSkills;
    for (var i = 0; i < all.length; i++) {
      if (all[i].id === id) return all[i];
    }
    return null;
  }

  function buildTooltipHtml(skill, type) {
    var gradeLabel = skill.grade === 'S' ? 'Platinum' : skill.grade === 'A' ? 'Gold' : skill.grade === 'B' ? 'Silver' : skill.grade === 'C' ? 'Bronze' : 'Ungraded';
    var levelName = RANK_NAMES[skill.level] || '';

    return '<div class="lb-tt-name">' + esc(skill.name || skill.id.split('/')[1]) + '</div>' +
      '<div class="lb-tt-id">' + esc(skill.id) + '</div>' +
      '<div class="lb-tt-divider"></div>' +
      '<div class="lb-tt-row"><span class="lb-tt-label">Trust Magnitude</span><span class="lb-tt-value">' + (skill.trustMagnitude || 0).toFixed(2) + '</span></div>' +
      '<div class="lb-tt-row"><span class="lb-tt-label">Grade</span><span class="lb-tt-value">' + gradeLabel + ' (' + skill.grade + ')</span></div>' +
      '<div class="lb-tt-row"><span class="lb-tt-label">Level</span><span class="lb-tt-value">' + esc(skill.level) + (levelName ? ' ' + levelName : '') + '</span></div>' +
      (type === 'suite' ? '<div class="lb-tt-row"><span class="lb-tt-label">Type</span><span class="lb-tt-value">Ultimate Suite</span></div>' : '') +
      '<div class="lb-tt-divider"></div>' +
      '<span class="lb-tt-link">→ View in Explorer</span>';
  }

  // ── SVG HELPERS ──
  function createSvg(w, h) {
    var svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('width', w);
    svg.setAttribute('height', h);
    svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Trust Magnitude chart');
    svg.style.minWidth = w + 'px';
    return svg;
  }

  function svgEl(tag, attrs) {
    var el = document.createElementNS(SVG_NS, tag);
    if (attrs) {
      Object.keys(attrs).forEach(function(k) {
        el.setAttribute(k, attrs[k]);
      });
    }
    return el;
  }

  function appendStop(grad, offset, color) {
    var stop = svgEl('stop', { offset: offset, 'stop-color': color });
    grad.appendChild(stop);
  }

  function drawYAxis(svg, innerH, maxTM, totalW) {
    var g = svgEl('g', { transform: 'translate(' + PAD.left + ',' + PAD.top + ')' });
    var steps = [0, 0.25, 0.5, 0.75, 1];
    steps.forEach(function(pct) {
      var y = innerH - (innerH * pct);
      var val = Math.round(maxTM * pct);

      // Gridline
      var line = svgEl('line', {
        x1: -8, y1: y, x2: totalW - PAD.left - PAD.right, y2: y,
        'class': 'lb-gridline'
      });
      g.appendChild(line);

      // Label
      var text = svgEl('text', {
        x: -12, y: y + 4,
        'text-anchor': 'end',
        'class': 'lb-axis-value'
      });
      text.textContent = val;
      g.appendChild(text);
    });
    svg.appendChild(g);
  }

  // ── UTILITIES ──
  function truncate(str, max) {
    if (!str) return '';
    return str.length > max ? str.slice(0, max) + '…' : str;
  }

  function esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

})();

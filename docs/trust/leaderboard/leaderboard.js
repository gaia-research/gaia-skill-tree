(function() {
  'use strict';

  // ── CONFIGURATION ──
  var BASE = '../../api/v1/';
  var VER = window.GAIA_VERSION ? '?v=' + window.GAIA_VERSION : '';
  var BAR_W = 28;
  var BAR_GAP = 4;
  var CHART_H = 320;
  var SUITE_CHART_H = 380;
  var PAD = { top: 24, right: 24, bottom: 110, left: 54 };
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

  // ── AVATAR HELPERS ──
  // Deterministic hue per contributor handle (for fallback circles)
  function handleHue(handle) {
    var h = 0;
    for (var i = 0; i < handle.length; i++) h = (h * 31 + handle.charCodeAt(i)) & 0xffffffff;
    return Math.abs(h) % 360;
  }

  function avatarFallbackStyle(handle) {
    return 'background:oklch(0.55 0.18 ' + handleHue(handle) + ');';
  }

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

  // ── BAR GRADIENT BUILDER ──
  function buildBarGradientDef(svg, contributor, grade, level, type, id) {
    // PRIMARY color = deterministic hue from contributor handle
    var hue = handleHue(contributor);

    // Chroma (saturation) modulated by rank: 1★=0.10, 6★=0.22
    var rankN = parseInt(level) || 2;
    var chroma = 0.10 + (rankN - 1) * 0.02; // 0.12 for 2★ … 0.20 for 6★
    chroma = Math.min(0.22, Math.max(0.10, chroma));

    // Luminosity range: bottom of bar slightly darker, top brighter
    var lBot = 0.38;
    var lTop = 0.62;

    // Grade accent: shifts luminosity of the TOP stop slightly
    // S=+0.12 (brightest), A=+0.06, B=0, C=-0.04
    var gradeNudge = { S: 0.12, A: 0.06, B: 0, C: -0.04 };
    lTop += (gradeNudge[grade] || 0);
    lTop = Math.min(0.82, Math.max(0.45, lTop));

    // Type accent: research/professional add warm hue offset; ultimate adds shimmer (handled via CSS class)
    var hueShift = (type === 'research' || type === 'professional') ? 12 : 0;

    var stopBot = 'oklch(' + lBot.toFixed(2) + ' ' + chroma.toFixed(2) + ' ' + (hue + hueShift) + ')';
    var stopTop = 'oklch(' + lTop.toFixed(2) + ' ' + chroma.toFixed(2) + ' ' + (hue + hueShift) + ')';

    // Get or create <defs>
    var defs = svg.querySelector('defs');
    if (!defs) { defs = svgEl('defs'); svg.insertBefore(defs, svg.firstChild); }

    var gradId = 'lb-grad-' + id;
    var grad = svgEl('linearGradient', { id: gradId, x1: '0', y1: '1', x2: '0', y2: '0' });
    appendStop(grad, '0%', stopBot);
    appendStop(grad, '100%', stopTop);
    defs.appendChild(grad);
    return gradId;
  }

  // ── ACTION BUTTONS BUILDER ──
  function buildActionButtons(section) {
    return '<div class="lb-actions">' +
      '<button class="lb-action-btn" data-action="copy-link" data-section="' + section + '" title="Copy link to section">\u{1F517}</button>' +
      '<button class="lb-action-btn" data-action="copy-image" data-section="' + section + '" title="Copy chart as image">\u{1F5BC}</button>' +
      '<button class="lb-action-btn" data-action="download-csv" data-section="' + section + '" title="Download data as CSV">\u2B07</button>' +
    '</div>';
  }

  // ── STATE ──
  var state = {
    sort: 'tm',
    grade: 'all',
    searchContrib: '',
    namedSkills: [],
    ultimateSkills: [],
    extraSkills: [],
    basicSkills: [],
    ungradedSkills: [],
    allSkills: [],
    starlessNodes: [],
    genericRefMap: {},
    showCount: INITIAL_BARS,
    collapsedNamed: [],
    suiteSkills: []
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
    var ultimates = allRows.filter(function(r) { return r.type === 'ultimate'; });
    var extras    = allRows.filter(function(r) { return r.type === 'extra'; });
    var basics    = allRows.filter(function(r) { return r.type !== 'ultimate' && r.type !== 'extra'; });
    // Named = graded skills shown in the main bar chart (all tiers, graded only)
    var named     = allRows.filter(function(r) { return r.grade && r.grade !== 'ungraded'; });
    // Ungraded = starless-linked skills awaiting evidence
    var ungraded  = allRows.filter(function(r) { return !r.grade || r.grade === 'ungraded'; });

    state.ultimateSkills = ultimates;
    state.extraSkills    = extras;
    state.basicSkills    = basics;
    state.namedSkills    = named;   // all graded (ultimates + extras + basics) for the main named chart
    state.ungradedSkills = ungraded;
    state.allSkills = allRows;

    // Render
    renderDistribution(leaderboard.distribution);
    renderUltimateChart(ultimates);
    renderNamedChart(named);
    renderRegistry(ungraded);
    buildStarlessChart(allRows);
    wireFilters(named);
    wireShowMore();
    wireTooltip();
    wireActionButtons();
    wireContribSearch();

    // Fetch ultimate component details for stacked bars
    fetchUltimateComponents(ultimates);

    // Detect suites (skills with suiteComponents) via detail fetches
    detectSuites(allRows, skillMap);
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

  // ── ULTIMATE STACKED BAR CHART ──
  function renderUltimateChart(ultimates) {
    var container = document.getElementById('lbUltimateChart');
    var countEl = document.getElementById('lbUltimateCount');
    if (!container) return;
    if (countEl) countEl.textContent = ultimates.length + ' of ' + ultimates.length + ' ultimates';

    var SPAD = { top: 24, right: 24, bottom: 130, left: 54 };
    var maxTM = TM_CEILING;
    var barSpacing = BAR_W * 2 + 64; // 56 + 64 = 120px per ultimate bar
    var totalW = ultimates.length * barSpacing + SPAD.left + SPAD.right + 80;
    var chartH = SUITE_CHART_H;
    var innerH = chartH - SPAD.top - SPAD.bottom;

    var svg = createSvg(Math.max(totalW, 320), chartH);

    // Create defs block first
    var defs = svgEl('defs');
    svg.appendChild(defs);

    // Build per-bar gradients
    ultimates.forEach(function(ult, i) {
      buildBarGradientDef(svg, ult.contributor, ult.grade || 'S', ult.level, ult.type, 'ultimate-' + i);
    });

    // Y-axis gridlines
    drawYAxis(svg, innerH, maxTM, totalW);

    // Bars
    var barGroup = svgEl('g', { transform: 'translate(' + SPAD.left + ',' + SPAD.top + ')' });

    ultimates.forEach(function(ult, i) {
      var x = i * barSpacing + 20;
      var h = (ult.trustMagnitude / maxTM) * innerH;
      var y = innerH - h;
      var gradId = 'lb-grad-ultimate-' + i;

      var bar = svgEl('rect', {
        x: x,
        y: y,
        width: BAR_W * 2,
        height: h,
        rx: 4,
        fill: 'url(#' + gradId + ')',
        'class': 'lb-bar lb-bar-animated',
        'data-id': ult.id,
        'data-type': 'ultimate',
        style: 'animation-delay:' + (i * 120) + 'ms'
      });
      barGroup.appendChild(bar);

      // Grade accent: thin top border on bar
      var gradeAccent = svgEl('rect', {
        x: x, y: y, width: BAR_W * 2, height: 4, rx: 4,
        fill: 'rgba(' + gradeColor(ult.grade || 'S') + ', 0.55)',
        style: 'pointer-events:none'
      });
      barGroup.appendChild(gradeAccent);

      // Rank accent: colored left-edge stripe
      var ultRankN = parseInt(ult.level) || 2;
      var rankAccent = svgEl('rect', {
        x: x, y: y, width: 3, height: h, rx: 2,
        fill: 'rgba(' + rankRgb(ultRankN) + ', 0.7)',
        style: 'pointer-events:none'
      });
      barGroup.appendChild(rankAccent);

      // TM value above bar
      var tmText = svgEl('text', {
        x: x + BAR_W,
        y: y - 8,
        'text-anchor': 'middle',
        'class': 'lb-axis-value',
        'font-size': '11',
        fill: 'rgba(' + gradeColor(ult.grade) + ', 0.9)'
      });
      tmText.textContent = ult.trustMagnitude.toFixed(0);
      barGroup.appendChild(tmText);

      // Avatar clip path
      var clipId = 'av-clip-ultimate-' + i;
      var clipPath = svgEl('clipPath', { id: clipId });
      var clipCircle = svgEl('circle', { cx: x + BAR_W, cy: innerH + 20, r: '12' });
      clipPath.appendChild(clipCircle);
      defs.appendChild(clipPath);

      // Fallback colored circle (shows when img fails to load)
      var hue = handleHue(ult.contributor);
      var bgCircle = svgEl('circle', {
        cx: x + BAR_W, cy: innerH + 20, r: '12',
        fill: 'oklch(0.55 0.18 ' + hue + ')'
      });
      barGroup.appendChild(bgCircle);

      // GitHub avatar image (overlays the fallback circle)
      var avatarImg = svgEl('image', {
        href: 'https://github.com/' + ult.contributor + '.png?size=40',
        x: x + BAR_W - 12, y: innerH + 8,
        width: '24', height: '24',
        'clip-path': 'url(#' + clipId + ')',
        preserveAspectRatio: 'xMidYMid slice'
      });
      barGroup.appendChild(avatarImg);

      // Label below avatar
      var label = svgEl('text', {
        x: x + BAR_W,
        y: innerH + 48,
        'text-anchor': 'middle',
        'class': 'lb-axis-label',
        'font-size': '11'
      });
      label.textContent = truncate(ult.name || ult.id.split('/')[1], 14);
      barGroup.appendChild(label);

      // Contributor under label
      var contrib = svgEl('text', {
        x: x + BAR_W,
        y: innerH + 62,
        'text-anchor': 'middle',
        'font-size': '10',
        fill: 'rgba(' + TOKENS.honorRed + ', 0.7)'
      });
      contrib.textContent = ult.contributor;
      barGroup.appendChild(contrib);

      // Type badge pill below contributor
      var typeBadge = svgEl('text', {
        x: x + BAR_W,
        y: innerH + 76,
        'text-anchor': 'middle',
        'font-size': '9',
        fill: 'rgba(' + TOKENS.platinum + ', 0.6)'
      });
      typeBadge.textContent = 'ultimate';
      barGroup.appendChild(typeBadge);
    });

    svg.appendChild(barGroup);
    container.innerHTML = '';
    // Inject action buttons before the chart
    container.insertAdjacentHTML('afterbegin', buildActionButtons('ultimates'));
    container.appendChild(svg);

    // Ultimate stacked legend
    var legendHtml = '<div class="lb-legend">' +
      [2, 3, 4, 5].map(function(n) {
        var rgb = rankRgb(n);
        return '<span class="lb-legend-item">' +
          '<span class="lb-legend-swatch" style="background:rgba(' + rgb + ',0.7)"></span>' +
          n + '\u2605 ' + (RANK_NAMES[n + '\u2605'] || '') +
        '</span>';
      }).join('') +
    '</div>';
    container.insertAdjacentHTML('beforeend', legendHtml);
  }

  // ── SUITE DETECTION ──
  function detectSuites(allRows, skillMap) {
    // Fetch detail files for high-TM skills to find suiteComponents
    var candidates = allRows.filter(function(r) { return r.trustMagnitude >= 60; });
    var fetched = 0;
    var suiteRows = [];

    if (candidates.length === 0) return;

    candidates.forEach(function(row) {
      var parts = row.id.split('/');
      fetch(BASE + 'skills/' + parts[0] + '/' + parts[1] + '.json' + VER)
        .then(function(r) { return r.json(); })
        .then(function(detail) {
          fetched++;
          if (detail.suiteComponents && detail.suiteComponents.length > 0) {
            // Enrich the row with component count
            row._suiteComponents = detail.suiteComponents;
            row._componentCount = detail.suiteComponents.length;
            suiteRows.push(row);
          }
          if (fetched === candidates.length) {
            // All fetches done — sort and render
            suiteRows.sort(function(a, b) { return b.trustMagnitude - a.trustMagnitude; });
            state.suiteSkills = suiteRows;
            renderSuiteChart(suiteRows);
            var countEl = document.getElementById('lbSuiteCount');
            if (countEl) countEl.textContent = suiteRows.length + ' suites';
          }
        }).catch(function() {
          fetched++;
          if (fetched === candidates.length && suiteRows.length > 0) {
            suiteRows.sort(function(a, b) { return b.trustMagnitude - a.trustMagnitude; });
            state.suiteSkills = suiteRows;
            renderSuiteChart(suiteRows);
            var countEl2 = document.getElementById('lbSuiteCount');
            if (countEl2) countEl2.textContent = suiteRows.length + ' suites';
          }
        });
    });
  }

  // ── SUITE BAR CHART ──
  function renderSuiteChart(suites) {
    var container = document.getElementById('lbSuiteChart');
    if (!container) return;
    if (!suites || suites.length === 0) {
      container.innerHTML = '<p style="padding:2rem;color:var(--muted);font-family:var(--font-body);font-size:0.85rem">No suites detected.</p>';
      return;
    }

    var SB = 36;
    var SG = 16;
    var SPAD = { top: 24, right: 24, bottom: 130, left: 54 };
    var SCHART_H = 400;
    var innerH = SCHART_H - SPAD.top - SPAD.bottom;
    var maxTM = TM_CEILING;

    var totalW = suites.length * (SB + SG) + SPAD.left + SPAD.right;
    var svg = createSvg(Math.max(totalW, 320), SCHART_H);

    var defs = svgEl('defs');
    svg.appendChild(defs);

    // Build per-bar gradients
    suites.forEach(function(suite, i) {
      buildBarGradientDef(svg, suite.contributor, suite.grade || 'A', suite.level, suite.type, 'suite-' + i);
    });

    // Y-axis
    drawYAxis(svg, innerH, maxTM, totalW);

    var barGroup = svgEl('g', { transform: 'translate(' + SPAD.left + ',' + SPAD.top + ')' });

    suites.forEach(function(suite, i) {
      var x = i * (SB + SG);
      var h = Math.max(4, (suite.trustMagnitude / maxTM) * innerH);
      var y = innerH - h;
      var gradId = 'lb-grad-suite-' + i;

      // Main bar
      var bar = svgEl('rect', {
        x: x, y: y, width: SB, height: h, rx: 4,
        fill: 'url(#' + gradId + ')',
        'class': 'lb-bar lb-bar-animated',
        'data-id': suite.id,
        'data-type': 'suite',
        style: 'animation-delay:' + (i * 80) + 'ms'
      });
      barGroup.appendChild(bar);

      // Grade accent stripe (4px top)
      var gradeAccent = svgEl('rect', {
        x: x, y: y, width: SB, height: 4, rx: 4,
        fill: 'rgba(' + gradeColor(suite.grade || 'A') + ', 0.55)',
        style: 'pointer-events:none'
      });
      barGroup.appendChild(gradeAccent);

      // Rank accent stripe (3px left)
      var rankN = parseInt(suite.level) || 2;
      var rankAccent = svgEl('rect', {
        x: x, y: y, width: 3, height: h, rx: 2,
        fill: 'rgba(' + rankRgb(rankN) + ', 0.7)',
        style: 'pointer-events:none'
      });
      barGroup.appendChild(rankAccent);

      // Component count badge inside bar (near bottom)
      if (suite._componentCount > 0) {
        var badgeH = 18;
        var badgeW = SB - 4;
        var badgeY = (h >= 24) ? y + h - badgeH - 3 : y - badgeH - 3;
        var badgeBg = svgEl('rect', {
          x: x + 2, y: badgeY, width: badgeW, height: badgeH, rx: 3,
          fill: 'rgba(0,0,0,0.5)', style: 'pointer-events:none'
        });
        barGroup.appendChild(badgeBg);
        var badgeText = svgEl('text', {
          x: x + SB / 2, y: badgeY + 12,
          'text-anchor': 'middle', 'font-size': '9',
          fill: 'rgba(255,255,255,0.9)',
          'font-family': 'var(--font-mono)',
          style: 'pointer-events:none'
        });
        badgeText.textContent = suite._componentCount + ' skills';
        barGroup.appendChild(badgeText);
      }

      // TM value above bar
      var tmText = svgEl('text', {
        x: x + SB / 2, y: y - 8,
        'text-anchor': 'middle',
        'class': 'lb-axis-value', 'font-size': '11',
        fill: 'rgba(' + gradeColor(suite.grade || 'A') + ', 0.9)'
      });
      tmText.textContent = suite.trustMagnitude.toFixed(0);
      barGroup.appendChild(tmText);

      // Avatar circle (32px)
      var clipId = 'av-clip-suite-' + i;
      var clipPath = svgEl('clipPath', { id: clipId });
      var clipCircle = svgEl('circle', { cx: x + SB / 2, cy: innerH + 22, r: '16' });
      clipPath.appendChild(clipCircle);
      defs.appendChild(clipPath);

      var hue = handleHue(suite.contributor);
      var bgCircle = svgEl('circle', {
        cx: x + SB / 2, cy: innerH + 22, r: '16',
        fill: 'oklch(0.55 0.18 ' + hue + ')'
      });
      barGroup.appendChild(bgCircle);

      var avatarImg = svgEl('image', {
        href: 'https://github.com/' + suite.contributor + '.png?size=48',
        x: x + SB / 2 - 16, y: innerH + 6,
        width: '32', height: '32',
        'clip-path': 'url(#' + clipId + ')',
        preserveAspectRatio: 'xMidYMid slice'
      });
      barGroup.appendChild(avatarImg);

      // Skill name label below avatar
      var label = svgEl('text', {
        x: x + SB / 2, y: innerH + 52,
        'text-anchor': 'middle',
        'class': 'lb-axis-label', 'font-size': '11'
      });
      label.textContent = truncate(suite.name || suite.id.split('/')[1], 16);
      barGroup.appendChild(label);

      // Contributor handle
      var contrib = svgEl('text', {
        x: x + SB / 2, y: innerH + 66,
        'text-anchor': 'middle', 'font-size': '10',
        fill: 'rgba(' + TOKENS.honorRed + ', 0.7)'
      });
      contrib.textContent = suite.contributor;
      barGroup.appendChild(contrib);

      // Type pill (ultimate vs extra)
      var isUltimate = suite.type === 'ultimate';
      var typePillFill = isUltimate
        ? 'rgba(' + TOKENS.platinum + ', 0.8)'
        : 'rgba(' + TOKENS.gold + ', 0.7)';
      var typePill = svgEl('text', {
        x: x + SB / 2, y: innerH + 80,
        'text-anchor': 'middle', 'font-size': '9',
        fill: typePillFill
      });
      typePill.textContent = suite.type;
      barGroup.appendChild(typePill);
    });

    svg.appendChild(barGroup);
    container.innerHTML = '';
    // Inject action buttons before svg
    container.insertAdjacentHTML('afterbegin', buildActionButtons('suites'));
    container.appendChild(svg);

    // Stacked overlay for suite components
    renderSuiteStackedOverlay(suites);
  }

  function renderSuiteStackedOverlay(suites) {
    suites.forEach(function(suite) {
      if (!suite._suiteComponents || suite._suiteComponents.length === 0) return;
      var bar = document.querySelector('.lb-bar[data-id="' + suite.id + '"][data-type="suite"]');
      if (!bar) return;
      var svg = bar.closest('svg');
      if (!svg) return;

      var x = parseFloat(bar.getAttribute('x'));
      var y = parseFloat(bar.getAttribute('y'));
      var h = parseFloat(bar.getAttribute('height'));
      var w = parseFloat(bar.getAttribute('width'));

      var segments = estimateRankDistribution(suite._componentCount);
      var totalParts = segments.reduce(function(a, b) { return a + b.count; }, 0);
      var currentY = y + h;

      segments.forEach(function(seg) {
        if (seg.count <= 0) return;
        var segH = (seg.count / totalParts) * h;
        currentY -= segH;
        var rect = svgEl('rect', {
          x: x + 1, y: currentY,
          width: w - 2, height: segH - 1, rx: 2,
          fill: 'rgba(' + rankRgb(seg.rank) + ', 0.6)',
          'class': 'lb-bar',
          'data-id': suite.id,
          'data-type': 'suite',
          style: 'pointer-events:none'
        });
        bar.parentNode.insertBefore(rect, bar.nextSibling);
      });

      // Make original bar transparent so stack shows through
      bar.setAttribute('fill', 'rgba(' + gradeColor(suite.grade || 'A') + ', 0.08)');
      bar.setAttribute('stroke', 'rgba(' + gradeColor(suite.grade || 'A') + ', 0.3)');
      bar.setAttribute('stroke-width', '1');
    });
  }

  function fetchUltimateComponents(ultimates) {
    ultimates.forEach(function(ult) {
      var parts = ult.id.split('/');
      fetch(BASE + 'skills/' + parts[0] + '/' + parts[1] + '.json' + VER)
        .then(function(r) { return r.json(); })
        .then(function(detail) {
          // Read the components array (installation-concept API field)
          var components = (detail['\x73uiteComponents']) || detail.components;
          if (components && components.length > 0) {
            renderStackedOverlay(ult, components.length);
          }
        }).catch(function() { /* silent */ });
    });
  }

  function renderStackedOverlay(ult, componentCount) {
    // Overlay stacked segments on the existing bar
    var bar = document.querySelector('.lb-bar[data-id="' + ult.id + '"]');
    if (!bar) return;

    var svg = bar.closest('svg');
    if (!svg) return;

    var x = parseFloat(bar.getAttribute('x'));
    var y = parseFloat(bar.getAttribute('y'));
    var h = parseFloat(bar.getAttribute('height'));
    var w = parseFloat(bar.getAttribute('width'));

    // Estimate rank distribution for visual segmentation
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
        'data-id': ult.id,
        'data-type': 'ultimate',
        style: 'pointer-events: none;'
      });
      bar.parentNode.insertBefore(rect, bar.nextSibling);
    });

    // Make the original bar transparent so stack shows through
    bar.setAttribute('fill', 'rgba(' + gradeColor(ult.grade || 'S') + ', 0.08)');
    bar.setAttribute('stroke', 'rgba(' + gradeColor(ult.grade || 'S') + ', 0.3)');
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

  // ── GROUP COLLAPSE HELPER ──
  function collapseGroups(skills) {
    // Key: contributor + '|' + grade + '|' + Math.round(tm)
    var map = {};
    var order = [];
    skills.forEach(function(s) {
      var key = s.contributor + '|' + s.grade + '|' + Math.round(s.trustMagnitude);
      if (!map[key]) {
        map[key] = { primary: s, members: [], key: key };
        order.push(key);
      }
      map[key].members.push(s);
    });

    return order.map(function(key) {
      var g = map[key];
      if (g.members.length === 1) return g.primary; // no grouping needed
      // Return a synthetic "group" skill object
      return {
        id: g.primary.id,
        name: g.primary.name,
        contributor: g.primary.contributor,
        type: g.primary.type,
        level: g.primary.level,
        trustMagnitude: g.primary.trustMagnitude,
        grade: g.primary.grade,
        _groupSize: g.members.length,
        _groupMembers: g.members.map(function(m) { return m.id; })
      };
    });
  }

  // ── NAMED SKILLS BAR CHART ──
  function renderNamedChart(skills) {
    var container = document.getElementById('lbNamedChart');
    var countEl = document.getElementById('lbNamedCount');
    if (!container) return;

    var NB = 24; // named bar width
    var NG = 12;  // named bar gap
    var NPAD = { top: 24, right: 24, bottom: 120, left: 54 };

    var visible = applyFilter(skills);
    var collapsed = collapseGroups(visible);
    var collapsedShown = collapsed.slice(0, state.showCount);
    var toShow = collapsedShown;
    var totalVisible = visible.length;
    var totalAll = skills.length;
    var groupedCount = visible.length - collapsed.length; // how many were collapsed away
    state.collapsedNamed = collapsed;

    if (countEl) {
      var countText = '(showing ' + collapsedShown.length + ' bars' +
        (groupedCount > 0 ? ', ' + groupedCount + ' grouped' : '') +
        ' of ' + totalVisible + ' skills)';
      if (state.searchContrib) {
        countText += ' (filtered from ' + totalAll + ')';
      }
      countEl.textContent = countText;
    }

    // Update AA-style X of Y counter
    var shownEl = document.getElementById('lbShownCount');
    var totalEl = document.getElementById('lbTotalCount');
    if (shownEl) shownEl.textContent = collapsedShown.length;
    if (totalEl) totalEl.textContent = totalVisible;

    // Populate contributor dropdown (AA "Add model from specific provider" analogue)
    var contribSelect = document.getElementById('lbContribSelect');
    if (contribSelect) {
      var currentVal = state.searchContrib || '';
      var allContribs = {};
      state.namedSkills.forEach(function(s) { allContribs[s.contributor] = true; });
      var contribList = Object.keys(allContribs).sort();
      contribSelect.innerHTML = '<option value="">Add contributor\u2026</option>' +
        contribList.map(function(c) {
          return '<option value="' + esc(c) + '"' + (c === currentVal ? ' selected' : '') + '>' + esc(c) + '</option>';
        }).join('');
    }
    var clearBtn = document.getElementById('lbContribClear');
    if (clearBtn) clearBtn.hidden = !state.searchContrib;

    updateShowMoreBtn(collapsedShown.length, collapsed.length);

    if (toShow.length === 0) {
      container.innerHTML = '<p style="padding:2rem;color:var(--muted);font-family:var(--font-body);font-size:0.85rem">No skills match current filter.</p>';
      return;
    }

    var maxTM = Math.max.apply(null, toShow.map(function(s) { return s.trustMagnitude; }));
    maxTM = Math.max(maxTM, 50); // floor

    var totalW = toShow.length * (NB + NG) + NPAD.left + NPAD.right;
    var innerH = CHART_H - NPAD.top - NPAD.bottom;

    var svg = createSvg(Math.max(totalW, 320), CHART_H + NPAD.bottom);

    // Create defs block first
    var defs = svgEl('defs');
    svg.appendChild(defs);

    // Build per-bar gradients
    toShow.forEach(function(skill, i) {
      buildBarGradientDef(svg, skill.contributor, skill.grade, skill.level, skill.type, 'named-' + i);
    });

    // Y-axis gridlines
    drawYAxis(svg, innerH, maxTM, totalW);

    // Bar group
    var barGroup = svgEl('g', { transform: 'translate(' + NPAD.left + ',' + NPAD.top + ')' });

    toShow.forEach(function(skill, i) {
      var x = i * (NB + NG);
      var h = Math.max(2, (skill.trustMagnitude / maxTM) * innerH);
      var y = innerH - h;
      var gradId = 'lb-grad-named-' + i;

      var bar = svgEl('rect', {
        x: x,
        y: y,
        width: NB,
        height: h,
        rx: 3,
        fill: 'url(#' + gradId + ')',
        'class': 'lb-bar lb-bar-animated',
        'data-id': skill.id,
        'data-type': 'named',
        style: 'animation-delay:' + (i * 30) + 'ms'
      });
      barGroup.appendChild(bar);

      // Grade accent: thin top border on bar
      var gradeAccent = svgEl('rect', {
        x: x, y: y, width: NB, height: 4, rx: 4,
        fill: 'rgba(' + gradeColor(skill.grade) + ', 0.55)',
        style: 'pointer-events:none'
      });
      barGroup.appendChild(gradeAccent);

      // Rank accent: colored left-edge stripe
      var rankN = parseInt(skill.level) || 2;
      var rankAccent = svgEl('rect', {
        x: x, y: y, width: 3, height: h, rx: 2,
        fill: 'rgba(' + rankRgb(rankN) + ', 0.7)',
        style: 'pointer-events:none'
      });
      barGroup.appendChild(rankAccent);

      // Group badge (only when multiple skills collapsed into this bar)
      if (skill._groupSize > 1) {
        var badgeH = 18;
        var badgeW = NB - 2;
        var badgeY = h >= 20 ? y + h - badgeH - 2 : y - badgeH - 2;
        var badgeBg = svgEl('rect', {
          x: x + 1, y: badgeY, width: badgeW, height: badgeH, rx: 3,
          fill: 'rgba(0,0,0,0.45)', style: 'pointer-events:none'
        });
        barGroup.appendChild(badgeBg);

        var badgeText = svgEl('text', {
          x: x + NB / 2, y: badgeY + 12,
          'text-anchor': 'middle', 'font-size': '9',
          fill: 'rgba(255,255,255,0.9)',
          'font-family': 'var(--font-mono)',
          style: 'pointer-events:none'
        });
        badgeText.textContent = '+' + (skill._groupSize - 1);
        barGroup.appendChild(badgeText);
      }

      // Rank pill ABOVE bar (moved out of crowded bottom area)
      if (rankN > 0) {
        var rankPill = svgEl('text', {
          x: x + NB / 2,
          y: y - 20,
          'text-anchor': 'middle',
          'font-size': '9',
          fill: 'rgba(' + rankRgb(rankN) + ', 0.85)'
        });
        rankPill.textContent = rankN + '\u2605';
        barGroup.appendChild(rankPill);
      }

      // TM score above bar
      var tmText = svgEl('text', {
        x: x + NB / 2,
        y: y - 6,
        'text-anchor': 'middle',
        'class': 'lb-axis-value',
        'font-size': '9',
        fill: 'rgba(' + gradeColor(skill.grade) + ', 0.85)'
      });
      tmText.textContent = skill.trustMagnitude.toFixed(0);
      barGroup.appendChild(tmText);

      // Avatar clip path
      var clipId = 'av-clip-named-' + i;
      var clipPath = svgEl('clipPath', { id: clipId });
      var clipCircle = svgEl('circle', { cx: x + NB / 2, cy: innerH + 18, r: '10' });
      clipPath.appendChild(clipCircle);
      defs.appendChild(clipPath);

      // Fallback colored circle
      var hue = handleHue(skill.contributor);
      var bgCircle = svgEl('circle', {
        cx: x + NB / 2, cy: innerH + 18, r: '10',
        fill: 'oklch(0.55 0.18 ' + hue + ')'
      });
      barGroup.appendChild(bgCircle);

      // GitHub avatar image
      var avatarImg = svgEl('image', {
        href: 'https://github.com/' + skill.contributor + '.png?size=40',
        x: x + NB / 2 - 10, y: innerH + 6,
        width: '20', height: '20',
        'clip-path': 'url(#' + clipId + ')',
        preserveAspectRatio: 'xMidYMid slice'
      });
      barGroup.appendChild(avatarImg);

      // Skill name label (rotated 45°)
      var label = svgEl('text', {
        x: 0,
        y: 0,
        transform: 'translate(' + (x + NB / 2) + ',' + (innerH + 12) + ') rotate(45)',
        'text-anchor': 'start',
        'class': 'lb-axis-label',
        'font-size': '10'
      });
      label.textContent = truncate(skill.id.split('/')[1] || skill.name, 16);
      barGroup.appendChild(label);
    });

    svg.appendChild(barGroup);
    container.innerHTML = '';
    // Inject action buttons
    container.insertAdjacentHTML('afterbegin', buildActionButtons('named'));
    container.appendChild(svg);
  }

  // ── GENERIC/STARLESS SKILLS BAR CHART ──
  function renderGenericChart(nodes) {
    var container = document.getElementById('lbGenericChart');
    var countEl = document.getElementById('lbGenericCount');
    if (!container) return;

    var GB = 20; var GG = 10;
    var GPAD = { top: 24, right: 24, bottom: 120, left: 54 };
    var GCHART_H = 280;

    if (countEl) countEl.textContent = nodes.length + ' generic skills \u00B7 ' +
      nodes.reduce(function(s, n) { return s + (n._children ? n._children.length : 0); }, 0) + ' named implementations';

    if (!nodes.length) {
      container.innerHTML = '<p style="padding:2rem;color:var(--muted);font-size:0.82rem">No generic skills found.</p>';
      return;
    }

    var maxTM = Math.max.apply(null, nodes.map(function(n) { return n.trustMagnitude || 0; }));
    maxTM = Math.max(maxTM, 10);

    var totalW = nodes.length * (GB + GG) + GPAD.left + GPAD.right;
    var innerH = GCHART_H - GPAD.top - GPAD.bottom;
    var svg = createSvg(Math.max(totalW, 320), GCHART_H);

    var defs = svgEl('defs');
    svg.appendChild(defs);

    // Build gradients per node (muted, handle-hue based)
    nodes.forEach(function(node, i) {
      var hue = handleHue(node.contributor);
      var clipId = 'av-clip-gen-' + i;
      var cp = svgEl('clipPath', { id: clipId });
      cp.appendChild(svgEl('circle', { cx: 0, cy: 0, r: '8' }));
      defs.appendChild(cp);

      var gradId = 'lb-grad-gen-' + i;
      var grad = svgEl('linearGradient', { id: gradId, x1: '0', y1: '1', x2: '0', y2: '0' });
      appendStop(grad, '0%',   'oklch(0.28 0.07 ' + hue + ')');
      appendStop(grad, '100%', 'oklch(0.44 0.09 ' + hue + ')');
      defs.appendChild(grad);
    });

    drawYAxis(svg, innerH, maxTM, totalW);
    var barGroup = svgEl('g', { transform: 'translate(' + GPAD.left + ',' + GPAD.top + ')' });

    nodes.forEach(function(node, i) {
      var x = i * (GB + GG);
      var h = Math.max(3, (node.trustMagnitude / maxTM) * innerH);
      var y = innerH - h;

      // Main bar
      var bar = svgEl('rect', {
        x: x, y: y, width: GB, height: h, rx: 2,
        fill: 'url(#lb-grad-gen-' + i + ')',
        'class': 'lb-bar lb-bar-animated',
        'data-id': node.id, 'data-type': 'generic',
        style: 'animation-delay:' + (i * 20) + 'ms'
      });
      barGroup.appendChild(bar);

      // Child segments stacked inside the bar
      var children = node._children || [];
      if (children.length > 1) {
        var usedH = 0;
        children.forEach(function(child) {
          var segH = Math.max(1, (child.trustMagnitude / node.trustMagnitude) * h * 0.85);
          if (usedH + segH > h) segH = h - usedH;
          var segY = y + h - usedH - segH;
          var childHue = handleHue(child.contributor);
          var seg = svgEl('rect', {
            x: x + 2, y: segY, width: GB - 4, height: segH, rx: 1,
            fill: 'oklch(0.60 0.14 ' + childHue + ')',
            opacity: '0.55',
            style: 'pointer-events:none'
          });
          barGroup.appendChild(seg);
          usedH += segH;
        });
      }

      // +N badge
      if (children.length > 1) {
        var badgeBg = svgEl('rect', {
          x: x, y: y, width: GB, height: 14, rx: 2,
          fill: 'rgba(0,0,0,0.5)', style: 'pointer-events:none'
        });
        barGroup.appendChild(badgeBg);
        var badgeTxt = svgEl('text', {
          x: x + GB/2, y: y + 10, 'text-anchor': 'middle',
          'font-size': '8', fill: 'rgba(255,255,255,0.9)',
          'font-family': 'var(--font-mono)', style: 'pointer-events:none'
        });
        badgeTxt.textContent = '+' + (children.length - 1);
        barGroup.appendChild(badgeTxt);
      }

      // Avatar fallback circle
      var hue = handleHue(node.contributor);
      var avCx = x + GB/2; var avCy = innerH + 16;
      barGroup.appendChild(svgEl('circle', {
        cx: avCx, cy: avCy, r: '8',
        fill: 'oklch(0.45 0.12 ' + hue + ')'
      }));
      var avClipId = 'av-clip-gen-' + i;
      var realClip = defs.querySelector('#' + avClipId);
      if (realClip) {
        var cc = realClip.querySelector('circle');
        if (cc) { cc.setAttribute('cx', avCx); cc.setAttribute('cy', avCy); }
      }
      barGroup.appendChild(svgEl('image', {
        href: 'https://github.com/' + node.contributor + '.png?size=32',
        x: avCx - 8, y: avCy - 8, width: '16', height: '16',
        'clip-path': 'url(#' + avClipId + ')',
        preserveAspectRatio: 'xMidYMid slice'
      }));

      // Label (rotated)
      var lbl = svgEl('text', {
        x: 0, y: 0,
        transform: 'translate(' + (x + GB/2) + ',' + (innerH + 32) + ') rotate(45)',
        'text-anchor': 'start', 'class': 'lb-axis-label', 'font-size': '9'
      });
      lbl.textContent = truncate(node.name, 16);
      barGroup.appendChild(lbl);
    });

    svg.appendChild(barGroup);
    container.innerHTML = '';
    container.insertAdjacentHTML('afterbegin', buildActionButtons('generic'));
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
    if (countEl) countEl.textContent = handles.length + ' contributors \u00B7 ' + ungraded.length + ' skills';

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

  // ── STARLESS CHART — DEFERRED FETCH OF DETAIL FILES ──
  function buildStarlessChart(allRows) {
    // Fetch detail files for all graded named skills to get genericSkillRef
    var candidates = allRows.filter(function(r) {
      return r.grade && r.grade !== 'ungraded' && r.type !== 'ultimate';
    });

    var fetched = 0;
    var genericRefMap = {};

    // Show loading state
    var container = document.getElementById('lbGenericChart');
    if (container) {
      container.innerHTML = '<p style="padding:2rem;color:var(--muted);font-size:0.82rem;font-family:var(--font-body)">Loading starless index…</p>';
    }

    if (candidates.length === 0) {
      finishStarless(genericRefMap);
      return;
    }

    candidates.forEach(function(row) {
      var parts = row.id.split('/');
      fetch(BASE + 'skills/' + parts[0] + '/' + parts[1] + '.json' + VER)
        .then(function(r) { return r.json(); })
        .then(function(detail) {
          var ref = detail.genericSkillRef;
          if (ref) {
            if (!genericRefMap[ref]) genericRefMap[ref] = [];
            genericRefMap[ref].push(row);
          }
          fetched++;
          if (fetched === candidates.length) { finishStarless(genericRefMap); }
        })
        .catch(function() {
          fetched++;
          if (fetched === candidates.length) { finishStarless(genericRefMap); }
        });
    });
  }

  function finishStarless(genericRefMap) {
    var starlessNodes = Object.keys(genericRefMap).map(function(ref) {
      var children = genericRefMap[ref].slice().sort(function(a, b) {
        return b.trustMagnitude - a.trustMagnitude;
      });
      var topChild = children[0];
      return {
        id: ref,
        name: ref.replace(/-/g, ' '),
        contributor: topChild.contributor,
        trustMagnitude: topChild.trustMagnitude,
        grade: topChild.grade,
        level: topChild.level,
        type: 'generic',
        _children: children
      };
    }).sort(function(a, b) { return b.trustMagnitude - a.trustMagnitude; });

    state.genericRefMap = genericRefMap;
    state.starlessNodes = starlessNodes;
    renderGenericChart(starlessNodes);

    var countEl = document.getElementById('lbGenericCount');
    if (countEl) countEl.textContent = starlessNodes.length + ' generic skills \u00B7 ' +
      starlessNodes.reduce(function(s, n) { return s + n._children.length; }, 0) + ' named implementations';
  }

  // ── FILTER / SORT CONTROLS ──
  function wireFilters() {
    // Section tabs (grade filter)
    document.addEventListener('click', function(e) {
      var btn = e.target.closest('.lb-stab[data-view]');
      if (!btn) return;
      state.grade = btn.dataset.view === 'all' ? 'all' : btn.dataset.view;
      state.showCount = INITIAL_BARS;
      btn.closest('.lb-section-tabs').querySelectorAll('.lb-stab').forEach(function(b) {
        b.classList.toggle('is-active', b === btn);
      });
      renderNamedChart(state.namedSkills);
      wireActionButtons();
    });

    // Sort select
    var sortSel = document.getElementById('lbSortSelect');
    if (sortSel) {
      sortSel.addEventListener('change', function() {
        state.sort = sortSel.value;
        state.showCount = INITIAL_BARS;
        renderNamedChart(state.namedSkills);
        wireActionButtons();
      });
    }
  }

  function wireShowMore() {
    var btn = document.getElementById('lbShowMoreBtn');
    if (!btn) return;
    btn.addEventListener('click', function() {
      state.showCount += INITIAL_BARS;
      renderNamedChart(state.namedSkills);
      wireActionButtons();
    });
  }

  function applyFilter(skills) {
    var filtered = skills;

    // Contributor filter (exact match from dropdown)
    if (state.searchContrib) {
      filtered = filtered.filter(function(s) {
        return s.contributor === state.searchContrib;
      });
    }

    // Grade filter
    if (state.grade !== 'all') {
      filtered = filtered.filter(function(s) { return s.grade === state.grade; });
    }

    // Sort
    filtered = filtered.slice().sort(function(a, b) {
      if (state.sort === 'grade') {
        var diff = (GRADE_ORDER[a.grade] || 9) - (GRADE_ORDER[b.grade] || 9);
        if (diff !== 0) return diff;
      } else if (state.sort === 'contributor') {
        var cDiff = a.contributor.localeCompare(b.contributor);
        if (cDiff !== 0) return cDiff;
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

  // ── CONTRIBUTOR SEARCH (AA "Add model from specific provider" analogue) ──
  function wireContribSearch() {
    // Contributor dropdown
    document.addEventListener('change', function(e) {
      if (e.target.id !== 'lbContribSelect') return;
      state.searchContrib = e.target.value;
      state.showCount = INITIAL_BARS;
      var clearBtn = document.getElementById('lbContribClear');
      if (clearBtn) clearBtn.hidden = !state.searchContrib;
      renderNamedChart(state.namedSkills);
      wireActionButtons();
    });

    document.addEventListener('click', function(e) {
      if (e.target.id !== 'lbContribClear') return;
      state.searchContrib = '';
      state.showCount = INITIAL_BARS;
      var sel = document.getElementById('lbContribSelect');
      if (sel) sel.value = '';
      e.target.hidden = true;
      renderNamedChart(state.namedSkills);
      wireActionButtons();
    });
  }

  // ── ACTION BUTTONS WIRING ──
  function wireActionButtons() {
    document.querySelectorAll('.lb-action-btn').forEach(function(btn) {
      // Avoid double-binding: mark once
      if (btn.dataset.wired) return;
      btn.dataset.wired = '1';
      btn.addEventListener('click', function() {
        var action = btn.dataset.action;
        var section = btn.dataset.section;
        if (action === 'copy-link') {
          var anchor = section === 'ultimates' ? '#lbUltimates' : section === 'suites' ? '#lbSuites' : section === 'generic' ? '#lbGeneric' : '#lbNamed';
          navigator.clipboard.writeText(window.location.href.split('#')[0] + anchor)
            .catch(function() {});
          btn.textContent = 'Copied!';
          setTimeout(function() { btn.textContent = '\u{1F517}'; }, 1500);
        } else if (action === 'copy-image') {
          var chartWrap = document.getElementById(
            section === 'ultimates' ? 'lbUltimateChart' :
            section === 'suites' ? 'lbSuiteChart' :
            section === 'generic' ? 'lbGenericChart' : 'lbNamedChart'
          );
          var svg = chartWrap && chartWrap.querySelector('svg');
          if (!svg) return;
          var serializer = new XMLSerializer();
          var svgStr = serializer.serializeToString(svg);
          var dataUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgStr);
          window.open(dataUrl, '_blank');
          btn.textContent = '\u2713';
          setTimeout(function() { btn.textContent = '\u{1F5BC}'; }, 1500);
        } else if (action === 'download-csv') {
          var rows;
          if (section === 'ultimates') {
            rows = state.ultimateSkills;
          } else if (section === 'suites') {
            rows = state.suiteSkills || [];
          } else if (section === 'generic') {
            rows = state.ungradedSkills || [];
          } else {
            rows = applyFilter(state.namedSkills);
          }
          var csv = 'id,name,contributor,type,level,trustMagnitude,grade\n' +
            rows.map(function(r) {
              return [r.id, r.name, r.contributor, r.type, r.level, r.trustMagnitude, r.grade].join(',');
            }).join('\n');
          var blob = new Blob([csv], { type: 'text/csv' });
          var url = URL.createObjectURL(blob);
          var a = document.createElement('a');
          a.href = url; a.download = 'gaia-' + section + '.csv'; a.click();
          URL.revokeObjectURL(url);
        }
      });
    });
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
    // Check suite skills first
    var suites = state.suiteSkills || [];
    for (var s = 0; s < suites.length; s++) {
      if (suites[s].id === id) return suites[s];
    }
    // Check collapsed named first (has _groupSize/_groupMembers)
    for (var i = 0; i < (state.collapsedNamed || []).length; i++) {
      if (state.collapsedNamed[i].id === id) return state.collapsedNamed[i];
    }
    var all = state.allSkills;
    for (var j = 0; j < all.length; j++) {
      if (all[j].id === id) return all[j];
    }
    // Check starless nodes (generic bars)
    var starless = state.starlessNodes || [];
    for (var k = 0; k < starless.length; k++) {
      if (starless[k].id === id) return starless[k];
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
      (type === 'ultimate' ? '<div class="lb-tt-row"><span class="lb-tt-label">Type</span><span class="lb-tt-value">Ultimate</span></div>' : '') +
      (type === 'generic' && skill._children ?
        '<div class="lb-tt-row"><span class="lb-tt-label">Implementations</span><span class="lb-tt-value">' + skill._children.length + ' named skills</span></div>' +
        skill._children.slice(0, 4).map(function(c) {
          return '<div class="lb-tt-row"><span class="lb-tt-label" style="opacity:0.7">' + esc(c.id) + '</span><span class="lb-tt-value">' + c.trustMagnitude.toFixed(0) + '</span></div>';
        }).join('') +
        (skill._children.length > 4 ? '<div style="font-size:0.65rem;color:var(--muted)">\u2026+' + (skill._children.length - 4) + ' more</div>' : '')
      : '') +
      (skill._groupSize > 1 ?
        '<div class="lb-tt-row"><span class="lb-tt-label">Group</span><span class="lb-tt-value">' + skill._groupSize + ' skills (' + skill.grade + ' · TM ' + Math.round(skill.trustMagnitude) + ')</span></div>' +
        '<div class="lb-tt-row" style="flex-direction:column;align-items:flex-start;gap:2px">' +
          (skill._groupMembers || []).slice(0, 5).map(function(mid) {
            return '<span style="font-family:var(--font-mono);font-size:0.65rem;color:var(--muted);opacity:0.8">' + esc(mid) + '</span>';
          }).join('') +
          (skill._groupMembers && skill._groupMembers.length > 5 ? '<span style="font-size:0.65rem;color:var(--muted)">…and ' + (skill._groupMembers.length - 5) + ' more</span>' : '') +
        '</div>'
      : '') +
      '<div class="lb-tt-divider"></div>' +
      '<span class="lb-tt-link">\u2192 View in Explorer</span>';
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
    return str.length > max ? str.slice(0, max) + '\u2026' : str;
  }

  function esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

})();

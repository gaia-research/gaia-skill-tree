/**
 * evidence-library.js — controller for the Evidence Library page.
 * Fetches gaia.json and named/index.json, flattens evidence sources,
 * renders stats, doughnut chart, search, filters, and collapsible groups.
 */
(function () {
  let allEntries = [];
  let allTypes = []; // ordered list of types present in data (by count desc)
  let currentFilters = {
    search: '',
    type: 'all',
    grade: 'all',
    sort: 'grade-desc'
  };

  // Keep track of user's explicit collapse overrides
  const collapsedGroups = new Set();
  const expandedGroups = new Set();

  const evStatsEl = document.getElementById('evStats');
  const evChartEl = document.getElementById('evChart');
  const evChartLegendEl = document.getElementById('evChartLegend');
  const evIndexEl = document.getElementById('evIndex');
  const evTotalCountEl = document.getElementById('evTotalCount');

  // Input elements
  const searchInput = document.getElementById('evSearch');
  const typeTabs = document.getElementById('evTypeTabs');
  const gradeTabs = document.getElementById('evGradeTabs');
  const sortSelect = document.getElementById('evSort');

  // --- Type normalization: maps legacy aliases to canonical names ---
  function normalizeType(raw) {
    if (!raw) return 'repo-own';
    if (raw === 'repo') return 'repo-own';
    if (raw === 'github-stars') return 'github-stars-own';
    return raw;
  }

  // Human-readable label for a type
  function typeLabel(t) {
    const labels = {
      'fusion-recipe': 'fusion',
      'github-stars-own': 'stars',
      'proxy-containment': 'proxy',
      'verifier-attestation': 'verifier',
      'benchmark-result': 'benchmark',
      'arxiv': 'arxiv',
      'peer-review': 'peer-review',
      'repo-own': 'repo',
      'self-attestation': 'self',
      'social-signal': 'social'
    };
    return labels[t] || t;
  }

  // Format a number as k (e.g. 60300 → "60.3k")
  function formatK(n) {
    if (!n) return '';
    const num = parseFloat(n);
    if (isNaN(num)) return String(n);
    if (num >= 1000) return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'k';
    return String(num);
  }

  // Initialise Page
  init();

  async function init() {
    try {
      const version = window.GAIA_VERSION ? '?v=' + window.GAIA_VERSION : '';
      const [gaiaRes, namedRes] = await Promise.all([
        fetch('../graph/gaia.json' + version),
        fetch('../graph/named/index.json' + version)
      ]);

      if (!gaiaRes.ok || !namedRes.ok) {
        throw new Error('Failed to load registry data files.');
      }

      const gaia = await gaiaRes.json();
      const named = await namedRes.ok ? await namedRes.json() : { buckets: {} };

      processData(gaia, named);
      buildTypeFilterTabs();
      setupEventListeners();
      render();
    } catch (err) {
      console.error('Evidence Library init failed:', err);
      evIndexEl.innerHTML = `<div class="ev-empty-state" style="color: var(--honor-red);">Error loading evidence library data. Please try again later.</div>`;
    }
  }

  // Flatten and normalize evidence entries
  function processData(gaia, named) {
    const entries = [];
    const typeCounts = {};

    // 1. Process starless (generic) skills from gaia.json
    if (gaia.skills && Array.isArray(gaia.skills)) {
      gaia.skills.forEach(s => {
        if (s.evidence && Array.isArray(s.evidence)) {
          s.evidence.forEach(ev => {
            const normType = normalizeType(ev.type);
            typeCounts[normType] = (typeCounts[normType] || 0) + 1;
            entries.push({
              ...ev,
              type: normType,
              skillId: s.id,
              skillName: s.name,
              skillLevel: null,
              layer: 'starless'
            });
          });
        }
      });
    }

    // 2. Process named skills from named/index.json buckets
    if (named.buckets) {
      Object.values(named.buckets).forEach(bucket => {
        if (Array.isArray(bucket)) {
          bucket.forEach(ns => {
            if (ns.evidence && Array.isArray(ns.evidence)) {
              ns.evidence.forEach(ev => {
                const normType = normalizeType(ev.type);
                typeCounts[normType] = (typeCounts[normType] || 0) + 1;
                entries.push({
                  ...ev,
                  type: normType,
                  skillId: ns.id,
                  skillName: ns.name,
                  skillLevel: ns.level,
                  layer: 'named'
                });
              });
            }
          });
        }
      });
    }

    allEntries = entries;
    // Sort types by count descending
    allTypes = Object.entries(typeCounts)
      .sort((a, b) => b[1] - a[1])
      .map(([t]) => t);
  }

  // Build type filter tabs dynamically from allTypes
  function buildTypeFilterTabs() {
    if (!typeTabs) return;
    // Remove existing non-"all" tabs
    typeTabs.querySelectorAll('.ev-tab:not([data-type="all"])').forEach(t => t.remove());
    // Append one tab per type found in data
    allTypes.forEach(t => {
      const btn = document.createElement('button');
      btn.className = 'ev-tab';
      btn.setAttribute('data-type', t);
      btn.textContent = typeLabel(t);
      typeTabs.appendChild(btn);
    });
  }

  // Setup UI event listeners
  function setupEventListeners() {
    // Search input (debounced)
    let debounceTimeout;
    searchInput.addEventListener('input', function (e) {
      clearTimeout(debounceTimeout);
      debounceTimeout = setTimeout(() => {
        currentFilters.search = e.target.value.trim().toLowerCase();
        renderListOnly();
      }, 150);
    });

    // Type filter tabs
    typeTabs.addEventListener('click', function (e) {
      const tab = e.target.closest('.ev-tab');
      if (!tab) return;

      typeTabs.querySelectorAll('.ev-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      currentFilters.type = tab.getAttribute('data-type');
      renderListOnly();
    });

    // Grade filter tabs
    gradeTabs.addEventListener('click', function (e) {
      const tab = e.target.closest('.ev-tab');
      if (!tab) return;

      gradeTabs.querySelectorAll('.ev-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      currentFilters.grade = tab.getAttribute('data-grade');
      renderListOnly();
    });

    // Sort select change
    sortSelect.addEventListener('change', function (e) {
      currentFilters.sort = e.target.value;
      renderListOnly();
    });

    // Collapsible group click delegation
    evIndexEl.addEventListener('click', function (e) {
      const header = e.target.closest('.ev-group-header');
      if (!header) return;

      const groupEl = header.closest('.ev-group');
      if (!groupEl) return;

      const groupId = groupEl.getAttribute('data-group-id');
      const isCollapsed = groupEl.classList.toggle('collapsed');

      if (isCollapsed) {
        collapsedGroups.add(groupId);
        expandedGroups.delete(groupId);
      } else {
        expandedGroups.add(groupId);
        collapsedGroups.delete(groupId);
      }
    });
  }

  // Full render (Stats + Doughnut + List)
  function render() {
    renderStats();
    renderListOnly();
  }

  // Compute and render stats & SVG doughnut
  function renderStats() {
    evTotalCountEl.textContent = allEntries.length;

    // Grade counts (S, A, B, C, ungraded)
    const gradeCounts = { S: 0, A: 0, B: 0, C: 0, ungraded: 0 };
    // Type counts for top-3 stat cards
    const typeCounts = {};
    allEntries.forEach(ev => {
      const g = effectiveGrade(ev) || 'ungraded';
      if (gradeCounts[g] !== undefined) gradeCounts[g]++;
      typeCounts[ev.type] = (typeCounts[ev.type] || 0) + 1;
    });

    // Stat cards: total sources + top 3 types by count
    const topTypes = Object.entries(typeCounts).sort((a, b) => b[1] - a[1]).slice(0, 3);
    const typeDisplayNames = {
      'arxiv': 'arXiv Papers', 'peer-review': 'Peer-Reviewed', 'repo-own': 'Repositories',
      'github-stars-own': 'GitHub Stars', 'social-signal': 'Social Signal',
      'fusion-recipe': 'Fusion Recipes', 'verifier-attestation': 'Verifier Attests',
      'benchmark-result': 'Benchmarks', 'proxy-containment': 'Proxy Contained',
      'self-attestation': 'Self-Attested',
    };

    evStatsEl.innerHTML = [
      `<div class="ev-stat-card">
        <div class="ev-stat-num">${allEntries.length}</div>
        <div class="ev-stat-label">Total Evidence</div>
      </div>`,
      ...topTypes.map(([t, count]) => `
        <div class="ev-stat-card" style="cursor:pointer;" onclick="document.querySelector('[data-type=\\'${t}\\']') && document.querySelector('[data-type=\\'${t}\\']').click()">
          <div class="ev-stat-num">${count}</div>
          <div class="ev-stat-label">${typeDisplayNames[t] || t}</div>
        </div>`)
    ].join('');

    // Render horizontal bar chart
    evChartEl.innerHTML = generateGradeBarChart(gradeCounts);
    evChartLegendEl.innerHTML = renderLegend(gradeCounts);
  }

  // Filter, sort, group, and render evidence list
  function renderListOnly() {
    // 1. Filtering
    let filtered = allEntries.filter(ev => {
      // Search term
      if (currentFilters.search) {
        const s = currentFilters.search;
        const skillMatch = (ev.skillName || '').toLowerCase().includes(s) || (ev.skillId || '').toLowerCase().includes(s);
        const sourceMatch = (ev.source || '').toLowerCase().includes(s);
        const evalMatch = (ev.evaluator || '').toLowerCase().includes(s);
        const notesMatch = (ev.notes || '').toLowerCase().includes(s);
        if (!skillMatch && !sourceMatch && !evalMatch && !notesMatch) return false;
      }

      // Type filter (ev.type is already normalized)
      if (currentFilters.type !== 'all' && ev.type !== currentFilters.type) {
        return false;
      }

      // Grade filter
      if (currentFilters.grade !== 'all') {
        const g = effectiveGrade(ev) || 'ungraded';
        if (g !== currentFilters.grade) return false;
      }

      return true;
    });

    if (filtered.length === 0) {
      evIndexEl.innerHTML = `<div class="ev-empty-state">No evidence sources match the active filters.</div>`;
      return;
    }

    // 2. Grouping by Skill ID
    const groupsMap = {};
    filtered.forEach(ev => {
      if (!groupsMap[ev.skillId]) {
        groupsMap[ev.skillId] = {
          skillId: ev.skillId,
          skillName: ev.skillName,
          skillLevel: ev.skillLevel,
          layer: ev.layer,
          entries: [],
          maxGradeWeight: -1,
          maxDateStr: ''
        };
      }
      groupsMap[ev.skillId].entries.push(ev);
    });

    const gradeWeight = { 'S': 4, 'A': 3, 'B': 2, 'C': 1, 'ungraded': 0 };
    const groups = Object.values(groupsMap);

    // Compute aggregate group sorting parameters
    groups.forEach(g => {
      g.entries.forEach(ev => {
        const w = gradeWeight[effectiveGrade(ev) || 'ungraded'];
        if (w > g.maxGradeWeight) g.maxGradeWeight = w;

        const d = ev.date || '';
        if (d > g.maxDateStr) g.maxDateStr = d;
      });

      // Sort items within group by grade (high->low), date (newest), or host
      g.entries.sort((a, b) => {
        if (currentFilters.sort === 'grade-desc') {
          const wA = gradeWeight[a.grade || 'ungraded'];
          const wB = gradeWeight[b.grade || 'ungraded'];
          if (wA !== wB) return wB - wA;
          return (a.date || '').localeCompare(b.date || '');
        } else if (currentFilters.sort === 'date-desc') {
          return (b.date || '').localeCompare(a.date || '');
        } else {
          return (a.source || '').localeCompare(b.source || '');
        }
      });
    });

    // 3. Sort Groups
    groups.sort((a, b) => {
      if (currentFilters.sort === 'grade-desc') {
        if (a.maxGradeWeight !== b.maxGradeWeight) {
          return b.maxGradeWeight - a.maxGradeWeight;
        }
        return (a.skillName || '').localeCompare(b.skillName || '');
      } else if (currentFilters.sort === 'date-desc') {
        if (a.maxDateStr !== b.maxDateStr) {
          return b.maxDateStr.localeCompare(a.maxDateStr);
        }
        return (a.skillName || '').localeCompare(b.skillName || '');
      } else { // skill-az
        return (a.skillName || '').localeCompare(b.skillName || '');
      }
    });

    // 4. Render Groups HTML
    evIndexEl.innerHTML = groups.map(g => {
      // Check collapse state — default collapse if > 5 entries, unless explicitly expanded
      let isCollapsed = g.entries.length > 5;
      if (collapsedGroups.has(g.skillId)) isCollapsed = true;
      else if (expandedGroups.has(g.skillId)) isCollapsed = false;

      const badgeHtml = g.layer === 'named' && typeof window.rankBadge === 'function'
        ? window.rankBadge(g.skillLevel, { size: 'sm' })
        : '';

      const titleHtml = g.layer === 'named'
        ? `<span class="ev-group-title-named">${esc(g.skillName)}</span>`
        : `<span class="ev-group-title-generic">${esc(g.skillName)}</span>`;

      return `
        <div class="ev-group ${isCollapsed ? 'collapsed' : ''}" data-group-id="${esc(g.skillId)}">
          <div class="ev-group-header">
            <div class="ev-group-title">
              ${titleHtml}
              ${badgeHtml}
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <span class="ev-group-meta">${g.entries.length} source${g.entries.length > 1 ? 's' : ''}</span>
              <svg class="ico ev-group-toggle-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </div>
          </div>
          <div class="ev-group-body">
            <div class="se-ev-grid">
              ${g.entries.map(renderRow).join('')}
            </div>
          </div>
        </div>`;
    }).join('');
  }

  // Derive weighted artifact score (mirrors _deriveWeightedScore in skill-explorer.js).
  // ALWAYS uses the live formula. Returns null when no metric drivers — never falls back
  // to ev.trustNumber (which is unweighted legacy storage).
  function deriveWeightedScore(ev) {
    const TM = window.TM_CONFIG;
    if (!TM) return null;
    const t = TM.canonicalType(ev.type || '');
    const cfg = TM.TYPES[t];
    if (!cfg) return null;
    const d = cfg.describe(ev);
    if (!d || d.value == null) return null;
    const base = TM.applyCap(t, d.value);
    let score = base * cfg.weight;
    if (cfg.freshness && cfg.freshness.decayPerYear) {
      const lv = ev.lastVerified || ev.date || null;
      if (lv) {
        const ageYrs = (Date.now() - new Date(lv).getTime()) / (1000 * 365.25 * 24 * 3600);
        score *= Math.max(0, 1 - cfg.freshness.decayPerYear * ageYrs);
      }
    }
    if (t === 'social-signal') {
      score *= (ev.creatorMultiplier || 1.0) * (ev.engagementRatio || 1.0);
    }
    if (ev.layer === 'generic' || ev._layer === 'generic') {
      const im = { 'arxiv': 0.70, 'peer-review': 0.30, 'social-signal': 0.35,
                   'proxy-containment': 0.25, 'benchmark-result': 0.15 }[t];
      if (im) score *= im;
    }
    return Math.round(score * 10) / 10;
  }

  // Derive the effective display grade for an evidence row.
  // Delegates to TM_CONFIG.effectiveGrade (single source of truth in tm-config.js).
  function effectiveGrade(ev) {
    const TM = window.TM_CONFIG;
    if (!TM || !TM.effectiveGrade) return (ev.grade || '').toUpperCase().charAt(0) || '';
    return TM.effectiveGrade(ev, deriveWeightedScore(ev));
  }

  // Build (i) tooltip for a type pill — reads from TM_CONFIG
  function typePillTooltip(normType) {
    const TM = window.TM_CONFIG;
    if (!TM) return normType;
    const cfg = TM.TYPES[normType];
    if (!cfg) return normType;
    return cfg.label.toUpperCase() + ' evidence\nFormula: ' + cfg.formula +
      '\nweight ×' + cfg.weight +
      (cfg.cap != null ? '  ·  cap ' + cfg.cap : '') +
      (cfg.gradeCeiling ? '  ·  ceiling ' + cfg.gradeCeiling : '') +
      '\nSee: ' + ((TM.RFC && TM.RFC.types) || TM.RFC_BASE);
  }

  // Build (i) tooltip for MAG bar — shows full chain
  function magTooltip(ev, weighted) {
    const TM = window.TM_CONFIG;
    if (!TM) return 'Trust config unavailable.';
    const t = TM.canonicalType(ev.type || '');
    const cfg = TM.TYPES[t];
    if (!cfg) return ev.type || '';
    const lines = [cfg.label.toUpperCase() + ' · ' + cfg.formula, ''];
    const d = cfg.describe ? cfg.describe(ev) : null;
    if (d && d.value != null) {
      const capped = TM.applyCap(t, d.value);
      const capNote = cfg.cap != null && d.value > cfg.cap ? ' → capped at ' + cfg.cap : '';
      lines.push('base:         ' + d.expr + ' = ' + d.value.toFixed(2) + capNote);
      lines.push('× weight:     ' + cfg.weight);
      if (cfg.freshness && cfg.freshness.decayPerYear) {
        const lv = ev.lastVerified || ev.date || null;
        if (lv) {
          const a = (Date.now() - new Date(lv).getTime()) / (1000*365.25*24*3600);
          const ff = Math.max(0, 1 - cfg.freshness.decayPerYear * a);
          lines.push('× freshness:  ' + ff.toFixed(3) + '  (−' + Math.round(cfg.freshness.decayPerYear*100) + '%/yr; age ' + a.toFixed(1) + ' yrs)');
        } else {
          lines.push('× freshness:  1.00  (assumed — no date)');
        }
      } else { lines.push('× freshness:  1.00  (no decay)'); }
      if (t === 'social-signal') {
        lines.push('× creator:    ' + (ev.creatorMultiplier || 1.0).toFixed(2));
        lines.push('× engagement: ' + (ev.engagementRatio || 1.0).toFixed(2));
      }
      if (cfg.plateau) {
        if (cfg.plateau.maxRows === 1) lines.push('× plateau:    1.00  (max 1 row)');
        else lines.push('× plateau:    ' + cfg.plateau.factors.join(' / ') + '  (max ' + cfg.plateau.maxRows + ' rows)');
      }
      lines.push('');
      lines.push('= MAG ' + (weighted != null ? weighted.toFixed(1) : '—') + '  (pre-plateau approximation)');
    } else {
      lines.push('No metric drivers recorded for this row.');
      const hints = {
        'github-stars-own': 'stars (and skillCountInRepo)', 'proxy-containment': 'externalStars (≥10000)',
        'verifier-attestation': 'verifiers', 'benchmark-result': 'percentile (0–100)',
        'arxiv': 'citations', 'peer-review': 'reviewers',
        'repo-own': 'commits + contributors', 'self-attestation': '(flat 10 — no fields needed)',
        'social-signal': 'views (≥1000)', 'fusion-recipe': 'origins (or gradedOriginCount)',
      };
      lines.push('Add ' + (hints[t] || 'metric fields') + ' to compute a live score.');
    }
    lines.push('');
    if (ev.grade) lines.push("This row's grade: " + ev.grade);
    const gf = cfg.gradeFloors || {};
    const fs = ['S','A','B','C'].filter(g => gf[g] != null).map(g => g + '≥' + gf[g]);
    if (fs.length) lines.push('Row grade floors: ' + fs.join(' · '));
    if (cfg.gradeCeiling) lines.push('Type ceiling: ' + cfg.gradeCeiling);
    lines.push('');
    lines.push('Full methodology: ' + ((TM.RFC && TM.RFC[cfg.anchor || 'types']) || TM.RFC_BASE));
    return lines.join('\n');
  }

  // Freshness indicator (only for decay types)
  function freshnessHtml(ev, normType) {
    const decayRates = { 'benchmark-result': 0.5, 'social-signal': 0.5, 'peer-review': 0.125 };
    const rate = decayRates[normType];
    if (!rate) return '';
    const lv = ev.lastVerified || ev.date || null;
    if (!lv) return '<span class="se-ev-freshness se-ev-freshness--unverified" title="No date — freshness assumed 1.0">unverified</span>';
    const ageYrs = (Date.now() - new Date(lv).getTime()) / (1000 * 365.25 * 24 * 3600);
    const factor = Math.max(0, 1 - rate * ageYrs);
    if (factor < 0.75) {
      const pct = Math.round((1 - factor) * 100);
      return '<span class="se-ev-freshness se-ev-freshness--stale" title="Freshness ' + factor.toFixed(2) + ' (−' + pct + '% from age)">stale</span>';
    }
    return '<span class="se-ev-freshness se-ev-freshness--fresh" title="Freshness ' + factor.toFixed(2) + '">fresh</span>';
  }

  // Render a single evidence row as a mosaic card (matches se-ev-card pattern)
  function renderRow(ev) {
    const TM = window.TM_CONFIG;
    const normType = ev.type || 'repo-own';
    const typeLbl = typeLabel(normType);
    const shortSrc = formatUrl(ev.source || '');
    const gradeChar = (ev.grade || '').toUpperCase().charAt(0);
    const isUngraded = !gradeChar;

    // Type pill (i) tooltip
    const pillTip = typePillTooltip(normType);

    // Weighted MAG score + MAG bar grade colour
    const weighted = deriveWeightedScore(ev);
    const barGradeChar = effectiveGrade(ev);
    const barGrade = barGradeChar || 'none';
    const magDisplay = weighted != null
      ? (Number.isInteger(weighted) ? String(weighted) : weighted.toFixed(1))
      : '—';
    const magTip = magTooltip(ev, weighted);

    // Metrics chips — same as se-ev-card
    const chips = [];
    if (ev.stars)     chips.push('<span class="se-ev-metric">★ ' + formatK(ev.stars) + '</span>');
    if (ev.views)     chips.push('<span class="se-ev-metric">👁 ' + formatK(ev.views) + '</span>');
    if (ev.citations) chips.push('<span class="se-ev-metric">📄 ' + ev.citations + ' cit.</span>');
    if (ev.reviewers) chips.push('<span class="se-ev-metric">' + ev.reviewers + ' reviewers</span>');
    if (ev.commits)   chips.push('<span class="se-ev-metric">' + ev.commits + ' commits</span>');
    const metricsHtml2 = chips.length ? '<div class="se-ev-metrics">' + chips.join('') + '</div>' : '';

    // Notes
    const notesHtml2 = ev.notes ? '<div class="se-ev-notes">' + esc(ev.notes) + '</div>' : '';

    // Fusion origins
    let originsHtml = '';
    if (normType === 'fusion-recipe' && Array.isArray(ev.origins) && ev.origins.length) {
      const chips2 = ev.origins.slice(0, 12).map(o => {
        const slug = o.indexOf('/') !== -1 ? o.split('/').pop() : o;
        return '<span class="se-ev-origin-chip" title="' + esc(o) + '">/' + esc(slug) + '</span>';
      });
      if (ev.origins.length > 12) chips2.push('<span class="se-ev-origin-chip" style="opacity:0.5">+' + (ev.origins.length - 12) + ' more</span>');
      originsHtml = '<div class="se-ev-origins"><span class="se-ev-origins-label">Origins (' + ev.origins.length + ')</span><div class="se-ev-origins-chips">' + chips2.join('') + '</div></div>';
    }

    // Evaluator
    const evalStr = ev.evaluator && ev.evaluator !== 'unknown' && ev.evaluator !== 'claude' && ev.evaluator !== 'system'
      ? '<span class="se-ev-eval">@' + esc(ev.evaluator) + '</span>' : '';

    // Freshness
    const freshHtml = freshnessHtml(ev, normType);

    // Layer hint
    const layerHtml = ev.layer === 'generic' || ev.layer === 'starless'
      ? '<span class="se-ev-layer-hint" title="From generic/starless layer">via generic</span>' : '';

    const cardClass = 'se-ev-card' + (isUngraded ? ' se-ev-card--ungraded' : '')
      + (metricsHtml2 || notesHtml2 || originsHtml ? ' se-ev-card--wide' : '');

    return `<div class="${cardClass}">` +
      '<div class="se-ev-card-body">' +
        '<div class="se-ev-card-top">' +
          '<span class="ev-type-pill type-' + normType + '">' + esc(typeLbl) +
            '<button class="ev-type-pill-info" type="button" title="' + esc(pillTip) + '" aria-label="' + esc(normType) + ' info">i</button>' +
          '</span>' +
          '<a class="se-ev-link" href="' + esc(ev.source || '#') + '" target="_blank" rel="noopener" title="' + esc(ev.source || '') + '">' + esc(shortSrc) + '</a>' +
          layerHtml +
        '</div>' +
        '<div class="se-ev-card-meta">' +
          evalStr +
          (ev.date ? '<span class="se-ev-date">' + esc(ev.date) + '</span>' : '') +
          freshHtml +
        '</div>' +
        notesHtml2 +
        metricsHtml2 +
        originsHtml +
      '</div>' +
      '<div class="se-ev-mag-bar" data-trust-grade="' + barGrade + '">' +
        '<span class="se-ev-mag-label">MAG <span class="se-ev-mag-num">' + esc(magDisplay) + '</span></span>' +
        (weighted != null ? '<button class="se-ev-mag-info" type="button" title="' + esc(magTip) + '" aria-label="Score details">i</button>' : '') +
      '</div>' +
    '</div>';
  }

  // Generates labeled horizontal bar chart (one row per grade, wide bars)
  function generateGradeBarChart(dataMap) {
    const grades = ['S', 'A', 'B', 'C', 'ungraded'];
    const total = Object.values(dataMap).reduce((a, b) => a + b, 0);
    if (total === 0) return '';
    const maxCount = Math.max(...grades.map(g => dataMap[g] || 0));
    const gradeNames = { S: 'Platinum', A: 'Gold', B: 'Silver', C: 'Bronze', ungraded: 'Ungraded' };

    const rows = grades.map(grade => {
      const count = dataMap[grade] || 0;
      if (count === 0 && grade === 'ungraded') return '';
      const barPct = maxCount > 0 ? (count / maxCount) * 100 : 0;
      const ofTotal = total > 0 ? Math.round((count / total) * 100) : 0;
      const gradeClass = grade === 'S' ? 'plat' : (grade === 'A' ? 'gold' : (grade === 'B' ? 'silver' : (grade === 'C' ? 'bronze' : 'ungraded')));
      return `
        <div class="ev-hbar-row" style="cursor:pointer;" onclick="document.querySelector('[data-grade=\\'${grade}\\']') && document.querySelector('[data-grade=\\'${grade}\\']').click()">
          <div class="ev-hbar-label">${gradeNames[grade]}</div>
          <div class="ev-hbar-track">
            <div class="ev-hbar-fill grade-segment grade-${gradeClass}" style="width:${barPct}%;"></div>
          </div>
          <div class="ev-hbar-count">${count} <span class="ev-hbar-pct">(${ofTotal}%)</span></div>
        </div>`;
    }).join('');

    return `<div class="ev-hbar-chart">${rows}</div>`;
  }

  // Generates Legend Table
  function renderLegend(dataMap) {
    const labels = {
      'S': 'Platinum (S)',
      'A': 'Gold (A)',
      'B': 'Silver (B)',
      'C': 'Bronze (C)',
      'ungraded': 'Ungraded'
    };
    const total = Object.values(dataMap).reduce((a, b) => a + b, 0);

    return ['S', 'A', 'B', 'C', 'ungraded'].map(grade => {
      const count = dataMap[grade] || 0;
      if (count === 0 && grade === 'S') return '';
      const pct = total > 0 ? Math.round((count / total) * 100) : 0;
      const gradeClass = grade === 'S' ? 'plat' : (grade === 'A' ? 'gold' : (grade === 'B' ? 'silver' : (grade === 'C' ? 'bronze' : 'ungraded')));
      return `
        <div class="ev-legend-item">
          <span class="ev-legend-dot grade-segment grade-${gradeClass}" style="width:12px;height:12px;border-radius:3px;display:inline-block;"></span>
          <span class="ev-legend-text">${labels[grade]}: <strong>${count}</strong> (${pct}%)</span>
        </div>`;
    }).join('');
  }

  // Utility helpers
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatUrl(url) {
    if (!url) return '';
    try {
      let clean = url.replace(/^(https?:\/\/)?(www\.)?/, '');
      if (clean.length > 50) {
        clean = clean.substring(0, 22) + '…' + clean.substring(clean.length - 22);
      }
      return clean;
    } catch (e) {
      return url;
    }
  }
})();

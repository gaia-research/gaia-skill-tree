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
    allEntries.forEach(ev => {
      const g = ev.grade || 'ungraded';
      if (gradeCounts[g] !== undefined) gradeCounts[g]++;
    });

    // Stat cards: total + grade breakdown
    const gradeLabels = { S: 'Platinum (S)', A: 'Gold (A)', B: 'Silver (B)', C: 'Bronze (C)', ungraded: 'Ungraded' };
    const gradePills = ['S', 'A', 'B', 'C', 'ungraded'].filter(g => gradeCounts[g] > 0);

    evStatsEl.innerHTML = [
      `<div class="ev-stat-card">
        <div class="ev-stat-num">${allEntries.length}</div>
        <div class="ev-stat-label">Total Sources</div>
      </div>`,
      ...gradePills.map(g => {
        const gradeClass = g === 'S' ? 'plat' : (g === 'A' ? 'gold' : (g === 'B' ? 'silver' : (g === 'C' ? 'bronze' : 'ungraded')));
        return `<div class="ev-stat-card" style="cursor:pointer;" onclick="document.querySelector('[data-grade=\\'${g}\\']').click()">
          <div class="ev-stat-num grade-${gradeClass}" style="color:inherit;">${gradeCounts[g]}</div>
          <div class="ev-stat-label">${gradeLabels[g]}</div>
        </div>`;
      })
    ].join('');

    // Render Horizontal Bar Chart
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
        const g = ev.grade || 'ungraded';
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
        const w = gradeWeight[ev.grade || 'ungraded'];
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
            ${g.entries.map(renderRow).join('')}
          </div>
        </div>`;
    }).join('');
  }

  // Render a single evidence row
  function renderRow(ev) {
    const g = ev.grade || 'ungraded';
    const gradeLabel = g === 'ungraded' ? '—' : g;
    const gradeClass = g === 'S' ? 'plat' : (g === 'A' ? 'gold' : (g === 'B' ? 'silver' : (g === 'C' ? 'bronze' : 'ungraded')));
    const normType = ev.type || 'repo-own'; // already normalized in processData
    const typeLbl = typeLabel(normType);
    const cleanUrl = formatUrl(ev.source);

    // Trust number
    const trustHtml = ev.trustNumber != null
      ? `<span class="ev-trust-score">${ev.trustNumber}</span>`
      : `<span class="ev-trust-score ev-trust-score--empty">—</span>`;

    // Notes block if present
    let notesHtml = '';
    if (ev.notes) {
      notesHtml = `<div class="ev-notes-row">${esc(ev.notes)}</div>`;
    }

    // Metrics chips
    const chips = [];
    if (ev.stars)     chips.push(`<span class="ev-metric-chip">★ ${formatK(ev.stars)}</span>`);
    if (ev.views)     chips.push(`<span class="ev-metric-chip">👁 ${formatK(ev.views)}</span>`);
    if (ev.citations) chips.push(`<span class="ev-metric-chip">📄 ${ev.citations} cit.</span>`);
    if (ev.reviewers) chips.push(`<span class="ev-metric-chip">${ev.reviewers} reviewers</span>`);
    if (ev.commits)   chips.push(`<span class="ev-metric-chip">${ev.commits} commits</span>`);
    const metricsHtml = chips.length > 0
      ? `<div class="ev-metrics-row">${chips.join('')}</div>`
      : '';

    const evalHtml = ev.evaluator && ev.evaluator !== 'unknown' && ev.evaluator !== 'claude'
      ? `<a href="../u/${esc(ev.evaluator)}/" class="ev-eval-link">@${esc(ev.evaluator)}</a>`
      : `<span style="opacity: 0.6;">${esc(ev.evaluator || 'system')}</span>`;

    return `
      <div class="ev-row">
        <div class="ev-grade-col">
          <div class="ev-grade-pill grade-${gradeClass}" title="${g === 'ungraded' ? 'Ungraded' : 'Grade ' + g}">${esc(gradeLabel)}</div>
        </div>
        <div class="ev-type-col">
          <div class="ev-type-pill type-${normType}">${esc(typeLbl)}</div>
        </div>
        <div class="ev-source-col">
          <a class="ev-source-link" href="${esc(ev.source || '')}" target="_blank" rel="noopener noreferrer" title="${esc(ev.source || '')}">
            ${esc(cleanUrl)}
          </a>
        </div>
        <div class="ev-trust-col">
          ${trustHtml}
        </div>
        <div class="ev-eval-col">
          ${evalHtml}
        </div>
        <div class="ev-date-col">
          ${esc(ev.date || '—')}
        </div>
        ${metricsHtml}
        ${notesHtml}
      </div>`;
  }

  // Generates Premium Horizontal Stacked Bar Chart
  function generateGradeBarChart(dataMap) {
    const grades = ['S', 'A', 'B', 'C', 'ungraded'];
    const total = Object.values(dataMap).reduce((a, b) => a + b, 0);
    if (total === 0) return '';

    const segmentsHtml = grades.map(grade => {
      const count = dataMap[grade] || 0;
      if (count === 0) return '';
      const pct = (count / total) * 100;
      const gradeClass = grade === 'S' ? 'plat' : (grade === 'A' ? 'gold' : (grade === 'B' ? 'silver' : (grade === 'C' ? 'bronze' : 'ungraded')));
      return `<div class="ev-bar-segment grade-segment grade-${gradeClass}" style="width: ${pct}%;" title="${grade === 'ungraded' ? 'Ungraded' : 'Grade ' + grade}: ${count} (${Math.round(pct)}%)"></div>`;
    }).join('');

    return `
      <div class="ev-bar-chart">
        <div class="ev-bar-total-count">${total}</div>
        <div class="ev-bar-total-label">Total Sources</div>
        <div class="ev-bar-track">
          ${segmentsHtml}
        </div>
      </div>`;
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

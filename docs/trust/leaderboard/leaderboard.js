(function() {
  'use strict';

  // ── HOST-PAGE PATH RESOLUTION ──
  // Script can be sourced from any page depth (e.g. /index.html embeds it
  // inline, /trust/leaderboard/ is its native home). Compute the repo-root
  // prefix from the current document URL so fetches and icon refs resolve
  // correctly regardless of where we're mounted.
  var ROOT_PREFIX = (function() {
    var p = window.location.pathname.replace(/[^/]*$/, ''); // strip filename
    // /trust/leaderboard/ → ../../ ; /codex/foo/ → ../ ; / → ''
    var depth = p.split('/').filter(Boolean).length;
    return depth === 0 ? '' : new Array(depth + 1).join('../');
  })();

  // Rewrite every existing `<use href="../../assets/icons.svg#…">` in the
  // DOM to use the host-relative prefix. The home-page embed uses bare
  // `assets/icons.svg#…`; the standalone page uses `../../assets/…`.
  function normalizeIconRefs(root) {
    var uses = (root || document).querySelectorAll('use[href*="assets/icons.svg"]');
    for (var i = 0; i < uses.length; i++) {
      var u = uses[i];
      var h = u.getAttribute('href') || '';
      var frag = h.indexOf('#') !== -1 ? h.substring(h.indexOf('#')) : '';
      u.setAttribute('href', ROOT_PREFIX + 'assets/icons.svg' + frag);
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { normalizeIconRefs(document); });
  } else {
    normalizeIconRefs(document);
  }

  // ── CONFIGURATION ──
  var BASE = ROOT_PREFIX + 'api/v1/';
  var VER = window.GAIA_VERSION ? '?v=' + window.GAIA_VERSION : '';
  var BAR_W = 28; // legacy — kept for any downstream readers; charts now use computeBarMetrics()
  var BAR_GAP = 4;
  var CHART_H = 320;
  var SUITE_CHART_H = 380;
  var PAD = { top: 24, right: 24, bottom: 110, left: 54 };
  var INITIAL_BARS = 40;
  var TM_CEILING = 600;
  var SVG_NS = 'http://www.w3.org/2000/svg';

  var GRADE_ORDER = { S: 0, A: 1, B: 2, C: 3, ungraded: 9 };

  // RANK_NAMES is no longer a static lookup — rank words fork by branch at 4★+.
  // Use rankNameFor(level, node) everywhere instead of RANK_NAMES[level].
  // Kept as a legacy fallback map for 1★–3★ only (branch-agnostic range).
  var RANK_NAMES_SHARED = { '1★': 'Awakened', '2★': 'Named', '3★': 'Evolved' };

  // Derive the branch-aware rank word for a skill.
  // Requires window.GaiaSemantics (skill-semantics.js loaded before leaderboard.js).
  function rankNameFor(level, node) {
    var gs = (typeof window !== 'undefined' && window.GaiaSemantics);
    if (!gs) return RANK_NAMES_SHARED[level] || '';
    var branch = gs.branchOf(node || {});
    return gs.rankWord(level, branch);
  }

  // ── EVIDENCE TYPES (per-type TM filter tabs above Named chart) ──
  var EVIDENCE_TYPES = [
    { id: 'all',                  label: 'All' },
    { id: 'peer-review',          label: 'Peer review' },
    { id: 'repo-own',             label: 'Repo' },
    { id: 'github-stars-own',     label: 'Stars' },
    { id: 'social-signal',        label: 'Social' },
    { id: 'benchmark-result',     label: 'Benchmark' },
    { id: 'arxiv',                label: 'arXiv' },
    { id: 'verifier-attestation', label: 'Verifier' },
    { id: 'proxy-containment',    label: 'Proxy' },
    { id: 'fusion-recipe',        label: 'Fusion' },
    { id: 'self-attestation',     label: 'Self' }
  ];

  // Methodology body content (kept in sync with registry/schema/meta.json::evidence.types[].description)
  // TODO: keep this list in sync with registry/schema/meta.json::evidence.types[].description
  var TM_METHODOLOGY_BODY = [
    '<p>Trust Magnitude is the evidence-backed score behind every Named Skill — the aggregate of independent demonstrations across <strong>10 Evidence Types</strong>:</p>',
    '<ul class="lb-tm-types">',
      '<li><strong>peer-review</strong> — published in a peer-reviewed venue. Highest weight.</li>',
      '<li><strong>arxiv</strong> — preprint citation. Verified but unrefereed.</li>',
      '<li><strong>repo-own</strong> — the skill ships in its origin contributor\'s public repo.</li>',
      '<li><strong>github-stars-own</strong> — community signal on the origin repo.</li>',
      '<li><strong>benchmark-result</strong> — verified benchmark percentile score.</li>',
      '<li><strong>verifier-attestation</strong> — a 4★+ Verifier confirmed the demonstration.</li>',
      '<li><strong>proxy-containment</strong> — referenced inside a higher-rank Verifier\'s skill.</li>',
      '<li><strong>social-signal</strong> — independent third-party views/citations. Capped at 80.</li>',
      '<li><strong>fusion-recipe</strong> — appears as a fusion component in a higher Ultimate skill.</li>',
      '<li><strong>self-attestation</strong> — contributor\'s own claim. Lowest weight.</li>',
    '</ul>',
    '<p>The aggregate Trust Magnitude is the proportionally-capped sum across all types. See <a href="' + ROOT_PREFIX + 'codex/trust-methodology.html">Trust Methodology</a> for the full grading rubric and threshold table.</p>'
  ].join('');

  // Read-only access to a skill's per-type TM (falls back to aggregate when 'all')
  function tmForType(skill, type) {
    if (type === 'all' || !type) return skill.trustMagnitude || 0;
    var bd = skill.typeBreakdown;
    if (!bd) return 0;
    return bd[type] || 0;
  }

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

  // --rank-N-rgb are emitted by scripts/generateCssTokens.py (issue #868).
  // The triplet fallbacks stay as a defensive floor for the case where
  // tokens.css hasn't loaded yet; they mirror the canonical token values.
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

  // ── BRANCH COLOR PALETTE (Yggdrasil II) ──
  // Keyed by branch ('standard'|'suite'|'unique'), NOT by the dead enum
  // (basic/extra/unique/ultimate). Branch is READ from the emitted field via
  // GaiaSemantics.branchOf — never read from skill.type directly.
  // Token source: --tier-basic-rgb (56,189,248), --tier-fusion-rgb (245,158,11),
  //               --tier-unique-rgb (124,58,237). No hex literals (CI guard E7).
  var BRANCH_COLORS = {
    standard: { top: [56,  189, 248], bot: [30,  100, 160] },   // --tier-basic-rgb
    suite:    { top: [245, 158,  11], bot: [160,  90,   5] },   // --tier-fusion-rgb (gold)
    unique:   { top: [124,  58, 237], bot: [60,   25, 140] }    // --tier-unique-rgb (darker plaque)
  };

  // Grade accent cap colors (solid RGBA strings)
  var GRADE_CAP_COLOR = {
    S: 'rgba(200,220,255,0.9)',
    A: 'rgba(251,191,36,0.85)',
    B: 'rgba(148,163,184,0.7)',
    C: 'rgba(180,120,60,0.7)'
  };

  // Resolve branch color stops for a skill node.
  // node may carry .type and .suiteComponents; level is the star level.
  // Falls back to 'standard' when GaiaSemantics hasn't loaded yet.
  function typeColors(nodeOrType, level) {
    var branch = 'standard';
    var gs = (typeof window !== 'undefined' && window.GaiaSemantics);
    if (gs && nodeOrType && typeof nodeOrType === 'object') {
      branch = gs.branchOf(nodeOrType);
    } else if (typeof nodeOrType === 'string') {
      // Legacy path: caller passes a raw type string ('basic'/'fusion'/old enum)
      if (nodeOrType === 'fusion') branch = 'suite';
      else branch = 'standard';
    }
    return BRANCH_COLORS[branch] || BRANCH_COLORS.standard;
  }

  function rgbStr(arr) { return arr[0] + ',' + arr[1] + ',' + arr[2]; }

  // ── DYNAMIC LAYOUT HELPERS ──
  // Compute bar width + gap that adapts to bar count, viewport, and density.
  // gapRatio: gap = barW * gapRatio (e.g. 0.5 → gap is half the bar width).
  function computeBarMetrics(N, containerW, padL, padR, minBarW, maxBarW, gapRatio) {
    if (!N || N <= 0) return { barW: minBarW, gap: minBarW * gapRatio, totalW: padL + padR };
    var available = Math.max(40, containerW - padL - padR);
    var unit = available / N; // pitch per bar (bar + gap)
    var barW = Math.max(minBarW, Math.min(maxBarW, unit / (1 + gapRatio)));
    var gap = barW * gapRatio;
    var totalW = Math.ceil(N * (barW + gap) + padL + padR);
    return { barW: barW, gap: gap, totalW: totalW };
  }

  // Adaptive label rotation/size/truncation based on per-bar spacing.
  function labelStyleFor(barSpacing) {
    if (barSpacing >= 80) return { rotation: 0,   fontPx: 11, maxChars: 16 };
    if (barSpacing >= 40) return { rotation: -30, fontPx: 10, maxChars: 12 };
    if (barSpacing >= 20) return { rotation: -45, fontPx: 9,  maxChars: 9  };
    return { rotation: -60, fontPx: 8, maxChars: 6 };
  }

  // Compute the bottom padding needed under a chart given label rotation, font size, and stacked lines.
  function computeBottomPad(rotationDeg, labelLines, fontPx) {
    var rotated = Math.abs(Math.sin(rotationDeg * Math.PI / 180)) * fontPx * 14;
    return Math.ceil(rotated + labelLines * fontPx * 1.4 + 24);
  }

  // Resolve target container width — uses the actual panel element width when
  // available so embedded contexts (e.g. homepage #trust-preview with a
  // max-width:1180px wrapper) don't produce an SVG wider than the container.
  function chartContainerW() {
    var panel = document.querySelector('.lb-chart-panel');
    if (panel && panel.offsetWidth > 0) return panel.offsetWidth;
    var vw = (typeof window !== 'undefined' && window.innerWidth) || 1024;
    return Math.min(vw - 40, 1280);
  }

  // Emit a label <text> with optional rotation. Caller still calls truncLabel.
  function makeLabel(x, y, rotation, fontPx, extraAttrs) {
    var attrs;
    if (rotation === 0) {
      attrs = {
        x: x, y: y,
        'text-anchor': 'middle',
        'class': 'lb-axis-label lb-axis-label--name',
        'font-size': String(fontPx)
      };
    } else {
      var anchor = rotation < 0 ? 'end' : 'start';
      attrs = {
        x: 0, y: 0,
        transform: 'translate(' + x + ',' + y + ') rotate(' + rotation + ')',
        'text-anchor': anchor,
        'class': 'lb-axis-label lb-axis-label--name',
        'font-size': String(fontPx)
      };
    }
    if (extraAttrs) {
      Object.keys(extraAttrs).forEach(function(k) { attrs[k] = extraAttrs[k]; });
    }
    return svgEl('text', attrs);
  }

  // Blend handle hue into mid-stop for personality (very subtle)
  function blendHandleMid(top, hue) {
    // Convert hue to a soft RGB hint and average with the type top color at 20%
    var hr = Math.round(Math.sin((hue / 180) * Math.PI) * 30);
    var hg = Math.round(Math.cos((hue / 180) * Math.PI) * 20);
    var r = Math.min(255, Math.max(0, top[0] + hr));
    var g = Math.min(255, Math.max(0, top[1] + hg));
    var b = Math.min(255, Math.max(0, top[2]));
    return [r, g, b];
  }

  // ── BAR GRADIENT BUILDER ──
  // Unified: main fill = BRANCH color (bottom→top), mid-stop blends contributor handle hue.
  // `node` is the full skill object carrying the emitted .branch that branchOf reads.
  function buildBarGradientDef(svg, contributor, grade, level, node, id) {
    var hue = handleHue(contributor);
    var tc = typeColors(node, level);
    var stopBot = 'rgb(' + rgbStr(tc.bot) + ')';
    var mid = blendHandleMid(tc.top, hue);
    var stopMid = 'rgba(' + rgbStr(mid) + ',0.92)';
    var stopTop = 'rgb(' + rgbStr(tc.top) + ')';

    var defs = svg.querySelector('defs');
    if (!defs) { defs = svgEl('defs'); svg.insertBefore(defs, svg.firstChild); }

    var gradId = 'lb-grad-' + id;
    var grad = svgEl('linearGradient', { id: gradId, x1: '0', y1: '1', x2: '0', y2: '0' });
    appendStop(grad, '0%',   stopBot);
    appendStop(grad, '55%',  stopMid);
    appendStop(grad, '100%', stopTop);
    defs.appendChild(grad);
    return gradId;
  }

  // ── GRADE CAP HELPER ──
  // Appends a thin grade-accent rect on top of a bar.
  function appendGradeCap(parent, grade, x, y, w) {
    var capColor = GRADE_CAP_COLOR[grade];
    if (!capColor) return;
    var cap = svgEl('rect', {
      x: x, y: y, width: w, height: 5, rx: 2,
      fill: capColor,
      style: 'pointer-events:none'
    });
    parent.appendChild(cap);
  }

  // ── WATERMARK + UPDATED BADGE HELPERS ──
  // Watermark renders as an HTML overlay on the chart panel (NOT inside the
  // scrolling SVG). This keeps it anchored to the panel's top-right corner
  // and lets us use the same gold+white gradient as the nav logo.
  function appendWatermark(svg, totalW) {
    // No-op for SVG — the watermark lives on the panel as an HTML element.
    // Kept as a function so existing call sites stay valid.
  }

  // Insert a top-right HTML watermark into a chart panel (idempotent — replaces
  // any existing watermark in the same panel).
  function ensurePanelWatermark(panel) {
    if (!panel) return;
    var existing = panel.querySelector(':scope > .lb-panel-watermark');
    if (existing) existing.remove();
    var wm = document.createElement('div');
    wm.className = 'lb-panel-watermark';
    wm.setAttribute('aria-hidden', 'true');
    wm.innerHTML =
      '<svg class="lb-panel-watermark-seal" viewBox="0 0 64 64" aria-hidden="true">' +
      '<use href="' + ROOT_PREFIX + 'assets/icons.svg#seal-diamond"/></svg>' +
      '<span class="lb-panel-watermark-text">Gaia</span>';
    panel.appendChild(wm);
  }

  // "Updated YYYY-MM-DD" tag in apex-gold, top-left interior of each chart SVG.
  function appendUpdatedBadge(svg, dateStr) {
    if (!dateStr) return;
    var g = svgEl('g', { 'pointer-events': 'none', transform: 'translate(14, 22)' });
    var t = svgEl('text', {
      x: 0, y: 0,
      'font-family': 'var(--font-data)',
      'font-size': '10',
      'letter-spacing': '0.06em',
      style: 'fill: var(--apex-gold); opacity: 0.95; pointer-events: none',
      'font-weight': '600'
    });
    t.textContent = 'UPDATED ' + dateStr;
    g.appendChild(t);
    svg.appendChild(g);
  }

  // ── ORIGIN BADGE HELPER ──
  // Renders a small laurel-wreath glyph in the top-left interior of a bar to mark origin skills.
  // Anchored to (barX, barY, barW); badge sits inside the bar, never overlapping labels below.
  // Uses currentColor + color: var(--apex-gold) — red origin mark is deprecated (Yggdrasil II E4).
  function appendOriginBadge(parent, barX, barY, barW) {
    var size = Math.max(10, Math.min(14, barW * 0.45));
    var margin = 3;
    // Soft dark scrim behind the glyph so it stays legible against light bars
    var scrim = svgEl('circle', {
      cx: barX + margin + size / 2,
      cy: barY + margin + size / 2,
      r: String(size / 2 + 1.5),
      fill: 'rgba(0,0,0,0.45)',
      'pointer-events': 'none'
    });
    parent.appendChild(scrim);
    var u = document.createElementNS(SVG_NS, 'use');
    u.setAttribute('href', ROOT_PREFIX + 'assets/icons.svg#origin-badge');
    u.setAttribute('x', String(barX + margin));
    u.setAttribute('y', String(barY + margin));
    u.setAttribute('width', String(size));
    u.setAttribute('height', String(size));
    u.setAttribute('fill', 'currentColor');
    u.setAttribute('color', 'var(--apex-gold)');
    u.setAttribute('pointer-events', 'none');
    parent.appendChild(u);
  }

  // ── AVATAR WREATH HELPER ──
  // Renders the gold origin-wreath-gold.svg ring OVER a bar-chart avatar circle.
  // E3: every avatar on every bar chart is framed by the gold wreath, not just origin
  // skills — the wreath is the Yggdrasil II origin mark and applies universally.
  // Sized 112% of the avatar diameter so the laurel reads as a border ring (mirrors
  // the plaque.css pattern: inset:-6%; width:112%).
  function appendAvatarWreath(parent, cx, cy, r) {
    var wreathSize = r * 2.24; // 112% of diameter
    var wreathImg = svgEl('image', {
      href: ROOT_PREFIX + 'assets/origin-wreath-gold.svg',
      x: String(cx - wreathSize / 2),
      y: String(cy - wreathSize / 2),
      width: String(wreathSize),
      height: String(wreathSize),
      'pointer-events': 'none',
      preserveAspectRatio: 'xMidYMid meet'
    });
    parent.appendChild(wreathImg);
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
    grouped: true,
    searchContribs: [],
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
    suiteSkills: [],
    ledgerExpanded: false,
    ledgerRows: [],
    suitesExpanded: false,
    namedExpanded: false,
    genericExpanded: false,
    skillSearchQuery: '',
    evidenceType: 'all',
    tmMethodologyOpen: false,
    updatedDate: ''
  };

  function fetchJson(url) {
    return fetch(url).then(function(r) {
      if (!r.ok) throw new Error('Fetch failed: ' + url + ' (' + r.status + ')');
      return r.json();
    });
  }

  function fetchSkillPages() {
    return fetchJson(BASE + 'skills/index.json' + VER).then(function(firstPage) {
      var totalPages = Math.max(1, parseInt(firstPage.totalPages || 1, 10) || 1);
      if (totalPages === 1) return [firstPage];
      var rest = [];
      for (var pageNum = 2; pageNum <= totalPages; pageNum++) {
        var path = pageNum === 1 ? 'skills/index.json' : 'skills/page-' + pageNum + '.json';
        rest.push(fetchJson(BASE + path + VER));
      }
      return Promise.all(rest).then(function(otherPages) {
        return [firstPage].concat(otherPages);
      });
    });
  }

  // ── DATA FETCH (parallel) ──
  Promise.all([
    fetchJson(BASE + 'leaderboard.json' + VER),
    fetchSkillPages()
  ]).then(function(results) {
    boot(results[0], results[1]);
  }).catch(function(err) {
    var page = document.querySelector('.lb-page');
    if (page) page.innerHTML = '<p style="padding:4rem 2rem;color:var(--muted);font-family:var(--font-body)">Failed to load leaderboard data.</p>';
    console.error('[leaderboard]', err);
  });

  function boot(leaderboard, skillPages) {
    // Build skill map
    var skillMap = {};
    (skillPages || []).forEach(function(page) {
      if (!page || !page.skills) return;
      page.skills.forEach(function(s) { skillMap[s.id] = s; });
    });

    // Stamp the "Updated" date (apex-gold tag in every chart).
    if (leaderboard.generatedAt) {
      state.updatedDate = leaderboard.generatedAt.slice(0, 10); // YYYY-MM-DD
    }

    // Enrich leaderboard rows
    // NOTE: the API JSON may still carry legacy `type` values (ultimate/extra/unique).
    // We normalize to valid schema types ('basic'/'fusion') and attach `_branch`
    // derived via GaiaSemantics.computeBranch so downstream code never reads
    // the dead enum (E1 compliance). suiteComponents from detail fetches later
    // may upgrade _branch to 'suite' via detectSuites.
    var gs = (typeof window !== 'undefined' && window.GaiaSemantics);
    var allRows = leaderboard.rows.map(function(row) {
      var skill = skillMap[row.id] || {};
      // Normalize legacy type strings to valid schema values
      var rawType = skill.type || 'basic';
      var normType = (rawType === 'fusion') ? 'fusion' : 'basic';
      return {
        id: row.id,
        name: skill.name || row.id.split('/')[1],
        contributor: row.id.split('/')[0],
        type: normType,
        suiteComponents: skill.suiteComponents || null,
        level: row.level || skill.level || '',
        trustMagnitude: row.trustMagnitude || 0,
        grade: row.grade || skill.overallTrustGrade || 'ungraded',
        origin: row.origin === true,
        typeBreakdown: row.typeBreakdown || null
      };
    });

    // Partition using branch semantics (never dead enum).
    // Suites are discovered later by detectSuites (detail fetches); initial
    // partition splits by whether the skill has suiteComponents in the index.
    var ultimates = allRows.filter(function(r) {
      return gs ? gs.branchOf(r) === 'suite' : false;
    });
    var extras = [];  // extra branch folded into suites under Yggdrasil II
    var basics = allRows.filter(function(r) {
      if (!gs) return true;
      var br = gs.branchOf(r);
      return br === 'standard' || br === 'unique';
    });
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
    renderNamedDistBar(leaderboard.distribution);
    renderTypeTabs();
    // renderUltimateChart(ultimates); // disabled — Suites section supersedes
    renderNamedChart(named);
    renderTrustMethodologyAccordion();
    renderRegistry(ungraded);
    buildStarlessChart(allRows);
    wireFilters(named);
    wireShowMore();
    wireTooltip();
    wireActionButtons();
    wireContribSearch();
    wireSkillSearch();
    renderLedger();

    // Fetch ultimate component details for stacked bars
    fetchUltimateComponents(ultimates);

    // Detect suites (skills with suiteComponents) via detail fetches
    detectSuites(allRows, skillMap);

    // Sticky TOC active-state observer
    wireTocObserver();
  }

  // ── STICKY TOC ──
  // Scroll-driven active state: the active section is the last one whose top
  // is above the viewport's 30% line. Robust across very tall sections (Named)
  // and very short ones (CTA/Registry) where IntersectionObserver thresholds
  // would otherwise miss the transition.
  function wireTocObserver() {
    var links = document.querySelectorAll('.lb-toc a');
    if (!links.length) return;
    var linkMap = {};
    var ids = [];
    links.forEach(function(a) {
      var id = a.getAttribute('data-toc');
      linkMap[id] = a;
      ids.push(id);
    });

    // Smooth scroll on click
    links.forEach(function(a) {
      a.addEventListener('click', function(e) {
        e.preventDefault();
        var id = a.getAttribute('data-toc');
        var target = document.getElementById(id);
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });

    function setActive(id) {
      links.forEach(function(a) { a.classList.remove('is-active'); });
      if (linkMap[id]) linkMap[id].classList.add('is-active');
    }

    function recompute() {
      var anchorY = window.innerHeight * 0.30; // activation line ~30% from top
      var current = ids[0];
      for (var i = 0; i < ids.length; i++) {
        var el = document.getElementById(ids[i]);
        if (!el) continue;
        var rect = el.getBoundingClientRect();
        if (rect.top - anchorY <= 0) {
          current = ids[i];
        } else {
          break;
        }
      }
      setActive(current);
    }

    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function() {
        recompute();
        ticking = false;
      });
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    recompute();
  }

  // ── DISTRIBUTION HEADER ──
  function renderDistribution(dist) {
    var el = document.getElementById('lbDist');
    if (!el) return;
    var segs = [
      { grade: 'S', count: dist.S || 0 },
      { grade: 'A', count: dist.A || 0 },
      { grade: 'B', count: dist.B || 0 },
      { grade: 'C', count: dist.C || 0 },
      { grade: 'ungraded', count: dist.ungraded || 0 }
    ];
    var total = segs.reduce(function(s, x) { return s + x.count; }, 0) || 1;
    // SVG donut — circumference = 2πr, dasharray slices encode each segment.
    var R = 38, CX = 50, CY = 50, STROKE = 14;
    var C = 2 * Math.PI * R;
    var offset = 0;
    var arcs = segs.map(function(seg) {
      if (!seg.count) return '';
      var len = (seg.count / total) * C;
      var dasharray = len + ' ' + (C - len);
      // Stagger animation: rotate via dashoffset so the slice "draws in".
      var dashoffset = -offset;
      var node = '<circle cx="' + CX + '" cy="' + CY + '" r="' + R + '"' +
        ' fill="none" stroke-width="' + STROKE + '" stroke-linecap="butt"' +
        ' data-trust-grade="' + seg.grade + '"' +
        ' class="lb-donut-arc lb-donut-arc--' + seg.grade + '"' +
        ' stroke-dasharray="' + dasharray + '"' +
        ' stroke-dashoffset="' + dashoffset + '"' +
        ' transform="rotate(-90 ' + CX + ' ' + CY + ')">' +
        '<title>' + seg.grade.toUpperCase() + ': ' + seg.count + ' skills (' +
        ((seg.count / total) * 100).toFixed(1) + '%)</title></circle>';
      offset += len;
      return node;
    }).join('');

    var legendItems = segs.map(function(seg) {
      if (!seg.count) return '';
      var pct = ((seg.count / total) * 100).toFixed(0);
      return '<li class="lb-donut-legend-item" data-trust-grade="' + seg.grade + '">' +
        '<span class="lb-donut-swatch" aria-hidden="true"></span>' +
        '<span class="lb-donut-legend-grade">' + (seg.grade === 'ungraded' ? 'Ungraded' : seg.grade) + '</span>' +
        '<span class="lb-donut-legend-count">' + seg.count + '</span>' +
        '<span class="lb-donut-legend-pct">' + pct + '%</span>' +
        '</li>';
    }).join('');

    el.innerHTML =
      '<div class="lb-donut-wrap">' +
        '<svg class="lb-donut" viewBox="0 0 100 100" aria-label="Grade distribution donut" role="img">' +
          '<defs>' +
            '<pattern id="lbDonutTextureS" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">' +
              '<rect width="6" height="6" fill="var(--evidence-platinum)"/>' +
              '<line x1="0" y1="0" x2="0" y2="6" stroke="rgba(255,255,255,0.18)" stroke-width="1"/>' +
            '</pattern>' +
            '<pattern id="lbDonutTextureA" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(0)">' +
              '<rect width="5" height="5" fill="var(--evidence-gold)"/>' +
              '<circle cx="2.5" cy="2.5" r="0.6" fill="rgba(0,0,0,0.25)"/>' +
            '</pattern>' +
            '<pattern id="lbDonutTextureB" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(90)">' +
              '<rect width="4" height="4" fill="var(--evidence-silver)"/>' +
              '<line x1="0" y1="2" x2="4" y2="2" stroke="rgba(255,255,255,0.22)" stroke-width="0.6"/>' +
            '</pattern>' +
            '<pattern id="lbDonutTextureC" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(-45)">' +
              '<rect width="6" height="6" fill="var(--evidence-bronze)"/>' +
              '<line x1="0" y1="3" x2="6" y2="3" stroke="rgba(0,0,0,0.2)" stroke-width="0.6"/>' +
            '</pattern>' +
          '</defs>' +
          // Track ring
          '<circle cx="' + CX + '" cy="' + CY + '" r="' + R + '" fill="none"' +
            ' stroke="rgba(var(--evidence-silver-rgb), 0.08)" stroke-width="' + STROKE + '"/>' +
          arcs +
          '<text x="50" y="48" text-anchor="middle" class="lb-donut-total">' + total + '</text>' +
          '<text x="50" y="60" text-anchor="middle" class="lb-donut-total-label">skills</text>' +
        '</svg>' +
        '<ul class="lb-donut-legend">' + legendItems + '</ul>' +
      '</div>';
  }

  // ── NAMED DISTRIBUTION BAR (replaces tab row) ──
  // Renders BAR-STYLED filter chips — each chip carries a mini vertical bar
  // sized to its share of total, in its grade color. Matches the chart aesthetic.
  function renderNamedDistBar(dist) {
    var el = document.getElementById('lbNamedDist');
    if (!el) return;
    var total = Math.max(1, (dist.S || 0) + (dist.A || 0) + (dist.B || 0) + (dist.C || 0));
    var segments = [
      { grade: 'S', count: dist.S || 0 },
      { grade: 'A', count: dist.A || 0 },
      { grade: 'B', count: dist.B || 0 },
      { grade: 'C', count: dist.C || 0 }
    ];
    var maxCount = Math.max.apply(null, segments.map(function(s) { return s.count; })) || 1;

    var keys = '<div class="lb-bar-filter">' +
      [{ grade: 'all', label: 'All', count: total }]
      .concat(segments.map(function(s) { return { grade: s.grade, label: s.grade, count: s.count }; }))
      .map(function(seg) {
        var active = (seg.grade === state.grade) ? ' is-active' : '';
        var tg = ' data-trust-grade="' + seg.grade + '"';
        var pct = seg.grade === 'all' ? 100 : Math.round((seg.count / maxCount) * 100);
        return '<button type="button" class="lb-bar-chip lb-named-filter' + active + '" data-view="' + seg.grade + '"' + tg + '>' +
          '<span class="lb-bar-chip__bar" style="height:' + pct + '%"></span>' +
          '<span class="lb-bar-chip__meta">' +
            '<span class="lb-bar-chip__count">' + seg.count + '</span>' +
            '<span class="lb-bar-chip__label">' + seg.label + '</span>' +
          '</span>' +
          '</button>';
      }).join('') +
    '</div>';

    el.innerHTML = keys;

    // Wire clicks — these buttons replace the old lb-stab tab row
    el.querySelectorAll('.lb-named-filter').forEach(function(btn) {
      btn.addEventListener('click', function() {
        state.grade = btn.dataset.view === 'all' ? 'all' : btn.dataset.view;
        state.showCount = INITIAL_BARS;
        el.querySelectorAll('.lb-named-filter').forEach(function(b) {
          b.classList.toggle('is-active', b === btn);
        });
        renderNamedChart(state.namedSkills);
        wireActionButtons();
      });
    });
  }

  // ── INLINE TRUST LEDGER ──
  var LEDGER_TRUNCATE = 20;

  function renderLedger() {
    fetch(ROOT_PREFIX + 'graph/ledger/data.json')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        state.ledgerRows = Array.isArray(data.rows) ? data.rows : [];
        renderLedgerTable();
        wireLedgerToggle();
        var countEl = document.getElementById('lbLedgerCount');
        if (countEl) countEl.textContent = state.ledgerRows.length + ' skills';
      })
      .catch(function() {
        var body = document.getElementById('lbLedgerBody');
        if (body) body.innerHTML = '<tr><td colspan="5" style="color:var(--muted);padding:1rem">Could not load ledger data.</td></tr>';
      });
  }

  function renderLedgerTable() {
    var body = document.getElementById('lbLedgerBody');
    if (!body || !state.ledgerRows.length) return;
    var rows = state.ledgerExpanded ? state.ledgerRows : state.ledgerRows.slice(0, LEDGER_TRUNCATE);
    body.innerHTML = rows.map(function(r, i) {
      var grade = r.grade || 'ungraded';
      var gradeKey = grade === 'ungraded' ? 'none' : grade;
      var stars = r.juneStars || r.currentStars || '?';
      return '<tr data-trust-grade="' + esc(gradeKey) + '">' +
        '<td class="col-rank">' + (i + 1) + '</td>' +
        '<td class="col-id"><a href="' + ROOT_PREFIX + 'named/#explorer/' + esc(r.skillId) + '">' + esc(r.skillId) + '</a></td>' +
        '<td class="col-tm"><span class="lb-tm-num">' + (typeof r.tm === 'number' ? r.tm.toFixed(1) : r.tm) + '</span></td>' +
        '<td class="col-grade"><span class="lb-grade-pill" data-trust-grade="' + esc(gradeKey) + '">' + (grade === 'ungraded' ? '\u2014' : grade) + '</span></td>' +
        '<td class="col-stars">' + esc(stars) + '</td>' +
      '</tr>';
    }).join('');
  }

  function wireLedgerToggle() {
    var btn = document.getElementById('lbLedgerToggle');
    var wrap = document.getElementById('lbLedgerWrap');
    if (!btn) return;
    btn.addEventListener('click', function() {
      state.ledgerExpanded = !state.ledgerExpanded;
      btn.textContent = state.ledgerExpanded ? 'Collapse \u25b4' : 'Show full table \u25be';
      if (wrap) wrap.classList.toggle('is-expanded', state.ledgerExpanded);
      renderLedgerTable();
    });
  }

  // ── ULTIMATE STACKED BAR CHART ──
  function renderUltimateChart(ultimates) {
    var container = document.getElementById('lbUltimateChart');
    var countEl = document.getElementById('lbUltimateCount');
    if (!container) return;
    if (countEl) countEl.textContent = ultimates.length + ' of ' + ultimates.length + ' ultimates';
    var gs = (typeof window !== 'undefined' && window.GaiaSemantics);

    var SPAD = { top: 24, right: 24, bottom: 0, left: 54 }; // bottom computed below
    var maxTM = TM_CEILING;

    // Fix 1: dynamic bar metrics for ultimates — wide bars, generous gap.
    var metrics = computeBarMetrics(ultimates.length, chartContainerW(), SPAD.left, SPAD.right, 24, 56, 0.6);
    var UB = metrics.barW;
    var UG = metrics.gap;
    var barSpacing = UB + UG;

    // Fix 2: adaptive label style
    var ls = labelStyleFor(barSpacing);

    // Fix 3: bottom padding for avatar + 3 label lines, accounting for rotation
    SPAD.bottom = computeBottomPad(ls.rotation, 3, ls.fontPx) + 44;

    var chartH = SUITE_CHART_H;
    var innerH = chartH - SPAD.top - SPAD.bottom;
    if (innerH < 80) innerH = 80;
    var totalW = Math.max(metrics.totalW, 320);

    var svg = createSvg(totalW, chartH);

    // Create defs block first
    var defs = svgEl('defs');
    svg.appendChild(defs);

    appendWatermark(svg, totalW);
    appendUpdatedBadge(svg, state.updatedDate);

    // Build per-bar gradients
    ultimates.forEach(function(ult, i) {
      buildBarGradientDef(svg, ult.contributor, ult.grade || 'S', ult.level, ult, 'ultimate-' + i);
    });

    // Y-axis gridlines
    drawYAxis(svg, innerH, maxTM, totalW);

    // Bars
    var barGroup = svgEl('g', { transform: 'translate(' + SPAD.left + ',' + SPAD.top + ')' });

    ultimates.forEach(function(ult, i) {
      var x = i * barSpacing;
      var h = (ult.trustMagnitude / maxTM) * innerH;
      var y = innerH - h;
      var gradId = 'lb-grad-ultimate-' + i;

      var bar = svgEl('rect', {
        x: x,
        y: y,
        width: UB,
        height: h,
        rx: 4,
        fill: 'url(#' + gradId + ')',
        'class': 'lb-bar lb-bar-animated',
        'data-id': ult.id,
        'data-type': 'suite',
        style: 'animation-delay:' + (i * 120) + 'ms'
      });
      barGroup.appendChild(bar);

      // Grade accent cap (metallic stripe at top of bar)
      appendGradeCap(barGroup, ult.grade || 'S', x, y, UB);

      // Fix 6: only render TM label when bar is tall enough
      if (h >= 30) {
        var tmText = svgEl('text', {
          x: x + UB / 2,
          y: y + h / 2 + 4,
          'text-anchor': 'middle',
          'class': 'lb-axis-value lb-axis-value--inbar',
          'font-size': String(Math.max(10, ls.fontPx + 1)),
          fill: 'rgba(255, 255, 255, 0.95)',
          'font-weight': '600',
          style: 'pointer-events:none'
        });
        tmText.textContent = ult.trustMagnitude.toFixed(0);
        barGroup.appendChild(tmText);
      }

      // Avatar — radius scales with bar width
      var avatarR = Math.min(14, Math.max(8, UB / 4));
      var avatarCx = x + UB / 2;
      var avatarCy = innerH + avatarR + 4;
      var clipId = 'av-clip-ultimate-' + i;
      var clipPath = svgEl('clipPath', { id: clipId });
      clipPath.appendChild(svgEl('circle', { cx: avatarCx, cy: avatarCy, r: String(avatarR) }));
      defs.appendChild(clipPath);

      // Fallback colored circle
      var hue = handleHue(ult.contributor);
      var bgCircle = svgEl('circle', {
        cx: avatarCx, cy: avatarCy, r: String(avatarR),
        fill: 'oklch(0.55 0.18 ' + hue + ')'
      });
      barGroup.appendChild(bgCircle);

      // GitHub avatar image
      var avatarImg = svgEl('image', {
        href: 'https://github.com/' + ult.contributor + '.png?size=40',
        x: avatarCx - avatarR, y: avatarCy - avatarR,
        width: String(avatarR * 2), height: String(avatarR * 2),
        'clip-path': 'url(#' + clipId + ')',
        preserveAspectRatio: 'xMidYMid slice'
      });
      barGroup.appendChild(avatarImg);

      // Gold origin-wreath-gold.svg ring — E3: every avatar is framed (Yggdrasil II)
      appendAvatarWreath(barGroup, avatarCx, avatarCy, avatarR);

      // Skill name label (adaptive)
      var labelY = innerH + avatarR * 2 + 14;
      var label = makeLabel(x + UB / 2, labelY, ls.rotation, ls.fontPx);
      truncLabel(label, ult.name || ult.id.split('/')[1], ls.maxChars);
      barGroup.appendChild(label);

      // Contributor handle below name label
      var rotatedExtra = Math.abs(Math.sin(ls.rotation * Math.PI / 180)) * ls.fontPx * 14;
      var contribY = labelY + rotatedExtra + ls.fontPx + 4;
      var contrib = svgEl('text', {
        x: x + UB / 2,
        y: contribY,
        'text-anchor': 'middle',
        'font-size': String(ls.fontPx),
        fill: 'rgba(' + TOKENS.gold + ', 0.7)'
      });
      truncLabel(contrib, ult.contributor, Math.max(8, ls.maxChars - 2));
      barGroup.appendChild(contrib);

      // Branch pill below contributor — use GaiaSemantics for correct rank word
      var ultBranch = gs ? gs.branchOf(ult) : 'suite';
      var ultPillWord = gs ? gs.rankWord(ult.level, ultBranch) : 'Suite';
      var typeBadge = svgEl('text', {
        x: x + UB / 2,
        y: contribY + ls.fontPx + 4,
        'text-anchor': 'middle',
        'font-size': String(Math.max(8, ls.fontPx - 1)),
        fill: 'rgba(' + TOKENS.gold + ', 0.7)'
      });
      typeBadge.textContent = ultPillWord;
      barGroup.appendChild(typeBadge);
    });

    svg.appendChild(barGroup);
    container.innerHTML = '';
    container.appendChild(svg);
    ensurePanelWatermark(container.closest('.lb-chart-panel'));
    // Action buttons above chart (outside scroll container)
    var existingActions = container.parentNode.querySelector(':scope > .lb-actions');
    if (existingActions) existingActions.remove();
    container.insertAdjacentHTML('beforebegin', buildActionButtons('ultimates'));

    // Ultimate stacked legend
    var legendHtml = '<div class="lb-legend">' +
      [2, 3, 4, 5].map(function(n) {
        var rgb = rankRgb(n);
        var word = rankNameFor(n + '\u2605', {});
        return '<span class="lb-legend-item">' +
          '<span class="lb-legend-swatch" style="background:rgba(' + rgb + ',0.7)"></span>' +
          n + '\u2605 ' + word +
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

    var SPAD = { top: 40, right: 24, bottom: 0, left: 54 }; // top: extra room for rank stars above bars
    var SCHART_H = 400;
    var maxTM = TM_CEILING;

    var visible = state.suitesExpanded ? suites : suites.slice(0, 8);

    // Fix 1: dynamic bar metrics for suites — beefy bars but cap so they don't bloat at low N.
    var metrics = computeBarMetrics(visible.length, chartContainerW(), SPAD.left, SPAD.right, 20, 40, 0.5);
    var SB = metrics.barW;
    var SG = metrics.gap;
    var barSpacing = SB + SG;

    // Fix 2: adaptive label style
    var ls = labelStyleFor(barSpacing);

    // Fix 3: bottom padding accommodates avatar (radius 16) + name label + contrib + type pill (3 lines)
    var labelLines = 3;
    SPAD.bottom = computeBottomPad(ls.rotation, labelLines, ls.fontPx) + 44;

    var innerH = SCHART_H - SPAD.top - SPAD.bottom;
    if (innerH < 80) innerH = 80;
    var totalW = Math.max(metrics.totalW, 320);
    var svg = createSvg(totalW, SCHART_H);

    var defs = svgEl('defs');
    svg.appendChild(defs);

    appendWatermark(svg, totalW);
    appendUpdatedBadge(svg, state.updatedDate);

    // Build per-bar gradients
    visible.forEach(function(suite, i) {
      buildBarGradientDef(svg, suite.contributor, suite.grade || 'A', suite.level, suite, 'suite-' + i);
    });

    // Y-axis
    drawYAxis(svg, innerH, maxTM, totalW);

    var barGroup = svgEl('g', { transform: 'translate(' + SPAD.left + ',' + SPAD.top + ')' });

    visible.forEach(function(suite, i) {
      var x = i * barSpacing;
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

      // Grade accent cap (metallic stripe at top of bar)
      appendGradeCap(barGroup, suite.grade || 'A', x, y, SB);

      // Rank stars — positioned ABOVE the bar top so they never obscure the
      // bar body or block hover. Clamped to a minimum Y so they stay visible
      // within the SVG viewport even for the tallest bars.
      var rankN = parseInt(suite.level) || 2;
      if (rankN > 0) {
        var starFontPx = Math.max(9, ls.fontPx);
        var starY = Math.max(-SPAD.top + starFontPx + 5, y - 6);
        var rankPill = svgEl('text', {
          x: x + SB / 2,
          y: starY,
          'text-anchor': 'middle',
          'font-size': String(starFontPx),
          'font-weight': '600',
          fill: 'rgba(' + rankRgb(rankN) + ', 0.95)',
          style: 'paint-order: stroke; stroke: rgba(0,0,0,0.55); stroke-width: 2px; stroke-linejoin: round; pointer-events: none'
        });
        rankPill.textContent = rankN + '\u2605';
        barGroup.appendChild(rankPill);
      }

      // Component count badge inside bar (near bottom)
      if (suite._componentCount > 0) {
        var badgeH = 18;
        var badgeW = Math.max(8, SB - 4);
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
          'font-family': 'var(--font-data)',
          style: 'pointer-events:none'
        });
        badgeText.textContent = suite._componentCount + ' skills';
        barGroup.appendChild(badgeText);
      }

      // TM value centered inside the bar (size scales with bar density)
      if (h >= 30) {
        var tmText = svgEl('text', {
          x: x + SB / 2, y: y + h / 2 + 4,
          'text-anchor': 'middle',
          'class': 'lb-axis-value lb-axis-value--inbar', 'font-size': String(Math.max(9, ls.fontPx + 1)),
          fill: 'rgba(255, 255, 255, 0.95)',
          'font-weight': '600',
          style: 'pointer-events:none'
        });
        tmText.textContent = suite.trustMagnitude.toFixed(0);
        barGroup.appendChild(tmText);
      }

      // Avatar — radius scales with bar width (clamped 10-16)
      var avatarR = Math.min(16, Math.max(10, SB / 2.4));
      var avatarCx = x + SB / 2;
      var avatarCy = innerH + avatarR + 4;
      var clipId = 'av-clip-suite-' + i;
      var clipPath = svgEl('clipPath', { id: clipId });
      var clipCircle = svgEl('circle', { cx: avatarCx, cy: avatarCy, r: String(avatarR) });
      clipPath.appendChild(clipCircle);
      defs.appendChild(clipPath);

      var hue = handleHue(suite.contributor);
      var bgCircle = svgEl('circle', {
        cx: avatarCx, cy: avatarCy, r: String(avatarR),
        fill: 'oklch(0.55 0.18 ' + hue + ')'
      });
      barGroup.appendChild(bgCircle);

      var avatarImg = svgEl('image', {
        href: 'https://github.com/' + suite.contributor + '.png?size=48',
        x: avatarCx - avatarR, y: avatarCy - avatarR,
        width: String(avatarR * 2), height: String(avatarR * 2),
        'clip-path': 'url(#' + clipId + ')',
        preserveAspectRatio: 'xMidYMid slice'
      });
      barGroup.appendChild(avatarImg);

      // Gold origin-wreath-gold.svg ring — E3: every avatar is framed (Yggdrasil II)
      appendAvatarWreath(barGroup, avatarCx, avatarCy, avatarR);

      // Origin laurel-wreath badge (pre-baked by C1) — top-left interior of bar
      if (suite.origin === true) {
        appendOriginBadge(barGroup, x, y, SB);
      }

      // Skill name label (slash-named form: contributor/skill, adaptive rotation/font/truncation)
      var labelY = innerH + avatarR * 2 + 14;
      var label = makeLabel(x + SB / 2, labelY, ls.rotation, ls.fontPx);
      truncLabel(label, suite.id || suite.name, Math.max(ls.maxChars, 14));
      barGroup.appendChild(label);

      // Contributor handle (placed below name label, with extra space if rotated)
      var rotatedExtra = Math.abs(Math.sin(ls.rotation * Math.PI / 180)) * ls.fontPx * 14;
      var contribY = labelY + rotatedExtra + ls.fontPx + 4;
      var contrib = svgEl('text', {
        x: x + SB / 2, y: contribY,
        'text-anchor': 'middle', 'font-size': String(ls.fontPx),
        fill: 'rgba(' + TOKENS.gold + ', 0.7)'
      });
      truncLabel(contrib, suite.contributor, Math.max(8, ls.maxChars - 2));
      barGroup.appendChild(contrib);

      // Branch pill — use GaiaSemantics.rankWord for branch-forked name, gold token for suite
      var gs = (typeof window !== 'undefined' && window.GaiaSemantics);
      var suiteBranch = gs ? gs.branchOf(suite) : 'suite';
      var suitePillWord = gs ? gs.rankWord(suite.level, suiteBranch) : 'Suite';
      var typePill = svgEl('text', {
        x: x + SB / 2, y: contribY + ls.fontPx + 4,
        'text-anchor': 'middle', 'font-size': String(Math.max(8, ls.fontPx - 1)),
        fill: suiteBranch === 'unique' ? 'rgba(' + TOKENS.rank4 + ',0.9)' : 'rgba(' + TOKENS.gold + ',0.9)'
      });
      typePill.textContent = suitePillWord;
      barGroup.appendChild(typePill);
    });

    svg.appendChild(barGroup);
    container.innerHTML = '';
    container.appendChild(svg);
    ensurePanelWatermark(container.closest('.lb-chart-panel'));
    // Inject action buttons above chart (outside scroll container)
    var existingActions = container.parentNode.querySelector('.lb-actions');
    if (existingActions) existingActions.remove();
    container.insertAdjacentHTML('beforebegin', buildActionButtons('suites'));

    // Add toggle button if there are more than 8 suites
    if (suites.length > 8) {
      var existing = document.getElementById('lbSuiteToggle');
      if (existing) existing.remove();
      var btn = document.createElement('button');
      btn.id = 'lbSuiteToggle';
      btn.className = 'lb-show-all-btn';
      btn.type = 'button';
      btn.innerHTML = state.suitesExpanded
        ? '<span>Show fewer</span><svg class="lb-show-all-icon" aria-hidden="true" viewBox="0 0 16 16"><path d="M3 10 L8 5 L13 10" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        : '<span>Show all <em>(' + suites.length + ')</em></span><svg class="lb-show-all-icon" aria-hidden="true" viewBox="0 0 16 16"><path d="M3 6 L8 11 L13 6" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      btn.addEventListener('click', function() {
        state.suitesExpanded = !state.suitesExpanded;
        renderSuiteChart(suites);
      });
      container.parentNode.insertBefore(btn, container.nextSibling);
    }

    // Update count to show '8 of 14 suites' when truncated
    var countEl = document.getElementById('lbSuiteCount');
    if (countEl) countEl.textContent = visible.length + (suites.length > visible.length ? ' of ' + suites.length : '') + ' suites';

    // Stacked overlay for suite components
    renderSuiteStackedOverlay(visible);
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

      // Keep the type-gradient bar visible with a slight transparency so the rank
      // segments inside are readable through it, then re-apply the grade cap on top.
      bar.setAttribute('opacity', '0.55');
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
        'data-type': 'suite',
        style: 'pointer-events: none;'
      });
      bar.parentNode.insertBefore(rect, bar.nextSibling);
    });

    // Keep the type-gradient bar visible with slight transparency so rank
    // segments inside are readable through it.
    bar.setAttribute('opacity', '0.55');
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
        origin: g.primary.origin,
        typeBreakdown: g.primary.typeBreakdown,
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

    var NPAD = { top: 40, right: 24, bottom: 0, left: 54 }; // top: extra room for rank stars above bars

    var visible = applyFilter(skills);
    var collapsed = state.grouped ? collapseGroups(visible) : visible;

    // Pagination: when dataset > 50, show 20 by default; "Show all" reveals rest.
    var PAGINATION_THRESHOLD = 50;
    var PAGINATION_INITIAL = 20;
    var needsPagination = collapsed.length > PAGINATION_THRESHOLD;
    var paginatedLimit = (needsPagination && !state.namedExpanded) ? PAGINATION_INITIAL : collapsed.length;
    var visibleCount = Math.min(state.showCount, paginatedLimit);

    var collapsedShown = collapsed.slice(0, visibleCount);
    var toShow = collapsedShown;
    var totalVisible = visible.length;
    var totalAll = skills.length;
    var groupedCount = visible.length - collapsed.length; // how many were collapsed away
    state.collapsedNamed = collapsed;

    if (countEl) {
      var countText = '(showing ' + collapsedShown.length + ' bars' +
        (groupedCount > 0 ? ', ' + groupedCount + ' grouped' : '') +
        ' of ' + totalVisible + ' skills)';
      if (state.searchContribs && state.searchContribs.length > 0) {
        countText += ' (filtered from ' + totalAll + ')';
      }
      if (state.skillSearchQuery) {
        countText += ' (search: \u201c' + state.skillSearchQuery + '\u201d)';
      }
      countEl.textContent = countText;
    }

    // Update AA-style X of Y counter
    var shownEl = document.getElementById('lbShownCount');
    var totalEl = document.getElementById('lbTotalCount');
    if (shownEl) shownEl.textContent = collapsedShown.length;
    if (totalEl) totalEl.textContent = totalVisible;

    updateShowMoreBtn(collapsedShown.length, Math.min(collapsed.length, paginatedLimit));

    if (toShow.length === 0) {
      container.innerHTML = '<p style="padding:2rem;color:var(--muted);font-family:var(--font-body);font-size:0.85rem">No skills match current filter.</p>';
      renderNamedPaginationBtn(container, collapsed.length, needsPagination);
      return;
    }

    // Fix 1: dynamic bar metrics
    var metrics = computeBarMetrics(toShow.length, chartContainerW(), NPAD.left, NPAD.right, 10, 24, 0.5);
    var NB = metrics.barW;
    var NG = metrics.gap;
    var barSpacing = NB + NG;

    // Fix 2: adaptive label style
    var ls = labelStyleFor(barSpacing);

    // Fix 3: dynamic bottom padding (skill name + avatar row above it)
    NPAD.bottom = computeBottomPad(ls.rotation, 1, ls.fontPx) + 36;

    var maxTM = Math.max.apply(null, toShow.map(function(s) { return tmForType(s, state.evidenceType); }));
    maxTM = Math.max(maxTM, 50); // floor

    // Dynamic chart height — under a type filter, scale height so the tallest
    // bar always fills ~75% of the chart, keeping bar density consistent across
    // tabs. CSS transition on .lb-chart-wrap eases the height change visually.
    var dynH = CHART_H;
    if (state.evidenceType && state.evidenceType !== 'all') {
      // Compare this type's max against the all-time TM ceiling (use full named
      // max as the reference). If filtered max is much smaller, shrink chart.
      var refMax = state._refMaxAll || (function() {
        var m = Math.max.apply(null, state.namedSkills.map(function(s) { return s.trustMagnitude || 0; }));
        state._refMaxAll = Math.max(m, 50);
        return state._refMaxAll;
      })();
      var ratio = Math.max(0.25, Math.min(1, maxTM / refMax));
      dynH = Math.round(220 + (CHART_H - 220) * Math.sqrt(ratio));
    }

    var totalW = Math.max(metrics.totalW, 320);
    var innerH = dynH - NPAD.top - NPAD.bottom;
    if (innerH < 80) innerH = 80;

    var svg = createSvg(totalW, dynH);

    // Create defs block first
    var defs = svgEl('defs');
    svg.appendChild(defs);

    appendWatermark(svg, totalW);
    appendUpdatedBadge(svg, state.updatedDate);

    // Build per-bar gradients
    toShow.forEach(function(skill, i) {
      buildBarGradientDef(svg, skill.contributor, skill.grade, skill.level, skill, 'named-' + i);
    });

    // Y-axis gridlines
    drawYAxis(svg, innerH, maxTM, totalW);

    // Fix 4: S/A/B/C background bands when grouped by grade
    if (state.grouped && state.sort === 'grade') {
      var bandsGroup = svgEl('g', { transform: 'translate(' + NPAD.left + ',' + NPAD.top + ')' });
      var prevGrade = null;
      var bandStartIdx = 0;
      var bi;
      for (bi = 0; bi <= toShow.length; bi++) {
        var bg = (bi < toShow.length) ? toShow[bi].grade : null;
        if (bg !== prevGrade && prevGrade != null) {
          var bandColor = gradeColor(prevGrade);
          var bx = bandStartIdx * barSpacing - NG / 2;
          var bw = (bi - bandStartIdx) * barSpacing;
          var bandRect = svgEl('rect', {
            x: bx, y: 0, width: bw, height: innerH,
            fill: 'rgba(' + bandColor + ', 0.04)',
            style: 'pointer-events:none'
          });
          bandsGroup.appendChild(bandRect);
          bandStartIdx = bi;
        }
        prevGrade = bg;
      }
      svg.appendChild(bandsGroup);
    }

    // Bar group
    var barGroup = svgEl('g', { transform: 'translate(' + NPAD.left + ',' + NPAD.top + ')' });

    toShow.forEach(function(skill, i) {
      var x = i * barSpacing;
      var tmVal = tmForType(skill, state.evidenceType);
      var h = Math.max(2, (tmVal / maxTM) * innerH);
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

      // Grade accent cap (metallic stripe at top of bar)
      appendGradeCap(barGroup, skill.grade, x, y, NB);

      // Group badge (only when multiple skills collapsed into this bar)
      if (skill._groupSize > 1) {
        var badgeH = 18;
        var badgeW = Math.max(8, NB - 2);
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
          'font-family': 'var(--font-data)',
          style: 'pointer-events:none'
        });
        badgeText.textContent = '+' + (skill._groupSize - 1);
        barGroup.appendChild(badgeText);
      }

      // Rank stars — positioned ABOVE the bar top so they never obscure the
      // bar body or block hover. Clamped to a minimum Y so they stay visible
      // within the SVG viewport even for the tallest bars.
      var rankN = parseInt(skill.level) || 2;
      if (rankN > 0) {
        var starFontPx = Math.max(9, ls.fontPx);
        // Place just above bar top; clamp so it doesn't leave the SVG viewport.
        var starY = Math.max(-NPAD.top + starFontPx + 5, y - 6);
        var rankPill = svgEl('text', {
          x: x + NB / 2,
          y: starY,
          'text-anchor': 'middle',
          'font-size': String(starFontPx),
          'font-weight': '600',
          fill: 'rgba(' + rankRgb(rankN) + ', 0.95)',
          style: 'paint-order: stroke; stroke: rgba(0,0,0,0.55); stroke-width: 2px; stroke-linejoin: round; pointer-events: none'
        });
        rankPill.textContent = rankN + '\u2605';
        barGroup.appendChild(rankPill);
      }

      // TM score centered inside bar (visible only when bar is tall enough to host the number)
      if (h >= 22) {
        var tmText = svgEl('text', {
          x: x + NB / 2,
          y: y + h / 2 + 4,
          'text-anchor': 'middle',
          'class': 'lb-axis-value lb-axis-value--inbar',
          'font-size': String(Math.max(8, ls.fontPx - 1)),
          style: 'pointer-events:none'
        });
        tmText.textContent = Math.round(tmVal);
        barGroup.appendChild(tmText);
      }

      // Avatar — radius scales with bar width
      var avatarR = Math.min(10, Math.max(5, NB / 2.4));
      var avatarCx = x + NB / 2;
      var avatarCy = innerH + avatarR + 4;

      var clipId = 'av-clip-named-' + i;
      var clipPath = svgEl('clipPath', { id: clipId });
      clipPath.appendChild(svgEl('circle', { cx: avatarCx, cy: avatarCy, r: String(avatarR) }));
      defs.appendChild(clipPath);

      // Fallback colored circle
      var hue = handleHue(skill.contributor);
      var bgCircle = svgEl('circle', {
        cx: avatarCx, cy: avatarCy, r: String(avatarR),
        fill: 'oklch(0.55 0.18 ' + hue + ')'
      });
      barGroup.appendChild(bgCircle);

      // GitHub avatar image
      var avatarImg = svgEl('image', {
        href: 'https://github.com/' + skill.contributor + '.png?size=40',
        x: avatarCx - avatarR, y: avatarCy - avatarR,
        width: String(avatarR * 2), height: String(avatarR * 2),
        'clip-path': 'url(#' + clipId + ')',
        preserveAspectRatio: 'xMidYMid slice'
      });
      barGroup.appendChild(avatarImg);

      // Gold origin-wreath-gold.svg ring — E3: every avatar is framed (Yggdrasil II)
      appendAvatarWreath(barGroup, avatarCx, avatarCy, avatarR);

      // Origin laurel-wreath badge (pre-baked by C1) — top-left interior of bar
      if (skill.origin === true) {
        appendOriginBadge(barGroup, x, y, NB);
      }

      // Skill name label (slash-named form: contributor/skill, adaptive rotation/font/truncation)
      var labelY = innerH + avatarR * 2 + 14;
      var label = makeLabel(x + NB / 2, labelY, ls.rotation, ls.fontPx);
      truncLabel(label, skill.id, Math.max(ls.maxChars, 14));
      barGroup.appendChild(label);
    });

    svg.appendChild(barGroup);
    container.innerHTML = '';
    container.appendChild(svg);
    ensurePanelWatermark(container.closest('.lb-chart-panel'));
    // Action buttons above chart (outside scroll container)
    var ea2 = container.parentNode.querySelector(':scope > .lb-actions');
    if (ea2) ea2.remove();
    container.insertAdjacentHTML('beforebegin', buildActionButtons('named'));

    renderNamedPaginationBtn(container, collapsed.length, needsPagination);
  }

  function renderNamedPaginationBtn(container, total, needsPagination) {
    var existing = document.getElementById('lbNamedPaginateBtn');
    if (existing) existing.remove();
    if (!needsPagination) return;
    var btn = document.createElement('button');
    btn.id = 'lbNamedPaginateBtn';
    btn.className = 'lb-show-all-btn';
    btn.type = 'button';
    btn.innerHTML = state.namedExpanded
      ? '<span>Show fewer</span><svg class="lb-show-all-icon" aria-hidden="true" viewBox="0 0 16 16"><path d="M3 10 L8 5 L13 10" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'
      : '<span>Show all <em>(' + total + ')</em></span><svg class="lb-show-all-icon" aria-hidden="true" viewBox="0 0 16 16"><path d="M3 6 L8 11 L13 6" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    btn.addEventListener('click', function() {
      state.namedExpanded = !state.namedExpanded;
      if (state.namedExpanded) state.showCount = total;
      renderNamedChart(state.namedSkills);
      wireActionButtons();
    });
    container.parentNode.insertBefore(btn, container.nextSibling);
  }

  // ── GENERIC/STARLESS SKILLS BAR CHART ──
  function renderGenericChart(nodes) {
    var container = document.getElementById('lbGenericChart');
    var countEl = document.getElementById('lbGenericCount');
    if (!container) return;

    var GPAD = { top: 28, right: 24, bottom: 0, left: 54 }; // bottom computed below
    var GCHART_H = 440;

    if (countEl) countEl.textContent = nodes.length + ' generic skills \u00B7 ' +
      nodes.reduce(function(s, n) { return s + (n._children ? n._children.length : 0); }, 0) + ' named implementations';

    if (!nodes.length) {
      container.innerHTML = '<p style="padding:2rem;color:var(--muted);font-size:0.82rem">No generic skills found.</p>';
      return;
    }

    // Fix 7: pagination — initial slice is smaller so each bar has room to breathe.
    var PAGINATION_THRESHOLD_GEN = 30;
    var PAGINATION_INITIAL_GEN = 12;
    var needsPaginationGen = nodes.length > PAGINATION_THRESHOLD_GEN;
    var allNodes = nodes;
    var displayNodes = (needsPaginationGen && !state.genericExpanded) ? nodes.slice(0, PAGINATION_INITIAL_GEN) : nodes;

    var maxTM = Math.max.apply(null, displayNodes.map(function(n) { return n.trustMagnitude || 0; }));
    maxTM = Math.max(maxTM, 10);

    // Fix 1: dynamic bar metrics — larger min bar width for readability
    var metrics = computeBarMetrics(displayNodes.length, chartContainerW(), GPAD.left, GPAD.right, 22, 56, 0.5);
    var GB = metrics.barW;
    var GG = metrics.gap;
    var barSpacing = GB + GG;

    // Fix 2: adaptive label style — bumped minimum font sizes for readability
    var ls = labelStyleFor(barSpacing);
    var childFontPx = Math.max(9, ls.fontPx - 1);
    var childMaxChars = Math.max(8, ls.maxChars - 2);
    var childLines = 4;

    // Fix 3: bottom padding = rotated name label + child label stack
    GPAD.bottom = computeBottomPad(ls.rotation, 1, ls.fontPx) + childLines * (childFontPx + 3) + 28;

    var totalW = Math.max(metrics.totalW, 320);
    var innerH = GCHART_H - GPAD.top - GPAD.bottom;
    if (innerH < 60) innerH = 60;
    var svg = createSvg(totalW, GCHART_H);

    var defs = svgEl('defs');
    svg.appendChild(defs);

    appendWatermark(svg, totalW);
    appendUpdatedBadge(svg, state.updatedDate);

    // Build gradients per node (muted, handle-hue based)
    displayNodes.forEach(function(node, i) {
      var hue = handleHue(node.contributor);
      var clipId = 'av-clip-gen-' + i;
      var cp = svgEl('clipPath', { id: clipId });
      cp.appendChild(svgEl('circle', { cx: 0, cy: 0, r: '8' }));
      defs.appendChild(cp);

      var gradId = 'lb-grad-gen-' + i;
      // Generic bars use the top child's branch color if available, else standard (basic)
      var genNode = (node._children && node._children[0]) || node;
      var gtc = typeColors(genNode, genNode.level);
      var genMid = blendHandleMid(gtc.top, hue);
      var grad = svgEl('linearGradient', { id: gradId, x1: '0', y1: '1', x2: '0', y2: '0' });
      appendStop(grad, '0%',   'rgb(' + rgbStr(gtc.bot) + ')');
      appendStop(grad, '55%',  'rgba(' + rgbStr(genMid) + ',0.92)');
      appendStop(grad, '100%', 'rgb(' + rgbStr(gtc.top) + ')');
      defs.appendChild(grad);
    });

    drawYAxis(svg, innerH, maxTM, totalW);
    var barGroup = svgEl('g', { transform: 'translate(' + GPAD.left + ',' + GPAD.top + ')' });

    displayNodes.forEach(function(node, i) {
      var x = i * barSpacing;
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

      // Child segments stacked inside the bar — each uses its own type color
      var children = node._children || [];
      if (children.length >= 1) {
        var usedH = 0;
        children.forEach(function(child, ci) {
          var segH = Math.max(1, (child.trustMagnitude / node.trustMagnitude) * h * 0.9);
          if (usedH + segH > h) segH = Math.max(1, h - usedH);
          var segY = y + h - usedH - segH;
          var segFill;
          var segStroke = null;
          if (child.origin) {
            // Origin child: apex-gold at 0.95 opacity + 1px white side strokes — canonical impl undeniable.
            segFill = 'rgba(' + TOKENS.gold + ', 0.95)';
            segStroke = 'rgba(255,255,255,0.85)';
          } else {
            var childTc = typeColors(child, child.level);
            segFill = 'rgba(' + rgbStr(childTc.top) + ',0.72)';
          }
          var segAttrs = {
            x: x + 2, y: segY, width: Math.max(1, GB - 4), height: Math.max(1, segH - 1), rx: 1,
            fill: segFill, opacity: '0.95', style: 'pointer-events:none'
          };
          if (segStroke) {
            segAttrs.stroke = segStroke;
            segAttrs['stroke-width'] = '1';
          }
          var seg = svgEl('rect', segAttrs);
          barGroup.appendChild(seg);
          usedH += segH;
        });
      }

      // Grade accent cap on generic bars (uses primary child grade)
      var primaryGrade = (node._children && node._children[0] && node._children[0].grade) || node.grade;
      if (primaryGrade && primaryGrade !== 'ungraded') {
        appendGradeCap(barGroup, primaryGrade, x, y, GB);
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
          'font-family': 'var(--font-data)', style: 'pointer-events:none'
        });
        badgeTxt.textContent = '+' + (children.length - 1);
        barGroup.appendChild(badgeTxt);
      }

      // (labels moved below: name first, then children)

      // Generic node name label (adaptive)
      var nameY = innerH + 14;
      var lbl2 = makeLabel(x + GB/2, nameY, ls.rotation, ls.fontPx);
      truncLabel(lbl2, node.name, ls.maxChars);
      barGroup.appendChild(lbl2);

      // Stacked contributor labels — below rotated name label.
      // Account for the FULL projection of a rotated multi-char label, then
      // pad an extra line-height so children never overlap the name tail.
      var rotatedLabelH = Math.abs(Math.sin(ls.rotation * Math.PI / 180)) * ls.fontPx * 18;
      var childStartY = nameY + rotatedLabelH + ls.fontPx + 8;

      // Origin laurel-wreath badge for parent generic node (pre-baked by C1) — top-left interior of bar
      if (node.origin === true) {
        appendOriginBadge(barGroup, x, y, GB);
      }

      var shownChildren = children.slice(0, 3);
      shownChildren.forEach(function(child, ci) {
        var lbl = svgEl('text', {
          x: x + GB/2,
          y: childStartY + (ci * (childFontPx + 3)),
          'text-anchor': 'middle',
          'font-size': String(childFontPx),
          fill: child.origin ? 'rgba(' + TOKENS.gold + ', 0.95)' : 'rgba(148,163,184,0.7)',
          'font-family': 'var(--font-data)'
        });
        lbl.textContent = truncate(child.contributor, childMaxChars) + (child.origin ? ' ◎' : '');
        barGroup.appendChild(lbl);
      });
      if (children.length > 3) {
        var moreLbl = svgEl('text', {
          x: x + GB/2,
          y: childStartY + (3 * (childFontPx + 3)),
          'text-anchor': 'middle', 'font-size': String(Math.max(6, childFontPx - 1)),
          fill: 'rgba(148,163,184,0.5)'
        });
        moreLbl.textContent = '+' + (children.length - 3) + ' more';
        barGroup.appendChild(moreLbl);
      }
    });

    svg.appendChild(barGroup);
    container.innerHTML = '';
    container.appendChild(svg);
    ensurePanelWatermark(container.closest('.lb-chart-panel'));
    // Action buttons above chart (outside scroll container)
    var ea3 = container.parentNode.querySelector(':scope > .lb-actions');
    if (ea3) ea3.remove();
    container.insertAdjacentHTML('beforebegin', buildActionButtons('generic'));

    renderGenericPaginationBtn(container, allNodes.length, needsPaginationGen);
  }

  function renderGenericPaginationBtn(container, total, needsPagination) {
    var existing = document.getElementById('lbGenericPaginateBtn');
    if (existing) existing.remove();
    if (!needsPagination) return;
    var btn = document.createElement('button');
    btn.id = 'lbGenericPaginateBtn';
    btn.className = 'lb-show-all-btn';
    btn.type = 'button';
    btn.innerHTML = state.genericExpanded
      ? '<span>Show fewer</span><svg class="lb-show-all-icon" aria-hidden="true" viewBox="0 0 16 16"><path d="M3 10 L8 5 L13 10" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'
      : '<span>Show all <em>(' + total + ')</em></span><svg class="lb-show-all-icon" aria-hidden="true" viewBox="0 0 16 16"><path d="M3 6 L8 11 L13 6" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    btn.addEventListener('click', function() {
      state.genericExpanded = !state.genericExpanded;
      renderGenericChart(state.starlessNodes);
      wireActionButtons();
    });
    container.parentNode.insertBefore(btn, container.nextSibling);
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
    // Filter graded named skills (exclude suites — they have their own chart)
    var gsRef = (typeof window !== 'undefined' && window.GaiaSemantics);
    var candidates = allRows.filter(function(r) {
      if (!r.grade || r.grade === 'ungraded') return false;
      if (!gsRef) return true;
      return gsRef.branchOf(r) !== 'suite';
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
            genericRefMap[ref].push({
              id: row.id,
              name: row.name,
              contributor: row.contributor,
              trustMagnitude: row.trustMagnitude,
              grade: row.grade,
              level: row.level,
              type: row.type,
              origin: detail.origin === true
            });
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
        if (a.origin && !b.origin) return -1;
        if (!a.origin && b.origin) return 1;
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
        origin: topChild.origin === true,
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
    // Section tabs (grade filter) — now wired via renderNamedDistBar buttons
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

    // Group toggle button
    var groupToggle = document.getElementById('lbGroupToggle');
    if (groupToggle) {
      groupToggle.addEventListener('click', function() {
        state.grouped = !state.grouped;
        groupToggle.textContent = state.grouped ? '\u229e Grouped' : '\u229f Expanded';
        groupToggle.classList.toggle('is-active', state.grouped);
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

  // ── EVIDENCE-TYPE TABS (above Named chart) ──
  function renderTypeTabs() {
    var host = document.getElementById('lbTypeTabs');
    if (!host) return;
    // Skip rendering if no enriched data yet
    if (!state.namedSkills || state.namedSkills.length === 0) {
      host.innerHTML = '';
      return;
    }
    host.innerHTML = EVIDENCE_TYPES.map(function(t) {
      return '<button class="lb-stab' + (state.evidenceType === t.id ? ' is-active' : '') +
             '" role="tab" data-type="' + t.id + '" type="button" aria-selected="' +
             (state.evidenceType === t.id ? 'true' : 'false') + '">' + t.label + '</button>';
    }).join('');
    host.querySelectorAll('.lb-stab').forEach(function(btn) {
      btn.addEventListener('click', function() {
        state.evidenceType = btn.getAttribute('data-type');
        renderTypeTabs();
        renderNamedChart(state.namedSkills);
        wireActionButtons();
      });
    });
  }

  // ── TRUST MAGNITUDE METHODOLOGY ACCORDION (below Named chart) ──
  function renderTrustMethodologyAccordion() {
    var body = document.getElementById('lbTmBody');
    var toggle = document.getElementById('lbTmToggle');
    var section = document.getElementById('lbTmAccordion');
    if (!body || !toggle || !section) return;
    if (!TM_METHODOLOGY_BODY) {
      section.hidden = true;
      return;
    }
    body.innerHTML = TM_METHODOLOGY_BODY;
    toggle.addEventListener('click', function() {
      state.tmMethodologyOpen = !state.tmMethodologyOpen;
      section.classList.toggle('is-open', state.tmMethodologyOpen);
      toggle.setAttribute('aria-expanded', String(state.tmMethodologyOpen));
      body.hidden = !state.tmMethodologyOpen;
      // The +→× swap is handled by CSS rotating .lb-tm-plus 45deg when .is-open.
    });
  }

  function applyFilter(skills) {
    var filtered = skills;

    // Contributor filter (multi-select from dropdown)
    if (state.searchContribs && state.searchContribs.length > 0) {
      filtered = filtered.filter(function(s) {
        return state.searchContribs.indexOf(s.contributor) !== -1;
      });
    }

    // Grade filter
    if (state.grade !== 'all') {
      filtered = filtered.filter(function(s) { return s.grade === state.grade; });
    }

    // Skill search filter
    if (state.skillSearchQuery) {
      filtered = filtered.filter(function(s) {
        var id = (s.contributor + '/' + s.slug).toLowerCase();
        var name = (s.name || s.slug || '').toLowerCase();
        return id.indexOf(state.skillSearchQuery) !== -1 || name.indexOf(state.skillSearchQuery) !== -1;
      });
    }

    // Evidence-type filter — when a specific type is active, drop skills whose
    // contribution from that type is zero (otherwise the chart would render
    // a wall of 0-height bars with no useful info).
    if (state.evidenceType && state.evidenceType !== 'all') {
      filtered = filtered.filter(function(s) {
        return tmForType(s, state.evidenceType) > 0;
      });
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
      return tmForType(b, state.evidenceType) - tmForType(a, state.evidenceType);
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

  // ── CONTRIBUTOR MULTI-SELECT ──
  function wireContribSearch() {
    var trigger = document.getElementById('lbMsTrigger');
    var dropdown = document.getElementById('lbMsDropdown');
    var searchInput = document.getElementById('lbMsSearch');
    var listEl = document.getElementById('lbMsList');
    var clearAll = document.getElementById('lbMsClearAll');
    var label = document.getElementById('lbMsLabel');
    var countEl = document.getElementById('lbMsCount');
    if (!trigger || !dropdown) return;

    function getContribs() {
      var all = {};
      state.namedSkills.forEach(function(s) { all[s.contributor] = true; });
      return Object.keys(all).sort();
    }

    function renderList(filter) {
      var contribs = getContribs();
      var q = (filter || '').toLowerCase();
      var shown = q ? contribs.filter(function(c) { return c.toLowerCase().indexOf(q) !== -1; }) : contribs;
      var wreathSrc = ROOT_PREFIX + 'assets/origin-wreath-gold.svg';
      listEl.innerHTML = shown.map(function(c) {
        var checked = state.searchContribs.indexOf(c) !== -1;
        var clean = String(c).replace(/^@/, '');
        var avatarSrc = 'https://github.com/' + encodeURIComponent(clean) + '.png?size=32';
        var identicon = 'https://github.com/identicons/' + encodeURIComponent(clean) + '.png';
        var errAttr = "if(this.dataset.fbk){this.onerror=null;}else{this.dataset.fbk='1';this.src='" + identicon.replace(/'/g, "\\'") + "';}";
        // E3: GitHub avatar framed by gold wreath (matches chart-bar appendAvatarWreath pattern)
        var avatarHtml =
          '<span class="lb-ms-avatar" style="background:oklch(0.55 0.18 ' + handleHue(c) + ')">' +
            '<img class="lb-ms-avatar-img" src="' + esc(avatarSrc) + '" alt="" decoding="async" loading="lazy" referrerpolicy="no-referrer" onerror="' + errAttr + '">' +
            '<img class="lb-ms-avatar-wreath" src="' + esc(wreathSrc) + '" alt="" aria-hidden="true">' +
          '</span>';
        return '<label class="lb-ms-item' + (checked ? ' is-checked' : '') + '">' +
          '<input type="checkbox" value="' + esc(c) + '"' + (checked ? ' checked' : '') + '>' +
          avatarHtml +
          '<span class="lb-ms-name">' + esc(c) + '</span>' +
        '</label>';
      }).join('');
    }

    function updateLabel() {
      var sel = state.searchContribs;
      label.textContent = sel.length === 0 ? 'Add contributor\u2026' :
        sel.length === 1 ? sel[0] :
        sel.length + ' contributors';
      if (countEl) countEl.textContent = sel.length > 0 ? sel.length + ' selected' : '';
    }

    trigger.addEventListener('click', function(e) {
      e.stopPropagation();
      var hidden = dropdown.hidden;
      dropdown.hidden = !hidden;
      if (!hidden) return;
      renderList('');
      if (searchInput) { searchInput.value = ''; searchInput.focus(); }
    });

    document.addEventListener('click', function(e) {
      if (!dropdown.hidden && !dropdown.contains(e.target) && e.target !== trigger) {
        dropdown.hidden = true;
      }
    });

    if (searchInput) {
      searchInput.addEventListener('input', function() {
        renderList(searchInput.value);
      });
    }

    if (listEl) {
      listEl.addEventListener('change', function(e) {
        var cb = e.target;
        if (cb.type !== 'checkbox') return;
        var val = cb.value;
        if (cb.checked) {
          if (state.searchContribs.indexOf(val) === -1) state.searchContribs.push(val);
        } else {
          state.searchContribs = state.searchContribs.filter(function(c) { return c !== val; });
        }
        cb.closest('.lb-ms-item').classList.toggle('is-checked', cb.checked);
        updateLabel();
        state.showCount = INITIAL_BARS;
        renderNamedChart(state.namedSkills);
        wireActionButtons();
      });
    }

    if (clearAll) {
      clearAll.addEventListener('click', function() {
        state.searchContribs = [];
        updateLabel();
        renderList(searchInput ? searchInput.value : '');
        state.showCount = INITIAL_BARS;
        renderNamedChart(state.namedSkills);
        wireActionButtons();
      });
    }
  }

  // ── SKILL SEARCH WIRING ──
  function wireSkillSearch() {
    var skillSearchEl = document.getElementById('lbSkillSearch');
    if (skillSearchEl) {
      skillSearchEl.addEventListener('input', function() {
        state.skillSearchQuery = this.value.toLowerCase().trim();
        renderNamedChart(state.namedSkills);
      });
    }
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
        window.location.href = ROOT_PREFIX + 'named/#explorer/' + id;
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
    var levelName = rankNameFor(skill.level, skill);

    return '<div class="lb-tt-name">' + esc(skill.name || skill.id.split('/')[1]) + '</div>' +
      '<div class="lb-tt-id">' + esc(skill.id) + '</div>' +
      '<div class="lb-tt-divider"></div>' +
      '<div class="lb-tt-row"><span class="lb-tt-label">Trust Magnitude</span><span class="lb-tt-value">' + (skill.trustMagnitude || 0).toFixed(2) + '</span></div>' +
      '<div class="lb-tt-row"><span class="lb-tt-label">Grade</span><span class="lb-tt-value">' + gradeLabel + ' (' + skill.grade + ')</span></div>' +
      '<div class="lb-tt-row"><span class="lb-tt-label">Level</span><span class="lb-tt-value">' + esc(skill.level) + (levelName ? ' ' + levelName : '') + '</span></div>' +
      (type === 'suite' ? '<div class="lb-tt-row"><span class="lb-tt-label">Branch</span><span class="lb-tt-value">Suite</span></div>' : '') +
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
            return '<span style="font-family:var(--font-data);font-size:0.65rem;color:var(--muted);opacity:0.8">' + esc(mid) + '</span>';
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

  // SVG label truncation with hover <title> tooltip
  function truncLabel(textEl, fullText, maxLen) {
    if (!fullText) { textEl.textContent = ''; return; }
    var display = fullText.length > maxLen ? fullText.substring(0, maxLen - 1) + '\u2026' : fullText;
    textEl.textContent = display;
    if (display !== fullText) {
      var titleEl = document.createElementNS(SVG_NS, 'title');
      titleEl.textContent = fullText;
      textEl.insertBefore(titleEl, textEl.firstChild);
    }
  }

  function esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

})();

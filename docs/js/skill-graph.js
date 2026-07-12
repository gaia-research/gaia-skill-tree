(function () {
  // ──────────────────────────────────────────────────────────────────
  // Canvas geometry locked per DESIGN.md (Graph Canvas section).
  // Touch the values only in DESIGN.md first; the consts in this file
  // must mirror that table exactly. Stage 5 audited every magic number
  // in this file against DESIGN.md and lifted them into the three
  // const blocks below — NODE_RADII, LINE_WEIGHTS, SPHERE_RADII.
  // ──────────────────────────────────────────────────────────────────
  //
  // ╔══ <canvas-tokens> contract ═══════════════════════════════════╗
  // ║ Every colour and font this canvas draws is read from a CSS    ║
  // ║ custom property on :root. A host page can override any token  ║
  // ║ to retheme the graph (e.g. local skill-tree views).           ║
  // ║                                                                ║
  // ║   --tier-basic / -rgb / -edge                                  ║
  // ║   --tier-extra / -rgb / -edge                                  ║
  // ║   --tier-unique / -rgb / -edge                                 ║
  // ║   --tier-ultimate / -rgb / -edge                               ║
  // ║   --rank-0 … --rank-6 / -bg / -border / -edge                  ║
  // ║   --honor-red / --honor-red-rgb                                ║
  // ║   --apex-gold / --apex-gold-rgb                                ║
  // ║   --muted / --text                                             ║
  // ║   --font-body / --font-mono / --font-display                   ║
  // ║                                                                ║
  // ║ Token map cached on first read via getCanvasTokens(). Call     ║
  // ║ invalidateCanvasTokens() if the theme is swapped at runtime.   ║
  // ╚════════════════════════════════════════════════════════════════╝
  const version = window.GAIA_VERSION ? '?v=' + window.GAIA_VERSION : '';
  const prefix = (typeof window.gaiaIconBase === 'function') ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '') : '';
  const GRAPH_JSON_URL = prefix + 'graph/gaia.json' + version;
  const GRAPH_SCALE = 1.625;

  // ── Locked canvas geometry (DESIGN.md ▸ Graph Canvas) ──────────
  // §6 node-radius re-axis: radius is keyed to EFFECTIVE RANK (bigger = more
  // proven), not type. NODE_RADII.get(rankOrLabel, type) accepts either an
  // integer effective rank or an "N★" glyph string and returns the rank-curve
  // radius. The per-type numeric constants below (ultimate/unique/extra/basic)
  // are LEGACY — retained only for the unique-void redraw pass (NODE_RADII.unique)
  // and any host still reading them; new call sites pass effectiveRank.
  const NODE_RADII = {
    ultimate: 12.5, unique: 9.5, extra: 6.9, basic: 3.5,  // legacy type-keyed
    get: function (rank, type) {
      if (type === 'unique') rank = 5;
      // Accept an int effective rank directly, else parse a leading "N★" int.
      const n = (typeof rank === 'number' && Number.isFinite(rank))
        ? Math.max(0, Math.round(rank))
        : (parseInt(rank, 10) || 0);
      // Boosted exponential curve for visibility: r = a * e^(b * n)
      // r(1) = 3.0, r(6) = 10.0
      if (n === 0) return 2.5;
      return 2.3 * Math.exp(0.25 * n);
    }
  };
  const LINE_WEIGHTS = {
    default: { ultimate: 1.55, other: 0.92 },
    highlighted: { ultimate: 2.20, other: 1.40 },
  };
  // Multiplied by `scale` at render time. Unique/orphan satellites use
  // their own larger radii (330 / 320+seed) in buildPositions(); those
  // are layout-tuning constants and intentionally not lifted here.
  const SPHERE_RADII = { basic: 250, extra: 145, ultimate: 44 };

  // ── Token reader: pulls colour + font tokens off :root once and
  // caches them. invalidateCanvasTokens() can be called from a theme-
  // swap hook to refresh. No fallback hex is hardcoded here — the
  // canonical source is tokens.css (generated from registry/gaia.json).
  // If tokens are missing the canvas paints transparent rather than
  // silently re-introducing tier hex codes inside this file.
  let _tokenCache = null;
  function _readVar(name) {
    if (typeof document === 'undefined') return '';
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }
  function _rgbOnly(triplet) {
    // tokens.css emits "R, G, B" with spaces; canvas rgba() works
    // either way but trimming keeps the strings tidy in DevTools.
    return triplet.replace(/\s+/g, '');
  }
  function getCanvasTokens() {
    if (_tokenCache) return _tokenCache;
    function tier(name) {
      const rgb = _rgbOnly(_readVar('--tier-' + name + '-rgb'));
      return {
        hex: _readVar('--tier-' + name),
        rgb: rgb,
        edge: _readVar('--tier-' + name + '-edge') || ('rgba(' + rgb + ',.55)'),
      };
    }
    function rank(n) {
      // §6 color-by-rank re-axis. tokens.css DOES emit --rank-N-rgb (grey
      // 148,163,184 at 0★ … apex-gold 251,191,36 at 6★); read it so the canvas
      // can build rgba() with a custom alpha for the rank ramp. bg/border/edge
      // are precomputed convenience forms.
      return {
        hex: _readVar('--rank-' + n),
        rgb: _rgbOnly(_readVar('--rank-' + n + '-rgb')),
        bg: _readVar('--rank-' + n + '-bg'),
        border: _readVar('--rank-' + n + '-border'),
        edge: _readVar('--rank-' + n + '-edge'),
      };
    }
    _tokenCache = {
      tier: {
        basic: tier('basic'),
        extra: tier('extra'),
        unique: tier('unique'),
        ultimate: tier('ultimate'),
      },
      rank: {
        0: rank(0), 1: rank(1), 2: rank(2), 3: rank(3),
        4: rank(4), 5: rank(5), 6: rank(6),
      },
      honorRed: _readVar('--honor-red'),
      honorRedRgb: _rgbOnly(_readVar('--honor-red-rgb')),
      apexGold: _readVar('--apex-gold'),
      apexGoldRgb: _rgbOnly(_readVar('--apex-gold-rgb')),
      muted: _readVar('--muted'),
      // --muted-rgb isn't emitted by tokens.css yet; canvas tooltips
      // and ruler ticks fall back to the slate-400 triplet which is
      // the historical value used for these surfaces. Update this
      // when --muted-rgb lands in tokens.css.
      mutedRgb: '148,163,184',
      fontBody: _readVar('--font-body'),
      fontMono: _readVar('--font-mono'),
      fontDisplay: _readVar('--font-display'),
    };
    return _tokenCache;
  }
  function invalidateCanvasTokens() { _tokenCache = null; }
  if (typeof window !== 'undefined') window.invalidateCanvasTokens = invalidateCanvasTokens;

  // canvasFont(role, sizePx) — single source for every `ctx.font = …`
  // call site. Roles map to the three Hunter's Atlas faces:
  //   body    → --font-body    (Bricolage Grotesque)
  //   handle  → --font-mono    (Departure Mono / JetBrains Mono)
  //   display → --font-display (EB Garamond, italic)
  function canvasFont(role, sizePx) {
    const t = getCanvasTokens();
    const sz = Math.max(6, Math.round(sizePx));
    if (role === 'display') return 'italic 600 ' + sz + 'px ' + t.fontDisplay;
    if (role === 'handle') return '600 ' + sz + 'px ' + t.fontMono;
    return 'bold ' + sz + 'px ' + t.fontBody;
  }

  const ORIGIN_PATHS = [
    new Path2D("M12 15V9l-2 1"),
    new Path2D("M12 21c-4-2-7-6-7-11 0-2 1.5-4 2.5-5"),
    new Path2D("M12 21c4-2 7-6 7-11 0-2-1.5-4-2.5-5"),
    new Path2D("M5 10c2 1 3 0 3-1"),
    new Path2D("M5.5 14c2 1 3 0 3-1"),
    new Path2D("M7 18c2 1 3 0 3-1"),
    new Path2D("M19 10c-2 1-3 0-3-1"),
    new Path2D("M18.5 14c-2 1-3 0-3-1"),
    new Path2D("M17 18c-2 1-3 0-3-1")
  ];

  // ── Per-skill tier palette (rgb triplets), keyed off the canonical
  // tier names. Reads canvas tokens; backwards-compat shim PALETTE so
  // sites that still reference `PALETTE.basic.rgb` keep working until
  // the entire file routes through getCanvasTokens(). When meta loads
  // we refresh the cached tokens so a registry update can re-tint the
  // canvas without a page reload.
  function _paletteFromTokens() {
    const t = getCanvasTokens().tier;
    return {
      basic: { rgb: t.basic.rgb, hex: t.basic.hex },
      extra: { rgb: t.extra.rgb, hex: t.extra.hex },
      unique: { rgb: t.unique.rgb, hex: t.unique.hex },
      ultimate: { rgb: t.ultimate.rgb, hex: t.ultimate.hex },
    };
  }
  let PALETTE = _paletteFromTokens();
  function _rankMetaFromTokens(labelMap) {
    const t = getCanvasTokens().rank;
    const out = {};
    Object.keys(labelMap || {}).forEach(function (k) {
      if (k === '0★') return;
      const n = parseInt(k, 10);
      if (Number.isNaN(n)) return;
      out[k] = { name: labelMap[k] || k, hex: t[n].hex, bg: t[n].bg };
    });
    if (!Object.keys(out).length) {
      // Fallback to the six canonical ranks if no label map was passed.
      [1, 2, 3, 4, 5, 6].forEach(function (n) {
        out[n + '★'] = { name: n + '★', hex: t[n].hex, bg: t[n].bg };
      });
    }
    return out;
  }
  let RANK_META = _rankMetaFromTokens(null);

  function _initMetaGraph(meta) {
    if (!meta) return;
    // Tokens are the single source of truth — they get refreshed from
    // tokens.css. The local palette objects mirror them so we don't
    // recompute on every draw.
    invalidateCanvasTokens();
    PALETTE = _paletteFromTokens();
    RANK_META = _rankMetaFromTokens(meta.levelLabels || null);
  }

  const FALLBACK_SKILLS = [
    { id: 'tokenize', type: 'basic', name: 'Tokenize', prerequisites: [] },
    { id: 'retrieve', type: 'basic', name: 'Retrieve', prerequisites: [] },
    { id: 'embed-text', type: 'basic', name: 'Embed Text', prerequisites: [] },
    { id: 'score-relevance', type: 'basic', name: 'Score Relevance', prerequisites: [] },
    { id: 'web-search', type: 'basic', name: 'Web Search', prerequisites: [] },
    { id: 'summarize', type: 'basic', name: 'Summarize', prerequisites: [] },
    { id: 'cite-sources', type: 'basic', name: 'Cite Sources', prerequisites: [] },
    { id: 'code-generation', type: 'basic', name: 'Code Generation', prerequisites: [] },
    { id: 'execute-bash', type: 'basic', name: 'Execute Bash', prerequisites: [] },
    { id: 'tool-select', type: 'basic', name: 'Tool Select', prerequisites: [] },
    { id: 'chunk-document', type: 'basic', name: 'Chunk Document', prerequisites: [] },
    { id: 'rank', type: 'basic', name: 'Rank', prerequisites: [] },
    { id: 'rag-pipeline', type: 'extra', name: 'RAG Pipeline', prerequisites: ['retrieve', 'chunk-document', 'embed-text', 'score-relevance', 'tokenize', 'rank'] },
    { id: 'research', type: 'extra', name: 'Research', prerequisites: ['web-search', 'summarize', 'cite-sources'] },
    { id: 'error-interpretation', type: 'basic', name: 'Error Interpretation', prerequisites: [] },
    { id: 'autonomous-debug', type: 'extra', name: 'Autonomous Debug', prerequisites: ['code-generation', 'execute-bash', 'error-interpretation'] },
    { id: 'ghostwrite', type: 'extra', name: 'Ghostwrite', prerequisites: ['research', 'write-report', 'audience-model'] },
    { id: 'knowledge-harvest', type: 'extra', name: 'Knowledge Harvest', prerequisites: ['web-scrape', 'embed-text', 'extract-entities'] },
    { id: 'autonomous-research-agent', type: 'ultimate', name: 'Autonomous Research Agent', prerequisites: ['research', 'ghostwrite', 'knowledge-harvest'] },
  ];
  const FALLBACK_NAMED_MAP = {
    'automated-testing': '0xdarkmatter/pytest-patterns',
    'test-driven-development': 'addy-osmani/test-driven-development',
    'document-editing': 'anthropic/pptx',
    'tool-creation': 'anthropic/skill-creator',
    'autonomous-debug': 'devin-ai/autonomous-swe',
    'write-report': 'glincker/readme-generator',
    'browser-automation': 'gooseworks/notte-browser',
    'autonomous-research-agent': 'karpathy/autoresearch',
    'framework-upgrade': 'laravel/upgrade-laravel-v13',
    'ux-audit': 'martin-stepanoski/nielsen-heuristics-audit',
    'multi-agent-orchestration-v': 'ruvnet/flow-nexus-swarm',
    'generate-test': 'upsonic/unittest-generator',
    'skill-discovery': 'vercel/find-skills',
    'rag-pipeline': 'yonatangross/orchestkit-rag',
  };
  const FALLBACK_TITLE_MAP = {
    'automated-testing': 'The Quality Guardian',
    'test-driven-development': 'The Red-Green Oath',
    'document-editing': 'The Slide Artisan',
    'tool-creation': "The Skill Forger's Art",
    'autonomous-debug': "The Codebreaker's Will",
    'write-report': 'The Document Weaver',
    'browser-automation': 'The Digital Navigator',
    'autonomous-research-agent': "The Scholar's Compass",
    'framework-upgrade': "The Versionist's Trial",
    'ux-audit': 'The Ten Laws of Sight',
    'multi-agent-orchestration-v': "The Grand Conductor's Blueprint",
    'generate-test': 'The Test Weaver',
    'skill-discovery': 'The Registry Scout',
    'rag-pipeline': 'The Knowledge Architect',
  };

  function normalizeSkills(graph) {
    const TYPE_ALIASES = { atomic: 'basic', composite: 'extra', legendary: 'ultimate' };
    const skills = (graph && graph.skills) ? graph.skills : FALLBACK_SKILLS;
    return skills.map(skill => ({
      id: skill.id,
      name: skill.name || skill.id,
      type: TYPE_ALIASES[skill.type] || skill.type || 'basic',
      // Generic refs are rank-less — the rank legend/coloring reads the top
      // named-variant star (namedMaxLevel) supplied by syncDocsGraphAssets.py.
      level: skill.namedMaxLevel || skill.level || '',
      effectiveLevel: skill.namedMaxLevel || skill.effectiveLevel || skill.level || '',
      // §4 effective rank as a small integer (0-6). Parsed from namedMaxLevel;
      // 0 for starless/≤1★. Color-by-rank + radius-by-rank read this (§6).
      effectiveRank: starsFromLabel(skill.namedMaxLevel != null ? skill.namedMaxLevel : skill.effectiveRank),
      demerits: Array.isArray(skill.demerits) ? skill.demerits : [],
      description: skill.description || '',
      prerequisites: Array.isArray(skill.prerequisites) ? skill.prerequisites : [],
      cluster: skill.cluster !== undefined ? skill.cluster : 0,
      positions: skill.positions || null,
    })).filter(skill => skill.id);
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function stableHash(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i += 1) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return Math.abs(h >>> 0);
  }

  // §4 runtime effective-rank join. gaia.json ships STARLESS (level: null on
  // every node — stars live on named skills only, per META.md §1). Each source
  // skill already carries `namedMaxLevel` — the max star among its named
  // children, pre-joined by syncDocsGraphAssets.py — as an "N★" glyph string.
  // We ONLY parse that leading integer; no new fetch, no walking of
  // named/index.json buckets (namedMaxLevel already encodes that join). 0-1★ or
  // absent → 0 (outer bark; the colored ramp begins at 2★ Named per the
  // redaction cutline). The parsed int is attached as `effectiveRank` on the
  // source skill BEFORE world-tree-layout.js runs (it reads node.effectiveRank).
  function starsFromLabel(label) {
    const n = parseInt(String(label == null ? '' : label), 10);
    return Number.isFinite(n) && n > 0 ? n : 0;
  }

  function clamp01(value) {
    return Math.max(0, Math.min(1, value));
  }

  function easeWorldTree(value) {
    // Smoothstep keeps the object morph reversible without a velocity snap.
    const t = clamp01(value);
    return t * t * (3 - 2 * t);
  }

  function lerp(a, b, amount) {
    return a + (b - a) * amount;
  }

  function asIdObject(value) {
    if (!value) return {};
    if (value instanceof Map) return Object.fromEntries(value.entries());
    return value;
  }

  function asIdSet(value) {
    if (!value) return new Set();
    if (value instanceof Set) return value;
    if (Array.isArray(value)) return new Set(value);
    return new Set(Object.keys(value).filter(key => value[key]));
  }

  function rgbFromHex(hex) {
    const raw = String(hex || '').trim().replace(/^#/, '');
    if (!/^[0-9a-f]{6}$/i.test(raw)) return '';
    return `${parseInt(raw.slice(0, 2), 16)},${parseInt(raw.slice(2, 4), 16)},${parseInt(raw.slice(4, 6), 16)}`;
  }

  function mixRgb(from, to, amount) {
    const a = String(from || '').split(',').map(Number);
    const b = String(to || '').split(',').map(Number);
    if (a.length !== 3 || b.length !== 3 || a.some(Number.isNaN) || b.some(Number.isNaN)) return to || from;
    return [0, 1, 2].map(index => Math.round(lerp(a[index], b[index], amount))).join(',');
  }

  // §6 color-by-rank ramp. Maps an effective star rank (0-6 int) to a rank-token
  // rgb triplet. The redaction cutline (§4) collapses 0-1★ to grey (--rank-0);
  // the colored ramp begins at 2★ and climbs to apex-gold at 6★. No hex
  // fallbacks — the triplets come straight from tokens.css via getCanvasTokens.
  function _rankColorRgb(effRank) {
    const t = getCanvasTokens();
    let n = Math.round(Number(effRank));
    if (!Number.isFinite(n) || n < 0) n = 0;
    if (n > 6) n = 6;
    const key = n <= 1 ? 0 : n;   // 0-1★ share the grey bark swatch
    const entry = t.rank[key] || t.rank[0];
    return (entry && entry.rgb) ? entry.rgb : t.rank[0].rgb;
  }

  function spherePoint(radius, seed, index, count) {
    const golden = Math.PI * (3 - Math.sqrt(5));
    const i = index + (seed % 17) / 17;
    const y = 1 - (i / Math.max(count - 1, 1)) * 2;
    const ring = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = golden * i + (seed % 360) * Math.PI / 180;
    return {
      x: Math.cos(theta) * ring * radius,
      y: y * radius,
      z: Math.sin(theta) * ring * radius,
      w: 0,
      phase: (seed % 628) / 100,
    };
  }

  function buildPositions(skills, scale, mode = 'semantic') {
    const positions = {};
    const hasPositions = skills.some(s => s.positions);

    if (hasPositions) {
      skills.forEach(skill => {
        if (skill.positions && skill.positions[mode]) {
          const p = skill.positions[mode];
          // Scale up coordinates (PCA/Spectral/Deterministic are normalized to [-1, 1])
          const s = 450 * scale;
          positions[skill.id] = {
            x: p[0] * s, y: p[1] * s, z: p[2] * s, w: p[3] * s,
            phase: stableHash(skill.id) % 628 / 100
          };
        }
      });
      // Fallback for missing positions
      skills.forEach(skill => {
        if (!positions[skill.id]) {
          positions[skill.id] = { x: 0, y: 0, z: 0, w: 0, phase: 0 };
        }
      });
      return positions;
    }

    // LEGACY Fallback (Spherical)
    const groups = { basic: [], extra: [], ultimate: [] };
    const satellite = { unique: [], orphan: [] };
    const allPrereqRefs = new Set();
    skills.forEach(skill => skill.prerequisites.forEach(pid => allPrereqRefs.add(pid)));
    skills.forEach(skill => {
      if (skill.type === 'unique') { satellite.unique.push(skill); }
      else if (skill.type === 'basic' && !skill.prerequisites.length && !allPrereqRefs.has(skill.id)) {
        satellite.orphan.push(skill);
      } else {
        (groups[skill.type] || groups.basic).push(skill);
      }
    });
    Object.values(groups).forEach(group => group.sort((a, b) => (a.name || a.id).localeCompare(b.name || b.id)));
    satellite.unique.sort((a, b) => (a.name || a.id).localeCompare(b.name || b.id));
    satellite.orphan.sort((a, b) => (a.name || a.id).localeCompare(b.name || b.id));
    // Multiply locked SPHERE_RADII (DESIGN.md) by the runtime scale.
    const radii = {
      basic: SPHERE_RADII.basic * scale,
      extra: SPHERE_RADII.extra * scale,
      ultimate: SPHERE_RADII.ultimate * scale,
    };
    Object.entries(groups).forEach(([type, group]) => {
      group.forEach((skill, index) => {
        positions[skill.id] = spherePoint(radii[type] || radii.basic, stableHash(skill.id), index, group.length);
      });
    });
    const uniqueCount = satellite.unique.length;
    satellite.unique.forEach((skill, idx) => {
      const seed = stableHash(skill.id);
      positions[skill.id] = {
        ...spherePoint(330 * scale, seed, idx, Math.max(uniqueCount, 1)),
        _satellite: 'unique',
      };
    });
    satellite.orphan.forEach((skill, idx) => {
      const seed = stableHash(skill.id);
      const baseR = (320 + (seed % 70)) * scale;
      const pos = spherePoint(baseR, seed, idx, Math.max(satellite.orphan.length, 1));
      positions[skill.id] = {
        ...pos,
        _satellite: 'orphan',
        _orbitSpeed: 0.2 + (seed % 100) / 100 * 0.65,
        _orbitAmp: (22 + (seed % 38)) * scale,
        _phX: (seed % 628) / 100,
        _phY: ((seed * 7) % 628) / 100,
        _phZ: ((seed * 13) % 628) / 100,
      };
    });
    return positions;
  }

  function drawRuler(canvas, logValue, opts) {
    const ctx2 = canvas.getContext('2d');
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const cw = canvas.clientWidth || 36, ch = canvas.clientHeight || 160;
    canvas.width = cw * dpr; canvas.height = ch * dpr;
    ctx2.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx2.clearRect(0, 0, cw, ch);
    const vert = opts.vertical !== false;
    const mainSize = vert ? ch : cw;
    const crossSize = vert ? cw : ch;
    const ppu = opts.pxPerUnit || 36;
    const minorStep = opts.minorStep || 0.15;
    const majorEvery = opts.majorEvery || 4;
    const startTick = Math.ceil((logValue - mainSize / 2 / ppu) / minorStep);
    const endTick = Math.floor((logValue + mainSize / 2 / ppu) / minorStep);
    ctx2.lineWidth = 1;
    for (let tick = startTick; tick <= endTick; tick++) {
      const pos = mainSize / 2 + (tick * minorStep - logValue) * ppu;
      const isMajor = tick % majorEvery === 0;
      const tickLen = isMajor ? crossSize * 0.38 : crossSize * 0.18;
      const alpha = isMajor ? 0.18 : 0.08;
      ctx2.beginPath();
      if (vert) { ctx2.moveTo(crossSize / 2 - tickLen / 2, pos); ctx2.lineTo(crossSize / 2 + tickLen / 2, pos); }
      else { ctx2.moveTo(pos, crossSize / 2 - tickLen / 2); ctx2.lineTo(pos, crossSize / 2 + tickLen / 2); }
      // Slate ruler tick — reads --muted-rgb from the token cache.
      ctx2.strokeStyle = `rgba(${getCanvasTokens().mutedRgb},${alpha})`;
      ctx2.stroke();
    }
    ctx2.beginPath();
    if (vert) { ctx2.moveTo(0, mainSize / 2); ctx2.lineTo(crossSize, mainSize / 2); }
    else { ctx2.moveTo(mainSize / 2, 0); ctx2.lineTo(mainSize / 2, crossSize); }
    ctx2.strokeStyle = `rgba(${getCanvasTokens().mutedRgb},.28)`;
    ctx2.lineWidth = 1;
    ctx2.stroke();
  }

  function createSkillGraph(canvas, options) {
    const ctx = canvas.getContext('2d');
    const DPR = Math.min(window.devicePixelRatio || 1, 2);
    // Runtime-mutable options for interactive mode toggling.
    // When the hero graph goes fullscreen, these flip on so the
    // single canvas gains drag/zoom/hover/labels without needing
    // a second graph instance.
    const _opts = {
      draggable: options.draggable || false,
      zoomable: options.zoomable || false,
      hoverable: options.hoverable || false,
    };
    const NAMED_LEVELS = new Set(['2★', '3★', '4★', '5★', '6★']);
    const state = {
      skills: FALLBACK_SKILLS,
      positions: buildPositions(FALLBACK_SKILLS, GRAPH_SCALE),
      stars: [],
      width: 0,
      height: 0,
      t: 0,
      mx: 0,
      my: 0,
      labelMode: options.labelMode || 'none', // Labels off by default
      layoutMode: 'semantic', // Default layout
      autoRotate: true,
      colorMode: 'tier',
      rx: 0, ry: 0, rz: 0, rw: 0,
      scale: options.scale || GRAPH_SCALE,
      zoom: 1,
      statusEl: options.statusEl || null,
      running: options.autostart !== false,
      frame: null,
      orbitX: 0,
      orbitY: 0,
      dragging: false,
      dragMode: 'orbit',
      dragLastX: 0,
      dragLastY: 0,
      dragStartX: 0,
      dragStartY: 0,
      dragMoved: false,
      panX: 0,
      panY: 0,
      paused: false,
      rotSpeed: 1,
      hoverSlowdown: 0,
      nebula: true,
      nebulaClouds: [],
      pinnedId: null,
      pinnedPos: null,
      collection: [],
      collectionEl: null,
      skillPanelEl: null,
      zoomCounterEl: null,
      scatterRulerCanvas: null,
      speedRulerCanvas: null,
      hoveredId: null,
      lastHoveredId: null,
      projectedNodes: {},
      tooltipEl: null,
      nodeAlphas: {},
      searchText: '',
      legendFilterType: null,
      legendFilterRank: null,
      legendHoverType: null,
      legendHoverRank: null,
      legendEl: null,
      showTitles: false,
      redPillActive: false,
      meta: null,
      namedMap: null,
      titleMap: null,
      originMap: null,
      treeLayout: null,
      heroPose: {},
      fieldPose: {},
      treeEdges: [],
      ancestorsById: {},
      descendantsById: {},
      directNeighborsById: {},
      treeBounds: null,
      treeSpread: 1,
      viewMix: 0,
      viewFrom: 0,
      viewTarget: 0,
      viewStartedAt: null,
      viewDuration: 900,
      viewPhase: 'hero2d',
      viewComplete: null,
      lastDrawAt: 0,
      // graphMode: 'public' (default) or 'local'. In local mode the
      // collection panel becomes "Claimed skills", the nav title swaps
      // to "@<handle> · Atlas", and (TODO) the scatter strip pulls
      // from the user's owned-skill counts. The handle is supplied via
      // options.graphHandle or document.documentElement.dataset.graphHandle.
      graphMode: options.graphMode || 'public',
      graphHandle: options.graphHandle || '',
    };

    function resize() {
      const parent = canvas.parentElement;
      const rect = canvas.getBoundingClientRect();
      state.width = Math.max(1, Math.round(rect.width || parent.clientWidth));
      state.height = Math.max(1, Math.round(rect.height || parent.clientHeight));
      canvas.width = state.width * DPR;
      canvas.height = state.height * DPR;
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
      state.stars = Array.from({ length: options.stars || 260 }, (_, i) => {
        const seed = i * 7919 + 97;
        const point = spherePoint((500 + (seed % 280)) * state.scale, seed, i, options.stars || 260);
        return { ...point, size: 0.4 + (seed % 13) / 10, alpha: 0.22 + (seed % 55) / 100 };
      });
      state.nebulaClouds = Array.from({ length: 8 }, (_, i) => {
        const seed = i * 1337 + 41;
        const a1 = (seed % 628) / 100, a2 = ((seed * 7) % 628) / 100;
        const r = (550 + (seed % 320)) * state.scale;
        const isAurora = i >= 6;
        const auroraHues = [140, 280];
        return {
          x: Math.cos(a1) * Math.cos(a2) * r, y: Math.sin(a2) * r, z: Math.sin(a1) * Math.cos(a2) * r,
          w: 0,
          phase: (seed % 628) / 100,
          radius: (200 + (seed % 140)) * state.scale,
          isAurora,
          hue: isAurora ? auroraHues[i - 6] : 220,
          sat: isAurora ? 60 : 5 + (seed % 8),
          alpha: isAurora ? 0.035 + (seed % 4) / 100 : 0.04 + (seed % 5) / 100,
        };
      });
    }

    function _normalizePoseMap(value) {
      const input = asIdObject(value);
      const output = {};
      Object.keys(input || {}).sort().forEach(id => {
        const p = input[id];
        if (!p || !Number.isFinite(Number(p.x)) || !Number.isFinite(Number(p.y))) return;
        output[id] = {
          x: Number(p.x),
          y: Number(p.y),
          z: Number.isFinite(Number(p.z)) ? Number(p.z) : 0,
          w: Number.isFinite(Number(p.w)) ? Number(p.w) : 0,
          phase: Number.isFinite(Number(p.phase)) ? Number(p.phase) : stableHash(id) % 628 / 100,
          _satellite: p._satellite,
        };
      });
      return output;
    }

    function _computeTreeBounds(heroPose, fieldPose) {
      const ids = Object.keys(heroPose);
      if (!ids.length) return null;
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity, maxZ = 0;
      ids.forEach(id => {
        const hp = heroPose[id];
        const fp = fieldPose[id] || hp;
        minX = Math.min(minX, hp.x, fp.x);
        maxX = Math.max(maxX, hp.x, fp.x);
        minY = Math.min(minY, hp.y, fp.y);
        maxY = Math.max(maxY, hp.y, fp.y);
        maxZ = Math.max(maxZ, Math.abs(fp.z || 0));
      });
      return {
        minX, maxX, minY, maxY, maxZ,
        width: Math.max(1, maxX - minX),
        height: Math.max(1, maxY - minY),
        centerX: (minX + maxX) / 2,
        centerY: (minY + maxY) / 2,
      };
    }

    function setTreeLayout(layout) {
      const heroPose = _normalizePoseMap(layout && layout.heroPose);
      const fieldPose = _normalizePoseMap(layout && layout.fieldPose);
      const requiredIds = state.skills.map(skill => skill.id);
      const complete = requiredIds.length > 0 && requiredIds.every(id => heroPose[id] && fieldPose[id]);
      const unavailable = !layout || layout.available === false || layout.status === 'unavailable' || !complete;
      if (unavailable) {
        state.treeLayout = null;
        state.structuralRouteKeys = null;
        state.heroPose = {};
        state.fieldPose = {};
        state.treeEdges = [];
        state.ancestorsById = {};
        state.descendantsById = {};
        state.directNeighborsById = {};
        state.treeBounds = null;
        state.positions = buildPositions(state.skills, state.scale, state.layoutMode);
        return false;
      }

      state.treeLayout = layout;
      // §8 perf: the structural-route key lookup set is derived once here from
      // the frozen layout, not rebuilt every draw() frame.
      state.structuralRouteKeys = layout.structuralRoutes
        ? new Set(Object.keys(layout.structuralRoutes))
        : null;
      state.heroPose = heroPose;
      state.fieldPose = fieldPose;
      state.positions = heroPose;
      state.treeBounds = _computeTreeBounds(heroPose, fieldPose);
      state.ancestorsById = asIdObject(layout.ancestorsById || layout.ancestors);
      state.descendantsById = asIdObject(layout.descendantsById || layout.descendants);

      const byId = Object.fromEntries(state.skills.map(skill => [skill.id, skill]));
      const inputEdges = Array.isArray(layout.edges) ? layout.edges : [];
      const structuralKeys = new Set(Array.isArray(layout.structuralEdgeKeys) ? layout.structuralEdgeKeys : []);
      const hasStructuralHierarchy = structuralKeys.size > 0;
      state.treeEdges = inputEdges.map(edge => {
        const from = edge.source || edge.sourceSkillId || edge.from;
        const to = edge.target || edge.targetSkillId || edge.to;
        if (!from || !to || !byId[from] || !byId[to]) return null;
        return {
          from,
          to,
          type: byId[to].type,
          structural: !hasStructuralHierarchy || structuralKeys.has(from + '\u0000' + to),
        };
      }).filter(Boolean);
      if (!state.treeEdges.length) {
        state.skills.forEach(skill => skill.prerequisites.forEach(parent => {
          if (byId[parent]) state.treeEdges.push({ from: parent, to: skill.id, type: skill.type });
        }));
      }

      const direct = {};
      state.skills.forEach(skill => { direct[skill.id] = new Set(); });
      state.treeEdges.forEach(edge => {
        direct[edge.from].add(edge.to);
        direct[edge.to].add(edge.from);
      });
      state.directNeighborsById = direct;
      return true;
    }

    function setSkills(skills, treeLayout) {
      state.skills = skills;
      if (treeLayout) setTreeLayout(treeLayout);
      else if (!state.treeLayout) state.positions = buildPositions(skills, state.scale, state.layoutMode);
      const newAlphas = {};
      skills.forEach(s => { newAlphas[s.id] = state.nodeAlphas[s.id] !== undefined ? state.nodeAlphas[s.id] : 1.0; });
      state.nodeAlphas = newAlphas;
      if (state.statusEl) {
        const edgeCount = skills.reduce((sum, skill) => sum + skill.prerequisites.length, 0);
        const uniqueCount = skills.filter(s => s.type === 'unique').length;
        const mb = (fill) => `<svg class="gst-icon" viewBox="0 0 10 15" fill="none" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"><rect x=".7" y=".7" width="8.6" height="13.6" rx="4.3"/><path d="M5 .7v5.8" stroke-width="1"/><path d="M.7 6.5h8.6" stroke-width="1"/>${fill}</svg>`;
        const iL = mb('<rect x=".7" y=".7" width="4.3" height="5.8" rx="2" stroke="none" fill="currentColor" opacity=".55"/>');
        const iM = mb('<rect x="3.4" y="1.4" width="3.2" height="4.2" rx="1.6" stroke="none" fill="currentColor" opacity=".55"/>');
        const iS = mb('<rect x="3.4" y="1.4" width="3.2" height="4.2" rx="1.6" stroke-width=".9" opacity=".5"/><path d="M5 2.2v3.2M4 3.1 5 2.2 6 3.1M4 4.5 5 5.4 6 4.5" stroke-width=".9"/>');
        const stat = `<span class="gst-stat">${skills.length}<span class="gst-dim"> skills</span> · ${edgeCount}<span class="gst-dim"> links</span>` +
          (uniqueCount ? ` · <span class="gst-unique-count">${uniqueCount}</span><span class="gst-dim"> Unique</span>` : '') +
          `</span>`;
        let tips = '';
        const isTouch = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0);
        if (isTouch) {
          if (_opts.draggable) tips += `<span class="gst-tip">Drag to pan</span>`;
          if (_opts.zoomable) tips += `<span class="gst-tip">Pinch to zoom</span>`;
        } else {
          if (_opts.draggable) {
            tips += `<span class="gst-tip">${iL}<span>pan</span></span>`;
            tips += `<span class="gst-tip"><kbd class="gst-ctrl">⌃</kbd>${iL}<span class="gst-or">/</span>${iM}<span>orbit</span></span>`;
          }
          if (_opts.zoomable) tips += `<span class="gst-tip">${iS}<span>zoom</span></span>`;
        }
        state.statusEl.innerHTML = stat + tips;
      }
    }

    function rotX(p, a) {
      const c = Math.cos(a), s = Math.sin(a);
      return { x: p.x, y: c * p.y - s * p.z, z: s * p.y + c * p.z, w: p.w, phase: p.phase };
    }
    function rotY(p, a) {
      const c = Math.cos(a), s = Math.sin(a);
      return { x: c * p.x + s * p.z, y: p.y, z: -s * p.x + c * p.z, w: p.w, phase: p.phase };
    }
    function rotXW(p, a) {
      const c = Math.cos(a), s = Math.sin(a);
      return { x: c * p.x - s * p.w, y: p.y, z: p.z, w: s * p.x + c * p.w, phase: p.phase };
    }
    function rotYW(p, a) {
      const c = Math.cos(a), s = Math.sin(a);
      return { x: p.x, y: c * p.y - s * p.w, z: p.z, w: s * p.y + c * p.w, phase: p.phase };
    }

    let treeProjectionFrame = null;
    function computeTreeProjection() {
      if (!state.treeLayout || !state.treeBounds) return null;
      const mix = easeWorldTree(state.viewMix);
      const bounds = state.treeBounds;
      const mobileTree = window.matchMedia('(max-width:700px)').matches;
      const heroCenterValue = parseFloat(getComputedStyle(canvas.parentElement).getPropertyValue('--hero-tree-center-x'));
      const heroCenterRatio = Number.isFinite(heroCenterValue) ? heroCenterValue : (mobileTree ? 0.5 : 0.72);
      const heroHeightFactor = mobileTree ? 0.84 : 0.71;
      const heroFit = Math.max(0.05, Math.min(
        state.width * (mobileTree ? 0.90 : 0.60) / bounds.width,
        state.height * heroHeightFactor / bounds.height
      ));
      const fieldFit = Math.max(0.05, Math.min(
        state.width * 0.84 / bounds.width,
        state.height * 0.72 / bounds.height
      ));
      return {
        mix,
        bounds,
        heroCenterRatio,
        heroFit,
        fieldFit,
        spread: state.treeSpread || 1,
        cameraDistance: Math.max(bounds.width, bounds.height, bounds.maxZ * 2, 1) * 2.35,
        fieldZoom: lerp(1, state.zoom, mix),
      };
    }

    function project(p) {
      if (state.treeLayout && state.treeBounds) {
        const config = treeProjectionFrame || computeTreeProjection();
        const { mix, bounds, heroCenterRatio, heroFit, fieldFit, spread, cameraDistance, fieldZoom } = config;
        const px = (p.x - bounds.centerX) * spread;
        const py = (p.y - bounds.centerY) * spread;
        const pz = (p.z || 0) * spread;
        const heroX = state.width * heroCenterRatio + px * heroFit;
        const heroY = state.height * 0.50 + py * heroFit;
        const perspective = Math.max(0.12, cameraDistance / (cameraDistance + pz));
        const fieldX = state.width * 0.5 + px * fieldFit * perspective * fieldZoom + state.panX * mix;
        const fieldY = state.height * 0.47 + py * fieldFit * perspective * fieldZoom + state.panY * mix;
        return {
          sx: lerp(heroX, fieldX, mix),
          sy: lerp(heroY, fieldY, mix),
          scale: lerp(heroFit, fieldFit * perspective * fieldZoom, mix),
          z: pz,
          w: 0,
        };
      }
      // 4D -> 3D Perspective Projection
      const fov4 = 2.0;
      const wCoeff = (p.w || 0) / (700 * state.scale); // Pushed back W-scale
      const scale4 = fov4 / (fov4 + wCoeff);
      const x3 = p.x * scale4, y3 = p.y * scale4, z3 = p.z * scale4;

      const fov = Math.min(state.width, state.height) * 0.75;
      // Pushed camera further back (480 instead of 360) to avoid clipping large clouds
      const denom = fov + z3 + 520 * state.scale;
      if (denom < 1) return { sx: state.width / 2 + state.panX, sy: state.height / 2 + state.panY, scale: 0, z: z3, w: p.w || 0 };
      const dist = fov / denom;
      const z = state.zoom;
      return {
        sx: state.width / 2 + x3 * dist * z + state.panX,
        sy: state.height / 2 + y3 * dist * z + state.panY,
        scale: dist * z * scale4,
        z: z3,
        w: p.w || 0
      };
    }
    // §2/§5 ghost armature + structural re-routing render helpers.
    // ghostPose points live in the SAME layout frame as heroPose/fieldPose, so
    // they transform through the identical rotate(ry,rx)+project() pipeline. We
    // hero-morph the depth: at viewMix->0 the spine reads flat (z folded out),
    // at viewMix->1 the boughs open into depth. Ghosts carry NO data — never
    // hover, label, click, or register in projectedNodes (§5.1 invariant).
    function _projectGhost(pose, ry, rx, treeMix) {
      if (!pose) return null;
      const p = rotX(rotY({
        x: pose.x, y: pose.y, z: (pose.z || 0) * treeMix, w: 0, phase: 0,
      }, ry), rx);
      return project(p);
    }
    // Resolve a structural-route waypoint (either a real node's transformed
    // point via xf, or a ghost anchor via ghostPose) to a projected screen point.
    function _routeStop(stop, xf, ghostPose, ry, rx, treeMix) {
      if (!stop) return null;
      if (stop.kind === 'node') {
        const tp = xf[stop.id];
        return tp ? project(tp) : null;
      }
      return _projectGhost(ghostPose[stop.key], ry, rx, treeMix);
    }

    function drawNode(sx, sy, r, color, alpha) {
      const grad = ctx.createRadialGradient(sx, sy, 0, sx, sy, r * 3.9);
      grad.addColorStop(0, `rgba(${color.rgb},${Math.min(alpha * 0.68, 1).toFixed(2)})`);
      grad.addColorStop(0.42, `rgba(${color.rgb},${Math.min(alpha * 0.24, 1).toFixed(2)})`);
      grad.addColorStop(1, `rgba(${color.rgb},0)`);
      ctx.beginPath(); ctx.arc(sx, sy, r * 3.9, 0, Math.PI * 2); ctx.fillStyle = grad; ctx.fill();
      ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2); ctx.fillStyle = `rgba(${color.rgb},${Math.min(alpha * 1.18, 1).toFixed(2)})`; ctx.fill();
      ctx.beginPath(); ctx.arc(sx - r * 0.28, sy - r * 0.28, r * 0.32, 0, Math.PI * 2); ctx.fillStyle = `rgba(255,255,255,${(alpha * 0.65).toFixed(2)})`; ctx.fill();
    }
    function drawNodeNamed(sx, sy, r, alpha) {
      // Named (red-pill) nodes glow in Honor Red — single role token.
      const honor = getCanvasTokens().honorRedRgb;
      const glow = ctx.createRadialGradient(sx, sy, 0, sx, sy, r * 4.2);
      glow.addColorStop(0, `rgba(${honor},${Math.min(alpha * 0.7, 1).toFixed(2)})`);
      glow.addColorStop(0.4, `rgba(${honor},${Math.min(alpha * 0.25, 1).toFixed(2)})`);
      glow.addColorStop(1, `rgba(${honor},0)`);
      ctx.beginPath(); ctx.arc(sx, sy, r * 4.2, 0, Math.PI * 2); ctx.fillStyle = glow; ctx.fill();
      ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${honor},${Math.min(alpha * 1.2, 1).toFixed(2)})`; ctx.fill();
      ctx.beginPath(); ctx.arc(sx - r * 0.28, sy - r * 0.28, r * 0.32, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${(alpha * 0.65).toFixed(2)})`; ctx.fill();
    }
    function drawNodeVI(sx, sy, r, alpha, t, p) {
      const phase = p.phase || 0;
      const spin = t * 1.3 + phase;

      // Impact blink: fires every ~5s, quick flash then gradual fade-out
      // [TEMPORARY] Flash disabled per request.
      const blink = 0;

      // ── GOLD CORONA (outermost glow) ──
      const coronaPulse = 0.85 + 0.15 * Math.sin(t * 0.9 + phase);
      const coronaR = r * (7.5 * coronaPulse);
      const corona = ctx.createRadialGradient(sx, sy, r * 1.2, sx, sy, coronaR);
      corona.addColorStop(0, `rgba(255,215,0,${(alpha * 0.48).toFixed(2)})`);
      corona.addColorStop(0.35, `rgba(255,170,0,${(alpha * 0.22).toFixed(2)})`);
      corona.addColorStop(0.7, `rgba(255,120,0,${(alpha * 0.08).toFixed(2)})`);
      corona.addColorStop(1, `rgba(255,80,0,0)`);
      ctx.beginPath(); ctx.arc(sx, sy, coronaR, 0, Math.PI * 2);
      ctx.fillStyle = corona; ctx.fill();

      // ── PULSAR BEAMS (triangular cones) ──
      ctx.save();
      ctx.translate(sx, sy);
      ctx.rotate(spin);
      for (let beam = 0; beam < 2; beam++) {
        const ba = beam * Math.PI;
        const beamLen = r * 5.8;
        const cone = Math.PI * 0.055;
        const bA = alpha * (0.45 + 0.15 * Math.sin(t * 1.8 + beam * 2.1)) * (1 - blink * 0.6);
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(Math.cos(ba - cone) * beamLen, Math.sin(ba - cone) * beamLen);
        ctx.lineTo(Math.cos(ba + cone) * beamLen, Math.sin(ba + cone) * beamLen);
        ctx.closePath();
        const bg = ctx.createLinearGradient(0, 0, Math.cos(ba) * beamLen, Math.sin(ba) * beamLen);
        bg.addColorStop(0, `rgba(255,255,255,${bA.toFixed(2)})`);
        bg.addColorStop(0.35, `rgba(255,240,180,${(bA * 0.45).toFixed(2)})`);
        bg.addColorStop(1, `rgba(255,215,0,0)`);
        ctx.fillStyle = bg; ctx.fill();
      }
      ctx.restore();

      // ── ORBITING SATELLITES ──
      for (let i = 0; i < 5; i++) {
        const orbitR = r * (1.7 + i * 0.55);
        const speed = 1.6 - i * 0.22;
        const angle = spin * speed + (Math.PI * 2 * i / 5);
        const satX = sx + Math.cos(angle) * orbitR;
        const satY = sy + Math.sin(angle) * orbitR * 0.72;
        const satR = r * (0.14 + 0.04 * Math.sin(t * 3 + i));
        const sA = alpha * (0.55 + 0.45 * Math.sin(t * 2.2 + i * 1.4)) * (1 - blink * 0.8);
        if (sA < 0.01) continue;
        const sg = ctx.createRadialGradient(satX, satY, 0, satX, satY, satR * 3.2);
        sg.addColorStop(0, `rgba(255,240,200,${sA.toFixed(2)})`);
        sg.addColorStop(0.35, `rgba(255,215,0,${(sA * 0.5).toFixed(2)})`);
        sg.addColorStop(1, `rgba(255,180,0,0)`);
        ctx.beginPath(); ctx.arc(satX, satY, satR * 3.2, 0, Math.PI * 2);
        ctx.fillStyle = sg; ctx.fill();
        ctx.beginPath(); ctx.arc(satX, satY, satR, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,250,220,${Math.min(sA * 1.2, 1).toFixed(2)})`;
        ctx.fill();
      }

      // ── BRIGHT WHITE ENERGY GLOW ──
      const glowPulse = 0.9 + 0.1 * Math.sin(t * 1.6 + phase);
      const glowR = r * (5.0 * glowPulse);
      const glow = ctx.createRadialGradient(sx, sy, r * 0.1, sx, sy, glowR);
      glow.addColorStop(0, `rgba(255,255,255,${(alpha * 0.72).toFixed(2)})`);
      glow.addColorStop(0.15, `rgba(255,255,245,${(alpha * 0.52).toFixed(2)})`);
      glow.addColorStop(0.4, `rgba(255,245,210,${(alpha * 0.22).toFixed(2)})`);
      glow.addColorStop(0.7, `rgba(255,230,160,${(alpha * 0.08).toFixed(2)})`);
      glow.addColorStop(1, `rgba(255,215,0,0)`);
      ctx.beginPath(); ctx.arc(sx, sy, glowR, 0, Math.PI * 2);
      ctx.fillStyle = glow; ctx.fill();

      // ── IMPACT BLINK (anime impact frame) ──
      if (blink > 0) {
        // White shockwave flash outward
        const blinkR = r * (12 + blink * 10);
        const blinkGrad = ctx.createRadialGradient(sx, sy, r * 0.5, sx, sy, blinkR);
        blinkGrad.addColorStop(0, `rgba(255,255,255,${(alpha * blink * 0.9).toFixed(2)})`);
        blinkGrad.addColorStop(0.3, `rgba(255,255,255,${(alpha * blink * 0.6).toFixed(2)})`);
        blinkGrad.addColorStop(0.6, `rgba(255,255,240,${(alpha * blink * 0.25).toFixed(2)})`);
        blinkGrad.addColorStop(1, `rgba(255,255,255,0)`);
        ctx.beginPath(); ctx.arc(sx, sy, blinkR, 0, Math.PI * 2);
        ctx.fillStyle = blinkGrad; ctx.fill();

        // BLACK inversion ring (perimeter inverts)
        const invR = r * (3.5 + blink * 3);
        ctx.beginPath(); ctx.arc(sx, sy, invR, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(0,0,0,${(alpha * blink * 0.8).toFixed(2)})`;
        ctx.lineWidth = r * (0.7 + blink * 0.5);
        ctx.stroke();

        // Bold black radial speed lines (like manga impact)
        const numImpact = 14;
        for (let i = 0; i < numImpact; i++) {
          const a = (Math.PI * 2 * i / numImpact) + phase;
          const len = r * (5 + blink * 7) * (0.6 + 0.4 * ((i * 7 + 3) % 5) / 5);
          const iA = alpha * blink * (0.5 + 0.5 * ((i * 13) % 7) / 7);
          ctx.beginPath();
          ctx.moveTo(sx + Math.cos(a) * r * 1.8, sy + Math.sin(a) * r * 1.8);
          ctx.lineTo(sx + Math.cos(a) * len, sy + Math.sin(a) * len);
          ctx.strokeStyle = `rgba(0,0,0,${iA.toFixed(2)})`;
          ctx.lineWidth = r * (0.3 + blink * 0.4);
          ctx.lineCap = 'round';
          ctx.stroke();
        }
      }

      // ── WHITE CORE ──
      const coreGrad = ctx.createRadialGradient(sx - r * 0.12, sy - r * 0.12, 0, sx, sy, r * 1.05);
      coreGrad.addColorStop(0, `rgba(255,255,255,${Math.min(alpha * 1.2, 1).toFixed(2)})`);
      coreGrad.addColorStop(0.35, `rgba(255,253,245,${Math.min(alpha * 1.1, 1).toFixed(2)})`);
      coreGrad.addColorStop(0.7, `rgba(255,240,200,${Math.min(alpha * 1.0, 1).toFixed(2)})`);
      coreGrad.addColorStop(1, `rgba(255,215,0,${(alpha * 0.85).toFixed(2)})`);
      ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2);
      ctx.fillStyle = coreGrad; ctx.fill();

      // Specular highlight
      ctx.beginPath(); ctx.arc(sx - r * 0.22, sy - r * 0.22, r * 0.35, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${(alpha * 0.95).toFixed(2)})`; ctx.fill();
    }
    function drawNodeUnique(sx, sy, r, alpha, t, p) {
      // Unique = singularity render. Reads --tier-unique-rgb so the
      // accretion disk / event horizon ring inherit the canonical
      // Unique tier hue when a host page reskins the canvas.
      const uniqueRgb = getCanvasTokens().tier.unique.rgb;
      // Accretion-disk particles use the Unique tier rgb at lower
      // alpha rather than introducing a second hue. Visually this
      // reads as the same hue family as the canonical rank-3 swatch
      // (the historical particle colour) without re-declaring it
      // here. When --rank-3-rgb lands in tokens.css we can swap to
      // it directly.
      const phase = p.phase || 0;
      const spin = t * 2.2 + phase;
      // Gravitational distortion — concentric rings that darken surrounding space
      const distortR = r * 8;
      const rings = 5;
      for (let i = rings; i >= 1; i--) {
        const ringR = r * 1.4 + (i / rings) * (distortR - r * 1.4);
        const warp = Math.sin(spin * 0.4 + i * 0.8) * 0.15;
        const ringAlpha = alpha * (0.06 + warp * 0.03) * (1 - i / (rings + 1));
        ctx.save();
        ctx.translate(sx, sy);
        ctx.rotate(spin * 0.12 + i * 0.3);
        ctx.scale(1, 0.55 + 0.15 * Math.sin(spin * 0.2 + i));
        ctx.beginPath(); ctx.arc(0, 0, ringR, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(0,0,0,${(ringAlpha * 2.5).toFixed(3)})`;
        ctx.lineWidth = r * (0.6 + 0.3 * Math.sin(spin * 0.3 + i * 1.2));
        ctx.stroke();
        ctx.restore();
      }
      // Big dark spinning void glow
      const voidR = r * 6;
      ctx.save();
      ctx.translate(sx, sy);
      ctx.rotate(spin * 0.3);
      const voidGrad = ctx.createRadialGradient(0, 0, r * 0.8, 0, 0, voidR);
      voidGrad.addColorStop(0, `rgba(0,0,0,${(alpha * 0.85).toFixed(2)})`);
      voidGrad.addColorStop(0.25, `rgba(10,0,20,${(alpha * 0.5).toFixed(2)})`);
      voidGrad.addColorStop(0.5, `rgba(26,5,51,${(alpha * 0.2).toFixed(2)})`);
      voidGrad.addColorStop(0.75, `rgba(${uniqueRgb},${(alpha * 0.07).toFixed(2)})`);
      voidGrad.addColorStop(1, `rgba(${uniqueRgb},0)`);
      ctx.beginPath(); ctx.arc(0, 0, voidR, 0, Math.PI * 2);
      ctx.fillStyle = voidGrad; ctx.fill();
      // Spinning dark arms (like a spiral galaxy but dark)
      for (let arm = 0; arm < 3; arm++) {
        const armAngle = (Math.PI * 2 * arm / 3) + spin * 0.7;
        ctx.beginPath();
        for (let j = 0; j <= 20; j++) {
          const frac = j / 20;
          const spiralR = r * 1.2 + frac * voidR * 0.7;
          const spiralA = armAngle + frac * Math.PI * 1.5;
          const px = Math.cos(spiralA) * spiralR;
          const py = Math.sin(spiralA) * spiralR * 0.45;
          if (j === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        ctx.strokeStyle = `rgba(0,0,0,${(alpha * 0.5).toFixed(2)})`;
        ctx.lineWidth = r * 0.5;
        ctx.stroke();
      }
      ctx.restore();
      // Accretion disk particles spinning wildly
      for (let i = 0; i < 16; i++) {
        const a = (Math.PI * 2 * i / 16) + spin * (1.5 + (i % 4) * 0.4);
        const orbitR = r * (1.6 + 0.4 * Math.sin(spin * 0.9 + i * 0.7));
        const dx = Math.cos(a) * orbitR;
        const dy = Math.sin(a) * orbitR * 0.35;
        const particleAlpha = alpha * (0.4 + 0.35 * Math.sin(spin * 2.5 + i * 1.1));
        const particleR = r * (0.1 + 0.05 * Math.sin(t * 4 + i));
        ctx.beginPath();
        ctx.arc(sx + dx, sy + dy, particleR, 0, Math.PI * 2);
        // Accretion-disk particle: lighter sibling of Unique hue.
        ctx.fillStyle = `rgba(${uniqueRgb},${Math.min(particleAlpha * 1.05, 1).toFixed(2)})`;
        ctx.fill();
      }
      // Event horizon ring — bright Unique-tier edge
      ctx.beginPath(); ctx.arc(sx, sy, r * 1.12, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${uniqueRgb},${(alpha * 0.9).toFixed(2)})`;
      ctx.lineWidth = 2; ctx.stroke();
      // Void core — fully opaque black
      ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2);
      ctx.fillStyle = '#000';
      ctx.fill();
      // Inner Unique-tier shimmer at edge of core
      ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${uniqueRgb},${(alpha * 0.5).toFixed(2)})`;
      ctx.lineWidth = r * 0.15; ctx.stroke();
    }
    function shouldLabel(skill) {
      if (state.redPillActive && state.namedMap[skill.id]) return true;
      if (state.labelMode === 'none') return false;
      if (state.labelMode === 'all') return true;
      if (state.labelMode === 'modal') return skill.type !== 'basic' || stableHash(skill.id) % 7 === 0;
      return skill.type === 'ultimate' || skill.type === 'unique';
    }

    function _canonicalSkillColor(skill) {
      if (state.colorMode === 'cluster' && skill.cluster !== undefined) {
        const hex = _readVar('--cluster-' + (Number(skill.cluster) % 8));
        const rgb = rgbFromHex(hex);
        if (rgb) return { rgb, hex };
      }
      const metaColor = state.meta && state.meta.typeColors && state.meta.typeColors[skill.type];
      if (metaColor) {
        const rgb = metaColor.rgb || rgbFromHex(metaColor.hex);
        if (rgb) return { rgb: _rgbOnly(String(rgb)), hex: metaColor.hex || '' };
      }
      return PALETTE[skill.type] || PALETTE.basic;
    }

    function _displaySkillColor(skill) {
      const canonical = _canonicalSkillColor(skill);
      // Legacy 3D graph (no World Tree layout): keep the canonical tier/cluster
      // color unchanged.
      if (!state.treeLayout) return canonical;
      // §6/§7 hero-vs-explorer split. Under the World Tree layout, color is
      // re-axed onto RANK, not type. viewMix drives the morph:
      //   hero (viewMix→0)     → single monochrome apex-gold (starless tips are
      //                          faint GOLD, never grey — grey muddies the mono
      //                          hero silhouette);
      //   explorer (viewMix→1) → the full rank ramp (grey 0-1★ bark → 2★ ramp →
      //                          apex-gold 6★). Cluster mode overrides both ends
      //                          with its per-cluster hue for the analytical view.
      const tokens = getCanvasTokens();
      const gold = tokens.apexGoldRgb;
      const amount = easeWorldTree(state.viewMix);
      const explorerRgb = state.colorMode === 'cluster'
        ? canonical.rgb
        : _rankColorRgb(skill.effectiveRank);
      return { rgb: mixRgb(gold, explorerRgb, amount), hex: canonical.hex };
    }
    // Phase 5: check reduced-motion once per draw frame (cached per graph instance)
    const _reducedMotion = () => window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function _updateViewMorph(now) {
      if (state.viewStartedAt === null) return;
      const duration = Math.max(1, state.viewDuration);
      const progress = clamp01((now - state.viewStartedAt) / duration);
      state.viewMix = lerp(state.viewFrom, state.viewTarget, easeWorldTree(progress));
      if (progress < 1) return;
      state.viewMix = state.viewTarget;
      state.viewStartedAt = null;
      state.viewPhase = state.viewTarget === 1 ? 'explorer3d' : 'hero2d';
      const done = state.viewComplete;
      state.viewComplete = null;
      if (typeof done === 'function') done(state.viewPhase);
    }

    function draw(frameNow) {
      if (!state.running) return;
      const now = Number.isFinite(frameNow) ? frameNow : performance.now();
      const mobileIdleTree = state.treeLayout
        && window.matchMedia('(max-width:700px)').matches
        && state.viewStartedAt === null
        && !state.dragging
        && !state.hoveredId
        && !state.pinnedId;
      if (mobileIdleTree && state.lastDrawAt && now - state.lastDrawAt < 32) {
        state.frame = requestAnimationFrame(draw);
        return;
      }
      state.lastDrawAt = now;
      _updateViewMorph(now);
      treeProjectionFrame = computeTreeProjection();
      const targetSlowdown = ((state.hoveredId || state.pinnedId) && !state.paused) ? 1 : 0;
      state.hoverSlowdown += (targetSlowdown - state.hoverSlowdown) * 0.035;
      // Always advance state.t so Level VI shimmer (hard lock) keeps running.
      // Under reduced-motion, freeze the idle AUTO-ROTATION angles for the hero
      // graph (non-draggable). The modal graph (draggable) can still be spun
      // manually by the user, so we don't suppress it there.
      const rmFreeze = _reducedMotion();
      if (!state.paused && state.autoRotate && !rmFreeze) state.t += 0.006 * state.rotSpeed * (1 - state.hoverSlowdown);
      ctx.clearRect(0, 0, state.width, state.height);
      state.projectedNodes = {};
      // Under reduced motion, lock idle rotation but retain user-controlled orbit.
      const treeMix = state.treeLayout ? easeWorldTree(state.viewMix) : 1;
      const idleRy = rmFreeze ? 0 : state.t * 0.16;
      const idleRx = rmFreeze ? 0 : Math.sin(state.t * 0.055) * 0.20;
      const ry = state.treeLayout
        ? treeMix * (idleRy + state.orbitY)
        : (_opts.draggable ? idleRy + state.orbitY : (rmFreeze ? state.orbitY : idleRy + state.mx * 0.10));
      const rx = state.treeLayout
        ? treeMix * (idleRx + state.orbitX)
        : (_opts.draggable ? idleRx + state.orbitX : (rmFreeze ? state.orbitX : idleRx + state.my * 0.055));
      const rw = state.t * 0.12;

      const xf = {};
      const positionIds = state.treeLayout ? Object.keys(state.heroPose) : Object.keys(state.positions);
      positionIds.forEach(id => {
        let p;
        if (state.treeLayout) {
          const heroPoint = state.heroPose[id];
          const fieldPoint = state.fieldPose[id] || heroPoint;
          p = {
            x: lerp(heroPoint.x, fieldPoint.x, treeMix),
            y: lerp(heroPoint.y, fieldPoint.y, treeMix),
            z: lerp(heroPoint.z || 0, fieldPoint.z || 0, treeMix),
            w: 0,
            phase: heroPoint.phase,
          };
        } else {
          p = state.positions[id];
        }
        if (p._satellite === 'orphan') {
          const s = p._orbitSpeed, amp = p._orbitAmp;
          p = {
            x: p.x + Math.cos(state.t * s + p._phX) * amp,
            y: p.y + Math.sin(state.t * s * 1.3 + p._phY) * amp,
            z: p.z + Math.sin(state.t * s * 0.7 + p._phZ) * amp,
            w: p.w || 0,
            phase: p.phase,
          };
        }
        if (state.treeLayout) {
          // Yggdrasil is spatially 3D, not a fourth-dimensional semantic cloud.
          p = rotX(rotY(p, ry), rx);
        } else if (state.layoutMode === 'semantic' || state.layoutMode === 'spectral') {
          // 4D Rotation Planes
          p = rotY(rotX(p, rx), ry);
          p = rotXW(p, rw);
          p = rotYW(p, rw * 0.5);
        } else {
          // Legacy 3D Rotation
          p = rotX(rotY(p, ry), rx);
        }
        xf[id] = p;
      });

      const neighborSet = new Set();
      const directNeighborSet = new Set();
      const focusId = state.pinnedId || state.hoveredId;
      if (focusId) {
        neighborSet.add(focusId);
        directNeighborSet.add(focusId);
        if (state.treeLayout) {
          asIdSet(state.ancestorsById[focusId]).forEach(id => neighborSet.add(id));
          asIdSet(state.descendantsById[focusId]).forEach(id => neighborSet.add(id));
          asIdSet(state.directNeighborsById[focusId]).forEach(id => directNeighborSet.add(id));
        } else {
          const focusSkill = state.skills.find(s => s.id === focusId);
          if (focusSkill) focusSkill.prerequisites.forEach(pid => { neighborSet.add(pid); directNeighborSet.add(pid); });
          state.skills.forEach(s => {
            if (s.prerequisites.includes(focusId)) { neighborSet.add(s.id); directNeighborSet.add(s.id); }
          });
        }
      }
      const hovering = Boolean(focusId);
      const isSearchActive = Boolean(state.searchText);
      const searchQuery = isSearchActive ? state.searchText.toLowerCase() : '';
      // Prefix-mode search: `/foo` matches only skill ID/name (slash
      // form), `@bar` matches only contributor handles. Everything
      // else is a free-text match across id, name, description, title
      // and handle. This mirrors the routes a user thinks in.
      let searchMode = 'free';
      let searchTerm = searchQuery;
      if (isSearchActive) {
        if (searchQuery.startsWith('/')) { searchMode = 'slash'; searchTerm = searchQuery.slice(1); }
        else if (searchQuery.startsWith('@')) { searchMode = 'handle'; searchTerm = searchQuery.slice(1); }
      }
      function _searchMatches(skill) {
        if (!isSearchActive) return true;
        if (!searchTerm) return true;
        const namedId = (state.namedMap && state.namedMap[skill.id]) || '';
        const handle = namedId ? namedId.split('/')[0] : '';
        const slugSlash = namedId ? namedId.split('/')[1] : '';
        const id = (skill.id || '').toLowerCase();
        const name = (skill.name || '').toLowerCase();
        const desc = (skill.description || '').toLowerCase();
        const title = (state.titleMap && state.titleMap[skill.id] || '').toLowerCase();
        if (searchMode === 'slash') {
          return id.includes(searchTerm) || name.includes(searchTerm) || (slugSlash || '').toLowerCase().includes(searchTerm);
        }
        if (searchMode === 'handle') {
          return (handle || '').toLowerCase().includes(searchTerm);
        }
        return id.includes(searchTerm) || name.includes(searchTerm) || desc.includes(searchTerm) ||
          title.includes(searchTerm) || namedId.toLowerCase().includes(searchTerm);
      }
      const legendHovering = Boolean(state.legendHoverType || state.legendHoverRank);
      const legendFiltering = Boolean(state.legendFilterType || state.legendFilterRank);
      state.skills.forEach(skill => {
        let targetVis;
        if (hovering) {
          targetVis = skill.id === focusId ? 1.0 : neighborSet.has(skill.id) ? 0.88 : 0.12;
        } else if (legendHovering) {
          const mt = !state.legendHoverType || skill.type === state.legendHoverType;
          const mr = !state.legendHoverRank || skill.level === state.legendHoverRank;
          targetVis = (mt && mr) ? 1.0 : 0.12;
        } else if (legendFiltering) {
          const mt = !state.legendFilterType || skill.type === state.legendFilterType;
          const mr = !state.legendFilterRank || skill.level === state.legendFilterRank;
          const matchesLegend = mt && mr;
          if (isSearchActive) {
            targetVis = (matchesLegend && _searchMatches(skill)) ? 1.0 : 0.12;
          } else {
            targetVis = matchesLegend ? 1.0 : 0.12;
          }
        } else if (isSearchActive) {
          targetVis = _searchMatches(skill) ? 1.0 : 0.12;
        } else {
          targetVis = 1.0;
        }
        if (state.redPillActive && !state.namedMap[skill.id]) targetVis = Math.min(targetVis, 0.07);
        if (state.nodeAlphas[skill.id] === undefined) state.nodeAlphas[skill.id] = targetVis;
        state.nodeAlphas[skill.id] += (targetVis - state.nodeAlphas[skill.id]) * 0.15;
      });
      state.stars.forEach(star => {
        const treeStars = Boolean(state.treeLayout);
        let p;
        if (treeStars) {
          // Keep the hero DAG front-facing, but let the surrounding starfield
          // orbit on its own depth axis so the atlas reads as a place, not a
          // flat rotating texture.
          const heroStarRy = rmFreeze ? 0 : state.t * 0.42;
          const heroStarRx = rmFreeze ? 0 : Math.sin(state.t * 0.14) * 0.16;
          p = rotX(rotY(star, lerp(heroStarRy, ry, treeMix)), lerp(heroStarRx, rx, treeMix));
        } else {
          p = rotX(rotY(star, ry), rx);
          if (state.layoutMode === 'semantic' || state.layoutMode === 'spectral') {
            p = rotXW(p, rw);
            p = rotYW(p, rw * 0.5);
          }
        }

        let pr = project(p);
        let depth = 1;
        if (treeStars && treeMix < 0.999 && treeProjectionFrame) {
          const config = treeProjectionFrame;
          const depthRange = 1400 * state.scale;
          depth = Math.max(0.45, Math.min(1.65, 1 - p.z / depthRange));
          const px = (p.x - config.bounds.centerX) * config.spread;
          const py = (p.y - config.bounds.centerY) * config.spread;
          const heroSx = state.width * config.heroCenterRatio + px * config.heroFit * depth;
          const heroSy = state.height * 0.5 + py * config.heroFit * depth;
          const heroScale = config.heroFit * depth;
          pr = {
            sx: lerp(heroSx, pr.sx, treeMix),
            sy: lerp(heroSy, pr.sy, treeMix),
            scale: lerp(heroScale, pr.scale, treeMix),
          };
        }
        if (pr.scale < 0.01) return;
        const twinkle = rmFreeze ? 1 : 0.86 + 0.14 * Math.sin(state.t * 1.3 + star.phase * 1.7);
        const depthAlpha = treeStars ? Math.max(0.72, Math.min(1.12, depth)) : 1;
        ctx.beginPath();
        ctx.arc(pr.sx, pr.sy, star.size * pr.scale * 1.55, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${(star.alpha * Math.min(pr.scale * 2, 1) * twinkle * depthAlpha).toFixed(2)})`;
        ctx.fill();
      });
      const skillById = Object.fromEntries(state.skills.map(skill => [skill.id, skill]));
      const edges = [];
      if (state.treeLayout) {
        state.treeEdges.forEach(edge => {
          if (!xf[edge.from] || !xf[edge.to]) return;
          edges.push({ ...edge, avgZ: (xf[edge.to].z + xf[edge.from].z) / 2 });
        });
      } else {
        state.skills.forEach(skill => {
          if (!xf[skill.id]) return;
          skill.prerequisites.forEach(pid => {
            if (!xf[pid]) return;
            edges.push({ from: pid, to: skill.id, type: skill.type, avgZ: (xf[skill.id].z + xf[pid].z) / 2 });
          });
        });
      }
      edges.sort((a, b) => a.avgZ - b.avgZ);
      const treeAmount = state.treeLayout ? easeWorldTree(state.viewMix) : 1;
      const heroCenterValue = state.treeLayout
        ? parseFloat(getComputedStyle(canvas.parentElement).getPropertyValue('--hero-tree-center-x'))
        : NaN;
      const heroCenterRatio = Number.isFinite(heroCenterValue)
        ? heroCenterValue
        : (window.matchMedia('(max-width:700px)').matches ? 0.5 : 0.72);
      const axisX = lerp(state.width * heroCenterRatio, state.width * 0.5, treeAmount);
      const nodeMeta = state.treeLayout && state.treeLayout.nodeMeta ? state.treeLayout.nodeMeta : {};

      // §2 ghost armature render + §3 structural-edge re-routing. Drawn BEFORE
      // the real edges/nodes so the synthetic skeleton drapes behind the wood.
      // Only under the World Tree layout; ghosts are faint and data-free.
      if (state.treeLayout && state.treeLayout.armature) {
        const armature = state.treeLayout.armature;
        const ghostPose = state.treeLayout.ghostPose || {};
        const structuralRoutes = state.treeLayout.structuralRoutes || {};
        const gTokens = getCanvasTokens();
        // Armature reads GOLD in the hero (part of the monochrome silhouette),
        // fading to a neutral muted mesh as the explorer takes over so the rank
        // ramp owns the color channel. treeAmount: 0 hero -> 1 explorer.
        const meshRgb = mixRgb(gTokens.apexGoldRgb, gTokens.mutedRgb, treeAmount);
        const meshAlpha = lerp(0.22, 0.10, treeAmount);

        // (a) trunk spine — connect consecutive spine waypoints into one column.
        ctx.lineCap = 'round';
        const spine = armature.spine || [];
        if (spine.length > 1) {
          ctx.beginPath();
          let started = false;
          spine.forEach(wp => {
            const pr = _projectGhost(ghostPose[wp.key], ry, rx, treeMix);
            if (!pr) return;
            if (!started) { ctx.moveTo(pr.sx, pr.sy); started = true; }
            else ctx.lineTo(pr.sx, pr.sy);
          });
          ctx.strokeStyle = `rgba(${meshRgb},${(meshAlpha * 1.15).toFixed(2)})`;
          ctx.lineWidth = lerp(3.2, 2.0, treeAmount) * state.scale;
          ctx.stroke();
        }
        // (b) boughs + roots — each anchor drapes back to its parent waypoint.
        const limbs = (armature.boughAnchors || []).concat(armature.rootAnchors || []);
        limbs.forEach(wp => {
          const parent = wp.parentKey ? ghostPose[wp.parentKey] : null;
          const pa = _projectGhost(parent, ry, rx, treeMix);
          const pb = _projectGhost(ghostPose[wp.key], ry, rx, treeMix);
          if (!pa || !pb) return;
          ctx.beginPath();
          ctx.moveTo(pa.sx, pa.sy);
          ctx.lineTo(pb.sx, pb.sy);
          ctx.strokeStyle = `rgba(${meshRgb},${(meshAlpha * (wp.level ? 0.6 : 0.85)).toFixed(2)})`;
          ctx.lineWidth = lerp(2.0, 1.2, treeAmount) * (wp.level ? 0.7 : 1) * state.scale;
          ctx.stroke();
        });
        // (c) reserved taproot stub below the collar (faint — no 6★ today).
        if (armature.taproot && armature.collarKey) {
          const pa = _projectGhost(ghostPose[armature.collarKey], ry, rx, treeMix);
          const pb = _projectGhost(ghostPose[armature.taprootKey], ry, rx, treeMix);
          if (pa && pb) {
            ctx.beginPath();
            ctx.moveTo(pa.sx, pa.sy);
            ctx.lineTo(pb.sx, pb.sy);
            ctx.strokeStyle = `rgba(${meshRgb},${(meshAlpha * 0.5).toFixed(2)})`;
            ctx.lineWidth = lerp(2.6, 1.6, treeAmount) * state.scale;
            ctx.stroke();
          }
        }
        // (d) unique dark-constellation stems — single-side ghost spires the
        // unique nodes stand on. Painted from the dark Unique palette, never the
        // rank ramp (§2.2). Only visible once the explorer opens (treeAmount>0).
        if (treeAmount > 0.02) {
          const uniqueRgb = gTokens.tier.unique.rgb;
          (armature.outsideAnchors || []).forEach(wp => {
            const pb = _projectGhost(ghostPose[wp.key], ry, rx, treeMix);
            if (!pb) return;
            // stem drops from the anchor toward the ground line for a "standing
            // stone" footing; use the collar y at the same x as a faint base.
            const base = _projectGhost({ x: wp.x, y: armature.groundY, z: wp.z }, ry, rx, treeMix);
            if (base) {
              ctx.beginPath();
              ctx.moveTo(base.sx, base.sy);
              ctx.lineTo(pb.sx, pb.sy);
              ctx.strokeStyle = `rgba(${uniqueRgb},${(0.18 * treeAmount).toFixed(2)})`;
              ctx.lineWidth = 1.1 * state.scale;
              ctx.stroke();
            }
          });
        }

        // (e) structural-edge re-routing — draw each structural route as a curve
        // draping through its ghost waypoints instead of a straight arc. Keyed by
        // the same edgeKey('src','tgt') form the layout emits. Non-structural
        // grafts are NOT here; they stay as the faint direct arcs below.
        Object.keys(structuralRoutes).forEach(key => {
          const route = structuralRoutes[key];
          if (!Array.isArray(route) || route.length < 2) return;
          const pts = route
            .map(stop => _routeStop(stop, xf, ghostPose, ry, rx, treeMix))
            .filter(Boolean);
          if (pts.length < 2) return;
          // endpoints are real nodes; color by the route target's rank so the
          // draped wood inherits the rank ramp (matches the node it feeds).
          const tgtId = route[0] && route[0].kind === 'node' ? route[0].id : null;
          const tgtSkill = tgtId ? skillById[tgtId] : null;
          const col = tgtSkill ? _displaySkillColor(tgtSkill) : { rgb: meshRgb };
          const fromVis = tgtId && state.nodeAlphas[tgtId] !== undefined ? state.nodeAlphas[tgtId] : 1.0;
          ctx.beginPath();
          ctx.moveTo(pts[0].sx, pts[0].sy);
          for (let i = 1; i < pts.length; i += 1) {
            const prev = pts[i - 1];
            const cur = pts[i];
            const midx = (prev.sx + cur.sx) / 2;
            const midy = (prev.sy + cur.sy) / 2;
            ctx.quadraticCurveTo(prev.sx, prev.sy, midx, midy);
            if (i === pts.length - 1) ctx.lineTo(cur.sx, cur.sy);
          }
          ctx.strokeStyle = `rgba(${col.rgb},${(lerp(0.30, 0.42, treeAmount) * fromVis).toFixed(2)})`;
          ctx.lineWidth = lerp(1.5, 1.15, treeAmount) * state.scale;
          ctx.stroke();
        });
      }
      // Structural edges already drawn as draped routes above are still redrawn
      // by the direct-arc pass below for hover emphasis; the route is the resting
      // silhouette, the arc carries neighbor-highlight state.
      // §8 perf: key set precomputed in setTreeLayout, not rebuilt per frame.
      const structuralRouteKeys = state.structuralRouteKeys || null;
      edges.forEach(edge => {
        const pa = project(xf[edge.from]), pb = project(xf[edge.to]);
        const targetSkill = skillById[edge.to] || { type: edge.type || 'basic' };
        const col = _displaySkillColor(targetSkill);
        const depthAlpha = Math.min(Math.max((xf[edge.to].z + 430 * state.scale) / (860 * state.scale), 0.08), 1);
        const isNeighborEdge = hovering && neighborSet.has(edge.from) && neighborSet.has(edge.to);
        const fromVis = state.nodeAlphas[edge.from] !== undefined ? state.nodeAlphas[edge.from] : 1.0;
        const toVis = state.nodeAlphas[edge.to] !== undefined ? state.nodeAlphas[edge.to] : 1.0;
        const edgeVis = (fromVis + toVis) / 2;
        const structural = edge.structural !== false;
        // A structural edge already draped as a ghost route (drawn above) only
        // needs a faint direct-arc echo at rest — the route is the resting
        // silhouette. On neighbor-highlight it flares to full weight.
        const drapedRoute = structural && structuralRouteKeys
          && structuralRouteKeys.has(edge.from + ' ' + edge.to);
        const structuralArcScale = (drapedRoute && !isNeighborEdge) ? 0.35 : 1;
        const baseEdgeAlpha = (isNeighborEdge
          ? 0.78
          : (structural ? lerp(0.62, 0.40, treeAmount) : lerp(0.07, 0.12, treeAmount))) * structuralArcScale;
        const branchCurve = lerp(1, 0.42, treeAmount);
        const middleY = (pa.sy + pb.sy) / 2;
        const fromZone = nodeMeta[edge.from] && nodeMeta[edge.from].zone;
        const toZone = nodeMeta[edge.to] && nodeMeta[edge.to].zone;
        const trunkEdge = fromZone === 'root' && toZone === 'crown';
        const axisPull = structural ? (trunkEdge ? 0.34 : 0.15) : 0.02;
        ctx.beginPath();
        ctx.moveTo(pa.sx, pa.sy);
        if (branchCurve > 0.001) {
          ctx.bezierCurveTo(
            lerp(pa.sx, axisX, axisPull * branchCurve),
            pa.sy + (middleY - pa.sy) * branchCurve * 0.68,
            lerp(pb.sx, axisX, axisPull * branchCurve * 0.34),
            pb.sy + (middleY - pb.sy) * branchCurve * 0.60,
            pb.sx,
            pb.sy
          );
        } else {
          ctx.lineTo(pb.sx, pb.sy);
        }
        ctx.strokeStyle = `rgba(${col.rgb},${(depthAlpha * baseEdgeAlpha * edgeVis).toFixed(2)})`;
        // Line weights locked per DESIGN.md ▸ Graph Canvas. See
        // LINE_WEIGHTS at the top of this file.
        const lw = isNeighborEdge ? LINE_WEIGHTS.highlighted : LINE_WEIGHTS.default;
        const edgeWidth = edge.type === 'ultimate' ? lw.ultimate : lw.other;
        const structuralWidth = trunkEdge ? 1.34 : 1.16;
        ctx.lineWidth = isNeighborEdge ? edgeWidth : edgeWidth * (structural ? structuralWidth : 0.58);
        ctx.stroke();
      });
      const nodes = state.skills.map(skill => ({ skill, z: xf[skill.id] ? xf[skill.id].z : -9999 })).sort((a, b) => a.z - b.z);
      const labelNodes = [];
      nodes.forEach(({ skill }) => {
        const p = xf[skill.id]; if (!p) return;
        const pr = project(p);
        if (pr.scale <= 0) return;
        state.projectedNodes[skill.id] = pr;

        const vis = state.nodeAlphas[skill.id] !== undefined ? state.nodeAlphas[skill.id] : 1.0;
        if (vis <= 0) return;

        // Hyperspace Perspective: Two-stage projection with W-depth fog
        const depthAlpha = Math.min(1, Math.max(0.18, (pr.z / 650 + 1) * (pr.w / 600 + 1)));

        const col = _displaySkillColor(skill);

        const isPinned = state.pinnedId === skill.id;
        const isHovered = state.hoveredId === skill.id;
        // §6 radius-by-rank: under the World Tree layout, size reads from the
        // joined effective rank; the legacy 3D graph keeps the level-glyph path.
        const baseR = state.treeLayout
          ? NODE_RADII.get(skill.effectiveRank, skill.type)
          : NODE_RADII.get(skill.level, skill.type);
        const pulse = 0.84 + 0.16 * Math.sin(state.t * 2.2 + p.phase);

        const specialMix = state.treeLayout ? easeWorldTree(state.viewMix) : 1;
        const nodeRadius = baseR * state.scale * pr.scale * pulse;
        if (skill.level === '6★' && specialMix > 0) {
          if (specialMix < 1) drawNode(pr.sx, pr.sy, nodeRadius, { rgb: getCanvasTokens().apexGoldRgb }, depthAlpha * vis * (1 - specialMix));
          drawNodeVI(pr.sx, pr.sy, nodeRadius, depthAlpha * vis * specialMix, state.t, p);
        } else if (skill.type === 'unique' && specialMix > 0) {
          if (specialMix < 1) drawNode(pr.sx, pr.sy, nodeRadius, { rgb: getCanvasTokens().apexGoldRgb }, depthAlpha * vis * (1 - specialMix));
          drawNodeUnique(pr.sx, pr.sy, nodeRadius, depthAlpha * vis * specialMix, state.t, p);
        } else if (state.redPillActive && state.namedMap && state.namedMap[skill.id] && specialMix > 0.98) {
          drawNodeNamed(pr.sx, pr.sy, baseR * state.scale * pr.scale * pulse, depthAlpha * vis);
        } else {
          drawNode(pr.sx, pr.sy, nodeRadius, col, depthAlpha * vis);
        }

        const rankVal = parseInt(skill.level, 10) || 0;
        const priorityScore = rankVal + (stableHash(skill.id) % 3);
        const shouldPop = (pr.scale > 1.25 && priorityScore >= 6) || isPinned || isHovered;

        if (state.labelMode === 'all' || (state.labelMode === 'priority' && shouldPop)) {
          labelNodes.push({ skill, pr, depthAlpha, colRgb: col.rgb });
        }
      });
      function drawLabel(skill, highlighted, forcedDepthAlpha, forcedColRgb) {
        const p = xf[skill.id]; if (!p) return;
        const pr = project(p);
        const depthAlpha = forcedDepthAlpha !== undefined ? forcedDepthAlpha : Math.min(Math.max((p.z + 430 * state.scale) / (860 * state.scale), 0), 1);
        if (!highlighted && depthAlpha < 0.22) return;
        const vis = state.nodeAlphas[skill.id] !== undefined ? state.nodeAlphas[skill.id] : 1.0;
        const labelAlpha = highlighted ? 1.0 : depthAlpha * Math.max(0.22, vis) * 0.9;
        if (labelAlpha < 0.04) return;
        const isNamedHover = state.redPillActive && state.namedMap && state.namedMap[skill.id];
        const tokens = getCanvasTokens();
        const colRgb = forcedColRgb || (isNamedHover
          ? tokens.honorRedRgb
          : ((PALETTE[skill.type] || PALETTE.basic).rgb));

        // Registry-3d aesthetic: Use mono font at reduced size for non-highlighted labels
        const size = highlighted ? (skill.type === 'ultimate' ? 13 : 10) : 9;
        let role = (highlighted || isNamedHover || state.labelMode === 'all') 
          ? (skill.type === 'ultimate' ? 'display' : 'handle') 
          : 'handle';

        ctx.font = canvasFont(role, size * pr.scale * 1.16);
        const namedId = (state.redPillActive && state.namedMap && state.namedMap[skill.id]) ? state.namedMap[skill.id] : null;
        if (namedId) {
          const parts = namedId.split('/');
          if (parts.length === 2) {
            // Pre-named/demoted handle is the slate block (████████) — no "@".
            const isRedHandle = parts[0] === (window.REDACTED_BLOCK || '████████');
            const handleTxt = isRedHandle ? parts[0] : '@' + parts[0];
            const slashTxt = '/' + parts[1];
            const isOrigin = state.originMap && state.originMap[skill.id];
            ctx.textAlign = 'left';
            const w1 = ctx.measureText(handleTxt).width;
            const w2 = ctx.measureText(slashTxt).width;
            const badgeW = isOrigin ? 20 * pr.scale : 0;
            const totalW = w1 + w2 + badgeW;
            const startX = pr.sx - totalW / 2;
            // Redacted handle renders slate, never honor-red.
            ctx.fillStyle = isRedHandle
              ? `rgba(148,163,184,${labelAlpha.toFixed(2)})`
              : `rgba(${tokens.honorRedRgb},${labelAlpha.toFixed(2)})`;
            ctx.fillText(handleTxt, startX, pr.sy + 18 * pr.scale);
            const rm = state.meta && state.meta.levelColors ? state.meta.levelColors[skill.level || 0] : null;
            ctx.fillStyle = rm ? rm.hex : `rgba(${colRgb},1)`;
            ctx.globalAlpha = labelAlpha;
            ctx.fillText(slashTxt, startX + w1, pr.sy + 18 * pr.scale);
            ctx.globalAlpha = 1.0;
            if (isOrigin) {
              ctx.save();
              ctx.translate(startX + w1 + w2 + 10 * pr.scale, pr.sy + 18 * pr.scale);
              ctx.scale(0.75 * pr.scale, 0.75 * pr.scale);
              ctx.translate(-12, -12);
              ctx.lineWidth = 1.5;
              ctx.lineCap = 'round';
              ctx.lineJoin = 'round';
              ctx.strokeStyle = `rgba(${tokens.apexGoldRgb}, ${labelAlpha.toFixed(2)})`;
              ORIGIN_PATHS.forEach(p => ctx.stroke(p));
              ctx.restore();
            }
            return;
          }
        }

        ctx.textAlign = 'center';
        const labelText = namedId || (state.showTitles && state.titleMap && state.titleMap[skill.id] ? state.titleMap[skill.id] : '/' + skill.id);
        ctx.fillStyle = `rgba(${colRgb},${labelAlpha.toFixed(2)})`;
        ctx.fillText(labelText, pr.sx, pr.sy + 18 * pr.scale);
      }
      labelNodes.forEach(({ skill, depthAlpha, colRgb }) => {
        const vis = state.nodeAlphas[skill.id] !== undefined ? state.nodeAlphas[skill.id] : 1.0;
        if (vis <= 0.95) drawLabel(skill, false, depthAlpha, colRgb);
      });
      labelNodes.forEach(({ skill, depthAlpha, colRgb }) => {
        const vis = state.nodeAlphas[skill.id] !== undefined ? state.nodeAlphas[skill.id] : 1.0;
        if (vis > 0.95) drawLabel(skill, true, depthAlpha, colRgb);
      });

      if (state.colorMode === 'cluster' && state.meta && state.meta.clusterNames) {
        // Find cluster with highest W+Z prominence
        let bestCluster = 0, bestScore = -Infinity;
        state.skills.forEach((skill) => {
          const pr = state.projectedNodes[skill.id];
          if (!pr) return;
          const score = pr.z + pr.w;
          if (score > bestScore) { bestScore = score; bestCluster = skill.cluster; }
        });
        const cName = state.meta.clusterNames[bestCluster];
        if (cName) {
          ctx.save();
          ctx.fillStyle = getCanvasTokens().apexGold;
          ctx.font = canvasFont('handle', 12);
          ctx.textAlign = 'center';
          ctx.globalAlpha = 0.85;
          ctx.fillText(`Hyper-Domain: ${cName}`, state.width / 2, state.height - 24);
          ctx.restore();
        }
      }

      // Final pass: redraw unique void cores on top of everything (labels, other effects)
      nodes.forEach(({ skill }) => {
        if (skill.type !== 'unique') return;
        const specialMix = state.treeLayout ? easeWorldTree(state.viewMix) : 1;
        if (specialMix <= 0) return;
        const p = xf[skill.id]; if (!p) return;
        const pr = project(p);
        if (pr.scale <= 0) return;
        const pulse = 0.84 + 0.16 * Math.sin(state.t * 2.2 + p.phase);
        const baseR = NODE_RADII.unique;
        const r = baseR * state.scale * pr.scale * pulse;
        ctx.save();
        ctx.globalAlpha = specialMix;
        ctx.beginPath(); ctx.arc(pr.sx, pr.sy, r * 1.05, 0, Math.PI * 2);
        ctx.fillStyle = '#000';
        ctx.fill();
        ctx.beginPath(); ctx.arc(pr.sx, pr.sy, r * 1.05, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(${getCanvasTokens().tier.unique.rgb},0.5)`;
        ctx.lineWidth = r * 0.15; ctx.stroke();
        ctx.restore();
      });
      if (_opts.hoverable && state.tooltipEl) {
        const displayId = state.pinnedId || state.hoveredId;
        const pr = state.projectedNodes[displayId];
        if (displayId && pr) {
          if (displayId !== state.lastHoveredId) {
            const skill = state.skills.find(s => s.id === displayId);
            const col = PALETTE[skill.type] || PALETTE.basic;
            const typeClass = `skill-tooltip-type-${skill.type}`;
            const rm = skill.level ? RANK_META[skill.level] : null;
            // §6.1 hover card two channels under the World Tree layout: rank
            // (color) + structural class (glyph). glyph comes from the frozen
            // resolveSemantics contract (nodeMeta[id].glyph); fall back to a
            // type→glyph map for the legacy 3D graph. Name color reads the rank
            // ramp under the tree so color = rank end-to-end.
            const _tlMeta = (state.treeLayout && state.treeLayout.nodeMeta
              && state.treeLayout.nodeMeta[skill.id]) || null;
            const _glyphMap = { basic: '○', extra: '◇', ultimate: '◆', unique: '◉' };
            const structGlyph = (_tlMeta && _tlMeta.glyph) || _glyphMap[skill.type] || '○';
            const nameRgb = state.treeLayout ? _rankColorRgb(skill.effectiveRank) : col.rgb;

            state.tooltipEl.textContent = '';

            const nameDiv = document.createElement('div');
            nameDiv.className = 'skill-tooltip-name';
            nameDiv.style.color = `rgba(${nameRgb},1)`;
            nameDiv.textContent = skill.name;
            state.tooltipEl.appendChild(nameDiv);

            const namedId = (state.namedMap && state.namedMap[skill.id]) || null;
            // Tooltip rows route through CSS classes (.gst-named-id /
            // .gst-skill-id) so Honor Red / muted slate / mono font
            // come from tokens.css. The slug half is colour-locked to
            // the skill's rank token per DESIGN.md (Honor Red is for
            // the @handle only).
            if (namedId) {
              const parts = namedId.split('/');
              const namedLineDiv = document.createElement('div');
              namedLineDiv.className = 'gst-named-id';
              
              const handleSpan = document.createElement('span');
              handleSpan.className = 'gst-named-handle';
              // Redacted handle is the slate block (████████) — slate, no "@".
              var _gstRed = parts[0] === (window.REDACTED_BLOCK || '████████');
              if (_gstRed) {
                handleSpan.className += ' plaque__redacted-handle';
                handleSpan.setAttribute('aria-label', 'Contributor not yet revealed');
              }
              handleSpan.textContent = _gstRed ? parts[0] : '@' + parts[0];
              namedLineDiv.appendChild(handleSpan);

              if (parts.length === 2) {
                const rm2 = skill.level ? RANK_META[skill.level] : null;
                const slugColor = rm2 ? rm2.hex : `rgba(${col.rgb},1)`;
                const slugSpan = document.createElement('span');
                slugSpan.className = 'gst-named-slug';
                slugSpan.style.color = slugColor;
                slugSpan.textContent = '/' + parts[1];
                namedLineDiv.appendChild(slugSpan);
              }
              state.tooltipEl.appendChild(namedLineDiv);
            }

            const idDiv = document.createElement('div');
            idDiv.className = 'gst-skill-id';
            idDiv.textContent = skill.id;
            state.tooltipEl.appendChild(idDiv);

            const rowDiv = document.createElement('div');
            rowDiv.className = 'skill-tooltip-row';
            
            const badgeSpan = document.createElement('span');
            badgeSpan.className = `skill-tooltip-badge ${typeClass}`;
            // Lead with the structural-class glyph (§6 glyph channel), then the
            // type label. Suite reads "SUITE", fusion covers extra/fusion.
            const _typeLabel = { basic: 'BASIC', extra: 'FUSION', ultimate: 'SUITE', unique: 'UNIQUE' }[skill.type] || skill.type.toUpperCase();
            badgeSpan.textContent = structGlyph + ' ' + _typeLabel;
            rowDiv.appendChild(badgeSpan);

            // Rank color channel: a pill tinted from the rank ramp so the hover
            // card echoes the node's color = rank encoding, even for starless
            // nodes (0–1★ → grey bark).
            if (state.treeLayout) {
              const rankPill = document.createElement('span');
              const _rr = _rankColorRgb(skill.effectiveRank);
              const _rn = Math.max(0, Math.round(Number(skill.effectiveRank) || 0));
              rankPill.style.cssText = `display:inline-block;padding:.12rem .42rem;border-radius:999px;font-size:.62rem;font-weight:700;background:rgba(${_rr},.16);color:rgb(${_rr})`;
              rankPill.textContent = _rn >= 2 ? _rn + '★' : '0–1★';
              rowDiv.appendChild(rankPill);
            }

            if (rm && !state.treeLayout) {
              const rankSpan = document.createElement('span');
              rankSpan.style.cssText = `display:inline-block;padding:.12rem .42rem;border-radius:999px;font-size:.62rem;font-weight:700;background:${rm.bg};color:${rm.hex}`;
              rankSpan.textContent = skill.level;
              rowDiv.appendChild(rankSpan);
            }
            
            if (skill.effectiveLevel && skill.effectiveLevel !== skill.level) {
              const effSpan = document.createElement('span');
              effSpan.className = 'gst-effective-pill';
              effSpan.textContent = 'effective ' + skill.effectiveLevel;
              rowDiv.appendChild(effSpan);
            }
            state.tooltipEl.appendChild(rowDiv);

            if (skill.demerits && skill.demerits.length) {
              const demeritDiv = document.createElement('div');
              demeritDiv.className = 'gst-demerit-note';
              demeritDiv.textContent = `${skill.demerits.length} demerit${skill.demerits.length === 1 ? '' : 's'}`;
              state.tooltipEl.appendChild(demeritDiv);
            }

            const addBtn = document.createElement('button');
            addBtn.className = 'graph-tooltip-add';
            addBtn.title = 'Add to collection';
            addBtn.setAttribute('aria-label', 'Add to collection');
            addBtn.textContent = '+';
            state.tooltipEl.appendChild(addBtn);

            if (skill.level) state.tooltipEl.setAttribute('data-level', skill.level);
            else state.tooltipEl.removeAttribute('data-level');
            state.lastHoveredId = displayId;
            if (addBtn) {
              addBtn.addEventListener('mousedown', e => { e.stopPropagation(); e.preventDefault(); });
              addBtn.addEventListener('click', e => {
                e.stopPropagation();
                if (!state.collection.includes(displayId)) {
                  state.collection.push(displayId);
                  renderCollection();
                }
              });
            }
          }
          if (state.pinnedId) {
            if (!state.pinnedPos) {
              let tx = pr.sx + 18, ty = pr.sy - 34;
              tx = Math.min(tx, state.width - 250); ty = Math.max(ty, 8);
              state.pinnedPos = { left: tx + 'px', top: ty + 'px' };
            }
            state.tooltipEl.style.left = state.pinnedPos.left;
            state.tooltipEl.style.top = state.pinnedPos.top;
          } else {
            let tx = pr.sx + 18, ty = pr.sy - 34;
            tx = Math.min(tx, state.width - 250); ty = Math.max(ty, 8);
            state.tooltipEl.style.left = tx + 'px';
            state.tooltipEl.style.top = ty + 'px';
          }
          state.tooltipEl.style.display = 'block';
          state.tooltipEl.classList.toggle('pinned', Boolean(state.pinnedId));
        } else if (!state.pinnedId) {
          state.tooltipEl.style.display = 'none';
          state.lastHoveredId = null;
        }
      }
      // ── Neighbor mini-cards when pinned ──
      if (_opts.hoverable && state.neighborCardsEl) {
        if (state.pinnedId && directNeighborSet.size > 1) {
          const neighbors = [...directNeighborSet].filter(id => id !== state.pinnedId);
          if (state._neighborIds !== neighbors.join(',')) {
            state._neighborIds = neighbors.join(',');
            state.neighborCardsEl.textContent = '';
            neighbors.forEach(nid => {
              const ns = state.skills.find(s => s.id === nid);
              if (!ns) return;
              const col = PALETTE[ns.type] || PALETTE.basic;
              const card = document.createElement('div');
              card.className = 'graph-neighbor-card';
              card.dataset.nid = nid;
              card.dataset.type = ns.type || 'basic';
              
              const span = document.createElement('span');
              span.style.color = `rgba(${col.rgb},.9)`;
              span.textContent = ns.name;
              card.appendChild(span);
              
              card.addEventListener('mousedown', e => e.stopPropagation());
              card.addEventListener('click', e => {
                e.stopPropagation();
                state.pinnedId = nid;
                state.pinnedPos = null;
                state.lastHoveredId = null;
                state._neighborIds = null;
              });
              state.neighborCardsEl.appendChild(card);
            });
          }
          neighbors.forEach(nid => {
            const pr = state.projectedNodes[nid];
            const card = state.neighborCardsEl.querySelector(`[data-nid="${nid}"]`);
            if (pr && card) {
              card.style.left = pr.sx + 'px';
              card.style.top = (pr.sy - 18) + 'px';
              card.style.display = '';
            } else if (card) {
              card.style.display = 'none';
            }
          });
          state.neighborCardsEl.style.display = '';
        } else {
          if (state._neighborIds) {
            state._neighborIds = null;
            state.neighborCardsEl.textContent = '';
          }
          state.neighborCardsEl.style.display = 'none';
        }
      }
      state.frame = requestAnimationFrame(draw);
    }

    function start() {
      if (state.running) return;
      state.running = true;
      draw();
    }

    function stop() {
      state.running = false;
      if (state.frame) cancelAnimationFrame(state.frame);
      state.frame = null;
    }

    resize();
    // ── INTERACTIVE CHROME ──────────────────────────────────────
    // Created once even if options.hoverable is false at startup.
    // setInteractive(true) will show/enable these elements later
    // when the hero graph goes fullscreen.
    const _interactiveReady = options.hoverable || options._prepareInteractive;
    if (_interactiveReady) {
      const tip = document.createElement('div');
      tip.className = 'skill-tooltip';
      canvas.parentElement.appendChild(tip);
      state.tooltipEl = tip;

      const neighborCards = document.createElement('div');
      neighborCards.className = 'graph-neighbor-cards';
      canvas.parentElement.appendChild(neighborCards);
      state.neighborCardsEl = neighborCards;

      const skillPanel = document.createElement('div');
      skillPanel.className = 'graph-skill-panel';
      skillPanel.style.display = 'none';
      canvas.parentElement.appendChild(skillPanel);
      state.skillPanelEl = skillPanel;
      skillPanel.addEventListener('mousedown', e => e.stopPropagation());

      const collectionPanel = document.createElement('div');
      collectionPanel.className = 'graph-collection-panel graph-collection-panel--responsive';
      collectionPanel.setAttribute('data-interactive-chrome', '');
      collectionPanel.style.display = 'none';
      // Floating window: position it at top left by default
      collectionPanel.style.position = 'absolute';
      collectionPanel.style.left = '1.5rem';
      collectionPanel.style.top = '60px';
      collectionPanel.style.zIndex = '30';

      // Collection panel chrome — uses sprite icons for copy / clear so
      // it inherits the same icon vocabulary as the rest of the site.
      // Internal `.gst-honor` class colours the "Named" / "named"
      // accents via tokens.css (--honor-red), no inline hex codes.
      // The graphMode prop swaps the panel title between "Collection"
      // (public registry) and "Claimed skills" (per-user local graph).
      const collectionTitle = state.graphMode === 'local' ? 'Claimed skills' : 'Collection';
      collectionPanel.innerHTML =
        `<div class="graph-collection-header" style="cursor: move;">` +
        `<span class="graph-collection-title">${collectionTitle}</span>` +
        `<div class="graph-collection-actions">` +
        `<button class="graph-collection-copy-all" title="Copy all named install commands" aria-label="Copy named install commands">` +
        `<svg class="gst-btn-ico" width="14" height="14" aria-hidden="true"><use href="assets/icons.svg#copy"/></svg>` +
        `</button>` +
        `<button class="graph-collection-clear-all" title="Clear collection" aria-label="Clear collection">` +
        `<svg class="gst-btn-ico" width="14" height="14" aria-hidden="true"><use href="assets/icons.svg#trash"/></svg>` +
        `</button>` +
        `<button class="graph-collection-minimize" title="Minimize panel" aria-label="Minimize panel">` +
        `<svg class="gst-btn-ico" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="8" x2="13" y2="8" /></svg>` +
        `</button>` +
        `</div></div>` +
        `<div class="graph-collection-list"></div>` +
        `<div class="graph-collection-note">You can only install <span class="gst-honor">named</span> skills.</div>`;
      canvas.parentElement.appendChild(collectionPanel);
      state.collectionEl = collectionPanel;
      collectionPanel.addEventListener('mousedown', e => e.stopPropagation());

      // Draggable Collection Panel logic
      const collHeader = collectionPanel.querySelector('.graph-collection-header');
      let collDragging = false, collOffsetX = 0, collOffsetY = 0;
      collHeader.addEventListener('mousedown', e => {
        if (window.matchMedia('(max-width:700px)').matches) return;
        collDragging = true;
        const rect = collectionPanel.getBoundingClientRect();
        collOffsetX = e.clientX - rect.left;
        collOffsetY = e.clientY - rect.top;
        collectionPanel.style.transition = 'none';
        e.preventDefault();
      });
      window.addEventListener('mousemove', e => {
        if (!collDragging) return;
        let x = e.clientX - collOffsetX;
        let y = e.clientY - collOffsetY;
        // Clamp to screen
        x = Math.max(0, Math.min(x, window.innerWidth - collectionPanel.offsetWidth));
        y = Math.max(0, Math.min(y, window.innerHeight - collectionPanel.offsetHeight));
        collectionPanel.style.left = x + 'px';
        collectionPanel.style.top = y + 'px';
      });
      window.addEventListener('mouseup', () => {
        if (collDragging) {
          collDragging = false;
          collectionPanel.style.transition = '';
        }
      });

      const minimizeBtn = collectionPanel.querySelector('.graph-collection-minimize');
      if (minimizeBtn) {
        const syncCollectionMinimize = () => {
          const minimized = collectionPanel.classList.contains('minimized');
          minimizeBtn.innerHTML = minimized
            ? `<svg class="gst-btn-ico" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="8" y1="3" x2="8" y2="13" /><line x1="3" y1="8" x2="13" y2="8" /></svg>`
            : `<svg class="gst-btn-ico" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="8" x2="13" y2="8" /></svg>`;
          minimizeBtn.title = minimized ? 'Maximize panel' : 'Minimize panel';
          minimizeBtn.setAttribute('aria-label', minimizeBtn.title);
        };
        minimizeBtn.addEventListener('click', () => {
          collectionPanel.classList.toggle('minimized');
          syncCollectionMinimize();
        });
        if (window.matchMedia('(max-width:700px)').matches) {
          collectionPanel.classList.add('minimized');
          syncCollectionMinimize();
        }
      }

      const clearBtn = collectionPanel.querySelector('.graph-collection-clear-all');
      clearBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to clear all skills from your collection?')) {
          state.collection = [];
          renderCollection();
        }
      });

      const copyAllBtn = collectionPanel.querySelector('.graph-collection-copy-all');
      const copyAllBtnHtml = copyAllBtn.innerHTML;
      copyAllBtn.addEventListener('click', () => {
        const lines = state.collection
          .map(id => state.namedMap[id])
          .filter(Boolean)
          .map(nid => `gaia install ${nid}`);
        if (lines.length === 0) return;
        navigator.clipboard.writeText(lines.join('\n')).then(() => {
          copyAllBtn.innerHTML =
            '<svg class="gst-btn-ico" width="14" height="14" aria-hidden="true">' +
            '<use href="assets/icons.svg#copy-check"/></svg>';
          copyAllBtn.classList.add('copied');
          setTimeout(() => { copyAllBtn.innerHTML = copyAllBtnHtml; copyAllBtn.classList.remove('copied'); }, 1500);
        });
      });

      renderCollection();

      function renderCollection() {
        const list = collectionPanel.querySelector('.graph-collection-list');
        if (state.collection.length === 0) {
          list.innerHTML =
            `<div class="graph-collection-empty" style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 0.6rem; text-align: center; gap: 0.2rem; opacity: 0.6;">` +
            `<div style="font-size: 0.55rem; color: var(--muted); line-height: 1.2;">` +
            `Your collection is empty.<br>Add skills via tooltips.` +
            `</div>` +
            `</div>`;
          collectionPanel.style.display = 'flex';
          return;
        }
        collectionPanel.style.display = 'flex';
        let html = '';
        // Collection cards render as .plaque--mini per Stage 3. Each
        // card carries the data-tier attribute so the per-tier glow
        // (--plaque-glow-intensity × --tier-*-bg) inherits the
        // collected skill's tier. Unnamed entries render as a ghost
        // plaque (dashed outline, muted text). Sprite-icon buttons
        // (share / remove) sit in the top-right corner of the card.
        state.collection.forEach(id => {
          const skill = state.skills.find(s => s.id === id) || { id, name: id, type: 'basic' };
          const col = PALETTE[skill.type] || PALETTE.basic;
          const namedId = (state.namedMap && state.namedMap[id]) || null;
          const cmd = namedId ? `gaia install ${namedId}` : `gaia propose /${id}`;
          const shareLink = namedId
            ? `<button class="graph-collection-share" data-nid="${namedId}" title="Open in Explorer" aria-label="Open in Explorer">` +
            `<svg class="gst-btn-ico" width="12" height="12" aria-hidden="true"><use href="assets/icons.svg#external-link"/></svg></button>`
            : '';
          const ghostAttr = namedId ? '' : ' data-ghost="true"';
          let formattedNamedId = '';
          if (namedId) {
            const parts = namedId.split('/');
            if (parts.length === 2) {
              const rm = state.meta && state.meta.levelColors ? state.meta.levelColors[skill.level || 0] : null;
              formattedNamedId = `<div class="graph-collection-card-named"><span class="gst-honor">@${esc(parts[0])}</span><span style="color:${rm ? rm.hex : `rgba(${col.rgb},1)`}">/${esc(parts[1])}</span></div>`;
            } else {
              formattedNamedId = `<div class="graph-collection-card-named">${esc(namedId)}</div>`;
            }
          }
          html +=
            `<div class="plaque--mini graph-collection-card" data-cid="${esc(id)}" data-tier="${esc(skill.type)}"${ghostAttr}>` +
            `<div class="graph-collection-card-top">` +
            `<span class="graph-collection-card-name" style="color:rgba(${col.rgb},1)">${esc(skill.name)}</span>` +
            `<div class="graph-collection-card-btns">${shareLink}` +
            `<button class="graph-collection-remove" data-cid="${id}" title="Remove" aria-label="Remove from collection">` +
            `<svg class="gst-btn-ico" width="12" height="12" aria-hidden="true"><use href="assets/icons.svg#close-x"/></svg>` +
            `</button>` +
            `</div>` +
            `</div>` +
            formattedNamedId +
            `<code class="graph-collection-cmd" data-cmd="${cmd}">$ ${cmd}</code>` +
            `</div>`;
        });
        list.innerHTML = html;
        list.querySelectorAll('.graph-collection-remove').forEach(btn => {
          btn.addEventListener('click', e => {
            e.stopPropagation();
            const cid = btn.dataset.cid;
            state.collection = state.collection.filter(x => x !== cid);
            renderCollection();
          });
        });
        list.querySelectorAll('.graph-collection-cmd').forEach(el => {
          el.addEventListener('click', () => {
            navigator.clipboard.writeText(el.dataset.cmd).then(() => {
              el.classList.add('copied');
              setTimeout(() => el.classList.remove('copied'), 1500);
            });
          });
        });
        list.querySelectorAll('.graph-collection-share').forEach(btn => {
          btn.addEventListener('click', e => {
            e.stopPropagation();
            const nid = btn.dataset.nid;
            let prefix = '';
            if (typeof window.gaiaIconBase === 'function') {
              prefix = window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '');
            } else {
              let path = window.location.pathname;
              if (path.endsWith('index.html')) {
                path = path.slice(0, -10);
              }
              if (!path.endsWith('/')) {
                path += '/';
              }
              prefix = path;
            }
            const resolvedUrl = new URL(prefix + 'named/#explorer/' + encodeURIComponent(nid).replace(/%2F/g, '/'), window.location.href).href;
            window.open(resolvedUrl, '_blank');
          });
        });
      }

      function openSkillPanel(skillId) {
        const skill = state.skills.find(s => s.id === skillId) || { id: skillId, name: skillId, type: 'basic', prerequisites: [] };
        const col = PALETTE[skill.type] || PALETTE.basic;
        const namedId = (state.namedMap && state.namedMap[skill.id]) || null;
        const titleText = (state.titleMap && state.titleMap[skill.id]) || null;
        const rm = skill.level ? RANK_META[skill.level] : null;
        const wasPaused = state.paused;
        state.paused = true;
        let c = `<div class="graph-skill-panel-header">`;
        c += `<div class="graph-skill-panel-name" style="color:rgba(${col.rgb},1)">${esc(skill.name)}</div>`;
        c += `<button class="graph-skill-panel-close" title="Close" aria-label="Close panel">×</button>`;
        c += `</div>`;
        c += `<div class="graph-skill-panel-body">`;
        if (namedId) {
          const parts = namedId.split('/');
          if (parts.length === 2) {
            const slugColor = rm ? rm.hex : `rgba(${col.rgb},1)`;
            c += `<div class="graph-skill-panel-named-id"><span class="gst-named-handle">@${esc(parts[0])}</span><span class="gst-named-slug" style="color:${slugColor}">/${esc(parts[1])}</span></div>`;
          } else {
            c += `<div class="graph-skill-panel-named-id"><span class="gst-named-handle">@${esc(namedId)}</span></div>`;
          }
        }
        if (namedId && titleText) c += `<div class="graph-skill-panel-title">"${esc(titleText)}"</div>`;
        c += `<div class="graph-skill-panel-type-row">`;
        c += `<span class="skill-tooltip-badge skill-tooltip-type-${esc(skill.type)}">${esc(skill.type.toUpperCase())}</span>`;
        if (rm) c += `<span style="display:inline-block;padding:.12rem .42rem;border-radius:999px;font-size:.62rem;font-weight:700;background:${rm.bg};color:${rm.hex}">${esc(skill.level)}</span>`;
        c += `</div>`;
        c += `<div class="graph-skill-panel-terminal">`;
        if (namedId) {
          c += `<code class="graph-skill-panel-cmd" data-cmd="gaia install ${esc(namedId)}">$ gaia install ${esc(namedId)}</code>`;
          c += `<a class="graph-skill-panel-explorer-link" href="#explorer/${esc(namedId)}">Open in Explorer →</a>`;
        } else {
          c += `<code class="graph-skill-panel-cmd" data-cmd="gaia propose /${esc(skill.id)}">$ gaia propose /${esc(skill.id)}</code>`;
          c += `<div class="graph-skill-panel-hint">Claim this skill as your own named implementation</div>`;
        }
        c += `</div></div>`;
        skillPanel.innerHTML = c;
        skillPanel.style.display = 'flex';
        
        // Position modal on top right of the node
        const pr = state.projectedNodes[skillId];
        if (pr) {
          let tx = pr.sx + 20, ty = pr.sy - 260;
          tx = Math.max(10, Math.min(tx, state.width - 330));
          ty = Math.max(10, Math.min(ty, state.height - 300));
          skillPanel.style.left = tx + 'px';
          skillPanel.style.top = ty + 'px';
          skillPanel.style.transform = 'none';
        }

        state.tooltipEl.style.display = 'none';
        const closePanel = () => {
          skillPanel.style.display = 'none';
          if (!wasPaused) state.paused = false;
          state.lastHoveredId = null;
        };
        skillPanel.querySelector('.graph-skill-panel-close').addEventListener('click', closePanel);
        const cmdEl = skillPanel.querySelector('.graph-skill-panel-cmd');
        if (cmdEl) {
          cmdEl.addEventListener('click', () => {
            const cmd = cmdEl.dataset.cmd;
            if (navigator.clipboard) {
              navigator.clipboard.writeText(cmd).then(() => {
                cmdEl.classList.add('copied');
                setTimeout(() => cmdEl.classList.remove('copied'), 1500);
              });
            }
          });
        }
        const explorerLink = skillPanel.querySelector('.graph-skill-panel-explorer-link');
        if (explorerLink) {
          explorerLink.addEventListener('click', e => {
            e.preventDefault();
            window.location.hash = `explorer/${namedId}`;
            if (window.openSkillExplorer) window.openSkillExplorer(namedId);
          });
        }
      }
      state.openSkillPanel = openSkillPanel;
      const searchWrap = document.createElement('div');
      searchWrap.className = 'graph-search-wrap';
      searchWrap.setAttribute('data-interactive-chrome', '');
      const searchInput = document.createElement('input');
      searchInput.type = 'text';
      searchInput.className = 'graph-search';
      searchInput.placeholder = '/skill · @handle · text';
      searchInput.title = 'Type /name to filter skills, @handle for contributors, or any text to search names + descriptions.';
      searchInput.setAttribute('aria-label', 'Filter skill graph: prefix with / for skill, @ for handle');
      searchInput.addEventListener('input', () => { state.searchText = searchInput.value.trim(); });
      searchInput.addEventListener('mousedown', e => e.stopPropagation());
      searchWrap.appendChild(searchInput);

      // ── Search syntax help affordance ─────────────────────────
      // The slash/at/free-text grammar is non-obvious; surface it via
      // an info button + popover next to the input. Clicking outside
      // or hitting Escape closes the popover (the Escape close is
      // wired below to consume the key only when the popover is open
      // so fullscreen Escape still works otherwise).
      const searchHelpBtn = document.createElement('button');
      searchHelpBtn.type = 'button';
      searchHelpBtn.className = 'graph-search-help';
      searchHelpBtn.setAttribute('aria-label', 'Search syntax help');
      searchHelpBtn.setAttribute('aria-expanded', 'false');
      searchHelpBtn.innerHTML = '<svg width="14" height="14" aria-hidden="true"><use href="assets/icons.svg#info"/></svg>';
      const searchHelpPopover = document.createElement('div');
      searchHelpPopover.className = 'graph-search-help-popover';
      searchHelpPopover.setAttribute('role', 'tooltip');
      searchHelpPopover.hidden = true;
      searchHelpPopover.innerHTML =
        '<div><code>/foo</code> filters skill IDs and names</div>' +
        '<div><code>@bar</code> filters contributor handles</div>' +
        '<div>any other text fuzzy-matches names, descriptions, titles</div>';
      function _closeSearchHelp() {
        searchHelpPopover.hidden = true;
        searchHelpBtn.setAttribute('aria-expanded', 'false');
      }
      function _openSearchHelp() {
        searchHelpPopover.hidden = false;
        searchHelpBtn.setAttribute('aria-expanded', 'true');
      }
      searchHelpBtn.addEventListener('mousedown', e => e.stopPropagation());
      searchHelpBtn.addEventListener('click', e => {
        e.stopPropagation();
        if (searchHelpPopover.hidden) _openSearchHelp(); else _closeSearchHelp();
      });
      searchHelpPopover.addEventListener('mousedown', e => e.stopPropagation());
      // Close on any pointerdown outside the help UI.
      document.addEventListener('pointerdown', e => {
        if (searchHelpPopover.hidden) return;
        if (e.target === searchHelpBtn || searchHelpBtn.contains(e.target)) return;
        if (searchHelpPopover.contains(e.target)) return;
        _closeSearchHelp();
      });
      // Escape closes the popover and consumes the key so fullscreen
      // doesn't also collapse. When the popover is closed, we don't
      // consume Escape — the existing fullscreen close handler runs.
      document.addEventListener('keydown', e => {
        if (e.key !== 'Escape') return;
        if (searchHelpPopover.hidden) return;
        e.preventDefault();
        e.stopPropagation();
        _closeSearchHelp();
      }, true);
      searchWrap.appendChild(searchHelpBtn);
      searchWrap.appendChild(searchHelpPopover);

      canvas.parentElement.appendChild(searchWrap);
      state.searchInputEl = searchInput;

      // Legend rebuilt to read from CSS tokens via data-attributes —
      // the swatch background and pill colour are set in styles.css
      // (.graph-legend-swatch[data-tier=...], .graph-legend-rank-pill[data-rank=...])
      // so all four tier hues and six rank hues come from --tier-* /
      // --rank-*. Sizes (7/10/12/14 px) still drive node-size hierarchy
      // and stay inline for clarity.
      // §6.1 legend flip. Under the World Tree re-axis, COLOR = rank and GLYPH =
      // structural class. The legend leads with the rank ramp (the color key) and
      // demotes type to a small glyph key (○ basic · ◇ fusion · ◉ unique · ◆
      // suite). The rank pills still carry their --rank-N swatch via data-rank;
      // the structure items still filter by skill.type via data-legend-type but
      // now show the glyph instead of a color swatch. Grey 0-1★ bark is shown as
      // a non-interactive ramp anchor (no clean per-node level string to filter).
      const legend = document.createElement('div');
      legend.className = 'graph-legend minimized';
      legend.setAttribute('data-interactive-chrome', '');
      legend.innerHTML =

        '<button type="button" class="graph-legend-drawer-toggle" aria-label="Toggle filters drawer">' +
        '<svg class="ico" width="16" height="16" aria-hidden="true"><use href="assets/icons.svg#claim-arrow"/></svg>' +
        '<span class="graph-legend-drawer-label">Filters</span>' +
        '</button>' +
        '<div class="graph-legend-content">' +
        '<div class="graph-legend-body">' +
        '<div class="graph-legend-section"><div class="graph-legend-heading">Rank <span class="graph-legend-subhead">= color</span></div>' +
        '<div class="graph-legend-ranks">' +
        '<span class="graph-legend-rank-pill graph-legend-rank-anchor" data-rank="0" title="0–1★ / unranked — outer bark, grey">0–1★</span>' +
        '<span class="graph-legend-rank-pill" data-legend-rank="2★" data-rank="2">2★</span>' +
        '<span class="graph-legend-rank-pill" data-legend-rank="3★" data-rank="3">3★</span>' +
        '<span class="graph-legend-rank-pill" data-legend-rank="4★" data-rank="4">4★</span>' +
        '<span class="graph-legend-rank-pill" data-legend-rank="5★" data-rank="5">5★</span>' +
        '<span class="graph-legend-rank-pill" data-legend-rank="6★" data-rank="6">6★</span>' +
        '</div></div>' +
        '<div class="graph-legend-section"><div class="graph-legend-heading">Structure <span class="graph-legend-subhead">= glyph</span></div>' +
        '<div class="graph-legend-item" data-legend-type="basic"><span class="graph-legend-glyph" aria-hidden="true">○</span>Basic</div>' +
        '<div class="graph-legend-item" data-legend-type="extra"><span class="graph-legend-glyph" aria-hidden="true">◇</span>Fusion</div>' +
        '<div class="graph-legend-item" data-legend-type="unique"><span class="graph-legend-glyph" aria-hidden="true">◉</span>Unique</div>' +
        '<div class="graph-legend-item" data-legend-type="ultimate"><span class="graph-legend-glyph" aria-hidden="true">◆</span>Suite</div>' +
        '</div>' +
        '<div class="graph-legend-section"><div class="graph-legend-heading">View</div>' +
        '<div class="graph-legend-item" data-legend-clusters><span class="graph-legend-swatch" style="width:12px;height:12px;background:var(--honor-red);border-radius:2px"></span>Clusters</div>' +

        '</div>' +
        '</div>' +

        '</div>';
      legend.addEventListener('mousedown', e => e.stopPropagation());
      
      const drawerToggle = legend.querySelector('.graph-legend-drawer-toggle');
      if (drawerToggle) {
        drawerToggle.addEventListener('click', e => {
          e.stopPropagation();
          legend.classList.toggle('minimized');
        });
      }
      legend.querySelectorAll('.graph-legend-item[data-legend-type]').forEach(item => {
        item.addEventListener('mouseenter', () => { state.legendHoverType = item.dataset.legendType; });
        item.addEventListener('mouseleave', () => { state.legendHoverType = null; });
        item.addEventListener('click', () => {
          const val = state.legendFilterType === item.dataset.legendType ? null : item.dataset.legendType;
          state.legendFilterType = val;
          legend.querySelectorAll('[data-legend-type]').forEach(el => el.classList.remove('active'));
          if (val) item.classList.add('active');
        });
      });
      legend.querySelectorAll('.graph-legend-rank-pill').forEach(pill => {
        // The 0–1★ ramp anchor is a legend key only (no clean per-node level
        // string to filter on), so skip wiring hover/click for it.
        if (!pill.dataset.legendRank) return;
        pill.addEventListener('mouseenter', () => { state.legendHoverRank = pill.dataset.legendRank; });
        pill.addEventListener('mouseleave', () => { state.legendHoverRank = null; });
        pill.addEventListener('click', () => {
          const val = state.legendFilterRank === pill.dataset.legendRank ? null : pill.dataset.legendRank;
          state.legendFilterRank = val;
          legend.querySelectorAll('.graph-legend-rank-pill').forEach(el => el.classList.remove('active'));
          if (val) pill.classList.add('active');
          });
          });
          const clusterToggle = legend.querySelector('[data-legend-clusters]');
          if (clusterToggle) {
          clusterToggle.addEventListener('click', () => {
          const on = clusterToggle.classList.toggle('active');
          state.colorMode = on ? 'cluster' : 'tier';
          });
          }
          canvas.parentElement.appendChild(legend);

      state.legendEl = legend;

      const scatterStrip = document.createElement('div');
      scatterStrip.className = 'graph-scatter-strip';
      scatterStrip.setAttribute('data-interactive-chrome', '');
      scatterStrip.setAttribute('aria-label', 'Density — arrow keys or drag to spread/clump');
      scatterStrip.setAttribute('role', 'slider');
      scatterStrip.setAttribute('aria-orientation', 'vertical');
      const scatterTop = document.createElement('div');
      scatterTop.className = 'graph-scatter-edge graph-scatter-edge--top';
      scatterTop.textContent = '+';
      const scatterTrackWrap = document.createElement('div');
      scatterTrackWrap.className = 'graph-scatter-track';
      const scatterRulerCanvas = document.createElement('canvas');
      scatterRulerCanvas.className = 'graph-ruler-canvas';
      scatterTrackWrap.appendChild(scatterRulerCanvas);
      state.scatterRulerCanvas = scatterRulerCanvas;
      const scatterBot = document.createElement('div');
      scatterBot.className = 'graph-scatter-edge graph-scatter-edge--bot';
      scatterBot.textContent = '−';
      const scatterTitle = document.createElement('div');
      scatterTitle.className = 'graph-scatter-title';
      scatterTitle.textContent = Math.round((state.treeLayout ? state.treeSpread : state.scale / (options.scale || GRAPH_SCALE)) * 100) + '%';
      scatterStrip.appendChild(scatterTop);
      scatterStrip.appendChild(scatterTrackWrap);
      scatterStrip.appendChild(scatterBot);
      scatterStrip.appendChild(scatterTitle);
      // Caption so first-time users notice the strip is draggable.
      // CSS rotates it vertically; class is styled by the CSS agent.
      const scatterCaption = document.createElement('div');
      scatterCaption.className = 'graph-strip-caption graph-strip-caption--scatter';
      scatterCaption.textContent = 'SPREAD';
      scatterStrip.appendChild(scatterCaption);

      function redrawScatterRuler() {
        const density = state.treeLayout ? state.treeSpread : state.scale;
        const logVal = Math.log(density);
        drawRuler(scatterRulerCanvas, logVal, { vertical: true, pxPerUnit: 42, minorStep: 0.1, majorEvery: 5 });
        const pct = Math.round((state.treeLayout ? state.treeSpread : state.scale / (options.scale || GRAPH_SCALE)) * 100);
        scatterTitle.textContent = pct + '%';
        scatterStrip.setAttribute('aria-valuetext', 'Density ' + pct + ' percent');
      }
      let scatterDragging = false, scatterLastY = 0;
      scatterStrip.addEventListener('mousedown', e => e.stopPropagation());
      scatterStrip.addEventListener('pointerdown', e => {
        e.preventDefault(); e.stopPropagation();
        scatterStrip.setPointerCapture(e.pointerId);
        scatterDragging = true;
        scatterLastY = e.clientY;
        redrawScatterRuler();
      });
      scatterStrip.addEventListener('pointermove', e => {
        if (!scatterDragging) return;
        const dy = scatterLastY - e.clientY;
        scatterLastY = e.clientY;
        if (state.treeLayout) {
          state.treeSpread = Math.max(0.35, Math.min(2.4, state.treeSpread * Math.exp(dy * 0.007)));
        } else {
          state.scale = Math.max(0.05, Math.min((options.scale || GRAPH_SCALE) * 10, state.scale * Math.exp(dy * 0.007)));
          state.positions = buildPositions(state.skills, state.scale, state.layoutMode);
        }
        redrawScatterRuler();
      });
      scatterStrip.addEventListener('pointerup', e => {
        scatterDragging = false;
        scatterStrip.releasePointerCapture(e.pointerId);
      });
      // ── Keyboard a11y: ArrowUp/Down to spread/clump, PageUp/Down
      // for bigger steps. Mirrors the pointer logic but uses fixed
      // increments instead of pixel deltas so screen-reader / keyboard
      // users get predictable behaviour.
      scatterStrip.tabIndex = 0;
      scatterStrip.addEventListener('keydown', e => {
        let factor = 0;
        if (e.key === 'ArrowUp') factor = Math.exp(0.05);
        else if (e.key === 'ArrowDown') factor = Math.exp(-0.05);
        else if (e.key === 'PageUp') factor = Math.exp(0.20);
        else if (e.key === 'PageDown') factor = Math.exp(-0.20);
        if (!factor) return;
        e.preventDefault();
        if (state.treeLayout) {
          state.treeSpread = Math.max(0.35, Math.min(2.4, state.treeSpread * factor));
        } else {
          state.scale = Math.max(0.05, Math.min((options.scale || GRAPH_SCALE) * 10, state.scale * factor));
          state.positions = buildPositions(state.skills, state.scale, state.layoutMode);
        }
        redrawScatterRuler();
      });
      canvas.parentElement.appendChild(scatterStrip);
      setTimeout(redrawScatterRuler, 50);

      const redPill = document.createElement('button');
      redPill.type = 'button';
      redPill.className = 'graph-redpill';
      redPill.setAttribute('data-interactive-chrome', '');
      redPill.textContent = 'Named Skills';
      redPill.title = 'Highlight Named skills (2★+) with contributor attribution and red glow';
      redPill.addEventListener('mousedown', e => e.stopPropagation());
      redPill.addEventListener('click', () => {
        state.redPillActive = !state.redPillActive;
        redPill.classList.toggle('active', state.redPillActive);
      });
      canvas.parentElement.appendChild(redPill);
      state.redPillEl = redPill;

      // ── Bottom bar: [pause][reset][zoom][speed strip] ──
      const bottomBar = document.createElement('div');
      bottomBar.className = 'graph-bottom-bar';
      bottomBar.setAttribute('data-interactive-chrome', '');
      bottomBar.addEventListener('mousedown', e => e.stopPropagation());

      const pauseBtn = document.createElement('button');
      pauseBtn.type = 'button';
      pauseBtn.className = 'graph-pause-btn';
      pauseBtn.innerHTML = `<svg class="gst-btn-ico" width="14" height="14" aria-hidden="true"><use href="assets/icons.svg#pause"/></svg>`;
      pauseBtn.title = 'Pause / resume rotation';
      pauseBtn.setAttribute('aria-pressed', 'false');
      pauseBtn.addEventListener('click', () => {
        state.paused = !state.paused;
        pauseBtn.classList.toggle('active', state.paused);
        pauseBtn.setAttribute('aria-pressed', String(state.paused));
        pauseBtn.innerHTML = `<svg class="gst-btn-ico" width="14" height="14" aria-hidden="true"><use href="assets/icons.svg#${state.paused ? 'play' : 'pause'}"/></svg>`;
      });
      bottomBar.appendChild(pauseBtn);
      state.pauseBtnEl = pauseBtn;

      const resetBtn = document.createElement('button');
      resetBtn.type = 'button';
      resetBtn.className = 'graph-reset-btn';
      resetBtn.innerHTML = `<svg class="gst-btn-ico" width="14" height="14" aria-hidden="true"><use href="assets/icons.svg#sync"/></svg>`;
      resetBtn.title = 'Reset View';
      resetBtn.addEventListener('click', () => {
        resetFilters();
      });
      bottomBar.appendChild(resetBtn);

      const randomBtn = document.createElement('button');
      randomBtn.type = 'button';
      randomBtn.className = 'graph-random-btn';
      randomBtn.innerHTML = `<svg class="gst-btn-ico" width="14" height="14" aria-hidden="true"><use href="assets/icons.svg#sparkle"/></svg>`;
      randomBtn.title = 'Zoom to Random Skill';
      randomBtn.addEventListener('click', () => {
        randomZoom();
      });
      bottomBar.appendChild(randomBtn);

      const zoomCounter = document.createElement('div');
      zoomCounter.className = 'graph-zoom-counter';
      zoomCounter.textContent = '1.0×';
      zoomCounter.title = 'Zoom level (click to reset)';
      zoomCounter.addEventListener('click', () => {
        state.zoom = 1;
        zoomCounter.textContent = '1.0×';
      });
      bottomBar.appendChild(zoomCounter);
      state.zoomCounterEl = zoomCounter;

      // Speed strip — horizontal infinite drag, right=faster
      const speedStrip = document.createElement('div');
      speedStrip.className = 'graph-speed-strip';
      speedStrip.setAttribute('aria-label', 'Rotation speed — arrow keys or drag');
      speedStrip.setAttribute('role', 'slider');
      speedStrip.setAttribute('aria-orientation', 'horizontal');
      const speedLeft = document.createElement('div');
      speedLeft.className = 'graph-speed-edge graph-speed-edge--left';
      speedLeft.textContent = '◀';
      const speedTrackWrap = document.createElement('div');
      speedTrackWrap.className = 'graph-speed-track';
      const speedRulerCanvas = document.createElement('canvas');
      speedRulerCanvas.className = 'graph-ruler-canvas';
      speedTrackWrap.appendChild(speedRulerCanvas);
      state.speedRulerCanvas = speedRulerCanvas;
      const speedRight = document.createElement('div');
      speedRight.className = 'graph-speed-edge graph-speed-edge--right';
      speedRight.textContent = '▶';
      const speedTitle = document.createElement('div');
      speedTitle.className = 'graph-speed-title';
      speedTitle.textContent = '×' + state.rotSpeed.toFixed(1);
      speedStrip.appendChild(speedLeft);
      speedStrip.appendChild(speedTrackWrap);
      speedStrip.appendChild(speedRight);
      speedStrip.appendChild(speedTitle);
      // Horizontal caption next to the title — same discoverability
      // hint as the scatter strip's SPREAD caption.
      const speedCaption = document.createElement('div');
      speedCaption.className = 'graph-strip-caption graph-strip-caption--speed';
      speedCaption.textContent = 'SPEED';
      speedStrip.appendChild(speedCaption);

      function redrawSpeedRuler() {
        const logVal = Math.log(Math.max(0.001, state.rotSpeed));
        drawRuler(speedRulerCanvas, logVal, { vertical: false, pxPerUnit: 42, minorStep: 0.1, majorEvery: 5 });
        speedTitle.textContent = '×' + state.rotSpeed.toFixed(1);
        speedStrip.setAttribute('aria-valuetext', 'Rotation ' + state.rotSpeed.toFixed(1) + ' times');
      }
      let speedDragging = false, speedLastX = 0;
      speedStrip.addEventListener('pointerdown', e => {
        e.preventDefault();
        speedStrip.setPointerCapture(e.pointerId);
        speedDragging = true;
        speedLastX = e.clientX;
        redrawSpeedRuler();
      });
      speedStrip.addEventListener('pointermove', e => {
        if (!speedDragging) return;
        const dx = e.clientX - speedLastX;
        speedLastX = e.clientX;
        state.rotSpeed = Math.max(0, Math.min(50, state.rotSpeed * Math.exp(dx * 0.007)));
        redrawSpeedRuler();
      });
      speedStrip.addEventListener('pointerup', e => {
        speedDragging = false;
        speedStrip.releasePointerCapture(e.pointerId);
      });
      // ── Keyboard a11y: ArrowLeft/Right to slow/speed, PageLeft/Right
      // for bigger steps. Clamp matches the pointer-drag clamp [0, 50].
      speedStrip.tabIndex = 0;
      speedStrip.addEventListener('keydown', e => {
        let factor = 0;
        if (e.key === 'ArrowRight') factor = Math.exp(0.05);
        else if (e.key === 'ArrowLeft') factor = Math.exp(-0.05);
        else if (e.key === 'PageUp' || e.key === 'PageDown') {
          // Some keyboards lack PageLeft/Right; treat PageUp/Down as
          // the big-step analogues on the horizontal axis.
          factor = e.key === 'PageUp' ? Math.exp(0.20) : Math.exp(-0.20);
        }
        if (!factor) return;
        e.preventDefault();
        state.rotSpeed = Math.max(0, Math.min(50, state.rotSpeed * factor));
        redrawSpeedRuler();
      });
      bottomBar.appendChild(speedStrip);
      setTimeout(redrawSpeedRuler, 50);
      canvas.parentElement.appendChild(bottomBar);
    }
    // Hide all interactive chrome initially if not interactive at start
    if (_interactiveReady && !options.hoverable) {
      const parent = canvas.parentElement;
      parent.querySelectorAll('.skill-tooltip, .graph-neighbor-cards, .graph-skill-panel, .graph-collection-panel, .graph-search-wrap, .graph-legend, .graph-scatter-strip, .graph-redpill, .graph-bottom-bar').forEach(el => {
        el.style.display = 'none';
        el.dataset.interactiveChrome = '1';
      });
    }
    window.addEventListener('resize', resize);
    const pointerTarget = options.pointerTarget || canvas;
    let _lastRect = null;
    window.addEventListener('resize', () => { _lastRect = null; });
    window.addEventListener('scroll', () => { _lastRect = null; }, { passive: true });
    function _pickNode(clientX, clientY) {
      if (!_lastRect) _lastRect = canvas.getBoundingClientRect();
      const mx = clientX - _lastRect.left;
      const my = clientY - _lastRect.top;
      let closest = null, closestDist = 24;
      Object.entries(state.projectedNodes).forEach(([id, pr]) => {
        const d = Math.hypot(pr.sx - mx, pr.sy - my);
        if (d < closestDist) { closestDist = d; closest = id; }
      });
      return closest;
    }
    pointerTarget.addEventListener('mousemove', event => {
      if (!_lastRect) _lastRect = canvas.getBoundingClientRect();
      const rect = _lastRect;
      if (_opts.draggable && state.dragging) {
        if (state._activeDragMode === 'orbit') {
          state.orbitY += (event.clientX - state.dragLastX) * 0.007;
          state.orbitX += (event.clientY - state.dragLastY) * 0.007;
        } else {
          state.panX += event.clientX - state.dragLastX;
          state.panY += event.clientY - state.dragLastY;
        }
        state.dragLastX = event.clientX;
        state.dragLastY = event.clientY;
        if (Math.hypot(event.clientX - state.dragStartX, event.clientY - state.dragStartY) > 5) state.dragMoved = true;
        state.hoveredId = null;
      } else {
        state.mx = ((event.clientX - rect.left) / Math.max(rect.width, 1) - 0.5) * 2;
        state.my = ((event.clientY - rect.top) / Math.max(rect.height, 1) - 0.5) * 2;
        if (_opts.hoverable) {
          const closest = _pickNode(event.clientX, event.clientY);
          state.hoveredId = closest;
          canvas.style.cursor = closest ? 'pointer' : (_opts.draggable ? 'grab' : 'default');
        }
      }
    });
    // Drag + click handlers — always wired so setInteractive() can
    // toggle _opts.draggable at runtime. Guard checks _opts.draggable
    // inside the handler so they're live.
    canvas.addEventListener('mouseleave', () => { if (!state.dragging && !state.pinnedId) state.hoveredId = null; });
    canvas.addEventListener('contextmenu', e => { if (_opts.draggable) e.preventDefault(); });
    canvas.addEventListener('focus', () => {
      if (!_opts.draggable) return;
      canvas.style.outline = '2px solid var(--apex-gold)';
      canvas.style.outlineOffset = '-4px';
    });
    canvas.addEventListener('blur', () => {
      canvas.style.outline = '';
      canvas.style.outlineOffset = '';
    });
    canvas.addEventListener('keydown', e => {
      if (!_opts.draggable) return;
      let handled = true;
      if (e.key === 'ArrowLeft') state.orbitY -= 0.09;
      else if (e.key === 'ArrowRight') state.orbitY += 0.09;
      else if (e.key === 'ArrowUp') state.orbitX -= 0.09;
      else if (e.key === 'ArrowDown') state.orbitX += 0.09;
      else if (e.key === '+' || e.key === '=' || e.code === 'NumpadAdd') state.zoom = Math.min(3, state.zoom * 1.12);
      else if (e.key === '-' || e.key === '_' || e.code === 'NumpadSubtract') state.zoom = Math.max(0.3, state.zoom / 1.12);
      else if (e.key === 'Enter' && state.hoveredId) {
        state.pinnedId = state.hoveredId;
        state.pinnedPos = null;
        state.lastHoveredId = null;
      } else handled = false;
      if (!handled) return;
      e.preventDefault();
      e.stopPropagation();
      if (state.zoomCounterEl) state.zoomCounterEl.textContent = state.zoom.toFixed(1) + '×';
    });
    canvas.addEventListener('mousedown', e => {
      if (!_opts.draggable) return;
      if (e.button === 2) return;
      e.preventDefault();

      // Update rect cache on mousedown to ensure precision before drag
      _lastRect = canvas.getBoundingClientRect();

      state.dragging = true;
      // Respect toggled dragMode. Ctrl/Middle-click swaps to the other mode.
      const base = state.dragMode || 'orbit';
      const other = base === 'orbit' ? 'pan' : 'orbit';
      state._activeDragMode = (e.button === 1 || e.ctrlKey) ? other : base;

      state.dragMoved = false;
      state.dragStartX = e.clientX;
      state.dragStartY = e.clientY;
      state.dragLastX = e.clientX;
      state.dragLastY = e.clientY;
      canvas.style.cursor = state._activeDragMode === 'orbit' ? 'grabbing' : 'move';
    });
    window.addEventListener('mouseup', e => {
      if (!state.dragging) return;
      const didClick = !state.dragMoved;
      state.dragging = false;
      state.dragMoved = false;
      canvas.style.cursor = state.hoveredId ? 'pointer' : (_opts.draggable ? 'grab' : 'default');
      if (didClick) {
        if (state.hoveredId) {
          state.pinnedId = state.hoveredId;
          state.pinnedPos = null;
          state.lastHoveredId = null;
        } else {
          state.pinnedId = null;
          state.pinnedPos = null;
          state.lastHoveredId = null;
        }
      }
    });
    // Zoom handler — always attached, guarded by _opts.zoomable.
    {
      canvas.addEventListener('wheel', e => {
        if (!_opts.zoomable) return;
        e.preventDefault();
        state.zoom = Math.max(0.3, Math.min(3.0, state.zoom * (1 - e.deltaY * 0.001)));
        if (state.zoomCounterEl) state.zoomCounterEl.textContent = state.zoom.toFixed(1) + '×';
      }, { passive: false });
    }
    // Touch handlers (pan + pinch-to-zoom)
    let _initialPinchDist = null;
    let _initialZoom = null;
    canvas.addEventListener('touchstart', e => {
      if (!_opts.draggable) return;
      if (e.touches.length === 1) {
        state.dragging = true;
        state._activeDragMode = state.dragMode || 'orbit';
        state.dragMoved = false;
        state.dragStartX = e.touches[0].clientX;
        state.dragStartY = e.touches[0].clientY;
        state.dragLastX = e.touches[0].clientX;
        state.dragLastY = e.touches[0].clientY;
      } else if (e.touches.length === 2 && _opts.zoomable) {
        state.dragging = false;
        const dx = e.touches[0].clientX - e.touches[1].clientX;
        const dy = e.touches[0].clientY - e.touches[1].clientY;
        _initialPinchDist = Math.sqrt(dx * dx + dy * dy);
        _initialZoom = state.zoom;
      }
    }, { passive: true });
    canvas.addEventListener('touchmove', e => {
      if (e.touches.length === 1 && state.dragging) {
        e.preventDefault();
        const clientX = e.touches[0].clientX;
        const clientY = e.touches[0].clientY;
        if (Math.abs(clientX - state.dragStartX) > 3 || Math.abs(clientY - state.dragStartY) > 3) {
          state.dragMoved = true;
        }
        if (state._activeDragMode === 'orbit') {
          state.orbitY += (clientX - state.dragLastX) * 0.007;
          state.orbitX += (clientY - state.dragLastY) * 0.007;
        } else {
          state.panX += clientX - state.dragLastX;
          state.panY += clientY - state.dragLastY;
        }
        state.dragLastX = clientX;
        state.dragLastY = clientY;
      } else if (e.touches.length === 2 && _opts.zoomable && _initialPinchDist) {
        e.preventDefault();
        const dx = e.touches[0].clientX - e.touches[1].clientX;
        const dy = e.touches[0].clientY - e.touches[1].clientY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        // Apply an exponent >1 so small finger movements move the
        // zoom further — users wanted pinch to feel "quicker".
        const ratio = Math.pow(dist / _initialPinchDist, 1.8);
        state.zoom = Math.max(0.3, Math.min(3.0, _initialZoom * ratio));
        if (state.zoomCounterEl) state.zoomCounterEl.textContent = state.zoom.toFixed(1) + '×';
      }
    }, { passive: false });
    canvas.addEventListener('touchend', e => {
      if (e.touches.length < 2) _initialPinchDist = null;
      if (e.touches.length === 0 && state.dragging) {
        const touch = e.changedTouches && e.changedTouches[0];
        if (!state.dragMoved && touch && _opts.hoverable) {
          const picked = _pickNode(touch.clientX, touch.clientY);
          state.hoveredId = picked;
          state.pinnedId = picked;
          state.pinnedPos = null;
          state.lastHoveredId = null;
        }
        state.dragging = false;
        state.dragMoved = false;
      }
    });
    function resetFilters() {
      state.legendFilterType = null;
      state.legendFilterRank = null;
      state.legendHoverType = null;
      state.legendHoverRank = null;
      state.showTitles = false;
      state.searchText = '';
      state.redPillActive = false;
      state.panX = 0; state.panY = 0;
      state.orbitX = 0; state.orbitY = 0;
      state.paused = false; state.rotSpeed = 1;
      state.zoom = 1;
      state.scale = options.scale || GRAPH_SCALE;
      state.treeSpread = 1;
      if (!state.treeLayout) state.positions = buildPositions(state.skills, state.scale, state.layoutMode);
      state.nebula = true;
      state.hoverSlowdown = 0;
      state.pinnedId = null; state.pinnedPos = null;
      if (state.skillPanelEl) state.skillPanelEl.style.display = 'none';
      if (state.pauseBtnEl) {
        state.pauseBtnEl.textContent = '⏸';
        state.pauseBtnEl.classList.remove('active');
        state.pauseBtnEl.setAttribute('aria-pressed', 'false');
      }
      if (state.labelsToggleEl) {
        const def = (options.labelMode && options.labelMode !== 'none') ? options.labelMode : 'all';
        state.labelMode = def;
        state._lastLabelMode = def;
        state.labelsToggleEl.classList.remove('off');
        state.labelsToggleEl.setAttribute('aria-pressed', String(def !== 'none'));
      }
      if (state.redPillEl) state.redPillEl.classList.remove('active');
      if (state.legendEl) {
        state.legendEl.querySelectorAll('.active').forEach(el => el.classList.remove('active'));
      }
      if (state.searchInputEl) state.searchInputEl.value = '';
      if (state.labelToggleEl) {
        state.labelToggleEl.classList.remove('active');
        state.labelToggleEl.setAttribute('aria-pressed', 'false');
      }
      if (state.zoomCounterEl) state.zoomCounterEl.textContent = '1.0×';
      if (state.nebulaToggleEl) {
        state.nebulaToggleEl.classList.add('active');
        state.nebulaToggleEl.setAttribute('aria-pressed', 'true');
      }
      if (state.scatterRulerCanvas) {
        drawRuler(state.scatterRulerCanvas, Math.log(state.treeLayout ? state.treeSpread : state.scale), { vertical: true, pxPerUnit: 42, minorStep: 0.1, majorEvery: 5 });
      }
      if (state.speedRulerCanvas) {
        drawRuler(state.speedRulerCanvas, 0, { vertical: false, pxPerUnit: 42, minorStep: 0.1, majorEvery: 5 });
      }
    }
    if (state.running) draw();
    function setNamedMap(map) { state.namedMap = map || {}; }
    function setTitleMap(map) { state.titleMap = map || {}; }
    function setOriginMap(map) { state.originMap = map || {}; }

    // ── RUNTIME MODE SWITCHING ──────────────────────────────────
    // setInteractive(on) — promote the ambient hero graph into a
    // fully interactive exploration canvas (or demote it back).
    // This avoids creating a second graph instance.
    function setInteractive(on) {
      _opts.draggable = on;
      _opts.zoomable = on;
      _opts.hoverable = on;
      canvas.style.pointerEvents = on ? 'auto' : 'none';
      canvas.style.cursor = on ? 'grab' : 'default';
      if (on) canvas.setAttribute('tabindex', '0');
      else {
        canvas.removeAttribute('tabindex');
        canvas.style.outline = '';
        canvas.style.outlineOffset = '';
      }
      // Toggle visibility of interactive chrome elements.
      // Skip elements that are controlled by user interaction
      // (tooltip, skill-panel, collection-panel) — they manage
      // their own display state.
      const parent = canvas.parentElement;
      if (parent) {
        parent.querySelectorAll('[data-interactive-chrome]').forEach(el => {
          if (el.classList.contains('skill-tooltip') ||
            el.classList.contains('graph-skill-panel') ||
            el.classList.contains('graph-collection-panel')) return;
          el.style.display = on ? '' : 'none';
        });
      }
      if (!on) {
        // Clear any interactive state
        state.hoveredId = null;
        state.pinnedId = null;
        state.pinnedPos = null;
        state.lastHoveredId = null;
        state.dragging = false;
        if (state.tooltipEl) state.tooltipEl.style.display = 'none';
        if (state.neighborCardsEl) { state.neighborCardsEl.style.display = 'none'; state.neighborCardsEl.textContent = ''; state._neighborIds = null; }
        if (state.skillPanelEl) state.skillPanelEl.style.display = 'none';
      }
    }
    function setLabelMode(mode) {
      state.labelMode = mode;
      if (mode !== 'none') state._lastLabelMode = mode;
      if (state.labelsToggleEl) {
        state.labelsToggleEl.classList.toggle('off', mode === 'none');
        state.labelsToggleEl.classList.toggle('priority', mode === 'priority');
        state.labelsToggleEl.setAttribute('aria-pressed', String(mode !== 'none'));
      }
    }
    function getLabelMode() { return state.labelMode; }
    function getStatusEl() { return state.statusEl; }
    function setStatusEl(el) { state.statusEl = el; setSkills(state.skills); }

    function setMeta(meta) {
      state.meta = meta;
    }

    function setLayoutMode(mode) {
      if (state.treeLayout) {
        state.layoutMode = 'yggdrasil';
        return;
      }
      state.layoutMode = mode;
      state.positions = buildPositions(state.skills, state.scale, mode);
    }
    function setAutoRotate(on) {
      state.autoRotate = on;
    }
    function setColorMode(mode) {
      state.colorMode = mode;
    }

    function setDragMode(mode) {
      state.dragMode = mode;
    }

    function randomZoom() {
      if (!state.skills.length) return;
      const picked = state.skills[Math.floor(Math.random() * state.skills.length)];
      state.paused = true;
      if (state.pauseBtnEl) { state.pauseBtnEl.textContent = '▶'; state.pauseBtnEl.classList.add('active'); state.pauseBtnEl.setAttribute('aria-pressed', 'true'); }
      state.zoom = 2.2;
      if (state.zoomCounterEl) state.zoomCounterEl.textContent = state.zoom.toFixed(1) + '×';
      state.hoveredId = picked.id;
      state.lastHoveredId = null;
      const p0 = state.positions[picked.id];
      if (p0) {
        const ry = state.t * 0.16 + state.orbitY;
        const rx = Math.sin(state.t * 0.055) * 0.20 + state.orbitX;
        // Calculate projected center for the current rotation
        let p = p0;
        if (state.layoutMode === 'semantic' || state.layoutMode === 'spectral') {
          p = rotY(rotX(p, rx), ry);
          p = rotXW(p, state.t * 0.12);
          p = rotYW(p, state.t * 0.06);
        } else {
          p = rotX(rotY(p0, ry), rx);
        }
        const pr = project(p);
        state.panX += state.width / 2 - pr.sx;
        state.panY += state.height / 2 - pr.sy;
      }
    }

    function setPaused(on) {
      state.paused = on;
    }
    function isPaused() {
      return state.paused;
    }

    function setViewMode(mode, viewOptions) {
      const target = mode === 'explorer3d' ? 1 : 0;
      const opts = viewOptions || {};
      if (target === 1 && state.viewMix < 0.001) {
        // The ambient clock keeps node shimmer alive in the flat hero. Reset
        // camera motion at entry so the morph begins from that exact frontal
        // silhouette instead of resolving at an arbitrary accumulated angle.
        state.t = 0;
        state.orbitX = 0;
        state.orbitY = 0;
        state.panX = 0;
        state.panY = 0;
        state.zoom = 1;
      }
      state.viewFrom = state.viewMix;
      state.viewTarget = target;
      state.viewPhase = target === 1 ? 'entering3d' : 'exiting3d';
      state.viewComplete = typeof opts.onComplete === 'function' ? opts.onComplete : null;
      const immediate = opts.immediate === true || _reducedMotion();
      if (immediate || Math.abs(state.viewFrom - target) < 0.001) {
        state.viewMix = target;
        state.viewStartedAt = null;
        state.viewPhase = target === 1 ? 'explorer3d' : 'hero2d';
        const done = state.viewComplete;
        state.viewComplete = null;
        if (done) done(state.viewPhase);
        return;
      }
      state.viewDuration = Math.max(120, (Number(opts.duration) || 900) * Math.abs(target - state.viewFrom));
      state.viewStartedAt = performance.now();
    }

    function getViewState() {
      return {
        phase: state.viewPhase,
        mix: state.viewMix,
        target: state.viewTarget,
        available: Boolean(state.treeLayout),
        nodeCount: state.skills.length,
        edgeCount: state.treeEdges.length,
        diagnostics: state.treeLayout && state.treeLayout.diagnostics ? state.treeLayout.diagnostics : null,
      };
    }

    return { setSkills, setTreeLayout, setNamedMap, setTitleMap, setOriginMap, resize, start, stop, resetFilters, setInteractive, setLabelMode, getLabelMode, getStatusEl, setStatusEl, setMeta, setLayoutMode, setAutoRotate, setColorMode, setDragMode, randomZoom, setPaused, isPaused, setViewMode, getViewState };
  }

  const hero = document.getElementById('hero');
  const trigger = document.querySelector('[data-graph-trigger]');
  const isMobile = window.matchMedia('(max-width:700px)').matches;

  // graphMode wiring (local-graph readiness, Stage 5):
  //   1. <html data-graph-mode="local" data-graph-handle="alice">
  //   2. ?mode=local&handle=alice  in the page URL
  // The first non-empty source wins; absence falls back to 'public'.
  function _resolveGraphMode() {
    const html = document.documentElement;
    const dsMode = (html.dataset.graphMode || '').toLowerCase();
    const dsHandle = html.dataset.graphHandle || '';
    let mode = dsMode === 'local' ? 'local' : 'public';
    let handle = dsHandle;
    try {
      const params = new URLSearchParams(window.location.search);
      const qm = (params.get('mode') || '').toLowerCase();
      const qh = params.get('handle') || '';
      if (qm === 'local') mode = 'local';
      if (qh) handle = qh;
    } catch (_) { /* ignore — non-browser env */ }
    return { mode, handle };
  }
  const _graphIdentity = _resolveGraphMode();
  // In local mode, rewrite the nav-trigger / dialog title to the
  // owner handle. Public mode leaves the existing copy alone.
  if (_graphIdentity.mode === 'local' && _graphIdentity.handle) {
    const navTrigger = document.querySelector('[data-graph-trigger]');
    if (navTrigger) navTrigger.textContent = '@' + _graphIdentity.handle + ' · Atlas';
    const dialogTitle = document.getElementById('skillGraphTitle');
    if (dialogTitle) dialogTitle.textContent = '@' + _graphIdentity.handle + ' · Atlas';
  }

  // ── SINGLE GRAPH INSTANCE ─────────────────────────────────────
  // Only one createSkillGraph call. The hero graph starts ambient
  // (no labels, no interaction). Clicking "Graph (3D)" promotes it
  // to fullscreen interactive mode with labels, zoom, pan, hover.
  // This halves GPU/memory usage vs. the previous two-canvas setup.
  const heroGraph = createSkillGraph(document.getElementById('canvas3d'), {
    labelMode: 'none',
    scale: GRAPH_SCALE,
    stars: isMobile ? 120 : 280,
    pointerTarget: hero,
    graphMode: _graphIdentity.mode,
    graphHandle: _graphIdentity.handle,
    _prepareInteractive: true,   // build chrome but keep hidden
  });

  // ── FULLSCREEN GRAPH MODE ────────────────────────────────────
  // Instead of opening a dialog with a second canvas, we toggle
  // #hero into a fixed fullscreen state and enable interactivity
  // on the existing canvas.
  let _graphFullscreen = false;
  let _graphClosing = false;
  let _pendingOpen = false;
  let _heroOriginRect = null;

  // Build status bar for fullscreen mode
  const _graphStatusBar = document.createElement('div');
  _graphStatusBar.className = 'graph-fullscreen-status';
  _graphStatusBar.setAttribute('data-graph-status', '');
  _graphStatusBar.setAttribute('data-interactive-chrome', '');
  hero.appendChild(_graphStatusBar);

  // Build the close button overlay for fullscreen mode
  const _graphCloseOverlay = document.createElement('div');
  _graphCloseOverlay.className = 'graph-fullscreen-chrome';
  _graphCloseOverlay.setAttribute('data-interactive-chrome', '');
  _graphCloseOverlay.innerHTML =
    '<div class="graph-fullscreen-header">' +
    '<div class="graph-atlas-controls">' +
    '<button type="button" class="graph-action-btn" data-graph-labels title="Labels: None/Priority"><svg class="ico" width="18" height="18" aria-hidden="true"><use href="assets/icons.svg#view-list"/></svg><span>Labels</span></button>' +
    '<button type="button" class="graph-action-btn" data-graph-mouse title="Interaction: Orbit/Pan"><svg class="ico" width="18" height="18" aria-hidden="true"><use href="assets/icons.svg#rotate"/></svg><span>Orbit</span></button>' +
    '</div>' +
    '<div class="graph-dialog-actions">' +
    '<a class="graph-action-btn" href="graph/gaia.gexf" aria-label="Download GEXF" download><svg class="ico" width="16" height="16" aria-hidden="true"><use href="assets/icons.svg#download"/></svg><span>GEXF</span></a>' +
    '<button type="button" class="graph-action-btn" data-graph-fullscreen-close aria-label="Close skill graph"><svg class="ico" width="20" height="20" aria-hidden="true"><use href="assets/icons.svg#close-x"/></svg></button>' +
    '</div>' +
    '</div>';
  hero.appendChild(_graphCloseOverlay);

  const hudToggleBtn = document.createElement('button');
  hudToggleBtn.className = 'graph-action-btn graph-hud-toggle-btn';
  hudToggleBtn.setAttribute('aria-label', 'Toggle HUD');
  hudToggleBtn.innerHTML = '<svg class="ico" width="18" height="18" aria-hidden="true"><use href="assets/icons.svg#hud-toggle"/></svg><span>Hide Controls</span>';
  hero.appendChild(hudToggleBtn);

  hudToggleBtn.addEventListener('click', () => {
    hero.classList.toggle('hud-hidden');
    hudToggleBtn.querySelector('span').textContent = hero.classList.contains('hud-hidden') ? 'Show Controls' : 'Hide Controls';
  });



  // ── Focus management for the fullscreen "dialog" ───────────────
  // Saved when opening so we can restore on close. Keyed at module
  // scope (not closure) so close handlers can read it.
  let _prevFocus = null;
  function _getHeroTabbables() {
    return Array.from(hero.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )).filter(el => el.offsetParent !== null || el === document.activeElement);
  }
  function _trapTabKey(e) {
    if (e.key !== 'Tab') return;
    const tabbables = _getHeroTabbables();
    if (!tabbables.length) return;
    const first = tabbables[0];
    const last = tabbables[tabbables.length - 1];
    if (e.shiftKey) {
      if (document.activeElement === first || !hero.contains(document.activeElement)) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }

  function _setTreeClip(rect) {
    const top = rect ? Math.max(0, rect.top) : 0;
    const left = rect ? Math.max(0, rect.left) : 0;
    const right = rect ? Math.max(0, window.innerWidth - rect.right) : 0;
    const bottom = rect ? Math.max(0, window.innerHeight - rect.bottom) : 0;
    hero.style.setProperty('--hero-tree-shell-top', top + 'px');
    hero.style.setProperty('--hero-tree-shell-right', right + 'px');
    hero.style.setProperty('--hero-tree-shell-bottom', bottom + 'px');
    hero.style.setProperty('--hero-tree-shell-left', left + 'px');
  }

  function _updateExploreButton(pressed) {
    const exploreBtn = document.getElementById('hudToggleBtn');
    if (exploreBtn) exploreBtn.setAttribute('aria-pressed', String(pressed));
  }

  function openGraphFullscreen() {
    if (_graphFullscreen && !_graphClosing) return true;
    if (!heroGraph.getViewState().available) {
      _pendingOpen = true;
      hero.dataset.treeState = 'loading';
      if (_graphStatusBar) _graphStatusBar.textContent = 'Preparing the Gaia World Tree…';
      return false;
    }
    _pendingOpen = false;
    _graphFullscreen = true;
    _graphClosing = false;
    _heroOriginRect = hero.getBoundingClientRect();
    _setTreeClip(_heroOriginRect);
    hero.classList.remove('hero-tree-explorer', 'hero-tree-exiting', 'hero-graph-fullscreen');
    hero.classList.add('hero-tree-entering');
    hero.dataset.treeState = 'entering3d';
    document.body.classList.add('hero-tree-explorer-open');
    _updateExploreButton(true);

    // Always start with HUD visible — mobile users were complaining
    // they had to discover the "Show Controls" button before seeing
    // the bottom bar, search, legend, or speed strip.
    hero.classList.remove('hud-hidden');
    hudToggleBtn.querySelector('span').textContent = 'Hide Controls';

    heroGraph.setInteractive(false);
    heroGraph.setLabelMode('none');
    heroGraph.setStatusEl(_graphStatusBar);

    // Sync header button states
    const labelsBtn = _graphCloseOverlay.querySelector('[data-graph-labels]');
    if (labelsBtn) labelsBtn.classList.remove('active');
    const mouseBtn = _graphCloseOverlay.querySelector('[data-graph-mouse]');
    if (mouseBtn) mouseBtn.querySelector('span').textContent = 'Orbit';

    // Capture focus and establish modal semantics before setViewMode(). Under
    // reduced motion its completion callback is synchronous, so doing this
    // afterward would lose the opener and break focus restoration on exit.
    _prevFocus = document.activeElement;
    hero.setAttribute('aria-modal', 'true');
    hero.setAttribute('role', 'dialog');
    hero.setAttribute('aria-label', 'Gaia World Tree explorer');
    hero.setAttribute('tabindex', '-1');
    if (typeof hero.focus === 'function') hero.focus();
    document.addEventListener('keydown', _trapTabKey);

    heroGraph.resize();
    requestAnimationFrame(() => _setTreeClip(null));
    heroGraph.setViewMode('explorer3d', {
      duration: 900,
      onComplete: () => {
        if (_graphClosing) return;
        hero.classList.remove('hero-tree-entering');
        hero.classList.add('hero-tree-explorer');
        hero.dataset.treeState = 'explorer3d';
        heroGraph.setInteractive(true);
        const colPanel = hero.querySelector('.graph-collection-panel');
        if (colPanel) colPanel.style.display = 'flex';
        const closeBtn = _graphCloseOverlay.querySelector('[data-graph-fullscreen-close]');
        if (closeBtn && typeof closeBtn.focus === 'function') closeBtn.focus();
      },
    });

    return true;
  }

  function closeGraphFullscreen() {
    if (!_graphFullscreen || _graphClosing) return false;
    _pendingOpen = false;
    _graphClosing = true;
    hero.classList.remove('hero-tree-entering', 'hero-tree-explorer', 'hero-graph-fullscreen');
    hero.classList.add('hero-tree-exiting');
    hero.dataset.treeState = 'exiting3d';
    heroGraph.setInteractive(false);
    heroGraph.setLabelMode('none');
    document.querySelectorAll('.graph-skill-panel, .graph-collection-panel').forEach(el => el.style.display = 'none');
    requestAnimationFrame(() => _setTreeClip(_heroOriginRect));
    heroGraph.setViewMode('hero2d', {
      duration: 900,
      onComplete: () => {
        hero.classList.remove('hero-tree-exiting', 'hero-graph-fullscreen');
        hero.dataset.treeState = 'hero2d';
        document.body.classList.remove('hero-tree-explorer-open');
        ['--hero-tree-shell-top', '--hero-tree-shell-right', '--hero-tree-shell-bottom', '--hero-tree-shell-left'].forEach(name => hero.style.removeProperty(name));
        hero.removeAttribute('aria-modal');
        hero.removeAttribute('role');
        hero.removeAttribute('aria-label');
        hero.removeAttribute('tabindex');
        document.removeEventListener('keydown', _trapTabKey);
        _graphFullscreen = false;
        _graphClosing = false;
        _updateExploreButton(false);
        heroGraph.resize();
        if (_prevFocus && typeof _prevFocus.focus === 'function') {
          try { _prevFocus.focus(); } catch (_) { /* element may be detached */ }
        }
        _prevFocus = null;
      },
    });
    return true;
  }

  if (trigger) {
    trigger.addEventListener('click', openGraphFullscreen);
  }

  // Close button inside the fullscreen chrome
  _graphCloseOverlay.querySelector('[data-graph-fullscreen-close]').addEventListener('click', closeGraphFullscreen);

  _graphCloseOverlay.querySelector('[data-graph-labels]').addEventListener('click', (e) => {
    const btn = e.currentTarget;
    const modes = ['none', 'all'];
    const current = modes.indexOf(heroGraph.getLabelMode());
    const next = modes[(current + 1) % modes.length];
    heroGraph.setLabelMode(next);
    btn.classList.toggle('active', next !== 'none');
  });

  _graphCloseOverlay.querySelector('[data-graph-mouse]').addEventListener('click', (e) => {
    const btn = e.currentTarget;
    const isOrbit = btn.querySelector('span').textContent === 'Orbit';
    const next = isOrbit ? 'pan' : 'orbit';
    btn.querySelector('span').textContent = next.charAt(0).toUpperCase() + next.slice(1);
    btn.querySelector('use').setAttribute('href', 'assets/icons.svg#' + (isOrbit ? 'hud-toggle' : 'rotate'));
    heroGraph.setDragMode(next);
  });

  const _randomBtn = _graphCloseOverlay.querySelector('[data-graph-random]');
  if (_randomBtn) {
    _randomBtn.addEventListener('click', () => {
      heroGraph.randomZoom();
    });
  }

  // Escape key to exit
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && _graphFullscreen) {
      e.preventDefault();
      e.stopPropagation();
      closeGraphFullscreen();
    }
  });

  window.gaiaWorldTree = {
    open: openGraphFullscreen,
    close: closeGraphFullscreen,
    toggle: function () {
      return (_graphFullscreen && !_graphClosing) ? closeGraphFullscreen() : openGraphFullscreen();
    },
    state: function () {
      const view = heroGraph.getViewState();
      return {
        phase: hero.dataset.treeState || view.phase,
        mix: view.mix,
        available: view.available,
        nodeCount: view.nodeCount,
        edgeCount: view.edgeCount,
        open: _graphFullscreen,
        closing: _graphClosing,
        diagnostics: view.diagnostics,
      };
    },
  };

  // ── Canvas a11y semantics ─────────────────────────────────────
  // The 3D canvas is a visual representation of the registry graph.
  // Provide role=img + a rich aria-label that summarises counts so
  // screen readers get a meaningful description. The label is
  // refreshed after the skills array and the named-skill index both
  // resolve. A hidden offscreen link points keyboard / AT users to
  // the static SVG fallback at graph/gaia.svg.
  const _canvas3d = document.getElementById('canvas3d');
  let _ariaSkillsCount = 0;
  let _ariaEdgesCount = 0;
  let _ariaNamedCount = 0;
  let _ariaApexCount = 0;
  function _refreshCanvasAria() {
    if (!_canvas3d) return;
    _canvas3d.setAttribute('role', 'img');
    _canvas3d.setAttribute(
      'aria-label',
      'Gaia skill graph — ' + _ariaSkillsCount + ' skills · ' +
      _ariaEdgesCount + ' prerequisite links · ' +
      _ariaNamedCount + ' named · ' +
      _ariaApexCount + ' apex (6★). Use arrow keys to orbit; +/- to zoom.'
    );
  }
  _refreshCanvasAria();
  // Hidden SVG fallback link inside #hero — visually offscreen but
  // present in the DOM for screen readers and as a no-CSS fallback.
  const _svgFallbackLink = document.createElement('a');
  _svgFallbackLink.className = 'sr-only';
  _svgFallbackLink.href = 'graph/gaia.svg';
  _svgFallbackLink.textContent = 'Static SVG version of the skill graph';
  _svgFallbackLink.style.cssText = 'position:absolute;left:-9999px;';
  hero.appendChild(_svgFallbackLink);

  // Probe the graph directory first so we get a clear diagnostic if the
  // static-asset host isn't serving JSON files from graph/.
  const _pingOk = fetch(prefix + 'graph/ping.json', { cache: 'no-store' })
    .then(r => r.ok && r.json()).then(d => !!(d && d.ok)).catch(() => false);

  fetch(GRAPH_JSON_URL, { cache: 'reload' })
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status} from ${GRAPH_JSON_URL}`);
      const ct = response.headers.get('content-type') || '';
      if (!ct.includes('json') && !ct.includes('text/plain')) {
        return response.text().then(body => {
          throw new Error(`Expected JSON, got ${ct || 'no content-type'}; body starts: ${body.slice(0, 80)}`);
        });
      }
      return response.json();
    })
    .then(graph => {
      _initMetaGraph(graph.meta);
      if (heroGraph) heroGraph.setMeta(graph.meta);
      // §4 runtime effective-rank join — attach `effectiveRank` (parsed from the
      // pre-joined `namedMaxLevel` glyph string) onto each SOURCE skill object
      // BEFORE the layout engine runs. world-tree-layout.js reads
      // node.effectiveRank via readEffectiveRank; it never re-derives the join.
      // Computed ONCE here, not per-frame (§8 performance).
      if (graph && Array.isArray(graph.skills)) {
        graph.skills.forEach(skill => {
          if (skill && typeof skill === 'object') {
            skill.effectiveRank = starsFromLabel(skill.namedMaxLevel);
          }
        });
      }
      const skills = normalizeSkills(graph);
      let treeLayout = null;
      const layoutApi = window.GaiaWorldTreeLayout;
      const buildLayout = layoutApi && (layoutApi.buildWorldTreeLayout || layoutApi.compute);
      if (typeof buildLayout === 'function') {
        try {
          treeLayout = buildLayout(graph, { width: 760, height: 680 });
        } catch (error) {
          console.warn('World Tree layout unavailable:', error);
        }
      }
      return { skills, treeLayout };
    })

    .then(result => {
      const skills = result.skills;
      if (heroGraph) heroGraph.setSkills(skills, result.treeLayout);
      _ariaSkillsCount = skills.length;
      _ariaEdgesCount = skills.reduce((acc, s) => acc + (Array.isArray(s.prerequisites) ? s.prerequisites.length : 0), 0);
      _ariaApexCount = skills.reduce((acc, s) => acc + (s.level === '6★' ? 1 : 0), 0);
      _refreshCanvasAria();
      if (_pendingOpen && heroGraph.getViewState().available) openGraphFullscreen();
    })
    .catch(error => {
      console.warn('Using embedded fallback skill graph:', error);
      _pingOk.then(ping => {
        const status = document.querySelector('[data-graph-status]');
        const pingMsg = ping ? 'graph/ dir reachable' : 'graph/ dir UNREACHABLE';
        if (status) status.textContent = `Fallback graph active (${pingMsg}). Fetch error: ${error && error.message ? error.message : String(error)}`;
      });
    });

  fetch(prefix + 'graph/named/index.json' + version)
    .then(r => r.ok ? r.json() : Promise.reject())
    .then(indexData => {
      const map = {};
      const titleMap = {};
      const originMap = {};
      const buckets = indexData.buckets || {};
      var redacts = function (lvl) { return window.isRedacted && window.isRedacted(lvl); };
      Object.entries(buckets).forEach(([skillId, arr]) => {
        if (Array.isArray(arr) && arr.length) {
          const origin = arr.find(e => e.origin) || arr[0];
          if (origin && origin.id) {
            // Always redact (never drop) a pre-named/demoted (≤1★) handle:
            // keep the slash-name shape but withhold the handle segment.
            map[skillId] = redacts(origin.level)
              ? (window.REDACTED_BLOCK || '████████') + '/' + (origin.id.split('/')[1] || origin.id)
              : origin.id;
          }
          if (origin && origin.title) titleMap[skillId] = origin.title;
          // A pre-named/demoted skill has no Origin standing.
          if (arr.some(e => e.origin && !redacts(e.level))) originMap[skillId] = true;
        }
      });
      if (heroGraph) heroGraph.setNamedMap(map);
      if (heroGraph) heroGraph.setTitleMap(titleMap);
      if (heroGraph) heroGraph.setOriginMap(originMap);
      _ariaNamedCount = Object.keys(map).length;
      _refreshCanvasAria();
    })
    .catch(() => { });
})();

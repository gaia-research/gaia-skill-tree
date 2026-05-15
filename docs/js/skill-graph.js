(function () {
  const GRAPH_JSON_URL = 'graph/gaia.json';
  const GRAPH_SCALE = 1.625;

  // Defaults — overwritten from meta once data loads
  let PALETTE = {
    basic:    { rgb:'56,189,248',   hex:'#38bdf8' },
    extra:    { rgb:'192,132,252',  hex:'#c084fc' },
    unique:   { rgb:'124,58,237',   hex:'#7c3aed' },
    ultimate: { rgb:'245,158,11',   hex:'#f59e0b' },
  };
  let TYPE_ORDER = { basic:0, extra:1, unique:2, ultimate:3 };
  let RANK_META = {
    '1★':  { name:'Awakened',       hex:'#38bdf8', bg:'rgba(56,189,248,.12)' },
    '2★': { name:'Named',          hex:'#63cab7', bg:'rgba(99,202,183,.12)' },
    '3★':{ name:'Evolved',        hex:'#a78bfa', bg:'rgba(167,139,250,.12)' },
    '4★': { name:'Hardened',       hex:'#e879f9', bg:'rgba(232,121,249,.12)' },
    '5★':  { name:'Transcendent',   hex:'#fbbf24', bg:'rgba(251,191,36,.12)' },
    '6★': { name:'Transcendent ★', hex:'#fbbf24', bg:'rgba(251,191,36,.20)' },
  };

  function _initMetaGraph(meta) {
    if (!meta) return;
    if (meta.typeColors) {
      PALETTE = {};
      Object.keys(meta.typeColors).forEach(function(t) {
        PALETTE[t] = { rgb: meta.typeColors[t].rgb, hex: meta.typeColors[t].hex };
      });
    }
    if (meta.levelColors && meta.levelLabels) {
      RANK_META = {};
      Object.keys(meta.levelColors).forEach(function(k) {
        if (k === '0★') return;
        RANK_META[k] = { name: meta.levelLabels[k] || k, hex: meta.levelColors[k].hex, bg: meta.levelColors[k].bg };
      });
    }
  }

  const FALLBACK_SKILLS = [
    { id:'tokenize', type:'basic', name:'Tokenize', prerequisites:[] },
    { id:'retrieve', type:'basic', name:'Retrieve', prerequisites:[] },
    { id:'embed-text', type:'basic', name:'Embed Text', prerequisites:[] },
    { id:'score-relevance', type:'basic', name:'Score Relevance', prerequisites:[] },
    { id:'web-search', type:'basic', name:'Web Search', prerequisites:[] },
    { id:'summarize', type:'basic', name:'Summarize', prerequisites:[] },
    { id:'cite-sources', type:'basic', name:'Cite Sources', prerequisites:[] },
    { id:'code-generation', type:'basic', name:'Code Generation', prerequisites:[] },
    { id:'execute-bash', type:'basic', name:'Execute Bash', prerequisites:[] },
    { id:'tool-select', type:'basic', name:'Tool Select', prerequisites:[] },
    { id:'chunk-document', type:'basic', name:'Chunk Document', prerequisites:[] },
    { id:'rank', type:'basic', name:'Rank', prerequisites:[] },
    { id:'rag-pipeline', type:'extra', name:'RAG Pipeline', prerequisites:['retrieve','chunk-document','embed-text','score-relevance','tokenize','rank'] },
    { id:'research', type:'extra', name:'Research', prerequisites:['web-search','summarize','cite-sources'] },
    { id:'error-interpretation', type:'basic', name:'Error Interpretation', prerequisites:[] },
    { id:'autonomous-debug', type:'extra', name:'Autonomous Debug', prerequisites:['code-generation','execute-bash','error-interpretation'] },
    { id:'ghostwrite', type:'extra', name:'Ghostwrite', prerequisites:['research','write-report','audience-model'] },
    { id:'knowledge-harvest', type:'extra', name:'Knowledge Harvest', prerequisites:['web-scrape','embed-text','extract-entities'] },
    { id:'autonomous-research-agent', type:'ultimate', name:'Autonomous Research Agent', prerequisites:['research','ghostwrite','knowledge-harvest'] },
  ];
  const FALLBACK_NAMED_MAP = {
    'automated-testing':           '0xdarkmatter/pytest-patterns',
    'test-driven-development':     'addy-osmani/test-driven-development',
    'document-editing':            'anthropic/pptx',
    'tool-creation':               'anthropic/skill-creator',
    'autonomous-debug':            'devin-ai/autonomous-swe',
    'write-report':                'glincker/readme-generator',
    'browser-automation':          'gooseworks/notte-browser',
    'autonomous-research-agent':   'karpathy/autoresearch',
    'framework-upgrade':           'laravel/upgrade-laravel-v13',
    'ux-audit':                    'martin-stepanoski/nielsen-heuristics-audit',
    'multi-agent-orchestration-v': 'ruvnet/flow-nexus-swarm',
    'generate-test':               'upsonic/unittest-generator',
    'skill-discovery':             'vercel/find-skills',
    'rag-pipeline':                'yonatangross/orchestkit-rag',
  };
  const FALLBACK_TITLE_MAP = {
    'automated-testing':           'The Quality Guardian',
    'test-driven-development':     'The Red-Green Oath',
    'document-editing':            'The Slide Artisan',
    'tool-creation':               "The Skill Forger's Art",
    'autonomous-debug':            "The Codebreaker's Will",
    'write-report':                'The Document Weaver',
    'browser-automation':          'The Digital Navigator',
    'autonomous-research-agent':   "The Scholar's Compass",
    'framework-upgrade':           "The Versionist's Trial",
    'ux-audit':                    'The Ten Laws of Sight',
    'multi-agent-orchestration-v': "The Grand Conductor's Blueprint",
    'generate-test':               'The Test Weaver',
    'skill-discovery':             'The Registry Scout',
    'rag-pipeline':                'The Knowledge Architect',
  };

  function normalizeSkills(graph) {
    const TYPE_ALIASES = { atomic: 'basic', composite: 'extra', legendary: 'ultimate' };
    const skills = (graph && graph.skills) ? graph.skills : FALLBACK_SKILLS;
    return skills.map(skill => ({
      id: skill.id,
      name: skill.name || skill.id,
      type: TYPE_ALIASES[skill.type] || skill.type || 'basic',
      level: skill.level || '',
      effectiveLevel: skill.effectiveLevel || (skill.level || ''),
      demerits: Array.isArray(skill.demerits) ? skill.demerits : [],
      rarity: skill.rarity || '',
      prerequisites: Array.isArray(skill.prerequisites) ? skill.prerequisites : [],
    })).filter(skill => skill.id);
  }

  function stableHash(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i += 1) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return Math.abs(h >>> 0);
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
      phase: (seed % 628) / 100,
    };
  }

  function buildPositions(skills, scale) {
    const groups = { basic:[], extra:[], ultimate:[] };
    const satellite = { unique:[], orphan:[] };
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
    Object.values(groups).forEach(group => group.sort((a,b) => (a.name || a.id).localeCompare(b.name || b.id)));
    satellite.unique.sort((a,b) => (a.name || a.id).localeCompare(b.name || b.id));
    satellite.orphan.sort((a,b) => (a.name || a.id).localeCompare(b.name || b.id));
    const positions = {};
    const radii = { basic: 250 * scale, extra: 145 * scale, ultimate: 44 * scale };
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
        _orbitAmp:   (22 + (seed % 38)) * scale,
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
    const endTick   = Math.floor((logValue + mainSize / 2 / ppu) / minorStep);
    ctx2.lineWidth = 1;
    for (let tick = startTick; tick <= endTick; tick++) {
      const pos = mainSize / 2 + (tick * minorStep - logValue) * ppu;
      const isMajor = tick % majorEvery === 0;
      const tickLen = isMajor ? crossSize * 0.38 : crossSize * 0.18;
      const alpha = isMajor ? 0.18 : 0.08;
      ctx2.beginPath();
      if (vert) { ctx2.moveTo(crossSize/2 - tickLen/2, pos); ctx2.lineTo(crossSize/2 + tickLen/2, pos); }
      else       { ctx2.moveTo(pos, crossSize/2 - tickLen/2); ctx2.lineTo(pos, crossSize/2 + tickLen/2); }
      ctx2.strokeStyle = `rgba(148,163,184,${alpha})`;
      ctx2.stroke();
    }
    ctx2.beginPath();
    if (vert) { ctx2.moveTo(0, mainSize/2); ctx2.lineTo(crossSize, mainSize/2); }
    else      { ctx2.moveTo(mainSize/2, 0); ctx2.lineTo(mainSize/2, crossSize); }
    ctx2.strokeStyle = `rgba(148,163,184,.28)`;
    ctx2.lineWidth = 1;
    ctx2.stroke();
  }

  function createSkillGraph(canvas, options) {
    const ctx = canvas.getContext('2d');
    const DPR = Math.min(window.devicePixelRatio || 1, 2);
    const NAMED_LEVELS = new Set(['2★','3★','4★','5★','6★']);
    const state = {
      skills: FALLBACK_SKILLS,
      positions: buildPositions(FALLBACK_SKILLS, GRAPH_SCALE),
      stars: [],
      width: 0,
      height: 0,
      t: 0,
      mx: 0,
      my: 0,
      labelMode: options.labelMode || 'ultimate',
      scale: options.scale || GRAPH_SCALE,
      zoom: 1,
      statusEl: options.statusEl || null,
      running: options.autostart !== false,
      frame: null,
      orbitX: 0,
      orbitY: 0,
      dragging: false,
      dragMode: 'pan',
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
      namedMap: FALLBACK_NAMED_MAP,
      titleMap: FALLBACK_TITLE_MAP,
    };

    function resize() {
      const parent = canvas.parentElement;
      state.width = parent.clientWidth;
      state.height = parent.clientHeight;
      canvas.width = state.width * DPR;
      canvas.height = state.height * DPR;
      canvas.style.width = state.width + 'px';
      canvas.style.height = state.height + 'px';
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
          radius: (200 + (seed % 140)) * state.scale,
          isAurora,
          hue: isAurora ? auroraHues[i - 6] : 220,
          sat: isAurora ? 60 : 5 + (seed % 8),
          alpha: isAurora ? 0.035 + (seed % 4) / 100 : 0.04 + (seed % 5) / 100,
        };
      });
    }

    function setSkills(skills) {
      state.skills = skills;
      state.positions = buildPositions(skills, state.scale);
      const newAlphas = {};
      skills.forEach(s => { newAlphas[s.id] = state.nodeAlphas[s.id] !== undefined ? state.nodeAlphas[s.id] : 1.0; });
      state.nodeAlphas = newAlphas;
      if (state.statusEl) {
        const edgeCount = skills.reduce((sum, skill) => sum + skill.prerequisites.length, 0);
        const uniqueCount = skills.filter(s => s.type === 'unique').length;
        const mb = (fill) => `<svg class="gst-icon" viewBox="0 0 10 15" fill="none" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"><rect x=".7" y=".7" width="8.6" height="13.6" rx="4.3"/><path d="M5 .7v5.8" stroke-width="1"/><path d="M.7 6.5h8.6" stroke-width="1"/>${fill}</svg>`;
        const iL = mb('<rect x=".7" y=".7" width="4.3" height="5.8" rx="2 0 0 2" stroke="none" fill="currentColor" opacity=".55"/>');
        const iM = mb('<rect x="3.4" y="1.4" width="3.2" height="4.2" rx="1.6" stroke="none" fill="currentColor" opacity=".55"/>');
        const iS = mb('<rect x="3.4" y="1.4" width="3.2" height="4.2" rx="1.6" stroke-width=".9" opacity=".5"/><path d="M5 2.2v3.2M4 3.1 5 2.2 6 3.1M4 4.5 5 5.4 6 4.5" stroke-width=".9"/>');
        const stat = `<span class="gst-stat">${skills.length}<span class="gst-dim"> skills</span> · ${edgeCount}<span class="gst-dim"> links</span>` +
          (uniqueCount ? ` · <span style="color:#7c3aed">${uniqueCount}</span><span class="gst-dim"> Unique</span>` : '') +
          `</span>`;
        let tips = '';
        if (options.draggable) {
          tips += `<span class="gst-tip">${iL}<span>pan</span></span>`;
          tips += `<span class="gst-tip"><kbd class="gst-ctrl">⌃</kbd>${iL}<span class="gst-or">/</span>${iM}<span>orbit</span></span>`;
        }
        if (options.zoomable) tips += `<span class="gst-tip">${iS}<span>zoom</span></span>`;
        state.statusEl.innerHTML = stat + tips;
      }
    }

    function rotX(p, a) {
      const c = Math.cos(a), s = Math.sin(a);
      return { x: p.x, y: c*p.y - s*p.z, z: s*p.y + c*p.z, phase: p.phase };
    }
    function rotY(p, a) {
      const c = Math.cos(a), s = Math.sin(a);
      return { x: c*p.x + s*p.z, y: p.y, z: -s*p.x + c*p.z, phase: p.phase };
    }
    function project(p) {
      const fov = Math.min(state.width, state.height) * 0.75;
      const denom = fov + p.z + 360 * state.scale;
      if (denom < 1) return { sx: state.width / 2 + state.panX, sy: state.height / 2 + state.panY, scale: 0 };
      const dist = fov / denom;
      const z = state.zoom;
      return { sx: state.width / 2 + p.x * dist * z + state.panX, sy: state.height / 2 + p.y * dist * z + state.panY, scale: dist * z };
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
      const glow = ctx.createRadialGradient(sx, sy, 0, sx, sy, r * 4.2);
      glow.addColorStop(0,   `rgba(239,68,68,${Math.min(alpha * 0.7, 1).toFixed(2)})`);
      glow.addColorStop(0.4, `rgba(239,68,68,${Math.min(alpha * 0.25, 1).toFixed(2)})`);
      glow.addColorStop(1,   'rgba(239,68,68,0)');
      ctx.beginPath(); ctx.arc(sx, sy, r * 4.2, 0, Math.PI * 2); ctx.fillStyle = glow; ctx.fill();
      ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(239,68,68,${Math.min(alpha * 1.2, 1).toFixed(2)})`; ctx.fill();
      ctx.beginPath(); ctx.arc(sx - r * 0.28, sy - r * 0.28, r * 0.32, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${(alpha * 0.65).toFixed(2)})`; ctx.fill();
    }
    function drawNodeVI(sx, sy, r, alpha, t, p) {
      const phase = p.phase || 0;
      const spin = t * 1.3 + phase;

      // Impact blink: fires every ~5s, quick flash then gradual fade-out
      const blinkT = (t + phase * 2.3) % 1.8;
      const blink = blinkT < 0.012 ? 1 : blinkT < 0.18 ? 1 - (blinkT - 0.012) / 0.168 : 0;

      // ── GOLD CORONA (outermost glow) ──
      const coronaPulse = 0.85 + 0.15 * Math.sin(t * 0.9 + phase);
      const coronaR = r * (7.5 * coronaPulse);
      const corona = ctx.createRadialGradient(sx, sy, r * 1.2, sx, sy, coronaR);
      corona.addColorStop(0,   `rgba(255,215,0,${(alpha * 0.48).toFixed(2)})`);
      corona.addColorStop(0.35,`rgba(255,170,0,${(alpha * 0.22).toFixed(2)})`);
      corona.addColorStop(0.7, `rgba(255,120,0,${(alpha * 0.08).toFixed(2)})`);
      corona.addColorStop(1,   `rgba(255,80,0,0)`);
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
        bg.addColorStop(0,   `rgba(255,255,255,${bA.toFixed(2)})`);
        bg.addColorStop(0.35,`rgba(255,240,180,${(bA * 0.45).toFixed(2)})`);
        bg.addColorStop(1,   `rgba(255,215,0,0)`);
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
        sg.addColorStop(0,   `rgba(255,240,200,${sA.toFixed(2)})`);
        sg.addColorStop(0.35,`rgba(255,215,0,${(sA * 0.5).toFixed(2)})`);
        sg.addColorStop(1,   `rgba(255,180,0,0)`);
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
      glow.addColorStop(0,   `rgba(255,255,255,${(alpha * 0.72).toFixed(2)})`);
      glow.addColorStop(0.15,`rgba(255,255,245,${(alpha * 0.52).toFixed(2)})`);
      glow.addColorStop(0.4, `rgba(255,245,210,${(alpha * 0.22).toFixed(2)})`);
      glow.addColorStop(0.7, `rgba(255,230,160,${(alpha * 0.08).toFixed(2)})`);
      glow.addColorStop(1,   `rgba(255,215,0,0)`);
      ctx.beginPath(); ctx.arc(sx, sy, glowR, 0, Math.PI * 2);
      ctx.fillStyle = glow; ctx.fill();

      // ── IMPACT BLINK (anime impact frame) ──
      if (blink > 0) {
        // White shockwave flash outward
        const blinkR = r * (12 + blink * 10);
        const blinkGrad = ctx.createRadialGradient(sx, sy, r * 0.5, sx, sy, blinkR);
        blinkGrad.addColorStop(0,   `rgba(255,255,255,${(alpha * blink * 0.9).toFixed(2)})`);
        blinkGrad.addColorStop(0.3, `rgba(255,255,255,${(alpha * blink * 0.6).toFixed(2)})`);
        blinkGrad.addColorStop(0.6, `rgba(255,255,240,${(alpha * blink * 0.25).toFixed(2)})`);
        blinkGrad.addColorStop(1,   `rgba(255,255,255,0)`);
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
      coreGrad.addColorStop(0,    `rgba(255,255,255,${Math.min(alpha * 1.2, 1).toFixed(2)})`);
      coreGrad.addColorStop(0.35, `rgba(255,253,245,${Math.min(alpha * 1.1, 1).toFixed(2)})`);
      coreGrad.addColorStop(0.7,  `rgba(255,240,200,${Math.min(alpha * 1.0, 1).toFixed(2)})`);
      coreGrad.addColorStop(1,    `rgba(255,215,0,${(alpha * 0.85).toFixed(2)})`);
      ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2);
      ctx.fillStyle = coreGrad; ctx.fill();

      // Specular highlight
      ctx.beginPath(); ctx.arc(sx - r * 0.22, sy - r * 0.22, r * 0.35, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${(alpha * 0.95).toFixed(2)})`; ctx.fill();
    }
    function drawNodeUnique(sx, sy, r, alpha, t, p) {
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
      voidGrad.addColorStop(0.75, `rgba(124,58,237,${(alpha * 0.07).toFixed(2)})`);
      voidGrad.addColorStop(1, `rgba(124,58,237,0)`);
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
        ctx.fillStyle = `rgba(167,139,250,${particleAlpha.toFixed(2)})`;
        ctx.fill();
      }
      // Event horizon ring — bright purple edge
      ctx.beginPath(); ctx.arc(sx, sy, r * 1.12, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(124,58,237,${(alpha * 0.9).toFixed(2)})`;
      ctx.lineWidth = 2; ctx.stroke();
      // Void core — fully opaque black
      ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2);
      ctx.fillStyle = '#000';
      ctx.fill();
      // Inner purple shimmer at edge of core
      ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(124,58,237,${(alpha * 0.5).toFixed(2)})`;
      ctx.lineWidth = r * 0.15; ctx.stroke();
    }
    function shouldLabel(skill) {
      if (state.redPillActive && state.namedMap[skill.id]) return true;
      if (state.labelMode === 'none') return false;
      if (state.labelMode === 'all') return true;
      if (state.labelMode === 'modal') return skill.type !== 'basic' || stableHash(skill.id) % 7 === 0;
      return skill.type === 'ultimate' || skill.type === 'unique';
    }
    function draw() {
      if (!state.running) return;
      const targetSlowdown = ((state.hoveredId || state.pinnedId) && !state.paused) ? 1 : 0;
      state.hoverSlowdown += (targetSlowdown - state.hoverSlowdown) * 0.035;
      if (!state.paused) state.t += 0.006 * state.rotSpeed * (1 - state.hoverSlowdown);
      ctx.clearRect(0, 0, state.width, state.height);
      state.projectedNodes = {};
      const ry = options.draggable
        ? state.t * 0.16 + state.orbitY
        : state.t * 0.16 + state.mx * 0.10;
      const rx = options.draggable
        ? Math.sin(state.t * 0.055) * 0.20 + state.orbitX
        : Math.sin(state.t * 0.055) * 0.20 + state.my * 0.055;
      if (state.nebula) {
        const maxR = Math.max(state.width, state.height) * 1.5;
        state.nebulaClouds.forEach(cloud => {
          const p = rotX(rotY(cloud, ry * 0.08), rx * 0.08);
          const pr = project(p);
          if (pr.scale < 0.005) return;
          const r = Math.min(cloud.radius * pr.scale * 2.8, maxR);
          if (r < 1) return;
          const g = ctx.createRadialGradient(pr.sx, pr.sy, 0, pr.sx, pr.sy, r);
          const s = cloud.sat;
          const h = cloud.hue;
          if (cloud.isAurora) {
            g.addColorStop(0,   `hsla(${h},${s}%,55%,${(cloud.alpha * 0.85).toFixed(3)})`);
            g.addColorStop(0.4, `hsla(${h},${s * 0.7}%,40%,${(cloud.alpha * 0.4).toFixed(3)})`);
            g.addColorStop(0.75,`hsla(${h},${s * 0.4}%,30%,${(cloud.alpha * 0.12).toFixed(3)})`);
            g.addColorStop(1,   `hsla(${h},${s * 0.2}%,20%,0)`);
          } else {
            g.addColorStop(0,   `hsla(${h},${s}%,72%,${(cloud.alpha * 0.8).toFixed(3)})`);
            g.addColorStop(0.3, `hsla(${h},${s}%,55%,${(cloud.alpha * 0.4).toFixed(3)})`);
            g.addColorStop(0.65,`hsla(${h},${s * 0.5}%,40%,${(cloud.alpha * 0.12).toFixed(3)})`);
            g.addColorStop(1,   `hsla(${h},0%,30%,0)`);
          }
          ctx.beginPath(); ctx.arc(pr.sx, pr.sy, r, 0, Math.PI * 2);
          ctx.fillStyle = g; ctx.fill();
        });
      }
      const xf = {};
      const allPrereqRefs = new Set();
      state.skills.forEach(skill => skill.prerequisites.forEach(pid => allPrereqRefs.add(pid)));
      state.skills.forEach(skill => {
        const p0 = state.positions[skill.id];
        if (!p0) return;
        if (p0._satellite === 'orphan') {
          const s = p0._orbitSpeed, amp = p0._orbitAmp;
          xf[skill.id] = rotX(rotY({
            x: p0.x + Math.cos(state.t * s + p0._phX) * amp,
            y: p0.y + Math.sin(state.t * s * 1.3 + p0._phY) * amp,
            z: p0.z + Math.sin(state.t * s * 0.7 + p0._phZ) * amp,
            phase: p0.phase,
          }, ry), rx);
        } else {
          xf[skill.id] = rotX(rotY(p0, ry), rx);
        }
      });
      const neighborSet = new Set();
      const focusId = state.pinnedId || state.hoveredId;
      if (focusId) {
        neighborSet.add(focusId);
        const focusSkill = state.skills.find(s => s.id === focusId);
        if (focusSkill) focusSkill.prerequisites.forEach(pid => neighborSet.add(pid));
        state.skills.forEach(s => { if (s.prerequisites.includes(focusId)) neighborSet.add(s.id); });
      }
      const hovering = Boolean(focusId);
      const isSearchActive = Boolean(state.searchText);
      const searchQuery = isSearchActive ? state.searchText.toLowerCase() : '';
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
            const matchesSearch = (skill.name || skill.id).toLowerCase().includes(searchQuery);
            targetVis = (matchesLegend && matchesSearch) ? 1.0 : 0.12;
          } else {
            targetVis = matchesLegend ? 1.0 : 0.12;
          }
        } else if (isSearchActive) {
          targetVis = (skill.name || skill.id).toLowerCase().includes(searchQuery) ? 1.0 : 0.12;
        } else {
          targetVis = 1.0;
        }
        if (state.redPillActive && !state.namedMap[skill.id]) targetVis = Math.min(targetVis, 0.07);
        if (state.nodeAlphas[skill.id] === undefined) state.nodeAlphas[skill.id] = targetVis;
        state.nodeAlphas[skill.id] += (targetVis - state.nodeAlphas[skill.id]) * 0.15;
      });
      state.stars.forEach(star => {
        const p = rotX(rotY(star, ry), rx);
        const pr = project(p);
        if (pr.scale < 0.01) return;
        ctx.beginPath();
        ctx.arc(pr.sx, pr.sy, star.size * pr.scale * 1.55, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${(star.alpha * Math.min(pr.scale * 2, 1)).toFixed(2)})`;
        ctx.fill();
      });
      const edges = [];
      state.skills.forEach(skill => {
        if (!xf[skill.id]) return;
        skill.prerequisites.forEach(pid => {
          if (!xf[pid]) return;
          edges.push({ from: pid, to: skill.id, type: skill.type, avgZ: (xf[skill.id].z + xf[pid].z) / 2 });
        });
      });
      edges.sort((a,b) => a.avgZ - b.avgZ);
      edges.forEach(edge => {
        const pa = project(xf[edge.from]), pb = project(xf[edge.to]);
        const col = PALETTE[edge.type] || PALETTE.basic;
        const depthAlpha = Math.min(Math.max((xf[edge.to].z + 430 * state.scale) / (860 * state.scale), 0.08), 1);
        const isNeighborEdge = hovering && neighborSet.has(edge.from) && neighborSet.has(edge.to);
        const fromVis = state.nodeAlphas[edge.from] !== undefined ? state.nodeAlphas[edge.from] : 1.0;
        const toVis   = state.nodeAlphas[edge.to]   !== undefined ? state.nodeAlphas[edge.to]   : 1.0;
        const edgeVis = (fromVis + toVis) / 2;
        const baseEdgeAlpha = isNeighborEdge ? 0.72 : 0.31;
        ctx.beginPath(); ctx.moveTo(pa.sx, pa.sy); ctx.lineTo(pb.sx, pb.sy);
        ctx.strokeStyle = `rgba(${col.rgb},${(depthAlpha * baseEdgeAlpha * edgeVis).toFixed(2)})`;
        ctx.lineWidth = isNeighborEdge ? (edge.type === 'ultimate' ? 2.2 : 1.4) : (edge.type === 'ultimate' ? 1.55 : 0.92);
        ctx.stroke();
      });
      const nodes = state.skills.map(skill => ({ skill, z: xf[skill.id] ? xf[skill.id].z : -9999 })).sort((a,b) => a.z - b.z);
      nodes.forEach(({ skill }) => {
        const p = xf[skill.id]; if (!p) return;
        const pr = project(p);
        if (pr.scale <= 0) return;
        state.projectedNodes[skill.id] = pr;
        const pulse = 0.84 + 0.16 * Math.sin(state.t * 2.2 + p.phase);
        const depthAlpha = Math.min(Math.max((p.z + 430 * state.scale) / (860 * state.scale), 0.16), 1);
        const col = PALETTE[skill.type] || PALETTE.basic;
        const baseR = skill.type === 'ultimate' ? 12.5 : skill.type === 'unique' ? 9.5 : skill.type === 'extra' ? 6.9 : 3.5;
        const vis = state.nodeAlphas[skill.id] !== undefined ? state.nodeAlphas[skill.id] : 1.0;
        if (skill.level === '6★') {
          drawNodeVI(pr.sx, pr.sy, baseR * state.scale * pr.scale * pulse, depthAlpha * vis, state.t, p);
        } else if (skill.type === 'unique') {
          drawNodeUnique(pr.sx, pr.sy, baseR * state.scale * pr.scale * pulse, depthAlpha * vis, state.t, p);
        } else if (state.redPillActive && state.namedMap[skill.id]) {
          drawNodeNamed(pr.sx, pr.sy, baseR * state.scale * pr.scale * pulse, depthAlpha * vis);
        } else {
          drawNode(pr.sx, pr.sy, baseR * state.scale * pr.scale * pulse, col, depthAlpha * vis);
        }
      });
      const labelNodes = nodes.filter(({ skill }) => shouldLabel(skill));
      function drawLabel(skill, highlighted) {
        const p = xf[skill.id]; if (!p) return;
        const pr = project(p);
        const depthAlpha = Math.min(Math.max((p.z + 430 * state.scale) / (860 * state.scale), 0), 1);
        if (!highlighted && depthAlpha < 0.22) return;
        const vis = state.nodeAlphas[skill.id] !== undefined ? state.nodeAlphas[skill.id] : 1.0;
        const labelAlpha = highlighted ? 1.0 : depthAlpha * Math.max(0.22, vis) * 0.9;
        if (labelAlpha < 0.04) return;
        const col = (state.redPillActive && state.namedMap[skill.id])
          ? { rgb:'239,68,68' }
          : (PALETTE[skill.type] || PALETTE.basic);
        const size = skill.type === 'ultimate' ? 13 : skill.type === 'extra' ? 10 : 8;
        ctx.font = `bold ${Math.max(6, Math.round(size * pr.scale * 1.16))}px Inter,system-ui,sans-serif`;
        ctx.fillStyle = `rgba(${col.rgb},${labelAlpha.toFixed(2)})`;
        ctx.textAlign = 'center';
        const labelText = (state.redPillActive && state.namedMap && state.namedMap[skill.id])
          ? state.namedMap[skill.id]
          : state.showTitles
            ? ((state.titleMap && state.titleMap[skill.id]) || skill.name)
            : '/' + skill.id;
        ctx.fillText(labelText, pr.sx, pr.sy + 18 * pr.scale);
      }
      labelNodes.forEach(({ skill }) => {
        const vis = state.nodeAlphas[skill.id] !== undefined ? state.nodeAlphas[skill.id] : 1.0;
        if (vis <= 0.95) drawLabel(skill, false);
      });
      labelNodes.forEach(({ skill }) => {
        const vis = state.nodeAlphas[skill.id] !== undefined ? state.nodeAlphas[skill.id] : 1.0;
        if (vis > 0.95) drawLabel(skill, true);
      });
      // Final pass: redraw unique void cores on top of everything (labels, other effects)
      nodes.forEach(({ skill }) => {
        if (skill.type !== 'unique') return;
        const p = xf[skill.id]; if (!p) return;
        const pr = project(p);
        if (pr.scale <= 0) return;
        const pulse = 0.84 + 0.16 * Math.sin(state.t * 2.2 + p.phase);
        const baseR = 9.5;
        const r = baseR * state.scale * pr.scale * pulse;
        ctx.beginPath(); ctx.arc(pr.sx, pr.sy, r * 1.05, 0, Math.PI * 2);
        ctx.fillStyle = '#000';
        ctx.fill();
        ctx.beginPath(); ctx.arc(pr.sx, pr.sy, r * 1.05, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(124,58,237,0.5)`;
        ctx.lineWidth = r * 0.15; ctx.stroke();
      });
      if (options.hoverable && state.tooltipEl) {
        const displayId = state.pinnedId || state.hoveredId;
        const pr = state.projectedNodes[displayId];
        if (displayId && pr) {
          if (displayId !== state.lastHoveredId) {
            const skill = state.skills.find(s => s.id === displayId);
            const col = PALETTE[skill.type] || PALETTE.basic;
            const typeClass = `skill-tooltip-type-${skill.type}`;
            const rm = skill.level ? RANK_META[skill.level] : null;
            const rankPill = rm
              ? `<span style="display:inline-block;padding:.12rem .42rem;border-radius:999px;font-size:.62rem;font-weight:700;background:${rm.bg};color:${rm.hex}">${skill.level}</span>`
              : '';
            const effectivePill = (skill.effectiveLevel && skill.effectiveLevel !== skill.level)
              ? `<span style="display:inline-block;padding:.12rem .42rem;border-radius:999px;font-size:.62rem;font-weight:700;background:rgba(251,191,36,.16);color:#fbbf24">effective ${skill.effectiveLevel}</span>`
              : '';
            const demeritNote = skill.demerits && skill.demerits.length
              ? `<div style="color:#fbbf24;font-size:.66rem;margin-top:.26rem">${skill.demerits.length} demerit${skill.demerits.length === 1 ? '' : 's'}</div>`
              : '';
            const namedId = state.namedMap[skill.id] || null;
            const namedLine = namedId
              ? `<div style="color:#ef4444;font-size:.67rem;font-weight:600;font-family:monospace;margin-bottom:.3rem;letter-spacing:.01em">${namedId}</div>`
              : '';
            state.tooltipEl.innerHTML =
              `<div class="skill-tooltip-name" style="color:rgba(${col.rgb},1)">${skill.name}</div>` +
              namedLine +
              `<div style="color:#64748b;font-size:.68rem;font-weight:500;margin-bottom:.3rem;font-family:monospace">${skill.id}</div>` +
              `<div class="skill-tooltip-row"><span class="skill-tooltip-badge ${typeClass}">${skill.type.toUpperCase()}</span>${rankPill}${effectivePill}</div>` +
              demeritNote +
              `<button class="graph-tooltip-add" title="Add to collection">+</button>`;
            state.lastHoveredId = displayId;
            const addBtn = state.tooltipEl.querySelector('.graph-tooltip-add');
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
            state.tooltipEl.style.top  = state.pinnedPos.top;
          } else {
            let tx = pr.sx + 18, ty = pr.sy - 34;
            tx = Math.min(tx, state.width - 250); ty = Math.max(ty, 8);
            state.tooltipEl.style.left = tx + 'px';
            state.tooltipEl.style.top  = ty + 'px';
          }
          state.tooltipEl.style.display = 'block';
          state.tooltipEl.classList.toggle('pinned', Boolean(state.pinnedId));
        } else if (!state.pinnedId) {
          state.tooltipEl.style.display = 'none';
          state.lastHoveredId = null;
        }
      }
      // ── Neighbor mini-cards when pinned ──
      if (options.hoverable && state.neighborCardsEl) {
        if (state.pinnedId && neighborSet.size > 1) {
          const neighbors = [...neighborSet].filter(id => id !== state.pinnedId);
          if (state._neighborIds !== neighbors.join(',')) {
            state._neighborIds = neighbors.join(',');
            state.neighborCardsEl.innerHTML = '';
            neighbors.forEach(nid => {
              const ns = state.skills.find(s => s.id === nid);
              if (!ns) return;
              const col = PALETTE[ns.type] || PALETTE.basic;
              const card = document.createElement('div');
              card.className = 'graph-neighbor-card';
              card.dataset.nid = nid;
              card.dataset.type = ns.type || 'basic';
              card.innerHTML = `<span style="color:rgba(${col.rgb},.9)">${ns.name}</span>`;
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
            state.neighborCardsEl.innerHTML = '';
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
    if (options.hoverable) {
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
      collectionPanel.className = 'graph-collection-panel';
      collectionPanel.style.display = 'none';
      collectionPanel.innerHTML =
        `<div class="graph-collection-header">` +
        `<span class="graph-collection-title">Collection</span>` +
        `<div class="graph-collection-actions">` +
        `<button class="graph-collection-copy-all" title="Copy all named install commands">Copy <span style="color:#ef4444">Named</span></button>` +
        `<button class="graph-collection-clear-all" title="Clear collection">Clear All</button>` +
        `</div></div>` +
        `<div class="graph-collection-list"></div>` +
        `<div class="graph-collection-note">You can only install <span style="color:#ef4444">named</span> skills. For unnamed ones, propose one first.</div>`;
      canvas.parentElement.appendChild(collectionPanel);
      state.collectionEl = collectionPanel;
      collectionPanel.addEventListener('mousedown', e => e.stopPropagation());

      let clearConfirmTimer = null;
      const clearBtn = collectionPanel.querySelector('.graph-collection-clear-all');
      clearBtn.addEventListener('click', () => {
        if (clearBtn.dataset.confirm === 'yes') {
          state.collection = [];
          renderCollection();
          clearBtn.dataset.confirm = '';
          clearBtn.textContent = 'Clear All';
          clearBtn.classList.remove('confirming');
          if (clearConfirmTimer) { clearTimeout(clearConfirmTimer); clearConfirmTimer = null; }
        } else {
          clearBtn.dataset.confirm = 'yes';
          clearBtn.textContent = 'Are you sure?';
          clearBtn.classList.add('confirming');
          clearConfirmTimer = setTimeout(() => {
            clearBtn.dataset.confirm = '';
            clearBtn.textContent = 'Clear All';
            clearBtn.classList.remove('confirming');
          }, 3000);
        }
      });

      const copyAllBtn = collectionPanel.querySelector('.graph-collection-copy-all');
      copyAllBtn.addEventListener('click', () => {
        const lines = state.collection
          .map(id => state.namedMap[id])
          .filter(Boolean)
          .map(nid => `gaia install ${nid}`);
        if (lines.length === 0) return;
        navigator.clipboard.writeText(lines.join('\n')).then(() => {
          copyAllBtn.innerHTML = '✓ Copied';
          copyAllBtn.classList.add('copied');
          setTimeout(() => { copyAllBtn.innerHTML = 'Copy <span style="color:#ef4444">Named</span>'; copyAllBtn.classList.remove('copied'); }, 1500);
        });
      });

      function renderCollection() {
        const list = collectionPanel.querySelector('.graph-collection-list');
        if (state.collection.length === 0) {
          collectionPanel.style.display = 'none';
          list.innerHTML = '';
          return;
        }
        collectionPanel.style.display = 'flex';
        let html = '';
        state.collection.forEach(id => {
          const skill = state.skills.find(s => s.id === id) || { id, name: id, type: 'basic' };
          const col = PALETTE[skill.type] || PALETTE.basic;
          const namedId = state.namedMap[id] || null;
          const cmd = namedId ? `gaia install ${namedId}` : `gaia propose /${id}`;
          const shareLink = namedId
            ? `<button class="graph-collection-share" data-nid="${namedId}" title="Open in Explorer">↗</button>`
            : '';
          html += `<div class="graph-collection-card" data-cid="${id}">` +
            `<div class="graph-collection-card-top">` +
            `<span class="graph-collection-card-name" style="color:rgba(${col.rgb},1)">${skill.name}</span>` +
            `<div class="graph-collection-card-btns">${shareLink}<button class="graph-collection-remove" data-cid="${id}" title="Remove">×</button></div>` +
            `</div>` +
            (namedId ? `<div class="graph-collection-card-named">${namedId}</div>` : '') +
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
            const url = window.location.origin + window.location.pathname + '#explorer/' + nid;
            window.open(url, '_blank');
          });
        });
      }

      function openSkillPanel(skillId) {
        const skill = state.skills.find(s => s.id === skillId) || { id: skillId, name: skillId, type: 'basic', prerequisites: [] };
        const col = PALETTE[skill.type] || PALETTE.basic;
        const namedId = state.namedMap[skill.id] || null;
        const titleText = (state.titleMap && state.titleMap[skill.id]) || null;
        const rm = skill.level ? RANK_META[skill.level] : null;
        const wasPaused = state.paused;
        state.paused = true;
        let c = `<div class="graph-skill-panel-header">`;
        c += `<div class="graph-skill-panel-name" style="color:rgba(${col.rgb},1)">${skill.name}</div>`;
        c += `<button class="graph-skill-panel-close" title="Close">×</button>`;
        c += `</div>`;
        c += `<div class="graph-skill-panel-body">`;
        if (namedId) c += `<div class="graph-skill-panel-named-id">${namedId}</div>`;
        if (namedId && titleText) c += `<div class="graph-skill-panel-title">"${titleText}"</div>`;
        c += `<div class="graph-skill-panel-type-row">`;
        c += `<span class="skill-tooltip-badge skill-tooltip-type-${skill.type}">${skill.type.toUpperCase()}</span>`;
        if (rm) c += `<span style="display:inline-block;padding:.12rem .42rem;border-radius:999px;font-size:.62rem;font-weight:700;background:${rm.bg};color:${rm.hex}">${skill.level}</span>`;
        c += `</div>`;
        c += `<div class="graph-skill-panel-terminal">`;
        if (namedId) {
          c += `<code class="graph-skill-panel-cmd" data-cmd="gaia install ${namedId}">$ gaia install ${namedId}</code>`;
          c += `<a class="graph-skill-panel-explorer-link" href="#explorer/${namedId}">Open in Explorer →</a>`;
        } else {
          c += `<code class="graph-skill-panel-cmd" data-cmd="gaia propose /${skill.id}">$ gaia propose /${skill.id}</code>`;
          c += `<div class="graph-skill-panel-hint">Claim this skill as your own named implementation</div>`;
        }
        c += `</div></div>`;
        skillPanel.innerHTML = c;
        skillPanel.style.display = 'flex';
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
      const searchInput = document.createElement('input');
      searchInput.type = 'text';
      searchInput.className = 'graph-search';
      searchInput.placeholder = 'Search skills…';
      searchInput.setAttribute('aria-label', 'Filter skill graph');
      searchInput.addEventListener('input', () => { state.searchText = searchInput.value.trim(); });
      searchInput.addEventListener('mousedown', e => e.stopPropagation());
      searchWrap.appendChild(searchInput);
      canvas.parentElement.appendChild(searchWrap);
      state.searchInputEl = searchInput;

      const legend = document.createElement('div');
      legend.className = 'graph-legend';
      legend.innerHTML =
        '<div class="graph-legend-section"><div class="graph-legend-heading">Type</div>' +
        '<div class="graph-legend-item" data-legend-type="basic"><span class="graph-legend-swatch" style="background:#38bdf8;width:7px;height:7px"></span>Basic</div>' +
        '<div class="graph-legend-item" data-legend-type="extra"><span class="graph-legend-swatch" style="background:#c084fc;width:10px;height:10px"></span>Extra</div>' +
        '<div class="graph-legend-item" data-legend-type="unique"><span class="graph-legend-swatch" style="background:#7c3aed;width:12px;height:12px"></span>Unique</div>' +
        '<div class="graph-legend-item" data-legend-type="ultimate"><span class="graph-legend-swatch" style="background:#f59e0b;width:14px;height:14px"></span>Ultimate</div>' +
        '</div><div class="graph-legend-section"><div class="graph-legend-heading">Rank</div>' +
        '<div class="graph-legend-ranks">' +
        '<span class="graph-legend-rank-pill" data-legend-rank="1★" style="background:rgba(56,189,248,.12);color:#38bdf8">1★</span>' +
        '<span class="graph-legend-rank-pill" data-legend-rank="2★" style="background:rgba(99,202,183,.12);color:#63cab7">2★</span>' +
        '<span class="graph-legend-rank-pill" data-legend-rank="3★" style="background:rgba(167,139,250,.12);color:#a78bfa">3★</span>' +
        '<span class="graph-legend-rank-pill" data-legend-rank="4★" style="background:rgba(232,121,249,.12);color:#e879f9">4★</span>' +
        '<span class="graph-legend-rank-pill" data-legend-rank="5★" style="background:rgba(251,191,36,.12);color:#fbbf24">5★</span>' +
        '<span class="graph-legend-rank-pill" data-legend-rank="6★" style="background:rgba(251,191,36,.20);color:#fbbf24">6★</span>' +
        '</div></div>';
      legend.addEventListener('mousedown', e => e.stopPropagation());
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
        pill.addEventListener('mouseenter', () => { state.legendHoverRank = pill.dataset.legendRank; });
        pill.addEventListener('mouseleave', () => { state.legendHoverRank = null; });
        pill.addEventListener('click', () => {
          const val = state.legendFilterRank === pill.dataset.legendRank ? null : pill.dataset.legendRank;
          state.legendFilterRank = val;
          legend.querySelectorAll('.graph-legend-rank-pill').forEach(el => el.classList.remove('active'));
          if (val) pill.classList.add('active');
        });
      });
      canvas.parentElement.appendChild(legend);
      state.legendEl = legend;

      const scatterStrip = document.createElement('div');
      scatterStrip.className = 'graph-scatter-strip';
      scatterStrip.setAttribute('aria-label', 'Scatter — drag up to spread, drag down to clump');
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
      scatterTitle.textContent = Math.round(state.scale / (options.scale || GRAPH_SCALE) * 100) + '%';
      scatterStrip.appendChild(scatterTop);
      scatterStrip.appendChild(scatterTrackWrap);
      scatterStrip.appendChild(scatterBot);
      scatterStrip.appendChild(scatterTitle);

      function redrawScatterRuler() {
        const logVal = Math.log(state.scale);
        drawRuler(scatterRulerCanvas, logVal, { vertical: true, pxPerUnit: 42, minorStep: 0.1, majorEvery: 5 });
        scatterTitle.textContent = Math.round(state.scale / (options.scale || GRAPH_SCALE) * 100) + '%';
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
        state.scale = Math.max(0.05, Math.min((options.scale || GRAPH_SCALE) * 10, state.scale * Math.exp(dy * 0.007)));
        state.positions = buildPositions(state.skills, state.scale);
        redrawScatterRuler();
      });
      scatterStrip.addEventListener('pointerup', e => {
        scatterDragging = false;
        scatterStrip.releasePointerCapture(e.pointerId);
      });
      canvas.parentElement.appendChild(scatterStrip);
      setTimeout(redrawScatterRuler, 50);

      const redPill = document.createElement('button');
      redPill.type = 'button';
      redPill.className = 'graph-redpill';
      redPill.textContent = 'Named Skills';
      redPill.title = 'Highlight Named skills (2★+) with contributor attribution and red glow';
      redPill.addEventListener('mousedown', e => e.stopPropagation());
      redPill.addEventListener('click', () => {
        state.redPillActive = !state.redPillActive;
        redPill.classList.toggle('active', state.redPillActive);
      });
      canvas.parentElement.appendChild(redPill);
      state.redPillEl = redPill;

      // ── Bottom bar: [pause][labels][titles][speed strip] ──
      const bottomBar = document.createElement('div');
      bottomBar.className = 'graph-bottom-bar';
      bottomBar.addEventListener('mousedown', e => e.stopPropagation());

      const pauseBtn = document.createElement('button');
      pauseBtn.type = 'button';
      pauseBtn.className = 'graph-pause-btn';
      pauseBtn.textContent = '⏸';
      pauseBtn.title = 'Pause / resume rotation';
      pauseBtn.addEventListener('click', () => {
        state.paused = !state.paused;
        pauseBtn.textContent = state.paused ? '▶' : '⏸';
        pauseBtn.classList.toggle('active', state.paused);
      });
      bottomBar.appendChild(pauseBtn);
      state.pauseBtnEl = pauseBtn;

      const labelsToggle = document.createElement('button');
      labelsToggle.type = 'button';
      labelsToggle.className = 'graph-bottom-btn';
      labelsToggle.textContent = 'Labels';
      labelsToggle.title = 'Toggle skill labels';
      labelsToggle.addEventListener('click', () => {
        if (state.labelMode === 'none') {
          state.labelMode = options.labelMode || 'ultimate';
          labelsToggle.classList.remove('off');
        } else {
          state.labelMode = 'none';
          labelsToggle.classList.add('off');
        }
      });
      bottomBar.appendChild(labelsToggle);
      state.labelsToggleEl = labelsToggle;

      const labelToggle = document.createElement('button');
      labelToggle.type = 'button';
      labelToggle.className = 'graph-bottom-btn';
      labelToggle.textContent = 'Titles';
      labelToggle.title = 'Show skill titles instead of /IDs';
      labelToggle.addEventListener('click', () => {
        state.showTitles = !state.showTitles;
        labelToggle.classList.toggle('active', state.showTitles);
      });
      bottomBar.appendChild(labelToggle);
      state.labelToggleEl = labelToggle;

      const nebulaToggle = document.createElement('button');
      nebulaToggle.type = 'button';
      nebulaToggle.className = 'graph-bottom-btn';
      nebulaToggle.textContent = 'Nebula';
      nebulaToggle.title = 'Toggle nebula cloud atmosphere';
      nebulaToggle.addEventListener('click', () => {
        state.nebula = !state.nebula;
        nebulaToggle.classList.toggle('active', state.nebula);
      });
      nebulaToggle.classList.add('active');
      bottomBar.appendChild(nebulaToggle);
      state.nebulaToggleEl = nebulaToggle;

      const randomBtn = document.createElement('button');
      randomBtn.type = 'button';
      randomBtn.className = 'graph-bottom-btn';
      randomBtn.textContent = 'Random';
      randomBtn.title = 'Zoom to a random skill';
      randomBtn.addEventListener('click', () => {
        if (!state.skills.length) return;
        const picked = state.skills[Math.floor(Math.random() * state.skills.length)];
        state.paused = true;
        if (state.pauseBtnEl) { state.pauseBtnEl.textContent = '▶'; state.pauseBtnEl.classList.add('active'); }
        state.zoom = 2.2;
        if (state.zoomCounterEl) state.zoomCounterEl.textContent = state.zoom.toFixed(1) + '×';
        state.hoveredId = picked.id;
        state.lastHoveredId = null;
        const p0 = state.positions[picked.id];
        if (p0) {
          const ry = state.t * 0.16 + state.orbitY;
          const rx = Math.sin(state.t * 0.055) * 0.20 + state.orbitX;
          const xfP = rotX(rotY(p0, ry), rx);
          const pr = project(xfP);
          state.panX += state.width / 2 - pr.sx;
          state.panY += state.height / 2 - pr.sy;
        }
      });
      bottomBar.appendChild(randomBtn);

      const resetBtn = document.createElement('button');
      resetBtn.type = 'button';
      resetBtn.className = 'graph-bottom-btn';
      resetBtn.textContent = 'Reset';
      resetBtn.title = 'Reset all settings to default';
      resetBtn.addEventListener('click', () => {
        resetFilters();
      });
      bottomBar.appendChild(resetBtn);

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

      function redrawSpeedRuler() {
        const logVal = Math.log(Math.max(0.001, state.rotSpeed));
        drawRuler(speedRulerCanvas, logVal, { vertical: false, pxPerUnit: 42, minorStep: 0.1, majorEvery: 5 });
        speedTitle.textContent = '×' + state.rotSpeed.toFixed(1);
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
      bottomBar.appendChild(speedStrip);
      setTimeout(redrawSpeedRuler, 50);
      canvas.parentElement.appendChild(bottomBar);
    }
    window.addEventListener('resize', resize);
    const pointerTarget = options.pointerTarget || canvas;
    pointerTarget.addEventListener('mousemove', event => {
      const rect = canvas.getBoundingClientRect();
      if (options.draggable && state.dragging) {
        if (state.dragMode === 'orbit') {
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
        if (options.hoverable) {
          const mx = event.clientX - rect.left;
          const my = event.clientY - rect.top;
          let closest = null, closestDist = 22;
          Object.entries(state.projectedNodes).forEach(([id, pr]) => {
            const d = Math.hypot(pr.sx - mx, pr.sy - my);
            if (d < closestDist) { closestDist = d; closest = id; }
          });
          state.hoveredId = closest;
          canvas.style.cursor = closest ? 'pointer' : (options.draggable ? 'grab' : 'default');
        }
      }
    });
    if (options.draggable) {
      canvas.style.cursor = 'grab';
      canvas.addEventListener('mouseleave', () => { if (!state.dragging && !state.pinnedId) state.hoveredId = null; });
      canvas.addEventListener('contextmenu', e => e.preventDefault());
      canvas.addEventListener('mousedown', e => {
        if (e.button === 2) return;
        e.preventDefault();
        state.dragging = true;
        state.dragMode = (e.button === 1 || e.ctrlKey) ? 'orbit' : 'pan';
        state.dragMoved = false;
        state.dragStartX = e.clientX;
        state.dragStartY = e.clientY;
        state.dragLastX = e.clientX;
        state.dragLastY = e.clientY;
        canvas.style.cursor = state.dragMode === 'orbit' ? 'grabbing' : 'move';
      });
      window.addEventListener('mouseup', e => {
        if (!state.dragging) return;
        const didClick = !state.dragMoved;
        state.dragging = false;
        state.dragMoved = false;
        canvas.style.cursor = state.hoveredId ? 'pointer' : 'grab';
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
    }
    if (options.zoomable) {
      canvas.addEventListener('wheel', e => {
        e.preventDefault();
        state.zoom = Math.max(0.3, Math.min(3.0, state.zoom * (1 - e.deltaY * 0.001)));
        if (state.zoomCounterEl) state.zoomCounterEl.textContent = state.zoom.toFixed(1) + '×';
      }, { passive: false });
    }
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
      state.positions = buildPositions(state.skills, state.scale);
      state.nebula = true;
      state.hoverSlowdown = 0;
      state.pinnedId = null; state.pinnedPos = null;
      if (state.skillPanelEl) state.skillPanelEl.style.display = 'none';
      if (state.pauseBtnEl) { state.pauseBtnEl.textContent = '⏸'; state.pauseBtnEl.classList.remove('active'); }
      if (state.labelsToggleEl) { state.labelMode = options.labelMode || 'ultimate'; state.labelsToggleEl.classList.remove('off'); }
      if (state.redPillEl) state.redPillEl.classList.remove('active');
      if (state.legendEl) {
        state.legendEl.querySelectorAll('.active').forEach(el => el.classList.remove('active'));
      }
      if (state.searchInputEl) state.searchInputEl.value = '';
      if (state.labelToggleEl) state.labelToggleEl.classList.remove('active');
      if (state.zoomCounterEl) state.zoomCounterEl.textContent = '1.0×';
      if (state.nebulaToggleEl) state.nebulaToggleEl.classList.add('active');
      if (state.scatterRulerCanvas) {
        drawRuler(state.scatterRulerCanvas, Math.log(state.scale), { vertical: true, pxPerUnit: 42, minorStep: 0.1, majorEvery: 5 });
      }
      if (state.speedRulerCanvas) {
        drawRuler(state.speedRulerCanvas, 0, { vertical: false, pxPerUnit: 42, minorStep: 0.1, majorEvery: 5 });
      }
    }
    if (state.running) draw();
    function setNamedMap(map) { state.namedMap = map || {}; }
    function setTitleMap(map) { state.titleMap = map || {}; }
    return { setSkills, setNamedMap, setTitleMap, resize, start, stop, resetFilters };
  }

  const hero = document.getElementById('hero');
  const trigger = document.querySelector('[data-graph-trigger]');
  const dialog = document.getElementById('skillGraphDialog');
  const closeBtn = document.querySelector('[data-graph-close]');
  const mobileHint = document.getElementById('graphMobileHint');
  const mobileHintDismiss = document.getElementById('graphMobileHintDismiss');
  if (mobileHintDismiss && mobileHint) {
    mobileHintDismiss.addEventListener('click', () => { mobileHint.style.display = 'none'; });
  }
  const isMobile = window.matchMedia('(max-width:700px)').matches;
  const heroGraph = isMobile ? null : createSkillGraph(document.getElementById('canvas3d'), { labelMode:'none', scale:GRAPH_SCALE, stars:280, pointerTarget:hero });
  const modalGraph = createSkillGraph(document.getElementById('graphDialogCanvas'), {
    labelMode:'all', scale:1.8, stars:320, statusEl:document.querySelector('[data-graph-status]'), autostart:false, zoomable:true, draggable:true, hoverable:true,
  });

  function peek(on) { hero.classList.toggle('hero-graph-peek', Boolean(on)); }

  const hudBtn = document.getElementById('hudToggleBtn');
  if (hudBtn) {
    let hudOn = false;
    hudBtn.addEventListener('click', () => {
      hudOn = !hudOn;
      hero.classList.toggle('hero-hud-mode', hudOn);
      hudBtn.setAttribute('aria-pressed', String(hudOn));
      hudBtn.textContent = hudOn ? '⇄ Exit HUD' : '⇄ View as HUD';
    });
  }

  trigger.addEventListener('mouseenter', () => peek(true));
  trigger.addEventListener('mouseleave', () => peek(false));
  trigger.addEventListener('focus', () => peek(true));
  trigger.addEventListener('blur', () => peek(false));
  trigger.addEventListener('click', () => {
    hero.classList.add('transitioning-to-graph');
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
    modalGraph.resize();
    modalGraph.start();
    peek(false);
  });
  function closeDialog() {
    if (dialog.close) dialog.close();
    else dialog.removeAttribute('open');
  }
  closeBtn.addEventListener('click', closeDialog);
  dialog.addEventListener('click', event => {
    if (event.target === dialog) closeDialog();
  });
  dialog.addEventListener('close', () => {
    hero.classList.remove('transitioning-to-graph');
    modalGraph.resetFilters();
    modalGraph.stop();
  });

  fetch(GRAPH_JSON_URL)
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then(graph => {
      _initMetaGraph(graph.meta);
      return normalizeSkills(graph);
    })
    .then(skills => { if (heroGraph) heroGraph.setSkills(skills); modalGraph.setSkills(skills); })
    .catch(error => {
      console.warn('Using embedded fallback skill graph:', error);
      const status = document.querySelector('[data-graph-status]');
      if (status) status.textContent = 'Using embedded preview graph. Run the page from docs/ to load the full graph.';
    });

  fetch('graph/named/index.json')
    .then(r => r.ok ? r.json() : Promise.reject())
    .then(indexData => {
      const map = {};
      const titleMap = {};
      const buckets = indexData.buckets || {};
      Object.entries(buckets).forEach(([skillId, arr]) => {
        if (Array.isArray(arr) && arr.length) {
          const origin = arr.find(e => e.origin) || arr[0];
          if (origin && origin.id) map[skillId] = origin.id;
          if (origin && origin.title) titleMap[skillId] = origin.title;
        }
      });
      if (heroGraph) heroGraph.setNamedMap(map);
      modalGraph.setNamedMap(map);
      if (heroGraph) heroGraph.setTitleMap(titleMap);
      modalGraph.setTitleMap(titleMap);
    })
    .catch(() => {});
})();

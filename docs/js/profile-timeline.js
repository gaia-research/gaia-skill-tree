(function () {
  // ──────────────────────────────────────────────────────────────────
  // profile-timeline.js — Dual-panel Progression Timeline
  //
  // Left panel:  SVG step-line chart (rank over time, per skill)
  // Right panel: Infinite-scrollable chronological event list
  //
  // Data contract: window.PROFILE_TIMELINE = { skills[], events[] }
  // Render target: <div id="profile-timeline">
  // ──────────────────────────────────────────────────────────────────

  // ── CSS (self-injected once) ──────────────────────────────────────
  var _cssInjected = false;
  function _injectStyles() {
    if (_cssInjected || typeof document === 'undefined') return;
    _cssInjected = true;
    var el = document.createElement('style');
    el.id = 'ptl2-styles';
    el.textContent = [
      /* ── Wrapper ── */
      '.ptl2 {',
      '  display: grid;',
      '  grid-template-columns: 1fr 340px;',
      '  gap: 0;',
      '  border: 1px solid var(--border,#1e293b);',
      '  border-radius: 10px;',
      '  overflow: hidden;',
      '  background: rgba(15,23,42,0.6);',
      '  min-height: 360px;',
      '}',

      /* ── Left: chart panel ── */
      '.ptl2__chart-panel {',
      '  position: relative;',
      '  padding: 20px 16px 16px 16px;',
      '  border-right: 1px solid var(--border,#1e293b);',
      '  min-width: 0;',
      '}',
      '.ptl2__chart-title {',
      '  font-family: var(--font-mono,monospace);',
      '  font-size: 0.6rem;',
      '  letter-spacing: 0.12em;',
      '  text-transform: uppercase;',
      '  color: rgba(226,232,240,0.3);',
      '  margin-bottom: 12px;',
      '}',
      '.ptl2__chart-svg {',
      '  display: block;',
      '  width: 100%;',
      '  height: auto;',
      '  overflow: visible;',
      '}',

      /* ── Legend ── */
      '.ptl2__legend {',
      '  display: flex;',
      '  flex-wrap: wrap;',
      '  gap: 4px 12px;',
      '  margin-top: 10px;',
      '}',
      '.ptl2__legend-item {',
      '  display: inline-flex;',
      '  align-items: center;',
      '  gap: 5px;',
      '  font-family: var(--font-body,sans-serif);',
      '  font-size: 0.68rem;',
      '  color: rgba(226,232,240,0.5);',
      '  cursor: pointer;',
      '  border-radius: 3px;',
      '  padding: 1px 5px 1px 2px;',
      '  transition: color 0.15s, background 0.15s;',
      '}',
      '.ptl2__legend-item:hover { color: var(--text,#e2e8f0); background: rgba(255,255,255,0.04); }',
      '.ptl2__legend-item.is-muted { opacity: 0.3; }',
      '.ptl2__legend-dot {',
      '  width: 8px; height: 8px;',
      '  border-radius: 50%;',
      '  flex-shrink: 0;',
      '}',

      /* ── Right: scrollable event list ── */
      '.ptl2__feed-panel {',
      '  display: flex;',
      '  flex-direction: column;',
      '  min-width: 0;',
      '}',
      '.ptl2__feed-header {',
      '  padding: 12px 16px 10px;',
      '  border-bottom: 1px solid var(--border,#1e293b);',
      '  font-family: var(--font-mono,monospace);',
      '  font-size: 0.6rem;',
      '  letter-spacing: 0.12em;',
      '  text-transform: uppercase;',
      '  color: rgba(226,232,240,0.3);',
      '  flex-shrink: 0;',
      '}',
      '.ptl2__feed-scroll {',
      '  flex: 1;',
      '  overflow-y: auto;',
      '  overscroll-behavior: contain;',
      '  scrollbar-width: thin;',
      '  scrollbar-color: rgba(100,116,139,0.3) transparent;',
      '  max-height: 440px;',
      '}',
      '.ptl2__feed-scroll::-webkit-scrollbar { width: 4px; }',
      '.ptl2__feed-scroll::-webkit-scrollbar-thumb { background: rgba(100,116,139,0.3); border-radius: 2px; }',

      /* Spine inside feed */
      '.ptl2__feed-inner { position: relative; padding: 8px 0 16px 0; }',
      '.ptl2__feed-spine {',
      '  position: absolute;',
      '  left: 22px;',
      '  top: 0; bottom: 0;',
      '  width: 1px;',
      '  background: var(--border,#1e293b);',
      '  pointer-events: none;',
      '}',

      /* Month group */
      '.ptl2__month { position: relative; }',
      '.ptl2__month-label {',
      '  display: block;',
      '  margin: 10px 0 6px 42px;',
      '  font-family: var(--font-mono,monospace);',
      '  font-size: 0.58rem;',
      '  letter-spacing: 0.1em;',
      '  text-transform: uppercase;',
      '  color: rgba(226,232,240,0.22);',
      '}',
      '.ptl2__month:first-child .ptl2__month-label { margin-top: 4px; }',

      /* Event row */
      '.ptl2__event {',
      '  display: grid;',
      '  grid-template-columns: 44px 1fr;',
      '  align-items: start;',
      '  margin-bottom: 1px;',
      '}',
      '.ptl2__marker-col {',
      '  display: flex;',
      '  align-items: flex-start;',
      '  justify-content: center;',
      '  padding-top: 11px;',
      '}',
      '.ptl2__dot {',
      '  width: 7px; height: 7px;',
      '  border-radius: 50%;',
      '  border: 1.5px solid var(--border,#1e293b);',
      '  background: var(--bg,#030712);',
      '  flex-shrink: 0;',
      '}',
      '.ptl2__dot--basic    { border-color: var(--tier-basic,#38bdf8);    background: rgba(56,189,248,.15); }',
      '.ptl2__dot--extra    { border-color: var(--tier-extra,#c084fc);    background: rgba(192,132,252,.15); }',
      '.ptl2__dot--unique   { border-color: var(--tier-unique,#7c3aed);   background: #000; }',
      '.ptl2__dot--ultimate { border-color: var(--tier-ultimate,#f59e0b); background: rgba(245,158,11,.15); }',
      '.ptl2__dot--rank { width: 9px; height: 9px; border-width: 2px; }',
      '.ptl2__event--rank-up .ptl2__dot--basic    { box-shadow: 0 0 6px rgba(56,189,248,.5); }',
      '.ptl2__event--rank-up .ptl2__dot--extra    { box-shadow: 0 0 6px rgba(192,132,252,.5); }',
      '.ptl2__event--rank-up .ptl2__dot--unique   { box-shadow: 0 0 8px rgba(124,58,237,.7); }',
      '.ptl2__event--rank-up .ptl2__dot--ultimate { box-shadow: 0 0 8px rgba(245,158,11,.6); }',

      /* Card */
      '.ptl2__card {',
      '  padding: 7px 14px 7px 0;',
      '  border-radius: 4px;',
      '  transition: background 0.12s;',
      '}',
      '.ptl2__card:hover { background: rgba(255,255,255,0.025); }',
      '.ptl2__card-head {',
      '  display: flex;',
      '  align-items: baseline;',
      '  gap: 5px;',
      '  flex-wrap: wrap;',
      '}',
      '.ptl2__skill-name {',
      '  font-size: 0.8rem;',
      '  font-weight: 600;',
      '  color: var(--text,#e2e8f0);',
      '  line-height: 1.35;',
      '  flex-shrink: 1;',
      '  min-width: 0;',
      '}',
      '.ptl2__chip {',
      '  font-family: var(--font-mono,monospace);',
      '  font-size: 0.54rem;',
      '  letter-spacing: 0.08em;',
      '  text-transform: uppercase;',
      '  font-weight: 700;',
      '  padding: 1px 5px;',
      '  border-radius: 2px;',
      '  flex-shrink: 0;',
      '  line-height: 1.7;',
      '}',
      '.ptl2__chip--register { color: var(--muted,#64748b); background: rgba(100,116,139,.1); border: 1px solid rgba(100,116,139,.2); }',
      '.ptl2__chip--propose  { color: var(--tier-basic,#38bdf8); background: rgba(56,189,248,.07); border: 1px solid rgba(56,189,248,.2); }',
      '.ptl2__chip--add      { color: var(--tier-basic,#38bdf8); background: rgba(56,189,248,.07); border: 1px solid rgba(56,189,248,.2); }',
      '.ptl2__chip--rank_up  { color: #86efac; background: rgba(134,239,172,.07); border: 1px solid rgba(134,239,172,.2); }',
      '.ptl2__chip--ascend   { color: #86efac; background: rgba(134,239,172,.07); border: 1px solid rgba(134,239,172,.2); }',
      '.ptl2__chip--promote  { color: #86efac; background: rgba(134,239,172,.07); border: 1px solid rgba(134,239,172,.2); }',
      '.ptl2__chip--demote   { color: #ef4444; background: rgba(239,68,68,.07);   border: 1px solid rgba(239,68,68,.2); }',
      '.ptl2__chip--fuse     { color: var(--tier-ultimate,#f59e0b); background: rgba(245,158,11,.07); border: 1px solid rgba(245,158,11,.2); }',
      '.ptl2__chip--default  { color: var(--muted,#64748b); background: rgba(100,116,139,.07); border: 1px solid rgba(100,116,139,.15); }',

      /* Rank delta */
      '.ptl2__rank-delta {',
      '  display: inline-flex; align-items: center; gap: 3px;',
      '  font-family: var(--font-mono,monospace);',
      '  font-size: 0.68rem; color: rgba(226,232,240,0.45);',
      '  flex-shrink: 0;',
      '}',
      '.ptl2__rank-from { text-decoration: line-through; opacity: 0.5; }',
      '.ptl2__rank-to   { color: #86efac; font-weight: 700; }',
      '.ptl2__rank-arr  { opacity: 0.35; }',
      '.ptl2__date {',
      '  font-family: var(--font-mono,monospace);',
      '  font-size: 0.58rem;',
      '  color: rgba(226,232,240,0.18);',
      '  margin-top: 1px;',
      '}',

      /* Empty */
      '.ptl2__empty {',
      '  display: flex; align-items: center; justify-content: center;',
      '  min-height: 200px;',
      '  font-family: var(--font-mono,monospace);',
      '  font-size: 0.75rem;',
      '  color: rgba(226,232,240,0.2);',
      '  letter-spacing: 0.08em;',
      '}',

      /* Entrance */
      '@keyframes ptl2-in {',
      '  from { opacity: 0; transform: translateX(-4px); }',
      '  to   { opacity: 1; transform: translateX(0); }',
      '}',
      '.ptl2__event { opacity: 0; animation: ptl2-in 0.22s ease-out forwards; }',
      '@media (prefers-reduced-motion: reduce) { .ptl2__event { animation: none !important; opacity: 1 !important; } }',

      /* Responsive: stack on narrow */
      '@media (max-width: 700px) {',
      '  .ptl2 { grid-template-columns: 1fr; }',
      '  .ptl2__chart-panel { border-right: none; border-bottom: 1px solid var(--border,#1e293b); }',
      '  .ptl2__feed-scroll { max-height: 320px; }',
      '}',
    ].join('\n');
    document.head.appendChild(el);
  }

  // ── Utility ───────────────────────────────────────────────────────
  var NS = 'http://www.w3.org/2000/svg';
  function svgEl(tag, attrs, textContent) {
    var el = document.createElementNS(NS, tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { el.setAttribute(k, attrs[k]); });
    if (textContent != null) el.textContent = textContent;
    return el;
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function parseRank(level) {
    if (!level) return 0;
    var s = String(level);
    var m = s.match(/^(\d)/);
    if (m) return Math.min(6, parseInt(m[1], 10));
    return Math.min(6, (s.match(/★/g) || []).length);
  }

  var TIER_COLOR = {
    basic:    'var(--tier-basic,#38bdf8)',
    extra:    'var(--tier-extra,#c084fc)',
    unique:   'var(--tier-unique,#7c3aed)',
    ultimate: 'var(--tier-ultimate,#f59e0b)',
  };
  var TIER_HEX = (function () {
    var s = typeof getComputedStyle !== 'undefined' ? getComputedStyle(document.documentElement) : null;
    function cv(prop, fb) { return s ? (s.getPropertyValue(prop).trim() || fb) : fb; }
    return {
      basic:    cv('--tier-basic',    '#38bdf8'),
      extra:    cv('--tier-extra',    '#c084fc'),
      unique:   cv('--tier-unique',   '#7c3aed'),
      ultimate: cv('--tier-ultimate', '#f59e0b'),
    };
  }());

  var ACTION_CHIP = {
    register: 'register', propose: 'propose', add: 'add',
    rank_up: 'rank_up', rank_down: 'demote', rank_retain: 'default',
    ascend: 'ascend', promote: 'promote', demote: 'demote', fuse: 'fuse'
  };
  var ACTION_LABEL = {
    register: 'Registered', propose: 'Proposed', add: 'Added',
    rank_up: 'Ranked Up', rank_down: 'Ranked Down', rank_retain: 'Retained Rank',
    ascend: 'Ascended', promote: 'Promoted', demote: 'Demoted', fuse: 'Fused'
  };
  function isRankAction(a) {
    return a === 'rank_up' || a === 'rank_down' || a === 'rank_retain' || a === 'ascend' || a === 'fuse' || a === 'promote' || a === 'demote';
  }

  function fmtMonth(d) { return d.toLocaleString('en', { month: 'short', year: 'numeric', timeZone: 'UTC' }); }
  function fmtDay(d)   { return d.toLocaleString('en', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }); }
  function monthKey(d) { return d.getUTCFullYear() + '-' + String(d.getUTCMonth() + 1).padStart(2, '0'); }

  // ── Build events ──────────────────────────────────────────────────
  function buildEvents(data) {
    var skillMap = {};
    (data.skills || []).forEach(function (s) { skillMap[s.id] = s; });

    var events = [];
    var seenKeys = {};

    // Level history entries with chronological diff calculation
    (data.skills || []).forEach(function (skill) {
      var sortedHistory = (skill.levelHistory || []).slice().sort(function (a, b) {
        return new Date(a.achievedAt) - new Date(b.achievedAt);
      });

      sortedHistory.forEach(function (h, idx) {
        var ts = new Date(h.achievedAt);
        if (isNaN(ts)) return;

        var currentRank = parseRank(h.level);
        var prevRank = 0;
        if (idx > 0) {
          prevRank = parseRank(sortedHistory[idx - 1].level);
        }

        var diff = currentRank - prevRank;
        var action = 'rank_up';
        if (idx > 0) {
          if (diff < 0) {
            action = 'rank_down';
          } else if (diff === 0) {
            action = 'rank_retain';
          }
        }

        var k = ts.toISOString() + '|' + action + '|' + skill.id;
        if (seenKeys[k]) return;
        seenKeys[k] = true;

        events.push({
          ts: ts, skillId: skill.id, skillName: skill.name || skill.id,
          type: skill.type || 'basic', action: action,
          newValue: h.level || null, previousValue: idx > 0 ? sortedHistory[idx - 1].level : null,
          diff: diff, details: null
        });
      });
    });

    // Explicit events mapping
    (data.events || []).forEach(function (ev) {
      var ts = new Date(ev.timestamp);
      if (isNaN(ts)) return;
      var skill = skillMap[ev.skillId] || {};

      var diff = 0;
      var action = ev.action || 'register';
      if (ev.newValue && ev.previousValue) {
        var currentRank = parseRank(ev.newValue);
        var prevRank = parseRank(ev.previousValue);
        diff = currentRank - prevRank;
        if (isRankAction(action) || action === 'rank_up' || action === 'rank_down' || action === 'rank_retain') {
          if (diff < 0) {
            action = 'rank_down';
          } else if (diff === 0) {
            action = 'rank_retain';
          } else {
            action = 'rank_up';
          }
        }
      }

      var k = ts.toISOString() + '|' + action + '|' + (ev.skillId || '');
      if (seenKeys[k]) return;
      seenKeys[k] = true;

      events.push({
        ts: ts, skillId: ev.skillId, skillName: skill.name || ev.skillId,
        type: skill.type || 'basic', action: action,
        newValue: ev.newValue || null, previousValue: ev.previousValue || null,
        diff: diff, details: ev.details || null
      });
    });

    events.sort(function (a, b) { return b.ts - a.ts; });
    return events;
  }

  // ── META-SHIFT detection ──────────────────────────────────────────
  var GAP_DAYS = 7;

  function detectMetaShifts(events) {
    var sorted = events.slice().sort(function (a, b) { return a.ts - b.ts; });
    var shifts = [];
    for (var i = 1; i < sorted.length; i++) {
      var gap = (sorted[i].ts - sorted[i - 1].ts) / 86400000;
      if (gap >= GAP_DAYS) {
        shifts.push((sorted[i].ts.getTime() + sorted[i - 1].ts.getTime()) / 2);
      }
    }
    return shifts;
  }

  // ── SVG Chart ─────────────────────────────────────────────────────
  var M = { top: 28, right: 20, bottom: 36, left: 44 };
  var VW = 560, VH = 280;
  var IW = VW - M.left - M.right;
  var IH = VH - M.top - M.bottom;

  function buildChart(data, events, filterOptions) {
    filterOptions = filterOptions || {};
    var activeSkills = filterOptions.activeSkills;

    var skills = (data.skills || []).filter(function (s) {
      if (activeSkills && !activeSkills.has(s.id)) return false;
      return s.levelHistory && s.levelHistory.length > 0;
    });
    if (skills.length === 0) return null;

    var allTs = [];
    skills.forEach(function (s) {
      (s.levelHistory || []).forEach(function (h) { allTs.push(new Date(h.achievedAt).getTime()); });
    });
    (data.events || []).forEach(function (e) { allTs.push(new Date(e.timestamp).getTime()); });

    var tMin = Math.min.apply(null, allTs);
    var tMax = Date.now();

    if (filterOptions.minDate) {
      tMin = new Date(filterOptions.minDate).getTime();
    } else {
      tMin -= 3 * 86400000;
    }

    if (filterOptions.maxDate) {
      tMax = new Date(filterOptions.maxDate).getTime();
    } else {
      tMax += 5 * 86400000;
    }

    if (tMin >= tMax) {
      tMax = tMin + 24 * 3600 * 1000;
    }
    var tSpan = tMax - tMin || 1;

    function xScale(ms) { return (ms - tMin) / tSpan * IW; }
    function yScale(rank) { return IH - (rank / 6) * IH; }

    var shifts = detectMetaShifts(events).filter(function (ms) {
      return ms >= tMin && ms <= tMax;
    });

    var svg = svgEl('svg', {
      viewBox: '0 0 ' + VW + ' ' + VH,
      'aria-hidden': 'true',
      role: 'presentation',
      class: 'ptl2__chart-svg',
    });

    var defs = svgEl('defs');
    var filt = svgEl('filter', { id: 'ptl2-glow', x: '-50%', y: '-50%', width: '200%', height: '200%' });
    filt.appendChild(svgEl('feGaussianBlur', { in: 'SourceGraphic', stdDeviation: '2.5', result: 'blur' }));
    var fm = svgEl('feMerge');
    fm.appendChild(svgEl('feMergeNode', { in: 'blur' }));
    fm.appendChild(svgEl('feMergeNode', { in: 'SourceGraphic' }));
    filt.appendChild(fm);
    defs.appendChild(filt);
    svg.appendChild(defs);

    var g = svgEl('g', { transform: 'translate(' + M.left + ',' + M.top + ')' });
    svg.appendChild(g);

    var mutedC = 'rgba(100,116,139,0.35)';
    var mutedLabel = 'rgba(100,116,139,0.6)';

    for (var r = 0; r <= 6; r++) {
      var gy = yScale(r);
      if (r > 0) {
        g.appendChild(svgEl('line', {
          x1: '0', y1: String(gy), x2: String(IW), y2: String(gy),
          stroke: mutedC, 'stroke-width': '0.5', 'stroke-dasharray': '3 5',
        }));
      }
      g.appendChild(svgEl('text', {
        x: '-8', y: String(gy + 4),
        'text-anchor': 'end', 'font-size': '10', fill: mutedLabel,
        'font-family': 'var(--font-mono,monospace)',
      }, r + '★'));
    }

    g.appendChild(svgEl('line', {
      x1: '0', y1: String(IH), x2: String(IW), y2: String(IH),
      stroke: mutedC, 'stroke-width': '0.75',
    }));

    var tickMs = tMin;
    var d0 = new Date(tMin);
    tickMs = new Date(Date.UTC(d0.getUTCFullYear(), d0.getUTCMonth() + 1, 1)).getTime();
    var fmt = new Intl.DateTimeFormat('en', { month: 'short', year: '2-digit', timeZone: 'UTC' });

    var monthsStep = 1;
    var daysDiff = tSpan / 86400000;
    if (daysDiff > 365 * 2) {
      monthsStep = 6;
    } else if (daysDiff > 365) {
      monthsStep = 3;
    } else if (daysDiff > 180) {
      monthsStep = 2;
    }

    while (tickMs <= tMax) {
      var tx = xScale(tickMs);
      if (tx >= 0 && tx <= IW) {
        g.appendChild(svgEl('line', {
          x1: String(tx), y1: String(IH), x2: String(tx), y2: String(IH + 4),
          stroke: mutedC, 'stroke-width': '1',
        }));
        g.appendChild(svgEl('text', {
          x: String(tx), y: String(IH + 15),
          'text-anchor': 'middle', 'font-size': '9', fill: mutedLabel,
          'font-family': 'var(--font-mono,monospace)',
        }, fmt.format(new Date(tickMs))));
      }
      var nd = new Date(tickMs);
      tickMs = new Date(Date.UTC(nd.getUTCFullYear(), nd.getUTCMonth() + monthsStep, 1)).getTime();
    }

    shifts.forEach(function (shiftMs) {
      var sx = xScale(shiftMs);
      if (sx >= 0 && sx <= IW) {
        var shiftLine = svgEl('line', {
          x1: String(sx), y1: '-4', x2: String(sx), y2: String(IH + 4),
          stroke: 'rgba(245,158,11,0.25)',
          'stroke-width': '1',
          'stroke-dasharray': '4 4',
        });
        g.appendChild(shiftLine);
        g.appendChild(svgEl('text', {
          x: String(sx + 3), y: '-8',
          'font-size': '8', fill: 'rgba(245,158,11,0.45)',
          'font-family': 'var(--font-mono,monospace)',
          'letter-spacing': '0.06em',
        }, 'META SHIFT'));
      }
    });

    var skillGroups = {};

    skills.forEach(function (skill) {
      var sorted = (skill.levelHistory || []).slice().sort(function (a, b) {
        return new Date(a.achievedAt) - new Date(b.achievedAt);
      });
      if (sorted.length === 0) return;

      var color = TIER_HEX[skill.type] || '#64748b';
      var grpId = 'ptl2-sg-' + skill.id.replace(/[^a-z0-9]/gi, '-');

      var grp = svgEl('g', { 'data-skill-id': skill.id, id: grpId, class: 'ptl2__chart-curve-group' });
      g.appendChild(grp);
      skillGroups[skill.id] = grp;

      var pts = [];
      var baseRank = 0;

      for (var j = 0; j < sorted.length; j++) {
        var ms = new Date(sorted[j].achievedAt).getTime();
        if (ms < tMin) {
          baseRank = parseRank(sorted[j].level);
        }
      }

      pts.push({ x: 0, y: yScale(baseRank) });

      sorted.forEach(function (h) {
        var ms = new Date(h.achievedAt).getTime();
        var rank = parseRank(h.level);

        if (ms >= tMin && ms <= tMax) {
          var cx = xScale(ms);
          if (pts.length > 0) {
            pts.push({ x: cx, y: pts[pts.length - 1].y });
          }
          pts.push({ x: cx, y: yScale(rank) });
        }
      });

      if (pts.length > 0) {
        pts.push({ x: IW, y: pts[pts.length - 1].y });
      }

      if (pts.length > 1) {
        var ptsStr = pts.map(function (p) { return p.x.toFixed(2) + ',' + p.y.toFixed(2); }).join(' ');
        grp.appendChild(svgEl('polyline', {
          points: ptsStr,
          fill: 'none',
          stroke: color,
          'stroke-width': '2.0',
          'stroke-linejoin': 'round',
          'stroke-linecap': 'round',
          opacity: '0.8',
          class: 'ptl2__chart-line'
        }));
      }

      sorted.forEach(function (h) {
        var ms = new Date(h.achievedAt).getTime();
        var rank = parseRank(h.level);
        if (ms >= tMin && ms <= tMax) {
          var cx = xScale(ms);
          var cy = yScale(rank);
          var dot = svgEl('circle', {
            cx: String(cx.toFixed(2)), cy: String(cy.toFixed(2)),
            r: rank >= 5 ? '5.5' : '4.0',
            fill: color,
            stroke: 'var(--bg,#030712)',
            'stroke-width': '1.5',
            'data-rank': rank + '★',
            'data-date': fmtDay(new Date(ms)),
            class: 'ptl2__chart-dot'
          });
          if (rank >= 5) dot.setAttribute('filter', 'url(#ptl2-glow)');
          grp.appendChild(dot);
        }
      });
    });

    return { svg: svg, skillGroups: skillGroups };
  }

  // ── Feed (scrollable event list) ─────────────────────────────────
  function renderFeed(events) {
    var groups = [];
    var gmap = {};
    events.forEach(function (ev) {
      var k = monthKey(ev.ts);
      if (!gmap[k]) { gmap[k] = { key: k, label: fmtMonth(ev.ts), events: [] }; groups.push(gmap[k]); }
      gmap[k].events.push(ev);
    });

    var inner = document.createElement('div');
    inner.className = 'ptl2__feed-inner';

    var spine = document.createElement('div');
    spine.className = 'ptl2__feed-spine';
    spine.setAttribute('aria-hidden', 'true');
    inner.appendChild(spine);

    var globalIdx = 0;
    groups.forEach(function (grp) {
      var monthEl = document.createElement('div');
      monthEl.className = 'ptl2__month';
      monthEl.setAttribute('role', 'group');
      monthEl.setAttribute('aria-label', grp.label);

      var labelEl = document.createElement('span');
      labelEl.className = 'ptl2__month-label';
      labelEl.setAttribute('aria-hidden', 'true');
      labelEl.textContent = grp.label;
      monthEl.appendChild(labelEl);

      grp.events.forEach(function (ev) {
        var action = ev.action || 'register';
        var chipCls = 'ptl2__chip ptl2__chip--' + (ACTION_CHIP[action] || 'default');
        var chipLabel = ACTION_LABEL[action] || action.replace(/_/g, ' ');
        var isRank = isRankAction(action);
        var dotCls = 'ptl2__dot ptl2__dot--' + (ev.type || 'basic') + (isRank ? ' ptl2__dot--rank' : '');
        
        var rowCls = 'ptl2__event';
        if (isRank) {
          if (action === 'rank_down' || action === 'demote' || ev.diff < 0) {
            rowCls += ' ptl2__event--rank-down';
          } else if (action === 'rank_retain' || ev.diff === 0) {
            rowCls += ' ptl2__event--rank-retain';
          } else {
            rowCls += ' ptl2__event--rank-up';
          }
        }

        var delay = Math.min(globalIdx * 20, 400);

        var row = document.createElement('div');
        row.className = rowCls;
        row.setAttribute('role', 'listitem');
        row.setAttribute('data-skill-id', ev.skillId || '');
        row.style.animationDelay = delay + 'ms';

        var mCol = document.createElement('div');
        mCol.className = 'ptl2__marker-col';
        mCol.setAttribute('aria-hidden', 'true');
        var dot = document.createElement('span');
        dot.className = dotCls;
        mCol.appendChild(dot);
        row.appendChild(mCol);

        var card = document.createElement('div');
        card.className = 'ptl2__card';

        var head = document.createElement('div');
        head.className = 'ptl2__card-head';

        var nameEl = document.createElement('span');
        nameEl.className = 'ptl2__skill-name';
        nameEl.textContent = ev.skillName || ev.skillId || '';
        head.appendChild(nameEl);

        var chip = document.createElement('span');
        chip.className = chipCls;
        chip.textContent = chipLabel;
        head.appendChild(chip);

        if (ev.newValue) {
          var delta = document.createElement('span');
          delta.className = 'ptl2__rank-delta';
          if (isRank && ev.previousValue) {
            var from = document.createElement('span');
            from.className = 'ptl2__rank-from';
            from.textContent = ev.previousValue;
            var arr = document.createElement('span');
            arr.className = 'ptl2__rank-arr';
            arr.textContent = ' → ';
            var to = document.createElement('span');
            to.className = 'ptl2__rank-to';
            to.textContent = ev.newValue;
            delta.appendChild(from); delta.appendChild(arr); delta.appendChild(to);
          } else if (isRank) {
            var to2 = document.createElement('span');
            to2.className = 'ptl2__rank-to';
            to2.textContent = ev.newValue;
            delta.appendChild(to2);
          }
          if (delta.childNodes.length > 0) head.appendChild(delta);
        }

        if (isRank && ev.diff !== 0 && ev.diff !== undefined) {
          var badge = document.createElement('span');
          if (ev.diff > 0) {
            badge.className = 'ptl2__delta-badge ptl2__delta-badge--pos';
            badge.textContent = '+' + ev.diff;
          } else {
            badge.className = 'ptl2__delta-badge ptl2__delta-badge--neg';
            badge.textContent = ev.diff;
          }
          head.appendChild(badge);
        }

        card.appendChild(head);

        var dateEl = document.createElement('time');
        dateEl.className = 'ptl2__date';
        dateEl.setAttribute('datetime', ev.ts.toISOString());
        dateEl.textContent = fmtDay(ev.ts);
        card.appendChild(dateEl);

        row.appendChild(card);
        monthEl.appendChild(row);
        globalIdx++;
      });

      inner.appendChild(monthEl);
    });

    return inner;
  }

  // ── Legend with toggle ────────────────────────────────────────────
  function buildLegend(skills, skillGroups) {
    var div = document.createElement('div');
    div.className = 'ptl2__legend';
    skills.forEach(function (skill) {
      if (!skill.levelHistory || skill.levelHistory.length === 0) return;
      var item = document.createElement('span');
      item.className = 'ptl2__legend-item';
      item.setAttribute('role', 'checkbox');
      item.setAttribute('aria-checked', 'true');
      item.setAttribute('tabindex', '0');
      item.setAttribute('data-skill-id', skill.id);

      var dot = document.createElement('span');
      dot.className = 'ptl2__legend-dot';
      dot.style.background = TIER_HEX[skill.type] || '#64748b';
      item.appendChild(dot);

      var label = document.createElement('span');
      label.textContent = skill.name || skill.id.split('/').pop();
      item.appendChild(label);

      function toggle() {
        var grp = skillGroups[skill.id];
        var muted = item.classList.toggle('is-muted');
        item.setAttribute('aria-checked', muted ? 'false' : 'true');
        if (grp) grp.style.opacity = muted ? '0' : '';
      }
      item.addEventListener('click', toggle);
      item.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
      });

      div.appendChild(item);
    });
    return div;
  }

  // ── Main render ───────────────────────────────────────────────────
  function renderProfileTimeline(container, data, filterOptions) {
    _injectStyles();
    while (container.firstChild) container.removeChild(container.firstChild);

    filterOptions = filterOptions || {};
    var activeSkills = filterOptions.activeSkills;

    var hasSkills = data && data.skills && data.skills.length > 0;
    if (!hasSkills) {
      container.innerHTML = '<div class="ptl2__empty">No progression data yet.</div>';
      return;
    }

    var allEvents = buildEvents(data);

    var events = allEvents.filter(function (ev) {
      if (activeSkills && !activeSkills.has(ev.skillId)) return false;
      if (filterOptions.minDate) {
        var tMin = new Date(filterOptions.minDate).getTime();
        if (ev.ts.getTime() < tMin) return false;
      }
      if (filterOptions.maxDate) {
        var tMax = new Date(filterOptions.maxDate).getTime();
        if (ev.ts.getTime() > tMax) return false;
      }
      return true;
    });

    if (events.length === 0) {
      container.innerHTML = '<div class="ptl2__empty">No events matching filters.</div>';
      return;
    }

    var wrapper = document.createElement('div');
    wrapper.className = 'ptl2';

    var chartPanel = document.createElement('div');
    chartPanel.className = 'ptl2__chart-panel';

    var activeChartSkills = (data.skills || []).filter(function (s) {
      if (activeSkills && !activeSkills.has(s.id)) return false;
      return s.levelHistory && s.levelHistory.length > 0;
    });

    var chartTitle = document.createElement('div');
    chartTitle.className = 'ptl2__chart-title';
    chartTitle.textContent = 'Rank Progression · ' + activeChartSkills.length + ' skills';
    chartPanel.appendChild(chartTitle);

    var chartResult = buildChart(data, events, filterOptions);
    var skillGroups = {};
    if (chartResult) {
      chartPanel.appendChild(chartResult.svg);
      skillGroups = chartResult.skillGroups;

      var legendSkills = data.skills.filter(function (s) {
        if (activeSkills && !activeSkills.has(s.id)) return false;
        return true;
      });
      var legend = buildLegend(legendSkills, skillGroups);
      chartPanel.appendChild(legend);
    }

    wrapper.appendChild(chartPanel);

    var feedPanel = document.createElement('div');
    feedPanel.className = 'ptl2__feed-panel';

    var feedHeader = document.createElement('div');
    feedHeader.className = 'ptl2__feed-header';
    feedHeader.textContent = 'Events · ' + events.length + ' total';
    feedPanel.appendChild(feedHeader);

    var feedScroll = document.createElement('div');
    feedScroll.className = 'ptl2__feed-scroll';
    feedScroll.setAttribute('role', 'list');
    feedScroll.setAttribute('aria-label', 'Skill progression events');
    feedScroll.appendChild(renderFeed(events));
    feedPanel.appendChild(feedScroll);

    wrapper.appendChild(feedPanel);
    container.appendChild(wrapper);

    var tooltip = document.querySelector('.ptl2__tooltip');
    if (!tooltip) {
      tooltip = document.createElement('div');
      tooltip.className = 'ptl2__tooltip';
      document.body.appendChild(tooltip);
    }

    if (chartResult) {
      Object.keys(skillGroups).forEach(function (skillId) {
        var grp = skillGroups[skillId];
        var skillEntry = data.skills.find(function (s) { return s.id === skillId; }) || {};

        grp.addEventListener('mouseenter', function (e) {
          Object.keys(skillGroups).forEach(function (sid) {
            if (sid !== skillId) {
              skillGroups[sid].style.opacity = '0.15';
            } else {
              skillGroups[sid].style.opacity = '1.0';
            }
          });

          var legendItem = container.querySelector('.ptl2__legend-item[data-skill-id="' + skillId + '"]');
          if (legendItem) legendItem.classList.add('is-highlighted');

          var bareId = skillId.includes('/') ? skillId.split('/').pop() : skillId;
          var plaqueCard = document.querySelector('article.plaque[data-skill-id$="' + bareId + '"]');
          if (plaqueCard) {
            plaqueCard.classList.add('is-highlighted');
          }

          tooltip.innerHTML = '';

          var titleRow = document.createElement('div');
          titleRow.className = 'ptl2__tooltip-title-row';

          var nameSpan = document.createElement('span');
          nameSpan.className = 'ptl2__tooltip-name';
          nameSpan.textContent = skillEntry.name || skillId.split('/').pop();
          titleRow.appendChild(nameSpan);

          var tierSpan = document.createElement('span');
          tierSpan.className = 'ptl2__tooltip-tier ptl2__tooltip-tier--' + (skillEntry.type || 'basic');
          tierSpan.textContent = skillEntry.type || 'basic';
          titleRow.appendChild(tierSpan);

          titleRow.appendChild(tierSpan);
          tooltip.appendChild(titleRow);

          var detailRow = document.createElement('div');
          detailRow.className = 'ptl2__tooltip-detail-row';

          var rankSpan = document.createElement('span');
          rankSpan.className = 'ptl2__tooltip-rank';
          rankSpan.textContent = 'Current Rank';
          detailRow.appendChild(rankSpan);

          var dateSpan = document.createElement('span');
          dateSpan.className = 'ptl2__tooltip-date';
          dateSpan.textContent = '';
          detailRow.appendChild(dateSpan);

          detailRow.appendChild(dateSpan);
          tooltip.appendChild(detailRow);

          tooltip.classList.add('is-visible');
        });

        grp.addEventListener('mousemove', function (e) {
          tooltip.style.left = (e.pageX + 16) + 'px';
          tooltip.style.top = (e.pageY + 16) + 'px';

          var targetDot = e.target;
          if (targetDot && targetDot.classList.contains('ptl2__chart-dot')) {
            var rank = targetDot.getAttribute('data-rank');
            var date = targetDot.getAttribute('data-date');

            var rankSpan = tooltip.querySelector('.ptl2__tooltip-rank');
            var dateSpan = tooltip.querySelector('.ptl2__tooltip-date');
            if (rankSpan && dateSpan) {
              rankSpan.textContent = 'Ranked to ' + rank;
              dateSpan.textContent = date;
            }
          }
        });

        grp.addEventListener('mouseleave', function (e) {
          Object.keys(skillGroups).forEach(function (sid) {
            skillGroups[sid].style.opacity = '';
          });

          var legendItem = container.querySelector('.ptl2__legend-item[data-skill-id="' + skillId + '"]');
          if (legendItem) legendItem.classList.remove('is-highlighted');

          var bareId = skillId.includes('/') ? skillId.split('/').pop() : skillId;
          var plaqueCard = document.querySelector('article.plaque[data-skill-id$="' + bareId + '"]');
          if (plaqueCard) {
            plaqueCard.classList.remove('is-highlighted');
          }

          tooltip.classList.remove('is-visible');
        });
      });
    }
  }

  function _auto() {
    var el = document.getElementById('profile-timeline');
    if (el && window.PROFILE_TIMELINE) renderProfileTimeline(el, window.PROFILE_TIMELINE);
  }

  if (typeof window !== 'undefined') {
    window.renderProfileTimeline = renderProfileTimeline;
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', _auto);
    } else {
      _auto();
    }
  }
})();


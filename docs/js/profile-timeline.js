(function () {
  // ──────────────────────────────────────────────────────────────────
  // profile-timeline.js — Skill Progression Timeline (vertical, linear)
  //
  // Data contract: window.PROFILE_TIMELINE = { skills[], events[] }
  // Render target:  <div id="profile-timeline" ...>
  //
  // Design: chronological event list grouped by month, with a
  // continuous vertical connector line and tier-coloured markers.
  // ──────────────────────────────────────────────────────────────────

  // ── CSS injected once ─────────────────────────────────────────────
  var _cssInjected = false;
  function _injectStyles() {
    if (_cssInjected || typeof document === 'undefined') return;
    _cssInjected = true;
    var style = document.createElement('style');
    style.id = 'profile-timeline-styles';
    style.textContent = [
      /* Container */
      '.ptl { position: relative; padding: 0; }',

      /* Continuous vertical spine */
      '.ptl__spine {',
      '  position: absolute;',
      '  left: 20px;',
      '  top: 8px;',
      '  bottom: 0;',
      '  width: 1px;',
      '  background: linear-gradient(to bottom,',
      '    transparent 0%,',
      '    var(--border, #1e293b) 6%,',
      '    var(--border, #1e293b) 94%,',
      '    transparent 100%);',
      '}',

      /* Month group */
      '.ptl__month { position: relative; margin-bottom: 0; }',

      /* Month header label */
      '.ptl__month-label {',
      '  position: sticky;',
      '  top: 64px;',
      '  z-index: 2;',
      '  display: inline-flex;',
      '  align-items: center;',
      '  gap: 0.5rem;',
      '  margin-left: 48px;',
      '  margin-bottom: 1rem;',
      '  margin-top: 1.5rem;',
      '  padding: 0.2rem 0.65rem;',
      '  font-family: var(--font-mono, monospace);',
      '  font-size: 0.65rem;',
      '  letter-spacing: 0.12em;',
      '  text-transform: uppercase;',
      '  color: rgba(226, 232, 240, 0.35);',
      '  background: var(--bg, #030712);',
      '  border: 1px solid var(--border, #1e293b);',
      '  border-radius: 3px;',
      '  pointer-events: none;',
      '}',
      '.ptl__month:first-child .ptl__month-label { margin-top: 0; }',

      /* Each event row */
      '.ptl__event {',
      '  position: relative;',
      '  display: grid;',
      '  grid-template-columns: 41px 1fr;',
      '  gap: 0;',
      '  margin-bottom: 2px;',
      '  align-items: start;',
      '}',

      /* Marker column (holds the dot) */
      '.ptl__marker-col {',
      '  display: flex;',
      '  flex-direction: column;',
      '  align-items: center;',
      '  padding-top: 13px;',
      '}',

      /* The dot */
      '.ptl__dot {',
      '  width: 9px;',
      '  height: 9px;',
      '  border-radius: 50%;',
      '  border: 1.5px solid var(--border, #1e293b);',
      '  background: var(--bg, #030712);',
      '  flex-shrink: 0;',
      '  transition: transform 0.15s, box-shadow 0.15s;',
      '}',
      '.ptl__dot--rank { width: 11px; height: 11px; border-width: 2px; }',
      '.ptl__dot--basic    { border-color: var(--tier-basic, #38bdf8);    background: rgba(56,189,248,.12); }',
      '.ptl__dot--extra    { border-color: var(--tier-extra, #c084fc);    background: rgba(192,132,252,.12); }',
      '.ptl__dot--unique   { border-color: var(--tier-unique, #7c3aed);   background: #000; }',
      '.ptl__dot--ultimate { border-color: var(--tier-ultimate, #f59e0b); background: rgba(245,158,11,.12); }',
      '.ptl__event--rank-up .ptl__dot--basic    { box-shadow: 0 0 8px  rgba(56,189,248,.5); }',
      '.ptl__event--rank-up .ptl__dot--extra    { box-shadow: 0 0 8px  rgba(192,132,252,.5); }',
      '.ptl__event--rank-up .ptl__dot--unique   { box-shadow: 0 0 10px rgba(124,58,237,.7); }',
      '.ptl__event--rank-up .ptl__dot--ultimate { box-shadow: 0 0 10px rgba(245,158,11,.6); }',

      /* Card */
      '.ptl__card {',
      '  padding: 8px 14px 8px 16px;',
      '  border-radius: 6px;',
      '  transition: background 0.15s;',
      '}',
      '.ptl__card:hover { background: rgba(255,255,255,0.03); }',

      /* Card head */
      '.ptl__card-head {',
      '  display: flex;',
      '  align-items: baseline;',
      '  gap: 0.45rem;',
      '  flex-wrap: wrap;',
      '}',

      '.ptl__skill-name {',
      '  font-family: var(--font-body, sans-serif);',
      '  font-size: 0.88rem;',
      '  font-weight: 600;',
      '  color: var(--text, #e2e8f0);',
      '  line-height: 1.4;',
      '}',

      /* Action chip */
      '.ptl__action-chip {',
      '  display: inline-block;',
      '  font-family: var(--font-mono, monospace);',
      '  font-size: 0.58rem;',
      '  letter-spacing: 0.1em;',
      '  text-transform: uppercase;',
      '  font-weight: 700;',
      '  padding: 2px 7px;',
      '  border-radius: 3px;',
      '  flex-shrink: 0;',
      '  line-height: 1.6;',
      '}',
      '.ptl__action-chip--register { color: var(--muted,#64748b); background: rgba(100,116,139,.1); border: 1px solid rgba(100,116,139,.2); }',
      '.ptl__action-chip--propose  { color: var(--tier-basic,#38bdf8); background: rgba(56,189,248,.08); border: 1px solid rgba(56,189,248,.2); }',
      '.ptl__action-chip--add      { color: var(--tier-basic,#38bdf8); background: rgba(56,189,248,.08); border: 1px solid rgba(56,189,248,.2); }',
      '.ptl__action-chip--rank_up  { color: #86efac; background: rgba(134,239,172,.08); border: 1px solid rgba(134,239,172,.22); }',
      '.ptl__action-chip--ascend   { color: #86efac; background: rgba(134,239,172,.08); border: 1px solid rgba(134,239,172,.22); }',
      '.ptl__action-chip--promote  { color: #86efac; background: rgba(134,239,172,.08); border: 1px solid rgba(134,239,172,.22); }',
      '.ptl__action-chip--demote   { color: var(--honor-red,#ef4444); background: rgba(239,68,68,.08); border: 1px solid rgba(239,68,68,.2); }',
      '.ptl__action-chip--fuse     { color: var(--tier-ultimate,#f59e0b); background: rgba(245,158,11,.08); border: 1px solid rgba(245,158,11,.2); }',
      '.ptl__action-chip--default  { color: var(--muted,#64748b); background: rgba(100,116,139,.08); border: 1px solid rgba(100,116,139,.18); }',

      /* Rank change */
      '.ptl__rank-change {',
      '  display: inline-flex;',
      '  align-items: center;',
      '  gap: 4px;',
      '  font-family: var(--font-mono,monospace);',
      '  font-size: 0.72rem;',
      '  color: rgba(226,232,240,0.5);',
      '  flex-shrink: 0;',
      '}',
      '.ptl__rank-from  { text-decoration: line-through; opacity: 0.55; }',
      '.ptl__rank-to    { color: #86efac; font-weight: 700; }',
      '.ptl__rank-arrow { opacity: 0.4; font-size: 0.6rem; }',

      /* Details & date */
      '.ptl__details {',
      '  margin-top: 2px;',
      '  font-size: 0.76rem;',
      '  color: rgba(226,232,240,0.35);',
      '  line-height: 1.4;',
      '}',
      '.ptl__date {',
      '  font-family: var(--font-mono,monospace);',
      '  font-size: 0.62rem;',
      '  color: rgba(226,232,240,0.22);',
      '  letter-spacing: 0.04em;',
      '  margin-top: 2px;',
      '}',

      /* Empty state */
      '.ptl__empty {',
      '  padding: 3rem 0;',
      '  text-align: center;',
      '  font-family: var(--font-mono,monospace);',
      '  font-size: 0.8rem;',
      '  color: rgba(226,232,240,0.25);',
      '  letter-spacing: 0.08em;',
      '}',

      /* Entrance animation */
      '@keyframes ptl-slide-in {',
      '  from { opacity: 0; transform: translateX(-6px); }',
      '  to   { opacity: 1; transform: translateX(0); }',
      '}',
      '.ptl__event {',
      '  opacity: 0;',
      '  animation: ptl-slide-in 0.28s ease-out forwards;',
      '}',

      /* Reduced motion */
      '@media (prefers-reduced-motion: reduce) {',
      '  .ptl__event { animation: none !important; opacity: 1 !important; }',
      '}',

      /* Responsive */
      '@media (max-width: 480px) {',
      '  .ptl__skill-name   { font-size: 0.82rem; }',
      '  .ptl__action-chip  { font-size: 0.52rem; }',
      '  .ptl__rank-change  { font-size: 0.65rem; }',
      '}',
    ].join('\n');
    document.head.appendChild(style);
  }

  // ── Helpers ───────────────────────────────────────────────────────
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
    var stars = (s.match(/★/g) || []).length;
    if (stars > 0) return Math.min(6, stars);
    return 0;
  }

  function fmtMonthYear(d) {
    return d.toLocaleString('en', { month: 'long', year: 'numeric', timeZone: 'UTC' });
  }

  function fmtDay(d) {
    return d.toLocaleString('en', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
  }

  function monthKey(d) {
    return d.getUTCFullYear() + '-' + String(d.getUTCMonth() + 1).padStart(2, '0');
  }

  var ACTION_CHIP_MAP = {
    register: 'register', propose: 'propose', add: 'add',
    rank_up: 'rank_up', ascend: 'ascend', promote: 'promote',
    demote: 'demote', fuse: 'fuse',
  };

  var ACTION_LABEL = {
    register: 'Registered', propose: 'Proposed', add: 'Added',
    rank_up: 'Ranked Up', ascend: 'Ascended', promote: 'Promoted',
    demote: 'Demoted', fuse: 'Fused',
  };

  function isRankAction(action) {
    return action === 'rank_up' || action === 'ascend' || action === 'fuse'
      || action === 'promote' || action === 'demote';
  }

  // ── Build unified event list ──────────────────────────────────────
  function buildEvents(data) {
    var skillMap = {};
    (data.skills || []).forEach(function (s) { skillMap[s.id] = s; });

    var events = [];

    // 1. Level-history from each skill's levelHistory
    (data.skills || []).forEach(function (skill) {
      (skill.levelHistory || []).forEach(function (h) {
        var ts = new Date(h.achievedAt);
        if (isNaN(ts.getTime())) return;
        events.push({
          ts: ts,
          skillId: skill.id,
          skillName: skill.name || skill.id,
          type: skill.type || 'basic',
          action: h.source === 'promotion' ? 'rank_up' : (h.source || 'rank_up'),
          newValue: h.level || null,
          previousValue: null,
          details: null,
        });
      });
    });

    // 2. Explicit events, deduplicated
    var seenKeys = {};
    events.forEach(function (e) {
      seenKeys[e.ts.toISOString() + '|' + e.action + '|' + e.skillId] = true;
    });

    (data.events || []).forEach(function (ev) {
      var ts = new Date(ev.timestamp);
      if (isNaN(ts.getTime())) return;
      var key = ts.toISOString() + '|' + (ev.action || '') + '|' + (ev.skillId || '');
      if (seenKeys[key]) return;
      seenKeys[key] = true;
      var skill = skillMap[ev.skillId] || {};
      events.push({
        ts: ts,
        skillId: ev.skillId,
        skillName: skill.name || ev.skillId,
        type: skill.type || 'basic',
        action: ev.action || 'register',
        newValue: ev.newValue || null,
        previousValue: ev.previousValue || null,
        details: ev.details || null,
      });
    });

    // Newest first
    events.sort(function (a, b) { return b.ts - a.ts; });
    return events;
  }

  // ── Group by month ────────────────────────────────────────────────
  function groupByMonth(events) {
    var groups = [];
    var groupMap = {};
    events.forEach(function (ev) {
      var k = monthKey(ev.ts);
      if (!groupMap[k]) {
        groupMap[k] = { key: k, label: fmtMonthYear(ev.ts), events: [] };
        groups.push(groupMap[k]);
      }
      groupMap[k].events.push(ev);
    });
    return groups;
  }

  // ── Render one event ──────────────────────────────────────────────
  function renderEvent(ev, idx) {
    var action = ev.action || 'register';
    var chipClass = 'ptl__action-chip--' + (ACTION_CHIP_MAP[action] || 'default');
    var label = ACTION_LABEL[action] || action.replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
    var isRank = isRankAction(action);

    var dotClass = 'ptl__dot ptl__dot--' + (ev.type || 'basic') + (isRank ? ' ptl__dot--rank' : '');
    var rowClass = 'ptl__event' + (isRank ? ' ptl__event--rank-up' : '');

    var rankChangeHtml = '';
    if (ev.newValue) {
      if (isRank && ev.previousValue) {
        rankChangeHtml = '<span class="ptl__rank-change">'
          + '<span class="ptl__rank-from">' + esc(ev.previousValue) + '</span>'
          + '<span class="ptl__rank-arrow"> → </span>'
          + '<span class="ptl__rank-to">' + esc(ev.newValue) + '</span>'
          + '</span>';
      } else if (isRank) {
        rankChangeHtml = '<span class="ptl__rank-change">'
          + '<span class="ptl__rank-to">' + esc(ev.newValue) + '</span>'
          + '</span>';
      }
    }

    var detailsHtml = (ev.details && action !== 'register')
      ? '<div class="ptl__details">' + esc(ev.details) + '</div>'
      : '';

    var delay = Math.min(idx * 25, 500);

    return '<div class="' + rowClass + '" role="listitem" style="animation-delay:' + delay + 'ms">'
      + '<div class="ptl__marker-col" aria-hidden="true">'
      +   '<span class="' + esc(dotClass) + '"></span>'
      + '</div>'
      + '<div class="ptl__card">'
      +   '<div class="ptl__card-head">'
      +     '<span class="ptl__skill-name">' + esc(ev.skillName) + '</span>'
      +     '<span class="ptl__action-chip ' + chipClass + '" aria-label="' + esc(label) + '">' + esc(label) + '</span>'
      +     rankChangeHtml
      +   '</div>'
      +   detailsHtml
      +   '<time class="ptl__date" datetime="' + esc(ev.ts.toISOString()) + '">' + esc(fmtDay(ev.ts)) + '</time>'
      + '</div>'
      + '</div>';
  }

  // ── Main render ───────────────────────────────────────────────────
  function renderProfileTimeline(container, data) {
    _injectStyles();

    while (container.firstChild) container.removeChild(container.firstChild);

    var hasSkills = data && data.skills && data.skills.length > 0;
    if (!hasSkills) {
      container.innerHTML = '<div class="ptl__empty">No progression data yet.</div>';
      return;
    }

    var events = buildEvents(data);
    if (events.length === 0) {
      container.innerHTML = '<div class="ptl__empty">No progression data yet.</div>';
      return;
    }

    var groups = groupByMonth(events);

    var html = '<div class="ptl">'
      + '<div class="ptl__spine" aria-hidden="true"></div>';

    var globalIdx = 0;
    groups.forEach(function (group) {
      html += '<div class="ptl__month" role="group" aria-label="' + esc(group.label) + '">';
      html += '<div class="ptl__month-label" aria-hidden="true">' + esc(group.label) + '</div>';
      group.events.forEach(function (ev) {
        html += renderEvent(ev, globalIdx++);
      });
      html += '</div>';
    });

    html += '</div>';
    container.innerHTML = html;
  }

  // ── Auto-render ───────────────────────────────────────────────────
  function _autoRender() {
    var el = document.getElementById('profile-timeline');
    if (el && window.PROFILE_TIMELINE) {
      renderProfileTimeline(el, window.PROFILE_TIMELINE);
    }
  }

  if (typeof window !== 'undefined') {
    window.renderProfileTimeline = renderProfileTimeline;
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', _autoRender);
    } else {
      _autoRender();
    }
  }
})();

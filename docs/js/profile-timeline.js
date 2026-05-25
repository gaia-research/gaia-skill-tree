(function () {
  // ──────────────────────────────────────────────────────────────────
  // profile-timeline.js  — Skill progression timeline (SVG line chart)
  //
  // Data contract: window.PROFILE_TIMELINE = { skills[], events[] }
  // Render target:  <div id="profile-timeline" ...>
  //
  // Token contract (read once, cached):
  //   --tier-basic / extra / unique / ultimate
  //   --apex-gold  --muted
  // ──────────────────────────────────────────────────────────────────

  // ── Token cache ──────────────────────────────────────────────────
  let _tokCache = null;
  function _rv(name) {
    if (typeof document === 'undefined') return '';
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }
  function getTokens() {
    if (_tokCache) return _tokCache;
    _tokCache = {
      basic:    _rv('--tier-basic')    || null,
      extra:    _rv('--tier-extra')    || null,
      unique:   _rv('--tier-unique')   || null,
      ultimate: _rv('--tier-ultimate') || null,
      apexGold: _rv('--apex-gold')     || null,
      muted:    _rv('--muted')         || null,
    };
    return _tokCache;
  }
  function invalidateTimelineTokens() { _tokCache = null; }
  if (typeof window !== 'undefined') window.invalidateTimelineTokens = invalidateTimelineTokens;

  // ── Helpers ──────────────────────────────────────────────────────
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // Parse a level string like '5★' or '★★★' or '3' → integer 0–6
  function parseRank(level) {
    if (!level) return 0;
    var s = String(level);
    // Leading digit preferred
    var m = s.match(/^(\d)/);
    if (m) return Math.min(6, parseInt(m[1], 10));
    // Count star characters as fallback
    var stars = (s.match(/★/g) || []).length;
    if (stars > 0) return Math.min(6, stars);
    return 0;
  }

  // Rank at a given epoch from levelHistory (sorted asc)
  function rankAt(levelHistory, ts) {
    var rank = 0;
    for (var i = 0; i < levelHistory.length; i++) {
      if (new Date(levelHistory[i].achievedAt).getTime() <= ts) {
        rank = parseRank(levelHistory[i].level);
      } else {
        break;
      }
    }
    return rank;
  }

  // SVG namespace helper
  var NS = 'http://www.w3.org/2000/svg';
  function svgEl(tag, attrs) {
    var el = document.createElementNS(NS, tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) { el.setAttribute(k, attrs[k]); });
    }
    return el;
  }

  // Format date as 'YYYY-MM-DD' for tooltip
  function fmtDate(d) {
    return d.getUTCFullYear() + '-' +
      String(d.getUTCMonth() + 1).padStart(2, '0') + '-' +
      String(d.getUTCDate()).padStart(2, '0');
  }

  // Format action label
  function fmtAction(ev) {
    var parts = [fmtDate(new Date(ev.timestamp)), (ev.action || '').toUpperCase()];
    if (ev.previousValue && ev.newValue) {
      parts.push(ev.previousValue + ' → ' + ev.newValue);
    } else if (ev.newValue) {
      parts.push('→ ' + ev.newValue);
    }
    return parts.join(' · ');
  }

  // ── Layout constants ─────────────────────────────────────────────
  var MARGIN = { top: 24, right: 28, bottom: 32, left: 56 };
  var VIEW_W = 800, VIEW_H = 360;
  var INNER_W = VIEW_W - MARGIN.left - MARGIN.right;
  var INNER_H = VIEW_H - MARGIN.top - MARGIN.bottom;

  // ── Scale functions ──────────────────────────────────────────────
  function makeScales(minT, maxT) {
    var tRange = maxT - minT || 1;
    var pad = tRange * 0.04;
    var t0 = minT - pad, t1 = maxT + pad;
    var tSpan = t1 - t0 || 1;
    function xScale(ts) { return (ts - t0) / tSpan * INNER_W; }
    function yScale(rank) { return INNER_H - (rank / 6) * INNER_H; }
    return { xScale: xScale, yScale: yScale, t0: t0, t1: t1 };
  }

  // ── Build step-after polyline points for one skill ──────────────
  function buildStepPoints(levelHistory, xScale, yScale) {
    if (!levelHistory || levelHistory.length === 0) return [];
    var sorted = levelHistory.slice().sort(function (a, b) {
      return new Date(a.achievedAt) - new Date(b.achievedAt);
    });
    var pts = [];
    var prevRank = 0;
    for (var i = 0; i < sorted.length; i++) {
      var ts = new Date(sorted[i].achievedAt).getTime();
      var rank = parseRank(sorted[i].level);
      // Step-after: horizontal segment at old rank, then vertical
      if (pts.length > 0) {
        pts.push({ x: xScale(ts), y: yScale(prevRank) }); // horizontal step
      }
      pts.push({ x: xScale(ts), y: yScale(rank) });
      prevRank = rank;
    }
    return pts;
  }

  // ── Accessible table fallback ────────────────────────────────────
  function buildFallbackTable(data) {
    var rows = [];
    (data.events || []).forEach(function (ev) {
      var skill = (data.skills || []).find(function (s) { return s.id === ev.skillId; });
      var name = skill ? skill.name : ev.skillId;
      rows.push([fmtDate(new Date(ev.timestamp)), esc(name || ''), esc((ev.action || '').toUpperCase()),
        esc(ev.previousValue || ''), esc(ev.newValue || ''), esc(ev.details || '')]);
    });
    // Also add levelHistory entries not captured by events
    (data.skills || []).forEach(function (skill) {
      (skill.levelHistory || []).forEach(function (h) {
        rows.push([fmtDate(new Date(h.achievedAt)), esc(skill.name || skill.id), esc((h.source || 'promotion').toUpperCase()),
          '', esc(h.level || ''), '']);
      });
    });
    rows.sort(function (a, b) { return a[0].localeCompare(b[0]); });

    var html = '<details><summary>Timeline data</summary>' +
      '<table><thead><tr>' +
      '<th scope="col">Date</th><th scope="col">Skill</th><th scope="col">Action</th>' +
      '<th scope="col">From</th><th scope="col">To</th><th scope="col">Details</th>' +
      '</tr></thead><tbody>';
    rows.forEach(function (r) {
      html += '<tr>' + r.map(function (c) { return '<td>' + c + '</td>'; }).join('') + '</tr>';
    });
    html += '</tbody></table></details>';
    return html;
  }

  // ── Main render function ─────────────────────────────────────────
  function renderProfileTimeline(container, data) {
    // Clear
    while (container.firstChild) container.removeChild(container.firstChild);

    // Guard: missing or empty data
    var hasSkills = data && data.skills && data.skills.length > 0;
    if (!hasSkills) {
      var emptyP = document.createElement('p');
      emptyP.className = 'profile-timeline__empty';
      emptyP.textContent = 'Timeline data pending.';
      container.appendChild(emptyP);
      return;
    }

    var tok = getTokens();

    // ── Collect all timestamps ───────────────────────────────────
    var allTs = [];
    data.skills.forEach(function (skill) {
      (skill.levelHistory || []).forEach(function (h) {
        var t = new Date(h.achievedAt).getTime();
        if (!isNaN(t)) allTs.push(t);
      });
    });
    (data.events || []).forEach(function (ev) {
      var t = new Date(ev.timestamp).getTime();
      if (!isNaN(t)) allTs.push(t);
    });

    if (allTs.length === 0) {
      var noTs = document.createElement('p');
      noTs.className = 'profile-timeline__empty';
      noTs.textContent = 'Timeline data pending.';
      container.appendChild(noTs);
      return;
    }

    var minT = Math.min.apply(null, allTs);
    var maxT = Math.max.apply(null, allTs);
    var scales = makeScales(minT, maxT);
    var xScale = scales.xScale;
    var yScale = scales.yScale;

    // ── Build aria-label summary ──────────────────────────────────
    var skillCount = data.skills.length;
    var peakRank = 0;
    data.skills.forEach(function (skill) {
      (skill.levelHistory || []).forEach(function (h) {
        var r = parseRank(h.level);
        if (r > peakRank) peakRank = r;
      });
    });
    var fmtMin = new Intl.DateTimeFormat('en', { year: 'numeric', month: 'short' }).format(new Date(minT));
    var fmtMax = new Intl.DateTimeFormat('en', { year: 'numeric', month: 'short' }).format(new Date(maxT));
    var ariaLabel = 'Progression timeline: ' + skillCount + ' skill' + (skillCount !== 1 ? 's' : '') +
      ' from ' + fmtMin + ' to ' + fmtMax +
      (peakRank > 0 ? ', peak rank ' + peakRank + '★.' : '.');
    container.setAttribute('aria-label', ariaLabel);

    // ── Legend ───────────────────────────────────────────────────
    var legendDiv = document.createElement('div');
    legendDiv.className = 'profile-timeline__legend';
    legendDiv.style.cssText = 'display:flex;flex-wrap:wrap;gap:.5rem .75rem;justify-content:flex-end;margin-bottom:.5rem;font-size:.75rem;';
    data.skills.forEach(function (skill) {
      var color = tok[skill.type] || '';
      var item = document.createElement('span');
      item.className = 'profile-timeline__legend-item';
      item.style.cssText = 'display:inline-flex;align-items:center;gap:.3rem;cursor:pointer;';
      item.setAttribute('role', 'button');
      item.setAttribute('tabindex', '0');
      item.setAttribute('aria-pressed', 'false');
      item.setAttribute('data-skill-id', skill.id);

      var dot = document.createElement('span');
      dot.className = 'profile-timeline__legend-dot';
      dot.setAttribute('data-type', skill.type);
      dot.style.cssText = 'display:inline-block;width:10px;height:10px;border-radius:50%;flex-shrink:0;';
      if (color) dot.style.background = color;

      var label = document.createElement('span');
      label.textContent = skill.name || skill.id;

      item.appendChild(dot);
      item.appendChild(label);

      function toggleSkill() {
        var grpId = 'ptl-skill-' + skill.id.replace(/[^a-zA-Z0-9]/g, '-');
        var grp = container.querySelector('[data-skill-id="' + esc(skill.id) + '"].profile-timeline__skill-group');
        if (!grp) return;
        var hidden = grp.classList.toggle('is-hidden');
        item.setAttribute('aria-pressed', hidden ? 'true' : 'false');
        item.style.opacity = hidden ? '0.4' : '1';
      }
      item.addEventListener('click', toggleSkill);
      item.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleSkill(); }
      });
      legendDiv.appendChild(item);
    });
    container.appendChild(legendDiv);

    // ── SVG scaffold ─────────────────────────────────────────────
    var svg = svgEl('svg', {
      viewBox: '0 0 ' + VIEW_W + ' ' + VIEW_H,
      role: 'presentation',
      'aria-hidden': 'true',
      style: 'width:100%;height:auto;display:block;overflow:visible;',
    });

    // ── Defs: apex glow filter ───────────────────────────────────
    var defs = svgEl('defs');
    var filter = svgEl('filter', { id: 'apex-glow', x: '-50%', y: '-50%', width: '200%', height: '200%' });
    var feBlur = svgEl('feGaussianBlur', { in: 'SourceGraphic', stdDeviation: '3', result: 'blur' });
    var feMerge = svgEl('feMerge');
    var feMerge1 = svgEl('feMergeNode', { in: 'blur' });
    var feMerge2 = svgEl('feMergeNode', { in: 'SourceGraphic' });
    feMerge.appendChild(feMerge1);
    feMerge.appendChild(feMerge2);
    filter.appendChild(feBlur);
    filter.appendChild(feMerge);
    defs.appendChild(filter);
    svg.appendChild(defs);

    // ── Chart group (offset by margins) ─────────────────────────
    var g = svgEl('g', { transform: 'translate(' + MARGIN.left + ',' + MARGIN.top + ')' });
    svg.appendChild(g);

    // ── Y gridlines + labels ─────────────────────────────────────
    var mutedColor = tok.muted || '';
    for (var rank = 1; rank <= 6; rank++) {
      var gy = yScale(rank);
      var gridLine = svgEl('line', {
        x1: '0', y1: String(gy), x2: String(INNER_W), y2: String(gy),
        stroke: mutedColor || 'var(--muted)',
        'stroke-width': '0.5',
        'stroke-dasharray': '3 4',
        opacity: '0.5',
      });
      g.appendChild(gridLine);

      var rankLabel = svgEl('text', {
        x: '-8',
        y: String(gy + 4),
        'text-anchor': 'end',
        'font-size': '11',
        fill: mutedColor || 'var(--muted)',
      });
      rankLabel.textContent = rank + '★';
      g.appendChild(rankLabel);
    }

    // ── X axis ticks ─────────────────────────────────────────────
    var tickCount = 5;
    var tickFmt = new Intl.DateTimeFormat('en', { year: 'numeric', month: 'short' });
    for (var ti = 0; ti <= tickCount; ti++) {
      var tickTs = scales.t0 + (ti / tickCount) * (scales.t1 - scales.t0);
      var tx = xScale(tickTs);
      var xTickLine = svgEl('line', {
        x1: String(tx), y1: String(INNER_H),
        x2: String(tx), y2: String(INNER_H + 4),
        stroke: mutedColor || 'var(--muted)',
        'stroke-width': '1',
      });
      g.appendChild(xTickLine);
      var xTickLabel = svgEl('text', {
        x: String(tx),
        y: String(INNER_H + 16),
        'text-anchor': 'middle',
        'font-size': '10',
        fill: mutedColor || 'var(--muted)',
      });
      xTickLabel.textContent = tickFmt.format(new Date(tickTs));
      g.appendChild(xTickLabel);
    }

    // ── X axis baseline ──────────────────────────────────────────
    var xAxisLine = svgEl('line', {
      x1: '0', y1: String(INNER_H),
      x2: String(INNER_W), y2: String(INNER_H),
      stroke: mutedColor || 'var(--muted)',
      'stroke-width': '0.75',
      opacity: '0.6',
    });
    g.appendChild(xAxisLine);

    // ── Tooltip DOM element ──────────────────────────────────────
    var tooltip = document.createElement('div');
    tooltip.className = 'profile-timeline__tooltip';
    tooltip.setAttribute('role', 'tooltip');
    tooltip.hidden = true;
    tooltip.style.cssText = [
      'position:absolute', 'z-index:10', 'pointer-events:none',
      'background:var(--surface,#1a1a2e)', 'border:1px solid var(--muted,#666)',
      'border-radius:6px', 'padding:.4rem .6rem', 'font-size:.72rem',
      'line-height:1.4', 'max-width:220px', 'box-shadow:0 4px 12px rgba(0,0,0,.4)',
    ].join(';');
    container.style.position = 'relative';
    container.appendChild(tooltip);

    // Shared hover state
    var hoverPoints = []; // { x, y (SVG coords), skillName, eventLine, details }

    // ── Per-skill groups ─────────────────────────────────────────
    data.skills.forEach(function (skill) {
      var color = tok[skill.type] || '';
      var sorted = (skill.levelHistory || []).slice().sort(function (a, b) {
        return new Date(a.achievedAt) - new Date(b.achievedAt);
      });
      if (sorted.length === 0) return;

      var grp = svgEl('g', {});
      grp.setAttribute('data-skill-id', skill.id);
      grp.className.baseVal = 'profile-timeline__skill-group';
      g.appendChild(grp);

      var pts = buildStepPoints(sorted, xScale, yScale);

      // Polyline or single dot
      if (pts.length > 1) {
        var pointsStr = pts.map(function (p) { return p.x + ',' + p.y; }).join(' ');
        var polyline = svgEl('polyline', {
          points: pointsStr,
          fill: 'none',
          stroke: color || 'currentColor',
          'stroke-width': '2',
          'stroke-linejoin': 'round',
          'stroke-linecap': 'round',
          class: 'profile-timeline__line profile-timeline__line--' + skill.type,
          'data-type': skill.type,
        });
        if (!color) polyline.setAttribute('stroke', 'var(--tier-' + skill.type + ')');
        grp.appendChild(polyline);
      }

      // Level history dots + apex glow
      sorted.forEach(function (h) {
        var ts = new Date(h.achievedAt).getTime();
        var rank = parseRank(h.level);
        var cx = xScale(ts);
        var cy = yScale(rank);

        if (rank === 6) {
          // Apex glow halo circle
          var glowCircle = svgEl('circle', {
            cx: String(cx), cy: String(cy), r: '8',
            fill: tok.apexGold || 'var(--apex-gold)',
            opacity: '0.6',
            filter: 'url(#apex-glow)',
          });
          grp.appendChild(glowCircle);
        }

        var dot = svgEl('circle', {
          cx: String(cx), cy: String(cy), r: rank === 6 ? '5' : '4',
          fill: color || 'var(--tier-' + skill.type + ')',
          stroke: 'var(--surface,#1a1a2e)',
          'stroke-width': '1.5',
          style: 'cursor:pointer;',
        });
        grp.appendChild(dot);

        // Register hover point
        var actionLine = fmtDate(new Date(ts)) + ' · ' + (h.source || 'PROMOTION').toUpperCase() + ' · ' + (h.level || '');
        hoverPoints.push({
          cx: cx + MARGIN.left, cy: cy + MARGIN.top,
          skillName: skill.name || skill.id,
          eventLine: actionLine,
          details: null,
        });
      });
    });

    // ── Event dots ───────────────────────────────────────────────
    (data.events || []).forEach(function (ev) {
      var skill = (data.skills || []).find(function (s) { return s.id === ev.skillId; });
      if (!skill) return;

      var evTs = new Date(ev.timestamp).getTime();
      if (isNaN(evTs)) return;

      var color = tok[skill.type] || '';
      var grp = container.querySelector('[data-skill-id="' + esc(skill.id) + '"].profile-timeline__skill-group');
      if (!grp) return;

      var isRankChange = (ev.action === 'rank_up' || ev.action === 'ascend' || ev.action === 'fuse') && ev.newValue;
      var rank;
      if (isRankChange) {
        rank = parseRank(ev.newValue);
      } else {
        // Find current rank at event time from levelHistory
        var sorted = (skill.levelHistory || []).slice().sort(function (a, b) {
          return new Date(a.achievedAt) - new Date(b.achievedAt);
        });
        rank = rankAt(sorted, evTs);
      }

      var cx = xScale(evTs);
      var cy = yScale(rank);
      var r = isRankChange ? 5 : 3;

      var evDot = svgEl('circle', {
        cx: String(cx), cy: String(cy), r: String(r),
        fill: 'none',
        stroke: color || 'var(--tier-' + skill.type + ')',
        'stroke-width': '2',
        opacity: '0.85',
        style: 'cursor:pointer;',
      });
      grp.appendChild(evDot);

      hoverPoints.push({
        cx: cx + MARGIN.left, cy: cy + MARGIN.top,
        skillName: skill.name || skill.id,
        eventLine: fmtAction(ev),
        details: ev.details || null,
        r: r + 8,
      });
    });

    // ── Tooltip interaction via pointermove on SVG ───────────────
    svg.addEventListener('pointermove', function (e) {
      var svgRect = svg.getBoundingClientRect();
      var scaleX = (VIEW_W) / svgRect.width;
      var scaleY = (VIEW_H) / svgRect.height;
      var logX = (e.clientX - svgRect.left) * scaleX;
      var logY = (e.clientY - svgRect.top) * scaleY;

      var best = null, bestDist = Infinity;
      hoverPoints.forEach(function (pt) {
        var dx = logX - pt.cx, dy = logY - pt.cy;
        var dist = Math.sqrt(dx * dx + dy * dy);
        var threshold = (pt.r || 14);
        if (dist < threshold && dist < bestDist) {
          bestDist = dist;
          best = pt;
        }
      });

      if (best) {
        tooltip.hidden = false;
        var lines = ['<strong>' + esc(best.skillName) + '</strong>',
          '<span>' + esc(best.eventLine) + '</span>'];
        if (best.details) lines.push('<span>' + esc(best.details) + '</span>');
        tooltip.innerHTML = lines.join('<br>');

        // Position tooltip relative to container
        var containerRect = container.getBoundingClientRect();
        var tx = e.clientX - containerRect.left + 12;
        var ty = e.clientY - containerRect.top - 36;
        // Clamp right edge
        if (tx + 230 > container.offsetWidth) tx = container.offsetWidth - 234;
        if (ty < 4) ty = 4;
        tooltip.style.left = tx + 'px';
        tooltip.style.top = ty + 'px';
      } else {
        tooltip.hidden = true;
      }
    });
    svg.addEventListener('mouseleave', function () {
      tooltip.hidden = true;
    });

    container.appendChild(svg);

    // ── Accessible table fallback ────────────────────────────────
    var fallbackWrap = document.createElement('div');
    fallbackWrap.className = 'profile-timeline__table-fallback';
    fallbackWrap.style.cssText = 'font-size:.72rem;margin-top:.5rem;';
    fallbackWrap.innerHTML = buildFallbackTable(data);
    container.appendChild(fallbackWrap);
  }

  // ── Auto-render on DOMContentLoaded ─────────────────────────────
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

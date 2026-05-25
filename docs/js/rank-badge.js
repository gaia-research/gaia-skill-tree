/* rank-badge.js — renders rank badges (chip, stars, full variants).
 * Exposes window.rankBadge.chip(n) and window.rankBadge.stars(n).
 * Depends on: icons.js (for window.icon helper).
 */
(function () {

  var LEVEL_COLORS = {
    0: { hex: 'var(--rank-0, #94a3b8)', bg: 'var(--rank-0-bg, rgba(100,116,139,.15))', border: 'var(--rank-0-border, rgba(100,116,139,.4))'  },
    1: { hex: 'var(--rank-1, #38bdf8)', bg: 'var(--rank-1-bg, rgba(56,189,248,.15))',  border: 'var(--rank-1-border, rgba(56,189,248,.4))'   },
    2: { hex: 'var(--rank-2, #63cab7)', bg: 'var(--rank-2-bg, rgba(99,202,183,.15))',  border: 'var(--rank-2-border, rgba(99,202,183,.4))'   },
    3: { hex: 'var(--rank-3, #a78bfa)', bg: 'var(--rank-3-bg, rgba(167,139,250,.15))', border: 'var(--rank-3-border, rgba(167,139,250,.4))'  },
    4: { hex: 'var(--rank-4, #e879f9)', bg: 'var(--rank-4-bg, rgba(232,121,249,.15))', border: 'var(--rank-4-border, rgba(232,121,249,.4))'  },
    5: { hex: 'var(--rank-5, #fbbf24)', bg: 'var(--rank-5-bg, rgba(251,191,36,.15))',  border: 'var(--rank-5-border, rgba(251,191,36,.4))'   },
    6: { hex: 'var(--rank-6, #fbbf24)', bg: 'var(--rank-6-bg, rgba(251,191,36,.22))',  border: 'var(--rank-6-border, rgba(251,191,36,.55))'  },
  };

  var RANK_NAMES = {
    0: 'Unawakened', 1: 'Awakened', 2: 'Named',
    3: 'Evolved', 4: 'Hardened', 5: 'Transcendent', 6: 'Transcendent ★',
  };

  function levelNum(level) {
    if (!level) return 0;
    var m = String(level).match(/(\d+)/);
    return m ? parseInt(m[1], 10) : 0;
  }

  function colorFor(n) {
    return LEVEL_COLORS[n] || LEVEL_COLORS[0];
  }

  function chip(n) {
    var c = colorFor(n);
    return (
      '<span class="rank-chip" style="color:' + c.hex +
      ';background:' + c.bg + ';border:1px solid ' + c.border + '">' +
      n + '★</span>'
    );
  }

  function stars(n, max) {
    max = max || 6;
    var html = '<span class="rank-stars" title="' + (RANK_NAMES[n] || '') + '">';
    for (var i = 1; i <= max; i++) {
      html += '<span class="rank-star' + (i <= n ? ' filled' : '') + '">★</span>';
    }
    return html + '</span>';
  }

  window.rankBadge = { chip: chip, stars: stars, levelNum: levelNum, colorFor: colorFor };
})();

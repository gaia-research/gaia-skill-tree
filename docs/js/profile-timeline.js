/* profile-timeline.js — interactive vertical timeline.
 * Reads window.PROFILE_SKILLS, groups by createdAt month, renders
 * stacked skill chips with IntersectionObserver entrance animations.
 */
(function () {

  var MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

  function fmtDate(iso) {
    if (!iso) return '—';
    var d = new Date(iso + 'T00:00:00Z');
    if (isNaN(d)) return iso;
    return MONTHS[d.getUTCMonth()] + ' ' + d.getUTCFullYear();
  }

  function bucketKey(iso) {
    if (!iso) return 'unknown';
    return iso.slice(0, 7); /* YYYY-MM */
  }

  function render(container) {
    var skills = window.PROFILE_SKILLS || [];
    if (!skills.length) {
      container.innerHTML = '<p class="pt-empty">No skills recorded yet.</p>';
      return;
    }

    /* group by month bucket, sort newest first */
    var buckets = {};
    skills.forEach(function (ns) {
      var key = bucketKey(ns.createdAt);
      if (!buckets[key]) buckets[key] = [];
      buckets[key].push(ns);
    });

    var keys = Object.keys(buckets).sort().reverse();

    /* spine */
    var html = '<div class="pt-spine"></div>';

    keys.forEach(function (key, idx) {
      var group = buckets[key];
      /* sort within bucket: highest rank first */
      group.sort(function (a, b) {
        return parseInt(b.levelNum || b.level || 0, 10) - parseInt(a.levelNum || a.level || 0, 10);
      });

      var chips = group.map(function (ns) {
        var n    = parseInt(ns.levelNum || ns.level || 0, 10);
        var typ  = ns.type || 'basic';
        var col  = TYPE_COLORS[typ] || TYPE_COLORS.basic;
        var star = n ? ' <span class="pt-chip-star">' + n + '★</span>' : '';
        var name = ns.name || String(ns.id || '').split('/').pop();
        var tip  = [name, ns.level, typ.charAt(0).toUpperCase() + typ.slice(1)].filter(Boolean).join(' · ');
        return (
          '<span class="pt-chip" data-type="' + typ + '" data-tooltip="' + tip + '">' +
          name + star + '</span>'
        );
      }).join('');

      html += (
        '<div class="pt-row" style="transition-delay:' + (idx * 55) + 'ms">' +
        '<span class="pt-date">' + fmtDate(key + '-01') + '</span>' +
        '<div class="pt-chips">' + chips + '</div>' +
        '</div>'
      );
    });

    container.innerHTML = html;

    /* IntersectionObserver entrance */
    if ('IntersectionObserver' in window) {
      var rows = container.querySelectorAll('.pt-row');
      var obs  = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.classList.add('visible');
            obs.unobserve(e.target);
          }
        });
      }, { threshold: 0.15 });
      rows.forEach(function (r) { obs.observe(r); });
    } else {
      /* fallback: show all immediately */
      container.querySelectorAll('.pt-row').forEach(function (r) {
        r.classList.add('visible');
      });
    }
  }

  function init() {
    var container = document.getElementById('profile-timeline');
    if (container) render(container);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

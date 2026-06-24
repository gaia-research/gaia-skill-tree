// <field-view-url-params>
//   ?field=1   — preferred. Opens the page directly into fullscreen
//                graph mode (interactive canvas, labels, full controls).
//   ?hud=1     — legacy alias. Same behaviour as ?field=1.
// </field-view-url-params>
//
// The Field view button has two interaction modes:
//   HOVER → field view (hero-hud-mode): remove glass blur so the
//           ambient canvas shows through, dimming hero text.
//   CLICK → fullscreen graph: enter interactive fullscreen mode via
//           the Graph (3D) trigger (same as the nav button).
(function () {
  'use strict';

  function paramOn(params, key) {
    if (!params.has(key)) return false;
    var v = (params.get(key) || '').toLowerCase();
    return v === '1' || v === 'true' || v === 'on' || v === '';
  }

  function init() {
    var hero = document.getElementById('hero');
    var btn = document.getElementById('hudToggleBtn');
    if (!hero || !btn) return;

    var isMobile = window.matchMedia('(max-width:700px)').matches;

    // ── HOVER: toggle field view (glass-off peek) — desktop only ──
    if (!isMobile) {
      btn.addEventListener('mouseenter', function () {
        hero.classList.add('hero-hud-mode');
      });
      btn.addEventListener('mouseleave', function () {
        hero.classList.remove('hero-hud-mode');
      });
    }

    // ── CLICK: open fullscreen graph mode ──
    btn.addEventListener('click', function () {
      hero.classList.remove('hero-hud-mode');
      var trigger = document.querySelector('[data-graph-trigger]');
      if (trigger) trigger.click();
    });

    // ── URL param auto-open ──
    try {
      var params = new URLSearchParams(window.location.search);
      if (paramOn(params, 'field') || paramOn(params, 'hud')) {
        setTimeout(function () {
          var trigger = document.querySelector('[data-graph-trigger]');
          if (trigger) trigger.click();
        }, 800);
      }
      if (paramOn(params, 'tree')) {
        setTimeout(function () {
          var treeBtn = document.getElementById('treeNavBtn');
          if (treeBtn) treeBtn.click();
        }, 800);
      }
    } catch (_) { /* ignore */ }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

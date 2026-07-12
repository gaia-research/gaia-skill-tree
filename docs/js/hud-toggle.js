// <world-tree-url-params>
//   ?tree=1    — canonical. Opens the interactive 3D World Tree explorer.
//   ?field=1   — deprecated compatibility alias for ?tree=1.
//   ?hud=1     — deprecated compatibility alias for ?tree=1.
// </world-tree-url-params>
//
// This file is intentionally a thin compatibility adapter. The renderer and
// lifecycle live in skill-graph.js behind window.gaiaWorldTree.
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

    function openWorldTree() {
      if (window.gaiaWorldTree && typeof window.gaiaWorldTree.open === 'function') {
        window.gaiaWorldTree.open();
        return;
      }
      // Defensive fallback for a stale cached skill-graph.js.
      var trigger = document.querySelector('[data-graph-trigger]');
      if (trigger && trigger !== btn) trigger.click();
    }

    btn.addEventListener('click', function () {
      openWorldTree();
    });

    // The supplied gold-tree plate is a flat reference surface. Give it a
    // restrained pointer parallax in the editorial hero only; the live canvas
    // stays independently projected and becomes the sole interactive object
    // in Tree Explorer. One rAF write per frame avoids pointer-event churn.
    var finePointer = window.matchMedia && window.matchMedia('(pointer: fine)').matches;
    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (finePointer && !reduceMotion) {
      var parallaxFrame = 0;
      var parallaxX = 0;
      var parallaxY = 0;
      var paintParallax = function () {
        parallaxFrame = 0;
        hero.style.setProperty('--hero-tree-parallax-x', parallaxX.toFixed(2) + 'px');
        hero.style.setProperty('--hero-tree-parallax-y', parallaxY.toFixed(2) + 'px');
      };
      hero.addEventListener('pointerenter', function () {
        if (hero.dataset.treeState === 'hero2d') hero.dataset.treeParallax = 'active';
      }, { passive: true });
      hero.addEventListener('pointermove', function (event) {
        if (hero.dataset.treeState !== 'hero2d') return;
        var rect = hero.getBoundingClientRect();
        parallaxX = ((event.clientX - rect.left) / Math.max(1, rect.width) - 0.5) * 12;
        parallaxY = ((event.clientY - rect.top) / Math.max(1, rect.height) - 0.5) * 8;
        if (!parallaxFrame) parallaxFrame = window.requestAnimationFrame(paintParallax);
      }, { passive: true });
      hero.addEventListener('pointerleave', function () {
        delete hero.dataset.treeParallax;
        parallaxX = 0;
        parallaxY = 0;
        if (!parallaxFrame) parallaxFrame = window.requestAnimationFrame(paintParallax);
      }, { passive: true });
    }

    // Canonical and legacy URL parameters all enter the same tree explorer.
    try {
      var params = new URLSearchParams(window.location.search);
      if (paramOn(params, 'tree') || paramOn(params, 'field') || paramOn(params, 'hud')) {
        setTimeout(function () {
          openWorldTree();
        }, 0);
      }
    } catch (_) { /* ignore */ }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

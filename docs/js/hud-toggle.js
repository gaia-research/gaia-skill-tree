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

    // The supplied gold-tree plate and the live canvas are two layers of one
    // tree. Give them a shared VERTICAL scroll parallax so the whole tree
    // sticks together and drifts as the page scrolls — never a pointer/hover
    // parallax (that decoupled the plate from the canvas and reacted to the
    // mouse, which the design explicitly rejects). Both layers read the same
    // --hero-tree-parallax-y var (see world-tree-hero.css), so they move as one.
    // One rAF write per scroll frame; disabled under reduced-motion.
    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!reduceMotion) {
      // Depth factor: the tree travels a fraction of the scroll distance, so it
      // lags the page and reads as behind-glass parallax. Negative sign lifts
      // the tree as you scroll down (crown rises out of view last).
      var PARALLAX_DEPTH = -0.08;
      var PARALLAX_MAX = 64; // px clamp so the tree never drifts off its frame
      var parallaxFrame = 0;
      var paintParallax = function () {
        parallaxFrame = 0;
        if (hero.dataset.treeState !== 'hero2d') {
          hero.style.setProperty('--hero-tree-parallax-y', '0px');
          return;
        }
        var rect = hero.getBoundingClientRect();
        // Progress of the hero through the viewport: 0 when its top is at the
        // top of the screen, growing as it scrolls up and out.
        var travel = -rect.top * PARALLAX_DEPTH;
        if (travel > PARALLAX_MAX) travel = PARALLAX_MAX;
        else if (travel < -PARALLAX_MAX) travel = -PARALLAX_MAX;
        hero.dataset.treeParallax = 'active';
        hero.style.setProperty('--hero-tree-parallax-y', travel.toFixed(2) + 'px');
      };
      var onScroll = function () {
        if (!parallaxFrame) parallaxFrame = window.requestAnimationFrame(paintParallax);
      };
      window.addEventListener('scroll', onScroll, { passive: true });
      window.addEventListener('resize', onScroll, { passive: true });
      // Prime once so the shift is applied before the first scroll.
      onScroll();
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

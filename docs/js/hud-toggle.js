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

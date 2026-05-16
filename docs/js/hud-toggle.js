// <field-view-url-params>
//   ?field=1   — preferred. Opens the page directly into Field view
//                (full-viewport overlay; chrome dimmed under the canvas).
//   ?hud=1     — legacy alias. Same behaviour as ?field=1; kept so old
//                shareables don't 404. Drop in Stage 7+ once analytics
//                show zero traffic on it.
// Either param sets aria-pressed="true" on the toggle button and
// adds the .hero-hud-mode class to #hero on first paint.
// </field-view-url-params>
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

    var on = false;
    try {
      var params = new URLSearchParams(window.location.search);
      if (paramOn(params, 'field') || paramOn(params, 'hud')) {
        on = true;
        hero.classList.add('hero-hud-mode');
        btn.setAttribute('aria-pressed', 'true');
        btn.textContent = '⇄ Exit field';
      }
    } catch (_) { /* ignore — non-browser env */ }

    btn.addEventListener('click', function () {
      on = !on;
      hero.classList.toggle('hero-hud-mode', on);
      btn.setAttribute('aria-pressed', String(on));
      btn.textContent = on ? '⇄ Exit field' : '⇄ Field view';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

(function () {
  'use strict';

  function init() {
    var hero = document.getElementById('hero');
    var btn = document.getElementById('hudToggleBtn');
    if (!hero || !btn) return;

    var on = false;
    btn.addEventListener('click', function () {
      on = !on;
      hero.classList.toggle('hero-hud-mode', on);
      btn.setAttribute('aria-pressed', String(on));
      btn.textContent = on ? '⇄ Exit HUD' : '⇄ View as HUD';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

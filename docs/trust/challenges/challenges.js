/*
 * /trust/challenges/challenges.js
 *
 * Reads the two public challenge artifacts and renders them with
 * GaiaChallenges (docs/js/challenge-surfaces.js). Fails closed: a load or
 * contract failure shows a quiet statement and no challenge.
 */
(function () {
  'use strict';

  var ROOT = '../../';
  var admitted = document.getElementById('csAdmittedList');
  var held = document.getElementById('csHeldList');
  var tipMount = document.getElementById('csAdmittedTip');
  var main = document.getElementById('csMain');

  function scrollToHash() {
    var raw = window.location.hash ? window.location.hash.slice(1) : '';
    if (!raw) return;
    var id;
    try { id = decodeURIComponent(raw); } catch (e) { return; }
    var target = document.getElementById(id);
    if (target && typeof target.scrollIntoView === 'function') target.scrollIntoView();
  }

  if (!window.GaiaChallenges || !window.GaiaTrustLifecycle) {
    if (admitted) admitted.innerHTML = '<p class="cs-empty" data-state="failed">The challenge projection could not be loaded, so nothing is shown here.</p>';
    if (held) held.innerHTML = '<p class="cs-empty" data-state="failed">The held reviews could not be loaded.</p>';
    return;
  }

  window.GaiaChallenges.load(ROOT + 'api/v1/', window.GAIA_VERSION).then(function (data) {
    window.GaiaChallenges.renderPage({ admitted: admitted, held: held }, data,
      { root: ROOT, bindTipsOn: main });
    if (data.projection.status === 'verified' && tipMount) {
      tipMount.innerHTML = window.GaiaChallenges.contestedTip();
      window.GaiaTrustLifecycle.components.bindTips(main);
    }
    scrollToHash();
  });
})();

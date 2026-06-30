/**
 * hero-share.js — Share button wiring for the Hall of Heroes gallery.
 * Delegates to openHohFullscreenModal (from hoh-modal.js) with the
 * correct skill metadata. Also adds "scroll to stage" on modal close.
 *
 * Load AFTER hoh-modal.js and heroes.js.
 */
(function () {
  'use strict';

  // ── Delegated click handler for .hero-card__share buttons ─────
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.hero-card__share');
    if (!btn) return;
    e.stopPropagation();

    var handle = btn.getAttribute('data-share-handle') || '';
    var skillId = btn.getAttribute('data-share-skill') || '';
    var slug = skillId.split('/').pop() || handle;

    // Attempt to find the named skill in window._gaiaNamedAll (populated
    // by other pages). For heroes/, we build the ns object from the DOM +
    // known data.
    var stage = btn.closest('.hero-stage');
    var ns = {
      id: skillId,
      contributor: handle,
      name: slug,
      level: '',
      type: 'ultimate',
      origin: true,
      ogPath: 'og/' + handle + '/' + slug + '.svg',
      description: '',
      tags: []
    };

    // Extract level from the stats display if available
    if (stage) {
      var statValues = stage.querySelectorAll('.hero-card__stat-value');
      if (statValues.length >= 2) {
        ns.level = statValues[1].textContent.trim();
      }
      // Determine type from stage class
      if (stage.classList.contains('hero-stage--unique')) {
        ns.type = 'unique';
      } else if (stage.classList.contains('hero-stage--named')) {
        ns.type = 'basic';
      } else if (stage.classList.contains('hero-stage--apex')) {
        ns.type = 'extra';
      }
    }

    // Open the share modal
    if (typeof window.openHohFullscreenModal === 'function') {
      window.openHohFullscreenModal(ns);
    }
  });

  // ── "View in Gallery" scroll-to-stage on modal close ──────────
  // After the modal closes, if the user came from a specific hero stage,
  // smoothly scroll it into view so they don't lose context.
  var lastShareStage = null;

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.hero-card__share');
    if (btn) {
      lastShareStage = btn.closest('.hero-stage');
    }
  });

  // Observe modal close (watch for is-active class removal)
  var modal = document.getElementById('hohFullscreenModal');
  if (modal && typeof MutationObserver !== 'undefined') {
    var obs = new MutationObserver(function (mutations) {
      mutations.forEach(function (m) {
        if (m.attributeName === 'aria-hidden') {
          var hidden = modal.getAttribute('aria-hidden') === 'true';
          if (hidden && lastShareStage) {
            // Brief delay to let the modal exit transition finish
            setTimeout(function () {
              if (lastShareStage && lastShareStage.offsetParent !== null) {
                lastShareStage.scrollIntoView({ behavior: 'smooth', block: 'center' });
              }
              lastShareStage = null;
            }, 300);
          }
        }
      });
    });
    obs.observe(modal, { attributes: true, attributeFilter: ['aria-hidden'] });
  }
})();

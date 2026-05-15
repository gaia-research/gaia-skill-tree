/* ============================================================
   plaque-reveal.js — Hunter's Atlas Naming Reveal Animation
   Phase 4 — SVG + CSS animation, no Lottie dependency
   ============================================================ */

(function () {
  'use strict';

  /* ── Shared data registry (populated by named-skills.js / page-ia.js) ── */
  var _namedByIdCache = null;

  function getNamedById() {
    if (_namedByIdCache) return _namedByIdCache;
    _namedByIdCache = {};
    // named-skills.js exposes buckets as window._gaiaNamedBuckets
    var source = window._gaiaNamedBuckets || null;
    if (!source) return _namedByIdCache;
    Object.keys(source).forEach(function (bucket) {
      (source[bucket] || []).forEach(function (entry) {
        _namedByIdCache[entry.id] = entry;
      });
    });
    return _namedByIdCache;
  }

  /* ── Helpers ── */

  function esc(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function levelNum(lvl) {
    if (!lvl) return 0;
    var n = parseInt(String(lvl).replace(/[^\d]/g, ''));
    return isNaN(n) ? 0 : n;
  }

  function buildStars(level) {
    var n = levelNum(level);
    var maxStars = 6;
    var html = '';
    for (var i = 1; i <= maxStars; i++) {
      html += '<span class="plaque-star' + (i > n ? ' plaque-star--dim' : '') +
              '" data-star-idx="' + i + '">★</span>';
    }
    return html;
  }

  function tierGlyph(level) {
    var n = levelNum(level);
    if (n >= 6) return '◆';
    if (n >= 4) return '◇';
    return '○';
  }

  function evidenceClass(level) {
    var n = levelNum(level);
    if (n >= 6) return 'CLASS A';
    if (n >= 5) return 'CLASS A';
    if (n >= 4) return 'CLASS A';
    if (n >= 3) return 'CLASS B';
    if (n >= 2) return 'CLASS C';
    return 'AWAITED';
  }

  /* ── Diamond Seal SVG ── */
  var SEAL_SVG = '<svg class="plaque-seal" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" aria-hidden="true">' +
    '<path d="M 32 4 L 60 32 L 32 60 L 4 32 Z" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="miter"/>' +
    '<text x="32" y="34" font-family="EB Garamond,Georgia,serif" font-weight="600" font-size="28" fill="currentColor" text-anchor="middle" dominant-baseline="central">G</text>' +
    '</svg>';

  /* ── Build plaque HTML ── */
  function buildPlaqueHTML(skillData, opts) {
    opts = opts || {};
    var settled = opts.settled || false;
    var isApex = levelNum(skillData.level) >= 6;
    var classes = 'plaque' + (isApex ? ' plaque--apex-vi' : '') + (settled ? ' plaque--settled' : '');

    return '<div class="' + classes + '" data-skill-id="' + esc(skillData.id) + '">' +
      // Header row: seal + skill name + tier glyph
      '<div class="plaque-header">' +
        SEAL_SVG +
        '<div class="plaque-skill-name ' + (settled ? '' : 'plaque-skill-name--animate') + '">' +
          esc(skillData.name || skillData.id) +
        '</div>' +
        '<div class="plaque-tier">' + tierGlyph(skillData.level) + '</div>' +
      '</div>' +
      // Contributor
      '<div class="plaque-contributor ' + (settled ? '' : 'plaque-contributor--animate') + '">' +
        esc(skillData.contributor || '') +
      '</div>' +
      // Title (italic subtitle)
      (skillData.title
        ? '<div class="plaque-title">' + esc(skillData.title) + '</div>'
        : '') +
      // Stars
      '<div class="plaque-stars">' + buildStars(skillData.level) + '</div>' +
      // Divider
      '<div class="plaque-divider"></div>' +
      // Description
      (skillData.description
        ? '<p class="plaque-description">' + esc(skillData.description) + '</p>'
        : '') +
      // Tags
      (skillData.tags && skillData.tags.length
        ? '<div class="plaque-tags">' +
            skillData.tags.slice(0, 5).map(function (t) {
              return '<span class="plaque-tag">' + esc(t) + '</span>';
            }).join('') +
          '</div>'
        : '') +
      // Evidence chip
      '<div class="plaque-evidence ' + (settled ? '' : 'plaque-evidence--animate') + '">' +
        evidenceClass(skillData.level) +
      '</div>' +
      // Underline
      '<div class="plaque-underline' + (settled ? ' plaque-underline--settled' : '') + '"></div>' +
    '</div>';
  }

  /* ── prefersReducedMotion ── */
  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  /* ── Orchestrate the 4-second cinematic ── */
  function runRevealAnimation(overlay, plaqueEl, skillData) {
    if (prefersReducedMotion()) {
      // Instant settle
      overlay.classList.add('active', 'settled');
      plaqueEl.style.opacity = '1';
      plaqueEl.style.transform = 'translateY(0)';
      // Show all elements immediately
      plaqueEl.querySelectorAll('.plaque-skill-name--animate, .plaque-tier, .plaque-contributor--animate, .plaque-star, .plaque-evidence--animate').forEach(function (el) {
        el.style.opacity = '1';
        el.style.filter = 'none';
        el.style.transform = 'none';
      });
      plaqueEl.querySelector('.plaque-underline') && (function (ul) {
        ul.classList.add('plaque-underline--settled');
      })(plaqueEl.querySelector('.plaque-underline'));
      return;
    }

    var isApex = levelNum(skillData.level) >= 6;

    // Hide animated elements initially
    var skillName = plaqueEl.querySelector('.plaque-skill-name--animate');
    var tierGlyphEl = plaqueEl.querySelector('.plaque-tier');
    var contributor = plaqueEl.querySelector('.plaque-contributor--animate');
    var stars = plaqueEl.querySelectorAll('.plaque-star');
    var evidence = plaqueEl.querySelector('.plaque-evidence--animate');
    var underline = plaqueEl.querySelector('.plaque-underline');

    [skillName, tierGlyphEl, contributor, evidence].forEach(function (el) {
      if (el) { el.style.opacity = '0'; }
    });
    stars.forEach(function (s) { s.style.opacity = '0'; s.style.transform = 'scale(0.4) rotate(-20deg)'; });
    if (underline) { underline.style.opacity = '0'; underline.style.transform = 'scaleX(0)'; }

    // t=0.0 — overlay fades in
    requestAnimationFrame(function () {
      overlay.classList.add('active');

      // t=0.8s — plaque emerges
      setTimeout(function () {
        plaqueEl.style.animation = 'plaque-emerge 0.55s cubic-bezier(0.2, 0.8, 0.2, 1) forwards';

        // t=1.4s — skill name + tier glyph ink pour
        setTimeout(function () {
          if (skillName) {
            skillName.style.animation = 'ink-pour 0.7s ease-out forwards';
          }
          if (tierGlyphEl) {
            tierGlyphEl.style.animation = 'ink-pour 0.7s ease-out 0.12s forwards';
          }

          // t=2.4s — contributor handle resolves
          setTimeout(function () {
            if (contributor) {
              contributor.style.animation = 'contributor-resolve 0.45s ease-out forwards';
            }

            // t=2.8s — stars ignite one by one
            setTimeout(function () {
              stars.forEach(function (star, i) {
                setTimeout(function () {
                  star.style.animation = 'star-ignite 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) forwards';
                }, i * 80);
              });

              // t=3.4s — evidence stamp
              setTimeout(function () {
                if (evidence) {
                  evidence.style.animation = 'evidence-stamp 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards';
                }

                // t=4.0s — settle: underline pulses, apex shimmer fires
                setTimeout(function () {
                  overlay.classList.add('settled');
                  if (underline) {
                    underline.style.animation = 'underline-pulse 0.8s ease-out forwards';
                    underline.style.opacity = '0.5';
                    underline.style.transform = 'scaleX(1)';
                  }
                  if (isApex) {
                    plaqueEl.classList.add('plaque--apex-vi');
                  }
                }, 600); // t=4.0s from star start (600ms offset)
              }, 600); // t=3.4s from contributor (600ms offset)
            }, 400); // t=2.8s from contributor resolve start
          }, 600); // 1.0s after ink-pour = t=2.4s from plaque emerge
        }, 600); // 0.6s after plaque emerge = t=1.4s total
      }, 800);
    });
  }

  /* ── Dismiss overlay ── */
  function dismissOverlay(overlay) {
    overlay.classList.remove('active', 'settled');
    setTimeout(function () {
      if (overlay.parentNode) {
        overlay.parentNode.removeChild(overlay);
      }
    }, 350);
  }

  /* ── Main exported function ── */
  function triggerPlaqueReveal(skillId) {
    // Get skill data
    var namedMap = getNamedById();
    var skillData = namedMap[skillId];

    if (!skillData) {
      // Fallback: try window._gaiaNamedBuckets directly (in case cache was empty at call time)
      var buckets = window._gaiaNamedBuckets || {};
      var found = null;
      Object.keys(buckets).some(function (bucket) {
        return (buckets[bucket] || []).some(function (e) {
          if (e.id === skillId) { found = e; return true; }
          return false;
        });
      });
      skillData = found;
    }

    if (!skillData) {
      // Minimal fallback with just the ID
      skillData = {
        id: skillId,
        name: skillId.split('/').pop().replace(/-/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); }),
        contributor: skillId.split('/')[0] || '',
        level: '2★'
      };
    }

    // Build overlay
    var overlay = document.createElement('div');
    overlay.className = 'plaque-reveal-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', 'Skill naming reveal: ' + (skillData.name || skillId));

    // Close button
    var closeBtn = document.createElement('button');
    closeBtn.className = 'plaque-reveal-close';
    closeBtn.setAttribute('aria-label', 'Close reveal');
    closeBtn.textContent = '✕';
    overlay.appendChild(closeBtn);

    // Plaque
    overlay.insertAdjacentHTML('beforeend', buildPlaqueHTML(skillData, { settled: false }));

    var plaqueEl = overlay.querySelector('.plaque');

    document.body.appendChild(overlay);

    // Wire dismiss
    function dismiss() { dismissOverlay(overlay); }
    closeBtn.addEventListener('click', dismiss);
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) dismiss();
    });
    document.addEventListener('keydown', function onEsc(e) {
      if (e.key === 'Escape') {
        dismiss();
        document.removeEventListener('keydown', onEsc);
      }
    });

    // Run animation
    runRevealAnimation(overlay, plaqueEl, skillData);
  }

  /* ── Build a settled plaque element (for profile pages / static use) ── */
  function buildSettledPlaque(skillData) {
    var wrapper = document.createElement('div');
    wrapper.innerHTML = buildPlaqueHTML(skillData, { settled: true });
    return wrapper.firstElementChild;
  }

  /* ── Wire HoH hover triggers with 200ms delay ── */
  function wireHallOfHeroesHover() {
    var hohContainer = document.getElementById('hohPlates');
    if (!hohContainer) return;

    var hoverTimer = null;

    hohContainer.addEventListener('mouseover', function (e) {
      var plate = e.target.closest('[data-skill-id]');
      if (!plate) return;
      var skillId = plate.getAttribute('data-skill-id');
      if (!skillId) return;
      clearTimeout(hoverTimer);
      hoverTimer = setTimeout(function () {
        triggerPlaqueReveal(skillId);
      }, 200);
    });

    hohContainer.addEventListener('mouseout', function (e) {
      clearTimeout(hoverTimer);
    });
  }

  /* ── Expose globally ── */
  window.triggerPlaqueReveal = triggerPlaqueReveal;
  window.buildSettledPlaque = buildSettledPlaque;

  /* ── Initialise on DOM ready ── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireHallOfHeroesHover);
  } else {
    wireHallOfHeroesHover();
  }

  // Also re-wire after page-ia.js populates the HoH plates
  // (page-ia.js runs after scripts load, so data may arrive async)
  var _hohObserver = null;
  function observeHoHPlates() {
    var hohContainer = document.getElementById('hohPlates');
    if (!hohContainer) return;
    if (_hohObserver) return;
    _hohObserver = new MutationObserver(function () {
      wireHallOfHeroesHover();
    });
    _hohObserver.observe(hohContainer, { childList: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', observeHoHPlates);
  } else {
    observeHoHPlates();
  }

})();

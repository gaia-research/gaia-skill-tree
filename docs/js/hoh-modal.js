/**
 * hoh-modal.js
 * Controls the premium fullscreen modal for Hall of Heroes mini-plaques.
 * Vanilla JS, no dependencies, IIFE-wrapped.
 */
(function () {
  'use strict';

  var toastTimer = null;
  var lastFocused = null;
  var inertedSiblings = [];
  var trapKeydownHandler = null;

  // Lazy registry cache — mirrors how badges/index.html fetches registry.json
  var _registryPromise = null;
  function getRegistry() {
    if (!_registryPromise) {
      _registryPromise = fetch('badges/registry.json')
        .then(function (r) { return r.ok ? r.json() : { contributors: {} }; })
        .catch(function () { return { contributors: {} }; });
    }
    return _registryPromise;
  }
  function firstApprovedRepo(registry, handle) {
    var entry = registry && registry.contributors && registry.contributors[handle];
    return (entry && entry.repos && entry.repos[0]) || null;
  }

  var FOCUSABLE_SELECTOR = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
    '[contenteditable]'
  ].join(',');

  function getFocusable(container) {
    if (!container) return [];
    var nodes = container.querySelectorAll(FOCUSABLE_SELECTOR);
    var out = [];
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      // Skip hidden / disabled / aria-hidden
      if (n.disabled) continue;
      if (n.getAttribute && n.getAttribute('aria-hidden') === 'true') continue;
      if (n.offsetParent === null && n.tagName !== 'AREA') continue;
      out.push(n);
    }
    return out;
  }

  function focusFirstFocusable(modalEl) {
    var focusables = getFocusable(modalEl);
    if (focusables.length) {
      try { focusables[0].focus(); } catch (_e) {}
    } else {
      // Fall back to modal itself
      try {
        modalEl.setAttribute('tabindex', '-1');
        modalEl.focus();
      } catch (_e) {}
    }
  }

  function buildTrapHandler(modalEl) {
    return function (e) {
      if (e.key !== 'Tab') return;
      var focusables = getFocusable(modalEl);
      if (!focusables.length) {
        e.preventDefault();
        return;
      }
      var first = focusables[0];
      var last = focusables[focusables.length - 1];
      var active = document.activeElement;
      if (e.shiftKey) {
        if (active === first || !modalEl.contains(active)) {
          e.preventDefault();
          try { last.focus(); } catch (_e) {}
        }
      } else {
        if (active === last || !modalEl.contains(active)) {
          e.preventDefault();
          try { first.focus(); } catch (_e) {}
        }
      }
    };
  }

  function activateInertSiblings(modalEl) {
    inertedSiblings = [];
    var children = document.body.children;
    for (var i = 0; i < children.length; i++) {
      var el = children[i];
      if (el === modalEl) continue;
      // Only flip elements we didn't already mark inert
      if (!el.inert) {
        el.inert = true;
        inertedSiblings.push(el);
      }
    }
  }

  function deactivateInertSiblings() {
    for (var i = 0; i < inertedSiblings.length; i++) {
      try { inertedSiblings[i].inert = false; } catch (_e) {}
    }
    inertedSiblings = [];
  }

  function showToast(message) {
    var toast = document.getElementById('hohFsToast');
    if (!toast) return;
    if (toastTimer) {
      clearTimeout(toastTimer);
    }
    toast.textContent = message;
    toast.classList.add('is-active');
    toastTimer = setTimeout(function () {
      toast.classList.remove('is-active');
      toastTimer = null;
    }, 3000);
  }

  function showCopySuccess(btn) {
    btn.classList.add('copied');
    var originalHtml = btn.innerHTML;
    btn.innerHTML = '<svg class="ico" width="12" height="12" aria-hidden="true"><use href="assets/icons.svg#check"></use></svg> Copied!';
    setTimeout(function () {
      btn.classList.remove('copied');
      btn.innerHTML = originalHtml;
    }, 1800);
  }

  function closeHohFullscreenModal() {
    var modal = document.getElementById('hohFullscreenModal');
    if (modal) {
      modal.classList.remove('is-active');
      modal.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
      document.documentElement.style.overflow = '';

      // Revert inert flags on body siblings we marked
      deactivateInertSiblings();

      // Remove focus-trap keydown listener
      if (trapKeydownHandler) {
        modal.removeEventListener('keydown', trapKeydownHandler);
        trapKeydownHandler = null;
      }

      // Restore focus to the element that opened the modal
      if (lastFocused && document.contains(lastFocused) && typeof lastFocused.focus === 'function') {
        try { lastFocused.focus(); } catch (_e) {}
      }
      lastFocused = null;
    }
  }

  function openHohFullscreenModal(ns) {
    var modal = document.getElementById('hohFullscreenModal');
    if (!modal) return;

    // Center Stage: render large --og plaque
    var stage = document.getElementById('hohFsStage');
    if (stage && window.plaque && typeof window.plaque.renderOg === 'function') {
      var ogNs = {
        id: ns.id,
        name: ns.name,
        contributor: ns.contributor,
        origin: ns.origin,
        level: ns.level,
        type: ns.type,
        description: ns.description,
        tags: ns.tags
      };
      // renderOg sanitizes all interpolated values via escapeHtml; safe by construction. CodeQL alert dismissed.
      stage.innerHTML = window.plaque.renderOg(ogNs);
    }

    // Set dynamic handle texts
    var handleText = document.getElementById('hohFsHandleText');
    if (handleText) {
      handleText.textContent = '@' + ns.contributor;
    }

    // Load dynamic handle README badge + markdown (with ?repo= if available)
    var badgePreview = document.getElementById('hohFsBadgePreview');
    var codeBlock = document.getElementById('hohFsCodeBlock');
    var copyBtn = document.getElementById('hohFsCopyBtn');
    var badgesLink = document.getElementById('hohFsBadgesLink');

    var badgeBase = 'https://gaia.tiongson.co/badges/' + ns.contributor + '/handle.svg';
    var profileUrl = 'https://gaia.tiongson.co/u/' + ns.contributor + '/';

    // Set immediately without ?repo= so the badge shows right away, then
    // update both src and markdown once the registry resolves.
    if (badgePreview) {
      badgePreview.alt = '@' + ns.contributor + ' on Gaia';
      badgePreview.src = 'badges/' + encodeURIComponent(ns.contributor) + '/handle.svg';
    }
    var markdown = '[![Gaia](' + badgeBase + ')](' + profileUrl + ')';
    if (codeBlock) codeBlock.textContent = markdown;
    if (badgesLink) badgesLink.href = 'badges/?u=' + encodeURIComponent(ns.contributor);

    getRegistry().then(function (registry) {
      var repo = firstApprovedRepo(registry, ns.contributor);
      if (repo) {
        var q = '?repo=' + encodeURIComponent(repo);
        if (badgePreview) {
          badgePreview.src = 'badges/' + encodeURIComponent(ns.contributor) + '/handle.svg' + q;
        }
        markdown = '[![Gaia](' + badgeBase + q + ')](' + profileUrl + ')';
        if (codeBlock) codeBlock.textContent = markdown;
      }
      // Re-wire copy button with the (possibly updated) markdown value
      if (copyBtn) {
        copyBtn.onclick = function () {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(markdown).then(function () {
              showCopySuccess(copyBtn);
            });
          } else {
            try {
              var ta = document.createElement('textarea');
              ta.value = markdown;
              ta.style.position = 'fixed';
              ta.style.opacity = '0';
              document.body.appendChild(ta);
              ta.focus();
              ta.select();
              var ok = document.execCommand('copy');
              document.body.removeChild(ta);
              if (ok) { showCopySuccess(copyBtn); }
              else { showToast('Copy failed — please manually copy the markdown block.'); }
            } catch (_e) {
              showToast('Copy failed — please manually copy the markdown block.');
            }
          }
        };
      }
    });

    // Dynamic Permalinks & URLs
    var permalink = 'https://gaia.tiongson.co/u/' + ns.contributor + '/#' + ns.id.replace('/', '-');
    var fullOgUrl = 'https://gaia.tiongson.co/' + ns.ogPath;

    // Action: Download
    var downloadBtn = modal.querySelector('[data-fs-action="download"]');
    if (downloadBtn) {
      downloadBtn.onclick = function () {
        var a = document.createElement('a');
        a.href = ns.ogPath;
        var skillIdShort = ns.id.split('/').pop();
        a.download = ns.contributor + '-' + skillIdShort + '.svg';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      };
    }

    // Action: X (Twitter)
    var xBtn = modal.querySelector('[data-fs-action="x"]');
    if (xBtn) {
      xBtn.onclick = function () {
        var tweetText = ns.name + ' · @' + ns.contributor + ' on Gaia';
        var url = 'https://twitter.com/intent/tweet?text=' +
          encodeURIComponent(tweetText) + '&url=' + encodeURIComponent(permalink);
        window.open(url, '_blank', 'noopener');
      };
    }

    // Action: Instagram
    var igBtn = modal.querySelector('[data-fs-action="instagram"]');
    if (igBtn) {
      igBtn.onclick = function () {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(fullOgUrl).then(function () {
            window.open('https://www.instagram.com/', '_blank', 'noopener');
            showToast('OG image link copied. Paste into your Instagram story or post.');
          });
        } else {
          window.open('https://www.instagram.com/', '_blank', 'noopener');
          showToast('Opening Instagram...');
        }
      };
    }

    // Action: Copy Link
    var copyLinkBtn = modal.querySelector('[data-fs-action="copy"]');
    if (copyLinkBtn) {
      copyLinkBtn.onclick = function () {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(permalink).then(function () {
            showToast('Permalink copied.');
          });
        } else {
          showToast('Copy failed. Long press link to copy.');
        }
      };
    }


    // Show the modal with transition
    modal.classList.add('is-active');
    modal.setAttribute('aria-hidden', 'false');
    modal.setAttribute('aria-modal', 'true');
    if (!modal.getAttribute('role')) {
      modal.setAttribute('role', 'dialog');
    }

    // Prevent body scroll when active
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';

    // A11y: focus trap + inert siblings
    lastFocused = document.activeElement;
    activateInertSiblings(modal);
    trapKeydownHandler = buildTrapHandler(modal);
    modal.addEventListener('keydown', trapKeydownHandler);
    // Defer focus until the modal is painted/transitioned in
    setTimeout(function () { focusFirstFocusable(modal); }, 0);
  }

  // Bootstrap Init
  function init() {
    var modal = document.getElementById('hohFullscreenModal');
    if (!modal) return;

    // Delegated click listener to catch plaque__fs-btn clicks dynamically
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.plaque__fs-btn');
      if (!btn) return;
      e.stopPropagation();
      e.preventDefault();

      var skillId = btn.getAttribute('data-skill-id');
      var handle = btn.getAttribute('data-handle');
      var name = btn.getAttribute('data-skill-name');
      var level = btn.getAttribute('data-level');
      var type = btn.getAttribute('data-type');
      var origin = btn.getAttribute('data-origin') === 'true';
      var ogPath = btn.getAttribute('data-og');
      var desc = btn.getAttribute('data-desc') || '';
      var tagsRaw = btn.getAttribute('data-tags');
      var tags = [];
      try { if (tagsRaw) tags = JSON.parse(tagsRaw); } catch(e) {}

      openHohFullscreenModal({
        id: skillId,
        contributor: handle,
        name: name,
        level: level,
        type: type,
        origin: origin,
        ogPath: ogPath,
        description: desc,
        tags: tags
      });
    });

    // Close actions
    var closeBtn = modal.querySelector('[data-fs-action="close"]');
    if (closeBtn) {
      closeBtn.addEventListener('click', closeHohFullscreenModal);
    }

    // Backdrop click close
    modal.addEventListener('click', function (e) {
      if (e.target === modal || e.target.classList.contains('hoh-fs-stage')) {
        closeHohFullscreenModal();
      }
    });

    // Global Key Bindings
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        closeHohFullscreenModal();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

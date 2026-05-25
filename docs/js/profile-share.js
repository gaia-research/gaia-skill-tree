/**
 * profile-share.js
 * Opens a share modal when a .plaque__share-btn is clicked.
 * Vanilla JS, no dependencies, IIFE-wrapped.
 */
(function () {
  'use strict';

  // Guard: prevent double-initialisation if the script is loaded more than once.
  if (window.__profileShareInit) return;
  window.__profileShareInit = true;

  // ─── State ────────────────────────────────────────────────────────────────

  var modal = null;
  var previousFocus = null;
  var toastTimer = null;

  // ─── DOM helpers ──────────────────────────────────────────────────────────

  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function qsa(selector, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(selector));
  }

  // ─── Focus trap ───────────────────────────────────────────────────────────

  function getFocusable(container) {
    return qsa(
      'a[href]:not([disabled]),button:not([disabled]),textarea:not([disabled]),' +
      'input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])',
      container
    ).filter(function (el) {
      return el.offsetParent !== null; // visible elements only
    });
  }

  function trapTab(e) {
    if (!modal || modal.hasAttribute('hidden')) return;
    var panel = qs('.share-modal__panel', modal);
    if (!panel) return;
    var focusable = getFocusable(panel);
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];

    if (e.key === 'Tab') {
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
  }

  // ─── Toast ────────────────────────────────────────────────────────────────

  function showToast(message) {
    if (!modal) return;
    var toast = qs('[data-share-toast]', modal);
    if (!toast) return;
    if (toastTimer) {
      clearTimeout(toastTimer);
      toastTimer = null;
    }
    toast.textContent = message;
    toast.removeAttribute('hidden');
    toastTimer = setTimeout(function () {
      toast.setAttribute('hidden', '');
      toastTimer = null;
    }, 3000);
  }

  // ─── Close ────────────────────────────────────────────────────────────────

  function closeShareModal() {
    if (!modal) return;
    modal.setAttribute('hidden', '');
    modal.classList.remove('share-modal--open');
    document.removeEventListener('keydown', handleKeydown);
    if (previousFocus && previousFocus.focus) {
      previousFocus.focus();
    }
    previousFocus = null;
  }

  // Exported for sample pages.
  window.closeShareModal = closeShareModal;

  // ─── Keydown handler (Escape + Tab trap) ──────────────────────────────────

  function handleKeydown(e) {
    if (e.key === 'Escape') {
      closeShareModal();
    } else if (e.key === 'Tab') {
      trapTab(e);
    }
  }

  // ─── Copy action ─────────────────────────────────────────────────────────

  function copyToClipboard(text, successMsg, failMsg) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () { showToast(successMsg); },
        function () { clipboardFallback(text, failMsg); }
      );
    } else {
      clipboardFallback(text, failMsg);
    }
  }

  function clipboardFallback(text, failMsg) {
    try {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      ta.style.pointerEvents = 'none';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      var ok = document.execCommand('copy');
      document.body.removeChild(ta);
      if (ok) {
        showToast('Permalink copied.');
      } else {
        showToast(failMsg || 'Copy failed — long-press the URL to copy: ' + text);
      }
    } catch (_e) {
      showToast(failMsg || 'Copy failed — long-press the URL to copy: ' + text);
    }
  }

  // ─── Open ─────────────────────────────────────────────────────────────────

  function openShareModal(btn) {
    if (!modal) return;

    var skillId   = btn.getAttribute('data-skill-id')   || '';
    var skillName = btn.getAttribute('data-skill-name') || '';
    var handle    = btn.getAttribute('data-handle')     || '';
    var ogPath    = btn.getAttribute('data-og')         || '';

    // Compute absolute OG URL.
    var ogUrl = ogPath;
    if (ogPath && ogPath.charAt(0) === '/') {
      ogUrl = location.origin + ogPath;
    }

    // Compute permalink.
    var base = (window.PROFILE_PERMALINK_BASE || (location.origin + location.pathname));
    var anchor = skillId.replace('/', '-');
    var permalink = base + '#' + anchor;

    // skillIdShort = the part after the first '/'.
    var slashIdx = skillId.indexOf('/');
    var skillIdShort = slashIdx !== -1 ? skillId.slice(slashIdx + 1) : skillId;

    // Update preview image.
    var preview = qs('[data-share-preview]', modal);
    if (preview) {
      preview.src = ogUrl;
      preview.alt = 'OG card for ' + skillName + ' by @' + handle;
    }

    // Update caption.
    var caption = qs('[data-share-caption]', modal);
    if (caption) {
      caption.textContent = skillName + ' · @' + handle;
    }

    // Wire download anchor.
    var downloadEl = qs('[data-share-action="download"]', modal);
    if (downloadEl) {
      downloadEl.href = ogUrl;
      downloadEl.setAttribute('download', handle + '-' + skillIdShort + '.png');
      // download anchor is same-origin — no rel="noopener" needed.
    }

    // Wire X / Twitter anchor.
    var xEl = qs('[data-share-action="x"]', modal);
    if (xEl) {
      var tweetText = skillName + ' · @' + handle + ' on Gaia';
      xEl.href = 'https://twitter.com/intent/tweet?text=' +
        encodeURIComponent(tweetText) + '&url=' + encodeURIComponent(permalink);
      // target/_blank already set in HTML; ensure rel is present.
      xEl.setAttribute('rel', 'noopener');
    }

    // Wire copy button.
    var copyBtn = qs('[data-share-action="copy"]', modal);
    if (copyBtn) {
      // Clone to remove old listeners; simpler than tracking refs.
      var copyClone = copyBtn.cloneNode(true);
      copyBtn.parentNode.replaceChild(copyClone, copyBtn);
      copyClone.addEventListener('click', function () {
        copyToClipboard(
          permalink,
          'Permalink copied.',
          'Copy failed — long-press the URL to copy: ' + permalink
        );
      });
    }

    // Wire Instagram button.
    var igBtn = qs('[data-share-action="instagram"]', modal);
    if (igBtn) {
      var igClone = igBtn.cloneNode(true);
      igBtn.parentNode.replaceChild(igClone, igBtn);
      igClone.addEventListener('click', function () {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(ogUrl).then(
            function () {
              window.open('https://www.instagram.com/', '_blank', 'noopener');
              showToast('OG image link copied. Paste into your Instagram story or post.');
            },
            function () {
              window.open('https://www.instagram.com/', '_blank', 'noopener');
              showToast('OG image link copied. Paste into your Instagram story or post.');
            }
          );
        } else {
          clipboardFallback(ogUrl, null);
          window.open('https://www.instagram.com/', '_blank', 'noopener');
          showToast('OG image link copied. Paste into your Instagram story or post.');
        }
      });
    }

    // Show the modal.
    modal.removeAttribute('hidden');
    modal.classList.add('share-modal--open');

    // Attach keydown handler.
    document.addEventListener('keydown', handleKeydown);

    // Set initial focus on the close button.
    var closeBtn = qs('.share-modal__close', modal);
    if (closeBtn) {
      closeBtn.focus();
    }
  }

  // ─── Bootstrap ────────────────────────────────────────────────────────────

  function init() {
    modal = qs('.share-modal');
    if (!modal) return; // Modal not present on this page — exit silently.

    // Bind [data-share-close] elements (backdrop + close button).
    qsa('[data-share-close]', modal).forEach(function (el) {
      el.addEventListener('click', closeShareModal);
    });

    // Bind all share trigger buttons.
    qsa('.plaque__share-btn').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation(); // Prevent parent plaque click handlers from firing.
        previousFocus = document.activeElement;
        openShareModal(btn);
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());

/**
 * hoh-modal.js
 * Controls the premium fullscreen modal for Hall of Heroes mini-plaques.
 * Vanilla JS, no dependencies, IIFE-wrapped.
 */
(function () {
  'use strict';

  var toastTimer = null;

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
        type: ns.type
      };
      stage.innerHTML = window.plaque.renderOg(ogNs);
    }

    // Set dynamic handle texts
    var handleText = document.getElementById('hohFsHandleText');
    if (handleText) {
      handleText.textContent = '@' + ns.contributor;
    }

    // Load dynamic handle README badge
    var badgePreview = document.getElementById('hohFsBadgePreview');
    if (badgePreview) {
      badgePreview.src = 'badges/' + encodeURIComponent(ns.contributor) + '/handle.svg';
    }

    // Generate markdown badge copy block
    var codeBlock = document.getElementById('hohFsCodeBlock');
    var markdown = '[![Gaia](https://gaia.tiongson.co/badges/' + ns.contributor + '/handle.svg)](https://gaia.tiongson.co/u/' + ns.contributor + '/)';
    if (codeBlock) {
      codeBlock.textContent = markdown;
    }

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
        a.download = ns.contributor + '-' + skillIdShort + '.png';
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

    // Action: Copy Markdown
    var copyBtn = document.getElementById('hohFsCopyBtn');
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
            if (ok) {
              showCopySuccess(copyBtn);
            } else {
              showToast('Copy failed — please manually copy the markdown block.');
            }
          } catch (_e) {
            showToast('Copy failed — please manually copy the markdown block.');
          }
        }
      };
    }

    // Show the modal with transition
    modal.classList.add('is-active');
    modal.setAttribute('aria-hidden', 'false');

    // Prevent body scroll when active
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';
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

      openHohFullscreenModal({
        id: skillId,
        contributor: handle,
        name: name,
        level: level,
        type: type,
        origin: origin,
        ogPath: ogPath
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

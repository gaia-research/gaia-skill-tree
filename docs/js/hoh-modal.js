/**
 * hoh-modal.js
 * Controls the premium fullscreen modal for Hall of Heroes mini-plaques.
 * Vanilla JS, no dependencies, IIFE-wrapped.
 */
(function () {
  'use strict';

  var toastTimer = null;

  function isSafeUrl(url) {
    if (!url) return false;
    var trimmed = String(url).trim();
    var lower = trimmed.toLowerCase();
    if (lower.indexOf('javascript:') === 0 || lower.indexOf('data:') === 0) {
      return false;
    }
    if (lower.indexOf('blob:') === 0) {
      return true;
    }
    var match = trimmed.match(/^([a-zA-Z][a-zA-Z0-9.+-]*):/);
    if (match) {
      var proto = match[1].toLowerCase();
      return proto === 'http' || proto === 'https';
    }
    return true;
  }
  var lastFocused = null;
  var inertedSiblings = [];
  var trapKeydownHandler = null;
  var idleTimer = null;
  var idleHandlersBound = false;

  // ── Direction A "Cinematic": rank accent resolver ────────────────
  // The ambient glow floor + card halo + action-rail tint all read the
  // CSS custom props --hoh-rk / --hoh-rk-rgb set on the modal. We resolve
  // the correct rank token NAME per level + branch (matching tokens.css and
  // the 9-variant register), then let CSS pull the -rgb companion. This keeps
  // the modal glow in lockstep with the plaque's own data-branch accent.
  function levelNum(level) {
    if (level == null) return 0;
    if (typeof level === 'number') return level | 0;
    var n = parseInt(String(level).replace(/[^\d]/g, ''), 10);
    return isNaN(n) ? 0 : Math.max(0, Math.min(6, n));
  }
  function branchFor(ns) {
    // Build-first: read the named index's ratified field; never resolve here.
    var emitted = String(ns && ns.branch || '').toLowerCase();
    return /^(standard|suite|unique)$/.test(emitted) ? emitted : 'standard';
  }
  // Returns the token STEM (e.g. 'rank-4-unique'); CSS reads var(--<stem>) and
  // var(--<stem>-rgb). Every stem below exists in tokens.css.
  function rankTokenStem(ns) {
    var n = levelNum(ns && ns.level);
    var branch = branchFor(ns);
    if (branch === 'unique') {
      // Unique ladder: 4★ violet, 5★ burnished copper, 6★ ember copper.
      if (n >= 6) return 'rank-6-unique';
      if (n >= 5) return 'rank-5-unique';
      return 'rank-4-unique';
    }
    // Suite + standard share the numeric rank tokens (0★→6★).
    return 'rank-' + n;
  }
  function applyRankAccent(modal, ns) {
    if (!modal) return;
    var stem = rankTokenStem(ns);
    modal.style.setProperty('--hoh-rk', 'var(--' + stem + ')');
    modal.style.setProperty('--hoh-rk-rgb', 'var(--' + stem + '-rgb)');
  }

  // Ensure the cinematic parallax backdrop exists. Only docs/index.html ships
  // the .hoh-fs-parallax-bg markup inline; the generated profile/named pages
  // and the hand-authored heroes page do not. Inject it once so every surface
  // gets the same full-bleed backdrop without editing 50 generated files.
  function ensureParallaxBg(modal) {
    if (!modal || modal.querySelector('.hoh-fs-parallax-bg')) return;
    var root = (typeof window.gaiaIconBase === 'function')
      ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '')
      : '';
    var bg = document.createElement('div');
    bg.className = 'hoh-fs-parallax-bg';
    bg.setAttribute('aria-hidden', 'true');
    var img = document.createElement('img');
    img.src = root + 'assets/world-tree/yggdrasil-backdrop-941.webp';
    img.alt = '';
    bg.appendChild(img);
    // Insert as the first child so it sits behind the stage/chrome.
    modal.insertBefore(bg, modal.firstChild);
  }

  // Ensure the Gaia Skill Tree brand lockup (seal + wordmark) exists on the
  // share modal. Every share surface must carry the logo + name (founder
  // directive, 2026-07-26). Injected once so all pages match without editing
  // 50 generated files; inline markup on index/heroes/generated pages is a
  // no-op here thanks to the presence guard.
  function ensureBrandLockup(modal) {
    if (!modal || modal.querySelector('.hoh-fs-brand')) return;
    var root = (typeof window.gaiaIconBase === 'function')
      ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '')
      : '';
    var brand = document.createElement('a');
    brand.className = 'hoh-fs-brand';
    var brandUrl = root + 'index.html';
    brand.href = isSafeUrl(brandUrl) ? brandUrl : '';
    brand.setAttribute('aria-label', 'Gaia Skill Tree home');

    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'hoh-fs-brand-seal');
    svg.setAttribute('viewBox', '0 0 64 64');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');

    var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M 32 4 L 60 32 L 32 60 L 4 32 Z');
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', 'currentColor');
    path.setAttribute('stroke-width', '2.5');
    path.setAttribute('stroke-linejoin', 'miter');
    svg.appendChild(path);

    var textNode = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    textNode.setAttribute('x', '32');
    textNode.setAttribute('y', '34');
    textNode.setAttribute('font-family', 'EB Garamond, Georgia, serif');
    textNode.setAttribute('font-weight', '600');
    textNode.setAttribute('font-size', '28');
    textNode.setAttribute('fill', 'currentColor');
    textNode.setAttribute('text-anchor', 'middle');
    textNode.setAttribute('dominant-baseline', 'central');
    textNode.textContent = 'G';
    svg.appendChild(textNode);

    var word = document.createElement('span');
    word.className = 'hoh-fs-brand-word';
    word.textContent = 'Gaia Skill Tree';

    brand.appendChild(svg);
    brand.appendChild(word);
    modal.appendChild(brand);
  }

  function setIdle(modal) {
    modal.classList.add('is-idle');
  }
  function wakeChrome(modal) {
    modal.classList.remove('is-idle');
    if (idleTimer) {
      clearTimeout(idleTimer);
    }
    idleTimer = setTimeout(function () { setIdle(modal); }, 2000);
  }
  function bindIdleHandlers(modal) {
    if (idleHandlersBound) return;
    idleHandlersBound = true;
    var wake = function () { wakeChrome(modal); };
    modal.addEventListener('mousemove', wake);
    modal.addEventListener('mousedown', wake);
    modal.addEventListener('keydown', wake);
    modal.addEventListener('touchstart', wake, { passive: true });

    // Premium parallax backdrop logic — translates background based on cursor offsets
    var bg = modal.querySelector('.hoh-fs-parallax-bg');
    if (bg) {
      modal.addEventListener('mousemove', function (e) {
        if (prefersReducedMotion()) return;
        var cx = window.innerWidth / 2;
        var cy = window.innerHeight / 2;
        var dx = (e.clientX - cx) / cx;
        var dy = (e.clientY - cy) / cy;
        // Shift up to 25px max based on cursor offset
        bg.style.transform = 'translate3d(' + (dx * 25) + 'px, ' + (dy * 25) + 'px, 0)';
      });
    }

    // Keep chrome visible while pointer is over an actionable region.
    modal.querySelectorAll('.hoh-fs-header, .hoh-fs-confirm, .hoh-fs-overlay').forEach(function (region) {
      region.addEventListener('mouseenter', wake);
    });
  }

  // Lazy registry cache — mirrors how badges/index.html fetches registry.json
  var _registryPromise = null;
  function getRegistry() {
    if (!_registryPromise) {
      var prefix = (typeof window.gaiaIconBase === 'function') ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '') : '';
      _registryPromise = fetch(prefix + 'badges/registry.json')
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

  function blobToDataUrl(blob) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () { resolve(String(reader.result || '')); };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  function triggerBlobDownload(blob, filename) {
    var href = URL.createObjectURL(blob);
    var anchor = document.createElement('a');
    anchor.href = isSafeUrl(href) ? href : '';
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    setTimeout(function () { URL.revokeObjectURL(href); }, 0);
  }

  function downloadStandaloneSvg(svgUrl, filename) {
    return fetch(svgUrl)
      .then(function (response) {
        if (!response.ok) throw new Error('SVG download failed');
        return response.text();
      })
      .then(function (source) {
        var doc = new DOMParser().parseFromString(source, 'image/svg+xml');
        if (!doc.documentElement || doc.querySelector('parsererror')) {
          throw new Error('Invalid SVG');
        }
        var images = Array.prototype.slice.call(doc.querySelectorAll('image'));
        return Promise.all(images.map(function (image) {
          var raw = image.getAttribute('href') ||
            image.getAttributeNS('http://www.w3.org/1999/xlink', 'href');
          if (!raw || raw.indexOf('data:') === 0) return Promise.resolve();
          var assetUrl = new URL(raw, svgUrl);
          if (assetUrl.protocol !== 'http:' && assetUrl.protocol !== 'https:') {
            return Promise.resolve();
          }
          return fetch(assetUrl.href)
            .then(function (response) {
              if (!response.ok) throw new Error('SVG asset download failed');
              return response.blob();
            })
            .then(blobToDataUrl)
            .then(function (dataUrl) {
              image.setAttribute('href', dataUrl);
              image.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', dataUrl);
            });
        })).then(function () {
          var serialized = new XMLSerializer().serializeToString(doc.documentElement);
          triggerBlobDownload(
            new Blob(['<?xml version="1.0" encoding="UTF-8"?>\n' + serialized], { type: 'image/svg+xml' }),
            filename
          );
        });
      });
  }

  function showCopySuccess(btn) {
    btn.classList.add('copied');
    var iconBase = (typeof window.gaiaIconBase === 'function')
      ? window.gaiaIconBase()
      : 'assets/icons.svg';
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'ico');
    svg.setAttribute('width', '14');
    svg.setAttribute('height', '14');
    svg.setAttribute('aria-hidden', 'true');
    var use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    use.setAttribute('href', iconBase + '#copy-check');
    svg.appendChild(use);

    var origChildren = Array.prototype.slice.call(btn.childNodes);
    btn.replaceChildren(svg);

    setTimeout(function () {
      btn.classList.remove('copied');
      btn.replaceChildren.apply(btn, origChildren);
    }, 1800);
  }

  function closeHohFullscreenModal() {
    var modal = document.getElementById('hohFullscreenModal');
    if (modal) {
      // If we're currently in native fullscreen on this modal, exit first —
      // otherwise the browser stays in fullscreen mode showing the now
      // opacity:0 / pointer-events:none modal, which reads as a blank page.
      var fsEl = document.fullscreenElement || document.webkitFullscreenElement;
      if (fsEl === modal) {
        var exit = document.exitFullscreen || document.webkitExitFullscreen;
        if (exit) {
          try {
            var p = exit.call(document);
            if (p && typeof p.then === 'function') {
              // Wait for the exit to settle before tearing the modal down so
              // the page paint order is: fullscreen exit → modal hide.
              p.then(function () { _finishClose(modal); }, function () { _finishClose(modal); });
              return;
            }
          } catch (_e) { /* fall through */ }
        }
      }
      _finishClose(modal);
    }
  }

  function _finishClose(modal) {
    modal.classList.remove('is-active');
    modal.classList.remove('is-idle');
    modal.classList.remove('is-fullscreen');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';

    if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; }

    // Re-hide the README panel + restore the confirm pill so the next open
    // always starts in the same compact state.
    var overlay = document.getElementById('hohFsOverlay');
    if (overlay) overlay.hidden = true;
    var dlPop = document.getElementById('hohDlPopover');
    if (dlPop) { dlPop.hidden = true; dlPop.classList.remove('is-open'); }
    var dlBtnClose = modal.querySelector('[data-fs-action="download"]');
    if (dlBtnClose) { dlBtnClose.setAttribute('aria-expanded','false'); dlBtnClose.classList.remove('is-active'); }
    var confirm = document.getElementById('hohFsConfirm');
    if (confirm) confirm.hidden = false;
    var restore = document.getElementById('hohFsOverlayRestore');
    if (restore) restore.hidden = true;

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

  function openHohFullscreenModal(ns) {
    var modal = document.getElementById('hohFullscreenModal');
    if (!modal) return;

    // Pre-named/demoted (≤1★) skills are not publicly named — they have no OG
    // card, badge, or shareable permalink. Refuse to open the share modal so
    // none of those handle-bearing URLs are ever constructed.
    if (ns && window.isRedacted && window.isRedacted(ns.level)) {
      showToast('This skill is not yet named — sharing unlocks at 2★.');
      return;
    }

    // Direction A: paint the modal's rank accent BEFORE the stage renders so
    // the ambient glow floor + card halo animate in already-colored.
    applyRankAccent(modal, ns);

    // Center Stage: show the build-rendered PNG. Loading an SVG through <img>
    // blocks that SVG's external WebP medallion in browsers; the generated PNG
    // is self-contained and matches the downloaded share image exactly.
    // Fall back to plaque.renderOg() when the build artifact is absent.
    var stage = document.getElementById('hohFsStage');
    if (stage) {
      var ogNs = {
        id: String(ns.id || ''),
        name: String(ns.name || ''),
        contributor: String(ns.contributor || ''),
        origin: !!ns.origin,
        level: String(ns.level || ''),
        type: String(ns.type || ''),
        branch: String(ns.branch || ''),
        rankWord: String(ns.rankWord || ''),
        description: String(ns.description || ''),
        tags: Array.isArray(ns.tags) ? ns.tags.map(function (t) { return String(t); }) : []
      };
      var renderMock = function () {
        if (window.plaque && typeof window.plaque.renderOg === 'function') {
          var mockMarkup = window.plaque.renderOg(ogNs);
          var doc = new DOMParser().parseFromString(mockMarkup, 'image/svg+xml');
          if (doc.documentElement && doc.documentElement.nodeName.toLowerCase() === 'svg') {
            stage.replaceChildren(doc.documentElement);
          }
        }
      };
      var ogPath = ns.ogPath || '';
      if (ogPath) {
        // Show mock immediately so the modal isn't blank during the fetch.
        renderMock();
        // Resolve ogPath against the docs root so it works from any sub-page.
        var docRoot = (typeof window.gaiaIconBase === 'function')
          ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '')
          : '';
        var pngPath = docRoot + ogPath.replace(/\.svg(\?.*)?$/, '.png');
        var imgEl = document.createElement('img');
        try {
          var resolvedUrl = new URL(pngPath, document.baseURI);
          var isHttp = resolvedUrl.protocol === 'https:' || resolvedUrl.protocol === 'http:';
          imgEl.src = (isHttp && isSafeUrl(resolvedUrl.href)) ? resolvedUrl.href : '';
        } catch (_e) { imgEl.src = ''; }
        imgEl.alt = ns.name || ns.id || '';
        imgEl.onload = function () { stage.replaceChildren(imgEl); };
        imgEl.onerror = function () { renderMock(); };
      } else {
        renderMock();
      }
    }

    // Set dynamic handle texts
    var handleText = document.getElementById('hohFsHandleText');
    if (handleText) {
      var cleanContrib = String(ns.contributor || '').replace(/[^a-zA-Z0-9_\-\.]/g, '');
      handleText.textContent = '@' + cleanContrib;
    }
    var disclaimer = document.getElementById('hohFsDisclaimer');
    if (disclaimer) {
      var cleanContrib = String(ns.contributor || '').replace(/[^a-zA-Z0-9_\-\.]/g, '');
      disclaimer.querySelectorAll('.hoh-fs-disclaimer-handle').forEach(function (el) {
        el.textContent = '@' + cleanContrib;
      });
    }

    // Load dynamic handle README badge + markdown (with ?repo= if available)
    var badgePreview = document.getElementById('hohFsBadgePreview');
    var codeBlock = document.getElementById('hohFsCodeBlock');
    var copyBtn = document.getElementById('hohFsCopyBtn');
    var badgesLink = document.getElementById('hohFsBadgesLink');

    var slug = ns.id ? ns.id.split('/').pop() : ns.contributor;
    var badgeBase = 'https://gaiaskilltree.com/badges/_assets/' + encodeURIComponent(ns.contributor) + '/' + encodeURIComponent(slug) + '.svg';
    var profileUrl = 'https://gaiaskilltree.com/u/' + encodeURIComponent(ns.contributor) + '/';

    // Set immediately without ?repo= so the badge shows right away, then
    // update both src and markdown once the registry resolves.
    var prefix = (typeof window.gaiaIconBase === 'function') ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '') : '';
    if (badgePreview) {
      badgePreview.alt = ns.contributor + '/' + slug + ' on Gaia';
      var previewUrl = prefix + 'badges/_assets/' + encodeURIComponent(ns.contributor) + '/' + encodeURIComponent(slug) + '.svg';
      badgePreview.src = isSafeUrl(previewUrl) ? previewUrl : '';
    }
    var markdown = '[![Gaia](' + badgeBase + ')](' + profileUrl + ')';
    if (codeBlock) codeBlock.textContent = markdown;
    if (badgesLink) {
      var targetBadgesUrl = prefix + 'badges/?u=' + encodeURIComponent(ns.contributor) + '&s=' + encodeURIComponent(slug);
      badgesLink.href = isSafeUrl(targetBadgesUrl) ? targetBadgesUrl : '';
    }

    getRegistry().then(function (registry) {
      var repo = firstApprovedRepo(registry, ns.contributor);
      if (repo) {
        var q = '?repo=' + encodeURIComponent(repo);
        if (badgePreview) {
          var previewUrlWithQ = prefix + 'badges/_assets/' + encodeURIComponent(ns.contributor) + '/' + encodeURIComponent(slug) + '.svg' + q;
          badgePreview.src = isSafeUrl(previewUrlWithQ) ? previewUrlWithQ : '';
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
    var permalink = 'https://gaiaskilltree.com/u/' + ns.contributor + '/#' + ns.id.replace('/', '-');
    var fullOgUrl = 'https://gaiaskilltree.com/' + ns.ogPath;

    // Action: Download — popover bubble with PNG / SVG choices
    var downloadBtn = modal.querySelector('[data-fs-action="download"]');
    var dlPopover   = document.getElementById('hohDlPopover');
    function closeDlPopover() {
      if (dlPopover) {
        dlPopover.hidden = true;
        dlPopover.classList.remove('is-open');
      }
      if (downloadBtn) {
        downloadBtn.setAttribute('aria-expanded', 'false');
        downloadBtn.classList.remove('is-active');
      }
    }
    if (downloadBtn && dlPopover) {
      downloadBtn.onclick = function (e) {
        e.stopPropagation();
        var open = !dlPopover.hidden;
        if (open) {
          closeDlPopover();
        } else {
          dlPopover.hidden = false;
          dlPopover.classList.add('is-open');
          downloadBtn.setAttribute('aria-expanded', 'true');
          downloadBtn.classList.add('is-active');
        }
      };
      dlPopover.querySelectorAll('[data-dl-format]').forEach(function (btn) {
        btn.onclick = function (e) {
          e.stopPropagation();
          var fmt  = btn.getAttribute('data-dl-format');
          var slug = ns.id.split('/').pop();
          var dlRoot = (typeof window.gaiaIconBase === 'function')
            ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '')
            : '';
          var href = fmt === 'png'
            ? dlRoot + 'og/' + ns.contributor + '/' + slug + '.png'
            : dlRoot + (ns.ogPath || 'og/' + ns.contributor + '/' + slug + '.svg');
          var resolvedHref = '';
          try {
            var dlUrl = new URL(href, document.baseURI);
            if (dlUrl.protocol !== 'https:' && dlUrl.protocol !== 'http:') return;
            resolvedHref = dlUrl.href;
          } catch (_e) { return; }
          closeDlPopover();
          if (fmt === 'svg') {
            showToast('Preparing self-contained SVG card…');
            downloadStandaloneSvg(resolvedHref, ns.contributor + '-' + slug + '.svg')
              .then(function () { showToast('Downloaded self-contained SVG card.'); })
              .catch(function () { showToast('SVG download failed. Please try again.'); });
            return;
          }
          var a = document.createElement('a');
          a.href = isSafeUrl(resolvedHref) ? resolvedHref : '';
          a.download = ns.contributor + '-' + slug + '.png';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          showToast('Downloading PNG card…');
        };
      });
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


    // Action: Confirm Yes — reveal the README badge panel.
    var confirmEl = document.getElementById('hohFsConfirm');
    var overlayEl = document.getElementById('hohFsOverlay');
    var restoreEl = document.getElementById('hohFsOverlayRestore');
    var yesBtn = modal.querySelector('[data-fs-action="confirm-yes"]');
    var noBtn = modal.querySelector('[data-fs-action="confirm-no"]');
    if (yesBtn) {
      yesBtn.onclick = function () {
        if (confirmEl) confirmEl.hidden = true;
        if (overlayEl) overlayEl.hidden = false;
        if (restoreEl) restoreEl.hidden = true;
        wakeChrome(modal);
      };
    }
    // Action: Confirm No — only dismiss the pill itself; keep the modal open.
    if (noBtn) {
      noBtn.onclick = function () {
        if (confirmEl) confirmEl.hidden = true;
        wakeChrome(modal);
      };
    }

    // Action: Minimize the README overlay → show the small restore chip.
    var minBtn = modal.querySelector('[data-fs-action="overlay-minimize"]');
    if (minBtn) {
      minBtn.onclick = function () {
        if (overlayEl) overlayEl.hidden = true;
        if (restoreEl) restoreEl.hidden = false;
        wakeChrome(modal);
      };
    }
    // Action: Close the README overlay outright (no restore chip).
    var ovCloseBtn = modal.querySelector('[data-fs-action="overlay-close"]');
    if (ovCloseBtn) {
      ovCloseBtn.onclick = function () {
        if (overlayEl) overlayEl.hidden = true;
        if (restoreEl) restoreEl.hidden = true;
        wakeChrome(modal);
      };
    }
    // Action: Restore — re-open the README panel from the chip.
    if (restoreEl) {
      restoreEl.onclick = function () {
        if (overlayEl) overlayEl.hidden = false;
        restoreEl.hidden = true;
        wakeChrome(modal);
      };
    }

    // Action: Fullscreen toggle — request/exit native fullscreen on the modal.
    var fsBtn = modal.querySelector('[data-fs-action="fullscreen"]');
    if (fsBtn) {
      fsBtn.onclick = function () {
        var inFs = !!(document.fullscreenElement || document.webkitFullscreenElement);
        if (inFs) {
          (document.exitFullscreen || document.webkitExitFullscreen).call(document);
        } else {
          var req = modal.requestFullscreen || modal.webkitRequestFullscreen;
          if (req) {
            try { req.call(modal); } catch (_e) {}
          }
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

    // Idle behavior: chrome visible briefly on open, then fades unless the
    // user moves the mouse / presses a key.
    bindIdleHandlers(modal);
    wakeChrome(modal);
  }

  // Bootstrap Init
  function init() {
    var modal = document.getElementById('hohFullscreenModal');
    if (!modal) return;

    // Direction A: guarantee the cinematic backdrop on every page (the inline
    // markup only exists in docs/index.html).
    ensureParallaxBg(modal);
    // Every share surface carries the Gaia Skill Tree logo + name.
    ensureBrandLockup(modal);

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

    // Delegated click listener for .plaque__share-btn (profile pages + explorer detail)
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.plaque__share-btn');
      if (!btn) return;
      e.stopPropagation();
      var skillId = btn.getAttribute('data-skill-id') || '';
      var handle  = btn.getAttribute('data-handle')   || skillId.split('/')[0];
      var name    = btn.getAttribute('data-skill-name') || skillId.split('/').pop();
      var ogPath  = btn.getAttribute('data-og') || ('og/' + handle + '/' + skillId.split('/').pop() + '.svg');
      var allNamed = window._gaiaNamedAll || [];
      var entry = allNamed.find(function(s){ return s.id === skillId; }) || {};
      openHohFullscreenModal({
        id: skillId,
        contributor: handle,
        name: name,
        level: entry.level || '',
        type: entry.type || 'basic',
        branch: entry.branch || '',
        origin: !!entry.origin,
        ogPath: ogPath,
        description: entry.description || '',
        tags: Array.isArray(entry.tags) ? entry.tags : []
      });
    });

    // Close actions
    var closeBtn = modal.querySelector('[data-fs-action="close"]');
    if (closeBtn) {
      closeBtn.addEventListener('click', closeHohFullscreenModal);
    }

    // Backdrop click close
    modal.addEventListener('click', function (e) {
      // Close download popover if click is outside the dl-wrap
      var dlWrap = document.getElementById('hohDlWrap');
      if (dlWrap && !dlWrap.contains(e.target)) {
        var popover = document.getElementById('hohDlPopover');
        if (popover && !popover.hidden) {
          var dlBtn = modal.querySelector('[data-fs-action="download"]');
          if (popover) { popover.hidden = true; popover.classList.remove('is-open'); }
          if (dlBtn) { dlBtn.setAttribute('aria-expanded','false'); dlBtn.classList.remove('is-active'); }
        }
      }
      if (e.target === modal || e.target.classList.contains('hoh-fs-stage')) {
        closeHohFullscreenModal();
      }
    });

    // Global Key Bindings
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        // Native fullscreen swallows the first Escape itself — only close the
        // modal if we're not already inside fullscreen.
        var inFs = !!(document.fullscreenElement || document.webkitFullscreenElement);
        if (!inFs) {
          closeHohFullscreenModal();
        }
      }
    });

    // Reflect native fullscreen state on the modal so the icon swaps.
    function syncFullscreenClass() {
      var fsEl = document.fullscreenElement || document.webkitFullscreenElement;
      modal.classList.toggle('is-fullscreen', fsEl === modal);
    }
    document.addEventListener('fullscreenchange', syncFullscreenClass);
    document.addEventListener('webkitfullscreenchange', syncFullscreenClass);
  }

  window.openHohFullscreenModal = openHohFullscreenModal;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

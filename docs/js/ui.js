window.switchOsTab = function(btn) {
  var step = btn.closest('.step');
  step.querySelectorAll('.os-tab').forEach(function(b){ b.classList.toggle('active', b === btn); });
  step.querySelectorAll('.os-panel').forEach(function(p){ p.classList.toggle('active', p.dataset.os === btn.dataset.os); });
};

(function(){
  var CLIP='<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="5" width="9" height="9" rx="1.5"/><path d="M11 5V3a1 1 0 00-1-1H3a1 1 0 00-1 1v7a1 1 0 001 1h2"/></svg>';
  var CHECK='<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="#4ade80" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 8l4 4 8-8"/></svg>';

  /* ── Reduced-motion helper ── */
  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  /* ─────────────────────────────────────────
     MOBILE NAV SHEET
     Slide-in panel from the right on ≤700px.
     ───────────────────────────────────────── */
  function initNavSheet() {
    var toggle = document.querySelector('.nav-menu-toggle');
    if (!toggle) return;

    /* Build sheet DOM once */
    var backdrop = document.createElement('div');
    backdrop.className = 'nav-sheet-backdrop';
    backdrop.setAttribute('aria-hidden', 'true');

    var sheet = document.createElement('nav');
    sheet.className = 'nav-sheet';
    sheet.setAttribute('role', 'dialog');
    sheet.setAttribute('aria-modal', 'true');
    sheet.setAttribute('aria-label', 'Navigation menu');

    /* Header */
    var header = document.createElement('div');
    header.className = 'nav-sheet-header';
    var wordmark = document.createElement('span');
    wordmark.className = 'nav-sheet-wordmark';
    wordmark.textContent = 'Gaia';
    var closeBtn = document.createElement('button');
    closeBtn.className = 'nav-sheet-close';
    closeBtn.setAttribute('aria-label', 'Close navigation');
    closeBtn.textContent = '✕';
    header.appendChild(wordmark);
    header.appendChild(closeBtn);
    sheet.appendChild(header);

    /* Links — mirror the main nav */
    var linksEl = document.createElement('div');
    linksEl.className = 'nav-sheet-links';

    /* Collect existing nav items */
    var mainNav = toggle.closest('nav');
    var existingItems = mainNav ? mainNav.querySelectorAll('ul li') : [];
    existingItems.forEach(function(li) {
      var src = li.firstElementChild;
      if (!src) return;
      var clone;
      if (src.tagName === 'A') {
        clone = document.createElement('a');
        clone.href = src.href;
        clone.textContent = src.textContent;
        if (src.getAttribute('aria-controls')) clone.setAttribute('aria-controls', src.getAttribute('aria-controls'));
      } else {
        /* Button */
        clone = document.createElement('button');
        clone.type = 'button';
        clone.textContent = src.textContent;
        /* Copy data attributes */
        Array.from(src.attributes).forEach(function(attr) {
          if (attr.name.startsWith('data-') || attr.name === 'aria-controls') {
            clone.setAttribute(attr.name, attr.value);
          }
        });
        /* Delegate click to original button so existing JS handlers fire */
        clone.addEventListener('click', function() {
          close();
          src.click();
        });
      }
      if (src.className) clone.className = src.className;
      linksEl.appendChild(clone);
    });
    sheet.appendChild(linksEl);

    document.body.appendChild(backdrop);
    document.body.appendChild(sheet);

    function open() {
      backdrop.classList.add('open');
      sheet.classList.add('open');
      toggle.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
      closeBtn.focus();
    }

    function close() {
      backdrop.classList.remove('open');
      sheet.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
      toggle.focus();
    }

    toggle.addEventListener('click', function() {
      sheet.classList.contains('open') ? close() : open();
    });
    closeBtn.addEventListener('click', close);
    backdrop.addEventListener('click', close);

    /* Close on link/anchor clicks inside sheet */
    linksEl.querySelectorAll('a').forEach(function(a) {
      a.addEventListener('click', close);
    });

    /* Esc key */
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && sheet.classList.contains('open')) close();
    });

    /* Keep old inline nav toggle working for non-sheet code paths */
    if (mainNav) {
      toggle.addEventListener('click', function() {
        /* The sheet handles open/close; keep aria-expanded in sync only */
      });
    }
  }

  /* ─────────────────────────────────────────
     FIRST-LOAD REVEAL SEQUENCE
     Runs once per session (sessionStorage gate).
     3 s cinematic, skippable on any click/keydown.
     Respects prefers-reduced-motion (instant skip).
     ───────────────────────────────────────── */
  function initFirstLoadReveal() {
    var SEEN_KEY = 'gaia-intro-seen';

    /* Skip entirely under reduced motion or if already seen */
    if (prefersReducedMotion()) return;
    if (sessionStorage.getItem(SEEN_KEY)) return;

    /* Mark as seen immediately so a refresh during the intro doesn't re-run */
    sessionStorage.setItem(SEEN_KEY, '1');

    /* Build overlay */
    var overlay = document.createElement('div');
    overlay.className = 'intro-overlay';
    overlay.setAttribute('aria-hidden', 'true');

    var line1 = document.createElement('div');
    line1.className = 'intro-reveal-line';
    line1.textContent = 'Skills are catalogued.';

    var line2 = document.createElement('div');
    line2.className = 'intro-reveal-line';
    line2.textContent = 'Names are earned.';

    var skipHint = document.createElement('div');
    skipHint.className = 'intro-skip';
    skipHint.textContent = 'click anywhere to skip';

    overlay.appendChild(line1);
    overlay.appendChild(line2);
    overlay.appendChild(skipHint);
    document.body.appendChild(overlay);

    var skipped = false;
    var timers = [];

    function dismiss() {
      if (skipped) return;
      skipped = true;
      timers.forEach(clearTimeout);
      overlay.classList.add('fading');
      setTimeout(function() { overlay.classList.add('done'); }, 1250);
    }

    /* Click or keydown skips */
    document.addEventListener('click', dismiss, { once: true });
    document.addEventListener('keydown', dismiss, { once: true });

    /* Sequence: line1 at 0.4s, line2 at 1.1s, dismiss at 3.0s */
    timers.push(setTimeout(function() {
      if (!skipped) line1.classList.add('visible');
    }, 400));
    timers.push(setTimeout(function() {
      if (!skipped) line2.classList.add('visible');
    }, 1100));
    timers.push(setTimeout(function() {
      dismiss();
    }, 3000));
  }

  /* ─────────────────────────────────────────
     COPY BUTTONS
     ───────────────────────────────────────── */
  function initCopyButtons(){
    document.querySelectorAll('pre').forEach(function(pre){
      if(pre.closest('.pre-wrap')) return;
      var wrap = document.createElement('div');
      wrap.className = 'pre-wrap';
      pre.parentNode.insertBefore(wrap, pre);
      wrap.appendChild(pre);
      var btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.innerHTML = CLIP;
      btn.title = 'Copy';
      btn.setAttribute('aria-label', 'Copy to clipboard');
      btn.addEventListener('click', function(){
        var text = pre.innerText;
        navigator.clipboard.writeText(text).then(function(){
          btn.innerHTML = CHECK;
          btn.classList.add('copied');
          setTimeout(function(){ btn.innerHTML = CLIP; btn.classList.remove('copied'); }, 1800);
        }).catch(function(){
          btn.innerHTML = CLIP;
          setTimeout(function(){ btn.innerHTML = CLIP; }, 1800);
        });
      });
      wrap.appendChild(btn);
    });
  }

  /* ─────────────────────────────────────────
     INIT
     ───────────────────────────────────────── */
  function init() {
    initCopyButtons();
    initNavSheet();
    initFirstLoadReveal();
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

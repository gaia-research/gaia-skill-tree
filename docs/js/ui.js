window.switchOsTab = function(btn) {
  var step = btn.closest('.rite-step, .step');
  step.querySelectorAll('.os-tab').forEach(function(b){ b.classList.toggle('active', b === btn); });
  step.querySelectorAll('.os-panel').forEach(function(p){ p.classList.toggle('active', p.dataset.os === btn.dataset.os); });
};

(function(){
  // Stage 1 — icon helper. Falls back to a no-op svg if icons.js failed to
  // load (e.g. while debugging) so the copy button stays clickable.
  function icon(id, opts){
    return (typeof window.gaiaIcon === 'function')
      ? window.gaiaIcon(id, opts || { size: 14 })
      : '<svg class="ico" width="14" height="14" aria-hidden="true"></svg>';
  }
  function CLIP(){ return icon('copy', { size: 14 }); }
  function CHECK(){ return icon('copy-check', { size: 14, className: 'ico ico--ok' }); }

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

    var nav = toggle.closest('nav');
    if (!nav) return;

    function open() {
      nav.classList.add('nav-open');
      toggle.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
    }

    function close() {
      nav.classList.remove('nav-open');
      toggle.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    }

    toggle.addEventListener('click', function(e) {
      e.stopPropagation();
      nav.classList.contains('nav-open') ? close() : open();
    });

    /* Close when clicking links */
    nav.querySelectorAll('ul li a, ul li button').forEach(function(el) {
      el.addEventListener('click', close);
    });

    /* Close on backdrop click (we'll add a backdrop in CSS or use nav itself) */
    document.addEventListener('click', function(e) {
      if (nav.classList.contains('nav-open') && !nav.contains(e.target)) {
        close();
      }
    });

    /* Esc key */
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && nav.classList.contains('nav-open')) close();
    });
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
  /* Clipboard write with fallback for insecure contexts (HTTP / LAN IP) */
  function copyToClipboard(text){
    if(window.isSecureContext && navigator.clipboard && navigator.clipboard.writeText){
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function(resolve, reject){
      try{
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        var ok = document.execCommand('copy');
        document.body.removeChild(ta);
        ok ? resolve() : reject(new Error('execCommand returned false'));
      }catch(err){ reject(err); }
    });
  }
  window.copyToClipboard = copyToClipboard;

  function flashCopied(btn){
    btn.innerHTML = CHECK();
    btn.classList.add('copied');
    setTimeout(function(){ btn.innerHTML = CLIP(); btn.classList.remove('copied'); }, 1600);
  }
  // Stage 1 — expose the flash-to-check helper so other call sites (the
  // skill explorer install button, for example) can share the animation.
  window.gaiaFlashCopied = flashCopied;

  function initCopyButtons(){
    document.querySelectorAll('pre').forEach(function(pre){
      if(pre.closest('.pre-wrap')) return;
      var wrap = document.createElement('div');
      wrap.className = 'pre-wrap';
      pre.parentNode.insertBefore(wrap, pre);
      wrap.appendChild(pre);
      var btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.innerHTML = CLIP();
      btn.title = 'Copy';
      btn.setAttribute('aria-label', 'Copy to clipboard');
      btn.addEventListener('click', function(){
        copyToClipboard(pre.innerText).then(function(){ flashCopied(btn); }).catch(function(){
          /* surface failure visibly */
          btn.title = 'Copy failed — select and copy manually';
        });
      });
      wrap.appendChild(btn);
    });
  }

  /* ─────────────────────────────────────────
     SCROLL TO TOP
     ───────────────────────────────────────── */
  function initScrollToTop() {
    var btn = document.getElementById('scrollToTop');
    if (!btn) return;
    window.addEventListener('scroll', function() {
      if (window.scrollY > 300) {
        btn.classList.add('visible');
      } else {
        btn.classList.remove('visible');
      }
    }, { passive: true });
    btn.addEventListener('click', function() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* ─────────────────────────────────────────
     INIT
     ───────────────────────────────────────── */
  function init() {
    initCopyButtons();
    initNavSheet();
    initFirstLoadReveal();
    initScrollToTop();
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

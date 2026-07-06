/* ============================================================
   Ascension Overdrive · v2 motion driver (Issue #975)
   ------------------------------------------------------------
   Scroll-linked, multi-layer parallax + sticky-scene state
   choreography for the #ascension section on docs/index.html.

   Contract with the CSS (docs/css/ascension-overdrive-v2.css):
   - Each .aov-scene toggles state classes on IntersectionObserver
     entry/exit: .is-entering, .is-active, .is-exiting.
   - Parallax layers (.aov-ledger, .aov-fog, .aov-arch) receive
     `transform: translate3d(0, Ypx, 0)` written from rAF, driven
     by the section's normalized scroll progress (0..1).
   - .aov-thread__path receives `stroke-dashoffset` written from
     the same rAF; bidirectional (draws on scroll-down, undraws
     on scroll-up).
   - Each rank scene's .aov-riser__line receives a scene-local
     scroll progress and draws its own dashoffset across the
     viewport width.
   - Apex Gate predicates toggle `.is-lit` one-by-one across the
     scene's 200vh pin (each takes ~33vh).
   - Apex Gate .aov-apex-coda toggles `.is-revealed` at the last
     20vh of the Apex scene.
   - Motion loops (<video>) inside .aov-ucard__plate lazy-load on
     card entry EXCEPT those flagged data-motion-pending=true.

   NO sessionStorage guard (deliberate: scroll-linked motion is
   designed to be re-experienced every visit; the user drives it).

   Reduced-motion: rAF loop still runs but writes no transforms
   (leaves rest state); IO still toggles is-active so CSS's
   composed-rest rules can apply.
   ============================================================ */
(function () {
  'use strict';

  var section = document.querySelector('.aov');
  if (!section) return;

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var isMobile = window.matchMedia && window.matchMedia('(max-width: 899px)').matches;

  // Parallax layer registry: element + rate. Rate 1.0 = native scroll.
  // Ledger 0.15 (nearly-static ground); fog 0.25 (drifts slowly);
  // arch 0.60 (descends toward viewer as user enters Apex).
  var ledger = section.querySelector('.aov-ledger');
  var fog    = section.querySelector('.aov-fog');
  var arch   = section.querySelector('.aov-arch');
  var thread = section.querySelector('.aov-thread__path');
  var risers = Array.prototype.slice.call(section.querySelectorAll('.aov-riser__line'));
  var predicates = Array.prototype.slice.call(section.querySelectorAll('.aov-pred'));
  var coda   = section.querySelector('.aov-apex-coda');
  var scenes = Array.prototype.slice.call(section.querySelectorAll('.aov-scene'));
  var apexScene = section.querySelector('.aov-scene[data-scene="apex"]');

  // Cache the thread path's total length once so dashoffset math
  // is a pure normalization from scroll progress. `getTotalLength`
  // is O(1) after the path is laid out.
  var threadLen = 0;
  if (thread && typeof thread.getTotalLength === 'function') {
    try {
      threadLen = thread.getTotalLength();
      thread.style.strokeDasharray = threadLen;
      thread.style.strokeDashoffset = threadLen;
    } catch (e) {
      threadLen = 4000; // fallback
    }
  }

  // Cache section rect on resize; window.scrollY is compared to
  // sectionTop / sectionHeight to produce a 0..1 scroll progress
  // over the whole section's scroll range.
  var sectionRect = { top: 0, height: 1 };
  function measure() {
    var r = section.getBoundingClientRect();
    sectionRect.top    = r.top + window.scrollY;
    sectionRect.height = section.offsetHeight;
    isMobile = window.matchMedia && window.matchMedia('(max-width: 899px)').matches;
  }
  measure();

  // Debounced resize (fires after 120ms of quiet).
  var resizeTimer = null;
  window.addEventListener('resize', function () {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(measure, 120);
  }, { passive: true });

  /* IntersectionObserver drives per-scene state classes.
     Threshold 0.05: fire is-entering when 5% is visible.
     Threshold 0.5: fire is-active. */
  if ('IntersectionObserver' in window) {
    var sceneObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var el = entry.target;
        if (entry.isIntersecting) {
          el.classList.add('is-entering');
          if (entry.intersectionRatio > 0.35) el.classList.add('is-active');
        } else {
          el.classList.remove('is-active');
          // keep is-entering so exit state is stable
        }
      });
    }, { threshold: [0, 0.05, 0.35, 0.75] });

    scenes.forEach(function (s) { sceneObserver.observe(s); });

    /* Motion-loop lazy-load: swap data-src → src and .play() when
       the card enters the viewport. Cards flagged data-motion-pending
       stay poster-only (unique-5-loop.mp4 is 19MB pending recompression). */
    var videos = Array.prototype.slice.call(section.querySelectorAll('.aov-ucard__plate video'));
    var videoObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var v = entry.target;
        if (v.dataset.motionPending === 'true') return;
        var srcEl = v.querySelector('source[data-src]');
        if (srcEl && !srcEl.getAttribute('src')) {
          srcEl.setAttribute('src', srcEl.getAttribute('data-src'));
          v.load();
          v.play().then(function () {
            v.classList.add('is-loaded');
          }).catch(function () {
            /* autoplay refused — poster stays visible */
          });
        }
        videoObserver.unobserve(v);
      });
    }, { threshold: 0.35 });
    videos.forEach(function (v) { videoObserver.observe(v); });
  }

  /* Scroll-linked rAF loop.
     Writes translateY on parallax layers, stroke-dashoffset on
     thread and risers, and .is-lit / .is-revealed toggles on the
     Apex Gate scene.

     `will-change: transform` is applied to parallax layers only
     while scroll is active; a debounced scroll-end handler removes
     it to free GPU resources when the section is quiet. */
  var scrolling = false;
  var scrollEndTimer = null;
  var parallaxLayers = [ledger, fog, arch].filter(Boolean);

  function markScrolling(active) {
    if (active === scrolling) return;
    scrolling = active;
    parallaxLayers.forEach(function (l) {
      l.style.willChange = active ? 'transform' : 'auto';
    });
  }

  var lastScrollY = window.scrollY;

  function tick() {
    // Normalized 0..1 progress across the section's total scroll
    // range. When the section top hits the viewport top, progress
    // begins; when the section bottom leaves the viewport bottom,
    // progress is complete.
    var vh = window.innerHeight;
    var y = window.scrollY;
    var start = sectionRect.top - vh;
    var end   = sectionRect.top + sectionRect.height;
    var range = end - start;
    var raw   = (y - start) / range;
    var p     = Math.max(0, Math.min(1, raw));

    // Local progress across the section's own body (starts when
    // section top hits viewport top, ends when section bottom
    // leaves top). Used for the gold thread so the thread draws
    // while the section is IN view, not while it's approaching.
    var localStart = sectionRect.top;
    var localEnd   = sectionRect.top + sectionRect.height - vh;
    var localRange = Math.max(1, localEnd - localStart);
    var lp = Math.max(0, Math.min(1, (y - localStart) / localRange));

    // Reduced-motion: leave all transforms at rest (0). Predicates
    // and coda still toggle so the composition reads as intended.
    var writeTransforms = !reduce && !isMobile;

    if (writeTransforms) {
      // Parallax translateY offsets. The layer moves *opposite*
      // to scroll at (1 - rate) × scroll — so a rate of 0.15
      // means the layer moves at 15% of native scroll (drifts
      // slowly upward as user scrolls down).
      // We express this as a fixed pixel offset relative to the
      // section's scroll range so the numbers stay stable.
      var maxDrift = sectionRect.height;
      if (ledger) {
        var ly = -p * maxDrift * 0.15;
        ledger.style.transform = 'translate3d(0, ' + ly.toFixed(1) + 'px, 0)';
      }
      if (fog) {
        var fy = -p * maxDrift * 0.25;
        fog.style.transform = 'translate3d(0, ' + fy.toFixed(1) + 'px, 0)';
      }
      if (arch) {
        // Arch descends toward the viewer as user enters Apex.
        // Rate 0.60 but only becomes visible in the last third
        // of the section. Opacity ramps from 0 → 0.55 over the
        // last 30% of scroll progress.
        var ap = Math.max(0, (p - 0.55) / 0.45);
        ap = ap * ap * (3 - 2 * ap);        // smoothstep
        var ay = (ap - 0.5) * 200;          // -100 → +100 px
        arch.style.transform = 'translate3d(-50%, ' + ay.toFixed(1) + 'px, 0)';
        arch.style.opacity = (ap * 0.55).toFixed(3);
      }
    } else {
      // Reduced-motion / mobile: composed rest state.
      if (ledger) ledger.style.transform = 'translate3d(0, 0, 0)';
      if (fog)    fog.style.transform    = 'translate3d(0, 0, 0)';
      if (arch) {
        arch.style.transform = 'translate3d(-50%, 0, 0)';
        arch.style.opacity   = '0.35';
      }
    }

    // Gold thread — scroll-linked dashoffset. Bidirectional
    // because `lp` reads scroll progress each frame, so scrolling
    // up naturally undraws the thread. Reduced-motion: leave
    // dashoffset at 0 (fully drawn) — CSS handles via !important.
    if (thread && threadLen && !reduce) {
      var off = threadLen * (1 - lp);
      thread.style.strokeDashoffset = off.toFixed(1);
    }

    // Risers — one per rank scene. Each scene's rise draws its
    // riser as the scene enters and completes as it fills the
    // viewport. Progress is scene-local:
    //   sceneP = 1 when scene stage center hits viewport center.
    risers.forEach(function (line) {
      var scene = line.closest('.aov-scene');
      if (!scene) return;
      var sr = scene.getBoundingClientRect();
      var sp = 1 - (sr.top + sr.height * 0.5) / vh;
      sp = Math.max(0, Math.min(1, sp));
      var len = line.getAttribute('data-len') || 1000;
      len = parseFloat(len);
      var lineOff = len * (1 - sp);
      if (!reduce) {
        line.style.strokeDasharray  = len;
        line.style.strokeDashoffset = lineOff.toFixed(1);
      } else {
        line.style.strokeDashoffset = 0;
      }
    });

    // Apex Gate — six predicates illuminate over the scene's
    // 200vh pin. Compute scene-local progress: 0 at scene top,
    // 1 at scene bottom. Divide into 6 segments; light each once
    // its segment starts. Reversible: scrolling back up unlights.
    if (apexScene && predicates.length) {
      var ar = apexScene.getBoundingClientRect();
      var apexRange = ar.height - vh;
      var apexP = 0;
      if (apexRange > 0) {
        apexP = Math.max(0, Math.min(1, -ar.top / apexRange));
      }
      var lit = Math.floor(apexP * 6 + 0.5);
      predicates.forEach(function (p, i) {
        if (i < lit) {
          p.classList.add('is-lit');
        } else {
          p.classList.remove('is-lit');
        }
      });
      if (coda) {
        if (apexP > 0.85) coda.classList.add('is-revealed');
        else              coda.classList.remove('is-revealed');
      }
    }

    // Debounced scroll-end will-change cleanup: if user hasn't
    // scrolled in 200ms, remove will-change from parallax layers.
    if (Math.abs(y - lastScrollY) > 1) {
      markScrolling(true);
      if (scrollEndTimer) clearTimeout(scrollEndTimer);
      scrollEndTimer = setTimeout(function () {
        markScrolling(false);
      }, 200);
      lastScrollY = y;
    }

    rafId = requestAnimationFrame(tick);
  }

  var rafId = requestAnimationFrame(tick);

  // Pause rAF when tab is backgrounded — no reason to burn
  // frames while the user is elsewhere.
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      if (rafId) cancelAnimationFrame(rafId);
      rafId = 0;
    } else {
      measure();
      if (!rafId) rafId = requestAnimationFrame(tick);
    }
  });
})();

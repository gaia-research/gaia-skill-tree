/* ============================================================
   Ascension Overdrive · motion choreography (Issue #975)
   ------------------------------------------------------------
   One coordinated ~3.0s reveal on section entry. Fires ONCE per
   session — sessionStorage guard keeps re-scroll silent.

   Sequence (relative to trigger T=0):
     0ms    ─ .is-playing → risers stroke-dashoffset draws in
              (900ms + 80ms per-line stagger, CSS-owned)
     1100ms ─ .is-playing → gold thread stroke-dashoffset draws in
              (1400ms, CSS-owned via transition-delay)
     1600ms ─ predicates illuminate one-by-one, 120ms stagger
              (JS toggles .is-lit; CSS handles brass-flash)
     2400ms ─ apex-card pulse (.is-apex-pulsed on plate)
   Total: ~3000ms

   Also owns motion-loop lazy-load: <video> elements inside
   .ao-ucard__stamp start with preload="none", swap to preload="auto"
   and call .play() only when the card enters the viewport. Cards
   flagged data-motion-pending stay poster-only (unique-5-loop.mp4
   is 19MB pending recompression).

   Reduced-motion: none of this fires; CSS composed rest state
   already carries the message.
   ============================================================ */
(function () {
  'use strict';

  var plate = document.querySelector('.ao-plate');
  if (!plate) return;

  var reduce =
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var SESSION_KEY = 'ascension-overdrive-played';
  var alreadyPlayed = false;
  try {
    alreadyPlayed = sessionStorage.getItem(SESSION_KEY) === '1';
  } catch (e) {
    /* private-mode / storage disabled — treat as fresh, fire once per page */
  }

  /* If reduced-motion or already played this session, jump to composed rest.
     Composed rest is what CSS renders when .is-played is set: transitions
     are cleared and geometry is pinned to the end state. */
  function pinToRestState() {
    plate.classList.add('is-played');
    var preds = plate.querySelectorAll('.ao-pred');
    preds.forEach(function (p) { p.classList.add('is-lit', 'is-lit--silent'); });
  }

  if (reduce) {
    /* Nothing to do — CSS reduced-motion rules already render the rest state.
       We do NOT toggle .is-playing here; the media query pins the geometry. */
  } else if (alreadyPlayed) {
    pinToRestState();
  }

  /* Motion sequence ------------------------------------------------ */
  function playMotion() {
    plate.classList.add('is-playing');

    // T=1600ms — light predicates one-by-one, 120ms stagger.
    var preds = plate.querySelectorAll('.ao-pred');
    preds.forEach(function (p, i) {
      setTimeout(function () {
        p.classList.add('is-lit');
      }, 1600 + i * 120);
    });

    // T=2400ms — apex card pulse.
    setTimeout(function () {
      plate.classList.add('is-apex-pulsed');
      // Strip will-change once motion ends so we don't hold the layer.
      setTimeout(function () {
        var risers = plate.querySelector('.ao-risers');
        if (risers) risers.style.willChange = 'auto';
      }, 800);
    }, 2400);

    try {
      sessionStorage.setItem(SESSION_KEY, '1');
    } catch (e) { /* ignore */ }
  }

  /* IntersectionObserver — fires when section is 20% into viewport.
     unobserve after first hit so motion is truly one-shot. */
  if (!reduce && !alreadyPlayed && 'IntersectionObserver' in window) {
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          obs.unobserve(entry.target);
          playMotion();
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '-20% 0px'
    });
    obs.observe(plate);
  } else if (!reduce && !alreadyPlayed) {
    // No IO support — play on load; motion still delivers.
    playMotion();
  }

  /* -------------------------------------------------------------
     Motion-loop lazy-load — <video> inside .ao-ucard__stamp
     ------------------------------------------------------------- */
  var videos = plate.querySelectorAll('.ao-ucard__stamp video');
  if (!videos.length) return;

  function loadVideo(video) {
    if (video.dataset.motionPending === 'true') return;   // unique-5-loop, skip
    if (video.dataset.loaded === 'true') return;
    video.dataset.loaded = 'true';
    // Swap the source in — preload="none" held it back.
    video.preload = 'auto';
    var src = video.querySelector('source');
    if (src && !src.getAttribute('src') && src.dataset.src) {
      src.setAttribute('src', src.dataset.src);
      video.load();
    }
    var playPromise = video.play();
    if (playPromise && typeof playPromise.then === 'function') {
      playPromise.then(function () {
        video.classList.add('is-live');
      }).catch(function () {
        /* autoplay blocked — poster stays, no error surface */
      });
    } else {
      video.classList.add('is-live');
    }
  }

  if (reduce) {
    // Skip video entirely under reduced-motion. Posters are the message.
    return;
  }

  if ('IntersectionObserver' in window) {
    var vObs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          loadVideo(entry.target);
          vObs.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.25,
      rootMargin: '0px 0px 200px 0px'
    });
    videos.forEach(function (v) { vObs.observe(v); });
  } else {
    // Fall back — load them all after a short delay, still respecting pending flag.
    setTimeout(function () {
      videos.forEach(loadVideo);
    }, 1200);
  }
})();

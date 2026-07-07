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
   - Apex Gate predicates run a modular state machine over the
     scene's 350vh pin. Each row carries `data-state="locked" |
     "unlocked" | "disabled"`. JS queries `[data-state="locked"]`
     at page load, divides the pin evenly across them, and adds
     `.is-breaking` (transient) then flips `data-state="unlocked"`
     (add-only) as each threshold is crossed. `disabled` rows are
     skipped entirely — they render as-is with no scroll trigger.
     Adding a new predicate in HTML is the only change needed to
     extend the gate; math auto-distributes across whatever `locked`
     rows the DOM presents.
   - Apex Gate .aov-apex-coda toggles `.is-revealed` at the last
     20vh of the Apex scene.
   - Unique branch scene: .aov-unique-header-line opacity ramps
     0→1 across the first 20vh of the scene pin (scroll-linked).
   - The Order coda scene: 9 .aov-order-rung elements toggle
     .is-lit top-to-bottom as scroll progresses; full assembly
     completes at ~50% of the coda scroll range.
   - Post-ratification 2026-07-06: Asset E MP4 loops on Unique
     cards are dropped; cards render static-poster only. The
     previous video-lazy-load observer is removed with them.

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
  // Ledger 0.15 (nearly-static ground); fog 0.25 (drifts slowly, per
  // Asset G manifest); arch 0.60 (descends toward viewer as user
  // enters Apex).
  var ledger = section.querySelector('.aov-ledger');
  var fog    = section.querySelector('.aov-fog');
  var arch   = section.querySelector('.aov-arch');
  var apexHero = section.querySelector('.aov-apex-hero');
  var thread = section.querySelector('.aov-thread__path');
  var risers = Array.prototype.slice.call(section.querySelectorAll('.aov-riser__line'));
  // Predicate rows that participate in the unlock ladder. Snapshotted
  // once at page load: everything in DOM order except rows whose
  // `data-state` is `disabled`. Its length N is the stable denominator
  // for the unlock threshold math, so segment size doesn't reshuffle
  // as rows transition from locked to unlocked. Adding a new
  // predicate = HTML edit + reload; no CSS or JS churn. Devtools
  // toggles that flip an existing row's data-state require a page
  // reload to be re-picked up.
  var unlockablePreds = Array.prototype.slice.call(
    section.querySelectorAll('.aov-pred')
  ).filter(function (pred) {
    return pred.dataset.state !== 'disabled';
  });
  var coda   = section.querySelector('.aov-apex-coda');
  var scenes = Array.prototype.slice.call(section.querySelectorAll('.aov-scene'));
  var apexScene = section.querySelector('.aov-scene[data-scene="apex"]');
  var uniqueScene   = section.querySelector('.aov-scene[data-scene="unique"]');
  var uniqueHeader  = section.querySelector('.aov-unique-header-line');
  var codaScene     = section.querySelector('.aov-scene[data-scene="coda"]');
  var orderRungs    = Array.prototype.slice.call(section.querySelectorAll('.aov-order-rung'));
  // Rank hero backdrops (Asset F). One per rank scene (r1..r5).
  // Each hero fades in over the first ~30vh of its scene, peaks at
  // ~0.55 at scene mid, fades out over the final ~30vh. Bidirectional.
  var rankHeroes = Array.prototype.slice.call(
    section.querySelectorAll('.aov-scene[data-scene="rank"] .aov-rank-hero')
  );

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
  var parallaxLayers = [ledger, fog, arch, apexHero].filter(Boolean);

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
    // Parallax transforms are ALLOWED on mobile (per operator nitpick
    // 2026-07-07): sticky pins are off on mobile (position: static
    // in the collapse block), but the parallax layers translate
    // freely with scroll to add subtle depth. Only reduced-motion
    // suppresses all transforms.
    var writeTransforms = !reduce;

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
        // of the section. Opacity ramps from 0 → 0.70 over the
        // last ~45% of scroll progress.
        //
        // G4 realignment (Issue #975): peak opacity lifted 0.55 →
        // 0.70 so the arch reads monumental at the Apex terminus.
        var ap = Math.max(0, (p - 0.55) / 0.45);
        ap = ap * ap * (3 - 2 * ap);        // smoothstep
        var ay = (ap - 0.5) * 200;          // -100 → +100 px
        arch.style.transform = 'translate3d(-50%, ' + ay.toFixed(1) + 'px, 0)';
        arch.style.opacity = (ap * 0.70).toFixed(3);

        // G7 realignment: apex hero plate rides the same ap ramp
        // but peaks at 0.55 so it sits underneath the arch as an
        // atmospheric backdrop rather than competing with it.
        if (apexHero) {
          apexHero.style.opacity = (ap * 0.55).toFixed(3);
        }
      }
    } else {
      // Reduced-motion / mobile: composed rest state. Do NOT write
      // inline opacity on the hero backdrops — CSS pins them at a
      // composed dim value via `@media (prefers-reduced-motion)` +
      // `@media (max-width: 899px)`, so inline styles would fight it.
      if (ledger) ledger.style.transform = 'translate3d(0, 0, 0)';
      if (fog)    fog.style.transform    = 'translate3d(0, 0, 0)';
      if (arch) {
        arch.style.transform = 'translate3d(-50%, 0, 0)';
        arch.style.opacity   = '0.35';
      }
    }

    // Ledger + haze opacity — scroll-linked (Issue #975 R3/R4 +
    // Asset G wire-up). Both parchment and haze ride the same ramp:
    // full at title / apex / coda so the atmosphere carries; fade
    // to a whisper through the rank scenes + Unique branch so
    // they don't fight the Asset F hero plates nor paint a
    // horizontal band across the top of the Unique scene. Boundary
    // constants match the current scene layout (title 100vh +
    // ranks 400vh + unique 100vh + rank5 100vh + apex 350vh +
    // coda 180vh):
    //   ~0.17 = end of title stage sticky range
    //   ~0.65 = start of apex stage sticky range
    // Each boundary is eased over a 0.05 band so the handoff
    // reads as a slow dim, not a hard switch. Haze rides at about
    // half the ledger amplitude per Asset G manifest guidance
    // (0.18 base / 0.03 valley) — subtle warm depth on the title
    // and terminus, mostly invisible where the ranks own the plane.
    if (!reduce && !isMobile) {
      var LEDGER_FULL   = 0.48;
      var LEDGER_VALLEY = 0.08;
      var FOG_FULL      = 0.18;
      var FOG_VALLEY    = 0.03;
      var ramp          = 1;               // 1.0 at full, 0.0 at valley
      if (p >= 0.17 && p <= 0.65) {
        ramp = 0;
      } else if (p > 0.12 && p < 0.17) {
        ramp = 1 - (p - 0.12) / 0.05;
      } else if (p > 0.65 && p < 0.70) {
        ramp = (p - 0.65) / 0.05;
      }
      if (ledger) {
        var ledgerOp = LEDGER_VALLEY + ramp * (LEDGER_FULL - LEDGER_VALLEY);
        ledger.style.opacity = ledgerOp.toFixed(3);
      }
      if (fog) {
        var fogOp = FOG_VALLEY + ramp * (FOG_FULL - FOG_VALLEY);
        fog.style.opacity = fogOp.toFixed(3);
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

    // Rank hero backdrops (Asset F). One per rank scene. Opacity
    // ramps 0 → 0.55 → 0 across each scene's viewport traversal:
    // fade-in over first 30% of scene scroll (scene top hits vh),
    // peak at scene mid (scene center at viewport center), fade-out
    // over final 30% (scene bottom leaving viewport top).
    //
    // We express this as a triangular envelope on scene-local
    // progress `sp` ∈ [0, 1], where sp = 0.5 when the scene center
    // hits the viewport center. Envelope: 0 at sp=0 and sp=1, peak
    // at sp=0.5. `smoothstep(min(sp, 1-sp) / 0.35)` gives a smooth
    // 30% ramp on each side with a held peak in the middle.
    //
    // Rank hero opacity ramp: writes to `.aov-rank-hero` div's inline
    // opacity based on scroll-local progress. On mobile the JS skips
    // this write (leaving the CSS `!important 0.15` pin) so the hero
    // stays subtle on small screens where it would otherwise dominate
    // the compressed viewport.
    if (!reduce && !isMobile) {
      rankHeroes.forEach(function (hero) {
        var scene = hero.closest('.aov-scene');
        if (!scene) return;
        var sr = scene.getBoundingClientRect();
        // Scene-local progress: 0 when scene top touches viewport
        // bottom, 1 when scene bottom leaves viewport top.
        var denom = (sr.height + vh);
        var sp = 1 - (sr.top + sr.height) / denom;
        sp = Math.max(0, Math.min(1, sp));
        var edge = Math.min(sp, 1 - sp);         // triangular envelope
        var ramp = Math.min(1, edge / 0.35);     // 30% fade on each side
        ramp = ramp * ramp * (3 - 2 * ramp);     // smoothstep
        hero.style.opacity = (ramp * 0.55).toFixed(3);
      });
    }

    // Apex Gate — modular latch-and-seal state machine over the
    // 350vh pin. See docs/css/ascension-overdrive-v2.css `.aov-pred`
    // block for the visual states.
    //
    // Contract:
    //   - `unlockablePreds` is snapshotted at page load as the DOM
    //     order of every `.aov-pred` whose `data-state` is NOT
    //     `disabled`. Its length N is the stable denominator.
    //   - Row i unlocks when apex-scene-local progress crosses its
    //     threshold `(i + 1) / N`. Approaching band (15% of segment
    //     before threshold) adds transient `.is-breaking`.
    //     Crossing the threshold removes `.is-breaking` and flips
    //     `data-state` to `"unlocked"` (add-only — never re-locks
    //     on scroll-back). Scrolling back past the approach band
    //     drops the transient breaking class so the seal reappears
    //     for rows still in the locked state.
    //   - Disabled rows are never in the list; they render as-is.
    //
    // Predicate-count-agnostic by design: adding an <li> with
    // `data-state="locked"` in HTML on next reload redistributes
    // the pin math automatically. Reduced-motion runs the state
    // flips so the composition reads as intended — CSS drops the
    // transitions and shudder animation.
    if (apexScene && unlockablePreds.length) {
      var ar = apexScene.getBoundingClientRect();
      var apexRange = ar.height - vh;
      var apexP = 0;
      if (apexRange > 0) {
        apexP = Math.max(0, Math.min(1, -ar.top / apexRange));
      }
      var segSize = 1 / unlockablePreds.length;
      // Approach band widened to 0.35 of a segment (was 0.15) so
      // the .is-breaking shudder + seal fade have visible scroll
      // duration under normal reading pace. At 6 predicates, this
      // is ~35% * 16.7% = ~5.8% of apex scroll (~156px on a 350vh
      // pin at 1080 vh) — enough to see the animation land.
      var approachBand = 0.35 * segSize;
      unlockablePreds.forEach(function (pred, i) {
        if (pred.dataset.state === 'unlocked') return;
        var threshold = (i + 1) * segSize;
        if (apexP >= threshold) {
          pred.classList.remove('is-breaking');
          pred.dataset.state = 'unlocked';
        } else if (apexP >= threshold - approachBand) {
          if (!pred.classList.contains('is-breaking')) {
            pred.classList.add('is-breaking');
          }
        } else if (pred.classList.contains('is-breaking')) {
          pred.classList.remove('is-breaking');
        }
      });

      if (coda) {
        if (apexP > 0.85) coda.classList.add('is-revealed');
        else              coda.classList.remove('is-revealed');
      }
    }

    // Unique branch scene — the header line fades in as scroll
    // enters the pin. Opacity ramps 0→1 across the first 20vh of
    // scene-local scroll, then stays composed. Bidirectional.
    // Reduced-motion / mobile: leave to CSS (opacity 1 !important).
    if (uniqueScene && uniqueHeader && !reduce && !isMobile) {
      var ur = uniqueScene.getBoundingClientRect();
      // Scene-local progress: 0 when scene top hits viewport top;
      // grows as scene scrolls past. Cap at 1 (scene has released).
      var uniqueP = Math.max(0, Math.min(1, -ur.top / vh));
      var headerOpacity = Math.max(0, Math.min(1, uniqueP / 0.2));
      uniqueHeader.style.opacity = headerOpacity.toFixed(3);
    }

    // The Order coda — nine rungs assemble top-to-bottom. Each
    // rung has a scene-local threshold; below the threshold the
    // rung is dormant, above it .is-lit is added. Full assembly
    // completes at ~50% of the coda's scroll range (per shape
    // brief). Reduced-motion / mobile: rungs are lit at rest via
    // CSS !important; skip writing.
    //
    // R7 shape work (Issue #975): each crown rung also picks up an
    // `.is-materializing` state class exactly once, the first time
    // its threshold is crossed. The class drives the one-shot font
    // animations (letter-spacing collapse on the Apex rung, outline
    // stroke breathe + settle-in scale on the Unique Apex rung).
    // The class is add-only — never removed on scroll-up — so the
    // crown rungs stay composed even after `.is-lit` retracts.
    if (codaScene && orderRungs.length && !reduce && !isMobile) {
      var cr = codaScene.getBoundingClientRect();
      var codaRange = cr.height - vh;
      var codaP = 0;
      if (codaRange > 0) {
        codaP = Math.max(0, Math.min(1, -cr.top / codaRange));
      }
      // Compress the assembly to the first 50% of the pin, so the
      // ladder is fully lit by the time the operator reaches half
      // the coda pin. The remaining 50% holds the composed state.
      var assembleP = Math.min(1, codaP / 0.5);
      var n = orderRungs.length;
      for (var i = 0; i < n; i++) {
        var threshold = i / n;
        if (assembleP >= threshold) {
          orderRungs[i].classList.add('is-lit');
          orderRungs[i].classList.add('is-materializing');
        } else {
          orderRungs[i].classList.remove('is-lit');
          // Deliberately do NOT remove is-materializing — the font
          // animation is a one-shot; letting the class persist keeps
          // the crown rungs composed on scroll-up.
        }
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

/* ============================================================
   Ascension Overdrive v4, Cosmic Y-Fork Edition (Issue #998)

   Scroll drives the atmosphere, the three named SVG paths, scene
   reveals, and both terminal gate ladders. There is deliberately no
   one-shot persistence guard: the ascent recomposes on every visit and is
   bidirectional when the reader scrolls back.
   ============================================================ */
(function () {
  'use strict';

  var section = document.querySelector('#ascension.aov');
  if (!section) return;

  var reduceQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  var mobileQuery = window.matchMedia('(max-width: 899px)');
  var thread = section.querySelector('.aov-thread');
  var trunkPath = section.querySelector('#aov4-fork-trunk');
  var suitePath = section.querySelector('#aov4-fork-branch-suite');
  var uniquePath = section.querySelector('#aov4-fork-branch-unique');
  var substrate = section.querySelector('.aov-substrate');
  var suiteHaze = section.querySelector('.aov-haze--suite');
  var uniqueHaze = section.querySelector('.aov-haze--unique');
  var scenes = Array.prototype.slice.call(section.querySelectorAll('[data-aov-scene]'));
  var terminalScene = section.querySelector('[data-aov-scene="paired-6"]');
  var parallaxLayers = [substrate, suiteHaze, uniqueHaze].filter(Boolean);
  var sectionMetrics = { top: 0, height: 1 };
  var frame = 0;
  var motionAttached = false;
  var sectionIsNear = false;
  var sectionObserver = null;
  var forkGeometry = {
    desktop: {
      viewBox: '0 0 3840 2160',
      trunk: 'M1920 2030 L1920 1253',
      suite: 'M1920 1253 C1805 1080 1306 691 1018 389',
      unique: 'M1920 1253 C2035 1080 2534 691 2822 389'
    },
    mobile: {
      viewBox: '0 0 1500 2000',
      trunk: 'M750 1840 L750 1140',
      suite: 'M750 1140 C690 980 480 680 375 400',
      unique: 'M750 1140 C810 980 1020 680 1125 400'
    }
  };

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function applyForkGeometry() {
    var geometry = mobileQuery.matches ? forkGeometry.mobile : forkGeometry.desktop;
    if (thread) thread.setAttribute('viewBox', geometry.viewBox);
    if (trunkPath) trunkPath.setAttribute('d', geometry.trunk);
    if (suitePath) suitePath.setAttribute('d', geometry.suite);
    if (uniquePath) uniquePath.setAttribute('d', geometry.unique);
  }

  function measure() {
    var rect = section.getBoundingClientRect();
    sectionMetrics.top = rect.top + window.scrollY;
    sectionMetrics.height = section.offsetHeight;
    requestFrame();
  }

  function setPathProgress(path, progress) {
    if (!path) return;
    path.style.strokeDasharray = '1';
    path.style.strokeDashoffset = (1 - clamp(progress, 0, 1)).toFixed(4);
  }

  function setGateProgress(progress) {
    if (!terminalScene) return;
    var gates = Array.prototype.slice.call(terminalScene.querySelectorAll('.aov-gate'));
    gates.forEach(function (gate) {
      var predicates = Array.prototype.slice.call(gate.children);
      predicates.forEach(function (predicate, index) {
        var threshold = (index + 1) / (predicates.length + 1);
        predicate.classList.toggle('is-open', progress >= threshold);
      });
    });
  }

  function setLayerHints(active) {
    var shouldHint = active && !reduceQuery.matches;
    parallaxLayers.forEach(function (layer) {
      layer.style.willChange = shouldHint ? 'transform' : 'auto';
    });
  }

  function draw() {
    frame = 0;
    var viewportHeight = Math.max(1, window.innerHeight);
    var scrollRange = Math.max(1, sectionMetrics.height - viewportHeight);
    var sectionProgress = clamp((window.scrollY - sectionMetrics.top) / scrollRange, 0, 1);
    var reduce = reduceQuery.matches;
    var mobile = mobileQuery.matches;

    if (reduce) {
      setPathProgress(trunkPath, 1);
      setPathProgress(suitePath, 1);
      setPathProgress(uniquePath, 1);
      setGateProgress(1);
      if (substrate) substrate.style.transform = 'translate3d(0, 0, 0)';
      if (suiteHaze) suiteHaze.style.transform = 'translate3d(0, 0, 0)';
      if (uniqueHaze) uniqueHaze.style.transform = 'translate3d(0, 0, 0)';
      if (suiteHaze) suiteHaze.style.opacity = '0.18';
      if (uniqueHaze) uniqueHaze.style.opacity = '0.18';
      return;
    }

    setPathProgress(trunkPath, clamp(sectionProgress / 0.4, 0, 1));
    setPathProgress(suitePath, clamp((sectionProgress - 0.4) / 0.6, 0, 1));
    setPathProgress(uniquePath, clamp((sectionProgress - 0.4) / 0.6, 0, 1));

    if (!mobile) {
      var drift = sectionProgress * viewportHeight;
      if (substrate) substrate.style.transform = 'translate3d(0, ' + (-drift * 0.15).toFixed(1) + 'px, 0)';
      if (suiteHaze) suiteHaze.style.transform = 'translate3d(0, ' + (-drift * 0.25).toFixed(1) + 'px, 0)';
      if (uniqueHaze) uniqueHaze.style.transform = 'translate3d(0, ' + (-drift * 0.25).toFixed(1) + 'px, 0)';
    }

    var divergenceProgress = clamp((sectionProgress - 0.38) / 0.12, 0, 1);
    if (suiteHaze) suiteHaze.style.opacity = (0.18 - divergenceProgress * 0.05).toFixed(3);
    if (uniqueHaze) uniqueHaze.style.opacity = (divergenceProgress * 0.2).toFixed(3);

    scenes.forEach(function (scene) {
      var rect = scene.getBoundingClientRect();
      var localProgress = clamp((viewportHeight - rect.top) / (rect.height + viewportHeight), 0, 1);
      scene.style.setProperty('--aov-scene-progress', localProgress.toFixed(4));
    });

    if (terminalScene) {
      var terminalRect = terminalScene.getBoundingClientRect();
      var terminalRange = Math.max(1, terminalRect.height - viewportHeight);
      var terminalProgress = clamp(-terminalRect.top / terminalRange, 0, 1);
      setGateProgress(terminalProgress);
    }
  }

  function requestFrame() {
    if (frame) return;
    frame = window.requestAnimationFrame(draw);
  }

  function attachMotion() {
    if (motionAttached || reduceQuery.matches) return;
    window.addEventListener('scroll', requestFrame, { passive: true });
    motionAttached = true;
    requestFrame();
  }

  function detachMotion() {
    if (motionAttached) {
      window.removeEventListener('scroll', requestFrame);
      motionAttached = false;
    }
    if (frame) {
      window.cancelAnimationFrame(frame);
      frame = 0;
    }
  }

  function handleReduceChange() {
    if (reduceQuery.matches) {
      detachMotion();
      setLayerHints(false);
      draw();
      return;
    }

    if (sectionIsNear) attachMotion();
    setLayerHints(sectionIsNear);
    measure();
  }

  function handleViewportChange() {
    applyForkGeometry();
    measure();
  }

  if ('IntersectionObserver' in window) {
    section.classList.add('aov--motion-ready');
    var sceneObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        entry.target.classList.toggle('is-active', entry.isIntersecting);
      });
    }, { rootMargin: '-12% 0px -12% 0px', threshold: 0.08 });

    scenes.forEach(function (scene) {
      sceneObserver.observe(scene);
    });

    sectionObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        sectionIsNear = entry.isIntersecting;
        section.classList.toggle('aov--active', sectionIsNear);
        setLayerHints(sectionIsNear);
        if (sectionIsNear) {
          attachMotion();
          requestFrame();
        } else {
          detachMotion();
        }
      });
    }, { rootMargin: '100% 0px', threshold: 0 });
    sectionObserver.observe(section);
  } else {
    sectionIsNear = true;
    section.classList.add('aov--active');
    scenes.forEach(function (scene) {
      scene.classList.add('is-active');
    });
    attachMotion();
  }

  window.addEventListener('resize', measure, { passive: true });
  reduceQuery.addEventListener('change', handleReduceChange);
  mobileQuery.addEventListener('change', handleViewportChange);

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      detachMotion();
    } else if (sectionIsNear) {
      attachMotion();
      measure();
    }
  });

  applyForkGeometry();
  if (reduceQuery.matches) {
    draw();
  } else if (!sectionObserver) {
    attachMotion();
  }
  measure();
})();

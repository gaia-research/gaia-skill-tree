/* ───────────────────────────────────────────────────────────────────────
   index-rail.js — wires the universal AlphaRail (js/alpha-rail.js) to the
   landing page as a single, page-wide index.

   • Scroll is GLOBAL: the rail follows the whole document scroll.
   • Markers above the explorer are the page's section headers (small dots that
     reveal their label on magnify); the "Named Skills Explorer" marker is the
     red divider accent.
   • Markers inside the explorer are dynamic — they mirror whatever the Named
     Skills Explorer is currently showing (type glyphs, A-Z letters, or DAG
     tiers), rebuilt on every view / sort / filter / search change via the
     `gaia:explorer-rendered` event dispatched by js/named-skills.js.

   Marker weights are proportional to each region's real scroll distance, so the
   rail doubles as a minimap and follow(p) stays aligned with the page.
   ─────────────────────────────────────────────────────────────────────── */
(function () {
  "use strict";

  if (!window.AlphaRail || !document.getElementById("named")) return;

  var REDUCED = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Fixed section markers, top → bottom. The explorer's own markers are
  // appended after these on every rebuild.
  var SECTIONS = [
    { key: "sec:paths",          label: "Register Your Repo",    targetId: "paths" },
    { key: "sec:ultimates",      label: "Claim an Ultimate",     targetId: "ultimates" },
    { key: "sec:hall-of-heroes", label: "Hall of Heroes",        targetId: "hall-of-heroes" },
    { key: "sec:ascension",      label: "The Ascension Cycle",   targetId: "ascension" },
    { key: "sec:named",          label: "Named Skills Explorer", targetId: "named", accent: "red" }
  ];

  var byKey = {};

  function onSelect(key) {
    var m = byKey[key];
    if (!m) return;
    var el = document.getElementById(m.targetId);
    if (el) el.scrollIntoView({ behavior: REDUCED ? "auto" : "smooth", block: "start" });
  }

  function docMax() {
    return Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
  }

  // Continuous scrub: dragging the rail scrolls the page proportionally to the
  // pointer (the in-between ticks are live positions), rather than snapping to a
  // header. follow() is suppressed while held (see the scroll listener) so the
  // strip stays put and the scroll stays smooth.
  //
  // pointermove fires many times per frame (especially on touch) with sub-pixel
  // jitter, and a synchronous scrollTo per event reflows + shakes. So we just
  // record the latest target here and let a single rAF apply it once per frame,
  // easing toward it to absorb finger tremor. docMax is cached at grab time so
  // we never read scrollHeight mid-drag.
  var scrubActive = false, scrubTargetY = 0, scrubMax = 0, scrubRAF = null;

  function scrubStep() {
    scrubRAF = null;
    var cur = window.scrollY || window.pageYOffset;
    var diff = scrubTargetY - cur;
    var next = Math.abs(diff) < 0.5 ? scrubTargetY : cur + diff * 0.35;
    if (next !== cur) window.scrollTo(0, next);
    // Keep stepping until we've settled on the latest target.
    if (scrubActive && Math.abs(scrubTargetY - (window.scrollY || window.pageYOffset)) >= 0.5) {
      scrubRAF = requestAnimationFrame(scrubStep);
    }
  }

  function onScrub(p) {
    if (!scrubActive) { scrubActive = true; scrubMax = docMax(); }
    scrubTargetY = p * scrubMax;
    if (scrubRAF == null) scrubRAF = requestAnimationFrame(scrubStep);
  }

  function onScrubEnd() {
    scrubActive = false;
    if (scrubRAF != null) { cancelAnimationFrame(scrubRAF); scrubRAF = null; }
    window.scrollTo(0, scrubTargetY);   // land exactly on the released position
    syncRail(true);
  }

  var rail = new window.AlphaRail({
    side: "right", onSelect: onSelect, onScrub: onScrub, onScrubEnd: onScrubEnd
  });

  // Map a section descriptor to a rail marker (the red accent marker carries
  // the honor-red token; the rest are muted dots).
  function sectionMark(s) {
    return {
      key: s.key, label: s.label, kind: "section",
      color: s.accent === "red" ? "var(--honor-red)" : "var(--muted)",
      accent: s.accent, targetId: s.targetId
    };
  }

  // Weight each marker by the scroll distance it spans, so ticks are dense
  // where the page is tall (the explorer) and sparse where it is short.
  function applyDistanceWeights(list) {
    var tops = list.map(function (m) {
      var el = m.targetId && document.getElementById(m.targetId);
      if (!el) return null;
      return el.getBoundingClientRect().top + (window.scrollY || window.pageYOffset);
    });
    var docBottom = document.documentElement.scrollHeight;
    for (var i = 0; i < list.length; i++) {
      var top = tops[i];
      var next = (i + 1 < list.length && tops[i + 1] != null) ? tops[i + 1] : docBottom;
      var span = (top != null) ? Math.max(0, next - top) : 0;
      list[i].weight = Math.max(1, Math.round(span / 28));   // ~28px of page per tick
    }
  }

  function rebuild() {
    var marks = SECTIONS.map(sectionMark)
      .concat(window._gaiaExplorerMarkers || []);
    byKey = {};
    marks.forEach(function (m) { byKey[m.key] = m; });
    applyDistanceWeights(marks);
    rail.renderMarkers(marks);
    syncRail(true);
  }

  // Continuous global scroll-follow.
  function syncRail(instant) {
    var max = docMax();
    var p = max > 0 ? (window.scrollY || window.pageYOffset) / max : 0;
    rail.follow(p, instant);
  }

  var followQueued = false;
  window.addEventListener("scroll", function () {
    if (rail._scrubbing) return;   // the user is driving the scroll; don't fight it
    if (followQueued) return;
    followQueued = true;
    requestAnimationFrame(function () { followQueued = false; syncRail(false); });
  }, { passive: true });

  // Rebuild whenever the explorer re-renders, and once data has settled.
  document.addEventListener("gaia:explorer-rendered", rebuild);

  var resizeT;
  window.addEventListener("resize", function () {
    clearTimeout(resizeT);
    resizeT = setTimeout(rebuild, 150);
  });

  // Initial paint (section markers show immediately; explorer markers fold in
  // when named-skills.js finishes its fetch and fires the event).
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", rebuild);
  } else {
    rebuild();
  }
})();

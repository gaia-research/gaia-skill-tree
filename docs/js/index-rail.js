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

  if (!window.AlphaRail || !document.getElementById("paths")) return;

  var REDUCED = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Fixed section markers, top → bottom. The explorer's own markers are
  // appended after these on every rebuild.
  var SECTIONS = [
    { key: "sec:hall-of-heroes", label: "Hall of Heroes",        targetId: "hall-of-heroes" },
    { key: "sec:trust-preview",   label: "Trust Ledger",          targetId: "trust-preview" },
    { key: "sec:paths",          label: "Register Your Repo",    targetId: "paths" },
    { key: "sec:ultimates",      label: "Claim an Ultimate",     targetId: "ultimates" },
    { key: "sec:review-showcase", label: "Review Gate",          targetId: "review-showcase" },
    { key: "sec:ascension",      label: "The Ascension Cycle",   targetId: "ascension" },
    { key: "sec:evidence-cycle", label: "The Evidence Grade Cycle", targetId: "evidence-cycle" },
    { key: "sec:meta-reports",   label: "Meta Reports",          targetId: "meta-reports", accent: "red" }
  ];

  var byKey = {};
  // True document offsets (px) of the first and last markers. The rail is
  // mapped against these — not scrollY/scrollMax — so a marker sits at the
  // viewport centre exactly when its section is centred (coherent positioning,
  // no drift partway down the page).
  var firstOff = 0, lastOff = 1;

  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }

  function onSelect(key) {
    var m = byKey[key];
    if (!m) return;
    var el = document.getElementById(m.targetId);
    if (el) el.scrollIntoView({ behavior: REDUCED ? "auto" : "smooth", block: "start" });
  }

  function docMax() {
    return Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
  }
  // Scroll position that puts rail-fraction p at the viewport centre.
  function scrollForP(p) {
    return clamp(firstOff + p * (lastOff - firstOff) - window.innerHeight / 2, 0, docMax());
  }
  // Rail-fraction for the current scroll (viewport centre vs the marker span).
  function pForScroll() {
    var span = lastOff - firstOff;
    if (span <= 0) return 0;
    var center = (window.scrollY || window.pageYOffset) + window.innerHeight / 2;
    return clamp((center - firstOff) / span, 0, 1);
  }

  // Continuous scrub: dragging the rail scrolls the page to the matching real
  // position. The scrub maps against a frozen frame (rail._scrubRefTy), so the
  // strip can parallax with the scroll without feedback. pointermove fires many
  // times per frame, so we apply the latest target once per rAF. On a mouse we
  // move directly (tracks the cursor 1:1); on touch we low-pass lightly so
  // finger tremor doesn't shake the page — fast enough to still follow, without
  // the old easing lag.
  var scrubActive = false, scrubTargetY = 0, scrubRAF = null;

  function scrubStep() {
    scrubRAF = null;
    if (!scrubActive) return;
    var cur = window.scrollY || window.pageYOffset;
    var ease = rail._touch ? 0.55 : 1;
    var next = cur + (scrubTargetY - cur) * ease;
    if (Math.abs(scrubTargetY - next) < 0.5) next = scrubTargetY;
    window.scrollTo(0, Math.round(next));
    if (scrubActive && Math.abs(scrubTargetY - (window.scrollY || window.pageYOffset)) >= 0.5) {
      scrubRAF = requestAnimationFrame(scrubStep);
    }
  }

  function onScrub(p) {
    scrubActive = true;
    scrubTargetY = scrollForP(p);
    if (scrubRAF == null) scrubRAF = requestAnimationFrame(scrubStep);
  }

  function onScrubEnd() {
    scrubActive = false;
    if (scrubRAF != null) { cancelAnimationFrame(scrubRAF); scrubRAF = null; }
    window.scrollTo(0, scrubTargetY);   // land exactly on the released position
    syncRail();
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
    var base = window.scrollY || window.pageYOffset;
    var tops = list.map(function (m) {
      var el = m.targetId && document.getElementById(m.targetId);
      if (!el) return null;
      return el.getBoundingClientRect().top + base;
    });
    var docBottom = document.documentElement.scrollHeight;
    for (var i = 0; i < list.length; i++) {
      var top = tops[i];
      var next = (i + 1 < list.length && tops[i + 1] != null) ? tops[i + 1] : docBottom;
      var span = (top != null) ? Math.max(0, next - top) : 0;
      list[i].weight = Math.max(1, Math.round(span / 28));   // ~28px of page per tick
    }
    // Cache the marker span so follow()/scrub map to true page positions.
    var present = tops.filter(function (t) { return t != null; });
    if (present.length) {
      firstOff = present[0];
      lastOff = Math.max(present[present.length - 1], firstOff + 1);
    }
  }

  function rebuild() {
    var marks = SECTIONS.map(sectionMark)
      .concat(window._gaiaExplorerMarkers || []);
    byKey = {};
    marks.forEach(function (m) { byKey[m.key] = m; });
    applyDistanceWeights(marks);
    rail.renderMarkers(marks);
    syncRail();
  }

  // Real-time parallax follow: the strip is translated to the true scroll
  // position every frame (instant — no CSS glide), so a normal browser scroll
  // moves the rail up smoothly in lockstep instead of chasing/jumping. The rail
  // travels less than the page (its span < the document), giving the parallax.
  function syncRail() { rail.follow(pForScroll(), true); }

  var followQueued = false;
  window.addEventListener("scroll", function () {
    // follow() runs even during a scrub: the scrub maps against a frozen frame
    // (rail._scrubRefTy), so the strip can parallax with the scroll it drives
    // without the input drifting. This also avoids any snap on release.
    if (followQueued) return;
    followQueued = true;
    requestAnimationFrame(function () { followQueued = false; syncRail(); });
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

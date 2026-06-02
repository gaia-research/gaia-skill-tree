/* ───────────────────────────────────────────────────────────────────────
   AlphaRail — universal alphabetical scrubber (no dependencies).

   Usage:
     var rail = new AlphaRail({
       side: "right",                       // "right" | "left"
       onSelect: function (letter, instant) {} // user tapped/scrubbed a letter
     });
     rail.render({ A: 17, B: 4, ... });      // letter -> entry count
     rail.follow(progress);                  // 0..1 scroll progress (smooth wheel)

   Behaviour:
     • Letters spaced proportionally (tick fillers ∝ count) with uniform ticks.
     • follow(p) glides the strip so the matching letter sits near the vertical
       centre — continuous, so it tracks the user's scroll instead of snapping.
       The strip overflows + fades off the top/bottom edges (wheel feel).
     • Hover/scrub magnifies nearest items like a macOS dock; magnified letters
       pop toward the content (and bigger on touch, so a finger doesn't hide it).
     • Tap a letter or drag along the rail to scrub; both fire onSelect.
   ─────────────────────────────────────────────────────────────────────── */
(function (global) {
  "use strict";

  var ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

  function AlphaRail(opts) {
    opts = opts || {};
    this.side = opts.side === "left" ? "left" : "right";
    this.onSelect = typeof opts.onSelect === "function" ? opts.onSelect : function () {};
    // Optional continuous-scrub hooks. When onScrub is supplied, dragging the
    // rail reports a smooth 0..1 progress instead of snapping to the nearest
    // marker — the in-between ticks become live scrub positions. Tap-to-jump
    // (onSelect) still fires for a click without a drag.
    this.onScrub = typeof opts.onScrub === "function" ? opts.onScrub : null;
    this.onScrubEnd = typeof opts.onScrubEnd === "function" ? opts.onScrubEnd : function () {};
    this.tickPer = opts.tickPer || 1;        // ticks per unit of count
    this.maxScale = opts.maxScale || 2.7;    // dock peak magnification (mouse)
    this.radius = opts.radius || 82;         // px magnify falloff radius
    this.pop = opts.pop || 26;               // px the peak item pops toward content
    this.reduced = !!(global.matchMedia &&
      global.matchMedia("(prefers-reduced-motion: reduce)").matches);

    this.active = null;
    this._p = 0;             // last scroll progress 0..1
    this._ty = 0;            // current track translateY
    this._touch = false;
    this._scrubbing = false;
    this._dragged = false;   // pointer moved during this press (drag vs click)
    this._scrubRefTy = 0;    // track translate captured at grab time (scrub frame)
    this._raf = null;
    this._pointerY = null;
    this._present = [];      // present (selectable) marker keys in order
    this._keys = [];         // all marker keys in order (incl. disabled empties)
    this._centers = [];      // item centre offsets within the track
    this._markEls = {};      // key -> marker button element
    this._markCenter = {};   // key -> centre offset within the track
    this._letterMode = false;// legacy A-Z render(counts) compatibility flag
    this._firstCenter = 0;
    this._lastCenter = 0;

    this._build(opts.mount || document.body);
  }

  AlphaRail.prototype._build = function (mount) {
    var el = document.createElement("div");
    el.className = "arail";
    el.setAttribute("data-side", this.side);
    el.setAttribute("role", "navigation");
    el.setAttribute("aria-label", "Alphabetical index");

    var track = document.createElement("div");
    track.className = "arail-track";
    el.appendChild(track);
    mount.appendChild(el);

    document.body.setAttribute("data-arail", this.side);

    this.el = el;
    this.track = track;
    this._wire();
  };

  // Legacy A-Z adapter: builds letter markers (and disabled empties) from a
  // { letter: count } map, then delegates to renderMarkers. Behaviour is kept
  // byte-for-byte so existing callers (starless.html) are unaffected.
  AlphaRail.prototype.render = function (counts) {
    counts = counts || {};
    this._letterMode = true;
    // Letters carry no --mark-color: CSS resolves resting = --muted and
    // aria-current = --tier-basic via fallbacks, matching the original rail.
    var markers = ALPHA.map(function (L) {
      var c = counts[L] || 0;
      return { key: L, label: L, glyph: L, kind: "letter", weight: c, empty: c <= 0 };
    });
    this.renderMarkers(markers, { _internal: true });
  };

  // Generic core: render an arbitrary, ordered list of keyed markers.
  //   markers: [{ key, label, glyph, color, weight, kind, accent, empty }]
  //     key    - identifier passed to onSelect/setActive (unique).
  //     label  - full text revealed on magnify (section/group markers).
  //     glyph  - single-char face for letter/group markers (sections use a dot).
  //     color  - CSS var string assigned to --mark-color (never a literal hex).
  //     weight - proportional tick fillers after the marker (>= 0).
  //     kind   - "section" | "group" | "letter" (drives CSS chrome).
  //     accent - optional flag (e.g. "red") for a divider accent marker.
  //     empty  - disabled placeholder (legacy A-Z greyed letters).
  AlphaRail.prototype.renderMarkers = function (markers, opts) {
    markers = markers || [];
    opts = opts || {};
    var self = this;
    this.track.innerHTML = "";
    this._markEls = {};
    this._markCenter = {};
    this._present = [];
    this._keys = [];
    if (!opts._internal) this._letterMode = false;

    markers.forEach(function (m) {
      var kind = m.kind || "letter";
      var empty = !!m.empty;

      var b = document.createElement("button");
      b.type = "button";
      b.className = "arail-mark" + (empty ? " is-empty" : "");
      b.setAttribute("data-key", m.key);
      b.setAttribute("data-kind", kind);
      if (m.accent) b.setAttribute("data-accent", m.accent);
      b.setAttribute("aria-label", "Jump to " + (m.label != null ? m.label : m.key));
      if (m.color) b.style.setProperty("--mark-color", m.color);

      // Glyph/letter face. Sections render a dot via CSS, so leave it blank.
      var face = document.createElement("span");
      face.className = "arail-mark-glyph";
      face.textContent = kind === "section" ? "" : (m.glyph != null ? m.glyph : "");
      b.appendChild(face);

      // Full label, revealed on magnify (section + group markers only — letters
      // already show their full content, matching the legacy A-Z rail).
      if (m.label != null && m.label !== "" && (kind === "section" || kind === "group")) {
        var lab = document.createElement("span");
        lab.className = "arail-mark-label";
        lab.textContent = m.label;
        b.appendChild(lab);
      }

      self._keys.push(m.key);
      self._markEls[m.key] = b;
      if (!empty) {
        self._present.push(m.key);
        b.addEventListener("click", function () {
          if (self._dragged) return;   // a drag-scrub already moved the view
          self.select(m.key, false);
        });
      } else {
        b.disabled = true;
      }
      self.track.appendChild(b);

      var ticks = m.weight > 0 ? Math.max(1, Math.round(m.weight * self.tickPer)) : 0;
      for (var i = 0; i < ticks; i++) {
        var t = document.createElement("span");
        t.className = "arail-tick";
        self.track.appendChild(t);
      }
    });

    this.items = [].slice.call(this.track.children);
    this._measure();
    this.follow(undefined, true);   // position instantly at current progress
  };

  // Cache transform-independent geometry (offsetTop ignores scale transforms).
  AlphaRail.prototype._measure = function () {
    var self = this;
    this._centers = this.items.map(function (it) {
      return it.offsetTop + it.offsetHeight / 2;
    });
    this._markCenter = {};
    this._keys.forEach(function (k) {
      var b = self._markEls[k];
      self._markCenter[k] = b.offsetTop + b.offsetHeight / 2;
    });
    if (this._present.length) {
      this._firstCenter = this._markCenter[this._present[0]];
      this._lastCenter = this._markCenter[this._present[this._present.length - 1]];
    }
  };

  // Continuous scroll-follow: p in 0..1 maps across the present-letter span.
  // The strip glides (CSS transition) so it tracks the user smoothly.
  AlphaRail.prototype.follow = function (p, instant) {
    if (typeof p === "number") this._p = Math.max(0, Math.min(1, p));
    if (!this._present.length) return;

    var pos = this._firstCenter + this._p * (this._lastCenter - this._firstCenter);
    this._ty = (global.innerHeight / 2) - pos;

    if (instant || this.reduced) {
      var prev = this.track.style.transition;
      this.track.style.transition = "none";
      this.track.style.transform = "translateY(" + this._ty + "px)";
      void this.track.offsetHeight;        // commit, so later transitions start here
      this.track.style.transition = prev;
    } else {
      this.track.style.transform = "translateY(" + this._ty + "px)";
    }

    // Star/highlight sits on the present marker nearest the centre.
    var best = null, bd = Infinity;
    for (var i = 0; i < this._present.length; i++) {
      var d = Math.abs(this._markCenter[this._present[i]] - pos);
      if (d < bd) { bd = d; best = this._present[i]; }
    }
    if (best && best !== this.active) { this.active = best; this._highlight(); }
  };

  // User-driven selection (tap/scrub/click). Highlights now; onSelect scrolls
  // the host, whose scroll then drives follow() — so motion stays smooth.
  AlphaRail.prototype.select = function (L, instant) {
    if (!L || !this._markEls[L] || this._markEls[L].disabled) return;
    this.active = L;
    this._highlight();
    this.onSelect(L, !!instant);
  };

  // Optional external highlight hook (no scroll side effect).
  AlphaRail.prototype.setActive = function (L) {
    if (!L || L === this.active || !this._markEls[L]) return;
    this.active = L;
    this._highlight();
  };

  AlphaRail.prototype._highlight = function () {
    for (var i = 0; i < this._keys.length; i++) {
      var k = this._keys[i];
      var b = this._markEls[k];
      if (b) b.setAttribute("aria-current", k === this.active ? "true" : "false");
    }
  };

  // ── Magnify (macOS dock). Reads cached centres only — no layout thrash. ──
  AlphaRail.prototype._applyMagnify = function () {
    this._raf = null;
    var y = this._pointerY;
    var dir = this.side === "right" ? -1 : 1;
    // Touch boost: a fingertip hides the rail, so pop bigger and scale harder.
    var maxScale = this._touch ? this.maxScale * 1.3 : this.maxScale;
    var radius = this._touch ? this.radius * 1.25 : this.radius;
    var pop = this._touch ? this.pop * 1.9 : this.pop;

    for (var i = 0; i < this.items.length; i++) {
      var it = this.items[i];
      var s = 1, tx = 0, bright = false;
      if (y != null) {
        var d = Math.abs((this._ty + this._centers[i]) - y);
        if (d < radius) {
          var f = 1 - d / radius;              // 1 at pointer → 0 at edge
          s = 1 + (maxScale - 1) * f * f;       // eased peak
          tx = dir * pop * f;
          bright = f > 0.4;
        }
      }
      it.style.transform = "translateX(" + tx + "px) scale(" + s + ")";
      if (it.className.indexOf("arail-mark") === 0) {
        // Legacy letters brighten to text colour; group/section markers keep
        // their token tint and instead reveal their full label on approach.
        if (it.getAttribute("data-kind") === "letter") {
          it.style.color = bright ? "var(--text)" : "";
        }
        // Brighten the label on approach; otherwise clear the inline value so
        // it falls back to its always-visible resting opacity (CSS).
        var lab = it.querySelector(".arail-mark-label");
        if (lab) lab.style.opacity = bright ? Math.min(1, f * 1.4).toFixed(2) : "";
      }
    }
  };

  AlphaRail.prototype._scheduleMagnify = function (y) {
    this._pointerY = y;
    if (!this._raf) this._raf = global.requestAnimationFrame(this._applyMagnify.bind(this));
  };

  AlphaRail.prototype._scrubTo = function (y) {
    if (!this._present.length) return;

    // Continuous mode: map the pointer to a smooth 0..1 progress across the
    // marker span and hand it back. The mapping uses the translate captured at
    // grab time (_scrubRefTy), not the live _ty — so follow() may keep running
    // (the strip parallaxes with the scroll the scrub causes) without the input
    // mapping drifting, i.e. no feedback oscillation.
    if (this.onScrub) {
      var span = this._lastCenter - this._firstCenter;
      var ref = this._scrubbing ? this._scrubRefTy : this._ty;
      var p = span > 0 ? ((y - ref) - this._firstCenter) / span : 0;
      this.onScrub(Math.max(0, Math.min(1, p)));
      return;
    }

    // Legacy mode: snap to the nearest present marker (A-Z rail).
    var best = null, bestD = Infinity;
    for (var i = 0; i < this._present.length; i++) {
      var L = this._present[i];
      var d = Math.abs((this._ty + this._markCenter[L]) - y);
      if (d < bestD) { bestD = d; best = L; }
    }
    if (best) this.select(best, true);   // instant scroll while scrubbing
  };

  AlphaRail.prototype._wire = function () {
    var self = this;
    var t = this.track;

    t.addEventListener("pointermove", function (e) {
      self._touch = e.pointerType === "touch";
      self._scheduleMagnify(e.clientY);
      if (self._scrubbing) { self._dragged = true; self._scrubTo(e.clientY); }
    });
    t.addEventListener("pointerleave", function () {
      if (!self._scrubbing) self._scheduleMagnify(null);
    });
    t.addEventListener("pointerdown", function (e) {
      self._touch = e.pointerType === "touch";
      self._scrubbing = true;
      self._dragged = false;
      self._scrubRefTy = self._ty;     // freeze the input frame for this drag
      try { t.setPointerCapture(e.pointerId); } catch (_) {}
      self._scrubTo(e.clientY);
      self._scheduleMagnify(e.clientY);
      e.preventDefault();
    });
    function end(e) {
      if (!self._scrubbing) return;
      self._scrubbing = false;
      try { t.releasePointerCapture(e.pointerId); } catch (_) {}
      self._scheduleMagnify(null);          // relax magnification
      if (self._dragged && self.onScrub) self.onScrubEnd();   // settle the rail
    }
    t.addEventListener("pointerup", end);
    t.addEventListener("pointercancel", end);

    global.addEventListener("resize", function () {
      self._measure();
      self.follow(undefined, true);
    });
  };

  global.AlphaRail = AlphaRail;
})(window);

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
    this._raf = null;
    this._pointerY = null;
    this._present = [];      // present letters in order
    this._centers = [];      // item centre offsets within the track
    this._letterCenter = {}; // letter -> centre offset within the track
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

  // Rebuild from a { letter: count } map.
  AlphaRail.prototype.render = function (counts) {
    counts = counts || {};
    var self = this;
    this.track.innerHTML = "";
    this.letterEls = {};
    this._present = [];

    ALPHA.forEach(function (L) {
      var c = counts[L] || 0;

      var b = document.createElement("button");
      b.type = "button";
      b.className = "arail-letter" + (c > 0 ? "" : " is-empty");
      b.setAttribute("data-letter", L);
      b.setAttribute("aria-label", "Jump to " + L);
      b.textContent = L;
      if (c > 0) {
        self._present.push(L);
        b.addEventListener("click", function () { self.select(L, false); });
      } else {
        b.disabled = true;
      }
      self.track.appendChild(b);
      self.letterEls[L] = b;

      var ticks = c > 0 ? Math.max(1, Math.round(c * self.tickPer)) : 0;
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
    this._letterCenter = {};
    this._present.forEach(function (L) {
      var b = self.letterEls[L];
      self._letterCenter[L] = b.offsetTop + b.offsetHeight / 2;
    });
    if (this._present.length) {
      this._firstCenter = this._letterCenter[this._present[0]];
      this._lastCenter = this._letterCenter[this._present[this._present.length - 1]];
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

    // Star/highlight sits on the present letter nearest the centre.
    var best = null, bd = Infinity;
    for (var i = 0; i < this._present.length; i++) {
      var d = Math.abs(this._letterCenter[this._present[i]] - pos);
      if (d < bd) { bd = d; best = this._present[i]; }
    }
    if (best && best !== this.active) { this.active = best; this._highlight(); }
  };

  // User-driven selection (tap/scrub/click). Highlights now; onSelect scrolls
  // the host, whose scroll then drives follow() — so motion stays smooth.
  AlphaRail.prototype.select = function (L, instant) {
    if (!L || !this.letterEls[L] || this.letterEls[L].disabled) return;
    this.active = L;
    this._highlight();
    this.onSelect(L, !!instant);
  };

  // Optional external highlight hook (no scroll side effect).
  AlphaRail.prototype.setActive = function (L) {
    if (!L || L === this.active || !this.letterEls[L]) return;
    this.active = L;
    this._highlight();
  };

  AlphaRail.prototype._highlight = function () {
    for (var i = 0; i < ALPHA.length; i++) {
      var b = this.letterEls[ALPHA[i]];
      if (b) b.setAttribute("aria-current", ALPHA[i] === this.active ? "true" : "false");
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
      if (it.className.indexOf("arail-letter") === 0) {
        it.style.color = bright ? "var(--text)" : "";
      }
    }
  };

  AlphaRail.prototype._scheduleMagnify = function (y) {
    this._pointerY = y;
    if (!this._raf) this._raf = global.requestAnimationFrame(this._applyMagnify.bind(this));
  };

  AlphaRail.prototype._scrubTo = function (y) {
    var best = null, bestD = Infinity;
    for (var i = 0; i < this._present.length; i++) {
      var L = this._present[i];
      var d = Math.abs((this._ty + this._letterCenter[L]) - y);
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
      if (self._scrubbing) self._scrubTo(e.clientY);
    });
    t.addEventListener("pointerleave", function () {
      if (!self._scrubbing) self._scheduleMagnify(null);
    });
    t.addEventListener("pointerdown", function (e) {
      self._touch = e.pointerType === "touch";
      self._scrubbing = true;
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

/**
 * hero-animations.js — Per-hero bespoke particle animations
 * Canvas-based particle systems for Ultimate heroes.
 * CSS keyframes handle the card entrance; this script adds ambient particles.
 *
 * Each hero gets a unique particle behavior:
 *   garrytan/gstack → Constellation Assembly (dots drift, connect with lines)
 *   ruvnet/ruflo → Sovereign Emergence (vertical light beams, hex grid)
 *   mattpocock/skills → Type Forge (lightning arcs)
 *   obra/superpowers → Plugin Cascade (orbiting cards)
 *
 * Performance: max 120 particles, 30fps cap, paused off-screen.
 * Graceful degradation: canvas hidden on mobile (<820px) and prefers-reduced-motion.
 */
(function () {
  'use strict';

  var MAX_PARTICLES = 120;
  var TARGET_FPS = 30;
  var FRAME_INTERVAL = 1000 / TARGET_FPS;
  var controllers = [];

  // ── Utilities ─────────────────────────────────────────────────
  function shouldAnimate() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return false;
    if (window.innerWidth < 820) return false;
    return true;
  }

  function rand(min, max) {
    return Math.random() * (max - min) + min;
  }

  // ── Base controller ───────────────────────────────────────────
  function AnimController(canvas, behavior) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.behavior = behavior;
    this.particles = [];
    this.running = false;
    this.initialized = false;
    this.lastFrame = 0;
    this.raf = null;
    this._resize();
    this._boundResize = this._resize.bind(this);
    window.addEventListener('resize', this._boundResize);
  }

  AnimController.prototype._resize = function () {
    var rect = this.canvas.parentElement.getBoundingClientRect();
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.w = rect.width + 160;
    this.h = rect.height + 160;
    this.canvas.width = this.w * dpr;
    this.canvas.height = this.h * dpr;
    this.canvas.style.width = this.w + 'px';
    this.canvas.style.height = this.h + 'px';
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };

  AnimController.prototype.start = function () {
    if (this.running) return;
    this.running = true;
    if (!this.initialized) {
      this.behavior.init(this);
      this.initialized = true;
    }
    this._loop(performance.now());
  };

  AnimController.prototype.pause = function () {
    this.running = false;
    if (this.raf) {
      cancelAnimationFrame(this.raf);
      this.raf = null;
    }
  };

  AnimController.prototype.resume = function () {
    if (this.running) return;
    if (!this.initialized) {
      this.start();
      return;
    }
    this.running = true;
    this._loop(performance.now());
  };

  AnimController.prototype._loop = function (now) {
    if (!this.running) return;
    this.raf = requestAnimationFrame(this._loop.bind(this));
    var delta = now - this.lastFrame;
    if (delta < FRAME_INTERVAL) return;
    this.lastFrame = now - (delta % FRAME_INTERVAL);
    this.ctx.clearRect(0, 0, this.w, this.h);
    this.behavior.update(this, delta);
    this.behavior.draw(this);
  };

  AnimController.prototype.destroy = function () {
    this.pause();
    window.removeEventListener('resize', this._boundResize);
  };


  // ── Constellation Assembly (garrytan) ─────────────────────────
  var constellationBehavior = {
    init: function (ctrl) {
      ctrl.particles = [];
      var count = Math.min(MAX_PARTICLES, 60);
      for (var i = 0; i < count; i++) {
        ctrl.particles.push({
          x: rand(0, ctrl.w),
          y: rand(0, ctrl.h),
          tx: rand(ctrl.w * 0.25, ctrl.w * 0.75),
          ty: rand(ctrl.h * 0.25, ctrl.h * 0.75),
          vx: rand(-0.3, 0.3),
          vy: rand(-0.3, 0.3),
          size: rand(1.5, 3),
          alpha: rand(0.3, 0.8),
          phase: rand(0, Math.PI * 2)
        });
      }
    },
    update: function (ctrl, dt) {
      var t = performance.now() * 0.001;
      ctrl.particles.forEach(function (p) {
        // Drift toward target with gentle sine modulation
        p.x += (p.tx - p.x) * 0.002 + Math.sin(t + p.phase) * 0.2;
        p.y += (p.ty - p.y) * 0.002 + Math.cos(t + p.phase * 0.7) * 0.15;
        p.alpha = 0.3 + Math.sin(t * 0.8 + p.phase) * 0.25;
      });
    },
    draw: function (ctrl) {
      var ctx = ctrl.ctx;
      var particles = ctrl.particles;
      // Draw connection lines between nearby particles
      var connectionDist = 80;
      for (var i = 0; i < particles.length; i++) {
        for (var j = i + 1; j < particles.length; j++) {
          var dx = particles[i].x - particles[j].x;
          var dy = particles[i].y - particles[j].y;
          var dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < connectionDist) {
            var a = (1 - dist / connectionDist) * 0.15;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = 'rgba(251, 191, 36, ' + a + ')';
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      // Draw particles
      particles.forEach(function (p) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(251, 191, 36, ' + p.alpha + ')';
        ctx.fill();
      });
    }
  };


  // ── Sovereign Emergence (ruvnet) ──────────────────────────────
  var sovereignBehavior = {
    init: function (ctrl) {
      ctrl.particles = [];
      // Vertical beams
      var beamCount = 8;
      for (var i = 0; i < beamCount; i++) {
        ctrl.particles.push({
          type: 'beam',
          x: ctrl.w * (0.2 + (i / beamCount) * 0.6),
          phase: rand(0, Math.PI * 2),
          width: rand(1, 3),
          alpha: rand(0.05, 0.15)
        });
      }
      // Hex grid dots
      var hexCount = Math.min(MAX_PARTICLES - beamCount, 50);
      for (var j = 0; j < hexCount; j++) {
        ctrl.particles.push({
          type: 'hex',
          x: rand(0, ctrl.w),
          y: rand(0, ctrl.h),
          size: rand(1, 2),
          alpha: rand(0.1, 0.4),
          phase: rand(0, Math.PI * 2)
        });
      }
    },
    update: function (ctrl, dt) {
      var t = performance.now() * 0.001;
      ctrl.particles.forEach(function (p) {
        if (p.type === 'beam') {
          p.alpha = 0.05 + Math.sin(t * 0.5 + p.phase) * 0.08;
        } else {
          p.alpha = 0.1 + Math.sin(t * 0.6 + p.phase) * 0.2;
          p.y -= 0.1;
          if (p.y < -10) p.y = ctrl.h + 10;
        }
      });
    },
    draw: function (ctrl) {
      var ctx = ctrl.ctx;
      ctrl.particles.forEach(function (p) {
        if (p.type === 'beam') {
          ctx.beginPath();
          ctx.moveTo(p.x, 0);
          ctx.lineTo(p.x, ctrl.h);
          ctx.strokeStyle = 'rgba(251, 191, 36, ' + p.alpha + ')';
          ctx.lineWidth = p.width;
          ctx.stroke();
        } else {
          ctx.beginPath();
          // Draw hexagon
          for (var k = 0; k < 6; k++) {
            var angle = (Math.PI / 3) * k - Math.PI / 6;
            var hx = p.x + p.size * 3 * Math.cos(angle);
            var hy = p.y + p.size * 3 * Math.sin(angle);
            if (k === 0) ctx.moveTo(hx, hy);
            else ctx.lineTo(hx, hy);
          }
          ctx.closePath();
          ctx.strokeStyle = 'rgba(251, 191, 36, ' + p.alpha + ')';
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      });
    }
  };


  // ── Type Forge (mattpocock) ───────────────────────────────────
  var typeforgeBehavior = {
    init: function (ctrl) {
      ctrl.particles = [];
      var count = Math.min(MAX_PARTICLES, 40);
      for (var i = 0; i < count; i++) {
        ctrl.particles.push({
          x: rand(0, ctrl.w),
          y: rand(0, ctrl.h),
          tx: ctrl.w / 2 + rand(-80, 80),
          ty: ctrl.h / 2 + rand(-40, 40),
          speed: rand(0.5, 2),
          size: rand(1, 2.5),
          alpha: rand(0.2, 0.7),
          trail: [],
          maxTrail: Math.floor(rand(4, 10))
        });
      }
    },
    update: function (ctrl, dt) {
      ctrl.particles.forEach(function (p) {
        var dx = p.tx - p.x;
        var dy = p.ty - p.y;
        var dist = Math.sqrt(dx * dx + dy * dy);
        if (dist > 2) {
          p.x += (dx / dist) * p.speed;
          p.y += (dy / dist) * p.speed;
        } else {
          // Arrived — pick a new target near center
          p.tx = ctrl.w / 2 + rand(-120, 120);
          p.ty = ctrl.h / 2 + rand(-60, 60);
          p.x = rand(0, ctrl.w) > ctrl.w / 2 ? ctrl.w : 0;
          p.y = rand(0, ctrl.h);
        }
        p.trail.push({ x: p.x, y: p.y });
        if (p.trail.length > p.maxTrail) p.trail.shift();
      });
    },
    draw: function (ctrl) {
      var ctx = ctrl.ctx;
      ctrl.particles.forEach(function (p) {
        // Draw trail (lightning arc effect)
        if (p.trail.length > 1) {
          ctx.beginPath();
          ctx.moveTo(p.trail[0].x, p.trail[0].y);
          for (var i = 1; i < p.trail.length; i++) {
            ctx.lineTo(p.trail[i].x, p.trail[i].y);
          }
          ctx.strokeStyle = 'rgba(56, 189, 248, ' + (p.alpha * 0.4) + ')';
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
        // Draw head
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(56, 189, 248, ' + p.alpha + ')';
        ctx.fill();
      });
    }
  };


  // ── Plugin Cascade (obra) ─────────────────────────────────────
  var cascadeBehavior = {
    init: function (ctrl) {
      ctrl.particles = [];
      var count = Math.min(MAX_PARTICLES, 24);
      var cx = ctrl.w / 2;
      var cy = ctrl.h / 2;
      for (var i = 0; i < count; i++) {
        var angle = (Math.PI * 2 / count) * i;
        ctrl.particles.push({
          angle: angle,
          radius: rand(80, 160),
          speed: rand(0.003, 0.008),
          size: rand(4, 10),
          alpha: rand(0.15, 0.45),
          cx: cx,
          cy: cy
        });
      }
    },
    update: function (ctrl, dt) {
      ctrl.particles.forEach(function (p) {
        p.angle += p.speed;
        p.cx = ctrl.w / 2;
        p.cy = ctrl.h / 2;
      });
    },
    draw: function (ctrl) {
      var ctx = ctrl.ctx;
      ctrl.particles.forEach(function (p) {
        var x = p.cx + Math.cos(p.angle) * p.radius;
        var y = p.cy + Math.sin(p.angle) * p.radius;
        // Draw mini card (rounded rect)
        var w = p.size * 2.5;
        var h = p.size * 1.6;
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(p.angle);
        ctx.beginPath();
        ctx.roundRect(-w / 2, -h / 2, w, h, 2);
        ctx.fillStyle = 'rgba(251, 191, 36, ' + p.alpha + ')';
        ctx.fill();
        ctx.strokeStyle = 'rgba(251, 191, 36, ' + (p.alpha * 0.6) + ')';
        ctx.lineWidth = 0.5;
        ctx.stroke();
        ctx.restore();
      });
    }
  };

  // Behavior registry
  var BEHAVIORS = {
    'garrytan': constellationBehavior,
    'ruvnet': sovereignBehavior,
    'mattpocock': typeforgeBehavior,
    'obra': cascadeBehavior
  };

  // ── Bootstrap ─────────────────────────────────────────────────
  function initAnimations() {
    if (!shouldAnimate()) return;

    var canvases = document.querySelectorAll('.hero-card__canvas[data-hero]');
    canvases.forEach(function (canvas) {
      var handle = canvas.getAttribute('data-hero');
      var behavior = BEHAVIORS[handle];
      if (!behavior) return;

      var ctrl = new AnimController(canvas, behavior);
      controllers.push(ctrl);

      // Store reference on the stage for IntersectionObserver pause/resume
      var stage = canvas.closest('.hero-stage');
      if (stage) {
        stage._heroAnimCtrl = ctrl;
        // Start only if already visible
        if (stage.classList.contains('is-visible')) {
          ctrl.start();
        }
      }
    });

    // Listen for stage visibility changes
    document.addEventListener('heroes-stage-visible', function (e) {
      var stage = e.detail && e.detail.stage;
      if (stage && stage._heroAnimCtrl && !stage._heroAnimCtrl.running) {
        stage._heroAnimCtrl.start();
      }
    });
  }

  // Wait for stages to be rendered
  window.addEventListener('heroes-stages-ready', function () {
    // Short delay to ensure DOM is painted
    requestAnimationFrame(function () {
      initAnimations();
    });
  });

  // Cleanup on page unload
  window.addEventListener('beforeunload', function () {
    controllers.forEach(function (ctrl) { ctrl.destroy(); });
    controllers = [];
  });

  // Handle reduced-motion changes at runtime
  if (window.matchMedia) {
    var mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    mq.addEventListener('change', function (e) {
      if (e.matches) {
        controllers.forEach(function (ctrl) { ctrl.pause(); });
      } else {
        controllers.forEach(function (ctrl) { ctrl.resume(); });
      }
    });
  }
})();

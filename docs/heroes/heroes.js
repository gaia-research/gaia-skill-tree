/**
 * heroes.js — Hall of Heroes orchestrator
 * Fetches contributor data, classifies tiers, renders theatrical stages,
 * and drives IntersectionObserver for entrance animations.
 *
 * Vanilla JS IIFE, no dependencies beyond plaque.js (for renderOg).
 */
(function () {
  'use strict';

  // ── Constants ─────────────────────────────────────────────────
  var API_URL = '../api/v1/contributors/index.json';
  var DETAIL_URL_TEMPLATE = '../api/v1/contributors/{handle}.json';
  var INTERSECTION_THRESHOLD = 0.3;

  // Hero -> bespoke animation mapping
  var ULTIMATE_ANIMS = {
    'garrytan/gstack': 'constellation',
    'ruvnet/ruflo': 'sovereign',
    'mattpocock/skills': 'typeforge',
    'obra/superpowers': 'cascade'
  };

  // Epithets for ultimate heroes (ceremonial one-liner)
  var ULTIMATE_EPITHETS = {
    'garrytan': 'Architect of the Constellation',
    'ruvnet': 'The Sovereign',
    'mattpocock': 'The Type Forge',
    'obra': 'Master of the Plugin Cascade'
  };

  var TYPE_GLYPH = {
    ultimate: '\u25C6',  // ◆
    unique: '\u25C9',    // ◉
    extra: '\u25C7',     // ◇
    basic: '\u25CB'      // ○
  };

  // ── Utilities ─────────────────────────────────────────────────
  function esc(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function levelNum(lvl) {
    if (!lvl) return 0;
    var n = parseInt(String(lvl).replace(/[^\d]/g, ''));
    return isNaN(n) ? 0 : n;
  }

  function classifyTier(contributor) {
    var lvl = levelNum(contributor.topSkill.level);
    var skillId = contributor.topSkill.id || '';
    // Ultimate: 5★+ AND is a known ultimate skill
    if (lvl >= 5 && ULTIMATE_ANIMS[skillId]) return 'ultimate';
    // Apex/Extra: 5★+ (non-ultimate suite)
    if (lvl >= 5) return 'apex';
    // Unique: 4★+
    if (lvl >= 4) return 'unique';
    // Named: everything else that passed the filter
    return 'named';
  }

  function getAnim(skillId) {
    return ULTIMATE_ANIMS[skillId] || 'constellation';
  }

  // ── Render functions ──────────────────────────────────────────

  function renderOgCard(contributor) {
    // Use plaque.renderOg if available, else fallback to a simple card
    var ns = {
      id: contributor.topSkill.id,
      name: contributor.topSkill.id.split('/').pop(),
      contributor: contributor.handle,
      level: contributor.topSkill.level,
      type: 'ultimate',
      origin: true,
      description: '',
      tags: []
    };

    if (window.plaque && typeof window.plaque.renderOg === 'function') {
      return window.plaque.renderOg(ns);
    }

    // Minimal fallback
    return '<div style="padding:40px;text-align:center;background:rgba(0,0,0,0.4);border-radius:14px;">' +
      '<div style="font-size:24px;color:var(--heroes-gold-warm);">' + esc(ns.name) + '</div>' +
      '<div style="font-size:14px;opacity:0.6;margin-top:8px;">@' + esc(contributor.handle) + '</div>' +
      '</div>';
  }

  function renderHeroStage(contributor, tier) {
    var handle = contributor.handle;
    var skillId = contributor.topSkill.id;
    var slug = skillId.split('/').pop();
    var lvl = levelNum(contributor.topSkill.level);
    var anim = tier === 'ultimate' ? getAnim(skillId) : '';
    var epithet = ULTIMATE_EPITHETS[handle] || '';

    var stageClass = 'hero-stage hero-stage--' + tier;
    var animAttr = anim ? ' data-anim="' + anim + '"' : '';

    var html = '';
    html += '<section class="' + stageClass + '" data-handle="' + esc(handle) + '" data-skill="' + esc(skillId) + '">';
    html += '<div class="hero-card">';

    // Canvas placeholder (populated by hero-animations.js for ultimates)
    if (tier === 'ultimate') {
      html += '<canvas class="hero-card__canvas" data-hero="' + esc(handle) + '" aria-hidden="true"></canvas>';
    }

    // OG card
    html += '<div class="hero-card__og"' + animAttr + '>';
    html += renderOgCard(contributor);
    html += '</div>';

    // Meta
    html += '<div class="hero-card__meta">';
    html += '<h2 class="hero-card__name">' + esc(slug) + '</h2>';
    html += '<div class="hero-card__handle">@' + esc(handle) + '</div>';
    if (epithet) {
      html += '<p class="hero-card__epithet">' + esc(epithet) + '</p>';
    }
    html += '<div class="hero-card__stats">';
    html += '<span><span class="hero-card__stat-value">' + contributor.namedSkills + '</span> named skills</span>';
    html += '<span><span class="hero-card__stat-value">' + contributor.topSkill.level + '</span> top rank</span>';
    html += '<span><span class="hero-card__stat-value">' + Math.round(contributor.prestigeScore) + '</span> prestige</span>';
    html += '</div>';
    html += '</div>';

    // Share button
    html += '<button class="hero-card__share" data-share-handle="' + esc(handle) + '" data-share-skill="' + esc(skillId) + '">';
    html += '<svg class="ico" width="14" height="14" aria-hidden="true"><use href="../assets/icons.svg#link"></use></svg>';
    html += 'Share';
    html += '</button>';

    html += '</div>';
    html += '</section>';
    return html;
  }

  function renderTierDivider(label) {
    return '<div class="heroes-tier-divider" aria-hidden="true">' +
      '<div class="heroes-tier-divider__line"></div>' +
      '<span class="heroes-tier-divider__label">' + esc(label) + '</span>' +
      '<div class="heroes-tier-divider__line"></div>' +
      '</div>';
  }

  function renderLoadingState() {
    return '<div class="heroes-loading">' +
      '<div class="heroes-loading__spinner"></div>' +
      '<span>Summoning heroes&hellip;</span>' +
      '</div>';
  }

  function renderEmptyState() {
    return '<div class="heroes-empty">' +
      '<p>No heroes have ascended to 4\u2605 yet.<br>The hall awaits its first legends.</p>' +
      '</div>';
  }

  // ── Observer setup ────────────────────────────────────────────
  function setupIntersectionObserver() {
    var stages = document.querySelectorAll('.hero-stage');
    if (!stages.length) return;

    // For browsers that don't support IntersectionObserver, show all immediately
    if (!('IntersectionObserver' in window)) {
      stages.forEach(function (el) { el.classList.add('is-visible'); });
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          // Don't unobserve — let canvas pause/resume use this too
        }
        // Pause canvas when off-screen (handled by hero-animations.js)
        if (entry.target._heroAnimCtrl) {
          if (entry.isIntersecting) {
            entry.target._heroAnimCtrl.resume();
          } else {
            entry.target._heroAnimCtrl.pause();
          }
        }
      });
    }, { threshold: INTERSECTION_THRESHOLD });

    stages.forEach(function (stage) {
      observer.observe(stage);
    });
  }

  // ── Main init ─────────────────────────────────────────────────
  function init() {
    var container = document.getElementById('heroesStages');
    if (!container) return;

    container.innerHTML = renderLoadingState();

    fetch(API_URL)
      .then(function (r) {
        if (!r.ok) throw new Error('API fetch failed: ' + r.status);
        return r.json();
      })
      .then(function (data) {
        var contributors = data.contributors || [];

        // Filter: topSkill.level >= 4★
        var heroes = contributors.filter(function (c) {
          return c.topSkill && levelNum(c.topSkill.level) >= 4;
        });

        // Sort by prestigeScore descending
        heroes.sort(function (a, b) {
          return (b.prestigeScore || 0) - (a.prestigeScore || 0);
        });

        if (!heroes.length) {
          container.innerHTML = renderEmptyState();
          return;
        }

        // Classify tiers
        var ultimates = [];
        var apex = [];
        var uniques = [];
        var named = [];

        heroes.forEach(function (c) {
          var tier = classifyTier(c);
          switch (tier) {
            case 'ultimate': ultimates.push(c); break;
            case 'apex': apex.push(c); break;
            case 'unique': uniques.push(c); break;
            default: named.push(c); break;
          }
        });

        // Build HTML
        var html = '';

        // Ultimate tier
        if (ultimates.length) {
          ultimates.forEach(function (c) {
            html += renderHeroStage(c, 'ultimate');
          });
        }

        // Apex tier
        if (apex.length) {
          html += renderTierDivider('Apex');
          apex.forEach(function (c) {
            html += renderHeroStage(c, 'apex');
          });
        }

        // Unique tier
        if (uniques.length) {
          html += renderTierDivider('Unique');
          uniques.forEach(function (c) {
            html += renderHeroStage(c, 'unique');
          });
        }

        // Named tier
        if (named.length) {
          html += renderTierDivider('Named');
          named.forEach(function (c) {
            html += renderHeroStage(c, 'named');
          });
        }

        container.innerHTML = html;

        // Set up scroll-driven entrance animations
        setupIntersectionObserver();

        // Notify hero-animations.js that stages are ready
        window.dispatchEvent(new CustomEvent('heroes-stages-ready'));
      })
      .catch(function (err) {
        console.error('[heroes] Failed to load contributors:', err);
        container.innerHTML = '<div class="heroes-empty"><p>Failed to load heroes. Please try again.</p></div>';
      });
  }

  // Boot
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

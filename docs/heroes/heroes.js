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
  var TRUST_LEDGER_URL = '../graph/ledger/data.json';
  var NAMED_INDEX_URL = '../graph/named/index.json';
  var DETAIL_URL_TEMPLATE = '../api/v1/contributors/{handle}.json';
  var INTERSECTION_THRESHOLD = 0.3;
  var SCROLL_TICKING = false;
  var ACTIVE_STAGE = null;
  var LEDGER_ITEMS = [];

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

  var TIER_LABEL = {
    ultimate: 'Ultimate',
    apex: 'Apex',
    transcendent: 'Transcendent',
    unique: 'Unique',
    extra: 'Extra',
    basic: 'Basic',
    named: 'Named'
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
    var type = contributor.topSkill.type || 'basic';
    // Ultimate: 5★+ AND is a known ultimate skill
    if (lvl >= 5 && ULTIMATE_ANIMS[skillId]) return 'ultimate';
    // Apex: 6★ (non-ultimate suite)
    if (lvl >= 6) return 'apex';
    // Transcendent: 5★ (non-ultimate suite)
    if (lvl === 5) return 'transcendent';
    // Unique is a skill type, not a star-level synonym.
    if (type === 'unique') return 'unique';
    if (type === 'extra') return 'extra';
    if (type === 'basic') return 'basic';
    // Named: everything else that passed the filter
    return 'named';
  }

  function getAnim(skillId) {
    return ULTIMATE_ANIMS[skillId] || 'constellation';
  }

  function getTierMarkLabel(contributor) {
    var lvl = levelNum(contributor.topSkill.level);
    var type = contributor.topSkill.type || 'basic';

    if (type === 'ultimate') {
      if (lvl === 6) return 'Ultimate · Apex';
      if (lvl === 5) return 'Ultimate · Transcendent';
      return 'Ultimate · Hardened';
    }

    if (lvl === 6) {
      if (type === 'unique') return 'Unique · Apex';
      if (type === 'extra') return 'Extra · Apex';
      return 'Apex';
    }

    if (lvl === 5) {
      if (type === 'unique') return 'Unique · Transcendent';
      if (type === 'extra') return 'Extra · Transcendent';
      return 'Transcendent';
    }

    if (lvl === 4) {
      if (type === 'unique') return 'Unique';
      if (type === 'extra') return 'Hardened · Extra';
      if (type === 'basic') return 'Hardened · Basic';
      return 'Hardened';
    }

    return TIER_LABEL[classifyTier(contributor)] || 'Named';
  }

  function stageIdFor(contributor) {
    var raw = contributor.handle + '-' + contributor.topSkill.id;
    return 'hero-' + String(raw).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
  }

  function rankText(contributor) {
    return contributor.topSkill && contributor.topSkill.level ? contributor.topSkill.level : 'Unranked';
  }

  function trustMagnitude(contributor) {
    if (contributor.heroTrustMagnitude != null) return contributor.heroTrustMagnitude;
    return contributor.topSkill && contributor.topSkill.trustMagnitude != null
      ? contributor.topSkill.trustMagnitude
      : 0;
  }

  function trustLedgerMap(data) {
    var rows = data && Array.isArray(data.rows) ? data.rows : [];
    var bySkill = {};
    rows.forEach(function (row) {
      if (row && row.skillId) bySkill[row.skillId] = row;
    });
    return bySkill;
  }

  function namedSkillMap(data) {
    var bySkill = {};

    function remember(entry) {
      if (entry && entry.id) bySkill[entry.id] = entry;
    }

    function walkList(list) {
      if (Array.isArray(list)) list.forEach(remember);
    }

    var buckets = data && data.buckets ? data.buckets : {};
    Object.keys(buckets).forEach(function (key) {
      walkList(buckets[key]);
    });
    walkList(data && data.awaitingClassification);

    var byContributor = data && data.byContributor ? data.byContributor : {};
    Object.keys(byContributor).forEach(function (key) {
      walkList(byContributor[key]);
    });

    return bySkill;
  }

  function withNamedSkillMeta(contributor, namedBySkill) {
    var skillId = contributor.topSkill && contributor.topSkill.id;
    var named = skillId ? namedBySkill[skillId] : null;
    if (!named) return contributor;
    contributor.topSkill.type = named.type || contributor.topSkill.type || 'basic';
    contributor.topSkill.name = named.name || contributor.topSkill.name;
    contributor.topSkill.origin = named.origin;
    return contributor;
  }

  function withLedgerTrustMagnitude(contributor, ledgerBySkill) {
    var skillId = contributor.topSkill && contributor.topSkill.id;
    var ledgerRow = skillId ? ledgerBySkill[skillId] : null;
    var tm = ledgerRow && typeof ledgerRow.tm === 'number'
      ? ledgerRow.tm
      : trustMagnitude(contributor);
    contributor.heroTrustMagnitude = tm;
    return contributor;
  }

  function formatTrustMagnitude(value) {
    return typeof value === 'number' ? value.toFixed(1) : '0.0';
  }

  function githubAvatarUrl(handle, size) {
    var clean = String(handle || '').trim().replace(/^@/, '');
    if (!clean) return '';
    return 'https://github.com/' + encodeURIComponent(clean) + '.png?size=' + (size || 160);
  }

  function scrollToStage(stage) {
    if (!stage) return;
    stage.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function notifyStageVisible(stage) {
    window.dispatchEvent(new CustomEvent('heroes-stage-visible', { detail: { stage: stage } }));
  }

  // ── Render functions ──────────────────────────────────────────

  function renderHeroStage(contributor, tier, index, total) {
    var handle = contributor.handle;
    var skillId = contributor.topSkill.id;
    var skillType = contributor.topSkill.type || 'basic';
    var slug = skillId.split('/').pop();
    var lvl = levelNum(contributor.topSkill.level);
    var anim = tier === 'ultimate' ? getAnim(skillId) : '';
    var epithet = ULTIMATE_EPITHETS[handle] || '';
    var stageId = stageIdFor(contributor);
    var titleId = stageId + '-title';
    var avatarUrl = githubAvatarUrl(handle, 240);

    var stageClass = 'hero-stage hero-stage--' + tier;
    var animAttr = anim ? ' data-anim="' + anim + '"' : '';
    var glyphType = contributor.topSkill.type || 'basic';
    if (tier === 'ultimate') glyphType = 'ultimate';
    var glyph = TYPE_GLYPH[glyphType] || TYPE_GLYPH.basic;
    var tierLabel = getTierMarkLabel(contributor);

    var html = '';
    html += '<section id="' + esc(stageId) + '" class="' + stageClass + '" data-handle="' + esc(handle) + '" data-skill="' + esc(skillId) + '" data-skill-type="' + esc(skillType) + '" data-tier="' + esc(tier) + '" data-level="' + esc(lvl) + '" data-ledger-index="' + esc(index) + '" data-avatar-url="' + esc(avatarUrl) + '" aria-labelledby="' + esc(titleId) + '">';
    html += '<div class="hero-stage__ordinal" aria-hidden="true">Plate ' + String(index + 1).padStart(2, '0') + ' / ' + String(total).padStart(2, '0') + '</div>';
    html += '<div class="hero-card">';

    // Canvas placeholder (populated by hero-animations.js for ultimates)
    if (tier === 'ultimate') {
      html += '<canvas class="hero-card__canvas" data-hero="' + esc(handle) + '" aria-hidden="true"></canvas>';
    }

    // The share plaque remains available from the action button. The page view
    // uses a lighter crest so the name/handle block is the single source of truth.
    html += '<div class="hero-card__crest-wrapper">';
    html += '<div class="hero-card__crest-diamond-back"' + animAttr + ' aria-hidden="true"></div>';
    html += '<div class="hero-card__crest-square-front">';
    html += '<img src="' + esc(avatarUrl) + '" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.parentNode.hidden=true">';
    html += '</div>';
    html += '<div class="hero-card__crest-seal" data-level="' + esc(lvl) + '">';
    html += '<span class="hero-card__crest-seal-glyph">' + esc(glyph) + '</span>';
    html += '</div>';
    html += '</div>';

    // Meta
    html += '<div class="hero-card__meta">';
    html += '<div class="hero-card__tier-mark" aria-label="' + esc(tierLabel) + ' tier"><span aria-hidden="true">' + esc(glyph) + '</span>' + esc(tierLabel) + '</div>';
    html += '<h2 class="hero-card__name" id="' + esc(titleId) + '">' + esc(slug) + '</h2>';
    html += '<div class="hero-card__handle">@' + esc(handle) + '</div>';
    if (epithet) {
      html += '<p class="hero-card__epithet">' + esc(epithet) + '</p>';
    }
    html += '<div class="hero-card__stats">';
    html += '<span><span class="hero-card__stat-value">' + contributor.namedSkills + '</span> named skills</span>';
    html += '<span><span class="hero-card__stat-value">' + contributor.topSkill.level + '</span> top rank</span>';
    html += '<span><span class="hero-card__stat-value">' + formatTrustMagnitude(trustMagnitude(contributor)) + '</span> Trust Magnitude</span>';
    html += '</div>';
    html += '</div>';

    // Share button
    html += '<button class="hero-card__share" data-share-handle="' + esc(handle) + '" data-share-skill="' + esc(skillId) + '" data-share-type="' + esc(skillType) + '">';
    html += '<svg class="ico" width="14" height="14" aria-hidden="true"><use href="../assets/icons.svg#link"></use></svg>';
    html += 'Share plaque';
    html += '</button>';

    html += '</div>';
    html += '</section>';
    return html;
  }

  function renderLedgerRail(heroes) {
    var rail = document.getElementById('heroesLedgerRail');
    var list = document.getElementById('heroesLedgerList');
    if (!rail || !list) return;

    if (!heroes.length) {
      rail.hidden = true;
      return;
    }

    list.innerHTML = heroes.map(function (entry, index) {
      var contributor = entry.contributor;
      var tier = entry.tier;
      var skillId = contributor.topSkill.id || '';
      var slug = skillId.split('/').pop() || contributor.handle;
      var glyphType = contributor.topSkill.type || 'basic';
      if (tier === 'ultimate') glyphType = 'ultimate';
      var avatarUrl = githubAvatarUrl(contributor.handle, 80);
      var lvl = levelNum(contributor.topSkill.level);
      return '<li class="heroes-ledger-rail__item">' +
        '<button class="heroes-ledger-rail__button" type="button" data-ledger-target="' + esc(stageIdFor(contributor)) + '" data-ledger-index="' + esc(index) + '" data-level="' + lvl + '">' +
        '<span class="heroes-ledger-rail__avatar" aria-hidden="true"><img src="' + esc(avatarUrl) + '" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.parentElement.hidden=true"></span>' +
        '<span class="heroes-ledger-rail__glyph" aria-hidden="true">' + esc(TYPE_GLYPH[glyphType] || TYPE_GLYPH.basic) + '</span>' +
        '<span class="heroes-ledger-rail__entry">' +
        '<span class="heroes-ledger-rail__name">' + esc(slug) + '</span>' +
        '<span class="heroes-ledger-rail__byline">@' + esc(contributor.handle) + ' · ' + esc(rankText(contributor)) + '</span>' +
        '</span>' +
        '</button>' +
        '</li>';
    }).join('');

    LEDGER_ITEMS = heroes;
    setLedgerAwaiting();
    rail.hidden = false;
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
          notifyStageVisible(entry.target);
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

  function setActiveStage(stage) {
    if (!stage || stage === ACTIVE_STAGE) return;

    if (ACTIVE_STAGE) {
      ACTIVE_STAGE.classList.remove('is-active');
    }

    ACTIVE_STAGE = stage;
    var rail = document.getElementById('heroesLedgerRail');
    if (rail) rail.classList.remove('is-awaiting');
    ACTIVE_STAGE.classList.add('is-active');
    notifyStageVisible(ACTIVE_STAGE);
    updateLedgerForStage(ACTIVE_STAGE);
  }

  function clearActiveStage() {
    if (ACTIVE_STAGE) {
      ACTIVE_STAGE.classList.remove('is-active');
      ACTIVE_STAGE = null;
    }
    setLedgerAwaiting();
  }

  function setLedgerAwaiting() {
    var rail = document.getElementById('heroesLedgerRail');
    var current = document.getElementById('heroesLedgerCurrent');
    var meta = document.getElementById('heroesLedgerMeta');
    var progress = document.getElementById('heroesLedgerProgress');
    if (!rail) return;

    rail.removeAttribute('data-active-level');
    rail.classList.add('is-awaiting');
    rail.querySelectorAll('[data-ledger-target]').forEach(function (button) {
      button.classList.remove('is-active');
      button.removeAttribute('aria-current');
    });

    if (current) current.textContent = 'Hall of Heroes';
    if (meta) meta.textContent = 'Scroll to enter the ledger';
    if (progress) progress.style.transform = 'scaleY(0)';
    rail.style.setProperty('--heroes-ledger-progress', '0');
  }

  function updateActiveStage() {
    SCROLL_TICKING = false;

    var stages = Array.prototype.slice.call(document.querySelectorAll('.hero-stage'));
    if (!stages.length) return;

    var viewportCenter = window.innerHeight * 0.5;
    var best = null;
    var bestDistance = Infinity;

    stages.forEach(function (stage) {
      var rect = stage.getBoundingClientRect();
      var stageCenter = rect.top + rect.height * 0.5;
      var visible = rect.top <= viewportCenter && rect.bottom >= viewportCenter;
      var distance = Math.abs(stageCenter - viewportCenter);
      if (visible && distance < bestDistance) {
        best = stage;
        bestDistance = distance;
      }
    });

    if (best) {
      setActiveStage(best);
    } else {
      clearActiveStage();
    }
  }

  function requestActiveStageUpdate() {
    if (SCROLL_TICKING) return;
    SCROLL_TICKING = true;
    requestAnimationFrame(updateActiveStage);
  }

  function updateLedgerForStage(stage) {
    var rail = document.getElementById('heroesLedgerRail');
    if (!rail) return;

    var index = parseInt(stage.getAttribute('data-ledger-index') || '0', 10);
    var entry = LEDGER_ITEMS[index];
    var current = document.getElementById('heroesLedgerCurrent');
    var meta = document.getElementById('heroesLedgerMeta');
    var progress = document.getElementById('heroesLedgerProgress');
    var buttons = rail.querySelectorAll('[data-ledger-target]');
    var total = LEDGER_ITEMS.length || buttons.length || 1;

    var lvl = stage.getAttribute('data-level') || '4';
    rail.setAttribute('data-active-level', lvl);

    buttons.forEach(function (button) {
      var isActive = button.getAttribute('data-ledger-target') === stage.id;
      button.classList.toggle('is-active', isActive);
      if (isActive) {
        button.setAttribute('aria-current', 'location');
      } else {
        button.removeAttribute('aria-current');
      }
    });

    if (entry && current) {
      var slug = (entry.contributor.topSkill.id || '').split('/').pop() || entry.contributor.handle;
      current.textContent = slug;
    }

    if (entry && meta) {
      var displayLabel = getTierMarkLabel(entry.contributor);
      meta.textContent = displayLabel + ' · ' + rankText(entry.contributor) + ' · Plate ' + (index + 1) + ' of ' + total;
    }

    if (progress) {
      progress.style.transform = 'scaleY(' + ((index + 1) / total).toFixed(4) + ')';
    }

    rail.style.setProperty('--heroes-ledger-progress', ((index + 1) / total).toFixed(4));
  }

  function setupLedgerRail() {
    var rail = document.getElementById('heroesLedgerRail');
    if (!rail) return;

    rail.addEventListener('click', function (e) {
      var targetButton = e.target.closest('[data-ledger-target]');
      if (targetButton) {
        scrollToStage(document.getElementById(targetButton.getAttribute('data-ledger-target')));
        return;
      }

      var nav = e.target.closest('[data-ledger-nav]');
      if (!nav) return;

      var currentIndex = ACTIVE_STAGE ? parseInt(ACTIVE_STAGE.getAttribute('data-ledger-index') || '0', 10) : 0;
      var direction = nav.getAttribute('data-ledger-nav') === 'next' ? 1 : -1;
      var nextIndex = Math.max(0, Math.min(LEDGER_ITEMS.length - 1, currentIndex + direction));
      var nextStage = document.querySelector('.hero-stage[data-ledger-index="' + nextIndex + '"]');
      scrollToStage(nextStage);
    });

    window.addEventListener('scroll', requestActiveStageUpdate, { passive: true });
    window.addEventListener('resize', requestActiveStageUpdate);
    requestActiveStageUpdate();
  }

  // ── Main init ─────────────────────────────────────────────────
  function init() {
    var container = document.getElementById('heroesStages');
    if (!container) return;

    container.innerHTML = renderLoadingState();

    Promise.all([
      fetch(API_URL).then(function (r) {
        if (!r.ok) throw new Error('Contributors API fetch failed: ' + r.status);
        return r.json();
      }),
      fetch(TRUST_LEDGER_URL).then(function (r) {
        if (!r.ok) throw new Error('Trust Ledger fetch failed: ' + r.status);
        return r.json();
      }).catch(function (err) {
        console.warn('[heroes] Trust Ledger unavailable; falling back to contributor topSkill trustMagnitude:', err);
        return { rows: [] };
      }),
      fetch(NAMED_INDEX_URL).then(function (r) {
        if (!r.ok) throw new Error('Named index fetch failed: ' + r.status);
        return r.json();
      }).catch(function (err) {
        console.warn('[heroes] Named index unavailable; falling back to basic/extra metadata from contributors API:', err);
        return {};
      })
    ])
      .then(function (results) {
        var data = results[0];
        var ledgerBySkill = trustLedgerMap(results[1]);
        var namedBySkill = namedSkillMap(results[2]);
        var contributors = data.contributors || [];

        // Filter: topSkill.level >= 4★
        var heroes = contributors.filter(function (c) {
          return c.topSkill && levelNum(c.topSkill.level) >= 4;
        }).map(function (c) {
          return withLedgerTrustMagnitude(withNamedSkillMeta(c, namedBySkill), ledgerBySkill);
        });

        // Sort by the top skill's Trust Ledger magnitude.
        heroes.sort(function (a, b) {
          return trustMagnitude(b) - trustMagnitude(a);
        });

        if (!heroes.length) {
          container.innerHTML = renderEmptyState();
          return;
        }

        // Classify tiers
        var ultimates = [];
        var apex = [];
        var transcendents = [];
        var uniques = [];
        var extras = [];
        var basics = [];
        var named = [];
        var ledgerEntries = [];

        heroes.forEach(function (c) {
          var tier = classifyTier(c);
          switch (tier) {
            case 'ultimate': ultimates.push(c); break;
            case 'apex': apex.push(c); break;
            case 'transcendent': transcendents.push(c); break;
            case 'unique': uniques.push(c); break;
            case 'extra': extras.push(c); break;
            case 'basic': basics.push(c); break;
            default: named.push(c); break;
          }
        });

        // Build HTML
        var html = '';
        var renderedIndex = 0;
        var totalHeroes = heroes.length;

        function appendHeroStage(c, tier) {
          ledgerEntries.push({ contributor: c, tier: tier });
          html += renderHeroStage(c, tier, renderedIndex++, totalHeroes);
        }

        // Ultimate tier
        if (ultimates.length) {
          ultimates.forEach(function (c) {
            appendHeroStage(c, 'ultimate');
          });
        }

        // Apex tier
        if (apex.length) {
          html += renderTierDivider('Apex');
          apex.forEach(function (c) {
            appendHeroStage(c, 'apex');
          });
        }

        // Transcendent tier
        if (transcendents.length) {
          html += renderTierDivider('Transcendent');
          transcendents.forEach(function (c) {
            appendHeroStage(c, 'transcendent');
          });
        }

        // Unique tier
        if (uniques.length) {
          html += renderTierDivider('Unique');
          uniques.forEach(function (c) {
            appendHeroStage(c, 'unique');
          });
        }

        // Extra tier
        if (extras.length) {
          html += renderTierDivider('Extra');
          extras.forEach(function (c) {
            appendHeroStage(c, 'extra');
          });
        }

        // Basic tier
        if (basics.length) {
          html += renderTierDivider('Basic');
          basics.forEach(function (c) {
            appendHeroStage(c, 'basic');
          });
        }

        // Named tier
        if (named.length) {
          html += renderTierDivider('Named');
          named.forEach(function (c) {
            appendHeroStage(c, 'named');
          });
        }

        container.innerHTML = html;

        // Set up scroll-driven entrance animations
        renderLedgerRail(ledgerEntries);
        setupIntersectionObserver();
        setupLedgerRail();

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

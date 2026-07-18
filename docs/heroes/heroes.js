/**
 * heroes.js — Hall of Heroes orchestrator
 * Fetches contributor data, READS the emitted semantic branch via
 * window.GaiaSemantics (skill-semantics.js), renders theatrical stages,
 * and drives IntersectionObserver for entrance animations.
 *
 * Yggdrasil II compliance:
 *   E1 — branch READ from the emitted field via GaiaSemantics.branchOf, never
 *        derived from skill.type === 'ultimate'|'unique'|'extra' (dead enum).
 *   E2 — rank words forked by branch via rankWord/rankLabel; banned ladder
 *        words ('Hardened' and the removed 6★ suite synonym) do not appear.
 *   E3 — every hero card has a GitHub avatar framed by the gold wreath
 *        (origin-wreath-gold.svg), identicon fallback, no standalone
 *        GitHub button.
 *   E4 — red origin mark removed; origin rendered as gold wreath frame.
 *
 * Vanilla JS IIFE, no dependencies beyond plaque.js + skill-semantics.js.
 * skill-semantics.js MUST be loaded before this file (heroes.html does so).
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

  // Hero → bespoke animation mapping (keyed by named-skill id, not type)
  var ULTIMATE_ANIMS = {
    'garrytan/gstack': 'constellation',
    'ruvnet/ruflo': 'sovereign',
    'mattpocock/skills': 'typeforge',
    'obra/superpowers': 'cascade'
  };

  // Epithets for top-tier heroes (ceremonial one-liner, keyed by handle)
  var ULTIMATE_EPITHETS = {
    'garrytan': 'Architect of the Constellation',
    'ruvnet': 'The Sovereign',
    'mattpocock': 'The Type Forge',
    'obra': 'Master of the Plugin Cascade'
  };

  // Rubric E1: glyphs keyed by DERIVED branch, never by skill.type.
  // Mirrors plaque.js BRANCH_GLYPH and tokens.css tier symbols.
  var BRANCH_GLYPH = {
    unique:   '◉',  // ◉  — E3: DARKER plaque branch
    suite:    '◆',  // ◆  — GOLD suite branch
    standard: '○'  // ○  — standard branch
  };

  // ── Utilities ─────────────────────────────────────────────────
  function esc(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function jsStr(s) {
    return String(s == null ? '' : s).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
  }

  function levelNum(lvl) {
    if (!lvl) return 0;
    var n = parseInt(String(lvl).replace(/[^\d]/g, ''));
    return isNaN(n) ? 0 : n;
  }

  // ── Rubric E1/E2 — READ the emitted branch, never guess ───────
  // Branch classification reads the taxonomy authority's emitted field via the
  // GaiaSemantics.branchOf seam (topSkill blob carries emitted .branch/.rank —
  // §8 Hall behavior: thread the emitted fields into the input, never re-derive
  // from type). NEVER compare topSkill.type against 'ultimate'|'unique'|'extra'.
  function computeBranchForTopSkill(contributor) {
    var skill = (contributor && contributor.topSkill) || {};
    if (window.GaiaSemantics && typeof window.GaiaSemantics.branchOf === 'function') {
      return window.GaiaSemantics.branchOf(skill);
    }
    // Degrade gracefully if skill-semantics.js somehow failed to load.
    return (skill && typeof skill.branch === 'string' && skill.branch) || 'standard';
  }

  // Returns the rank label string for a contributor's top skill.
  // E2: uses rankLabel — emits e.g. "Unique · 4★", "Ultimate · 5★", "Apex · 6★".
  // BANNED ladder words — neither 'Hardened' nor the removed 6★ suite synonym
  // appear in rankLabel output.
  function topSkillRankLabel(contributor) {
    var skill = (contributor && contributor.topSkill) || {};
    var lvl = levelNum(skill.level);
    var branch = computeBranchForTopSkill(contributor);
    if (window.GaiaSemantics && typeof window.GaiaSemantics.rankLabel === 'function') {
      return window.GaiaSemantics.rankLabel(lvl, branch);
    }
    return lvl + '★';
  }

  // Returns the CSS tier class suffix for the hero stage background/animation.
  // Maps branch + rank → presentational CSS class (hero-stage--<suffix>).
  // E1: derived purely from the emitted branch (branchOf seam) + numeric rank —
  // no type reads.
  function stageTierClass(contributor) {
    var branch = computeBranchForTopSkill(contributor);
    var lvl = levelNum(contributor.topSkill.level);
    var skillId = contributor.topSkill.id || '';

    if (branch === 'unique') return 'unique';

    if (branch === 'suite') {
      // Named ultmates with bespoke particle animations get the special class.
      if (lvl >= 5 && ULTIMATE_ANIMS[skillId]) return 'ultimate';
      if (lvl >= 6) return 'apex';
      if (lvl >= 5) return 'apex';
      return 'extra';
    }

    // Standard branch
    return 'basic';
  }

  function getAnim(skillId) {
    return ULTIMATE_ANIMS[skillId] || 'constellation';
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
    // Thread the EMITTED taxonomy fields from the named index onto the topSkill
    // blob so GaiaSemantics.branchOf/rankWordOf/medallionOf READ them (§8: the
    // fix is to thread emitted fields into the input, never re-derive). The
    // contributors API topSkill blob omits them.
    if (typeof named.branch === 'string' && named.branch) contributor.topSkill.branch = named.branch;
    if (typeof named.rankWord === 'string' && named.rankWord) contributor.topSkill.rankWord = named.rankWord;
    if (typeof named.medallion === 'string' && named.medallion) contributor.topSkill.medallion = named.medallion;
    if (named.suiteComponents) contributor.topSkill.suiteComponents = named.suiteComponents;
    if (named.links) contributor.topSkill.links = named.links;
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

  // ── Gold-wreath avatar (E3/E4) ────────────────────────────────
  // Renders the contributor's GitHub avatar framed by origin-wreath-gold.svg.
  // Identicon fallback on onerror — never hides the frame.
  // Reuses plaque._fields.avatar when available; falls back to inline pattern.
  // The red origin mark (E4) is deprecated — gold wreath IS the origin signal.
  function heroAvatarHtml(contributor, size) {
    var handle = (contributor && contributor.handle) || '';
    if (!handle) return '';
    var clean = String(handle).replace(/^@/, '');
    size = size || 120;

    // Prefer plaque._fields.avatar so the wreath is always in sync with the
    // shared component. Construct a minimal ns-like object.
    if (window.plaque && window.plaque._fields && typeof window.plaque._fields.avatar === 'function') {
      var ns = {
        contributor: handle,
        level: contributor.topSkill && contributor.topSkill.level,
        origin: !!(contributor.topSkill && contributor.topSkill.origin),
        links: contributor.topSkill && contributor.topSkill.links || {}
      };
      return window.plaque._fields.avatar(ns, { size: size });
    }

    // Inline fallback — mirrors _fieldAvatar exactly (no hex, no duplication).
    var avatarSrc = 'https://github.com/' + encodeURIComponent(clean) + '.png?size=' + (size * 2);
    var identicon = 'https://github.com/identicons/' + encodeURIComponent(clean) + '.png';
    var wreathSrc = '../assets/origin-wreath-gold.svg';
    var isOrigin = !!(contributor.topSkill && contributor.topSkill.origin);
    var title = isOrigin ? 'Origin contributor @' + clean : '@' + clean;
    var errAttr = "if(this.dataset.fbk){this.onerror=null;}else{this.dataset.fbk='1';this.src='" +
      jsStr(identicon) + "';}";
    var imgHtml = '<img class="hero-card__crest-avatar-img" src="' + esc(avatarSrc) + '" ' +
      'alt="" decoding="async" loading="lazy" referrerpolicy="no-referrer" ' +
      'onerror="' + errAttr + '">';
    var wreathHtml = '<img class="hero-card__crest-avatar-wreath" src="' + esc(wreathSrc) + '" ' +
      'alt="" aria-hidden="true">';
    return '<span class="hero-card__crest-avatar" title="' + esc(title) + '" ' +
      'aria-label="' + esc(title) + '"' +
      (isOrigin ? ' data-origin="true"' : '') + '>' +
      imgHtml + wreathHtml +
      '</span>';
  }

  // ── AOV4 rank medallion stamp (E3) ────────────────────────────
  // The crest rank marker IS the Ascension-Overdrive v4 stamp — the same
  // medallion the plaques carry. Routed through the shared plaque._fields.orb
  // so branch (suite/unique) + rank pick the asset identically everywhere;
  // never a bespoke per-surface stamp. Falls back to '' if plaque.js is
  // somehow absent (the legacy ◆ glyph then remains the sole rank marker).
  function heroRankStampHtml(contributor) {
    if (!(window.plaque && window.plaque._fields &&
          typeof window.plaque._fields.orb === 'function')) {
      return '';
    }
    var skill = (contributor && contributor.topSkill) || {};
    var ns = {
      contributor: contributor && contributor.handle,
      level: skill.level,
      type: skill.type,
      suiteComponents: skill.suiteComponents,
    };
    // 'lg' size modifier → the AOV4 'hero' tier asset (largest stamp).
    return window.plaque._fields.orb(ns, 'lg');
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
    var slug = skillId.split('/').pop();
    var lvl = levelNum(contributor.topSkill.level);
    var branch = computeBranchForTopSkill(contributor);
    var anim = tier === 'ultimate' ? getAnim(skillId) : '';
    var epithet = ULTIMATE_EPITHETS[handle] || '';
    var stageId = stageIdFor(contributor);
    var titleId = stageId + '-title';

    // E1: glyph from BRANCH_GLYPH — never reads skill.type.
    var glyph = BRANCH_GLYPH[branch] || BRANCH_GLYPH.standard;

    // E2: tier mark uses rankLabel — branch-forked, no banned words.
    var tierLabel = topSkillRankLabel(contributor);

    var stageClass = 'hero-stage hero-stage--' + tier;
    var animAttr = anim ? ' data-anim="' + anim + '"' : '';

    // E3: data-skill-type reflects stored type only; visual branch is data-branch
    // (set by data-tier in CSS for the hero stage context).
    var html = '';
    html += '<section id="' + esc(stageId) + '" class="' + stageClass + '" data-handle="' + esc(handle) + '" data-skill="' + esc(skillId) + '" data-branch="' + esc(branch) + '" data-tier="' + esc(tier) + '" data-level="' + esc(lvl) + '" data-ledger-index="' + esc(index) + '" aria-labelledby="' + esc(titleId) + '">';
    html += '<div class="hero-stage__ordinal" aria-hidden="true">Plate ' + String(index + 1).padStart(2, '0') + ' / ' + String(total).padStart(2, '0') + '</div>';
    html += '<div class="hero-card">';

    // Canvas placeholder (populated by hero-animations.js for ultimates)
    if (tier === 'ultimate') {
      html += '<canvas class="hero-card__canvas" data-hero="' + esc(handle) + '" aria-hidden="true"></canvas>';
    }

    // E3: crest wrapper — diamond back + gold-wreath avatar (replaces plain img + red mark).
    html += '<div class="hero-card__crest-wrapper">';
    html += '<div class="hero-card__crest-diamond-back"' + animAttr + ' aria-hidden="true"></div>';
    html += '<div class="hero-card__crest-square-front">';
    html += heroAvatarHtml(contributor, 200);
    html += '</div>';
    // E3: rank marker IS the AOV4 medallion stamp (shared plaque orb path).
    // The legacy ◆ crest-seal glyph is retained as the fallback shown only
    // when the stamp is unavailable (plaque.js absent / webp 404 → the orb's
    // own [data-stamp-fail] tint plus this glyph keep a rank marker visible).
    var rankStamp = heroRankStampHtml(contributor);
    html += '<div class="hero-card__crest-seal" data-level="' + esc(lvl) + '">';
    if (rankStamp) {
      html += rankStamp;
    }
    html += '<span class="hero-card__crest-seal-glyph" aria-hidden="true">' + esc(glyph) + '</span>';
    html += '</div>';
    html += '</div>';

    // Meta
    html += '<div class="hero-card__meta">';
    html += '<div class="hero-card__tier-mark" aria-label="' + esc(tierLabel) + '"><span aria-hidden="true">' + esc(glyph) + '</span>' + esc(tierLabel) + '</div>';
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
    html += '<button class="hero-card__share" data-share-handle="' + esc(handle) + '" data-share-skill="' + esc(skillId) + '" data-share-branch="' + esc(branch) + '">';
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
      // E1: glyph keyed by branch, not type.
      var branch = computeBranchForTopSkill(contributor);
      var glyph = BRANCH_GLYPH[branch] || BRANCH_GLYPH.standard;
      var avatarUrl = githubAvatarUrl(contributor.handle, 80);
      var lvl = levelNum(contributor.topSkill.level);
      return '<li class="heroes-ledger-rail__item">' +
        '<button class="heroes-ledger-rail__button" type="button" data-ledger-target="' + esc(stageIdFor(contributor)) + '" data-ledger-index="' + esc(index) + '" data-level="' + lvl + '">' +
        '<span class="heroes-ledger-rail__avatar" aria-hidden="true"><img src="' + esc(avatarUrl) + '" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.parentElement.hidden=true"></span>' +
        '<span class="heroes-ledger-rail__glyph" aria-hidden="true">' + esc(glyph) + '</span>' +
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
      '<p>No heroes have ascended to 4★ yet.<br>The hall awaits its first legends.</p>' +
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
      // E2: rankLabel via GaiaSemantics — no banned words in ledger meta.
      var displayLabel = topSkillRankLabel(entry.contributor);
      meta.textContent = displayLabel + ' · Plate ' + (index + 1) + ' of ' + total;
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

        var ledgerEntries = [];

        // Build HTML in strict TM order. Tier dividers follow live ranking.
        // E2: divider labels use rankLabel (branch-forked, no banned words).
        var html = '';
        var renderedIndex = 0;
        var totalHeroes = heroes.length;
        var previousTier = null;

        function appendHeroStage(c, tier) {
          ledgerEntries.push({ contributor: c, tier: tier });
          html += renderHeroStage(c, tier, renderedIndex++, totalHeroes);
        }

        heroes.forEach(function (c) {
          var tier = stageTierClass(c);
          if (tier !== previousTier && previousTier !== null) {
            // Use rankLabel for the divider heading — branch-forked, no banned words.
            var dividerLabel = topSkillRankLabel(c);
            html += renderTierDivider(dividerLabel);
          }
          appendHeroStage(c, tier);
          previousTier = tier;
        });

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

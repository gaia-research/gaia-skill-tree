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
  var GRAPH_URL = '../graph/gaia.json';
  var DETAIL_URL_TEMPLATE = '../api/v1/contributors/{handle}.json';
  var INTERSECTION_THRESHOLD = 0.3;
  var SCROLL_TICKING = false;
  var ACTIVE_STAGE = null;
  var LEDGER_ITEMS = [];
  // Windowed locator (desktop ≥820px): show only a neighborhood of rows around
  // the active plate instead of all N. Chosen as prev 2 / current / next 3 — a
  // 6-row window reads as "where am I + what's next" without overflowing the
  // fixed rail at ~820–900px, while still previewing the immediate ascent path.
  var LEDGER_WINDOW_BEFORE = 2;
  var LEDGER_WINDOW_AFTER = 3;
  var LEDGER_ACTIVE_INDEX = -1;
  var GAIA_SKILL_MAP = {};

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

  // The branch is the Hall's organising fact, so it gets said in words as well
  // as in glyph and colour (PRODUCT.md accessibility baseline: never symbol
  // alone, never colour alone). Words only — the derivation still comes from
  // GaiaSemantics.branchOf.
  var BRANCH_WORD = {
    unique:   'Unique branch',
    suite:    'Suite branch',
    standard: 'Standard branch'
  };

  // One sentence per branch, shown on the chapter head. Half-Merged voice:
  // states what the structure actually is, no ceremony beyond the chapter title.
  var BRANCH_NOTE = {
    unique:   'Carried to this rank on its own, with no suite beneath it.',
    suite:    'Fused from named components into a single capstone.',
    standard: 'Ranked on the shared ladder below the branch fork.'
  };

  // Largest Fusion Score across the rendered Hall, computed once per load in
  // init(). The suite composition bar reads against it, so the bar always means
  // "against the most composed capability in the Hall right now" rather than
  // against an invented ceiling. 1 is a safe floor (never divide by zero).
  var HALL_FUSION_MAX = 1;

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

  // §8 Hall selection — the Hall shows EVERY qualifying named skill (rank >= 4),
  // NOT one-per-contributor. The contributors-API topSkill blob is capped to a
  // single max-Trust-Magnitude skill per contributor (so a contributor whose
  // top skill is < 4★ vanishes, dropping their 4★+ uniques). Instead we read
  // the named index directly — it carries the emitted branch/rank/rankWord/
  // medallion per entry — and build one hero per rank>=4 named skill. This
  // threads the emitted fields into the input (never re-derives from type).
  function heroesFromNamedIndex(data) {
    var out = [];
    // Per-contributor total named-skill count (for the card's "N named skills"
    // context stat — each hero card is now one skill, but still shows how many
    // named skills its contributor holds).
    var countByContributor = {};
    function tally(entry) {
      if (entry && entry.contributor) {
        countByContributor[entry.contributor] = (countByContributor[entry.contributor] || 0) + 1;
      }
    }
    function consider(entry) {
      if (!entry || !entry.id) return;
      var rank = (typeof entry.rank === 'number') ? entry.rank : levelNum(entry.level);
      if (rank < 4) return;
      // Synthesize a contributor-shaped object so the existing render path
      // (which reads contributor.topSkill.*) works unchanged. topSkill IS the
      // named entry, carrying its emitted taxonomy fields.
      out.push({
        handle: entry.contributor,
        namedSkills: 0,
        topSkill: {
          id: entry.id,
          name: entry.name,
          level: entry.level,
          type: entry.type,
          branch: entry.branch,
          rank: entry.rank,
          rankWord: entry.rankWord,
          medallion: entry.medallion,
          origin: entry.origin,
          links: entry.links,
          genericSkillRef: entry.genericSkillRef,
          suiteComponents: entry.suiteComponents,
          trustMagnitude: entry.trustMagnitude,
          fusionScore: entry.fusionScore,
          fusionScoreVersion: entry.fusionScoreVersion,
          fusionBreakdown: entry.fusionBreakdown
        }
      });
    }
    function walkList(list, fn) { if (Array.isArray(list)) list.forEach(fn); }
    var buckets = data && data.buckets ? data.buckets : {};
    Object.keys(buckets).forEach(function (key) { walkList(buckets[key], tally); walkList(buckets[key], consider); });
    walkList(data && data.awaitingClassification, tally);
    walkList(data && data.awaitingClassification, consider);
    var byContributor = data && data.byContributor ? data.byContributor : {};
    Object.keys(byContributor).forEach(function (key) { walkList(byContributor[key], consider); });
    // De-dupe by skill id (an entry can appear in both a bucket and byContributor),
    // then stamp each hero with its contributor's total named count.
    var seen = {};
    return out.filter(function (h) {
      var id = h.topSkill.id;
      if (seen[id]) return false;
      seen[id] = true;
      h.namedSkills = countByContributor[h.handle] || 1;
      return true;
    });
  }

  // §8 canonical order: rank descending, and within a rank Unique before its
  // Suite counterpart (never co-mingled), Trust Magnitude as the final tiebreak.
  function branchOrder(branch) {
    return branch === 'unique' ? 0 : branch === 'suite' ? 1 : 2;
  }
  function compareHeroes(a, b) {
    var ra = (typeof a.topSkill.rank === 'number') ? a.topSkill.rank : levelNum(a.topSkill.level);
    var rb = (typeof b.topSkill.rank === 'number') ? b.topSkill.rank : levelNum(b.topSkill.level);
    if (ra !== rb) return rb - ra;
    var boa = branchOrder(a.topSkill.branch), bob = branchOrder(b.topSkill.branch);
    if (boa !== bob) return boa - bob;
    var ta = trustMagnitude(a), tb = trustMagnitude(b);
    if (ta !== tb) return tb - ta;
    return String(a.topSkill.id).localeCompare(String(b.topSkill.id));
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
    if (named.genericSkillRef) contributor.topSkill.genericSkillRef = named.genericSkillRef;
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

  function fusionDisplay(value) {
    return value % 1 === 0 ? String(Math.round(value)) : value.toFixed(2);
  }

  // Shared tooltip copy for both branches. Mirrors the explanation in
  // skill-explorer.js's _renderFusionStrip (same data, same "why the numbers
  // moved" framing). Formula lives in src/gaia_cli/fusionScore.py; never
  // recompute it here.
  function fusionTooltip(display, breakdown) {
    var bd = breakdown || {};
    return [
      'Fusion Score ' + display + ': how much distinct structure this capability composes.',
      'A structural reading only, independent of Trust Magnitude. It is not a second trust',
      'number, it grants no credit, and it gates no rank. Yggdrasil III split it out of the',
      'old Trust Magnitude, which had been mixing structure with evidence.',
      '',
      'Distinct structural nodes: ' + (bd.transitiveCount || 0) + ' (' + (bd.directCount || 0) + ' direct)'
    ].join('\n');
  }

  // ── Fusion Score readout, keyed to the branch ─────────────────
  // The two branches carry genuinely different Fusion Scores, so they get
  // genuinely different readouts rather than one badge pretending they are
  // symmetric. Verified against docs/graph/named/index.json at 4★+:
  //   suite  — 140 to 393, present on every entry. Composition IS the branch's
  //            defining fact, so it reads as a headline figure with a bar
  //            scaled against the Hall's own maximum.
  //   unique — 0 to 249, median 40, and 0 on roughly a third of entries. A zero
  //            is a real result (this capability composes nothing distinct of
  //            its own), so it is stated in words rather than blanked out.
  // A missing field is the one case that renders nothing: the score was never
  // computed for that entry, which is not the same claim as "zero".
  function heroFusionHtml(contributor, branch) {
    var skill = (contributor && contributor.topSkill) || {};
    var fs = skill.fusionScore;
    if (fs == null || fs === '') return '';
    var value = Number(fs);
    if (!isFinite(value) || value < 0) return '';

    var display = fusionDisplay(value);
    var tip = fusionTooltip(value > 0 ? '+' + display : '0', skill.fusionBreakdown);
    var bd = skill.fusionBreakdown || {};
    var nodes = bd.transitiveCount || 0;
    var components = (skill.suiteComponents && skill.suiteComponents.length) || 0;

    if (branch === 'suite') {
      var pct = Math.max(2, Math.min(100, Math.round((value / HALL_FUSION_MAX) * 100)));
      var sub = [];
      if (nodes) sub.push(nodes + ' nodes composed');
      if (components) sub.push(components + ' named components');
      return '<div class="hero-card__fusion hero-card__fusion--suite" title="' + esc(tip) + '">' +
        '<span class="hero-card__fusion-label">Fusion Score</span>' +
        '<span class="hero-card__fusion-value" aria-label="Fusion Score plus ' + esc(display) +
          ', a structural reading independent of Trust Magnitude">+' + esc(display) + '</span>' +
        (sub.length ? '<span class="hero-card__fusion-sub">' + esc(sub.join(' · ')) + '</span>' : '') +
        '<span class="hero-card__fusion-bar" aria-hidden="true">' +
          '<span class="hero-card__fusion-bar-fill" style="width:' + pct + '%"></span>' +
        '</span>' +
        '</div>';
    }

    if (value === 0) {
      return '<div class="hero-card__fusion hero-card__fusion--unique hero-card__fusion--zero" ' +
        'title="' + esc(tip) + '">' +
        '<span class="hero-card__fusion-label">Fusion Score</span>' +
        '<span class="hero-card__fusion-value">0</span>' +
        '<span class="hero-card__fusion-sub">composes no distinct structure</span>' +
        '</div>';
    }

    return '<div class="hero-card__fusion hero-card__fusion--unique" title="' + esc(tip) + '">' +
      '<span class="hero-card__fusion-label">Fusion Score</span>' +
      '<span class="hero-card__fusion-value" aria-label="Fusion Score plus ' + esc(display) +
        ', a structural reading independent of Trust Magnitude">+' + esc(display) + '</span>' +
      (nodes ? '<span class="hero-card__fusion-sub">' + nodes + ' nodes composed</span>' : '') +
      '</div>';
  }

  function githubAvatarUrl(handle, size) {
    var clean = String(handle || '').trim().replace(/^@/, '');
    if (!clean) return '';
    return 'https://github.com/' + encodeURIComponent(clean) + '.png?size=' + (size || 160);
  }

  // ── Origin-gated gold-wreath avatar (E3/E4) ───────────────────
  // Renders the contributor's GitHub avatar; origin-wreath-gold.svg appears
  // only when the contributor's top skill is marked `origin: true`.
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
    var wreathHtml = isOrigin
      ? '<img class="hero-card__crest-avatar-wreath" src="' + esc(wreathSrc) + '" alt="" aria-hidden="true">'
      : '';
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
      branch: computeBranchForTopSkill(contributor),
      suiteComponents: skill.suiteComponents,
    };
    // 'lg' size modifier → the AOV4 'hero' tier asset (largest stamp).
    return window.plaque._fields.orb(ns, 'lg');
  }

  function scrollToStage(stage) {
    if (!stage) return;
    // Honor prefers-reduced-motion: skip the smooth animation for users who
    // asked for reduced motion. Gated once here so every caller (dialog entry,
    // rail row, nav arrow) inherits the behavior.
    var prefersReduced = window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    stage.scrollIntoView({ behavior: prefersReduced ? 'auto' : 'smooth', block: 'center' });
  }

  function notifyStageVisible(stage) {
    window.dispatchEvent(new CustomEvent('heroes-stage-visible', { detail: { stage: stage } }));
  }

  // ── Render functions ──────────────────────────────────────────

  function namedSlugText(id) {
    if (!id) return '';
    var s = String(id).indexOf('/') !== -1 ? String(id).split('/', 2)[1] : String(id);
    return s.charAt(0) === '/' ? s : '/' + s;
  }

  function fusedCount(contributor) {
    var topSkill = contributor && contributor.topSkill;
    if (!topSkill) return 0;
    var genericRef = topSkill.genericSkillRef || (topSkill.id ? topSkill.id.split('/').pop() : '');
    var generic = GAIA_SKILL_MAP[genericRef];
    if (!generic || generic.type !== 'fusion') return 0;

    var visited = {};
    function walk(id) {
      if (!id || visited[id] || !GAIA_SKILL_MAP[id]) return;
      visited[id] = true;
      var node = GAIA_SKILL_MAP[id];
      var prereqs = Array.isArray(node.prerequisites) ? node.prerequisites : [];
      prereqs.forEach(function (p) {
        walk(p);
      });
    }

    var directPrereqs = Array.isArray(generic.prerequisites) ? generic.prerequisites : [];
    directPrereqs.forEach(function (p) {
      walk(p);
    });

    return Object.keys(visited).length;
  }

  function renderHeroStage(contributor, tier, index, total) {
    var handle = contributor.handle;
    var skillId = contributor.topSkill.id;
    var slug = namedSlugText(skillId);
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
    // The field plate behind the crest is the branch's material: the Suite gets
    // the gilded haze, the Unique gets the orrery ring. Both are existing
    // Ascension Overdrive art, selected in CSS off data-branch.
    html += '<div class="hero-card__crest-wrapper">';
    html += '<div class="hero-card__field" aria-hidden="true"></div>';
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

    // Ledger column — everything that is read rather than looked at. On desktop
    // it sits beside the crest; on mobile it stacks beneath it.
    html += '<div class="hero-card__ledger">';

    // The branch, stated. Glyph + word + colour together, so the Unique/Suite
    // fork survives for a reader who cannot use hue (PRODUCT.md a11y baseline).
    html += '<div class="hero-card__branchmark"><span class="hero-card__branchmark-glyph" aria-hidden="true">' +
      esc(glyph) + '</span>' + esc(BRANCH_WORD[branch] || BRANCH_WORD.standard) + '</div>';

    // Meta
    html += '<div class="hero-card__meta">';
    html += '<div class="hero-card__tier-mark">' + esc(tierLabel) + '</div>';
    html += '<h2 class="hero-card__name" id="' + esc(titleId) + '"><a class="hero-card__name-link" href="../named/#explorer/' + esc(skillId) + '">' + esc(slug) + '</a></h2>';
    html += '<div class="hero-card__handle"><a class="hero-card__handle-link" href="../u/' + esc(handle) + '/">@' + esc(handle) + '</a></div>';
    if (epithet) {
      html += '<p class="hero-card__epithet">' + esc(epithet) + '</p>';
    }
    html += '<div class="hero-card__stats">';
    html += '<span><span class="hero-card__stat-value">' + formatTrustMagnitude(trustMagnitude(contributor)) + '</span> Trust Magnitude</span>';
    html += '<span><span class="hero-card__stat-value">' + contributor.namedSkills + '</span> named skills</span>';
    // "Fused" counts the distinct prerequisites behind the generic reference.
    // It is zero for most Unique entries, where an empty stat is noise, so the
    // row only carries it when there is something to count.
    var fused = fusedCount(contributor);
    if (fused > 0) {
      html += '<span><span class="hero-card__stat-value">' + fused + '</span> fused</span>';
    }
    html += '</div>';
    html += '</div>';

    var fusionBlock = heroFusionHtml(contributor, branch);
    if (fusionBlock) html += fusionBlock;

    // Card actions. The avatar already links to the source repository (E3), so
    // the row carries the two destinations the crest cannot: the skill's entry
    // in the explorer, and the share plaque.
    html += '<div class="hero-card__actions">';
    html += '<a class="hero-card__cta hero-card__cta--primary" href="../named/#explorer/' + esc(skillId) + '">';
    html += 'View skill entry';
    html += '</a>';
    // data-share-level / data-share-type feed hero-share.js so the shared
    // plaque carries this skill's real rank and type instead of guessing them
    // back out of the rendered stats row.
    html += '<button class="hero-card__share" data-share-handle="' + esc(handle) + '" data-share-skill="' + esc(skillId) + '" data-share-branch="' + esc(branch) + '" data-share-level="' + esc(contributor.topSkill.level || '') + '" data-share-type="' + esc(contributor.topSkill.type || 'basic') + '">';
    html += '<svg class="ico" width="14" height="14" aria-hidden="true"><use href="../assets/icons.svg#link"></use></svg>';
    html += 'Share plaque';
    html += '</button>';
    html += '</div>';

    html += '</div>';

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
      var slug = namedSlugText(skillId) || contributor.handle;
      // E1: glyph keyed by branch, not type.
      var branch = computeBranchForTopSkill(contributor);
      var glyph = BRANCH_GLYPH[branch] || BRANCH_GLYPH.standard;
      var avatarUrl = githubAvatarUrl(contributor.handle, 80);
      // Degrade to the GitHub identicon on avatar error (same fallback the stage
      // crest uses) rather than hiding the cell — hiding collapsed the 26px grid
      // gutter and shifted glyph+name left, misaligning the row vs neighbors.
      // The identicon keeps SOMETHING in the cell so the gutter never empties;
      // the data-fbk guard stops an infinite onerror loop if it also 404s.
      var cleanHandle = String(contributor.handle || '').replace(/^@/, '');
      var identicon = 'https://github.com/identicons/' + encodeURIComponent(cleanHandle) + '.png';
      var avatarErr = "if(this.dataset.fbk){this.onerror=null;}else{this.dataset.fbk='1';this.src='" +
        jsStr(identicon) + "';}";
      var lvl = levelNum(contributor.topSkill.level);
      // The rail row shows only the (truncatable) slug, so carry the full
      // identifier on the button title for hover recovery: full skill name plus
      // @handle when available.
      var fullName = contributor.topSkill.name || slug;
      var handle = contributor.handle;
      var title = fullName + (handle ? ' — @' + handle : '');
      return '<li class="heroes-ledger-rail__item">' +
        '<button class="heroes-ledger-rail__button" type="button" title="' + esc(title) + '" data-ledger-target="' + esc(stageIdFor(contributor)) + '" data-ledger-index="' + esc(index) + '" data-branch="' + esc(branch) + '" data-level="' + lvl + '">' +
        '<span class="heroes-ledger-rail__avatar" aria-hidden="true"><img src="' + esc(avatarUrl) + '" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="' + esc(avatarErr) + '"></span>' +
        '<span class="heroes-ledger-rail__glyph" aria-hidden="true">' + esc(glyph) + '</span>' +
        '<span class="heroes-ledger-rail__name">' + esc(slug) + '</span>' +
        '</button>' +
        '</li>';
    }).join('');

    LEDGER_ITEMS = heroes;
    LEDGER_ACTIVE_INDEX = -1;
    applyLedgerWindow(-1);
    ensureAllPlatesPanel();
    setLedgerAwaiting();
    rail.hidden = false;
  }

  // Chapter head. The Hall runs to 80-odd plates and the old divider only fired
  // on a change of presentational tier, so all 64 rank-4 Uniques arrived as one
  // undivided run. Chapters are keyed on branch AND rank instead, which is the
  // real structure of the ladder: the scroll now reads as four named sections
  // with a plate count each.
  function renderChapter(branch, label, count, index) {
    var glyph = BRANCH_GLYPH[branch] || BRANCH_GLYPH.standard;
    var note = BRANCH_NOTE[branch] || '';
    var plural = count === 1 ? 'plate' : 'plates';
    return '<div class="heroes-chapter" data-branch="' + esc(branch) + '"' +
      (index === 0 ? ' data-first="true"' : '') + '>' +
      '<span class="heroes-chapter__glyph" aria-hidden="true">' + esc(glyph) + '</span>' +
      '<h2 class="heroes-chapter__title">' + esc(label) + '</h2>' +
      '<p class="heroes-chapter__note">' + esc(note) + '</p>' +
      '<span class="heroes-chapter__count">' + count + ' ' + plural + '</span>' +
      '</div>';
  }

  // Live branch tally under the page title. Counts come from the rendered set,
  // never from a hardcoded number, so the header cannot go stale as the
  // registry grows.
  function renderHeaderTally(heroes) {
    var el = document.getElementById('heroesHeaderTally');
    if (!el) return;
    var counts = { unique: 0, suite: 0, standard: 0 };
    heroes.forEach(function (c) {
      var b = computeBranchForTopSkill(c);
      if (counts[b] == null) counts[b] = 0;
      counts[b]++;
    });
    var parts = [];
    if (counts.unique) {
      parts.push('<span class="heroes-header__tally-item" data-branch="unique">' +
        '<span class="heroes-header__tally-glyph" aria-hidden="true">' + BRANCH_GLYPH.unique + '</span>' +
        '<strong>' + counts.unique + '</strong> Unique</span>');
    }
    if (counts.suite) {
      parts.push('<span class="heroes-header__tally-item" data-branch="suite">' +
        '<span class="heroes-header__tally-glyph" aria-hidden="true">' + BRANCH_GLYPH.suite + '</span>' +
        '<strong>' + counts.suite + '</strong> Suite</span>');
    }
    parts.push('<span class="heroes-header__tally-item heroes-header__tally-item--total">' +
      '<strong>' + heroes.length + '</strong> plates</span>');
    el.innerHTML = parts.join('');
    el.hidden = false;
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
    rail.removeAttribute('data-active-branch');
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

  // Reveal only the window of rows around the active index (desktop rail). Cheap
  // on scroll: toggles a class per <li> rather than rebuilding innerHTML. The
  // full list stays in the DOM (the "all plates" panel and prev/next walk it);
  // CSS hides non-windowed rows at ≥820px only, so the mobile carousel is
  // unaffected (it keeps showing every chip and scrolls horizontally).
  function applyLedgerWindow(activeIndex) {
    var list = document.getElementById('heroesLedgerList');
    if (!list) return;
    var items = list.children;
    var total = items.length;
    if (!total) return;

    var lo = activeIndex - LEDGER_WINDOW_BEFORE;
    var hi = activeIndex + LEDGER_WINDOW_AFTER;
    // Slide the window so it stays full-width at the ends (clamp, then shift).
    if (lo < 0) { hi += -lo; lo = 0; }
    if (hi > total - 1) { lo -= (hi - (total - 1)); hi = total - 1; }
    if (lo < 0) lo = 0;

    for (var i = 0; i < total; i++) {
      var inWindow = (activeIndex < 0) ? (i <= LEDGER_WINDOW_BEFORE + LEDGER_WINDOW_AFTER) : (i >= lo && i <= hi);
      items[i].classList.toggle('is-in-window', inWindow);
    }
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

    LEDGER_ACTIVE_INDEX = index;
    applyLedgerWindow(index);

    var lvl = stage.getAttribute('data-level') || '4';
    rail.setAttribute('data-active-level', lvl);
    var activeBranch = stage.getAttribute('data-branch') || '';
    if (activeBranch) {
      rail.setAttribute('data-active-branch', activeBranch);
    } else {
      rail.removeAttribute('data-active-branch');
    }

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
      var slug = namedSlugText(entry.contributor.topSkill.id) || entry.contributor.handle;
      current.textContent = slug;
    }

    if (entry && meta) {
      // E2: rankLabel via GaiaSemantics — no banned words in ledger meta.
      // Plate ordinal matches the stage ordinal EXACTLY (zero-padded "Plate NN
      // / NN") so the two "Plate N" strings on screen never disagree — both
      // derive from index+1 off the same active index.
      var displayLabel = topSkillRankLabel(entry.contributor);
      var plateOrdinal = 'Plate ' + String(index + 1).padStart(2, '0') +
        ' / ' + String(total).padStart(2, '0');
      meta.textContent = displayLabel + ' · ' + plateOrdinal;
    }

    if (progress) {
      progress.style.transform = 'scaleY(' + ((index + 1) / total).toFixed(4) + ')';
    }

    rail.style.setProperty('--heroes-ledger-progress', ((index + 1) / total).toFixed(4));
  }

  // ── "All plates" full index (opened on demand from the rail) ──
  // The windowed rail only shows a neighborhood; this native <dialog> is how
  // EVERY hero stays reachable. It reads LEDGER_ITEMS (the full list), reuses
  // the data-ledger-target scroll-to path, and gets Esc dismiss + focus trap
  // for free from <dialog>.showModal(). Trigger + dialog are injected here so
  // the static index.html markup is untouched.
  var ALL_PLATES_TRIGGER = null;
  var ALL_PLATES_DIALOG = null;

  function ensureAllPlatesPanel() {
    var rail = document.getElementById('heroesLedgerRail');
    if (!rail) return;

    if (!ALL_PLATES_TRIGGER) {
      var trigger = document.createElement('button');
      trigger.type = 'button';
      trigger.className = 'heroes-ledger-rail__all';
      trigger.id = 'heroesLedgerAll';
      trigger.setAttribute('aria-haspopup', 'dialog');
      trigger.setAttribute('aria-controls', 'heroesLedgerAllPanel');
      trigger.innerHTML =
        '<span class="heroes-ledger-rail__all-caret" aria-hidden="true">▾</span>' +
        '<span class="heroes-ledger-rail__all-label"></span>';
      // Insert after the list, before the controls, so it reads as "expand the
      // ledger" beneath the windowed rows.
      var controls = rail.querySelector('.heroes-ledger-rail__controls');
      if (controls) {
        rail.insertBefore(trigger, controls);
      } else {
        rail.appendChild(trigger);
      }
      trigger.addEventListener('click', openAllPlates);
      ALL_PLATES_TRIGGER = trigger;
    }

    // Surface the real count so the button reads as the primary "see everything"
    // affordance ("all N plates"). Derived from LEDGER_ITEMS.length, not a
    // hardcoded 24, and refreshed on every render so it tracks the live list.
    var allLabel = ALL_PLATES_TRIGGER.querySelector('.heroes-ledger-rail__all-label');
    if (allLabel) allLabel.textContent = 'all ' + LEDGER_ITEMS.length + ' plates';

    if (!ALL_PLATES_DIALOG && typeof document.createElement('dialog').showModal === 'function') {
      var dialog = document.createElement('dialog');
      dialog.className = 'heroes-ledger-all';
      dialog.id = 'heroesLedgerAllPanel';
      dialog.setAttribute('aria-label', 'All plates in the Hall of Heroes');
      dialog.innerHTML =
        '<div class="heroes-ledger-all__head">' +
        '<h2 class="heroes-ledger-all__title">All Plates</h2>' +
        '<button class="heroes-ledger-all__close" type="button" aria-label="Close all-plates index">' +
        '<svg class="ico" width="16" height="16" aria-hidden="true"><use href="../assets/icons.svg#close-x"></use></svg>' +
        '</button>' +
        '</div>' +
        '<ol class="heroes-ledger-all__list" id="heroesLedgerAllList"></ol>';
      document.body.appendChild(dialog);

      // Close on the X, on backdrop click, and (native) on Esc.
      dialog.querySelector('.heroes-ledger-all__close').addEventListener('click', closeAllPlates);
      dialog.addEventListener('click', function (e) {
        if (e.target === dialog) closeAllPlates();
      });
      // Clicking an entry scrolls to that plate, then dismisses.
      dialog.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-ledger-target]');
        if (!btn) return;
        closeAllPlates();
        scrollToStage(document.getElementById(btn.getAttribute('data-ledger-target')));
      });
      ALL_PLATES_DIALOG = dialog;
    }
  }

  function renderAllPlatesList() {
    var listEl = document.getElementById('heroesLedgerAllList');
    if (!listEl) return;
    listEl.innerHTML = LEDGER_ITEMS.map(function (entry, index) {
      var contributor = entry.contributor;
      var skillId = contributor.topSkill.id || '';
      var slug = namedSlugText(skillId) || contributor.handle;
      var branch = computeBranchForTopSkill(contributor);
      var glyph = BRANCH_GLYPH[branch] || BRANCH_GLYPH.standard;
      var lvl = levelNum(contributor.topSkill.level);
      // The full index CAN carry @handle + rank — it is the reference view, not
      // the scannable rail. rankLabel is branch-forked (E2), no banned words.
      var rankLabel = topSkillRankLabel(contributor);
      return '<li class="heroes-ledger-all__item">' +
        '<button class="heroes-ledger-all__entry" type="button" data-ledger-target="' + esc(stageIdFor(contributor)) + '" data-ledger-index="' + esc(index) + '" data-branch="' + esc(branch) + '" data-level="' + lvl + '">' +
        '<span class="heroes-ledger-all__glyph" aria-hidden="true">' + esc(glyph) + '</span>' +
        '<span class="heroes-ledger-all__body">' +
        '<span class="heroes-ledger-all__name">' + esc(slug) + '</span>' +
        '<span class="heroes-ledger-all__by">@' + esc(contributor.handle) + ' &middot; ' + esc(rankLabel) + '</span>' +
        '</span>' +
        '</button>' +
        '</li>';
    }).join('');
  }

  function openAllPlates() {
    if (!ALL_PLATES_DIALOG) return;
    renderAllPlatesList();
    ALL_PLATES_DIALOG.showModal();
    // Land focus on the active entry so keyboard users start in context. When
    // LEDGER_ACTIVE_INDEX is -1 (awaiting state, before any scroll) that lookup
    // matches nothing — fall back to the first entry, then the close button, so
    // focus always lands somewhere inside the dialog.
    var active = ALL_PLATES_DIALOG.querySelector('[data-ledger-index="' + LEDGER_ACTIVE_INDEX + '"]') ||
      ALL_PLATES_DIALOG.querySelector('.heroes-ledger-all__entry') ||
      ALL_PLATES_DIALOG.querySelector('.heroes-ledger-all__close');
    if (active) active.focus();
  }

  function closeAllPlates() {
    if (ALL_PLATES_DIALOG && ALL_PLATES_DIALOG.open) ALL_PLATES_DIALOG.close();
    if (ALL_PLATES_TRIGGER) ALL_PLATES_TRIGGER.focus();
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

  // ── First-load reveal sequence (Hall of Heroes ceremonial entrance) ──
  function initFirstLoadReveal() {
    var SEEN_KEY = 'gaia-heroes-intro-seen';
    if (typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (sessionStorage.getItem(SEEN_KEY)) return;
    sessionStorage.setItem(SEEN_KEY, '1');

    var overlay = document.createElement('div');
    overlay.className = 'intro-overlay';
    overlay.setAttribute('aria-hidden', 'true');

    var line1 = document.createElement('div');
    line1.className = 'intro-reveal-line';
    line1.textContent = 'Skills are catalogued.';

    var line2 = document.createElement('div');
    line2.className = 'intro-reveal-line';
    line2.textContent = 'Names are earned.';

    var skipHint = document.createElement('div');
    skipHint.className = 'intro-skip';
    skipHint.textContent = 'click anywhere to skip';

    overlay.appendChild(line1);
    overlay.appendChild(line2);
    overlay.appendChild(skipHint);
    document.body.appendChild(overlay);

    var skipped = false;
    var timers = [];

    function dismiss() {
      if (skipped) return;
      skipped = true;
      timers.forEach(clearTimeout);
      overlay.classList.add('fading');
      setTimeout(function () {
        overlay.classList.add('done');
        if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      }, 1250);
    }

    document.addEventListener('click', dismiss, { once: true });
    document.addEventListener('keydown', dismiss, { once: true });

    timers.push(setTimeout(function () {
      if (!skipped) line1.classList.add('visible');
    }, 300));
    timers.push(setTimeout(function () {
      if (!skipped) line2.classList.add('visible');
    }, 900));
    timers.push(setTimeout(function () {
      dismiss();
    }, 1800));
  }

  // ── Main init ─────────────────────────────────────────────────
  function init() {
    initFirstLoadReveal();
    var container = document.getElementById('heroesStages');
    if (!container) return;

    container.innerHTML = renderLoadingState();

    Promise.all([
      // Contributors API is no longer the Hall's source (§8 selection now reads
      // the named index below); kept as a non-fatal fetch for forward-compat and
      // so a stale/absent API never blanks the Hall.
      fetch(API_URL).then(function (r) {
        return r.ok ? r.json() : { contributors: [] };
      }).catch(function () {
        return { contributors: [] };
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
      }),
      fetch(GRAPH_URL).then(function (r) {
        if (!r.ok) throw new Error('Graph gaia.json fetch failed: ' + r.status);
        return r.json();
      }).catch(function (err) {
        console.warn('[heroes] Graph gaia.json unavailable:', err);
        return { skills: [] };
      })
    ])
      .then(function (results) {
        var ledgerBySkill = trustLedgerMap(results[1]);
        var namedData = results[2];
        var gaiaData = results[3];
        var namedBySkill = namedSkillMap(namedData);

        GAIA_SKILL_MAP = {};
        var gList = (gaiaData && Array.isArray(gaiaData.skills)) ? gaiaData.skills : [];
        gList.forEach(function (s) {
          if (s && s.id) GAIA_SKILL_MAP[s.id] = s;
        });

        // §8: build one hero per qualifying named skill (rank >= 4) from the
        // named index — NOT one-per-contributor off the capped topSkill blob.
        // Enrich each with the Trust Ledger magnitude (falls back to the
        // entry's own trustMagnitude) for the ordering tiebreak.
        var heroes = heroesFromNamedIndex(namedData).map(function (c) {
          return withLedgerTrustMagnitude(withNamedSkillMeta(c, namedBySkill), ledgerBySkill);
        });

        // §8 canonical order: rank desc, Unique before Suite within a rank,
        // Trust Magnitude tiebreak.
        heroes.sort(compareHeroes);

        if (!heroes.length) {
          container.innerHTML = renderEmptyState();
          return;
        }

        var ledgerEntries = [];

        // Scale the suite composition bar against the Hall's own largest score.
        HALL_FUSION_MAX = heroes.reduce(function (max, c) {
          var v = Number(c.topSkill && c.topSkill.fusionScore);
          return isFinite(v) && v > max ? v : max;
        }, 1);

        // Chapter run-lengths, precomputed so each head can state its own count
        // before its plates render.
        function chapterKeyFor(c) {
          var rank = (typeof c.topSkill.rank === 'number') ? c.topSkill.rank : levelNum(c.topSkill.level);
          return computeBranchForTopSkill(c) + '|' + rank;
        }
        var chapterCounts = {};
        heroes.forEach(function (c) {
          var key = chapterKeyFor(c);
          chapterCounts[key] = (chapterCounts[key] || 0) + 1;
        });

        // Fill the header's live branch tally. Real counts off the rendered set,
        // so the intro never drifts from what is actually on the page.
        renderHeaderTally(heroes);

        // Build HTML in strict rank/branch order.
        // E2: chapter labels use rankLabel (branch-forked, no banned words).
        var html = '';
        var renderedIndex = 0;
        var totalHeroes = heroes.length;
        var previousKey = null;
        var chapterIndex = 0;

        function appendHeroStage(c, tier) {
          ledgerEntries.push({ contributor: c, tier: tier });
          html += renderHeroStage(c, tier, renderedIndex++, totalHeroes);
        }

        heroes.forEach(function (c) {
          var tier = stageTierClass(c);
          var key = chapterKeyFor(c);
          if (key !== previousKey) {
            html += renderChapter(
              computeBranchForTopSkill(c),
              topSkillRankLabel(c),
              chapterCounts[key] || 1,
              chapterIndex++
            );
          }
          appendHeroStage(c, tier);
          previousKey = key;
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

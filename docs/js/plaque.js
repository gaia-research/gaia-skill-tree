/* Gaia Plaque component family — Stage 3.
 *
 * Single source of truth for every plaque variant. One field-helper set
 * powers six render methods (mini / tile / row / detail / settled / og).
 * Only variant chrome — layout + which slots are visible — differs.
 *
 *   plaque.renderMini(ns, opts)      // HoH track plate
 *   plaque.renderTile(ns, opts)      // explorer grid card
 *   plaque.renderRow(ns, opts)       // explorer list row
 *   plaque.renderDetail(ns, opts)    // explorer modal hero (two-column)
 *   plaque.renderSettled(ns, opts)   // profile trophy card
 *   plaque.renderOg(ns, opts)        // 1200×630 social card (HTML mock;
 *                                     the canonical OG is server-rendered
 *                                     by scripts/generateOgCards.py)
 *
 * All variants emit `.plaque` + `.plaque--<variant>` with the existing
 * `data-type="<basic|extra|unique|ultimate>"` and `data-level="N"`
 * attributes. Apex (6★) adds `plaque--apex-vi` for the rainbow shimmer
 * shadow animation defined in plaque.css.
 *
 * Forbidden: inline SVG strings, inline hex codes, inline rank chips.
 * - Icons: window.gaiaIcon(id, opts).
 * - Rank surfaces: window.rankBadge(level, opts).
 * - Slug/handle/profile helpers: window.namedSlug / window.handleLink.
 *
 * Loaded AFTER icons.js and rank-badge.js, BEFORE named-skills.js,
 * skill-explorer.js, page-ia.js.
 */
(function () {
  'use strict';

  // ── shared utilities ──────────────────────────────────────────────
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function jsStr(s) {
    return String(s == null ? '' : s).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
  }

  function levelNum(level) {
    if (level == null) return 0;
    if (typeof level === 'number') return level | 0;
    var n = parseInt(String(level).replace(/[^\d]/g, ''), 10);
    return isNaN(n) ? 0 : Math.max(0, Math.min(6, n));
  }

  function icon(id, size) {
    return (typeof window.gaiaIcon === 'function')
      ? window.gaiaIcon(id, { size: size || 14 })
      : '<svg class="ico" width="' + (size || 14) + '" height="' + (size || 14) + '" aria-hidden="true"></svg>';
  }

  function rankBadge(level, opts) {
    if (typeof window.rankBadge !== 'function') return '';
    return window.rankBadge(level, opts || {});
  }

  function namedSlug(ns) {
    if (typeof window.namedSlug === 'function') return window.namedSlug(ns);
    if (!ns) return '';
    var id = ns.id || '';
    if (id.indexOf('/') !== -1) return '/' + id.split('/', 2)[1];
    return '/' + (ns.genericSkillRef || id || '');
  }

  function handleLink(handle, opts) {
    if (typeof window.handleLink === 'function') return window.handleLink(handle || '', opts || {});
    if (!handle) return '';
    var cls = 'atlas-handle' + (opts && opts.extraClass ? ' ' + opts.extraClass : '');
    var rel = (opts && opts.rel) || './u/';
    return '<a class="' + esc(cls) + '" href="' + esc(rel + encodeURIComponent(handle) + '/') + '">@' + esc(handle) + '</a>';
  }

  // ── shared field helpers (one source of truth) ───────────────────
  // Each field helper returns HTML for that slot. Variants opt in/out
  // by including or skipping the slot in their render method — variant
  // chrome lives in CSS, never JS.

  function _fieldOrb(ns, sizeModifier) {
    var type = (ns && ns.type) || 'basic';
    var n = levelNum(ns && ns.level);
    var mod = sizeModifier ? ' plaque-orb--' + sizeModifier : '';
    var apex = n >= 6 ? ' plaque-orb--vi' : '';
    return '<div class="plaque-orb plaque-orb--' + esc(type) + mod + apex + '" aria-hidden="true"></div>';
  }

  function _fieldSlug(ns) {
    var slug = namedSlug(ns);
    var id = ns && ns.id || '';
    return '<div class="plaque__slug plaque-skill-name named-slug" title="' + esc(id) + '">' + esc(slug) + '</div>';
  }

  function _fieldTitle(ns) {
    var title = ns && (ns.title || ns.name) || '';
    if (!title) return '';
    return '<div class="plaque__title plaque-title">' + esc(title) + '</div>';
  }

  function _fieldHandleRow(ns) {
    var contribLink = handleLink(ns && ns.contributor || '');
    if (!contribLink) return '';
    return '<div class="plaque__handle plaque-contrib-row">' + contribLink + _fieldOriginBadge(ns) + '</div>';
  }

  function _fieldDescription(ns) {
    var desc = ns && ns.description || '';
    if (!desc) return '';
    return '<p class="plaque__description plaque-description">' + esc(desc) + '</p>';
  }

  function _fieldTags(ns, limit) {
    var tags = (ns && Array.isArray(ns.tags)) ? ns.tags : [];
    var cap = (typeof limit === 'number') ? limit : tags.length;
    var sliced = tags.slice(0, cap);
    if (!sliced.length) return '';
    var inner = sliced.map(function (t) {
      return '<span class="plaque__tag plaque-tag">' + esc(t) + '</span>';
    }).join('');
    return '<div class="plaque__tags plaque-tags">' + inner + '</div>';
  }

  function _fieldRank(ns, variant) {
    var v = variant || 'stars';
    var type = (ns && ns.type) || 'basic';
    var html = rankBadge(ns && ns.level, { variant: v, label: ns && ns.level, tier: type });
    if (!html) return '';
    return '<div class="plaque__rank">' + html + '</div>';
  }

  function _fieldGhLink(ns) {
    var links = (ns && ns.links) || {};
    var url = links.github || links.npm || '';
    if (!url) return '';
    return '<a class="plaque__gh-link ns-gh-link" href="' + esc(url) +
      '" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="View on GitHub">' +
      icon('github', 14) + '</a>';
  }

  function _fieldVariantsBadge(ns) {
    if (!ns || !ns.variants || !ns.variants.length) return '';
    var count = ns.variants.length;
    return '<div class="plaque__variants-badge ns-variants-badge" title="' + count + ' additional implementation(s) available">' +
      '+' + count + ' implementation' + (count > 1 ? 's' : '') +
      '</div>';
  }

  function _fieldOriginBadge(ns) {
    if (!ns || !ns.origin) return '';
    // Stage 4 — render the origin badge from the shared sprite so it inherits
    // --honor-red via currentColor. Include a small (i) icon for context on hover.
    return '<span class="plaque__origin" data-tooltip="Origin contributor: The creator of the first skill version" aria-label="Origin contributor: The creator of the first skill version">' +
      icon('origin-badge', 16) +
      '<span class="origin-info" style="margin-left: 3px; color: var(--muted); opacity: 0.7;">' + icon('info', 10) + '</span>' +
      '</span>';
  }

  // Install row — shared mini-terminal block (used by tile / detail / settled).
  // The copy button is wired in via inline onclick that delegates to
  // window.nsInstCopy (defined by named-skills.js). If that's not present
  // we fall back to navigator.clipboard inline.
  function _fieldInstallRow(ns) {
    if (!ns || !ns.id) return '';
    var cmd = 'gaia install ' + ns.id;
    var copyClick = 'event.stopPropagation();' +
      'if(typeof window.nsInstCopy===\'function\'){window.nsInstCopy(this);}' +
      'else{navigator.clipboard.writeText(this.dataset.cmd);}';
    return '<div class="plaque__install-row ns-install-row">' +
      '<span class="plaque__install-prompt ns-install-prompt">$</span>' +
      '<span class="plaque__install-cmd ns-install-cmd-txt">' + esc(cmd) + '</span>' +
      '<button class="plaque__install-copy ns-install-copy" type="button" aria-label="Copy install command" title="Copy install command" data-cmd="' + esc(cmd) + '" onclick="' + copyClick + '">' +
      icon('copy', 13) + '</button>' +
      '</div>';
  }

  function _fieldSlugInteractive(ns, onclickAttr) {
    var slug = namedSlug(ns);
    var id = ns && ns.id || '';
    if (onclickAttr) {
      return '<button class="plaque__slug plaque-skill-name named-slug plaque__slug--clickable" type="button" title="' + esc(id) + '" onclick="event.stopPropagation(); ' + onclickAttr + '">' + esc(slug) + '</button>';
    }
    return _fieldSlug(ns);
  }

  function _fieldFullscreenBtn(ns) {
    if (!ns || !ns.id) return '';
    var skillId = ns.id;
    var handle = ns.contributor || '';
    var name = ns.name || '';
    var level = ns.level || '';
    var type = ns.type || '';
    var origin = ns.origin ? 'true' : 'false';
    var desc = ns.description || '';
    var tagsRaw = (ns.tags && ns.tags.length) ? JSON.stringify(ns.tags) : '';
    var slashIdx = skillId.indexOf('/');
    var skillIdShort = slashIdx !== -1 ? skillId.slice(slashIdx + 1) : skillId;
    var ogPath = handle && skillIdShort ? 'og/' + handle + '/' + skillIdShort + '.svg' : '';
    return '<button class="plaque__fs-btn" type="button" aria-label="Fullscreen View" title="Show Fullscreen Social Card" ' +
      'data-skill-id="' + esc(skillId) + '" ' +
      'data-handle="' + esc(handle) + '" ' +
      'data-skill-name="' + esc(name) + '" ' +
      'data-level="' + esc(level) + '" ' +
      'data-type="' + esc(type) + '" ' +
      'data-origin="' + esc(origin) + '" ' +
      'data-desc="' + esc(desc) + '" ' +
      'data-tags="' + esc(tagsRaw) + '" ' +
      'data-og="' + esc(ogPath) + '">' +
      icon('share', 12) +
      '</button>';
  }

  // ── plaque shell ─────────────────────────────────────────────────
  function _shell(variant, ns, innerHtml, extraOpts) {
    var type = (ns && ns.type) || 'basic';
    var n = levelNum(ns && ns.level);
    var apex = n >= 6 ? ' plaque--apex-vi' : '';
    extraOpts = extraOpts || {};
    var extraCls = extraOpts.extraClass ? ' ' + extraOpts.extraClass : '';
    var clickAttr = '';
    if (ns && ns.id && extraOpts.click !== false) {
      clickAttr = ' onclick="' + (extraOpts.onclick ||
        '(function(id){if(typeof openSkillExplorer===\'function\')openSkillExplorer(id);})(\'' + jsStr(ns.id) + '\')') + '"';
    }
    var role = extraOpts.role ? ' role="' + esc(extraOpts.role) + '" tabindex="0"' : '';
    var extraAttrs = extraOpts.attrs || '';
    return '<article class="plaque plaque--' + esc(variant) + apex + extraCls +
      '" data-type="' + esc(type) + '" data-level="' + esc(n) +
      '" data-skill-id="' + esc(ns && ns.id || '') + '"' +
      clickAttr + role + extraAttrs + '>' +
      innerHtml +
      '</article>';
  }

  // ── variant: mini (HoH track plate + tree-view DAG node) ────────
  // Field set: orb · slug · handle · rank stars (no description, no tags,
  // no install row).
  // Stage 4 — extra opts supported:
  //   opts.dagId   string  → emits data-id=<dagId> so the Tree-view
  //                          DAG layer can resolve nodes for arrow drawing.
  //   opts.ghost   boolean → emits data-ghost + a hatched-border CSS hook
  //                          (no GitHub icon for ghosts; suppress rank stars).
  //   opts.extraClass / attrs / onclick / click flow through _shell.
  function renderMini(ns, opts) {
    opts = opts || {};
    var isGhost = !!opts.ghost;
    var shellOpts = { click: false };
    var extra = opts.extraClass || '';
    if (isGhost) extra = (extra ? extra + ' ' : '') + 'plaque--ghost';
    if (extra) shellOpts.extraClass = extra;
    var attrs = opts.attrs || '';
    if (opts.dagId) attrs += ' data-id="' + esc(opts.dagId) + '"';
    if (isGhost) attrs += ' data-ghost="true"';
    if (attrs) shellOpts.attrs = attrs;

    var slugOnclick = opts.onclick || ('(function(id){if(typeof openSkillExplorer===\'function\')openSkillExplorer(id);})(\'' + jsStr(ns.id) + '\')');

    var inner =
      _fieldOrb(ns) +
      (isGhost ? '' : _fieldHandleRow(ns)) +
      (isGhost ? '' : _fieldRank(ns, 'stars')) +
      (isGhost ? _fieldSlug(ns) : _fieldSlugInteractive(ns, slugOnclick)) +
      (isGhost ? '' : _fieldFullscreenBtn(ns)) +
      (isGhost ? '' : _fieldGhLink(ns));

    return _shell('mini', ns, inner, shellOpts);
  }

  // ── variant: tile (explorer grid) ────────────────────────────────
  // Field set: header (orb + level chip + origin star + gh link)
  //          · slug · title · handle · description · tags (3) · install row.
  function renderTile(ns, opts) {
    var header =
      '<div class="plaque__header plaque-header">' +
        _fieldOrb(ns) +
        _fieldRank(ns, 'chip') +
        _fieldGhLink(ns) +
      '</div>';

    var inner =
      header +
      _fieldSlug(ns) +
      _fieldTitle(ns) +
      _fieldHandleRow(ns) +
      _fieldDescription(ns) +
      _fieldTags(ns, 3) +
      _fieldInstallRow(ns);

    return _shell('tile', ns, inner, opts);
  }

  // ── variant: row (explorer list) ─────────────────────────────────
  // Field set: same as tile, laid horizontally. Description hidden via
  // CSS only — no silent field drops at the JS level.
  function renderRow(ns, opts) {
    var inner =
      _fieldOrb(ns, 'sm') +
      _fieldSlug(ns) +
      _fieldTitle(ns) +
      _fieldHandleRow(ns) +
      _fieldTags(ns, 2) +
      _fieldRank(ns, 'chip') +
      _fieldGhLink(ns) +
      '<span class="plaque__arrow ns-lr-arrow" aria-hidden="true">›</span>';

    return _shell('row', ns, inner, opts);
  }

  // ── variant: detail (explorer modal hero, two-column) ────────────
  // Left column: orb (lg) · slug · handle · rank (full) · install row · gh link
  // Right column: title · description · tags
  function renderDetail(ns, opts) {
    opts = opts || {};
    var links = (ns && ns.links) || {};
    var repoUrl = links.github || links.npm || '';
    var ghLink = repoUrl
      ? '<a class="plaque__gh-link ns-gh-link" href="' + esc(repoUrl) + '" target="_blank" rel="noopener" aria-label="Show on GitHub">' +
          icon('github', 14) + '</a>'
      : '';

    var skillId = (ns && ns.id) || '';
    var slashIdx = skillId.indexOf('/');
    var skillIdShort = slashIdx !== -1 ? skillId.slice(slashIdx + 1) : skillId;
    var handle = (ns && ns.contributor) || '';
    var skillName = (ns && ns.name) || '';
    var ogPath = handle && skillIdShort ? '/og/' + handle + '/' + skillIdShort + '.svg' : '';
    var actions =
      '<div class="plaque__actions plaque-detail-actions">' +
        '<button type="button" class="plaque__share-btn" ' +
          'data-skill-id="' + esc(skillId) + '" ' +
          'data-skill-name="' + esc(skillName) + '" ' +
          'data-handle="' + esc(handle) + '" ' +
          'data-og="' + esc(ogPath) + '" ' +
          'aria-label="Share this skill">' +
          icon('share', 14) +
        '</button>' +
        '<button type="button" class="plaque__claim-btn" data-claim="unclaimed" ' +
          'aria-disabled="true" title="Badge claim coming soon">' +
          'Add to README' +
        '</button>' +
      '</div>';

    var left =
      '<div class="plaque__col plaque-detail-left">' +
        _fieldOrb(ns, 'lg') +
        _fieldSlug(ns) +
        _fieldHandleRow(ns) +
        _fieldRank(ns, 'stars') +
        _fieldInstallRow(ns) +
        ghLink +
        actions +
      '</div>';

    var right =
      '<div class="plaque__col plaque-detail-right">' +
        _fieldTitle(ns) +
        _fieldDescription(ns) +
        _fieldTags(ns) +
      '</div>';

    // Detail is the modal content — it's not itself clickable.
    var shellOpts = Object.assign({}, opts, { click: false });
    return _shell('detail', ns, left + right, shellOpts);
  }

  // ── variant: settled (profile trophy card) ───────────────────────
  // Tile field set + rank stars + evidence-class chip + gold underline.
  function renderSettled(ns, opts) {
    opts = opts || {};
    var header =
      '<div class="plaque__header plaque-header">' +
        _fieldOrb(ns) +
        _fieldRank(ns, 'chip') +
        _fieldGhLink(ns) +
      '</div>';

    var inner =
      header +
      _fieldSlug(ns) +
      _fieldTitle(ns) +
      _fieldHandleRow(ns) +
      _fieldDescription(ns) +
      _fieldTags(ns, 5) +
      _fieldRank(ns, 'stars') +
      '<div class="plaque__evidence plaque-evidence">' + esc(_evidenceClass(ns && ns.level)) + '</div>' +
      '<div class="plaque__underline plaque-underline plaque-underline--settled"></div>';

    return _shell('settled', ns, inner, opts);
  }

  function _evidenceClass(level) {
    var n = levelNum(level);
    if (n >= 4) return 'CLASS A';
    if (n >= 3) return 'CLASS B';
    if (n >= 2) return 'CLASS C';
    return 'AWAITED';
  }

  // ── variant: og (HTML mock of the 1200×630 social card) ──────────
  // The canonical OG card is generated as SVG by generateOgCards.py.
  // This HTML mock exists so the sampler page can show what the OG card
  // looks like in-browser — at scaled-down size — without a raster step.
  function renderOg(ns, opts) {
    opts = opts || {};
    var header =
      '<div class="plaque__header plaque-header">' +
        '<span class="plaque__og-seal">' + icon('seal-diamond', 36) + '</span>' +
        _fieldRank(ns, 'full') +
      '</div>';

    var inner =
      header +
      _fieldOrb(ns, 'lg') +
      _fieldSlug(ns) +
      _fieldTitle(ns) +
      _fieldHandleRow(ns) +
      _fieldDescription(ns) +
      _fieldTags(ns, 4) +
      _fieldInstallRow(ns);

    var shellOpts = Object.assign({}, opts, { click: false });
    return _shell('og', ns, inner, shellOpts);
  }

  // ── variant: mini-stack (HoH track plate, multi-skill per contributor) ─
  // Lists up to N qualifying slash-skills for ONE contributor, each in its
  // own row with row-level data-type/data-level so per-skill CSS rules
  // resolve the correct tier/rank colour. The plate's outer data-type +
  // data-level reflect the contributor's PRIMARY (highest-ranked) skill —
  // that's what drives the orb glow + Apex shimmer halo.
  //
  // Inputs:
  //   skills  Array of { id, name, contributor, level, type, origin,
  //                       canonicalId, onclick }  — pre-sorted highest first.
  //   opts.maxRows  default 3.  More than maxRows → "+N more" overflow row.
  function renderMiniStack(skills, opts) {
    opts = opts || {};
    if (!Array.isArray(skills) || !skills.length) return '';
    var TYPE_RANK = { ultimate: 0, unique: 1, extra: 2, basic: 3 };
    var sorted = skills.slice().sort(function (a, b) {
      var ld = levelNum(b.level) - levelNum(a.level);
      if (ld !== 0) return ld;
      return (TYPE_RANK[a.type] || 9) - (TYPE_RANK[b.type] || 9);
    });
    var primary = sorted[0];
    var maxRows = (typeof opts.maxRows === 'number') ? opts.maxRows : 3;
    var visible = sorted.slice(0, maxRows);
    var overflow = Math.max(0, sorted.length - visible.length);

    var anyOrigin = sorted.some(function (s) { return !!s.origin; });
    var primaryNs = {
      id: primary.id,
      name: primary.name,
      contributor: primary.contributor,
      origin: anyOrigin,
      level: primary.level,
      type: primary.type,
    };

    var TIER_GLYPH = { ultimate: '◆', unique: '◉', extra: '◇', basic: '○' };

    var header =
      '<div class="plaque__stack-header">' +
        _fieldOrb(primaryNs) +
        _fieldHandleRow(primaryNs) +
        _fieldFullscreenBtn(primaryNs) +
      '</div>';

    var rows = visible.map(function (s) {
      var n = levelNum(s.level);
      var glyph = TIER_GLYPH[s.type] || TIER_GLYPH.basic;
      var slug = namedSlug(s);
      var slugTitle = s.id || '';
      var clickAttr = s.onclick
        ? 'event.stopPropagation(); ' + s.onclick
        : '(function(id){if(typeof openSkillExplorer===\'function\')openSkillExplorer(id);})(\'' + jsStr(s.canonicalId || s.id) + '\')';
      var stars = rankBadge(s.level, { variant: 'stars', label: s.level, tier: s.type });
      return '<div class="plaque__stack-row" data-type="' + esc(s.type || 'basic') +
        '" data-level="' + esc(n) + '">' +
          '<span class="plaque__stack-glyph tier-glyph" data-type="' + esc(s.type || 'basic') +
            '" aria-hidden="true">' + glyph + '</span>' +
          '<button class="plaque__slug plaque-skill-name named-slug plaque__slug--clickable" type="button" ' +
            'title="' + esc(slugTitle) + '" onclick="' + clickAttr + '">' + esc(slug) + '</button>' +
          (stars ? '<span class="plaque__stack-rank">' + stars + '</span>' : '') +
        '</div>';
    }).join('');

    var moreRow = overflow
      ? '<div class="plaque__stack-more">+' + overflow + ' more</div>'
      : '';

    var inner = header + '<div class="plaque__stack-body">' + rows + moreRow + '</div>';
    var shellOpts = { click: false, extraClass: 'plaque--mini-stack' };
    return _shell('mini', primaryNs, inner, shellOpts);
  }

  // ── public API ───────────────────────────────────────────────────
  var plaque = {
    renderMini: renderMini,
    renderMiniStack: renderMiniStack,
    renderTile: renderTile,
    renderRow: renderRow,
    renderDetail: renderDetail,
    renderSettled: renderSettled,
    renderOg: renderOg,
    // Private helpers exposed for debugging only; do not depend on these
    // in call-site code — the public render methods are the contract.
    _fields: {
      orb: _fieldOrb,
      slug: _fieldSlug,
      title: _fieldTitle,
      handle: _fieldHandleRow,
      description: _fieldDescription,
      tags: _fieldTags,
      rank: _fieldRank,
      install: _fieldInstallRow,
      gh: _fieldGhLink,
      origin: _fieldOriginBadge,
    },
  };

  window.plaque = plaque;
})();

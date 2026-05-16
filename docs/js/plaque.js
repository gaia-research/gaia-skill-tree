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
    return '<div class="plaque__handle plaque-contrib-row">' + contribLink + '</div>';
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
    var html = rankBadge(ns && ns.level, { variant: v, label: ns && ns.level });
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

  function _fieldOriginStar(ns) {
    if (!ns || !ns.origin) return '';
    return '<span class="plaque__origin ns-origin" title="Origin contributor">★</span>';
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
      '<button class="plaque__install-copy ns-install-copy" type="button" title="Copy install command" data-cmd="' + esc(cmd) + '" onclick="' + copyClick + '">' +
      icon('copy', 13) + '</button>' +
      '</div>';
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

  // ── variant: mini (HoH track plate) ──────────────────────────────
  // Field set: orb · slug · handle · rank stars (no description, no tags,
  // no install row).
  function renderMini(ns, opts) {
    var inner =
      _fieldOrb(ns) +
      _fieldSlug(ns) +
      _fieldHandleRow(ns) +
      _fieldRank(ns, 'stars');
    return _shell('mini', ns, inner, opts);
  }

  // ── variant: tile (explorer grid) ────────────────────────────────
  // Field set: header (orb + level chip + origin star + gh link)
  //          · slug · title · handle · description · tags (3) · install row.
  function renderTile(ns, opts) {
    var header =
      '<div class="plaque__header plaque-header">' +
        _fieldOrb(ns) +
        _fieldRank(ns, 'chip') +
        _fieldOriginStar(ns) +
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
      ? '<a class="plaque__gh-link se-github-link" href="' + esc(repoUrl) + '" target="_blank" rel="noopener">' +
          icon('github', 14) + ' Show on GitHub ' + icon('external-link', 12) + '</a>'
      : '';

    var left =
      '<div class="plaque__col plaque-detail-left">' +
        _fieldOrb(ns, 'lg') +
        _fieldSlug(ns) +
        _fieldHandleRow(ns) +
        _fieldRank(ns, 'full') +
        _fieldInstallRow(ns) +
        ghLink +
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
        _fieldOriginStar(ns) +
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

  // ── public API ───────────────────────────────────────────────────
  var plaque = {
    renderMini: renderMini,
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
      origin: _fieldOriginStar,
    },
  };

  window.plaque = plaque;
})();

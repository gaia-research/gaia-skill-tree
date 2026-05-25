/* plaque.js — client-side plaque card renderer.
 * Exposes window.plaque with renderSettled(), renderTile(), renderMini().
 * Depends on: icons.js (window.icon), rank-badge.js (window.rankBadge).
 */
(function () {
  var ICON_BASE = document.documentElement.getAttribute('data-icon-base') || '../../assets/icons.svg';

  var TAG_PAL = [
    { c:'var(--tier-basic, #38bdf8)',    bg:'var(--tier-basic-bg, rgba(56,189,248,.12))',   bd:'var(--tier-basic-border, rgba(56,189,248,.3))'    },
    { c:'var(--tier-extra, #c084fc)',    bg:'var(--tier-extra-bg, rgba(192,132,252,.12))',  bd:'var(--tier-extra-border, rgba(192,132,252,.3))'   },
    { c:'var(--rank-2, #63cab7)',        bg:'var(--rank-2-bg, rgba(99,202,183,.12))',       bd:'var(--rank-2-border, rgba(99,202,183,.3))'        },
    { c:'var(--rank-3, #a78bfa)',        bg:'var(--rank-3-bg, rgba(167,139,250,.12))',      bd:'var(--rank-3-border, rgba(167,139,250,.3))'       },
    { c:'var(--tier-ultimate, #f59e0b)', bg:'var(--tier-ultimate-bg, rgba(245,158,11,.12))',bd:'var(--tier-ultimate-border, rgba(245,158,11,.3))' },
    { c:'var(--rank-4, #e879f9)',        bg:'var(--rank-4-bg, rgba(232,121,249,.12))',      bd:'var(--rank-4-border, rgba(232,121,249,.3))'       },
  ];

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function tagColor(t) {
    var h = 0;
    for (var i = 0; i < t.length; i++) h = (h * 31 + t.charCodeAt(i)) % TAG_PAL.length;
    return TAG_PAL[h];
  }

  function tagHtml(t) {
    var p = tagColor(t);
    return '<span class="plaque__tag" style="color:' + p.c + ';background:' + p.bg + ';border-color:' + p.bd + '">' + esc(t) + '</span>';
  }

  function ico(id, size) {
    return '<svg class="ico" width="' + size + '" height="' + size + '" aria-hidden="true"><use href="' + ICON_BASE + '#' + id + '"/></svg>';
  }

  /* ── field builders ─────────────────────────────────────── */

  function fieldOrb(ns) {
    var type = ns.type || 'basic';
    return '<div class="plaque-orb" data-type="' + esc(type) + '"></div>';
  }

  function fieldRankChip(ns) {
    var n = window.rankBadge.levelNum(ns.level);
    return window.rankBadge.chip(n);
  }

  function fieldRankStars(ns) {
    var n = window.rankBadge.levelNum(ns.level);
    return window.rankBadge.stars(n);
  }

  function fieldOriginBadge(ns) {
    if (!ns || !ns.origin) return '';
    return (
      '<span class="plaque__origin" ' +
      'data-tooltip="Origin contributor: The creator of the first skill version" ' +
      'aria-label="Origin contributor">' +
      ico('origin-badge', 16) +
      '<span class="origin-info">' + ico('info', 10) + '</span>' +
      '</span>'
    );
  }

  function fieldGhLink(ns) {
    var url = (ns.links || {}).github || (ns.links || {}).npm || '';
    if (!url) return '';
    return (
      '<a class="plaque__gh-link" href="' + esc(url) + '" ' +
      'target="_blank" rel="noopener" onclick="event.stopPropagation()" title="View on GitHub">' +
      ico('github', 14) + '</a>'
    );
  }

  function fieldShareBtn(ns) {
    return (
      '<button class="plaque__share-btn" type="button" ' +
      'aria-label="Share ' + esc(ns.name || ns.id) + '" ' +
      'data-skill-id="' + esc(ns.id) + '" ' +
      'onclick="event.stopPropagation();profileShare.open(this)">' +
      ico('share', 14) + '</button>'
    );
  }

  function fieldSlug(ns) {
    var slug = '/' + String(ns.id || '').split('/').pop();
    return '<div class="plaque__slug">' + esc(slug) + '</div>';
  }

  function fieldTitle(ns) {
    var name = ns.name || (String(ns.id || '').split('/').pop()) || ns.id;
    return '<div class="plaque__title">' + esc(name) + '</div>';
  }

  function fieldHandle(ns) {
    var h = ns.contributor || '';
    return '<div class="plaque__handle">by <a href="../../u/' + esc(h) + '/">@' + esc(h) + '</a></div>';
  }

  function fieldDescription(ns) {
    if (!ns.description) return '';
    var d = String(ns.description).slice(0, 220) + (ns.description.length > 220 ? '…' : '');
    return '<p class="plaque__description">' + esc(d) + '</p>';
  }

  function fieldTags(ns, max) {
    var tags = (ns.tags || []).slice(0, max || 5).map(tagHtml).join('');
    return tags ? '<div class="plaque__tags">' + tags + '</div>' : '';
  }

  function fieldEvidence(ns) {
    var n = window.rankBadge.levelNum(ns.level);
    var cls = n >= 4 ? 'CLASS A' : n === 3 ? 'CLASS B' : n === 2 ? 'CLASS C' : 'AWAITED';
    return '<div class="plaque__evidence">' + cls + '</div>';
  }

  function fieldInstall(ns) {
    if (!ns.id) return '';
    var cmd = 'gaia install ' + ns.id;
    return (
      '<div class="plaque__install-row">' +
      '<span class="plaque__install-prompt">$</span>' +
      '<span class="plaque__install-cmd">' + esc(cmd) + '</span>' +
      '<button class="plaque__install-copy" type="button" aria-label="Copy" title="Copy" ' +
      'data-cmd="' + esc(cmd) + '" onclick="event.stopPropagation();placCopy(this)">' +
      ico('copy', 13) + '</button></div>'
    );
  }

  /* ── shell wrapper ──────────────────────────────────────── */

  function shell(variant, ns, inner) {
    var n    = window.rankBadge.levelNum(ns.level);
    var type = ns.type || 'basic';
    var apex = n >= 6 ? ' plaque--apex-vi' : '';
    return (
      '<article class="plaque plaque--' + variant + apex + '" ' +
      'data-skill-id="' + esc(ns.id || '') + '" ' +
      'data-type="' + esc(type) + '" data-level="' + n + '">' +
      inner + '</article>'
    );
  }

  /* ── public variants ────────────────────────────────────── */

  function renderSettled(ns) {
    var header = (
      '<div class="plaque__header">' +
      fieldOrb(ns) + fieldRankChip(ns) + fieldOriginBadge(ns) +
      fieldGhLink(ns) + fieldShareBtn(ns) +
      '</div>'
    );
    var inner = (
      header +
      fieldSlug(ns) + fieldTitle(ns) + fieldHandle(ns) +
      fieldDescription(ns) + fieldTags(ns, 5) +
      fieldRankStars(ns) + fieldEvidence(ns) + fieldInstall(ns) +
      '<div class="plaque__underline"></div>'
    );
    return shell('settled', ns, inner);
  }

  function renderTile(ns) {
    var header = (
      '<div class="plaque__header">' +
      fieldOrb(ns) + fieldRankChip(ns) + fieldOriginBadge(ns) +
      fieldGhLink(ns) + '</div>'
    );
    var inner = (
      header +
      fieldSlug(ns) + fieldTitle(ns) + fieldHandle(ns) +
      fieldDescription(ns) + fieldTags(ns, 3) + fieldInstall(ns)
    );
    return shell('tile', ns, inner);
  }

  function renderMini(ns) {
    var inner = fieldOrb(ns) + fieldSlug(ns) + fieldHandle(ns) + fieldRankStars(ns);
    return shell('mini', ns, inner);
  }

  /* ── copy helper ────────────────────────────────────────── */
  window.placCopy = function (btn) {
    navigator.clipboard.writeText(btn.dataset.cmd).then(function () {
      var prev = btn.innerHTML;
      btn.innerHTML = ico('check', 13);
      setTimeout(function () { btn.innerHTML = prev; }, 1500);
    }).catch(function () {});
  };

  window.plaque = { renderSettled: renderSettled, renderTile: renderTile, renderMini: renderMini };
})();

/* Gaia icon helper — Stage 1 (foundation).
 *
 * Resolves the sprite path so the helper works from both the site root
 * (docs/index.html) and from nested pages (docs/u/<handle>/index.html,
 * docs/samples/foundation.html, …).
 *
 * Resolution order:
 *   1. window.GAIA_ICON_BASE if set explicitly (a per-page override).
 *   2. <html data-icon-base="…"> attribute if present.
 *   3. Computed from window.location.pathname depth — '../' per nested
 *      level above docs/, prefixing 'assets/icons.svg'.
 *
 * Exposes:
 *   - window.gaiaIconBase()   → returns 'assets/icons.svg' or '../../assets/icons.svg'
 *   - window.gaiaIcon(id, opts)
 *
 * The opts object accepts:
 *   - className  (default 'ico')   → CSS class on the wrapper svg
 *   - title      (string|null)     → adds <title> for accessibility; sets role="img"
 *   - size       (number|null)     → optional width/height (px). Defaults to CSS.
 */
(function () {
  function computeBase() {
    if (typeof window.GAIA_ICON_BASE === 'string' && window.GAIA_ICON_BASE) {
      return window.GAIA_ICON_BASE;
    }
    var htmlEl = document.documentElement;
    if (htmlEl && htmlEl.getAttribute('data-icon-base')) {
      return htmlEl.getAttribute('data-icon-base');
    }
    // Heuristic: count path segments after the docs root.
    // The site is published at the repo root on GH Pages, with docs/ → /.
    // Nested pages we know about:
    //   /u/<handle>/index.html         → 2 levels deep
    //   /samples/<name>.html           → 1 level deep
    // Everything else (incl. /, /codex.html, /how-we-do-things.html) → 0.
    try {
      var path = window.location.pathname.replace(/\/+$/, '');
      var segs = path.split('/').filter(Boolean);
      // Trim a trailing filename like 'index.html' or 'codex.html'.
      if (segs.length && /\.html?$/i.test(segs[segs.length - 1])) {
        segs.pop();
      }
      // Trim a top-level repo slug used on GitHub Pages (e.g. 'gaia-skill-tree').
      // We only walk relative — if first segment matches our known nested
      // mounts ('u' or 'samples'), we count from there. Otherwise treat as
      // root-level.
      var depth = 0;
      var idx = segs.indexOf('u');
      var idxS = segs.indexOf('samples');
      if (idx !== -1) {
        depth = segs.length - idx;
      } else if (idxS !== -1) {
        depth = segs.length - idxS;
      }
      var prefix = '';
      for (var i = 0; i < depth; i++) prefix += '../';
      return prefix + 'assets/icons.svg';
    } catch (_e) {
      return 'assets/icons.svg';
    }
  }

  var _cachedBase = null;
  function gaiaIconBase() {
    if (_cachedBase === null) _cachedBase = computeBase();
    return _cachedBase;
  }

  function gaiaIcon(id, opts) {
    opts = opts || {};
    var cls = opts.className || 'ico';
    var size = opts.size;
    var title = opts.title || null;
    var attrs = 'class="' + cls + '" aria-hidden="' + (title ? 'false' : 'true') + '"';
    if (title) attrs += ' role="img"';
    if (size) attrs += ' width="' + size + '" height="' + size + '"';
    var inner = (title ? '<title>' + String(title)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</title>' : '') +
      '<use href="' + gaiaIconBase() + '#' + id + '"/>';
    return '<svg ' + attrs + '>' + inner + '</svg>';
  }

  window.gaiaIconBase = gaiaIconBase;
  window.gaiaIcon = gaiaIcon;
})();

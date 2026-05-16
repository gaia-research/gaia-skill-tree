/* Gaia rank badge — Stage 2 (rank unification).
 *
 * Single component that renders every rank surface (chip, stars, full).
 * Reads colours purely from CSS tokens via attribute selectors on
 * .rank-badge[data-level="N"] — see the .rank-badge rule block in
 * docs/css/styles.css. No JS colour logic; no inline style strings.
 *
 * Exposes:
 *   - window.rankBadge(level, opts)
 *
 * Args:
 *   - level   string | number   e.g. '4★', '4', 4
 *   - opts.variant  'chip' | 'stars' | 'full'   (default 'chip')
 *   - opts.size     'sm' | 'md' | 'lg'          (default 'md')
 *   - opts.label    string                       (default '<N>★', shown in chip)
 *   - opts.ariaLabel string                      (default 'Rank <N> of 6')
 *
 * Returns: HTML string.
 *
 * DOM shape:
 *   <span class="rank-badge" data-level="N" data-variant="<variant>" data-size="<size>">
 *     <span class="rank-badge__chip">N★</span>          (chip / full)
 *     <span class="rank-badge__stars">                   (stars / full)
 *       <span class="rank-badge__star" data-on>★</span>
 *       …six total, data-on for lit / data-off for dim…
 *     </span>
 *   </span>
 */
(function () {
  function levelNum(level) {
    if (level == null) return 0;
    if (typeof level === 'number') return level | 0;
    var n = parseInt(String(level).replace(/[^\d]/g, ''), 10);
    return isNaN(n) ? 0 : Math.max(0, Math.min(6, n));
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function chipHtml(n, label) {
    var text = label != null ? label : (n + '★');
    return '<span class="rank-badge__chip">' + esc(text) + '</span>';
  }

  function starsHtml(n) {
    var out = '<span class="rank-badge__stars" aria-hidden="true">';
    for (var i = 1; i <= 6; i++) {
      var lit = i <= n;
      out += '<span class="rank-badge__star" ' + (lit ? 'data-on=""' : 'data-off=""') + '>★</span>';
    }
    out += '</span>';
    return out;
  }

  function rankBadge(level, opts) {
    opts = opts || {};
    var n = levelNum(level);
    var variant = opts.variant || 'chip';
    if (variant !== 'chip' && variant !== 'stars' && variant !== 'full') variant = 'chip';
    var size = opts.size || 'md';
    if (size !== 'sm' && size !== 'md' && size !== 'lg') size = 'md';
    var aria = opts.ariaLabel || ('Rank ' + n + ' of 6');

    var inner = '';
    if (variant === 'chip') {
      inner = chipHtml(n, opts.label);
    } else if (variant === 'stars') {
      inner = starsHtml(n);
    } else { // full
      inner = chipHtml(n, opts.label) + starsHtml(n);
    }

    return '<span class="rank-badge" data-level="' + n + '" data-variant="' + variant +
      '" data-size="' + size + '" role="img" aria-label="' + esc(aria) + '">' +
      inner + '</span>';
  }

  window.rankBadge = rankBadge;
})();

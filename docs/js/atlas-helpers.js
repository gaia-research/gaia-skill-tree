/* ============================================================
   atlas-helpers.js — Hunter's Atlas shared client helpers
   Exposes window.namedSlug, window.profileHref, window.handleLink.
   No build step; vanilla browser JS, IIFE pattern.
   ============================================================ */

(function () {
  'use strict';

  function esc(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /**
   * namedSlug(entry) → '/{secondSegment}' from entry.id.
   * For 'karpathy/autoresearch' → '/autoresearch'.
   * Falls back to '/{entry.genericSkillRef || entry.id}' if no slash present.
   */
  function namedSlug(entry) {
    if (!entry) return '';
    var id = entry.id || '';
    if (typeof id === 'string' && id.indexOf('/') !== -1) {
      var second = id.split('/', 2)[1];
      return '/' + second;
    }
    var fallback = entry.genericSkillRef || id || '';
    return '/' + fallback;
  }

  /**
   * profileHref(handle, rel?) → '{rel}{encodeURIComponent(handle)}/'.
   * Preserves handle casing. Default rel is './u/'.
   */
  function profileHref(handle, rel) {
    var base = rel == null ? './u/' : rel;
    return base + encodeURIComponent(handle || '') + '/';
  }

  /**
   * handleLink(handle, opts?) → HTML anchor string '<a class="atlas-handle" …>@handle</a>'.
   * opts.rel — relative prefix passed to profileHref.
   * opts.extraClass — additional class(es) appended.
   * Empty handle → returns empty string.
   */
  function handleLink(handle, opts) {
    if (!handle) return '';
    opts = opts || {};
    var cls = 'atlas-handle' + (opts.extraClass ? ' ' + opts.extraClass : '');
    var href = profileHref(handle, opts.rel);
    return '<a class="' + esc(cls) + '" href="' + esc(href) + '">@' + esc(handle) + '</a>';
  }

  window.namedSlug = namedSlug;
  window.profileHref = profileHref;
  window.handleLink = handleLink;
})();

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

  /* ── Universal redaction gate (mirror of src/gaia_cli/redaction.py) ───────
     Per META.md, stars live on named skills only: a skill at 1★ (Awakened) or
     0★ (Basic) is NOT yet named, and a demoted skill is rewritten down to 1★.
     In both cases its contributor handle is withheld behind a "classified"
     look on every PUBLIC surface. This is the single browser-side choke point
     — keep it in lockstep with the Python module. */
  var REDACT_AT_OR_BELOW = 1;
  var REDACTED_HANDLE = '[anonymous]';

  function levelNum(level) {
    if (level == null) return 0;
    if (typeof level === 'number') return level | 0;
    var m = String(level).match(/\d+/);
    return m ? parseInt(m[0], 10) : 0;
  }

  /** isRedacted(level) → true when a skill at this level must hide its handle. */
  function isRedacted(level) {
    return levelNum(level) <= REDACT_AT_OR_BELOW;
  }

  /**
   * redactedHandle(opts?) → the classified slate "@[anonymous]" span.
   * Shares the .plaque__redacted-handle styling (flicker/scan) used by the
   * server-rendered profile plaques so the look is identical everywhere.
   */
  function redactedHandle(opts) {
    opts = opts || {};
    var cls = 'plaque__redacted-handle' + (opts.extraClass ? ' ' + opts.extraClass : '');
    return '<span class="' + esc(cls) + '" aria-label="Contributor not yet revealed">@'
      + esc(REDACTED_HANDLE) + '</span>';
  }

  /**
   * handleLink(handle, opts?) → HTML anchor string '<a class="atlas-handle" …>@handle</a>'.
   * opts.rel — relative prefix passed to profileHref.
   * opts.extraClass — additional class(es) appended.
   * opts.level — when supplied and ≤ 1★, returns the redacted slate span
   *   instead of the honor-red link (universal gate — callers that thread the
   *   level can never leak a pre-named handle).
   * Empty handle → returns empty string.
   */
  function handleLink(handle, opts) {
    if (!handle) return '';
    opts = opts || {};
    if (opts.level !== undefined && isRedacted(opts.level)) {
      return redactedHandle({ extraClass: opts.extraClass });
    }
    var cls = 'atlas-handle' + (opts.extraClass ? ' ' + opts.extraClass : '');
    var href = profileHref(handle, opts.rel);
    return '<a class="' + esc(cls) + '" href="' + esc(href) + '">@' + esc(handle) + '</a>';
  }

  window.namedSlug = namedSlug;
  window.profileHref = profileHref;
  window.handleLink = handleLink;
  window.isRedacted = isRedacted;
  window.redactedHandle = redactedHandle;
  window.REDACTED_HANDLE = REDACTED_HANDLE;
})();

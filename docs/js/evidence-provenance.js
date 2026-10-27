/**
 * evidence-provenance.js — one renderer for how an evidence row names where
 * it came from.
 *
 * Every surface that shows an evidence row (Skill Explorer cards, the
 * Evidence Library, the named-skill report table) calls this module for the
 * same five facts, exactly as the source data records them:
 *
 *   type label · source host · evaluator · date · link
 *
 * Nothing is deduplicated, filtered or rewritten here. A row whose evaluator
 * is "unknown" shows "by unknown"; a row with no date shows "undated". A
 * missing field is named as missing, never silently dropped. Duplicates are
 * an audit concern, not a rendering concern.
 *
 * Every function returns an HTML string, escapes its inputs and carries no
 * colour values (CSS tokens in docs/css/styles.css own colour). Links are
 * rendered as anchors only for http(s) URLs; any other scheme renders as
 * inert text, so a hostile `source` can never become a `javascript:` link.
 *
 * Prose lives in the tooltip (GaiaTrustLifecycle.components.tip when that
 * module is loaded, a native title otherwise), not in the row.
 *
 * UMD: window.GaiaEvidenceProvenance in browsers, module.exports under Node
 * (tests/test_evidence_provenance.js).
 */
(function(root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) {
    module.exports = factory(root);
  } else {
    root.GaiaEvidenceProvenance = factory(root);
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function(root) {
  'use strict';

  var TYPE_LABELS = {
    'fusion-recipe': 'fusion',
    'github-stars-own': 'stars',
    'proxy-containment': 'proxy',
    'verifier-attestation': 'verifier',
    'benchmark-result': 'benchmark',
    'arxiv': 'arxiv',
    'peer-review': 'peer-review',
    'repo-own': 'repo',
    'self-attestation': 'self',
    'social-signal': 'social'
  };

  var TAIL_CHARS = 12;

  var TYPE_ALIASES = { 'repo': 'repo-own', 'github-stars': 'github-stars-own' };

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function text(value) {
    return typeof value === 'string' ? value.trim() : '';
  }

  /**
   * Canonical evidence type for a raw (possibly legacy-aliased) type. A row
   * that records no type has no type here: it is never defaulted to a real one.
   */
  function normalizeType(raw) {
    var type = text(raw);
    if (!type) return '';
    return TYPE_ALIASES[type] || type;
  }

  /** Short visible label for a raw type; unknown types show as written. */
  function typeLabel(raw) {
    var type = normalizeType(raw);
    if (!type) return 'no type';
    return TYPE_LABELS[type] || type;
  }

  /**
   * Key under which a row counts as a duplicate of an earlier one: the score
   * baseline counts only the first row per (type + source).
   */
  function duplicateKey(ev) {
    var row = ev && typeof ev === 'object' ? ev : {};
    return (row.type || '') + '|' + (row.source || '');
  }

  /** Rows (same order) tagged `_duplicate` when an earlier row shares their key. */
  function markDuplicates(rows) {
    var seen = {};
    return (Array.isArray(rows) ? rows : []).map(function(row) {
      if (!row || typeof row !== 'object' || row._synthetic) return row;
      var key = duplicateKey(row);
      if (Object.prototype.hasOwnProperty.call(seen, key)) return Object.assign({}, row, { _duplicate: true });
      seen[key] = true;
      return row;
    });
  }

  /** The URL when it is a well-formed http(s) URL, else ''. */
  function safeHref(url) {
    var value = text(url);
    if (!/^https?:\/\//i.test(value)) return '';
    try {
      var parsed = new URL(value);
      if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') return '';
      if (!parsed.hostname) return '';
      return value;
    } catch (error) {
      return '';
    }
  }

  /** Host of a source URL without a leading "www.", or '' when unparseable. */
  function sourceHost(url) {
    var href = safeHref(url);
    if (!href) return '';
    try {
      return new URL(href).hostname.replace(/^www\./i, '').toLowerCase();
    } catch (error) {
      return '';
    }
  }

  /** The URL path (+ query/hash) after the host, for the ellipsised tail. */
  function sourcePath(url) {
    var href = safeHref(url);
    if (!href) return '';
    try {
      var parsed = new URL(href);
      var tail = parsed.pathname + parsed.search + parsed.hash;
      return tail === '/' ? '' : tail;
    } catch (error) {
      return '';
    }
  }

  /**
   * Provenance facts for one evidence row, exactly as recorded.
   * `evaluator` and `date` are '' when the row does not carry them.
   */
  function describe(ev) {
    var row = ev && typeof ev === 'object' ? ev : {};
    var url = text(row.source);
    var href = safeHref(url);
    return {
      type: normalizeType(row.type),
      typeLabel: typeLabel(row.type),
      url: url,
      href: href,
      host: sourceHost(url),
      path: sourcePath(url),
      duplicate: !!row._duplicate,
      evaluator: text(row.evaluator),
      date: text(row.date),
      lastVerified: text(row.lastVerified),
      synthetic: !!(row._synthetic || row.synthetic)
    };
  }

  /** Prose lines for the provenance tooltip. */
  function provenanceLines(ev) {
    var d = describe(ev);
    var lines = [];
    lines.push(d.type
      ? 'Type: ' + d.typeLabel + (d.type !== d.typeLabel ? ' (' + d.type + ')' : '') + '.'
      : 'No evidence type is recorded for this row.');
    if (d.synthetic) {
      lines.push('Derived from the skill’s suite components; it is not a recorded evidence row.');
      return lines;
    }
    lines.push(d.url ? 'Source: ' + d.url : 'No source URL is recorded for this row.');
    if (d.url && !d.href) lines.push('The recorded source is not an http(s) URL, so it is shown as text and not linked.');
    lines.push(d.evaluator ? 'Evaluator, as recorded: ' + d.evaluator + '.' : 'No evaluator is recorded for this row.');
    lines.push(d.date ? 'Date, as recorded: ' + d.date + '.' : 'No date is recorded for this row.');
    if (d.lastVerified && d.lastVerified !== d.date) lines.push('Last verified: ' + d.lastVerified + '.');
    if (d.duplicate) lines.push('Duplicate of an earlier row with the same type and source. It is shown as recorded; only the first row counts toward the score.');
    return lines;
  }

  function lifecycleTip() {
    var lifecycle = root && root.GaiaTrustLifecycle;
    return lifecycle && lifecycle.components && typeof lifecycle.components.tip === 'function'
      ? lifecycle.components.tip : null;
  }

  /**
   * The (i) provenance tooltip trigger. Uses the shared toggletip when the
   * trust-lifecycle module is present (callers should then run
   * GaiaTrustLifecycle.components.bindTips on their mount); otherwise a native
   * title, which carries the same prose.
   */
  function renderTip(ev, opts) {
    var lines = provenanceLines(ev);
    var tip = (opts && opts.tip) || lifecycleTip();
    var d = describe(ev);
    var label = 'Evidence provenance: ' + (d.synthetic ? 'derived from suite components' :
      d.typeLabel + ', ' + (d.host || (d.url ? 'unlinked source' : 'no source')));
    if (tip) {
      return '<span class="lc-anchor ev-prov-tip">' + tip('i', lines, { label: label, cls: 'ev-prov-info' }) + '</span>';
    }
    return '<button class="ev-prov-info ev-prov-info--native" type="button" title="' + esc(lines.join('\n')) +
      '" aria-label="' + esc(label) + '">i</button>';
  }

  /** `.ev-type-pill` with the caller's formula tooltip, labelled by type. */
  function renderTypePill(ev, opts) {
    var d = describe(ev);
    var pillTip = !d.type ? 'No evidence type is recorded for this row.'
      : (opts && opts.pillTip != null ? opts.pillTip : d.type);
    return '<span class="ev-type-pill type-' + esc(d.type || 'none') + '">' + esc(d.typeLabel) +
      '<button class="ev-type-pill-info" type="button" title="' + esc(pillTip) +
      '" aria-label="' + esc((d.type || 'no type') + ' evidence type info') + '">i</button></span>';
  }

  /** Host (emphasised) + path (ellipsised) as one link, or inert text. */
  function renderSource(ev) {
    var d = describe(ev);
    if (d.synthetic) {
      return '<span class="se-ev-link ev-prov-none" title="Derived from suite components">derived</span>';
    }
    if (!d.url) {
      return '<span class="se-ev-link ev-prov-none">no source</span>';
    }
    if (!d.href) {
      return '<span class="se-ev-link ev-prov-none" title="' + esc(d.url) + '">' + esc(d.url) + '</span>';
    }
    // The tail of the path (an issue number, a file name) is what tells two
    // rows on one host apart, so it never ellipsises: only the middle gives way.
    var head = d.path.length > TAIL_CHARS ? d.path.slice(0, d.path.length - TAIL_CHARS) : '';
    var tail = head ? d.path.slice(d.path.length - TAIL_CHARS) : d.path;
    return '<a class="se-ev-link ev-prov-link" href="' + esc(d.href) +
      '" target="_blank" rel="noopener noreferrer" title="' + esc(d.href) + '">' +
      '<span class="ev-prov-host">' + esc(d.host) + '</span>' +
      (head ? '<span class="ev-prov-path">' + esc(head) + '</span>' : '') +
      (tail ? '<span class="ev-prov-tail">' + esc(tail) + '</span>' : '') + '</a>';
  }

  /** "by <evaluator>" exactly as recorded, or an explicit absence. */
  function renderEvaluator(ev) {
    var d = describe(ev);
    if (d.synthetic) return '';
    if (!d.evaluator) return '<span class="se-ev-eval ev-prov-none" title="Evaluator">no evaluator</span>';
    return '<span class="se-ev-eval" title="Evaluator">by ' + esc(d.evaluator) + '</span>';
  }

  /** The recorded date, or an explicit absence. */
  function renderDate(ev) {
    var d = describe(ev);
    if (d.synthetic) return '';
    if (!d.date) return '<span class="se-ev-date ev-prov-none" title="Date">undated</span>';
    return '<time class="se-ev-date" title="Date" datetime="' + esc(d.date) + '">' + esc(d.date) + '</time>';
  }

  /** Marker for a row shown as recorded that the score baseline does not count. */
  function renderDuplicate(ev) {
    var d = describe(ev);
    if (!d.duplicate) return '';
    return '<span class="ev-prov-dup" title="Duplicate of an earlier row with the same type and source; shown as recorded, not counted.">duplicate \u00b7 not counted</span>';
  }

  /**
   * The provenance block shared by every evidence card: a top line (type pill,
   * source link, tooltip, caller extras) and a meta line (evaluator, date,
   * caller extras).
   *
   *   opts.pillTip    title text for the type pill's (i) button
   *   opts.topExtra   trusted HTML appended to the top line (layer hint)
   *   opts.metaExtra  trusted HTML appended to the meta line (freshness)
   *   opts.tip        tooltip builder override (tests)
   */
  function renderProvenance(ev, opts) {
    opts = opts || {};
    return '<div class="se-ev-card-top">' +
        renderTypePill(ev, opts) +
        renderSource(ev) +
        renderTip(ev, opts) +
        (opts.topExtra || '') +
      '</div>' +
      '<div class="se-ev-card-meta">' +
        renderEvaluator(ev) +
        renderDate(ev) +
        renderDuplicate(ev) +
        (opts.metaExtra || '') +
      '</div>';
  }

  /** Re-bind toggletips inside a freshly rendered mount, when available. */
  function bindTips(mount) {
    var lifecycle = root && root.GaiaTrustLifecycle;
    if (mount && lifecycle && lifecycle.components && typeof lifecycle.components.bindTips === 'function') {
      lifecycle.components.bindTips(mount);
    }
  }

  return {
    esc: esc,
    normalizeType: normalizeType,
    typeLabel: typeLabel,
    safeHref: safeHref,
    sourceHost: sourceHost,
    describe: describe,
    provenanceLines: provenanceLines,
    renderTip: renderTip,
    renderTypePill: renderTypePill,
    renderSource: renderSource,
    renderEvaluator: renderEvaluator,
    renderDate: renderDate,
    renderDuplicate: renderDuplicate,
    duplicateKey: duplicateKey,
    markDuplicates: markDuplicates,
    renderProvenance: renderProvenance,
    bindTips: bindTips
  };
});

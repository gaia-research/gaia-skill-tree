/**
 * challenge-surfaces.js — Yggdrasil IV public challenge surfaces (EPIC #2189, outcome 5, W3–W6)
 *
 * One reader for the two public challenge artifacts, and the renderers that
 * every challenge surface shares:
 *
 *   api/v1/challenges/index.json    gaia-challenge-projection/v1  admitted challenges
 *   api/v1/challenges/reviews.json  gaia-challenge-review/v1      held admission reviews
 *
 * DOCTRINE (plans/website.md, plans/challenger-pipeline.md)
 * - Fail closed, whole file. Anything that is not a well-formed `verified`
 *   projection reads as `unavailable`, and `unavailable` renders nothing: no
 *   mark, no row, no history. A surface that consumes this module must look
 *   exactly as it did before when the projection is unavailable.
 * - Only admitted challenges ever contest anything. A challenge is "contested"
 *   only while it is admitted and unresolved. Consequence is only ever
 *   `current-baseline` or `approved-decision` (or unavailable); a proposal is
 *   never read, and any proposal-shaped key makes the whole file unavailable.
 * - Held reviews are a separate artifact. They are an admission attempt that
 *   was held: never "contested", never the challenge mark, never a standing.
 * - Decoration is additive. `decorateBars` and `decorateRows` only append
 *   nodes beside what the host already drew; they never write an attribute on
 *   a bar, a number or a row the host owns, so bar widths and figures stay
 *   byte-identical.
 * - Shape checking is not authentication. The build re-validates every case
 *   bundle; this module only refuses a mangled contract.
 *
 * Requires GaiaTrustLifecycle (docs/js/trust-lifecycle.js), loaded first, for
 * the challenge mark, toggletip and per-challenge shape check.
 */
(function(root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) {
    module.exports = factory(function() { return require('./trust-lifecycle.js'); });
  } else {
    root.GaiaChallenges = factory(function() { return root.GaiaTrustLifecycle; });
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function(lifecycle) {
  'use strict';

  var PROJECTION_CONTRACT = 'gaia-challenge-projection/v1';
  var REVIEW_CONTRACT = 'gaia-challenge-review/v1';
  var CONSEQUENCES = ['current-baseline', 'approved-decision', 'unavailable'];
  var HOLD_REASONS = [
    'trusted-issuer-unavailable', 'trusted-issuer-misconfigured', 'receipt-unverifiable',
    'challenge-rejected', 'bundle-not-bound-to-receipt', 'admission-request-missing',
    'not-recommended-for-admission', 'event-log-broken'
  ];
  var CASE_ID = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
  var REPO = 'https://github.com/gaia-research/gaia-skill-tree';
  var SVG_NS = 'http://www.w3.org/2000/svg';

  var HELD_HEADING = 'Admission held, under review, no effect on standing';

  // ── 1. Small guards ────────────────────────────────────────────────────

  function tl() {
    var mod = lifecycle();
    return mod && typeof mod.normalizeChallenge === 'function' && mod.components ? mod : null;
  }

  function isObj(v) { return v !== null && typeof v === 'object' && !Array.isArray(v); }
  function isStr(v) { return typeof v === 'string' && v.trim().length > 0; }

  function hasExactKeys(obj, keys) {
    var own = Object.keys(obj);
    if (own.length !== keys.length) return false;
    for (var i = 0; i < keys.length; i++) if (own.indexOf(keys[i]) < 0) return false;
    return true;
  }

  function anyKeyMatches(value, re) {
    if (Array.isArray(value)) {
      for (var i = 0; i < value.length; i++) if (anyKeyMatches(value[i], re)) return true;
      return false;
    }
    if (!isObj(value)) return false;
    var names = Object.keys(value);
    for (var n = 0; n < names.length; n++) {
      if (re.test(names[n]) || anyKeyMatches(value[names[n]], re)) return true;
    }
    return false;
  }

  function anyStringMatches(value, re) {
    if (typeof value === 'string') return re.test(value);
    if (Array.isArray(value)) {
      for (var i = 0; i < value.length; i++) if (anyStringMatches(value[i], re)) return true;
      return false;
    }
    if (!isObj(value)) return false;
    var names = Object.keys(value);
    for (var n = 0; n < names.length; n++) if (anyStringMatches(value[names[n]], re)) return true;
    return false;
  }

  function esc(value) {
    var mod = lifecycle();
    if (mod && typeof mod.esc === 'function') return mod.esc(value);
    return String(value == null ? '' : value).replace(/[&<>"']/g, function(c) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
  }

  function safeHttps(url) {
    var mod = lifecycle();
    return !!mod && typeof mod.isSafeHttps === 'function' && mod.isSafeHttps(url);
  }

  function dateOf(iso) {
    var mod = lifecycle();
    return mod && typeof mod.formatDateUTC === 'function' ? mod.formatDateUTC(iso) : String(iso || '');
  }

  // ── 2. The admitted-challenge projection ──────────────────────────────

  function unavailable(loadFailed) {
    return {status: 'unavailable', subjects: [], loadFailed: loadFailed === true};
  }

  function parseChallenge(item, subjectId, seen) {
    var mod = tl();
    if (!mod || !isObj(item)) return null;
    var parsed = mod.normalizeChallenge(item);
    if (!parsed || item.subjectId !== subjectId || typeof item.materialToOrigin !== 'boolean') return null;
    if (seen[parsed.challengeId]) return null;
    if (!Array.isArray(item.history) || !item.history.length) return null;
    for (var e = 0; e < item.history.length; e++) {
      var event = item.history[e];
      if (!isObj(event) || event.challenge_id !== parsed.challengeId || !isStr(event.event_type) || !isStr(event.at_utc)) return null;
    }
    if (parsed.isResolved && !parsed.resolution) return null;
    seen[parsed.challengeId] = true;
    parsed.subjectId = subjectId;
    parsed.contributorId = isStr(item.contributorId) ? item.contributorId.trim() : '';
    parsed.testVersion = isStr(item.testVersion) ? item.testVersion.trim() : '';
    parsed.history = item.history.map(function(ev) {
      return {type: ev.event_type, atUTC: ev.at_utc, actor: isStr(ev.actor) ? ev.actor : '', details: isStr(ev.details) ? ev.details : ''};
    });
    return parsed;
  }

  function parseConsequence(c) {
    if (!isObj(c) || CONSEQUENCES.indexOf(c.kind) < 0) return null;
    if (c.kind === 'unavailable') return {kind: 'unavailable'};
    if (typeof c.tm !== 'number' || !isFinite(c.tm) || c.tm < 0 ||
        !(typeof c.stars === 'number' && c.stars % 1 === 0 && c.stars >= 0 && c.stars <= 6)) return null;
    return {kind: c.kind, tm: c.tm, stars: c.stars,
      originHandle: isStr(c.originHandle) ? c.originHandle.trim() : '',
      recalibrationPending: c.recalibrationPending === true};
  }

  /**
   * Validate the whole projection. Anything but a well-formed `verified`
   * document is `unavailable`; there is no partial trust.
   */
  function parseProjection(doc) {
    if (!isObj(doc) || !hasExactKeys(doc, ['contract', 'sourceStatus', 'subjects'])) return unavailable();
    if (doc.contract !== PROJECTION_CONTRACT || doc.sourceStatus !== 'verified') return unavailable();
    if (!Array.isArray(doc.subjects) || !doc.subjects.length) return unavailable();
    if (anyKeyMatches(doc.subjects, /propos/i)) return unavailable();
    var subjects = [], ids = {}, seen = {};
    for (var i = 0; i < doc.subjects.length; i++) {
      var s = doc.subjects[i];
      if (!isObj(s) || !hasExactKeys(s, ['subjectId', 'genericSkillRef', 'materialOriginContested', 'consequence', 'challenges'])) return unavailable();
      if (!isStr(s.subjectId) || ids[s.subjectId] || !isStr(s.genericSkillRef)) return unavailable();
      if (typeof s.materialOriginContested !== 'boolean' || !Array.isArray(s.challenges) || !s.challenges.length) return unavailable();
      var consequence = parseConsequence(s.consequence);
      if (!consequence) return unavailable();
      ids[s.subjectId] = true;
      var challenges = [];
      for (var c = 0; c < s.challenges.length; c++) {
        var parsed = parseChallenge(s.challenges[c], s.subjectId, seen);
        if (!parsed) return unavailable();
        challenges.push(parsed);
      }
      var material = challenges.some(function(ch) { return ch.materialToOrigin && !ch.isResolved; });
      if (material !== s.materialOriginContested) return unavailable();
      subjects.push({subjectId: s.subjectId, genericSkillRef: s.genericSkillRef,
        materialOriginContested: s.materialOriginContested, consequence: consequence, challenges: challenges});
    }
    return {status: 'verified', subjects: subjects, loadFailed: false};
  }

  /**
   * subjectId -> {subjectId, open, originContested, challenges}, for subjects
   * that are admitted AND still contested (at least one unresolved challenge).
   * Resolved challenges are history, not contest.
   */
  function contestedIndex(projection) {
    var map = Object.create(null);
    if (!projection || projection.status !== 'verified') return map;
    for (var i = 0; i < projection.subjects.length; i++) {
      var s = projection.subjects[i];
      var open = s.challenges.filter(function(ch) { return !ch.isResolved; });
      if (!open.length) continue;
      map[s.subjectId] = {subjectId: s.subjectId, open: open.length,
        originContested: s.materialOriginContested, challenges: open};
    }
    return map;
  }

  /** Merge entries for one drawn element that stands for several identical skills. */
  function combineEntries(entries) {
    var list = entries.filter(Boolean);
    if (!list.length) return null;
    var open = 0, origin = false, ids = [];
    for (var i = 0; i < list.length; i++) {
      open += list[i].open;
      origin = origin || list[i].originContested;
      ids.push(list[i].subjectId);
    }
    return {subjectId: ids[0], subjectIds: ids, open: open, originContested: origin};
  }

  function contestLabel(entry, opts) {
    var n = entry.open;
    var ids = entry.subjectIds && entry.subjectIds.length > 1 ? entry.subjectIds : null;
    var lead = (opts && opts.isOrigin && entry.originContested) ? 'Origin contested. ' : '';
    var what = 'Contested by ' + n + ' open admitted challenge' + (n === 1 ? '' : 's') +
      (ids ? ' across ' + ids.length + ' skills' : '');
    var tail = entry.originContested ? ', including one that contests Origin' : ', Origin not affected';
    return lead + what + tail + '. Trust Magnitude, stars and rank are unchanged until an approved decision.';
  }

  // ── 3. Held admission reviews ─────────────────────────────────────────

  var CONTESTED_WORD = /contested/i;
  var FORBIDDEN_REVIEW_KEY = /contested|propos|^(tm|stars?|grade|origin|level|trustmagnitude|rank)$/i;

  function parseReview(rec) {
    if (!isObj(rec) || rec.contract !== REVIEW_CONTRACT || rec.status !== 'admission-held') return null;
    if (!isStr(rec.caseId) || !CASE_ID.test(rec.caseId) || !isStr(rec.subjectId) || !isStr(rec.claim)) return null;
    var held = rec.held;
    if (!isObj(held) || HOLD_REASONS.indexOf(held.reason) < 0 || !isStr(held.explanation)) return null;
    // System-generated fields may never carry the dispute word; challenger-authored text is data.
    if (anyStringMatches({contract: rec.contract, status: rec.status, held: held, disclosure: rec.disclosure}, CONTESTED_WORD)) return null;
    if (anyKeyMatches(rec, FORBIDDEN_REVIEW_KEY)) return null;
    var challenger = isObj(rec.challenger) ? rec.challenger : null;
    if (!challenger || !isStr(challenger.name)) return null;
    var assessment = isObj(rec.assessment) ? rec.assessment : {};
    var experiment = isObj(rec.experiment) ? rec.experiment : {};
    return {
      caseId: rec.caseId, subjectId: rec.subjectId.trim(), claim: rec.claim.trim(),
      comparator: isStr(rec.comparator) ? rec.comparator.trim() : '',
      challenger: {name: challenger.name.trim(), version: isStr(challenger.version) ? challenger.version.trim() : '',
        sourceUrl: safeHttps(challenger.sourceUrl) ? challenger.sourceUrl.trim() : ''},
      outcome: isStr(assessment.outcome) ? assessment.outcome.trim() : '',
      suggestedAction: isStr(assessment.suggestedAction) ? assessment.suggestedAction.trim() : '',
      independence: isStr(assessment.independence) ? assessment.independence.trim() : '',
      experimentResult: isStr(experiment.result) ? experiment.result.trim() : '',
      holdReason: held.reason, holdExplanation: held.explanation.trim(),
      disclosure: isStr(rec.disclosure) ? rec.disclosure.trim() : '',
      evidenceUrl: REPO + '/tree/main/evidence/frontier-challenges/' + encodeURIComponent(rec.caseId)
    };
  }

  /** Drops only the offending record; the rest of a well-formed document stands. */
  function parseReviews(doc) {
    var none = {reviews: [], loadFailed: false};
    if (!isObj(doc) || !hasExactKeys(doc, ['contract', 'reviews']) || doc.contract !== REVIEW_CONTRACT || !Array.isArray(doc.reviews)) return none;
    var seen = {}, kept = [];
    for (var i = 0; i < doc.reviews.length; i++) {
      var r = parseReview(doc.reviews[i]);
      if (r && !seen[r.caseId]) { seen[r.caseId] = true; kept.push(r); }
    }
    kept.sort(function(a, b) { return a.caseId < b.caseId ? -1 : a.caseId > b.caseId ? 1 : 0; });
    return {reviews: kept, loadFailed: false};
  }

  // ── 4. Loading ────────────────────────────────────────────────────────

  function fetchJson(url) {
    return fetch(url, {cache: 'no-cache'}).then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  /**
   * Load both artifacts from `base` (a path ending in `api/v1/`). Never rejects:
   * a failed fetch is an unavailable projection and no reviews.
   */
  function load(base, version) {
    var q = version ? '?v=' + encodeURIComponent(version) : '';
    return Promise.all([
      fetchJson(base + 'challenges/index.json' + q).then(parseProjection, function() { return unavailable(true); }),
      fetchJson(base + 'challenges/reviews.json' + q).then(parseReviews, function() { return {reviews: [], loadFailed: true}; })
    ]).then(function(r) { return {projection: r[0], reviews: r[1]}; });
  }

  // ── 5. Additive decoration of host-owned surfaces ─────────────────────

  function pageHref(rootPrefix, subjectId) {
    return rootPrefix + 'trust/challenges/#subject-' + encodeURIComponent(subjectId);
  }

  function markInner(severity) {
    var mod = tl();
    var svg = mod && mod.components.markSvg ? mod.components.markSvg('open', severity) : '';
    return svg.replace(/^<svg[^>]*>/, '').replace(/<\/svg>\s*$/, '');
  }

  function chartMark(doc, cx, cy, entry, opts) {
    var label = contestLabel(entry, opts);
    var severity = entry.originContested ? 'material' : 'scoped';
    var size = 16, half = size / 2;
    var a = doc.createElementNS(SVG_NS, 'a');
    a.setAttribute('class', 'cs-chartmark');
    a.setAttribute('href', pageHref(opts.root, entry.subjectId));
    a.setAttribute('aria-label', label);
    a.setAttribute('data-skill-id', entry.subjectId);
    var title = doc.createElementNS(SVG_NS, 'title');
    title.textContent = label;
    a.appendChild(title);
    var ring = doc.createElementNS(SVG_NS, 'rect');
    ring.setAttribute('class', 'cs-chartmark__ring');
    ring.setAttribute('x', String(cx - half - 4));
    ring.setAttribute('y', String(cy - half - 4));
    ring.setAttribute('width', String(size + 8));
    ring.setAttribute('height', String(size + 8));
    ring.setAttribute('rx', '4');
    a.appendChild(ring);
    var g = doc.createElementNS(SVG_NS, 'g');
    g.setAttribute('class', 'lc-mark');
    g.setAttribute('data-state', 'open');
    g.setAttribute('data-severity', severity);
    g.setAttribute('data-size', 'sm');
    g.setAttribute('transform', 'translate(' + (cx - half) + ' ' + (cy - half) + ') scale(' + (size / 24) + ')');
    g.innerHTML = markInner(severity);
    a.appendChild(g);
    return a;
  }

  /**
   * Pin a contest mark to the foot of each contested bar in the leaderboard's
   * Named chart (the upper right corner of the contributor avatar, where the
   * Origin wreath also sits). Reads each bar's geometry and appends to the
   * bar's own group; never writes to a bar. Returns the number of marks.
   *
   *   lookup(skillId) -> {entry, isOrigin} | null
   */
  function decorateBars(container, lookup, opts) {
    opts = opts || {};
    if (!container || typeof container.querySelectorAll !== 'function' || typeof lookup !== 'function') return 0;
    var doc = container.ownerDocument || (typeof document !== 'undefined' ? document : null);
    if (!doc || !tl()) return 0;
    var stale = container.querySelectorAll('.cs-chartmark');
    for (var s = 0; s < stale.length; s++) if (stale[s].parentNode) stale[s].parentNode.removeChild(stale[s]);
    var bars = container.querySelectorAll('.lb-bar[data-type="named"]');
    var count = 0;
    for (var i = 0; i < bars.length; i++) {
      var bar = bars[i];
      var found = lookup(bar.getAttribute('data-id'));
      if (!found || !found.entry || !bar.parentNode) continue;
      var x = parseFloat(bar.getAttribute('x')), y = parseFloat(bar.getAttribute('y'));
      var w = parseFloat(bar.getAttribute('width')), h = parseFloat(bar.getAttribute('height'));
      if (![x, y, w, h].every(isFinite)) continue;
      var r = Math.min(10, Math.max(5, w / 2.4));   // the avatar the host draws under this bar
      var cx = x + w / 2, cy = y + h + r + 4;
      bar.parentNode.appendChild(chartMark(doc, cx + r * 0.75, cy - r * 0.75, found.entry,
        {root: opts.root || '', isOrigin: found.isOrigin === true}));
      count += 1;
    }
    return count;
  }

  function rowMarkHtml(entry, rootPrefix, isOrigin) {
    var mod = tl();
    var label = contestLabel(entry, {isOrigin: isOrigin});
    var mark = mod.components.challengeMark('open', {severity: entry.originContested ? 'material' : 'scoped', size: 'sm', decorative: true});
    return '<a class="cs-rowmark" href="' + esc(pageHref(rootPrefix, entry.subjectId)) + '" aria-label="' + esc(label) +
      '" title="' + esc(label) + '">' + mark + '<span class="cs-rowmark__word">Contested</span></a>';
  }

  /**
   * Append a "Contested" link after the skill id in each contested table row.
   * The row id is read from the id cell; nothing the host wrote is altered.
   */
  function decorateRows(tbody, lookup, opts) {
    opts = opts || {};
    if (!tbody || typeof tbody.querySelectorAll !== 'function' || typeof lookup !== 'function' || !tl()) return 0;
    var cells = tbody.querySelectorAll('td.col-id');
    var count = 0;
    for (var i = 0; i < cells.length; i++) {
      var cell = cells[i];
      if (cell.querySelector && cell.querySelector('.cs-rowmark')) continue;
      var anchor = cell.querySelector ? cell.querySelector('a') : null;
      var id = anchor ? String(anchor.textContent || '').trim() : '';
      var found = id ? lookup(id) : null;
      if (!found || !found.entry) continue;
      cell.insertAdjacentHTML('beforeend', rowMarkHtml(found.entry, opts.root || '', found.isOrigin === true));
      count += 1;
    }
    return count;
  }

  // ── 6. Challenge history (admitted events only) ───────────────────────

  var EVENT_LABELS = {'verified-publication': 'Verified and published', 'technical-resolution': 'Technical resolution'};

  /** Flat, newest-first event list drawn only from admitted challenges. */
  function historyEvents(projection) {
    var out = [];
    if (!projection || projection.status !== 'verified') return out;
    projection.subjects.forEach(function(s) {
      s.challenges.forEach(function(ch) {
        ch.history.forEach(function(ev, index) {
          var receipt = '';
          if (index === 0 && ev.type === 'verified-publication') receipt = ch.verifier.receiptUrl;
          else if (ev.type === 'technical-resolution' && ch.resolution) receipt = ch.resolution.receiptUrl;
          out.push({subjectId: s.subjectId, challengeId: ch.challengeId, claim: ch.claim, type: ev.type,
            atUTC: ev.atUTC, actor: ev.actor, receiptUrl: receipt, materialToOrigin: ch.materialToOrigin});
        });
      });
    });
    out.sort(function(a, b) { return a.atUTC < b.atUTC ? 1 : a.atUTC > b.atUTC ? -1 : (a.challengeId < b.challengeId ? -1 : 1); });
    return out;
  }

  function externalLink(href, label) {
    return '<a class="cs-link" href="' + esc(href) + '" target="_blank" rel="noopener noreferrer">' + esc(label) +
      '<span aria-hidden="true"> &#8599;</span></a>';
  }

  /**
   * Render the "Challenge history" block of the Trust Ledger page. With no
   * admitted events the mount is emptied and hidden: the page is as before.
   */
  function renderHistory(mount, projection, opts) {
    if (!mount) return 0;
    opts = opts || {};
    var events = historyEvents(projection);
    if (!events.length || !tl()) {
      mount.innerHTML = '';
      mount.hidden = true;
      return 0;
    }
    var h = ['<h2 class="cs-history__title" id="csHistoryTitle">Challenge history</h2>',
      '<p class="cs-history__lede">Events from admitted challenges only. A challenge appears here after the trusted issuer has verified it; ' +
      'it does not change a Trust Magnitude, star or grade in the table above. Standing moves only by an approved decision.</p>',
      '<ol class="cs-history__list" aria-labelledby="csHistoryTitle">'];
    events.forEach(function(ev) {
      h.push('<li class="cs-event" data-event="' + esc(ev.type) + '">' +
        '<time class="cs-event__date" datetime="' + esc(ev.atUTC) + '">' + esc(dateOf(ev.atUTC)) + '</time>' +
        '<span class="cs-event__what"><strong>' + esc(EVENT_LABELS[ev.type] || ev.type) + '</strong>' +
        '<a class="cs-event__subject" href="' + esc(pageHref(opts.root || '', ev.subjectId)) + '">' + esc(ev.subjectId) + '</a>' +
        '<span class="cs-event__claim">' + esc(ev.claim) + '</span></span>' +
        (ev.receiptUrl ? '<span class="cs-event__receipt">' + externalLink(ev.receiptUrl, 'Receipt') + '</span>' : '') + '</li>');
    });
    h.push('</ol>');
    mount.innerHTML = h.join('');
    mount.hidden = false;
    return events.length;
  }

  // ── 7. The challenges page ────────────────────────────────────────────

  var STATUS_WORDS = {
    'verified-pending': 'Open, awaiting adjudication',
    'upheld': 'Upheld',
    'narrowed': 'Narrowed',
    'technically-rebutted': 'Technically rebutted',
    'resolved-by-upstream-improvement': 'Resolved by upstream improvement',
    'rejected': 'Rejected'
  };

  var OUTCOME_WORDS = {
    substantiated: 'Substantiated', narrowed: 'Narrowed', contradicted: 'Contradicted',
    inconclusive: 'Inconclusive', rejected: 'Rejected'
  };

  var RESULT_WORDS = {
    supported: 'Supported', contradicted: 'Contradicted', inconclusive: 'Inconclusive', execution_failed: 'Execution failed'
  };

  var ACTION_WORDS = {
    'request-admission-review': 'Request an admission review', 'no-action': 'No action',
    'reject': 'Reject', 'complementary-scope': 'Complementary scope'
  };

  function consequenceLine(c) {
    if (c.kind === 'approved-decision') {
      return 'Approved decision: ' + c.stars + ' of 6 stars, Trust Magnitude ' + (Math.round(c.tm * 100) / 100) + '.';
    }
    if (c.kind === 'current-baseline') {
      return 'Published baseline: ' + c.stars + ' of 6 stars, Trust Magnitude ' + (Math.round(c.tm * 100) / 100) + '. No decision is asserted.';
    }
    return 'The canonical standing source is unavailable, so no rank or Trust Magnitude is shown.';
  }

  function boutHtml(ch, comps) {
    var open = !ch.isResolved;
    var state = open ? 'open' : (ch.isUpstreamSuperseded ? 'upstream' : 'rebutted');
    var severity = ch.materialToOrigin ? 'material' : 'scoped';
    var rows = [['Status', STATUS_WORDS[ch.status] || ch.status],
      ['Scope', ch.materialToOrigin ? 'Material: could affect present Origin qualification' : 'Scoped to one capability; Origin is not contested'],
      ['Verified', dateOf(ch.verifiedAtUTC)],
      ['Pinned', [ch.pinnedVersion, ch.pinnedSha].filter(Boolean).join(' @ ')],
      ['Comparator', ch.comparator],
      ['Baseline', ch.baseline]];
    var dl = rows.filter(function(r) { return r[1]; }).map(function(r) {
      return '<div class="cs-kv"><dt>' + esc(r[0]) + '</dt><dd>' + esc(r[1]) + '</dd></div>';
    }).join('');
    var links = [externalLink(ch.verifier.receiptUrl, 'Verification receipt')];
    if (ch.contributorNoticeRef) links.push(externalLink(ch.contributorNoticeRef, 'Contributor notice'));
    if (ch.resolution) links.push(externalLink(ch.resolution.receiptUrl, 'Resolution receipt'));
    var events = ch.history.map(function(ev) {
      return '<li><time datetime="' + esc(ev.atUTC) + '">' + esc(dateOf(ev.atUTC)) + '</time> ' +
        esc(EVENT_LABELS[ev.type] || ev.type) + (ev.actor ? ' <span class="cs-dim">by ' + esc(ev.actor) + '</span>' : '') + '</li>';
    }).join('');
    return '<li class="cs-bout" data-state="' + state + '" data-severity="' + severity + '">' +
      '<div class="cs-bout__mark">' + comps.challengeMark(state, {severity: severity, size: 'md', decorative: true}) + '</div>' +
      '<div class="cs-bout__body"><p class="cs-bout__claim">' + esc(ch.claim) + '</p>' +
      '<dl class="cs-kvs">' + dl + '</dl>' +
      '<p class="cs-bout__links">' + links.join('') + '</p>' +
      '<details class="cs-bout__history"><summary>History (' + ch.history.length + ')</summary><ol>' + events + '</ol></details>' +
      '</div></li>';
  }

  function subjectHtml(s, opts, comps) {
    var open = s.challenges.filter(function(ch) { return !ch.isResolved; });
    var resolved = s.challenges.length - open.length;
    var chips = [];
    if (open.length) chips.push(comps.stateChip(s.materialOriginContested ? 'open-material' : 'open-scoped',
      {label: open.length > 1 ? (s.materialOriginContested ? 'Contests Origin' : 'Scoped challenge') + ' x' + open.length : null}));
    else chips.push(comps.stateChip('rebutted-scoped', {label: 'All resolved'}));
    var id = 'subject-' + s.subjectId;
    var ordered = open.concat(s.challenges.filter(function(ch) { return ch.isResolved; }));
    return '<article class="cs-subject" id="' + esc(id) + '" data-origin-contested="' + (s.materialOriginContested ? 'true' : 'false') + '" data-open="' + open.length + '">' +
      '<header class="cs-subject__head"><h3 class="cs-subject__id"><a href="' + esc((opts.root || '') + 'named/#explorer/' + encodeURI(s.subjectId)) + '">' +
      esc(s.subjectId) + '</a></h3><div class="cs-subject__chips">' + chips.join('') + '</div></header>' +
      '<p class="cs-subject__bucket">Capability bucket <span>' + esc(s.genericSkillRef) + '</span> &middot; ' +
      open.length + ' open, ' + resolved + ' resolved</p>' +
      '<p class="cs-subject__standing">' + esc(consequenceLine(s.consequence)) + ' A challenge never changes these figures by itself.</p>' +
      '<ol class="cs-bouts">' + ordered.map(function(ch) { return boutHtml(ch, comps); }).join('') + '</ol></article>';
  }

  function reviewHtml(r) {
    var rows = [
      ['Assessment outcome', OUTCOME_WORDS[r.outcome] || r.outcome],
      ['Suggested action', ACTION_WORDS[r.suggestedAction] || r.suggestedAction],
      ['Experiment result', RESULT_WORDS[r.experimentResult] || r.experimentResult],
      ['Comparator', r.comparator],
      ['Independence', r.independence ? r.independence.replace(/-/g, ' ') : ''],
      ['Held because', r.holdExplanation]];
    var dl = rows.filter(function(x) { return x[1]; }).map(function(x) {
      return '<div class="cs-kv"><dt>' + esc(x[0]) + '</dt><dd>' + esc(x[1]) + '</dd></div>';
    }).join('');
    var challenger = r.challenger.name + (r.challenger.version ? ' ' + r.challenger.version : '');
    var links = [externalLink(r.evidenceUrl, 'Case evidence')];
    if (r.challenger.sourceUrl) links.push(externalLink(r.challenger.sourceUrl, 'Challenger source'));
    return '<article class="cs-review" id="case-' + esc(r.caseId) + '" data-reason="' + esc(r.holdReason) + '">' +
      '<h3 class="cs-review__title"><span class="cs-review__side">' + esc(challenger) + '</span>' +
      '<span class="cs-review__vs">against</span><span class="cs-review__side">' + esc(r.subjectId) + '</span></h3>' +
      '<p class="cs-review__claim">' + esc(r.claim) + '</p>' +
      '<dl class="cs-kvs">' + dl + '</dl>' +
      (r.disclosure ? '<p class="cs-review__note">' + esc(r.disclosure) + '</p>' : '') +
      '<p class="cs-review__links">' + links.join('') + '</p></article>';
  }

  /**
   * Render /trust/challenges/. `mounts` = {admitted, held} elements; `data` is
   * the result of load(). Empty and unavailable states are quiet and true.
   */
  function renderPage(mounts, data, opts) {
    opts = opts || {};
    var mod = tl();
    var projection = data && data.projection ? data.projection : unavailable(true);
    var reviews = data && data.reviews ? data.reviews : {reviews: [], loadFailed: true};
    if (mounts.admitted) {
      if (!mod || projection.status !== 'verified') {
        var failed = !mod || projection.loadFailed;
        mounts.admitted.innerHTML = '<p class="cs-empty" data-state="' + (failed ? 'failed' : 'unavailable') + '">' +
          (failed ? 'The challenge projection could not be loaded, so nothing is shown here.'
            : 'No challenge has been admitted. A challenge is listed here only after the trusted receipt issuer has verified it; until then nothing on this page, and no standing anywhere on the site, is affected.') + '</p>';
      } else {
        mounts.admitted.innerHTML = projection.subjects.map(function(s) { return subjectHtml(s, opts, mod.components); }).join('');
      }
    }
    if (mounts.held) {
      if (reviews.loadFailed) {
        mounts.held.innerHTML = '<p class="cs-empty" data-state="failed">The held reviews could not be loaded.</p>';
      } else if (!reviews.reviews.length) {
        mounts.held.innerHTML = '<p class="cs-empty" data-state="none">No admission is being held for review.</p>';
      } else {
        mounts.held.innerHTML = reviews.reviews.map(reviewHtml).join('');
      }
    }
    if (mod && opts.bindTipsOn) mod.components.bindTips(opts.bindTipsOn);
  }

  /** Toggletip explaining the word, for the page heading. */
  function contestedTip() {
    var mod = tl();
    if (!mod) return '';
    return mod.components.tip('<span class="cs-info" aria-hidden="true">i</span>',
      ['What contested means here.',
        'A subject is contested only while an admitted, independently verified challenge against it is unresolved.',
        'Contested does not lower Trust Magnitude, stars, grade or Origin. There is no automatic demotion; standing changes only by an approved decision.'],
      {cls: 'cs-infotip', label: 'What contested means'});
  }

  return {
    PROJECTION_CONTRACT: PROJECTION_CONTRACT,
    REVIEW_CONTRACT: REVIEW_CONTRACT,
    HELD_HEADING: HELD_HEADING,
    parseProjection: parseProjection,
    parseReviews: parseReviews,
    load: load,
    contestedIndex: contestedIndex,
    combineEntries: combineEntries,
    contestLabel: contestLabel,
    decorateBars: decorateBars,
    decorateRows: decorateRows,
    historyEvents: historyEvents,
    renderHistory: renderHistory,
    renderPage: renderPage,
    contestedTip: contestedTip,
    pageHref: pageHref
  };
});

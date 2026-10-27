/**
 * trust-lifecycle.js — Yggdrasil IV Trust Degradation, Challenge, and Recovery UI
 *
 * Pure view-model builder and accessible DOM renderer for the skill detail
 * explorer (docs/js/skill-explorer.js).
 *
 * CHALLENGE IDENTITY — REUSABLE COMPONENTS (DESIGN.md § Challenge)
 * Exposed as GaiaTrustLifecycle.components; every function returns an HTML
 * string, escapes its inputs and carries no colour values (CSS tokens in
 * docs/css/styles.css own colour). Not yet wired into other surfaces.
 *
 *   challengeMark(state, {severity, size, label, decorative})
 *     state 'open' | 'rebutted' | 'upstream'; severity 'scoped' | 'material';
 *     size 'sm' 14px | 'md' 20px | 'lg' 32px | 'xl' 56-72px.
 *     .lc-mark[data-state][data-severity][data-size] > svg.lc-mark__svg
 *     Open: a touchstone-slate plate with a V-notch cut into its top edge,
 *     filled with signal hachure. Notch depth is severity (scoped nicks the
 *     plate; material cleaves it past centre). Answered: the notch becomes a
 *     struck steel hallmark with an inlaid chevron (two chevrons = material;
 *     a plinth bar beneath = resolved by upstream improvement).
 *   markStateOf(challenge) -> {state, severity} for a normalized challenge.
 *   stateChip(kind, {label})
 *     .lc-chip[data-chip][data-tone] — glyph + short visible label. Kinds:
 *     open-scoped, open-material, rebutted-{scoped,material},
 *     upstream-{scoped,material}, approved-decision, current-baseline,
 *     unavailable, recalibration, origin-held, origin-contested, origin-unknown.
 *   trustMeter({tm, kind, recalibrationPending, decorative})
 *     .lc-meter[data-kind][data-recal] — Trust Magnitude on a log bar
 *     (0-500) with grade-floor ticks. Solid fill = approved decision, hollow
 *     = published baseline, empty = unavailable, dashed collar = recalibration.
 *   tip(innerHtml, lines, {label, cls})
 *     button.lc-tip + span.lc-tipbox[role=tooltip]; hover, focus and tap
 *     reveal it, aria-describedby carries it to screen readers.
 *   bindTips(mountEl) — tap toggle, Escape and outside-click dismissal.
 *
 * GOVERNANCE DOCTRINE & RATIFICATION (2026-10-25 RFC #2148 / D8):
 * - Gaia is a long-lived trust registry, not a fast-moving leaderboard.
 * - Confirmed degradation requires independently verified, materially relevant
 *   counterevidence under comparable conditions; no demotion on elapsed time alone.
 * - Verified challenges go public immediately after independent verification.
 * - Scoped capability challenges are strictly kept distinct from Origin contested.
 * - Current Origin is exactly one and merit-based; never infer Origin transfer
 *   or vacancy merely because an incumbent is contested.
 * - Technical resolutions (Class B) must be distinguished from numerical trust
 *   recalibrations (Class C).
 * - Upstream-superseded challenges remain permanently visible in history.
 * - Historical awards and prior Origin holdings are preserved without erasure.
 *
 * CONSUMED PROJECTION CONTRACT:
 * The named-index publication producer supplies the versioned lifecycle DTO.
 * Contract validation here checks consistency, not authentication. Only the
 * configured publication source can establish authority; arbitrary JSON cannot.
 *
 * Historical presentation fields below are documentation of the old renderer,
 * not accepted inputs. Only gaia-trust-lifecycle/v1 is accepted.
 * {
 *   snapshot: {
 *     snapshotId: string,          // non-empty, e.g. "snap-2026-10-26-001"
 *     evaluatedAtUTC: string,      // ISO-8601 UTC
 *     policyVersion: string,       // e.g. "yggdrasil-4.0.0"
 *     approvedBy?: string,         // Maintainer / Founder handle
 *     approvalRef?: string         // HTTPS URL to approval PR/decision
 *   },
 *   approvedStanding: {
 *     status?: string,             // "in-good-standing" | "degraded" | "recalibration-pending" | "unknown"
 *     approvedStars?: number,      // 0..6
 *     approvedTm?: number,         // non-negative number
 *     degradation?: {
 *       priorStars?: number,
 *       degradedStars?: number,
 *       reason: string,
 *       decisionRef?: string,      // HTTPS URL
 *       adjudicatedAtUTC?: string
 *     },
 *     recalibrationPending?: {
 *       reason: string,
 *       resolvedChallengeId?: string,
 *       closedAtUTC?: string,
 *       receiptUrl?: string        // HTTPS URL
 *     }
 *   },
 *   origin: {
 *     status?: string,             // "held" | "contested" | "unassigned" | "unknown"
 *     currentOriginHandle?: string,// Incumbent handle
 *     contested?: boolean,         // Derived/ratified contested marker
 *     genericSkillRef?: string,
 *     incumbentNotice?: string
 *   },
 *   challenges?: Array<{
 *     challengeId: string,         // Unique stable ID (SHA-256)
 *     claimId?: string,
 *     claim: string,               // Human-readable challenged claim
 *     behaviorId?: string,
 *     materialToOrigin: boolean,   // true => contests Origin; false => scoped capability
 *     scopeDescription?: string,
 *     status: string,              // "verified-pending" | "upheld" | "narrowed" |
 *                                  // "technically-rebutted" | "resolved-by-upstream-improvement" | "rejected"
 *     pinnedVersion?: string,
 *     pinnedSha?: string,
 *     environment?: string,
 *     comparator?: string,
 *     baseline?: string,
 *     verifiedAtUTC: string,       // ISO-8601 UTC
 *     verifier: {
 *       verifierId: string,
 *       verificationMethod: string,// e.g. "reproducible-benchmark-runner" (never model-only)
 *       receiptUrl: string         // REQUIRED HTTPS URL to public receipt
 *     },
 *     contributorNoticeRef?: string,// HTTPS URL
 *     responseDueUTC?: string,
 *     resolution?: {
 *       disposition: string,       // "technically-rebutted" | "resolved-by-upstream-improvement" | "rejected"
 *       resolvedAtUTC: string,
 *       verifierId: string,
 *       receiptUrl: string,        // REQUIRED HTTPS URL
 *       upstreamVersion?: string,
 *       upstreamSha?: string,
 *       recalibrationPending?: boolean
 *     }
 *   }>,
 *   historicalAwards?: Array<{
 *     awardType: string,           // "origin-awarded" | "rank-awarded" | "milestone"
 *     dateUTC: string,             // ISO-8601 UTC
 *     handle: string,
 *     stars?: number,
 *     title: string,
 *     notes?: string,
 *     receiptRef?: string          // HTTPS URL
 *   }>
 * }
 */

(function(root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.GaiaTrustLifecycle = factory();
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
  'use strict';

  // ── 1. SECURITY & SANITIZATION HELPERS ─────────────────────────────────

  var HTTPS_REGEX = /^https:\/\/[a-zA-Z0-9][-a-zA-Z0-9.]*(?::[0-9]+)?(?:\/[^\s"<>]*)?$/;

  /**
   * Validates that a URL is strictly HTTPS and safe for link attributes.
   * Rejects javascript:, http:, data:, or malformed strings.
   */
  function isSafeHttps(url) {
    if (typeof url !== 'string') return false;
    var trimmed = url.trim();
    if (!trimmed) return false;
    return HTTPS_REGEX.test(trimmed);
  }

  /**
   * HTML escape helper. Escapes &, <, >, ", '.
   */
  function esc(value) {
    if (value == null) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /**
   * Format ISO-8601 UTC timestamp to readable string YYYY-MM-DD (UTC).
   */
  function formatDateUTC(isoStr) {
    if (!isoStr || typeof isoStr !== 'string') return 'Unknown Date';
    var trimmed = isoStr.trim();
    if (trimmed.length >= 10 && /^\d{4}-\d{2}-\d{2}/.test(trimmed)) {
      return trimmed.slice(0, 10);
    }
    return trimmed;
  }

  // ── 2. VIEW-MODEL CONTRACT VALIDATION & SHAPING ───────────────────────

  var VALID_CHALLENGE_STATUSES = {
    'verified-pending': true,
    'upheld': true,
    'narrowed': true,
    'technically-rebutted': true,
    'resolved-by-upstream-improvement': true,
    'rejected': true
  };

  /**
   * Normalize a producer challenge for display. Shape checks do not verify it.
   */
  function normalizeChallenge(raw) {
    if (!raw || typeof raw !== 'object') return null;

    var challengeId = typeof raw.challengeId === 'string' ? raw.challengeId.trim() : '';
    var claim = typeof raw.claim === 'string' ? raw.claim.trim() : '';
    var status = typeof raw.status === 'string' ? raw.status.trim().toLowerCase() : '';
    var verifiedAtUTC = typeof raw.verifiedAtUTC === 'string' ? raw.verifiedAtUTC.trim() : '';

    // Core integrity gate: must have id, claim, date, and valid public status
    if (!challengeId || !claim || !verifiedAtUTC) return null;
    if (!VALID_CHALLENGE_STATUSES[status]) return null;

    // Display shape only: independence and receipt authority belong to the producer.
    var verifier = raw.verifier;
    if (!verifier || typeof verifier !== 'object') return null;
    var verifierId = typeof verifier.verifierId === 'string' ? verifier.verifierId.trim() : '';
    var verificationMethod = typeof verifier.verificationMethod === 'string' ? verifier.verificationMethod.trim() : '';
    var receiptUrl = typeof verifier.receiptUrl === 'string' ? verifier.receiptUrl.trim() : '';

    if (!verifierId || !verificationMethod || !isSafeHttps(receiptUrl)) return null;

    // Disallow model-only or LLM-only verification (doctrine invariant)
    var methodLower = verificationMethod.toLowerCase();
    if (methodLower === 'model' || methodLower === 'llm' || methodLower === 'model-only' || methodLower === 'semantic-model') {
      return null;
    }

    // Materiality to origin: require strict actual boolean; malformed / unknown must NOT contest Origin
    var materialToOrigin = (raw.materialToOrigin === true);

    // Resolution packet (if present)
    var resolution = null;
    if (raw.resolution && typeof raw.resolution === 'object') {
      var resDisp = typeof raw.resolution.disposition === 'string' ? raw.resolution.disposition.trim().toLowerCase() : '';
      var resReceipt = typeof raw.resolution.receiptUrl === 'string' ? raw.resolution.receiptUrl.trim() : '';
      if (resDisp && isSafeHttps(resReceipt)) {
        resolution = {
          disposition: resDisp,
          resolvedAtUTC: typeof raw.resolution.resolvedAtUTC === 'string' ? raw.resolution.resolvedAtUTC.trim() : '',
          verifierId: typeof raw.resolution.verifierId === 'string' ? raw.resolution.verifierId.trim() : '',
          receiptUrl: resReceipt,
          upstreamVersion: typeof raw.resolution.upstreamVersion === 'string' ? raw.resolution.upstreamVersion.trim() : '',
          upstreamSha: typeof raw.resolution.upstreamSha === 'string' ? raw.resolution.upstreamSha.trim() : '',
          recalibrationPending: false
        };
      }
    }

    var isResolved = (status === 'technically-rebutted' ||
                      status === 'resolved-by-upstream-improvement' ||
                      status === 'rejected');

    var isUpstreamSuperseded = (status === 'resolved-by-upstream-improvement');

    return {
      challengeId: challengeId,
      linkedChallengeId: typeof raw.linkedChallengeId === 'string' ? raw.linkedChallengeId : '',
      history: raw.history,
      claimId: typeof raw.claimId === 'string' ? raw.claimId.trim() : '',
      claim: claim,
      behaviorId: typeof raw.behaviorId === 'string' ? raw.behaviorId.trim() : '',
      materialToOrigin: materialToOrigin,
      scopeDescription: typeof raw.scopeDescription === 'string' ? raw.scopeDescription.trim() : '',
      status: status,
      isResolved: isResolved,
      isUpstreamSuperseded: isUpstreamSuperseded,
      isAdjudicationPending: (status === 'verified-pending'),
      pinnedVersion: typeof raw.pinnedVersion === 'string' ? raw.pinnedVersion.trim() : '',
      pinnedSha: typeof raw.pinnedSha === 'string' ? raw.pinnedSha.trim() : '',
      environment: typeof raw.environment === 'string' ? raw.environment.trim() : '',
      comparator: typeof raw.comparator === 'string' ? raw.comparator.trim() : '',
      baseline: typeof raw.baseline === 'string' ? raw.baseline.trim() : '',
      verifiedAtUTC: verifiedAtUTC,
      verifier: {
        verifierId: verifierId,
        verificationMethod: verificationMethod,
        receiptUrl: receiptUrl
      },
      contributorNoticeRef: isSafeHttps(raw.contributorNoticeRef) ? raw.contributorNoticeRef.trim() : '',
      responseDueUTC: typeof raw.responseDueUTC === 'string' ? raw.responseDueUTC.trim() : '',
      resolution: resolution
    };
  }

  /**
   * Normalize an array of historical awards.
   */
  function normalizeAwards(rawList) {
    if (!Array.isArray(rawList)) return [];
    var out = [];
    for (var i = 0; i < rawList.length; i++) {
      var item = rawList[i];
      if (!item || typeof item !== 'object') continue;
      var title = typeof item.title === 'string' ? item.title.trim() : '';
      var handle = typeof item.handle === 'string' ? item.handle.trim() : '';
      if (!title && !handle) continue;
      out.push({
        awardType: typeof item.awardType === 'string' ? item.awardType.trim() : 'award',
        dateUTC: typeof item.dateUTC === 'string' ? item.dateUTC.trim() : '',
        handle: handle,
        stars: (typeof item.stars === 'number' && item.stars >= 0) ? item.stars : null,
        title: title || 'Attributed Award',
        notes: typeof item.notes === 'string' ? item.notes.trim() : '',
        receiptRef: isSafeHttps(item.receiptRef) ? item.receiptRef.trim() : ''
      });
    }
    return out;
  }

  // ── 2a. STRICT v1 SHAPE VALIDATION (FAIL CLOSED) ──────────────────────

  var UTC_REGEX = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|\+00:00)$/;

  /** Strict ISO-8601 UTC instant (explicit Z or +00:00, real calendar date). Returns epoch ms or NaN. */
  function parseUtc(value) {
    if (typeof value !== 'string') return NaN;
    var m = UTC_REGEX.exec(value);
    if (!m) return NaN;
    var parts = m.slice(1, 7).map(Number);
    var ms = Date.UTC(parts[0], parts[1] - 1, parts[2], parts[3], parts[4], parts[5]);
    var d = new Date(ms);
    if (isNaN(ms) || d.getUTCFullYear() !== parts[0] || d.getUTCMonth() !== parts[1] - 1 ||
        d.getUTCDate() !== parts[2] || d.getUTCHours() !== parts[3] ||
        d.getUTCMinutes() !== parts[4] || d.getUTCSeconds() !== parts[5]) return NaN;
    return Date.parse(value);
  }

  function isNonEmptyString(value) {
    return typeof value === 'string' && value.trim() !== '';
  }

  /**
   * Every numeric TM the Explorer can show for this entry, or null if one is
   * unusable. Mirrors skill-explorer.js renderHero():
   *   ns.trustMagnitude || ns.overallTrustMagnitude || ns.trustNumber
   * (first truthy wins, so 0 falls through). All three fields are checked
   * because any of them can reach the screen.
   */
  function displayedTrustMagnitudes(entry) {
    // Real numbers only. Strings are rejected outright so Number() and Python
    // float() parsing can never disagree; real data is float-only.
    var fields = ['trustMagnitude', 'overallTrustMagnitude', 'trustNumber'];
    var out = [];
    for (var f = 0; f < fields.length; f++) {
      var raw = entry[fields[f]];
      if (raw === undefined || raw === null) continue;
      if (typeof raw !== 'number' || !isFinite(raw)) return null;
      out.push(raw);
    }
    return out;
  }

  /**
   * Hero rank exactly as plaque.js levelNum() reads it. null = entry has no
   * level (nothing to contradict). Mirrored by _heroStars in lifecycleProjection.py.
   */
  function heroStars(entry) {
    var level = entry.level;
    if (level === undefined || level === null) return null;
    if (typeof level === 'number') return level | 0;
    var n = parseInt(String(level).replace(/[^\d]/g, ''), 10);
    return isNaN(n) ? 0 : Math.max(0, Math.min(6, n));
  }

  var HISTORY_RECEIPT_FIELDS = ['receipt_id', 'receipt_digest', 'transcript_digest', 'method'];

  /**
   * Required v1 challenge shape plus history consistency. Shape checking is not
   * authentication; it only guarantees the producer contract was not mangled.
   */
  function isValidV1Challenge(item, parsed, entry) {
    var identity = ['challengeId', 'claimId', 'claim', 'behaviorId', 'contributorId',
      'pinnedVersion', 'pinnedSha', 'environment', 'testVersion', 'baseline', 'comparator'];
    for (var k = 0; k < identity.length; k++) if (!isNonEmptyString(item[identity[k]])) return false;
    if (item.subjectId !== entry.id || typeof item.materialToOrigin !== 'boolean') return false;
    if (['verified-pending', 'technically-rebutted', 'resolved-by-upstream-improvement'].indexOf(item.status) < 0) return false;
    if (!(item.linkedChallengeId === null || isNonEmptyString(item.linkedChallengeId))) return false;
    if (!isSafeHttps(item.contributorNoticeRef) || isNaN(parseUtc(item.verifiedAtUTC))) return false;
    var history = item.history;
    if (!Array.isArray(history) || history.length !== (parsed.isResolved ? 2 : 1)) return false;
    for (var e = 0; e < history.length; e++) {
      var event = history[e];
      if (!event || typeof event !== 'object' || event.challenge_id !== item.challengeId ||
          !isNonEmptyString(event.actor) || isNaN(parseUtc(event.at_utc))) return false;
      for (var r = 0; r < HISTORY_RECEIPT_FIELDS.length; r++) {
        if (!isNonEmptyString(event[HISTORY_RECEIPT_FIELDS[r]])) return false;
      }
    }
    var opening = history[0];
    if (opening.event_type !== 'verified-publication' || opening.at_utc !== item.verifiedAtUTC ||
        opening.actor !== parsed.verifier.verifierId || opening.method !== parsed.verifier.verificationMethod) return false;
    if (!parsed.isResolved) return item.resolution === undefined;
    var closing = history[1], res = item.resolution;
    return closing.event_type === 'technical-resolution' &&
      parseUtc(closing.at_utc) >= parseUtc(opening.at_utc) &&
      !!res && typeof res === 'object' && parsed.resolution !== null &&
      res.disposition === item.status && res.resolvedAtUTC === closing.at_utc &&
      res.verifierId === closing.actor;
  }

  /**
   * Pure View-Model Builder.
   *
   * Accepts named skill object `entry`. Reads optional `entry.trustLifecycle`.
   * Returns null if trustLifecycle is absent or invalid (preserving current UI).
   */
  function buildTrustLifecycleViewModel(entry) {
    if (!entry || typeof entry !== 'object') return null;
    var payload = entry.trustLifecycle;
    if (!payload || typeof payload !== 'object') return null;

    // This validates the producer contract, not its provenance. The named-index
    // build strips contributor metadata and is the trust boundary for publication.
    if (payload.contract !== 'gaia-trust-lifecycle/v1' || payload.subjectId !== entry.id ||
        payload.genericSkillRef !== entry.genericSkillRef || !Array.isArray(payload.challenges) ||
        typeof payload.materialOriginContested !== 'boolean' || !payload.consequence ||
        ['unavailable', 'current-baseline', 'approved-decision'].indexOf(payload.consequence.kind) < 0) return null;
    var seen = Object.create(null);
    for (var i = 0; i < payload.challenges.length; i++) {
      var item = payload.challenges[i], parsed = normalizeChallenge(item);
      if (!parsed || !isValidV1Challenge(item, parsed, entry) || seen[parsed.challengeId]) return null;
      seen[parsed.challengeId] = true;
    }
    var material = payload.challenges.some(function(ch) {
      return ch.materialToOrigin && ch.status === 'verified-pending';
    });
    if (material !== payload.materialOriginContested) return null;
    var consequence = payload.consequence;
    if (consequence.kind !== 'unavailable' &&
        (!Number.isInteger(consequence.stars) || consequence.stars < 0 || consequence.stars > 6 ||
         typeof consequence.tm !== 'number' || !Number.isFinite(consequence.tm) || consequence.tm < 0 ||
         typeof consequence.recalibrationPending !== 'boolean' ||
         !(consequence.originHandle === null || (typeof consequence.originHandle === 'string' && consequence.originHandle.trim())))) return null;
    if (consequence.kind !== 'unavailable') {
      // Both consequence kinds (baseline and decision) must agree with what the
      // Explorer hero actually shows; otherwise fail closed.
      var heroRank = heroStars(entry);
      var heroTms = displayedTrustMagnitudes(entry);
      if ((heroRank !== null && heroRank !== consequence.stars) || heroTms === null ||
          heroTms.some(function(value) { return Math.abs(value - consequence.tm) > 0.01; })) return null;
    }
    // Translate DTO into the presentation model. No display field authenticates it.
    payload = {
      challenges: payload.challenges,
      origin: {currentOriginHandle: consequence.originHandle || '', genericSkillRef: entry.genericSkillRef},
      approvedStanding: {status: consequence.kind === 'approved-decision' ? 'in-good-standing' : 'unknown',
        approvedStars: consequence.stars, approvedTm: consequence.tm,
        recalibrationPending: consequence.recalibrationPending === true ? {reason: 'Technical resolution recorded; trust recalibration pending.'} : null},
      historicalAwards: []
    };

    // V1 carries no display snapshot identity. A decision is an outcome from
    // the trusted publication port, not inferred from browser-visible fields.
    var hasApprovedProvenance = consequence.kind === 'approved-decision';
    var snapshot = {isPinned: false};

    // 2. Verified Challenges
    var rawChallenges = Array.isArray(payload.challenges) ? payload.challenges : [];
    var verifiedChallenges = [];
    for (var c = 0; c < rawChallenges.length; c++) {
      var norm = normalizeChallenge(rawChallenges[c]);
      if (norm) verifiedChallenges.push(norm);
    }

    var activeChallenges = verifiedChallenges.filter(function(ch) { return !ch.isResolved; });
    var resolvedChallenges = verifiedChallenges.filter(function(ch) { return ch.isResolved; });

    // Active material challenge check (determines Origin Contested)
    var hasActiveMaterialChallenge = activeChallenges.some(function(ch) {
      return ch.materialToOrigin;
    });

    // 3. Current Merit-Based Origin
    var rawOrig = payload.origin || {};
    var incumbentHandle = '';
    if (typeof rawOrig.currentOriginHandle === 'string' && rawOrig.currentOriginHandle.trim()) {
      incumbentHandle = rawOrig.currentOriginHandle.trim().replace(/^@/, '');
    }

    // Origin contested condition:
    // An active material challenge contests the known incumbent, not ownership.
    var isOriginContested = Boolean(incumbentHandle && hasActiveMaterialChallenge);

    var originModel = {
      handle: incumbentHandle || 'unassigned',
      status: isOriginContested ? 'contested' : (incumbentHandle ? 'held' : 'unknown'),
      isContested: isOriginContested,
      genericSkillRef: typeof rawOrig.genericSkillRef === 'string' ? rawOrig.genericSkillRef.trim() : (entry.genericSkillRef || ''),
      notice: isOriginContested
        ? 'Current Origin is actively contested by a verified material challenge under adjudication. Under Yggdrasil IV doctrine, Origin remains held by the incumbent and does not transfer or vacate while contested.'
        : (incumbentHandle ? 'Merit-based Origin is held by the qualified named implementation. Transfer requires an approved Class C determination.' : 'Origin ownership is unavailable from the consequence source.')
    };

    // 4. Approved Standing
    var rawApp = payload.approvedStanding || {};
    var rawStatus = typeof rawApp.status === 'string' ? rawApp.status.trim().toLowerCase() : '';
    var rawStars = (typeof rawApp.approvedStars === 'number' && rawApp.approvedStars >= 0 && rawApp.approvedStars <= 6)
      ? rawApp.approvedStars : null;
    var rawTm = (typeof rawApp.approvedTm === 'number' && !isNaN(rawApp.approvedTm) && rawApp.approvedTm >= 0)
      ? rawApp.approvedTm : null;

    // Numeric decision and current baseline are distinct source outcomes.
    var approvedStars = hasApprovedProvenance ? rawStars : null;
    var approvedTm = hasApprovedProvenance ? rawTm : null;

    // Numerical degradation packet
    var degradation = null;
    if (rawApp.degradation && typeof rawApp.degradation === 'object') {
      var d = rawApp.degradation;
      degradation = {
        priorStars: typeof d.priorStars === 'number' ? d.priorStars : null,
        degradedStars: typeof d.degradedStars === 'number' ? d.degradedStars : null,
        reason: typeof d.reason === 'string' ? d.reason.trim() : 'Approved numerical degradation',
        decisionRef: isSafeHttps(d.decisionRef) ? d.decisionRef.trim() : '',
        adjudicatedAtUTC: typeof d.adjudicatedAtUTC === 'string' ? d.adjudicatedAtUTC.trim() : ''
      };
    }

    // Recalibration pending packet
    var recalibrationPending = null;
    if (rawApp.recalibrationPending && typeof rawApp.recalibrationPending === 'object') {
      var r = rawApp.recalibrationPending;
      recalibrationPending = {
        reason: typeof r.reason === 'string' ? r.reason.trim() : 'Technical challenge resolved; trust recalibration pending Class C review',
        resolvedChallengeId: typeof r.resolvedChallengeId === 'string' ? r.resolvedChallengeId.trim() : '',
        closedAtUTC: typeof r.closedAtUTC === 'string' ? r.closedAtUTC.trim() : '',
        receiptUrl: isSafeHttps(r.receiptUrl) ? r.receiptUrl.trim() : ''
      };
    }

    // Derive overall standing classification
    var standingKey = 'unknown';
    var standingBadge = '[Unassessed] Partial / Unknown Standing';
    var standingDesc = 'Standing assessment has not been formally approved in this snapshot.';
    var standingTone = 'muted';

    if (isOriginContested) {
      standingKey = 'contested';
      standingBadge = '[Contested] Origin Contested';
      standingDesc = 'A verified material challenge is actively contesting Origin qualification. Current Origin remains held by the incumbent during adjudication.';
      standingTone = 'honor-red';
    } else if (rawStatus === 'degraded' || degradation !== null) {
      standingKey = 'degraded';
      standingBadge = '[Degraded] Approved Numerical Degradation';
      standingDesc = 'A Class C adjudicated reduction in standing has been approved and published in the snapshot.';
      standingTone = 'honor-red';
    } else if (recalibrationPending !== null || rawStatus === 'recalibration-pending') {
      standingKey = 'recalibration-pending';
      standingBadge = '[Pending] Trust Recalibration';
      standingDesc = 'The consequence source reports that canonical trust recalibration is pending Class C review.';
      standingTone = 'violet';
    } else if (activeChallenges.some(function(ch) { return ch.isAdjudicationPending; })) {
      standingKey = 'adjudication-pending';
      standingBadge = '[Pending] Adjudication Pending';
      standingDesc = 'Independent counterevidence has been verified for a specified claim. Awaiting adjudication; no automatic demotion applies.';
      standingTone = 'gold';
    } else if (consequence.kind === 'current-baseline') {
      standingKey = 'baseline';
      standingBadge = '[Current] Published Baseline';
      standingDesc = 'Current baseline supplied by the publication source; no numeric decision is asserted.';
      standingTone = 'muted';
    } else if (hasApprovedProvenance) {
      standingKey = 'approved-decision';
      standingBadge = '[Approved] Published Numeric Decision';
      standingDesc = 'Numeric standing is supplied by the canonical consequence source.';
      standingTone = 'teal';
    }

    // Single Coherent Authority Doctrine (Yggdrasil IV):
    // If the entry presents hero metrics (trustMagnitude, level) that contradict
    // the snapshot approved metrics, reject/degrade contradictory payload rather
    // than rendering two conflicting authorities.
    var entryTm = (typeof entry.trustMagnitude === 'number' && !isNaN(entry.trustMagnitude))
      ? entry.trustMagnitude
      : ((typeof entry.overallTrustMagnitude === 'number' && !isNaN(entry.overallTrustMagnitude))
        ? entry.overallTrustMagnitude
        : null);

    var entryStars = null;
    if (typeof entry.level === 'number') {
      entryStars = entry.level;
    } else if (typeof entry.level === 'string') {
      var matchDigits = entry.level.match(/\d+/);
      if (matchDigits) entryStars = parseInt(matchDigits[0], 10);
    }

    var isContradictory = false;
    var contradictionDetail = '';
    if (hasApprovedProvenance) {
      if (entryTm !== null && approvedTm !== null && Math.abs(entryTm - approvedTm) > 0.01) {
        isContradictory = true;
        contradictionDetail = 'Hero Trust Magnitude (' + entryTm + ') contradicts snapshot approved TM (' + approvedTm + ').';
      } else if (entryStars !== null && approvedStars !== null && entryStars !== approvedStars) {
        isContradictory = true;
        contradictionDetail = 'Hero star rank (' + entryStars + '★) contradicts snapshot approved rank (' + approvedStars + '★).';
      }
    }

    if (isContradictory) {
      standingKey = 'contradictory';
      standingBadge = '[Degraded] Contradictory Authority Payload';
      standingDesc = 'Payload rejected under single-authority doctrine: ' + contradictionDetail + ' View refuses conflicting authorities.';
      standingTone = 'honor-red';
      approvedStars = null;
      approvedTm = null;
    }

    // 5. Historical Awards
    var historicalAwards = normalizeAwards(payload.historicalAwards);

    return {
      snapshot: snapshot,
      consequence: consequence,
      standing: {
        key: standingKey,
        badgeText: standingBadge,
        description: standingDesc,
        tone: standingTone,
        approvedStars: approvedStars,
        approvedTm: approvedTm,
        degradation: degradation,
        recalibrationPending: recalibrationPending
      },
      origin: originModel,
      challenges: verifiedChallenges,
      activeChallengesCount: activeChallenges.length,
      resolvedChallengesCount: resolvedChallenges.length,
      historicalAwards: historicalAwards
    };
  }

  // ── 3. CHALLENGE IDENTITY COMPONENTS (REUSABLE) ───────────────────────
  //
  // Geometry lives on a 24-unit grid so the same marks can be ported to SVG
  // badges, OG cards, graph nodes and Python generators without redrawing.
  // Colours come only from CSS tokens in docs/css/styles.css; the markup
  // carries classes and data attributes, never colour values.

  var MARK_SIZES = {sm: true, md: true, lg: true, xl: true};

  // The plate: a chamfered square, the punch every challenge mark is struck on.
  var PLATE = [[5, 3], [19, 3], [21, 5], [21, 19], [19, 21], [5, 21], [3, 19], [3, 5]];

  // An open challenge cuts a V-notch into the top edge. Depth carries severity:
  // a scoped challenge nicks the plate, a material one cleaves it past centre.
  var NOTCH = {
    scoped: [[9.5, 3], [12, 9], [14.5, 3]],
    material: [[9, 3], [12, 15], [15, 3]]
  };

  // Hachure spacing (x + y step). Material hatching is denser.
  var HATCH_STEP = {scoped: 3.4, material: 2.6};

  function round2(n) {
    return Math.round(n * 100) / 100;
  }

  function pathOf(points) {
    var d = '';
    for (var i = 0; i < points.length; i++) {
      d += (i ? 'L' : 'M') + round2(points[i][0]) + ' ' + round2(points[i][1]);
    }
    return d + 'Z';
  }

  function notchedPlate(severity) {
    return [PLATE[0]].concat(NOTCH[severity], PLATE.slice(1));
  }

  /**
   * Diagonal hachure clipped to a (possibly concave) polygon. Lines run along
   * x + y = c; each line keeps only the even-odd inside spans.
   */
  function hatchSegments(poly, step) {
    var segs = [];
    for (var c = 8 + step / 2; c < 40; c += step) {
      var ts = [];
      for (var i = 0; i < poly.length; i++) {
        var a = poly[i], b = poly[(i + 1) % poly.length];
        var fa = a[0] + a[1] - c, fb = b[0] + b[1] - c;
        if ((fa < 0) !== (fb < 0)) {
          var u = fa / (fa - fb);
          ts.push(a[0] + u * (b[0] - a[0]));
        }
      }
      ts.sort(function(x, y) { return x - y; });
      for (var k = 0; k + 1 < ts.length; k += 2) {
        segs.push([ts[k], c - ts[k], ts[k + 1], c - ts[k + 1]]);
      }
    }
    return segs;
  }

  /** Heraldic chevron band: tip at (12, yTip), arms reaching the plate edges (x = 4 / 20). */
  function chevronPath(yTip, thickness) {
    var drop = 7;
    return pathOf([[4, yTip + drop], [12, yTip], [20, yTip + drop],
      [20, yTip + drop + thickness], [12, yTip + thickness], [4, yTip + drop + thickness]]);
  }

  // Answered challenges become a struck hallmark. One chevron = scoped,
  // two = material (Origin was on the line). Upstream adds a plinth bar.
  var HALLMARK = {
    rebutted: {
      scoped: [chevronPath(7, 3.6)],
      material: [chevronPath(4.5, 2.9), chevronPath(9.6, 2.9)]
    },
    upstream: {
      scoped: [chevronPath(5.5, 3.4), 'M6.5 17.3L17.5 17.3L17.5 19.3L6.5 19.3Z'],
      material: [chevronPath(3.9, 2.5), chevronPath(8.2, 2.5), 'M7 18.6L17 18.6L17 20L7 20Z']
    }
  };

  var MARK_LABELS = {
    'open:scoped': 'Open scoped challenge',
    'open:material': 'Open material challenge, contests Origin',
    'rebutted:scoped': 'Scoped challenge technically rebutted',
    'rebutted:material': 'Material challenge technically rebutted',
    'upstream:scoped': 'Scoped challenge resolved by upstream improvement',
    'upstream:material': 'Material challenge resolved by upstream improvement'
  };

  var markSvgCache = {};

  function markSvg(state, severity) {
    var key = state + ':' + severity;
    if (markSvgCache[key]) return markSvgCache[key];
    var s = ['<svg class="lc-mark__svg" viewBox="0 0 24 24" focusable="false" aria-hidden="true">'];
    if (state === 'open') {
      var poly = notchedPlate(severity);
      var d = pathOf(poly);
      s.push('<path class="lc-mark__slate" d="' + d + '"/>');
      s.push('<g class="lc-mark__hatch">');
      var segs = hatchSegments(poly, HATCH_STEP[severity]);
      for (var i = 0; i < segs.length; i++) {
        var g = segs[i];
        s.push('<line x1="' + round2(g[0]) + '" y1="' + round2(g[1]) + '" x2="' + round2(g[2]) +
          '" y2="' + round2(g[3]) + '" style="--i:' + i + '"/>');
      }
      s.push('</g>');
      s.push('<path class="lc-mark__edge" d="' + d + '"/>');
    } else {
      var plate = pathOf(PLATE);
      s.push('<path class="lc-mark__steel" d="' + plate + '"/>');
      s.push('<path class="lc-mark__bevel-hi" d="M3 19V5L5 3H19"/>');
      s.push('<path class="lc-mark__bevel-lo" d="M21 5V19L19 21H5"/>');
      var parts = HALLMARK[state][severity];
      for (var p = 0; p < parts.length; p++) s.push('<path class="lc-mark__chev" d="' + parts[p] + '"/>');
      s.push('<path class="lc-mark__rim" d="' + plate + '"/>');
    }
    s.push('</svg>');
    markSvgCache[key] = s.join('');
    return markSvgCache[key];
  }

  /**
   * Challenge Mark.
   *   state     'open' | 'rebutted' | 'upstream'
   *   opts.severity    'scoped' | 'material'   (default 'scoped')
   *   opts.size        'sm' | 'md' | 'lg' | 'xl' (default 'md')
   *   opts.label       accessible name override
   *   opts.decorative  true => aria-hidden (an adjacent label carries meaning)
   */
  function challengeMark(state, opts) {
    opts = opts || {};
    if (state !== 'open' && state !== 'rebutted' && state !== 'upstream') state = 'open';
    var severity = opts.severity === 'material' ? 'material' : 'scoped';
    var size = MARK_SIZES[opts.size] ? opts.size : 'md';
    var a11y = opts.decorative
      ? ' aria-hidden="true"'
      : ' role="img" aria-label="' + esc(opts.label || MARK_LABELS[state + ':' + severity]) + '"';
    return '<span class="lc-mark" data-state="' + state + '" data-severity="' + severity +
      '" data-size="' + size + '"' + a11y + '>' + markSvg(state, severity) + '</span>';
  }

  /** Map a normalized challenge to its mark state and severity. */
  function markStateOf(challenge) {
    var severity = challenge && challenge.materialToOrigin ? 'material' : 'scoped';
    if (!challenge || !challenge.isResolved) return {state: 'open', severity: severity};
    return {state: challenge.isUpstreamSuperseded ? 'upstream' : 'rebutted', severity: severity};
  }

  var CHIPS = {
    'open-scoped': {label: 'Scoped challenge', tone: 'signal', mark: ['open', 'scoped']},
    'open-material': {label: 'Contests Origin', tone: 'signal', mark: ['open', 'material']},
    'rebutted-scoped': {label: 'Rebutted', tone: 'steel', mark: ['rebutted', 'scoped']},
    'rebutted-material': {label: 'Rebutted', tone: 'steel', mark: ['rebutted', 'material']},
    'upstream-scoped': {label: 'Resolved upstream', tone: 'steel', mark: ['upstream', 'scoped']},
    'upstream-material': {label: 'Resolved upstream', tone: 'steel', mark: ['upstream', 'material']},
    'approved-decision': {label: 'Approved', tone: 'steel', swatch: 'solid'},
    'current-baseline': {label: 'Baseline', tone: 'quiet', swatch: 'hollow'},
    'unavailable': {label: 'Unavailable', tone: 'quiet', swatch: 'dotted'},
    'recalibration': {label: 'Recalibration pending', tone: 'quiet', swatch: 'dashed'},
    'origin-held': {label: 'Held', tone: 'steel', swatch: 'solid'},
    'origin-contested': {label: 'Contested', tone: 'signal', mark: ['open', 'material']},
    'origin-unknown': {label: 'Unavailable', tone: 'quiet', swatch: 'dotted'}
  };

  /**
   * State Chip: glyph + short visible label (symbol never stands alone).
   *   kind  key of CHIPS ('open-scoped', 'rebutted-material', 'approved-decision', ...)
   *   opts.label  visible label override
   */
  function stateChip(kind, opts) {
    opts = opts || {};
    var spec = CHIPS[kind] || CHIPS.unavailable;
    var glyph = spec.mark
      ? challengeMark(spec.mark[0], {severity: spec.mark[1], size: 'sm', decorative: true})
      : '<span class="lc-chip__swatch" data-swatch="' + spec.swatch + '" aria-hidden="true"></span>';
    return '<span class="lc-chip" data-chip="' + esc(kind) + '" data-tone="' + spec.tone + '">' +
      glyph + '<span class="lc-chip__label">' + esc(opts.label || spec.label) + '</span></span>';
  }

  // Trust Magnitude is drawn on a log scale; ticks mark the grade floors.
  var METER_CAP = 500;
  var GRADE_FLOORS = [['C', 20], ['B', 50], ['A', 100], ['S', 250]];

  function meterPosition(tm) {
    var p = Math.log(1 + Math.max(0, tm)) / Math.log(1 + METER_CAP);
    return Math.max(0, Math.min(1, p));
  }

  function formatTm(tm) {
    return String(round2(tm));
  }

  var KIND_WORDS = {
    'approved-decision': 'approved decision',
    'current-baseline': 'published baseline',
    'unavailable': 'unavailable'
  };

  /**
   * Trust Meter: Trust Magnitude as a log-scale bar with grade-floor ticks.
   *   opts.tm                    number | null (null => unavailable)
   *   opts.kind                  'approved-decision' | 'current-baseline' | 'unavailable'
   *   opts.recalibrationPending  boolean
   *   opts.decorative            true => aria-hidden (an enclosing control is labelled)
   */
  function trustMeter(opts) {
    opts = opts || {};
    var hasTm = typeof opts.tm === 'number' && isFinite(opts.tm) && opts.tm >= 0;
    var kind = KIND_WORDS[opts.kind] && hasTm ? opts.kind : 'unavailable';
    var pct = hasTm ? round2(meterPosition(opts.tm) * 100) : 0;
    var a11y;
    if (opts.decorative) {
      a11y = ' aria-hidden="true"';
    } else if (hasTm) {
      a11y = ' role="meter" aria-label="Trust Magnitude" aria-valuemin="0" aria-valuemax="' + METER_CAP +
        '" aria-valuenow="' + esc(formatTm(opts.tm)) + '" aria-valuetext="' +
        esc(formatTm(opts.tm) + ', ' + KIND_WORDS[kind] + (opts.recalibrationPending ? ', recalibration pending' : '')) + '"';
    } else {
      a11y = ' role="img" aria-label="Trust Magnitude unavailable"';
    }
    var h = ['<span class="lc-meter" data-kind="' + kind + '"' + (opts.recalibrationPending ? ' data-recal=""' : '') +
      ' style="--lc-fill:' + pct + '%"' + a11y + '>'];
    h.push('<span class="lc-meter__track">');
    if (hasTm) h.push('<span class="lc-meter__fill"></span>');
    if (hasTm && opts.recalibrationPending) h.push('<span class="lc-meter__recal"></span>');
    for (var i = 0; hasTm && i < GRADE_FLOORS.length; i++) {
      h.push('<span class="lc-meter__tick" data-grade="' + GRADE_FLOORS[i][0] + '" style="--at:' +
        round2(meterPosition(GRADE_FLOORS[i][1]) * 100) + '%"></span>');
    }
    h.push('</span></span>');
    return h.join('');
  }

  var tipSeq = 0;

  /**
   * Accessible tooltip (toggletip). The trigger is a real button: hover, focus
   * and tap all reveal the tip, and aria-describedby gives screen readers the
   * full text even while it is visually hidden.
   *   inner      trigger HTML (must not contain interactive elements)
   *   lines      string | string[] tooltip text (escaped here)
   *   opts.label accessible name of the trigger
   *   opts.cls   extra classes on the trigger
   */
  function tip(inner, lines, opts) {
    opts = opts || {};
    tipSeq += 1;
    var id = 'lc-tip-' + tipSeq;
    var list = Array.isArray(lines) ? lines : [lines];
    var body = [];
    for (var i = 0; i < list.length; i++) {
      if (list[i]) body.push('<span class="lc-tipbox__line">' + esc(list[i]) + '</span>');
    }
    return '<button type="button" class="lc-tip' + (opts.cls ? ' ' + esc(opts.cls) : '') + '"' +
      (opts.label ? ' aria-label="' + esc(opts.label) + '"' : '') + ' aria-describedby="' + id + '">' + inner +
      '</button><span class="lc-tipbox" role="tooltip" id="' + id + '">' + body.join('') + '</span>';
  }

  // ── 4. ACCESSIBLE PANEL RENDERER ─────────────────────────────────────

  var SEVERITY_NOTES = {
    scoped: 'Scoped capability challenge: it tests one specified capability and does not contest Origin.',
    material: 'Material challenge: it could affect present Origin qualification. Origin stays with the incumbent while contested.'
  };

  var STATUS_NOTES = {
    open: 'Verified and public. Awaiting adjudication; there is no automatic demotion.',
    rebutted: 'Technically rebutted under independent, reproducible verification. The original challenge stays on record.',
    upstream: 'Resolved by an upstream improvement to the same challenged claim, independently verified. The original challenge stays on record.'
  };

  var EVENT_LABELS = {
    'verified-publication': 'Verified and published',
    'technical-resolution': 'Technical resolution'
  };

  var GITHUB_HANDLE = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$/;

  function link(href, label) {
    return '<a class="lc-link" href="' + esc(href) + '" target="_blank" rel="noopener noreferrer">' +
      esc(label) + '<span aria-hidden="true"> &#8599;</span></a>';
  }

  function dayCount(fromUtc, toUtc) {
    var a = parseUtc(fromUtc), b = parseUtc(toUtc);
    if (isNaN(a) || isNaN(b) || b < a) return null;
    return Math.round((b - a) / 86400000);
  }

  function railHtml(ch) {
    var opened = formatDateUTC(ch.verifiedAtUTC);
    if (!ch.isResolved || !ch.resolution) {
      return '<span class="lc-rail" data-state="open" role="img" aria-label="Published ' + esc(opened) + ', still open">' +
        '<span class="lc-rail__date">' + esc(opened) + '</span><span class="lc-rail__bar"></span>' +
        '<span class="lc-rail__end"></span></span>';
    }
    var closed = formatDateUTC(ch.resolution.resolvedAtUTC);
    var days = dayCount(ch.verifiedAtUTC, ch.resolution.resolvedAtUTC);
    var span = days === null ? '' : ' after ' + days + (days === 1 ? ' day' : ' days');
    return '<span class="lc-rail" data-state="closed" role="img" aria-label="Published ' + esc(opened) +
      ', resolved ' + esc(closed) + esc(span) + '">' +
      '<span class="lc-rail__date">' + esc(opened) + '</span><span class="lc-rail__bar"></span>' +
      '<span class="lc-rail__date">' + esc(closed) + '</span></span>';
  }

  function recordRow(term, value, cls) {
    return '<div class="lc-record__row' + (cls ? ' ' + cls : '') + '"><dt>' + esc(term) + '</dt><dd>' + value + '</dd></div>';
  }

  function recordHtml(ch, mark) {
    var h = ['<div class="lc-record">'];
    h.push('<p class="lc-record__note">' + esc(SEVERITY_NOTES[mark.severity]) + ' ' + esc(STATUS_NOTES[mark.state]) + '</p>');
    h.push('<dl class="lc-record__grid">');
    h.push(recordRow('Challenge', '<code class="lc-code">' + esc(ch.challengeId) + '</code>', 'lc-record__row--wide'));
    if (ch.linkedChallengeId) h.push(recordRow('Linked', '<code class="lc-code">' + esc(ch.linkedChallengeId) + '</code>', 'lc-record__row--wide'));
    if (ch.behaviorId) h.push(recordRow('Behavior', esc(ch.behaviorId)));
    if (ch.environment) h.push(recordRow('Environment', esc(ch.environment)));
    // The assay: the pinned subject read against its comparator and baseline.
    if (ch.pinnedVersion || ch.pinnedSha) {
      h.push(recordRow('Pinned', esc(ch.pinnedVersion || 'pinned') + ' <span class="lc-dim">' + esc(ch.pinnedSha) + '</span>', 'lc-assay lc-assay--subject'));
    }
    if (ch.comparator) h.push(recordRow('Comparator', esc(ch.comparator), 'lc-assay lc-assay--comparator'));
    if (ch.baseline) h.push(recordRow('Baseline', esc(ch.baseline), 'lc-assay lc-assay--baseline'));
    h.push(recordRow('Verifier', '@' + esc(ch.verifier.verifierId) + ' <span class="lc-dim">' + esc(ch.verifier.verificationMethod) + '</span>'));
    if (ch.resolution && (ch.resolution.upstreamVersion || ch.resolution.upstreamSha)) {
      h.push(recordRow('Upstream', esc(ch.resolution.upstreamVersion || 'newer version') + ' <span class="lc-dim">' + esc(ch.resolution.upstreamSha) + '</span>'));
    }
    h.push('</dl>');
    if (Array.isArray(ch.history) && ch.history.length) {
      h.push('<ol class="lc-events">');
      for (var e = 0; e < ch.history.length; e++) {
        var ev = ch.history[e] || {};
        var type = typeof ev.event_type === 'string' ? ev.event_type : '';
        h.push('<li class="lc-events__item" data-event="' + esc(type) + '"><time class="lc-events__date">' +
          esc(formatDateUTC(ev.at_utc)) + '</time><span class="lc-events__what">' + esc(EVENT_LABELS[type] || type) +
          '</span><span class="lc-dim">@' + esc(ev.actor) + '</span></li>');
      }
      h.push('</ol>');
    }
    h.push('<p class="lc-record__links">');
    h.push(link(ch.verifier.receiptUrl, 'Verification receipt'));
    if (ch.contributorNoticeRef) h.push(link(ch.contributorNoticeRef, 'Contributor notice'));
    if (ch.resolution) h.push(link(ch.resolution.receiptUrl, 'Resolution proof'));
    h.push('</p></div>');
    return h.join('');
  }

  function boutHtml(ch) {
    var mark = markStateOf(ch);
    // The row's mark carries its state (no duplicate text chip); its accessible name says it.
    var h = ['<li class="lc-bout" data-state="' + mark.state + '" data-severity="' + mark.severity + '">'];
    h.push('<details class="lc-bout__details"><summary class="lc-bout__sum">');
    h.push(challengeMark(mark.state, {severity: mark.severity, size: 'md'}));
    h.push('<span class="lc-bout__main"><span class="lc-bout__claim">' + esc(ch.claim) + '</span>');
    h.push('<span class="lc-bout__meta">' + railHtml(ch) + '</span></span>');
    h.push('<span class="lc-bout__toggle" aria-hidden="true"></span></summary>');
    h.push(recordHtml(ch, mark));
    h.push('</details></li>');
    return h.join('');
  }

  function latestResolved(resolved) {
    var best = null, bestAt = -Infinity;
    for (var i = 0; i < resolved.length; i++) {
      var at = resolved[i].resolution ? parseUtc(resolved[i].resolution.resolvedAtUTC) : NaN;
      if (best === null || (!isNaN(at) && at >= bestAt)) { best = resolved[i]; bestAt = isNaN(at) ? bestAt : at; }
    }
    return best;
  }

  function starsHtml(stars, branch) {
    if (typeof stars !== 'number') return '';
    var rb = (typeof globalThis !== 'undefined' && typeof globalThis.rankBadge === 'function') ? globalThis.rankBadge : null;
    if (rb) {
      var opts = {variant: 'stars', size: 'sm', ariaLabel: stars + ' of 6 stars'};
      if (branch) opts.branch = branch;
      return '<span class="lc-stars" aria-hidden="true">' + rb(stars, opts) + '</span>';
    }
    return '<span class="lc-stars lc-stars--plain" aria-hidden="true">' + esc(stars) + '&#9733;</span>';
  }

  /**
   * Render the complete Trust Lifecycle panel HTML.
   *   opts.branch  resolved rank branch for star colouring (read, never derived)
   */
  function renderTrustLifecycleHtml(vm, opts) {
    if (!vm) return '';
    opts = opts || {};
    var open = [], resolved = [];
    for (var i = 0; i < vm.challenges.length; i++) (vm.challenges[i].isResolved ? resolved : open).push(vm.challenges[i]);
    var openMaterial = open.filter(function(c) { return c.materialToOrigin; });
    var lead = openMaterial[0] || open[0] || latestResolved(resolved);
    var panelState = open.length ? (openMaterial.length ? 'open-material' : 'open-scoped') : (resolved.length ? 'answered' : 'clear');

    var kind = vm.consequence.kind;
    var hasNumbers = kind !== 'unavailable' && typeof vm.consequence.tm === 'number';
    var recal = vm.standing.recalibrationPending;

    var h = [];
    h.push('<section class="lc-panel" data-lc-state="' + panelState + '" aria-labelledby="seLifecycleHeading">');

    // Header: the dominant challenge, shown not told. Its chip is the one text chip in the view.
    h.push('<header class="lc-head lc-anchor">');
    if (lead) {
      var leadMark = markStateOf(lead);
      var leadLabel = MARK_LABELS[leadMark.state + ':' + leadMark.severity];
      h.push(tip(challengeMark(leadMark.state, {severity: leadMark.severity, size: 'xl', decorative: true}),
        [leadLabel + '.', SEVERITY_NOTES[leadMark.severity], STATUS_NOTES[leadMark.state]],
        {cls: 'lc-head__mark', label: leadLabel}));
    }
    h.push('<div class="lc-head__text"><h3 id="seLifecycleHeading" class="lc-title">Trust Lifecycle</h3>');
    if (lead) {
      var leadState = markStateOf(lead);
      var group = leadState.state === 'open' ? (openMaterial.length ? openMaterial : open) : [lead];
      var chipKind = leadState.state === 'open' ? 'open-' + leadState.severity : leadState.state + '-' + leadState.severity;
      var chipLabel = group.length > 1 ? CHIPS[chipKind].label + ' ×' + group.length : null;
      h.push('<div class="lc-head__chips">' + stateChip(chipKind, {label: chipLabel}));
      if (resolved.length && (open.length || resolved.length > 1)) {
        h.push('<span class="lc-honors" role="img" aria-label="' + resolved.length + ' resolved ' +
          (resolved.length === 1 ? 'challenge' : 'challenges') + ' on record">');
        for (var r = 0; r < resolved.length; r++) {
          var rm = markStateOf(resolved[r]);
          h.push(challengeMark(rm.state, {severity: rm.severity, size: 'sm', decorative: true}));
        }
        h.push('</span>');
      }
      h.push('</div>');
    }
    h.push('</div></header>');

    // Standing plate: the numbers as instruments, then Origin.
    h.push('<div class="lc-plate" data-challenge="' + panelState + '" role="group" aria-label="Standing">');

    var meterLabel = hasNumbers
      ? 'Trust Magnitude ' + formatTm(vm.consequence.tm) + ', ' + vm.consequence.stars + ' of 6 stars, ' + KIND_WORDS[kind] +
        (recal ? ', recalibration pending' : '')
      : 'Trust standing unavailable';
    var meterLines = [];
    if (kind === 'approved-decision') meterLines.push('Approved numeric decision published by the canonical consequence source.');
    else if (kind === 'current-baseline') meterLines.push('Published baseline. No numeric decision is asserted.');
    else meterLines.push('The canonical consequence source is unavailable, so no rank or Trust Magnitude is shown.');
    if (recal) meterLines.push(recal.reason);
    if (open.length) meterLines.push('A pending challenge never changes these numbers by itself; there is no automatic demotion.');
    if (hasNumbers) meterLines.push('Log scale. Ticks mark grade floors: C 20, B 50, A 100, S 250 (S also needs evidence diversity).');

    var inst = ['<span class="lc-instrument">'];
    inst.push('<span class="lc-instrument__read"><span class="lc-num">' + (hasNumbers ? esc(formatTm(vm.consequence.tm)) : '&#8212;') +
      '</span><span class="lc-unit">TM</span></span>');
    if (hasNumbers) inst.push(starsHtml(vm.consequence.stars, opts.branch));
    // Decision, baseline and recalibration are carried by the meter's form (solid, hollow,
    // dashed collar); the trigger's accessible name and tooltip say it in words.
    inst.push(trustMeter({tm: hasNumbers ? vm.consequence.tm : null, kind: kind, recalibrationPending: !!recal, decorative: true}));
    inst.push('</span>');
    h.push('<div class="lc-plate__row lc-anchor">' + tip(inst.join(''), meterLines, {cls: 'lc-plate__meter', label: meterLabel}) + '</div>');

    // Origin: the wreath carries the contest, or the honour of having held it.
    var origin = vm.origin;
    var handle = origin.status === 'unknown' ? '' : origin.handle;
    var materialAnswered = resolved.filter(function(c) { return c.materialToOrigin; });
    var pin = '';
    if (origin.isContested) pin = challengeMark('open', {severity: 'material', size: 'sm', decorative: true});
    else if (handle && materialAnswered.length) {
      var pm = markStateOf(latestResolved(materialAnswered));
      pin = challengeMark(pm.state, {severity: 'material', size: 'sm', decorative: true});
    }
    var wreath = ['<span class="lc-wreath" data-status="' + esc(origin.status) + '">'];
    wreath.push('<span class="lc-wreath__initial" aria-hidden="true">' + (handle ? esc(handle.charAt(0).toUpperCase()) : '') + '</span>');
    if (handle && GITHUB_HANDLE.test(handle)) {
      wreath.push('<img class="lc-wreath__avatar" src="https://github.com/' + encodeURIComponent(handle) +
        '.png?size=96" alt="" width="40" height="40" loading="lazy" decoding="async">');
    }
    if (pin) wreath.push('<span class="lc-wreath__pin">' + pin + '</span>');
    wreath.push('</span>');
    var originLabel = handle
      ? 'Current Origin @' + handle + ', ' + (origin.isContested ? 'contested' : 'held') +
        (!origin.isContested && materialAnswered.length ? ', defended against a material challenge' : '')
      : 'Origin unavailable';
    var originInner = '<span class="lc-origin">' + wreath.join('') + '<span class="lc-origin__text">' +
      '<span class="lc-origin__line"><span class="lc-origin__handle"' + (handle ? '>@' + esc(handle) : ' data-none="">&#8212;') +
      '</span></span>' +
      (origin.genericSkillRef ? '<span class="lc-origin__bucket">' + esc(origin.genericSkillRef) + '</span>' : '') +
      '</span></span>';
    var originLines = [origin.notice];
    if (origin.genericSkillRef) originLines.push('Bucket: ' + origin.genericSkillRef + '.');
    h.push('<div class="lc-plate__row lc-anchor">' + tip(originInner, originLines, {cls: 'lc-plate__origin', label: originLabel}) + '</div>');
    h.push('</div>');

    // Challenge ledger: every verified challenge, open first, history kept.
    if (vm.challenges.length) {
      tipSeq += 1;
      var ledgerId = 'lc-ledger-' + tipSeq;
      h.push('<div class="lc-ledger"><h4 class="lc-ledger__title" id="' + ledgerId + '">Challenges' +
        '<span class="lc-ledger__count">' + open.length + ' open &middot; ' + resolved.length + ' resolved</span></h4>');
      h.push('<ol class="lc-ledger__list" aria-labelledby="' + ledgerId + '">');
      var ordered = open.concat(resolved);
      for (var b = 0; b < ordered.length; b++) h.push(boutHtml(ordered[b]));
      h.push('</ol></div>');
    }

    // Historical awards (not carried by v1; rendered only if a later contract supplies them).
    if (vm.historicalAwards.length) {
      h.push('<ol class="lc-awards" aria-label="Historical awards">');
      for (var a = 0; a < vm.historicalAwards.length; a++) {
        var aw = vm.historicalAwards[a];
        h.push('<li class="lc-awards__item"><time class="lc-events__date">' + esc(formatDateUTC(aw.dateUTC)) + '</time>' +
          '<span class="lc-awards__title">' + esc(aw.title) + '</span>' +
          (aw.stars != null ? '<span class="lc-dim">' + esc(aw.stars) + '&#9733;</span>' : '') +
          (aw.handle ? '<span class="lc-origin__handle">@' + esc(aw.handle) + '</span>' : '') +
          (aw.receiptRef ? link(aw.receiptRef, 'Receipt') : '') + '</li>');
      }
      h.push('</ol>');
    }

    h.push('</section>');
    return h.join('');
  }

  // ── 5. TOOLTIP BEHAVIOUR (TAP, ESCAPE, OUTSIDE CLICK) ────────────────

  var docBound = false;

  function closeTips(scope, except) {
    if (!scope || typeof scope.querySelectorAll !== 'function') return;
    var openTips = scope.querySelectorAll('.lc-tip[data-open]');
    for (var i = 0; i < openTips.length; i++) {
      if (openTips[i] !== except) openTips[i].removeAttribute('data-open');
    }
  }

  /** Tap toggles a tip (touch has no hover); Escape and outside taps close it. */
  function bindTips(el) {
    if (!el || typeof el.addEventListener !== 'function' || el.getAttribute('data-lc-tips') === 'bound') return;
    el.setAttribute('data-lc-tips', 'bound');
    el.addEventListener('click', function(ev) {
      var trigger = ev.target && ev.target.closest ? ev.target.closest('.lc-tip') : null;
      closeTips(el, trigger);
      if (!trigger) return;
      if (trigger.hasAttribute('data-open')) trigger.removeAttribute('data-open');
      else trigger.setAttribute('data-open', '');
    });
    el.addEventListener('keydown', function(ev) {
      if (ev.key === 'Escape') closeTips(el, null);
    });
    el.addEventListener('focusout', function(ev) {
      var t = ev.target;
      if (t && t.classList && t.classList.contains('lc-tip')) t.removeAttribute('data-open');
    });
    if (!docBound && typeof document !== 'undefined') {
      docBound = true;
      document.addEventListener('click', function(ev) {
        if (ev.target && ev.target.closest && ev.target.closest('.lc-panel')) return;
        closeTips(document, null);
      });
    }
  }

  // ── 6. PUBLIC MOUNT RENDER FUNCTION ───────────────────────────────────

  /**
   * Main entrypoint invoked by skill-explorer.js inside openExplorer().
   *
   * @param {string|HTMLElement} mount Mount element or id (e.g. 'se-tm')
   * @param {Object} entry Named skill entry (e.g. ns)
   */
  function renderLifecycleSection(mount, entry) {
    var el = typeof mount === 'string' ? document.getElementById(mount) : mount;
    if (!el) return;

    // Invariant: If trustLifecycle payload is absent, preserve existing DOM exactly (clear mount).
    if (!entry || !entry.trustLifecycle) {
      el.innerHTML = '';
      return;
    }

    var vm = buildTrustLifecycleViewModel(entry);
    if (!vm) {
      el.innerHTML = '';
      return;
    }

    // Branch is read from the taxonomy authority's emitted field, never derived.
    var semantics = typeof globalThis !== 'undefined' ? globalThis.GaiaSemantics : null;
    var branch = semantics && typeof semantics.branchOf === 'function'
      ? semantics.branchOf(entry)
      : (typeof entry.branch === 'string' ? entry.branch : '');

    el.innerHTML = renderTrustLifecycleHtml(vm, {branch: branch});
    bindTips(el);
  }

  return {
    isSafeHttps: isSafeHttps,
    esc: esc,
    formatDateUTC: formatDateUTC,
    normalizeChallenge: normalizeChallenge,
    normalizeAwards: normalizeAwards,
    buildTrustLifecycleViewModel: buildTrustLifecycleViewModel,
    renderTrustLifecycleHtml: renderTrustLifecycleHtml,
    renderLifecycleSection: renderLifecycleSection,
    components: {
      challengeMark: challengeMark,
      markStateOf: markStateOf,
      stateChip: stateChip,
      trustMeter: trustMeter,
      tip: tip,
      bindTips: bindTips
    }
  };
});

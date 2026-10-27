/**
 * trust-lifecycle.js — Yggdrasil IV Trust Degradation, Challenge, and Recovery UI
 *
 * Pure view-model builder and accessible DOM renderer for the skill detail
 * explorer (docs/js/skill-explorer.js).
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
      if (!parsed || ['verified-pending', 'technically-rebutted', 'resolved-by-upstream-improvement'].indexOf(item.status) < 0 || seen[parsed.challengeId] || item.subjectId !== entry.id ||
          typeof item.materialToOrigin !== 'boolean' || !Array.isArray(item.history) ||
          !item.history.length || (parsed.isResolved && (!parsed.resolution || item.history.length !== 2)) ||
          (!parsed.isResolved && item.history.length !== 1) ||
          !(item.linkedChallengeId === null || typeof item.linkedChallengeId === 'string') ||
          !item.history[0] || item.history[0].event_type !== 'verified-publication' ||
          item.history.some(function(event) { return !event || event.challenge_id !== item.challengeId ||
            typeof event.actor !== 'string' || !event.actor.trim() || typeof event.at_utc !== 'string' || !event.at_utc; }) ||
          (parsed.isResolved && (item.history[1].event_type !== 'technical-resolution' ||
            parsed.resolution.disposition !== item.status))) return null;
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
      var heroRank = typeof entry.level === 'number' ? entry.level : parseInt(entry.level, 10);
      if ((!isNaN(heroRank) && heroRank !== consequence.stars) ||
          (typeof entry.trustMagnitude === 'number' && Math.abs(entry.trustMagnitude - consequence.tm) > 0.01)) return null;
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

  // ── 3. ACCESSIBLE HTML RENDERER ───────────────────────────────────────

  /**
   * Render the complete Trust Lifecycle & Challenge History section HTML.
   */
  function renderTrustLifecycleHtml(vm) {
    if (!vm) return '';

    var h = [];
    h.push('<section class="se-lc-section" aria-labelledby="seLifecycleHeading">');

    // Section Header
    h.push('  <div class="se-flow-h">');
    h.push('    <div class="se-flow-h__lede">');
    h.push('      <span class="se-flow-eyebrow">Yggdrasil IV Governance</span>');
    h.push('      <h3 id="seLifecycleHeading" class="se-flow-title">Trust Lifecycle &amp; Challenge History</h3>');
    h.push('    </div>');
    h.push('  </div>');

    // Snapshot Identity Bar
    h.push('  <div class="se-lc-snapshot-bar" role="region" aria-label="Snapshot Identity">');
    if (vm.snapshot.isPinned) {
      h.push('    <div class="se-lc-snapshot-row">');
      h.push('      <span class="se-lc-snapshot-item"><strong class="se-lc-k">Snapshot:</strong> <code class="se-lc-code">' + esc(vm.snapshot.snapshotId) + '</code></span>');
      h.push('      <span class="se-lc-snapshot-item"><strong class="se-lc-k">Evaluated:</strong> ' + esc(formatDateUTC(vm.snapshot.evaluatedAtUTC)) + '</span>');
      if (vm.snapshot.policyVersion) {
        h.push('      <span class="se-lc-snapshot-item"><strong class="se-lc-k">Policy:</strong> ' + esc(vm.snapshot.policyVersion) + '</span>');
      }
      if (vm.snapshot.approvedBy) {
        h.push('      <span class="se-lc-snapshot-item"><strong class="se-lc-k">Approved By:</strong> ' + esc(vm.snapshot.approvedBy) + '</span>');
      }
      if (vm.snapshot.approvalRef) {
        h.push('      <span class="se-lc-snapshot-item"><a class="se-lc-link" href="' + esc(vm.snapshot.approvalRef) + '" target="_blank" rel="noopener noreferrer">Approval Reference &#8599;</a></span>');
      }
      if (vm.snapshot.isRehearsal) {
        h.push('      <span class="se-lc-snapshot-item"><span class="se-lc-badge se-lc-badge--gold" role="note">REHEARSAL</span> <em class="se-lc-em">Publication backend pending</em></span>');
      }
      if (!vm.snapshot.hasApprovedProvenance) {
        h.push('      <span class="se-lc-snapshot-item"><span class="se-lc-badge se-lc-badge--narrowed" role="note">UNAPPROVED SNAPSHOT</span> <em class="se-lc-em">Lacks maintainer/founder approval provenance</em></span>');
      }
      h.push('    </div>');
    } else {
      h.push('    <div class="se-lc-snapshot-row se-lc-snapshot-row--unpinned">');
      h.push('      <span class="se-lc-snapshot-item">Publication snapshot metadata unavailable</span>');
      h.push('    </div>');
    }
    h.push('  </div>');

    // Approved Standing Card
    h.push('  <div class="se-lc-card se-lc-card--standing se-lc-card--tone-' + esc(vm.standing.tone) + '" role="region" aria-label="Approved Standing">');
    h.push('    <div class="se-lc-card-header">');
    h.push('      <span class="se-lc-badge se-lc-badge--' + esc(vm.standing.tone) + '" role="status">' + esc(vm.standing.badgeText) + '</span>');
    h.push('      <div class="se-lc-metrics-group">');
    if (vm.standing.approvedStars != null) {
      h.push('        <span class="se-lc-metric-pill"><strong class="se-lc-k">Approved Rank:</strong> ' + esc(vm.standing.approvedStars) + '&#9733;</span>');
    } else {
      h.push('        <span class="se-lc-metric-pill se-lc-metric-pill--unassessed"><strong class="se-lc-k">Approved Rank:</strong> Unassessed</span>');
    }
    if (vm.standing.approvedTm != null) {
      h.push('        <span class="se-lc-metric-pill"><strong class="se-lc-k">Approved TM:</strong> ' + esc(vm.standing.approvedTm) + '</span>');
    }
    h.push('      </div>');
    h.push('    </div>');
    h.push('    <p class="se-lc-card-desc">' + esc(vm.standing.description) + '</p>');
    if (vm.consequence.kind === 'current-baseline') {
      h.push('    <p class="se-lc-card-desc">Published baseline: ' + esc(vm.consequence.stars) + '&#9733; · TM ' + esc(vm.consequence.tm) + ' (no numeric decision asserted).</p>');
    } else if (vm.consequence.kind === 'unavailable') {
      h.push('    <p class="se-lc-card-desc">Canonical consequence source unavailable.</p>');
    }

    // Degradation callout (if any)
    if (vm.standing.degradation) {
      var deg = vm.standing.degradation;
      h.push('    <div class="se-lc-callout se-lc-callout--degradation" role="alert">');
      h.push('      <div class="se-lc-callout-title">[Adjudicated Degradation] Approved Score Adjustment</div>');
      h.push('      <div class="se-lc-callout-body">');
      if (deg.priorStars != null && deg.degradedStars != null) {
        h.push('        <div class="se-lc-callout-row"><strong>Rank Shift:</strong> ' + esc(deg.priorStars) + '&#9733; &#8594; ' + esc(deg.degradedStars) + '&#9733;</div>');
      }
      h.push('        <div class="se-lc-callout-row"><strong>Adjudication Rationale:</strong> ' + esc(deg.reason) + '</div>');
      if (deg.adjudicatedAtUTC) {
        h.push('        <div class="se-lc-callout-row"><strong>Adjudicated:</strong> ' + esc(formatDateUTC(deg.adjudicatedAtUTC)) + '</div>');
      }
      if (deg.decisionRef) {
        h.push('        <div class="se-lc-callout-row"><a class="se-lc-link" href="' + esc(deg.decisionRef) + '" target="_blank" rel="noopener noreferrer">Class C Ruling Reference &#8599;</a></div>');
      }
      h.push('      </div>');
      h.push('    </div>');
    }

    // Recalibration pending callout (if any)
    if (vm.standing.recalibrationPending) {
      var rec = vm.standing.recalibrationPending;
      h.push('    <div class="se-lc-callout se-lc-callout--recalibration" role="note">');
      h.push('      <div class="se-lc-callout-title">[Technical Resolution] Recalibration Pending</div>');
      h.push('      <div class="se-lc-callout-body">');
      h.push('        <div class="se-lc-callout-row">' + esc(rec.reason) + '</div>');
      if (rec.resolvedChallengeId) {
        h.push('        <div class="se-lc-callout-row"><strong>Resolved Challenge:</strong> <code class="se-lc-code">' + esc(rec.resolvedChallengeId) + '</code></div>');
      }
      if (rec.closedAtUTC) {
        h.push('        <div class="se-lc-callout-row"><strong>Resolved Date:</strong> ' + esc(formatDateUTC(rec.closedAtUTC)) + '</div>');
      }
      if (rec.receiptUrl) {
        h.push('        <div class="se-lc-callout-row"><a class="se-lc-link" href="' + esc(rec.receiptUrl) + '" target="_blank" rel="noopener noreferrer">Technical Resolution Proof &#8599;</a></div>');
      }
      h.push('      </div>');
      h.push('    </div>');
    }
    h.push('  </div>');

    // Current Origin & Contest Status Card
    h.push('  <div class="se-lc-card se-lc-card--origin" role="region" aria-label="Merit-Based Origin Status">');
    h.push('    <div class="se-lc-card-header">');
    h.push('      <h4 class="se-lc-card-title">Merit-Based Origin</h4>');
    if (vm.origin.isContested) {
      h.push('      <span class="se-lc-badge se-lc-badge--honor-red" role="status">[Contested] Origin Contested</span>');
    } else if (vm.origin.status === 'held') {
      h.push('      <span class="se-lc-badge se-lc-badge--held" role="status">[Held] Origin Held</span>');
    } else {
      h.push('      <span class="se-lc-badge" role="status">[Unknown] Origin Unavailable</span>');
    }
    h.push('    </div>');

    h.push('    <div class="se-lc-origin-holder">');
    h.push('      <span class="se-lc-k">Current Origin Incumbent:</span> ');
    h.push('      <span class="atlas-handle se-lc-origin-handle">' + (vm.origin.status === 'unknown' ? 'Unavailable' : '@' + esc(vm.origin.handle)) + '</span>');
    if (vm.origin.genericSkillRef) {
      h.push('      <span class="se-lc-origin-generic">for bucket <code class="se-lc-code">' + esc(vm.origin.genericSkillRef) + '</code></span>');
    }
    h.push('    </div>');

    h.push('    <p class="se-lc-notice-text">' + esc(vm.origin.notice) + '</p>');
    h.push('  </div>');

    // Verified Public Challenges Section
    h.push('  <div class="se-lc-challenges-block" role="region" aria-label="Verified Public Challenges">');
    h.push('    <div class="se-lc-block-header">');
    h.push('      <h4 class="se-lc-block-title">Verified Public Challenges</h4>');
    h.push('      <span class="se-lc-count-pill">' + esc(vm.activeChallengesCount) + ' Active &middot; ' + esc(vm.resolvedChallengesCount) + ' Resolved</span>');
    h.push('    </div>');

    if (!vm.challenges.length) {
      h.push('    <div class="se-lc-empty">No verified public challenges on record for this skill.</div>');
    } else {
      h.push('    <div class="se-lc-challenge-list">');
      for (var j = 0; j < vm.challenges.length; j++) {
        var ch = vm.challenges[j];
        var openAttr = !ch.isResolved ? ' open' : '';
        h.push('      <details class="se-lc-challenge-item se-lc-challenge-item--' + (ch.isResolved ? 'resolved' : 'active') + '"' + openAttr + '>');
        h.push('        <summary class="se-lc-challenge-summary" tabindex="0">');
        h.push('          <div class="se-lc-challenge-summary-left">');

        // Scope Tag (Material Origin vs Scoped Capability)
        if (ch.materialToOrigin) {
          h.push('            <span class="se-lc-scope-tag se-lc-scope-tag--material">[Material Origin Challenge]</span>');
        } else {
          h.push('            <span class="se-lc-scope-tag se-lc-scope-tag--scoped">[Scoped Capability Challenge]</span>');
        }

        // Status Badge
        var statusClass = 'pending';
        var statusLabel = '[Pending] Verified Pending';
        if (ch.status === 'technically-rebutted') {
          statusClass = 'resolved';
          statusLabel = '[Rebutted] Technically Rebutted';
        } else if (ch.status === 'resolved-by-upstream-improvement') {
          statusClass = 'superseded';
          statusLabel = '[Superseded] Upstream Resolved';
        } else if (ch.status === 'upheld') {
          statusClass = 'upheld';
          statusLabel = '[Upheld] Upheld';
        } else if (ch.status === 'narrowed') {
          statusClass = 'narrowed';
          statusLabel = '[Narrowed] Narrowed';
        } else if (ch.status === 'rejected') {
          statusClass = 'rejected';
          statusLabel = '[Rejected] Rejected';
        }

        h.push('            <span class="se-lc-badge se-lc-badge--' + statusClass + '">' + esc(statusLabel) + '</span>');
        h.push('            <span class="se-lc-claim-text">' + esc(ch.claim) + '</span>');
        h.push('          </div>');
        h.push('          <div class="se-lc-challenge-summary-right">');
        h.push('            <span class="se-lc-date">' + esc(formatDateUTC(ch.verifiedAtUTC)) + '</span>');
        h.push('          </div>');
        h.push('        </summary>');

        // Expanded details
        h.push('        <div class="se-lc-challenge-details">');
        h.push('          <div class="se-lc-grid">');
        h.push('            <div class="se-lc-grid-cell">');
        h.push('              <span class="se-lc-cell-label">Challenge ID:</span>');
        h.push('              <code class="se-lc-code">' + esc(ch.challengeId) + '</code>');
        h.push('            </div>');

        if (ch.linkedChallengeId) {
          h.push('            <div class="se-lc-grid-cell"><span class="se-lc-cell-label">Linked challenge:</span><code class="se-lc-code">' + esc(ch.linkedChallengeId) + '</code></div>');
        }
        if (ch.behaviorId) {
          h.push('            <div class="se-lc-grid-cell">');
          h.push('              <span class="se-lc-cell-label">Behavior ID:</span>');
          h.push('              <span class="se-lc-cell-val">' + esc(ch.behaviorId) + '</span>');
          h.push('            </div>');
        }

        if (ch.pinnedVersion || ch.pinnedSha) {
          h.push('            <div class="se-lc-grid-cell">');
          h.push('              <span class="se-lc-cell-label">Pinned Source:</span>');
          h.push('              <span class="se-lc-cell-val">' + esc(ch.pinnedVersion || 'Pinned') + ' (' + esc(ch.pinnedSha || 'SHA') + ')</span>');
          h.push('            </div>');
        }

        if (ch.comparator || ch.baseline) {
          h.push('            <div class="se-lc-grid-cell">');
          h.push('              <span class="se-lc-cell-label">Comparison:</span>');
          h.push('              <span class="se-lc-cell-val">Comparator: ' + esc(ch.comparator || 'N/A') + ' &middot; Baseline: ' + esc(ch.baseline || 'N/A') + '</span>');
          h.push('            </div>');
        }

        h.push('            <div class="se-lc-grid-cell">');
        h.push('              <span class="se-lc-cell-label">Independent Verifier:</span>');
        h.push('              <span class="se-lc-cell-val">@' + esc(ch.verifier.verifierId) + ' (' + esc(ch.verifier.verificationMethod) + ')</span>');
        h.push('            </div>');

        h.push('            <div class="se-lc-grid-cell">');
        h.push('              <span class="se-lc-cell-label">Verification Receipt:</span>');
        h.push('              <a class="se-lc-link" href="' + esc(ch.verifier.receiptUrl) + '" target="_blank" rel="noopener noreferrer">Public Verification Receipt &#8599;</a>');
        h.push('            </div>');

        if (ch.contributorNoticeRef) {
          h.push('            <div class="se-lc-grid-cell">');
          h.push('              <span class="se-lc-cell-label">Contributor Notice:</span>');
          h.push('              <a class="se-lc-link" href="' + esc(ch.contributorNoticeRef) + '" target="_blank" rel="noopener noreferrer">Public Notice &#8599;</a>');
          if (ch.responseDueUTC) {
            h.push('              <span class="se-lc-muted-note">(Response due: ' + esc(formatDateUTC(ch.responseDueUTC)) + ')</span>');
          }
          h.push('            </div>');
        }
        h.push('          </div>'); // .se-lc-grid

        if (Array.isArray(ch.history)) {
          h.push('          <div class="se-lc-muted-note">');
          ch.history.forEach(function(event) {
            h.push('<div>' + esc(event.event_type) + ' · ' + esc(formatDateUTC(event.at_utc)) + ' · ' + esc(event.actor) + '</div>');
          });
          h.push('          </div>');
        }
        // Resolution section (if challenge is closed/resolved)
        if (ch.resolution) {
          h.push('          <div class="se-lc-res-box">');
          h.push('            <div class="se-lc-res-title">[Resolution Proof] ' + esc(ch.resolution.disposition) + '</div>');
          h.push('            <div class="se-lc-res-body">');
          h.push('              <div><strong>Resolved Date:</strong> ' + esc(formatDateUTC(ch.resolution.resolvedAtUTC)) + ' by @' + esc(ch.resolution.verifierId) + '</div>');
          if (ch.resolution.upstreamVersion || ch.resolution.upstreamSha) {
            h.push('              <div><strong>Upstream Source:</strong> ' + esc(ch.resolution.upstreamVersion || 'Newer version') + ' (' + esc(ch.resolution.upstreamSha || 'SHA') + ')</div>');
          }
          h.push('              <div><a class="se-lc-link" href="' + esc(ch.resolution.receiptUrl) + '" target="_blank" rel="noopener noreferrer">Technical Resolution Proof &#8599;</a></div>');
          if (ch.resolution.recalibrationPending) {
            h.push('              <div class="se-lc-muted-note">Canonical trust recalibration is pending Class C founder review.</div>');
          }
          h.push('            </div>');
          h.push('          </div>');
        } else if (ch.isUpstreamSuperseded) {
          h.push('          <div class="se-lc-res-box">');
          h.push('            <div class="se-lc-res-title">[Historical Record] Upstream-Superseded Historical Challenge</div>');
          h.push('            <p class="se-lc-muted-note">This challenge was historically verified and later superseded by an upstream improvement. Under Yggdrasil IV doctrine, historical challenge records remain publicly discoverable.</p>');
          h.push('          </div>');
        }

        h.push('        </div>'); // .se-lc-challenge-details
        h.push('      </details>');
      }
      h.push('    </div>'); // .se-lc-challenge-list
    }
    h.push('  </div>'); // .se-lc-challenges-block

    // Historical Awards Section
    h.push('  <div class="se-lc-awards-block" role="region" aria-label="Historical Awards and Permanent Attribution">');
    h.push('    <div class="se-lc-block-header">');
    h.push('      <h4 class="se-lc-block-title">Historical Awards &amp; Permanent Attribution</h4>');
    h.push('    </div>');

    if (!vm.historicalAwards.length) {
      h.push('    <div class="se-lc-empty">No historical awards recorded in the active snapshot.</div>');
    } else {
      h.push('    <div class="se-lc-award-list">');
      for (var a = 0; a < vm.historicalAwards.length; a++) {
        var aw = vm.historicalAwards[a];
        h.push('      <div class="se-lc-award-item">');
        h.push('        <div class="se-lc-award-left">');
        h.push('          <span class="se-lc-award-date">' + esc(formatDateUTC(aw.dateUTC)) + '</span>');
        h.push('          <span class="se-lc-award-title">' + esc(aw.title) + '</span>');
        if (aw.stars != null) {
          h.push('          <span class="se-lc-award-stars">' + esc(aw.stars) + '&#9733;</span>');
        }
        h.push('          <span class="se-lc-award-handle">@' + esc(aw.handle) + '</span>');
        if (aw.notes) {
          h.push('          <div class="se-lc-award-notes">' + esc(aw.notes) + '</div>');
        }
        h.push('        </div>');
        if (aw.receiptRef) {
          h.push('        <div class="se-lc-award-right">');
          h.push('          <a class="se-lc-link" href="' + esc(aw.receiptRef) + '" target="_blank" rel="noopener noreferrer">Award Receipt &#8599;</a>');
          h.push('        </div>');
        }
        h.push('      </div>');
      }
      h.push('    </div>');
    }
    h.push('  </div>'); // .se-lc-awards-block

    h.push('</section>');
    return h.join('\n');
  }

  // ── 4. STYLESHEET INJECTION (SCOPED, STRICTLY TOKEN-ANCHORED) ─────────

  function ensureStyles() {
    if (typeof document === 'undefined') return;
    if (document.getElementById('se-trust-lifecycle-styles')) return;

    var style = document.createElement('style');
    style.id = 'se-trust-lifecycle-styles';
    style.textContent = [
      '.se-lc-section { width: 100%; margin: 0 auto; color: var(--text); font-family: var(--font-body); }',
      '.se-lc-snapshot-bar { margin-bottom: 1.2rem; padding: 0.55rem 0.85rem; border: 1px solid var(--border); border-radius: 6px; background: rgba(0, 0, 0, 0.35); font-size: 0.78rem; color: var(--muted); }',
      '.se-lc-snapshot-row { display: flex; flex-wrap: wrap; gap: 0.6rem 1.4rem; align-items: center; }',
      '.se-lc-snapshot-item { display: inline-flex; align-items: center; gap: 0.35rem; }',
      '.se-lc-k { color: var(--text); font-weight: 600; }',
      '.se-lc-code { font-family: var(--font-mono); font-size: 0.76rem; background: var(--code-bg); padding: 0.1rem 0.3rem; border-radius: 3px; border: 1px solid var(--border); color: var(--text); }',
      '.se-lc-card { border-radius: 8px; padding: 1.1rem 1.25rem; margin-bottom: 1.4rem; background: var(--surface); border: 1px solid var(--border); }',
      '.se-lc-card-header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 0.75rem; margin-bottom: 0.6rem; }',
      '.se-lc-card-title { font-size: 1.05rem; font-weight: 600; margin: 0; font-family: var(--font-display); color: var(--text); letter-spacing: -0.01em; }',
      '.se-lc-card-desc { margin: 0.4rem 0 0; font-size: 0.88rem; line-height: 1.5; color: var(--text); }',
      '.se-lc-card--tone-honor-red { border-color: rgba(var(--honor-red-rgb, 239, 68, 68), 0.5); background: linear-gradient(180deg, rgba(var(--honor-red-rgb, 239, 68, 68), 0.08) 0%, var(--surface) 100%); }',
      '.se-lc-card--tone-teal { border-color: rgba(99, 202, 183, 0.4); background: linear-gradient(180deg, rgba(99, 202, 183, 0.06) 0%, var(--surface) 100%); }',
      '.se-lc-card--tone-violet { border-color: rgba(167, 139, 250, 0.4); background: linear-gradient(180deg, rgba(167, 139, 250, 0.06) 0%, var(--surface) 100%); }',
      '.se-lc-card--tone-gold { border-color: rgba(251, 191, 36, 0.4); background: linear-gradient(180deg, rgba(251, 191, 36, 0.06) 0%, var(--surface) 100%); }',
      '.se-lc-badge { display: inline-flex; align-items: center; padding: 0.2rem 0.55rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; line-height: 1.2; border: 1px solid var(--border); }',
      '.se-lc-badge--honor-red,.se-lc-badge--upheld { color: var(--honor-red); border-color: rgba(var(--honor-red-rgb, 239, 68, 68), 0.4); background: rgba(var(--honor-red-rgb, 239, 68, 68), 0.12); }',
      '.se-lc-badge--teal,.se-lc-badge--resolved,.se-lc-badge--held { color: var(--rank-2); border-color: rgba(99, 202, 183, 0.4); background: rgba(99, 202, 183, 0.12); }',
      '.se-lc-badge--violet,.se-lc-badge--recalibration { color: var(--rank-3); border-color: rgba(167, 139, 250, 0.4); background: rgba(167, 139, 250, 0.12); }',
      '.se-lc-badge--gold,.se-lc-badge--pending { color: var(--apex-gold); border-color: rgba(251, 191, 36, 0.4); background: rgba(251, 191, 36, 0.12); }',
      '.se-lc-badge--superseded { color: var(--muted); border-color: var(--border); background: rgba(148, 163, 184, 0.1); }',
      '.se-lc-badge--narrowed,.se-lc-badge--rejected { color: var(--muted); border-color: var(--border); background: rgba(148, 163, 184, 0.1); }',
      '.se-lc-metrics-group { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; }',
      '.se-lc-metric-pill { display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.2rem 0.5rem; background: rgba(0, 0, 0, 0.35); border: 1px solid var(--border); border-radius: 4px; font-size: 0.78rem; font-family: var(--font-mono); }',
      '.se-lc-callout { margin-top: 0.9rem; padding: 0.75rem 0.9rem; border-radius: 6px; border: 1px solid var(--border); background: rgba(0, 0, 0, 0.3); font-size: 0.84rem; }',
      '.se-lc-callout--degradation { border-color: rgba(var(--honor-red-rgb, 239, 68, 68), 0.35); }',
      '.se-lc-callout--recalibration { border-color: rgba(167, 139, 250, 0.35); }',
      '.se-lc-callout-title { font-weight: 700; margin-bottom: 0.35rem; font-size: 0.82rem; letter-spacing: 0.03em; }',
      '.se-lc-callout-body { display: flex; flex-direction: column; gap: 0.25rem; color: var(--text); }',
      '.se-lc-origin-holder { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; margin: 0.4rem 0; font-size: 0.95rem; }',
      '.se-lc-origin-handle { color: var(--honor-red); font-weight: 700; font-family: var(--font-mono); }',
      '.se-lc-origin-generic { color: var(--muted); font-size: 0.8rem; }',
      '.se-lc-notice-text { font-size: 0.82rem; color: var(--muted); line-height: 1.45; margin: 0.5rem 0 0; }',
      '.se-lc-challenges-block { margin-top: 1.6rem; }',
      '.se-lc-block-header { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.8rem; }',
      '.se-lc-block-title { font-family: var(--font-display); font-size: 1.25rem; font-weight: 600; margin: 0; color: var(--text); letter-spacing: -0.01em; }',
      '.se-lc-count-pill { font-size: 0.76rem; color: var(--muted); font-family: var(--font-mono); padding: 0.15rem 0.45rem; border: 1px solid var(--border); border-radius: 4px; background: rgba(0,0,0,0.25); }',
      '.se-lc-challenge-list { display: flex; flex-direction: column; gap: 0.75rem; }',
      '.se-lc-challenge-item { border: 1px solid var(--border); border-radius: 6px; background: var(--surface); overflow: hidden; transition: border-color 0.15s ease; }',
      '.se-lc-challenge-item:focus-within { border-color: var(--rank-2); }',
      '.se-lc-challenge-summary { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; cursor: pointer; user-select: none; list-style: none; gap: 0.75rem; background: rgba(0,0,0,0.18); outline: none; }',
      '.se-lc-challenge-summary::-webkit-details-marker { display: none; }',
      '.se-lc-challenge-summary:focus-visible { outline: 2px solid var(--rank-2); outline-offset: -2px; }',
      '.se-lc-challenge-summary-left { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 0.7rem; flex: 1 1 auto; }',
      '.se-lc-scope-tag { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; font-family: var(--font-mono); }',
      '.se-lc-scope-tag--material { color: var(--honor-red); }',
      '.se-lc-scope-tag--scoped { color: var(--tier-basic); }',
      '.se-lc-claim-text { font-size: 0.88rem; font-weight: 600; color: var(--text); }',
      '.se-lc-challenge-summary-right { flex: 0 0 auto; font-size: 0.76rem; color: var(--muted); font-family: var(--font-mono); }',
      '.se-lc-challenge-details { padding: 1rem 1.1rem; border-top: 1px solid var(--border); background: rgba(0,0,0,0.25); }',
      '.se-lc-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 0.65rem 1rem; font-size: 0.82rem; }',
      '.se-lc-grid-cell { display: flex; flex-direction: column; gap: 0.15rem; }',
      '.se-lc-cell-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); font-weight: 600; }',
      '.se-lc-cell-val { color: var(--text); }',
      '.se-lc-res-box { margin-top: 0.9rem; padding: 0.75rem 0.85rem; border-radius: 4px; border: 1px solid var(--border); background: rgba(0,0,0,0.35); font-size: 0.82rem; }',
      '.se-lc-res-title { font-weight: 700; font-size: 0.8rem; margin-bottom: 0.35rem; color: var(--rank-2); }',
      '.se-lc-res-body { display: flex; flex-direction: column; gap: 0.25rem; color: var(--text); }',
      '.se-lc-awards-block { margin-top: 1.8rem; padding-top: 1.4rem; border-top: 1px solid var(--border); }',
      '.se-lc-award-list { display: flex; flex-direction: column; gap: 0.55rem; }',
      '.se-lc-award-item { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.6rem; padding: 0.65rem 0.85rem; border: 1px solid var(--border); border-radius: 6px; background: rgba(0,0,0,0.22); font-size: 0.84rem; }',
      '.se-lc-award-left { display: flex; flex-wrap: wrap; align-items: center; gap: 0.45rem 0.7rem; }',
      '.se-lc-award-date { font-family: var(--font-mono); font-size: 0.76rem; color: var(--muted); }',
      '.se-lc-award-title { font-weight: 600; color: var(--text); }',
      '.se-lc-award-stars { color: var(--apex-gold); font-weight: 700; font-family: var(--font-mono); }',
      '.se-lc-award-handle { color: var(--honor-red); font-family: var(--font-mono); font-size: 0.8rem; }',
      '.se-lc-award-notes { width: 100%; color: var(--muted); font-size: 0.78rem; margin-top: 0.15rem; }',
      '.se-lc-link { color: var(--tier-basic); text-decoration: none; font-size: 0.8rem; }',
      '.se-lc-link:hover { text-decoration: underline; }',
      '.se-lc-empty { padding: 1.1rem; text-align: center; color: var(--muted); font-size: 0.84rem; border: 1px dashed var(--border); border-radius: 6px; }',
      '.se-lc-muted-note { color: var(--muted); font-size: 0.78rem; }'
    ].join('\n');
    document.head.appendChild(style);
  }

  // ── 5. PUBLIC MOUNT RENDER FUNCTION ───────────────────────────────────

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

    ensureStyles();
    el.innerHTML = renderTrustLifecycleHtml(vm);
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
    ensureStyles: ensureStyles
  };
});

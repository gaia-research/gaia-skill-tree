"""Score mattpocock/skills under all 4 proposals + synthesis, with full grandfathering.

"Grandfathering" here = treat the suite-of-suites graph as fusion-equivalent at maximum
permissiveness: count every transitive origin (depth-2 closure), accept all fusion recipes
the registry data carries (or that the suite structure implies), apply each proposal's
most-permissive fusion-magnitude rule.

Run:  python scoreGates.py
Inputs:  _snapshot.json (corpus structure)
         evidence-repo.json, evidence-media.json, evidence-written.json (curated by sonnet)
Outputs: _scores.json + console table.

The 9-predicate apex gate (RFC §10.12) is reported separately AFTER each proposal's TM
verdict so we see the formula score on its own merit before the gate clamps it.
"""
import json
import math
import os
import sys
import datetime

sys.stdout.reconfigure(encoding='utf-8')

DIR = os.path.dirname(os.path.abspath(__file__))


def loadJson(name, default=None):
    path = os.path.join(DIR, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def loadEvidence():
    """Merge curated evidence from the three sonnet runs (any present)."""
    rows = []
    for name in ['evidence-repo.json', 'evidence-media.json', 'evidence-written.json']:
        data = loadJson(name)
        if data and isinstance(data, dict):
            for ev in (data.get('evidence') or []):
                rows.append(ev)
    return rows


def parseStarsRaw(raw):
    """Extract integer star count from strings like '1247 stars' / 'stars: 1.2k'."""
    if raw is None:
        return None
    s = str(raw).lower().replace(',', '').strip()
    # find first numeric token, support k/m suffix
    import re
    m = re.search(r'(\d+(?:\.\d+)?)\s*([km])?', s)
    if not m:
        return None
    n = float(m.group(1))
    suf = m.group(2)
    if suf == 'k':
        n *= 1000
    elif suf == 'm':
        n *= 1_000_000
    return int(n)


def parseDownloadsRaw(raw):
    return parseStarsRaw(raw)


def parseCitationsRaw(raw):
    return parseStarsRaw(raw)


def parseInterviewRaw(raw):
    """Best-effort: extract view count for plateau."""
    return parseStarsRaw(raw)


# ---------------------------------------------------------------------------
# Per-type magnitude functions (raw magnitude before weight × freshness).
# Each proposal can override the magnitude function and the cap.
# ---------------------------------------------------------------------------

def magFusionRecipe(originsCount, capPerOrigin, mode='synthesis'):
    """
    P1: 16 × origins × 1.3 weight (linear)
    P2: 20 × origins × 1.8 weight (linear)
    P3: tiered — 5+ origins → 25 each, 7+ origins → 30 each, else 20 each — × 2.0
    P4: 20 × origins × 1.4 weight
    Synthesis: (15 × origins + 5 × √origins) × 1.4 — sqrt softening, no per-origin cap
    """
    if mode == 'P1':
        return 16 * originsCount  # weight applied separately
    if mode == 'P2':
        return 20 * originsCount
    if mode == 'P3':
        if originsCount >= 7:
            per = 30
        elif originsCount >= 5:
            per = 25
        else:
            per = 20
        return per * originsCount
    if mode == 'P4':
        return 20 * originsCount
    # synthesis (default)
    return 15 * originsCount + 5 * math.sqrt(originsCount)


def magGithubStarsOwn(stars, cap):
    """log10-ish: stars/1000 capped (same shape across all proposals; only cap differs)."""
    if stars is None or stars <= 0:
        return 0
    return min(cap, stars / 1000.0)


def magProxyContainment(externalStars, cap, hasDependencyLink=True):
    """external_stars/1000 × 0.8, capped. Synthesis adds: requires verifiable dep link else 0."""
    if externalStars is None or externalStars <= 0:
        return 0
    if not hasDependencyLink:
        return 0
    return min(cap, (externalStars / 1000.0) * 0.8)


def magNpmDownloads(weeklyDownloads, cap=100):
    """Not in core RFC type list but maps to repo-own-equivalent or proxy. We use floor."""
    if weeklyDownloads is None or weeklyDownloads <= 0:
        return 0
    # log10(weeklyDownloads) × 25 capped — rough fit so 1k DL = 75, 10k = 100
    return min(cap, math.log10(max(weeklyDownloads, 1)) * 25)


def magInterview(viewCount, cap=60):
    """Cap 60. Use views/100k × 30 + base 20 if verified video. Conservative."""
    if viewCount is None or viewCount <= 0:
        return 20  # baseline for verifiable existence
    return min(cap, 20 + (viewCount / 100_000.0) * 30)


def magArxiv(citations, cap, perCitation=0.2):
    """citations / 5 capped (RFC). Each cite worth ~0.2 raw."""
    if citations is None or citations <= 0:
        return 0
    return min(cap, citations / 5.0)


def magVerifierAttestation(verifierCount, perVerifier=30):
    """30 × verifiers."""
    return perVerifier * (verifierCount or 0)


def magBenchmarkResult(percentile, cap=100):
    """percentile capped at cap."""
    if percentile is None:
        return 0
    return min(cap, percentile)


def magPeerReview(reviewerCount, perReviewer=25):
    return perReviewer * (reviewerCount or 0)


def magRepoOwn(commits, contributors, cap=60):
    """commits/200 + contributors² × 2, capped."""
    if commits is None and contributors is None:
        return 0
    c = (commits or 0) / 200.0
    p = (contributors or 0) ** 2 * 2
    return min(cap, c + p)


def magSelfAttestation(_):
    return 10  # flat


# ---------------------------------------------------------------------------
# Plateau application (per-type, ordered by magnitude desc).
# ---------------------------------------------------------------------------

def applyPlateau(magnitudes, plateau, maxEntries):
    """Sort desc, multiply each by plateau[i], cap to maxEntries."""
    sortedMags = sorted(magnitudes, reverse=True)[:maxEntries]
    out = []
    for i, m in enumerate(sortedMags):
        mult = plateau[i] if i < len(plateau) else plateau[-1]
        out.append(m * mult)
    return out


# ---------------------------------------------------------------------------
# Proposal specs — drives the scoring.
# ---------------------------------------------------------------------------

PROPOSALS = {
    'P1-strict-S': {
        'thresholds': {'S': 320, 'A': 110, 'B': 55, 'C': 22},
        'fusionMode': 'P1',
        'fusionWeight': 1.3,
        'fusionPerOriginCap': None,
        'starsCap': 180,
        'proxyCap': 140,
        'arxivCap': 90,
        'verifierWeight': 1.5,
        'verifierMag': 28,
        'minDistinctTypesForS': 4,
        'requireNonSelfProducibleAtS': True,
        'socialTotalCap': 80,
        'plateaus': {
            'arxiv': ([1.0, 0.5, 0.25, 0.1, 0.1], 5),
            'repo-own': ([1.0, 0.5, 0.25], 3),
            'verifier-attestation': ([1.0, 0.85, 0.7], 5),
            'social-signal': ([1.0, 0.5, 0.25], 3),
            'interview': ([1.0, 0.5, 0.25], 3),
        },
        'mothershipDivisor': lambda nComponents: max(1, nComponents / 4),
    },
    'P2-attainable-S': {
        'thresholds': {'S': 200, 'A': 100, 'B': 50, 'C': 20},
        'fusionMode': 'P2',
        'fusionWeight': 1.8,
        'fusionPerOriginCap': None,
        'starsCap': 200,
        'proxyCap': 160,
        'arxivCap': 100,
        'verifierWeight': 1.5,
        'verifierMag': 30,
        'minDistinctTypesForS': 3,  # relaxed to 2 if fusion >=10 origins
        'fusionDiversityRelaxation': {'minOrigins': 10, 'minTypes': 2},
        'requireNonSelfProducibleAtS': False,
        'socialTotalCap': 80,
        'plateaus': {
            'arxiv': ([1.0, 0.5, 0.25, 0.125], 4),
            'repo-own': ([1.0, 0.5, 0.25], 3),
            'verifier-attestation': ([1.0, 1.0, 1.0], 5),
            'social-signal': ([1.0, 0.5, 0.25], 3),
            'interview': ([1.0, 0.5, 0.25], 3),
        },
        'mothershipDivisor': lambda nComponents: 1,  # no discount
    },
    'P3-fusion-heavy': {
        'thresholds': {'S': 250, 'A': 100, 'B': 50, 'C': 20},
        'fusionMode': 'P3',
        'fusionWeight': 2.0,
        'starsCap': 150,
        'proxyCap': 130,
        'arxivCap': 100,
        'verifierWeight': 1.5,
        'verifierMag': 30,
        'minDistinctTypesForS': 3,  # relaxed to 2 with S-fusion-exception (7+ origins)
        'sFusionException': {'minOrigins': 7, 'minTypes': 2},
        'requireNonSelfProducibleAtS': False,
        'requireGradedOriginsOnly': True,  # only origins ≥C count
        'socialTotalCap': 80,
        'plateaus': {
            'arxiv': ([1.0, 0.5, 0.25, 0.125], 4),
            'repo-own': ([1.0, 0.5, 0.25], 3),
            'verifier-attestation': ([1.0, 0.85, 0.7], 5),
            'social-signal': ([1.0, 0.5, 0.25], 3),
            'interview': ([1.0, 0.5, 0.25], 3),
        },
        'mothershipDivisor': lambda nComponents: max(1, nComponents),  # full N
    },
    'P4-community-heavy': {
        'thresholds': {'S': 220, 'A': 95, 'B': 45, 'C': 18},
        'fusionMode': 'P4',
        'fusionWeight': 1.4,
        'starsCap': 250,
        'proxyCap': 200,
        'arxivCap': 100,
        'verifierWeight': 1.5,
        'verifierMag': 30,
        'minDistinctTypesForS': 3,
        'requireNonSelfProducibleAtS': False,
        'socialTotalCap': 70,  # mid-A reachable
        'plateaus': {
            'arxiv': ([1.0, 0.5, 0.25, 0.125], 4),
            'repo-own': ([1.0, 0.5, 0.25], 3),
            'verifier-attestation': ([1.0, 0.85, 0.7], 5),
            'social-signal': ([1.0, 0.7, 0.4], 3),
            'interview': ([1.0, 0.7, 0.4], 3),
        },
        'mothershipDivisor': lambda nComponents: max(1, math.ceil(nComponents / 4)),
    },
    'synthesis': {
        'thresholds': {'S': 250, 'A': 100, 'B': 50, 'C': 20},
        'fusionMode': 'synthesis',
        'fusionWeight': 1.4,
        'starsCap': 200,
        'proxyCap': 160,
        'arxivCap': 100,
        'verifierWeight': 1.5,
        'verifierMag': 30,
        'minDistinctTypesForS': 3,
        'requireNonSelfProducibleAtS': True,
        'requireGradedOriginsOnly': True,
        'socialTotalCap': 80,
        'plateaus': {
            'arxiv': ([1.0, 0.5, 0.25, 0.125], 4),
            'repo-own': ([1.0, 0.5, 0.25], 3),
            'verifier-attestation': ([1.0, 0.85, 0.7], 5),
            'social-signal': ([1.0, 0.5, 0.25], 3),
            'interview': ([1.0, 0.5, 0.25], 3),
        },
        'mothershipDivisor': lambda nComponents: min(4, max(1, math.ceil(nComponents / 4))),
    },
    # Marco's suite-vs-fusion improvement — synthesis with 3 anti-gameability grafts:
    # (1) author-diversity divisor: N origins by K authors → effective magnitude ÷ max(1, N/K)
    # (2) suite-vs-fusion role tag: take min(suiteOriginCount, fusionOriginCount) for bonus
    # (3) per-origin grade-floor + ≥1 cross-author origin required at apex
    'synthesis-plus': {
        'thresholds': {'S': 250, 'A': 100, 'B': 50, 'C': 20},
        'fusionMode': 'synthesis',
        'fusionWeight': 1.4,
        'starsCap': 200,
        'proxyCap': 160,
        'arxivCap': 100,
        'verifierWeight': 1.5,
        'verifierMag': 30,
        'minDistinctTypesForS': 3,
        'requireNonSelfProducibleAtS': True,
        'requireGradedOriginsOnly': True,
        'socialTotalCap': 80,
        'authorDiversityDivisor': True,  # NEW
        'suiteVsFusionMin': True,  # NEW
        'requireCrossAuthorOriginAtS': True,  # NEW
        'plateaus': {
            'arxiv': ([1.0, 0.5, 0.25, 0.125], 4),
            'repo-own': ([1.0, 0.5, 0.25], 3),
            'verifier-attestation': ([1.0, 0.85, 0.7], 5),
            'social-signal': ([1.0, 0.5, 0.25], 3),
            'interview': ([1.0, 0.5, 0.25], 3),
        },
        'mothershipDivisor': lambda nComponents: min(4, max(1, math.ceil(nComponents / 4))),
    },
}

NON_SELF_PRODUCIBLE = {'benchmark-result', 'verifier-attestation', 'peer-review', 'proxy-containment'}

# Per-evidence post-weight tier bins (for "≥1 A-tier row" diversity rules)
def evTier(postWeightMag):
    if postWeightMag >= 90:
        return 'S'
    if postWeightMag >= 50:
        return 'A'
    if postWeightMag >= 20:
        return 'B'
    if postWeightMag >= 5:
        return 'C'
    return 'unranked'


# ---------------------------------------------------------------------------
# Score one proposal for one skill given its evidence rows and graph snapshot.
# ---------------------------------------------------------------------------

def scoreProposal(stance, snapshot, evidenceRows):
    spec = PROPOSALS[stance]
    weights = {
        'fusion-recipe': spec['fusionWeight'],
        'github-stars-own': 1.0,
        'proxy-containment': 1.0,
        'verifier-attestation': spec['verifierWeight'],
        'benchmark-result': 1.4,
        'arxiv': 1.0,
        'peer-review': 1.2,
        'repo-own': 0.6,
        'self-attestation': 0.4 if stance != 'P1-strict-S' else 0.5,
        'social-signal': 1.0,
        'interview': 0.8,  # treat interview ≈ social-signal-ish; not explicit RFC type
        'media-mention': 0.5,
        'npm-downloads': 0.7,
        'repo': 0.3,
    }

    plateaus = spec['plateaus']

    # Bucket evidence by type
    byType = {}
    for ev in evidenceRows:
        t = ev.get('type', 'repo')
        byType.setdefault(t, []).append(ev)

    perTypeScores = {}  # type -> total post-weight magnitude
    perRowDetails = []  # for diagnostic output
    distinctTypes = set()

    # 1) Fusion-recipe — derived from snapshot.transitiveCount (all origins, grandfathered)
    grandfatheredOrigins = snapshot.get('transitiveCount', 0)

    # CRITICAL CORRECTION (Marco 2026-06-17): only components with role='origin' count as
    # fusion-recipe origins. Variants ride on someone else's prior canonical origin and
    # MUST NOT inflate fusion magnitude. Per-generic-skill-node origin uniqueness rule.
    trueOrigins = sum(1 for c in snapshot.get('componentDetails', [])
                      if c.get('role') == 'origin')
    variantsCount = sum(1 for c in snapshot.get('componentDetails', [])
                        if c.get('role') == 'variant')

    if spec.get('requireGradedOriginsOnly'):
        # Only count origins with grade ≥ C AND role='origin'
        graded = [c for c in snapshot.get('componentDetails', [])
                  if c.get('grade') in {'S', 'A', 'B', 'C'} and c.get('role') == 'origin']
        validOrigins = len(graded)
    else:
        # Even non-strict proposals must respect role='origin' — variants are not fusion sources.
        validOrigins = trueOrigins

    if validOrigins > 0:
        rawMag = magFusionRecipe(validOrigins, spec.get('fusionPerOriginCap'), mode=spec['fusionMode'])

        # synthesis-plus: author-diversity divisor.
        # Count distinct authors among origins. mattpocock-19 → all from 'mattpocock' → divisor 19.
        if spec.get('authorDiversityDivisor'):
            authorIds = set()
            for c in snapshot.get('componentDetails', []):
                if c.get('id') in snapshot.get('directOrigins', []) or c.get('id') in snapshot.get('transitiveClosure', []):
                    cid = c.get('id', '')
                    author = cid.split('/')[0] if '/' in cid else 'unknown'
                    authorIds.add(author)
            distinctAuthors = max(1, len(authorIds))
            authorDivisor = max(1.0, validOrigins / distinctAuthors)
            rawMag = rawMag / authorDivisor
            authorDivNote = f' / author-diversity-divisor={authorDivisor:.2f} (N={validOrigins} origins, K={distinctAuthors} authors)'
        else:
            authorDivNote = ''

        # synthesis-plus: suite-vs-fusion min(). For now suite count == fusion count (registry
        # doesn't distinguish), so this is a no-op in mattpocock case but the structure is here
        # for when someone files a paper fusion graph that exceeds their installable suite.
        if spec.get('suiteVsFusionMin'):
            suiteOriginCount = len(snapshot.get('directOrigins', []))  # has suiteComponents
            fusionOriginCount = validOrigins  # post-graded-floor
            effectiveCount = min(suiteOriginCount, fusionOriginCount)
            if effectiveCount < validOrigins:
                rawMag *= effectiveCount / validOrigins
                authorDivNote += f' / suite-vs-fusion-min={effectiveCount}'

        postWeight = rawMag * weights['fusion-recipe']
        perTypeScores['fusion-recipe'] = postWeight
        distinctTypes.add('fusion-recipe')
        perRowDetails.append({
            'type': 'fusion-recipe',
            'rawMag': rawMag,
            'postWeight': postWeight,
            'tier': evTier(postWeight),
            'origins': validOrigins,
            'note': f'role=origin only ({trueOrigins}/{grandfatheredOrigins} components, {variantsCount} variants excluded){authorDivNote}',
        })

    # 2) Curated evidence rows
    for t, rows in byType.items():
        magnitudes = []
        for ev in rows:
            raw = ev.get('magnitudeRaw')
            if t == 'github-stars-own':
                stars = parseStarsRaw(raw)
                m = magGithubStarsOwn(stars, spec['starsCap'])
            elif t == 'proxy-containment':
                stars = parseStarsRaw(raw)
                m = magProxyContainment(stars, spec['proxyCap'], hasDependencyLink=ev.get('hasDependencyLink', True))
            elif t == 'arxiv':
                cites = parseCitationsRaw(raw)
                m = magArxiv(cites, spec['arxivCap'])
            elif t == 'verifier-attestation':
                count = ev.get('verifierCount', 1)
                m = magVerifierAttestation(count, spec['verifierMag'])
            elif t == 'benchmark-result':
                pct = ev.get('percentile')
                m = magBenchmarkResult(pct)
            elif t == 'peer-review':
                rc = ev.get('reviewerCount', 1)
                m = magPeerReview(rc)
            elif t == 'repo-own':
                m = magRepoOwn(ev.get('commits'), ev.get('contributors'))
            elif t == 'self-attestation':
                m = magSelfAttestation(raw)
            elif t == 'interview':
                m = magInterview(parseInterviewRaw(raw))
            elif t == 'npm-downloads':
                m = magNpmDownloads(parseDownloadsRaw(raw))
            elif t == 'social-signal':
                # bare magnitude; full social rules (creator multiplier, engagement) deferred.
                # use min(60, parseStarsRaw(raw)/100) as conservative placeholder.
                v = parseStarsRaw(raw)
                m = min(60, (v or 0) / 100)
            elif t == 'media-mention':
                m = 15  # conservative
            elif t == 'repo':
                m = 25  # cap 40, mid-baseline
            else:
                m = 0
            magnitudes.append(m)

        # Apply plateau if defined
        if t in plateaus:
            plat, maxN = plateaus[t]
            magnitudes = applyPlateau(magnitudes, plat, maxN)

        weight = weights.get(t, 0.5)
        postWeights = [m * weight for m in magnitudes]
        total = sum(postWeights)

        # social-signal absolute total cap
        if t == 'social-signal':
            total = min(total, spec['socialTotalCap'])

        if total > 0:
            perTypeScores[t] = total
            distinctTypes.add(t)
            for raw, pw in zip(magnitudes, postWeights):
                perRowDetails.append({
                    'type': t,
                    'rawMag': raw,
                    'postWeight': pw,
                    'tier': evTier(pw),
                    'note': '',
                })

    trustMagnitude = sum(perTypeScores.values())

    # Determine grade (formula side only; apex gate is separate)
    th = spec['thresholds']
    distinctCount = len(distinctTypes)
    hasNonSelfProducibleType = any(t in distinctTypes for t in NON_SELF_PRODUCIBLE)
    hasATier = any(d['tier'] in {'S', 'A'} for d in perRowDetails)
    hasSTier = any(d['tier'] == 'S' for d in perRowDetails)

    # S diversity check
    sDiversityOk = distinctCount >= spec['minDistinctTypesForS']
    # P2 fusion-relaxation
    if not sDiversityOk and stance == 'P2-attainable-S':
        rel = spec.get('fusionDiversityRelaxation', {})
        if validOrigins >= rel.get('minOrigins', 999) and distinctCount >= rel.get('minTypes', 999):
            sDiversityOk = True
    # P3 S-fusion-exception
    if not sDiversityOk and stance == 'P3-fusion-heavy':
        rel = spec.get('sFusionException', {})
        if validOrigins >= rel.get('minOrigins', 999) and distinctCount >= rel.get('minTypes', 999):
            sDiversityOk = True

    sNonSelfOk = (not spec['requireNonSelfProducibleAtS']) or hasNonSelfProducibleType

    grade = 'ungraded'
    gradeReason = []
    if trustMagnitude >= th['S'] and sDiversityOk and sNonSelfOk and hasATier:
        # Synthesis & P1 also require ≥1 S-tier row OR ≥3 A-tier of distinct types
        grade = 'S'
        gradeReason.append('S thresholds cleared')
    elif trustMagnitude >= th['A'] and distinctCount >= 1 and hasATier:
        grade = 'A'
        gradeReason.append('A thresholds cleared')
    elif trustMagnitude >= th['B']:
        grade = 'B'
        gradeReason.append('B threshold cleared')
    elif trustMagnitude >= th['C']:
        grade = 'C'
        gradeReason.append('C threshold cleared')
    else:
        gradeReason.append(f'TM {trustMagnitude:.1f} below C={th["C"]}')

    # Reasons for non-promotion
    if grade != 'S':
        if trustMagnitude < th['S']:
            gradeReason.append(f'TM {trustMagnitude:.1f} < S={th["S"]}')
        if not sDiversityOk:
            gradeReason.append(f'distinct types {distinctCount} < required {spec["minDistinctTypesForS"]}')
        if not sNonSelfOk:
            gradeReason.append('missing non-self-producible type')
        if not hasATier:
            gradeReason.append('no A-tier or S-tier row')

    return {
        'stance': stance,
        'thresholds': th,
        'trustMagnitude': round(trustMagnitude, 2),
        'grade': grade,
        'gradeReason': '; '.join(gradeReason),
        'distinctTypes': sorted(distinctTypes),
        'distinctTypeCount': distinctCount,
        'hasNonSelfProducible': hasNonSelfProducibleType,
        'hasATier': hasATier,
        'hasSTier': hasSTier,
        'fusionGrandfatheredOrigins': grandfatheredOrigins,
        'fusionValidOrigins': validOrigins,
        'perTypeScores': {k: round(v, 2) for k, v in perTypeScores.items()},
        'perRowDetails': perRowDetails,
    }


# ---------------------------------------------------------------------------
# 9-predicate apex gate (RFC §10.12) — reported AFTER TM verdict.
# ---------------------------------------------------------------------------

def evalApexGate(snapshot, stanceVerdict, evidenceRows, today=None):
    """Apex gate after Marco's 2026-06-17 amendments (FINAL):
    - Single origin-count predicate: ≥5 fusion-origin components graded ≥A
      (consolidates old transitiveOriginsGte12 + aGradedClosureGte8)
    - Depth-2 evaluated against fusion graph (role='origin' filter); suite is install-only
    - Tenure: source-based, A/S-tier evidence rows only, max source age ≥180 days
    - crossOrgVerifier: REMOVED (re-enable when ecosystem grows)
    - systemWideCap: REMOVED (cap=5 unlikely to bind)
    - apexPromotionPrSigned: SOLE human gate; Marco PR-signs at big-bang time
    Net: 6 predicates (was 9).
    """
    today = today or datetime.date.today()
    suite = snapshot
    suiteId = suite['suiteId']

    # Fusion-graph origins = role='origin' components only.
    fusionOrigins = [c for c in snapshot['componentDetails']
                     if c.get('role') == 'origin']
    fusionOriginIds = {c['id'] for c in fusionOrigins}
    aGradedFusionOrigins = [c for c in fusionOrigins
                            if c.get('grade') in {'S', 'A'}]

    predicates = {}

    # Predicate 1: ≥5 fusion-origin components graded A or S
    predicates['aGradedOriginsGte5'] = {
        'pass': len(aGradedFusionOrigins) >= 5,
        'value': f'{len(aGradedFusionOrigins)} A/S-graded fusion origins (out of {len(fusionOrigins)} total)',
        'note': '≥5 fusion-origin components (role=origin) with grade ≥A. Consolidates prior transitiveOriginsGte12 + aGradedClosureGte8.',
    }

    # Predicate 2: ≥1 directly-nested suite (fusion-side: nested origin contains its own origin children)
    nestedDirect = sum(1 for c in fusionOrigins
                       if c.get('id') in snapshot['directOrigins']
                       and c.get('nestedComponents'))
    predicates['directNestedSuiteGte1'] = {
        'pass': nestedDirect >= 1,
        'value': nestedDirect,
        'note': '≥1 directly-nested suite among role=origin children (graph-shape signal)',
    }

    # Predicate 3: depth-2 reachability — fusion-only graph
    # Count fusion-origins of fusion-origins that aren't already direct.
    direct = set(snapshot['directOrigins'])
    depth2OnlyFusion = set()
    for c in fusionOrigins:
        for n in (c.get('nestedComponents') or []):
            # Is the nested item also role='origin'? Need to check componentDetails for it.
            nestedDetail = next((d for d in snapshot['componentDetails'] if d['id'] == n), None)
            if nestedDetail and nestedDetail.get('role') == 'origin' and n not in direct:
                depth2OnlyFusion.add(n)
    predicates['depth2OnlyReachableGte1'] = {
        'pass': len(depth2OnlyFusion) >= 1,
        'value': len(depth2OnlyFusion),
        'note': '≥1 fusion-origin reachable only at depth-2 (suite components excluded — installation-only)',
    }

    # Predicate 4: formula puts skill at S
    predicates['overallGradeS'] = {
        'pass': stanceVerdict['grade'] == 'S',
        'value': stanceVerdict['grade'],
        'note': 'formula puts skill at S',
    }

    # Predicate 5: source-tenure ≥180 days, A/S-tier evidence rows only
    # Use perRowDetails which has post-weight magnitude already computed
    perRowDetails = stanceVerdict.get('perRowDetails', [])
    aOrSRowsByType = {}
    for d in perRowDetails:
        if d['tier'] in {'A', 'S'}:
            aOrSRowsByType.setdefault(d['type'], True)

    # Cross-reference back to evidenceRows for sourceStartedAt — match by type
    qualifyingTenureRows = []
    for ev in (evidenceRows or []):
        evType = ev.get('type')
        if evType not in aOrSRowsByType:
            continue
        rawDate = ev.get('sourceStartedAt')
        if not rawDate:
            continue
        try:
            d = datetime.date.fromisoformat(str(rawDate)[:10])
            days = (today - d).days
            if days >= 180:
                qualifyingTenureRows.append({
                    'skillId': ev.get('skillId'),
                    'type': evType,
                    'sourceStartedAt': rawDate,
                    'days': days,
                })
        except (ValueError, TypeError):
            continue
    qualifyingTenureRows.sort(key=lambda r: -r['days'])
    maxDays = qualifyingTenureRows[0]['days'] if qualifyingTenureRows else 0
    predicates['sourceTenureDaysGte180AorS'] = {
        'pass': maxDays >= 180,
        'value': f'{maxDays} days (best A/S-tier row); {len(qualifyingTenureRows)} qualifying rows',
        'note': '≥1 evidence row at A or S tier with source ≥180 days old',
        'qualifying': qualifyingTenureRows[:5],
    }

    # Predicate 6: Marco PR-signed apex promotion
    predicates['apexPromotionPrSigned'] = {
        'pass': False,
        'value': 'unsigned (intentional until G7 big-bang migration PR)',
        'note': 'sole human-attestation gate; cross-org cosigners disabled until ecosystem grows',
    }

    passes = sum(1 for p in predicates.values() if p['pass'])
    total = len(predicates)
    return {
        'predicateResults': predicates,
        'passingCount': passes,
        'totalPredicates': total,
        'apexEligible': passes == total,
        'failingPredicates': [k for k, v in predicates.items() if not v['pass']],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    snapshot = loadJson('_snapshot.json')
    if not snapshot:
        print('FATAL: _snapshot.json missing — run snapshot generator first')
        sys.exit(1)
    evidenceRows = loadEvidence()

    print('=' * 80)
    print(f"Scoring: {snapshot['suiteId']}")
    print(f"  Direct components: {snapshot['directCount']}")
    print(f"  Transitive origins (depth-2): {snapshot['transitiveCount']}")
    print(f"  Curated evidence rows loaded: {len(evidenceRows)}")
    if not evidenceRows:
        print('  WARNING: no curated evidence yet — only fusion-recipe will score')
    print('=' * 80)

    results = {}
    for stance in ['P1-strict-S', 'P2-attainable-S', 'P3-fusion-heavy', 'P4-community-heavy', 'synthesis', 'synthesis-plus']:
        verdict = scoreProposal(stance, snapshot, evidenceRows)
        gate = evalApexGate(snapshot, verdict, evidenceRows)
        results[stance] = {'verdict': verdict, 'apexGate': gate}

        print(f"\n--- {stance} ---")
        print(f"  TM:        {verdict['trustMagnitude']:.2f}")
        print(f"  Grade:     {verdict['grade']:<2}  ({verdict['gradeReason']})")
        print(f"  Types:     {verdict['distinctTypeCount']} distinct: {verdict['distinctTypes']}")
        print(f"  Per-type:  {verdict['perTypeScores']}")
        print(f"  Apex gate: {gate['passingCount']}/9 predicates pass")
        if not gate['apexEligible']:
            print(f"    Failing: {gate['failingPredicates']}")

    # Save
    out = {
        'generatedAt': str(datetime.date.today()),
        'snapshot': snapshot,
        'evidenceRows': evidenceRows,
        'evidenceRowCount': len(evidenceRows),
        'results': results,
    }
    with open(os.path.join(DIR, '_scores.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"\nWrote {os.path.join(DIR, '_scores.json')}")


if __name__ == '__main__':
    main()

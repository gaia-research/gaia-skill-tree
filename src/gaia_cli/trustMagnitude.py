"""G7 Trust Magnitude — per-evidence artifact scores, skill aggregate, apex gate.

Implements the G7 Trust Taxonomy RFC (founder/handovers/G7_TRUST_TAXONOMY_RFC.md)
plus the 2026-06-17 amendments (G7_HANDOVER_DELTA_2026-06-17.md):

- Ten evidence-type magnitude formulas with weights, caps, freshness, and
  per-type plateaus (RFC §2).
- Trust Magnitude aggregate: TM = sum(artifact_score_i) x set_bonus (RFC §3).
- Overall Trust Grade with diversity gate (RFC §4).
- Six-active-predicate apex gate (delta §B). Two predicates feature-flagged OFF
  return None (cross-org verifier, system-wide cap).
- Anti-auto-mint (RFC §10.14): only fusion-recipe rows are auto-derivable; every
  other evidence type must be physically present in the skill's evidence array.
- Rank-floor sanity rule support (RFC §4.3): exposed via promotion._passes_rank_floor.

All public symbols use camelCase / PascalCase per workspace rule (no underscores
in NEW symbols). Schema fields read defensively so the module functions before
I1's schema fields land in registry/named/ markdown frontmatter.
"""

from __future__ import annotations

import datetime
import math
from typing import Any, Optional

from gaia_cli.evidence import inherited_evidence

# ---------------------------------------------------------------------------
# Constants - RFC §2 master table
# ---------------------------------------------------------------------------

# Grade thresholds for Overall Trust Grade (RFC §4)
GRADE_S_FLOOR = 250.0
GRADE_A_FLOOR = 100.0
GRADE_B_FLOOR = 50.0
GRADE_C_FLOOR = 20.0

# Per-type weights (RFC §2.1)
TYPE_WEIGHTS = {
    "fusion-recipe": 1.5,
    "github-stars-own": 1.0,
    "proxy-containment": 1.0,
    "verifier-attestation": 1.5,
    "benchmark-result": 1.4,
    "arxiv": 1.0,
    "peer-review": 1.2,
    "repo-own": 0.6,
    "self-attestation": 0.5,
    "social-signal": 1.0,
}

# Per-type magnitude caps (RFC §2.1; social-signal is hard-capped per §10.7)
TYPE_CAPS = {
    "github-stars-own": 200.0,
    "proxy-containment": 160.0,
    "benchmark-result": 100.0,
    "arxiv": 100.0,
    "repo-own": 60.0,
    "self-attestation": 10.0,
    "social-signal": 80.0,
}

# Self-producible types that cannot anchor S alone (RFC §4 diversity gate)
SELF_PRODUCIBLE_TYPES = frozenset({"fusion-recipe", "self-attestation", "repo-own"})

# Apex predicate thresholds (delta §B)
APEX_AGRADED_ORIGINS_MIN = 5
APEX_TENURE_DAYS_MIN = 180

# Feature flags - when False, the predicate returns None (skipped, not failed).
ENABLE_CROSS_ORG_VERIFIER = False
ENABLE_SYSTEM_WIDE_CAP = False


# ---------------------------------------------------------------------------
# v2 inheritance contract (RATIFIED 2026-06-18, workflow wf_7cbe217f-006)
# ---------------------------------------------------------------------------
# Per-evidence-type partition between layers + inherit multipliers.
# Layers: "named" (sits on a named skill markdown) or "generic"
# (sits on a generic taxonomy node and is inheritable by named children).
#
# allowedLayers["named"] only -> "pinned-named" types: validation must reject
#   these rows when attached to a generic node.
# allowedLayers ["generic", "named"] -> "flexible" types: row may sit on a
#   named or a generic node. inheritMultiplier is applied ONLY when a flexible
#   row is inherited (sits on the generic, contributing to a named child's
#   TM); attached at the named layer itself, the multiplier is 1.0.

EVIDENCE_TYPE_LAYER_CONTRACT: dict = {
    # Pinned-named (cannot be inherited at all)
    'fusion-recipe':         {'allowedLayers': ['named'], 'inheritMultiplier': None},
    'github-stars-own':      {'allowedLayers': ['named'], 'inheritMultiplier': None},
    'repo-own':              {'allowedLayers': ['named'], 'inheritMultiplier': None},
    'self-attestation':      {'allowedLayers': ['named'], 'inheritMultiplier': None},
    'verifier-attestation':  {'allowedLayers': ['named'], 'inheritMultiplier': None},
    # Flexible (inheritable from generic with discount)
    'arxiv':                 {'allowedLayers': ['generic', 'named'], 'inheritMultiplier': 0.70},
    'peer-review':           {'allowedLayers': ['generic', 'named'], 'inheritMultiplier': 0.30},
    'social-signal':         {'allowedLayers': ['generic', 'named'], 'inheritMultiplier': 0.35},
    'proxy-containment':     {'allowedLayers': ['generic', 'named'], 'inheritMultiplier': 0.25},
    'benchmark-result':      {'allowedLayers': ['generic', 'named'], 'inheritMultiplier': 0.15},
}


def _ownLayerOf(skill: dict) -> str:
    """Return the skill's own layer ("named" if it has genericSkillRef, else "generic")."""
    return 'named' if skill.get('genericSkillRef') else 'generic'


def _rowLayerOf(row: dict, fallback: str = 'generic') -> str:
    """Read a row's layer field; legacy rows without it fall back per the source skill."""
    layer = row.get('layer')
    if layer in ('named', 'generic'):
        return layer
    return fallback


def _inheritMultiplierFor(row: dict, skill: dict) -> float:
    """Return the inherit multiplier for a row contributing to *skill*'s TM.

    Returns 1.0 unless:
    - The row's layer differs from the skill's own layer (i.e. it's inherited).
    - The row's evidence type is in the flexible partition with a numeric
      inheritMultiplier (the five non-pinned types).

    Pinned-named types (verifier-attestation, fusion-recipe, github-stars-own,
    repo-own, self-attestation) never trigger inheritance because the schema
    validator rejects them on generic nodes; if one slips through, this
    function returns 1.0 (caller inherits the row at face value rather than
    silently zeroing it).
    """
    rowLayer = _rowLayerOf(row)
    ownLayer = _ownLayerOf(skill)
    if rowLayer == ownLayer:
        return 1.0
    rowType = _typeOf(row)
    if rowType is None:
        return 1.0
    contract = EVIDENCE_TYPE_LAYER_CONTRACT.get(rowType)
    if contract is None:
        return 1.0
    mult = contract.get('inheritMultiplier')
    if mult is None:
        return 1.0
    return float(mult)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _grade(row: dict) -> Optional[str]:
    """Return effective grade letter for an evidence row (S/A/B/C) or None."""
    g = row.get("grade")
    if g in ("S", "A", "B", "C"):
        return g
    cls = row.get("class")
    if cls in ("S", "A", "B", "C"):
        return cls
    return None


def _gradeIndex(g: Optional[str]) -> int:
    """0=S best, 3=C, 4=ungraded."""
    if g == "S":
        return 0
    if g == "A":
        return 1
    if g == "B":
        return 2
    if g == "C":
        return 3
    return 4


def _parseIso(value: Any) -> Optional[datetime.datetime]:
    """Parse ISO 8601 string into a UTC-aware datetime, or None."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(raw)
    except ValueError:
        # Try date-only (YYYY-MM-DD)
        try:
            dt = datetime.datetime.strptime(raw[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def _utcNow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _canonicalUrl(url: Optional[str]) -> Optional[str]:
    """Normalize a URL for same-source dedup (RFC §5.2).

    Strips fragments, trailing slashes, normalizes tree/->blob/.
    """
    if not url:
        return None
    s = str(url).strip()
    if not s:
        return None
    # Strip fragment
    if "#" in s:
        s = s.split("#", 1)[0]
    # Normalize tree/->blob/ for github links
    s = s.replace("/tree/", "/blob/")
    # Strip trailing slash
    while s.endswith("/"):
        s = s[:-1]
    return s.lower()


TYPE_ALIASES: dict = {'repo': 'repo-own'}


def _typeOf(row: dict) -> Optional[str]:
    """Resolve evidence row type, normalizing legacy aliases (e.g. 'repo' -> 'repo-own')."""
    t = row.get("type")
    if not t:
        return None
    effectiveType = TYPE_ALIASES.get(t, t)
    return effectiveType


def _freshnessFactor(row: dict, evidenceType: str) -> float:
    """Compute freshness multiplier in [0, 1] (RFC §3 Freshness multipliers).

    Returns 1.0 if row has no `lastVerified` or the type doesn't decay.
    """
    decayPerYear = {
        "benchmark-result": 0.5,
        "social-signal": 0.5,
        "peer-review": 0.125,  # 25% per 2 years = 12.5%/year linear
    }
    rate = decayPerYear.get(evidenceType, 0.0)
    if rate == 0.0:
        return 1.0
    last = _parseIso(row.get("lastVerified"))
    if last is None:
        return 1.0
    ageYears = (_utcNow() - last).days / 365.25
    factor = 1.0 - rate * ageYears
    return max(0.0, factor)


# ---------------------------------------------------------------------------
# Per-type raw magnitude (RFC §2)
# ---------------------------------------------------------------------------


def _fusionRecipeMagnitude(origins: int) -> float:
    """RFC §2.2: m = 20*origins for origins ≤ 10; 200 + 20*sqrt(origins-10) past 10.

    Sqrt-softening past 10 prevents pathological large fusions from
    dominating the aggregate. Only graded ≥C origins count (see _gradedOriginCount).
    Weight 1.5.
    """
    if origins <= 0:
        return 0.0
    if origins <= 10:
        return 20.0 * origins
    return 200.0 + 20.0 * math.sqrt(origins - 10)


def _gradedOriginCount(origins: list, genericSkillMap: Optional[dict]) -> int:
    """Count fusion-recipe origins that are graded >= C (RFC §3.5).

    Skips origins whose role == 'variant' (delta §C-2).

    Args:
        origins: list of origin entries; either bare strings or dicts with id/role.
        genericSkillMap: {id: skill_dict} to look up grade and role.
    """
    if not origins:
        return 0
    seen = set()
    count = 0
    for entry in origins:
        if isinstance(entry, dict):
            originId = entry.get("id") or entry.get("skillId")
            inlineRole = entry.get("role")
            inlineGrade = entry.get("grade") or entry.get("overallGrade")
        else:
            originId = entry
            inlineRole = None
            inlineGrade = None
        if not originId or originId in seen:
            continue
        seen.add(originId)
        # If we have a registry map, resolve role and grade. Otherwise use
        # inline hints; fall back to assuming graded (so a bare-id list
        # without context still counts).
        if genericSkillMap is not None:
            node = genericSkillMap.get(originId) or {}
        else:
            node = {}
        # role='variant' contributes 0 (delta §C-2)
        role = inlineRole or node.get("role")
        if role == "variant":
            continue
        # Graded >= C check
        nodeGrade = inlineGrade
        if nodeGrade is None:
            nodeGrade = _highestGradeFromEvidence(node.get("evidence") or [])
        if nodeGrade is None:
            nodeGrade = node.get("overallGrade") or node.get("grade")
        if nodeGrade in ("S", "A", "B", "C"):
            count += 1
        elif genericSkillMap is None and inlineGrade is None:
            # Bare id list with no map and no inline grade: assume graded.
            count += 1
    return count


def _highestGradeFromEvidence(evidence: list) -> Optional[str]:
    best: Optional[str] = None
    for row in evidence or []:
        g = _grade(row)
        if g is None:
            continue
        if best is None or _gradeIndex(g) < _gradeIndex(best):
            best = g
    return best


# ---------------------------------------------------------------------------
# Public API: computeArtifactScore
# ---------------------------------------------------------------------------


def computeArtifactScore(
    evidenceRow: dict,
    genericSkillMap: Optional[dict] = None,
) -> float:
    """Compute the per-evidence artifact score (RFC §1, §3).

    artifact_score = magnitude * type_weight * freshness * creator_mult *
                     engagement_ratio * mothership_discount

    Note: plateau and same-source dedup are applied in computeTrustMagnitude
    (they require sibling-row context). This function returns the row's raw
    pre-plateau, pre-dedup contribution.

    Returns 0.0 for rows with unknown type.
    Returns 0.0 for verifier-attestation rows with `verifierActiveRank=False`
    (null-on-derank, RFC §10.4 - surfaced as 0 at the row level; sum-time
    callers can use computeArtifactScoreOrNone for the strict null reading).
    """
    score = computeArtifactScoreOrNone(evidenceRow, genericSkillMap)
    if score is None:
        return 0.0
    return score


def computeArtifactScoreOrNone(
    evidenceRow: dict,
    genericSkillMap: Optional[dict] = None,
) -> Optional[float]:
    """Same as computeArtifactScore but returns None for null-on-derank rows.

    Used by computeTrustMagnitude to exclude (not zero) deranked verifier rows
    from the sum, per RFC §10.4 / §5.6.
    """
    evidenceType = _typeOf(evidenceRow)
    if evidenceType is None:
        return 0.0

    # Sprint D W2a (#904) — mirrored and pending benchmark-result rows are
    # citations only and MUST be excluded from Trust Magnitude. Return None
    # so the row is dropped from the TM sum entirely (matches the
    # null-on-derank contract); returning 0.0 would still trigger a fallback
    # grade-stamp through derive_row_grade, which is not the desired behavior.
    if evidenceType == "benchmark-result":
        provenance = evidenceRow.get("provenance")
        if provenance in ("mirrored", "pending"):
            return None

    # Null-on-derank: verifier-attestation rows tied to a now-sub-4-star verifier
    # evaluate to None (excluded from the sum, NOT zero in dedup math). The
    # CLI writes `verifierActiveRank: false` on rows whose attesting verifier
    # has lost rank; legacy field name `derank: true` also honored.
    if evidenceType == "verifier-attestation":
        if evidenceRow.get("verifierActiveRank") is False:
            return None
        if evidenceRow.get("derank") is True:
            return None

    weight = TYPE_WEIGHTS.get(evidenceType, 0.0)
    if weight == 0.0:
        return 0.0

    rawMagnitude = _rawMagnitudeForType(evidenceType, evidenceRow, genericSkillMap)

    # Per-type cap (applied row-level for non-stackable types)
    cap = TYPE_CAPS.get(evidenceType)
    if cap is not None:
        rawMagnitude = min(rawMagnitude, cap)

    freshness = _freshnessFactor(evidenceRow, evidenceType)

    # NOTE: mothership discount for github-stars-own is already baked into
    # _rawMagnitudeForType (divides by min(skillCountInRepo, 4)). Do NOT
    # apply it again here — that would double-discount.

    # Creator multiplier and engagement ratio for social-signal (RFC §2.11)
    creatorMult = 1.0
    engagementRatio = 1.0
    if evidenceType == "social-signal":
        creatorMult = float(evidenceRow.get("creatorMultiplier", 1.0))
        if "engagementRatio" in evidenceRow:
            # Pre-stored value — back-compat path.
            engagementRatio = float(evidenceRow["engagementRatio"])
        elif "likes" in evidenceRow or "comments" in evidenceRow:
            # Compute from raw fields when present (RFC §2.11).
            # engagement_ratio = min(1.5, (likes + comments*5) / views * 50)
            rawViews = float(evidenceRow.get("views", 0) or 0)
            if rawViews > 0:
                rawLikes = float(evidenceRow.get("likes", 0) or 0)
                rawComments = float(evidenceRow.get("comments", 0) or 0)
                engagementRatio = min(1.5, (rawLikes + rawComments * 5.0) / rawViews * 50.0)
            # If views zero/absent, fall through leaving engagementRatio=1.0.
        # If neither stored ratio nor raw fields are present, fall through to 1.0.

    score = rawMagnitude * weight * freshness * creatorMult * engagementRatio
    return score


def _rawMagnitudeForType(
    evidenceType: str,
    row: dict,
    genericSkillMap: Optional[dict],
) -> float:
    """Compute pre-weight, pre-cap raw magnitude per RFC §2.1 type table."""
    if evidenceType == "fusion-recipe":
        # Origins may be (a) explicit `origins` list, (b) `gradedOriginCount`
        # number, or (c) derived from a parent skill's suiteComponents.
        origins = row.get("origins")
        if isinstance(origins, list):
            graded = _gradedOriginCount(origins, genericSkillMap)
        else:
            graded = int(row.get("gradedOriginCount", row.get("origins", 0)) or 0)
        return _fusionRecipeMagnitude(graded)

    if evidenceType == "github-stars-own":
        stars = float(row.get("stars", 0) or 0)
        skillCount = int(row.get("skillCountInRepo", 1) or 1)
        # RFC §2.3: min(200, stars/1000) / mothership_divisor
        # mothership_divisor = min(skill_count_in_repo, 4)  — caps at 4 per RFC
        divisor = min(skillCount, 4)
        return min(200.0, stars / 1000.0) / max(1, divisor)

    if evidenceType == "proxy-containment":
        externalStars = float(row.get("externalStars", 0) or 0)
        if externalStars < 10000:
            return 0.0
        # RFC §2.4: (external_stars/1000) × 0.8
        return (externalStars / 1000.0) * 0.8

    if evidenceType == "verifier-attestation":
        verifiers = int(row.get("verifiers", 1) or 1)
        return 30.0 * verifiers

    if evidenceType == "benchmark-result":
        return float(row.get("percentile", 0) or 0)

    if evidenceType == "arxiv":
        citations = float(row.get("citations", 0) or 0)
        # RFC §2.6: citations/5
        return citations / 5.0

    if evidenceType == "peer-review":
        reviewers = int(row.get("reviewers", 1) or 1)
        return 25.0 * reviewers

    if evidenceType == "repo-own":
        commits = float(row.get("commits", 0) or 0)
        contributors = int(row.get("contributors", 0) or 0)
        return commits / 200.0 + contributors * contributors * 2.0

    if evidenceType == "self-attestation":
        return 10.0

    if evidenceType == "social-signal":
        # RFC §2.10: raw base = log10(views) × 8.
        # creator_mult and engagement_ratio are applied by the caller
        # (computeArtifactScoreOrNone / TM inspect path) so they must NOT
        # be baked in here — doing so would double-apply them.
        views = float(row.get("views", 0) or 0)
        if views < 1000:
            return 0.0
        return math.log10(views) * 8.0

    return 0.0


# ---------------------------------------------------------------------------
# Same-source dedup, plateau, social-signal same-creator dedup
# ---------------------------------------------------------------------------


def _dedupeSameSource(rows: list[dict]) -> list[dict]:
    """Collapse evidence rows pointing at the same canonical URL into one.

    Highest pre-weight magnitude wins. Source URLs are preserved on the merged
    entry as `_collapsedSources`.
    """
    if not rows:
        return []
    seen: dict[tuple[str, str], int] = {}
    out: list[dict] = []
    for row in rows:
        url = (
            _canonicalUrl(row.get("source"))
            or _canonicalUrl(row.get("url"))
            or _canonicalUrl(row.get("sourceUrl"))
        )
        if url is None:
            out.append(row)
            continue
        key = (_typeOf(row) or "", url)  # dedup within type
        if key in seen:
            existingIdx = seen[key]
            existing = out[existingIdx]
            if _rowComparableMagnitude(row) > _rowComparableMagnitude(existing):
                merged = dict(row)
                sources = list(existing.get("_collapsedSources") or [])
                src = existing.get("source") or existing.get("url")
                if src:
                    sources.append(src)
                merged["_collapsedSources"] = sources
                out[existingIdx] = merged
        else:
            out.append(row)
            seen[key] = len(out) - 1
    return out


def _rowComparableMagnitude(row: dict) -> float:
    """A cheap comparator for same-source dedup tie-breaking."""
    t = _typeOf(row)
    if t == "github-stars-own":
        return float(row.get("stars", 0) or 0)
    if t == "proxy-containment":
        return float(row.get("externalStars", 0) or 0)
    if t == "verifier-attestation":
        return float(row.get("verifiers", 1) or 1)
    if t == "benchmark-result":
        return float(row.get("percentile", 0) or 0)
    if t == "arxiv":
        return float(row.get("citations", 0) or 0)
    if t == "peer-review":
        return float(row.get("reviewers", 1) or 1)
    if t == "repo-own":
        return float(row.get("commits", 0) or 0) + float(row.get("contributors", 0) or 0) * 100
    if t == "social-signal":
        return float(row.get("views", 0) or 0)
    return 0.0


_PLATEAU_FACTORS = [1.0, 0.5, 0.25]

# Per-type plateau configs: (factors_list, max_rows)
_PLATEAU_CONFIG: dict = {
    "proxy-containment":    ([1.0],                       1),
    "verifier-attestation": ([1.0, 0.85, 0.70],           5),
    "arxiv":                ([1.0, 0.5, 0.25, 0.125],     4),
    "peer-review":          ([1.0, 0.5, 0.25],            3),
    "social-signal":        ([1.0, 0.5, 0.25],            3),
    "repo-own":             ([1.0, 0.5, 0.25],            3),
    "github-stars-own":     ([1.0],                       1),
    "self-attestation":     ([1.0],                       1),
    "benchmark-result":     ([1.0],                       1),
    "fusion-recipe":        ([1.0],                       1),
}


def _applyPlateauAndCreatorDedup(
    rowsWithScores: list[tuple[dict, Optional[float]]],
) -> list[tuple[dict, Optional[float]]]:
    """Apply per-type plateau for stackable types (RFC §2.1).

    Each type in _PLATEAU_CONFIG is capped at maxRows rows; rows beyond the
    cap get score 0.0.  social-signal also deduplicates by creator within
    its plateau pass.

    Rows with score=None (null-on-derank) are passed through unchanged.
    """
    byType: dict[str, list[int]] = {}
    for idx, (row, _score) in enumerate(rowsWithScores):
        t = _typeOf(row) or ""
        byType.setdefault(t, []).append(idx)

    out: list[tuple[dict, Optional[float]]] = list(rowsWithScores)

    for t, indices in byType.items():
        cfg = _PLATEAU_CONFIG.get(t)
        if cfg is None:
            continue
        plateauFactors, maxRows = cfg

        if t == "social-signal":
            # Per-creator dedup within the plateau pass
            byCreator: dict[str, list[int]] = {}
            for i in indices:
                creator = (
                    rowsWithScores[i][0].get("creator")
                    or rowsWithScores[i][0].get("creatorId")
                    or "_unknown"
                )
                byCreator.setdefault(creator, []).append(i)
            for creator, creatorIndices in byCreator.items():
                scored = [(i, rowsWithScores[i][1]) for i in creatorIndices]
                scored.sort(key=lambda x: (x[1] is None, -(x[1] or 0.0)))
                for rank, (i, score) in enumerate(scored):
                    if score is None:
                        continue
                    if rank >= maxRows:
                        out[i] = (rowsWithScores[i][0], 0.0)
                    else:
                        factor = plateauFactors[rank] if rank < len(plateauFactors) else plateauFactors[-1]
                        out[i] = (rowsWithScores[i][0], score * factor)
        else:
            scored = [(i, rowsWithScores[i][1]) for i in indices]
            scored.sort(key=lambda x: (x[1] is None, -(x[1] or 0.0)))
            for rank, (i, score) in enumerate(scored):
                if score is None:
                    continue
                if rank >= maxRows:
                    out[i] = (rowsWithScores[i][0], 0.0)
                else:
                    factor = plateauFactors[rank] if rank < len(plateauFactors) else plateauFactors[-1]
                    out[i] = (rowsWithScores[i][0], score * factor)
    return out


# ---------------------------------------------------------------------------
# Public API: enforceAntiAutoMint
# ---------------------------------------------------------------------------


def enforceAntiAutoMint(skill: dict) -> list[dict]:
    """Return the skill's evidence list with phantom rows removed (RFC §10.14).

    A phantom row is one that would be implied by `suiteComponents` or
    `fusionRecipes` but is NOT physically present in the original evidence[].
    Only the fusion-recipe row itself is auto-derivable per §10.8.

    Returns a NEW list (does not mutate skill).
    """
    rows = list(skill.get("evidence") or [])
    cleaned: list[dict] = []
    for row in rows:
        if row.get("_phantom") is True:
            continue
        if row.get("phantom") is True:
            continue
        if row.get("autoMinted") is True and _typeOf(row) != "fusion-recipe":
            continue
        cleaned.append(row)
    return cleaned


# ---------------------------------------------------------------------------
# Public API: computeTrustMagnitude
# ---------------------------------------------------------------------------


def computeTrustMagnitude(
    skill: dict,
    genericSkillMap: Optional[dict] = None,
    namedSkillMap: Optional[dict] = None,
) -> float:
    """Compute the skill's Trust Magnitude (RFC §3, v2 inheritance contract).

    Sum of artifact_score for every evidence row in the *effective pool*,
    after:
    - effective-pool resolution: own evidence union inherited generic
      evidence (deduped by source) per `inherited_evidence`. The inherit
      multiplier (`EVIDENCE_TYPE_LAYER_CONTRACT[type].inheritMultiplier`) is
      applied at sum-time only to rows that come in via inheritance, not
      during pool resolution.
    - anti-auto-mint (RFC §10.14)
    - same-source dedup (RFC §5.2)
    - per-type plateau (proxy-containment, peer-review, social-signal)
    - null-on-derank exclusion (RFC §5.6)
    - per-type cap (already applied in computeArtifactScoreOrNone)
    - social-signal hard A-cap (sum of social-signal contributions <= 80)
    """
    del namedSkillMap  # reserved for future cross-skill rules

    # 1. Resolve the effective pool (own union inherited).
    pool = _effectivePool(skill, genericSkillMap)

    # 2. Anti-auto-mint over the merged pool.
    evidence = enforceAntiAutoMint({"evidence": pool})

    # 3. Same-source dedup, preserving row layer.
    deduped = _dedupeSameSource(evidence)

    # 4. Auto-mint fusion-recipe row from suiteComponents if missing (RFC §10.8).
    suiteComponents = skill.get("suiteComponents") or []
    hasFusionRow = any(_typeOf(r) == "fusion-recipe" for r in deduped)
    if suiteComponents and not hasFusionRow:
        # Auto-derived fusion-recipe lives at the skill's own layer.
        deduped = list(deduped) + [{
            "type": "fusion-recipe",
            "origins": list(suiteComponents),
            "_autoDerived": True,
            "layer": _ownLayerOf(skill),
        }]

    # 5. Per-row artifact score, with inherit multiplier applied at sum-time.
    rowsWithScores: list[tuple[dict, Optional[float]]] = []
    for row in deduped:
        baseScore = computeArtifactScoreOrNone(row, genericSkillMap)
        if baseScore is None:
            rowsWithScores.append((row, None))
            continue
        mult = _inheritMultiplierFor(row, skill)
        rowsWithScores.append((row, baseScore * mult))

    # 6. Plateau / per-creator dedup, then social cap + sum.
    rowsWithScores = _applyPlateauAndCreatorDedup(rowsWithScores)

    socialTotal = 0.0
    nonSocialTotal = 0.0
    for row, score in rowsWithScores:
        if score is None:
            continue
        if _typeOf(row) == "social-signal":
            socialTotal += score
        else:
            nonSocialTotal += score
    socialTotal = min(socialTotal, 80.0)
    return nonSocialTotal + socialTotal


def computeTrustMagnitudeByType(
    skill: dict,
    genericSkillMap: Optional[dict] = None,
    namedSkillMap: Optional[dict] = None,
) -> dict:
    """Return {evidenceTypeId: contribution} so sum(values) ~= computeTrustMagnitude.

    Mirrors computeTrustMagnitude's pipeline (effective pool, anti-auto-mint,
    same-source dedup, fusion-recipe auto-derive, plateau, social-signal A-cap)
    but partitions the total by evidence type. After computing raw per-type
    totals, scales all entries proportionally so dict-sum equals the aggregate
    TM within 0.02. Each value is rounded to 2 decimals. Missing types simply
    don't appear (frontend treats absent as 0).
    """
    del namedSkillMap  # reserved for future cross-skill rules

    # 1-2-3: pool resolution, anti-auto-mint, dedup (same as computeTrustMagnitude).
    pool = _effectivePool(skill, genericSkillMap)
    evidence = enforceAntiAutoMint({"evidence": pool})
    deduped = _dedupeSameSource(evidence)

    # 4: auto-mint fusion-recipe if needed.
    suiteComponents = skill.get("suiteComponents") or []
    hasFusionRow = any(_typeOf(r) == "fusion-recipe" for r in deduped)
    if suiteComponents and not hasFusionRow:
        deduped = list(deduped) + [{
            "type": "fusion-recipe",
            "origins": list(suiteComponents),
            "_autoDerived": True,
            "layer": _ownLayerOf(skill),
        }]

    # 5: per-row scoring with inherit multiplier.
    rowsWithScores: list[tuple[dict, Optional[float]]] = []
    for row in deduped:
        baseScore = computeArtifactScoreOrNone(row, genericSkillMap)
        if baseScore is None:
            rowsWithScores.append((row, None))
            continue
        mult = _inheritMultiplierFor(row, skill)
        rowsWithScores.append((row, baseScore * mult))

    # 6: plateau / per-creator dedup.
    rowsWithScores = _applyPlateauAndCreatorDedup(rowsWithScores)

    # 7: partition by type, applying social-signal A-cap proportionally.
    perType: dict[str, float] = {}
    socialTotal = 0.0
    for row, score in rowsWithScores:
        if score is None:
            continue
        t = _typeOf(row) or "unknown"
        if t == "social-signal":
            socialTotal += score
        perType[t] = perType.get(t, 0.0) + score

    # Social-signal A-cap: scale only the social-signal bucket to the cap.
    if "social-signal" in perType and socialTotal > 80.0:
        perType["social-signal"] = 80.0

    aggregate = computeTrustMagnitude(skill, genericSkillMap)
    rawSum = sum(perType.values())

    # Scale proportionally so dict-sum matches aggregate within 0.02.
    if rawSum > 0 and abs(rawSum - aggregate) > 0.02:
        factor = aggregate / rawSum
        perType = {t: v * factor for t, v in perType.items()}

    # Round to 2 decimals; drop zero buckets.
    out = {t: round(v, 2) for t, v in perType.items() if round(v, 2) != 0.0}
    return out


def _effectivePool(skill: dict, genericSkillMap: Optional[dict]) -> list[dict]:
    """Resolve the merged own + inherited evidence pool for a skill.

    Generic skills return their own evidence (no parent to inherit from).
    Named skills (those with `genericSkillRef`) walk the parent generic and
    merge in any generic-layer rows that aren't already shadowed by their own
    same-source rows. Each row carries an explicit `layer` field after this
    pass — own rows are stamped with the skill's own layer, inherited rows
    keep their generic layer.
    """
    ownLayer = _ownLayerOf(skill)
    ownRows: list[dict] = []
    for row in skill.get("evidence") or []:
        # Stamp own-layer (preserve any explicit `layer` already set).
        stamped = dict(row)
        stamped.setdefault("layer", ownLayer)
        ownRows.append(stamped)

    if ownLayer == "generic" or not skill.get("genericSkillRef"):
        return ownRows

    generic = None
    if genericSkillMap is not None:
        generic = genericSkillMap.get(skill.get("genericSkillRef"))

    # `inherited_evidence` returns own-first then generic, deduped by source.
    merged = inherited_evidence({"evidence": ownRows}, generic)

    # Stamp any inherited rows that aren't already layer-tagged with "generic".
    out: list[dict] = []
    ownSources = {r.get("source") for r in ownRows if r.get("source")}
    for row in merged:
        if row.get("source") in ownSources:
            out.append(row)
            continue
        stamped = dict(row)
        stamped.setdefault("layer", "generic")
        out.append(stamped)
    return out


# ---------------------------------------------------------------------------
# Public API: computeOverallTrustGrade
# ---------------------------------------------------------------------------


def computeOverallTrustGrade(
    trustMagnitude: float,
    distinctTypes: int,
    hasNonSelfProducible: bool,
) -> str:
    """Map (TM, distinctTypes, hasNonSelf) -> grade letter (RFC §4).

    Returns one of "S", "A", "B", "C", "ungraded".

    Diversity gate:
    - S: TM >= 250 AND distinctTypes >= 3 AND hasNonSelfProducible.
    - A: TM >= 100.
    - B: TM >= 50.
    - C: TM >= 20.
    - ungraded: TM < 20.
    """
    if trustMagnitude >= GRADE_S_FLOOR and distinctTypes >= 3 and hasNonSelfProducible:
        return "S"
    if trustMagnitude >= GRADE_A_FLOOR:
        return "A"
    if trustMagnitude >= GRADE_B_FLOOR:
        return "B"
    if trustMagnitude >= GRADE_C_FLOOR:
        return "C"
    return "ungraded"


def computeOverallTrustGradeFromSkill(
    skill: dict,
    genericSkillMap: Optional[dict] = None,
    namedSkillMap: Optional[dict] = None,
) -> str:
    """Convenience: compute TM and grade together from a skill dict."""
    tm = computeTrustMagnitude(skill, genericSkillMap, namedSkillMap)
    distinctTypes = _countDistinctEvidenceTypes(skill)
    hasNonSelf = _hasNonSelfProducible(skill)
    return computeOverallTrustGrade(tm, distinctTypes, hasNonSelf)


def computeRowArtifactScores(
    skill: dict,
    genericSkillMap: Optional[dict] = None,
) -> list:
    """Return [(row_dict, artifact_score), ...] for every on-disk evidence row.

    Applies the same effective-pool, anti-auto-mint, dedup, and plateau logic
    as computeTrustMagnitude, but returns per-row scores for grade backfill.
    Auto-derived rows (_autoDerived: True) are flagged so callers can skip them
    during write-back. Null-on-derank verifier rows are included with score=0.0.
    """
    pool = _effectivePool(skill, genericSkillMap)
    evidence = enforceAntiAutoMint({"evidence": pool})
    deduped = _dedupeSameSource(evidence)

    suiteComponents = skill.get("suiteComponents") or []
    hasFusionRow = any(_typeOf(r) == "fusion-recipe" for r in deduped)
    if suiteComponents and not hasFusionRow:
        deduped = list(deduped) + [{
            "type": "fusion-recipe",
            "origins": list(suiteComponents),
            "_autoDerived": True,
            "layer": _ownLayerOf(skill),
        }]

    rowsWithScores: list = []
    for row in deduped:
        baseScore = computeArtifactScoreOrNone(row, genericSkillMap)
        if baseScore is None:
            rowsWithScores.append((row, 0.0))
            continue
        mult = _inheritMultiplierFor(row, skill)
        rowsWithScores.append((row, baseScore * mult))

    rowsWithScores = _applyPlateauAndCreatorDedup(rowsWithScores)
    return rowsWithScores


def _countDistinctEvidenceTypes(skill: dict) -> int:
    evidence = enforceAntiAutoMint(skill)
    deduped = _dedupeSameSource(evidence)
    types: set[str] = set()
    for row in deduped:
        t = _typeOf(row)
        if t:
            types.add(t)
    if skill.get("suiteComponents") and "fusion-recipe" not in types:
        types.add("fusion-recipe")
    return len(types)


def _hasNonSelfProducible(skill: dict) -> bool:
    evidence = enforceAntiAutoMint(skill)
    deduped = _dedupeSameSource(evidence)
    for row in deduped:
        t = _typeOf(row)
        if t and t not in SELF_PRODUCIBLE_TYPES:
            return True
    return False


# ---------------------------------------------------------------------------
# Apex gate predicates (delta §B - six active + two OFF)
# ---------------------------------------------------------------------------


def checkAGradedOriginsGte5(
    skill: dict,
    genericSkillMap: Optional[dict] = None,
    namedSkillMap: Optional[dict] = None,
) -> bool:
    """>=5 distinct A-or-S-graded origin skills, walking the fusion graph + suite components.

    Strict semantics (issue #729 founder ruling): bare evidence rows do NOT count
    by themselves. Only skill IDs reachable via:
      - Source A: fusion-recipe role='origin' rows in skill.evidence[]
      - Source B: skill.suiteComponents entries (counted as fusion structure)

    For each deduplicated origin skill ID, looks up its overallTrustGrade from
    namedSkillMap (preferred) or genericSkillMap. Returns True if >= 5 origins
    resolve to grade 'S' or 'A'.

    Conservative fallback: if both maps are None, returns False (can't verify).
    Unresolvable origin IDs are skipped (not counted).
    """
    if namedSkillMap is None and genericSkillMap is None:
        return False

    # Source A: fusion-recipe role='origin' rows (exclude role='variant')
    fusionOrigins: set[str] = set()
    for row in skill.get("evidence") or []:
        if _typeOf(row) != "fusion-recipe":
            continue
        for entry in row.get("origins") or []:
            if isinstance(entry, dict):
                originId = entry.get("id") or entry.get("skillId")
                inlineRole = entry.get("role")
            else:
                originId = entry
                inlineRole = None
            if not originId:
                continue
            # Resolve role from inline hint or genericSkillMap
            role = inlineRole
            if role is None and genericSkillMap is not None:
                role = (genericSkillMap.get(originId) or {}).get("role")
            if role == "variant":
                continue
            fusionOrigins.add(originId)

    # Source B: suiteComponents entries
    suiteOrigins: set[str] = set(skill.get("suiteComponents") or [])

    # Deduplicated union
    allOrigins = fusionOrigins | suiteOrigins

    if not allOrigins:
        return False

    # Count origins with overallTrustGrade in {S, A}
    count = 0
    for originId in allOrigins:
        grade = None
        # Prefer namedSkillMap for overallTrustGrade lookup
        if namedSkillMap is not None:
            node = namedSkillMap.get(originId)
            if node is not None:
                grade = node.get("overallTrustGrade") or node.get("overallGrade") or node.get("grade")
        # Fall back to genericSkillMap
        if grade is None and genericSkillMap is not None:
            node = genericSkillMap.get(originId)
            if node is not None:
                grade = node.get("overallTrustGrade") or node.get("overallGrade") or node.get("grade")
        # Unresolvable: skip (do not count)
        if grade is None:
            continue
        if grade in ("S", "A"):
            count += 1

    return count >= APEX_AGRADED_ORIGINS_MIN


def checkSourceTenureDaysGte180AorS(skill: dict, now: Optional[datetime.datetime] = None) -> bool:
    """A/S rows: max source age across A/S rows must be >= 180 days (delta §B).

    - Compute post-weight magnitude per row first to determine effective A/S.
    - For each A/S row read `sourceStartedAt` (ISO date, new from I1).
    - Take max source age across A/S rows. True if max age >= 180 days.
    - If no A/S rows exist, return False.
    - If `sourceStartedAt` absent on an A/S row, treat as age=0 days.
    """
    nowDt = now or _utcNow()
    evidence = enforceAntiAutoMint(skill)
    deduped = _dedupeSameSource(evidence)
    aOrSAges: list[int] = []
    for row in deduped:
        g = _grade(row)
        if g not in ("S", "A"):
            continue
        startedAt = _parseIso(row.get("sourceStartedAt"))
        if startedAt is None:
            aOrSAges.append(0)
        else:
            aOrSAges.append((nowDt - startedAt).days)
    if not aOrSAges:
        return False
    return max(aOrSAges) >= APEX_TENURE_DAYS_MIN


def checkDirectNestedSuiteGte1(skill: dict, genericSkillMap: Optional[dict] = None) -> bool:
    """>=1 direct suiteComponents that itself has non-empty suiteComponents.

    Structural predicate; reads frontmatter only (no inference).
    """
    components = skill.get("suiteComponents") or []
    if not components:
        return False
    if genericSkillMap is None:
        return False
    for cid in components:
        comp = genericSkillMap.get(cid) or {}
        if comp.get("suiteComponents"):
            return True
    return False


def checkDepth2OnlyReachableGte1(
    skill: dict,
    registryState: Optional[dict] = None,
) -> bool:
    """Walks fusion graph (role='origin' edges + suiteComponents).

    Counts skills reachable at depth-2 via fusion-recipe origins or
    suiteComponents. Must be >= 1.

    `registryState` carries `genericSkillMap` and (optionally) `namedSkillMap`.
    Suite-based ultimates have no `fusion-recipe` rows; their fusion graph IS
    the `suiteComponents` array, so we walk both fusion-recipe origins AND
    suiteComponents at every depth (RFC §11.12.3, founder ruling per #746).

    A node is counted as "depth-2 reachable" if it sits two hops from `skill`
    via the union graph; nodes at depth-1 are excluded only when `skill` itself
    appears among them (cycle guard). Per Marco's #746 ruling, suite ultimates
    whose nested components also appear at depth-1 (a flat redundancy that
    suite authors typically include) still qualify on the basis of nested
    structural depth.
    """
    if registryState is None:
        return False
    genericSkillMap = registryState.get("genericSkillMap") or {}
    namedSkillMap = registryState.get("namedSkillMap") or {}
    skillId = skill.get("id") or skill.get("skillId")
    if not skillId:
        return False

    # Depth-1 set: direct fusion-recipe origins UNION suiteComponents.
    depth1 = set(
        _fusionAndSuiteOriginIds(skill, genericSkillMap, namedSkillMap)
    )
    if not depth1:
        return False

    depth2: set[str] = set()
    for d1id in depth1:
        # Look up depth-1 node in named map first (suiteComponent IDs like
        # "garrytan/garrytan" live there), then fall back to the generic map
        # for fusion-recipe origins.
        d1node = (
            namedSkillMap.get(d1id)
            or genericSkillMap.get(d1id)
            or {}
        )
        d2 = _fusionAndSuiteOriginIds(d1node, genericSkillMap, namedSkillMap)
        for d2id in d2:
            if d2id == skillId:
                continue
            depth2.add(d2id)
    return len(depth2) >= 1


def _fusionOriginIds(skill: dict, genericSkillMap: dict) -> list[str]:
    """Resolve fusion-recipe origins from a skill, role='variant' excluded.

    Suite components are excluded - only fusion-recipe rows in evidence count.
    """
    out: list[str] = []
    for row in skill.get("evidence") or []:
        if _typeOf(row) != "fusion-recipe":
            continue
        for entry in row.get("origins") or []:
            if isinstance(entry, dict):
                originId = entry.get("id") or entry.get("skillId")
                inlineRole = entry.get("role")
            else:
                originId = entry
                inlineRole = None
            if not originId:
                continue
            node = genericSkillMap.get(originId) or {}
            role = inlineRole or node.get("role")
            if role == "variant":
                continue
            out.append(originId)
    return out


def _fusionAndSuiteOriginIds(
    skill: dict,
    genericSkillMap: dict,
    namedSkillMap: Optional[dict] = None,
) -> list[str]:
    """Union of fusion-recipe origins and suiteComponents.

    Suite-based ultimates (e.g. `garrytan/gstack`) carry no `fusion-recipe`
    evidence row; their fusion graph IS the `suiteComponents` array. Per
    RFC §11.12.3 founder ruling (#746), apex depth walks must include both.
    """
    del namedSkillMap  # reserved — suiteComponent IDs are looked up by caller
    out: list[str] = list(_fusionOriginIds(skill, genericSkillMap))
    seen = set(out)
    for cid in skill.get("suiteComponents") or []:
        if not cid or cid in seen:
            continue
        seen.add(cid)
        out.append(cid)
    return out


def checkOverallGradeS(skill: dict, genericSkillMap: Optional[dict] = None) -> bool:
    """Apex Overall Trust Grade must equal S (under strict-evidence reading)."""
    return computeOverallTrustGradeFromSkill(skill, genericSkillMap) == "S"


def checkApexPromotionPrSigned(skill: dict) -> bool:
    """The skill carries an `apexPromotionPr.signed=true` annotation.

    Reads `skill.apexGateStatus.apexPromotionPrSigned` defensively (I1 schema).
    """
    status = skill.get("apexGateStatus") or {}
    if status.get("apexPromotionPrSigned") is True:
        return True
    apexPr = skill.get("apexPromotionPr") or {}
    return bool(apexPr.get("signed"))


def checkCrossOrgVerifier(
    skill: dict,
    registryState: Optional[dict] = None,
) -> Optional[bool]:
    """Feature-flagged OFF (delta §B). Returns None until 2026-Q4 review."""
    if not ENABLE_CROSS_ORG_VERIFIER:
        return None
    del registryState
    orgs: set[str] = set()
    for row in skill.get("evidence") or []:
        if _typeOf(row) != "verifier-attestation":
            continue
        for cosigner in row.get("cosigners") or []:
            org = cosigner.get("org") if isinstance(cosigner, dict) else None
            if org:
                orgs.add(org)
    return len(orgs) >= 2


def checkSystemWideCap(registryState: Optional[dict] = None) -> Optional[bool]:
    """Feature-flagged OFF (delta §B). CI (I4) handles the hard cap."""
    if not ENABLE_SYSTEM_WIDE_CAP:
        return None
    if registryState is None:
        return None
    apexCount = registryState.get("systemWideApexCount", 0)
    return apexCount < 5


# ---------------------------------------------------------------------------
# Public API: passesSuiteApexGate
# ---------------------------------------------------------------------------


def passesSuiteApexGate(
    skill: dict,
    registryState: Optional[dict] = None,
) -> dict[str, Optional[bool]]:
    """Run the six active apex predicates plus the two OFF scaffolds.

    Returns a dict mapping predicate name -> True/False/None. None means the
    predicate is feature-flagged OFF (skipped, neither passing nor failing).

    The public boolean "is apex" is:
        all(v is True for v in d.values() if v is not None)
    """
    state = registryState or {}
    genericSkillMap = state.get("genericSkillMap")
    namedSkillMap = state.get("namedSkillMap")
    return {
        "aGradedOriginsGte5": checkAGradedOriginsGte5(skill, genericSkillMap, namedSkillMap),
        "sourceTenureDaysGte180AorS": checkSourceTenureDaysGte180AorS(skill),
        "directNestedSuiteGte1": checkDirectNestedSuiteGte1(skill, genericSkillMap),
        "depth2OnlyReachableGte1": checkDepth2OnlyReachableGte1(skill, state),
        "overallGradeS": checkOverallGradeS(skill, genericSkillMap),
        "apexPromotionPrSigned": checkApexPromotionPrSigned(skill),
        "crossOrgVerifier": checkCrossOrgVerifier(skill, state),
        "systemWideCap": checkSystemWideCap(state),
    }


def isSuiteApex(passResult: dict[str, Optional[bool]]) -> bool:
    """True iff every active (non-None) predicate passes."""
    return all(v is True for v in passResult.values() if v is not None)


def checkUniqueImpossibleGate(
    skill: dict,
    registryState: Optional[dict] = None,
) -> dict[str, Optional[bool]]:
    """PROVISIONAL 6★ Unique Impossible gate (Yggdrasil II decision log Q9).

    The Unique-branch analogue of the Suite Apex gate. It is the Apex active-6
    predicate set **MINUS** ``directNestedSuiteGte1`` — a Unique skill is
    standalone, so the nested-suite structural requirement does not apply. That
    leaves five active predicates. For shape parity with
    :func:`passesSuiteApexGate`, the two feature-flagged-OFF scaffolds
    (``crossOrgVerifier``, ``systemWideCap``) are still included as ``None``.

    ◇ PROVISIONAL — formal ratification is deferred to a follow-up RFC
    (Yggdrasil III candidate, per decision log Q9). A passing result is NOT yet
    a canonical promotion authorization; treat it as advisory only.

    Returns a dict mapping predicate name -> True/False/None (None = skipped).
    The public boolean "is unique-impossible" mirrors :func:`isSuiteApex`::

        all(v is True for v in d.values() if v is not None)
    """
    state = registryState or {}
    genericSkillMap = state.get("genericSkillMap")
    namedSkillMap = state.get("namedSkillMap")
    return {
        "aGradedOriginsGte5": checkAGradedOriginsGte5(skill, genericSkillMap, namedSkillMap),
        "sourceTenureDaysGte180AorS": checkSourceTenureDaysGte180AorS(skill),
        # directNestedSuiteGte1 intentionally omitted — the defining difference
        # between Unique Impossible and Suite Apex (no nested-suite requirement).
        "depth2OnlyReachableGte1": checkDepth2OnlyReachableGte1(skill, state),
        "overallGradeS": checkOverallGradeS(skill, genericSkillMap),
        "apexPromotionPrSigned": checkApexPromotionPrSigned(skill),
        "crossOrgVerifier": checkCrossOrgVerifier(skill, state),
        "systemWideCap": checkSystemWideCap(state),
    }



# ---------------------------------------------------------------------------
# Public API: explainTrustMagnitude
# ---------------------------------------------------------------------------


def explainTrustMagnitude(
    skill: dict,
    genericSkillMap: Optional[dict] = None,
    namedSkillMap: Optional[dict] = None,
) -> str:
    """Return a human-readable explanation of how Trust Magnitude was computed.

    Mirrors computeTrustMagnitude step-by-step and annotates each row with
    its multiplier chain, inherit multiplier (when != 1.0), and contribution.

    Rows where inheritMultiplier != 1.0 are marked with a '^ inherited from
    <genericRef>' annotation so the caller can visually distinguish them from
    own-layer rows.

    Returns a plain-text string (no ANSI; suitable for testing and piping).
    """
    del namedSkillMap  # reserved — same convention as computeTrustMagnitude

    genericRef = skill.get("genericSkillRef") or ""

    # Step 1: effective pool
    pool = _effectivePool(skill, genericSkillMap)

    # Step 2: anti-auto-mint
    evidence = enforceAntiAutoMint({"evidence": pool})

    # Step 3: same-source dedup
    deduped = _dedupeSameSource(evidence)

    # Step 4: auto-derive fusion-recipe from suiteComponents if absent
    suiteComponents = skill.get("suiteComponents") or []
    hasFusionRow = any(_typeOf(r) == "fusion-recipe" for r in deduped)
    if suiteComponents and not hasFusionRow:
        deduped = list(deduped) + [{
            "type": "fusion-recipe",
            "origins": list(suiteComponents),
            "_autoDerived": True,
            "layer": _ownLayerOf(skill),
        }]

    # Step 5: per-row scores with inherit multiplier
    rowsWithScores: list[tuple[dict, Optional[float]]] = []
    for row in deduped:
        baseScore = computeArtifactScoreOrNone(row, genericSkillMap)
        if baseScore is None:
            rowsWithScores.append((row, None))
            continue
        mult = _inheritMultiplierFor(row, skill)
        rowsWithScores.append((row, baseScore * mult))

    # Step 6: plateau / per-creator dedup
    rowsWithScores = _applyPlateauAndCreatorDedup(rowsWithScores)

    # Step 7: social cap + total
    socialTotal = 0.0
    nonSocialTotal = 0.0
    for row, score in rowsWithScores:
        if score is None:
            continue
        if _typeOf(row) == "social-signal":
            socialTotal += score
        else:
            nonSocialTotal += score
    socialCapped = min(socialTotal, 80.0)
    totalTM = nonSocialTotal + socialCapped

    # Derive grade
    distinctTypes = len({
        _typeOf(r) for r, _ in rowsWithScores if _typeOf(r)
    })
    hasNonSelf = any(
        _typeOf(r) not in SELF_PRODUCIBLE_TYPES
        for r, s in rowsWithScores
        if _typeOf(r) and s is not None and s > 0
    )
    grade = computeOverallTrustGrade(totalTM, distinctTypes, hasNonSelf)

    # Build the explanation string
    lines: list[str] = []
    lines.append(f"Trust Magnitude: {totalTM:.2f} (grade: {grade})")
    lines.append("")
    lines.append(f"Effective pool ({len(rowsWithScores)} rows):")

    for row, finalScore in rowsWithScores:
        rowType = _typeOf(row) or "unknown"
        source = (
            row.get("source")
            or row.get("url")
            or row.get("sourceUrl")
            or "(no source)"
        )
        lines.append(f"  {rowType}: {source}")

        # Recompute intermediate factors for display
        baseScore = computeArtifactScoreOrNone(row, genericSkillMap)
        if baseScore is None:
            lines.append("    null-on-derank (verifier deranked — excluded from sum)")
            lines.append("")
            continue

        weight = TYPE_WEIGHTS.get(rowType, 0.0)
        freshness = _freshnessFactor(row, rowType)

        rawMag = _rawMagnitudeForType(rowType, row, genericSkillMap)
        cap = TYPE_CAPS.get(rowType)
        if cap is not None:
            rawMag = min(rawMag, cap)

        # Creator multiplier + engagement ratio (social-signal only)
        creatorMult = 1.0
        engagementRatio = 1.0
        if rowType == "social-signal":
            creatorMult = float(row.get("creatorMultiplier", 1.0))
            if "engagementRatio" in row:
                engagementRatio = float(row["engagementRatio"])
            elif "likes" in row or "comments" in row:
                rawViews = float(row.get("views", 0) or 0)
                if rawViews > 0:
                    rawLikes = float(row.get("likes", 0) or 0)
                    rawComments = float(row.get("comments", 0) or 0)
                    engagementRatio = min(1.5, (rawLikes + rawComments * 5.0) / rawViews * 50.0)

        inheritMult = _inheritMultiplierFor(row, skill)

        # Mothership discount for github-stars-own is baked into rawMag already —
        # do NOT show it as a separate factor (would imply double-discount).
        # Instead note the divisor in the base description.
        factorParts = [
            f"base {rawMag:.2f}",
            f"x weight {weight}",
            f"x freshness {freshness:.2f}",
        ]
        if rowType == "social-signal":
            factorParts.append(f"x creator {creatorMult}")
            factorParts.append(f"x engagement {engagementRatio:.2f}")

        if inheritMult != 1.0:
            inheritNote = (
                f"x inheritMultiplier {inheritMult:.2f}"
                f" [^ inherited from {genericRef or 'generic'}]"
            )
            factorParts.append(inheritNote)

        # Plateau factor: reverse-engineer from finalScore vs baseScore*inheritMult
        plateauFactor = None
        prePlateau = baseScore * inheritMult
        if prePlateau > 0 and finalScore is not None:
            ratio = finalScore / prePlateau
            if abs(ratio - 1.0) > 0.001:
                plateauFactor = ratio

        lines.append("    " + " ".join(factorParts))
        if plateauFactor is not None:
            lines.append(f"    x plateau {plateauFactor:.2f}")
        if finalScore is not None:
            lines.append(f"    = {finalScore:.2f}")
        lines.append("")

    if socialTotal > 80.0:
        lines.append(f"  [social-signal A-cap applied: {socialTotal:.2f} -> 80.00]")
        lines.append("")

    return "\n".join(lines)

__all__ = [
    "computeArtifactScore",
    "computeArtifactScoreOrNone",
    "computeTrustMagnitude",
    "computeOverallTrustGrade",
    "computeOverallTrustGradeFromSkill",
    "explainTrustMagnitude",
    "passesSuiteApexGate",
    "isSuiteApex",
    "checkUniqueImpossibleGate",
    "enforceAntiAutoMint",
    "checkAGradedOriginsGte5",
    "checkSourceTenureDaysGte180AorS",
    "checkDirectNestedSuiteGte1",
    "checkDepth2OnlyReachableGte1",
    "checkOverallGradeS",
    "checkApexPromotionPrSigned",
    "checkCrossOrgVerifier",
    "checkSystemWideCap",
    "GRADE_S_FLOOR",
    "GRADE_A_FLOOR",
    "GRADE_B_FLOOR",
    "GRADE_C_FLOOR",
    "SELF_PRODUCIBLE_TYPES",
]

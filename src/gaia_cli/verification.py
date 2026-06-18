"""Verification workflow — 4-tier predicate engine for skill trust certification.

Implements the four verification tiers defined in the Phase 1 Trust Infrastructure
scope (issues #658 + #650):

  1. community-verified — at least one graded evidence row.
  2. benchmark-verified — at least one evidence row of type 'benchmark-result'.
  3. security-reviewed  — clean security scan recorded in the timeline within
                          the last 90 UTC days.
  4. enterprise-ready   — Overall Trust Grade >= A AND tenure (days since
                          firstEvidenceAt) >= 30 completed UTC days.

The four tiers are NOT a strict ladder: security-reviewed and enterprise-ready
are independent quality dimensions of an already community-verified skill.
``resolveTier`` returns the highest passing tier for headline display along
with a per-tier pass/fail breakdown.

The enterprise-ready Overall Trust Grade gate uses a MAX-grade proxy until the
G7 Trust Magnitude formula lands in code (see
``founder/handovers/G7_TRUST_TAXONOMY_RFC.md``). The security-reviewed tier
reads ``security_scan_passed`` timeline events; the actual scan-emit wiring is
provided by a follow-up PR that depends on G3 (cli/security-scanner).
"""

from __future__ import annotations

import datetime
from typing import Iterable

# Highest-to-lowest grade ordering. Mirrors gaia_cli.grading._GRADE_ORDER.
# Lower index in this list == better grade.
GRADE_ORDER = ["S", "A", "B", "C"]

# Allowlist of evidence types that count toward the benchmark-verified tier.
# Tracks the canonical type reserved by the G7 Benchmark RFC
# (docs/architecture/benchmark-framework.md).
BENCHMARK_EVIDENCE_TYPES = frozenset({"benchmark-result"})

# Tier-recency window: a security_scan_passed event must be at most this many
# UTC days old to satisfy the security-reviewed tier.
SECURITY_SCAN_WINDOW_DAYS = 90

# Minimum tenure (in completed UTC days) since firstEvidenceAt for
# enterprise-ready.
ENTERPRISE_TENURE_DAYS = 30

# Tier list in highest-to-lowest priority order, used by resolveTier to surface
# the headline tier on `gaia skills info` and `gaia dev verify-tier`.
TIER_ORDER = [
    "enterprise-ready",
    "security-reviewed",
    "benchmark-verified",
    "community-verified",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def effectiveGrade(entry: dict) -> str | None:
    """Return the effective grade letter for an evidence entry, or None.

    Re-exported from :mod:`gaia_cli.promotion` (G4 #709 collapse: this used to
    duplicate the logic; now it forwards to the shared implementation). Reads
    ``grade`` first; falls back to the deprecated ``class`` field for backward
    compatibility with pre-grade evidence records.
    """
    from .promotion import effectiveGrade as _shared

    return _shared(entry)


def maxGrade(evidenceList: Iterable[dict]) -> str | None:
    """Return the highest grade letter across an evidence list, or None.

    'Highest' means closest to 'S' in ``GRADE_ORDER`` (lowest index wins).
    Used as the Overall Trust Grade proxy for enterprise-ready until the
    full Trust Magnitude formula ships in code.
    """
    best: str | None = None
    for entry in evidenceList or []:
        g = effectiveGrade(entry)
        if g is None:
            continue
        if best is None or GRADE_ORDER.index(g) < GRADE_ORDER.index(best):
            best = g
    return best


def gradeAtLeast(grade: str | None, floor: str) -> bool:
    """Return True if ``grade`` is at least ``floor`` on the S>A>B>C scale."""
    if grade not in GRADE_ORDER or floor not in GRADE_ORDER:
        return False
    return GRADE_ORDER.index(grade) <= GRADE_ORDER.index(floor)


def parseIso(value: str | None) -> datetime.datetime | None:
    """Parse an ISO 8601 string into a timezone-aware UTC datetime, or None."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    # Accept a trailing 'Z' as UTC, which fromisoformat does not parse on
    # Python < 3.11.
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def firstEvidenceAt(skill: dict) -> datetime.datetime | None:
    """Resolve the tenure baseline for a skill, or None if unknown.

    Preference order:
      1. ``skill.verification.firstEvidenceAt`` (the canonical record).
      2. The earliest ``evidence_added`` timeline event (graceful fallback
         when the canonical field hasn't been backfilled yet).
    """
    verification = skill.get("verification") or {}
    fromRecord = parseIso(verification.get("firstEvidenceAt"))
    if fromRecord is not None:
        return fromRecord

    earliest: datetime.datetime | None = None
    for event in skill.get("timeline") or []:
        if event.get("action") != "evidence_added":
            continue
        ts = parseIso(event.get("timestamp"))
        if ts is None:
            continue
        if earliest is None or ts < earliest:
            earliest = ts
    return earliest


# ---------------------------------------------------------------------------
# Tier predicates
# ---------------------------------------------------------------------------


def isCommunityVerified(skill: dict, evidence: list) -> tuple[bool, str]:
    """Tier 1: at least one graded evidence row (any of S/A/B/C).

    ``skill`` is accepted for symmetry with the other predicates and for
    forward-compat hooks; only ``evidence`` is read today.
    """
    del skill  # reserved for future use
    for entry in evidence or []:
        if effectiveGrade(entry) is not None:
            return True, ">=1 graded evidence row"
    return False, "no graded evidence yet"


def isBenchmarkVerified(skill: dict, evidence: list) -> tuple[bool, str]:
    """Tier 2: at least one evidence row of type 'benchmark-result'."""
    del skill
    for entry in evidence or []:
        if entry.get("type") in BENCHMARK_EVIDENCE_TYPES:
            return True, ">=1 evidence row of type 'benchmark-result'"
    return False, "no benchmark-result evidence"


def isSecurityReviewed(
    skill: dict, scanEvents: list, now: datetime.datetime
) -> tuple[bool, str]:
    """Tier 3: a clean security scan within the last 90 UTC days.

    ``scanEvents`` is the skill's timeline pre-filtered to events with
    ``action == 'security_scan_passed'``. Each event must carry an ``at``
    timestamp (ISO 8601). For backward compatibility we also accept the
    standard ``timestamp`` field used by other timeline events.
    """
    del skill
    nowUtc = now.astimezone(datetime.timezone.utc) if now.tzinfo else now.replace(
        tzinfo=datetime.timezone.utc
    )
    cutoff = nowUtc - datetime.timedelta(days=SECURITY_SCAN_WINDOW_DAYS)
    latest: datetime.datetime | None = None
    for event in scanEvents or []:
        ts = parseIso(event.get("at") or event.get("timestamp"))
        if ts is None:
            continue
        if ts < cutoff:
            continue
        if latest is None or ts > latest:
            latest = ts
    if latest is None:
        return False, f"no clean scan in last {SECURITY_SCAN_WINDOW_DAYS} days"
    return (
        True,
        f"scan passed {latest.date().isoformat()} (within {SECURITY_SCAN_WINDOW_DAYS} days)",
    )


def isEnterpriseReady(
    skill: dict, evidence: list, now: datetime.datetime
) -> tuple[bool, str]:
    """Tier 4: Trust Grade >= A AND tenure >= 30 completed UTC days.

    Tenure is computed against ``firstEvidenceAt`` (canonical record, with a
    timeline-derived fallback). The Trust Grade gate uses MAX-grade as a
    placeholder until the G7 Trust Magnitude formula ships in code.
    """
    grade = maxGrade(evidence)
    if not gradeAtLeast(grade, "A"):
        if grade is None:
            return False, "Trust Grade None (need >=A)"
        return False, f"Trust Grade {grade} (need >=A)"

    baseline = firstEvidenceAt(skill)
    if baseline is None:
        return False, f"Trust Grade {grade}, no firstEvidenceAt set"

    nowUtc = now.astimezone(datetime.timezone.utc) if now.tzinfo else now.replace(
        tzinfo=datetime.timezone.utc
    )
    tenureDays = (nowUtc - baseline).days
    if tenureDays < ENTERPRISE_TENURE_DAYS:
        return (
            False,
            f"Trust Grade {grade}, tenure {tenureDays} days (need >={ENTERPRISE_TENURE_DAYS})",
        )
    return True, f"Trust Grade {grade}, tenure {tenureDays} days"


# ---------------------------------------------------------------------------
# Tier resolution
# ---------------------------------------------------------------------------


def resolveTier(
    skill: dict,
    evidence: list,
    scanEvents: list,
    now: datetime.datetime,
) -> tuple[str | None, dict[str, dict]]:
    """Evaluate every tier and return ``(highestEarnedTier, tierStatusMap)``.

    ``tierStatusMap`` is keyed by tier name and holds ``{'passed': bool,
    'reason': str}`` for each of the four tiers.

    The four tiers are independent quality dimensions, not a strict ladder
    — for example, a skill can be enterprise-ready without being
    benchmark-verified. ``resolveTier`` surfaces the highest tier that
    passes (per ``TIER_ORDER``) for headline display, and the full breakdown
    is preserved in ``tierStatusMap`` so callers can render every tier.
    """
    cv = isCommunityVerified(skill, evidence)
    bv = isBenchmarkVerified(skill, evidence)
    sr = isSecurityReviewed(skill, scanEvents, now)
    er = isEnterpriseReady(skill, evidence, now)

    statusMap: dict[str, dict] = {
        "community-verified": {"passed": cv[0], "reason": cv[1]},
        "benchmark-verified": {"passed": bv[0], "reason": bv[1]},
        "security-reviewed": {"passed": sr[0], "reason": sr[1]},
        "enterprise-ready": {"passed": er[0], "reason": er[1]},
    }

    highest: str | None = None
    for tier in TIER_ORDER:
        if statusMap[tier]["passed"]:
            highest = tier
            break
    return highest, statusMap


def filterScanEvents(timeline: Iterable[dict]) -> list[dict]:
    """Pluck ``security_scan_passed`` events out of a full timeline list."""
    return [
        e
        for e in (timeline or [])
        if e.get("action") == "security_scan_passed"
    ]


def utcNow() -> datetime.datetime:
    """Return a timezone-aware UTC ``datetime`` for the current moment.

    Wrapped in a helper so tests can monkey-patch a fixed clock.
    """
    return datetime.datetime.now(datetime.timezone.utc)


def stampFirstEvidenceAt(
    record: dict, isoTimestamp: str | None = None
) -> str | None:
    """Set ``record.verification.firstEvidenceAt`` if it is not already set.

    Mutates ``record`` in place. Returns the stamped timestamp string when a
    write occurred, or None if the field was already populated.

    ``isoTimestamp`` defaults to the current UTC time formatted with a 'Z'
    suffix to match the timeline-event style used elsewhere in the CLI.
    """
    verification = record.setdefault("verification", {})
    if verification.get("firstEvidenceAt"):
        return None
    if isoTimestamp is None:
        isoTimestamp = utcNow().strftime("%Y-%m-%dT%H:%M:%SZ")
    verification["firstEvidenceAt"] = isoTimestamp
    return isoTimestamp

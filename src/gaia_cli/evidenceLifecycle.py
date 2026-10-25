"""Governed Evidence Assertion Lifecycle, Identity, and Rehearsal Engine.

Yggdrasil IV (RFC #2148 §§3, 4, 7, 10 and founder ratification 2026-10-25):
Bounded P3 Preparation:
- Stable evidence identity (``evidenceId``) across metric refreshes.
- Positive integer revision identity (``revision``) and immutable supersession (``supersedes``).
- Four-state assertion state machine: ``active | suspended | revoked | superseded``.
- Strict cryptographic approval binding (``decisionRef``, ``reviewedOldDigest``, ``reviewedNewDigest``).
- Deterministic score-neutral legacy migration rehearsal and exact in-memory rollback proof.
- Bounded operational observation states and metric provenance.

No helpers in this module write canonical data to disk; canonical publication
and CLI commands are held for founder/two-Core review.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import urllib.parse
from dataclasses import dataclass
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Canonical Lifecycle States & Vocabularies (RFC #2148 §3.1, §3.2, §3.3)
# ---------------------------------------------------------------------------

ASSERTION_ACTIVE = "active"
ASSERTION_SUSPENDED = "suspended"
ASSERTION_REVOKED = "revoked"
ASSERTION_SUPERSEDED = "superseded"
ASSERTION_STATES = (
    ASSERTION_ACTIVE,
    ASSERTION_SUSPENDED,
    ASSERTION_REVOKED,
    ASSERTION_SUPERSEDED,
)

OBSERVATION_UNKNOWN = "unknown"
OBSERVATION_REACHABLE = "reachable"
OBSERVATION_TRANSIENT_FAILURE = "transient-failure"
OBSERVATION_UNAVAILABLE = "unavailable"
OBSERVATION_CHANGED = "changed"
OBSERVATION_STATES = (
    OBSERVATION_UNKNOWN,
    OBSERVATION_REACHABLE,
    OBSERVATION_TRANSIENT_FAILURE,
    OBSERVATION_UNAVAILABLE,
    OBSERVATION_CHANGED,
)

METRIC_VERIFIED = "verified"
METRIC_REPORTED = "reported"
METRIC_INFERRED = "inferred"
METRIC_UNKNOWN = "unknown"
METRIC_METHODS = (
    METRIC_VERIFIED,
    METRIC_REPORTED,
    METRIC_INFERRED,
    METRIC_UNKNOWN,
)

NUMERIC_METRIC_FIELDS = (
    "stars",
    "commits",
    "contributors",
    "citations",
    "views",
    "reviewers",
    "percentile",
    "score",
    "trustNumber",
    "downloads",
    "likes",
    "comments",
    "externalStars",
    "verifiers",
    "skillCountInRepo",
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class EvidenceLifecycleError(Exception):
    """Base exception for evidence lifecycle operations."""


class EvidenceValidationError(EvidenceLifecycleError, ValueError):
    """Raised when an evidence payload violates schema or numeric validity."""


class AmbiguousCollisionError(EvidenceLifecycleError, ValueError):
    """Raised when duplicate legacy evidence rows collide on identity."""


class MalformedRevisionCycleError(EvidenceLifecycleError, ValueError):
    """Raised when revision numbers or supersession references form a cycle or invalid order."""


class StaleApprovalError(EvidenceLifecycleError, ValueError):
    """Raised when approval binding references an outdated old digest."""


class DigestMismatchError(EvidenceLifecycleError, ValueError):
    """Raised when calculated payload digest does not match reviewed digest."""


class InvalidTransitionError(EvidenceLifecycleError, ValueError):
    """Raised when an assertion state transition is prohibited."""


class EvidenceNotFoundError(EvidenceLifecycleError, KeyError):
    """Raised when targeting an unknown or missing evidenceId."""


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ApprovalTransition:
    """Cryptographic approval binding for evidence lifecycle transitions.

    Approval transitions must bind reviewed old/new payload digests,
    not boolean flags claiming human approval.
    """
    decision_ref: str
    reviewed_old_digest: Optional[str] = None
    reviewed_new_digest: str = ""
    actor: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class MigrationRehearsalResult:
    """In-memory result of legacy evidence migration rehearsal."""
    skill_id: str
    before_payload: dict
    after_payload: dict
    before_digest: str
    after_digest: str
    rollback_payload: dict
    score_neutral: bool
    before_score: float
    after_score: float
    migrated_row_count: int
    unmigrated_row_count: int = 0


# ---------------------------------------------------------------------------
# Canonical Digest & Serialization
# ---------------------------------------------------------------------------

def canonical_json_bytes(obj: Any) -> bytes:
    """Return deterministic canonical JSON UTF-8 bytes with sorted keys."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def compute_payload_digest(obj: Any, exclude_self_digest: bool = True) -> str:
    """Compute deterministic SHA-256 hex digest of a canonical JSON payload.

    When hashing an evidence row or payload that carries 'reviewedNewDigest', that field
    is excluded from the digest calculation so that the digest binds the reviewed assertion
    payload without a self-referential paradox.
    """
    if isinstance(obj, dict) and exclude_self_digest and "reviewedNewDigest" in obj:
        clean = {k: v for k, v in obj.items() if k != "reviewedNewDigest"}
        return hashlib.sha256(canonical_json_bytes(clean)).hexdigest()
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


# ---------------------------------------------------------------------------
# Normalization & Identity Derivation
# ---------------------------------------------------------------------------

def normalize_source_locator(source: str) -> str:
    """Normalize a source URL or locator for stable identity derivation.

    Lowercases scheme and host, normalizes trailing slashes, and trims whitespace.
    """
    if not source:
        return ""
    s = str(source).strip()
    parsed = urllib.parse.urlparse(s)
    if parsed.scheme:
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        normalized = urllib.parse.urlunparse((
            parsed.scheme.lower(),
            netloc,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        ))
        return normalized.rstrip("/")
    return s.rstrip("/")


def derive_evidence_identity(skill_id: str, row: dict) -> str:
    """Derive deterministic, stable evidenceId for an evidence row.

    If the row already carries an evidenceId, returns it unchanged.
    Otherwise derives a stable kebab-case identifier from skillId, evidence type,
    and normalized source locator (or benchmarkId).
    """
    existing_id = row.get("evidenceId")
    if existing_id is not None:
        if not isinstance(existing_id, str) or not existing_id.strip():
            raise EvidenceValidationError("Row has empty or invalid evidenceId")
        return existing_id.strip()

    t = (row.get("type") or "").strip().lower()
    if not t:
        raise EvidenceValidationError(f"Cannot derive evidence identity without 'type' for row in {skill_id}")

    locator = ""
    if t == "benchmark-result" and row.get("benchmarkId"):
        locator = str(row["benchmarkId"]).strip().lower()
    else:
        src = row.get("source") or row.get("url") or row.get("sourceUrl") or ""
        locator = normalize_source_locator(str(src))

    if not locator:
        raise EvidenceValidationError(f"Cannot derive evidence identity for row without source locator: {row}")

    safe_skill = re.sub(r"[^a-zA-Z0-9]+", "-", str(skill_id)).strip("-").lower()
    safe_type = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    loc_hash = hashlib.sha256(locator.encode("utf-8")).hexdigest()[:8]

    return f"ev-{safe_skill}-{safe_type}-{loc_hash}"


# ---------------------------------------------------------------------------
# Payload & History Validation
# ---------------------------------------------------------------------------

def validate_evidence_payload(row: dict, allow_legacy: bool = False) -> None:
    """Validate finite raw metrics and lifecycle constraints on an evidence row.

    Rejects non-finite (NaN, Inf) numeric metrics, blank strings on required fields,
    and invalid assertion states.
    """
    if not isinstance(row, dict):
        raise EvidenceValidationError(f"Evidence row must be a dict, got {type(row).__name__}")

    # Check finite numbers
    for k, v in row.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if math.isnan(v) or math.isinf(v):
                raise EvidenceValidationError(f"Evidence field '{k}' has non-finite value: {v}")

    # Core required fields in all evidence rows
    for field in ("source", "evaluator", "date"):
        val = row.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            raise EvidenceValidationError(f"Evidence row missing required non-blank field '{field}'")

    t = row.get("type")
    if t is not None and (not isinstance(t, str) or not t.strip()):
        raise EvidenceValidationError("Evidence type must be a non-blank string")

    if not allow_legacy:
        eid = row.get("evidenceId")
        if not eid or not isinstance(eid, str) or not eid.strip():
            raise EvidenceValidationError("Migrated evidence row requires non-blank 'evidenceId'")

        rev = row.get("revision")
        if rev is None or not isinstance(rev, int) or rev < 1:
            raise EvidenceValidationError(f"Evidence row revision must be positive integer >= 1, got {rev}")

        state = row.get("assertionState")
        if state not in ASSERTION_STATES:
            raise EvidenceValidationError(
                f"Invalid assertionState '{state}'; must be one of {ASSERTION_STATES}"
            )

        dref = row.get("decisionRef")
        if dref is not None and (not isinstance(dref, str) or not dref.strip()):
            raise EvidenceValidationError("decisionRef must be a non-blank string when present")

        sup = row.get("supersedes")
        if sup is not None:
            if not isinstance(sup, int) or sup < 1:
                raise EvidenceValidationError(f"supersedes must be a positive integer >= 1, got {sup}")
            if sup >= rev:
                raise MalformedRevisionCycleError(
                    f"supersedes ({sup}) must be strictly less than revision ({rev})"
                )

        obs = row.get("observationState")
        if obs is not None and obs not in OBSERVATION_STATES:
            raise EvidenceValidationError(
                f"Invalid observationState '{obs}'; must be one of {OBSERVATION_STATES}"
            )

        mm = row.get("metricMethod")
        if mm is not None and mm not in METRIC_METHODS:
            raise EvidenceValidationError(
                f"Invalid metricMethod '{mm}'; must be one of {METRIC_METHODS}"
            )

        cd = row.get("contentDigest")
        if cd is not None and (not isinstance(cd, str) or not re.match(r"^[a-f0-9]{64}$", cd)):
            raise EvidenceValidationError("contentDigest must be 64-char lowercase hex SHA-256")


def detect_legacy_collisions(skill_id: str, rows: list[dict]) -> None:
    """Check for duplicate identities or colliding identity keys in legacy rows.

    Raises AmbiguousCollisionError if multiple legacy rows produce colliding identities
    or share the identical (type, source locator).
    """
    seen_keys: dict[tuple[str, str], int] = {}
    seen_explicit_ids: dict[str, int] = {}

    for idx, row in enumerate(rows):
        eid = row.get("evidenceId")
        if eid:
            eid_str = str(eid).strip()
            if eid_str in seen_explicit_ids:
                prev_idx = seen_explicit_ids[eid_str]
                raise AmbiguousCollisionError(
                    f"Skill '{skill_id}' has ambiguous duplicate evidenceId '{eid_str}' "
                    f"on row {prev_idx} and row {idx}"
                )
            seen_explicit_ids[eid_str] = idx

        t = (row.get("type") or "").strip().lower()
        if t == "benchmark-result" and row.get("benchmarkId"):
            src = str(row["benchmarkId"]).strip().lower()
        else:
            raw_src = row.get("source") or row.get("url") or row.get("sourceUrl") or ""
            src = normalize_source_locator(str(raw_src))

        key = (t, src)
        if key in seen_keys:
            prev_idx = seen_keys[key]
            raise AmbiguousCollisionError(
                f"Skill '{skill_id}' has ambiguous duplicate legacy collision for identity key {key}: "
                f"row {prev_idx} and row {idx}"
            )
        seen_keys[key] = idx


def validate_revision_history(skill_id: str, rows: list[dict]) -> None:
    """Validate that for each evidenceId, revisions form a valid DAG with no cycles
    and at most one active assertion.
    """
    by_id: dict[str, list[dict]] = {}
    for row in rows:
        eid = row.get("evidenceId")
        if eid:
            by_id.setdefault(str(eid).strip(), []).append(row)

    for eid, rev_rows in by_id.items():
        revisions: dict[int, dict] = {}
        active_count = 0
        for r in rev_rows:
            rev = r.get("revision")
            if rev is None or not isinstance(rev, int) or rev < 1:
                raise MalformedRevisionCycleError(
                    f"Evidence '{eid}' in '{skill_id}' has invalid revision {rev}"
                )
            if rev in revisions:
                raise MalformedRevisionCycleError(
                    f"Evidence '{eid}' in '{skill_id}' has duplicate revision {rev}"
                )
            revisions[rev] = r

            state = r.get("assertionState")
            if state == ASSERTION_ACTIVE:
                active_count += 1

        if active_count > 1:
            raise MalformedRevisionCycleError(
                f"Evidence '{eid}' in '{skill_id}' has {active_count} active revisions; at most 1 allowed"
            )

        # Check supersedes references and cycle freedom
        visited = set()
        for rev, r in revisions.items():
            sup = r.get("supersedes")
            if sup is not None:
                if sup == rev:
                    raise MalformedRevisionCycleError(
                        f"Evidence '{eid}' revision {rev} supersedes itself"
                    )
                if sup > rev:
                    raise MalformedRevisionCycleError(
                        f"Evidence '{eid}' revision {rev} supersedes future revision {sup}"
                    )
                if sup not in revisions:
                    raise MalformedRevisionCycleError(
                        f"Evidence '{eid}' revision {rev} supersedes non-existent revision {sup}"
                    )

            # Cycle check following supersedes chain backwards
            curr_rev = rev
            chain = []
            while curr_rev is not None:
                if curr_rev in chain:
                    raise MalformedRevisionCycleError(
                        f"Supersession cycle detected in evidence '{eid}' along chain {chain + [curr_rev]}"
                    )
                chain.append(curr_rev)
                curr_row = revisions.get(curr_rev)
                if not curr_row:
                    break
                curr_rev = curr_row.get("supersedes")


# ---------------------------------------------------------------------------
# Scoring Filter (Score-Neutral Read Compatibility)
# ---------------------------------------------------------------------------

def active_evidence_rows(skill: dict, include_legacy: bool = True) -> list[dict]:
    """Return only active scoring-eligible evidence rows from a skill payload.

    Legacy rows (lacking assertionState) are included only when include_legacy=True.
    Suspended, revoked, and superseded rows are excluded from scoring.
    """
    rows = skill.get("evidence") or []
    out = []
    for r in rows:
        state = r.get("assertionState")
        if state is None:
            if include_legacy:
                out.append(r)
        elif state == ASSERTION_ACTIVE:
            out.append(r)
    return out


# ---------------------------------------------------------------------------
# State Transitions & Approval Binding
# ---------------------------------------------------------------------------

def transition_assertion_state(
    row: dict,
    target_state: str,
    approval: ApprovalTransition,
) -> dict:
    """Transition an evidence assertion to a new state with strict approval binding.

    Approval transitions must bind reviewed old/new payload digests,
    not boolean flags claiming human approval.
    """
    if target_state not in ASSERTION_STATES:
        raise InvalidTransitionError(f"Unknown target assertionState: '{target_state}'")

    current_state = row.get("assertionState", ASSERTION_ACTIVE)
    if current_state == ASSERTION_SUPERSEDED:
        raise InvalidTransitionError("Cannot transition a superseded (terminal) revision")

    if not approval.decision_ref or not str(approval.decision_ref).strip():
        raise EvidenceValidationError("decision_ref must be a non-blank string for approval transitions")

    # Cryptographic old-digest verification
    actual_old_digest = compute_payload_digest(row)
    if approval.reviewed_old_digest != actual_old_digest:
        raise StaleApprovalError(
            f"Approval binding stale: reviewedOldDigest '{approval.reviewed_old_digest}' "
            f"!= actual payload digest '{actual_old_digest}'"
        )

    if current_state == target_state:
        # No-op return identical copy
        return dict(row)

    new_row = dict(row)
    new_row["assertionState"] = target_state
    new_row["decisionRef"] = approval.decision_ref.strip()
    new_row["reviewedOldDigest"] = approval.reviewed_old_digest
    new_row["reviewedNewDigest"] = approval.reviewed_new_digest

    validate_evidence_payload(new_row, allow_legacy=False)

    actual_new_digest = compute_payload_digest(new_row)
    if approval.reviewed_new_digest != actual_new_digest:
        raise DigestMismatchError(
            f"Approval binding mismatch: reviewedNewDigest '{approval.reviewed_new_digest}' "
            f"!= actual new payload digest '{actual_new_digest}'"
        )

    return new_row


def refresh_metric_assertion(
    skill: dict,
    evidence_id: str,
    metric_updates: dict,
    approval: ApprovalTransition,
    observation_provenance: Optional[dict] = None,
) -> tuple[dict, dict]:
    """Create a successor revision for an active evidence row and supersede the old revision.

    Retains full history (previous revision is NOT deleted).
    Validates approval binding.
    Returns (updated_skill, new_row).
    """
    skill_id = skill.get("id", "unknown")
    evidence = list(skill.get("evidence") or [])
    active_idx = None
    active_row = None

    for idx, r in enumerate(evidence):
        if r.get("evidenceId") == evidence_id and r.get("assertionState") == ASSERTION_ACTIVE:
            active_idx = idx
            active_row = r
            break

    if active_row is None or active_idx is None:
        raise EvidenceNotFoundError(f"No active assertion found for evidenceId '{evidence_id}' in '{skill_id}'")

    actual_old_digest = compute_payload_digest(active_row)
    if approval.reviewed_old_digest != actual_old_digest:
        raise StaleApprovalError(
            f"Approval binding stale: reviewedOldDigest '{approval.reviewed_old_digest}' "
            f"!= actual current digest '{actual_old_digest}'"
        )

    old_rev = active_row.get("revision", 1)
    new_rev = old_rev + 1

    # Mark old row as superseded
    superseded_row = dict(active_row)
    superseded_row["assertionState"] = ASSERTION_SUPERSEDED

    # Construct successor revision
    new_row = dict(active_row)
    new_row.update(metric_updates)
    new_row["revision"] = new_rev
    new_row["supersedes"] = old_rev
    new_row["assertionState"] = ASSERTION_ACTIVE
    new_row["decisionRef"] = approval.decision_ref.strip()
    new_row["reviewedOldDigest"] = approval.reviewed_old_digest
    new_row["reviewedNewDigest"] = approval.reviewed_new_digest

    if observation_provenance:
        for k, v in observation_provenance.items():
            if v is not None:
                new_row[k] = v

    validate_evidence_payload(new_row, allow_legacy=False)

    actual_new_digest = compute_payload_digest(new_row)
    if approval.reviewed_new_digest != actual_new_digest:
        raise DigestMismatchError(
            f"Approval binding mismatch: reviewedNewDigest '{approval.reviewed_new_digest}' "
            f"!= actual new digest '{actual_new_digest}'"
        )

    # Retain both in evidence array!
    new_evidence = list(evidence)
    new_evidence[active_idx] = superseded_row
    new_evidence.append(new_row)

    validate_revision_history(skill_id, new_evidence)

    updated_skill = dict(skill)
    updated_skill["evidence"] = new_evidence
    return updated_skill, new_row


# ---------------------------------------------------------------------------
# Migration Rehearsal & Exact Rollback Proof
# ---------------------------------------------------------------------------

def rehearse_legacy_migration(
    skill: dict,
    decision_ref: str = "migration:yggdrasil-iv-rehearsal",
    generic_skill_map: Optional[dict] = None,
) -> MigrationRehearsalResult:
    """Rehearse deterministic score-neutral legacy evidence migration in-memory.

    Returns proposed before/after payloads, digests, exact rollback payload,
    and proves score neutrality. Does NOT write any files to disk.
    """
    skill_id = skill.get("id", "unknown")
    evidence = skill.get("evidence") or []

    # Validate raw payloads
    for r in evidence:
        validate_evidence_payload(r, allow_legacy=True)

    # Detect duplicate legacy collisions
    detect_legacy_collisions(skill_id, evidence)

    # Check if already migrated
    already_migrated = bool(evidence) and all(
        r.get("evidenceId") and r.get("revision") and r.get("assertionState")
        for r in evidence
    )

    before_payload = copy.deepcopy(skill)
    before_digest = compute_payload_digest(before_payload)

    # Baseline Trust Magnitude score from existing scoring engine (read-only)
    from gaia_cli.trustMagnitude import computeTrustMagnitude
    before_score = computeTrustMagnitude(before_payload, generic_skill_map)

    if already_migrated:
        return MigrationRehearsalResult(
            skill_id=skill_id,
            before_payload=before_payload,
            after_payload=before_payload,
            before_digest=before_digest,
            after_digest=before_digest,
            rollback_payload={"evidence": copy.deepcopy(evidence)},
            score_neutral=True,
            before_score=before_score,
            after_score=before_score,
            migrated_row_count=0,
            unmigrated_row_count=0,
        )

    migrated_rows = []
    for r in evidence:
        row_copy = copy.deepcopy(r)
        eid = derive_evidence_identity(skill_id, row_copy)
        row_copy["evidenceId"] = eid
        row_copy["revision"] = row_copy.get("revision", 1)
        row_copy["assertionState"] = ASSERTION_ACTIVE
        row_copy["decisionRef"] = decision_ref.strip()
        if "metricMethod" not in row_copy:
            row_copy["metricMethod"] = METRIC_REPORTED

        validate_evidence_payload(row_copy, allow_legacy=False)
        migrated_rows.append(row_copy)

    after_payload = copy.deepcopy(skill)
    after_payload["evidence"] = migrated_rows
    after_digest = compute_payload_digest(after_payload)

    # Verify score neutrality: TM engine should score identical active rows identically
    after_score = computeTrustMagnitude(after_payload, generic_skill_map)
    score_neutral = abs((before_score or 0.0) - (after_score or 0.0)) < 1e-9

    rollback_payload = {
        "evidence": copy.deepcopy(evidence)
    }

    return MigrationRehearsalResult(
        skill_id=skill_id,
        before_payload=before_payload,
        after_payload=after_payload,
        before_digest=before_digest,
        after_digest=after_digest,
        rollback_payload=rollback_payload,
        score_neutral=score_neutral,
        before_score=before_score,
        after_score=after_score,
        migrated_row_count=len(migrated_rows),
        unmigrated_row_count=0,
    )


def apply_rollback(after_payload: dict, rollback_payload: dict) -> dict:
    """Apply exact rollback payload to restore the pre-migration state.

    Proves in-memory reversibility: restored payload matches before payload digest.
    """
    restored = copy.deepcopy(after_payload)
    restored["evidence"] = copy.deepcopy(rollback_payload.get("evidence", []))
    return restored

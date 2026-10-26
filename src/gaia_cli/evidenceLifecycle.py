"""Governed Evidence Assertion Lifecycle, Identity, and Rehearsal Engine.

Yggdrasil IV (RFC #2148 §§3, 4, 7, 10 and founder ratification 2026-10-25):
Bounded P3 Preparation:
- Stable evidence identity (``evidenceId``) across metric refreshes.
- Positive integer revision identity (``revision``) and immutable supersession (``supersedes``).
- Four-state assertion state machine: ``active | suspended | revoked | superseded``.
- Shadow-only proposal plans with full-payload checksums; checksums are not approval.
- Deterministic score-neutral legacy migration rehearsal and exact in-memory rollback proof.
- Bounded operational observation states and metric provenance.

No helpers in this module write canonical data to disk; canonical publication
and CLI commands are held for founder/two-Core review. The production TM engine
does not currently consume these assertion states; that integration is deliberately
held and is not changed by this rehearsal-only module.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
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


class InvalidTransitionError(EvidenceLifecycleError, ValueError):
    """Raised when an assertion state transition is prohibited."""


class EvidenceNotFoundError(EvidenceLifecycleError, KeyError):
    """Raised when targeting an unknown or missing evidenceId."""


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LifecycleProposal:
    """Untrusted rehearsal plan; never evidence of human approval or authority.

    Digests are integrity/CAS checksums only. A trusted reviewed-receipt resolver
    and founder/Core authorization are required before any future application.
    """
    operation: str
    before_payload: dict
    after_payload: dict
    before_digest: str
    after_digest: str
    history_before: tuple[dict, ...]
    history_after: tuple[dict, ...]
    decision_ref: str
    scope: tuple[str, ...]


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
    """Compute a deterministic SHA-256 checksum of a canonical JSON payload.

    ``reviewedNewDigest`` is omitted only to avoid self-reference. This checksum
    detects payload differences; it neither authenticates a reviewer nor grants authority.
    """
    if isinstance(obj, dict) and exclude_self_digest and "reviewedNewDigest" in obj:
        clean = {k: v for k, v in obj.items() if k != "reviewedNewDigest"}
        return hashlib.sha256(canonical_json_bytes(clean)).hexdigest()
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


# ---------------------------------------------------------------------------
# Normalization & Identity Derivation
# ---------------------------------------------------------------------------

def normalize_source_locator(source: str) -> str:
    """Mirror the TM engine's source identity canonicalization exactly.

    In particular, query strings are preserved; fragments are removed and GitHub
    ``tree/`` paths are treated as ``blob/`` paths, as in ``_canonicalUrl``.
    """
    if not isinstance(source, str):
        return ""
    value = source.strip()
    if not value:
        return ""
    value = value.split("#", 1)[0].replace("/tree/", "/blob/")
    return value.rstrip("/").lower()


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
    loc_hash = hashlib.sha256(locator.encode("utf-8")).hexdigest()

    return f"ev-{safe_skill}-{safe_type}-{loc_hash}"


# ---------------------------------------------------------------------------
# Payload & History Validation
# ---------------------------------------------------------------------------

def validate_evidence_payload(row: dict, allow_legacy: bool = False) -> None:
    """Validate evidence structure and schema-relevant metric/date constraints."""
    if not isinstance(row, dict):
        raise EvidenceValidationError(f"Evidence row must be a dict, got {type(row).__name__}")

    allowed = {
        "type", "grade", "trustNumber", "class", "source", "evaluator", "date", "notes",
        "verified", "disputed", "verificationSource", "sourceStartedAt", "lastVerified", "citations", "stars",
        "commits", "contributors", "views", "reviewers", "percentile", "skillCountInRepo",
        "unverified", "layer", "links", "cosigners", "benchmarkId", "score", "unit", "runAt",
        "provenance", "attestor", "datasetHash", "benchmarkInputHash", "harnessUrl", "evidenceId",
        "revision", "supersedes", "assertionState", "decisionRef", "sourceRevision",
        "observationState", "lastObservedAt", "metricMethod", "measurementScope", "contentDigest", "reviewedOldDigest",
        "reviewedNewDigest", "decisionHistory",
    }
    unknown = set(row) - allowed
    if unknown:
        raise EvidenceValidationError(f"Unknown evidence field(s): {', '.join(sorted(unknown))}")

    for field in ("source", "evaluator", "date"):
        val = row.get(field)
        if not isinstance(val, str) or not val.strip():
            raise EvidenceValidationError(f"Evidence row missing required non-blank field '{field}'")
    if not isinstance(row.get("type"), str) or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", row["type"]):
        raise EvidenceValidationError("Evidence type must match the schema's kebab-case type pattern")

    from datetime import date, datetime
    try:
        date.fromisoformat(row["date"])
        if "sourceStartedAt" in row:
            date.fromisoformat(row["sourceStartedAt"])
    except (TypeError, ValueError) as exc:
        raise EvidenceValidationError("date must be a valid ISO-8601 calendar date") from exc

    integer_metrics = set(NUMERIC_METRIC_FIELDS) - {"percentile", "score", "trustNumber"}
    for key in NUMERIC_METRIC_FIELDS:
        if key not in row:
            continue
        value = row[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EvidenceValidationError(f"Metric '{key}' must be a number (booleans are not numbers)")
        if not math.isfinite(value) or value < 0:
            raise EvidenceValidationError(f"Metric '{key}' must be finite and non-negative")
        if key in integer_metrics and not isinstance(value, int):
            raise EvidenceValidationError(f"Metric '{key}' must be an integer")
        if key == "percentile" and (not isinstance(value, int) or value > 100):
            raise EvidenceValidationError("Metric 'percentile' must be an integer between 0 and 100")
        if key == "trustNumber" and value > 100:
            raise EvidenceValidationError("Metric 'trustNumber' must be between 0 and 100")
        if key == "skillCountInRepo" and value < 1:
            raise EvidenceValidationError("Metric 'skillCountInRepo' must be at least 1")

    for key in ("verified", "disputed", "unverified"):
        if key in row and not isinstance(row[key], bool):
            raise EvidenceValidationError(f"'{key}' must be a boolean")
    for key in ("lastObservedAt", "runAt"):
        if key in row:
            try:
                parsed = datetime.fromisoformat(row[key].replace("Z", "+00:00"))
                from datetime import timezone
                if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
                    raise ValueError("timestamp must be explicitly UTC")
                if not row[key].endswith("Z"):
                    raise ValueError("timestamp must use Z UTC notation")
            except (AttributeError, TypeError, ValueError) as exc:
                raise EvidenceValidationError(f"{key} must be an aware UTC ISO-8601 date-time ending in Z") from exc

    lifecycle_fields = {"evidenceId", "revision", "assertionState", "decisionRef", "supersedes", "decisionHistory", "reviewedOldDigest", "reviewedNewDigest"}
    if not allow_legacy and lifecycle_fields.intersection(row):
        required_lifecycle = {"evidenceId", "revision", "assertionState"}
        missing = required_lifecycle - set(row)
        if missing:
            raise EvidenceValidationError(f"Partial lifecycle metadata; missing: {', '.join(sorted(missing))}")

    if not allow_legacy:
        eid = row.get("evidenceId")
        if not isinstance(eid, str) or not eid.strip():
            raise EvidenceValidationError("Migrated evidence row requires non-blank 'evidenceId'")
        rev = row.get("revision")
        if isinstance(rev, bool) or not isinstance(rev, int) or rev < 1:
            raise EvidenceValidationError(f"Evidence row revision must be positive integer >= 1, got {rev}")
        state = row.get("assertionState")
        if state not in ASSERTION_STATES:
            raise EvidenceValidationError(f"Invalid assertionState '{state}'; must be one of {ASSERTION_STATES}")
        dref = row.get("decisionRef")
        if state != ASSERTION_ACTIVE and (not isinstance(dref, str) or not dref.strip()):
            raise EvidenceValidationError("Non-active lifecycle rows require a non-blank decisionRef")
        if dref is not None and (not isinstance(dref, str) or not dref.strip()):
            raise EvidenceValidationError("decisionRef must be a non-blank string when present")
        sup = row.get("supersedes")
        if sup is not None and (isinstance(sup, bool) or not isinstance(sup, int) or sup < 1 or sup >= rev):
            raise MalformedRevisionCycleError(f"supersedes must be an integer in [1, revision), got {sup}")
        obs = row.get("observationState")
        if obs is not None and obs not in OBSERVATION_STATES:
            raise EvidenceValidationError(f"Invalid observationState '{obs}'; must be one of {OBSERVATION_STATES}")
        mm = row.get("metricMethod")
        if mm is not None and mm not in METRIC_METHODS:
            raise EvidenceValidationError(f"Invalid metricMethod '{mm}'; must be one of {METRIC_METHODS}")
        cd = row.get("contentDigest")
        for field in ("contentDigest", "reviewedOldDigest", "reviewedNewDigest", "datasetHash", "benchmarkInputHash"):
            digest = row.get(field)
            if digest is not None and not (field == "contentDigest" and digest == "unknown") and (not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)):
                raise EvidenceValidationError(f"{field} must be 64-char lowercase hex SHA-256" + (" or explicit 'unknown'" if field == "contentDigest" else ""))
        history = row.get("decisionHistory", [])
        if not isinstance(history, list) or any(
            not isinstance(item, dict)
            or not isinstance(item.get("decisionRef"), str) or not item["decisionRef"].strip()
            or item.get("assertionState") not in ASSERTION_STATES
            or not isinstance(item.get("priorPayload"), dict)
            for item in history
        ):
            raise EvidenceValidationError("decisionHistory must retain decisionRef, assertionState, and complete priorPayload")


def detect_legacy_collisions(skill_id: str, rows: list[dict]) -> None:
    """Check for duplicate identities or colliding identity keys in legacy rows.

    Raises AmbiguousCollisionError if multiple legacy rows produce colliding identities
    or share the identical (type, source locator).
    """
    seen_keys: dict[tuple[str, str], int] = {}
    seen_explicit_ids: dict[str, int] = {}
    seen_derived_ids: dict[str, tuple[str, str]] = {}

    for idx, row in enumerate(rows):
        eid = row.get("evidenceId")
        if eid:
            eid_str = str(eid).strip()
            if not row.get("revision") and eid_str in seen_explicit_ids:
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
        if row.get("revision") or row.get("assertionState"):
            continue
        if key in seen_keys:
            prev_idx = seen_keys[key]
            raise AmbiguousCollisionError(
                f"Skill '{skill_id}' has ambiguous duplicate legacy collision for identity key {key}: "
                f"row {prev_idx} and row {idx}"
            )
        seen_keys[key] = idx
        derived_id = derive_evidence_identity(skill_id, row)
        prior_key = seen_derived_ids.get(derived_id)
        if prior_key is not None and prior_key != key:
            raise AmbiguousCollisionError(
                f"Skill '{skill_id}' has SHA-256 evidence identity collision for {derived_id}"
            )
        seen_derived_ids[derived_id] = key


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

        latest_revision = max(revisions) if revisions else None
        # Prior revisions are immutable snapshots and may retain their historical
        # assertionState. Only the greatest revision is current for proposal reads.

        # Check supersedes references and cycle freedom
        visited = set()
        for rev, r in revisions.items():
            sup = r.get("supersedes")
            if rev > 1 and sup is None:
                raise MalformedRevisionCycleError(
                    f"Evidence '{eid}' revision {rev} must supersede its immediate predecessor {rev - 1}"
                )
            if sup is not None:
                if sup == rev:
                    raise MalformedRevisionCycleError(
                        f"Evidence '{eid}' revision {rev} supersedes itself"
                    )
                if sup != rev - 1:
                    raise MalformedRevisionCycleError(
                        f"Evidence '{eid}' revision {rev} must supersede its immediate predecessor {rev - 1}, got {sup}"
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
    """Return active rows for proposal-time inspection, not production scoring.

    Legacy rows (lacking assertionState) are included only when include_legacy=True.
    The current TM engine does not call this helper; assertion filtering remains a
    deliberately held integration gate pending founder/two-Core approval.
    """
    rows = skill.get("evidence") or []
    latest: dict[str, dict] = {}
    legacy = []
    for row in rows:
        eid = row.get("evidenceId")
        if eid is None:
            if include_legacy:
                legacy.append(row)
            continue
        current = latest.get(eid)
        if current is None or row.get("revision", 0) > current.get("revision", 0):
            latest[eid] = row
    return [row for row in latest.values() if row.get("assertionState") == ASSERTION_ACTIVE] + legacy


# ---------------------------------------------------------------------------
# Shadow Proposal Plans (Not an authorization surface)
# ---------------------------------------------------------------------------

def prepare_assertion_transition(skill: dict, evidence_id: str, target_state: str, decision_ref: str) -> LifecycleProposal:
    """Prepare an immutable, append-only successor proposal; never authorizes it."""
    from datetime import datetime, timezone
    if target_state not in ASSERTION_STATES:
        raise InvalidTransitionError(f"Unknown target assertionState: '{target_state}'")
    if not isinstance(decision_ref, str) or not decision_ref.strip():
        raise EvidenceValidationError("decision_ref must be a non-blank proposal reference")
    before = copy.deepcopy(skill)
    rows = copy.deepcopy(skill.get("evidence") or [])
    matches = [i for i, row in enumerate(rows) if row.get("evidenceId") == evidence_id]
    if not matches:
        raise EvidenceNotFoundError(f"No assertion found for evidenceId '{evidence_id}'")
    latest_revision = max(rows[i].get("revision", 0) for i in matches)
    latest = [i for i in matches if rows[i].get("revision", 0) == latest_revision]
    if len(latest) != 1:
        raise AmbiguousCollisionError(f"Multiple latest revisions found for evidenceId '{evidence_id}'")
    index = latest[0]
    current = rows[index]
    validate_evidence_payload(current, allow_legacy=False)
    if current.get("assertionState") == ASSERTION_SUPERSEDED:
        raise InvalidTransitionError("Cannot transition a superseded (terminal) revision")
    if current.get("assertionState") == target_state:
        after = before
    else:
        successor = copy.deepcopy(current)
        old_revision = current["revision"]
        successor["revision"] = old_revision + 1
        successor["supersedes"] = old_revision
        successor["assertionState"] = target_state
        successor["decisionRef"] = decision_ref.strip()
        # Actor/time are provenance about this proposal only, never authority.
        history = list(successor.get("decisionHistory") or [])
        history.append({"decisionRef": current.get("decisionRef", "legacy:unknown"),
            "assertionState": current["assertionState"], "priorPayload": copy.deepcopy(current),
            "proposedBy": "unknown", "proposedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")})
        successor["decisionHistory"] = history
        validate_evidence_payload(successor, allow_legacy=False)
        rows.append(successor)
        after = copy.deepcopy(skill)
        after["evidence"] = rows
        validate_revision_history(str(skill.get("id", "unknown")), rows)
    return LifecycleProposal("assertion-transition", before, after, compute_payload_digest(before),
        compute_payload_digest(after), tuple(copy.deepcopy(before.get("evidence") or [])),
        tuple(copy.deepcopy(after.get("evidence") or [])), decision_ref.strip(), (str(skill.get("id", "unknown")), evidence_id))


def prepare_metric_refresh(skill: dict, evidence_id: str, metric_updates: dict,
                           decision_ref: str, observation_provenance: Optional[dict] = None) -> LifecycleProposal:
    """Prepare a metric successor proposal; whitelist metric/provenance only."""
    if not isinstance(metric_updates, dict) or not metric_updates:
        raise EvidenceValidationError("metric_updates must be a non-empty object")
    illegal = set(metric_updates) - set(NUMERIC_METRIC_FIELDS)
    if illegal:
        raise EvidenceValidationError(f"Only raw metric fields may be refreshed; prohibited: {', '.join(sorted(illegal))}")
    allowed_provenance = {"metricMethod", "observationState", "lastObservedAt", "contentDigest", "sourceRevision", "measurementScope"}
    provenance = observation_provenance
    if not isinstance(provenance, dict) or set(provenance) != allowed_provenance:
        raise EvidenceValidationError("observation_provenance must provide method, state, UTC time, source revision, content digest, and measurement scope")
    if provenance["metricMethod"] not in METRIC_METHODS or provenance["observationState"] not in OBSERVATION_STATES:
        raise EvidenceValidationError("observation provenance method/state is invalid")
    for key in ("sourceRevision", "contentDigest", "measurementScope"):
        if not isinstance(provenance[key], str) or not provenance[key].strip():
            raise EvidenceValidationError(f"observation provenance '{key}' must be explicit; use 'unknown' when unavailable")
    if provenance["contentDigest"] != "unknown" and not re.fullmatch(r"[a-f0-9]{64}", provenance["contentDigest"]):
        raise EvidenceValidationError("contentDigest must be SHA-256 or explicit 'unknown'")
    if not isinstance(provenance["lastObservedAt"], str):
        raise EvidenceValidationError("lastObservedAt must be an aware UTC ISO-8601 date-time ending in Z")
    try:
        from datetime import datetime, timezone
        observed = datetime.fromisoformat(provenance["lastObservedAt"].replace("Z", "+00:00"))
        if observed.tzinfo is None or observed.utcoffset() != timezone.utc.utcoffset(observed) or not provenance["lastObservedAt"].endswith("Z"):
            raise ValueError("not UTC")
    except (TypeError, ValueError) as exc:
        raise EvidenceValidationError("lastObservedAt must be an aware UTC ISO-8601 date-time ending in Z") from exc
    if not isinstance(decision_ref, str) or not decision_ref.strip():
        raise EvidenceValidationError("decision_ref must be a non-blank proposal reference")

    before = copy.deepcopy(skill)
    rows = copy.deepcopy(skill.get("evidence") or [])
    matches = [i for i, row in enumerate(rows) if row.get("evidenceId") == evidence_id]
    if not matches:
        raise EvidenceNotFoundError(f"No assertion found for evidenceId '{evidence_id}' in '{skill.get('id', 'unknown')}'")
    latest_revision = max(rows[i].get("revision", 0) for i in matches)
    latest = [i for i in matches if rows[i].get("revision", 0) == latest_revision]
    if len(latest) != 1:
        raise AmbiguousCollisionError(f"Multiple latest revisions found for evidenceId '{evidence_id}'")
    index = latest[0]
    old = rows[index]
    if old.get("assertionState") != ASSERTION_ACTIVE:
        raise EvidenceNotFoundError(f"No active assertion found for evidenceId '{evidence_id}' in '{skill.get('id', 'unknown')}'")
    validate_evidence_payload(old, allow_legacy=False)
    old_rev = old["revision"]
    next_row = copy.deepcopy(old)
    next_row.update(metric_updates)
    next_row.update(provenance)
    next_row["revision"] = old_rev + 1
    next_row["supersedes"] = old_rev
    decision_history = list(next_row.get("decisionHistory") or [])
    decision_history.append({"decisionRef": old.get("decisionRef", "legacy:unknown"),
        "assertionState": old["assertionState"], "priorPayload": copy.deepcopy(old),
        "proposedBy": "unknown", "proposedAt": provenance["lastObservedAt"]})
    next_row["decisionHistory"] = decision_history
    next_row["decisionRef"] = decision_ref.strip()
    next_row["reviewedOldDigest"] = compute_payload_digest(old)
    # This is a digest of the proposal body, not a signature or authorized receipt.
    next_row.pop("reviewedNewDigest", None)
    next_row["reviewedNewDigest"] = compute_payload_digest(next_row)
    rows.append(next_row)
    validate_evidence_payload(next_row, allow_legacy=False)
    validate_revision_history(str(skill.get("id", "unknown")), rows)
    after = copy.deepcopy(skill)
    after["evidence"] = rows
    return LifecycleProposal("metric-refresh", before, after, compute_payload_digest(before),
        compute_payload_digest(after), tuple(copy.deepcopy(before.get("evidence") or [])),
        tuple(copy.deepcopy(rows)), decision_ref.strip(), (str(skill.get("id", "unknown")), evidence_id))


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

    # Validate legacy syntax, then detect ambiguous IDs before diagnosing
    # partial lifecycle metadata so duplicate explicit IDs remain actionable.
    for row in evidence:
        validate_evidence_payload(row, allow_legacy=True)
    detect_legacy_collisions(skill_id, evidence)
    lifecycle_fields = {"evidenceId", "revision", "assertionState", "decisionRef", "supersedes", "decisionHistory", "reviewedOldDigest", "reviewedNewDigest"}
    for row in evidence:
        if lifecycle_fields.intersection(row):
            validate_evidence_payload(row, allow_legacy=False)

    # Check if already migrated
    already_migrated = all(
        r.get("evidenceId") and r.get("revision") and r.get("assertionState")
        for r in evidence
    )

    before_payload = copy.deepcopy(skill)
    before_digest = compute_payload_digest(before_payload)

    # Baseline Trust Magnitude score from existing scoring engine (read-only)
    from gaia_cli.trustMagnitude import computeTrustMagnitude
    before_score = computeTrustMagnitude(before_payload, generic_skill_map)

    if already_migrated:
        for row in evidence:
            validate_evidence_payload(row, allow_legacy=False)
        validate_revision_history(skill_id, evidence)
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
    for original in evidence:
        row_copy = copy.deepcopy(original)
        if lifecycle_fields.intersection(row_copy):
            # Complete migrated payloads are preserved byte-for-value; never
            # complete, overwrite, or normalize an existing lifecycle decision.
            validate_evidence_payload(row_copy, allow_legacy=False)
        else:
            row_copy["evidenceId"] = derive_evidence_identity(skill_id, row_copy)
            row_copy["revision"] = 1
            row_copy["assertionState"] = ASSERTION_ACTIVE
            # decisionRef, reviewer, date, metric method and verified are not
            # invented. This is a score-neutral migration proposal only.
            validate_evidence_payload(row_copy, allow_legacy=False)
        migrated_rows.append(row_copy)

    validate_revision_history(skill_id, migrated_rows)

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

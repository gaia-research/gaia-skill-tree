"""Pure Yggdrasil IV challenge lifecycle primitives.

This module models observations, public technical proceedings, and numeric
proposals separately. It performs no persistence, network, model, scoring, or
canonical registry operations; callers own those boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any
from urllib.parse import urlparse


class ChallengeStatus(str, Enum):
    VERIFIED_PENDING = "verified-pending"
    UPHELD = "upheld"
    NARROWED = "narrowed"
    TECHNICALLY_REBUTTED = "technically-rebutted"
    RESOLVED_BY_UPSTREAM_IMPROVEMENT = "resolved-by-upstream-improvement"
    REJECTED = "rejected"


class ObservationState(str, Enum):
    UNKNOWN = "unknown"
    REACHABLE = "reachable"
    TRANSIENT_FAILURE = "transient-failure"
    UNAVAILABLE = "unavailable"
    CHANGED = "changed"


class NumericProposalState(str, Enum):
    SHADOW = "shadow"
    AWAITING_APPROVAL = "awaiting-approval"
    APPROVED_PUBLISHED = "approved-published"


class ClosureDisposition(str, Enum):
    CLOSED = "closed"
    CLASS_C = "class-c"


@dataclass(frozen=True)
class Observation:
    subject_id: str
    observed_at_utc: str
    state: ObservationState
    source_version: str | None = None
    source_sha: str | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        _required(self.subject_id, "subject_id")
        _utc(self.observed_at_utc)
        if self.source_sha is not None:
            _required(self.source_sha, "source_sha")

    @property
    def observation_id(self) -> str:
        return _digest(_canonical(self))


@dataclass(frozen=True)
class ChallengeEvent:
    event_type: str
    at_utc: str
    actor: str
    details: str = ""
    linked_challenge_id: str | None = None

    @property
    def event_id(self) -> str:
        return _digest(_canonical(self))

    def __post_init__(self) -> None:
        _required(self.event_type, "event_type")
        _required(self.actor, "actor")
        _utc(self.at_utc)


@dataclass(frozen=True)
class Challenge:
    claim_id: str
    subject_id: str
    claim: str
    behavior_id: str
    contributor_id: str
    contributor_notice_ref: str
    pinned_version: str
    pinned_sha: str
    environment: str
    test_version: str
    baseline: str
    comparator: str
    status: ChallengeStatus
    material_to_origin: bool
    created_at_utc: str
    history: tuple[ChallengeEvent, ...]
    challenge_id: str = ""
    linked_challenge_id: str | None = None

    def __post_init__(self) -> None:
        for field in ("claim_id", "subject_id", "claim", "behavior_id", "contributor_id",
                      "pinned_version", "pinned_sha", "environment", "test_version",
                      "baseline", "comparator"):
            _required(getattr(self, field), field)
        _public_ref(self.contributor_notice_ref, "contributor_notice_ref")
        _utc(self.created_at_utc)
        if not self.history:
            raise ValueError("challenge history must preserve at least its opening event")
        if not self.challenge_id:
            object.__setattr__(self, "challenge_id", _digest(_canonical({
                "claimId": self.claim_id, "subjectId": self.subject_id,
                "claim": self.claim, "behaviorId": self.behavior_id,
                "contributorId": self.contributor_id,
                "contributorNoticeRef": self.contributor_notice_ref,
                "pinnedVersion": self.pinned_version, "pinnedSha": self.pinned_sha,
                "environment": self.environment, "testVersion": self.test_version,
                "baseline": self.baseline, "comparator": self.comparator,
                "materialToOrigin": self.material_to_origin,
                "createdAtUTC": self.created_at_utc,
                "linkedChallengeId": self.linked_challenge_id,
            })))

    @property
    def resolved(self) -> bool:
        return self.status in {
            ChallengeStatus.TECHNICALLY_REBUTTED,
            ChallengeStatus.RESOLVED_BY_UPSTREAM_IMPROVEMENT,
            ChallengeStatus.REJECTED,
        }


@dataclass(frozen=True)
class TechnicalProof:
    claim_id: str
    behavior_id: str
    prior_version: str
    prior_sha: str
    current_version: str
    current_sha: str
    environment: str
    test_version: str
    baseline: str
    comparator: str
    actual_output: str
    verifier_id: str
    contributor_id: str
    builder_id: str
    verification_result: str
    verification_method: str
    public_receipt_ref: str
    contributor_notice_ref: str
    verified_at_utc: str
    upstream_improvement: bool = False

    @property
    def proof_digest(self) -> str:
        return _digest(_canonical(self))

    def __post_init__(self) -> None:
        # Proof packets may be incomplete; closure classifies gaps as Class C
        # rather than treating a malformed packet as an exceptional success path.
        _utc(self.verified_at_utc)


@dataclass(frozen=True)
class ClosureResult:
    disposition: ClosureDisposition
    challenge: Challenge
    reason: str
    contested: bool


@dataclass(frozen=True)
class NumericProposal:
    """Numeric reassessment state only; never calculates or publishes scores."""
    proposal_id: str
    challenge_id: str
    state: NumericProposalState
    payload_digest: str
    created_at_utc: str

    def __post_init__(self) -> None:
        for field in ("proposal_id", "challenge_id", "payload_digest"):
            _required(getattr(self, field), field)
        _utc(self.created_at_utc)


def open_challenge(*, subject_id: str, claim_id: str, claim: str, behavior_id: str,
                   contributor_id: str, contributor_notice_ref: str,
                   pinned_version: str, pinned_sha: str, environment: str,
                   test_version: str, baseline: str, comparator: str,
                   verified_at_utc: str, verifier_id: str, material_to_origin: bool,
                   linked_challenge_id: str | None = None) -> Challenge:
    """Create an independently verified public challenge and its opening event."""
    _required(verifier_id, "verifier_id")
    if verifier_id == contributor_id:
        raise ValueError("challenge verifier must be independent of contributor")
    event = ChallengeEvent("verified-publication", verified_at_utc, verifier_id,
                           "public challenge opened; contributor notified", linked_challenge_id)
    return Challenge(claim_id, subject_id, claim, behavior_id, contributor_id,
                     contributor_notice_ref, pinned_version, pinned_sha, environment,
                     test_version, baseline, comparator, ChallengeStatus.VERIFIED_PENDING,
                     material_to_origin, verified_at_utc, (event,),
                     linked_challenge_id=linked_challenge_id)


def close_technical_challenge(challenge: Challenge, proof: TechnicalProof,
                              *, closed_at_utc: str) -> ClosureResult:
    """Close only complete, same-behavior independent proof; otherwise Class C."""
    _utc(closed_at_utc)
    reason = _proof_failure(challenge, proof)
    if reason:
        return ClosureResult(ClosureDisposition.CLASS_C, challenge, reason,
                             challenge.material_to_origin and not challenge.resolved)
    status = (ChallengeStatus.RESOLVED_BY_UPSTREAM_IMPROVEMENT if proof.upstream_improvement
              else ChallengeStatus.TECHNICALLY_REBUTTED)
    event = ChallengeEvent("technical-resolution", closed_at_utc, proof.verifier_id,
                           proof.public_receipt_ref)
    updated = replace(challenge, status=status, history=challenge.history + (event,))
    return ClosureResult(ClosureDisposition.CLOSED, updated, "complete independent proof",
                         updated.material_to_origin and not updated.resolved)


def create_numeric_proposal(*, challenge_id: str, state: NumericProposalState,
                            payload_digest: str, created_at_utc: str) -> NumericProposal:
    """Create a stable numeric proposal marker without interpreting its payload."""
    identity = _digest(_canonical({"challengeId": challenge_id, "state": state,
                                   "payloadDigest": payload_digest,
                                   "createdAtUTC": created_at_utc}))
    return NumericProposal(identity, challenge_id, state, payload_digest, created_at_utc)


def origin_contested(challenges: tuple[Challenge, ...]) -> bool:
    """Derived marker: any unresolved material challenge keeps it contested."""
    return any(item.material_to_origin and not item.resolved for item in challenges)


def link_reopened_challenge(previous: Challenge, new_challenge: Challenge) -> Challenge:
    """Require reopening as a distinct challenge linked to immutable history."""
    if new_challenge.challenge_id == previous.challenge_id:
        raise ValueError("reopening requires a distinct new challenge ID")
    if new_challenge.linked_challenge_id != previous.challenge_id:
        raise ValueError("new challenge must link to the prior challenge")
    return new_challenge


def _proof_failure(challenge: Challenge, proof: TechnicalProof) -> str:
    required = ("claim_id", "behavior_id", "prior_version", "prior_sha", "current_version",
                "current_sha", "environment", "test_version", "baseline", "comparator",
                "actual_output", "verifier_id", "contributor_id", "builder_id",
                "verification_result", "verification_method")
    if any(not isinstance(getattr(proof, field), str) or not getattr(proof, field).strip()
           for field in required):
        return "technical proof is missing required fields"
    try:
        _public_ref(proof.public_receipt_ref, "public_receipt_ref")
        _public_ref(proof.contributor_notice_ref, "contributor_notice_ref")
    except ValueError:
        return "public linked receipt and contributor notification are required"
    if challenge.status != ChallengeStatus.VERIFIED_PENDING:
        return "challenge is not open for technical closure"
    if proof.claim_id != challenge.claim_id or proof.behavior_id != challenge.behavior_id:
        return "proof does not address the same pinned claim and behavior"
    if proof.contributor_id != challenge.contributor_id:
        return "proof contributor conflicts with challenge provenance"
    if proof.verifier_id in {proof.contributor_id, proof.builder_id}:
        return "independent verifier must differ from contributor and builder"
    if proof.verification_method.lower() in {"model", "llm", "model-only", "semantic-model"}:
        return "model-only verification is insufficient"
    if proof.verification_result.lower() not in {"pass", "passed", "verified"}:
        return "verification did not pass"
    if not proof.prior_version or not proof.prior_sha or not proof.current_version or not proof.current_sha:
        return "prior and current version/SHA are required"
    if not proof.environment or not proof.test_version or not proof.baseline or not proof.comparator:
        return "equivalent environment, test version, baseline, and comparator are required"
    if not proof.actual_output.strip():
        return "actual output is missing"
    if (proof.prior_version, proof.prior_sha, proof.environment, proof.test_version,
            proof.baseline, proof.comparator) != (
            challenge.pinned_version, challenge.pinned_sha, challenge.environment,
            challenge.test_version, challenge.baseline, challenge.comparator):
        return "proof conflicts with pinned version/SHA or comparison conditions"
    if proof.prior_sha == proof.current_sha and proof.upstream_improvement:
        return "upstream improvement must identify a changed source SHA"
    return ""


def _required(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")


def _utc(value: str) -> datetime:
    _required(value, "UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise ValueError("timestamp must be ISO-8601 UTC") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp must be explicitly UTC")
    return parsed.astimezone(timezone.utc)


def _public_ref(value: str, field: str) -> None:
    _required(value, field)
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{field} must be a public HTTPS reference")


def _canonical(value: Any) -> str:
    def normalized(item: Any) -> Any:
        if hasattr(item, "value"):
            return item.value
        if hasattr(item, "__dataclass_fields__"):
            return {key: normalized(val) for key, val in item.__dict__.items()}
        if isinstance(item, dict):
            return {key: normalized(val) for key, val in sorted(item.items())}
        if isinstance(item, (tuple, list)):
            return [normalized(val) for val in item]
        return item
    return json.dumps(normalized(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

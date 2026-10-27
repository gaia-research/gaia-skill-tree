"""Pure Yggdrasil IV challenge lifecycle primitives.

The ``VerificationReceiptResolver`` is a REQUIRED trusted in-process boundary:
callers must resolve an immutable Steward receipt that binds exact context and
transcript digests. Serialized packets, raw flags, URLs and Python constructors
are not a security sandbox or proof of human/cryptographic authority. This
module does not fetch URLs, authenticate humans, or persist receipts.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Protocol
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

    @property
    def observation_id(self) -> str:
        return _digest(_canonical(self))


@dataclass(frozen=True)
class VerificationReceipt:
    """Immutable resolver output, not an untrusted packet assertion.

    ``context_digest`` binds exact proceeding/draft identity; ``transcript_digest``
    binds the canonical reproducible payload. The trusted adapter is responsible
    for establishing receipt provenance and immutability.
    """
    receipt_id: str
    context_digest: str
    transcript_digest: str
    verifier_id: str
    builder_id: str
    contributor_id: str
    result: str
    method: str
    method_version: str
    actual_output: str
    output_digest: str
    public_receipt_ref: str
    notice_ref: str
    verified_at_utc: str

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            _required(getattr(self, name), name)
        _utc(self.verified_at_utc)
        _public_ref(self.public_receipt_ref, "public_receipt_ref")
        _public_ref(self.notice_ref, "notice_ref")


class VerificationReceiptResolver(Protocol):
    """Challenge-bindable trusted resolver.

    ``for_challenge`` must return a resolver bound to exactly that challenge id
    (exposing it as ``challenge_id``); the domain never calls an unbound resolver.
    """
    def for_challenge(self, challenge_id: str) -> "BoundVerificationReceiptResolver": ...


class BoundVerificationReceiptResolver(Protocol):
    challenge_id: str

    def resolve(self, receipt_id: str) -> VerificationReceipt: ...


@dataclass(frozen=True)
class ChallengeEvent:
    event_type: str
    at_utc: str
    actor: str
    details: str = ""
    challenge_id: str = ""
    receipt_id: str = ""
    receipt_digest: str = ""
    transcript_digest: str = ""
    notice_ref: str = ""
    method: str = ""
    method_version: str = ""
    actual_output: str = ""
    output_digest: str = ""
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
    history_digest: str = ""

    def __post_init__(self) -> None:
        for field in ("claim_id", "subject_id", "claim", "behavior_id", "contributor_id",
                      "pinned_version", "pinned_sha", "environment", "test_version",
                      "baseline", "comparator"):
            _required(getattr(self, field), field)
        _public_ref(self.contributor_notice_ref, "contributor_notice_ref")
        _utc(self.created_at_utc)
        expected = _challenge_id(self)
        if not self.challenge_id:
            object.__setattr__(self, "challenge_id", expected)
        elif self.challenge_id != expected:
            raise ValueError("challenge_id does not match immutable challenge context")
        expected_history = _digest(_canonical(self.history))
        if not self.history_digest:
            object.__setattr__(self, "history_digest", expected_history)
        elif self.history_digest != expected_history:
            raise ValueError("challenge history digest mismatch")
        validate_challenge_history(self)

    @property
    def resolved(self) -> bool:
        return self.status in {ChallengeStatus.TECHNICALLY_REBUTTED,
                               ChallengeStatus.RESOLVED_BY_UPSTREAM_IMPROVEMENT,
                               ChallengeStatus.REJECTED}


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
    challenge_id: str = ""
    method_version: str = ""
    output_digest: str = ""
    pinned_sha_known: bool = True
    comparator_known: bool = True

    @property
    def proof_digest(self) -> str:
        return _digest(_canonical(self))

    def __post_init__(self) -> None:
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


def open_challenge(*, receipt_resolver: VerificationReceiptResolver | None = None,
                   verification_receipt_id: str = "", subject_id: str, claim_id: str,
                   claim: str, behavior_id: str, contributor_id: str,
                   contributor_notice_ref: str, pinned_version: str, pinned_sha: str,
                   environment: str, test_version: str, baseline: str, comparator: str,
                   verified_at_utc: str, verifier_id: str, material_to_origin: bool,
                   linked_challenge_id: str | None = None) -> Challenge:
    """Open only after a trusted resolver validates a reproducible receipt."""
    if receipt_resolver is None:
        raise ValueError("trusted verification receipt resolver is required")
    _public_ref(contributor_notice_ref, "contributor_notice_ref")
    draft = {"subject_id": subject_id, "claim_id": claim_id, "claim": claim,
             "behavior_id": behavior_id, "contributor_id": contributor_id,
             "contributor_notice_ref": contributor_notice_ref,
             "pinned_version": pinned_version, "pinned_sha": pinned_sha,
             "environment": environment, "test_version": test_version,
             "baseline": baseline, "comparator": comparator,
             "material_to_origin": material_to_origin, "created_at_utc": verified_at_utc,
             "linked_challenge_id": linked_challenge_id}
    context = _digest(_canonical(draft))
    challenge_id = _challenge_id_from_draft(draft)
    receipt = _resolve(receipt_resolver, verification_receipt_id, challenge_id)
    receipt_error = _validate_receipt(receipt, context_digest=context, transcript_digest=None,
                      verifier_id=verifier_id, contributor_id=contributor_id,
                      notice_ref=contributor_notice_ref, at=verified_at_utc)
    if receipt_error:
        raise ValueError(receipt_error)
    if receipt.verifier_id in {receipt.builder_id, contributor_id}:
        raise ValueError("challenge verifier must be independent of builder and contributor")
    event = _receipt_event("verified-publication", receipt, challenge_id,
                           "public challenge opened", verified_at_utc)
    return Challenge(claim_id, subject_id, claim, behavior_id, contributor_id,
                     contributor_notice_ref, pinned_version, pinned_sha, environment,
                     test_version, baseline, comparator, ChallengeStatus.VERIFIED_PENDING,
                     material_to_origin, verified_at_utc, (event,), linked_challenge_id=linked_challenge_id)


def close_technical_challenge(challenge: Challenge, proof: TechnicalProof,
                              *, closed_at_utc: str,
                              receipt_resolver: VerificationReceiptResolver | None = None,
                              verification_receipt_id: str = "") -> ClosureResult:
    """Close only with receipt-authorized, exact-challenge reproducible proof."""
    closed_at = _utc(closed_at_utc)
    if receipt_resolver is None:
        return _class_c(challenge, "trusted verification receipt resolver is required")
    # An exact replay of the already approved closure is idempotent; it does not
    # append a second history event. A different proof remains a Class C case.
    if challenge.resolved:
        if len(challenge.history) == 2:
            event = challenge.history[-1]
            try:
                receipt = _resolve(receipt_resolver, verification_receipt_id, challenge.challenge_id)
            except (KeyError, ValueError) as exc:
                return _class_c(challenge, f"trusted receipt unavailable: {exc}")
            if (_proof_failure(challenge, proof, allow_resolved_replay=True)
                    or event.receipt_id != receipt.receipt_id
                    or event.receipt_digest != _digest(_canonical(receipt))
                    or event.transcript_digest != proof.proof_digest
                    or receipt.transcript_digest != proof.proof_digest
                    or event.challenge_id != challenge.challenge_id
                    or event.actor != receipt.verifier_id
                    or event.notice_ref != receipt.notice_ref
                    or event.method != receipt.method
                    or event.method_version != receipt.method_version
                    or event.actual_output != receipt.actual_output
                    or event.output_digest != receipt.output_digest
                    or event.at_utc != closed_at_utc
                    or _utc(event.at_utc) < max(_utc(challenge.created_at_utc),
                                                  _utc(receipt.verified_at_utc))):
                return _class_c(challenge, "resolved challenge requires an exact approved receipt replay or a linked new challenge")
            replay_context = _digest(_canonical({"challenge_id": challenge.challenge_id,
                "claim_id": challenge.claim_id, "behavior_id": challenge.behavior_id,
                "pinned_version": challenge.pinned_version, "pinned_sha": challenge.pinned_sha,
                "environment": challenge.environment, "test_version": challenge.test_version,
                "baseline": challenge.baseline, "comparator": challenge.comparator}))
            reason = _validate_receipt(receipt, context_digest=replay_context,
                transcript_digest=proof.proof_digest, verifier_id=proof.verifier_id,
                contributor_id=challenge.contributor_id,
                notice_ref=proof.contributor_notice_ref, at=proof.verified_at_utc)
            if reason or receipt.verifier_id in {receipt.builder_id, receipt.contributor_id}:
                return _class_c(challenge, reason or "receipt verifier must be independent of builder and contributor")
            disposition = ClosureDisposition.CLOSED
            return ClosureResult(disposition, challenge, "exact approved receipt replay (idempotent)",
                                 challenge.material_to_origin and not challenge.resolved)
        return _class_c(challenge, "resolved challenge requires a linked new challenge")
    reason = _proof_failure(challenge, proof)
    if reason:
        return _class_c(challenge, reason)
    try:
        receipt = _resolve(receipt_resolver, verification_receipt_id, challenge.challenge_id)
    except (KeyError, ValueError) as exc:
        return _class_c(challenge, f"trusted receipt unavailable: {exc}")
    context = _digest(_canonical({"challenge_id": challenge.challenge_id,
                                  "claim_id": challenge.claim_id,
                                  "behavior_id": challenge.behavior_id,
                                  "pinned_version": challenge.pinned_version,
                                  "pinned_sha": challenge.pinned_sha,
                                  "environment": challenge.environment,
                                  "test_version": challenge.test_version,
                                  "baseline": challenge.baseline,
                                  "comparator": challenge.comparator}))
    reason = _validate_receipt(receipt, context_digest=context,
                               transcript_digest=proof.proof_digest,
                               verifier_id=proof.verifier_id,
                               contributor_id=challenge.contributor_id,
                               notice_ref=proof.contributor_notice_ref, at=proof.verified_at_utc)
    if reason:
        return _class_c(challenge, reason)
    if receipt.method.lower() not in {"reproducible-test", "benchmark-replay", "cli-replay"}:
        return _class_c(challenge, "verification receipt method is not an approved reproducible method")
    if receipt.verifier_id in {receipt.builder_id, receipt.contributor_id}:
        return _class_c(challenge, "receipt verifier must be independent of builder and contributor")
    if closed_at < max(_utc(challenge.created_at_utc), _utc(receipt.verified_at_utc)):
        return _class_c(challenge, "closure cannot predate opening or proof verification")
    status = (ChallengeStatus.RESOLVED_BY_UPSTREAM_IMPROVEMENT if proof.upstream_improvement
              else ChallengeStatus.TECHNICALLY_REBUTTED)
    event = _receipt_event("technical-resolution", receipt, challenge.challenge_id,
                           "same-challenge reproducible technical resolution", closed_at_utc)
    updated = replace(challenge, status=status, history=challenge.history + (event,), history_digest="")
    return ClosureResult(ClosureDisposition.CLOSED, updated, "trusted independent proof receipt",
                         updated.material_to_origin and not updated.resolved)


def create_numeric_proposal(*, challenge_id: str, state: NumericProposalState,
                            payload_digest: str, created_at_utc: str) -> NumericProposal:
    identity = _digest(_canonical({"challengeId": challenge_id, "state": state,
                                   "payloadDigest": payload_digest, "createdAtUTC": created_at_utc}))
    return NumericProposal(identity, challenge_id, state, payload_digest, created_at_utc)


def origin_contested(challenges: tuple[Challenge, ...]) -> bool:
    return any(item.material_to_origin and not item.resolved for item in challenges)


def link_reopened_challenge(previous: Challenge, new_challenge: Challenge) -> Challenge:
    if not previous.resolved:
        raise ValueError("only a resolved challenge may be reopened as a linked proceeding")
    if new_challenge.challenge_id == previous.challenge_id:
        raise ValueError("reopening requires a distinct new challenge ID")
    if new_challenge.linked_challenge_id != previous.challenge_id:
        raise ValueError("new challenge must link to the prior challenge")
    return new_challenge


def validate_challenge_history(challenge: Challenge,
                               receipt_resolver: VerificationReceiptResolver | None = None) -> None:
    """Validate structure and, when rehydrating, resolve every immutable receipt.

    Serialized data must go through this function with the trusted resolver;
    constructor validation alone is intentionally not an authority boundary.
    """
    if not challenge.history:
        raise ValueError("challenge history must preserve its opening event")
    first = challenge.history[0]
    if (first.event_type != "verified-publication" or first.challenge_id != challenge.challenge_id
            or not first.receipt_id or not first.receipt_digest or not first.transcript_digest):
        raise ValueError("opening history must contain a bound verification receipt")
    if len(challenge.history) > 2:
        raise ValueError("unsupported challenge history transition")
    if len(challenge.history) == 1:
        if challenge.status is not ChallengeStatus.VERIFIED_PENDING:
            raise ValueError("status does not match append-only history")
    else:
        last = challenge.history[-1]
        if (last.event_type != "technical-resolution" or last.challenge_id != challenge.challenge_id
                or not last.receipt_id or not last.receipt_digest or not last.transcript_digest
                or _utc(last.at_utc) < _utc(first.at_utc)):
            raise ValueError("invalid technical-resolution history event")
        if challenge.status not in {ChallengeStatus.TECHNICALLY_REBUTTED,
                                    ChallengeStatus.RESOLVED_BY_UPSTREAM_IMPROVEMENT}:
            raise ValueError("status does not match authorized technical history")
    if receipt_resolver is not None:
        for event in challenge.history:
            receipt = _resolve(receipt_resolver, event.receipt_id, challenge.challenge_id)
            if (_digest(_canonical(receipt)) != event.receipt_digest
                    or receipt.transcript_digest != event.transcript_digest
                    or event.challenge_id != challenge.challenge_id
                    or receipt.verifier_id != event.actor
                    or receipt.notice_ref != event.notice_ref
                    or receipt.method != event.method
                    or receipt.method_version != event.method_version
                    or receipt.actual_output != event.actual_output
                    or receipt.output_digest != event.output_digest):
                raise ValueError("history event does not match its resolved immutable receipt")
            if (receipt.result.lower() not in {"pass", "passed", "verified"}
                    or receipt.method.lower() not in {"reproducible-test", "benchmark-replay", "cli-replay"}
                    or not isinstance(receipt.builder_id, str)
                    or not receipt.builder_id.strip()
                    or receipt.verifier_id in {receipt.builder_id, receipt.contributor_id}):
                raise ValueError("history receipt lacks independent passing reproducible verification")
            if _utc(event.at_utc) < _utc(receipt.verified_at_utc):
                raise ValueError("history event cannot predate receipt verification")
            if event.event_type == "verified-publication" and event.at_utc != challenge.created_at_utc:
                raise ValueError("opening event time must match challenge creation time")
            if event.event_type == "verified-publication":
                context = _digest(_canonical({"subject_id": challenge.subject_id,
                    "claim_id": challenge.claim_id, "claim": challenge.claim,
                    "behavior_id": challenge.behavior_id, "contributor_id": challenge.contributor_id,
                    "contributor_notice_ref": challenge.contributor_notice_ref,
                    "pinned_version": challenge.pinned_version, "pinned_sha": challenge.pinned_sha,
                    "environment": challenge.environment, "test_version": challenge.test_version,
                    "baseline": challenge.baseline, "comparator": challenge.comparator,
                    "material_to_origin": challenge.material_to_origin,
                    "created_at_utc": challenge.created_at_utc,
                    "linked_challenge_id": challenge.linked_challenge_id}))
            else:
                context = _digest(_canonical({"challenge_id": challenge.challenge_id,
                    "claim_id": challenge.claim_id, "behavior_id": challenge.behavior_id,
                    "pinned_version": challenge.pinned_version, "pinned_sha": challenge.pinned_sha,
                    "environment": challenge.environment, "test_version": challenge.test_version,
                    "baseline": challenge.baseline, "comparator": challenge.comparator}))
            if receipt.context_digest != context:
                raise ValueError("history receipt is bound to different challenge context")


def _proof_failure(challenge: Challenge, proof: TechnicalProof, *,
                   allow_resolved_replay: bool = False) -> str:
    if challenge.status is not ChallengeStatus.VERIFIED_PENDING and not allow_resolved_replay:
        return "challenge is not open for technical closure"
    if proof.challenge_id != challenge.challenge_id:
        return "proof does not bind the exact challenge_id"
    if (proof.claim_id, proof.behavior_id) != (challenge.claim_id, challenge.behavior_id):
        return "proof does not address the same pinned claim and behavior"
    if proof.contributor_id != challenge.contributor_id:
        return "proof contributor conflicts with challenge provenance"
    if proof.verifier_id in {proof.contributor_id, proof.builder_id}:
        return "independent verifier must differ from contributor and builder"
    if proof.verification_result.lower() not in {"pass", "passed", "verified"}:
        return "verification did not pass"
    if proof.verification_method.lower() not in {"reproducible-test", "benchmark-replay", "cli-replay"}:
        return "verification method is not an approved reproducible method"
    if not proof.pinned_sha_known or not proof.comparator_known:
        return "unknown pinned baseline or comparator escalates to Class C"
    fields = (proof.prior_version, proof.prior_sha, proof.current_version, proof.current_sha,
              proof.environment, proof.test_version, proof.baseline, proof.comparator,
              proof.actual_output, proof.method_version, proof.output_digest)
    if any(not isinstance(value, str) or not value.strip() for value in fields):
        return "technical proof lacks versioned method, actual output, or output digest"
    if (proof.prior_version, proof.prior_sha, proof.environment, proof.test_version,
        proof.baseline, proof.comparator) != (challenge.pinned_version, challenge.pinned_sha,
        challenge.environment, challenge.test_version, challenge.baseline, challenge.comparator):
        return "proof conflicts with pinned version/SHA or comparison conditions"
    try:
        _public_ref(proof.public_receipt_ref, "public_receipt_ref")
        _public_ref(proof.contributor_notice_ref, "contributor_notice_ref")
    except ValueError:
        return "public linked receipt and contributor notification are required"
    if proof.prior_sha == proof.current_sha and proof.upstream_improvement:
        return "upstream improvement must identify a changed source SHA"
    return ""


def _class_c(challenge: Challenge, reason: str) -> ClosureResult:
    return ClosureResult(ClosureDisposition.CLASS_C, challenge, reason,
                         challenge.material_to_origin and not challenge.resolved)


def _resolve(resolver: VerificationReceiptResolver, receipt_id: str,
             challenge_id: str) -> VerificationReceipt:
    _required(receipt_id, "verification_receipt_id")
    _required(challenge_id, "challenge_id")
    binder = getattr(resolver, "for_challenge", None)
    if not callable(binder):
        raise ValueError("receipt resolver cannot bind to a challenge; refusing unbound resolution")
    bound = binder(challenge_id)
    if getattr(bound, "challenge_id", None) != challenge_id:
        raise ValueError("receipt resolver is not bound to this exact challenge id")
    receipt = bound.resolve(receipt_id)
    if not isinstance(receipt, VerificationReceipt) or receipt.receipt_id != receipt_id:
        raise ValueError("resolver did not return the requested immutable verification receipt")
    return receipt


def _validate_receipt(receipt: VerificationReceipt, *, context_digest: str,
                      transcript_digest: str | None, verifier_id: str,
                      contributor_id: str, notice_ref: str, at: str) -> str:
    if not isinstance(receipt.builder_id, str) or not receipt.builder_id.strip():
        return "verification receipt builder identity is absent or ambiguous"
    if receipt.verifier_id in {receipt.builder_id, contributor_id}:
        return "verification receipt verifier must be independent of builder and contributor"
    if receipt.context_digest != context_digest:
        return "verification receipt is bound to different exact context"
    if transcript_digest is not None and receipt.transcript_digest != transcript_digest:
        return "verification receipt transcript digest does not match proof payload"
    if receipt.verifier_id != verifier_id or receipt.contributor_id != contributor_id:
        return "verification receipt actor identities conflict with proceeding"
    if receipt.notice_ref != notice_ref:
        return "verification receipt notification binding differs"
    if receipt.result.lower() not in {"pass", "passed", "verified"}:
        return "trusted verification receipt did not record a passing result"
    if receipt.method.lower() not in {"reproducible-test", "benchmark-replay", "cli-replay"}:
        return "trusted receipt method is not an approved reproducible method"
    if _utc(receipt.verified_at_utc) > _utc(at):
        return "receipt verification occurs after asserted event time"
    return ""


def _receipt_event(event_type: str, receipt: VerificationReceipt, challenge_id: str,
                   details: str, event_at: str | None = None) -> ChallengeEvent:
    return ChallengeEvent(event_type, event_at or receipt.verified_at_utc, receipt.verifier_id, details,
                          challenge_id, receipt.receipt_id, _digest(_canonical(receipt)),
                          receipt.transcript_digest, receipt.notice_ref, receipt.method,
                          receipt.method_version, receipt.actual_output, receipt.output_digest)


def _challenge_id_from_draft(draft: dict[str, Any]) -> str:
    return _digest(_canonical({"claimId": draft["claim_id"], "subjectId": draft["subject_id"],
        "claim": draft["claim"], "behaviorId": draft["behavior_id"],
        "contributorId": draft["contributor_id"], "contributorNoticeRef": draft["contributor_notice_ref"],
        "pinnedVersion": draft["pinned_version"], "pinnedSha": draft["pinned_sha"],
        "environment": draft["environment"], "testVersion": draft["test_version"],
        "baseline": draft["baseline"], "comparator": draft["comparator"],
        "materialToOrigin": draft["material_to_origin"], "createdAtUTC": draft["created_at_utc"],
        "linkedChallengeId": draft["linked_challenge_id"]}))


def _challenge_id(challenge: Challenge) -> str:
    return _digest(_canonical({"claimId": challenge.claim_id, "subjectId": challenge.subject_id,
        "claim": challenge.claim, "behaviorId": challenge.behavior_id,
        "contributorId": challenge.contributor_id, "contributorNoticeRef": challenge.contributor_notice_ref,
        "pinnedVersion": challenge.pinned_version, "pinnedSha": challenge.pinned_sha,
        "environment": challenge.environment, "testVersion": challenge.test_version,
        "baseline": challenge.baseline, "comparator": challenge.comparator,
        "materialToOrigin": challenge.material_to_origin, "createdAtUTC": challenge.created_at_utc,
        "linkedChallengeId": challenge.linked_challenge_id}))


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
        if isinstance(item, Enum):
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

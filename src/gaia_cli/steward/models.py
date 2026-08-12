"""Small, JSON-serializable contracts used by Gaia Steward.

The contracts deliberately avoid persistence or command behavior.  They are the
stable boundary between sensors, debt reconciliation, and receipts.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


OBSERVATION_SCHEMA = "steward-observation-v1"
DEBT_SCHEMA = "steward-debt-v1"
LEDGER_SCHEMA = "steward-ledger-v1"
RECEIPT_SCHEMA = "steward-receipt-v1"
DISPATCH_PACKET_SCHEMA = "steward-dispatch-packet-v1"
FOUNDER_QUEUE_SCHEMA = "steward-founder-queue-v1"
FOUNDER_DECISION_SCHEMA = "steward-founder-decision-v1"


class AuthorityClass(str, Enum):
    """The maximum authority Steward may assign to a debt kind."""

    A = "A"
    B = "B"
    C = "C"


def stable_json(value: Any) -> str:
    """Return the canonical JSON representation used for semantic identity."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "subject"


def content_hash(value: Any) -> str:
    """Return the full SHA-256 digest for a canonical JSON value."""

    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def normalize_decision_target(value: str) -> str:
    """Normalize an explicit founder decision target without guessing one.

    Targets are identifiers, not prose. Unicode is normalized, case-folded,
    and whitespace is reduced to hyphens. Any remaining ambiguous character
    fails closed instead of silently changing grouping semantics.
    """

    if not isinstance(value, str):
        raise ValueError("decisionTarget must be a string")
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    normalized = re.sub(r"\s+", "-", normalized)
    if not normalized:
        raise ValueError("decisionTarget must be non-empty")
    if len(normalized) > 256:
        raise ValueError("decisionTarget exceeds 256 characters")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9._:/-]*[a-z0-9])?", normalized):
        raise ValueError(
            "decisionTarget must normalize to a lowercase identifier using "
            "letters, digits, '.', '_', ':', '/', or '-'"
        )
    return normalized


@dataclass(frozen=True)
class RoutingBudget:
    """Fixed zero-model ceiling carried by report-only V1 packets."""

    model_calls: int
    max_tokens: int
    max_minutes: int

    def __post_init__(self) -> None:
        for name, value in (
            ("modelCalls", self.model_calls),
            ("maxTokens", self.max_tokens),
            ("maxMinutes", self.max_minutes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value != 0:
                raise ValueError(f"routing budget {name} must be zero in report-only V1")

    def to_dict(self) -> dict[str, int]:
        return {
            "modelCalls": self.model_calls,
            "maxTokens": self.max_tokens,
            "maxMinutes": self.max_minutes,
        }


@dataclass(frozen=True)
class DispatchPacket:
    """A deterministic Class B work packet. It never executes its contents."""

    dispatch_id: str
    debt: Mapping[str, Any]
    evidence: Mapping[str, Any]
    authority: AuthorityClass
    rule: str
    routine: str
    objective: str
    allowed_paths: tuple[str, ...]
    allowed_commands: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    proof: tuple[str, ...]
    budget: RoutingBudget

    def __post_init__(self) -> None:
        if self.authority is not AuthorityClass.B:
            raise ValueError("dispatch packets are restricted to Class B debt")
        if not self.dispatch_id.startswith("dispatch-"):
            raise ValueError("dispatchId must be a stable dispatch identifier")
        for name, value in (
            ("rule", self.rule),
            ("routine", self.routine),
            ("objective", self.objective),
        ):
            if not value.strip():
                raise ValueError(f"dispatch packet {name} must be non-empty")
        for name, values in (
            ("allowedPaths", self.allowed_paths),
            ("allowedCommands", self.allowed_commands),
            ("forbiddenPaths", self.forbidden_paths),
            ("stopConditions", self.stop_conditions),
            ("proof", self.proof),
        ):
            if not values or any(not item.strip() for item in values):
                raise ValueError(f"dispatch packet {name} must be a non-empty string list")
        stable_json(self.debt)
        stable_json(self.evidence)

    @classmethod
    def create(
        cls,
        *,
        debt: Mapping[str, Any],
        evidence: Mapping[str, Any],
        authority: AuthorityClass,
        rule: str,
        routine: str,
        objective: str,
        allowed_paths: tuple[str, ...],
        allowed_commands: tuple[str, ...],
        forbidden_paths: tuple[str, ...],
        stop_conditions: tuple[str, ...],
        proof: tuple[str, ...],
        budget: RoutingBudget,
    ) -> "DispatchPacket":
        # A packet remains the same requested work when its evidence refreshes.
        # Content is separately hashed below so receipts can still attest to the
        # exact rendering that was reviewed.
        semantic_identity = {
            "schemaVersion": DISPATCH_PACKET_SCHEMA,
            "debtId": debt.get("id"),
            "authority": authority.value,
            "rule": rule,
        }
        if not isinstance(semantic_identity["debtId"], str) or not semantic_identity["debtId"]:
            raise ValueError("dispatch packet debt must include a non-empty id")
        dispatch_id = f"dispatch-{content_hash(semantic_identity)[:20]}"
        return cls(
            dispatch_id=dispatch_id,
            debt=dict(debt),
            evidence=dict(evidence),
            authority=authority,
            rule=rule,
            routine=routine,
            objective=objective,
            allowed_paths=allowed_paths,
            allowed_commands=allowed_commands,
            forbidden_paths=forbidden_paths,
            stop_conditions=stop_conditions,
            proof=proof,
            budget=budget,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": DISPATCH_PACKET_SCHEMA,
            "dispatchId": self.dispatch_id,
            "debt": dict(self.debt),
            "evidence": dict(self.evidence),
            "authority": self.authority.value,
            "rule": self.rule,
            "routine": self.routine,
            "objective": self.objective,
            "allowedPaths": list(self.allowed_paths),
            "allowedCommands": list(self.allowed_commands),
            "forbiddenPaths": list(self.forbidden_paths),
            "stopConditions": list(self.stop_conditions),
            "proof": list(self.proof),
            "budget": self.budget.to_dict(),
        }

    @property
    def packet_hash(self) -> str:
        return content_hash(self.to_dict())


@dataclass(frozen=True)
class FounderDecision:
    """One exact Class C decision group in the founder queue."""

    decision_id: str
    rule: str
    decision_target: str
    objective: str
    debt_ids: tuple[str, ...]
    evidence: tuple[Mapping[str, Any], ...]

    @classmethod
    def create(
        cls,
        *,
        rule: str,
        decision_target: str,
        objective: str,
        debt_ids: tuple[str, ...],
        evidence: tuple[Mapping[str, Any], ...],
    ) -> "FounderDecision":
        normalized_target = normalize_decision_target(decision_target)
        normalized_ids = tuple(sorted(set(debt_ids)))
        if not rule.strip() or not objective.strip() or not normalized_ids:
            raise ValueError("founder decision rule, objective, and debt ids are required")
        if len(evidence) != len(normalized_ids):
            raise ValueError("founder decision evidence must match source debt count")
        normalized_evidence = tuple(
            sorted((dict(item) for item in evidence), key=stable_json)
        )
        # The decision is identified by its policy question and exact target,
        # not by today's evidence rows. New blocked debt must not produce a new
        # founder decision identity.
        semantic_identity = {
            "schemaVersion": FOUNDER_DECISION_SCHEMA,
            "rule": rule,
            "decisionTarget": normalized_target,
        }
        decision_id = f"decision-{content_hash(semantic_identity)[:20]}"
        return cls(
            decision_id=decision_id,
            rule=rule,
            decision_target=normalized_target,
            objective=objective,
            debt_ids=normalized_ids,
            evidence=normalized_evidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": FOUNDER_DECISION_SCHEMA,
            "decisionId": self.decision_id,
            "rule": self.rule,
            "decisionTarget": self.decision_target,
            "objective": self.objective,
            "debtIds": list(self.debt_ids),
            "evidence": [dict(item) for item in self.evidence],
        }


@dataclass(frozen=True)
class FounderQueue:
    """Stable, sorted Class C queue rendered from one fresh scan."""

    queue_id: str
    decisions: tuple[FounderDecision, ...]

    @classmethod
    def create(cls, decisions: tuple[FounderDecision, ...]) -> "FounderQueue":
        ordered = tuple(
            sorted(decisions, key=lambda item: (item.rule, item.decision_target, item.decision_id))
        )
        # This is one queue surface; its content hash records membership.
        return cls(queue_id="founder-queue-v1", decisions=ordered)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": FOUNDER_QUEUE_SCHEMA,
            "queueId": self.queue_id,
            "decisions": [item.to_dict() for item in self.decisions],
        }

    @property
    def queue_hash(self) -> str:
        return content_hash(self.to_dict())


@dataclass(frozen=True)
class Subject:
    type: str
    id: str

    def __post_init__(self) -> None:
        if not self.type.strip() or not self.id.strip():
            raise ValueError("subject type and id must be non-empty")

    def to_dict(self) -> dict[str, str]:
        return {"type": self.type, "id": self.id}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Subject":
        return cls(type=str(data["type"]), id=str(data["id"]))


@dataclass(frozen=True)
class Observation:
    """A sensor statement about one reproducible repository condition."""

    kind: str
    subject: Subject
    observed_at: str
    source: str
    status: str
    current_state: Mapping[str, Any]
    observed_state: Mapping[str, Any]
    confidence: float = 1.0
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in {"healthy", "drift"}:
            raise ValueError("observation status must be healthy or drift")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("observation confidence must be between 0 and 1")
        if not self.kind.strip() or not self.source.strip() or not self.observed_at.strip():
            raise ValueError("observation kind, source, and observed_at are required")
        # Fail early if a sensor emits a value that cannot enter a JSON receipt.
        stable_json(self.current_state)
        stable_json(self.observed_state)
        stable_json(self.provenance)

    @property
    def semantic_key(self) -> str:
        return stable_json({"kind": self.kind, "subject": self.subject.to_dict()})

    @property
    def debt_id(self) -> str:
        digest = hashlib.sha256(self.semantic_key.encode("utf-8")).hexdigest()[:16]
        return f"debt:{self.kind}:{_slug(self.subject.id)}:{digest}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": OBSERVATION_SCHEMA,
            "kind": self.kind,
            "subject": self.subject.to_dict(),
            "observedAt": self.observed_at,
            "source": self.source,
            "status": self.status,
            "currentState": dict(self.current_state),
            "observedState": dict(self.observed_state),
            "confidence": self.confidence,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class Priority:
    importance: float
    decision_impact: float
    exposure: float
    freshness_need: float
    expected_cost: float
    score: float

    def to_dict(self) -> dict[str, float]:
        return {
            "importance": self.importance,
            "decisionImpact": self.decision_impact,
            "exposure": self.exposure,
            "freshnessNeed": self.freshness_need,
            "expectedCost": self.expected_cost,
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Priority":
        return cls(
            importance=float(data["importance"]),
            decision_impact=float(data["decisionImpact"]),
            exposure=float(data["exposure"]),
            freshness_need=float(data["freshnessNeed"]),
            expected_cost=float(data["expectedCost"]),
            score=float(data["score"]),
        )


@dataclass(frozen=True)
class Debt:
    id: str
    kind: str
    subject: Subject
    source: str
    current_state: Mapping[str, Any]
    observed_state: Mapping[str, Any]
    confidence: float
    priority: Priority
    authority: AuthorityClass
    status: str
    first_observed_at: str
    last_observed_at: str
    observation_count: int
    resolution: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"open", "resolved"}:
            raise ValueError("V1 debt status must be open or resolved")
        if self.observation_count < 1:
            raise ValueError("debt observation_count must be positive")

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "schemaVersion": DEBT_SCHEMA,
            "id": self.id,
            "kind": self.kind,
            "subject": self.subject.to_dict(),
            "source": self.source,
            "currentState": dict(self.current_state),
            "observedState": dict(self.observed_state),
            "confidence": self.confidence,
            "priority": self.priority.to_dict(),
            "authority": {"class": self.authority.value},
            "status": self.status,
            "firstObservedAt": self.first_observed_at,
            "lastObservedAt": self.last_observed_at,
            "observationCount": self.observation_count,
        }
        if self.resolution is not None:
            data["resolution"] = self.resolution
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Debt":
        if data.get("schemaVersion") != DEBT_SCHEMA:
            raise ValueError("unsupported debt schemaVersion")
        return cls(
            id=str(data["id"]),
            kind=str(data["kind"]),
            subject=Subject.from_dict(data["subject"]),
            source=str(data["source"]),
            current_state=dict(data["currentState"]),
            observed_state=dict(data["observedState"]),
            confidence=float(data["confidence"]),
            priority=Priority.from_dict(data["priority"]),
            authority=AuthorityClass(data["authority"]["class"]),
            status=str(data["status"]),
            first_observed_at=str(data["firstObservedAt"]),
            last_observed_at=str(data["lastObservedAt"]),
            observation_count=int(data["observationCount"]),
            resolution=data.get("resolution"),
        )


@dataclass(frozen=True)
class Receipt:
    run_id: str
    started_at: str
    finished_at: str
    observations_collected: int
    coverage_unknown: tuple[str, ...]
    debt_created: tuple[str, ...]
    debt_updated: tuple[str, ...]
    debt_resolved: tuple[str, ...]
    open_debt: tuple[str, ...]
    authority_counts: Mapping[str, int]
    result_status: str
    repairs: tuple[Mapping[str, Any], ...] = ()
    blocked: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": RECEIPT_SCHEMA,
            "runId": self.run_id,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "observationsCollected": self.observations_collected,
            "coverageUnknown": list(self.coverage_unknown),
            "debtCreated": list(self.debt_created),
            "debtUpdated": list(self.debt_updated),
            "debtResolved": list(self.debt_resolved),
            "openDebt": list(self.open_debt),
            "authorityCounts": dict(self.authority_counts),
            "dispatches": [],
            "repairs": [dict(item) for item in self.repairs],
            "blocked": [dict(item) for item in self.blocked],
            "founderEscalations": [],
            "models": [],
            "result": {"status": self.result_status},
        }

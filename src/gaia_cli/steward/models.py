"""Small, JSON-serializable contracts used by Gaia Steward.

The contracts deliberately avoid persistence or command behavior.  They are the
stable boundary between sensors, debt reconciliation, and receipts.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


OBSERVATION_SCHEMA = "steward-observation-v1"
DEBT_SCHEMA = "steward-debt-v1"
LEDGER_SCHEMA = "steward-ledger-v1"
RECEIPT_SCHEMA = "steward-receipt-v1"


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

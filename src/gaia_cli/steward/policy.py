"""Load and validate the checked-in Gaia Steward policy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import yaml

from gaia_cli.steward.models import AuthorityClass, Priority


POLICY_RELATIVE_PATH = Path("founder/steward/POLICY.yaml")
_TOP_LEVEL_KEYS = {
    "version",
    "mode",
    "state",
    "allowedWrites",
    "authority",
    "priority",
    "budgets",
}
_PRIORITY_KEYS = {
    "importance",
    "decisionImpact",
    "exposure",
    "freshnessNeed",
    "expectedCost",
}


class PolicyError(ValueError):
    """Raised when the repository's machine policy is absent or unsafe."""


@dataclass(frozen=True)
class PriorityWeights:
    importance: float
    decision_impact: float
    exposure: float
    freshness_need: float
    expected_cost: float

    def calculate(self, confidence: float) -> Priority:
        score = round(
            self.importance
            * confidence
            * self.decision_impact
            * self.exposure
            * self.freshness_need
            / self.expected_cost,
            6,
        )
        return Priority(
            importance=self.importance,
            decision_impact=self.decision_impact,
            exposure=self.exposure,
            freshness_need=self.freshness_need,
            expected_cost=self.expected_cost,
            score=score,
        )


@dataclass(frozen=True)
class StewardPolicy:
    version: int
    state_directory: Path
    receipts_directory: str
    allowed_writes: tuple[str, ...]
    authority: Mapping[str, AuthorityClass]
    priority: Mapping[str, PriorityWeights]
    max_observations_per_run: int

    @classmethod
    def load(cls, repo_root: Path) -> "StewardPolicy":
        policy_path = repo_root / POLICY_RELATIVE_PATH
        try:
            raw_bytes = policy_path.read_bytes()
        except OSError as exc:
            raise PolicyError(f"cannot read Steward policy at {policy_path}: {exc}") from exc
        if len(raw_bytes) > 64 * 1024:
            raise PolicyError("Steward policy exceeds the 64 KiB safety limit")
        try:
            data = yaml.safe_load(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise PolicyError(f"invalid Steward policy YAML: {exc}") from exc
        return cls._from_mapping(data)

    @classmethod
    def _from_mapping(cls, data: Any) -> "StewardPolicy":
        if not isinstance(data, dict):
            raise PolicyError("Steward policy must be a YAML mapping")
        unknown = set(data) - _TOP_LEVEL_KEYS
        missing = _TOP_LEVEL_KEYS - set(data)
        if unknown or missing:
            raise PolicyError(
                f"Steward policy keys invalid; missing={sorted(missing)}, unknown={sorted(unknown)}"
            )
        if data["version"] != 1:
            raise PolicyError("Steward policy version must be 1")
        if data["mode"] != "report-only":
            raise PolicyError("Steward V1 policy mode must be report-only")

        state = _mapping(data["state"], "state")
        if set(state) != {"directory", "receiptsDirectory"}:
            raise PolicyError("state must contain only directory and receiptsDirectory")
        state_directory = _safe_relative_path(state["directory"], "state.directory")
        if state_directory != Path(".gaia/steward"):
            raise PolicyError("Steward V1 state.directory must be .gaia/steward")
        receipts_directory = str(state["receiptsDirectory"])
        if PurePosixPath(receipts_directory) != PurePosixPath("receipts"):
            raise PolicyError("Steward V1 receiptsDirectory must be receipts")

        allowed_writes_raw = data["allowedWrites"]
        if not isinstance(allowed_writes_raw, list) or not allowed_writes_raw:
            raise PolicyError("allowedWrites must be a non-empty list")
        allowed_writes = tuple(str(item) for item in allowed_writes_raw)
        if allowed_writes != (".gaia/steward/**",):
            raise PolicyError("Steward V1 may write only .gaia/steward/**")

        authority_raw = _mapping(data["authority"], "authority")
        if not authority_raw:
            raise PolicyError("authority must classify at least one debt kind")
        try:
            authority = {
                str(kind): AuthorityClass(str(value))
                for kind, value in authority_raw.items()
            }
        except ValueError as exc:
            raise PolicyError("authority values must be A, B, or C") from exc

        priority_raw = _mapping(data["priority"], "priority")
        if set(priority_raw) != set(authority):
            raise PolicyError("priority and authority must classify the same debt kinds")
        priorities: dict[str, PriorityWeights] = {}
        for kind, raw_weights in priority_raw.items():
            weights = _mapping(raw_weights, f"priority.{kind}")
            if set(weights) != _PRIORITY_KEYS:
                raise PolicyError(f"priority.{kind} must contain exactly {sorted(_PRIORITY_KEYS)}")
            values = {key: _bounded_number(value, f"priority.{kind}.{key}") for key, value in weights.items()}
            if values["expectedCost"] == 0:
                raise PolicyError(f"priority.{kind}.expectedCost must be greater than zero")
            priorities[str(kind)] = PriorityWeights(
                importance=values["importance"],
                decision_impact=values["decisionImpact"],
                exposure=values["exposure"],
                freshness_need=values["freshnessNeed"],
                expected_cost=values["expectedCost"],
            )

        budgets = _mapping(data["budgets"], "budgets")
        if set(budgets) != {"maxObservationsPerRun"}:
            raise PolicyError("budgets must contain only maxObservationsPerRun")
        max_observations = budgets["maxObservationsPerRun"]
        if isinstance(max_observations, bool) or not isinstance(max_observations, int) or max_observations < 1:
            raise PolicyError("maxObservationsPerRun must be a positive integer")

        return cls(
            version=1,
            state_directory=state_directory,
            receipts_directory=receipts_directory,
            allowed_writes=allowed_writes,
            authority=authority,
            priority=priorities,
            max_observations_per_run=max_observations,
        )

    def authority_for(self, kind: str) -> AuthorityClass:
        try:
            return self.authority[kind]
        except KeyError as exc:
            raise PolicyError(f"debt kind is not classified by policy: {kind}") from exc

    def priority_for(self, kind: str, confidence: float) -> Priority:
        try:
            return self.priority[kind].calculate(confidence)
        except KeyError as exc:
            raise PolicyError(f"debt kind has no priority policy: {kind}") from exc


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise PolicyError(f"{name} must be a mapping")
    if not all(isinstance(key, str) and key for key in value):
        raise PolicyError(f"{name} keys must be non-empty strings")
    return value


def _safe_relative_path(value: Any, name: str) -> Path:
    if not isinstance(value, str) or not value:
        raise PolicyError(f"{name} must be a non-empty string")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise PolicyError(f"{name} must be a safe repository-relative path")
    return Path(*path.parts)


def _bounded_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PolicyError(f"{name} must be numeric")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise PolicyError(f"{name} must be between 0 and 1")
    return number

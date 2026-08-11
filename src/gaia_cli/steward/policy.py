"""Load and validate the checked-in Gaia Steward policy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping

import yaml

from gaia_cli.steward.models import AuthorityClass, Priority, RoutingBudget


POLICY_RELATIVE_PATH = Path("founder/steward/POLICY.yaml")
_TOP_LEVEL_KEYS = {
    "version",
    "mode",
    "state",
    "allowedWrites",
    "authority",
    "priority",
    "budgets",
    "repairs",
    "routing",
}
_PRIORITY_KEYS = {
    "importance",
    "decisionImpact",
    "exposure",
    "freshnessNeed",
    "expectedCost",
}
_REPAIR_KEYS = {"maxRepairsPerRun", "executors"}
_EXECUTOR_KEYS = {
    "debtKind",
    "authority",
    "canonicalPath",
    "writablePath",
    "allowedCommands",
    "stopConditions",
}
_CLASS_A_MODE = "class-a-closed-loop"
_CLASS_A_ALLOWED_WRITES = (
    ".gaia/steward/**",
    "src/gaia_cli/data/registry/schema/**",
)
_ROUTING_KEYS = {"maxDispatchesPerRun", "budget", "dispatchRules", "founderRules"}
_ROUTING_BUDGET_KEYS = {"modelCalls", "maxTokens", "maxMinutes"}
_DISPATCH_RULE_KEYS = {
    "debtKind",
    "authority",
    "routine",
    "objective",
    "allowedPaths",
    "allowedCommands",
    "forbiddenPaths",
    "stopConditions",
    "proof",
}
_FOUNDER_RULE_KEYS = {
    "debtKind",
    "authority",
    "decisionTargetField",
    "objective",
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
class RepairExecutorPolicy:
    """One mechanically bounded Class A repair authority envelope."""

    id: str
    debt_kind: str
    authority: AuthorityClass
    canonical_path: str
    writable_path: str
    allowed_commands: tuple[str, ...]
    stop_conditions: tuple[str, ...]


@dataclass(frozen=True)
class DispatchRulePolicy:
    """One report-only Class B packet rule."""

    id: str
    debt_kind: str
    authority: AuthorityClass
    routine: str
    objective: str
    allowed_paths: tuple[str, ...]
    allowed_commands: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    proof: tuple[str, ...]


@dataclass(frozen=True)
class FounderRulePolicy:
    """One exact Class C founder-grouping rule."""

    id: str
    debt_kind: str
    authority: AuthorityClass
    decision_target_field: str
    objective: str


@dataclass(frozen=True)
class StewardPolicy:
    version: int
    state_directory: Path
    receipts_directory: str
    allowed_writes: tuple[str, ...]
    authority: Mapping[str, AuthorityClass]
    priority: Mapping[str, PriorityWeights]
    max_observations_per_run: int
    max_repairs_per_run: int
    repair_executors: Mapping[str, RepairExecutorPolicy]
    max_dispatches_per_run: int
    routing_budget: RoutingBudget
    dispatch_rules: Mapping[str, DispatchRulePolicy]
    founder_rules: Mapping[str, FounderRulePolicy]

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
        if data["mode"] not in {"report-only", _CLASS_A_MODE}:
            raise PolicyError("Steward policy mode must be report-only or class-a-closed-loop")

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
        expected_writes = (
            (".gaia/steward/**",)
            if data["mode"] == "report-only"
            else _CLASS_A_ALLOWED_WRITES
        )
        if allowed_writes != expected_writes:
            raise PolicyError(f"Steward {data['mode']} allowedWrites are fixed by policy")

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

        repairs = _mapping(data["repairs"], "repairs")
        if set(repairs) != _REPAIR_KEYS:
            raise PolicyError("repairs must contain only maxRepairsPerRun and executors")
        max_repairs = repairs["maxRepairsPerRun"]
        if isinstance(max_repairs, bool) or not isinstance(max_repairs, int) or max_repairs < 0:
            raise PolicyError("maxRepairsPerRun must be a non-negative integer")
        executor_data = _mapping(repairs["executors"], "repairs.executors")
        executors: dict[str, RepairExecutorPolicy] = {}
        for executor_id, raw_executor in executor_data.items():
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", executor_id):
                raise PolicyError("repair executor ids must be kebab-case")
            executor = _mapping(raw_executor, f"repairs.executors.{executor_id}")
            if set(executor) != _EXECUTOR_KEYS:
                raise PolicyError(
                    f"repairs.executors.{executor_id} must contain exactly "
                    f"{sorted(_EXECUTOR_KEYS)}"
                )
            debt_kind = _nonempty_string(executor["debtKind"], f"repairs.executors.{executor_id}.debtKind")
            if debt_kind not in authority:
                raise PolicyError(f"repair executor {executor_id} has unclassified debt kind")
            try:
                executor_authority = AuthorityClass(executor["authority"])
            except ValueError as exc:
                raise PolicyError(f"repair executor {executor_id} authority must be A, B, or C") from exc
            if executor_authority is not AuthorityClass.A or authority[debt_kind] is not AuthorityClass.A:
                raise PolicyError(f"repair executor {executor_id} may only execute Class A debt")
            canonical_path = _safe_glob(executor["canonicalPath"], f"repairs.executors.{executor_id}.canonicalPath")
            writable_path = _safe_glob(executor["writablePath"], f"repairs.executors.{executor_id}.writablePath")
            if writable_path not in allowed_writes:
                raise PolicyError(f"repair executor {executor_id} writablePath is not allowed")
            allowed_commands = _string_list(executor["allowedCommands"], f"repairs.executors.{executor_id}.allowedCommands")
            stop_conditions = _string_list(executor["stopConditions"], f"repairs.executors.{executor_id}.stopConditions")
            executors[executor_id] = RepairExecutorPolicy(
                id=executor_id,
                debt_kind=debt_kind,
                authority=executor_authority,
                canonical_path=canonical_path,
                writable_path=writable_path,
                allowed_commands=allowed_commands,
                stop_conditions=stop_conditions,
            )
        if data["mode"] == "report-only" and (max_repairs or executors):
            raise PolicyError("report-only policy may not authorize repair executors")
        if data["mode"] == _CLASS_A_MODE and (max_repairs != 1 or len(executors) != 1):
            raise PolicyError("class-a-closed-loop policy must authorize exactly one repair executor")

        routing = _mapping(data["routing"], "routing")
        if set(routing) != _ROUTING_KEYS:
            raise PolicyError(f"routing must contain exactly {sorted(_ROUTING_KEYS)}")
        max_dispatches = routing["maxDispatchesPerRun"]
        if max_dispatches != 1 or isinstance(max_dispatches, bool):
            raise PolicyError("routing.maxDispatchesPerRun must be exactly 1")
        budget_raw = _mapping(routing["budget"], "routing.budget")
        if set(budget_raw) != _ROUTING_BUDGET_KEYS:
            raise PolicyError(
                f"routing.budget must contain exactly {sorted(_ROUTING_BUDGET_KEYS)}"
            )
        try:
            routing_budget = RoutingBudget(
                model_calls=budget_raw["modelCalls"],
                max_tokens=budget_raw["maxTokens"],
                max_minutes=budget_raw["maxMinutes"],
            )
        except ValueError as exc:
            raise PolicyError(str(exc)) from exc

        dispatch_data = _mapping(routing["dispatchRules"], "routing.dispatchRules")
        if set(dispatch_data) != {"registry-integrity-review"}:
            raise PolicyError("routing must define exactly registry-integrity-review")
        dispatch_rules: dict[str, DispatchRulePolicy] = {}
        for rule_id, raw_rule in dispatch_data.items():
            rule = _mapping(raw_rule, f"routing.dispatchRules.{rule_id}")
            if set(rule) != _DISPATCH_RULE_KEYS:
                raise PolicyError(
                    f"routing.dispatchRules.{rule_id} must contain exactly "
                    f"{sorted(_DISPATCH_RULE_KEYS)}"
                )
            debt_kind = _nonempty_string(rule["debtKind"], f"routing.dispatchRules.{rule_id}.debtKind")
            rule_authority = _authority_value(rule["authority"], f"routing.dispatchRules.{rule_id}.authority")
            if (
                debt_kind != "registry_integrity_failed"
                or rule_authority is not AuthorityClass.B
                or authority.get(debt_kind) is not AuthorityClass.B
            ):
                raise PolicyError(
                    "registry-integrity-review must route only Class B registry_integrity_failed debt"
                )
            allowed_paths = tuple(
                _safe_glob(item, f"routing.dispatchRules.{rule_id}.allowedPaths")
                for item in _string_list(rule["allowedPaths"], f"routing.dispatchRules.{rule_id}.allowedPaths")
            )
            forbidden_paths = tuple(
                _safe_glob(item, f"routing.dispatchRules.{rule_id}.forbiddenPaths")
                for item in _string_list(rule["forbiddenPaths"], f"routing.dispatchRules.{rule_id}.forbiddenPaths")
            )
            if set(allowed_paths) & set(forbidden_paths):
                raise PolicyError(f"routing dispatch rule {rule_id} path scopes overlap")
            dispatch_rules[rule_id] = DispatchRulePolicy(
                id=rule_id,
                debt_kind=debt_kind,
                authority=rule_authority,
                routine=_nonempty_string(rule["routine"], f"routing.dispatchRules.{rule_id}.routine"),
                objective=_nonempty_string(rule["objective"], f"routing.dispatchRules.{rule_id}.objective"),
                allowed_paths=allowed_paths,
                allowed_commands=_string_list(rule["allowedCommands"], f"routing.dispatchRules.{rule_id}.allowedCommands"),
                forbidden_paths=forbidden_paths,
                stop_conditions=_string_list(rule["stopConditions"], f"routing.dispatchRules.{rule_id}.stopConditions"),
                proof=_string_list(rule["proof"], f"routing.dispatchRules.{rule_id}.proof"),
            )

        founder_data = _mapping(routing["founderRules"], "routing.founderRules")
        if set(founder_data) != {"generic-mapping-decision"}:
            raise PolicyError("routing must define exactly generic-mapping-decision")
        founder_rules: dict[str, FounderRulePolicy] = {}
        for rule_id, raw_rule in founder_data.items():
            rule = _mapping(raw_rule, f"routing.founderRules.{rule_id}")
            if set(rule) != _FOUNDER_RULE_KEYS:
                raise PolicyError(
                    f"routing.founderRules.{rule_id} must contain exactly "
                    f"{sorted(_FOUNDER_RULE_KEYS)}"
                )
            debt_kind = _nonempty_string(rule["debtKind"], f"routing.founderRules.{rule_id}.debtKind")
            rule_authority = _authority_value(rule["authority"], f"routing.founderRules.{rule_id}.authority")
            if (
                debt_kind != "generic_mapping"
                or rule_authority is not AuthorityClass.C
                or authority.get(debt_kind) is not AuthorityClass.C
                or rule["decisionTargetField"] != "decisionTarget"
            ):
                raise PolicyError(
                    "generic-mapping-decision must require decisionTarget for Class C generic_mapping debt"
                )
            founder_rules[rule_id] = FounderRulePolicy(
                id=rule_id,
                debt_kind=debt_kind,
                authority=rule_authority,
                decision_target_field="decisionTarget",
                objective=_nonempty_string(rule["objective"], f"routing.founderRules.{rule_id}.objective"),
            )

        return cls(
            version=1,
            state_directory=state_directory,
            receipts_directory=receipts_directory,
            allowed_writes=allowed_writes,
            authority=authority,
            priority=priorities,
            max_observations_per_run=max_observations,
            max_repairs_per_run=max_repairs,
            repair_executors=executors,
            max_dispatches_per_run=max_dispatches,
            routing_budget=routing_budget,
            dispatch_rules=dispatch_rules,
            founder_rules=founder_rules,
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

    def executor_for(self, debt_kind: str) -> RepairExecutorPolicy | None:
        matches = [item for item in self.repair_executors.values() if item.debt_kind == debt_kind]
        if len(matches) > 1:
            raise PolicyError(f"multiple repair executors are configured for {debt_kind}")
        return matches[0] if matches else None

    def dispatch_rule_for(self, debt_kind: str) -> DispatchRulePolicy | None:
        matches = [item for item in self.dispatch_rules.values() if item.debt_kind == debt_kind]
        if len(matches) > 1:
            raise PolicyError(f"multiple dispatch rules are configured for {debt_kind}")
        return matches[0] if matches else None

    def founder_rule_for(self, debt_kind: str) -> FounderRulePolicy | None:
        matches = [item for item in self.founder_rules.values() if item.debt_kind == debt_kind]
        if len(matches) > 1:
            raise PolicyError(f"multiple founder rules are configured for {debt_kind}")
        return matches[0] if matches else None


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


def _safe_glob(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.endswith("/**"):
        raise PolicyError(f"{name} must be a safe repository-relative /** path")
    _safe_relative_path(value[:-3], name)
    return value


def _nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PolicyError(f"{name} must be a non-empty string")
    return value


def _string_list(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise PolicyError(f"{name} must be a non-empty list")
    return tuple(_nonempty_string(item, name) for item in value)


def _bounded_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PolicyError(f"{name} must be numeric")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise PolicyError(f"{name} must be between 0 and 1")
    return number


def _authority_value(value: Any, name: str) -> AuthorityClass:
    try:
        return AuthorityClass(value)
    except (TypeError, ValueError) as exc:
        raise PolicyError(f"{name} must be A, B, or C") from exc

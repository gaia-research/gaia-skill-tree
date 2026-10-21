"""Policy for the Steward issue-hygiene capability.

The ``issueHygiene`` section of ``founder/steward/POLICY.yaml`` may narrow the
capability or switch it off. It may never widen it: the rule ids are code
registered, the caps are pinned here, and anything unknown fails loudly at load
time rather than being quietly ignored.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping


class HygienePolicyError(ValueError):
    """Raised when the issueHygiene policy section is malformed or exceeds a cap."""


# Closure rules registered in code (contract section 3.4). Policy selects among
# them; it cannot add a rule that has no implementation.
KNOWN_RULE_IDS = (
    "A1-child-curated",
    "A2-umbrella-synced",
    "A3-umbrella-superseded",
    "A4-duplicate-child",
    "A5-botreport-superseded",
)

HYGIENE_KEYS = {
    "maxClosuresPerRun",
    "maxCensusAgeSeconds",
    "closedWindowDays",
    "enabledRules",
    "a5Disabled",
    "writesEnabled",
}

DEFAULT_MAX_CLOSURES = 10
DEFAULT_CENSUS_AGE_SECONDS = 21_600
DEFAULT_CLOSED_WINDOW_DAYS = 30

# Hard ceilings. A POLICY edit can lower any of these, never raise them.
MAX_CLOSURES_HARD_CAP = 25
MIN_CENSUS_AGE_SECONDS = 300
MAX_CENSUS_AGE_SECONDS = 86_400
MIN_CLOSED_WINDOW_DAYS = 1
MAX_CLOSED_WINDOW_DAYS = 90
MAX_A5_PATHS = 16
_WORKFLOW_ROOT = PurePosixPath(".github/workflows")


@dataclass(frozen=True)
class HygienePolicy:
    maxClosuresPerRun: int = DEFAULT_MAX_CLOSURES
    maxCensusAgeSeconds: int = DEFAULT_CENSUS_AGE_SECONDS
    closedWindowDays: int = DEFAULT_CLOSED_WINDOW_DAYS
    enabledRules: tuple[str, ...] = KNOWN_RULE_IDS
    a5Disabled: tuple[str, ...] = ()
    writesEnabled: bool = False

    def ruleEnabled(self, ruleId: str) -> bool:
        return ruleId in self.enabledRules


def _requireInt(value: Any, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise HygienePolicyError(f"issueHygiene.{name} must be an integer")
    if not low <= value <= high:
        raise HygienePolicyError(f"issueHygiene.{name} must be between {low} and {high}, not {value}")
    return value


def _requireWorkflowPaths(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise HygienePolicyError("issueHygiene.a5Disabled must be a list of workflow paths")
    if len(value) > MAX_A5_PATHS:
        raise HygienePolicyError(f"issueHygiene.a5Disabled exceeds {MAX_A5_PATHS} paths")
    paths: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise HygienePolicyError("issueHygiene.a5Disabled entries must be non-empty strings")
        candidate = PurePosixPath(item)
        if candidate.is_absolute() or ".." in candidate.parts or candidate.parent != _WORKFLOW_ROOT:
            raise HygienePolicyError(
                f"issueHygiene.a5Disabled entries must be files directly under .github/workflows/: {item!r}"
            )
        paths.append(item)
    if len(set(paths)) != len(paths):
        raise HygienePolicyError("issueHygiene.a5Disabled contains duplicates")
    return tuple(paths)


def loadHygienePolicy(policyDict: Mapping[str, Any] | None) -> HygienePolicy:
    """Validate the raw ``issueHygiene`` mapping and return the frozen policy.

    ``None`` means the section is absent: no rule is enabled and writes stay off,
    so an old POLICY.yaml cannot grant closure authority by omission.
    """

    if policyDict is None:
        return HygienePolicy(writesEnabled=False, enabledRules=())
    if not isinstance(policyDict, Mapping):
        raise HygienePolicyError("issueHygiene must be a mapping")
    unknown = set(policyDict) - HYGIENE_KEYS
    missing = HYGIENE_KEYS - set(policyDict)
    if unknown or missing:
        raise HygienePolicyError(
            f"issueHygiene keys invalid; missing={sorted(missing)}, unknown={sorted(unknown)}"
        )

    rules = policyDict["enabledRules"]
    if not isinstance(rules, list):
        raise HygienePolicyError("issueHygiene.enabledRules must be a list")
    unknownRules = sorted({str(item) for item in rules} - set(KNOWN_RULE_IDS))
    if unknownRules:
        raise HygienePolicyError(f"issueHygiene.enabledRules names unregistered rules: {unknownRules}")
    if len(set(rules)) != len(rules):
        raise HygienePolicyError("issueHygiene.enabledRules contains duplicates")
    enabled = tuple(rule for rule in KNOWN_RULE_IDS if rule in rules)

    writes = policyDict["writesEnabled"]
    if not isinstance(writes, bool):
        raise HygienePolicyError("issueHygiene.writesEnabled must be true or false")

    return HygienePolicy(
        maxClosuresPerRun=_requireInt(policyDict["maxClosuresPerRun"], "maxClosuresPerRun", 0, MAX_CLOSURES_HARD_CAP),
        maxCensusAgeSeconds=_requireInt(
            policyDict["maxCensusAgeSeconds"], "maxCensusAgeSeconds", MIN_CENSUS_AGE_SECONDS, MAX_CENSUS_AGE_SECONDS
        ),
        closedWindowDays=_requireInt(
            policyDict["closedWindowDays"], "closedWindowDays", MIN_CLOSED_WINDOW_DAYS, MAX_CLOSED_WINDOW_DAYS
        ),
        enabledRules=enabled,
        a5Disabled=_requireWorkflowPaths(policyDict["a5Disabled"]),
        writesEnabled=writes,
    )

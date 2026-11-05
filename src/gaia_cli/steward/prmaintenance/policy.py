"""Policy for the Steward PR-maintenance capability (``prMaintenance`` in ``founder/steward/POLICY.yaml``).

The section may narrow the capability or switch it off. It may never widen it: ceilings are pinned here,
squash is not representable, and unknown keys fail loudly at load time. As with issue hygiene, editing
``writesEnabled`` alone grants nothing: runtime also requires the decided authority record
``steward-pr-maintenance-authority`` with resolution ``approved`` (see ``authority.py``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

DECISION_ID = "steward-pr-maintenance-authority"
DECISION_PATH = Path("founder/steward/decisions") / f"{DECISION_ID}.json"
ACTIONS = ("comment", "merge", "close")
METHODS = ("merge", "rebase")
KEYS = {
    "writesEnabled", "killSwitch", "maxCensusAgeSeconds", "maxMergesPerRun", "maxClosuresPerRun", "maxCommentsPerRun",
    "hourlyWriteCap", "verificationTtlSeconds", "maxReplacementsPerRun", "enabledActions", "destinations", "mergeMethods",
}
# Hard ceilings. A POLICY edit can lower any of these, never raise them.
CEILINGS = {
    "maxMergesPerRun": 5, "maxClosuresPerRun": 5, "maxCommentsPerRun": 60, "hourlyWriteCap": 25, "maxReplacementsPerRun": 3,
}


class PrPolicyError(ValueError):
    """The prMaintenance policy section is malformed or exceeds a ceiling."""


@dataclass(frozen=True)
class WriteCoordination:
    """Separately provisioned deployment binding; presence is not activation proof."""

    protocol: str
    forgeHost: str
    repositoryId: str
    repositoryName: str
    epoch: str
    genesis: str
    historyPin: str
    canonicalUrl: str
    authorityBranch: str
    clock: Mapping[str, Any]
    remote: str = "origin"
    ref: str = "refs/heads/steward/pr-write-coordination-v1"
    protectionsVerified: bool = True
    bypassingWritersDrained: bool = True


def coordinationBinding(value: Any) -> WriteCoordination | None:
    if value is None:
        return None
    from gaia_cli.steward.prmaintenance import coordination as core

    if not isinstance(value, dict) or set(value) != set(WriteCoordination.__dataclass_fields__):
        raise PrPolicyError("writeCoordination requires the complete strict deployment binding")
    try:
        binding = WriteCoordination(**value)
        core.Namespace(binding.forgeHost, binding.repositoryId, binding.repositoryName, binding.epoch, binding.protocol).validate()
        core.sha(binding.genesis, git=True)
        core.sha(binding.historyPin, git=True)
        if binding.remote != "origin" or binding.ref != f"refs/heads/{core.REF}":
            raise ValueError("canonical origin/ref required")
        if binding.canonicalUrl != f"https://{binding.forgeHost}/{binding.repositoryName}.git":
            raise ValueError("canonical HTTPS repository URL required")
        if binding.protectionsVerified is not True or binding.bypassingWritersDrained is not True:
            raise ValueError("separate namespace protection/drain verification required")
        # Current ratified scope is the GitHub tree repository's canonical main,
        # never a branch a stale/staged checkout can nominate to approve itself.
        if binding.authorityBranch != "main":
            raise ValueError("canonical main authority branch required")
        if not isinstance(binding.clock, dict) or set(binding.clock) != {"url", "maxSkewSeconds", "precisionSeconds", "maxRoundTripSeconds"}:
            raise ValueError("complete trusted clock contract required")
        core.text(binding.clock["url"], 2048)
        if any(char.isspace() for char in binding.clock["url"]):
            raise ValueError("clock endpoint must be a plain HTTPS URL")
        url = urlsplit(binding.clock["url"])
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("trusted clock requires an HTTPS endpoint without credentials/query/fragment")
        if url.port is not None:
            core.integer(url.port, 1, 65535)
        integer(binding.clock["maxSkewSeconds"], "clock.maxSkewSeconds", 0, 5)
        integer(binding.clock["precisionSeconds"], "clock.precisionSeconds", 1, 1)
        integer(binding.clock["maxRoundTripSeconds"], "clock.maxRoundTripSeconds", 1, 5)
        return binding
    except (ValueError, TypeError, KeyError, core.CoordinationError) as exc:
        raise PrPolicyError("invalid writeCoordination deployment/clock binding") from exc


@dataclass(frozen=True)
class PrMaintenancePolicy:
    writesEnabled: bool = False
    killSwitch: bool = False
    maxCensusAgeSeconds: int = 3600
    maxMergesPerRun: int = 2
    maxClosuresPerRun: int = 2
    maxCommentsPerRun: int = 30
    hourlyWriteCap: int = 10
    verificationTtlSeconds: int = 21600
    maxReplacementsPerRun: int = 2
    enabledActions: tuple[str, ...] = ()
    destinations: tuple[str, ...] = ("main",)
    mergeMethods: tuple[str, ...] = ("merge",)
    writeCoordination: WriteCoordination | None = None

    def actionEnabled(self, action: str) -> bool:
        return self.writesEnabled and not self.killSwitch and action in self.enabledActions


def integer(value: Any, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise PrPolicyError(f"prMaintenance.{name} must be an integer from {low} to {high}")
    return value


def loadPrMaintenancePolicy(section: Any) -> PrMaintenancePolicy:
    """Absent section => no write authority. A present section must be complete and within ceilings."""

    if section is None:
        return PrMaintenancePolicy()
    if not isinstance(section, Mapping):
        raise PrPolicyError("prMaintenance must be a mapping")
    unknown, missing = set(section) - KEYS - {"writeCoordination"}, KEYS - set(section)
    if unknown or missing:
        raise PrPolicyError(f"prMaintenance keys invalid; missing={sorted(missing)}, unknown={sorted(unknown)}")
    for flag in ("writesEnabled", "killSwitch"):
        if not isinstance(section[flag], bool):
            raise PrPolicyError(f"prMaintenance.{flag} must be true or false")
    actions = section["enabledActions"]
    if not isinstance(actions, list) or set(actions) - set(ACTIONS) or len(set(actions)) != len(actions):
        raise PrPolicyError(f"prMaintenance.enabledActions must be a unique subset of {list(ACTIONS)}")
    methods = section["mergeMethods"]
    if not isinstance(methods, list) or not methods or set(methods) - set(METHODS):
        raise PrPolicyError(f"prMaintenance.mergeMethods must be a non-empty subset of {list(METHODS)}; squash is never allowed")
    destinations = section["destinations"]
    if not isinstance(destinations, list) or not destinations or not all(
            isinstance(item, str) and item and not item.startswith("-") and ".." not in item for item in destinations):
        raise PrPolicyError("prMaintenance.destinations must be a non-empty list of plain branch names")
    return PrMaintenancePolicy(
        writesEnabled=section["writesEnabled"], killSwitch=section["killSwitch"],
        maxCensusAgeSeconds=integer(section["maxCensusAgeSeconds"], "maxCensusAgeSeconds", 300, 21600),
        maxMergesPerRun=integer(section["maxMergesPerRun"], "maxMergesPerRun", 0, CEILINGS["maxMergesPerRun"]),
        maxClosuresPerRun=integer(section["maxClosuresPerRun"], "maxClosuresPerRun", 0, CEILINGS["maxClosuresPerRun"]),
        maxCommentsPerRun=integer(section["maxCommentsPerRun"], "maxCommentsPerRun", 0, CEILINGS["maxCommentsPerRun"]),
        hourlyWriteCap=integer(section["hourlyWriteCap"], "hourlyWriteCap", 0, CEILINGS["hourlyWriteCap"]),
        verificationTtlSeconds=integer(section["verificationTtlSeconds"], "verificationTtlSeconds", 300, 86400),
        maxReplacementsPerRun=integer(section["maxReplacementsPerRun"], "maxReplacementsPerRun", 0, CEILINGS["maxReplacementsPerRun"]),
        enabledActions=tuple(action for action in ACTIONS if action in actions),
        destinations=tuple(destinations), mergeMethods=tuple(method for method in METHODS if method in methods),
        writeCoordination=coordinationBinding(section.get("writeCoordination")),
    )


def prAuthorityApproved(root: Path) -> bool:
    """The founder ruling that grants the route. Missing, malformed, rejected or symlinked records fail closed."""

    path = root / DECISION_PATH
    if any(parent.is_symlink() for parent in (path, *path.parents) if parent != root.parent):
        return False
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(record, dict) and record.get("schemaVersion") == "steward-decision-v1" \
        and record.get("id") == DECISION_ID and record.get("status") == "decided" and record.get("resolution") == "approved"

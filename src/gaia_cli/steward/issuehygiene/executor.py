"""The one closure gate for issue hygiene (contract sections 3.5 and 7, lane B7).

Every write that closes a GitHub issue passes through ``gateClosure``. ``scripts/steward_issue_close.py``
calls it for a single ``forge.close_issue`` action. ``scripts/steward_issue_reconcile.py --apply-closures``
calls it for each proven plan of a manifest. Nothing else may build a forge for a closure.

``gateClosure`` re-derives the closure from the checkout, so a stored action is only a claim:

* the policy must set ``issueHygiene.writesEnabled``, the rule must be enabled, and A5 needs its ``a5Disabled`` list;
* this run may not exceed ``maxClosuresPerRun``, and no UTC hour may exceed the policy cap or the hard cap of 25 closures
  in any 60 minutes, counting every run's receipts (``hourlyBudget``);
* the receipts store is fixed (``.gaia/steward/issue-hygiene/receipts``) and reached through no symlink;
* the census must be complete, fresh, and for the repository the action and the caller name (``repo``);
* reconciliation must reproduce the action's manifest digest, and the closure's digests (``closureSha8`` and
  ``preservedSha256``) must match the re-derived plan.

Actions and debt plans carry digests and identifiers only (``compactPlan``). The full preserved payload and its
closing comments are rebuilt from the census at execution time, so they are never stored in the ledger.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from gaia_cli.steward.issuehygiene.census import loadCensus
from gaia_cli.steward.issuehygiene.closure import compactPlan, planClosures
from gaia_cli.steward.issuehygiene.hygienepolicy import HygienePolicy
from gaia_cli.steward.issuehygiene.reconcile import RULE_A5, reconcile, workflowProbesFor
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from gaia_cli.steward.issuehygiene.sensor import CENSUS_INPUT, observedDigest

RECEIPTDIR = Path(".gaia/steward/issue-hygiene/receipts")
HARD_HOURLY_CAP = 25
PLAN_CEILING = 1_000_000
REQUIRED = (
    "key", "issue", "ruleId", "authority", "state", "stateReason", "duplicateOf", "parent", "canonical",
    "expectedSnapshot", "evidence", "closureSha8", "preservedSha256", "receiptPath", "manifestSha256", "repo",
)
class ActionRefused(Exception):
    """The action cannot be performed as written, or the checkout no longer proves it. Nothing is written."""


def loadActionFile(path: Path) -> dict[str, Any]:
    try:
        action = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ActionRefused(f"action file unreadable: {type(exc).__name__}") from exc
    if not isinstance(action, dict):
        raise ActionRefused("action file must hold a JSON object")
    missing = [name for name in REQUIRED if name not in action]
    if missing:
        raise ActionRefused(f"action is missing {', '.join(missing)}")
    issue = action["issue"]
    if not isinstance(issue, int) or isinstance(issue, bool) or issue <= 0:
        raise ActionRefused("action issue must be a positive integer")
    if not isinstance(action["repo"], str) or not action["repo"].strip():
        raise ActionRefused("action names no repository")
    return action


def receiptFor(root: Path, receiptPath: Any) -> Path:
    """The receipt must sit in the issue-hygiene receipts store, reached through no symlink."""

    if not isinstance(receiptPath, str):
        raise ActionRefused("receiptPath must be a string")
    relative = Path(receiptPath)
    if relative.is_absolute() or relative.parent != RECEIPTDIR or relative.suffix != ".jsonl" or ".." in relative.parts:
        raise ActionRefused("receiptPath must be a .jsonl file under .gaia/steward/issue-hygiene/receipts/")
    walked = Path(".")
    for part in RECEIPTDIR.parts:
        walked = walked / part
        if (root / walked).is_symlink():
            raise ActionRefused("the receipts store is reached through a symlink")
    target = root / relative
    if target.resolve().parent != (root / RECEIPTDIR).resolve():
        raise ActionRefused("receiptPath resolves outside the receipts store")
    return target


def storeFiles(root: Path) -> list[Path]:
    """Every receipts file of this checkout, whatever run wrote it."""

    directory = root / RECEIPTDIR
    if not directory.is_dir() or directory.is_symlink():
        return []
    return sorted(path for path in directory.glob("*.jsonl") if path.is_file() and not path.is_symlink())


def closedEntries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in storeFiles(root):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict) and entry.get("outcome") == "closed" and isinstance(entry.get("closedAt"), str):
                entries.append(entry)
    return entries


def parseClosedAt(text: str) -> datetime | None:
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def closuresWithinHour(root: Path, now: datetime) -> int:
    """Closures recorded in any run whose closedAt falls in the 60 minutes before ``now``."""
    start = now - timedelta(minutes=60)
    count = 0
    for entry in closedEntries(root):
        moment = parseClosedAt(entry["closedAt"])
        if moment is not None and start <= moment <= now:
            count += 1
    return count


def closuresInUtcHour(root: Path, now: datetime) -> int:
    hour = now.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    count = 0
    for entry in closedEntries(root):
        moment = parseClosedAt(entry["closedAt"])
        if moment is not None and hour <= moment.astimezone(timezone.utc) < hour + timedelta(hours=1):
            count += 1
    return count


def hourlyBudget(root: Path, now: datetime, policy: HygienePolicy) -> int:
    """Closures still allowed right now, across every run: the hard cap over 60 minutes and the policy cap per UTC hour."""
    rolling = HARD_HOURLY_CAP - closuresWithinHour(root, now)
    perHour = policy.maxClosuresPerRun - closuresInUtcHour(root, now)
    return max(0, min(rolling, perHour))


RECORDED_OUTCOMES = ("closed", "already-closed")


def recordedReceipt(receipt: Path, key: str, issue: int) -> dict[str, Any] | None:
    """The last receipt this checkout recorded for (key, issue) as done: the one a repeat run reports."""

    if not receipt.is_file():
        return None
    found = None
    for line in receipt.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("key") == key and entry.get("issue") == issue \
                and entry.get("outcome") in RECORDED_OUTCOMES:
            found = entry
    return found


def closedCountFor(receipt: Path, runId: str) -> int:
    if not receipt.is_file():
        return 0
    count = 0
    for line in receipt.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("runId") == runId and entry.get("outcome") == "closed":
            count += 1
    return count


def workflowsCoveredBy(plan: Mapping[str, Any], policy: HygienePolicy) -> bool:
    """An A5 closure is proven only when every workflow it names is listed in policy."""
    if not policy.a5Disabled:
        return False
    names = [entry.get("ref") for entry in plan.get("evidence") or [] if entry.get("type") == "workflow"]
    return bool(names) and all(name in policy.a5Disabled for name in names)


def sameRepo(left: Any, right: Any) -> bool:
    return isinstance(left, str) and isinstance(right, str) and left.strip().lower() == right.strip().lower() and bool(left.strip())


def gateClosure(root: Path, action: Mapping[str, Any], receipt: Path, runId: str, now: datetime,
                repo: str | None = None) -> dict[str, Any]:
    """Every check a closure must pass before a forge is built. Returns the re-derived plan. Raises ActionRefused.

    ``repo`` is the repository the caller will write to (the close script's ``--repo``, or the reconcile
    ``--repo``). It must equal the action's repository and the census repository, case-insensitively.
    """

    from gaia_cli.steward.policy import PolicyError, StewardPolicy

    if action.get("authority") != "A":
        raise ActionRefused("only authority A closures are performed")
    try:
        loaded = StewardPolicy.load(root)
    except PolicyError as exc:
        raise ActionRefused(f"steward policy unreadable: {exc}") from exc
    if loaded.issue_hygiene_error:
        raise ActionRefused(loaded.issue_hygiene_error)
    policy = loaded.issue_hygiene
    if not policy.writesEnabled:
        raise ActionRefused("issueHygiene.writesEnabled is false; closures are not performed")
    if action["ruleId"] not in policy.enabledRules:
        raise ActionRefused(f"rule {action['ruleId']} is not enabled in issueHygiene.enabledRules")
    if action["ruleId"] == RULE_A5 and not policy.a5Disabled:
        raise ActionRefused("A5 needs a non-empty issueHygiene.a5Disabled list")
    if closedCountFor(receipt, runId) >= policy.maxClosuresPerRun:
        raise ActionRefused(f"maxClosuresPerRun ({policy.maxClosuresPerRun}) already reached for run {runId}")
    if hourlyBudget(root, now, policy) <= 0:
        raise ActionRefused("the closure budget for this hour is spent (policy cap, or the hard cap of 25 in 60 minutes)")

    census = loadCensus(root / CENSUS_INPUT, now=now, maxAgeSeconds=policy.maxCensusAgeSeconds)
    if not census.status.complete:
        raise ActionRefused(f"issue census is {census.status.status}; nothing is proven")
    censusRepo = (census.document or {}).get("repo")
    if not sameRepo(censusRepo, action["repo"]) or (repo is not None and not sameRepo(censusRepo, repo)):
        raise ActionRefused("the census, the action and the target repository do not name the same repository")
    manifest = reconcile(census, buildRegistryIndex(root), policy, now, workflowDisabled=workflowProbesFor(census, policy))
    if observedDigest(manifest) != action["manifestSha256"]:
        raise ActionRefused("the action's manifest no longer matches the census; the next scan re-observes it")
    everything = replace(policy, writesEnabled=True, maxClosuresPerRun=PLAN_CEILING)
    matching = [plan for plan in planClosures(manifest, everything)
                if plan["key"] == action["key"] and plan["issue"] == action["issue"] and plan["ruleId"] == action["ruleId"]]
    if len(matching) != 1:
        raise ActionRefused("the census no longer proves this closure")
    plan = matching[0]
    if plan["closureSha8"] != action["closureSha8"] or plan["preservedSha256"] != action["preservedSha256"]:
        raise ActionRefused("the action's closure digests do not match the re-derived closure")
    if plan["stateReason"] != action["stateReason"] or plan.get("duplicateOf") != action.get("duplicateOf"):
        raise ActionRefused("the action's transition does not match the re-derived closure")
    if "comment" in action and action["comment"] != plan["comment"]:
        raise ActionRefused("the action's closing comment does not match the re-derived comment")
    if plan["ruleId"] == RULE_A5 and not workflowsCoveredBy(plan, policy):
        raise ActionRefused("A5 evidence names workflows that policy does not list")
    return plan

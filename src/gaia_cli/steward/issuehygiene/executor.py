"""The one closure gate for issue hygiene (contract sections 3.5 and 7, lanes B7 and B8).

Every write that closes a GitHub issue passes through ``gateClosure`` and then ``reserveClosure``.
``scripts/steward_issue_close.py`` calls both for a single ``forge.close_issue`` action.
``scripts/steward_issue_reconcile.py --apply-closures`` calls both for each proven plan of a manifest.
Nothing else may build a forge for a closure.

``gateClosure`` re-derives the closure from the checkout, so a stored action is only a claim:

* the policy must set ``issueHygiene.writesEnabled``, the rule must be enabled, and A5 needs its ``a5Disabled`` list;
* the pair must not be recorded as done in ANY receipts file or in the outcome store (B8 H-1);
* this run may not exceed ``maxClosuresPerRun``, and no UTC hour may exceed the policy cap or the hard cap of 25 closures
  in any 60 minutes, counting every run's receipts and every open reservation (``hourlyBudget``);
* the receipts store is fixed (``.gaia/steward/issue-hygiene/receipts``) and reached through no symlink;
* the census must be complete, fresh, and for the repository the action and the caller name (``repo``);
* the closure's own evidence must be unchanged: ``itemSha256`` is the digest of this issue's proof (B8 H-3b), so
  unrelated census churn never refuses it;
* the closure's digests (``closureSha8`` and ``preservedSha256``) must match the re-derived plan.

``reserveClosure`` takes the budget slot under the repository's budget lock and records it as a ``reserved`` line before
the forge is called (B8 M-3). A reservation resolves when a terminal line for the same pair is appended to the same file.

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
from gaia_cli.steward.issuehygiene.closure import (
    RECEIPT_SCHEMA,
    ActionRefused,
    appendReceipt,
    budgetLock,
    compactPlan,
    isoTime,
    itemDigest,
    planClosures,
)
from gaia_cli.steward.issuehygiene.hygienepolicy import HygienePolicy
from gaia_cli.steward.issuehygiene.outcomes import OutcomeStoreError, donePairs
from gaia_cli.steward.issuehygiene.reconcile import RULE_A5, reconcile, workflowProbesFor
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from gaia_cli.steward.issuehygiene.sensor import CENSUS_INPUT

RECEIPTDIR = Path(".gaia/steward/issue-hygiene/receipts")
HARD_HOURLY_CAP = 25
PLAN_CEILING = 1_000_000
RESERVED = "reserved"
REQUIRED = (
    "key", "issue", "ruleId", "authority", "state", "stateReason", "duplicateOf", "parent", "canonical",
    "expectedSnapshot", "evidence", "closureSha8", "preservedSha256", "receiptPath", "manifestSha256", "repo",
    "itemSha256",
)
__all__ = [
    "ActionRefused", "HARD_HOURLY_CAP", "PLAN_CEILING", "RECEIPTDIR", "RECORDED_OUTCOMES", "AlreadyRecorded",
    "closedCountFor", "closedEntries", "closuresInUtcHour", "closuresWithinHour", "compactPlan", "gateClosure",
    "hourlyBudget", "loadActionFile", "loadHygienePolicyOrRefuse", "openReservations", "receiptFor",
    "recordedReceipt", "reserveClosure", "sameRepo", "storeFiles",
]


class AlreadyRecorded(ActionRefused):
    """The pair is already recorded as done. A repeat run reports the recorded outcome; nothing is performed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="already-recorded")


def loadActionFile(path: Path) -> dict[str, Any]:
    try:
        action = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ActionRefused(f"action file unreadable: {type(exc).__name__}", code="action-unreadable") from exc
    if not isinstance(action, dict):
        raise ActionRefused("action file must hold a JSON object", code="action-unreadable")
    missing = [name for name in REQUIRED if name not in action]
    if missing:
        raise ActionRefused(f"action is missing {', '.join(missing)}", code="action-unreadable")
    issue = action["issue"]
    if not isinstance(issue, int) or isinstance(issue, bool) or issue <= 0:
        raise ActionRefused("action issue must be a positive integer", code="action-unreadable")
    if not isinstance(action["repo"], str) or not action["repo"].strip():
        raise ActionRefused("action names no repository", code="action-unreadable")
    return action


def receiptFor(root: Path, receiptPath: Any) -> Path:
    """The receipt must sit in the issue-hygiene receipts store, reached through no symlink."""

    if not isinstance(receiptPath, str):
        raise ActionRefused("receiptPath must be a string", code="receipt-path")
    relative = Path(receiptPath)
    if relative.is_absolute() or relative.parent != RECEIPTDIR or relative.suffix != ".jsonl" or ".." in relative.parts:
        raise ActionRefused("receiptPath must be a .jsonl file under .gaia/steward/issue-hygiene/receipts/", code="receipt-path")
    walked = Path(".")
    for part in RECEIPTDIR.parts:
        walked = walked / part
        if (root / walked).is_symlink():
            raise ActionRefused("the receipts store is reached through a symlink", code="receipt-path")
    target = root / relative
    if target.resolve().parent != (root / RECEIPTDIR).resolve():
        raise ActionRefused("receiptPath resolves outside the receipts store", code="receipt-path")
    return target


def storeFiles(root: Path) -> list[Path]:
    """Every receipts file of this checkout, whatever run wrote it."""

    directory = root / RECEIPTDIR
    if not directory.is_dir() or directory.is_symlink():
        return []
    return sorted(path for path in directory.glob("*.jsonl") if path.is_file() and not path.is_symlink())


def fileEntries(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def openReservations(path: Path) -> list[dict[str, Any]]:
    """Reservations in one receipts file that no later line for the same (key, issue) has resolved (B8 M-3).

    A reservation left by a crash stays open until the same pair gets a terminal line, which bounds it to its UTC hour
    for the policy cap and to 60 minutes for the hard cap.
    """
    if not path.is_file():
        return []
    open_: dict[tuple[Any, Any], dict[str, Any]] = {}
    for entry in fileEntries(path):
        pair = (entry.get("key"), entry.get("issue"))
        if entry.get("outcome") == RESERVED:
            open_[pair] = entry
        else:
            open_.pop(pair, None)
    return list(open_.values())


def closedEntries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in storeFiles(root):
        for entry in fileEntries(path):
            if entry.get("outcome") == "closed" and isinstance(entry.get("closedAt"), str):
                entries.append(entry)
    return entries


def parseClosedAt(text: str) -> datetime | None:
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def countedMoments(root: Path) -> list[datetime]:
    """Every closure this checkout has performed or reserved: closed receipts and open reservations, in any run."""
    moments: list[datetime] = []
    for path in storeFiles(root):
        for entry in fileEntries(path):
            if entry.get("outcome") == "closed" and isinstance(entry.get("closedAt"), str):
                moment = parseClosedAt(entry["closedAt"])
                if moment is not None:
                    moments.append(moment)
        for entry in openReservations(path):
            moment = parseClosedAt(entry["reservedAt"]) if isinstance(entry.get("reservedAt"), str) else None
            if moment is not None:
                moments.append(moment)
    return moments


def closuresWithinHour(root: Path, now: datetime) -> int:
    """Closures (performed or reserved) in any run whose moment falls in the 60 minutes before ``now``."""
    start = now - timedelta(minutes=60)
    return sum(1 for moment in countedMoments(root) if start <= moment <= now)


def closuresInUtcHour(root: Path, now: datetime) -> int:
    hour = now.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return sum(1 for moment in countedMoments(root) if hour <= moment.astimezone(timezone.utc) < hour + timedelta(hours=1))


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
    for entry in fileEntries(receipt):
        if entry.get("key") == key and entry.get("issue") == issue and entry.get("outcome") in RECORDED_OUTCOMES:
            found = entry
    return found


def closedCountFor(receipt: Path, runId: str) -> int:
    """Closures this run has performed or reserved in its receipts file (B8 M-3: reservations count for the run cap)."""
    if not receipt.is_file():
        return 0
    closed = sum(1 for entry in fileEntries(receipt) if entry.get("runId") == runId and entry.get("outcome") == "closed")
    reserved = sum(1 for entry in openReservations(receipt) if entry.get("runId") == runId)
    return closed + reserved


def workflowsCoveredBy(plan: Mapping[str, Any], policy: HygienePolicy) -> bool:
    """An A5 closure is proven only when every workflow it names is listed in policy."""
    if not policy.a5Disabled:
        return False
    names = [entry.get("ref") for entry in plan.get("evidence") or [] if entry.get("type") == "workflow"]
    return bool(names) and all(name in policy.a5Disabled for name in names)


def sameRepo(left: Any, right: Any) -> bool:
    return isinstance(left, str) and isinstance(right, str) and left.strip().lower() == right.strip().lower() and bool(left.strip())


def loadHygienePolicyOrRefuse(root: Path) -> HygienePolicy:
    """The checkout's issue-hygiene policy, read through the one steward policy loader. Refuses when it is unreadable."""

    from gaia_cli.steward.policy import PolicyError, StewardPolicy

    try:
        loaded = StewardPolicy.load(root)
    except PolicyError as exc:
        raise ActionRefused(f"steward policy unreadable: {exc}", code="policy-unreadable") from exc
    if loaded.issue_hygiene_error:
        raise ActionRefused(loaded.issue_hygiene_error, code="policy-unreadable")
    return loaded.issue_hygiene


def reserveClosure(root: Path, receipt: Path, policy: HygienePolicy, now: datetime, key: str, issue: int,
                   runId: str, repo: str) -> None:
    """Take one closure slot: re-check the run cap and the hourly budget under the repository's budget lock, then write a
    ``reserved`` line to the receipts file. The line is written before the forge is called (B8 M-3). Raises ActionRefused."""

    with budgetLock(repo):
        if closedCountFor(receipt, runId) >= policy.maxClosuresPerRun:
            raise ActionRefused(f"maxClosuresPerRun ({policy.maxClosuresPerRun}) already reached for run {runId}", code="run-cap")
        if hourlyBudget(root, now, policy) <= 0:
            raise ActionRefused("the closure budget for this hour is spent (policy cap, or the hard cap of 25 in 60 minutes)",
                                code="hour-budget")
        appendReceipt(receipt, {
            "schemaVersion": RECEIPT_SCHEMA, "outcome": RESERVED, "key": key, "issue": issue, "runId": runId,
            "reservedAt": isoTime(now),
        })


def gateClosure(root: Path, action: Mapping[str, Any], receipt: Path, runId: str, now: datetime,
                repo: str | None = None) -> dict[str, Any]:
    """Every check a closure must pass before a forge is built. Returns the re-derived plan. Raises ActionRefused.

    ``repo`` is the repository the caller will write to (the close script's ``--repo``, or the reconcile
    ``--repo``). It must equal the action's repository and the census repository, case-insensitively.
    Refusals carry a reason ``code`` that the driver records as the outcome of the step.
    """

    if action.get("authority") != "A":
        raise ActionRefused("only authority A closures are performed", code="authority")
    from .authority import closureAuthorityApproved

    if not closureAuthorityApproved(root):
        raise ActionRefused("issue closure authority is an unratified Class C proposal", code="authority-pending")
    policy = loadHygienePolicyOrRefuse(root)
    if not policy.writesEnabled:
        raise ActionRefused("issueHygiene.writesEnabled is false; closures are not performed", code="writes-disabled")
    if action["ruleId"] not in policy.enabledRules:
        raise ActionRefused(f"rule {action['ruleId']} is not enabled in issueHygiene.enabledRules", code="rule-disabled")
    if action["ruleId"] == RULE_A5 and not policy.a5Disabled:
        raise ActionRefused("A5 needs a non-empty issueHygiene.a5Disabled list", code="a5-unlisted")
    try:
        recorded = donePairs(root)
    except OutcomeStoreError as exc:
        raise ActionRefused(f"closure outcomes unreadable: {exc}", code="store-unreadable") from exc
    if (action["key"], action["issue"]) in recorded:
        raise AlreadyRecorded("this pair is already recorded as done in the receipts store or outcome store; "
                              "a reopened issue is a founder decision, never a second closure")
    if closedCountFor(receipt, runId) >= policy.maxClosuresPerRun:
        raise ActionRefused(f"maxClosuresPerRun ({policy.maxClosuresPerRun}) already reached for run {runId}", code="run-cap")
    if hourlyBudget(root, now, policy) <= 0:
        raise ActionRefused("the closure budget for this hour is spent (policy cap, or the hard cap of 25 in 60 minutes)",
                            code="hour-budget")

    census = loadCensus(root / CENSUS_INPUT, now=now, maxAgeSeconds=policy.maxCensusAgeSeconds)
    if not census.status.complete:
        raise ActionRefused(f"issue census is {census.status.status}; nothing is proven", code="census-not-complete")
    censusRepo = (census.document or {}).get("repo")
    if not sameRepo(censusRepo, action["repo"]) or (repo is not None and not sameRepo(censusRepo, repo)):
        raise ActionRefused("the census, the action and the target repository do not name the same repository", code="repo-mismatch")
    manifest = reconcile(census, buildRegistryIndex(root), policy, now, workflowDisabled=workflowProbesFor(census, policy))
    everything = replace(policy, writesEnabled=True, maxClosuresPerRun=PLAN_CEILING)
    matching = [plan for plan in planClosures(manifest, everything, done=recorded)
                if plan["key"] == action["key"] and plan["issue"] == action["issue"] and plan["ruleId"] == action["ruleId"]]
    if len(matching) != 1:
        raise ActionRefused("the census no longer proves this closure", code="not-proven")
    plan = matching[0]
    if itemDigest(plan) != action.get("itemSha256"):
        raise ActionRefused("this closure's own evidence changed since it was emitted; the next scan re-observes it",
                            code="item-changed")
    if plan["closureSha8"] != action["closureSha8"] or plan["preservedSha256"] != action["preservedSha256"]:
        raise ActionRefused("the action's closure digests do not match the re-derived closure", code="item-changed")
    if plan["stateReason"] != action["stateReason"] or plan.get("duplicateOf") != action.get("duplicateOf"):
        raise ActionRefused("the action's transition does not match the re-derived closure", code="item-changed")
    if "comment" in action and action["comment"] != plan["comment"]:
        raise ActionRefused("the action's closing comment does not match the re-derived comment", code="item-changed")
    if plan["ruleId"] == RULE_A5 and not workflowsCoveredBy(plan, policy):
        raise ActionRefused("A5 evidence names workflows that policy does not list", code="a5-unlisted")
    return plan

#!/usr/bin/env python3
"""Perform one ``forge.close_issue`` action and print its outcome (#2130, lane D2, gated in B5).

    python scripts/steward_issue_close.py --action .gaia/steward/drive/closures/RUN--STEP.json

The action file is the ``params`` object of a ``forge.close_issue`` action. This script does not trust
it. Before any forge object is built it re-derives the proof from the checkout:

1. ``founder/steward/POLICY.yaml`` must set ``issueHygiene.writesEnabled: true``.
2. The action's rule must be in ``enabledRules``. An A5 closure also needs a non-empty ``a5Disabled``
   list that covers every workflow its evidence names.
3. This run may not exceed ``maxClosuresPerRun``: the receipts already written for this run id that
   record a ``closed`` outcome count against the cap.
4. The receipt path must sit under ``.gaia/steward/issue-hygiene/receipts/`` with no symlink on the way.
5. The census the sensor reads must be complete and fresh.
6. Reconciliation of that census must reproduce the action's ``manifestSha256`` (the same digest the sensor
   reports) and must still prove the same (key, issue, rule). Its closing comments must equal the action's.

Only then does ``closure.executeClosure`` re-read the live issue, post or find the marked comments, close
the issue and append one receipt. Nothing is deleted and no registry file is touched. The plan that runs
is the re-derived one, never the action file's copy.

Stdout is one JSON outcome line for ``gaia steward full record`` (exactly one proof field: ``commentUrl``,
``commentId`` or ``markerVerified``). Stderr carries refusal reasons only; the token is never printed.

Exit codes
  0  closed, already-closed or stale-skip (nothing wrong; the outcome says which)
  1  failed (this item only; retryable, counted by the runner). Includes blocked-identity: the live
     issue is locked, a pull request, renumbered, or transferred, so nothing was written.
  2  refused: the action cannot be performed as written, or the checkout no longer proves it. No forge is
     built and nothing is written. The runner treats this as non-retryable and skips the action.
  3  blocked: auth, rate or transport failure, or no token. The batch stops.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gaia_cli.steward.issuehygiene.closure import ForgeBlockedError, closureProven, executeClosure, planClosures  # noqa: E402
from gaia_cli.steward.issuehygiene.census import loadCensus  # noqa: E402
from gaia_cli.steward.issuehygiene.hygienepolicy import HygienePolicy  # noqa: E402
from gaia_cli.steward.issuehygiene.outcomes import RECEIPTDIR  # noqa: E402
from gaia_cli.steward.issuehygiene.reconcile import RULE_A5, reconcile  # noqa: E402
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex  # noqa: E402
from gaia_cli.steward.issuehygiene.sensor import CENSUS_INPUT, observedDigest  # noqa: E402
from gaia_cli.steward.issuehygiene.reconcile import workflowProbesFor  # noqa: E402
from gaia_cli.steward.policy import PolicyError, StewardPolicy  # noqa: E402
from steward_issue_census import DEFAULT_REPO  # noqa: E402
from steward_issue_reconcile import GhForge  # noqa: E402

REQUIRED = (
    "key", "issue", "ruleId", "authority", "state", "stateReason", "duplicateOf", "parent", "canonical",
    "reason", "expectedSnapshot", "original", "evidence", "comment", "receiptPath", "manifestSha256",
)
PLAN_CEILING = 1_000_000
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2
EXIT_BLOCKED = 3
EXIT_BY_OUTCOME = {
    "closed": EXIT_OK, "already-closed": EXIT_OK, "stale-skip": EXIT_OK,
    "blocked-identity": EXIT_FAILED, "failed": EXIT_FAILED, "blocked": EXIT_BLOCKED,
}


class ActionRefused(Exception):
    """The action file cannot be performed as written, or the checkout no longer proves it."""


def loadAction(path: Path) -> dict[str, Any]:
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
    if not isinstance(action["comment"], str) or not action["comment"].strip():
        raise ActionRefused("action carries no closing comment")
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


def workflowsCoveredBy(plan: dict[str, Any], policy: HygienePolicy) -> bool:
    """An A5 closure is proven only when every workflow it names is listed in policy."""
    if not policy.a5Disabled:
        return False
    names = [entry.get("ref") for entry in plan.get("evidence") or [] if entry.get("type") == "workflow"]
    return bool(names) and all(name in policy.a5Disabled for name in names)


def gate(root: Path, action: dict[str, Any], receipt: Path, runId: str, now: datetime) -> dict[str, Any]:
    """Every check that must pass before a forge is built. Returns the re-derived plan. Raises ActionRefused."""
    if action.get("authority") != "A":
        raise ActionRefused("only authority A closures are performed")
    try:
        policy = StewardPolicy.load(root).issue_hygiene
    except PolicyError as exc:
        raise ActionRefused(f"steward policy unreadable: {exc}") from exc
    if not policy.writesEnabled:
        raise ActionRefused("issueHygiene.writesEnabled is false; closures are not performed")
    if action["ruleId"] not in policy.enabledRules:
        raise ActionRefused(f"rule {action['ruleId']} is not enabled in issueHygiene.enabledRules")
    if action["ruleId"] == RULE_A5 and not policy.a5Disabled:
        raise ActionRefused("A5 needs a non-empty issueHygiene.a5Disabled list")
    if closedCountFor(receipt, runId) >= policy.maxClosuresPerRun:
        raise ActionRefused(f"maxClosuresPerRun ({policy.maxClosuresPerRun}) already reached for run {runId}")

    census = loadCensus(root / CENSUS_INPUT, now=now, maxAgeSeconds=policy.maxCensusAgeSeconds)
    if not census.status.complete:
        raise ActionRefused(f"issue census is {census.status.status}; nothing is proven")
    manifest = reconcile(census, buildRegistryIndex(root), policy, now, workflowDisabled=workflowProbesFor(census, policy))
    if observedDigest(manifest) != action["manifestSha256"]:
        raise ActionRefused("the action's manifest no longer matches the census; the next scan re-observes it")
    everything = replace(policy, writesEnabled=True, maxClosuresPerRun=PLAN_CEILING)
    matching = [plan for plan in planClosures(manifest, everything)
                if plan["key"] == action["key"] and plan["issue"] == action["issue"] and plan["ruleId"] == action["ruleId"]]
    if len(matching) != 1:
        raise ActionRefused("the census no longer proves this closure")
    plan = matching[0]
    if plan["comment"] != action["comment"] or (action.get("comments") is not None and action["comments"] != plan["comments"]):
        raise ActionRefused("the action's closing comments do not match the re-derived comments")
    if plan["ruleId"] == RULE_A5 and not workflowsCoveredBy(plan, policy):
        raise ActionRefused("A5 evidence names workflows that policy does not list")
    return plan


def outcomeFrom(receipt: dict[str, Any]) -> dict[str, Any]:
    """The payload ``gaia steward full record`` validates for a forge.close_issue step: one proof field only."""

    outcome: dict[str, Any] = {
        "outcome": receipt["outcome"], "key": receipt["key"], "issue": receipt["issue"],
        "closedAt": receipt.get("closedAt"), "failure": receipt.get("failure"),
        "preservedSha256": receipt.get("preservedSha256"),
    }
    if receipt.get("commentUrl"):
        outcome["commentUrl"] = receipt["commentUrl"]
    elif receipt.get("commentId"):
        outcome["commentId"] = receipt["commentId"]
    elif receipt.get("markerVerified") is True:
        outcome["markerVerified"] = True
    return outcome


def parseArgs(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--action", type=Path, required=True, help="the forge.close_issue params as a JSON file")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository checkout (default: this repo)")
    parser.add_argument("--repo", default=None, help=f"owner/name (default: $GITHUB_REPOSITORY or {DEFAULT_REPO})")
    parser.add_argument("--run-id", default=None, help="receipt run id (default: the receipt file stem)")
    parser.add_argument("--now", default=None, help="RFC 3339 instant for receipts and census age (tests and replays)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, forgeFactory: Callable[[str, str | None], Any] | None = None) -> int:
    args = parseArgs(argv)
    root = args.root.resolve()
    actionPath = args.action if args.action.is_absolute() else root / args.action
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    try:
        action = loadAction(actionPath)
        receipt = receiptFor(root, action["receiptPath"])
        runId = args.run_id or receipt.stem
        plan = gate(root, action, receipt, runId, now)
    except ActionRefused as exc:
        print(f"steward issue close refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    repo = args.repo or os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPO
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    try:
        forge = (forgeFactory or GhForge)(repo, token)
        executed = executeClosure(plan, forge, receipt, now, runId)
    except ValueError as exc:  # executeClosure: not authority A, or an unregistered rule
        print(f"steward issue close refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    except ForgeBlockedError as exc:
        print(f"steward issue close blocked: {exc}", file=sys.stderr)
        return EXIT_BLOCKED
    outcome = outcomeFrom(executed)
    if outcome["outcome"] == "closed" and not closureProven(outcome, plan["issue"], repo):
        print("steward issue close refused: the outcome carries no single valid proof", file=sys.stderr)
        return EXIT_REFUSED
    print(json.dumps(outcome, sort_keys=True))
    return EXIT_BY_OUTCOME[outcome["outcome"]]


if __name__ == "__main__":
    raise SystemExit(main())

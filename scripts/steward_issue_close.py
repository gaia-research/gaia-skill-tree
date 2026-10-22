#!/usr/bin/env python3
"""Perform one ``forge.close_issue`` action and print its outcome (#2130, lane D2, gated in B5, one gate in B7).

    python scripts/steward_issue_close.py --action .gaia/steward/drive/closures/RUN--STEP.json

The action file is the ``params`` object of a ``forge.close_issue`` action. It carries identifiers and digests,
not the closing comments: the executor rebuilds those from the census. This script does not trust the action.
Before any forge object is built it runs ``gaia_cli.steward.issuehygiene.executor.gateClosure``, which re-derives
the proof from the checkout:

1. ``founder/steward/POLICY.yaml`` must set ``issueHygiene.writesEnabled: true``.
2. The action's rule must be in ``enabledRules``. An A5 closure also needs a non-empty ``a5Disabled`` list that
   covers every workflow its evidence names.
3. This run may not exceed ``maxClosuresPerRun``, and the hourly budget (every run's receipts) must not be spent.
4. The receipt path must sit under ``.gaia/steward/issue-hygiene/receipts/`` with no symlink on the way.
5. The census the sensor reads must be complete and fresh, and name the repository the action and ``--repo`` name.
6. Reconciliation of that census must reproduce the action's ``manifestSha256``, and the closure's digests
   (``closureSha8``, ``preservedSha256``) must match the re-derived closure.

Only then does ``closure.executeClosure`` re-read the live issue, post or find the marked comments, close
the issue and append one receipt. Nothing is deleted and no registry file is touched. The plan that runs
is the re-derived one, never the action file's copy. ``--now`` is not accepted for writes: freshness is checked
against the real clock, so an old instant cannot make a stale census look current.

Stdout is one JSON outcome line for ``gaia steward full record`` (exactly one proof field: ``commentUrl``,
``commentId`` or ``markerVerified``). A closure this checkout already performed is printed again from its
receipt, with its recorded outcome. Stderr carries refusal reasons only; the token is never printed.

Exit codes
  0  closed, already-closed, stale-skip, or resumed-done (a repeat of a closure already recorded; the outcome says which)
  1  failed (this item only; retryable, counted by the runner). Includes blocked-identity: the live
     issue is locked, a pull request, renumbered, or transferred, so nothing was written.
  2  refused: the action cannot be performed as written, or the checkout no longer proves it. No forge is
     built and nothing is written. Stdout then carries one ``refused`` outcome line with a machine-readable
     ``reason`` code (B8 H-3a): the driver records it, which settles the step, and a later run may emit the pair again.
  3  blocked: auth, rate or transport failure, or no token. The batch stops.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gaia_cli.steward.clock import utcNow  # noqa: E402
from gaia_cli.steward.issuehygiene.closure import (  # noqa: E402
    ActionRefused,
    ForgeBlockedError,
    closureProven,
    executeClosure,
)
from gaia_cli.steward.issuehygiene.executor import (  # noqa: E402
    AlreadyRecorded,
    gateClosure,
    loadActionFile,
    loadHygienePolicyOrRefuse,
    receiptFor,
    recordedReceipt,
    reserveClosure,
)
from steward_issue_census import DEFAULT_REPO  # noqa: E402
from steward_issue_reconcile import GhForge  # noqa: E402

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2
EXIT_BLOCKED = 3
EXIT_BY_OUTCOME = {
    "closed": EXIT_OK, "already-closed": EXIT_OK, "stale-skip": EXIT_OK, "resumed-done": EXIT_OK,
    "blocked-identity": EXIT_FAILED, "failed": EXIT_FAILED, "blocked": EXIT_BLOCKED,
}


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


def refusal(exc: ActionRefused, action: dict[str, Any] | None) -> int:
    """Refuse with exit 2. The reason is printed on stderr, and one ``refused`` outcome line goes to stdout (B8 H-3a),
    so the driver can record the refusal and settle the step. The reason ``code`` is machine-readable."""

    print(f"steward issue close refused: {exc}", file=sys.stderr)
    if action is not None and isinstance(action.get("key"), str) and isinstance(action.get("issue"), int):
        line = {"outcome": "refused", "reason": exc.code, "key": action["key"], "issue": action["issue"],
                "failure": str(exc)[:300], "closedAt": None}
        print(json.dumps(line, sort_keys=True))
    return EXIT_REFUSED


def parseArgs(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--action", type=Path, required=True, help="the forge.close_issue params as a JSON file")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository checkout (default: this repo)")
    parser.add_argument("--repo", default=None, help=f"owner/name (default: $GITHUB_REPOSITORY or {DEFAULT_REPO})")
    parser.add_argument("--run-id", default=None, help="receipt run id (default: the receipt file stem)")
    parser.add_argument("--now", default=None,
                        help="accepted for compatibility and IGNORED: freshness uses the real clock")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, forgeFactory: Callable[[str, str | None], Any] | None = None) -> int:
    args = parseArgs(argv)
    root = args.root.resolve()
    actionPath = args.action if args.action.is_absolute() else root / args.action
    if args.now is not None:
        print("note: --now is ignored by the closure executor; freshness uses the real clock", file=sys.stderr)
    now = utcNow()
    repo = args.repo or os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPO
    action: dict[str, Any] | None = None
    receipt: Path | None = None
    try:
        action = loadActionFile(actionPath)
        receipt = receiptFor(root, action["receiptPath"])
        runId = args.run_id or receipt.stem
        plan = gateClosure(root, action, receipt, runId, now, repo)
    except AlreadyRecorded as exc:
        # A repeat of a closure this checkout already recorded: report the recorded outcome. Recorded elsewhere: refuse.
        done = recordedReceipt(receipt, action["key"], action["issue"]) if receipt is not None and action else None
        if done is None:
            return refusal(exc, action)
        return printRecorded(done, action["issue"], repo)
    except ActionRefused as exc:
        return refusal(exc, action)
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    try:
        forge = (forgeFactory or GhForge)(repo, token)
        policy = loadHygienePolicyOrRefuse(root)
        executed = executeClosure(
            plan, forge, receipt, now, runId, repo,
            reserve=lambda: reserveClosure(root, receipt, policy, now, plan["key"], plan["issue"], runId, repo),
        )
    except ActionRefused as exc:  # the budget reservation, or the policy, refused: nothing was written
        return refusal(exc, action)
    except ValueError as exc:  # executeClosure: not authority A, or an unregistered rule
        return refusal(ActionRefused(str(exc)), action)
    except ForgeBlockedError as exc:
        print(f"steward issue close blocked: {exc}", file=sys.stderr)
        return EXIT_BLOCKED
    if executed["outcome"] == "resumed-done":
        done = recordedReceipt(receipt, plan["key"], plan["issue"])
        if done is None:
            return refusal(ActionRefused("the pair is recorded as done elsewhere in the receipts store", code="already-recorded"), action)
        executed = done
    return printRecorded(executed, plan["issue"], repo)


def printRecorded(executed: dict[str, Any], issue: int, repo: str) -> int:
    outcome = outcomeFrom(executed)
    if outcome["outcome"] == "closed" and not closureProven(outcome, issue, repo):
        print("steward issue close refused: the outcome carries no single valid proof", file=sys.stderr)
        return EXIT_REFUSED
    print(json.dumps(outcome, sort_keys=True))
    return EXIT_BY_OUTCOME[outcome["outcome"]]


if __name__ == "__main__":
    raise SystemExit(main())

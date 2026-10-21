#!/usr/bin/env python3
"""Perform one ``forge.close_issue`` action and print its outcome (#2130, lane D2).

    python scripts/steward_issue_close.py --action .gaia/steward/drive/closures/RUN--STEP.json

The action file is the ``params`` object of a ``forge.close_issue`` action: a closure plan
from ``closure.planClosures`` with its rebuilt closing ``comment`` and a ``receiptPath``
under ``.gaia/steward/issue-hygiene/receipts/``. ``closure.executeClosure`` re-reads the
live issue, requires the manifest snapshot to still hold, finds or posts the marked
comment, closes the issue and appends one receipt. Nothing is deleted and no registry
file is touched.

Stdout is one JSON outcome line for ``gaia steward full record``. Stderr carries usage
problems only; the token is never printed.

Exit codes
  0  closed, already-closed or stale-skip (nothing wrong; the outcome says which)
  1  failed (this item only; retryable, counted by the runner)
  2  refused input: the action file is missing a field or names a receipt outside the store
  3  blocked: auth, rate or transport failure, or no token; nothing is known about the item
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gaia_cli.steward.issuehygiene.closure import ForgeBlockedError, executeClosure  # noqa: E402
from gaia_cli.steward.issuehygiene.outcomes import RECEIPTDIR  # noqa: E402
from steward_issue_census import DEFAULT_REPO  # noqa: E402
from steward_issue_reconcile import GhForge  # noqa: E402

REQUIRED = (
    "key", "issue", "ruleId", "authority", "state", "stateReason", "duplicateOf", "parent", "canonical",
    "reason", "expectedSnapshot", "original", "evidence", "comment", "receiptPath", "manifestSha256",
)
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2
EXIT_BLOCKED = 3
EXIT_BY_OUTCOME = {
    "closed": EXIT_OK, "already-closed": EXIT_OK, "stale-skip": EXIT_OK,
    "failed": EXIT_FAILED, "blocked": EXIT_BLOCKED,
}


class ActionRefused(Exception):
    """The action file cannot be performed as written."""


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
    """The receipt must sit in the issue-hygiene receipts store, never anywhere else."""

    if not isinstance(receiptPath, str):
        raise ActionRefused("receiptPath must be a string")
    relative = Path(receiptPath)
    if relative.is_absolute() or relative.parent != RECEIPTDIR or relative.suffix != ".jsonl" or ".." in relative.parts:
        raise ActionRefused("receiptPath must be a .jsonl file under .gaia/steward/issue-hygiene/receipts/")
    return root / relative


def outcomeFrom(receipt: dict[str, Any]) -> dict[str, Any]:
    """The payload ``gaia steward full record`` validates for a forge.close_issue step."""

    return {
        "outcome": receipt["outcome"], "key": receipt["key"], "issue": receipt["issue"],
        "commentUrl": receipt.get("commentUrl"), "commentId": receipt.get("commentId"),
        "markerVerified": receipt.get("markerVerified") is True, "closedAt": receipt.get("closedAt"),
        "failure": receipt.get("failure"),
    }


def parseArgs(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--action", type=Path, required=True, help="the forge.close_issue params as a JSON file")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository checkout (default: this repo)")
    parser.add_argument("--repo", default=None, help=f"owner/name (default: $GITHUB_REPOSITORY or {DEFAULT_REPO})")
    parser.add_argument("--run-id", default=None, help="receipt run id (default: the receipt file stem)")
    parser.add_argument("--now", default=None, help="RFC 3339 instant for receipts (tests and replays)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, forgeFactory: Callable[[str, str | None], Any] | None = None) -> int:
    args = parseArgs(argv)
    root = args.root.resolve()
    actionPath = args.action if args.action.is_absolute() else root / args.action
    try:
        action = loadAction(actionPath)
        receipt = receiptFor(root, action["receiptPath"])
    except ActionRefused as exc:
        print(f"steward issue close refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
    repo = args.repo or os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPO
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    runId = args.run_id or receipt.stem
    try:
        forge = (forgeFactory or GhForge)(repo, token)
        outcome = outcomeFrom(executeClosure(action, forge, receipt, now, runId))
    except ValueError as exc:  # executeClosure: not authority A, or an unregistered rule
        print(f"steward issue close refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    except ForgeBlockedError as exc:
        print(f"steward issue close blocked: {exc}", file=sys.stderr)
        return EXIT_BLOCKED
    print(json.dumps(outcome, sort_keys=True))
    return EXIT_BY_OUTCOME[outcome["outcome"]]


if __name__ == "__main__":
    raise SystemExit(main())

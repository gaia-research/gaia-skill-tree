#!/usr/bin/env python3
"""Turn `gh run list --json ...` output into the ci-health sensor's driver input.

The Steward sensors never touch the network. A driver (the scheduled workflow,
or an operator) collects CI history and hands it over as
`.gaia/steward/inputs/ci-runs.json` (`steward-ci-runs-v1`). This script is
that hand-over: a pure transform with no network access of its own.

    gh run list --branch main --limit 200 \
      --json workflowName,workflowDatabaseId,conclusion,headSha,createdAt,url,attempt,status > runs.json
    python scripts/steward_collect_ci_runs.py runs.json \
      --repository gaia-research/gaia-skill-tree --branch main

Runs that have not completed carry no conclusion and are skipped: an
in-progress run is not evidence either way.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "steward-ci-runs-v1"
OUTPUT = Path(".gaia/steward/inputs/ci-runs.json")
MAX_RUNS = 5000


class InputError(ValueError):
    """The gh output is not a list of run objects with the required fields."""


def convert(raw: Any, *, repository: str, branch: str, collected_at: str) -> dict[str, Any]:
    if not isinstance(raw, list):
        raise InputError("gh run list output must be a JSON list")
    if len(raw) > MAX_RUNS:
        raise InputError(f"more than {MAX_RUNS} runs; narrow the gh query")
    runs: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise InputError(f"run {index} is not an object")
        if item.get("status") != "completed" or not item.get("conclusion"):
            continue
        attempt = item.get("attempt")
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
            raise InputError(f"run {index} has no integer attempt")
        entry = {"runAttempt": attempt}
        for target, source in (
            ("workflow", "workflowName"),
            ("conclusion", "conclusion"),
            ("headSha", "headSha"),
            ("createdAt", "createdAt"),
            ("url", "url"),
        ):
            value = item.get(source)
            if not isinstance(value, str) or not value:
                raise InputError(f"run {index} is missing {source}")
            entry[target] = value
        # Optional stable workflow identity: two workflows can share a display
        # name, a path or numeric id cannot. The sensor groups on it when present.
        path = item.get("workflowPath")
        if isinstance(path, str) and path:
            entry["workflowPath"] = path
        identifier = item.get("workflowDatabaseId")
        if isinstance(identifier, int) and not isinstance(identifier, bool):
            entry["workflowId"] = identifier
        runs.append(entry)
    return {
        "schemaVersion": SCHEMA,
        "repository": repository,
        "branch": branch,
        "collectedAt": collected_at,
        "runs": runs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="file holding `gh run list --json` output")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        raw = json.loads(args.source.read_text(encoding="utf-8"))
        document = convert(
            raw,
            repository=args.repository,
            branch=args.branch,
            collected_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
    except (OSError, json.JSONDecodeError, InputError) as exc:
        print(f"steward_collect_ci_runs: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(document['runs'])} completed runs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

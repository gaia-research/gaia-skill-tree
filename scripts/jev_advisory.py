#!/usr/bin/env python3
"""scripts/jev_advisory.py — Read-only Jev advisory sidecar CLI.

Usage:
  python scripts/jev_advisory.py --mode {mapping,issues,upstream,evidence,meta,steward} \\
      --input file.json [--output generated-output/jev/report.json] \\
      [--live] [--init-budget] [--state-dir .gaia/jev] \\
      [--max-calls 20] [--monthly-limit-usd 0.5] [--collect-repo] [--offset 0]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from gaia_cli.jevAdvisory import (
    SUPPORTED_MODES,
    load_input,
    run_advisory,
    validate_paths,
)
from gaia_cli.jev import JevClient


def main(argv: list[str] | None = None, client: Any = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gaia Jev Advisory Sidecar: read-only evaluation runner."
    )
    parser.add_argument(
        "--mode",
        choices=sorted(SUPPORTED_MODES),
        default="mapping",
        help="Advisory evaluation mode (default: mapping)",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Path to input JSON file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="generated-output/jev/report.json",
        help="Path to write report JSON (default: generated-output/jev/report.json)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Enable live network calls (requires TYPESAFE_API_KEY and initialized budget)",
    )
    parser.add_argument(
        "--init-budget",
        action="store_true",
        default=False,
        help="Explicitly initialize the current UTC-month entry in the local budget ledger",
    )
    parser.add_argument(
        "--state-dir",
        type=str,
        default=".gaia/jev",
        help="State directory for ledger and cache (default: .gaia/jev)",
    )
    parser.add_argument(
        "--max-calls",
        type=int,
        default=20,
        help="Maximum HTTP calls permitted in this process (0..20, default: 20)",
    )
    parser.add_argument(
        "--monthly-limit-usd",
        type=float,
        default=0.5,
        help="Monthly limit in USD (0..5, default: 0.5)",
    )
    parser.add_argument(
        "--collect-repo",
        action="store_true",
        default=False,
        help="Collect items from local repository (CI alternative to --input)",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Offset to start processing items from (default: 0)",
    )

    args = parser.parse_args(argv)

    # 1. State and path validation must happen BEFORE budget initialization or writes
    try:
        validate_paths(
            input_path=args.input,
            output_path=args.output,
            repo_root=str(_REPO_ROOT),
            state_dir=args.state_dir,
        )
    except (ValueError, FileNotFoundError) as err:
        sys.stderr.write(f"Validation error: {err}\n")
        return 2

    # 2. Client initialization
    if client is None:
        try:
            client = JevClient(
                args.state_dir,
                live=args.live,
                maxCalls=args.max_calls,
                monthlyLimitUsd=args.monthly_limit_usd,
            )
        except Exception as err:
            sys.stderr.write(f"Client initialization error: {err}\n")
            return 1

    # 3. Budget initialization if requested
    if args.init_budget:
        try:
            budget_info = client.initializeBudget()
            print(f"Jev budget initialized: {budget_info}")
        except Exception as err:
            sys.stderr.write(f"Budget initialization error: {err}\n")
            return 1
        if not args.input and not args.collect_repo:
            return 0

    if not args.input and not args.collect_repo:
        sys.stderr.write(
            "Error: Either --input or --collect-repo must be specified (or --init-budget alone).\n"
        )
        return 1

    # 4. Load input
    try:
        items, overflow_reported, total_available = load_input(
            args.mode,
            input_path=args.input,
            collect_repo=args.collect_repo,
            repo_root=str(_REPO_ROOT),
            offset=args.offset,
        )
    except Exception as err:
        sys.stderr.write(f"Input error: {err}\n")
        return 1

    # 5. Run advisory evaluation
    report = run_advisory(
        args.mode,
        items,
        client,
        repo_root=str(_REPO_ROOT),
        overflow_reported=overflow_reported,
        total_available=total_available,
        offset=args.offset,
    )

    # 6. Write output
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(report, fp, indent=2)

    print(
        f"Wrote Jev advisory report ({report['summary']['processedCount']} items, "
        f"{report['summary']['advisoryCount']} advisory, {report['summary']['fallbackCount']} fallback) "
        f"to {args.output}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

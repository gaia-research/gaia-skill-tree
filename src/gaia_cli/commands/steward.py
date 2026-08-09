"""Top-level local Gaia Steward commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gaia_cli.commands.base import Command


class StewardCommand(Command):
    name = "steward"
    help = "Report repository maintenance debt"
    description = "Scan maintenance debt or repair one policy-authorized Class A debt."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        subparsers = parser.add_subparsers(dest="steward_command", metavar="{scan,run}")
        scan = subparsers.add_parser(
            "scan",
            help="Collect observations and report normalized maintenance debt",
            description=(
                "Run local read-only sensors. Only ignored state and immutable receipts "
                "under .gaia/steward/ may be written."
            ),
        )
        scan.add_argument("--json", action="store_true", help="Output the full scan result as JSON")
        run = subparsers.add_parser(
            "run",
            help="Repair at most one eligible Class A debt with independent proof",
            description="Run local sensors then the one policy-authorized Class A repair, if eligible.",
        )
        run.add_argument("--json", action="store_true", help="Output the full run result as JSON")

    def execute(self, args: argparse.Namespace) -> int | None:
        if args.steward_command not in {"scan", "run"}:
            print("usage: gaia steward {scan,run} [--json]", file=sys.stderr)
            return 2

        from gaia_cli.steward.controller import StewardController
        from gaia_cli.steward.policy import PolicyError
        from gaia_cli.steward.receipts import StateError

        try:
            controller = StewardController()
            result = controller.scan(Path(args.registry)) if args.steward_command == "scan" else controller.run(Path(args.registry))
        except (OSError, PolicyError, StateError, RuntimeError, ValueError) as exc:
            print(f"Steward {args.steward_command} failed: {exc}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True, ensure_ascii=False))
            return 0

        receipt = result.receipt
        print(f"Gaia Steward {args.steward_command}")
        print(f"Observations       {receipt.observations_collected}")
        print(f"Open debt          {len(receipt.open_debt)}")
        print(f"Created            {len(receipt.debt_created)}")
        print(f"Updated            {len(receipt.debt_updated)}")
        print(f"Resolved           {len(receipt.debt_resolved)}")
        print(f"Coverage unknown   {len(receipt.coverage_unknown)}")
        print(
            "Authority          "
            f"A {receipt.authority_counts.get('A', 0)}  "
            f"B {receipt.authority_counts.get('B', 0)}  "
            f"C {receipt.authority_counts.get('C', 0)}"
        )
        print("Model dispatches   0")
        print(f"Repairs            {len(receipt.repairs)}")
        print(f"Blocked            {len(receipt.blocked)}")
        print(f"Result             {receipt.result_status}")
        try:
            receipt_display = result.receipt_path.relative_to(Path(args.registry).resolve())
        except ValueError:
            receipt_display = result.receipt_path
        print(f"Receipt            {receipt_display}")
        return 0


COMMAND = StewardCommand()

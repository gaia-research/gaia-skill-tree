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
        subparsers = parser.add_subparsers(
            dest="steward_command", metavar="{scan,run,dispatch,founder}"
        )
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
        dispatch = subparsers.add_parser(
            "dispatch",
            help="Render one report-only, bounded Class B packet",
            description=(
                "Freshly scan known-coverage local state then render one policy-bounded "
                "Class B packet. Never invokes an agent or creates a patch."
            ),
        )
        dispatch.add_argument("debt_id", help="Open Class B debt id to render")
        dispatch.add_argument("--json", action="store_true", help="Output the packet and receipt as JSON")
        founder = subparsers.add_parser(
            "founder",
            help="Render the report-only Class C founder decision queue",
            description=(
                "Freshly scan known-coverage local state and group only by exact "
                "normalized decisionTarget. Never changes canonical state."
            ),
        )
        founder.add_argument("--json", action="store_true", help="Output the queue and receipt as JSON")

    def execute(self, args: argparse.Namespace) -> int | None:
        if args.steward_command not in {"scan", "run", "dispatch", "founder"}:
            print("usage: gaia steward {scan,run,dispatch,founder} [--json]", file=sys.stderr)
            return 2

        from gaia_cli.steward.controller import StewardController
        from gaia_cli.steward.policy import PolicyError
        from gaia_cli.steward.receipts import StateError
        from gaia_cli.steward.routing import RoutingError, render_dispatch, render_founder_queue

        try:
            root = Path(args.registry)
            if args.steward_command == "scan":
                result = StewardController().scan(root)
            elif args.steward_command == "run":
                result = StewardController().run(root)
            elif args.steward_command == "dispatch":
                result = render_dispatch(root, args.debt_id)
            else:
                result = render_founder_queue(root)
        except (OSError, PolicyError, StateError, RoutingError, RuntimeError, ValueError) as exc:
            print(f"Steward {args.steward_command} failed: {exc}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True, ensure_ascii=False))
            return 0

        if args.steward_command in {"dispatch", "founder"}:
            artifact = result.artifact
            print(f"Gaia Steward {args.steward_command}")
            if args.steward_command == "dispatch":
                print(f"Dispatch             {artifact.dispatch_id}")
                print(f"Debt                 {artifact.debt['id']}")
                print(f"Authority            {artifact.authority.value}")
                print(f"Routine              {artifact.routine}")
            else:
                print(f"Queue                {artifact.queue_id}")
                print(f"Founder decisions    {len(artifact.decisions)}")
                for decision in artifact.decisions:
                    print(f"{decision.decision_id}  {decision.decision_target}  ({len(decision.debt_ids)} debt)")
            print("Model dispatches    0")
            try:
                receipt_display = result.receipt_path.relative_to(Path(args.registry).resolve())
            except ValueError:
                receipt_display = result.receipt_path
            print(f"Receipt            {receipt_display}")
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

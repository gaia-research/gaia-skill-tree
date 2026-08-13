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
            dest="steward_command", metavar="{scan,run,dispatch,verify,founder}"
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
        dispatch.add_argument(
            "--prompt",
            action="store_true",
            help=(
                "Print the packet as a harness-neutral Tree Keeper prompt to paste "
                "into any agent. Renders only; runs nothing and spends nothing."
            ),
        )
        verify = subparsers.add_parser(
            "verify",
            help="Independently verify one dispatched Class B patch",
            description=(
                "Judge a candidate patch against the envelope its dispatch receipt "
                "recorded, not against a freshly re-derived one. Everything a path "
                "comparison, a policy lookup, or an exit code can settle is settled "
                "here for free. The machine may reject and may escalate; it may never "
                "accept. Use --prompt to render the independent verifier's prompt for "
                "the judgment that survives, which is refused when machinery already "
                "decided."
            ),
        )
        verify.add_argument("debt_id", help="Dispatched Class B debt id under verification")
        verify.add_argument(
            "--diff", required=True, help="Path to the candidate unified diff"
        )
        verify.add_argument(
            "--proof",
            required=True,
            help="Path to a steward-proof-transcript-v1 JSON document",
        )
        verify.add_argument("--json", action="store_true", help="Output the verdict and receipt as JSON")
        verify.add_argument(
            "--prompt",
            action="store_true",
            help=(
                "Print the harness-neutral independent verifier prompt. Refused when "
                "machinery already reached a verdict."
            ),
        )
        founder = subparsers.add_parser(
            "founder",
            help="Render the report-only Class C founder decision queue",
            description=(
                "Freshly scan known-coverage local state and group only explicit current "
                "unresolved candidates by exact normalized decisionTarget. Never changes "
                "canonical state. For controlled local report input, use ignored "
                ".gaia/steward/discovery-mapping-input.json with schemaVersion "
                "steward-discovery-mapping-input-v1 and valid current/unresolved candidates. "
                "Exits 0 after reporting a known-coverage queue (including zero decisions); "
                "exits 2, writes no founder queue, and reports coverage failure when a "
                "current/unresolved controlled candidate is malformed."
            ),
        )
        founder.add_argument("--json", action="store_true", help="Output the queue and receipt as JSON")

    def execute(self, args: argparse.Namespace) -> int | None:
        if args.steward_command not in {"scan", "run", "dispatch", "verify", "founder"}:
            print("usage: gaia steward {scan,run,dispatch,verify,founder} [--json]", file=sys.stderr)
            return 2

        from gaia_cli.steward.controller import StewardController
        from gaia_cli.steward.policy import PolicyError
        from gaia_cli.steward.receipts import StateError
        from gaia_cli.steward.routing import (
            RoutingError,
            render_dispatch,
            render_dispatch_prompt,
            render_founder_queue,
            render_verification,
            render_verifier_prompt_for,
        )

        prompt: str | None = None
        try:
            root = Path(args.registry)
            if args.steward_command == "scan":
                result = StewardController().scan(root)
            elif args.steward_command == "run":
                result = StewardController().run(root)
            elif args.steward_command == "dispatch":
                if args.prompt:
                    result, prompt = render_dispatch_prompt(root, args.debt_id)
                else:
                    result = render_dispatch(root, args.debt_id)
            elif args.steward_command == "verify":
                if args.prompt:
                    result, prompt = render_verifier_prompt_for(
                        root,
                        args.debt_id,
                        diff_path=Path(args.diff),
                        proof_path=Path(args.proof),
                    )
                else:
                    result, _diff, _outputs = render_verification(
                        root,
                        args.debt_id,
                        diff_path=Path(args.diff),
                        proof_path=Path(args.proof),
                    )
            else:
                result = render_founder_queue(root)
        except (OSError, PolicyError, StateError, RoutingError, RuntimeError, ValueError) as exc:
            print(f"Steward {args.steward_command} failed: {exc}", file=sys.stderr)
            return 2

        if args.json:
            payload = result.to_dict()
            if prompt is not None:
                payload["prompt"] = prompt
            print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
            if args.steward_command == "verify":
                # The verdict must survive the output format. A machine reading
                # JSON gets the same disposition a human reading the table does.
                return {"pending": 0, "reject": 1, "escalate": 3}[result.artifact.verdict]
            return 0

        if prompt is not None:
            # The prompt is the whole output: it is meant to be piped or pasted
            # verbatim, so no status banner may precede it.
            print(prompt, end="")
            return 0

        if args.steward_command == "verify":
            verdict = result.artifact
            print("Gaia Steward verify")
            print(f"Dispatch             {verdict.dispatch_id}")
            print(f"Debt                 {verdict.debt_id}")
            print(f"Finding confirmed    {verdict.finding_confirmed}")
            print(f"Scope valid          {verdict.scope_valid}")
            print(f"Proof valid          {verdict.proof_valid}")
            print(f"Authority valid      {verdict.authority_still_valid}")
            print(f"Guards weakened      {verdict.guards_weakened}")
            print(f"New debt             {len(verdict.new_debt)}")
            print(f"Verdict              {verdict.verdict}")
            for reason in verdict.reasons:
                print(f"  - {reason}")
            if not verdict.decided:
                # Steward has no authority to accept and must never be read as
                # having done so. A clean mechanical pass is the beginning of
                # verification, not the end of it.
                print(
                    "\nNo mechanical objection. Steward cannot accept work — run\n"
                    f"  gaia steward verify {verdict.debt_id} --diff ... --proof ... --prompt\n"
                    "and have an independent verifier judge whether the patch resolves\n"
                    "the finding and whether the proof is genuine."
                )
            try:
                receipt_display = result.receipt_path.relative_to(Path(args.registry).resolve())
            except ValueError:
                receipt_display = result.receipt_path
            print(f"Receipt              {receipt_display}")
            return {"pending": 0, "reject": 1, "escalate": 3}[verdict.verdict]

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

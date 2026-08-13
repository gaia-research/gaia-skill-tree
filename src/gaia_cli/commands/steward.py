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
            dest="steward_command", metavar="{scan,run,dispatch,lane,verify,founder}"
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
        lane = subparsers.add_parser(
            "lane",
            help="Report or advance the bounded Class B rolling maintenance lane",
            description=(
                "The lane is a bounded state machine over open Class B debt. Its "
                "three limits — maxInFlight, maxAttempts, cooldownSeconds — are what "
                "make it a lane rather than a loop, and code caps each one so policy "
                "can never grant unbounded autonomy. `next` hands out the highest-value "
                "dispatch the bounds permit and is the pickup point for an agent or a "
                "scheduled routine; `record` takes an outcome the lane cannot observe "
                "for itself. Debt that exhausts its attempts leaves the agent lane for "
                "the founder queue."
            ),
        )
        lane_actions = lane.add_subparsers(dest="lane_action", metavar="{status,next,record}")
        lane_status = lane_actions.add_parser(
            "status", help="Reconcile the lane against a fresh scan and report it"
        )
        lane_status.add_argument("--json", action="store_true", help="Output the lane as JSON")
        lane_next = lane_actions.add_parser(
            "next", help="Hand out the next bounded dispatch the lane permits"
        )
        lane_next.add_argument("--json", action="store_true", help="Output the packet as JSON")
        lane_next.add_argument(
            "--prompt",
            action="store_true",
            help="Print the harness-neutral Tree Keeper prompt for the selected debt",
        )
        lane_record = lane_actions.add_parser(
            "record",
            help="Record a verification outcome the lane cannot observe for itself",
            description=(
                "Steward's own verification is structurally incapable of producing "
                "accept, so closing an entry as accepted is always someone's explicit "
                "act. --note records who said so."
            ),
        )
        lane_record.add_argument("debt_id", help="Tracked Class B debt id")
        lane_record.add_argument(
            "--verdict", required=True, choices=("accept", "reject", "escalate"),
            help="The independent verifier's decision",
        )
        lane_record.add_argument(
            "--note", default="", help="Who decided, and anything the history should carry"
        )
        lane_record.add_argument("--json", action="store_true", help="Output the lane as JSON")
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
        if args.steward_command not in {"scan", "run", "dispatch", "lane", "verify", "founder"}:
            print(
                "usage: gaia steward {scan,run,dispatch,lane,verify,founder} [--json]",
                file=sys.stderr,
            )
            return 2
        if args.steward_command == "lane" and getattr(args, "lane_action", None) not in {
            "status",
            "next",
            "record",
        }:
            print("usage: gaia steward lane {status,next,record}", file=sys.stderr)
            return 2

        from gaia_cli.steward.controller import StewardController
        from gaia_cli.steward.policy import PolicyError
        from gaia_cli.steward.receipts import StateError
        from gaia_cli.steward.lane import LaneError
        from gaia_cli.steward.routing import (
            LaneEmpty,
            RoutingError,
            record_lane_verdict,
            render_dispatch,
            render_dispatch_prompt,
            render_founder_digest,
            render_founder_queue,
            render_lane,
            render_lane_next,
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
            elif args.steward_command == "lane":
                if args.lane_action == "status":
                    result = render_lane(root)
                elif args.lane_action == "next":
                    result, prompt = render_lane_next(root, prompt=args.prompt)
                else:
                    result = record_lane_verdict(
                        root, args.debt_id, args.verdict, note=args.note
                    )
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
            elif args.json:
                result = render_founder_queue(root)
            else:
                # The digest *is* the human surface. A terse list of decision
                # ids is machine output wearing a person's clothes.
                result, prompt = render_founder_digest(root)
        except LaneEmpty as exc:
            # A lane with nothing to hand out is healthy, not broken. Scheduled
            # pickups run on quiet days far more often than busy ones, and a
            # failure exit here would page a human for a working system.
            print(f"Gaia Steward lane\nNothing to dispatch: {exc}")
            return 0
        except (
            OSError, PolicyError, StateError, RoutingError, LaneError, RuntimeError, ValueError
        ) as exc:
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

        if args.steward_command == "lane" and args.lane_action in {"status", "record"}:
            report = result.artifact
            summary = report.lane.summary()
            counts = summary["counts"]
            print("Gaia Steward lane")
            print(
                "Bounds               "
                f"maxInFlight {summary['policy']['maxInFlight']}  "
                f"maxAttempts {summary['policy']['maxAttempts']}  "
                f"cooldown {summary['policy']['cooldownSeconds']}s"
            )
            print(f"Queued               {counts['queued']}")
            print(f"In flight            {counts['dispatched']}  (capacity {summary['capacity']})")
            print(f"Escalated            {counts['escalated']}")
            print(f"Closed               {counts['closed']}")
            for entry in report.lane.entries:
                if entry.state == "closed":
                    continue
                print(
                    f"  {entry.state:<10} {entry.debt_id}  "
                    f"attempt {entry.attempts}/{summary['policy']['maxAttempts']}  "
                    f"last {entry.last_verdict or '—'}"
                )
            print(f"Next                 {report.next_debt_id or '—'}  ({report.reason})")
            if counts["escalated"]:
                print(
                    "\nEscalated debt has left the agent lane. It is a founder matter now:\n"
                    "  gaia steward founder"
                )
            try:
                receipt_display = result.receipt_path.relative_to(Path(args.registry).resolve())
            except ValueError:
                receipt_display = result.receipt_path
            print(f"Receipt              {receipt_display}")
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

        if args.steward_command == "lane":
            packet = result.artifact
            print("Gaia Steward lane next")
            print(f"Dispatch             {packet.dispatch_id}")
            print(f"Debt                 {packet.debt['id']}")
            print(f"Authority            {packet.authority.value}")
            print(f"Routine              {packet.routine}")
            print(
                "\nRe-run with --prompt for the pasteable Tree Keeper prompt. When the\n"
                "work comes back, do not read the diff first:\n"
                f"  gaia steward verify {packet.debt['id']} --diff ... --proof ..."
            )
            try:
                receipt_display = result.receipt_path.relative_to(Path(args.registry).resolve())
            except ValueError:
                receipt_display = result.receipt_path
            print(f"Receipt              {receipt_display}")
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

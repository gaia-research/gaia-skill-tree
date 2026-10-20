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
            dest="steward_command", metavar="{scan,run,dispatch,lane,verify,founder,full}"
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
        self._configureFull(subparsers)

    @staticmethod
    def _configureFull(subparsers: argparse._SubParsersAction) -> None:
        full = subparsers.add_parser(
            "full",
            help="Run the full, resumable Steward pipeline (deterministic; emits actions)",
            description=(
                "The zero-model runner behind /gaia-steward-full. It observes, triages, lands "
                "Class A repairs on branches, dispatches and verifies bounded Class B work, "
                "re-observes and reports - recording every step in a durable ledger. Whatever "
                "needs a model or a forge becomes an action for a driver; `record` takes the "
                "outcome back. Never merges and never pushes to main."
            ),
        )
        actions = full.add_subparsers(dest="fullAction", metavar="{run,record,status}")

        def ledgerOptions(target: argparse.ArgumentParser) -> None:
            target.add_argument(
                "--ledger", choices=("auto", "git", "local"), default="auto",
                help="Ledger transport: git ref on the remote, a local file, or auto (git when the remote answers)",
            )
            target.add_argument("--json", action="store_true", help="Output the result as JSON")

        run = actions.add_parser(
            "run",
            help="Start (or resume) a pipeline run",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=EXITCODES,
        )
        modes = run.add_mutually_exclusive_group()
        modes.add_argument("--observe", action="store_true", help="Observe only: recover, reconcile, observe, report")
        modes.add_argument("--triage", action="store_true", help="Observe and triage only")
        modes.add_argument("--verify", action="store_true", help="Verify recorded work and re-observe")
        modes.add_argument("--retro", action="store_true", help="Live sensor/routine coverage table only")
        run.add_argument("--routine", metavar="N", help="Restrict triage to routine N (1-17)")
        run.add_argument("--debt", metavar="ID", help="Restrict triage to one debt id")
        run.add_argument("--resume", metavar="RUN", help="Continue an existing run from its recorded phase")
        run.add_argument("--afk", action="store_true", help="Founder decisions queue silently; never prompt")
        run.add_argument("--trigger", choices=("manual", "scheduled"), default="manual", help="What started this run")
        run.add_argument("--no-agents", dest="noAgents", action="store_true", help="Never dispatch Class B work")
        run.add_argument(
            "--integration-branch", dest="integrationBranch", metavar="B",
            help="Branch Class A repairs land on (default: $GAIA_STEWARD_INTEGRATION_BRANCH). Never main.",
        )
        run.add_argument("--push", action="store_true", help="Push Class A landing branches to the remote")
        ledgerOptions(run)

        record = actions.add_parser("record", help="Record a driver's outcome for an emitted action")
        record.add_argument("runId", metavar="RUN_ID", help="Run that emitted the action")
        record.add_argument("stepId", metavar="STEP_ID", help="Step id of the action")
        record.add_argument("--input", required=True, metavar="FILE.json", help="JSON outcome file")
        ledgerOptions(record)

        status = actions.add_parser("status", help="Read-only view of the ledger and the active run")
        ledgerOptions(status)

    def execute(self, args: argparse.Namespace) -> int | None:
        if args.steward_command not in {"scan", "run", "dispatch", "lane", "verify", "founder", "full"}:
            print(
                "usage: gaia steward {scan,run,dispatch,lane,verify,founder,full} [--json]",
                file=sys.stderr,
            )
            return 2
        if args.steward_command == "full":
            return self._executeFull(args)
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

    # ------------------------------------------------------------------
    # gaia steward full
    # ------------------------------------------------------------------

    @staticmethod
    def _fullStore(root: Path, choice: str, remote: str):
        """Pick the ledger transport. `auto` prefers the shared git ref when the remote answers."""

        import subprocess

        from gaia_cli.steward.ledger import FileLedgerStore, GitRefLedgerStore

        local = FileLedgerStore(root / ".gaia" / "steward" / "full" / "ledger.json")
        if choice == "local":
            return local
        shared = GitRefLedgerStore(root, remote)
        if choice == "git":
            return shared
        try:
            probe = subprocess.run(
                ["git", "-C", str(root), "ls-remote", "--exit-code", remote, "HEAD"],
                capture_output=True, timeout=30, check=False,
            )
            reachable = probe.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            reachable = False
        return shared if reachable else local

    @staticmethod
    def _fullModeOf(args: argparse.Namespace) -> str:
        for flag in ("observe", "triage", "verify", "retro"):
            if getattr(args, flag, False):
                return flag
        return "full"

    def _executeFull(self, args: argparse.Namespace) -> int:
        import os

        from gaia_cli.steward.fullrun import FullRunConfig, FullRunError, FullRunner
        from gaia_cli.steward.ledger import LedgerConflict, LedgerUnavailable
        from gaia_cli.steward.policy import PolicyError
        from gaia_cli.steward.receipts import StateError

        action = getattr(args, "fullAction", None)
        if action not in {"run", "record", "status"}:
            print("usage: gaia steward full {run,record,status} [--json]", file=sys.stderr)
            return 2
        root = Path(args.registry).resolve()
        remote = "origin"
        try:
            store = self._fullStore(root, args.ledger, remote)
            config = FullRunConfig(
                repo_root=root,
                store=store,
                integration_branch=(
                    getattr(args, "integrationBranch", None)
                    or os.environ.get("GAIA_STEWARD_INTEGRATION_BRANCH")
                    or None
                ),
                remote=remote,
                push=bool(getattr(args, "push", False)),
                trigger=getattr(args, "trigger", "manual"),
                agents=not getattr(args, "noAgents", False),
                holder=os.environ.get("GAIA_STEWARD_ACTOR", "cli"),
            )
            runner = FullRunner(config)
            if action == "status":
                result = runner.status()
            elif action == "record":
                outcome = self._readOutcome(args.input)
                result = runner.record(args.runId, args.stepId, outcome)
            else:
                result = self._fullRun(runner, args)
        except _FullRefused as exc:
            print(f"Steward full refused: {exc}", file=sys.stderr)
            return 2
        except (FullRunError, PolicyError, StateError, ValueError) as exc:
            print(f"Steward full refused: {exc}", file=sys.stderr)
            return 2
        except (LedgerUnavailable, LedgerConflict, OSError) as exc:
            print(f"Steward full failed: {exc}", file=sys.stderr)
            return 1

        if args.json:
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True, ensure_ascii=False))
        elif action == "status":
            self._printFullStatus(result)
        else:
            self._printFullRun(result)
        return 0 if action == "status" else result.exitCode

    @staticmethod
    def _readOutcome(path: str) -> dict:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _FullRefused(f"cannot read outcome file {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise _FullRefused("outcome file must contain a JSON object")
        return data

    def _fullRun(self, runner, args: argparse.Namespace):
        modeFlags = [f for f in ("observe", "triage", "verify", "retro") if getattr(args, f, False)]
        if args.resume:
            if modeFlags or args.routine is not None or args.debt:
                raise _FullRefused("--resume continues the recorded mode and filters; do not combine it with mode flags")
            return runner.resume(args.resume)
        routine = None
        if args.routine is not None:
            try:
                routine = int(args.routine)
            except ValueError:
                raise _FullRefused(f"--routine must be a number between 1 and 17, not {args.routine!r}") from None
            if not 1 <= routine <= 17:
                raise _FullRefused("--routine must be between 1 and 17")
        return runner.start(
            self._fullModeOf(args), routine=routine, debt=args.debt, afk=args.afk
        )

    @staticmethod
    def _printFullRun(view) -> None:
        print("Gaia Steward full")
        if view.status == "observing-existing":
            print(f"Status               observing-existing")
            print(f"Holder               {view.holder}  (phase {view.holderPhase})")
            print(f"Next                 {view.nextAction}")
            return
        ledger = view.ledger
        shared = "shared" if ledger.get("shared") else "local only (ledger_local_only)"
        print(f"Run                  {view.runId}  (mode {view.mode})")
        print(f"Status               {view.status}  (phase {view.phase})")
        print(f"Ledger               {ledger.get('transport')}  {shared}")
        summary = view.summary
        observe = summary.get("reobserve") or summary.get("observe")
        if observe:
            print(
                f"Observed             {observe.get('observations', 0)} observations, "
                f"{observe.get('openDebt', 0)} open debt, "
                f"coverage unknown {len(observe.get('coverageUnknown', []))}, "
                f"not evaluated {len(observe.get('notEvaluated', []))}"
            )
        triage = summary.get("triage")
        if triage:
            counts = triage["counts"]
            print(
                f"Triage               A {counts['A']}  B {counts['B']}  "
                f"B-report-only {counts['B-report-only']}  C {counts['C']}"
            )
        retro = summary.get("retro")
        if retro:
            StewardCommand._printRetro(retro, table=view.mode == "retro")
        classA = summary.get("class_a")
        if classA:
            landed = classA.get("landings", [])
            print(f"Class A              {classA.get('status')}  {len(landed)} landing outcome(s)"
                  + (f"  - {classA['reason']}" if classA.get("reason") else ""))
        classB = summary.get("class_b")
        if classB:
            detail = classB.get("dispatched") or classB.get("reason") or classB.get("status")
            print(f"Class B              {classB.get('status')}  {detail}")
        resolved = (summary.get("reobserve") or {}).get("resolvedWork")
        if resolved:
            print(f"Resolved             {len(resolved)} work item(s) after re-observation")
        if view.unresolvedWork:
            print(f"Adopted work         {len(view.unresolvedWork)} unfinished item(s) from an earlier run")
        for action in view.actions:
            print(f"Action               {action['type']}  {action['stepId']}  ({action['debtId']})")
        desk = view.desk
        if desk is not None:
            if desk.get("quiet"):
                print("Desk                 nothing needs you")
            else:
                print(f"Desk                 {len(desk['decisions'])} decision(s), {len(desk['operations'])} operation(s)")
                for item in desk["decisions"]:
                    print(f"  decision  {item['decisionId']}")
                for item in desk["operations"]:
                    print(f"  operation [{item['kind']}] {item['subject']}")
        if view.error:
            print(f"Error                {view.error}")
        print(f"Next                 {view.nextAction}")

    @staticmethod
    def _printRetro(retro: dict, *, table: bool) -> None:
        print(
            f"Coverage             {retro['registered']} registered, {retro['executed']} executed, "
            f"{len(retro['unknown'])} unknown, {len(retro['notEvaluated'])} not evaluated"
        )
        if not table:
            return
        print("Sensors")
        for sensor in retro["sensors"]:
            seen = sensor["observations"]
            reason = f"  ({sensor['reason']})" if sensor.get("reason") else ""
            routines = ",".join(str(n) for n in sensor["routine_ids"]) or "-"
            print(f"  {sensor['id']:<28} {sensor['state']:<14} drift {seen['drift']:<4} "
                  f"healthy {seen['healthy']:<4} routines {routines}{reason}")
        print("Routines")
        for routine in retro["routines"]:
            detectors = ", ".join(f"{d['sensor']}:{d['state']}" for d in routine["detectors"]) or "-"
            print(f"  {routine['routine']:>2}  {routine['state']:<12} {detectors}")

    @staticmethod
    def _printFullStatus(view) -> None:
        print("Gaia Steward full status")
        shared = "shared" if view.ledger.get("shared") else "local only (ledger_local_only)"
        print(f"Ledger               {view.ledger.get('transport')}  {shared}")
        if view.holder:
            print(f"Run lease            {view.holder}  (phase {view.holderPhase}, until {view.holderExpiresAt})")
        else:
            print("Run lease            free")
        print(f"Last scheduled run   {view.lastScheduledRunAt or 'never'}")
        counts = ", ".join(f"{state} {n}" for state, n in view.workCounts.items()) or "none"
        print(f"Work                 {counts}")
        if view.lane:
            lane = view.lane["counts"]
            print(f"Lane                 queued {lane['queued']}  dispatched {lane['dispatched']}  "
                  f"escalated {lane['escalated']}  closed {lane['closed']}")
        for run in view.recentRuns[:5]:
            print(f"  {run['runId']}  {run['mode']:<8} {run['status']}")


EXITCODES = """\
exit codes:
  0  completed, or awaiting-action (a driver must perform the emitted actions)
  1  failed: a phase raised, the ledger was unavailable, or the run lost its lease
  2  refused input: bad arguments, an unreadable or invalid outcome file, an unknown run,
     or a conflicting --integration-branch on --resume
  3  blocked: sensor coverage is unknown (any mode); nothing was acted on
  4  observing-existing: another run holds the run lease; nothing was started
"""


class _FullRefused(ValueError):
    """The caller's arguments or input file were refused; exit code 2."""


COMMAND = StewardCommand()

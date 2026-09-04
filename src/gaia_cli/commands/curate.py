"""`gaia curate` command scaffold."""

from __future__ import annotations

import argparse

from gaia_cli.commands.base import Command
from gaia_cli.curation.orchestrator import CurationOrchestrator
from gaia_cli.curation.state import CurationRun


class CurateCommand(Command):
    name = "curate"
    help = "Scaffold a guided Gaia curation run"
    description = "Resolve a skill source and drive it through the gated Gaia curation workflow."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("url", nargs="?", help="GitHub repo or SKILL.md URL to curate")
        parser.add_argument(
            "--generic",
            "-g",
            dest="generic",
            help="Suggested generic skill id for the candidate mapping",
        )
        parser.add_argument(
            "--discover",
            action="store_true",
            help="Run optional evidence discovery before evidence verification",
        )
        parser.add_argument(
            "--resume",
            metavar="RUN_ID",
            help="Resume an existing curation run by run id",
        )
        parser.add_argument(
            "--status",
            action="store_true",
            help="Print the curation run status and exit",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Plan the curation run without mutating the registry or GitHub",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        if args.resume:
            run = CurationRun.load(CurationRun(run_id=args.resume).run_dir)
        else:
            if not args.url:
                print("gaia curate: URL is required unless --resume is provided")
                return 2
            run = CurationRun(
                input_url=args.url,
                suggested_generic_id=args.generic,
                discover=args.discover,
                dry_run=args.dry_run,
            )
            run.save(run.run_dir)

        if args.status:
            CurationOrchestrator.print_status(run)
            return 0

        orchestrator = CurationOrchestrator(run, dry_run=args.dry_run or run.dry_run)
        orchestrator.run_to_next_gate()
        run.save(run.run_dir)
        CurationOrchestrator.print_status(run)
        return 0


COMMAND = CurateCommand()

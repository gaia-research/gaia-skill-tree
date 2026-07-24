import argparse
from gaia_cli.commands.base import Command

class AppraiseCommand(Command):
    name = "appraise"
    help = "Inspect a skill card with status and actions"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "skillId",
            nargs="?",
            default=None,
            help="Skill ID to appraise (default: most recent)",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.main import appraise_command
        appraise_command(args)
        return 0

class FuseCommand(Command):
    name = "fuse"
    help = "Confirm a skill combination or create a custom fusion path"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "skillId", nargs="?", default=None, help="Skill ID to fuse"
        )
        parser.add_argument("--name", help="Optional display name for the skill")
        parser.add_argument(
            "--skills", help="Comma-separated list of skills to combine for a custom fusion"
        )
        parser.add_argument(
            "--delete", action="store_true", help="Delete an existing custom fusion"
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.main import fuse_command
        try:
            fuse_command(args)
        except Exception:
            # Matches the FuseCancelled check in main
            pass
        return 0

COMMANDS = [AppraiseCommand(), FuseCommand()]

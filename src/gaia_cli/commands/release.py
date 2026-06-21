import argparse
from gaia_cli.commands.base import Command

class ReleaseCommand(Command):
    name = "release"
    help = "argparse.SUPPRESS"  # Kept suppressed as deprecated shim

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("release_type", choices=("patch", "minor", "major"))
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Force sync versions if they disagree before bump",
        )
        parser.add_argument(
            "--no-push",
            action="store_true",
            help="Skip git push (commit and tag locally only)",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.impl import release_command
        release_command(args)
        return 0

COMMAND = ReleaseCommand()

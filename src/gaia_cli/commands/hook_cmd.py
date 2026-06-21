import argparse
import sys
from gaia_cli.commands.base import Command

class HookCommand(Command):
    name = "_hook"
    help = "argparse.SUPPRESS"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--event", default="file_edit", help="Hook event type")

    def execute(self, args: argparse.Namespace) -> int | None:
        print(
            "WARNING: 'gaia _hook' is DEPRECATED and will be removed in v7.0.0. Use 'gaia dev hook' instead.",
            file=sys.stderr,
        )
        from gaia_cli.main import hook_command
        hook_command(args)
        return 0

COMMAND = HookCommand()

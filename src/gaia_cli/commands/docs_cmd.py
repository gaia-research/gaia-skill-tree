import argparse
import sys
from gaia_cli.commands.base import Command

class DocsCommand(Command):
    name = "docs"
    help = "argparse.SUPPRESS"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        docs_sub = parser.add_subparsers(dest="docs_command")
        docs_build = docs_sub.add_parser(
            "build", help="Regenerate generated documentation regions"
        )
        docs_build.add_argument(
            "--check", action="store_true", help="Fail if docs are stale without writing"
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        print(
            "WARNING: 'gaia docs build' is DEPRECATED and will be removed in v7.0.0. Use 'gaia dev docs' instead.",
            file=sys.stderr,
        )
        from gaia_cli.main import docs_command
        docs_command(args)
        return 0

COMMAND = DocsCommand()

import argparse
from gaia_cli.commands.base import Command

class TreeCommand(Command):
    name = "tree"
    help = "Show your Gaia skill tree"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--named",
            action="store_true",
            help="Show only skills that have a named implementation",
        )
        parser.add_argument(
            "--title",
            action="store_true",
            help="Show display name instead of slash command / contributor ID",
        )
        parser.add_argument(
            "--canon",
            action="store_true",
            help="Show canonical registry data instead of custom skills only.",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Self-test: print all tier glyphs and rank chips in resolved token colors",
        )
        parser.add_argument(
            "--custom", action="store_true", help="Show only custom skills (default)"
        )
        parser.add_argument(
            "--all",
            "-a",
            action="store_true",
            dest="show_all",
            help="Show all prerequisites including unowned (/??? entries)",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.main import tree_command
        tree_command(args)
        return 0

COMMAND = TreeCommand()

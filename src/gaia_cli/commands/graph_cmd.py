import argparse
from gaia_cli.commands.base import Command

class GraphCommand(Command):
    name = "graph"
    help = "Generate and open the Gaia skill graph"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--format",
            choices=("html", "svg", "json"),
            default="html",
            help="Graph artifact format (default: html)",
        )
        parser.add_argument(
            "-o", "--output", help="Output path (default: registry/render/gaia.html)"
        )
        parser.add_argument(
            "--open",
            dest="open",
            action="store_true",
            default=True,
            help="Open the generated graph (default)",
        )
        parser.add_argument(
            "--no-open",
            dest="open",
            action="store_false",
            help="Do not open the generated graph",
        )
        parser.add_argument(
            "--custom",
            action="store_true",
            help="Only include custom skills in the graph (default)",
        )
        parser.add_argument(
            "--canon",
            action="store_true",
            help="Show canonical registry graph instead of custom skills only",
        )
        parser.add_argument(
            "--all",
            "-a",
            action="store_true",
            dest="show_all",
            help="Include unowned prerequisite nodes in the graph",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.impl import graph_command
        graph_command(args)
        return 0

COMMAND = GraphCommand()

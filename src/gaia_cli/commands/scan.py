import argparse
from gaia_cli.commands.base import Command

class ScanCommand(Command):
    name = "scan"
    help = "Scan configured paths and installed skills for skill evidence"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress scan output; only show notifications",
        )
        parser.add_argument(
            "--json", action="store_true", help="Output scan results as JSON"
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Scan globally installed skills in addition to the local repository",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.main import scan_command
        scan_command(args)
        return 0

COMMAND = ScanCommand()

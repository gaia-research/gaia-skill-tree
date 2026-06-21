import argparse
from gaia_cli.commands.base import Command

class ValidateCommand(Command):
    name = "validate"
    help = "argparse.SUPPRESS"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--intake",
            action="store_true",
            help="Validate intake batches instead of canonical graph",
        )
        parser.add_argument(
            "--meta-sync",
            action="store_true",
            help="Verify meta.json is in sync with gaia.json",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        import sys
        print(
            "WARNING: 'gaia validate' is DEPRECATED and will be removed in v7.0.0. Use 'gaia dev validate' instead.",
            file=sys.stderr,
        )
        from gaia_cli.main import validate_command
        validate_command(args)
        return 0

class TestCommand(Command):
    name = "test"
    help = "argparse.SUPPRESS"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("suite", choices=("meta", "all"), help="Test suite to run")

    def execute(self, args: argparse.Namespace) -> int | None:
        import sys
        print(
            "WARNING: 'gaia test' is DEPRECATED and will be removed in v7.0.0. Use 'gaia dev test' instead.",
            file=sys.stderr,
        )
        from gaia_cli.main import test_command
        test_command(args)
        return 0

COMMANDS = [ValidateCommand(), TestCommand()]

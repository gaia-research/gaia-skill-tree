import argparse
from gaia_cli.commands.base import Command

class InitCommand(Command):
    name = "init"
    help = "Create or update local Gaia config"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--user", help="Gaia username to write into .gaia/config.toml"
        )
        parser.add_argument(
            "--registry-ref", help="Gaia registry URL to write into .gaia/config.toml"
        )
        parser.add_argument(
            "--scan", action="append", help="Path to scan; repeat for multiple paths"
        )
        parser.add_argument(
            "--yes", "-y", "--y", action="store_true", help="Use non-interactive defaults"
        )
        parser.add_argument(
            "--force", action="store_true", help="Overwrite existing .gaia/config.toml"
        )
        parser.add_argument(
            "--auto-prompt-combinations",
            action="store_true",
            help="Enable automatic prompts for detected skill combinations",
        )
        parser.add_argument(
            "--workspace", action="store_true", help="Force workspace mode (local scan/tree only, disables remote push)"
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.main import init_command
        init_command(args)
        return 0

COMMAND = InitCommand()

import argparse
from gaia_cli.commands.base import Command

class ShareCommand(Command):
    name = "share"
    help = "Export a portable share bundle of your skill tree"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--user", help="User whose tree to share (default: configured gaiaUser)"
        )
        parser.add_argument(
            "-o", "--output", help="Path to write the bundle JSON (default: generated-output/share/)"
        )
        parser.add_argument(
            "--stdout",
            action="store_true",
            help="Print the bundle JSON to stdout instead of writing a file",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.impl import share_command
        share_command(args)
        return 0

class InstallCommand(Command):
    name = "install"
    help = "Install a named skill"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "skill_id",
            nargs="?",
            help="Skill ID, catalogRef, or unique bare slug to install",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List and interactively select skills to install",
        )
        parser.add_argument(
            "--ultimate",
            action="store_true",
            help="Batch-install all component skills (alias for --suite)",
        )
        parser.add_argument(
            "--suite",
            action="store_true",
            help="Batch-install all component skills for a suite",
        )
        parser.add_argument(
            "--install-location",
            dest="install_location",
            choices=["local", "global"],
            default="local",
            help="Where to install: local (.agents/.claude, default) or global (~/.gaia/skills)",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.impl import install_command
        install_command(args)
        return 0

class UninstallCommand(Command):
    name = "uninstall"
    help = "Uninstall a named skill"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("skill_id", help="Skill ID to uninstall")

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.impl import uninstall_command
        uninstall_command(args)
        return 0

COMMANDS = [ShareCommand(), InstallCommand(), UninstallCommand()]

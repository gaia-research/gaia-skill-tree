import argparse
from gaia_cli.commands.base import Command

class FetchCommand(Command):
    name = "fetch"
    help = "Download the latest canonical registry files to .gaia/registry"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        pass

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.impl import fetch_command
        fetch_command(args)
        return 0

class PullCommand(Command):
    name = "pull"
    help = "Fetch registry data and run a full scan"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        pass

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.impl import pull_command
        pull_command(args)
        return 0

class UpdateCommand(Command):
    name = "update"
    help = "Update Gaia CLI and registry"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        pass

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.impl import update_command
        update_command(args)
        return 0

COMMANDS = [FetchCommand(), PullCommand(), UpdateCommand()]

import argparse
from gaia_cli.commands.base import Command

class WhoamiCommand(Command):
    name = "whoami"
    help = "Show your Gaia identity and Verifier/operator status"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        pass

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.impl import whoami_command
        whoami_command(args)
        return 0

class LoginCommand(Command):
    name = "login"
    help = "Sign in with GitHub via the device flow"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--repo",
            help="Verify ownership of this owner/repo after signing in",
        )
        parser.add_argument(
            "--no-store",
            action="store_true",
            help="Authenticate for this session only; do not persist the token",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.impl import login_command
        login_command(args)
        return 0

class LogoutCommand(Command):
    name = "logout"
    help = "Sign out of GitHub (clears the local token; revoke in GitHub settings)"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        pass

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.impl import logout_command
        logout_command(args)
        return 0

COMMANDS = [WhoamiCommand(), LoginCommand(), LogoutCommand()]

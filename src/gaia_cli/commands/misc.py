import argparse
import sys
from gaia_cli.commands.base import Command

class LookupCommand(Command):
    name = "lookup"
    help = "Look up a canonical skill and its named implementations"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("skillId", help="Skill ID to inspect")

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.main import lookup_command
        lookup_command(args)
        return 0

class PathCommand(Command):
    name = "path"
    help = "Show prerequisite unlock-path tree toward a target skill"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "skillId", help="Canonical skill ID (or /slash-form) to build the path toward"
        )
        parser.add_argument(
            "--owned-only",
            action="store_true",
            dest="owned_only",
            help="Prune already-owned branches; show only skills still needed",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit machine-readable JSON instead of the tree display",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.main import path_command
        path_command(args)
        return 0

class VersionCommand(Command):
    name = "version"
    help = "Print the Gaia CLI version"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        pass

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.main import version_command
        version_command(args)
        return 0

class ResetCommand(Command):
    name = "reset"
    help = "Clear your skill tree and local state for a fresh start"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--yes", "-y", "--y", action="store_true", help="Skip confirmation prompt"
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.main import reset_command
        reset_command(args)
        return 0

class TrustCommand(Command):
    name = "trust"
    help = "Trust Magnitude diagnostics"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        trust_sub = parser.add_subparsers(dest="trust_command")
        trust_explain_parser = trust_sub.add_parser(
            "explain", help="Show per-row multiplier chain for a skill's Trust Magnitude"
        )
        trust_explain_parser.add_argument(
            "skillId", help="Canonical skill ID to explain"
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.main import trust_explain_command, get_parser
        if getattr(args, "trust_command", None) == "explain":
            trust_explain_command(args)
            return 0
        else:
            parser, _ = get_parser()
            # Find the trust parser choice to print help
            # Since trust is dynamic, it registers under subparsers choice
            subparsers = parser._subparsers._actions[0] if parser._subparsers else None
            if subparsers and "trust" in subparsers.choices:
                subparsers.choices["trust"].print_help()
            else:
                parser.print_help()
            return 0

COMMANDS = [LookupCommand(), PathCommand(), VersionCommand(), ResetCommand(), TrustCommand()]

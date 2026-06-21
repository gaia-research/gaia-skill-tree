import argparse
from gaia_cli.commands.base import Command

class PushCommand(Command):
    name = "push"
    help = "Prepare detected skills for review and file a GitHub issue"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the skill batch without writing it",
        )
        parser.add_argument(
            "--no-issue",
            action="store_true",
            dest="no_issue",
            help="Write intake record without creating a GitHub issue",
        )
        parser.add_argument(
            "--no-pr", action="store_true", dest="no_issue", help=argparse.SUPPRESS
        )
        parser.add_argument(
            "--yes", "-y", "--y", action="store_true", dest="yes", help="Skip confirmation prompts"
        )
        parser.add_argument(
            "--allow-unsafe",
            action="store_true",
            dest="allowUnsafe",
            help="Override the security scanner block on high-severity findings (requires --reason)",
        )
        parser.add_argument(
            "--reason",
            type=str,
            default="",
            dest="overrideReason",
            help="Document an --allow-unsafe override for the audit trail",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.main import push_command
        push_command(args)
        return 0

class ProposeCommand(Command):
    name = "propose"
    help = "Propose a single canonical skill as a named PR"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "skillId", help="Canonical skill ID (accepts /skill-id form)"
        )
        parser.add_argument(
            "--target", help="Named skill target in contributor/skill-name format"
        )
        parser.add_argument(
            "--ultimate",
            action="store_true",
            help="Require that the selected skill is ultimate",
        )
        parser.add_argument(
            "--yes", "-y", "--y", action="store_true", help="Use defaults without interactive prompts"
        )
        parser.add_argument(
            "--no-pr",
            action="store_true",
            help="Write intake proposal without opening a PR",
        )

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.main import propose_command
        propose_command(args)
        return 0

COMMANDS = [PushCommand(), ProposeCommand()]

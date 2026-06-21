import argparse
from gaia_cli.commands.base import Command
from gaia_cli.impl import SKILLS_USAGE

class SkillsCommand(Command):
    name = "skills"
    help = "Browse and manage named skills"
    epilog = SKILLS_USAGE
    formatter_class = argparse.RawDescriptionHelpFormatter

    def configure(self, parser: argparse.ArgumentParser) -> None:
        skills_sub = parser.add_subparsers(dest="skills_command")
        
        skills_list = skills_sub.add_parser("list", help="List available named skills")
        skills_list.add_argument(
            "--exclude-pending", action="store_true", help="Hide pending skill proposals"
        )
        
        skills_search = skills_sub.add_parser("search", help="Search named skills")
        skills_search.add_argument("query", help="Search query")
        skills_search.add_argument(
            "--exclude-pending", action="store_true", help="Hide pending skill proposals"
        )
        
        skills_info = skills_sub.add_parser("info", help="Show details for a named skill")
        skills_info.add_argument("skill_id", help="Skill ID to inspect")
        skills_info.add_argument(
            "--exclude-pending", action="store_true", help="Hide pending skill proposals"
        )
        
        skills_install = skills_sub.add_parser("install", help="Install a named skill")
        skills_install.add_argument(
            "skill_id",
            metavar="skill",
            help="Skill ID, catalogRef, or unique bare slug to install",
        )
        skills_install.add_argument(
            "--suite", action="store_true", help="Install as a suite (recursive)"
        )
        skills_install.add_argument(
            "--install-location",
            dest="install_location",
            choices=["local", "global"],
            default="local",
            help="Where to install: local (.agents/.claude, default) or global (~/.gaia/skills)",
        )
        
        skills_sub.add_parser(
            "update", help="Update all installed skills from source"
        )
        
        skills_uninstall = skills_sub.add_parser(
            "uninstall", help="Uninstall a named skill"
        )
        skills_uninstall.add_argument("skill_id", help="Skill ID to uninstall")

    def execute(self, args: argparse.Namespace) -> int | None:
        from gaia_cli.impl import skills_command
        if not getattr(args, "skills_command", None):
            try:
                from gaia_cli.tui import GaiaApp
                GaiaApp().run()
            except ImportError:
                # Printed by get_parser caller if fallback needed
                raise
            return 0
        skills_command(args)
        return 0

COMMAND = SkillsCommand()

import sys
import os
import argparse
import signal
from gaia_cli.commands import discover_commands
from gaia_cli.commands.base import Command
from gaia_cli.impl import (
    ColoredHelpFormatter,
    COMMAND_USAGE,
    PUBLIC_COMMANDS,
    resolve_registry_path,
    require_explicit_writable_registry,
)

def get_parser():
    parser = argparse.ArgumentParser(
        prog="gaia",
        description="Gaia Registry CLI",
        epilog=COMMAND_USAGE,
        formatter_class=ColoredHelpFormatter,
    )
    parser.add_argument(
        "--registry",
        default=None,
        help="Path to a local Gaia registry checkout. Defaults to auto-resolved local or global registry.",
    )
    parser.add_argument(
        "--global",
        "-g",
        dest="global_flag",
        action="store_true",
        help="Use global GAIA_HOME registry, ignoring any local .gaia/ config.",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="store_true",
        help="Print the Gaia CLI version and exit.",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Launch the TUI (Terminal User Interface).",
    )
    parser.add_argument(
        "--canon",
        action="store_true",
        help="Show canonical registry data instead of local-first view.",
    )

    subparsers = parser.add_subparsers(
        dest="command", metavar="{" + ",".join(PUBLIC_COMMANDS) + "}", help=argparse.SUPPRESS
    )
    subparsers.add_parser("help", help="Show command help")

    # Dynamically configure subparsers for all discovered commands
    commands = discover_commands()
    for name in sorted(commands.keys()):
        cmd = commands[name]
        
        # Determine help string; if help is suppressed, pass argparse.SUPPRESS
        h = cmd.help
        if h == "argparse.SUPPRESS" or h is argparse.SUPPRESS:
            h = argparse.SUPPRESS

        sub_parser = subparsers.add_parser(
            cmd.name,
            help=h,
            description=cmd.description or None,
            epilog=cmd.epilog or None,
            formatter_class=cmd.formatter_class or ColoredHelpFormatter,
        )
        cmd.configure(sub_parser)

    return parser, subparsers

def main():
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser, subparsers = get_parser()
    args = parser.parse_args()

    if args.tui:
        os.execvp(sys.argv[0], [sys.argv[0], "skills"])

    if len(sys.argv) == 1 and sys.stdin.isatty() and sys.stdout.isatty():
        from gaia_cli.selector import run_selector
        run_selector(parser)
        return

    args.registry = resolve_registry_path(args.registry, global_flag=args.global_flag)
    require_explicit_writable_registry(parser, args)

    if args.version:
        from gaia_cli.impl import version_command
        version_command(args)
        return

    if args.command == "help":
        parser.print_help()
        return

    commands = discover_commands()
    if args.command in commands:
        cmd = commands[args.command]
        sys.exit(cmd.execute(args) or 0)
    else:
        parser.print_help()

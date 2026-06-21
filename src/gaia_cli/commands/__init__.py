"""Subcommands for the Gaia CLI."""

import importlib
import pkgutil
import sys
from typing import Dict
from gaia_cli.commands.base import Command

def discover_commands() -> Dict[str, Command]:
    """Dynamically discover and load all command modules under this package."""
    commands = {}
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        if module_name == "base":
            continue
        try:
            module = importlib.import_module(f"gaia_cli.commands.{module_name}")
            if hasattr(module, "COMMAND"):
                cmd = getattr(module, "COMMAND")
                if isinstance(cmd, Command):
                    commands[cmd.name] = cmd
        except Exception as e:
            print(f"Error loading command {module_name}: {e}", file=sys.stderr)
    return commands

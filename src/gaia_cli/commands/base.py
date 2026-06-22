import argparse
from typing import Protocol, runtime_checkable

@runtime_checkable
class Command(Protocol):
    name: str
    help: str
    description: str = ""
    epilog: str = ""
    formatter_class: type[argparse.HelpFormatter] | None = None

    def configure(self, parser: argparse.ArgumentParser) -> None:
        """Add sub-arguments to the parser."""
        ...

    def execute(self, args: argparse.Namespace) -> int | None:
        """Execute the command."""
        ...

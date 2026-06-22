import argparse
from gaia_cli.commands.base import Command

class McpCommand(Command):
    name = "mcp"
    help = "argparse.SUPPRESS"
    description = (
        "Start the Gaia MCP (Model Context Protocol) server, which exposes the skill registry "
        "to AI tools and IDE integrations via stdio. "
        "Requires building the server first: run `npm run build` inside packages/mcp/."
    )

    def configure(self, parser: argparse.ArgumentParser) -> None:
        pass

    def execute(self, args: argparse.Namespace) -> int | None:
        import sys
        print(
            "WARNING: 'gaia mcp' is DEPRECATED and will be removed in v7.0.0. Use 'gaia dev mcp' instead.",
            file=sys.stderr,
        )
        from gaia_cli.main import mcp_command
        mcp_command(args)
        return 0

COMMAND = McpCommand()

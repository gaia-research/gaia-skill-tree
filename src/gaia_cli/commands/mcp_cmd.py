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


def execute_dev_mcp(args) -> int | None:
    import os
    import subprocess
    import sys
    from pathlib import Path

    action = getattr(args, "mcp_command", None)
    if action in ("start", "stop", "status"):
        script = Path(args.registry) / "packages" / "mcp" / "dist" / "src" / "daemon.js"
        if not script.exists():
            print(f"MCP server build not found: {script}", file=sys.stderr)
            print("Run `npm run build` in packages/mcp first.", file=sys.stderr)
            sys.exit(1)

        env = os.environ.copy()
        env["GAIA_REGISTRY_PATH"] = str(args.registry)
        
        from gaia_cli.scanner import load_config
        config = load_config()
        if config and config.get("gaiaUser"):
            env["GAIA_USER"] = config["gaiaUser"]

        res = subprocess.call(["node", str(script), action], env=env)
        return res
    else:
        from gaia_cli.impl import mcp_command
        mcp_command(args)
        return 0


COMMAND = McpCommand()


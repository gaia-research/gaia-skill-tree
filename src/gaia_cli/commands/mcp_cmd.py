"""Helper for the canonical `gaia dev mcp` command.

The deprecated top-level `gaia mcp` shim was retired in v7.0.0. Only the
`execute_dev_mcp` helper remains here, invoked by `gaia dev mcp` via
`gaia_cli.commands.dev`.
"""


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

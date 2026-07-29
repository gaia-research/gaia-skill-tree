"""Helper for the canonical `gaia dev mcp` command.

The deprecated top-level `gaia mcp` shim was retired in v7.0.0.

The in-repo `packages/mcp` prototype (and the `start`/`stop`/`status` daemon
verbs that shelled out to its `dist/src/daemon.js` build) was deleted: it was a
prototype that never shipped. The real server lives in `gaia-research/gaia-mcp`
and is published to npm as `@gaia-research/mcp`. `gaia dev mcp` is now purely
informational — it prints how to install and run that package.
"""


def execute_dev_mcp(args) -> int | None:
    from gaia_cli.impl import mcp_command

    mcp_command(args)
    return 0

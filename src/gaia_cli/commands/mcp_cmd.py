"""Helper for the canonical `gaia dev mcp` command.

The deprecated top-level `gaia mcp` shim was retired in v7.0.0.

The in-repo `packages/mcp` prototype (and the `start`/`stop`/`status` daemon
verbs that shelled out to its `dist/src/daemon.js` build) was deleted: it was a
prototype that never shipped. Its standalone successor, `@gaia-research/mcp`,
was in turn decommissioned and deprecated on npm on 2026-08-19; summon now
ships bundled inside the Skill Heaven plugin. `gaia dev mcp` is purely
informational — it prints how to install that plugin.
"""


def execute_dev_mcp(args) -> int | None:
    from gaia_cli.impl import mcp_command

    mcp_command(args)
    return 0

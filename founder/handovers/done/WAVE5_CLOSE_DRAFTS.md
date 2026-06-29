# Wave 5 — Close-out comment drafts (for orchestrator approval before posting)

**Drafted:** 2026-06-22, by claude-bot (agent wave 5 of Epic #780 close-out).
**Action required:** Orchestrator must review, then post via `gh issue comment` and close via `gh issue close`.

---

## Issue #783 — Polyglot Monorepo Versioning

### Draft comment to post on issue #783

---

Closing #783 — Polyglot Monorepo Versioning (Changesets approach).

**What shipped vs what was planned:**

The original issue proposed adopting Changesets (`@changesets/cli`) to manage version bumps across the four version-bearing manifests (`pyproject.toml`, `packages/cli-npm/package.json`, `packages/mcp/package.json`, `registry/gaia.json`).

After discussion during Epic #780, the Changesets approach was **rejected in favor of a simpler lockstep validation script** (`scripts/verify_lockstep.py`). The midpoint handover (`EPIC780_MIDPOINT_HANDOVER.md`, filed during the epic) noted this decision:

> "Close the Changesets portion of #783 by posting a comment on issue #783 explaining that the Changesets approach was rejected in favor of `verify_lockstep.py` lockstep validation. The pre-commit hook now enforces that all four manifests agree before a release bump."

The `verify_lockstep.py` approach is implemented and enforced by the pre-commit hook. The `gaia dev release <type>` command (`gaia dev release --sync` for force-alignment) is the single entry point for version bumps.

**If Changesets adoption is still wanted** for a non-`pyproject.toml`-driven cadence (e.g., to support per-package semantic release), please file a new issue scoped to that use case. The decision to reject Changesets for the lockstep case does not preclude future adoption for a different scope.

Closing as scope-delivered (lockstep validation landed) / approach superseded (Changesets not pursued).

---

## Issue #785 — Abstract MCP Management

### Draft comment to post on issue #785

---

Closing #785 — Abstract MCP Management.

**What shipped:**

Marco's explicit framing for this issue was: *"Minimal abstraction — invest minimal effort here."*

What shipped in Epic #780 (PR #787) matches that scope:
- A 50-line `merger.ts` that wires the Gaia MCP server into the `@modelcontextprotocol/sdk` transport.
- A PID-file `daemon.ts` that manages the MCP server process lifecycle (start/stop/status).
- `gaia dev mcp start|stop|status` as the CLI interface (top-level `gaia mcp` is a deprecated shim delegating to `gaia dev mcp`).
- The raw `@modelcontextprotocol/sdk` is still in place — no full MCPorter abstraction layer was introduced.

**Why no full MCPorter adoption:**

Full MCPorter adoption (a plug-in registry layer, hot-reload, transport abstraction) was explicitly out of scope. The minimal implementation satisfies the issue's stated goal of "make MCP manageable via CLI without over-engineering the abstraction."

**If full MCPorter adoption is wanted later**, file a new issue describing the concrete use case (e.g., multiple MCP servers, hot-reload requirement, transport-agnostic testing). That work should be scoped independently once there's a concrete need.

Closing as scope-delivered per original framing.

---

## Orchestrator action checklist

After reviewing these drafts:

1. Post #783 comment: `gh issue comment 783 --body "$(cat <draft>)"`
2. Close #783: `gh issue close 783`
3. Post #785 comment: `gh issue comment 785 --body "$(cat <draft>)"`
4. Close #785: `gh issue close 785`

Both issues should then be reflected in the Wave 6 epic summary.

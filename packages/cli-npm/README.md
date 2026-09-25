# Gaia CLI

The Gaia CLI integrates local development repositories and CI pipelines with the Gaia Skill Tree registry.

> **Prefer the Agent Plugin / MCP?** If you use Claude Code, the recommended path
> is the unified **Skill Heaven** plugin, which bundles its own summon MCP server:
>
> ```bash
> claude plugin install skill-heaven@gaia-skill-heaven
> ```
>
> The core mechanic is `/summon` — materializing capabilities into session context
> on demand with zero ambient skill debt. Standalone `@gaia-research/mcp` has been
> decommissioned and deprecated on npm as of 2026-08-19. For anything that writes,
> use this CLI. Source: <https://github.com/gaia-research/gaia-skill-heaven>.

## Installation

**Install the CLI from PyPI:**

```bash
pip install gaia-cli
```

That is the published, supported install path — `gaia-cli` is on PyPI and is the
package every `gaia` command in this document comes from.

This npm wrapper (`@gaia-registry/cli`) is **not published to npm**. There is no
`npm install` line for it, because there is nothing on the registry to install.
It is built and exercised from a source checkout only (see *Local Development*
below). If you want Gaia on a Node-only machine, `pip install gaia-cli` is still
the answer — the wrapper delegates to the same Python implementation anyway.

## Requirements

- **Node.js 18+** for running the npm wrapper.
- **Python 3.8+** because the wrapper delegates to the Python implementation.

The npm wrapper automatically detects your Python installation and provides instructions if Python is not found.

## CLI Usage

Run Gaia from any project after installing:

```bash
gaia init --user your-username
gaia scan
gaia appraise
gaia skills search web
```

From a local registry checkout, you can pass the registry path explicitly:

```bash
gaia --registry /path/to/gaia-skill-tree scan
gaia --registry /path/to/gaia-skill-tree push --dry-run
gaia --registry /path/to/gaia-skill-tree push
```

## Commands

- `gaia init`: Initializes `.gaia/config.toml` in the current repo.
- `gaia scan`: Scans repo paths, writes `generated-output/promotion-candidates.json`, and renders `generated-output/tree.{html,md}`.
- `gaia pull`: Refreshes registry data from `origin`.
- `gaia push`: Submits a batch intake record under `registry-for-review/skill-batches/`.
- `gaia appraise`: Displays your tree card and any scan-flagged promotions.
- `gaia promote <skill>`: Promotes only when the last scan recommended that skill, using the scan-suggested level.
- `gaia tree`: Renders your local skill tree.
- `gaia graph`: Rebuilds registry graph artifacts.
- `gaia skills list/search/info/install/uninstall`: Browses and manages named skills.
- `gaia version`, `gaia --version`, `gaia -v`: Prints the CLI version.

Preview a batch before writing it:

```bash
gaia push --dry-run
```

## GitHub Action

The GitHub Action remains packaged here for CI integrations that want to run Gaia from npm.

### Configuration

Add `.github/workflows/gaia.yml` to your repo:

```yaml
name: Gaia Skill Sync

on: [push]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: gaia-registry/gaia/packages/cli-npm/github-action@main
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          username: 'your-github-username'
```

### Gaia Configuration (`.gaia/config.toml`)

The CLI is configured via `.gaia/config.toml` in your repository root:

```toml
username = "mbtiongson1"
gaiaRegistryRef = "https://github.com/gaia-research/gaia-skill-tree"
scanPaths = ["src/", "docs/", "tools/"]
autoPromptCombinations = false
```

## Local Development

```bash
cd packages/cli-npm
npm install
npm test
```

The package copies `../../src/gaia_cli` during `prepack` so the npm binary can delegate to the same Python implementation used by PyPI. Production behavior belongs in `src/gaia_cli/`; the npm code should stay a thin wrapper.

# Epic #780 — Deprecation Shim Cleanup

**Created:** 2026-06-22
**Target removal:** v7.0.0 (2 major releases after v5.x)

## Why these shims exist

Epic #780 migrated all dev-only CLI commands from top-level (`gaia release`, `gaia validate`, etc.) to the `gaia dev` namespace. The old top-level commands were kept as thin deprecation shims so that:

1. CI workflows and scripts referencing the old commands don't break immediately
2. Contributors' muscle memory has time to adjust
3. Documentation references can be updated incrementally

## Shims to remove in v7.0.0

| Old Command | New Command | Shim Location |
|---|---|---|
| `gaia release <type>` | `gaia dev release <type>` | `src/gaia_cli/main.py` (or `commands/release.py`) |
| `gaia validate` | `gaia dev validate` | `src/gaia_cli/main.py` (or `commands/validate_cmd.py`) |
| `gaia test <suite>` | `gaia dev test <suite>` | `src/gaia_cli/main.py` (or `commands/validate_cmd.py`) |
| `gaia docs build` | `gaia dev docs` | `src/gaia_cli/main.py` |
| `gaia trust explain` | `gaia dev trust-explain` | `src/gaia_cli/main.py` |
| `gaia mcp` | `gaia dev mcp` | `src/gaia_cli/main.py` (or `commands/mcp_cmd.py`) |

## What each shim does

```python
def release_command(args):
    print("⚠️  `gaia release` is deprecated. Use `gaia dev release` instead.",
          file=sys.stderr)
    dev_release_command(args)
```

## Cleanup steps for v7

1. Delete each shim function listed above
2. Remove each from `get_parser()`'s `subparsers.add_parser(...)` calls
3. Remove each from `PUBLIC_COMMANDS` tuple (if still present)
4. Remove from the `main()` dispatch `elif` chain (if still using the old dispatch)
5. Update `COMMAND_USAGE` help text — remove the old command lines
6. Search for any remaining references:
   ```bash
   grep -rn "gaia release\|gaia validate\|gaia test\|gaia docs build\|gaia trust explain\|gaia mcp" \
     .github/workflows/ CLAUDE.md CONTEXT.md META.md MISSION.md DEV.md CONTRIBUTING.md README.md
   ```
7. Run full test suite to verify no breakage
8. Update CHANGELOG: "BREAKING: Removed deprecated top-level dev commands. Use `gaia dev` namespace."

## Why not remove earlier

The shims are low-cost (6 thin functions, ~30 lines total). Removing before v7 would break:
- Any external CI/CD that references `gaia validate` directly
- Agent skills that shell out to `gaia validate` or `gaia release`
- Contributors following older documentation

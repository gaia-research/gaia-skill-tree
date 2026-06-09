# Gaia CLI GEMINI.md

Specific guidance for the Gaia CLI (`gaia`).

## Core Usage Flow
1. `gaia init` - Initialize local state and registry config.
2. `gaia scan` - Analyze codebase tokens, map to registry, and update local state.
3. `gaia push` - Select mapped skills/fusions to propose to the central registry.
4. `gaia fuse` (optional) - Define custom skill fusions locally if mappings are needed.
5. `gaia tree` - Visualize the current skill tree and unlocks structure.

## Tree Visualization Legend
The `gaia tree` command uses specific colors to denote skill origins and ranks:

### Origin Colors
- **Slate Blue/Grey** `(148, 163, 184)`: Starless Generic Skills (unranked nodes in the taxonomy).
- **Bold Red** `(239, 68, 68)`: Named Contributor Skills (e.g., `contributor/skill-name`).
- **Bright Green** `(134, 239, 172)`: Local/Custom User Skills (manually added or locally scanned).
- **Purple** `(192, 132, 252)`: Fused Skills (extra skills resulting from custom fusions).

### Rank Colors
Ranks `1★` through `6★` use colors defined in the registry palette (see `RANK_COLORS` in `gaia.json`).
- `5★` is a **Transcendent Level** and is rendered with a Gold-to-Red gradient.
- `6★` is a **Transcendent ★ Level** and is rendered with a full Rainbow effect (Blue -> Purple -> Gold -> Red -> Purple -> Green).

## Tooling Strategy
1. **Close the Gap**: Always prioritize programmatic CLI use over manual registry edits. If a required registry mutation is missing from the CLI, **update the CLI to fit the gap** first.
2. **Atomic Registry Commit**: Features adding CLI registry mutations should include the corresponding registry data changes in the same atomic commit.
3. **No Hand-Editing**: Manual YAML frontmatter or timeline edits are forbidden. All registry state changes must be verifiable and logged via CLI command execution.

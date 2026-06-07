# GEMINI.md

Agent guidance for the gaia-skill-tree repository. See CLAUDE.md for full details.

## Curation & CI Troubleshooting

For details on local setup, common commands, resolving stale documentation checks, pre-existing test failures, and version lockstep requirements, see [DEV.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/DEV.md).


## Meta Strategy (Source of Truth)

The registry's taxonomy, evidence methodology, and ranking strategy are defined in [META.md](./META.md). This is the single source of truth for all "Meta" rules.

### Meta Audit Implementation Rules

1. **Generic Skills**: Generic skills are completely starless/rankless. Only named skills have ranks. When auditing, do not run "level overshoot" checks against generic nodes.
2. **Origin Claims**: Origin mapping is not strictly chronological ("earliest"). It represents the highest-rated or most attributed skill in a generic bucket. There can only be one origin per bucket. Setting `origin: true` on one named skill requires stripping it from any others in the same bucket (now automated via `gaia dev update-named --origin`).
3. **Raw Repo Links**: Ecosystem suites (like `obra/superpowers`, `ruvnet/ruflo`, or `mattpocock`) are exempt from strict `SKILL.md` file link checks and should intentionally point to their raw repo URL.

### Tooling Strategy

1. **Close the Gap**: Always prioritize programmatic CLI use over manual registry edits. If a required registry mutation is missing from the CLI (e.g., changing origins, unsetting starless demerits, or standalone timeline events), **update the CLI to fit the gap** first. 
2. **Atomic Registry Commit**: Features adding CLI registry mutations should include the corresponding registry data changes in the same atomic commit.
3. **No Hand-Editing**: Manual YAML frontmatter or timeline edits are forbidden. All registry state changes must be verifiable and logged via CLI command execution.



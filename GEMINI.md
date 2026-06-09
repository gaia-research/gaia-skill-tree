# GEMINI.md

Agent guidance for the gaia-skill-tree repository. See CLAUDE.md for full details.

## Domain Instructions
- [Gaia CLI](./src/gaia_cli/GEMINI.md): Core usage flow, tree legend, and CLI tooling strategy.

## Curation Guidelines

Refer to [DEV.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/DEV.md) for local environment setup, testing, and CI troubleshooting. Keep these curation-specific rules in mind:

### 1. `links.github` URL must use `blob/` not `tree/`
GitHub directory URLs use `tree/` but the installer only recognizes `blob/branch/subpath`. Convert manually to ensure skills are discoverable.

### 2. Only `links.github` is read by the installer
Wrong keys like `links.repo`, `links.docs`, or `origin` won't work. Always use `links.github` and strip any `#fragment` from docs URLs.

### 3. Suites never need `links.github` — do not flag them as uninstallable
Suite skills (with `suiteComponents`) install via components and have no directory of their own. Mark non-suite individual skills at 2★ or below with no public repo as `installable: false`.

### 4. Suite component links need subpaths
Each component in a suite must have a `blob/branch/subpath` URL, not a bare repo root, or symlinks will point incorrectly.



## Meta Strategy (Source of Truth)

The registry's taxonomy, evidence methodology, and ranking strategy are defined in [META.md](./META.md). This is the single source of truth for all "Meta" rules.

### Meta Audit Implementation Rules

1. **Generic Skills**: Generic skills are completely starless/rankless. Only named skills have ranks. When auditing, do not run "level overshoot" checks against generic nodes.
2. **Origin Claims**: Origin mapping is not strictly chronological ("earliest"). It represents the highest-rated or most attributed skill in a generic bucket. There can only be one origin per bucket. Setting `origin: true` on one named skill requires stripping it from any others in the same bucket (now automated via `gaia dev update-named --origin`).
3. **Raw Repo Links**: Ecosystem suites (like `obra/superpowers`, `ruvnet/ruflo`, or `mattpocock`) are exempt from strict `SKILL.md` file link checks and should intentionally point to their raw repo URL.

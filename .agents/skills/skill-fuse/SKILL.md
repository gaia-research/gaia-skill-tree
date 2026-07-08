---
name: skill-fuse
description: >-
  Composes multiple named skill implementations for a single contributor
  into a unified ultimate or suite skill node in the Gaia registry.
  Collects component IDs, verifies node existence, researches evidence,
  writes the ultimate node, back-links derivatives on all components,
  updates registry indexes, validates, and opens a pull request.
  Use when a contributor has accumulated 3+ named skills and you want
  to consolidate them into a single suite.
version: 1.0.0
genericSkillRef: skill-fusion
contributor: gaia-research
---

# skill-fuse

Fuse all of a contributor's named skills into a single **ultimate/suite** skill node in the Gaia registry.

## When to use

- A contributor has 3+ named skills and you want a unified suite entry
- You want to create a capstone skill that represents a full skill set
- Triggered by `/gaia-fuse-full-suite <contributor>`

## How it works

1. **Collect** component IDs from `registry/named/<contributor>/`
2. **Verify** each component ID exists as a registry node
3. **Research** evidence to determine the appropriate star level
4. **Write** the ultimate node JSON via `gaia dev add --type ultimate`
5. **Back-link** derivatives on all component skills via `gaia dev link`
6. **Update** `registry/named-skills.json` via `gaia dev docs`
7. **Validate** via `gaia validate`
8. **Open** a PR on a `review/meta/` branch

## Usage

```bash
# Invoke via the gaia-fuse-full-suite skill
/gaia-fuse-full-suite <contributor>
```

## Output

A new ultimate skill node in `registry/nodes/ultimate/` with:
- `suiteComponents` listing all named skill IDs
- `fusion-recipe` evidence row (auto-derived)
- Back-links on all component skills via `derivatives[]`
- A draft PR on `review/meta/fuse-<contributor>`

## Notes

- Components must already be curated named skills (2★+) to count toward fusion-recipe origins
- The `fusion-recipe` evidence type is auto-derived — do not add it manually
- Suite ultimates require ≥ 3 named prerequisites for the fusion to be valid
- Related skill: `/gaia-curate-chain` for adding new generic + named skills before fusing

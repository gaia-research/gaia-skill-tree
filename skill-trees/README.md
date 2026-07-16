# Gaia User Skill Trees

> **⚠ Yggdrasil II migration notice (2026-07-14)**
>
> This directory (present in the repository since May 2026 but never officially
> ratified as a feature under Yggdrasil II or any prior Meta Schema RFC) will be
> **migrated in its entirety to a separate "your-skill-tree" repository**.
>
> It is **intentionally excluded from the Yggdrasil II migration** (`#997`).
> Validation scripts (`validate_timelines.py`, Guard E, branch-scope CI) will be
> pointed away from `skill-trees/` in a later infrastructure pass, once the
> target repository is bootstrapped and the transfer protocol is agreed.
>
> Do **not** add new user trees here pending that migration.  Existing data will
> be preserved as-is and re-pointed at the new home when the infra pass lands.

---

This directory contains personal skill tree records, one per Gaia username.

## Structure

```text
skill-trees/
├── mbtiongson1/
│   ├── skill-tree.json    ← Validated against registry/schema/skillTree.schema.json
│   └── skill-tree.md      ← Generated human-readable projection
└── <your-username>/
    ├── skill-tree.json
    └── skill-tree.md
```

`skill-tree.json` is the durable user-owned record. `skill-tree.md` is a generated
projection for humans. New local renders from `gaia scan` and `gaia tree` are
written to `generated-output/tree.md` and `generated-output/tree.html`.

## Identity Model

- Each directory is named after the configured Gaia username.
- A user's tree records unlocked skills, evidence, pending combinations, and
  summary stats.
- Ownership is enforced through repository review rules and CODEOWNERS.
- You should not write to another user's skill tree without explicit review.

## How Skill Trees Grow

1. Run `gaia init --user <you>` in a project.
2. Run `gaia scan` to detect skills and render your local tree.
3. Review `generated-output/promotion-candidates.json` for recommended level-ups.
4. Run `gaia promote <skill>` or `gaia promote --all` to apply only scan-approved
   promotions. Gaia uses the level suggested by the scan.
5. Run `gaia push` when you want to submit new skill intake for review.

The skill tree is the heart of Gaia: it is the map of what an agent can actually
do, how those skills combine, and what evidence supports each level.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full details.

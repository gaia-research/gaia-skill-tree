---
name: gaia-audit
description: Review one Gaia skill, named skill, or real-skill catalog item for outdated, superseded, overpromoted, weakly sourced, or incorrectly mapped evidence. Use when the user asks to audit a specific skill or says a listed skill may not deserve its current rank.
version: 1.0.0
---

# gaia-audit

Audit exactly one Gaia skill, named skill, or real-skill catalog item and submit the smallest source-level correction.

## Workflow

1. Identify the target:
   - Canonical skill: `registry/gaia.json`
   - Named skill: `registry/named/<contributor>/<skill>.md`
   - Real-skill catalog item: `registry/real-skills.json`
2. Search the repo for every occurrence of the target with `rg`.
3. Re-check current source evidence. Prefer direct `SKILL.md`, paper, benchmark, release note, or reproducible repo URLs over directory listings or homepages.
4. Separate these questions:
   - Does the skill exist?
   - Is it a generic (starless) or a named skill? Generic skills have no level; only named implementations have stars (2★–6★).
   - Does it map to the claimed Gaia capability?
   - Does it justify its stars (for named), tier, named status, or `promotedNamedSkillId`?
   - Is it outdated, superseded, overpromoted, duplicate, or under-sourced?
   - **Upgrade Path & Fusion Analysis**: Can this skill be evolved? Consolidate multiple overlapping basic concepts under a single elegant Basic generic skill (e.g. literature-search) to avoid vendor-bloat. If a set of related basic skills can be combined into a multi-step high-level orchestration, plan to fuse them into a new **Extra** master skill (like `computational-biology-workflows`).
   - **Rigorous Verification**: Does the source include a specific **agent playbook** (e.g., `AGENTS.md`, `CLAUDE.md`, `.claude/skills/`, or a documented autonomous agent workflow)?
   - **Demerit Check (Strategic)**: Only actively audit demerits for *named* skills at **3★+** (generics have no demerits). Be lenient toward skills that are portable across platforms. Reward portable, "Generalized" skills by favoring them for promotion to higher stars or Ultimate tier when they remain demerit-free at high levels.
   - Do **not** audit the `rarity` field — the rarity axis is deprecated (see `CONTEXT.md` § Rarity); the schema still requires it but it carries no review signal.
5. Present findings first. If a correction is warranted, edit only source-of-truth files:
   - `registry/gaia.json` or `registry/nodes/**/*.json`
   - `registry/named/**`
   - `registry/real-skills.json`
   - reviewer policy docs when criteria are missing
6. Regenerate outputs and promote:
   - If a skill is promoted to Named status, ensure its `registry/named/` file exists and the real-skill catalog entry is updated.
   - Run:
     ```bash
     gaia dev build
     ```
7. Verify:
   ```bash
   gaia validate
   gaia validate --intake
   gaia test all
   git diff --check
   ```

## Demotion Rules (Audit Enforcement)

- **Star Bar Enforcement**: Any skill at **3★+** MUST have a verified GitHub implementation link (usually in `links.github`). If missing or dead, demote to **Named (2★)**.
- **Unique Skill Reclassification**: Unique skills demoted below **4★** must be reclassified to **Basic** (or **Extra**) to pass validation. Use `gaia dev reclassify`.
- **Evidence Health (Liveness)**: Use `scripts/verify_evidence.py`. Any skill with dead links must be assigned the **`broken-evidence`** demerit and demoted by one level.
- **Pruning Placeholder Evidence**: Skills with placeholder or non-verifiable evidence should be demoted to **Awakened (1★)** status using `gaia dev update-named --status awakened`.
- **Suite Components**: Suites do not need `links.github` themselves but their components must have specific `blob/branch/subpath` URLs.

## Gaia CLI Commands for Audit

- **Calibrate Level** (named skills only): `gaia dev calibrate <contributor/skill_id> <level>★` — calibrate operates on *named* skills (contributor/skill format), not bare generic IDs. Generic skills have no level to calibrate.
- **Reclassify Type** (generic only): `gaia dev reclassify <generic_id> <type>` — changes a generic's type (basic/extra/unique).
- **Update Named Status**: `gaia dev update-named <contributor/skill_id> --status <status>`
- **Broken evidence**: demerits are removed from the schema (a meta shift toward advanced evidence tiers is underway), so do **not** patch `demerits` on any node. For a dead link, remove/replace the offending evidence entry (direct YAML edit) or log it via `gaia dev evidence`, and add a `demote` timeline event. Always run `gaia validate` after.
- **Build Registry**: `gaia docs build` (always run after registry edits to sync derivatives).

## Output

Report:
- Evidence checked
- Correction made or reason no change was warranted
- Generated files updated
- Verification commands and results

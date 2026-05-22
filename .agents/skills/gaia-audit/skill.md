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
   - Does it map to the claimed Gaia capability?
   - Does it justify its stars, tier, named status, or `promotedNamedSkillId`?
   - Is it outdated, superseded, overpromoted, duplicate, or under-sourced?
   - **Upgrade Path & Fusion Analysis**: Can this skill be evolved? Consolidate multiple overlapping basic concepts under a single elegant Basic generic skill (e.g. literature-search) to avoid vendor-bloat. If a set of related basic skills can be combined into a multi-step high-level orchestration, plan to fuse them into a new **Extra** master skill (like `computational-biology-workflows`).
   - **Rigorous Verification**: Does the source include a specific **agent playbook** (e.g., `AGENTS.md`, `CLAUDE.md`, `.claude/skills/`, or a documented autonomous agent workflow)?
   - **Demerit Check (Strategic)**: Only actively audit demerits for skills at **3★+**. Be lenient toward skills that are portable across platforms. Reward portable, "Generalized" skills by favoring them for promotion to higher stars or Ultimate tier when they remain demerit-free at high levels.
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
     gaia docs build
     ```
7. Verify:
   ```bash
   gaia validate
   gaia validate --intake
   gaia test all
   git diff --check
   ```

## Demotion Rules

- Keep real skills in `registry/real-skills.json` when the source is valid but remove unsupported promotion fields.
- Remove `promotedNamedSkillId` when the item does not justify the named claim.
- Remove or downgrade `status: named`, `title`, or `catalogRef` when reviewer classification is unsupported.
- Remap broad `mapsToGaia` links to narrower accurate IDs when evidence supports only a smaller capability.
- Do not claim Ultimate tier or 5★+ stars from installability or source-directory presence alone.

## Output

Report:
- Evidence checked
- Correction made or reason no change was warranted
- Generated files updated
- Verification commands and results

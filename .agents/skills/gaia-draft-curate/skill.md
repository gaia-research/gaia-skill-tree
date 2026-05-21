---
name: gaia-draft-curate
description: Review pending Gaia draft skill intake batches and open draft PRs. Classifies each proposed skill (accept/rename/duplicate/needs-evidence/reject) without touching registry/gaia.json. Optionally triggers a promotion PR for accepted skills. Use when the user asks to "check drafts", "review intake batches", "triage pending skills", or explicitly types /gaia-draft-curate.
version: 1.2.0
---

# gaia-draft-curate

Review pending Gaia draft skill intake batches and open draft PRs. This skill is read-only with respect to `registry/gaia.json` — it classifies proposals and, after user confirmation, may hand off to `/gaia-curate` for promotion.

## What this skill does

1. **Pull latest** — `git pull --ff-only` so local state matches remote.

2. **Scan intake batches** — glob `registry-for-review/skill-batches/*.json` (skip `.gitkeep`). For each batch file, parse and validate against `registry/schema/skillBatch.schema.json` using `python3 scripts/validate_intake.py`. Report any schema errors immediately.

3. **Check open draft PRs** — run:
   ```bash
   gh pr list --label "draft-skills" --state open --json number,title,headRefName,url,createdAt
   ```
   Cross-reference with local batch files by `batchId` where possible. List any PRs that have no corresponding local batch (remote-only) and any local batches that have no open PR.

4. **Evidence enrichment and Rigorous Verification** — before displaying the review table, for each proposed skill in the batch:

   a. Search GitHub for concrete implementations:
   ```bash
   gh search repos "<proposed-skill-name>" --sort=stars --limit=5
   gh search repos --topic="<proposed-skill-id>" --sort=stars --limit=5
   ```
   b. **Verify Agent Playbooks**: Inspect each qualifying repo for an **agent playbook** (e.g., `AGENTS.md`, `CLAUDE.md`, `.claude/skills/`, or a documented autonomous agent workflow). A repo without a clear playbook should be flagged as `needs-playbook`.
   
   c. **Fusion Analysis**: Determine if the proposed skill represents a new capability or is "original enough" to warrant a new **Generic (Extra) Name** in the canonical `registry/gaia.json`.

   d. **Demerit Identification (Strategic)**: Check for `heavyweight-dependency` or `niche-integration`. Only actively look for these for **3★+** skills. Favor cross-platform/universal implementations by keeping them demerit-free.
   
   e. If a repo-level URL was previously recorded as evidence for this skill (e.g., the `sourceRepo` in the intake batch), **re-resolve it to a specific SKILL.md path** using the steps above before accepting. Flag repo-root URLs as `needs-specific-url` if no SKILL.md can be found.

   f. Query SkillsMP for matching community skills:
   ```
   WebFetch: https://skillsmp.com/api/v1/skills/search?q=<skill-name>
   ```
   Note any SkillsMP matches as "Evidence Tier C available".

   This enrichment helps reviewers make informed accept/reject decisions. Skills with readily available Evidence Tier B/A and a verified SKILL.md should be favored for acceptance.

5. **Display review table** — for each batch, show:

   **Batch `<batchId>`** | Source: `<sourceRepo>` | Generated: `<generatedAt>`

   | # | Proposed ID | Name | Type | Similarity hints | Evidence Available | Decision |
   |---|---|---|---|---|---|---|
   | 1 | `skill-id` | Skill Name | atomic | `existing-skill` (0.82), `other` (0.61) | B: github.com/... | _(pending)_ |
   | … |

   Also show `knownSkills` count (already in registry — informational only, no action needed).

6. **Collect decisions** — ask the user to classify each proposed skill:
   - `accept` — ready to promote into `registry/gaia.json`
   - `rename <new-id>` — change the ID, then accept
   - `duplicate <existing-id>` — already covered; drop
   - `needs-evidence` — hold; note what Evidence Tier A/B source is missing
   - `reject` — remove from consideration

   Present one batch at a time. Do not proceed to the next batch until the current one is fully classified.

7. **Summarise decisions** — after all batches are reviewed, print a final tally:
   - Accepted: N skills (list IDs)
   - Renamed: N skills (old-id → new-id)
   - Held (needs evidence): N (list IDs + missing evidence notes)
   - Dropped (duplicate/reject): N (list IDs)

8. **Offer promotion** — if there are any accepted/renamed skills, ask the user:
   > "Promote accepted skills to `registry/gaia.json` now? This will invoke `/gaia-curate` for the accepted batch."

   - If **yes**: hand off to the `gaia-curate` workflow starting at step 4, pre-populating all decisions as `accept`. The promotion PR must link back to the originating intake PR(s).
   - If **no**: print the manual promotion steps and exit:
     ```
     # For each accepted skill, add to registry/gaia.json, then:
     python3 scripts/validate.py
     python3 scripts/generateProjections.py
     python3 scripts/exportGexf.py
     git commit -am "[atomic|composite] <name> — promote from registry-for-review/<batchId>"
     gh pr create --title "[promote] <slug>" --body "Promotes accepted skills from intake PR #<N>"
     ```

9. **Report** — output a final summary (see Output section).

## When there are no pending drafts

If `registry-for-review/skill-batches/` is empty and no open `draft-skills` PRs exist, report:

> No pending draft intake batches found. Use `gaia push` to generate a new batch, or run `/gaia-curate` to add skills directly to the canonical graph.

Then stop — do not attempt any curation.

## Constraints

- **Read-only by default** — this skill never writes to `registry/gaia.json` directly. That only happens via the `/gaia-curate` promotion path with explicit user confirmation.
- Never modify batch files in `registry-for-review/skill-batches/` — they are immutable intake records.
- `needs-evidence` decisions should note what evidence tier is missing (Evidence Tier A paper / Evidence Tier B repo).
- If `gh` is not authenticated, skip the PR listing step and work from local batch files only; note the limitation in output.

## Repo location

Run from the root of your local clone of this repository. If you have not cloned it yet:
```
git clone https://github.com/mbtiongson1/gaia-skill-tree.git
cd gaia-skill-tree
```

## Output

At the end, report:
- Batches reviewed (count)
- Open draft PRs found (count + URLs)
- Decisions: accepted / renamed / held / dropped (counts + IDs)
- Whether promotion was triggered (yes/no + branch name if yes)

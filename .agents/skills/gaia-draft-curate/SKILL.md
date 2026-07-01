---
name: gaia-draft-curate
description: >
  Triage and classify pending Gaia skill intake batches in registry-for-review/, then optionally hand off accepted skills to /gaia-curate for promotion. Use this skill when the user says "check drafts", "review intake batches", "triage pending skills", "what's waiting in the intake queue", "process batch proposals", "review gaia push output", "what did gaia push submit", "classify draft skills", "look at the review queue", "are there any pending skill proposals", "open a draft PR for intake", or explicitly types /gaia-draft-curate. This is the human-review gate between `gaia push` (which writes to registry-for-review/) and the canonical registry — it never writes to registry/gaia.json directly. If you want to skip staging and add skills straight to the registry, use /gaia-curate instead.
version: 1.3.0
---

# gaia-draft-curate

Review and classify pending Gaia skill intake batches from `registry-for-review/skill-batches/`. This skill is the human-review gate between `gaia push` (which stages proposals) and the canonical registry. It reads, enriches, and classifies — it never writes to `registry/gaia.json` directly.

## What this skill does

### Step 1 — Sync local state

Pull so your view matches remote:
```bash
git pull --ff-only
```

### Step 2 — Scan intake batches

Glob `registry-for-review/skill-batches/*.json` (skip `.gitkeep`). For each batch file, validate against schema:
```bash
python3 scripts/validate_intake.py
```
Report schema errors immediately — do not proceed with a malformed batch.

### Step 3 — Cross-reference open draft PRs

```bash
gh pr list --label "draft-skills" --state open --json number,title,headRefName,url,createdAt
```

Match PRs to local batches by `batchId`. Call out:
- Local batches with no open PR (needs PR opened)
- Open PRs with no corresponding local batch (remote-only; flag for manual inspection)

Skip this step and note the limitation if `gh` is not authenticated.

### Step 4 — Enrich each proposed skill

Before presenting the review table, enrich each proposed skill so the user has enough signal to decide:

**a. Find concrete implementations via GitHub search:**
```bash
gh search repos "<proposed-skill-name>" --sort=stars --limit=5
gh search repos --topic="<proposed-skill-id>" --sort=stars --limit=5
```
Only count repos with stars > 50, last commit < 1 year, and a README. Prefer repos with CI and clear docs.

**b. Resolve the evidence URL to a specific SKILL.md path.** If the batch recorded a bare repo URL as `sourceRepo`, use the search results to find the actual `SKILL.md` blob URL (`github.com/owner/repo/blob/main/skills/foo/SKILL.md`). Mark bare repo-root URLs as `needs-specific-url` if no SKILL.md can be found — a repo root installs to a root symlink and makes the skill undiscoverable.

**c. Check for deduplication / canonical alignment.** Does this skill map to an existing generic ID in `registry/gaia.json`? Multiple vendor wrappers for the same concept (e.g. different search APIs) should map to one unified generic ID (`literature-search`), not spawn separate generic skills. If several batch entries represent specialized forms of a single high-level workflow, plan to fuse them into one composite extra-tier skill.

**d. For 3★+ skills only — check for heavyweight-dependency or niche-integration demerits.** Favour cross-platform implementations; flag vendor lock-in.

### Step 5 — Display the review table

For each batch:

**Batch `<batchId>`** | Source: `<sourceRepo>` | Generated: `<generatedAt>`

| # | Proposed ID | Name | Type | Similarity hints | Evidence available | Decision |
|---|---|---|---|---|---|---|
| 1 | `skill-id` | Skill Name | atomic | `existing-skill` (0.82) | B: github.com/… | _(pending)_ |

Also show `knownSkills` count from the batch (informational — these are already in the registry; no action needed).

### Step 6 — Collect decisions

Ask the user to classify each proposed skill. Work one batch at a time — do not move to the next until the current batch is fully classified.

| Decision | Meaning |
|---|---|
| `accept` | Ready to promote |
| `rename <new-id>` | Change the ID, then accept |
| `duplicate <existing-id>` | Already covered — drop |
| `needs-evidence` | Hold; note what tier is missing (Tier A paper / Tier B repo / specific SKILL.md URL) |
| `reject` | Remove from consideration |

### Step 7 — Summarise

Print a final tally after all batches are reviewed:
- Accepted: N skills (list IDs)
- Renamed: N skills (old-id → new-id)
- Held: N (IDs + missing-evidence notes)
- Dropped: N (IDs)

### Step 8 — Offer promotion

If there are accepted or renamed skills, ask:

> "Promote accepted skills to `registry/gaia.json` now? This will invoke `/gaia-curate` for the accepted batch."

- **Yes** — hand off to `/gaia-curate` starting at its evidence-research step, pre-populated with accepted decisions. The promotion PR must link back to the originating intake PR(s).
- **No** — print the manual steps and exit:
  ```bash
  # For each accepted skill:
  gaia dev add "<name>" --type basic --description "..."
  gaia dev evidence <skill-id> "<url>" --class B
  python3 scripts/validate.py
  gaia dev docs
  git commit -am "[atomic|composite] <name> — promote from registry-for-review/<batchId>"
  gh pr create --title "[promote] <slug>" --body "Promotes accepted skills from intake PR #<N>"
  ```

## When there are no pending drafts

If `registry-for-review/skill-batches/` is empty and no open `draft-skills` PRs exist:

> No pending draft intake batches found. Use `gaia push` to generate a new batch, or run `/gaia-curate` to add skills directly to the canonical graph.

Stop — do not attempt any curation.

## Constraints

- Never write to `registry/gaia.json` directly. That only happens via the `/gaia-curate` promotion path with explicit user confirmation.
- Never modify batch files in `registry-for-review/skill-batches/` — they are immutable intake records.
- `needs-evidence` decisions must specify what is actually missing (type, tier, URL format).
- All registry mutations that do happen downstream must go through `gaia dev` CLI commands, not direct file edits (Programmatic-First Policy).

## Output

At the end, report:
- Batches reviewed (count)
- Open draft PRs found (count + URLs)
- Decisions: accepted / renamed / held / dropped (counts + IDs)
- Whether promotion was triggered (yes/no + branch name if yes)

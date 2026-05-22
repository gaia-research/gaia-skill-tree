---
name: gaia-curate
description: Expand the Gaia skill registry with new popular AI agent skills, fully evidenced and validated, then push a PR. Use this skill when the user asks to "update the tree", "add new skills to Gaia", "curate the registry", "expand the skill graph", or explicitly types /gaia-curate.
version: 1.6.0
---

# gaia-curate

Expand the Gaia skill registry (`registry/gaia.json`) with new popular AI agent skills, fully evidenced and validated, then push a PR.

## What this skill does

0. **Load the sources registry** — read `registry/skill-sources.md` before doing any research. This is the authoritative list of known skill marketplaces, GitHub orgs, and registries. Use every listed source as a research target in step 2. When you discover a new marketplace or skill collection repo not yet in that file, append it following the format described at the bottom of the file — include it in the same PR.

1. **Read the current graph** — load `registry/gaia.json` to see every existing skill ID so nothing is duplicated.
2. **Research** — for each candidate skill, gather concrete evidence using ALL of the following channels (in order of priority):

   **2a. GitHub search (50% of research effort — Evidence Tier B):**
   Search for actual repos implementing the skill:
   ```bash
   gh search repos --topic="<skill-topic>" --sort=stars --limit=20
   gh search repos "<skill-name> agent" --sort=stars --limit=10
   ```
   Qualify repos: stars > 50, last commit < 1 year, has README + license. Prefer repos with CI, tests, and clear documentation.

   **2a-ii. Inspect repos for individual skill files — do not use a repo URL as evidence until you confirm what is inside it.**

   A repo is often a *collection* of many skills, not a single skill. After finding a qualifying repo, check the common skill directory layouts:
   ```bash
   # Check each layout — only the first match that returns results matters
   gh api repos/{owner}/{repo}/contents/skills --jq '.[].name'
   gh api repos/{owner}/{repo}/contents/.claude/skills --jq '.[].name'
   gh api repos/{owner}/{repo}/contents/codex/skills --jq '.[].name'
   gh api repos/{owner}/{repo}/contents/.codex/skills --jq '.[].name'
   gh api repos/{owner}/{repo}/contents/cursor/skills --jq '.[].name'
   ```
   If a skills directory exists, it will return a list of subdirectory names — each is a distinct skill.

   **For each skill subdirectory found:**
   1. Verify it contains a `SKILL.md` (or `skill.md`) file:
      ```bash
      gh api repos/{owner}/{repo}/contents/<skills-dir>/<skill-name>/SKILL.md --jq '.download_url'
      ```
   2. Fetch the SKILL.md content to read its description.
   3. Map it to an existing or new Gaia skill ID.
   4. Use the **raw file URL** (e.g., `https://github.com/{owner}/{repo}/blob/main/<skills-dir>/<skill-name>/SKILL.md`) as the Evidence Tier B `source` — never the repo root URL.
   5. Treat each discovered skill as a **separate candidate** to evaluate independently (accept/rename/duplicate/reject it on its own merits).

   If no skills directory is found, the repo itself is the evidence source and its URL may be used directly.

   **2b. SkillsMP search (10% — Evidence Tier C):**
   Query the SkillsMP public API for related community skills:
   ```
   WebFetch: https://skillsmp.com/api/v1/skills/search?q=<skill-name>
   ```
   Use matching SkillsMP entries as supplementary Evidence Tier C. Rate limit: 50 requests/day unauthenticated.

   **2c. Paper search (20% — Evidence Tier A):**
   For skills targeting Level II+ or those with only Evidence Tier C:
   ```
   WebSearch: "<skill-name> arxiv 2024 2025 2026 agent benchmark"
   WebSearch: "<skill-name> survey" site:arxiv.org
   ```
   Use arXiv abs URLs as Evidence Tier A. Only include papers with clear relevance and measurable benchmarks.

   **2d. Existing tree audit (20%):**
   Before proposing new skills, scan `registry/gaia.json` for:
   - Skills at level 0/I with only Evidence Tier C (upgrade candidates)
   - Skills with `status: "provisional"` that could be validated with better evidence
   - Skills at level II+ missing Evidence Tier A

   Prioritize upgrading these with B/A evidence before proposing entirely new skills. This ensures the tree grows stronger, not just wider.

3. **Design the batch** — for each candidate skill determine:
   - Type: `basic` (no prerequisites) / `extra` (≥2 prereqs) / `ultimate` (≥3 prereqs + 3 Evidence Tier A/B sources). A graph-isolated `basic` at 4★+ may be promoted to `unique`.
   - **Fusion-First Design & Semantic Mapping Rationale**: 
     - *No Made-up Generics*: Avoid creating a new, separate generic skill for every vendor API or service (e.g., do not create distinct generic skills for `pubmed`, `arxiv`, `biorxiv`, `europepmc` etc.). Map multiple named implementations of identical concepts to a single elegant basic generic skill (e.g. `literature-search`) to prevent registry bloat and maintain a high-quality global graph.
     - *Master Skill Fusion*: When multiple distinct named skills represent specialized capabilities that can be combined or orchestrated in a multi-step workflow (e.g., fetching structures, aligning sequences, rendering structures), define a composite **Extra** skill (like `computational-biology-workflows`) and link the basic skills as its prerequisites. Calibrate the advanced named implementations (e.g. AlphaFold, AlphaGenome) to higher levels (`3★` or `4★` max) referencing that composite Extra skill.
   - Stars: target **4★** (Hardened) minimum — requires at least 1× Evidence Tier B or A.
   - Prerequisites and derivatives (must reference existing IDs).
   - **Demerit Check (Strategic)**: Identify `heavyweight-dependency`, `niche-integration`, or `experimental-feature`. Only strictly apply these to skills at **3★+**. If a high-level skill is cross-platform and "Universal," reward it by omitting demerits.
   - **Named Promotion**: Determine if the specific implementation should be promoted to a **Named Skill** in `registry/named/`.
   - Do **not** ask the contributor to choose a rarity value — the rarity axis is deprecated (see `CONTEXT.md` § Rarity). `gaia add` writes the legacy default automatically; the field will disappear once the schema migration lands.
4. **Present draft for review** — before writing any code or committing, display the full proposed skills table:

   | ID | Name | Type | Stars | Prereqs | Demerits | Named Promotion? |
   |---|---|---|---|---|---|---|
   | … | … | … | … | … | … | … |

   Similarity hints are lexical matches from the existing registry (≥0.45 score). For each proposed skill, ask the user to mark one of:
   - `accept` — proceed as designed
   - `rename <new-id>` — change the ID before generating
   - `duplicate` — already covered by an existing skill; drop it
   - `needs-evidence` — hold until an Evidence Tier A/B source is supplied
   - `reject` — remove from the batch entirely

   **Do not proceed to step 5 until the user has reviewed and the batch contains at least one `accept`.** Incorporate all `rename` decisions before writing the script. Drop everything that is not `accept`/`rename`.

5. **Execute meta shifts via CLI** — for each accepted skill from step 4, use the `gaia add` command. This ensures timeline logging, schema integrity, and automated assembly.
   ```bash
   gaia add "Skill Name" --id <id> --type <type> --description "..."
   ```
   For named promotions, use:
   ```bash
   gaia add "Skill Name" --id <id> --named --contributor <user> --generic-ref <ref>
   ```
6. **Run validation** — `gaia validate` must exit 0.

7. **Regenerate derived files** — run `gaia docs build`. This ensures `registry.md`, `combinations.md`, `skills/**/*.md`, `registry/gaia.gexf`, and `skill-trees/*/skill-tree.md` stay in sync.
8. **Commit on a review branch** — branch name `review/meta/<slug>`, commit message follows `[type] Title — brief description`.
9. **Push and open a PR** via the GitHub API using stored git credentials. The auto-triage CI classifies the PR:
   - PRs touching `registry/` from a bot with evidence score ≥ 60 are auto-merged.
   - PRs flagged `draft-skills` or `needs-review` are routed to the `route-review` job — a human must approve before merge.
   - Ultimate skill proposals always require maintainer approval.
10. **Register the batch itself** as a `registryCuration` evidence entry if new demonstrations were produced.

## Two-phase intake workflow (gaia push)

For contributors who use the `gaia push` CLI, a separate **draft intake** path exists that does NOT directly modify `registry/gaia.json`:

1. **`gaia push`** — scans the source repo for skill-shaped tokens, builds `registry-for-review/skill-batches/<batchId>.json`, and opens a draft PR with labels `draft-skills` and `needs-review`.
2. **Reviewer classification** — maintainers review the draft PR and mark each proposed skill: `accept` / `rename` / `duplicate` / `needs-evidence` / `reject`.
3. **Promotion PR** — accepted skills are promoted into `registry/gaia.json` in a separate follow-up PR. That PR must run `gaia validate` and `gaia validate --intake` and must link back to the intake PR.

Use `/gaia-draft-curate` to triage pending intake batches before running this skill.

To validate intake batch files locally:
```bash
gaia validate --intake
```

## Constraints

- **Programmatic Registry Management**: NEVER hand-edit files in `registry/nodes/` or `registry/gaia.json`. Use `gaia add`, `gaia merge`, `gaia split`, and `gaia evidence`.
- All evidence `source` values must be real, resolvable URLs (arXiv abs pages or GitHub repos).
- Ultimate skills at `status: validated` require ≥3 Evidence Tier A/B entries; new ultimates should land as `provisional` until the maintainer merges.
- No cycles in the DAG. No orphaned composite nodes.
- Skill IDs: `lowercase-dash` format (e.g., `chain-of-thought`, `web-search`). No camelCase, no vendor names, no abbreviations unless universally understood. Pattern: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`.
- **Edge schema**: edges use `sourceSkillId`/`targetSkillId` keys (not `from`/`to`). Valid `edgeType` values are `prerequisite`, `corequisite`, `enhances` only — there is NO `derivative` edge type. Use `enhances` for skill→derivative edges.
- **Encoding**: all Python `open()` calls must use `encoding='utf-8'` to avoid CP-1252 drift on Windows (em-dash `—` becomes `0x97` without it, failing CI on Linux).

## Evidence standards (quick reference)

| Evidence Tier | Standard |
|---|---|
| A | Peer-reviewed paper — use `https://arxiv.org/abs/<id>` |
| B | Reproducible open-source demo — use the GitHub repo URL |
| C | Credible vendor/community demo (only sufficient for Level II) |

## Repo location

Run from the root of your local clone of this repository. If you have not cloned it yet:
```
git clone https://github.com/mbtiongson1/gaia-skill-tree.git
cd gaia-skill-tree
```

## Recording contributors

After the PR is opened, add the contributor's GitHub username to the `## Contributors` section of `README.md` (at the bottom of the file, before the License section) if not already listed. Use the format:

```markdown
| @username | Brief description of contribution |
```

If the `## Contributors` section does not exist yet, create it. Commit this change in the same PR as the skill additions. This ensures every person who runs `/gaia-curate` is permanently thanked in the project.

## Output

At the end, report:
- PR URL
- Skills added (count by type)
- Validation result summary
- Any existing skills whose `derivatives` arrays were patched
- Review decisions applied (accepted / renamed / dropped)
- Contributor recorded in README

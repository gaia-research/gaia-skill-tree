---
name: gaia-bot-curate
description: Curate Gaia bot crawler branches into real-skill catalog entries. Use when the user asks to process bot/* crawl branches, curate crawler output, clean up bot proposal branches, or explicitly types /gaia-bot-curate.
---

# gaia-bot-curate

Curate remote `bot/*` crawler branches into `registry/real-skills.json` from a fresh `origin/main` review branch.

## Workflow

1. **Start clean**
   - `git fetch --all --prune`
   - Confirm no local work will be overwritten.
   - Create `review/meta/<short-crawl-slug>` from `origin/main`; do not merge bot branches.

2. **Collect bot payloads outside the repo**
   - List remote crawler branches with `git for-each-ref refs/remotes/origin/bot`.
   - For each branch, find added `proposals/*.json` files with `git diff --name-only $(git merge-base origin/main <branch>)..<branch> -- proposals`.
   - Write raw payload copies and a compact deduplicated candidate JSON to `/tmp`.
   - Write `/tmp/gaia-bot-crawl-skill-names-<date>.md` with source branch, proposal file, candidate ID, name, evidence URL, and duplicate source refs.
   - Deduplicate by proposal `id`; if missing, use normalized lowercase `name`.

3. **Dispatch narrow triage agents**
   - Split by source type (`github`, `vscode-marketplace`, `huggingface`, or other discovered source).
   - Give each agent only the relevant `/tmp` candidate JSON subset plus the rule below; do not pass full raw payloads or unrelated history.
   - Ask for accepted/rejected JSON-like output with `id`, `name`, `contributor`, `url`, optional `sourceRepo`, `mapsToGaia`, and `reason`.

4. **Accept and Analyze Real Skills**
   - **Accept** concrete skill implementations, workflow artifacts, model capability pages, or reputable package/repo pages.
   - **Rigorous Verification**: Treat MCP servers, API connectors, and tool extensions as `needs-evidence` unless they include a specific **agent playbook** (e.g., `AGENTS.md`, `CLAUDE.md`, `.claude/skills/`, or a documented autonomous agent workflow like Firecrawl's `Map` logic).
   - **Fusion Analysis**: For each accepted item, determine if it is "original enough" to warrant a new **Generic (Extra) Name** in the canonical `registry/gaia.json`. If it fuses multiple basic capabilities (e.g., `web-scrape` + `browser-automation`), propose a new Extra skill.
   - **Demerit Assignment (Strategic)**: Apply demerits only to skills at **Level 3★ (Evolved)** or higher. For lower levels, be lenient unless the skill is strictly vendor-locked.
     - **Threshold**: Only assign a demerit if it breaks the "Install Anywhere" promise for a developer.
     - `heavyweight-dependency`: Only if it requires massive infrastructure (e.g., full Airflow stack, 10GB+ Docker) that a typical dev can't run locally.
     - `niche-integration`: Only if restricted to a specific non-portable OS or IDE (e.g., Windows-only Visual Studio).
     - **Reward Generality**: If a high-level skill remains demerit-free, prioritize it for **Named Promotion**.
   - **Named Promotion**: If the item has a clear playbook and high quality, propose it as a **Named Skill** (2★+) in `registry/named/` with a unique Title (e.g., "The Digital Pathweaver").

5. **Integrate and Promote**
   - Main agent executes `gaia dev add` and `gaia dev evidence` commands for accepted entries (the mutation verbs live under `gaia dev`, not at the top level).
   - **For generic (starless) nodes**: `gaia dev add "Skill Name" --id <id> --type extra --description "..."` — generic skills have no `--level` flag; they are rank-less taxonomy.
   - **For named skills**: `gaia dev add "Skill Name" --id <id> --named --contributor <user> --generic-ref <ref> --status awakened` — named skills are submitted with `status: awakened` (enum `{awakened, named}`); a reviewer later promotes to `named` and calibrates stars (2★–6★). Do not hand-set `title`/`catalogRef`.
   - Use `gaia dev evidence` to attach the payload URLs and details to the appropriate skill (generic or named, as applicable).
   - NEVER hand-edit files in `registry/`.

6. **Clean remote bot branches**
   - Delete consumed remote bot branches only after the `/tmp` snapshot exists and the review branch contains the curated result.
   - Verify deletion with `git ls-remote --heads origin <branch>...`.

7. **Verify and publish**
   - Run:
     ```bash
     gaia docs build
     gaia validate
     ./.venv/bin/pytest tests/test_validate.py tests/test_real_skill_catalog.py tests/test_registry_layout.py
     git diff --check
     ```
   - Review `git diff --name-only origin/main`; `review/meta` branches must not touch `packages/`, `src/`, or `registry/schema/`.
   - If hooks add package/version churn on a curation-only `review/meta` branch, restore out-of-scope files from `origin/main`, rerun verification, and amend with `--no-verify` after manual validation.
   - Push the review branch and open a PR summarizing accepted, rejected, `needs-evidence`, validation, and deleted bot branches.

## Output

Report:
- PR URL.
- Temp snapshot path.
- Accepted real-skill count by source.
- Rejected and `needs-evidence` counts with reasons.
- Validation commands and outcomes.
- Remote bot branches deleted.

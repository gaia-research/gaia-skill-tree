---
name: gaia-docs-sync
description: Sync documentation updates across the main repository and the adjacent wiki repository. Use when updating crucial documentation (like README.md, docs/index.html, or wiki pages) to ensure all surfaces stay in sync efficiently, especially from a docs branch.
---

# gaia-docs-sync

Ensure documentation changes are accurately applied to both the main repository (`README.md`, `docs/index.html`) and the adjacent wiki repository (`../gaia-wiki`), and pushed via PR and direct push respectively.

## What this skill does

1. Validates the current branch is appropriate for docs (e.g., `docs/*`).
2. Updates primary documentation files in the main repository (e.g., `README.md`, `docs/index.html`).
3. Commits and pushes the changes, then creates a PR for the main repo.
4. Manuevers to the adjacent wiki repository.
5. Applies the exact same documentation updates to the corresponding wiki pages (e.g., `Getting-Started.md`, `CLI-Reference.md`).
6. Commits and pushes the wiki updates directly to the wiki's `master` branch.

## Workflow

### 1. Update Main Repository Documentation

Make the requested changes to the main repository documentation files (e.g., `README.md`, `docs/index.html`).

Once complete:
```bash
git add <files>
git commit -m "docs: <summary of changes>"
```

### 2. Push and PR Main Repository

Push the documentation branch and create a PR to merge into `main`.

```bash
git push -u origin <branch-name>
gh pr create --title "docs: <summary of changes>" --body "<detailed description>"
```

### 3. Update Adjacent Wiki Repository

Clone or pull the wiki repository into an adjacent folder if it's not already up to date.

```bash
# If not cloned yet:
git clone https://github.com/mbtiongson1/gaia-skill-tree.wiki.git ../gaia-wiki

# If already cloned:
cd ../gaia-wiki
git pull origin master
```

### 4. Apply Changes to Wiki Pages

Identify which wiki pages correspond to the changes made in the main repository (e.g., `Getting-Started.md`, `Home.md`, `CLI-Reference.md`). 

Apply the identical logic or content updates to these wiki pages.

### 5. Commit and Push Wiki Updates

Commit and push the wiki repository directly to `master`.

```bash
cd ../gaia-wiki
git add <updated-files>.md
git commit -m "docs: <summary of changes>"
git push origin master
```

## Constraints
- **Use Docs Branches:** Always use a `docs/*` branch for main repo documentation updates to avoid triggering unnecessary CI/CD branch checks intended for `cli/*` or `schema/*` branches.
- **Maintainer Hooks:** Note that the main repo has a pre-commit hook that generates docs automatically. Ensure this hook succeeds.
- **Wiki Location:** The wiki must remain adjacent to the main repo (i.e. `../gaia-wiki`) to allow easy cross-repo synchronization.
- **Accuracy:** The wiki and the main repo documentation must reflect the exact same technical capabilities, such as CLI command options, schema requirements, or rank nomenclature.

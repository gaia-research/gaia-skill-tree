---
name: pr
description: Push committed changes and create a draft PR on GitHub. Use when you have staged changes ready to push and want to open a draft PR for early feedback or documentation.
---

# PR

Quickly push changes and open a draft pull request on GitHub.

## When to Use

- You have staged changes ready to push and want to create a draft PR
- Early feedback needed on work-in-progress
- Want to document and track changes before final review
- Need to open a PR for discussion or CI validation

## Instructions

### Step 1: Verify Staged Changes

Check what will be committed:
```bash
git status
```

Ensure all changes you want are staged with:
```bash
git add <files>
```

Or add everything:
```bash
git add .
```

### Step 2: Create Commit Message

Write a clear, conventional commit message. Use the format:
```
<type>(<scope>): <description>

<optional body with details>
```

Types: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, etc.

Examples:
- `feat(registry): add new skill category`
- `fix(cli): resolve version mismatch`
- `chore: regenerate artifacts`

### Step 3: Commit Changes

```bash
git commit -m "your commit message here"
```

### Step 4: Push to Remote

```bash
git push -u origin <branch-name>
```

If you're on `main` or pushing to an existing branch:
```bash
git push
```

### Step 4: Create Draft PR

```bash
gh pr create --draft
```

This will prompt you for:
- **Title** — auto-filled from commit, edit as needed
- **Body** — add context, description, or leave blank
- **Assignees** — optional
- **Labels** — optional

Or specify details inline:
```bash
gh pr create --draft --title "Your PR Title" --body "Description here"
```

## Tips

- **Draft PRs** show as "Draft" and won't trigger auto-merge workflows
- **Rebase before final PR** — `git rebase -i origin/main` to clean up commits
- **Ready to review?** — Use `gh pr ready` to convert from draft to ready-for-review
- **Add more commits** — Just push again with `git push`, the PR updates automatically

## Troubleshooting

**"fatal: The current branch has no upstream branch"**
- Use `git push -u origin <branch-name>` on first push

**"Permission denied" when pushing**
- Check your git credentials: `gh auth status`
- Re-authenticate if needed: `gh auth login`

**PR creation fails**
- Ensure you're in a git repository: `git rev-parse --show-toplevel`
- Check GitHub CLI is installed: `gh version`

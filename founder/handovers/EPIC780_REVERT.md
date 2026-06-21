# Epic #780 — Revert Playbook

**Created:** 2026-06-22
**Epic:** #780 Architectural Modernization & Technical Debt Reduction
**Integration Branch:** `dev/improve-codebase-architecture`

## Pre-Merge Snapshot

Before merging the integration branch to main, create a snapshot tag:

```bash
git tag pre-epic-780 main
git push origin pre-epic-780
```

This is the instant-rollback anchor.

---

## Full Epic Revert (after merge to main)

If the entire integration branch needs to be rolled back:

```bash
# 1. Find the merge commit
git log --merges --oneline main | head -5

# 2. Revert the merge (keep main's side)
git revert -m 1 <merge-commit-sha>
git push origin main

# 3. Or hard-reset to the snapshot tag (nuclear option, requires force push)
git reset --hard pre-epic-780
git push --force-with-lease origin main
```

---

## Per-Sub-Issue Revert

Each sub-issue is merged as a regular merge commit (no squash). Find and revert individually:

### Sub-Issue 1: Artifact Pipeline (#781)

```bash
# Revert the merge commit
git log --merges --oneline dev/improve-codebase-architecture | grep "781\|artifact"
git revert -m 1 <sha>

# Manual cleanup: re-track generated files
git checkout pre-epic-780 -- .gitignore
git add registry/gaia.json docs/graph/gaia.json base_gaia.json \
  registry/named-skills.json docs/graph/gaia.gexf docs/graph/gaia.svg \
  docs/graph/named/index.json docs/graph/ledger/data.json graph/embeddings.json
git commit -m "revert: re-track generated files (revert #781)"
```

**Workflow revert:** Remove the "Upload Generated Artifacts" step from `sync-artifacts.yml`.

### Sub-Issue 2b: Command Migration (NEW)

```bash
git log --merges --oneline dev/improve-codebase-architecture | grep "command-migration\|2b"
git revert -m 1 <sha>
```

**Workflow revert:** Replace all `gaia dev release/validate/test/docs` back to `gaia release/validate/test/docs build` in:
- `.github/workflows/sync-artifacts.yml` (lines 87–88)
- `.github/workflows/validate.yml` (lines 49, 57, 64, 80)
- `.github/workflows/python-package.yml` (line 52)

### Sub-Issue 2: CLI Dynamic Discovery (#782)

```bash
git log --merges --oneline dev/improve-codebase-architecture | grep "782\|dynamic-dispatch"
git revert -m 1 <sha>
```

**This is the most complex revert.** The revert re-inflates `main.py` from ~200 to ~4,078 lines and removes the `commands/` modules. Test immediately:

```bash
gaia --help
gaia dev --help
python -m pytest tests/test_cli_core.py tests/test_meta_ops.py
```

### Sub-Issue 3: Taskfile + Lockstep (#783)

```bash
git log --merges --oneline dev/improve-codebase-architecture | grep "783\|versioning"
git revert -m 1 <sha>
rm Taskfile.yml  # if revert doesn't fully clean it
```

**Workflow revert:** If CI was changed to use `task`, revert to direct `gaia dev` calls.

### Sub-Issue 4: Skill Quality Gates (#784)

```bash
git log --merges --oneline dev/improve-codebase-architecture | grep "784\|quality-gates"
git revert -m 1 <sha>
```

**Workflow revert:** Remove the `skill-quality` job from `validate.yml`.

### Sub-Issue 5: MCP Abstraction (#785)

```bash
git log --merges --oneline dev/improve-codebase-architecture | grep "785\|mcp"
git revert -m 1 <sha>
```

No workflow changes to revert.

---

## Automated Rollback Script

The script `scripts/rollback-epic-780.sh` is a convenience wrapper:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "⚠️  This will revert the Epic #780 merge from main."
echo "    Pre-merge tag: pre-epic-780"
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 1; fi

MERGE_SHA=$(git log --merges --oneline main | grep "epic-780\|improve-codebase-architecture" | head -1 | awk '{print $1}')
if [[ -z "$MERGE_SHA" ]]; then
  echo "ERROR: Could not find the Epic #780 merge commit."
  echo "Manual fallback: git reset --hard pre-epic-780 && git push --force-with-lease origin main"
  exit 1
fi

git revert -m 1 "$MERGE_SHA"
echo "✓ Reverted $MERGE_SHA. Push with: git push origin main"
```

---

## Post-Revert Verification

After any revert, run:

```bash
gaia validate                    # or gaia dev validate (whichever is active)
gaia test all                    # or gaia dev test all
gaia docs build --check          # or gaia dev docs --check
python -m pytest tests/ -x       # fast-fail on first error
```

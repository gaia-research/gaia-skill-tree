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

#!/bin/bash
#
# delete-bot-branches.sh
# Clean up consumed bot/* crawler branches after curation
#
# Usage:
#   ./scripts/delete-bot-branches.sh          # Delete all bot/* branches
#   ./scripts/delete-bot-branches.sh --dry-run  # Show what would be deleted
#

set -e

DRY_RUN=false
DELETED=0
FAILED=0
SKIPPED=0

if [[ "$1" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "🔍 DRY RUN MODE - No changes will be made"
  echo ""
fi

echo "Fetching latest remote refs..."
git fetch origin --prune > /dev/null 2>&1

echo "Collecting bot/* branches..."
BRANCHES=$(git for-each-ref refs/remotes/origin/bot --format='%(refname:short)' | sed 's/^origin\///')

if [ -z "$BRANCHES" ]; then
  echo "✅ No bot/* branches found - nothing to delete"
  exit 0
fi

BRANCH_COUNT=$(echo "$BRANCHES" | wc -l)
echo "Found $BRANCH_COUNT bot/* branches:"
echo "$BRANCHES" | sed 's/^/  - /'
echo ""

if [[ "$DRY_RUN" == true ]]; then
  echo "Would delete:"
  echo "$BRANCHES" | sed 's/^/  git push origin --delete /'
  exit 0
fi

echo "🗑️  Deleting bot/* branches..."
echo ""

for branch in $BRANCHES; do
  if git push origin --delete "$branch" 2>/dev/null; then
    echo "✅ Deleted: $branch"
    ((DELETED++))
  else
    echo "❌ Failed: $branch"
    ((FAILED++))
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Summary:"
echo "  ✅ Deleted: $DELETED"
if [ $FAILED -gt 0 ]; then
  echo "  ❌ Failed:  $FAILED"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAILED -gt 0 ]; then
  echo ""
  echo "⚠️  Some branches failed to delete. This may be due to:"
  echo "   - Insufficient permissions on the remote"
  echo "   - Network connectivity issues"
  echo "   - Branch protection rules"
  echo ""
  echo "Verify with: git ls-remote --heads origin | grep 'bot/'"
  exit 1
fi

exit 0

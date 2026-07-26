#!/usr/bin/env bash
# Validate a SKILL.md file is well-formed.
# Usage: bash scripts/validate.sh <path-to-SKILL.md>
set -euo pipefail

FILE="${1:-}"
if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "Error: provide a valid SKILL.md path" >&2
  exit 1
fi

errors=0

# Check YAML frontmatter exists
if ! head -1 "$FILE" | grep -q '^---$'; then
  echo "FAIL: missing YAML frontmatter (first line must be ---)" >&2
  errors=$((errors + 1))
fi

# Check frontmatter closes
if [[ $(grep -c '^---$' "$FILE") -lt 2 ]]; then
  echo "FAIL: YAML frontmatter not closed (need two --- lines)" >&2
  errors=$((errors + 1))
fi

# Check name field
if ! sed -n '/^---$/,/^---$/p' "$FILE" | grep -q '^name:'; then
  echo "FAIL: missing 'name:' in frontmatter" >&2
  errors=$((errors + 1))
fi

# Check description field
if ! sed -n '/^---$/,/^---$/p' "$FILE" | grep -q 'description'; then
  echo "FAIL: missing 'description' in frontmatter" >&2
  errors=$((errors + 1))
fi

if [[ $errors -gt 0 ]]; then
  echo "$errors error(s) found." >&2
  exit 1
fi

echo "OK: $FILE is well-formed"
exit 0

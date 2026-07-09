#!/usr/bin/env bash
# List installed skills available for fusion.
# Usage: bash scripts/candidates.sh [--dir <skills-dir>]
set -euo pipefail

DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) DIR="$2"; shift 2;;
    *) echo "Usage: candidates.sh [--dir <skills-dir>]" >&2; exit 1;;
  esac
done

# Auto-detect skills directory
if [[ -z "$DIR" ]]; then
  for d in .agents/skills .claude/skills .cursor/rules; do
    [[ -d "$d" ]] && DIR="$d" && break
  done
fi

if [[ -z "$DIR" || ! -d "$DIR" ]]; then
  echo "No skills directory found." >&2
  exit 1
fi

# List each skill that has a SKILL.md (or similar)
for skill_dir in "$DIR"/*/; do
  [[ -d "$skill_dir" ]] || continue
  name=$(basename "$skill_dir")
  desc=""
  for md in "$skill_dir"SKILL.md "$skill_dir"*.md; do
    if [[ -f "$md" ]]; then
      # Extract description from YAML frontmatter
      desc=$(awk '
        BEGIN { in_yaml=0; desc="" }
        /^---$/ {
          in_yaml++;
          if (in_yaml == 2) exit;
          next;
        }
        in_yaml == 1 {
          if ($0 ~ /^description:/) {
            idx = index($0, ":");
            val = substr($0, idx + 1);
            gsub(/^[ \t]+|[ \t]+$/, "", val);
            if (val ~ /^[>|]/) {
              getline;
              gsub(/^[ \t]+|[ \t]+$/, "", $0);
              desc = $0;
            } else {
              if (val ~ /^".*"$/ || val ~ /^\x27.*\x27$/) {
                val = substr(val, 2, length(val) - 2);
              }
              desc = val;
            }
            exit;
          }
        }
        END { print desc }
      ' "$md" 2>/dev/null || true)
      [[ -n "$desc" ]] && break
    fi
  done
  printf "%s\t%s\n" "$name" "${desc:-(no description)}"
done

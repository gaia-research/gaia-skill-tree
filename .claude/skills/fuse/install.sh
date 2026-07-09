#!/usr/bin/env bash
# Install skill-fuse into your agent skills directory.
set -euo pipefail

# Detect target
TARGET=""
for d in .agents/skills .claude/skills; do
  [[ -d "$d" ]] && TARGET="$d" && break
done

if [[ -z "$TARGET" ]]; then
  if [[ -d ".claude" ]]; then
    TARGET=".claude/skills"
  elif [[ -d ".agents" ]]; then
    TARGET=".agents/skills"
  else
    TARGET=".agents/skills"
  fi
  mkdir -p "$TARGET"
fi

# Clone and clean
git clone --depth 1 https://github.com/gaia-research/skill-fuse.git "$TARGET/fuse" 2>/dev/null
rm -rf "$TARGET/fuse/.git"

echo ""
echo "  skill-fuse installed to $TARGET/fuse"
echo "  Invoke with: /fuse"
echo ""

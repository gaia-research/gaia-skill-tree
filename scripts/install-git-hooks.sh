#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
chmod +x .githooks/pre-commit scripts/install-git-hooks.sh scripts/syncDocsGraphAssets.py
git config core.hooksPath .githooks
printf 'Gaia git hooks installed via core.hooksPath=.githooks\n'

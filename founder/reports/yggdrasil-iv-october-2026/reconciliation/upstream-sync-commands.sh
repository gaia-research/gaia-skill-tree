#!/usr/bin/env bash
# Re-runnable upstream refresh for the Yggdrasil IV October 2026 launch lane
# (EPIC #2189 outcome 2). Re-resolves each upstream's latest GitHub release live,
# then applies `gaia dev sync-upstream` per named skill. Run from a review/meta/*
# worktree cut from dev/yggdrasil-iv:
#
#   bash founder/reports/yggdrasil-iv-october-2026/reconciliation/upstream-sync-commands.sh --dry-run
#   bash founder/reports/yggdrasil-iv-october-2026/reconciliation/upstream-sync-commands.sh
#
# After a real run, regenerate Class S and commit the deterministic set
# (CLAUDE.md "Curation PR - which artifacts to commit"):
#   GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH=src python3 -m gaia_cli.main dev docs
#   python3 scripts/build_docs.py --check
#
# Idempotent: a skill already at the latest tag is reported and skipped. Existing
# `upstream.mode` is preserved (override per row below). Never hand-edit upstream:
# blocks; this script only calls the CLI verb.
set -u
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
ROOT="$(git rev-parse --show-toplevel)"; cd "$ROOT" || exit 1
export GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH="$ROOT/src"
USER_HANDLE="${GAIA_SYNC_USER:-mbtiongson1}"
GAIA() { python3 -m gaia_cli.main "$@"; }

# skill-id | upstream owner/repo | mode | bootstrap(0/1)
ROWS='
addy-osmani/agent-skills|addyosmani/agent-skills|components|0
garrytan/gbrain|garrytan/gbrain|components|0
heygen-com/hyperframes|heygen-com/hyperframes|components|0
mattpocock/skills|mattpocock/skills|components|0
obra/superpowers|obra/superpowers|components|0
ruvnet/agentdb|ruvnet/ruflo|components|0
ruvnet/dual-mode|ruvnet/ruflo|components|0
ruvnet/flow-nexus|ruvnet/ruflo|components|0
ruvnet/github-suite|ruvnet/ruflo|components|0
ruvnet/reasoningbank|ruvnet/ruflo|components|0
ruvnet/ruflo-v3|ruvnet/ruflo|components|0
ruvnet/ruflo|ruvnet/ruflo|components|0
leonxlnx/taste-skill|Leonxlnx/taste-skill|components|1
garrytan/garrytan|garrytan/gstack|components|1
garrytan/gstack|garrytan/gstack|components|1
'

fail=0
printf '%s\n' "$ROWS" | while IFS='|' read -r skill repo mode boot; do
  [ -z "$skill" ] && continue
  info="$(gh api "repos/$repo/releases/latest" --jq '[.tag_name,.published_at,.html_url]|@tsv' 2>/dev/null)"
  if [ -z "$info" ]; then echo "SKIP $skill: no latest release for $repo"; continue; fi
  tag="$(echo "$info" | cut -f1)"; rel="$(echo "$info" | cut -f2)"; url="$(echo "$info" | cut -f3)"
  args=(dev sync-upstream "$skill" --tag "$tag" --source-url "$url" --released-at "$rel" --mode "$mode" --user "$USER_HANDLE")
  [ "$boot" = "1" ] && args+=(--bootstrap)
  [ "$DRY" = "1" ] && args+=(--dry-run)
  echo "== $skill -> $tag ($rel)"
  out="$(GAIA "${args[@]}" 2>&1)"; rc=$?
  if [ $rc -ne 0 ] && echo "$out" | grep -q "already synced"; then echo "   already at $tag; skipped"
  elif [ $rc -ne 0 ]; then echo "$out" | tail -5; echo "   FAILED rc=$rc"; fi
  [ "$DRY" = "0" ] && [ $rc -eq 0 ] && echo "   $out" | tail -1
done
echo "Done. Next (real run): GAIA dev docs; python3 scripts/build_docs.py --check"

#!/usr/bin/env bash
# Bounded CI poll for a PR — exits cleanly, never loops forever.
#
# Usage:
#   ci-poll.sh <pr-number> [--max N] [--interval S]
#
# Exit codes:
#   0  — all required checks green
#   1  — still pending after max rounds (re-invoke to retry)
#   2  — one or more checks failed (read output for which ones)
#   3  — usage / dependency error

set -euo pipefail
command -v gh &>/dev/null || { echo "gh CLI required." >&2; exit 3; }
command -v jq &>/dev/null || { echo "jq required." >&2; exit 3; }

PR="${1:?Usage: ci-poll.sh <pr-number> [--max N] [--interval S]}"
shift

MAX=10
INTERVAL=30
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max)      MAX="$2";      shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 3 ;;
  esac
done

echo "▶ ci-poll PR #$PR  max=${MAX} rounds  interval=${INTERVAL}s"
round=0
while [[ $round -lt $MAX ]]; do
  round=$((round + 1))
  echo -n "  [${round}/${MAX}] checking... "

  result=$(gh pr checks "$PR" --json name,state,conclusion 2>/dev/null) || {
    echo "gh pr checks failed, retrying." >&2
    sleep "$INTERVAL"; continue
  }

  pending=$(echo "$result" | jq '[.[] | select(.state == "PENDING" or .state == "IN_PROGRESS")] | length')
  failed=$(echo  "$result" | jq '[.[] | select(.conclusion == "FAILURE" or .conclusion == "ERROR" or .conclusion == "TIMED_OUT")] | length')

  if [[ "$failed" -gt 0 ]]; then
    echo "❌ $failed failed"
    echo "$result" | jq -r '.[] | select(.conclusion == "FAILURE" or .conclusion == "ERROR" or .conclusion == "TIMED_OUT") | "    FAIL: \(.name)"'
    exit 2
  fi

  if [[ "$pending" -eq 0 ]]; then
    echo "✅ all green"
    exit 0
  fi

  echo "$pending pending — waiting ${INTERVAL}s"
  sleep "$INTERVAL"
done

echo "⏱ max rounds (${MAX}) reached — still pending"
exit 1

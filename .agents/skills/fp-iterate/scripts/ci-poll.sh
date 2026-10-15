#!/usr/bin/env bash
# Bounded current-head CI inspection. 0=green, 1=pending, 2=failed, 3=usage.
# gh returns 1 for failures and 8 for pending checks; those are result data.
set -euo pipefail
command -v gh >/dev/null || { echo 'gh CLI required.' >&2; exit 3; }
command -v jq >/dev/null || { echo 'jq required.' >&2; exit 3; }
PR="${1:?Usage: ci-poll.sh <pr-number> [--max N] [--interval S]}"
shift
[[ "$PR" =~ ^[1-9][0-9]*$ ]] || { echo 'PR must be a positive number.' >&2; exit 3; }
MAX=10
INTERVAL=30
while [[ $# -gt 0 ]]; do
  [[ $# -ge 2 ]] || { echo 'Missing option value.' >&2; exit 3; }
  case "$1" in
    --max) MAX="$2" ;;
    --interval) INTERVAL="$2" ;;
    *) echo 'Unknown option.' >&2; exit 3 ;;
  esac
  shift 2
done
[[ "$MAX" =~ ^[1-9][0-9]*$ && "$INTERVAL" =~ ^(0|[1-9][0-9]*)$ ]] || { echo 'Invalid poll bounds.' >&2; exit 3; }
[[ ${#MAX} -le 3 && "$MAX" -le 100 && ${#INTERVAL} -le 2 && "$INTERVAL" -le 60 ]] || { echo 'Poll bounds too large.' >&2; exit 3; }
for ((round=1; round<=MAX; round++)); do
  before=$(gh pr view "$PR" --json headRefOid --jq .headRefOid 2>/dev/null) || before=''
  status=0
  result=$(gh pr checks "$PR" --required --json name,state,bucket 2>/dev/null) || status=$?
  after=$(gh pr view "$PR" --json headRefOid --jq .headRefOid 2>/dev/null) || after=''
  if [[ "$before" =~ ^[a-fA-F0-9]{40}$ && "$before" == "$after" && ( "$status" == 0 || "$status" == 1 || "$status" == 8 ) ]] && \
     jq -e 'type=="array" and length>0 and all(.[]; type=="object" and (.name|type)=="string" and (.bucket|type)=="string")' >/dev/null 2>&1 <<< "$result"; then
    failed=$(jq '[.[]|select(.bucket=="fail" or .bucket=="cancel")]|length' <<< "$result")
    if [[ "$failed" -gt 0 ]]; then
      echo "failed: required checks at $after"
      jq -r '.[]|select(.bucket=="fail" or .bucket=="cancel")|"FAIL: \(.name) (\(.state))"' <<< "$result"
      exit 2
    fi
    # Unknown/queued/blocked/missing results fail closed to pending.
    if [[ "$status" == 0 ]] && jq -e 'all(.[]; .bucket=="pass" or .bucket=="skipping")' >/dev/null <<< "$result"; then
      echo "green: required checks at $after"
      exit 0
    fi
  fi
  echo "pending or unverifiable: round $round/$MAX"
  if [[ "$round" -lt "$MAX" ]]; then sleep "$INTERVAL"; fi
done
exit 1

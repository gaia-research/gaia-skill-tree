#!/usr/bin/env bash
# Bounded current-head CI inspection, compatible with gh 2.46.
# Conservatively requires EVERY reported current-head check/context to pass.
# This helper does not discover absent branch-protection requirements; verify
# required check completeness in the final PR review. 0=green, 1=pending/error,
# 2=failed, 3=usage. Never interpret unsupported/auth/API errors as green.
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
  status=0
  snapshot=$(gh pr view "$PR" --json headRefOid,statusCheckRollup 2>/dev/null) || status=$?
  if [[ "$status" != 0 ]]; then
    echo "CI inspection error: gh pr view exited $status; check CLI compatibility, authentication and API access." >&2
  elif ! jq -e 'type=="object" and (.headRefOid|type)=="string" and (.headRefOid|test("^[a-fA-F0-9]{40}$")) and (.statusCheckRollup|type)=="array"' >/dev/null 2>&1 <<< "$snapshot"; then
    echo 'CI inspection error: malformed head/check response.' >&2
  else
    before=$(jq -r .headRefOid <<< "$snapshot")
    status=0
    after=$(gh pr view "$PR" --json headRefOid --jq .headRefOid 2>/dev/null) || status=$?
    if [[ "$status" != 0 ]]; then
      echo "CI inspection error: head recheck exited $status; check authentication and API access." >&2
    elif [[ "$before" != "$after" ]]; then
      echo 'CI inspection pending: head changed or could not be verified.'
    else
      verdict=$(jq -r '
        def result:
          if .__typename=="CheckRun" then
            if (.name|type)!="string" or .status!="COMPLETED" then "pending"
            elif (.conclusion=="SUCCESS" or .conclusion=="NEUTRAL" or .conclusion=="SKIPPED") then "pass"
            elif (.conclusion=="FAILURE" or .conclusion=="CANCELLED" or .conclusion=="TIMED_OUT" or .conclusion=="ACTION_REQUIRED" or .conclusion=="STARTUP_FAILURE" or .conclusion=="STALE") then "fail"
            else "pending" end
          elif .__typename=="StatusContext" then
            if (.context|type)!="string" then "pending"
            elif .state=="SUCCESS" then "pass"
            elif (.state=="FAILURE" or .state=="ERROR") then "fail"
            else "pending" end
          else "pending" end;
        .statusCheckRollup | map(result) |
        if any(.[]; .=="fail") then "fail"
        elif length>0 and all(.[]; .=="pass") then "pass"
        else "pending" end' <<< "$snapshot")
      if [[ "$verdict" == fail ]]; then
        echo "failed: reported checks at $after"
        jq -r '.statusCheckRollup[] | "CHECK: \(.name // .context // "unknown") (\(.conclusion // .state // .status // "unknown"))"' <<< "$snapshot"
        exit 2
      elif [[ "$verdict" == pass ]]; then
        echo "green: all reported checks at $after; verify required-check completeness before merge"
        exit 0
      fi
    fi
  fi
  echo "pending or unverifiable: round $round/$MAX"
  if [[ "$round" -lt "$MAX" ]]; then sleep "$INTERVAL"; fi
done
exit 1

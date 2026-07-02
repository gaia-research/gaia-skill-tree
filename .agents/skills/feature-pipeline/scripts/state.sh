#!/usr/bin/env bash
# State management for the feature-pipeline suite.
#
# Usage:
#   state.sh init "<feature>"      — create fresh .fp-state.json
#   state.sh show                  — pretty-print current state
#   state.sh get  <key>            — print single value (raw)
#   state.sh set  <key> <value>    — update one field
#   state.sh push <key> <value>    — append value to a JSON array field
#
# Env:  FP_STATE_FILE  (default: .fp-state.json)

set -euo pipefail
STATE="${FP_STATE_FILE:-.fp-state.json}"
cmd="${1:-show}"; shift || true

_ts() { date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ; }
_require_state() { [[ -f "$STATE" ]] || { echo "No state file found. Run: state.sh init \"<feature>\"" >&2; exit 1; }; }
_require_jq()    { command -v jq &>/dev/null || { echo "jq is required but not installed." >&2; exit 1; }; }

_require_jq

case "$cmd" in
  init)
    feature="${1:?Usage: state.sh init \"<feature>\"}"
    cat > "$STATE" <<JSON
{
  "feature":          "$feature",
  "phase":            1,
  "branch":           null,
  "prNumber":         null,
  "prUrl":            null,
  "issueNumbers":     [],
  "planApproved":     false,
  "reviewCommentUrl": null,
  "ciRound":          0,
  "ciStatus":         "pending",
  "lastUpdated":      "$(_ts)"
}
JSON
    echo "✓ State initialised → $STATE"
    jq '.' "$STATE"
    ;;

  show)
    _require_state
    jq '.' "$STATE"
    ;;

  get)
    _require_state
    key="${1:?Usage: state.sh get <key>}"
    jq -r ".$key // empty" "$STATE"
    ;;

  set)
    _require_state
    key="${1:?Usage: state.sh set <key> <value>}"
    val="${2?Usage: state.sh set <key> <value>}"  # allow empty string
    ts="$(_ts)"
    # Preserve JSON types: booleans, integers, null
    if [[ "$val" == "true" || "$val" == "false" || "$val" == "null" ]]; then
      jq ".$key = $val | .lastUpdated = \"$ts\"" "$STATE" > "$STATE.tmp"
    elif [[ "$val" =~ ^-?[0-9]+$ ]]; then
      jq ".$key = ($val) | .lastUpdated = \"$ts\"" "$STATE" > "$STATE.tmp"
    else
      jq ".$key = \"$val\" | .lastUpdated = \"$ts\"" "$STATE" > "$STATE.tmp"
    fi
    mv "$STATE.tmp" "$STATE"
    echo "✓ $key = $val"
    ;;

  push)
    _require_state
    key="${1:?Usage: state.sh push <key> <value>}"
    val="${2:?Usage: state.sh push <key> <value>}"
    ts="$(_ts)"
    if [[ "$val" =~ ^-?[0-9]+$ ]]; then
      jq ".$key += [$val] | .lastUpdated = \"$ts\"" "$STATE" > "$STATE.tmp"
    else
      jq ".$key += [\"$val\"] | .lastUpdated = \"$ts\"" "$STATE" > "$STATE.tmp"
    fi
    mv "$STATE.tmp" "$STATE"
    echo "✓ pushed $val → $key"
    ;;

  *)
    echo "Unknown command: $cmd" >&2
    echo "Commands: init show get set push" >&2
    exit 1
    ;;
esac

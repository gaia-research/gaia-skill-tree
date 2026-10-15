#!/usr/bin/env bash
# Recoverable feature-pipeline state. This records work; it grants no authority.
# Usage: init <feature> [structured-economy|lean-autonomous|hard-gated]
#        show | get <key> | set <key> <value> | push <key> <value>
#        checkpoint <routine|destructive|design|cli-visual|schema|ontology|
#                    governance|l4|security|provenance|evidence|merge|publish|
#                    external-contact|contract-break|unknown-drift>
# Env: FP_STATE_FILE (default .fp-state.json). Legacy state is hard-gated.
set -euo pipefail
STATE="${FP_STATE_FILE:-.fp-state.json}"
cmd="${1:-show}"
shift || true
_ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
_require_state() { [[ -f "$STATE" ]] || { echo 'No state file; use init.' >&2; exit 1; }; }
command -v jq >/dev/null || { echo 'jq is required.' >&2; exit 1; }

case "$cmd" in
  init)
    feature="${1:?Usage: state.sh init <feature> [mode]}"
    mode="${2:-structured-economy}"
    case "$mode" in structured-economy|lean-autonomous|hard-gated) ;; *) echo 'Invalid mode.' >&2; exit 2;; esac
    [[ ! -e "$STATE" ]] || { echo 'State exists; inspect and resume it.' >&2; exit 1; }
    # noclobber protects an interrupted/concurrent run from losing prior state.
    (set -o noclobber; jq -n --arg feature "$feature" --arg mode "$mode" --arg ts "$(_ts)" \
      '{feature:$feature,mode:$mode,phase:1,branch:null,prNumber:null,prUrl:null,
        issueNumbers:[],findings:[],planApproved:false,reviewCommentUrl:null,
        ciRound:0,ciStatus:"pending",lastUpdated:$ts}' > "$STATE")
    jq . "$STATE"
    ;;
  show) _require_state; jq . "$STATE" ;;
  get)
    _require_state
    key="${1:?Usage: state.sh get <key>}"
    jq -r --arg key "$key" 'if has($key) then .[$key] else empty end' "$STATE"
    ;;
  set|push)
    _require_state
    key="${1:?Usage: state.sh set|push <key> <value>}"
    val="${2?Usage: state.sh set|push <key> <value>}"
    if [[ "$key" == mode ]]; then
      case "$val" in structured-economy|lean-autonomous|hard-gated) ;; *) echo 'Invalid mode.' >&2; exit 2;; esac
    fi
    # Parse literal booleans/null/integers; all other values are opaque strings.
    encoded=$(jq -n --arg val "$val" 'if ($val | test("^(true|false|null|-?(0|[1-9][0-9]*))$")) then ($val|fromjson) else $val end')
    temp=$(mktemp "${STATE}.XXXXXX")
    trap 'rm -f "$temp"' EXIT
    if [[ "$cmd" == set ]]; then
      jq --arg key "$key" --argjson val "$encoded" --arg ts "$(_ts)" \
        '.[$key]=$val | .lastUpdated=$ts' "$STATE" > "$temp"
    else
      jq --arg key "$key" --argjson val "$encoded" --arg ts "$(_ts)" \
        'if (.[$key]|type)!="array" then error("push requires an array") else .[$key]+=[$val] end | .lastUpdated=$ts' "$STATE" > "$temp"
    fi
    mv "$temp" "$STATE"
    ;;
  checkpoint)
    _require_state
    boundary="${1:?Usage: state.sh checkpoint <boundary>}"
    mode=$(jq -er '.mode // "hard-gated"' "$STATE")
    case "$mode" in structured-economy|lean-autonomous|hard-gated) ;; *) echo 'Invalid stored mode.' >&2; exit 2;; esac
    case "$boundary" in
      routine) if [[ "$mode" != hard-gated ]]; then echo 'continue: routine checkpoint'; exit 0; fi ;;
      destructive|design|cli-visual|schema|ontology|governance|l4|security|provenance|evidence|merge|publish|external-contact|contract-break|unknown-drift) ;;
      *) echo 'Unknown boundary; classify under repo policy before advancing.' >&2; exit 2 ;;
    esac
    echo "stop: $boundary (mode=$mode); requires applicable human authority"
    exit 3
    ;;
  *) echo 'Commands: init show get set push checkpoint' >&2; exit 2 ;;
esac

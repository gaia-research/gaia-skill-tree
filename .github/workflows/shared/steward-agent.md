---
description: Shared envelope for Gaia Steward agent workflows (builder and verifier). Engine-agnostic.
network: defaults
safe-outputs:
  jobs:
    steward-outcome:
      description: "Record the single structured outcome of this steward agent run. Call exactly once, last."
      runs-on: ubuntu-latest
      output: "Outcome recorded"
      permissions:
        contents: read
      inputs:
        outcome:
          description: "The outcome as one JSON object string (schema is in your task)."
          required: true
          type: string
      steps:
        - name: Persist outcome
          run: |
            set -euo pipefail
            mkdir -p steward-outcome
            jq -e '[.items[] | select(.type == "steward_outcome")] | length == 1' "$GH_AW_AGENT_OUTPUT" >/dev/null
            jq -r '[.items[] | select(.type == "steward_outcome")][0].outcome' "$GH_AW_AGENT_OUTPUT" | jq -e 'type == "object"' >/dev/null
            jq -r '[.items[] | select(.type == "steward_outcome")][0].outcome' "$GH_AW_AGENT_OUTPUT" > steward-outcome/outcome.json
        - name: Upload outcome
          uses: actions/upload-artifact@v4
          with:
            name: steward-outcome
            path: steward-outcome/outcome.json
            if-no-files-found: error
---

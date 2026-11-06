# Native provider-pin diagnosis and scoped control

## Observed cause (installed pi-subagent 0.8.0)

Read-only inspection found two interacting behaviours:

- `src/policy.ts:239–242` treats an explicit request `fallback_models: []` as absent because it tests filtered length, then inherits the agent/profile fallback list.
- `src/orchestrator.ts:154–158` computes `maxAttempts = 1 + max(maxRetries, fallbacks.length)`. Consequently `max_retries: 0` alone does NOT suppress an inherited nonempty fallback chain.

This explains the recorded OpenAI-primary/Codex-retry incident. No installed source or global configuration was edited. The earlier provider access refusal is not being worked around: the refused WHOLE-review request is not rerun, and no provider change/context stripping is authorized.

## Documented, project-local constraint

A temporary project-local named worker instruction file `.pi/agents/campaign-terra-pinned.md` narrows the assigned route to OpenAI Terra HIGH, with explicit agent-level `fallback_models: []`, `max_retries: 0`, `spawns: false`. This is not a global default, new tool capability, package installation or extension patch. It does not authorize any task or the separate canonical CI-churn edits.

The agent parser preserves the literal empty list. Policy's agent-level nullish fallback selection therefore produces a real empty list instead of inherited defaults. The file is session-operational and retained locally; this report records the durable reasoning.

## Verification actually performed

- Imported the installed parser/policy via already-installed jiti, with no model calls or installs. Resolved the exact helper against the current configured profile defaults. Assertions passed: requested OpenAI Terra HIGH; fallbackModels=[]; maxRetries=0; computed maximumManagedAttempts=1; nested spawning disabled.
- One benign routing-only probe (no repository/review/security content, no tools) returned ROUTE_READY. Actual per-assistant runtime envelope was `provider=openai`, `model=gpt-6.1-terra`, `api=openai-responses`; one assistant response, HIGH journal setting, no fallback response. This is harness evidence, not independent provider-side attestation or a guarantee for every future configuration/version.
- Original package, global config, existing agents and refused-review evidence remain untouched. There is no root workaround that retries a provider refusal.

## Current use and limits

New task070b3ae2 is bounded defensive remediation of cloud F1/F2, with the prior access incident disclosed, in a new worktree from314f. It is NOT the refused whole review. The helper guarantees at most one managed primary attempt under the inspected implementation. If the provider refuses, the task stops; no automatic fallback or refusal retry. Actual implementation-route envelopes must still be collected before trusting its result.

Future installed-version/default changes require re-verification. An upstream fix should distinguish explicit empty overrides from omission and separately bound fallback attempts; no upstream or global patch has been applied here.

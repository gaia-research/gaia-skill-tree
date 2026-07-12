---
name: gaia-curate-chain
description: >-
  Gated curation extension. Runs the canonical Gaia curation core first, then
  adds fixed-topology subagents, deterministic gates, and bounded retries.
  Use for small batches where schema correctness and auditability matter.
version: 2.0.0
argument-hint: "<topic-or-source-to-curate>"
---

# Gaia Curate Chain

This is an extension of `/gaia-curate`, not a second curation methodology.
Read and execute `.agents/skills/gaia-curate/CURATION-CORE.md` first. The core
owns source loading, discovery, generic lookup, generic/named mapping, evidence
capture, proposal design, human review, and mutation boundaries. Keep the core
packet intact; do not reimplement those steps with alternate taxonomy or
 evidence rules.

## Extension workflow

After the core produces an approved preliminary packet:

1. Persist state to `generated-output/curate-chain-state.json` (gitignored).
2. Dispatch fresh subagents for the approved research/design units when
   independent context is valuable.
3. Run deterministic gates between links: packet shape, generic ref resolution,
   evidence URL presence, DAG validity, and `gaia validate`.
4. On failure, route back one link with the concrete failure; allow at most two
   retries per gate.
5. Record the contract version/digest in state. If the core contract changes,
   revalidate mappings and mutation plans before resuming.
6. Perform the approved CLI mutations, regenerate docs, validate, and ship one
   PR.

## State minimum

```json
{
  "contractVersion": "core-v1",
  "corePacket": "generated-output/curation-core-packet.json",
  "link": 1,
  "gates": [],
  "mutations": [],
  "prUrl": null
}
```

## Required gates

```bash
test -s generated-output/curation-core-packet.json
gaia validate
gaia dev docs --check
```

Validate named IDs in preferred `contributor/skill-name` form and resolve
`genericSkillRef` (CLI: `--generic-ref`) against `gaia dev list --generic
--json`. Do not use deprecated `--class`, manual trust values, or duplicate the
core's evidence scoring logic.

## Ship boundary

Use only `gaia dev` mutations. Regenerate with `gaia dev docs`, run
`gaia validate` and `gaia dev docs --check`, then push a single review PR.

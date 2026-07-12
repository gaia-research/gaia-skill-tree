# Gaia Curation Core

This is the canonical preliminary curation contract. `/gaia-curate`, `/gaia-curate-chain`, and `/gaia-curate-dynamic` all begin here. Extension workflows must not restate or override these rules; they may add orchestration, gates, or adversarial review after the core packet is produced.

## Core sequence

1. Read `registry/skill-sources.md` and the canonical registry.
2. Search and inspect candidate upstream implementations. Use specific `blob/<branch>/.../SKILL.md` URLs when available.
3. Run the generic lookup before designing entries:

   ```bash
   gaia dev list --generic --description
   # machine-readable form:
   gaia dev list --generic --json
   ```

4. Map each implementation to an existing generic parent whenever possible.
5. Create a new starless generic only when no suitable vendor-neutral, reusable, falsifiable parent exists.
6. Propose named implementations separately, using preferred IDs in `contributor/skill-name` form and a resolving `genericSkillRef` (CLI spelling: `--generic-ref`).
7. Capture evidence sources and raw source measurements. Do not assign derived trust values or deprecated classes.
8. Present the review table and stop for explicit decisions before mutation.

## Proposal model

| Name | Starless (generic) | Named (`/slash-skill`) | Type | Generic ref | Action |
|---|---|---|---|---|---|
| Capability | existing or proposed generic | — | basic/fusion | — | accept/rename/etc. |
| Implementation | existing generic parent | `/implementation` | named | `contributor/generic-id` | accept/rename/etc. |

A generic row must be vendor-neutral and starless. A named row is a specific implementation and must resolve to an existing generic parent. An upstream slash skill is evidence/attribution, not automatically a new generic.

## Evidence contract

Record source facts, not computed scores:

- `repo-own`: `commits`, `contributors`;
- `github-stars-own`: `stars`, and `skillCountInRepo` when applicable;
- use the specific implementation `blob/` URL where available;
- record evidence type, source URL, provenance, and notes.

Never author `class`, `trustNumber`, `trustMagnitude`, `artifact_score`, or manual A/B/C grades. Gaia computes derived scores and grades.

Example:

```bash
gaia dev evidence contributor/skill-name <blob-url> \
  --type repo-own --commits N --contributors N

gaia dev evidence contributor/skill-name <repo-url> \
  --type github-stars-own --stars N --skill-count-in-repo N
```

Do not pass `--trust` or the deprecated `--class` option.

## Core packet

Extensions should persist or pass a packet containing at least:

```json
{
  "existingIds": [],
  "genericMappings": [],
  "candidates": [],
  "batch": [],
  "decisions": [],
  "evidence": [],
  "contractVersion": "core-v1"
}
```

The packet is preliminary work, not approval. Extensions must preserve its evidence and decisions, then add their own state without silently remapping candidates.

## Mutation boundary

After explicit approval, mutate only through `gaia dev` commands. Validate with `gaia validate`; regenerate with `gaia dev docs` and check with `gaia dev docs --check`. Never hand-edit canonical or generated registry files.

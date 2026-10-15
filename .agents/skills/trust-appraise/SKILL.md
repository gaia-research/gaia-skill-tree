---
name: trust-appraise
description: >
  Dry-run Trust Magnitude for proposed named skills or suites before curation. Use when deciding whether a proposed suite deserves A/S treatment, when checking Fusion Score structural inputs, when comparing repo stars vs suite component counts, or when asked to appraise a candidate before adding it to the registry.
version: "1.1.0"
genericSkillRef: registry-inspection
---

# /trust-appraise

Runs a **non-mutating** Trust Magnitude dry run. Formulas, dedup, inheritance, grade
floors and star gates are **not** restated here. The canonical source is
[`docs/agents/curation-authority-map.md`](../../../docs/agents/curation-authority-map.md),
which is checked against `src/gaia_cli/trustMagnitude.py` by
`tests/test_curation_authority_map.py`.

Two modes:

1. **Registry mode** (`--skill`) appraises an already-curated skill. A `contributor/skill` id
   reads `registry/named/<contributor>/<skill>.md` and resolves its `genericSkillRef`
   against `registry/nodes/`. A bare id reads the generic node. Use it during L4 human
   review to see the real TM and per-row artifact scores before signing off.
2. **Proposal mode** (`--repo`) appraises a proposed suite from live GitHub signals before
   curation. It is the pre-curation companion to `/trust-appraise-all`.

## Usage

```bash
# Appraise one or more curated skills (use during L4 human review)
PYTHONPATH=src python3 scripts/trust_appraise.py \
  --skill rico-favor/implement-with-discernment \
  --skill caioribeiroclw-pixel/evidence-attestation

# Appraise a proposed suite (pre-curation)
PYTHONPATH=src python3 scripts/trust_appraise.py \
  --repo gsd-build/get-shit-done \
  --components 5 \
  --evidence-path docs/INVENTORY.md

# Default suite appraisal set
PYTHONPATH=src python3 scripts/trust_appraise.py

# Machine-readable output
PYTHONPATH=src python3 scripts/trust_appraise.py --skill foo/bar --json
```

## Scope labels: always report them

Every result carries `scope`, `genericResolution` and `totalStatus` (authority map §2):

| Mode | `scope` | `genericResolution` | `totalStatus` |
|---|---|---|---|
| `--repo` proposal | `named-own/proposal` | `not evaluated` | `partial` |
| `--skill` named, generic ref resolves | `effective named` | `resolved` | `final` |
| `--skill` named, generic ref missing from the registry | `named-own` | `not evaluated` | `partial` |
| `--skill` named with no `genericSkillRef` | `effective named` | `not applicable` | `final` |
| `--skill` generic node | `generic` | `not applicable` | `final` |

A `partial` total is **never** the effective named TM. Say "generic: not evaluated", not
"inheritance disallowed". Generic-layer evidence that a skill later inherits still counts,
even when it does not prove implementation usage.

## Proposal-mode metrics and their status

The proposal builds a temporary skill from its own rows only:
- `github-stars-own` at the evidence blob URL
- `repo-own` at the repository root
- a structural `fusion-recipe` row, which scores 0 TM and feeds only the informational Fusion Score

`skillCountInRepo` is recorded and never divides a score. Each collected metric is reported
in `metricClaims` with a `verified` / `reported` / `inferred` / `unknown` status and its
repro command (authority map §5):

- `contributorContributionSum` is the sum of GitHub per-contributor `contributions`. It is
  **not** a count of unique commits. The engine's `repo-own` input field is named `commits`,
  so the proposal fills that input from the sum and labels it `inferred`. Never report it
  as "N commits".
- Repository metrics describe the whole repository. Skill-file installability (a verified
  `links.github` `blob/` URL) is a separate check.

## Important caveat

A high dry-run score is **not** promotion approval. Use this skill to surface evidence
quality and TM bias before L4 human review, never to bypass review. `arxiv` rows with 0
citations score 0 TM whatever their `trustNumber`. `social-signal` rows need verifiable view
counts, and fabricated numbers inflate scores directly. 4★ strictly requires grade A
(TM ≥ 100), and grade S (5★) needs an independent witness. Both rules are in authority map §3.

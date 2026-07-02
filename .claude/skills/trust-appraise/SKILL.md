---
name: trust-appraise
description: >
  Dry-run Trust Magnitude for proposed named skills or suites before curation. Use when deciding whether a proposed suite deserves A/S treatment, when checking fusion-recipe bias, when comparing repo stars vs suite component counts, or when asked to appraise a candidate before adding it to the registry.
version: "1.0.0"
genericSkillRef: registry-inspection
---

# /trust-appraise

Runs a **non-mutating** Trust Magnitude dry run for proposed Gaia suites. This is the pre-curation companion to `/trust-appraise-all`, which inspects already-curated registry entries.

## Usage

```bash
# Default appraisal set used during GSD/Addy suite curation
PYTHONPATH=src python3 scripts/trust_appraise.py

# Appraise one proposed suite
PYTHONPATH=src python3 scripts/trust_appraise.py \
  --repo gsd-build/get-shit-done \
  --components 5 \
  --evidence-path docs/INVENTORY.md

# Machine-readable output
PYTHONPATH=src python3 scripts/trust_appraise.py --json
```

## What it scores

The helper builds a temporary skill object and calls `gaia_cli.trustMagnitude` directly. It includes:

- `github-stars-own` with `skillCountInRepo` so mothership discount applies.
- `repo-own` from live GitHub contributor and contribution counts.
- `fusion-recipe` from the proposed curated component count.

## Important caveat

A high dry-run score is **not** promotion approval. Fusion credit should only count after the components are curated as named origins and independently graded. Use this skill to surface bias before L4 human review, not to bypass review.

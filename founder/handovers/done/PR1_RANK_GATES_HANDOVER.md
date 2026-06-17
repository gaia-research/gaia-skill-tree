# Handover: PR-1 — Gate Skill Ranking on Evidence Grades (#699)

**Type:** Backend / Trust Model  
**Branch:** `feat/rank-gates`  
**Resolves #699**  

## Context
With the new Trust Model (grades S/A/B/C) fully implemented, we need to enforce a gate that ties a skill's general rank progression (e.g., Evolved, Apex) directly to its Overall Trust Grade. Currently, we enforce the ultimate gate (pillar rule) for suite skills, but general rank ascension does not yet strictly require specific evidence grade minimums.

## Objectives
1. **Update `meta.json`**: Define the grade floors required for each rank tier (e.g., reaching Evolved requires an Overall Grade of ≥ B, Apex requires ≥ A).
2. **Update `grading.py`**: Modify the pipeline so that a skill's rank is capped by its Overall Trust Grade during validation and processing.
3. **Graceful Degradation**: Ensure skills that do not meet the evidence requirements are held at their highest allowed rank, rather than causing pipeline failures.

## Definition of Done
- Validation logic correctly blocks/caps rank progression based on `meta.json` thresholds.
- `gaia validate` passes locally.
- Full test suite passes.
- PR resolves `#699`.

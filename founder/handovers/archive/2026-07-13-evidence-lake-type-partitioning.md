# Evidence Lake: Replace Rank Tiers with Evidence-Type Partitions

## Decision

The evidence lake must store and audit raw evidence by evidence type, not by a skill's current star rank. Rank is a derived Trust Magnitude outcome and changes over time; it is not a stable storage partition.

## Problem

The current `tier_1.md` through `tier_6.md` artifacts are stale whenever ranks change. They mix evidence collection with a downstream, mutable classification and create noisy adversarial-audit findings that are unrelated to source quality.

A second gap exists in the intake handoff: an L4-approved intake is routed to `/ev-pipeline`, but the pipeline only compiles collector inputs. It does not materialize an intake's raw source rows into those inputs.

## Target Flow

```text
L4-approved intake
  → evidence seed (skill ID, source URL, claimed evidence type, attribution scope)
  → collector input, partitioned by evidence type
  → collection, source verification, adversarial audit, link validation
  → Trust Magnitude appraisal and derived rank
  → maintainer CLI promotion
```

## Follow-up Scope

1. **Lake scripts**
   - Replace tier-file generation with deterministic evidence-type outputs.
   - Keep a unified index keyed by skill ID and evidence type.
   - Treat TM grade and star rank as report fields calculated at appraisal time only.

2. **Intake handoff**
   - Emit a raw evidence-seed artifact after L4 approval.
   - Do not carry a requested star level, tier, grade, or class as authoritative evidence.
   - Require provenance and attribution scope: implementation-specific, suite-wide, or generic-capability.

3. **Evidence-pipeline skills and docs**
   - Update collection, star verification, adversarial audit, link validation, and pipeline orchestration instructions.
   - Shard adversarial review by evidence type rather than current rank.
   - Mirror every changed skill in `.agents/skills/` and `.claude/skills/`.

4. **Migration**
   - Generate evidence-type artifacts alongside existing tier files temporarily.
   - Update all readers and tests.
   - Remove tier files only after no consumer depends on them.

## Firecrawl Application

For the Firecrawl intake, source rows should distinguish suite-wide evidence (for example, Firecrawl repository adoption) from endpoint-specific evidence (scrape, search, interact, onboarding, research index). A suite-wide source must not be copied as full-strength proof for every component.

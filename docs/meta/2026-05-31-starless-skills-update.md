---
title: "Starless Skills Update"
author: "Marcus Rafael Tiongson, Engineer"
summary: "Generic skill taxonomy refactored as rank-free, with star-based prestige reserved for named implementations."
label: "Schema Migration"
---

## Abstract

Structural refactoring of the generic skill taxonomy to remove rank-based prestige (stars) from canonical skill definitions. Stars now live exclusively on named implementations, reflecting the reality that only attributed contributors have reputational stake. Generic nodes serve as taxonomy and composition anchors—not ranked aspirations.

## Executive Summary

The May 2026 schema migration (`#551`, `#552`) separates prestige concerns from taxonomy concerns. Generic skills (`prompt-optimization`, `code-review`, etc.) are now "starless"—they are pure categorical nodes with no rank. Named skills (`stanfordnlp/dspy`, `pbakaus/impeccable`, etc.) carry the stars; they represent concrete, versioned implementations that can be evaluated and attributed.

### Rationale

**Before**: Generic skills had a `level` field and could be 2★, 3★, 4★. This created three problems:
1. **Ownership ambiguity**: A generic skill's rank suggested some canonical "best" implementation—but who owns that?
2. **Stale rankings**: A generic skill ranked at 3★ could not change when implementations leveled up (or were demoted).
3. **Misaligned UI**: Users saw a skill card for "code-review" at 3★, clicked it, and found multiple implementations at 2★, 4★, 5★—confusing.

**After**: Generic skills are rank-free. Their `level` field is removed. Users see:
- Generic skill card: *"Code Review"* — no stars, just description
- Implementations below: *"anthropic/code-review (4★)"*, *"garrytan/code-review (5★)"*, etc.

Stars reflect real contributor work. Generic nodes reflect shared vocabulary.

## Changes

### Schema Transformation

**Generic Skill Node**
```diff
- "level": "3★",
- "rarity": "common",  # deprecated
  "name": "Code Review",
  "type": "basic",
  "description": "...",
  "prerequisites": ["code-reading", "static-analysis"],
  "derivatives": ["architecture-review"],
```

**Named Skill Node** (unchanged, stars now emphasis)
```yaml
id: pbakaus/impeccable
genericSkillRef: ux-audit
level: 4★  # ← stars live here
...
```

### Affected Files

- **Registry schema** (`registry/schema/`) — Removed `level` from generic skill types
- **Generic skills** (44 nodes across basic/intermediate/advanced/ultimate) — All `level` fields removed
- **Mbtiongson1 named skills** — Reclassified to 2★ (project-local, not production)
- **CLI docs** — Updated to reflect starless generics

### Named Skills Reclassified

The 6 project-local named skills (`mbtiongson1/*`) were reclassified to 2★ to reflect their scope:
- `gaia-audit` — 2★ (internal tool)
- `gaia-curate` — 2★ (internal tool)
- `gaia-docs-sync` — 2★ (internal tool)
- `gaia-integrity` — 2★ (internal tool)
- `gaia-triage` — 2★ (internal tool)
- `gaia-draft-curate` — 2★ (internal tool)

**Rationale**: These skills serve Gaia's internal workflows, not external agents. They belong at 2★ (project scope) rather than 4-5★ (universal).

## Vocabulary & Taxonomy

### Starless = Rank-Free Generic

A generic skill with no `level` field. It is:
- **Taxonomic anchor**: Pulls named implementations under a shared category
- **Composition building block**: Other skills can list it as prerequisite/derivative
- **Neutral vocabulary**: No judgment about quality; purely categorical

### Star System (Named Only)

Stars now strictly measure **named implementations**:
- **1★** — Prototype, proof-of-concept (unverified)
- **2★** — Production-ready in specific context (tested, may be narrow scope)
- **3★** — Polished, general-purpose implementation (evidence-backed, stable)
- **4★** — Expert-level or deeply integrated skill (A-class evidence, significant scope)
- **5★** — Transcendent, composable ultimate (rare; usually multi-contributor capstone)
- **6★** — Reserved for future suites

### Retired Term: Rarity

The `rarity` field (`common`, `uncommon`, `rare`, `epic`, `legendary`) is deprecated and being phased out. It served no meaningful purpose once stars migrated to named skills.

## UI Implications

### Search & Discovery

**Before**: Users saw generic skill cards with stars. Clicking led to a "best of" carousel.

**After**: Generic skill cards are star-free. Implementation cards show individual ratings:
```
Prompt Optimization (generic skill)
├─ stanfordnlp/dspy  ★★★★
├─ anthropic/prompt-tuning  ★★★
├─ openai/few-shot-learning  ★★
└─ more...
```

### Skill Graph

Generic skills remain as nodes. Named skills attach beneath them. No rank confusion.

### Rankings & Leaderboards

Sorting and filtering now only apply to **named skills** (which have stars). Generic skills appear in pure alphabetic or dependency-based order.

## Migration Notes

### For Contributors

When adding a new skill:
1. If it's a **generic concept**, submit a generic node (no level)
2. If it's a **concrete implementation**, create a named skill under the generic and assign your 2-4★ rating
3. Do not add stars to generic nodes

### For Curation

- Use `gaia dev add "Name" --type basic` for generics (stars auto-defaulted to none)
- Use `gaia dev add "Name" --type basic --level 3★` for named skills (stars required)

### Backward Compatibility

- Existing generic skills' deprecated `level` and `rarity` fields are hidden from UI but preserved in JSON for audit trail
- Named skills unaffected; stars unchanged

## Validation

✅ **Schema passes all checks:**
- 44 generic skills confirmed starless
- 220+ named skills retain stars
- Zero generic-to-named rank conflicts
- Derivative chains validated (no circular dependencies)

## References

[1] Tiongson, M. R. (2026). *Starless Skills Update*. Gaia Skill Tree Registry.  
[2] Tiongson, M. R. (2026). Schema Refactor: Rank-Free Generics. PR #551.  
[3] Tiongson, M. R. (2026). Taxonomy Redesign (UI & Docs). PR #552.  
[4] Meta. (2025). Star System & Prestige Rules. META.md.

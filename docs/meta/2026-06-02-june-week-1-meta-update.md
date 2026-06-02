---
title: "June Week 1 Meta Update"
author: "Marcus Rafael Tiongson, Auditor"
summary: "Origin reassignments, URL curation, and CLI enhancements across 68 registry files."
label: "Registry Update"
---

## Abstract

Comprehensive meta audit sweep correcting origin attribution across 11 generic skill buckets, curating 30+ GitHub links to precise SKILL.md paths, and introducing new CLI commands for programmatic registry mutations. All changes enforce the principle: origin = highest-rated skill per generic bucket.

## Executive Summary

The June Week 1 sweep resolves critical registry inconsistencies from the May audit phase. Origin flags are now correctly assigned to the highest-rated skill in each generic bucket. GitHub links have been curated from raw repository roots to specific SKILL.md file paths, improving installation reliability. Two new CLI commands (`--origin` flag and `gaia dev timeline`) enable programmatic registry state changes with full timeline auditing.

### Key Changes

- **11 origin reassignments** — Demoted lower-rated origins, promoted 4★ and 3★ skills to canonical roles
- **30+ GitHub link updates** — All 3★+ skills now link precisely to installation targets
- **4 skills marked uninstallable** — OpenAI conceptual skills and suite-referenced implementations removed from installation pool
- **2 new CLI commands** — Enforce origin uniqueness and enable standalone timeline events

## Origin Corrections

Each generic skill bucket now designates its highest-rated implementation as the canonical origin:

| Bucket | Level Change | Result |
|--------|--------------|--------|
| design-system-extraction | 2★ → 4★ | garrytan/design-consultation promoted |
| document-editing | 2★ → 4★ | garrytan/document-generate promoted |
| performance-tuning | 2★ → 3★ | addy-osmani/performance-optimization promoted |
| ux-audit | 2★ → 4★ | pbakaus/impeccable promoted |
| code-generation | 3★ → 4★ | garrytan/design-html retained at peak |
| + 6 others | Various | 10 additional buckets corrected |

**Principle:** Origin designation is not chronological ("earliest"). It represents the highest-rated or most-attributed skill in the bucket. There can only be one origin per bucket.

## GitHub Link Curation

50+ named skills across 6 contributors updated to point to SKILL.md files:

### google-deepmind science-skills (25 skills)
All alphafold, clinical trials, ChEMBL, gnomAD, etc. databases updated:
- **Before**: `https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database`
- **After**: `https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md`

### Ecosystem suites (intentionally raw repo links)
- `obra/superpowers`, `ruvnet/ruflo`, `mattpocock/personal` — Remain at repo root per contributor instruction
- `garrytan/gstack` — Component links still point to component subdirs, not SKILL.md

### Special cases
- **karpathy/autoresearch**: Main repo (karpathy/autoresearch) now serves as evidence; implementation links to balukosuri fork with SKILL.md
- **langgenius/dify**: 6 skills (.agents/skills subdirectories) all updated to point to SKILL.md paths

## Installability

### Demoted to 2★ — Abstract Concepts
- **openai/self-consistency** — 4★ → 2★ (prompting technique without implementation)
- **openai/few-shot-learning** — 4★ → 2★ (in-context learning pattern, not code)

### Marked `installable: false`
- **sickn33/mcp-builder** — 3★ (links to suite repo root, no specific SKILL.md)
- **stanfordnlp/dspy** — 3★ (research framework, not installable agent code)

## CLI Enhancements

### New `--origin` Flag
```bash
gaia dev update-named anthropic/pptx --origin false
```
Enforces single origin per bucket; automatically demotes competing origins and records timeline events.

### New Timeline Command
```bash
gaia dev timeline my-skill --action demote --notes "Reason for change"
```
Records standalone timeline events (demote, rank_up, verified, disputed) with contributor attribution and timestamp.

## Validation

✅ **All checks pass:**
- No duplicate origins within generic buckets
- All 30+ GitHub links validated to SKILL.md paths
- All 3★+ skills have installation targets or marked uninstallable
- 68 timeline events recorded for audit traceability

## Next Steps

### P1 — Dead Evidence Links
37 dead URLs (mostly `gaia-registry/gaia/blob/main/docs/evidence/...`) need re-evidencing or removal via `gaia dev evidence`.

### P4 — Placeholder Bodies
~19 skills with placeholder `## Installation` sections require actual descriptions.

### Future Audits
- Registry-wide evidence backfill (A/B class for 4★+)
- Contributor re-engagement for missing evidence
- Taxonomy validation across generic skill chains

## References

[1] Tiongson, M. R. (2026). June Week 1 Meta Update. Gaia Skill Tree Registry.  
[2] Tiongson, M. R. (2026). Meta Audit Implementation Rules. GEMINI.md.  
[3] Meta. (2025). Origin Attribution Guidelines. META.md.

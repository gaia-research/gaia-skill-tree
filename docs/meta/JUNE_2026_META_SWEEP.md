# June 2026 Meta Audit Sweep

**Date**: 2026-06-02  
**Branch**: review/meta/sweep (PR #555)  
**Status**: ✅ Complete

## Summary

Comprehensive audit sweep addressing registry taxonomy, URL curation, and origin attribution across 68 files. Resolved 11 mis-attributed origin claims, updated 30+ GitHub links to precise SKILL.md paths, and demoted 2 abstract OpenAI concepts marked uninstallable.

## Changes

### 1. CLI Enhancements

**New Flags & Commands:**
- `gaia dev update-named <skill> --origin true|false` — Enforce single origin per generic bucket with automatic demotion of competing origins
- `gaia dev timeline <id> --action <action> --notes "..."` — Standalone timeline event recording (demote, rank_up, verified, disputed, etc.)

**Documentation Updates:**
- `.agents/skills/gaia-meta-audit/SKILL.md` — Clarified CLI mutation capabilities
- `GEMINI.md` — Added "Meta Audit Implementation Rules" and "Tooling Strategy" sections

### 2. Origin Reassignments

Corrected 11 mis-attributed origin claims by reassigning to the highest-rated skill per generic bucket:

| Bucket | Demoted (was origin:true) | Promoted (now origin:true) | Levels |
|--------|--------------------------|---------------------------|--------|
| design-system-extraction | Manavarya09/design-extract (2★) | garrytan/design-consultation (4★) | ↑2 |
| document-editing | anthropic/pptx (2★) | garrytan/document-generate (4★) | ↑2 |
| document-editing | mattpocock/edit-article (2★) | garrytan/document-generate (4★) | ↑2 |
| performance-tuning | ruvnet/performance-analysis (2★) | addy-osmani/performance-optimization (3★) | ↑1 |
| ux-audit | martin-stepanoski/nielsen-heuristics-audit (2★) | pbakaus/impeccable (4★) | ↑2 |
| code-generation | garrytan/design-html (3★) | garrytan/design-html (4★) | ↑1 |
| + 5 others | Various 2-3★ | Various 3-4★ | ↑1-2 |

**Principle Applied:** Origin = highest-rated or most-attributed skill in generic bucket. There can only be one origin per bucket.

### 3. GitHub Link Curation

Updated 30+ named skills to point to precise `SKILL.md` files:

**Examples:**
- `bradautomates/claude-video`: `.../claude-video` → `.../claude-video/blob/main/SKILL.md`
- `pbakaus/impeccable`: `.../impeccable` → `.../impeccable/blob/main/.agents/skills/impeccable/SKILL.md`
- **google-deepmind science-skills** (25 skills): All updated from directory roots to `/blob/main/skills/<skill>/SKILL.md`
- `karpathy/autoresearch`: Main repo now evidence; implementation link updated to `balukosuri` fork with SKILL.md

**Exception:** Ecosystem suites (`obra/superpowers`, `ruvnet/ruflo`, `mattpocock` personal suite) intentionally link to raw repo URLs per contributor instruction.

### 4. Demotion & Installability

**Abstract Concepts Demoted to 2★ with `installable: false`:**
- `openai/self-consistency` — 4★ → 2★ (prompting technique, no code)
- `openai/few-shot-learning` — 4★ → 2★ (in-context learning, no code)
- `sickn33/mcp-builder` — 3★ marked `installable: false` (links to suite, no specific install)
- `stanfordnlp/dspy` — 3★ marked `installable: false` (research framework, not deployable)

### 5. Issues Resolved

**P1: Dead Evidence URLs**
- 37 dead links (mostly `gaia-registry/gaia/blob/main/docs/evidence/...`) identified
- Action: Re-evidence or remove via `gaia dev evidence` or `gaia dev calibrate`

**P1: Missing `links.github` (3★+ skills)**
- `stanfordnlp/dspy` — Marked uninstallable ✓
- `sickn33/mcp-builder` — Marked uninstallable ✓

**P1: Link Casing / Missing SKILL.md**
- All 30+ affected skills updated ✓

**P2: Mis-attributed Origins**
- All 11 corrected per highest-rated rule ✓

**P4: Placeholder Bodies**
- ~19 skills with placeholder `## Installation` bodies — Flagged in AUDIT-sweep.md for backfill

## Validation

✅ All validation checks pass:
- No duplicate origins within generic buckets
- All origin flags point to highest-rated skills
- All 3★+ skills either have SKILL.md links or marked `installable: false`
- Timeline events recorded for all origin changes

## Files Modified

- **68 files changed** (+340, -100)
- **Registry**: 54 named skill files + 2 generic skills
- **CLI**: `dev.py`, `main.py`
- **Documentation**: `.agents/skills/gaia-meta-audit/SKILL.md`, `GEMINI.md`, `AUDIT-sweep.md`

## Next Steps

1. **Dead Evidence Links (P1)**: Run `gaia dev evidence` to backfill or remove 37 dead links
2. **Placeholder Bodies (P4)**: Backfill descriptions for ~19 skills with placeholder installation sections
3. **Evidence Backfill**: Contribute A/B class evidence for high-level skills currently lacking proof

## References

- **PR**: #555 (review/meta/sweep)
- **Audit Output**: AUDIT-sweep.md (root)
- **Rules**: META.md § "Taxonomy & Taxonomy", GEMINI.md § "Meta Audit Implementation Rules"

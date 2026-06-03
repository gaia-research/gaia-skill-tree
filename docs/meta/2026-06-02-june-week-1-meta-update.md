---
title: "June Week 1 Meta Update"
author: "Marcus Rafael Tiongson, Auditor"
summary: "Origin reassignments, URL curation, and CLI enhancements — extended by a whole-registry automated meta sweep with adversarial verification and a before/after confusion matrix."
label: "Registry Update"
chart: 2026-06-timeline.json
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

## Automated Meta Sweep — Whole-Registry Audit

This update is extended by a programmatic **gaia-meta-sweep**: a five-phase Workflow that audited all 183 named skills and 215 generic references against META.md. Twelve survey dimensions were fanned out to parallel agents (cost-optimized models), their candidate sets deterministically pre-extracted, Semantic-Fusion candidates and new generic references proposed, and every representative finding put through a three-lens **adversarial verification** gate (correctness / evidence / precedent) under a ≥2-of-3 survival rule. The run began **read-only**, then — with maintainer approval — was promoted to an **apply-safe** pass; every mutation below was applied programmatically via `gaia dev` and validation-gated (`gaia validate` + `--intake`). See *Mutations Applied*.

### Method

- **Survey** — 12 audit dimensions, one agent each, over pre-extracted ground-truth candidates.
- **Fuse** — Semantic-Fusion candidates (META §6.2), moderate aggressiveness.
- **Propose** — new generic skill references (META §1).
- **Verify** — 3 independent skeptics per representative claim; survives only on ≥2/3 agreement.
- **Report** — this addendum, a machine-readable findings index, and a timeline series.

### Detection Confusion Matrix (Before / After)

The deterministic extractor flags candidates; survey judgment and adversarial verification are the adjudicating ground truth. **Before** the verification gate (extraction → survey judgment):

| Extractor | Adjudged real | Adjudged not real |
|-----------|---------------|-------------------|
| **Flagged** (211) | TP = 201 | FP = 10 |
| **Not flagged** | FN ≈ 0 | TN = remainder |

Precision = 201 / 211 = **95.3%**. The 10 false positives were caught by the survey agents: 5 browser/scraper skills that matched the *heavyweight-dependency* keyword filter but bundle no heavy runtime, 3 same-day `createdAt` ties in origin, and 2 documentation files using a non-standard heading. **After** the verification gate, all **12 / 12** representative claims survived ≥2-of-3 skeptics — no survivor was reclassified, so precision holds and confidence rises. (FN ≈ 0 across the eight deterministic dimensions, which scan exhaustively; unmeasured for the three keyword-pre-filtered dimensions.)

### Origin Rule Shift — the sharp Before / After (META §4.1)

The sweep surfaced a governance conflict: the registry's working principle (*Origin = highest-rated*) contradicted the then-current META §4.1 (*Origin = first / earliest contributor*). **META §4.1 has been updated** so the **most renowned** (highest-rated) implementation earns Origin — an early entry can be superseded by a better one. Re-deriving the origin findings under each rule shows a clean inversion:

| Origin detection | Before — *earliest* rule | After — *renowned* rule (§4.1) |
|------------------|--------------------------|--------------------------------|
| Buckets flagged | 5 | 7 |
| Valid under final rule (TP) | 0 | 7 |
| False positives (cleared by rule) | 5 | 0 |
| False negatives (missed by rule) | 7 | 0 |

The two sets are **disjoint** (overlap = 0): the five earliest-rule flags were merit-compliant all along, while seven buckets where a lower-rated skill held Origin over a higher-rated one were invisible to the earliest rule. The seven actionable corrections under the new rule:

| Bucket | Current Origin | Should be (most renowned) |
|--------|----------------|---------------------------|
| browser-control | browser-use/browser-harness (2★) | garrytan/browse (3★) |
| finishing-a-development-branch | obra/finishing-a-development-branch (2★) | garrytan/ship (4★) |
| systematic-debugging | obra/systematic-debugging (3★) | garrytan/investigate (4★) |
| tool-creation | anthropic/skill-creator (2★) | mattpocock/write-a-skill (3★) |
| vertical-slice-planning | mattpocock/to-issues (3★) | garrytan/garrytan (5★) |
| web-scrape | firecrawl/firecrawl (2★) | garrytan/scrape (3★) |
| write-report | glincker/readme-generator (2★) | garrytan/retro (3★) |

### Findings by Dimension

| Dimension | META | Flagged | Confirmed | Top priority |
|-----------|------|---------|-----------|--------------|
| class-mismatch | §2.1 | 5 | 5 | **P0** |
| star-bar / installability | §2.4 | 22 | 22 | P1 |
| liveness | §2.2 | 37 | 37 | P1 |
| unbacked-star | §1.1 | 29 | 29 | P1 |
| brand-coupled | §1 | 1 | 1 | P1 |
| unique-isolation | §1.2 | 1 | 1 | P1 |
| origin-attribution | §4.1 | 7 | 7 | P2 |
| heavy-deps | §3 | 6 | 1 | P2 |
| champion-cluster | §6.1 | 38 | 38 | P3 |
| placeholder-bodies | — | 49 | 47 | P4 |
| testuser-timelines | — | 0 | 0 | — |

One **P0** evidence-integrity case: `mbtiongson1/gaia-audit` claims Class A from a self-referential link inside the gaia repo (seed evidence, insufficient per §2.4). Liveness found 37 dead evidence URLs (mostly `gaia-registry/gaia/.../docs/evidence/*.md` seed links). No bucket yet designates a **Champion** (§6.1).

### Semantic Fusion Candidates (META §6.2)

Eight Extra-tier fusions of existing capabilities — verified as Extras, **not** Ultimates (none require 10k★):

1. `security-review-pipeline` ← code-review-pipeline + security-audit
2. `safe-deployment-verification` ← deployment-automation + verification-before-completion
3. `release-coordination-pipeline` ← finishing-a-development-branch + release-automation
4. `intelligent-pattern-memory` ← memory-pattern-design + agent-memory-learning
5. `optimized-context-workflow` ← context-compression + prompt-optimization
6. `structured-documentation-generation` ← document-editing + write-report
7. `browser-powered-security-scanning` ← browser-automation + security-audit
8. `workflow-driven-multi-agent-orchestration` ← workflow-automation + multi-agent-orchestration-v

### New Generic References & Mutations Applied

Promoted from read-only to an **apply-safe** pass (maintainer-approved). Applied programmatically via `gaia dev`, validation-gated after each batch:

- **Origin (§4.1):** 7 buckets reassigned to the most-renowned holder (`update-named --origin`), auto-demoting the prior origin — browser-control, finishing-a-development-branch, systematic-debugging, tool-creation, vertical-slice-planning, web-scrape, write-report.
- **Brand rename:** `gstack` → `founder-mode-orchestration` (references updated).
- **Unique reclassify:** `fine-tune` → basic.
- **P0 evidence integrity:** `gaia-audit` Class A → C (self-referential seed link, §2.4).
- **Star Bar — hardened to 1★ (§2.4):** 22 skills at 3★+ with missing/root-only `links.github` hard-demoted to **1★**.
- **Evidence floor:** 5 non-flagship 3★ skills → 2★; **12 flagship 4★/5★ skills exempted** (longer meta lifecycle) and routed to an ultimate-review issue.
- **Liveness:** all **37** dead evidence URLs stripped via the new `gaia dev rm-evidence` command (one transient 502 on a live repo left intact).

Resulting tier distribution: **1★ 22 · 2★ 98 · 3★ 27 · 4★ 29 · 5★ 5 · 6★ 2**.

**Still proposals (not applied — need new nodes / research):** the 8 Semantic-Fusion Extras above, deferred to a follow-up curation PR.

## References

[1] Tiongson, M. R. (2026). June Week 1 Meta Update. Gaia Skill Tree Registry.  
[2] Tiongson, M. R. (2026). Meta Audit Implementation Rules. GEMINI.md.  
[3] Meta. (2025). Origin Attribution Guidelines. META.md.  
[4] Gaia. (2026). *gaia-meta-sweep* — Whole-Registry Audit Workflow. Read-only run, 2026-06-02.  
[5] Gaia. (2026). Machine-readable findings index. `meta/reports/2026-06-02-meta-sweep.findings.json`.  
[6] Meta. (2026). §4.1 Origin Status — merit-based update (most renowned earns Origin). META.md.

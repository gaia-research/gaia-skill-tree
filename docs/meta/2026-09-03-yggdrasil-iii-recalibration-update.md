---
title: "Yggdrasil III Integrity Shift: Purging Imposter Aggregators, Enforcing the Logarithmic Adoption Curve, and Restoring the Legitimate Leaderboard"
author: "Gaia Research"
date: "2026-09-04"
summary: "Following a forensic audit of 339 named skills, Gaia has purged 12 non-skill and imposter entries (including K-Dense-AI's library squats and paper-only stubs), patched sub-suite component cap evasions, enacted a logarithmic adoption curve capped at 175 TM, and restored a clean, legitimate leaderboard."
abstract: |
  This report details the registry integrity sweep following the ratification of
  Issue #1705 (Logarithmic Diminishing Returns) and Issue #1706 (Registry Recalibration).
  An exhaustive audit of all 339 named skills surfaced systemic provenance distortions:
  aggregator monorepos squatting canonical package names (e.g. K-Dense-AI claiming 41k
  stars on standard Python libraries), pure academic prompting papers lacking code,
  closed commercial SaaS products, and sub-suites evading component adoption caps.
  Gaia executed an uncompromising remediation: 12 non-skill entities were expunged,
  unearned monorepo star rows and historical database citations stripped, Star Bar 404
  violations demoted to 1★, and the suite component cap engine patched. Ingesting 22
  fresh, grounded evidence rows across legitimate 4★ skills produced a clean, tamper-proof
  leaderboard topped by genuine agent capabilities.
label: "Meta Shift"
---

## Abstract

On 2026-09-04, Gaia completed a comprehensive forensic audit and integrity remediation
across the entire 339 named-skill registry. Prompted by the discovery of aggregator
imposters siphoning repository stars to monopolize top leaderboard positions, this
pass audited provenance, code existence, and evidence validity for every entry in
`registry/named/`.

The remediation purged 12 non-skill entities (abstract prompting papers without code,
closed commercial SaaS, awesome-list stubs, and software libraries), stripped 98+
contaminated evidence rows (including 35 historical database consortium papers from
Google DeepMind wrappers and 41k-star monorepo rows from K-Dense-AI), patched engine
sub-suite cap evasions, enforced Star Bar 404 demotions, and recalibrated Trust
Magnitude across 280 active named skills using the newly ratified logarithmic
adoption curve.

## 1. The Imposter Aggregator Pattern ("K-Dense AI")

The most severe integrity hazard uncovered was the aggregator/directory imposter pattern:
an entity creates a repository containing thin wrappers around third-party open-source
software libraries, squats on canonical tool namespaces, and attributes the entire
monorepo's accumulated star count to each individual stub.

In the case of `k-dense-ai/*`, ten separate skill files (`transformers`, `qiskit`,
`pytorch-lightning`, `rdkit`, `scanpy`, `scvi-tools`, `stable-baselines3`,
`torch-geometric`, `deepchem`, and `pymc`) were registered claiming 41,201 GitHub
repository stars each. None of these entries contained substantive agent skill
workflows; their markdown bodies were empty template stubs (`## Installation\nAdd installation instructions here.`).
By siphoning 41k stars individually, they occupied ranks #2, #4, #5, and #18 on the
global leaderboard, displacing genuine creator tools.

All ten `k-dense-ai` stubs were stripped of the monorepo stars, demoted to 1★, and
flagged as directory prompt wrappers.

## 2. Purging Non-Skill Entities

Agent skills must represent falsifiable, installable instructions or workflows for an
autonomous LLM agent (`META.md` §1). Entities that do not meet this standard have been
expunged from the registry:

| Entity ID | Nature of Entity | Reason for Removal |
|---|---|---|
| `openai/few-shot-learning` | Academic paper (Brown 2020) | No code, no `SKILL.md`, `installable: false` |
| `openai/self-consistency` | Academic paper (Wang 2022) | Google Research paper falsely credited to OpenAI |
| `devin-ai/autonomous-swe` | Commercial SaaS product | Closed proprietary service (`cognition-labs/devin` 404) |
| `stanfordnlp/dspy` | Software library | Python framework (`pip install dspy-ai`), not an agent skill |
| `google-deepmind/science_skills_common` | Python helper package | Explicit frontmatter note: "Not a standalone agent skill" |
| `huggingface/semantic-cache` | Third-party cache tool | Points to Ant Group `codefuse-ai/ModelCache`; no HF link |
| `getagentseal/codeburn` | Desktop telemetry CLI | Standalone npm application (`npx codeburn`), not an agent skill |
| `changkun/plan-decompose-gh-wallfacer` | Monolithic application | Standalone Go service, not an installable skill |
| `Taoidle/plan-decompose-gh-plan-cascade` | Monolithic application | Standalone TypeScript service, not an installable skill |
| `yundu-ai/mcp-tool-developer` | Phantom handle | GitHub user `yundu-ai` returns HTTP 404 |
| `rico-favor/implement-with-discernment` | Circular fork | Points to personal fork of `gaia-skill-tree` itself |

In addition, `karpathy/autoresearch-universal` was reattributed to its true community
author, `balukosuri/autoresearch-universal`, ending false attribution to Andrej Karpathy.

## 3. Evidence Lake Decontamination

Reviewers had previously admitted external citations and internal artifacts as Grade S/A
evidence. These rows were audited and stripped:

- **Google DeepMind Consortium Papers (35 rows stripped)**: Historical database
  foundation papers from 20 to 30 years ago (e.g. 2000 PDB paper with 10k citations,
  2001 dbSNP paper with 7k citations) and public homepages (`pubmed.ncbi.nlm.nih.gov`,
  `arxiv.org/about`) were incorrectly classified as Grade S/A peer reviews for agent
  wrappers. Astral's 51,000-star `astral-sh/uv` repository was similarly stripped from
  `google-deepmind/uv`.
- **Academic Paper Hijacking**: Unrelated papers cited as peer review were removed from
  `anthropic/skill-creator` (Princeton ToolMaker), `pbakaus/impeccable` (arXiv:2411.01606),
  `upsonic/unittest-generator` (UMass CoverUp), `martin-stepanoski/nielsen-heuristics-audit`
  (1994 NN/g article), and `safishamsi/graphify` (CodexGraph).
- **Firecrawl Core Engine Star Attribution**: Stripped 176k stars from Firecrawl's core
  C++/TS engine that were incorrectly applied to `firecrawl/skills` (a 98-star repository),
  and removed an unverified marketing blog benchmark from `firecrawl-research-index`.

## 4. Engine Hardening: The Sub-Suite Component Cap

Under Gaia governance, member skills inside a suite inherit a baseline from the parent
suite repository, capped at **50.0 TM per component** (`META.md` §3).

Forensic analysis revealed that several suites evaded this cap by setting `suiteRef` to
intermediate sub-categories (e.g. `garrytan/cso` setting `suiteRef: garrytan/garrytan`
instead of `garrytan/gstack`, and `mattpocock/*` setting `suiteRef: mattpocock/engineering`).
Because `_githubRepositoryFromRow` did not match the intermediate name, the engine
failed to apply the cap, allowing component skills to inflate up to 286.0 TM.

`src/gaia_cli/trustMagnitude.py` was patched with canonical root suite mappings
(`CANONICAL_ROOT_SUITES`) and owner-level reconciliation. Now, all component skills
belonging to `garrytan/gstack`, `mattpocock/skills`, `addy-osmani/agent-skills`,
`ruvnet/ruflo`, and `firecrawl/firecrawl` are strictly capped at 50.0 TM for suite-level
adoption, while component-specific evidence remains uncapped.

## 5. Logarithmic Diminishing-Returns Adoption Formula (Issue #1705)

The linear repository-star adoption formula was replaced with the logarithmic
diminishing-returns curve:

$$\text{adoptionScore} = \min\left(175.0,\; 35.0 \times \log_{10}\left(\max\left(1.0,\; \frac{\text{stars}}{10.0}\right)\right)\right)$$

By capping `github-stars-own` at 175.0 TM (strictly below the 250.0 TM Grade S floor),
adoption alone can no longer satisfy Grade S. An independent witness (objective
benchmark result, verifier attestation, or Grade A peer review) is mandatory to cross
into Grade S.

## 6. Grounded Evidence Ingestion Across 4★ Flagships

To anchor legitimate creators, 22 verified evidence rows were ingested across four
canonical partitions (`evidence/by-type/`):
- `dietrichgebert/ponytail` (124k stars, verified video demo)
- `mvanhorn/last30days` (61k stars, 1,150 commits, verified video demo)
- `ayghri/i-have-adhd` (27k stars, video/social engagement)
- `leonxlnx/taste-skill` (84k stars, verified adoption)
- `gsd-build/get-shit-done` (64k stars, multi-phase agent workflow)
- `anthropics/brand-guidelines` (verified enterprise style system)

## 7. The Legitimate Leaderboard

Following full recalibration across 280 named skills, the restored leaderboard is
topped by authentic, verified agent skills:

| Rank | Skill ID | TM | Grade | Level | Lineage / Provenance |
|:---:|---|:---:|:---:|:---:|---|
| **1** | `mattpocock/skills` | 233.42 | A | 5★ | Suite Capstone (46 tools) |
| **2** | `nextlevelbuilder/ui-ux-pro-max` | 226.50 | A | 5★ | 124k-star design engine, academic paper |
| **3** | `garrytan/gstack` | 225.66 | A | 5★ | Suite Capstone (YC Founder tools) |
| **4** | `dietrichgebert/ponytail` | 221.96 | A | 4★ | 124k-star video automation |
| **5** | `obra/superpowers` | 220.81 | A | 5★ | Suite Capstone (Core agent disciplines) |
| **6** | `mvanhorn/last30days` | 205.15 | A | 4★ | 61k-star research tool |
| **7** | `addy-osmani/code-simplification` | 190.00 | A | 5★ | Clean adoption + HumanEval benchmark |
| **8** | `anthropics/brand-guidelines` | 184.32 | A | 4★ | Official Anthropic guidelines |
| **9** | `addy-osmani/agent-skills` | 174.62 | A | 5★ | Suite Capstone (Engineering workflows) |
| **10** | `ruvnet/ruflo` | 174.59 | A | 5★ | Suite Capstone (Flow Nexus orchestration) |
| **11** | `leonxlnx/taste-skill` | 172.43 | A | 4★ | 84k-star design curation |
| **12** | `safishamsi/graphify` | 171.88 | A | 5★ | Knowledge-graph engine |
| **13** | `gsd-build/get-shit-done` | 169.36 | A | 4★ | 64k-star planning framework |
| **14** | `pbakaus/impeccable` | 169.34 | A | 5★ | Frontend design system |
| **15** | `vercel-labs/vercel-react-best-practices` | 162.66 | A | 4★ | Official Vercel Labs practices |

## Conclusion & Governance Invariants

The Yggdrasil III integrity shift cements three non-negotiable registry invariants:
1. **Agent Skills Only**: Academic concepts without code, closed SaaS services, and
   raw Python libraries cannot be admitted as named skills.
2. **No Monorepo Laundering**: Aggregators cannot project whole-repository stars onto
   individual prompt stubs.
3. **No S Grade Without an Independent Witness**: High star counts alone top out at
   175.0 TM (Grade A). Grade S requires an objective, verified external witness.

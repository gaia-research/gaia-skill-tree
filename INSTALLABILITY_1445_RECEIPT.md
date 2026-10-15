# Installability Repair Receipt — Registry Slice #1445

**Date:** 2026-10-09  
**Slice:** #1445 (Installability Repair & Link Sanitation)  
**Branch:** `review/meta/1445-installability-repair`  
**Base commit:** `9dae8fcda` (`chore: release v8.19.0 [skip-gen]`)  
**Operator Identity:** `nova-gaia <297571362+nova-gaia@users.noreply.github.com>`  

---

## 1. Executive Summary

This receipt documents the resolution of registry slice #1445. Following the historical founder plan (`founder/handovers/2026-08-05-plan-1445-links-github.md`), fresh upstream source evidence was audited from `generated-output/evidence/1445/`.

All mutations were performed strictly via CLI (`gaia dev rename` and `gaia dev update-named`) using branch-local `PYTHONPATH=src` under Verifier override authorization (`GAIA_OPERATOR_OVERRIDE=1`).

Key actions taken:
1. **Verified Relinks (3 skills):**
   - `panniantong/agent-reach` relinked to `https://github.com/Panniantong/Agent-Reach/blob/main/agent_reach/skill/SKILL.md`.
   - `gooseworks/notte-browser` relinked to `https://github.com/gooseworks-ai/goose-skills/blob/main/skills/research-tools/capabilities/browser-automation-notte/SKILL.md`.
   - `yonatangross/orchestkit-rag` relinked to `https://github.com/yonatangross/orchestkit/blob/main/plugins/ork/skills/rag-retrieval/SKILL.md`.
2. **Issue #1446 Option A Renames (2 skills):**
   - `gooseworks/notte-browser` -> `gooseworks/browser-automation-notte` (matches upstream directory and `name: browser-automation-notte`).
   - `yonatangross/orchestkit-rag` -> `yonatangross/rag-retrieval` (matches upstream directory and `name: rag-retrieval`).
3. **GSD Suite Components Investigation & Relink/Rename (5 skills):**
   - All five `gsd-build` suite components now have discoverable upstream `skills/gsd-<slug>/SKILL.md` in `open-gsd/gsd-core` on branch `next`.
   - Verified that all five manifests match their canonical capabilities.
   - Renamed `gsd-build/<slug>` -> `gsd-build/gsd-<slug>` via CLI to match the upstream discoverable skill directory.
   - Relinked each to `https://github.com/open-gsd/gsd-core/blob/next/skills/gsd-<slug>/SKILL.md`.
   - Accurately documented the external `@opengsd/gsd-core` (`~/.claude/gsd-core`) runtime prerequisite in `## Installation` via CLI (`--installation-file`), without claiming Gaia installs the external runtime.
4. **GSD Suite Parent Resolution (`gsd-build/get-shit-done`):**
   - Per CLAUDE/CONTRIBUTING/curation guidelines, suite parents install by iterating their component skills and are explicitly exempt from having their own `links.github` (`docs/agents/curation-guidelines.md`: *"Any skill with suiteComponents ... installs by iterating its components. It has no installation directory of its own and does not need links.github."*).
   - The legacy `links.github` pointing to an archived repository `README.md` caused the installer to attempt an unnecessary root installation and exit 1 after all components installed.
   - Cleared parent `links.github` via `gaia dev update-named gsd-build/get-shit-done --github-link '' --no-build`, preserving all other metadata (4★ rank, `installable: true`, TM 169.36, Grade A, evidence rows).
   - Documented component fan-out and external runtime prerequisite in `## Installation` via CLI (`--installation-file`).
   - Parity outcome resolved from **FAIL SUITE (exit 1)** to **PASS 5/5 components installed (exit 0)**.
5. **Targeted Parity Verification:**
   - All 8 repaired skills swept in `install_parity.py` against `skills@1.5.21`: **8 passed, 0 failed** (`ok STANDARD`).
   - Suite parent `gsd-build/get-shit-done`: **passed cleanly** (`ok SUITE`, 5/5 components installed).
   - Full 9-item sweep (8 repaired skills + suite parent): **9 passed, 0 failed**.
6. **Strict Metadata Invariance:**
   - Ranks, Trust Magnitude scores, Trust Grades, and evidence arrays preserved exactly without calibration or drift.
7. **Blocked Issues Left Untouched:**
   - `disler/*` suite components left blocked pending founder Q1 ruling.
   - `safishamsi/graphify` left blocked pending founder Q2 ruling (currently **5★ / S-grade (TM 316.88)**).
   - `stanfordnlp/dspy` and `getagentseal/codeburn` remain absent from current main; not restored. No policy changes or `installable: false` decisions taken.

---

## 2. Before vs. After Link and Outcome Matrix

Per-skill BEFORE link/outcome table for all 8 original IDs plus the suite parent:

| Original Skill ID | Repaired Skill ID | Before `links.github` URL | Before Parity Outcome / Error | After Parity Outcome |
|---|---|---|---|---|
| `panniantong/agent-reach` | `panniantong/agent-reach` | `https://github.com/Panniantong/Agent-Reach/blob/main/SKILL.md` | `FAIL STANDARD` (exit 1: `Error: no SKILL.md at .../skills/panniantong/Agent-Reach/.`) | `ok STANDARD` (PASS) |
| `gooseworks/notte-browser` | `gooseworks/browser-automation-notte` | `https://github.com/gooseworks-ai/goose-skills` | `FAIL REPO_ROOT` (exit 1: `Error: no SKILL.md at .../skills/gooseworks/goose-skills/.`) | `ok STANDARD` (PASS) |
| `yonatangross/orchestkit-rag` | `yonatangross/rag-retrieval` | `https://github.com/yonatangross/orchestkit` | `FAIL REPO_ROOT` (exit 1: `Error: no SKILL.md at .../skills/yonatangross/orchestkit/.`) | `ok STANDARD` (PASS) |
| `gsd-build/discuss-phase` | `gsd-build/gsd-discuss-phase` | `https://github.com/open-gsd/gsd-core/blob/next/commands/gsd/discuss-phase.md` | `FAIL STANDARD` (exit 1: `Error: no SKILL.md at .../skills/gsd-build/gsd-core/commands/gsd.`) | `ok STANDARD` (PASS) |
| `gsd-build/execute-phase` | `gsd-build/gsd-execute-phase` | `https://github.com/open-gsd/gsd-core/blob/next/commands/gsd/execute-phase.md` | `FAIL STANDARD` (exit 1: `Error: no SKILL.md at .../skills/gsd-build/gsd-core/commands/gsd.`) | `ok STANDARD` (PASS) |
| `gsd-build/plan-phase` | `gsd-build/gsd-plan-phase` | `https://github.com/open-gsd/gsd-core/blob/next/commands/gsd/plan-phase.md` | `FAIL STANDARD` (exit 1: `Error: no SKILL.md at .../skills/gsd-build/gsd-core/commands/gsd.`) | `ok STANDARD` (PASS) |
| `gsd-build/ship` | `gsd-build/gsd-ship` | `https://github.com/open-gsd/gsd-core/blob/next/commands/gsd/ship.md` | `FAIL STANDARD` (exit 1: `Error: no SKILL.md at .../skills/gsd-build/gsd-core/commands/gsd.`) | `ok STANDARD` (PASS) |
| `gsd-build/verify-work` | `gsd-build/gsd-verify-work` | `https://github.com/open-gsd/gsd-core/blob/next/commands/gsd/verify-work.md` | `FAIL STANDARD` (exit 1: `Error: no SKILL.md at .../skills/gsd-build/gsd-core/commands/gsd.`) | `ok STANDARD` (PASS) |
| `gsd-build/get-shit-done` (Suite) | `gsd-build/get-shit-done` | `https://github.com/gsd-build/get-shit-done/blob/main/README.md` | `FAIL SUITE` (exit 1: 5 component failures + root failure on archived README fallback) | `ok SUITE` (PASS: 5/5 components installed, exit 0) |

---

## 3. Pinned Source Revisions & Cryptographic Evidence

Evidence artifacts inspected from `generated-output/evidence/1445/`:

| Registry Skill ID (New) | Upstream Repo | Branch | Tree SHA | Pinned File Path | Git Blob SHA | Evidence File SHA256 |
|---|---|---|---|---|---|---|
| `panniantong/agent-reach` | `Panniantong/Agent-Reach` | `main` | `94f06c1969dfc1834001269d79d3ad0972d9dee6` | `agent_reach/skill/SKILL.md` | `462f4c282c8644744510ba7f47e1f8eb7efde622` | `0df9cd22ade17b77cc3698a14f1224c4aad9df5d533a1878dbe5df11b62f8377` |
| `gooseworks/browser-automation-notte` | `gooseworks-ai/goose-skills` | `main` | `4b07e0b4a8fbaa091b44ef2e1fa1d67bfe9367de` | `skills/research-tools/capabilities/browser-automation-notte/SKILL.md` | `e0795d3a1ed2de079b0f2ab351195952ae0db265` | `8868de8b2acb8fa8e3acbf0d6ed51c69c638f4580c4ccc79995777c3191829f4` |
| `yonatangross/rag-retrieval` | `yonatangross/orchestkit` | `main` | `7626a416e31fb71b372f3c5ba0708d842b189a70` | `plugins/ork/skills/rag-retrieval/SKILL.md` | `511b7ca93d09c6cad3e631d0414cf5b3ce8a96fd` | `f462879df6d42e00cca06d490172fa02398643b12f54f26a4e9a9b8b38b673f5` |
| `gsd-build/gsd-discuss-phase` | `open-gsd/gsd-core` | `next` | `ed0f3fd55849eb041eb2503762c9833b83694abd` | `skills/gsd-discuss-phase/SKILL.md` | `0ae43caac4aa008271d7625173917d09b9b09c29` | `9f2c1b9e67c21db81238f5e9e943675695571bd806b60e725c00ae64f83cda5e` |
| `gsd-build/gsd-execute-phase` | `open-gsd/gsd-core` | `next` | `ed0f3fd55849eb041eb2503762c9833b83694abd` | `skills/gsd-execute-phase/SKILL.md` | `3dfdc720405be8f45054fdd76c6fcf9e57d7e0f2` | `6f772b746d7ae9c260ee83c3f5d5cca9c1aec9f71e1e97cc01d184379369fb3c` |
| `gsd-build/gsd-plan-phase` | `open-gsd/gsd-core` | `next` | `ed0f3fd55849eb041eb2503762c9833b83694abd` | `skills/gsd-plan-phase/SKILL.md` | `f73e2b81b86b754e11f47b71e5ba13c465322d41` | `5f7332b4170afe508c27a7c6ae6965f1da19d601d5ba354d56f34ff85055f1f5` |
| `gsd-build/gsd-ship` | `open-gsd/gsd-core` | `next` | `ed0f3fd55849eb041eb2503762c9833b83694abd` | `skills/gsd-ship/SKILL.md` | `50888a7e45ea98e7973e210c94787a3cc382d79c` | `b98d1e2ebb3af60fc052dbb1cff019e106fa34f96b12fa8e26d774c3fbd79b55` |
| `gsd-build/gsd-verify-work` | `open-gsd/gsd-core` | `next` | `ed0f3fd55849eb041eb2503762c9833b83694abd` | `skills/gsd-verify-work/SKILL.md` | `199db8a38e18889d8f892003b153ea5fc9020122` | `bdcec255104a19e331248eb137b1e3ca9e13c1bf16d7683160abd103f26387f3` |

---

## 4. Upstream Manifest Validation

### 4.1 `panniantong/agent-reach`
- **Upstream Frontmatter:**
  ```yaml
  name: agent-reach
  description: >
    MUST USE when user wants to 调研/research/搜索/search/查/找/look up anything
    on the internet — e.g. 全网调研 X / 帮我调研一下 X / 查一下 X / 搜搜 X /
    看看大家怎么评价 X / X 上有什么讨论 / research this topic.
    16 platforms, multi-backend routing (OpenCLI / per-platform CLIs / APIs).
  ```
- **Capability Match:** Matches registry generic reference `agent-reach` and description of 16+ platform routing.
- **References:** `references/search.md`, `references/social.md`, `references/career.md`, `references/dev.md`, `references/web.md`, `references/video.md`, `references/finance.md`.

### 4.2 `gooseworks/browser-automation-notte`
- **Upstream Frontmatter:**
  ```yaml
  name: browser-automation-notte
  description: Browser automation - control browser sessions, scrape pages, and run AI agents
  source: orthogonal
  ```
- **Capability Match:** Matches registry generic reference `browser-automation`, catalog prose ("Notte Browser API for session control, page scraping, form filling, and autonomous web agent execution").
- **References:** `~/.gooseworks/credentials.json`, `npx gooseworks login`, REST proxy endpoints.

### 4.3 `yonatangross/rag-retrieval`
- **Upstream Frontmatter:**
  ```yaml
  name: rag-retrieval
  license: MIT
  compatibility: "Claude Code 2.1.277+."
  description: Retrieval-Augmented Generation patterns for grounded LLM responses. Use when building RAG pipelines, embedding documents, implementing hybrid search, contextual retrieval, HyDE, agentic RAG, multimodal RAG, query decomposition, reranking, or pgvector search.
  ```
- **Capability Match:** Matches registry generic reference `rag-pipeline`, catalog prose ("Production-grade RAG retrieval skill covering 30+ patterns").
- **References:** 30 modular rule files under `rules/` (Core RAG, Embeddings, Contextual Retrieval, HyDE, Agentic RAG, Multimodal RAG, Query Decomposition, Reranking, PGVector).

### 4.4 `gsd-build` Components
All five manifests match canonical capabilities:
1. `gsd-discuss-phase`: `name: gsd-discuss-phase`, description: "Gather phase context through adaptive questioning before planning." (generic reference: `brainstorming`). References `@~/.claude/gsd-core/workflows/discuss-phase.md`.
2. `gsd-execute-phase`: `name: gsd-execute-phase`, description: "SDD phase execution — execute all plans in a phase with dependency-aware wave parallelization" (generic reference: `subagent-driven-development`). References `@~/.claude/gsd-core/workflows/execute-phase.md`.
3. `gsd-plan-phase`: `name: gsd-plan-phase`, description: "Create detailed phase plan (PLAN.md) with verification loop" (generic reference: `writing-plans`). References `@~/.claude/gsd-core/workflows/plan-phase.md`.
4. `gsd-ship`: `name: gsd-ship`, description: "Create PR, run review, and prepare for merge after verification passes" (generic reference: `finishing-a-development-branch`). References `@~/.claude/gsd-core/workflows/ship.md`.
5. `gsd-verify-work`: `name: gsd-verify-work`, description: "Validate built features through conversational UAT" (generic reference: `verification-before-completion`). References `@~/.claude/gsd-core/workflows/verify-work.md`.

---

## 5. CLI Mutation Log

All mutations were executed with `GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH=src python3 -m gaia_cli.main`:

1. `dev update-named panniantong/agent-reach --github-link "https://github.com/Panniantong/Agent-Reach/blob/main/agent_reach/skill/SKILL.md" --installation-file artifacts/1445/agent-reach-install.md --no-build`
2. `dev rename gooseworks/notte-browser gooseworks/browser-automation-notte --no-build`
3. `dev update-named gooseworks/browser-automation-notte --github-link "https://github.com/gooseworks-ai/goose-skills/blob/main/skills/research-tools/capabilities/browser-automation-notte/SKILL.md" --no-build`
4. `dev rename yonatangross/orchestkit-rag yonatangross/rag-retrieval --no-build`
5. `dev update-named yonatangross/rag-retrieval --name "RAG Retrieval" --github-link "https://github.com/yonatangross/orchestkit/blob/main/plugins/ork/skills/rag-retrieval/SKILL.md" --no-build`
6. `dev rename gsd-build/discuss-phase gsd-build/gsd-discuss-phase --no-build`
7. `dev update-named gsd-build/gsd-discuss-phase --github-link "https://github.com/open-gsd/gsd-core/blob/next/skills/gsd-discuss-phase/SKILL.md" --installation-file artifacts/1445/gsd-install-discuss-phase.md --no-build`
8. `dev rename gsd-build/execute-phase gsd-build/gsd-execute-phase --no-build`
9. `dev update-named gsd-build/gsd-execute-phase --github-link "https://github.com/open-gsd/gsd-core/blob/next/skills/gsd-execute-phase/SKILL.md" --installation-file artifacts/1445/gsd-install-execute-phase.md --no-build`
10. `dev rename gsd-build/plan-phase gsd-build/gsd-plan-phase --no-build`
11. `dev update-named gsd-build/gsd-plan-phase --github-link "https://github.com/open-gsd/gsd-core/blob/next/skills/gsd-plan-phase/SKILL.md" --installation-file artifacts/1445/gsd-install-plan-phase.md --no-build`
12. `dev rename gsd-build/ship gsd-build/gsd-ship --no-build`
13. `dev update-named gsd-build/gsd-ship --github-link "https://github.com/open-gsd/gsd-core/blob/next/skills/gsd-ship/SKILL.md" --installation-file artifacts/1445/gsd-install-ship.md --no-build`
14. `dev rename gsd-build/verify-work gsd-build/gsd-verify-work --no-build`
15. `dev update-named gsd-build/gsd-verify-work --github-link "https://github.com/open-gsd/gsd-core/blob/next/skills/gsd-verify-work/SKILL.md" --installation-file artifacts/1445/gsd-install-verify-work.md --no-build`
16. `dev update-named gsd-build/get-shit-done --github-link "" --installation-file generated-output/artifacts/1445/gsd-suite-installation.md --no-build`
17. `dev docs` (regenerated Class S and Class P graph and index artifacts)

---

## 6. Metadata Invariance Audit

| Skill ID (New) | Rank | TM | Grade | Evidence Rows | Origin Flag | Generic Ref | Notes |
|---|---|---|---|---|---|---|---|
| `panniantong/agent-reach` | `3★` | `53.86` | `B` | 5 | `false` | `agent-reach` | Preserved unchanged |
| `gooseworks/browser-automation-notte` | `1★` | `0.0` | `ungraded` | 0 | `false` | `browser-automation` | Preserved unchanged |
| `yonatangross/rag-retrieval` | `1★` | `0.0` | `ungraded` | 0 | `false` | `rag-pipeline` | Preserved unchanged |
| `gsd-build/gsd-discuss-phase` | `3★` | `50.0` | `B` | 2 | `false` | `brainstorming` | Preserved unchanged |
| `gsd-build/gsd-execute-phase` | `3★` | `50.0` | `B` | 2 | `false` | `subagent-driven-development` | Preserved unchanged |
| `gsd-build/gsd-plan-phase` | `3★` | `50.0` | `B` | 2 | `false` | `writing-plans` | Preserved unchanged |
| `gsd-build/gsd-ship` | `3★` | `50.0` | `B` | 2 | `false` | `finishing-a-development-branch` | Preserved unchanged |
| `gsd-build/gsd-verify-work` | `3★` | `50.0` | `B` | 2 | `false` | `verification-before-completion` | Preserved unchanged |
| `gsd-build/get-shit-done` | `4★` | `169.36` | `A` | 3 | `false` | `git-ship-done-pipeline` | Preserved unchanged; suiteComponents repointed; links.github cleared per suite parent exemption |

---

## 7. Install-Parity Results

### 7.1 Targeted Sweep of 8 Repaired Skills
Command:
```bash
python scripts/install_parity.py \
  --only panniantong/agent-reach \
  --only gooseworks/browser-automation-notte \
  --only yonatangross/rag-retrieval \
  --only gsd-build/gsd-discuss-phase \
  --only gsd-build/gsd-execute-phase \
  --only gsd-build/gsd-plan-phase \
  --only gsd-build/gsd-ship \
  --only gsd-build/gsd-verify-work \
  --jobs 1 --json generated-output/parity/1445-after.json
```
Output:
```
[  1/8] ok   STANDARD   gooseworks/browser-automation-notte
[  2/8] ok   STANDARD   gsd-build/gsd-discuss-phase
[  3/8] ok   STANDARD   gsd-build/gsd-execute-phase
[  4/8] ok   STANDARD   gsd-build/gsd-plan-phase
[  5/8] ok   STANDARD   gsd-build/gsd-ship
[  6/8] ok   STANDARD   gsd-build/gsd-verify-work
[  7/8] ok   STANDARD   panniantong/agent-reach
[  8/8] ok   STANDARD   yonatangross/rag-retrieval

KPIs: Swept 8 | Pass 8 | Fail 0 | Dirname mismatches: 0 | Dangling symlinks: 0
```

### 7.2 Suite Parent Resolution (`gsd-build/get-shit-done`)
Command:
```bash
python scripts/install_parity.py --only gsd-build/get-shit-done --jobs 1 --json generated-output/parity/1445-after-suite.json
```
- **Before:** `FAIL SUITE` (exit 1 on root README.md fallback pointing at archived upstream repository).
- **After:** `ok SUITE gsd-build/get-shit-done` (**PASS 5/5 components installed**, exit 0).

Output:
```
[  1/1] ok   SUITE      gsd-build/get-shit-done

==============================================================================
KPIs
==============================================================================
Swept       1   pass 1   fail 0

Category      total   pass   fail
SUITE             1      1      0

Wall clock          16.61s across 1 job(s)
Suite components    5/5 installed
```

### 7.3 Combined Sweep of All 9 Repaired Items
Command:
```bash
python scripts/install_parity.py \
  --only panniantong/agent-reach \
  --only gooseworks/browser-automation-notte \
  --only yonatangross/rag-retrieval \
  --only gsd-build/gsd-discuss-phase \
  --only gsd-build/gsd-execute-phase \
  --only gsd-build/gsd-plan-phase \
  --only gsd-build/gsd-ship \
  --only gsd-build/gsd-verify-work \
  --only gsd-build/get-shit-done \
  --jobs 1 --json generated-output/parity/1445-all-pass.json
```
Output:
```
[  1/9] ok   STANDARD   gooseworks/browser-automation-notte
[  2/9] ok   SUITE      gsd-build/get-shit-done
[  3/9] ok   STANDARD   gsd-build/gsd-discuss-phase
[  4/9] ok   STANDARD   gsd-build/gsd-execute-phase
[  5/9] ok   STANDARD   gsd-build/gsd-plan-phase
[  6/9] ok   STANDARD   gsd-build/gsd-ship
[  7/9] ok   STANDARD   gsd-build/gsd-verify-work
[  8/9] ok   STANDARD   panniantong/agent-reach
[  9/9] ok   STANDARD   yonatangross/rag-retrieval

KPIs: Swept 9 | Pass 9 | Fail 0 | Dirname mismatches: 0 | Dangling symlinks: 0 | Suite components: 5/5 installed
```

---

## 8. Test and Validation Results

- `python3 scripts/validate.py`: All 10 validation gates passed, DAG valid, zero reference or cycle errors.
- `python3 scripts/validate_timelines.py`: Passed, 241 owned named skills across 40 trees, all timeline events valid.
- `python3 scripts/build_docs.py --check`: Passed (`Documentation is up to date.`), zero unexpected drift.
- Pytest unit and regression suite:
  - `PYTHONPATH=src pytest tests/test_dev_named.py tests/test_dev_rename.py tests/test_build_docs_*.py tests/test_docs_*.py`: 77 passed.
  - `PYTHONPATH=src pytest tests/test_meta_ops.py tests/test_install.py tests/test_real_skill_catalog.py tests/test_dev_build.py tests/test_suite_install.py`: 116 passed.

---

## 9. Preserved Blockers & Out-of-Scope Items

- **`disler/*` suite components:** 3 skills remain blocked pending founder decision on Q1 (suite components exemption vs installable: false vs upstream repackaging).
- **`safishamsi/graphify`:** 1 skill remains blocked pending founder decision on Q2 (currently **5★ / S-grade (TM 316.88)**; decision on 5★ demotion vs install-shape packaging exception).
- **`stanfordnlp/dspy` & `getagentseal/codeburn`:** absent on current `main` (commit `9dae8fcda`), not restored.
- **No policy modifications or `installable: false` flags applied:** Zero star-bar resets or demotions attempted.

# Registry & Intake Advisory Report: Jev Sidecar + Luna High Review

**Date:** 2026-10-01  
**Harness / Workflow:** Bounded Jev Advisory Lane (`scripts/jev_advisory.py`) with `worker-luna-high` Fallback Reasoning  
**Scope:** Intake Batches (`registry-for-review/skill-batches/`), Issue Backlog (#2024–#1993), and Canonical Generic Nodes (`registry/nodes/`)  
**Status:** Read-only advisory audit & curator triage handoff  

---

## Executive Summary

Following the merge of PR #2029 introducing the repository-native Jev Advisory Lane (`docs/agents/jev.md`), this operational audit demonstrates the bounded multi-agent advisory loop in production:
1. **Automated Semantic Evaluation:** Live TypeSafe System One (`jev-1.13.0`) evaluations executed across candidate mapping batches, generic ontology descriptions, and open issues.
2. **Deterministic Guardrails & Budgeting:** Local monthly budget ledger (`.gaia/jev/budget.json`) maintained strict accounting. Total run cost was **$0.000274 USD** across 7 live API calls, preserving over **$0.499** of the local developer monthly limit ($0.50).
3. **Actionable Luna Fallback:** When items fell below the 0.75 confidence threshold or hit process call allocations, structured fallback packets were handed off to `worker-luna-high` for deep architectural reasoning.

---

## 1. Candidate Mapping Findings (Intake Batches)

Three pending candidate intake proposals were evaluated against Gaia's canonical generic capability graph:

| Candidate ID | Source Batch | Jev Recommendation | Jev Conf. | Luna High Verdict | Curator Action |
|---|---|---|---|---|---|
| `latent-spaces/brag` | `20260926162927-mbtiongson1-from-file.json` | `project-launch-video-production` | `0.90` | **ACCEPT** | Map as named implementation to existing fusion node `project-launch-video-production`. Do not decompose into component primitives (`video-rendering`, `creative-direction`). |
| `InsightFactoryAPP/project-management` | `20260911153000-InsightFactoryAPP-from-file.json` | `project-management` | `1.00` | **REFINE** | Generic node `project-management` already exists. Do not create a duplicate generic node. Review batch strictly as a named implementation under the existing fusion node. |
| `mbtiongson1/codebase-graph-retrieval` | `20260910121121-mbtiongson1-from-file.json` | `codebase-graph-retrieval` | `1.00` | **ACCEPT** | Clean 1.0 match to existing canonical fusion node. Lexical similarity matches to biomedical sequence retrieval are false positives; approve as named candidate. |

---

## 2. Issue Backlog & Upstream Release Triage (#2024–#1993)

25 open repository issues were analyzed for duplicate relationships, priority classification, and upstream umbrella-child structuring:

### Cluster A: `obra/superpowers` v6.4.2 Release Upgrade
- **Umbrella Issue:** #2020 (`[upstream] obra/superpowers → v6.4.2`)
- **Child Intakes:** #2021 (`diagnosing-superpowers`), #2022 (`test-driven-development`), #2023 (`using-superpowers`), #2024 (`writing-skills`)
- **Jev Advisory:** All 5 items evaluated live with **P2** priority (confidence `0.96`–`0.98`) and duplicate status `NONE_OF_SHORTLIST` (`0.86`–`0.91`).
- **Curator Action:** Batch-curate the upgrade into `registry/named/obra/`. Ensure #2022 references canonical testing generic capability rather than minting a new generic node.

### Cluster B: `addyosmani/agent-skills` 0.6.11 (17 Child Intakes)
- **Umbrella Issue:** #2002 (`[upstream] addyosmani/agent-skills → 0.6.11`)
- **Child Intakes:** #2003 through #2019 (17 skills covering CI/CD, debugging, context engineering, ADRs, etc.)
- **Luna High Architecture Analysis:**
  - **Single Suite Admission:** Treat `addyosmani/agent-skills` as a unified upstream suite under Yggdrasil III (`META.md` §1.2), rather than 17 independent, uncoordinated intake reviews.
  - **Generic Alignment:** Most child skills map directly to existing generic capabilities:
    - `ci-cd-and-automation` → `ci-cd`
    - `debugging-and-error-recovery` → `debug-interactive`
    - `context-engineering` → `context-compression`
    - `browser-testing-with-devtools` → `browser-automation`
  - **Priority:** Assign **P2** to umbrella #2002. Use `/gaia-suite-intake` to curate named components and capstone.

### Cluster C: Governance, Infrastructure & Peripheral Intakes
- **#2001 (`Gaia Steward weekly rhythm`):** **P1**. Cross-cutting infrastructure and maintenance reliability enhancement. Needs architectural review. Note: Jev advisory is strictly forbidden inside Steward runtime dispatch loops (Zero-Model Invariant).
- **#1999 (`[meta post] 95 upstream skill candidates`):** **P3**. Content engine deliverable; should sequence after integration facts land.
- **#1997, #1993 (`garrytan` MCP/Webhook intakes):** **P2/P3**. Already tracked under parent umbrella #1835.
- **#1996, #1995, #1994 (`heygen-com` video skills):** **P2/P3**. Tracked under parent umbrella #1823.

---

## 3. Meta Registry Generic Node Audit

Analysis of canonical generic nodes in `registry/nodes/`:

### Focus Node: `adaptive-pattern-learning` (Basic)
- **Current Description:** *"Records task outcomes and identifies recurring scenarios to rank optimal response strategies over time. It enables genuine self-improvement through a feedback learning loop by matching scenarios and transferring knowledge across related domains via vector similarity."*
- **Jev Advisory Outcome:** `reviewRoute: well_scoped`, but confidence was `0.64` (probabilities: `well_scoped: 0.73`, `overly_broad: 0.27`). Triggered Luna fallback.
- **Luna High Review:** **REFINE**.
  - The node is fundamentally well-scoped as a basic capability around outcome recording and strategy adaptation.
  - However, the current phrasing overreaches by promising *"genuine self-improvement"* and *"optimal response strategies"*.
  - **Recommendation:** Refactor description to focus on the observable feedback loop and make vector similarity/cross-domain transfer explicit as optional techniques rather than mandatory prerequisites.

---

## 4. Spend & Telemetry Ledger

- **Ledger Path:** `.gaia/jev/budget.json`
- **Active Month:** `2026-10`
- **Pricing:** TypeSafe System One (`jev-1.13.0`), \$0.042 per million input tokens, zero output token charge.
- **Run Metrics:**
  - Total HTTP Calls: 7
  - Total Reserved: $0.021 USD
  - Total Actual Cost: **$0.000274 USD**
  - Remaining Monthly Budget: **$0.499726 USD** (out of $0.50 cap)
- **Zero Registry Drift:** All outputs written exclusively to scratch/generated reports. Canonical registry nodes untouched.

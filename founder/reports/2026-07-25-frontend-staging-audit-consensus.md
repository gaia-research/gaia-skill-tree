# Frontend Audit & Optimization Consensus (`dev/yggdrasil-ii-staging`)
**Date:** July 25, 2026  
**Status:** Audit Document Created — Under Review (Not Final)  
**Branch:** `dev/yggdrasil-ii-staging`  
**Methodology:** 10-Agent Multi-Phase Workflow (Proposals → Adversarial Challenges → Judicial Evaluation → Master Synthesis)

---

## 1. Executive Summary & Vision

A multi-phase workflow audit evaluated the frontend of `dev/yggdrasil-ii-staging` from the perspective of human developers, contributor claimers, and external AI agents. The primary objective is to transform the frontend into a high-signal **Evidence-Backed Agent Capability Registry** by stripping away non-essential UI simulations, unlinked scratchpads, obsolete script references, and redundant pages while preserving core governance features, dynamic proof surfaces, and typographic brand identity.

---

## 2. Validated Final Consensus

* **Typographic Styling Preserved:** The typographic SVG branch inside `#heroTreeTitle` is retained as a visual bridge to the interactive 3D DAG canvas.
* **Preventing Cumulative Layout Shift (CLS):** Interactive terminal simulators retain static heights (`320px`) and initial `"Awaiting simulation trigger..."` state copy to prevent layout jumps.
* **Parallax Scroll Optimization Retained:** The `#ascension` section is retained on the homepage with lazy-load event bindings and `IntersectionObserver` detachments.
* **Dead Code Cleanup:** The inert legacy markup `<template id="hall-of-heroes-legacy-template">` in `docs/index.html` is confirmed inactive and marked for deletion.
* **CI-Safe Directory Pruning:** Development artifacts, visual test samplers (`docs/samples/`), experiments (`docs/experiments/`), and duplicate OKF markdown files are marked for removal after updating `scripts/build_docs.py` and guard allowlists.
* **Cloudflare Worker Exemption Intact:** The `"samples"` bypass handle in `worker/index.js` remains untouched to preserve static badge preview routes.
* **Consolidation & Safety:** Folder and navigation consolidation must include strict DOM existence checks (e.g. `#treeNavBtn` in `skill-explorer.js`) and retain auxiliary mounts in `window.GAIA_MOUNTS`.

---

## 3. Detailed Homepage Action Plan (`docs/index.html`)

### 3.1 Hero Section (`#hero`)
- **Action:** Retain inline `<svg class="hero-sakura-branch">` inside `#heroTreeTitle` and associated CSS in `docs/css/world-tree-hero.css`.
- **Cleanup:** Remove hardcoded static top audit report banner (`meta/reports/2026-07-13...`).

### 3.2 Review Showcase Terminal Simulation (`#review-showcase`)
- **Dimensions:** Lock `#localSimConsole` and `#remoteSimConsole` at `320px` height.
- **Formatting:** Update `.review-sim-body` CSS to enforce left-alignment (`text-align: left; white-space: pre-wrap; word-break: normal; overflow-wrap: break-word;`).

### 3.3 Hall of Heroes (`#hall-of-heroes`)
- **Cleanup:** Delete `<template id="hall-of-heroes-legacy-template">` tag block (lines 482–497) from `docs/index.html` and obsolete CSS rules referencing `#hall-of-heroes-legacy` or `#hohPlatesLegacy`.

---

## 4. File & Route Pruning

### 4.1 Decommissioning Build Dependencies
1. Delete `scripts/build_okf_bundle.py`.
2. Remove `build_okf_bundle()` and `okf-bundle` tasks from `scripts/build_docs.py`.
3. Update `DEV.md` to remove obsolete OKF bundle CLI commands.

### 4.2 Safe File Deletions
Remove the following unlinked / test paths:
- `docs/samples/` (16 sample HTML files)
- `docs/experiments/` (ml-graph-viz prototypes)
- `docs/archive/` (`ADOPTION.html`, `SHOWCASE.html`)
- `docs/plans/` (screenshot artifacts)
- `docs/superpowers/` (internal planning files)
- `docs/okf/skills/` & `docs/okf/*.md` files (retain `docs/okf/index.json`)
- `docs/starless.html` (redundant filter view)

### 4.3 Mounts & Guard Calibration
- Update `window.GAIA_MOUNTS` in `docs/js/mounts.js`, `docs/js/site-nav.js`, `docs/js/site-footer.js`, `docs/js/skill-explorer.js`, and `docs/js/icons.js`.
- Retain `"samples"` in `worker/index.js` `PASSTHROUGH_HANDLES` for badge generation compatibility.
- Update `scripts/check_rank_vocabulary.py`, `scripts/check_taxonomy_authority.py`, and `.github/workflows/docs-cohesion.yml`.

---

## 5. Navigation & Page Consolidation

### 5.1 Merging Generic Skills into Named Skills
- Add toggle control in `docs/named/index.html` ("Implementations" vs "Canonical Capabilities").
- Implement `mapGenericToPlaque()` in `named-skills.js` to normalize generic skills from `docs/okf/index.json`.
- Replace `/docs/skills/index.html` with a static HTTP meta refresh redirect to `../named/index.html?view=canonical`.

### 5.2 Streamlining Navigation (`site-nav.js`)
- Reduce primary header navigation to 4 main links: **Skills** (`/named/`), **Benchmarks** (`/benchmarks/`), **Reports** (`/reports/`), and **Docs** (`/en/`).
- Add DOM null-guards in `docs/js/skill-explorer.js` for removed element IDs (`#treeNavBtn`).

---

## 6. Implementation Phases

1. **Phase 1: Build & Pipeline Decommissioning**
2. **Phase 2: Directory & Markdown Pruning**
3. **Phase 3: Taxonomy & Vocabulary Guard Sync**
4. **Phase 4: UI Refactoring & Page Consolidation**
5. **Phase 5: Verification & Site Asset Regeneration**

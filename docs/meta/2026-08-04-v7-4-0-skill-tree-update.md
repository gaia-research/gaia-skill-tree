---
title: "v7.4.0 Skill Tree Report: Backlog Changes in /registry/"
author: "Gaia Research"
summary: "A focused report on the backlog-era /registry/ changes: new and refreshed named skill files, expanded generic skill nodes, benchmark-source trust infrastructure, and the public surfaces that make those data changes visible."
abstract: |
  This is a focused report on the issue-backlog changes to /registry/, not a chronological release list and not a package-release announcement. It summarizes the data that changed: named skill files, generic skill nodes, benchmark-source infrastructure, and the review surfaces that now expose those records more clearly.
label: Skill Tree Report
---

## Abstract

This report explains the main backlog-era changes to `/registry/`. The center of gravity is the data layer: new named skill files, updated named skill files, new and refreshed generic skill nodes, benchmark-source trust infrastructure, and the site surfaces that make those records inspectable. A later `v7.3.9` refresh added Weekly Report 2026-32; that was a minor follow-up and is not the subject of this report.

## Scope

The issue-backlog closeout changed `/registry/` across 41 files: 27 additions and 14 modifications. The work was not just a site polish pass. It expanded the skill tree's canonical data with new implementation records, new generic capabilities, and new evidence-review structure.

Read this as a report on the data that landed, grouped by what a maintainer or reviewer would inspect in the folder:

- `registry/named/`: named implementation files added or refreshed.
- `registry/nodes/`: generic `basic` and `fusion` skill nodes added or refreshed.
- `registry/benchmark-sources.json` and `registry/schema/`: benchmark-source and evidence-shape infrastructure.
- Generated/public surfaces: pages that let humans inspect the changed records without reading raw files.

## Visual Summary

The rendered report shows the data movement as a `/registry/` map: named skills, generic nodes, trust/schema infrastructure, and public review surfaces. The goal is to make the shape of the backlog changes visible before the detailed tables.

## Named Skill Files

### New named skills

The backlog closeout added 13 named implementation files. Most of the volume came from scientific Python and machine-learning capabilities, with smaller additions in brand governance, daily logging, and hair-styling workflows.

| Contributor | New named skills |
|---|---|
| `anthropics` | `brand-guidelines` |
| `aplaceforallmystuff` | `log-to-daily` |
| `dietrichgebert` | `ponytail` |
| `k-dense-ai` | `deepchem`, `pymc`, `pytorch-lightning`, `qiskit`, `rdkit`, `scanpy`, `scvi-tools`, `stable-baselines3`, `torch-geometric`, `transformers` |

### Updated named skills

Eight existing named skill files were refreshed so their records better match the current skill tree and public surfaces:

- `addy-osmani/incremental-implementation`, `addy-osmani/planning-and-task-breakdown`, and `addy-osmani/spec-driven-development`.
- `firecrawl/firecrawl-research-index`.
- `gaia-research/skill-fuse`, including repository surface work from #1004.
- `gsd-build/get-shit-done`.
- `obra/brainstorming` and `obra/subagent-driven-development`.

## Generic Skill Nodes

The backlog closeout also expanded generic skill coverage. Fourteen files under `registry/nodes/` were added or updated: 12 new nodes and 2 refreshed nodes.

| Area | Generic nodes |
|---|---|
| Workflow and documentation | `brand-guideline-application` (`basic`), `prompt-caching` (`basic`), `session-journaling` (`basic`) |
| Scientific and computational work | `cheminformatics-analysis` (`fusion`), `molecular-machine-learning` (`fusion`), `quantum-circuit-programming` (`basic`), `single-cell-analysis` (`basic`), `single-cell-omics-modeling` (`fusion`) |
| Machine learning systems | `graph-neural-network-modeling` (`fusion`), `neural-training-orchestration` (`fusion`), `reinforcement-learning-training` (`fusion`), `transformer-model-engineering` (`fusion`) |
| Refreshed nodes | `probabilistic-programming` (`basic`), `test-driven-development` (`basic`) |

These nodes give the public graph stronger first-class vocabulary for benchmark-backed ML libraries, scientific analysis stacks, and prompt/cache/session workflow primitives.

## Benchmark-Source Trust Infrastructure

The largest trust-infrastructure change is the verified benchmark-source catalog. The backlog closeout added `registry/benchmark-sources.json`, added `registry/schema/benchmarkSourceCatalog.schema.json`, and updated benchmark-result, named-skill, and skill schemas.

That matters because benchmark-result evidence can now point toward approved benchmark sources instead of treating every benchmark claim as equally trustworthy. It gives future evidence ingestion a clearer path: source first, result second, trust review always explicit.

## Public Review Surfaces

Several site surfaces were polished because they are how humans inspect the changed data:

### Suite Explorer

Suite Explorer now preserves the distinction between Path/Fusion origin labels and Suite lens component labels. Path and Fusion views keep origin labels; the Suite lens switches rendered nodes to suite-component labels. The compact transparent outboard Suite Components rail is hidden by default, and row clicks focus graph nodes only.

That polish turns Suite Explorer into a better diagnostic surface for suite data. Missing or off-path suite metadata is easier to spot, which supports the still-open Suite data/meta-audit follow-up (#1438) instead of hiding data-shape gaps.

### Share Plaques

Share Plaques received a rendering fix for modal and export paths. The modal now prefers inlined SVG, and the PNG raster scripts inline/transcode display-sized AOV medallions so PNG and HTML modal medallions render consistently. A follow-up hotfix capped inlined raster size after the initial OG PNG workflow failed.

### Trust Leaderboard and benchmark pages

The Trust Leaderboard redesign from #868 and the benchmark surface work from #1419 both make the underlying records easier to inspect. The result is less friction for users moving between contributor reputation, evidence, and benchmark-backed capability pages.

### Weekly Reports

Weekly Reports received local/deployed link stability improvements during the backlog closeout. That surface is included only where it helps explain how humans inspect the backlog-era `/registry/` changes.

## Notes for Reviewers

This report should be reviewed as a data-and-surface explanation, not as a package release note. The key facts are:

- PR #1395 merged the issue-backlog integration and carried the `/registry/` data changes summarized here.
- The `/registry/` folder changed across 41 files: 27 additions and 14 modifications.
- The main data movements were 13 new named skill files, 8 refreshed named skill files, 14 generic node files, and benchmark-source trust infrastructure.
- #1438 remains open for deeper Suite data and meta-audit follow-up.

## References

[1] PR #1395: issue-backlog integration merge.

[2] Issues closed by #1395: #868 Trust Leaderboard redesign, #1004 skill-fuse repo surfaces, #1268 frontend performance pass, #1419 verified benchmark-source catalog.

[3] Follow-up still open: #1438 Suite data and meta-audit work.

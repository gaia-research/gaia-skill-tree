---
title: "v7.4.0 Skill Tree Report: Backlog Changes in /registry/"
author: "Gaia Research"
summary: "A reader-facing report on the backlog-era /registry/ changes: new and refreshed named skill files, expanded generic skill nodes, benchmark-source trust infrastructure, and public surfaces that make those records easier to inspect."
abstract: |
  The backlog closeout materially expanded the skill tree's data layer. This report traces what changed inside /registry/: new named implementation files, refreshed contributor records, new generic basic and fusion nodes, benchmark-source trust infrastructure, and the review surfaces that now make those records easier to inspect.
label: Skill Tree Report
---

## Abstract

The backlog closeout materially expanded the skill tree's data layer. This report traces what changed inside `/registry/`: new named implementation files, refreshed contributor records, new generic `basic` and `fusion` nodes, benchmark-source trust infrastructure, and the review surfaces that now make those records easier to inspect. A later `v7.3.9` refresh added Weekly Report 2026-32; that refresh is context, not the subject of this report.

## Scope

The backlog closeout changed `/registry/` across 41 files: 27 additions and 14 modifications. The work was not just site polish. It expanded the canonical skill data with new implementation records, new generic capabilities, and a clearer evidence-review structure for benchmark-backed claims.

Read this as a report on the data that landed, grouped by what a maintainer or reviewer would inspect in the folder:

- `registry/named/`: named implementation files added or refreshed.
- `registry/nodes/`: generic `basic` and `fusion` skill nodes added or refreshed.
- `registry/benchmark-sources.json` and `registry/schema/`: benchmark-source and evidence-shape infrastructure.
- Generated/public surfaces: pages that let humans inspect changed records without opening raw files.

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

Eight existing named skill files were refreshed so their records better match their upstream source material and the public skill surfaces:

- `addy-osmani/incremental-implementation`, `addy-osmani/planning-and-task-breakdown`, and `addy-osmani/spec-driven-development` now point at the corresponding Addy Osmani Agent Skills source files and supporting public reviews.
- `firecrawl/firecrawl-research-index` now carries Firecrawl Research Index evidence and benchmark-source context.
- `gaia-research/skill-fuse` now points at the standalone `skill-fuse` skill repository and its installable skill file.
- `gsd-build/get-shit-done` now records the public GSD repository, release source, and supporting arXiv evidence.
- `obra/brainstorming` and `obra/subagent-driven-development` now connect the Superpowers skill files with public demo and review evidence.

## Generic Skill Nodes

The backlog closeout also expanded generic skill coverage. Fourteen files under `registry/nodes/` were added or updated: 12 new nodes and 2 refreshed nodes.

| Area | Generic nodes |
|---|---|
| Workflow and documentation | `brand-guideline-application` (`basic`), `prompt-caching` (`basic`), `session-journaling` (`basic`) |
| Scientific and computational work | `cheminformatics-analysis` (`fusion`), `molecular-machine-learning` (`fusion`), `quantum-circuit-programming` (`basic`), `single-cell-analysis` (`basic`), `single-cell-omics-modeling` (`fusion`) |
| Machine learning systems | `graph-neural-network-modeling` (`fusion`), `neural-training-orchestration` (`fusion`), `reinforcement-learning-training` (`fusion`), `transformer-model-engineering` (`fusion`) |
| Refreshed nodes | `probabilistic-programming` (`basic`), `test-driven-development` (`basic`) |

These nodes give the public graph stronger first-class vocabulary for benchmark-backed machine-learning libraries, scientific analysis stacks, and prompt/cache/session workflow primitives.

## Benchmark-Source Trust Infrastructure

The largest trust-infrastructure change is the verified benchmark-source catalog. The backlog closeout added `registry/benchmark-sources.json`, added `registry/schema/benchmarkSourceCatalog.schema.json`, and updated benchmark-result, named-skill, and skill schemas.

That matters because benchmark-result evidence can now point toward approved benchmark sources instead of treating every benchmark claim as equally trustworthy. It gives future evidence ingestion a clearer path: source first, result second, trust review always explicit.

The initial catalog includes Firecrawl Research Index / alphaXiv ArXivQA context, OpenAI HumanEval and the local HumanEval harness, and the Hugging Face Open LLM Leaderboard as distinct benchmark-source records.

## Public Review Surfaces

Several site surfaces were polished because they are how humans inspect the changed data:

### Suite Explorer

Suite Explorer now preserves the distinction between Path/Fusion origin labels and Suite lens component labels. Path and Fusion views keep origin labels; the Suite lens switches rendered nodes to suite-component labels. The compact transparent outboard Suite Components rail is hidden by default, and row clicks focus graph nodes only.

That polish turns Suite Explorer into a better diagnostic surface for suite data. Missing or off-path suite metadata is easier to spot instead of hiding data-shape gaps.

### Share Plaques

Share Plaques received a rendering fix for modal and export paths. The modal now prefers inlined SVG, and the PNG raster scripts inline/transcode display-sized AOV medallions so PNG and HTML modal medallions render consistently. A follow-up hotfix capped inlined raster size after the initial OG PNG workflow failed.

### Trust Leaderboard and benchmark pages

The Trust Leaderboard redesign and benchmark pages make the underlying records easier to inspect. The result is less friction for users moving between contributor reputation, evidence, and benchmark-backed capability pages.

### Weekly Reports

Weekly Reports received local/deployed link stability improvements during the backlog closeout. That surface is included only where it helps explain how humans inspect the backlog-era `/registry/` changes.

## Notes for Reviewers

This report should be reviewed as a data-and-surface explanation, not as a package release note. The key facts are:

- The backlog merge carried the `/registry/` data changes summarized here.
- The `/registry/` folder changed across 41 files: 27 additions and 14 modifications.
- The main data movements were 13 new named skill files, 8 refreshed named skill files, 14 generic node files, and benchmark-source trust infrastructure.
- Suite data still has deeper follow-up work, especially around off-path suite components and manifest completeness.

## Sources and References

### Named skill source material

[Anthropic Brand Guidelines skill](https://github.com/anthropics/skills/blob/main/skills/brand-guidelines/SKILL.md) — source skill file behind `anthropics/brand-guidelines`.

[Daily Patterns Pack](https://github.com/aplaceforallmystuff/daily-patterns-pack) — upstream repository behind `aplaceforallmystuff/log-to-daily`.

[Ponytail skill implementation](https://github.com/DietrichGebert/ponytail) — upstream repository for `dietrichgebert/ponytail`.

[Addy Osmani Agent Skills](https://github.com/addyosmani/agent-skills) — source repository for the refreshed implementation, planning, and spec-driven development records.

[Obra Superpowers](https://github.com/obra/superpowers) — source repository for the refreshed brainstorming and subagent-driven development records.

[GSD Build protocol](https://github.com/gsd-build/get-shit-done) — source repository and release trail behind `gsd-build/get-shit-done`.

[Skill Fuse](https://github.com/gaia-research/skill-fuse) — installable upstream repository for `gaia-research/skill-fuse`.

### Scientific and machine-learning skill sources

[K-Dense AI Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) — source index for the ten newly added scientific and ML named skill files.

[DeepChem skill file](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/deepchem/SKILL.md) — molecular machine-learning skill source.

[RDKit skill file](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/rdkit/SKILL.md) — cheminformatics skill source.

[PyMC skill file](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/pymc/SKILL.md) — probabilistic programming skill source.

### Benchmark and trust infrastructure

[Firecrawl Research Index launch](https://www.firecrawl.dev/blog/research-index-launch) — benchmark-result evidence and source URL for the Firecrawl Research Index record.

[alphaXiv retrieval-agent methodology](https://www.alphaxiv.org/blog/training-retrieval-agents-for-arxiv-search) — methodology reference for the ArXivQA retrieval benchmark source.

[OpenAI HumanEval](https://github.com/openai/human-eval) — canonical coding benchmark source in the benchmark-source catalog.

[Hugging Face Open LLM Leaderboard](https://huggingface.co/spaces/HuggingFaceH4/open%5Fllm%5Fleaderboard) — model-evaluation benchmark source in the catalog.

### Public review context

[Agentailor top agent skills review](https://blog.agentailor.com/posts/top-agent-skills-for-agentic-engineering-2026) — independent public review context for several refreshed agent-engineering skill records.

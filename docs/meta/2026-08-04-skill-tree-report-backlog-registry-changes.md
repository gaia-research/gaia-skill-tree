---
title: "Skill Tree Report: Backlog Changes in /registry/"
author: "Gaia Research"
summary: "A reader-facing report on the backlog-era /registry/ changes: new and refreshed named skill files, expanded generic skill nodes, benchmark-source trust infrastructure, and public surfaces that make those records easier to inspect."
abstract: |
  This report follows the data that changed in /registry/: new named implementation records, refreshed contributor records, new generic basic and fusion nodes, benchmark-source trust infrastructure, and the review surfaces that make those records easier to inspect.
label: Skill Tree Report
---

## Abstract

This report follows the data that changed in `/registry/`: new named implementation records, refreshed contributor records, new generic `basic` and `fusion` nodes, benchmark-source trust infrastructure, and the review surfaces that make those records easier to inspect. The emphasis is not release chronology. The emphasis is what the skill tree now knows, which evidence channels back it, and how a reader can inspect the resulting records.

## Change Map

The backlog closeout changed `/registry/` across 41 files: 27 additions and 14 modifications. The work expanded the canonical skill data with new implementation records, new generic capabilities, and a clearer evidence-review structure for benchmark-backed claims.

Read the change as four connected data movements:

- `registry/named/`: named implementation files added or refreshed.
- `registry/nodes/`: generic `basic` and `fusion` skill nodes added or refreshed.
- `registry/benchmark-sources.json` and `registry/schema/`: benchmark-source and evidence-shape infrastructure.
- Generated/public surfaces: pages that let humans inspect changed records without opening raw files.

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

Eight existing named skill files were refreshed so their records better match upstream source material and public evidence:

- `addy-osmani/incremental-implementation`, `addy-osmani/planning-and-task-breakdown`, and `addy-osmani/spec-driven-development` now align with the Addy Osmani Agent Skills repository and independent public review coverage.
- `firecrawl/firecrawl-research-index` now carries Firecrawl Research Index evidence and benchmark-source context.
- `gaia-research/skill-fuse` now points at the standalone `skill-fuse` repository.
- `gsd-build/get-shit-done` now records the public GSD repository, release source, and supporting arXiv evidence.
- `obra/brainstorming` and `obra/subagent-driven-development` now connect the Superpowers repository with public demo and review evidence.

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

Share Plaques received a rendering fix for modal and export paths. The modal now prefers inlined SVG, and the PNG raster scripts inline/transcode display-sized AOV medallions so PNG and HTML modal medallions render consistently.

### Trust Leaderboard and benchmark pages

The Trust Leaderboard redesign and benchmark pages make the underlying records easier to inspect. The result is less friction for users moving between contributor reputation, evidence, and benchmark-backed capability pages.

### Weekly Reports

Weekly Reports received local/deployed link stability improvements during the backlog closeout. That surface is included only where it helps explain how humans inspect the backlog-era `/registry/` changes.

## Reading the Data

The key facts are:

- The `/registry/` folder changed across 41 files: 27 additions and 14 modifications.
- The main data movements were 13 new named skill files, 8 refreshed named skill files, 14 generic node files, and benchmark-source trust infrastructure.
- Suite data still has deeper follow-up work, especially around off-path suite components and manifest completeness.

## Sources and References

### Benchmark and trust signals

[Firecrawl Research Index launch](https://www.firecrawl.dev/blog/research-index-launch) — benchmark-result evidence and source URL for the Firecrawl Research Index record.

[alphaXiv retrieval-agent methodology](https://www.alphaxiv.org/blog/training-retrieval-agents-for-arxiv-search) — methodology reference for the ArXivQA retrieval benchmark source.

[OpenAI HumanEval](https://github.com/openai/human-eval) — canonical coding benchmark source in the benchmark-source catalog.

[Hugging Face Open LLM Leaderboard](https://huggingface.co/spaces/HuggingFaceH4/open%5Fllm%5Fleaderboard) — model-evaluation benchmark source in the catalog.

### Scientific and machine-learning signals

[DeepChem](https://github.com/deepchem/deepchem) — upstream project behind the molecular machine-learning node family.

[PyMC](https://github.com/pymc-devs/pymc) — upstream project behind the probabilistic-programming refresh.

[PyMC peer-reviewed paper](https://doi.org/10.7717/peerj-cs.1516) — public research context for probabilistic programming evidence.

[PyTorch Lightning](https://github.com/Lightning-AI/pytorch-lightning) — upstream project behind neural training orchestration coverage.

[Qiskit quantum-computing paper](https://arxiv.org/abs/1707.03429) — public research context for quantum circuit programming.

[Scanpy](https://github.com/scverse/scanpy) — upstream project behind single-cell analysis coverage.

[Stable-Baselines3 JMLR paper](https://jmlr.org/papers/v22/20-1364.html) — peer-reviewed context for reinforcement-learning training.

[PyTorch Geometric paper](https://arxiv.org/abs/1903.02428) — graph neural network modeling context.

[Transformers library paper](https://aclanthology.org/2020.emnlp-demos.6/) — peer-reviewed context for transformer model engineering.

### Outside project and review signals

[Anthropic Skills](https://github.com/anthropics/skills) — upstream source repository for the brand-guidelines implementation record.

[Daily Patterns Pack](https://github.com/aplaceforallmystuff/daily-patterns-pack) — upstream repository behind the session-journaling implementation record.

[Ponytail](https://github.com/DietrichGebert/ponytail) — upstream repository for the Ponytail implementation record.

[Addy Osmani Agent Skills](https://github.com/addyosmani/agent-skills) — source repository for refreshed implementation, planning, and spec-driven development records.

[Obra Superpowers](https://github.com/obra/superpowers) — source repository for refreshed brainstorming and subagent-driven development records.

[GSD Build](https://github.com/gsd-build/get-shit-done) — source repository behind the refreshed execution-protocol record.

[Skill Fuse](https://github.com/gaia-research/skill-fuse) — upstream repository behind the skill-fuse record.

[Agentailor top agent skills review](https://blog.agentailor.com/posts/top-agent-skills-for-agentic-engineering-2026) — independent public review context for several refreshed agent-engineering records.

[Ponytail demo video](https://www.youtube.com/watch?v=2xuFcmUAQUc) — public demo signal for the Ponytail implementation record.

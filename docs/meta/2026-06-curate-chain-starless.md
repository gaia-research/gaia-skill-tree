---
title: "Chained Curation: Thirteen Starless References and a Unique Reclassification"
author: "gaia-curate-chain (automated curation pass)"
summary: A gated prompt-chaining curation pass adds 13 starless references and reclassifies feed-monitoring from Unique to Basic.
label: Curation Pass
abstract: |
  A six-link, gate-checked curation pass expanded the starless layer of the
  registry by thirteen generic references. The pass also surfaced a taxonomy
  correction: feed-monitoring, previously held as a Unique Skill, was
  reclassified to Basic once curation established a fusion path forward into a
  new Extra. This report records the full set of additions and focuses on the
  reasoning behind the feed-monitoring decision.
---

## Abstract

A six-link, gate-checked curation pass expanded the starless layer of the registry by thirteen generic references. The pass also surfaced a taxonomy correction: `feed-monitoring`, previously held as a Unique Skill, was reclassified to Basic once curation established a fusion path forward into a new Extra. This report records the full set of additions and focuses on the reasoning behind the `feed-monitoring` decision.

## Executive Summary

This pass was run as a prompt-chaining workflow: six sequential links, each handled by a fresh sub-agent, with a programmatic gate between every link. Evidence was gathered against arXiv, public repositories, and community sources; all thirty-nine source URLs were confirmed resolvable before the design link began. Every addition is a *starless* reference — a generic taxonomy node that carries no stars of its own and holds the shared, capability-level evidence pool its future named children inherit.

The headline taxonomy event of the pass was the reclassification of `feed-monitoring` from the **Unique** tier to **Basic**, detailed in §3.

## Additions

Thirteen starless references were added. Four are **Basic Skills**; nine are **Extra Skills** that draw on existing prerequisites already present in the graph.

| Reference | Tier | Prerequisites |
|-----------|------|---------------|
| time-series-forecasting | Basic | — |
| synthetic-data-generation | Basic | — |
| probabilistic-programming | Basic | — |
| cultural-localization | Basic | — |
| financial-modeling | Extra | statistical-analysis, data-analysis, generate-sql |
| supply-chain-optimization | Extra | statistical-analysis, data-analysis, detect-anomaly |
| causal-inference | Extra | statistical-analysis, hypothesis-generate, logical-inference |
| regulatory-compliance-mapping | Extra | knowledge-graph-build, extract-entities, security-audit |
| threat-intelligence-synthesis | Extra | feed-monitoring, knowledge-graph-build, security-audit |
| ontology-alignment | Extra | knowledge-graph-build, schema-design, extract-entities |
| explainability-audit | Extra | evaluate-output, statistical-analysis, data-visualize |
| edge-optimization | Extra | fine-tune, evaluate-output, performance-tuning |
| adversarial-robustness-testing | Extra | agent-eval, prompt-injection-defense, guardrails |

One candidate, `multi-modal-fusion`, was rejected at human review as redundant with the existing `multimodal-reasoning` reference. A second candidate, `probabilistic-programming`, was retained as distinct from `statistical-analysis`: it carries the Bayesian and uncertainty-quantification evidence pool (posteriordb, PyMC, Stan), keeping that material on the reference where it fits best.

## The feed-monitoring Reclassification

The defining property of a **Unique Skill** is the absence of a fusion path forward — it is a Basic that reached elite depth and has nowhere left to fuse. `feed-monitoring` had been held as a Unique on exactly that basis.

This pass changed that fact about the graph. The new Extra `threat-intelligence-synthesis` builds on `feed-monitoring` as a prerequisite: continuous monitoring of security and advisory feeds is the upstream input that threat-intelligence synthesis draws on, alongside `knowledge-graph-build` and `security-audit`. The moment that prerequisite edge exists, `feed-monitoring` has a fusion path forward — and a reference with a fusion path forward is, by definition, not a Unique.

The validation gate enforced this automatically. The first validation run after the additions failed with a single error:

> Unique skill 'feed-monitoring' is referenced as a prerequisite by another skill — unique skills must be graph-isolated.

Rather than route the new Extra around `feed-monitoring`, the correct fix was to update the stale fact: `feed-monitoring` was reclassified from Unique to Basic via `gaia dev reclassify feed-monitoring basic`, then wired as a prerequisite of `threat-intelligence-synthesis`. Validation then passed cleanly. The Unique count in the graph moved from three to two; the Basic count rose accordingly.

The lesson is that Unique status is not permanent — it is a statement that *no fusion path is known yet*. When curation discovers such a path, the honest action is to demote the reference and let it serve as a prerequisite, not to preserve its isolation artificially.

## Method and Gates

Each link advanced only after a programmatic check passed:

- **Scope** — enumerated the existing references and proposed research targets.
- **Research** — gathered evidence; all source URLs verified resolvable.
- **Design** — mapped candidates to tiers and prerequisites, forming an acyclic graph.
- **Human review** — accept / reject / reclassify decisions, including the rejection of `multi-modal-fusion`.
- **Mutation** — all changes applied through `gaia dev` commands; no hand-edited node files.
- **Ship** — regenerated docs and confirmed validation, manifest version lockstep, and a clean build.

All registry mutations were performed programmatically in keeping with the Programmatic-First policy.

## References

[1] Anthropic. (2025). *Building Effective Agents*. https://www.anthropic.com/engineering/building-effective-agents
[2] Gaia Registry. (2026). *CONTEXT.md — Tier and Stars Taxonomy*. Internal nomenclature reference.

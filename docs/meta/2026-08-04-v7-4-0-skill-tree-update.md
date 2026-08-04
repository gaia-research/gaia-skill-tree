---
title: "v7.4.0 Skill Tree Update: Backlog Closeout, Benchmark Sources, and Skill Surface Polish"
author: "Gaia Research"
summary: "A user-facing Skill Tree update for the v7.4.0 skill-tree cycle: backlog closeout, verified benchmark-source infrastructure, new and refreshed skills, and polish across Suite Explorer, Share Plaques, Trust Leaderboard, benchmarks, and Weekly Reports."
abstract: |
  This Skill Tree update summarizes the user-facing work that landed through the issue-backlog closeout and is being framed for the next v7.4.0 skill-tree cycle. It is a site post, not a package, tag, or PyPI release announcement.
  After PR #1395 merged, the automated sync published v7.3.8. PR #1430 then landed the 2026-32 Weekly Report first and advanced the main branch to v7.3.9 canary.
label: Skill Tree Update
---

## Abstract

This Skill Tree update closes the public narrative around the backlog merge: new and updated named skills, new generic skill coverage, benchmark-source infrastructure, and site polish across the main exploration surfaces. The important distinction for reviewers is version scope: this post is framed for the v7.4.0 skill-tree cycle and future-facing Skill Tree messaging, while the actual post-backlog package path moved through `v7.3.8`, then `v7.3.9` canary after the 2026-32 Weekly Report merge.

## Executive Summary

PR #1395 merged the issue-backlog integration to `main`, closed the backlog milestone, and triggered the automated artifact sync that published `v7.3.8`. PR #1430 followed first with the 2026-32 Weekly Report and advanced the main branch to `v7.3.9` canary before this v7.4.0 Skill Tree post returned for review. This post captures the user-facing Skill Tree and site changes from that merge without claiming that a package release already exists.

The merge directly closed four visible work items: Trust Leaderboard redesign (#868), skill-fuse repository surfaces (#1004), frontend performance pass (#1268), and the verified benchmark-source catalog (#1419). The Suite data and meta-audit follow-up (#1438) remains open, which is intentional: the new Suite Explorer behavior now makes missing or off-path suite metadata easier to see instead of hiding it behind a dense component rail.

## Visual Summary

The rendered report includes a compact release path, visual counts, and focus controls so reviewers can see the shape of the update before reading the full ledger. The visuals distinguish package state from communication state: `v7.3.8` shipped the backlog closeout, `v7.3.9` carries the Weekly Report 2026-32 handoff, and this post remains the held v7.4.0 Skill Tree narrative.

## Skill Tree Growth

### New named skills

The backlog closeout added a concentrated set of named skills, spanning brand governance, daily logging, hair-styling, scientific Python workflows, machine learning frameworks, chemistry tooling, quantum circuits, reinforcement learning, graph neural networks, transformers, and single-cell analysis.

| Contributor | New named skills |
|---|---|
| `anthropics` | `brand-guidelines` |
| `aplaceforallmystuff` | `log-to-daily` |
| `dietrichgebert` | `ponytail` |
| `k-dense-ai` | `deepchem`, `pymc`, `pytorch-lightning`, `qiskit`, `rdkit`, `scanpy`, `scvi-tools`, `stable-baselines3`, `torch-geometric`, `transformers` |

### Updated named skills

Several existing named skills also received public-facing updates or better Skill Tree alignment:

- `addy-osmani/incremental-implementation`, `addy-osmani/planning-and-task-breakdown`, and `addy-osmani/spec-driven-development`.
- `firecrawl/firecrawl-research-index`.
- `gaia-research/skill-fuse`, including repository surface work from #1004.
- `gsd-build/get-shit-done`.
- `obra/brainstorming` and `obra/subagent-driven-development`.

## Generic Skill Coverage

The merge broadened generic coverage for both practical workflow skills and scientific/ML capabilities. Newly added or updated generic skill nodes include a mix of `basic` and `fusion` nodes:

| Area | Generic nodes |
|---|---|
| Workflow and documentation | `brand-guideline-application` (`basic`), `prompt-caching` (`basic`), `session-journaling` (`basic`) |
| Scientific and computational work | `cheminformatics-analysis` (`fusion`), `molecular-machine-learning` (`fusion`), `quantum-circuit-programming` (`basic`), `single-cell-analysis` (`basic`), `single-cell-omics-modeling` (`fusion`) |
| Machine learning systems | `graph-neural-network-modeling` (`fusion`), `neural-training-orchestration` (`fusion`), `reinforcement-learning-training` (`fusion`), `transformer-model-engineering` (`fusion`) |
| Also updated | `probabilistic-programming` (`basic`), `test-driven-development` (`basic`) updates |

These nodes make the public graph more legible for users who arrive through a skill profile, search result, or contributor page: the Skill Tree now has stronger first-class vocabulary for benchmark-backed ML libraries, scientific analysis stacks, and prompt/cache/session workflow primitives.

## Benchmark Evidence Infrastructure

The biggest trust-infrastructure change is the verified benchmark-source catalog. The backlog closeout introduced a benchmark-source catalog and schema, benchmark-result schema updates, and public benchmark pages/API support. Together, these pieces create a safer path for future evidence ingestion: benchmark-result rows can point to approved benchmark sources instead of treating every benchmark claim as equally trustworthy.

This is infrastructure work, but it is user-facing in effect. The benchmark pages and API now have a clearer data model, and future trust reviews can distinguish a verified benchmark source from a vendor claim, a stale citation, or an unreviewed leaderboard scrape.

## Site Surface Polish

### Suite Explorer

Suite Explorer now preserves the distinction between Path/Fusion origin labels and Suite lens component labels. Path and Fusion views keep origin labels; the Suite lens switches rendered nodes to suite-component labels. The compact transparent outboard Suite Components rail is hidden by default, and row clicks focus graph nodes only.

That polish matters because it turns Suite Explorer into a better diagnostic surface. Missing or off-path suite data is easier to spot, which supports the still-open Suite data/meta-audit follow-up (#1438) instead of pretending the suite layer is complete.

### Share Plaques

Share Plaques received a rendering fix for modal and export paths. The modal now prefers inlined SVG, and the PNG raster scripts inline/transcode display-sized AOV medallions so PNG and HTML modal medallions render consistently. A follow-up hotfix capped inlined raster size after the initial OG PNG workflow failed, keeping the export path functional without ballooning assets.

### Trust Leaderboard and benchmark surfaces

The Trust Leaderboard redesign from #868 and the benchmark surface work from #1419 both received public polish and performance improvements. The result is less friction for users moving between contributor reputation, evidence, and benchmark-backed capability pages.

### Weekly Reports

Weekly Reports now use root-relative links for internal user-facing navigation while preserving absolute SEO/canonical metadata. This keeps local and deployed browsing paths stable without weakening search metadata.

## Closure Notes

This post is intentionally scoped to Skill Tree communication. It should be reviewed as a site-content update, not as a package release. The factual release state remains:

- PR #1395 merged the backlog integration and closed the issue-backlog work.
- The automated sync/tag path published `v7.3.8` as GitHub latest and PyPI latest. PR #1430 then landed Weekly Report 2026-32 and advanced main to `v7.3.9` canary.
- `v7.4.0` is the framing for this Skill Tree post, not a package/tag/PyPI release claim.
- #1438 remains open for Suite data and meta-audit follow-up.

## References

[1] PR #1395: issue-backlog integration merge and automated sync/tag to `v7.3.8`.

[2] Issues closed by #1395: #868 Trust Leaderboard redesign, #1004 skill-fuse repo surfaces, #1268 frontend performance pass, #1419 verified benchmark-source catalog.

[3] Follow-up still open: #1438 Suite data and meta-audit work.

[4] PR #1430: Weekly Report 2026-32, merged first and autosynced to `v7.3.9` canary.

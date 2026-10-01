# Gaia Curation Principles

This document defines the semantic principles governing candidate skill mapping, generic capability identity, and topology decisions in the Gaia Skill Tree.

The normative, versioned curation principles contract is packaged in:
[`src/gaia_cli/data/curation/principles.json`](../../src/gaia_cli/data/curation/principles.json) (`contractVersion: curation-principles-v1`, `rubricVersion: 1.0.0`).

---

## Packaged JSON Contract vs. Unresolved RFCs

In Gaia architecture, **the versioned packaged JSON contract represents canonical active doctrine**, whereas discussion threads and unmerged RFCs represent exploratory proposals:

1. **Source of Truth Doctrine:**
   - Active curation and semantic evaluation tools (`gaia dev assess`, `gaia dev prefill`, `scripts/curation_benchmark.py`) load and evaluate against `src/gaia_cli/data/curation/principles.json`.
   - The contract defines four immutable doctrine tenets:
     - *Similarity is not identity.*
     - *Popularity is not identity.*
     - *Packaging is not identity.*
     - *Trust is not topology.*
2. **Authority and Status of RFCs:**
   - Historical issues and unresolved RFCs (e.g., #1483 on product coupling, #1675 on context-mode retrieval, #1906 on probabilistic should vs. may, #1922 on assurance sensors) provide valuable context and debate history, but they **do not constitute active operational authority** until codified into the canonical schema or packaged JSON contract.
   - When evaluating candidates, agents and curators must adhere to the codified principles in `principles.json` and normative rules in `META.md` / `GOVERNANCE.md`, rather than treating speculative or unmerged RFC suggestions as enforceable policy.

---

## Core Semantic Principles Summary

The packaged contract defines eight semantic principles evaluated during candidate assessment:

| Principle | Core Doctrine | Operational Rule |
|---|---|---|
| **Identity** | Strip vendor/implementation details | A named implementation is not automatically a narrower generic. |
| **Transferability** | Independence from product vocabulary | Could another independent implementation satisfy this generic? Product coupling does not warrant purging. |
| **Relation** | Relational taxonomy | Classify relation to strongest generic as `same`, `narrower`, `broader`, `composite`, `orthogonal`, or `unknown`. |
| **Material Distinction** | Falsifiable behavioral difference | A split requires observable behavioral distinction, not merely different naming, framework, or CLI flags. |
| **Atomicity** | Universal primitives vs. compositions | `basic` has 0 prerequisites; `fusion` has >= 1. Do not infer capability structure from software packaging. |
| **Artifact Packaging** | Capability vs. distribution vehicle | Distinguish capabilities from suites, packages, routers, wrappers, or capstones. `suiteComponents` is not a generic identity. |
| **Overlap** | Rigorous neighbor comparison | Empty retrieval does not prove novelty; multiple high-cosine neighbors do not prove fusion. |
| **Topology Independence** | Invariance to popularity or trust | Contributor fame, stars, TM, and evidence abundance are excluded from topology decisions. Advice is SHOULD; human L4 decides MAY. |

---

## Machine Advice vs. Human Authority

All automated evaluations produced by `gaia dev prefill` or `gaia dev assess` default to non-authoritative machine proposals (`unknown` semantics by default when evidence is ambiguous). Only authorized human reviewers at the L4 curation gate hold ratification authority, recorded via `gaia dev ratify` with complete review attestation metadata.

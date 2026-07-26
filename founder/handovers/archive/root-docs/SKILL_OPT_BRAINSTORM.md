# Brainstorming SkillOpt Integration for Gaia Skill Bench (GSB)

This document explores how to incorporate Microsoft's **SkillOpt** technology (a text-space optimizer for agent skills) into the Gaia Skill Tree ecosystem, particularly for benchmarking named skills and defining a new optimization-based index.

---

## 1. Executive Summary: What is SkillOpt?

SkillOpt (Microsoft Research, 2026) treats a compact natural-language skill document (e.g., instructions, prompt files, or tool descriptions) as the **trainable state** of a frozen language agent. By keeping the target model weights fixed and optimizing the procedure instructions in text space, it behaves like a deep-learning optimizer but for prompts.

The core optimization loop works as follows:
1. **Rollout (Forward Pass):** The target agent runs on a batch of training tasks using the current skill instructions, generating execution trajectories (message logs, tool calls, and final scores).
2. **Reflect (Backward Pass / Gradients):** An optimizer model analyzes the trajectories. It separates success and failure minibatches to distill patterns of what to keep vs. what to correct.
3. **Bounded Edits (Optimizer Step):** The optimizer proposes add, delete, and replace edits (patches) to the skill document. These edits are constrained by an edit budget (the *textual learning rate*) to prevent prompt drift.
4. **Validation Gate (Accept/Reject):** The candidate skill document is evaluated on a held-out validation set. The edits are accepted only if the validation score strictly improves.
5. **Slow/Meta Updates (Momentum):** Long-horizon insights are consolidated at epoch boundaries to prevent cross-epoch forgetting.

---

## 2. Integrating SkillOpt for Gaia Skill Benchmarking

Currently, the **Gaia Skill Bench (GSB)** vision measures the skill itself along a 4-pillar formula:
*   **Performance (40%):** Success rate against a frozen taskset.
*   **Reliability (30%):** Consistency across repeated seeded runs.
*   **Triggering (20%):** Selectivity (fires when it should; stays silent for distractors).
*   **Efficiency (10%):** Resource utilization (tokens, steps, latency).

Applying SkillOpt's concepts to Gaia introduces three distinct opportunities:

### Opportunity A: Standardized Evaluation Harness (GSB Reference Runner)
Instead of executing tasks ad-hoc, the GSB runner can adapt SkillOpt's modular environment-adapter architecture.
*   **Input:** A named skill markdown file from `registry/named/**/*.md` (e.g., `mattpocock/diagnose.md`).
*   **Harness:** Extracts the instruction text, loads the frozen taskset, and rolls out the agent (target model + tools) in a deterministic, seeded sandbox.
*   **Output:** Captures step-by-step trace data and logs, directly feeding the GSB 4-pillar evaluator.

### Opportunity B: The "Trainability / Plasticity Index" (TPI)
Rather than scoring a skill solely on its static human-written version, we introduce a new benchmark index: **Trainability**.
*   **The Concept:** A truly robust skill is modular, clear, and highly optimizable. If we subject a named skill to $N$ epochs of text-space optimization, how much does it improve?
*   **Metric Components:**
    1.  **Baseline Score ($S_{base}$):** The score of the initial human-authored skill.
    2.  **Optimized Ceiling ($S_{opt}$):** The maximum score achieved after $N$ epochs of optimization.
    3.  **Optimization Gain / Plasticity ($\Delta S = S_{opt} - S_{base}$):** Measures how well the skill instruction set adapts to automated refinement.
    4.  **Convergence Rate ($\eta_{conv}$):** The number of epochs/steps needed to reach the optimized ceiling.
    5.  **Fragility Index ($F$):** The ratio of proposed edits to accepted edits. A fragile prompt will fail the validation gate repeatedly, whereas a structured, modular skill accepts edits cleanly.

### Opportunity C: The "Transferability Index" (TI)
SkillOpt research shows that skills trained on one model (e.g., Qwen-4B) can transfer to another (e.g., GPT-5.5) and still yield gains.
*   **The Index:** We optimize the skill document on a cheap, open-weight target model (Target A) using a training split. We then evaluate the resulting `best_skill.md` on a frontier target model (Target B) on a held-out test split.
*   **The Goal:** A high Transferability Index proves the skill encodes *general workflow logic* and *reusable procedural knowledge* rather than model-specific prompt-hacking or parameter overfitting.

---

## 3. Make vs. Buy: How to Implement SkillOpt in Gaia

We have two implementation paths:

### Path 1: Use `skillopt` As-Is (Import Microsoft's Package)
We install the `skillopt` package and wrap it as a dependency for our benchmark runner.
*   **How it works:** We write a custom benchmark adapter under `envs/` in our GSB repo that interfaces with Gaia's named skills and CLI. We run the training loop using the library's `ReflACTTrainer`.
*   **Pros:**
    *   Zero algorithm implementation overhead (the complex patch merge, edit clipping, and meta-learning mechanics are pre-written).
    *   Immediately inherits bugfixes, optimizations, and new model backend support from the upstream Microsoft repo.
*   **Cons:**
    *   **Heavy Dependency Footprint:** Installs PyTorch, Hugging Face `datasets`, Gradio, and multiple model SDKs, which bloats the lightweight `gaia_cli` install.
    *   **Configuration Incompatibility:** SkillOpt uses complex hierarchical YAML configurations (`configs/_base_`, etc.), whereas Gaia favors highly structured registry metadata (JSON schemas).
    *   **Auditability & Sandbox Constraints:** Running external codebase loops makes securing the CI execution environment harder.

### Path 2: Create "GSB-Opt" (Gaia's Native Lightweight Text-Space Optimizer)
We write a native, lightweight implementation of text-space optimization tailored to Gaia's registry schema.
*   **How it works:**
    *   We implement a minimalist python optimizer (e.g. `scripts/benchmarks/gsb_opt/`) that does not require deep learning packages.
    *   It relies on standard LLM clients (OpenAI/Anthropic APIs) to:
        1.  Parse the Markdown instruction blocks from `registry/named/**/*.md`.
        2.  Run rollout evaluations on tasks.
        3.  Generate diffs/patches using unified diff formats or JSON-structured edit proposals (`add`, `delete`, `replace` text ranges).
        4.  Apply edits natively via Python file manipulations and run validation splits.
*   **Pros:**
    *   **Ultra-lightweight:** Zero external library bloat. Can run natively in a simple virtualenv.
    *   **Gaia-Native Integration:** Directly reads/writes the YAML frontmatter and Markdown files of the registry.
    *   **Security & Determinism:** Built from the ground up to respect Gaia's reproducibility fingerprinting (`datasetHash` and `benchmarkInputHash`).
    *   **Custom Heuristics:** We can tune the optimizer's edit grammar to match developer skill file structures (e.g., targeting specific sub-headings like `## Instructions` or `## Tools` while keeping `## Overview` or `## Origin` frozen).
*   **Cons:**
    *   Requires writing and testing the diff/patch application logic and reflection parser from scratch.
    *   Missing advanced Microsoft Research features (e.g., hierarchical patch merging or cosine learning rate scheduling) in the initial release.

### Recommended Path: **The Hybrid Approach (Native GSB-Opt Core with Upstream Compatibility)**
We should **create our own lightweight runner (GSB-Opt)** as the official, zero-dependency Gaia benchmarking tool. 
However, we structure our skill inputs and evaluation datasets to be **100% compatible** with Microsoft's SkillOpt. 
*   This means any developer who wants to run high-powered optimization on their skill can export it, run the official `skillopt` package locally to tune it across 4 epochs, and then check the optimized `best_skill.md` back into Gaia.
*   Gaia's CI runner will execute a lightweight, deterministic validation pass to verify the final score and issue the `ci-reproduced` fingerprint.

---

## 4. The Proposed "Skill Trainability Index" Schema

To support this new index, we can add a new schema to `registry/schema/evidence/benchmark-result.schema.json` (or a separate schema for optimization-based benchmarks).

### Frontmatter/Row Representation in `registry/named/**/*.md`
An optimization benchmark result can be registered in the skill's `evidence` list:

```yaml
evidence:
  - type: benchmark-result
    benchmarkId: gsb-opt-trainability@v1.0
    score: 85.2
    unit: pct
    provenance: ci-reproduced
    attestor: https://github.com/gaia-research/gaia-skill-tree/actions/runs/987654@abc1234
    datasetHash: a8f9e6b4c3d2e1f0... # Hash of the GSB taskset
    benchmarkInputHash: d7e8f9a0b1c2d3e4... # Hash of taskset + prompt + target model config
    runAt: '2026-07-11T12:00:00Z'
    notes: "Baseline: 62.1% -> Optimized: 85.2% (+23.1% lift) over 3 epochs. Fragility: 12%."
    # Custom optimization metadata
    optimizationMetadata:
      baselineScore: 62.1
      optimizedScore: 85.2
      epochsRun: 3
      acceptedEdits: 4
      targetModel: qwen3.5-4b
      optimizerModel: gpt-5.5
```

---

## 5. Roadmap for SkillOpt & GSB Integration

Following the established post-Sprint D roadmap sequence, the integration is phased to ensure stability:

```
                  ┌────────────────────────────────────────┐
                  │            Sprint D Closes             │
                  │   (/benchmarks/ landing surface MVP)   │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │                Sprint E                │
                  │     (Skill Groups & External Benches)  │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │                Sprint F                │
                  │   (Monorepo Migration & frozen URLs)   │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │    "gaia-research" Website Launch      │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │    "gaia-skill-bench" Repo Bootstrap   │
                  │ (GSB-Opt reference harness & tasksets) │
                  └────────────────────────────────────────┘
```

1.  **Phase 0: GSB Taskset Definition (Sprint E):** Establish the frozen tasksets for different skill groups (e.g., code engineering, RAG, tool use).
2.  **Phase 1: Harness & Evaluation Integration (Sprint F):** Build the native target runner that executes named skills against GSB tasksets.
3.  **Phase 2: Local Optimization Command (`gaia dev optimize` - Post-Website Launch):** Ship the lightweight "GSB-Opt" reflection-edit loop so developers can optimize their skills locally.
4.  **Phase 3: The Trainability Index Rollout (Ongoing):** Run CI-certified optimization checks on incoming PRs to populate the registry with baseline and optimized benchmarks.

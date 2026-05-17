---
id: stanfordnlp/dspy
name: DSPy
contributor: stanfordnlp
origin: true
genericSkillRef: prompt-optimization
status: named
level: 3★
description: Declarative programming of language model pipelines, automatically optimizing prompts and RAG retrieval using bootstrapping and teleprompters.
title: "The Programmatic Prompt Engineer"
catalogRef: stanfordnlp-dspy
---

# DSPy

**The Programmatic Prompt Engineer**

Declarative programming of language model pipelines, automatically optimizing prompts and RAG retrieval using bootstrapping and teleprompters.

- **Generic Skill:** `prompt-optimization`
- **Contributor:** `stanfordnlp`
- **Status:** `named`
- **Level:** `3★`

## Description
DSPy is a framework for self-improving language model pipelines. It shifts from manual prompt engineering to a declarative programming model where you define modules and signatures, and DSPy's optimizers (teleprompters) automatically compile these into high-quality prompts or fine-tuned weights based on your training data and metrics.

## Key Features
- **Signatures:** Declarative specifications of input/output behavior.
- **Modules:** Reusable building blocks for LM programs (Predict, ChainOfThought, ProgramOfThought).
- **Optimizers (Teleprompters):** Algorithms that tune the prompt instructions and examples (BootstrapFewShot, MIPRO, COPRO).
- **Metric-Driven:** Automatically evaluates and iterates on pipeline performance.

## Links
- [GitHub Repository](https://github.com/stanfordnlp/dspy)
- [Research Paper (ArXiv)](https://arxiv.org/abs/2310.03714)

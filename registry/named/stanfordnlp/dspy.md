---
id: stanfordnlp/dspy
name: DSPy
contributor: stanfordnlp
origin: true
genericSkillRef: prompt-optimization
status: named
level: 4★
installable: false
description: Declarative programming of language model pipelines, automatically optimizing
  prompts and RAG retrieval using bootstrapping and teleprompters.
title: The Programmatic Prompt Engineer
catalogRef: stanfordnlp-dspy
createdAt: '2026-06-02'
updatedAt: '2026-06-19'
timeline:
- timestamp: '2026-06-02T01:44:00Z'
  action: demote
  contributor: unknown
  details: 'No installable code available (research framework); marked installable:
    false.'
- timestamp: '2026-06-02T23:48:18Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:21Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T09:21:47Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://arxiv.org/abs/2310.03714 (type: arxiv)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:29:08Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:34:47Z'
  details: TM 0.0 -> 100.0, grade ungraded -> A (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:39Z'
  details: TM 0.0 -> 100.0, grade ungraded -> A (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:45Z'
  details: TM 0.0 -> 100.0, grade ungraded -> A (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:38Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 1★ to 4★ per G7 final rankings calibration.
trustMagnitude: 100.0
overallTrustGrade: A
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
evidence:
- source: https://arxiv.org/abs/2310.03714
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: arxiv
  class: A
  notes: DSPy paper — ~700 citations as of 2026-06-19 (arXiv:2310.03714, ICLR 2024)
  citations: 700
verification:
  firstEvidenceAt: '2026-06-19T09:21:47Z'
trustMagnitudeInputHash: 379258625357acb056eaaf3a0ff982d04f9b5f903aed8b94ea0614b6277e2645
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

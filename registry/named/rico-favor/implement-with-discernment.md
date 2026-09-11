---
id: rico-favor/implement-with-discernment
name: implement-with-discernment
contributor: rico-favor
origin: false
genericSkillRef: implement-with-discernment
status: named
level: 1★
description: Applies deliberate judgment before writing code, evaluating whether
  to implement at all, scoping to the minimum needed, deferring or rejecting features
  that add complexity without proportionate value, and stopping when the task is done.
createdAt: '2026-07-09'
updatedAt: '2026-09-11'
title: Implement With Discernment
installable: false
timeline:
- timestamp: '2026-07-08T21:02:12Z'
  action: add
  contributor: unknown
  details: Added named skill rico-favor/implement-with-discernment
- timestamp: '2026-07-08T21:02:30Z'
  action: evidence_added
  contributor: unknown
  details: "Added evidence from https://github.com/rico-favor/gaia-skill-tree (type: repo-own)"
- timestamp: '2026-07-08T21:48:31Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 2★ to 1★
- timestamp: '2026-09-11T16:00:00Z'
  action: note
  contributor: mbtiongson1
  details: Restored from git history and recalibrated at 1★ baseline with substantive skill guidance
evidence:
- source: https://github.com/rico-favor/gaia-skill-tree
  evaluator: rico-favor
  date: '2026-07-09'
  type: self-attestation
  trustNumber: 10.0
  notes: Co-founder self-attestation of deliberate minimal implementation and anti-complexity workflows across Gaia engineering
verification:
  firstEvidenceAt: '2026-07-08T21:02:30Z'
---

# Implement With Discernment

Use this skill when evaluating, scoping, and executing code changes to ensure that software additions are necessary, bounded, and resistant to complexity creep.

## Core Philosophy

The primary cost of software is not writing code — it is reading, testing, debugging, securing, and maintaining it over time. Every new line of code is a liability until proven to deliver disproportionate value.

Discernment means applying rigorous restraint before touching code:
- **Do not write code when a design, process, or configuration choice solves the problem.**
- **Do not build for hypothetical futures.** Solve the immediate falsifiable problem.
- **Do not expand scope beyond the explicit boundaries of the task.**

## The Four Disciplines

### 1. The Necessity Gate ("Should this exist?")
Before writing code, answer three gating questions:
1. What breaks if we do nothing?
2. Can this be solved with existing primitives, standard library tools, or docs?
3. Does the proposed complexity pay for itself in immediate utility?

If the answer to (1) is "nothing critical" or (2) is "yes," do not write new code. Reject or defer the feature.

### 2. Surgical Scoping & Minimal Viable Diff
When implementation is required:
- Keep changes localized to the smallest possible blast radius.
- Do not opportunistically refactor adjacent files or "clean up" unrelated formatting.
- Prefer one targeted, readable edit over clever architectural abstractions.
- Avoid introducing new dependencies or runtime frameworks when a standard solution exists.

### 3. Kill Criteria & Restraint
Define upfront what you will **not** build:
- Establish explicit non-goals before opening the editor.
- Reject premature generalizations, dynamic plugin loaders, and multi-tenant abstractions for single-purpose tools.
- When an edge case is rare and expensive to handle in software, handle it via documentation, operational policy, or fail-fast assertion rather than intricate code branches.

### 4. Stopping When Done
- Stop immediately when the acceptance criteria are met and verified.
- Resist the temptation to add "just one more helper" or speculative options.
- Leave the codebase cleaner by minimizing surface area, not by maximizing code output.

## Pre-Commit Discernment Checklist

Before finalizing any implementation:
- [ ] Is every added line directly required by the specification?
- [ ] Could any newly added function be deleted without breaking correctness?
- [ ] Are we adding abstractions to solve a problem we only have once?
- [ ] Did we resist the urge to refactor code outside the scope of this fix?
- [ ] Is the diff legible and easy for a human reviewer to verify in under five minutes?

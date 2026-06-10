---
id: mattpocock/engineering
name: Engineering
contributor: mattpocock
origin: true
title: The Matt Pocock Engineering Discipline
genericSkillRef: engineering-discipline
status: named
level: 5★
description: Engineering category suite for Matt Pocock's skills.
createdAt: '2026-05-21'
updatedAt: '2026-06-10'
suiteRef: mattpocock/skills
suiteComponents:
- mattpocock/diagnose
- mattpocock/grill-with-docs
- mattpocock/improve-codebase-architecture
- mattpocock/prototype
- mattpocock/setup-matt-pocock-skills
- mattpocock/to-issues
- mattpocock/to-prd
- mattpocock/triage
- mattpocock/ubiquitous-language
- mattpocock/zoom-out
---

## Overview

The Matt Pocock Engineering Discipline is a suite of ten complementary skills that cover the full engineering workflow: orientation (Zoom Out, Triage), diagnosis (Diagnose), design review (Grill with Docs, Improve Codebase Architecture), decomposition (To PRD, To Issues), domain modelling (Ubiquitous Language), rapid validation (Prototype), and onboarding (Setup Matt Pocock Skills). The skills are designed to be used together — Zoom Out and Triage orient the agent, Diagnose drives a feedback-loop-first debugging discipline, To PRD and To Issues decompose work into tracked units, and Improve Codebase Architecture deepens modules using the domain glossary produced by Ubiquitous Language.

The defining principle across the suite is incremental grounding: every skill surfaces the domain vocabulary and constraints before generating output, so the agent's reasoning stays anchored to the actual codebase rather than to generic patterns.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.

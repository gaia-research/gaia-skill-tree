---
id: mattpocock/ubiquitous-language
name: Ubiquitous Language
contributor: mattpocock
origin: false
genericSkillRef: ubiquitous-language
status: named
title: "The Ubiquitous Language Mapper"
title: "The Domain Linguist"
catalogRef: mattpocock-ubiquitous-language
level: "4★"
description: Extracts and formalises a project's domain terminology into a shared glossary, enforcing consistent naming across code and conversations to eliminate ambiguity.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/ubiquitous-language/SKILL.md
tags:
  - domain-driven-design
  - ddd
  - ubiquitous-language
  - glossary
  - terminology
  - alignment
createdAt: "2026-05-15"
updatedAt: "2026-05-15"
suiteRef: "mattpocock/engineering"
---

## Overview

Ubiquitous Language brings Domain-Driven Design (DDD) principles to the AI agent workflow. The agent scans the conversation and codebase to identify domain-relevant nouns and verbs, proposing a canonical glossary that is persisted to `CONTEXT.md`.

Once established, the agent uses this language as a "source of truth," ensuring that new code, variable names, and architectural decisions align with the business domain. This reduces token waste by eliminating the need for repeated explanations and prevents "software entropy" where jargon diverges from intent.

## Origin

Released by @mattpocock as part of the "Skills for Real Engineers" suite.

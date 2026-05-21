---
id: mattpocock/edit-article
name: Edit Article
contributor: mattpocock
origin: false
genericSkillRef: document-editing
status: named
title: "The Article Editor"
title: "The Section-by-Section Rewrite"
catalogRef: mattpocock-edit-article
level: "2★"
description: Edits articles by first sectioning them as a DAG of information dependencies, confirming the section order, then rewriting each section for clarity and flow with a 240-character-per-paragraph constraint.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/personal/edit-article/SKILL.md
tags:
  - article-editing
  - prose-rewrite
  - information-dag
  - section-structure
  - clarity
createdAt: "2026-04-30"
updatedAt: "2026-04-30"
suiteRef: "mattpocock/personal"
---

## Overview

Edit Article models an article as a directed acyclic graph of information dependencies: each section can only introduce concepts that prior sections have established. Before rewriting anything, the agent divides the article into dependency-ordered sections and confirms the structure with the author. It then rewrites section by section, enforcing a 240-character maximum per paragraph to keep prose dense and scannable.

## Origin

Published by @mattpocock (Matt Pocock, Total TypeScript). Named implementation of the `document-editing` skill bucket for long-form article editing (origin: anthropic/pptx).

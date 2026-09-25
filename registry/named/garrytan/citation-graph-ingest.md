---
id: garrytan/citation-graph-ingest
name: citation-graph-ingest
contributor: garrytan
origin: false
genericSkillRef: knowledge-graph-build
status: named
level: 2★
description: 'Build a TYPED citation/reference graph over an ingested corpus — not
  just

  embeddings. Flat similarity retrieval cannot tell you that document A

  *overrules* B, *distinguishes* C, or *relies_on* D. This skill extracts every

  inter-document reference, classifies the edge TYPE with LLM judgment, and

  writes first-class typed edges via `gbrain link`, so `gbrain graph-query

  --type` can walk the argument ("everything this brief relies on, minus

  anything overruled since"). Every cite-heavy corpus is the same shape: law,

  academic papers, patents, regulatory filings, a book''s bibliography.'
createdAt: '2026-09-23'
updatedAt: '2026-09-23'
title: citation-graph-ingest
links:
  github: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/citation-graph-ingest/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:06Z'
  action: add
  contributor: unknown
  details: Added named skill garrytan/citation-graph-ingest
---

## Installation
Add installation instructions here.

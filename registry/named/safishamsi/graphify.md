---
id: safishamsi/graphify
name: Graphify
contributor: safishamsi
origin: true
genericSkillRef: knowledge-graph-build
status: named
title: The Structural Muse
level: 1★
description: Maps codebases and documentation into a queryable knowledge graph using
  AST analysis and semantic extraction.
links:
  github: https://github.com/safishamsi/graphify
tags:
- knowledge-graph
- rag
- ast
createdAt: '2026-05-14'
updatedAt: '2026-06-19'
timeline:
- timestamp: '2026-06-02T23:48:24Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:21Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T09:19:58Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/safishamsi/graphify (type: github-stars-own)'
- timestamp: '2026-06-19T09:22:28Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://arxiv.org/abs/2408.03910 (type: arxiv)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:29:08Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:34:47Z'
  details: TM 0.0 -> 86.57, grade ungraded -> B (direct edit -- CLI gap)
trustMagnitude: 86.57
overallTrustGrade: B
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
- source: https://github.com/safishamsi/graphify/stargazers
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: github-stars-own
  class: A
  notes: 68,766 GitHub stars as of 2026-06-19 (verified via firecrawl validation report;
    standalone skill)
  stars: 68766
- source: https://arxiv.org/abs/2408.03910
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: arxiv
  class: A
  notes: GraphRAG / knowledge graph paper — ~89 citations as of 2026-06-19 (arXiv:2408.03910)
  citations: 89
verification:
  firstEvidenceAt: '2026-06-19T09:19:58Z'
trustMagnitudeInputHash: 301014660931c34ae8ce9092ffc4c080d0ae5051871a9d3d9ffd50e7a7f5aceb
---

## Overview

Graphify is a memory layer for AI agents that transforms unstructured project data into a structured knowledge graph. By combining tree-sitter for code structural analysis with LLMs for semantic extraction, it enables assistants to perform deep architectural queries and maintain long-term context across large repositories.

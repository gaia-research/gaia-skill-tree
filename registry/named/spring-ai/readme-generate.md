---
id: spring-ai/readme-generate
name: REST API README Generator
contributor: spring-ai
origin: false
genericSkillRef: write-report
status: named
title: The Endpoint Scribe
catalogRef: spring-ai-readme-generate
level: 2★
description: Scans a Java Spring project for controller annotations, extracts REST
  API endpoint definitions, and automatically generates structured API documentation
  in README format.
links:
  github: https://github.com/spring-ai-alibaba/examples/blob/main/.claude/skills/readme-generate/SKILL.md
tags:
- java
- spring
- rest-api
- documentation
- readme
createdAt: '2026-04-30'
updatedAt: '2026-06-14'
evidence:
- class: B
  source: https://github.com/spring-ai-alibaba/examples/blob/main/.claude/skills/readme-generate/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: Published implementation in the Spring AI Alibaba examples repository; reproducible
    from SKILL.md. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-10T05:38:19Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/spring-ai-alibaba/examples/blob/main/.claude/skills/readme-generate/SKILL.md
- timestamp: '2026-06-14T12:33:03Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/spring-ai-alibaba/examples/blob/main/.claude/skills/readme-generate/SKILL.md
    as B (trustNumber: 70.0)'
---

## Overview

REST API README Generator by Spring AI Alibaba specializes in Java Spring Boot projects. The agent uses AST analysis to locate `@RestController`, `@GetMapping`, `@PostMapping`, and related annotations, extracts endpoint paths, HTTP methods, request/response types, and generates a formatted README with a complete API reference table.

## Notes

This is a specialization of the `write-report` skill focused on Java Spring REST API documentation. The origin implementation for this bucket is `glincker/readme-generator` (general-purpose README generation).

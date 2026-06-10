---
id: ruvnet/v3-ddd-architecture
name: V3 DDD Architecture
contributor: ruvnet
origin: false
role: variant
genericSkillRef: ubiquitous-language
status: named
title: The Domain Sculptor
catalogRef: ruvnet-v3-ddd-architecture
level: 2★
description: Applies Domain-Driven Design principles to the Ruflo v3 architecture
  including bounded contexts, aggregate roots, domain events, and ubiquitous language.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- ddd
- domain-driven-design
- bounded-contexts
- aggregate-roots
- v3-sprint
createdAt: '2026-05-19'
updatedAt: '2026-06-10'
suiteRef: ruvnet/ruflo-v3
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: Part of the Ruflo orchestration platform (public repo); DDD restructuring
    of the v3 codebase documented in the suite.
timeline:
- timestamp: '2026-06-10T05:38:18Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/ruvnet/ruflo
---

## Overview

V3 DDD Architecture applies Domain-Driven Design methodology to the Ruflo v3 codebase restructuring. It establishes bounded contexts for the core orchestration, memory, plugin, and agent domains. Aggregate roots encapsulate domain logic, domain events enable decoupled cross-context communication, and ubiquitous language ensures consistent terminology across code, docs, and team communication.

## Key Capabilities

- **Bounded context definition**: explicit separation of orchestration, memory, plugin, and agent domains
- **Aggregate root design**: domain logic encapsulation with clear ownership boundaries
- **Domain event modeling**: decoupled cross-context communication via typed domain events
- **Ubiquitous language establishment**: consistent terminology across code, documentation, and team communication

## Origin

Published by @ruvnet as a variant implementation for the `ubiquitous-language` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

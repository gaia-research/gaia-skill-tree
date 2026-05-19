---
id: ruvnet/swarm-orchestration
name: Swarm Orchestration
contributor: ruvnet
origin: true
genericSkillRef: swarm-topology-management
status: named
title: "The Topology Architect"
catalogRef: ruvnet-swarm-orchestration
level: "3★"
description: Initializes and manages multi-agent swarm network topologies (hierarchical, mesh, ring, star) with automatic load balancing, fault tolerance, and shared memory coordination.
links:
  github: https://github.com/ruvnet/ruflo
tags:
  - swarm
  - topology
  - multi-agent
  - load-balancing
  - fault-tolerance
createdAt: "2026-05-19"
updatedAt: "2026-05-19"
suiteRef: "ruvnet/ruflo"
---

## Overview

Swarm Orchestration provides foundational swarm network topology management for multi-agent systems. It supports four topology patterns: hierarchical for centralized coordination, mesh for peer-to-peer equality, ring for sequential processing, and star for delegation. The system handles load balancing through performance-based agent selection and provides built-in fault tolerance with retry logic and task reassignment.

## Key Capabilities

- **4 topology patterns**: hierarchical, mesh, ring, and star agent network configurations
- **Load balancing**: performance-based agent selection and dynamic work distribution
- **Fault tolerance**: retry logic and automatic task reassignment on agent failure
- **Shared memory coordination**: cross-agent context sharing for coherent swarm behavior
- **Real-time performance monitoring**: live agent health and throughput metrics

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `swarm-topology-management` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

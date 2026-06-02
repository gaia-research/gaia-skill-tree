---
id: ruvnet/flow-nexus-neural
name: Flow Nexus Neural
contributor: ruvnet
origin: true
genericSkillRef: distributed-neural-training
status: named
title: The Neural Conductor
catalogRef: ruvnet-flow-nexus-neural
level: 3★
description: Trains neural networks across distributed E2B sandbox clusters with support
  for feedforward, LSTM, GAN, autoencoder, and transformer architectures, federated
  learning, and a model marketplace.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- neural-training
- distributed
- federated-learning
- e2b
- model-marketplace
createdAt: '2026-05-19'
updatedAt: '2026-05-19'
suiteRef: ruvnet/flow-nexus
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-05-19'
  notes: Ruflo orchestration platform — 34k+ GitHub stars.
---

## Overview

Flow Nexus Neural enables training and deployment of neural networks in distributed E2B sandbox environments. Users can train across multiple architectures (feedforward, LSTM, GAN, autoencoder, transformer) with five resource tiers, deploy distributed training clusters using mesh/ring/star/hierarchical topologies, and publish trained models to the template marketplace. Federated learning keeps data localized on nodes while enabling collaborative training.

## Key Capabilities

- **Multi-architecture neural training**: feedforward, LSTM, GAN, autoencoder, and transformer (5 types)
- **Distributed cluster training**: mesh, ring, star, and hierarchical topology options across E2B sandboxes
- **Federated learning**: data-localized collaborative training across distributed nodes
- **Model marketplace publishing**: trained model deployment and template sharing

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `distributed-neural-training` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

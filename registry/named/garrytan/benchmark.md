---
id: garrytan/benchmark
name: Benchmark
contributor: garrytan
origin: false
genericSkillRef: evaluate-output
status: named
title: "Gstack Benchmark"
catalogRef: garrytan-benchmark
level: "4★"
description: Web performance benchmarking that captures baseline metrics, compares current performance against those baselines, and identifies regressions in load times, Core Web Vitals, and bundle sizes across specified pages.
links:
  github: https://github.com/garrytan/gstack/blob/main/benchmark/SKILL.md
tags:
  - performance
  - benchmarking
  - core-web-vitals
  - regression
suiteRef: "garrytan/gstack"
createdAt: "2026-05-18"
updatedAt: "2026-05-18"
---

## Overview

Gstack Benchmark measures web application performance end to end. It captures a baseline across target pages on first run, then compares every subsequent run against that baseline — surfacing regressions in Time to First Byte, Largest Contentful Paint, Total Blocking Time, and bundle size before they reach production.

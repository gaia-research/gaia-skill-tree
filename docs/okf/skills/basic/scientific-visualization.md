---
type: "AI Agent Skill"
title: "Scientific Visualization"
description: "Creates publication-ready scientific figures and visualizes molecular structures."
resource: "https://gaia.tiongson.co/codex.html#scientific-visualization"
tags: ["gaia-skill-tree", "basic-skill"]
timestamp: "2026-06-02T00:00:00Z"
---

# Scientific Visualization

## Description

Creates publication-ready scientific figures with multi-panel layouts, statistical annotations, colorblind-safe palettes, and journal-specific formatting (Nature, Science, Cell) using matplotlib, seaborn, and plotly. It also includes visualizing, analyzing, and rendering protein and molecular structures without a hardware-accelerated GUI.

## Use Case

A developer wants to create images of a protein structure, highlight specific binding sites, or perform structural alignments. They would use PyMOL in a headless OSMesa environment to render these images as PNGs, saving the corresponding `.pse` sessions for later inspection in a local GUI.

## Directives

When running PyMOL, always set `PYOPENGL_PLATFORM=osmesa` for software rendering and avoid `cmd.draw()` or `cmd.ray()` with hardware acceleration. Always call `cmd.quit()` at the end of scripts to prevent process hangs, and always save a `.pse` session alongside `.png` outputs.

## Derivatives

- [Scientific Writing](/skills/extra/scientific-writing.md)


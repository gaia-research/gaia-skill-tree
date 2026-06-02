# /scientific-visualization
**ID:** scientific-visualization  
**Type:** Basic Skill  
**Rank:** _rank-less generic reference — stars are earned by named implementations_  
**Skill Call:** `/scientific-visualization`

---

**Summary:** Creates publication-ready scientific figures and visualizes molecular structures.

## Description
Creates publication-ready scientific figures with multi-panel layouts, statistical annotations, colorblind-safe palettes, and journal-specific formatting (Nature, Science, Cell) using matplotlib, seaborn, and plotly. It also includes visualizing, analyzing, and rendering protein and molecular structures without a hardware-accelerated GUI.

## Use Case
A developer wants to create images of a protein structure, highlight specific binding sites, or perform structural alignments. They would use PyMOL in a headless OSMesa environment to render these images as PNGs, saving the corresponding `.pse` sessions for later inspection in a local GUI.

## Directives
When running PyMOL, always set `PYOPENGL_PLATFORM=osmesa` for software rendering and avoid `cmd.draw()` or `cmd.ray()` with hardware acceleration. Always call `cmd.quit()` at the end of scripts to prevent process hangs, and always save a `.pse` session alongside `.png` outputs.

## Prerequisites
_None._

## Unlocks
- [Scientific Writing](../extra/scientific-writing.md)

## Named Implementations
_None yet — be the first to claim this skill._

## Evidence (inherited capability)
_Capability-level evidence for this generic reference. Every named implementation above inherits it._

_None._

## Known Agents
_None verified yet._

---

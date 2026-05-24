# /scientific-visualization  [2★ · Named]
**ID:** scientific-visualization  
**Type:** Basic Skill  
**Level:** 2★  
**Tier:** Named  
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

## Evidence
| Class | Source | Evaluator | Date |
|---|---|---|---|
| B | https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/scientific-skills/scientific-visualization/SKILL.md | mbtiongson1 | 2026-04-30 |
| B | https://github.com/google-deepmind/science-skills/blob/main/skills/pymol/SKILL.md | unknown | 2026-05-23 |
| B | https://github.com/google-deepmind/science-skills/blob/main/skills/pymol/SKILL.md | unknown | 2026-05-23 |

## Known Agents
_None verified yet._

---

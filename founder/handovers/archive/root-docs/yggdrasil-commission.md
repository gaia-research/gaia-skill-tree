# Yggdrasil 3D Shell — Commission Specification

**Target:** Merge into PR #1125 (`design/homepage-gaia-tree-hero`).
**Purpose:** Purely visual "golden tree of light" 3D shell to encompass the node DAG on the homepage hero.

## 1. Visual Direction & Aesthetic
* **Shape (Organic 3D Topology):** Massive, towering world tree with highly organic, twisting, and randomized branching.
* **Style (Minimal 3D Wireframe):** The model must read as a pure 3D wireframe projection. No solid fills, no dense flat patterns, and absolutely NO runes or symbols. Less is more. It should use sparse, minimal contour lines that define realistic 3D wood volume and twisting topology, rather than looking like a flat 2D drawing.
* **Foliage:** Minimalist clustering, adhering to the pure wireframe aesthetic.

## 2. Technical Deliverables (The Handoff)
To guarantee 60fps performance on mobile web, this asset relies on a strict split between artist geometry and developer shaders.

### A. The Artist Deliverable (`yggdrasil-shell.glb`)
* **Format:** `.glb` (GLTF Binary).
* **Contents:** The static geometry of the trunk, branches, and leaf clusters. 
* **Constraint:** The model must be low-poly, clean vector-like mesh, and entirely static. No baked animations for wind or falling leaves.

### B. The Code Deliverable (Three.js WebGL)
* **Rustling Leaves (Wind):** We will not bake animation into the file. Instead, we will write a custom **Vertex Shader** in Three.js that slightly displaces the leaf vertices using a sine wave over time. This makes the tree feel alive and realistic with virtually zero CPU cost.
* **Falling Leaves (Particles):** A lightweight `THREE.Points` system spawned around the canopy coordinates, allowing leaves to drift down dynamically.
* **Exploration Opacity:** The wireframe material will be configured with `transparent: true`. When the user enters "Explore in 3D" mode, the code will smoothly tween the entire shell's opacity down (e.g., to 15%) so the interactive DAG nodes remain the primary focus.

## 3. Mockup Reference
- **Final Mockup Image:** `assets/workbench/generated/yggdrasil-mockup-final.png`

## 4. Garbage Collection
Once the final `.glb` is acquired and integrated, the generated mockup image file will remain in the gitignored directory and should not be committed to the repo, ensuring we don't bloat the git history.

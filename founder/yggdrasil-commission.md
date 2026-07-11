# Yggdrasil 3D Shell — Commission Specification

**Target:** Merge into PR #1125 (`design/homepage-gaia-tree-hero`).
**Purpose:** Purely visual "golden tree of light" 3D shell to encompass the node DAG on the homepage hero.

## 1. Visual Direction & Aesthetic
* **Shape (Acacia-like):** A thick, ancient, massive central trunk that splays out into a broad, flat, umbrella-like canopy (Acacia tree silhouette). This perfectly complements the wide horizontal spread of the upper DAG nodes.
* **Material:** A translucent, glowing "hologram of light" or ethereal semi-transparent golden mesh. It should not look like physical brown wood; it must look sacred, digital, and woven from light.
* **Foliage:** Aspen-gold leaves. These should cluster around the upper canopy, catching the light and shimmering.

## 2. Technical Deliverables (The Handoff)
This commission is split into two halves to ensure optimal WebGL performance and file size:

### A. The Artist Deliverable (`yggdrasil-shell.glb`)
* **Format:** `.glb` (GLTF Binary).
* **Contents:** The static geometry of the thick trunk, the sweeping acacia branches, and static clusters of aspen-gold leaves.
* **Constraint:** The model must be entirely static (no baked animations) and relatively low-poly to ensure fast web loading. The material should be set up to accept emissive (glowing) textures in Three.js.
* **Alignment:** The artist does not need to perfectly wrap the specific JSON DAG nodes. A generalized wide-canopy Acacia shape is sufficient. We will scale the `.glb` within Three.js to roughly encompass the node coordinates.

### B. The Code Deliverable (Three.js Particle System)
* **Falling Leaves:** Because `.glb` files cannot natively store dynamic particle physics, the falling golden leaves will be implemented directly in `docs/js/skill-graph.js`.
* **Implementation:** A `THREE.Points` or `THREE.InstancedMesh` system will be spawned at the top Y-coordinates of the canopy, simulating slow, glowing golden leaves drifting downward through the DAG. 

## 3. Mockup Reference
*(To be generated via `mockup-iteration` and linked here. The mockup will be stored in a gitignored `assets/workbench/generated/` folder.)*

- **Prompt used:** `[PENDING]`
- **Reference Image:** `[PENDING]`

## 4. Garbage Collection
Once the final `.glb` is acquired and integrated, the generated mockup image files will remain in the gitignored directory and should not be committed to the repo, ensuring we don't bloat the git history.
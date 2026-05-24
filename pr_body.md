## 4D ML Hyper-Atlas Integration

This PR integrates the 4D ML Hyper-Atlas into the Gaia skill graph, transitioning the registry from deterministic layouts to a 4D PCA-based semantic view.

### Key Features
- **4D Hyper-Atlas Engine:** Added 4D rotation matrices and hyperspace perspective projection to `skill-graph.js`.
- **Automated Data Pipeline:** Integrated `scripts/build_layouts_3d.py` into the build pipeline. PCA coordinate generation is now automatic.
- **Rank-Based Geometry:** Switched to rank-based exponential node sizing (1★-6★).
- **HUD/UI Overhaul:**
    - Consolidated controls into a right-aligned header.
    - Implemented a floating, draggable Collection panel (maximized by default).
    - Added Orbit/Pan interaction toggle.
    - Cleaned up visuals: removed stars, nebula, and SVG download button.
- **Skill Modal:** Repositioned to appear at the top-right of the selected node.

### Verification
- Full project build and asset sync completed.
- CSS tokens and graph rendering validated.
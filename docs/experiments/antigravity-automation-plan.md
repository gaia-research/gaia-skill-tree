# Antigravity Automation Plan: Semantic Atlas Orchestration

## Objective
Transition the Gaia skill graph from a static, tier-based deterministic layout to a dynamic, ML-driven **Semantic Atlas**. This ensures conceptual neighbors (e.g., `web-search` and `scrape-html`) sit near each other regardless of their tier, revealing the true "shape" of agent capabilities.

## Antigravity SDK Integration

### 1. Triggers (The Pulse)
We will leverage SDK Triggers to keep the graph "alive" with every contribution:
*   **`ReviewMergeTrigger`**: Fires whenever a PR from a `review/` branch is merged into `main`. This is the primary signal that the canonical graph has evolved.
*   **`RegistryIntakeTrigger`**: Fires when a new PR is opened via `gaia push`. The agent can generate a "Preview Layout" to show the contributor where their new skill will land in the semantic constellation.
*   **`StaleEvidenceTrigger`**: Fires periodically (e.g., `every(7, days)`) to re-evaluate embeddings if skill descriptions are updated without a version bump.

### 2. The "Atlas Architect" Agent (The Brain)
A Layer 1 Antigravity Agent configured with the following:
*   **System Instructions**: "You are the Gaia Atlas Architect. Your goal is to optimize the 3D layout of the skill registry to maximize semantic clarity and discoverability. Use OKLCH color strategies for domain clusters."
*   **Capabilities**: `CapabilitiesConfig(allow_writes=True)` for updating `docs/graph/gaia.json` and `registry/similarity.json`.

### 3. Workflow Hooks (The Guardrails)
To prevent the ML layout from becoming unreadable, we implement the following SDK Hooks:
*   **`inspect` (Readability Check)**: Before committing new coordinates, the agent must verify that no two nodes occupy the same 3D coordinate space (Collision Detection).
*   **`decide` (Review Gate)**: If the ML layout moves more than 20% of the nodes significantly, the agent must `ask_user()` for approval before overwriting the production layout.
*   **`transform` (Visual Branding)**: Automatically injects Gaia design tokens (`--tier-*`, `--apex-gold`) into the generated graph metadata.

## ML Architecture Implementation
Instead of the current `build_layouts.py` (which is 2D and bag-of-words based), the Antigravity Agent will run:
1.  **Embedding**: Use `sentence-transformers` (`all-MiniLM-L6-v2`) to generate 384D vectors from skill names + descriptions.
2.  **Projection**: Use **UMAP** (Uniform Manifold Approximation and Projection) to reduce 384D to 3D `(x, y, z)`.
3.  **Clustering**: Run **HDBSCAN** to detect "Skill Domains" and assign cluster IDs.
4.  **Edge Weighting**: Weight edges in the 3D projection based on prerequisite lineage.

## Implementation Timeline
1.  **Phase 1**: Implement `scripts/ml_layout_3d.py` (Pure Python + NumPy).
2.  **Phase 2**: Define the Antigravity `Agent` and `Triggers` in `.agents/skills/gaia-atlas-architect/`.
3.  **Phase 3**: Wire the trigger to GitHub Actions / Webhooks for automated re-calculation on merge.

# Handover: PR-6 — Narrow-Path Tree Rendering Fix (#642)

**Type:** CLI / Formatting  
**Branch:** `fix/narrow-tree-render`  
**Resolves #642**  

## Context
When generating a `skill-tree.md` file (e.g., via `gaia share` or explicit exports), the current logic accidentally renders the full canonical tree rather than the precise, narrow path of the specific skill bundle snapshot. 

## Objectives
1. **Scope the Renderer**: Update the markdown generation logic (likely in `src/gaia_cli/treeManager.py` or formatting logic) to traverse only the nodes included in the provided snapshot/bundle.
2. **Exclude Unrelated Siblings**: Ensure unrelated skills from the wider canonical tree do not bleed into the output.

## Definition of Done
- A generated `skill-tree.md` accurately reflects only the targeted skill path.
- Unit tests cover the scoping logic.
- PR resolves `#642`.

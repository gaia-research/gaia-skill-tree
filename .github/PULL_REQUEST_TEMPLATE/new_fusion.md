## New Fusion Recipe

### Fusion Details
- **Source Skills:** `skillA`, `skillB`, ...
- **Target Skill:** `targetSkillId`
- **Edge Type:** `prerequisite` / `corequisite` / `enhances`
- **Level Floor:** I / II / III / IV / V
- **Condition:** What must be true for this fusion to activate.

### Rationale
Explain why this combination of source skills should unlock the target skill. Provide evidence or reasoning for the level floor.

### Evidence References
List evidence entries from the target skill that support this specific fusion path:
- `targetSkillId#evidence[0]`

### Checklist

**Contributor:**
- [ ] All source skill IDs exist in `gaia.json`.
- [ ] Target skill ID exists in `gaia.json`.
- [ ] Edge records added to the `edges` array in `gaia.json`.
- [ ] Level floor is justified — source skills must be at this level or above.
- [ ] I have run `gaia validate` locally and it passes.

**Reviewer:**
- [ ] **Validity:** The fusion path is plausible and evidence-backed.
- [ ] **Level floor:** Appropriate for the claimed combination.
- [ ] **Graph integrity:** No cycles introduced.
- [ ] **No duplicates:** This fusion path doesn't already exist.

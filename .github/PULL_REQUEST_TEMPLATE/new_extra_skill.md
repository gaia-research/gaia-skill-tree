## New Extra Skill

### Skill Details
- **ID:** `skillId`
- **Name:** Skill Name
- **Level:** II / III / IV / V
- **Prerequisites:** `parentA`, `parentB`, ...
- **Description:** Clear, agent-agnostic definition of the emergent capability.
- **Fusion Condition:** What must be true for this combination to work.

### Evidence
| Class | Source | Evaluator | Date | Notes |
|---|---|---|---|---|
| B / A | URL | username | YYYY-MM-DD | Brief description |

### Rationale
Explain why these specific prerequisites produce this emergent behavior. What capability exists in the composite that does not exist in any individual parent?

### Checklist

**Contributor:**
- [ ] Skill ID uses `kebab-case` with no vendor references.
- [ ] Description describes an emergent capability, not just "all parents at once."
- [ ] At least 2 prerequisites listed, all referencing existing skill IDs in `gaia.json`.
- [ ] Evidence meets the minimum threshold for the claimed level (Level III = Class B+).
- [ ] Fusion condition is specified if applicable.
- [ ] I have run `gaia validate` locally and it passes.
- [ ] I have NOT edited any files in `skills/`, `registry.md`, or `combinations.md`.

**Reviewer:**
- [ ] **Correctness:** Definition is precise and non-overlapping.
- [ ] **Compositional validity:** Parents plausibly produce the claimed emergent behavior.
- [ ] **Evidence quality:** Sources are reproducible and correctly classified.
- [ ] **Classification quality:** Level and rarity justified with rationale.
- [ ] **Graph integrity:** No cycles, missing references, or orphaned nodes.
- [ ] **Naming:** ID follows conventions, is agent-agnostic.

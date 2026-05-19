## New Basic Skill

### Skill Details
- **ID:** `skillId`
- **Name:** Skill Name
- **Level:** I / II / III / IV / V
- **Description:** Clear, agent-agnostic definition of the capability.

### Evidence
| Class | Source | Evaluator | Date | Notes |
|---|---|---|---|---|
| C / B / A | URL | username | YYYY-MM-DD | Brief description |

### Checklist

**Contributor:**
- [ ] Skill ID uses `kebab-case` with no vendor references.
- [ ] Description is precise, falsifiable, and non-overlapping with existing skills.
- [ ] Evidence meets the minimum threshold for the claimed level.
- [ ] `prerequisites` array is empty (basic skills have no parents).
- [ ] `derivatives` array lists known child skills (if any).
- [ ] I have run `gaia validate` locally and it passes.
- [ ] I have NOT edited any files in `skills/`, `registry.md`, or `combinations.md`.

**Reviewer:**
- [ ] **Correctness:** Definition is precise and non-overlapping.
- [ ] **Evidence quality:** Sources are reproducible and correctly classified.
- [ ] **Classification quality:** Level and rarity justified.
- [ ] **Graph integrity:** No invalid references or cycles.
- [ ] **Naming:** ID follows conventions, is agent-agnostic.

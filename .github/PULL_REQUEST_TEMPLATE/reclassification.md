## Reclassification Request

### Target Skill
- **ID:** `skillId`
- **Current Level:** X → **Proposed Level:** Y
- **Current Rarity:** X → **Proposed Rarity:** Y (if applicable)

### Justification
Explain why the current classification is incorrect or outdated. Reference new evidence, updated benchmarks, or changed agent landscape.

### New Evidence (if applicable)
| Class | Source | Evaluator | Date | Notes |
|---|---|---|---|---|
| B / A | URL | username | YYYY-MM-DD | Brief description |

### Checklist

**Contributor:**
- [ ] Justification references concrete evidence, not opinion.
- [ ] If upgrading level, new evidence meets the threshold for the target level.
- [ ] If downgrading, explanation of why previous evidence no longer applies.
- [ ] Rarity changes are only permitted if backed by updated prevalence data.
- [ ] I have run `gaia validate` locally and it passes.

**Reviewer:**
- [ ] **Evidence quality:** New sources are valid and correctly classified.
- [ ] **Classification change justified:** The shift is supported by data, not inflation.
- [ ] **No cascading breakage:** Reclassification doesn't invalidate downstream skills.
- [ ] **Graph integrity:** All checks pass after the change.

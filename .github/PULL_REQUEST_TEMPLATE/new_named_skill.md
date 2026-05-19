## New Named Skill

A named skill is a real-world implementation of an abstract Gaia skill, attributed to a specific contributor. **Contributors always submit with `status: awakened`.** Reviewer classification (title, catalogRef, status promotion) happens in a separate PR after merge.

### Skill Details
- **ID:** `contributor/skill-name`
- **Display Name:** Skill Name
- **genericSkillRef:** `existing-gaia-skill-id`
- **Level:** II / III / IV / V / VI
- **Origin:** true / false _(true = first known implementation of this skill bucket)_
- **Description:** What this specific implementation does.

### Links _(optional)_
- **GitHub:** https://github.com/...
- **Docs:** https://...

### Tags _(optional)_
`tag-one`, `tag-two`

---

### Contributor Checklist

- [ ] ID follows `contributor/skill-name` format.
- [ ] `genericSkillRef` matches an existing skill ID in `gaia.json`.
- [ ] Level is II or above.
- [ ] **`status` is set to `awakened`** — do NOT set `status: named`, `title`, or `catalogRef`. Those are reviewer-only fields.
- [ ] `origin: true` only if this is the first known implementation in the skill bucket.
- [ ] I have run `gaia validate` locally and it passes.

---

### Reviewer Checklist

- [ ] `genericSkillRef` resolves to a valid skill in `gaia.json`.
- [ ] Level is appropriate for the implementation's evidence and capability.
- [ ] Origin flag is correct — check `registry/named/index.json` for existing origin entries in this bucket.
- [ ] **Classification check** — does this match a real-world SKILL.md or named implementation in the ecosystem?
  - If **YES** → merge as `awakened`, then open a classification PR using the `named_skill_classification` template.
  - If **NO** → merge as `awakened`. The skill sits in `awaitingClassification` until a future classification PR.

## Named Skill Classification

This PR promotes an existing `awakened` named skill to `status: named` by confirming its real-world identity. **Only reviewers and maintainers should open this PR type.**

Contributors do not open classification PRs. If you are a contributor, your skill was already merged as `awakened` — this step happens separately after a reviewer verifies the real-world match.

---

### Classification Details

- **Named Skill ID:** `contributor/skill-name`
- **Awakened PR:** #_(link to the original named skill PR)_
- **Real-world match confirmed:** _(e.g. karpathy/autoresearch, superpowers/brainstorming)_
- **Source URL:** https://...
- **RPG Title assigned:** `"The Reviewer-Assigned Epithet"`
- **Catalog entry ID:** `catalog-item-id` _(if mapping to an existing catalog entry)_

---

### Changes in This PR

- `status: awakened` → `status: named`
- `title:` `"The Assigned Epithet"` _(required)_
- `catalogRef:` `catalog-item-id` _(optional — set if a catalog entry exists or is being added)_

If no catalog entry exists yet for this real-world skill, also add an item to `registry/real-skills.json` with `promotedNamedSkillId` pointing back to this named skill.

---

### Classification Checklist

**Reviewer only — do not assign title or catalogRef speculatively:**

- [ ] I have personally verified this named skill matches a real-world published implementation (a SKILL.md, repo, or documented tool).
- [ ] The `title` is an original reviewer-assigned RPG epithet — not copied verbatim from the source.
- [ ] `status` is changed from `awakened` to `named`.
- [ ] If `catalogRef` is set: the catalog item `id` exists in `registry/real-skills.json`.
- [ ] If no catalog entry exists: I have added one to `registry/real-skills.json` with `promotedNamedSkillId` set.
- [ ] `gaia validate` passes with the new status.
- [ ] I am a maintainer or have maintainer approval for this classification.

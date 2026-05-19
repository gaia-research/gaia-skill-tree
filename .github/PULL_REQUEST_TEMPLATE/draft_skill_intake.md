## Draft Skill Intake

This PR submits a **draft intake batch** for maintainer/community review.

- Canonical intake artifact: `registry-for-review/skill-batches/*.json`
- This PR does **not** directly update canonical DAG nodes in `registry/gaia.json`
- Accepted items should be promoted in a follow-up canonical graph PR

### Reviewer Actions

For each proposed skill, mark one outcome in review comments:
- `accept`
- `rename`
- `duplicate`
- `needs-evidence`
- `reject`

### Reviewer Checklist

- [ ] Definition is clear, agent-agnostic, and non-overlapping.
- [ ] Similarity hints are directionally useful (not treated as ground truth).
- [ ] Evidence expectations are noted when needed.
- [ ] Duplicate/merge opportunities are flagged.

### Maintainer Promotion Checklist

- [ ] Accepted draft skills are promoted into `registry/gaia.json` in a follow-up PR.
- [ ] `gaia validate` passes for promotion PR.
- [ ] `gaia validate --intake` passes for promotion PR.
- [ ] Promotion PR links back to this intake PR.

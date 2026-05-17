# Contributing to Gaia

Thanks for helping improve the Gaia skill graph.

This page is now a **contributor quickstart**. Detailed policy, reviewer playbooks, and deep troubleshooting now live in the GitHub Wiki repo.

---

---

## 1) Pick your workflow

### A) Submit discovered skills (recommended)

```bash
gaia push
```

Useful variants:

```bash
gaia push --dry-run
gaia push --no-pr
python3 scripts/validate_intake.py
```

Use this when proposing skills via `registry-for-review/skill-batches/*.json`.

### B) Update the canonical graph directly

1. Fork the repo.
2. Edit or add individual JSON files in `registry/nodes/`.
3. Validate:
   ```bash
   python3 scripts/validate.py
   ```
   Note: The validator now checks the `registry/nodes/` directory by default.
4. Open a PR. The pre-commit hooks will automatically handle `gaia.json` assembly and documentation regeneration.

---

## 2) What files are source-of-truth?

- ✅ `registry/nodes/**/*.json` (**The ONLY source for skills**)
- ✅ `registry-for-review/skill-batches/*.json` (intake batches)
- ❌ **DO NOT** edit `registry/gaia.json` directly — it is now an auto-generated artifact.
- ❌ Do not hand-edit generated docs/graph projections produced by build pipelines.

---

## 3) Branch naming (copy/paste)

| Prefix | Use for | Scope |
|---|---|---|
| `schema/...` | schema + terminology changes | `registry/schema/` only |
| `cli/...` | CLI / package code | `src/gaia_cli/`, `packages/`, `tests/` |
| `docs/...` | markdown/docs content | `docs/`, `*.md` |
| `design/...` | website UI assets | `docs/` HTML/CSS/JS |
| `review/gaia-push/...` | intake PRs | `registry-for-review/` |
| `review/meta/...` | registry curation | `registry/` (excluding schema) |
| `infra/...` | CI/tooling/config | `.github/`, `scripts/`, config |
| `dev/...` | experiments | unrestricted |
| `feat/...`, `fix/...` | general changes | unrestricted (schema rules still enforced) |

Hard rule: any schema file change must come from a `schema/...` branch.

---

## 4) Naming + evidence minimums

### Naming

- Skill IDs: `kebab-case` (`web-scrape`, `parse-json`)
- Display names: Title Case
- Skill types in graph: `basic`, `extra`, `ultimate`
- Keep skills vendor-agnostic

### Evidence by star level

Use the schema star notation for all new and updated registry entries. The old roman numeral labels are legacy-only and should not appear in `level` values.

| Level value | Rank label | Evidence floor |
|---|---|---|
| `0★` | Basic | no evidence required |
| `1★` | Awakened | no evidence required |
| `2★` | Named | ≥ 1 Tier C |
| `3★` | Evolved | ≥ 1 Tier B |
| `4★` | Hardened | ≥ 1 Tier B/A |
| `5★` | Transcendent | ≥ 1 Tier B/A |
| `6★` | Transcendent ★ | Tier A + peer review |

Legacy mapping for reviewers: `0`/`I` → `0★`/`1★`, `II` → `2★`, `III` → `3★`, `IV` → `4★`, `V` → `5★`, and `VI` → `6★`.

### Ultimate (`ultimate`) requirements

- At least 3 Tier A/B evidence items
- 2 maintainer approvals
- Must be `validated` at merge

### Demerits and effective level

- Demerits are allowed only on claimed levels `2★` and above.
- Allowed demerit IDs are canonical and schema-validated: `niche-integration`, `experimental-feature`, `heavyweight-dependency`.
- Each demerit lowers runtime potential by one star level (effective level), floored at `1★`.
- Named skill claims stay constrained by canonical level requirements; demerits do not bypass evidence floors.

---

## 5) PR checklist (copy/paste)

- [ ] Correct branch prefix
- [ ] Edited only source-of-truth files
- [ ] Validation command(s) passed
- [ ] Evidence meets level/type requirements
- [ ] PR template selected
- [ ] PR title format:
  ```
  [type] skill-name — short description
  ```

Examples:
- `[basic] parse-csv — add CSV parsing primitive`
- `[extra] autonomous-debug — compose debug workflow`
- `[reclassify] web-scrape — promote with new evidence`

---

## 6) FAQ

**Q: I ran `gaia push`. Are proposed skills already in the DAG?**  
No. Intake batches are review artifacts until accepted skills are promoted into `registry/gaia.json`.

**Q: Where should long-form guidance go?**  
In the [Wiki](https://github.com/mbtiongson1/gaia-skill-tree/wiki) (review standards, curation heuristics, edge cases, troubleshooting).

---

## 7) Helpful links

- [README quickstart](../README.md)
- [Docs site](docs/index.html)
- [Governance](docs/GOVERNANCE.md)
- [Wiki](https://github.com/mbtiongson1/gaia-skill-tree/wiki) · [Wiki git repo](https://github.com/mbtiongson1/gaia-skill-tree.wiki.git)


---

## 8) Demotion and Reclassification Criteria

Use this section for reviewer decisions when a skill should be demoted, remapped, or declassified.

A review is required when evidence shows a skill is:
- **outdated** (implementation or evidence no longer reflects current behavior),
- **superseded** (a better canonical mapping or replacement now exists),
- **overpromoted** (current level exceeds demonstrated evidence tier), or
- supported by **insufficient usage evidence** for its assigned rank.

Reviewer workflow:
- Reviewers should use `/gaia-audit` before approving PRs that demote, declassify, remap, dispute, or re-promote a specific skill.
- Reviewers should use `/gaia-meta-audit` to build queues for stale links, unsupported promotions, possible duplicates, and broad mapping quality checks.

---

## 9) Unique Skill Promotion

A **Unique Skill** (◉) is a graph-isolated intrinsic skill that has reached elite mastery through individual depth rather than fusion/combination. Unique skills occupy their own tier between Extra and Ultimate in prestige.

### Eligibility Criteria

A basic skill may be promoted to `type: "unique"` when ALL of the following are true:

1. **Level ≥ 4★** (Hardened or above)
2. **Zero prerequisites** (`prerequisites: []`)
3. **Graph-isolated** — not referenced as a prerequisite by any other skill
4. **Has at least one named implementation** in `registry/named/`

### Promotion Workflow

```bash
# 1. Scan detects eligible skills automatically
gaia scan

# 2. Review unique-eligible candidates in the output
cat generated-output/promotion-candidates.json | grep '"promotionType": "unique"'

# 3. Promote via CLI (updates type field in gaia.json)
gaia promote <skill-id> --unique
```

### Validation Rules

The schema and validator enforce:
- Unique skills MUST be level 4★, 5★, or 6★
- Unique skills MUST have `prerequisites: []`
- Unique skills MUST NOT appear in any other skill's `prerequisites` array
- Unique skills CANNOT become extra or ultimate (no fusion path)
- Further level-up within unique (4★ → 5★ → 6★) follows standard evidence requirements

### Approval Requirements

- PRs promoting a skill to unique require maintainer approval
- Evidence must meet the standard floor for the skill's level (B/A class for 4★+)
- Reviewers should use `/gaia-audit` to verify isolation and evidence quality before approving

---

## 10) Automated Maintenance

The registry is supported by several automated workflows:
- **Auto-Sync:** On every push to a branch, a GitHub Action automatically runs the versioning and regeneration scripts. You no longer need to run these manually before pushing.
- **Validation:** Every PR is automatically validated for schema correctness, DAG integrity, and evidence quality.

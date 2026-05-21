---
name: gaia-fuse-full-suite
description: Fuse all named skills from a single contributor into one ultimate skill and record it in the timeline. Use when the user asks to "fuse a suite", "fuse all of <user>'s skills", "create a fusion ultimate for <user>", or explicitly types /gaia-fuse-full-suite.
---

# gaia-fuse-full-suite

Fuse every named skill attributed to a single contributor into a new ultimate skill node, back-link it across all component nodes, record a `fuse` timeline event, and open a PR.

## Inputs

Ask the user (or infer from context) before starting:

| Input | Description | Example |
|---|---|---|
| `contributor` | GitHub username of the named contributor | `obra` |
| `ultimate-id` | kebab-case ID for the new ultimate skill | `superpowers` |
| `ultimate-name` | Human-readable name | `Superpowers` |
| `source-url` | Canonical repo/page for the suite (for evidence) | `https://github.com/obra/superpowers` |

If the contributor already has an ultimate with this ID and it is already fused, abort and report the existing entry.

## Workflow

### 1. Collect components

```bash
ls registry/named/<contributor>/
```

For each `.md` file, parse the YAML frontmatter and extract:
- `genericSkillRef` → the component skill ID
- `level` → used for summary table
- `title` → the named title

Fail loudly if any file is missing `genericSkillRef` or has `status: awakened` (awakened skills are not yet named and cannot be fused).

### 2. Verify component nodes exist

For each component `genericSkillRef`, confirm a node JSON file exists in `registry/nodes/basic/` or `registry/nodes/extra/` (or appears in `registry/gaia.json` skills list). Report any missing IDs and abort — missing nodes must be registered first.

### 3. Check for an existing ultimate

```python
import json
with open("registry/gaia.json", "r", encoding="utf-8") as f:
    g = json.load(f)
existing = next((s for s in g["skills"] if s["id"] == "<ultimate-id>"), None)
```

If it exists and already has a `fuse` timeline entry, abort. If it exists without a `fuse` entry, add one (update mode). If it does not exist, proceed to creation.

### 4. Research evidence and determine level

Fetch `source-url` with WebFetch. Look for:
- GitHub star count ≥ 10,000 → strong Class B
- Multi-platform adoption (≥ 3 unrelated hosts) → strong Class B
- Active version / release tag → healthy Class B
- Published academic paper or official spec → Class A

**Level decision:**
- **5★** — strong Class B (10k+ stars and multi-platform, or version ≥ 1.0 with ≥ 3 adopters) OR any Class A evidence
- **4★** — only a modest Class B (active repo, < 10k stars, single platform)
- Never below 4★ for a named-origin fusion (the naming itself is evidence)

Record the level decision and evidence notes before continuing.

### 5. Create or update the ultimate node

Write `registry/nodes/ultimate/<ultimate-id>.json`:

```json
{
  "id": "<ultimate-id>",
  "name": "<ultimate-name>",
  "type": "ultimate",
  "level": "<level>",
  "rarity": "common",
  "description": "<one sentence synthesising what the suite achieves>",
  "prerequisites": ["<component-id-1>", "..."],
  "derivatives": [],
  "conditions": "Requires demonstrating all N <contributor> discipline skills together in a real multi-step context.",
  "evidence": [{ ... }],
  "knownAgents": [],
  "status": "provisional",
  "createdAt": "<today>",
  "updatedAt": "<today>",
  "version": "0.1.0",
  "timeline": [
    {
      "timestamp": "<today>T00:00:00Z",
      "action": "fuse",
      "contributor": "<evaluator-github-username>",
      "details": "Fused N <contributor>/<suite-name> skills into /<ultimate-id> ultimate. Components: <comma-separated list>. Promoted to <level> on evidence: <brief evidence summary>."
    }
  ]
}
```

If updating an existing node, merge the new `fuse` timeline event into the existing `timeline` array; do not overwrite other fields.

The `rarity` field is a deprecated schema requirement (see `CONTEXT.md` § Rarity). Write the legacy default `"common"` and do not deliberate over the value; the field will be removed once the schema migration lands.

### 6. Update component nodes

For each component node at `registry/nodes/basic/<id>.json` (or `extra/`):

- Read the file.
- If `derivatives` does not already contain `<ultimate-id>`, append it.
- Write the file back.

Do **not** modify any fields other than `derivatives`.

### 7. Update `registry/gaia.json`

```python
import json, datetime

with open("registry/gaia.json", "r", encoding="utf-8") as f:
    g = json.load(f)

# 7a. Add or update the ultimate skill entry
# (mirrors the node JSON — keep in sync)
existing_idx = next((i for i, s in enumerate(g["skills"]) if s["id"] == "<ultimate-id>"), None)
if existing_idx is not None:
    g["skills"][existing_idx] = ultimate_entry   # update mode
else:
    g["skills"].append(ultimate_entry)           # create mode

# 7b. Add prerequisite edges (skip duplicates)
existing_edge_pairs = {(e["sourceSkillId"], e["targetSkillId"]) for e in g["edges"]}
for component_id in component_ids:
    if (component_id, "<ultimate-id>") not in existing_edge_pairs:
        g["edges"].append({
            "sourceSkillId": component_id,
            "targetSkillId": "<ultimate-id>",
            "edgeType": "prerequisite"
        })

g["generatedAt"] = datetime.date.today().isoformat() + "T00:00:00Z"

with open("registry/gaia.json", "w", encoding="utf-8") as f:
    json.dump(g, f, indent=2, ensure_ascii=False)
```

### 8. Regenerate the named index

```bash
PYTHONIOENCODING=utf-8 python scripts/generateNamedIndex.py
```

Confirm it exits 0 and the ultimate's `genericSkillRef` does not appear in warnings.

### 9. Validate

```bash
PYTHONIOENCODING=utf-8 python scripts/validate.py
```

All 10 checks must pass. If any fail:
- Reference integrity failures → fix missing derivatives or prerequisites.
- DAG cycle → a component likely points back to itself through the ultimate; remove the self-referencing derivative.
- Ultimate constraints → check that the evidence class meets the threshold for the chosen star level.

Do **not** open a PR until validation is clean.

### 10. Commit and open PR

Branch: `review/meta/<ultimate-id>-fusion`

```bash
git checkout -b review/meta/<ultimate-id>-fusion origin/main
git add registry/nodes/ultimate/<ultimate-id>.json \
        registry/nodes/basic/<component-id>.json \   # one per component
        registry/gaia.json \
        registry/named-skills.json
git commit -m "feat(registry): fuse <contributor>/<suite-name> into /<ultimate-id> <level> ultimate

- Add /superpowers ultimate node fusing N named <contributor> skills
- Back-link derivatives on all N component nodes
- Add fuse timeline event (action: fuse, <today>)
- Update registry/gaia.json and regenerate named-skills.json

validate.py: all 10 checks pass (<total> skills, <edge> edges)."
git push -u origin review/meta/<ultimate-id>-fusion
```

Open the PR with:

```
## Summary

- New ultimate skill **/<ultimate-id>** (<level>) fusing N named <contributor> skills
- Fuse timeline event recorded; components back-linked via `derivatives`
- Evidence: <one-line summary of source and signals>

## Component skills

| ID | Named Title | Level |
|---|---|---|
| <id> | <title> | <level> |
| ... | ... | ... |

## Level rationale

<Why 5★ or 4★ — cite specific signals from step 4>

## Validation

- `python scripts/validate.py` — all 10 checks pass
- `python scripts/generateNamedIndex.py` — <bucket count> buckets, no errors
```

## Output

Report back:
- PR URL
- Ultimate skill ID and star level
- Number of components fused
- Evidence class and key signal (stars, adopters, version)
- Validation pass/fail summary

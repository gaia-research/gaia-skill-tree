---
name: gaia-fuse-full-suite
description: >
  Fuse all of a contributor's named skills into a single ultimate/suite skill node in the Gaia registry.
  Use when the user says "fuse <contributor>'s skills", "create a suite for <contributor>",
  "build an ultimate for <user>", "fuse all of <user>'s named skills", "create a fusion ultimate",
  "consolidate <contributor> into one skill", or explicitly types /gaia-fuse-full-suite.
  Also triggers when a contributor has accumulated 3+ named skills and the user asks what to do
  next with them, or when someone asks "can we make a suite from these?".
  This skill: collects component IDs from registry/named/<contributor>/, verifies nodes exist,
  researches evidence to determine the star level, writes the ultimate node JSON, back-links
  derivatives on all components, updates registry/gaia.json, regenerates the named index,
  validates, and opens a PR on a review/meta/ branch.
---

# gaia-fuse-full-suite

Fuse every named skill attributed to a contributor into a new ultimate skill node, back-link
it across all component nodes, record a `fuse` timeline event, and open a PR.

An ultimate node is the right abstraction when a contributor has built a coherent body of
named skills that together form a recognisable suite. The fusion step makes that relationship
explicit in the graph: prerequisites point to the ultimate, and the ultimate's evidence anchors
the whole cluster's credibility.

## Inputs

Gather these before starting. Infer from context when obvious; ask when ambiguous.

| Input | Description | Example |
|---|---|---|
| `contributor` | GitHub username of the named contributor | `obra` |
| `ultimate-id` | kebab-case ID for the new ultimate skill | `superpowers` |
| `ultimate-name` | Human-readable display name | `Superpowers` |
| `source-url` | Canonical repo or landing page (for evidence research) | `https://github.com/obra/superpowers` |

If the contributor already has an ultimate with this ID **and** it has a `fuse` timeline entry,
abort early and report the existing entry — there is nothing to do.

## Workflow

### 1. Collect components

```bash
ls registry/named/<contributor>/
```

For each `.md` file, parse the YAML frontmatter and extract:
- `genericSkillRef` — the component skill ID
- `level` — used in the summary table
- `title` — the named title

Fail loudly (do not silently skip) if any file is missing `genericSkillRef`, or has
`status: awakened`. Awakened skills have not been named yet and cannot participate in a fusion
— their inclusion would undercount what the suite represents.

### 2. Verify component nodes exist

For each `genericSkillRef`, confirm a node JSON file exists under `registry/nodes/basic/` or
`registry/nodes/extra/`. Report any missing IDs and abort — missing nodes must be registered
via `gaia dev add` before the fusion can proceed. Do not create stub nodes inline.

### 3. Check for an existing ultimate

```python
import json
with open("registry/gaia.json", "r", encoding="utf-8") as f:
    g = json.load(f)
existing = next((s for s in g["skills"] if s["id"] == "<ultimate-id>"), None)
```

- Already exists + has `fuse` timeline entry → abort (report URL).
- Already exists, no `fuse` entry → update mode (add the timeline event; do not overwrite other fields).
- Does not exist → proceed to creation.

### 4. Research evidence and determine level

Fetch `source-url` with WebFetch. Look for:
- GitHub star count ≥ 10,000 → strong Class B signal
- Multi-platform adoption (≥ 3 unrelated hosts) → strong Class B
- Active release tag / version ≥ 1.0 → healthy Class B
- Published academic paper or official specification → Class A

**Level decision:**
- **5★** — strong Class B (10k+ stars and multi-platform, or version ≥ 1.0 with ≥ 3 adopters) OR any Class A evidence
- **4★** — modest Class B only (active repo, < 10k stars, single platform)
- Never below 4★ for a named-origin fusion — the naming act itself is a form of evidence

Record the level decision and evidence notes before continuing. You will need them for the
node JSON and the PR description.

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
  "evidence": [{ "..." : "..." }],
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

The `rarity` field is a deprecated schema artifact (see `CONTEXT.md` § Rarity). Write `"common"`
and move on — do not deliberate over the value.

In update mode, merge the new `fuse` timeline event into the existing array; do not clobber
other fields.

### 6. Back-link component nodes

For each component node at `registry/nodes/basic/<id>.json` (or `extra/`):
- Read the file.
- If `derivatives` does not already include `<ultimate-id>`, append it.
- Write the file back.

Touch only `derivatives`. Editing other fields would be an unintended side-effect and could
fail validation.

### 7. Update `registry/gaia.json`

```python
import json, datetime

with open("registry/gaia.json", "r", encoding="utf-8") as f:
    g = json.load(f)

# Add or replace the ultimate skill entry
existing_idx = next((i for i, s in enumerate(g["skills"]) if s["id"] == "<ultimate-id>"), None)
if existing_idx is not None:
    g["skills"][existing_idx] = ultimate_entry   # update mode
else:
    g["skills"].append(ultimate_entry)           # create mode

# Add prerequisite edges (skip duplicates to keep the graph clean)
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

All checks must pass. Common failures and fixes:
- **Reference integrity** — a missing derivative or prerequisite; add the back-link.
- **DAG cycle** — a component accidentally points back to itself through the ultimate; remove the self-referencing derivative.
- **Ultimate constraints** — evidence class doesn't meet the threshold for the chosen star level; either downgrade the level or find stronger evidence.

Do not open a PR until validation is clean.

### 10. Commit and open PR

Branch: `review/meta/<ultimate-id>-fusion`

```bash
git checkout -b review/meta/<ultimate-id>-fusion origin/main
git add registry/nodes/ultimate/<ultimate-id>.json \
        registry/nodes/basic/<component-id>.json \
        registry/gaia.json \
        registry/named-skills.json
git commit -m "feat(registry): fuse <contributor>/<suite-name> into /<ultimate-id> <level> ultimate

- Add /ultimate-id ultimate node fusing N named <contributor> skills
- Back-link derivatives on all N component nodes
- Add fuse timeline event (action: fuse, <today>)
- Update registry/gaia.json and regenerate named-skills.json

validate.py: all checks pass (<total> skills, <edge> edges)."
git push -u origin review/meta/<ultimate-id>-fusion
```

PR body template:

```
## Summary

- New ultimate skill **/<ultimate-id>** (<level>) fusing N named <contributor> skills
- Fuse timeline event recorded; components back-linked via `derivatives`
- Evidence: <one-line summary of source and signals>

## Component skills

| ID | Named Title | Level |
|---|---|---|
| <id> | <title> | <level> |

## Level rationale

<Why 5★ or 4★ — cite specific signals from step 4>

## Validation

- `python scripts/validate.py` — all checks pass
- `python scripts/generateNamedIndex.py` — no errors
```

## Output

Report back concisely:
- PR URL
- Ultimate skill ID and star level
- Number of components fused
- Evidence class and key signal (stars, adopters, version)
- Validation result

---
name: gaia-fuse-full-suite
description: >
  Fuse all of a contributor's named skills into a single fusion node (suite capstone) in the registry.
  Use when the user says "fuse <contributor>'s skills", "create a suite for <contributor>",
  "build a capstone for <user>", "fuse all of <user>'s named skills", "create a suite fusion",
  "consolidate <contributor> into one skill", or explicitly types /gaia-fuse-full-suite.
  Also triggers when a contributor has accumulated 3+ named skills and the user asks what to do
  next with them, or when someone asks "can we make a suite from these?".
  This skill: collects component IDs from registry/named/<contributor>/, verifies nodes exist,
  researches evidence and appraises Trust Magnitude, runs `gaia dev fuse` to write the fusion
  node and suite manifest, validates, and opens a PR on a review/meta/ branch.
---

# gaia-fuse-full-suite

Fuse every named skill attributed to a contributor into a new **fusion** node, link it as the
suite capstone, record a `fuse` timeline event, and open a PR.

A fusion node is the right abstraction when a contributor has built a coherent body of
named skills that together form a recognisable suite. The fusion step makes that relationship
explicit in the graph: prerequisites point to the fusion node, and the fusion node's evidence
anchors the whole cluster's credibility.

## Taxonomy (Yggdrasil II)

Ratified 2026-07-07. Read `CONTEXT.md` § Taxonomy v6 before writing any copy.

- The **type** axis is starless-only and collapsed to exactly `{basic, fusion}`. `extra`,
  `ultimate`, and `unique` are **retired as types** — never write them to a node.
- **Ultimate** (5★ Suite) and **Apex** (6★ Suite) survive **only as rank names**, never as
  taxonomy words. A fused capstone is a **Fusion**, not "an Ultimate".
- **Branch** (`standard` / `suite` / `unique`) is derived at read time, never declared. A Named
  Skill carrying `suiteComponents` is `suite` at any rank.
- The per-star **Evidence Floor** is retired. **Trust Magnitude is the sole promotion gate.**

## Programmatic-First — use the CLI

Per `CLAUDE.md`, all registry mutations go through `gaia dev` verbs. **Do not hand-write node
JSON** — `gaia dev fuse` writes the fusion node, the suite manifest, the back-links, and the
timeline event, and it always emits `type: fusion` into `registry/nodes/fusion/`. Hand-edits
skip timeline logging and are how schema-invalid nodes reach the registry.

## Inputs

Gather these before starting. Infer from context when obvious; ask when ambiguous.

| Input | Description | Example |
|---|---|---|
| `contributor` | GitHub username of the named contributor | `obra` |
| `fusion-id` | kebab-case ID for the new fusion node | `superpowers` |
| `fusion-name` | Human-readable display name | `Superpowers` |
| `capstone-id` | Named capstone to link (`contributor/slug`) | `obra/superpowers` |
| `source-url` | Canonical repo or landing page (for evidence research) | `https://github.com/obra/superpowers` |

If the contributor already has a fusion node with this ID **and** it has a `fuse` timeline entry,
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
`registry/nodes/fusion/`. Report any missing IDs and abort — missing nodes must be registered
via `gaia dev add` before the fusion can proceed. Do not create stub nodes inline.

### 3. Check for an existing fusion node

```bash
gaia dev list --generic | grep '<fusion-id>'
```

- Already exists + has `fuse` timeline entry → abort (report URL).
- Already exists, no `fuse` entry → update mode; `gaia dev fuse` merges rather than clobbers.
- Does not exist → proceed to creation.

### 4. Research evidence and appraise Trust Magnitude

Fetch `source-url` with WebFetch and record the signals that will feed TM scoring:
- GitHub star count and trajectory
- Multi-platform adoption (unrelated hosts shipping it)
- Active release tag / version ≥ 1.0
- Published academic paper, peer review, or official specification

Log each source through the CLI so it is graded and timestamped:

```bash
gaia dev evidence <fusion-id> "<url>" --type <evidence-type> --evaluator <your-handle>
```

Then appraise:

```bash
gaia appraise <fusion-id>
```

**Rank decision — Trust Magnitude is the sole gate.** There is no per-star Evidence Floor
under Yggdrasil II; do not assert a star level from an evidence grade alone. For the Suite
branch the published gates are:

- **4★ Extra** — Origin Contributor recorded + TM ≥ 100
- **5★ Ultimate** — Origin in `suiteComponents` + 5 A-graded origins in `suiteComponents` + TM ≥ 250
- **6★ Apex** — the full 6-predicate Apex Gate (see `META.md`)

If the appraised TM does not clear a gate, record the rank the TM supports and say so in the
PR. Do not round up.

### 5. Run the fusion

```bash
gaia dev fuse <fusion-id> \
  --name "<fusion-name>" \
  --description "<one sentence synthesising what the suite achieves>" \
  --prereqs <component-id-1>,<component-id-2>,... \
  --named-capstone <capstone-id> \
  --suite-components <named-id-1>,<named-id-2>,...
```

This writes `registry/nodes/fusion/<fusion-id>.json` with `type: fusion`, upserts the suite
manifest at `registry/suites/<contributor>/<slug>.json`, back-links `derivatives` on every
component node, appends the `fuse` timeline event, and rebuilds the graph and docs.

Notes:
- `--type` is **not** a flag. `gaia dev fuse` always produces a fusion node; the type is
  derived structurally from the presence of prerequisites.
- `suiteComponents` is a **Named-Skill-only** field. Never write it onto the starless node.
- Do not write a `branch` field — branch is computed at read time.
- Pass `--no-build` only if you are batching several fusions; run one build at the end.

### 6. Validate

```bash
PYTHONIOENCODING=utf-8 gaia dev validate
```

All checks must pass. Common failures and fixes:
- **Reference integrity** — a missing derivative or prerequisite; re-run the fuse with the
  complete `--prereqs` list.
- **DAG cycle** — a component points back to itself through the fusion node; remove the
  self-referencing derivative.
- **Fusion constraints** — the recorded rank exceeds what Trust Magnitude supports; lower the
  rank via `gaia dev calibrate`, or log stronger evidence and re-appraise.
- **Meta sync** — `registry/` and the bundled snapshot diverged; re-run the build step.

Do not open a PR until validation is clean.

### 7. Commit and open PR

Branch: `review/meta/<fusion-id>-fusion`

Per `CLAUDE.md` Guard E, a change to `registry/nodes/` or `registry/named/` **must** ship the
regenerated Class S artifacts (`docs/graph/*`) in the same PR.

```bash
git checkout -b review/meta/<fusion-id>-fusion origin/main
git add registry/nodes/fusion/<fusion-id>.json \
        registry/nodes/basic/<component-id>.json \
        registry/suites/<contributor>/ \
        registry/named-skills.json \
        docs/graph/
git commit -m "feat(registry): fuse <contributor>/<suite-name> into /<fusion-id> <rank> fusion

- Add /<fusion-id> fusion node capstoning N named <contributor> skills
- Back-link derivatives on all N component nodes
- Add fuse timeline event (action: fuse, <today>)
- Regenerate Class S artifacts (docs/graph/*)

gaia dev validate: all checks pass (<total> skills, <edge> edges)."
git push -u origin review/meta/<fusion-id>-fusion
```

PR body template:

```
## Summary

- New fusion node **/<fusion-id>** (<rank>) capstoning N named <contributor> skills
- Fuse timeline event recorded; components back-linked via `derivatives`
- Evidence: <one-line summary of source and signals>
- Trust Magnitude: <TM> (gate for <rank> is <threshold>)

## Component skills

| ID | Named Title | Rank |
|---|---|---|
| <id> | <title> | <rank> |

## Rank rationale

<Which TM gate the appraisal cleared — cite the appraised TM from step 4>

## Validation

- `gaia dev validate` — all checks pass
```

## Output

Report back concisely:
- PR URL
- Fusion node ID and rank
- Number of components fused
- Appraised Trust Magnitude and the key signals behind it
- Validation result

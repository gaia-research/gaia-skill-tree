---
name: gaia-meta-sweep
description: >
  Orchestrate a whole-registry Gaia meta sweep. Use when the user asks to run
  a meta sweep, full meta audit, audit the whole registry against META.md,
  find systemic nomenclature/evidence/type issues, surface Semantic Fusion
  candidates, find missing GitHub links, or produce a durable report under
  docs/meta/reports/. This is the macro companion to /gaia-meta-audit and
  /gaia-audit: it fans out audit agents, adversarially verifies findings, and
  synthesizes a publishable report.
---

# gaia-meta-sweep

Orchestrate a registry-wide meta audit using a multi-phase Workflow. The skill fans out 12 parallel audit agents, one per audit dimension from META.md, then runs adversarial verification on every finding before synthesizing a journal-style HTML report, a Chart.js timeline JSON, and a machine-readable findings index.

## Inputs

Ask the user (or infer from context) before kicking off. These four parameters gate how much the skill mutates vs. just reports:

| Input | Description | Default |
|---|---|---|
| `mode` | `read-only` (findings + report only) or `apply-safe` (also runs `gaia dev rename`/`calibrate`/`evidence` for high-confidence corrections) | `read-only` |
| `fusion-aggressiveness` | `moderate` (3–8 high-confidence Semantic Fusion candidates, adversarially verified) or `aggressive` (10–20+ including speculative pairings) | `moderate` |
| `scope` | `all` (every named + generic skill) or a filter expression (e.g. `level>=3★`, `contributor:mbtiongson1`) | `all` |
| `report-slug` | Filename for the report under `docs/meta/reports/` | `<YYYY-MM-DD>-meta-audit.html` |
| `commit` | `none` (leave files unstaged), `worktree` (commit on current branch), or `branch:<name>` (create + commit on a fresh branch) | `none` |

## Pre-flight

1. Confirm working tree is on a branch you may write to. Registry mutations follow the `review/meta/<slug>` branch prefix (see `AGENTS.md` Branch Naming). Refuse to mutate `main` directly unless the user explicitly says so.

2. Read `META.md` once and cache its key sections in the workflow prompt — this avoids each sub-agent re-reading the full file, which adds latency and drift:
   - §1 Taxonomy (star tiers, skill types)
   - §2 Evidence Methodology + §2.3 Specialist Path Rubric + §2.4 Meta-Audit Standards
   - §3 Demerits
   - §4 Governance & Promotion (Origin rule)
   - §6 Master Skill Fusion & Pruning (Champion + Semantic Fusion)

3. Snapshot today's registry counts so Phase 5 can include a before/after distribution table:

   ```bash
   PYTHONIOENCODING=utf-8 python - <<'PY'
   import json, collections
   g = json.load(open("registry/gaia.json", encoding="utf-8"))
   nb = json.load(open("registry/named-skills.json", encoding="utf-8"))["buckets"]
   c = collections.Counter(e.get("level","?") for v in nb.values() for e in v)
   print({k: c[k] for k in ["2★","3★","4★","5★","6★"]})
   PY
   ```

   Note: generic skill references are starless — they carry no `level` field. Stars live only on named skills (2★–6★); a generic's effective rank is the highest star among its named children.

## Workflow invocation

Use the Workflow tool. Author the script inline. Only ask the user before launching if the task seems exploratory and they haven't explicitly asked for a sweep — a direct "run meta sweep" is sufficient opt-in.

### Phase plan

Five phases with a barrier only between Survey → Verify, because the synthesis phase needs the full deduplicated finding set before it can write the report. Phases 1–3 run in parallel (pipeline) since they produce independent outputs.

```javascript
export const meta = {
  name: 'gaia-meta-sweep',
  description: 'Whole-registry audit against META.md with fusion + new-generic proposals',
  phases: [
    { title: 'Survey',  detail: 'fan-out audit dimensions across registry' },
    { title: 'Fuse',    detail: 'identify Semantic Fusion candidates (META §6.2)' },
    { title: 'Propose', detail: 'propose new generic skill refs for the schema' },
    { title: 'Verify',  detail: 'adversarially verify each finding' },
    { title: 'Report',  detail: 'synthesize HTML + timeline JSON' },
  ],
}
```

### Phase 1 — Survey (parallel, one agent per dimension)

Spawn one agent per audit dimension. Parallelism matters here: 12 dimensions × full registry is the bottleneck; running them concurrently cuts wall-clock time by ~10×. Each agent scopes to the whole registry but only looks at its one dimension, keeping prompts focused and outputs structured.

Dimensions:

1. `star-bar` — every 3★+ named skill missing/dead `links.github` (META §2.4)
2. `liveness` — run `python scripts/verify_evidence.py`, return broken URLs (META §2.2 Liveness Heartbeat)
3. `origin-attribution` — for every `genericSkillRef`, sort named skills by `createdAt`; flag any non-earliest with `origin: true` (META §4.1)
4. `unbacked-star` — named skills whose `level` is not backed by their own + inherited evidence (generics are starless — no overshoot possible)
5. `brand-coupled` — generic IDs containing brand/product names (META §1, §2.4)
6. `heavy-deps` — 3★+ named skills with known heavyweight deps / niche integrations (generic demerits are removed from the schema)
7. `installability` — 3★+ non-suite skills with `installable: false` or no GitHub link (META §2.4 Star Bar)
8. `placeholder-bodies` — named markdown with stub `## Installation` only (no `## Overview`)
9. `testuser-timelines` — `contributor: testuser` survivors that were never cleaned up
10. `champion-cluster` — generics where multi-implementation clusters exist but no Champion is set (META §6.1)
11. `unique-isolation` — Unique skills with prerequisites or whose top named star is below 4★ (META §1.2 — Unique = 4★+ named star, 0 prereqs)
12. `class-mismatch` — evidence claiming Class A without peer-review/10k★ marker (META §2.1)

Each agent returns structured findings so Phase 4 can process them programmatically without re-parsing prose:

```json
{ "type": "object", "required": ["dimension","findings"],
  "properties": {
    "dimension": {"type": "string"},
    "findings": {"type": "array", "items": {
      "type": "object", "required": ["target","priority","reason","suggestedAction","sources"],
      "properties": {
        "target":          {"type":"string"},
        "priority":        {"enum":["P0","P1","P2","P3","P4"]},
        "reason":          {"type":"string"},
        "suggestedAction": {"type":"string"},
        "sources":         {"type":"array","items":{"type":"string"}}
      }}}}}
```

### Phase 2 — Fuse (Semantic Fusion candidates)

Spawn one agent that walks named skills pairwise within shared topical clusters and surfaces fusion candidates per META §6.2. Aggressiveness controls the cap (3–8 moderate vs. 10–20 aggressive). Reject any candidate requiring ≥10k stars — that threshold is an Ultimate; redirect to `/gaia-fuse-full-suite` instead.

Reference the worked example from PR #525 (`safishamsi/graphify` + `mattpocock/triage` → `graph-driven-issue-triage` 3★).

```json
{ "type":"object","required":["candidates"],
  "properties":{"candidates":{"type":"array","items":{
    "type":"object","required":["proposedGenericId","proposedName","prerequisites","rationale","exampleNamed"],
    "properties":{
      "proposedGenericId":{"type":"string"},
      "proposedName":{"type":"string"},
      "prerequisites":{"type":"array","items":{"type":"string"},"minItems":2},
      "rationale":{"type":"string"},
      "exampleNamed":{"type":"array","items":{"type":"string"}}
    }}}}}
```

### Phase 3 — Propose (new generic skill refs)

Spawn one agent that reads `registry/schema/meta.json` plus the Phase-1 findings and proposes new generic node IDs for capabilities being repeatedly named without a canonical generic to anchor them. Focus on:

- Brand-coupled generics renamed to abstract phrases (from Phase 1 dimension 5)
- Repeated `genericSkillRef` collisions where a more specific Extra would reduce mis-attribution
- Schema additions implied by fusion candidates (Phase 2 prerequisites that don't exist yet)

```json
{ "type":"object","required":["proposals"],
  "properties":{"proposals":{"type":"array","items":{
    "type":"object","required":["id","name","type","description","prerequisites","reasoning"],
    "properties":{
      "id":{"type":"string","pattern":"^[a-z0-9-]+$"},
      "name":{"type":"string"},
      "type":{"enum":["basic","extra","unique"]},
      "description":{"type":"string","minLength":10},
      "prerequisites":{"type":"array","items":{"type":"string"}},
      "reasoning":{"type":"string"}
    }}}}}
```

### Phase 4 — Verify (adversarial)

For every Phase-1, Phase-2, and Phase-3 finding, spawn **3 independent skeptic agents** prompted to *refute* the finding. Use diverse lenses (correctness / evidence-strength / META-rule-precedent). A finding survives only if ≥2 of 3 agree it is real. This prevents false positives from polluting the report and eroding reviewer trust in future sweeps.

```javascript
const votes = await parallel(Array.from({length: 3}, () => () =>
  agent(`Try to refute: ${claim}. Default to refuted=true if uncertain.`, {schema: VERDICT})))
const survives = votes.filter(Boolean).filter(v => !v.refuted).length >= 2
```

```json
{ "type":"object","required":["refuted","reason"],
  "properties":{"refuted":{"type":"boolean"},"reason":{"type":"string"},"counterEvidence":{"type":"string"}}}
```

### Phase 5 — Report (synthesis)

A single synthesis agent receives all surviving findings, fusion candidates, and new-generic proposals and produces three artifacts:

1. **`docs/meta/reports/<slug>.html`** — Copy the structure of `docs/meta/reports/2026-05-25-programmatic-registry-audit.html` (LaTeX-style journal layout: abstract, executive summary, sections per dimension, references). Title: `Registry Audit Report: <Month YYYY> Meta Sweep`. Author: from `git config user.name` or `gaia` config.

2. **`docs/meta/reports/<YYYY-MM>-timeline.json`** — Chart.js-shaped timeline matching `may-2026-timeline.json` (labels = days in the audit window; datasets = one per star tier). Use the Pre-flight snapshot as the right-edge values.

3. **`docs/meta/reports/<slug>.findings.json`** — Machine-readable index of every surviving finding tagged by phase, priority, and META.md section reference. This is the durable artifact other tools (Liveness Heartbeat, future `gaia dev` migrations) can consume without parsing HTML.

The synthesis agent must:

- Tag every meta change with the META.md section number that justifies it (this is what makes the report auditable, not just readable)
- Tag every Semantic Fusion candidate with `META §6.2`
- Tag every new generic proposal with `META §1` + the originating dimension
- Include a "Before/After" rank distribution table from the Pre-flight snapshot vs. projected post-mutation counts
- If `mode == apply-safe`, list every applied `gaia dev` command in a "Mutations Applied" section; otherwise list them under "Mutations Proposed"

## Apply-safe mutations (only if mode = apply-safe)

After Phase 5 produces the findings.json, replay the high-confidence subset programmatically. Only these mutation types are auto-applyable — everything else stays a proposal because the risk of irreversible registry damage outweighs the convenience:

| Finding type | CLI command |
|---|---|
| Brand-coupled generic ID | `gaia dev rename <old> <new>` |
| Unbacked named star | `gaia dev calibrate <author/skill> N★` or direct YAML edit on the named markdown |
| Missing 3★+ evidence | `gaia dev evidence <id> <url> --class B --evaluator <user>` |
| Dead evidence link | Remove/replace the offending evidence entry + log a `demote` timeline event |
| Unique reclassification (top named star below 4★) | `gaia dev reclassify <id> basic` |

After every mutation, validate immediately — a half-applied set that fails CI is worse than no mutations at all:

```bash
gaia validate
gaia validate --intake
gaia docs build
```

If any check fails, abort the apply pass and revert (`git checkout -- registry/`); leave the report as findings-only.

## Output

Report back:

- Path to the HTML report and timeline JSON
- Counts: findings by priority, fusion candidates, new generic proposals, surviving after Verify
- Any mutations applied (or "none — read-only run")
- Validation status (`gaia validate` exit code if mutations were applied)
- Suggested follow-ups: which P0/P1 findings should be routed to `/gaia-audit` for source-level correction

## Gotchas

- `registry/gaia.json` and `docs/graph/gaia.json` are auto-regen targets — let auto-sync CI handle them on a `review/meta/*` branch. Only commit them manually if the Schema + DAG check requires lockstep (then add labels `skip-scope-check` + `[skip-gen]`).
- Force-push doesn't always re-trigger path-filtered workflows; use `gh workflow run validate.yml --ref <branch>` after `--force-with-lease`.
- The `gaia dev` timeline contributor lands as `unknown` if local git config isn't picked up — patch JSON to set the actual user before committing.
- Renames leave orphan `registry/skills/<type>/<old-id>.md`; delete by hand after rename.
- `gaia docs build` needs `numpy` + `scipy`; install via `pip install -e ".[docs]"` or `pip install -e ".[dev]"`.
- The rarity axis is deprecated — do not flag rarity issues; the schema still requires the field but it carries no review signal.

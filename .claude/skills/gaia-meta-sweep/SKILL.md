---
name: gaia-meta-sweep
description: Run a multi-phase Workflow that audits the entire Gaia registry against META.md, tags Semantic Fusion candidates, proposes new generic skill references in the schema, logs every meta change, and writes a journal-style report to docs/meta/reports/. Use when the user asks for a "full meta audit", "sweep the meta", "audit the whole registry", "produce a meta report", or explicitly types /gaia-meta-sweep.
---

# gaia-meta-sweep

Orchestrate a registry-wide meta audit with the **Workflow** tool. The skill spawns a fan-out of focused audit agents, an adversarial verification pass, a Semantic-Fusion / new-generic-proposal pass, and a synthesis pass that emits a publish-ready HTML report under `docs/meta/reports/`.

This skill is the macro-level companion to `/gaia-meta-audit` (queue building) and `/gaia-audit` (single-target correction). Where those two operate one target at a time, `/gaia-meta-sweep` covers the whole registry in one shot via Workflow orchestration and produces a single artifact the user can publish.

## When to use

Trigger when the user says any of:

- "run a meta sweep" / "sweep the meta" / "full meta audit"
- "audit the whole registry against META.md"
- "produce a new meta report" / "post a report under docs/meta/reports"
- explicit `/gaia-meta-sweep`

Do **not** trigger for single-target audits (route to `/gaia-audit`) or for queue building only (route to `/gaia-meta-audit`).

## Inputs

Ask the user (or infer) before kicking off:

| Input | Description | Default |
|---|---|---|
| `mode` | `read-only` (findings + report only) or `apply-safe` (also runs `gaia dev rename`/`calibrate`/`evidence`/demerit edits for high-confidence corrections) | `read-only` |
| `fusion-aggressiveness` | `moderate` (3–8 high-confidence Semantic Fusion candidates, adversarially verified) or `aggressive` (10–20+ including speculative pairings) | `moderate` |
| `scope` | `all` (every named + generic skill) or a filter expression (e.g. `level>=3★`, `contributor:mbtiongson1`) | `all` |
| `report-slug` | Filename for the report under `docs/meta/reports/` | `<YYYY-MM-DD>-meta-audit.html` |
| `commit` | `none` (leave files unstaged), `worktree` (commit on the current branch), or `branch:<name>` (create + commit on a fresh branch) | `none` |

## Pre-flight

1. Confirm working tree is on a branch you may write to (NOT `main` directly unless the user said so explicitly). Match the branch-prefix policy in `CLAUDE.md` — typically `review/meta/<slug>`.
2. Read `META.md` once and cache its key sections in the workflow prompt:
   - §1 Taxonomy (star tiers, skill types)
   - §2 Evidence Methodology + §2.3 Specialist Path Rubric + §2.4 Meta-Audit Standards
   - §3 Demerits
   - §4 Governance & Promotion (Origin rule)
   - §6 Master Skill Fusion & Pruning (Champion + Semantic Fusion)
3. Snapshot today's registry counts:
   ```bash
   PYTHONIOENCODING=utf-8 python - <<'PY'
   import json, collections
   g = json.load(open("registry/gaia.json", encoding="utf-8"))
   c = collections.Counter(s.get("level","?") for s in g["skills"])
   print({k: c[k] for k in ["0★","1★","2★","3★","4★","5★","6★"]})
   PY
   ```
   These numbers feed the timeline JSON in step 6.

## Workflow tool invocation

Use the Workflow tool. Author the script inline; a self-contained example is below. The user's keyword "workflow" implies opt-in; if absent and the task is large, ask before launching.

### Phase plan

The script is organized as five phases. Default to **pipeline()** between phases (META.md §6 fan-out is naturally per-target). Use a **barrier** only between Survey → Verify (because the synthesis stage needs the deduped finding set to write the report).

```javascript
export const meta = {
  name: 'gaia-meta-sweep',
  description: 'Whole-registry audit against META.md with fusion + new-generic proposals',
  phases: [
    { title: 'Survey',   detail: 'fan-out audit dimensions across registry' },
    { title: 'Fuse',     detail: 'identify Semantic Fusion candidates (META §6.2)' },
    { title: 'Propose',  detail: 'propose new generic skill refs for the schema' },
    { title: 'Verify',   detail: 'adversarially verify each finding' },
    { title: 'Report',   detail: 'synthesize HTML + timeline JSON' },
  ],
}
```

### Phase 1 — Survey (parallel, one agent per dimension)

Spawn one agent per **audit dimension** from META.md §2.4 + §3, each scoped to the whole registry. Use `agent()` with a JSON Schema so each returns structured findings.

Dimensions (each is one agent):

1. `star-bar` — every 3★+ named skill missing/dead `links.github` (META §2.4)
2. `liveness` — run `python scripts/verify_evidence.py`, return broken URLs (META §2.2 Liveness Heartbeat)
3. `origin-attribution` — for every `genericSkillRef`, sort named skills by `createdAt`; flag any non-earliest with `origin: true` (META §4.1)
4. `level-overshoot` — named whose `level` exceeds canonical generic's level (META §1)
5. `brand-coupled` — generic IDs containing brand/product names (META §1, §2.4)
6. `demerits-missing` — 3★+ skills with known heavyweight deps / niche integrations not flagged (META §3)
7. `installability` — 3★+ non-suite skills with `installable: false` or no GitHub link (META §2.4 Star Bar)
8. `placeholder-bodies` — named markdown with stub `## Installation` only (no `## Overview`)
9. `testuser-timelines` — `contributor: testuser` survivors
10. `champion-cluster` — for every generic, surface multi-implementation clusters where no Champion is set (META §6.1)
11. `unique-isolation` — Unique skills with prerequisites or below 4★ (META §1.2 — Unique = level 4★+, 0 prereqs)
12. `class-mismatch` — evidence claiming Class A without peer-review/10k★ marker (META §2.1)

Each agent returns:

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

Spawn one agent that walks the named registry pairwise within shared topical clusters and surfaces fusion candidates per META §6.2. Aggressiveness controls the cap (3–8 vs 10–20).

Schema:

```json
{ "type":"object","required":["candidates"],
  "properties":{"candidates":{"type":"array","items":{
    "type":"object","required":["proposedGenericId","proposedName","prerequisites","level","rationale","exampleNamed"],
    "properties":{
      "proposedGenericId":{"type":"string"},
      "proposedName":{"type":"string"},
      "prerequisites":{"type":"array","items":{"type":"string"},"minItems":2},
      "level":{"enum":["3★","4★"]},
      "rationale":{"type":"string"},
      "exampleNamed":{"type":"array","items":{"type":"string"}}
    }}}}}
```

Reference the worked example from PR #525 (`safishamsi/graphify` + `mattpocock/triage` → `graph-driven-issue-triage` 3★). **Reject** any candidate that requires ≥10k stars (that's an Ultimate; redirect to `/gaia-fuse-full-suite`).

### Phase 3 — Propose (new generic skill refs)

Spawn one agent that reads `registry/schema/meta.json` plus the deduped Phase-1 findings and proposes new **generic** node IDs for any capability that is currently being repeatedly named without a canonical generic to map to. Focus on:

- Brand-coupled generics renamed to abstract phrases (Phase 1 dimension 5).
- Repeated `genericSkillRef` collisions where a more specific Extra would reduce mis-attribution.
- Schema additions implied by the Fusion candidates (Phase 2 prerequisites that don't yet exist).

Schema:

```json
{ "type":"object","required":["proposals"],
  "properties":{"proposals":{"type":"array","items":{
    "type":"object","required":["id","name","type","level","description","prerequisites","reasoning"],
    "properties":{
      "id":{"type":"string","pattern":"^[a-z0-9-]+$"},
      "name":{"type":"string"},
      "type":{"enum":["basic","extra","unique"]},
      "level":{"enum":["0★","1★","2★","3★","4★"]},
      "description":{"type":"string","minLength":10},
      "prerequisites":{"type":"array","items":{"type":"string"}},
      "reasoning":{"type":"string"}
    }}}}}
```

### Phase 4 — Verify (adversarial)

For every Phase-1, Phase-2, and Phase-3 finding, spawn **3 independent skeptic agents** prompted to *refute* the finding. Use diverse lenses (correctness / evidence-strength / META-rule-precedent). A finding survives only if ≥2 of 3 agree it is real.

```javascript
const votes = await parallel(Array.from({length: 3}, () => () =>
  agent(`Try to refute: ${claim}. Default to refuted=true if uncertain.`, {schema: VERDICT})))
const survives = votes.filter(Boolean).filter(v => !v.refuted).length >= 2
```

VERDICT schema:

```json
{ "type":"object","required":["refuted","reason"],
  "properties":{"refuted":{"type":"boolean"},"reason":{"type":"string"},"counterEvidence":{"type":"string"}}}
```

### Phase 5 — Report (synthesis)

A single synthesis agent receives the surviving findings + fusion candidates + new-generic proposals and produces:

1. **`docs/meta/reports/<slug>.html`** — copy the structure of `docs/meta/reports/2026-05-25-programmatic-registry-audit.html` (LaTeX-style journal layout, abstract, executive summary, sections per dimension, references). Title: `Registry Audit Report: <Month YYYY> Meta Sweep`. Author: the current `gaia` user (from `git config user.name` or `gaia` config).
2. **`docs/meta/reports/<YYYY-MM>-timeline.json`** — Chart.js-shaped timeline matching `may-2026-timeline.json` (labels = days in the audit window; datasets = one per star tier). Use the snapshot from Pre-flight step 3 as the right-edge values.
3. **`docs/meta/reports/<slug>.findings.json`** — machine-readable index with every surviving finding tagged by phase, priority, and any META.md section reference. This is the durable artifact other tools (the Liveness Heartbeat, future `gaia dev` migrations) can consume.

The synthesis agent must:

- Tag every meta change with the META.md section number that justifies it.
- Tag every Semantic Fusion candidate with `META §6.2`.
- Tag every new generic proposal with `META §1` + the originating dimension.
- Include a "Before/After" rank distribution table sourced from Pre-flight snapshot vs. projected post-mutation counts.
- If `mode == apply-safe`, list every applied `gaia dev` command in a "Mutations Applied" section, otherwise list them under "Mutations Proposed".

## Apply-safe mutations (only if mode = apply-safe)

After Phase 5 produces the findings.json, replay the high-confidence subset programmatically. **Only these mutations are auto-applyable**; everything else stays a proposal.

| Finding type | CLI command |
|---|---|
| Brand-coupled generic ID | `gaia dev rename <old> <new>` |
| Level overshoot (named > generic) | direct YAML edit on the named markdown (CLI doesn't expose `level`) |
| Missing 3★+ evidence | `gaia dev evidence <id> <url> --class B --evaluator <user>` |
| Dead-link demerit | direct YAML edit: add `broken-evidence` to `demerits` + log a `demote` timeline event |
| Unique reclassification (below 4★) | `gaia dev reclassify <id> basic` |

After every mutation:

```bash
gaia validate
gaia validate --intake
gaia docs build
```

If any check fails, **abort the apply pass** and revert (`git checkout -- registry/`); leave the report as findings-only. Never push a half-applied mutation set.

## Output

Report back to the user:

- Path to the HTML report and timeline JSON
- Counts: findings by priority, fusion candidates, new generic proposals, surviving after Verify
- Any mutations applied (or "none — read-only run")
- Validation status (`gaia validate` exit code if mutations were applied)
- Suggested follow-ups: which findings should be routed to `/gaia-audit` for source-level correction

## Gotchas (cached from PR #525 + audit history)

- `registry/gaia.json` and `docs/graph/gaia.json` are auto-regen targets — let the auto-sync CI handle them on a `review/meta/*` branch unless the Schema + DAG check requires lockstep (then commit + label `skip-scope-check` + `[skip-gen]`).
- Force-push doesn't always re-trigger path-filtered workflows; use `gh workflow run validate.yml --ref <branch>` after `--force-with-lease`.
- The `gaia dev` timeline contributor lands as `unknown` if local git config isn't picked up — patch JSON to set the actual user before committing.
- Renames leave orphan `registry/skills/<type>/<old-id>.md`; delete by hand.
- `gaia docs build` needs `numpy` + `scipy`; install via `pip install -e ".[docs]"` or `pip install -e ".[dev]"`.
- The rarity axis is deprecated — do not flag rarity issues; the schema still requires it but it carries no review signal.

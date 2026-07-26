# Workflow patterns — synthesizer-fallback + commit-frequently

Lessons captured during Phase 1.5 (Session 15, 2026-06-20) about running large dynamic Workflows with many parallel agents and a final synthesizer.

---

## 1. The synthesizer problem

A "synthesizer" is the final agent in a workflow that takes the output of every prior section/fact-check/figure agent and stitches it into a single coherent document (markdown report, blog post, executive brief). Synthesizers tend to:

- **Have the largest input** (every prior agent's output gets concatenated → 50–200k input tokens).
- **Run on Opus** for quality.
- **Time out, hit token limits, or just refuse to commit on the first try** — the API "retries" silently inside the workflow, doubling cost and wall-clock.
- **Return null** when they finally give up after retries, costing the user the entire run if the workflow doesn't have a salvage path.

Marco's directive (2026-06-20): *"synthesize agent almost always retries. If you can have a fallback method to salvage content instead of doing it all over again, implement already. Have it commit frequently as well."*

---

## 2. The fallback pattern — three layers of salvage

Every synthesizer call must be wrapped in a salvage harness with three layers in order of preference. Each layer commits its output as a partial, so even if Layer 3 fails the user has *something* on disk.

### Layer 1 — primary synthesizer (Opus, full context)

```js
let synthesized = null
try {
  synthesized = await agent(buildSynthesisPrompt(sections, figures, factChecks), {
    label: 'synth-primary',
    phase: 'Synth',
    schema: FULL_DOC_SCHEMA,
    model: 'opus',
    effort: 'high'
  })
} catch (e) {
  log(`synth-primary failed: ${e.message} — falling back to L2`)
}
```

If `synthesized` is non-null and validates against the schema, ship it. Done.

### Layer 2 — chunked synthesizer (Sonnet, 2-pass)

If L1 returns null or schema-invalid: split the section list into halves, synthesize each half on Sonnet, then concat. Sonnet is 5× cheaper and 2× faster; two passes are still ahead on cost.

```js
if (!synthesized) {
  const half = Math.ceil(sections.length / 2)
  const [partA, partB] = await parallel([
    () => agent(buildSynthesisPrompt(sections.slice(0, half), figures, factChecks), {
      label: 'synth-L2-A', phase: 'Synth', schema: PARTIAL_DOC_SCHEMA, model: 'sonnet'
    }),
    () => agent(buildSynthesisPrompt(sections.slice(half), figures, factChecks), {
      label: 'synth-L2-B', phase: 'Synth', schema: PARTIAL_DOC_SCHEMA, model: 'sonnet'
    }),
  ])
  if (partA && partB) {
    synthesized = mergePartials(partA, partB) // plain JS string concat with section-aware joiner
    log('synth-L2 succeeded')
  }
}
```

### Layer 3 — mechanical assembly (no agent)

If L1 and L2 both failed: assemble the document **mechanically** in plain JS. No agent call. Concat sections in order, drop figures inline at known anchor points, append a final "## Appendix" with the raw fact-check JSON. Result is rough but **complete and shippable** — the user can polish manually.

```js
if (!synthesized) {
  log('synth-L1+L2 both failed — falling back to mechanical assembly (Layer 3)')
  synthesized = {
    fullMarkdown: assembleMechanical(sections, figures, factChecks),
    salvaged: true,        // flag so the orchestrator knows to flag this in the PR
    layer: 'L3-mechanical'
  }
}
```

`assembleMechanical()` is a pure function — can never fail. Worst case the user gets a well-formatted concatenation of every prior agent's output. That is **infinitely better than null**.

---

## 3. Commit-frequently inside the workflow

Workflows currently return their final synthesized output to the orchestrator, which then writes one file. If the synthesizer dies (and salvage layers also fail), **the orchestrator has nothing**.

Fix: have the workflow call `agent(...)` for a "writer" agent at each major checkpoint that writes the partial output to disk via the agent's Bash tool. The orchestrator polls those files even if the workflow itself dies.

```js
// Inside the workflow, after each section completes:
await agent(`Write this section to docs/meta/drafts/section-${i}.md and commit:
\`\`\`
${section.body}
\`\`\`
Run: git add docs/meta/drafts/section-${i}.md && git commit -m "wip(meta-post): section ${i}" && git push origin <branch>
Report SHA.`,
  { label: `writer-s${i}`, phase: 'Write', model: 'haiku' })
```

Use **Haiku** for the writer agents — they are pure I/O wrappers and don't need reasoning.

---

## 4. Orchestrator side — recovery path

When a workflow's `task-notification` arrives:

1. Read the workflow result (final task output).
2. If `result.fullMarkdown` is present → ship it.
3. Else if `result.layer === 'L3-mechanical'` → ship with `(salvaged)` marker in the PR body.
4. Else (workflow died completely) → check `docs/meta/drafts/` for committed partials and assemble manually.

```bash
# Recovery check
ls docs/meta/drafts/ 2>/dev/null && echo "Partial sections found — assemble manually" || echo "No partials — full re-dispatch"
```

---

## 5. Application to current state (2026-06-20 meta-post)

The currently-running meta-post workflow `wx5yz90ix` (`june-2026-meta-post-wf_de453e83-9e9.js`) was authored **before** this pattern was documented. It does not have L2/L3 fallback. If the synthesizer dies:

1. Check `C:\Users\C5396183\.claude\projects\C--Users-C5396183-gaia-skill-tree\9b6ee9e5-98c9-4870-886e-917de41b4c4b\subagents\workflows\wf_de453e83-9e9\` for the per-agent JSONL transcripts.
2. The 6 section writers each produced full markdown — those are intact in the transcripts.
3. Manually concat them as L3-mechanical assembly.
4. Render via `python scripts/add_post.py report "..." "..." --source docs/meta/2026-06-recap.md`.

For the **next** workflow (any future retrospective, audit, or large multi-agent doc), use this pattern from the start.

---

## 6. Checklist for new workflow scripts

When authoring a new dynamic Workflow with a synthesizer:

- [ ] L1 synthesizer wrapped in try/catch, returns null on failure (not throw)
- [ ] L2 chunked synthesizer on Sonnet as fallback, schema-validated
- [ ] L3 mechanical assembly function, pure JS, never fails
- [ ] Writer agents commit each section's output to `docs/meta/drafts/` (or equivalent staging dir) as it completes
- [ ] Final return value includes `salvaged: bool` and `layer: 'L1' | 'L2' | 'L3-mechanical'` flags
- [ ] Workflow `meta.phases` includes `Synth` and `Write` phases for visibility
- [ ] Orchestrator-side recovery: poll the staging dir if the workflow returns null

---

*Authored: 2026-06-20, Session 15. Pattern derived from cost-overrun observations on the meta-post workflow.*

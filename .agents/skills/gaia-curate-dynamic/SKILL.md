---
name: gaia-curate-dynamic
description: >-
  Dynamic-workflow curation for the Gaia registry. Use this skill — not
  /gaia-curate or /gaia-curate-chain — when the scope is wide, open-ended, or
  high-stakes: "sweep every source for agent skills", "curate the whole
  <domain> space", "find everything new since <date>", "do a deep verification
  pass", "run a parallel curation sweep", "high-stakes registry expansion",
  "fan out across all sources", or /gaia-curate-dynamic. At runtime the
  orchestrator writes its own execution plan, fans out tens-to-hundreds of
  parallel sub-agents across sources and candidates, and validates every
  proposal convergently — a proposer argues for the skill while an independent
  refuter tries to disprove it, iterating until they agree. All state persists
  in a resumable ledger so a multi-hour sweep survives interruption. For a
  quick single-pass, use /gaia-curate. For a small gated batch where schema
  correctness matters more than speed, use /gaia-curate-chain.
version: 1.0.0
argument-hint: "<broad-curation-goal>"
---

# gaia-curate-dynamic

A **dynamic-workflow** registry curation skill. Unlike `/gaia-curate` (one linear pass) and `/gaia-curate-chain` (fixed six-link chain), this skill is **composed at runtime**: the orchestrator reads the goal and the registry, writes its own execution plan, dispatches many sub-agents in parallel, and converges their findings adversarially. Built for breadth (every source at once) and for trust (nothing ships until a refuter fails to break it).

## Choosing the right curation skill

| Skill | Pattern | Best for |
|-------|---------|----------|
| `gaia-curate` | Single pass, one agent | Fast, low-stakes batches |
| `gaia-curate-chain` | Fixed six-link prompt chain | Small batch, schema-critical |
| **`gaia-curate-dynamic`** | **Runtime-composed, massively parallel, convergent** | Wide sweeps, high-stakes verification |

---

## Core design principles

**Runtime composition** — there is no hard-coded phase list. The orchestrator writes a run plan for *this* goal (which sources to shard, how many agents, how many validation rounds) and adapts it as findings arrive. A rich source gets more shards; a dry one gets fewer.

**Parallel fan-out** — independent work runs concurrently because serial processing of a large sweep wastes the session budget. Dispatch all discovery sub-agents in a single turn. One sub-agent per source shard during discovery, one per candidate during deep-dive.

**Convergent validation** — every surviving candidate is argued by a proposer and independently attacked by a refuter. The refuter must not see the proposer's reasoning (only its claims), so it can surface genuine objections rather than rubber-stamping. They iterate until they converge, or until the round budget runs out and the human breaks the tie. Single-verdict decisions are the failure mode this eliminates.

**Persistent, resumable ledger** — all state lives in `generated-output/curate-dynamic-ledger.json` (gitignored). Every stage writes atomically. On every invocation, read the ledger first: if `stage` is not `ship`, print a one-line resume summary and continue from the earliest unfinished stage without redoing finished work.

---

## Ledger shape

```json
{
  "goal": "<argument>",
  "startedAt": "<iso>",
  "stage": "plan|discover|deepdive|converge|synthesize|review|ship",
  "plan": { "sources": [], "discoverShards": 0, "validationRounds": 2 },
  "existingIds": [],
  "discoveries": [ { "source": "...", "rawCandidates": [] } ],
  "candidates": [
    { "id": "...", "name": "...", "evidence": [],
      "proposer": { "verdict": "", "type": "", "level": null },
      "refuter":  { "verdict": "", "objections": [] },
      "converged": false, "rounds": 0, "decision": "" }
  ],
  "batch": [],
  "prUrl": null
}
```

---

## Stage 0 — Plan synthesis (orchestrator)

1. Read `registry/skill-sources.md` and `registry/gaia.json`; record `existingIds` into the ledger for deduplication.
2. Write the run plan: which sources to shard, how many discovery sub-agents, and the validation round budget (default 2; raise to 3 for Level II+ or ultimate proposals). Store under `plan`.
3. Print a one-paragraph plan summary so the user sees the shape of the run before fan-out begins.

## Stage 1 — Parallel discovery (one sub-agent per source shard)

Dispatch all discovery sub-agents in a single turn. Each shard receives one source and this brief:

> Enumerate skill-shaped artifacts in `{{source}}` relevant to `{{goal}}`. For local runs use the `gh` CLI and inspect each repo's `skills/` directory, recording raw `blob/<branch>/<subpath>/SKILL.md` URLs. For cloud/remote runs use GitHub MCP tools — do not claim GitHub is unreachable without checking MCP. Supplement with SkillsMP and arXiv. Return `rawCandidates[]` with `{name, source, url, oneLineCapability}`. Do not judge or rank — harvest only. Drop anything whose `name` slug already appears in `existingIds`.

Write each shard's output to `discoveries[]` as it returns.

## Stage 2 — Parallel candidate deep-dive (one proposer per candidate)

Flatten and dedupe `discoveries` into a candidate set. Dispatch a **proposer** sub-agent per candidate in one batched turn:

> Build the strongest honest case for adding `{{candidate}}` to Gaia. Gather evidence as `{class, source}` — arXiv abs = A, reproducible repo blob URL = B, vendor/community = C; every URL must resolve. Propose `type` (basic/extra/ultimate), `named` (+ `genericSkillRef`), and a star level for named skills. Emit a proposer verdict. Be concrete — unsupported claims will be attacked in the next stage.

## Stage 3 — Convergent validation (proposer ⇄ refuter until they agree)

For each candidate with a proposer verdict, dispatch an **independent refuter** (fresh context; must not see the proposer's reasoning, only its claims):

> Try to break the case for `{{candidate}}`. Check: does each evidence URL resolve and is it on-topic? Is this a duplicate of an existing Gaia skill or another candidate? Is the level inflated for the evidence class? Is it vendor-locked or non-novel — should it collapse into an existing generic via Fusion-First? Return `objections[]` and a verdict: `uphold` / `lower-level` / `merge-into <id>` / `reject`.

The orchestrator reconciles each round:
- **Converged** when proposer and refuter agree on accept + type + level (or both agree to reject/merge). Mark `converged: true`, set `decision`.
- **Not converged** — run another round: proposer answers the objections, refuter re-attacks. Repeat up to `plan.validationRounds`. If still split after the budget, mark `decision: needs-evidence` and carry both views to the human checkpoint.

Independent shards run in parallel; only divergent candidates consume extra rounds.

## Stage 4 — Synthesis and Fusion-First (orchestrator)

Merge converged candidates into `batch[]`:
- Apply **Fusion-First**: collapse vendor variants onto one generic (`literature-search`, not `pubmed`+`arxiv`+`biorxiv`); specialised capabilities become `extra` skills with the generic as a prerequisite.
- Set schema-correct fields: `type` ↔ prereq arity (basic/unique = 0, extra ≥ 2, ultimate ≥ 3); generics carry no level; named skills get `status: awakened`.
- Run pre-flight checks: IDs match their pattern, no DAG cycles. Surface any violations before presenting to the human.

## Stage 5 — Single human checkpoint

Present one consolidated table — converged accepts, plus any `needs-evidence` rows with the proposer/refuter split shown. Collect `accept`/`rename`/`duplicate`/`needs-evidence`/`reject` per row. One approval gate for the whole sweep. Proceed only with ≥ 1 `accept`.

## Stage 6 — Mutation, validation, and ship

All mutations via CLI — never hand-edit `registry/nodes/` or `gaia.json` directly, because direct edits skip timeline logging and can produce states that fail `gaia validate`.

```bash
# generic (no --level)
gaia dev add "Skill Name" --id <id> --type <type> --description "..."
# named (awakened intake; reviewer assigns title/catalogRef/stars later)
gaia dev add "Skill Name" --id <id> --named --contributor <user> \
  --generic-ref <ref> --status awakened
gaia dev evidence <skill-id> "<url>" --class <A|B|C>

gaia validate                      # must exit 0
gaia docs build                    # regenerate docs/projections
gaia docs build --check            # must be clean before push
```

Branch `review/meta/<slug>`, commit `[meta] <title>` plus a `[skip-gen]` docs commit, push (retry on network error with 2s/4s/8s/16s backoff), open the PR, and add the contributor to `README.md ## Contributors`.

Report: ledger path, fan-out counts (sources sharded, candidates deep-dived, rounds spent), converged vs dropped tallies, and the PR URL.

---

## Key constraints (with reasoning)

**Convergence is the bar** — no candidate ships on a single verdict. A proposer and an independent refuter must converge because single-agent judgment is systematically optimistic; the refuter finds the gaps the proposer rationalised away.

**Refuters must not see proposer reasoning** — only claims. Exposing the reasoning anchors the refuter to the proposer's framing, defeating the adversarial purpose. Fresh context means genuine independence.

**Parallelism over serial dispatch** — dispatch independent sub-agents in one turn. Serial dispatch of 50 candidates would exhaust the session before converging; parallel dispatch finishes in fractions of the time.

**Named skills enter as `awakened`** — `title`, `catalogRef`, and star levels are reviewer-only assignments. Submitting anything higher bypasses the human review gate that the awakened status enforces.

**Evidence URLs must resolve and use `blob/` not `tree/`** — the installer only recognises `blob/<branch>/<subpath>` URLs; a `tree/` URL or a bare repo root produces an undiscoverable symlink.

**One PR per sweep** — the whole batch lands for review together so the human can assess Fusion-First decisions and naming consistency across the set.

## Invocation

```
/gaia-curate-dynamic <broad-curation-goal>
```

If the goal is omitted, ask what domain or time-window to sweep before writing the run plan.

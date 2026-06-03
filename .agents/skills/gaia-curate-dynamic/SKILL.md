---
name: gaia-curate-dynamic
description: >-
  Dynamic-workflow curation for the Gaia registry. Instead of a fixed pipeline,
  the orchestrator analyses the request at runtime, writes its own orchestration
  plan, fans out tens-to-hundreds of parallel sub-agents across sources and
  candidates, and validates every proposal convergently — proposer agents argue
  for a skill while refuter agents try to disprove its evidence/level/novelty,
  iterating until they agree. State is persisted to a resumable ledger so a
  large sweep survives interruption. Use for big, open-ended curation —
  "sweep every source for agent skills", "curate the whole <domain> space",
  "find and verify everything new since <date>" — or /gaia-curate-dynamic.
  Prefer /gaia-curate for a quick pass and /gaia-curate-chain for a small,
  fixed, gated batch.
version: 1.0.0
argument-hint: "<broad-curation-goal>"
---

# gaia-curate-dynamic

A **dynamic-workflow** implementation of registry curation, modelled on
[Introducing dynamic workflows in Claude Code](https://claude.com/blog/introducing-dynamic-workflows-in-claude-code).

> *Claude dynamically writes orchestration scripts that run tens to hundreds of
> parallel sub-agents in a single session, checking its work before anything
> reaches you. Multiple agents address a problem from independent angles while
> others attempt refutation, iterating until the answers converge — which is how
> a workflow reaches results a single pass can't.*

Where `/gaia-curate` is one linear pass and `/gaia-curate-chain` is a fixed
six-link prompt chain, this skill is **composed at runtime**: the orchestrator
reads the goal and the registry, decides how much to fan out and how to
partition the work, dispatches many sub-agents in parallel, and converges their
findings adversarially. It is built for breadth (every source at once) and for
trust (nothing ships until a refuter failed to break it).

## The three curation models

| Skill | Pattern | Topology | Best for |
|-------|---------|----------|----------|
| `gaia-curate` | Single pass | one agent | fast, low-stakes batches |
| `gaia-curate-chain` | Prompt chaining + gates | fixed L1→L6 | small batch, schema-critical |
| **`gaia-curate-dynamic`** | **Dynamic workflow** | **runtime-composed, massively parallel, convergent** | wide sweeps, high-stakes verification |

## Core principles

1. **Runtime composition.** There is no hard-coded phase list. The orchestrator
   writes a **run plan** for *this* goal (how many discovery shards, how many
   candidates to deep-dive, how many validation rounds) and stores it in the
   ledger. The plan adapts as findings arrive — a source yielding 60 candidates
   gets more shards than one yielding 3.
2. **Parallel fan-out.** Independent work runs concurrently: one sub-agent per
   source during discovery, one per candidate during deep-dive. Dispatch in
   batches (multiple `Agent` calls in a single turn). Scale the count to the
   work, not to a fixed number.
3. **Convergent validation.** Every surviving candidate is argued by a
   **proposer** and attacked by an **independent refuter**. They iterate until
   they converge on the same accept/level/evidence verdict (or the refuter wins
   and the candidate is dropped). Convergence — not a single judgement — is the
   bar for shipping.
4. **Persistent, resumable ledger.** All state lives in
   `generated-output/curate-dynamic-ledger.json` (gitignored). Every stage
   writes atomically so a multi-hour sweep resumes exactly where it stopped
   after any interruption. On invocation, **read the ledger first** and resume
   the earliest unfinished stage rather than restarting.

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

## Stage 0 — Plan synthesis (orchestrator, runtime-composed)

The orchestrator does this itself — it is the dynamic part:

1. Read `registry/skill-sources.md` and `registry/gaia.json`; record
   `existingIds` (for dedupe) into the ledger.
2. From the goal, **write the run plan**: which sources to shard, how many
   discovery sub-agents, and the validation round budget (default 2, raise to 3
   for Level II+ / ultimate proposals). Store it under `plan`.
3. Print a one-paragraph plan summary so the user can see the shape of the run
   before the fan-out begins.

The plan is a living object — later stages may add shards when a source proves
unexpectedly rich.

## Stage 1 — Parallel discovery (fan-out: one sub-agent per source shard)

Dispatch all discovery sub-agents in a single turn. Each shard gets one source
and this brief:

> Enumerate skill-shaped artifacts in `{{source}}` relevant to `{{goal}}`.
> **Local runs**: use the `gh` CLI; inspect each repo for a `skills/` directory
> and record the raw `blob/<branch>/<subpath>/SKILL.md` URL. **Cloud/remote
> runs**: use the GitHub MCP tools — never claim GitHub is unreachable without
> checking MCP. Supplement with SkillsMP and arXiv. Return `rawCandidates[]`
> with `{name, source, url, oneLineCapability}`. Do not judge or rank — just
> harvest. Drop anything whose `name` slug already appears in `existingIds`.

Write each shard's output to `discoveries[]` as it returns.

## Stage 2 — Parallel candidate deep-dive (fan-out: one proposer per candidate)

Flatten and dedupe `discoveries` into a candidate set. Dispatch a **proposer**
sub-agent per candidate (batch the `Agent` calls), brief:

> Build the strongest honest case for adding `{{candidate}}` to Gaia. Gather
> evidence as `{class, source}` (arXiv abs = A, reproducible repo blob = B,
> vendor/community = C; every URL must resolve). Propose `type`
> (basic/extra/ultimate), `named` (+ `genericSkillRef`), and a star level for
> named. Emit a `proposer` verdict. Be concrete; unsupported claims will be
> attacked in the next stage.

## Stage 3 — Convergent validation (proposer ⇄ refuter until they agree)

For each candidate with a proposer verdict, dispatch an **independent refuter**
(fresh context, must not see the proposer's reasoning, only its claims):

> Try to **break** the case for `{{candidate}}`. Check: is each evidence URL
> real and on-topic? Is it a duplicate of an existing Gaia skill or another
> candidate? Is the level inflated for the evidence class? Is it vendor-locked
> (a demerit) or non-novel (Fusion-First: should it collapse into an existing
> generic)? Return `objections[]` and a verdict: `uphold` / `lower-level` /
> `merge-into <id>` / `reject`.

The orchestrator reconciles each round:
- **Converged** when proposer and refuter agree on accept + type + level (or
  both agree on reject/merge). Mark `converged: true`, set `decision`.
- **Not converged** → run another round (proposer answers the objections,
  refuter re-attacks), up to `plan.validationRounds`. If still split after the
  budget, mark `decision: needs-evidence` and carry both views to the human.

Independent shards run in parallel; only divergent candidates consume extra
rounds. This is the convergent-validation loop that makes the dynamic workflow
worth its cost.

## Stage 4 — Synthesis & Fusion-First (orchestrator)

Merge converged candidates into `batch[]`:
- Apply **Fusion-First**: collapse vendor variants onto one generic
  (`literature-search`, not `pubmed`+`arxiv`+`biorxiv`); orchestrate
  specialised capabilities as an `extra` with the basics as prerequisites.
- Set schema-correct fields: `type` ↔ prereq arity (basic/unique 0, extra ≥2,
  ultimate ≥3); generics carry **no level**; named skills get
  `status: awakened`.
- Run the same deterministic pre-flight as the chain skill (IDs match their
  pattern, no DAG cycles) before presenting anything.

## Stage 5 — Single human checkpoint

Present one consolidated table — converged accepts, plus any `needs-evidence`
rows with the proposer/refuter split shown — and collect
`accept`/`rename`/`duplicate`/`needs-evidence`/`reject`. One approval gate for
the whole sweep; proceed only with ≥1 `accept`.

## Stage 6 — Mutation, validation & ship

Deterministic, programmatic-only:
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
Branch `review/meta/<slug>`, commit `[meta] <title>` + a `[skip-gen]` docs
commit, push (retry on network error 2s/4s/8s/16s), open the PR, and add the
contributor to `README.md` `## Contributors`. Report the ledger path, fan-out
counts (sources sharded, candidates deep-dived, rounds spent), converged vs
dropped tallies, and the PR URL.

---

## Resume protocol

On every invocation: if `generated-output/curate-dynamic-ledger.json` exists and
its `stage` is not `ship`, print a one-line resume summary and continue from the
earliest unfinished stage. Never restart a completed fan-out — re-dispatch only
the sub-agents whose ledger entries are missing or unconverged.

## Constraints

| Rule | Detail |
|------|--------|
| **Dynamic, not fixed** | The orchestrator writes and adapts the run plan; fan-out scales to the work. Stages 1–3 may re-shard. |
| **Convergence is the bar** | No candidate ships on a single verdict — a proposer and an independent refuter must converge (or the human breaks a tie). |
| **Parallelism** | Dispatch independent sub-agents in one turn. Refuters must not see proposer reasoning. |
| **Programmatic-First** | All mutations via `gaia dev add/merge/split/evidence`. Never hand-edit `registry/nodes/` or `gaia.json`. |
| **Named = awakened** | Named skills submitted `status: awakened`; `title`/`catalogRef`/stars are reviewer-only. Generics carry no level. |
| **Evidence reality** | Every `source` resolves (arXiv abs = A, repo blob URL = B, vendor/community = C). |
| **Edges** | `sourceSkillId`/`targetSkillId`; `edgeType ∈ {prerequisite, corequisite, enhances}`. No `derivative` — use `enhances`. |
| **Encoding** | All Python `open()` uses `encoding='utf-8'`. |
| **Resumable** | Ledger writes are atomic; a run survives interruption and resumes without redoing finished work. |
| **One PR** | A whole sweep lands as a single review PR. |

## Invocation

```
/gaia-curate-dynamic <broad-curation-goal>
```
If the goal is omitted, ask what domain or time-window to sweep before writing
the run plan.

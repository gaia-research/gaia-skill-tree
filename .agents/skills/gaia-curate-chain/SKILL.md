---
name: gaia-curate-chain
description: >-
  Prompt-chaining curation for the Gaia registry — six discrete links (Scope,
  Research, Design, Human Review, Mutate, Ship), each handed to a fresh
  sub-agent, with a programmatic gate between every link that must pass before
  the chain advances. Use when evidence quality and schema correctness matter
  more than speed: "curate the tree carefully", "add skills with gates",
  "step-by-step registry expansion", "gated curation", "auditable curation",
  "chain the curation", "curate incrementally", "add skills without mistakes",
  "high-quality skill additions", "small batch precision curation". Also
  triggers on /gaia-curate-chain. For a fast single-pass run use /gaia-curate;
  for a wide domain sweep with parallel sub-agents use /gaia-curate-dynamic.
version: 1.1.0
argument-hint: "<topic-or-source-to-curate>"
---

# gaia-curate-chain

A **prompt-chaining** implementation of Gaia registry curation, following the
pattern described in Anthropic's
[Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents).

> *Prompt chaining decomposes a task into a sequence of steps, where each LLM
> call processes the output of the previous one. You can add programmatic checks
> (gates) on any intermediate step to ensure the process stays on track.*

Curation is a natural fit: it's a linear pipeline (research → design → review
→ mutate → ship), each phase is easier to get right in isolation, and catching
a bad evidence URL or invalid schema shape at a gate is far cheaper than
discovering it after `gaia validate` or CI fails. The trade-off is latency for
accuracy.

```
L1 Scope ──g1──▶ L2 Research ──g2──▶ L3 Map/Design ──g3──▶ L4 Human Review
                                                                  │ g4
                                                                  ▼
                          ◀── ship ── L6 Regenerate+PR ◀──g5── L5 Mutate
```

Each `Ln` is one sub-agent call. Each `gn` is a **programmatic gate** the
orchestrator runs itself — a deterministic shell/jq check, not an LLM
judgement. The chain advances only when the gate passes. On failure the gate
**routes back one link** with the failure reason, bounded to 2 retries per
gate, then stops and asks the user.

## Which curation skill to use

| Skill | Pattern | When to use |
|-------|---------|-------------|
| `gaia-curate` | Single linear pass | Fast, low-stakes batches |
| **`gaia-curate-chain`** | **Fixed topology + programmatic gates** | Small batch where schema correctness must be verified at each step |
| `gaia-curate-dynamic` | Runtime-composed, massively parallel, convergent | Wide domain sweeps; high-stakes verification at scale |

## Orchestrator responsibility

You (the orchestrator) own three things: holding the chain state file, dispatching each link as a sub-agent, and running each gate. You do **not** do a link's research/design/mutation work — that belongs to the sub-agent. The one exception is gate execution (deterministic shell), which is always yours to run.

## Chain state

Persist one JSON blob to `generated-output/curate-chain-state.json` (gitignored)
so each sub-agent can read prior output without re-deriving it.

```json
{
  "topic": "<argument>",
  "link": 1,
  "existingIds": ["..."],
  "targets": ["..."],
  "candidates": [ { "id": "...", "name": "...", "evidence": [], "typeGuess": "" } ],
  "batch": [ { "id": "...", "type": "", "level": null, "named": false, "status": "", "prereqs": [], "evidence": [], "decision": "" } ],
  "mutations": [],
  "prUrl": null
}
```

---

## L1 — Scope & dedupe

Dispatch a sub-agent (lightweight reasoning is enough) with:

> Read `registry/skill-sources.md` (the authoritative source list) and
> `registry/gaia.json`. Emit: (a) `existingIds` — every skill ID already in
> the graph, and (b) `targets` — 5–15 concrete research targets for topic
> `{{topic}}`, each a marketplace/org/repo/paper lead drawn from the sources
> file. If you find a source not yet listed, note it for inclusion in the PR.
> Write both arrays into the chain state. Do no research yet.

**Gate g1** (orchestrator runs):
```bash
jq -e '(.existingIds|length>0) and (.targets|length>0)' \
  generated-output/curate-chain-state.json
```
Fail → re-dispatch L1 with the reason. Pass → L2.

---

## L2 — Research & evidence

Dispatch a fresh sub-agent per cluster of targets. These are independent, so
they may run in parallel (*sectioning* — a sibling pattern described in the
article):

> For each target, gather concrete evidence. **Local runs**: use the `gh` CLI
> (`gh search repos --topic=… --sort=stars`), then inspect for a `skills/`
> directory and use the **raw `blob/<branch>/<subpath>/SKILL.md` URL** as the
> source — never a bare repo root. **Cloud/remote runs (no `gh`)**: use the
> GitHub MCP tools (`search_repositories`, `get_file_contents`) — never claim
> `gh` is unavailable without checking MCP first. Supplement with SkillsMP
> (`https://skillsmp.com/api/v1/skills/search?q=…`, Class C) and arXiv abs
> URLs (Class A) for Level II+ candidates. Emit `candidates[]` with an
> `evidence[]` array of `{class, source}` per candidate. Every `source` must
> be a real, resolvable URL.

**Gate g2 — evidence gate** (the primary quality gate of the chain):
```bash
# Every candidate has >=1 evidence URL; Level II+ candidates have >=1 Class A or B source
jq -e 'all(.candidates[];
        (.evidence|length>0) and
        ((.typeGuess|test("basic|generic")) or
         ([.evidence[].class]|any(.=="A" or .=="B"))))' \
  generated-output/curate-chain-state.json
```
Fail → route back to L2 for the failing candidates only (carry their IDs in the
reason). Drop any candidate that still has no resolvable evidence after retry.

---

## L3 — Schema mapping & batch design

Dispatch a design sub-agent (heavier reasoning preferred here — schema errors
caught now are far cheaper than retrying after g5 fails):

> Turn `candidates[]` into a `batch[]` ready for the CLI. For each candidate:
>
> - **Fusion-First**: map multiple vendor implementations of one concept onto a
>   single generic (e.g. don't mint `pubmed`/`arxiv`/`biorxiv` separately — use
>   `literature-search`). Orchestrate specialised capabilities as an `extra`
>   with the basics as prerequisites.
> - Assign `type`: `basic`/`unique` (0 prereqs), `extra` (≥2), `ultimate` (≥3).
> - `named`: true if it is a specific named implementation. Named skills MUST
>   be submitted with `status: "awakened"` — only reviewers later promote to
>   `named` and assign `title`/`catalogRef`; never set those here. Generic
>   nodes use `status: "provisional"`.
> - `level`: named only, `2★–6★`; omit entirely for generics (the schema
>   rejects a level on a generic node).
> - Demerit check (`heavyweight-dependency`/`niche-integration`/`experimental-feature`)
>   applies only at 3★+.
>
> Emit the full `batch[]` and a review table.

**Gate g3 — schema pre-flight gate** (catches invalid shapes before any
mutation touches the registry — this is why the gate exists):
```bash
jq -e '
 def gidok: test("^[a-z][a-z0-9]*(-[a-z0-9]+)*$");
 def nidok: test("^[a-z0-9][a-z0-9_-]*/[a-z0-9][a-z0-9_-]*$");
 all(.batch[];
   (if .named then (.id|nidok) else (.id|gidok) end)
   and (if .type=="basic" or .type=="unique" then (.prereqs|length)==0
        elif .type=="extra"  then (.prereqs|length)>=2
        elif .type=="ultimate" then (.prereqs|length)>=3 else false end)
   and (if .named then (.status=="awakened")
        else (.status=="provisional" and (.level==null)) end))' \
  generated-output/curate-chain-state.json
```
Also confirm no prerequisite cycle — every prereq must be an `existingId` or
another batch entry, and the union must form a DAG. Fail → route back to L3
with the offending field. Pass → L4.

---

## L4 — Human review gate

The orchestrator presents the L3 table directly to the user. This gate is a
person, not a script — it exists because the registry is a shared resource and
schema-valid does not mean semantically correct.

| ID | Name | Type | Stars | Prereqs | Demerits | Named? | Status |
|----|------|------|-------|---------|----------|--------|--------|

For each row the user marks: `accept` / `rename <new-id>` / `duplicate` /
`needs-evidence` / `reject`. Apply renames in place, drop everything that is
not `accept`/`rename`, and write the resolved `decision` per batch entry.

**Gate g4**: proceed only if ≥1 `accept` remains. Otherwise stop and report.
Do not advance to L5 without explicit user review — this is the one gate
that can never be automated away.

---

## L5 — Execute mutations (CLI only)

Dispatch as a sub-agent (or run as orchestrator — this link is deterministic
CLI). All mutations go through `gaia dev`; hand-editing `registry/nodes/` skips
timeline logging and corrupts the audit trail.

For each accepted batch entry:

Generic (no `--level` — the schema rejects a level on a generic):
```bash
gaia dev add "Skill Name" --id <id> --type <type> --description "..."
```

Named (awakened intake — reviewer assigns title/catalogRef/stars later):
```bash
gaia dev add "Skill Name" --id <id> --named --contributor <user> \
  --generic-ref <ref> --status awakened
```

Evidence:
```bash
gaia dev evidence <skill-id> "<url>" --class <A|B|C>
```

Relationships via `gaia dev link` / `gaia dev merge` / `gaia dev split`.
Record each command run into `mutations[]`.

**Gate g5 — validation gate**:
```bash
gaia validate && echo GATE_G5_PASS
```
Run `gaia validate --intake` too if the run produced an intake batch. Fail →
route back to L5 with the validator output. After 2 failed retries, stop and
surface the error — never push a registry that fails validation.

---

## L6 — Regenerate & ship

Final link (deterministic enough for the orchestrator to run directly):

1. `gaia dev docs` — regenerate `docs/`, projections, and Class S artifacts.
2. Branch `review/meta/<slug>`, commit:
   ```bash
   git add registry/ docs/ README.md
   git commit -m "[meta] Add <topic> skills — chained curation"
   git commit -am "chore(docs): regenerate after registry edits [skip-gen]" || true
   ```
3. Push `-u origin review/meta/<slug>` (retry on network error: 2s/4s/8s/16s).
4. Open the PR via GitHub MCP `create_pull_request`. Auto-triage CI classifies
   it; ultimates and `needs-review` items require maintainer approval.
5. Add the contributor to `## Contributors` in `README.md` (`| @username | Brief description |`).

**Gate g6 — ship gate**:
```bash
gaia dev docs --check && echo GATE_G6_PASS
```
Plus version lockstep across the four manifests. Fail → fix and re-run before
pushing — a stale-docs branch will fail CI.

---

## Constraints

| Rule | Reason |
|------|--------|
| **Fixed topology** | Links run L1→L6. A gate may route back one link (max 2 retries) but never skip forward — forward skips defeat the purpose of the gates. |
| **Gates are programmatic** | Every `gn` except g4 is a deterministic shell/jq check. LLM opinion is not a substitute here — jq either passes or it doesn't. |
| **Programmatic-First** | Mutations via `gaia dev add/merge/split/evidence` only. Hand-edits skip timeline logging and corrupt the audit trail. |
| **Named = awakened** | Named skills submitted `status: "awakened"`; `title`/`catalogRef` are reviewer-only. Generics use `provisional` and carry no level. |
| **Evidence reality** | Every `source` is a real, resolvable URL: arXiv abs = Class A, reproducible repo blob URL = Class B, vendor/community = Class C. |
| **Edges** | `sourceSkillId`/`targetSkillId`; `edgeType ∈ {prerequisite, corequisite, enhances}`. No `derivative` — use `enhances`. |
| **Encoding** | All Python `open()` uses `encoding='utf-8'` to avoid CP-1252 drift on Windows. |
| **Orchestrator scope** | Dispatches links and runs gates only — does not do a link's research/design/mutation work itself. |
| **Single PR** | One PR per chain run. |

## Invocation

```
/gaia-curate-chain <topic-or-source>
```
If the topic is omitted, ask which area to curate before starting L1.

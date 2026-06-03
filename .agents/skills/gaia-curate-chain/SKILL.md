---
name: gaia-curate-chain
description: >-
  Prompt-chaining workflow for expanding the Gaia registry. Decomposes the
  traditional /gaia-curate pipeline into six discrete links, each handled by a
  fresh sub-agent that consumes the previous link's structured output, with a
  programmatic GATE between every link that must pass before the chain advances.
  Use when the user wants curation to be auditable, incremental, and hard to
  derail — "curate the tree carefully", "chain the curation", "add skills with
  gates", "step-by-step registry expansion" — or types /gaia-curate-chain.
  Prefer the flat /gaia-curate for a quick single-pass run; prefer this when
  evidence quality and schema correctness matter more than latency.
version: 1.0.0
argument-hint: "<topic-or-source-to-curate>"
---

# gaia-curate-chain

A **prompt-chaining** implementation of registry curation, following the
"workflow" patterns in Anthropic's
[Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents).

> *Prompt chaining decomposes a task into a sequence of steps, where each LLM
> call processes the output of the previous one. You can add programmatic checks
> (see "gate" below) on any intermediate steps to ensure the process is still on
> track.*

Curation is a textbook fit for this pattern: it is already a linear pipeline
(research → design → review → mutate → ship), each step is easier to get right
in isolation than as one mega-prompt, and a wrong intermediate result (bad
evidence, an invalid ID, a cycle) is far cheaper to catch at a gate than after
`gaia validate` or CI fails. We trade latency for accuracy.

```
L1 Scope ──g1──▶ L2 Research ──g2──▶ L3 Map/Design ──g3──▶ L4 Human Review
                                                                  │ g4
                                                                  ▼
                          ◀── ship ── L6 Regenerate+PR ◀──g5── L5 Mutate
```

Each `Ln` is one sub-agent call. Each `gn` is a **programmatic gate** the
ORCHESTRATOR runs itself (a shell/jq check, not an LLM judgement). The chain
only advances when the gate passes; on failure the gate **routes back one
link** with the failure reason (bounded to 2 retries per gate, then it stops
and asks the user).

## How this differs from `feature-pipeline` and flat `gaia-curate`

| Skill | Pattern (per the article) | When to use |
|-------|---------------------------|-------------|
| `gaia-curate` | Single linear pass, one agent | Fast, trusted, low-stakes batches |
| `feature-pipeline` | Orchestrator–workers (dynamic delegation, stop hooks) | Explore → fix → ship a feature |
| **`gaia-curate-chain`** | **Prompt chaining with gates** (fixed topology, deterministic checks) | High-stakes curation where each link must be verifiably correct before the next begins |

The ORCHESTRATOR (the active agent) owns only: holding the chain state file,
dispatching each link, and running each gate. It does **not** do a link's
research/design/mutation work itself — that is the sub-agent's job. The one
exception is gate execution (deterministic shell), which is the orchestrator's.

## Chain state

The orchestrator keeps a single JSON blob threaded through the chain. Each link
appends to it; each gate reads it. Persist it to
`generated-output/curate-chain-state.json` (gitignored) so a link's sub-agent
can read the prior output without re-deriving it.

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

Dispatch a sub-agent (Explore-class is enough) with:

> Read `registry/skill-sources.md` (the authoritative source list) and
> `registry/gaia.json`. Emit (a) `existingIds`: every skill ID already in the
> graph, and (b) `targets`: 5–15 concrete research targets for topic
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

Dispatch a fresh sub-agent per cluster of targets (these are independent, so
they may run in parallel — *sectioning*, a sibling pattern in the article):

> For each target, gather concrete evidence. **Local runs**: use the `gh` CLI
> (`gh search repos --topic=… --sort=stars`, then inspect for a `skills/`
> directory and use the **raw `blob/<branch>/<subpath>` SKILL.md URL** as the
> source — never a bare repo root). **Cloud/remote runs (no `gh`)**: use the
> GitHub MCP tools (`search_repositories`, `get_file_contents`) — never claim
> `gh` is unavailable without checking MCP first. Supplement with SkillsMP
> (`https://skillsmp.com/api/v1/skills/search?q=…`, Class C) and arXiv abs URLs
> (Class A) for Level II+ candidates. Emit `candidates[]` with an `evidence[]`
> array of `{class, source}` per candidate. Every `source` must be a real,
> resolvable URL.

**Gate g2 — the evidence gate** (the key quality gate of the chain):
```bash
# every candidate has >=1 evidence URL, and every Level II+ candidate
# has at least one Class A or B source
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

Dispatch a design sub-agent (HEAVIER reasoning preferred):

> Turn `candidates[]` into a `batch[]` ready for the CLI. For each:
> - **Fusion-First**: map multiple vendor implementations of one concept onto a
>   single generic (e.g. don't mint `pubmed`/`arxiv`/`biorxiv` — use
>   `literature-search`). Orchestrate specialised capabilities as an `extra`
>   with the basics as prerequisites.
> - Assign `type`: `basic`/`unique` (0 prereqs), `extra` (≥2), `ultimate` (≥3).
> - `named`: true if it is a specific implementation. **Named skills MUST be
>   submitted with `status: "awakened"`** (only reviewers later promote to
>   `named` and assign `title`/`catalogRef` — never set those here). Generic
>   nodes use `status: "provisional"`.
> - `level`: named only, `2★–6★`; **omit entirely for generics** (the schema
>   rejects a level on a generic node).
> - Demerit check (`heavyweight-dependency`/`niche-integration`/`experimental-feature`)
>   applies only at 3★+.
> Emit the full `batch[]` and a review table.

**Gate g3 — the schema pre-flight gate** (catch invalid shapes before any
mutation hits the registry):
```bash
jq -e '
 def gidok: test("^[a-z][a-z0-9]*(-[a-z0-9]+)*$");       # generic id
 def nidok: test("^[a-z0-9][a-z0-9_-]*/[a-z0-9][a-z0-9_-]*$");  # contributor/skill-name
 all(.batch[];
   (if .named then (.id|nidok) else (.id|gidok) end)
   and (if .type=="basic" or .type=="unique" then (.prereqs|length)==0
        elif .type=="extra"  then (.prereqs|length)>=2
        elif .type=="ultimate" then (.prereqs|length)>=3 else false end)
   and (if .named then (.status=="awakened")
        else (.status=="provisional" and (.level==null)) end))' \
  generated-output/curate-chain-state.json
```
Also confirm no prerequisite cycle (every prereq is an `existingId` or another
batch ID, and the union forms a DAG). Fail → route back to L3 with the offending
field. Pass → L4.

---

## L4 — Human review gate (human-in-the-loop)

The orchestrator presents the L3 table directly to the user — this gate is a
person, not a script:

| ID | Name | Type | Stars | Prereqs | Demerits | Named? | Status |
|----|------|------|-------|---------|----------|--------|--------|

For each row the user marks: `accept` / `rename <new-id>` / `duplicate` /
`needs-evidence` / `reject`. Apply renames in place, drop everything that is not
`accept`/`rename`, and write the resolved `decision` per batch entry.

**Gate g4**: proceed only if ≥1 `accept` remains. Otherwise stop and report.
**Do not advance to L5 without explicit user review** — this is the one gate
that cannot be automated away.

---

## L5 — Execute mutations (CLI only)

Dispatch (or run as orchestrator, since this link is deterministic CLI):

> For each accepted batch entry, mutate **only** via `gaia dev` commands
> (never hand-edit `registry/nodes/` or `gaia.json`):
>
> Generic (no `--level`):
> ```bash
> gaia dev add "Skill Name" --id <id> --type <type> --description "..."
> ```
> Named (awakened intake state):
> ```bash
> gaia dev add "Skill Name" --id <id> --named --contributor <user> \
>   --generic-ref <ref> --status awakened
> ```
> Evidence:
> ```bash
> gaia dev evidence <skill-id> "<url>" --class <A|B|C>
> ```
> Relationships via `gaia dev link` / `gaia dev merge` / `gaia dev split`.
> Record each command run into `mutations[]`.

**Gate g5 — validation gate**:
```bash
gaia validate && echo GATE_G5_PASS
```
(`gaia validate --intake` too if the run produced an intake batch.) Fail → route
back to L5 with the validator output; after 2 failed retries, stop and surface
the error to the user — do not push a registry that fails validation.

---

## L6 — Regenerate & ship

Final link (deterministic enough for the orchestrator):

1. `gaia docs build` — regenerate `docs/`, `registry.md`, projections.
2. Branch `review/meta/<slug>`, commit
   `[meta] <Title> — <brief>` plus a docs commit tagged `[skip-gen]`:
   ```bash
   git add registry/ docs/ README.md
   git commit -m "[meta] Add <topic> skills — chained curation"
   git commit -am "chore(docs): regenerate after registry edits [skip-gen]" || true
   ```
3. Push `-u origin review/meta/<slug>` (retry on network error: 2s/4s/8s/16s).
4. Open the PR (GitHub MCP `create_pull_request`). Auto-triage CI classifies it;
   ultimates and `needs-review` items require maintainer approval.
5. Add the contributor to the `## Contributors` section of `README.md` in the
   same PR (`| @username | Brief description |`).

**Gate g6 — ship gate**:
```bash
gaia docs build --check && echo GATE_G6_PASS
```
plus version lockstep across the four manifests. Fail → fix and re-run, never
push a stale-docs branch.

---

## Constraints

| Rule | Detail |
|------|--------|
| **Fixed topology** | Links run L1→L6 in order. A gate may route back **one** link (max 2 retries) but never skip forward. |
| **Gates are programmatic** | Every `gn` except g4 is a deterministic shell/jq check the orchestrator runs — not an LLM opinion. g4 is the human gate. |
| **Programmatic-First** | All mutations via `gaia dev add/merge/split/evidence`. Never hand-edit `registry/nodes/` or `gaia.json`. |
| **Named = awakened** | Named skills are submitted `status: "awakened"`; `title`/`catalogRef` are reviewer-only. Generics use `provisional` and carry no level. |
| **Evidence reality** | Every `source` is a real, resolvable URL (arXiv abs = Class A, reproducible repo blob URL = Class B, vendor/community = Class C). |
| **Edges** | `sourceSkillId`/`targetSkillId`; `edgeType ∈ {prerequisite, corequisite, enhances}`. No `derivative` type — use `enhances`. |
| **Encoding** | All Python `open()` uses `encoding='utf-8'`. |
| **No self-work** | Orchestrator dispatches links and runs gates; it does not do a link's research/design/mutation. |
| **Single PR** | One PR per chain run. |

## Invocation

```
/gaia-curate-chain <topic-or-source>
```
If the topic is omitted, ask which area to curate before starting L1.

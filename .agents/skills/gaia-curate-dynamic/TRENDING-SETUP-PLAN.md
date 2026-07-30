# Trending-Set Up Plan for `/gaia-curate-dynamic` with Worker-Free Subagents at Concurrency=16

> **Planner-free output.** This document is the plan itself — produced by the planner-free agent, not executed. It specifies every configuration artifact, file path, and dispatch step needed to produce one batch intake containing 16 curation seeds for review.

---

## Goal

Set up the `/gaia-curate-dynamic` workflow so that it runs `/gaia-curate-trending` with 16 worker-free subagents at concurrency=16, producing a single batch intake JSON (and corresponding GitHub issue) with exactly 16 proposed curation seeds ready for L4 human review.

---

## 1. Preflight Configuration

### File: `.agents/skills/gaia-curate-dynamic/preflight.json`

This is the runtime configuration record persisted before any dispatch begins. It captures the harness, concurrency target, model tiers, and spawn mode.

```json
{
  "harness": "claude-code",
  "version": "3.0.0",
  "spawnMode": "subagent",
  "requestedConcurrency": 16,
  "observedConcurrency": 1,
  "structuredOutput": true,
  "usageReporting": "native",
  "budgetEnforcement": "orchestrator",
  "models": {
    "orchestrator": "claude-opus-4",
    "lunaLight": "kilo-auto/free:medium",
    "lunaHigh": "kilo-auto/free:medium"
  },
  "harnessResolution": {
    "claudeCode": {
      "binary": "$CLAUDE_BIN",
      "fallback": "PATH resolution",
      "recipe": "\"$CLAUDE_BIN\" -p --model \"$LUNA_LIGHT_MODEL\" --output-format json < \"$PROMPT_FILE\""
    }
  },
  "capacityEstablisher": {
    "phase": "canary",
    "wave0": { "agents": 1, "tier": "lunaLight", "task": "fetch first source page, parse SKILL.md candidates" },
    "wave1": { "agents": 2, "tier": "lunaLight", "task": "fetch two source pages, parse SKILL.md candidates" },
    "gate": "Both wave0 and wave1 must succeed before scaling to full concurrency."
  },
  "concurrencySchedule": {
    "description": "Scale from canary (1) to wave (2) to full (16)",
    "steps": [
      { "phase": "canary", "concurrency": 1, "condition": "first Luna Light harvester succeeds" },
      { "phase": "wave", "concurrency": 2, "condition": "both wave0 and wave1 succeed" },
      { "phase": "full", "concurrency": 16, "condition": "wave gate passed; no 429/overload observed" }
    ],
    "backoffRule": "On 429/overload/5xx/timeout: reduce concurrency, retry at most twice with backoff. Never increase retries."
  }
}
```

### Design rationale

| Decision | Rationale |
|---|---|
| `harness: claude-code` | Active harness; resolves `CLAUDE_BIN` first then PATH |
| `spawnMode: subagent` | The workflow tool's `agent()` calls spawn subagent processes; compatible with its concurrency model |
| `requestedConcurrency: 16` | Matches `defaultConcurrency: 16` in `~/.pi/workflows/settings.json` |
| `observedConcurrency: 1` | Starts at 1 (canary), then 2 (wave), then scales to 16 |
| `models.lunaLight = kilo-auto/free:medium` | Worker-free model tier; orchestrator stays on session model |
| `budgetEnforcement: orchestrator` | Orchestrator tracks cost |
| `usageReporting: native` | Native if harness exposes token counts |

---

## 2. Source Manifest

### File: `registry-for-review/discovered-artifacts/trending-manifest.yaml`

```yaml
contractVersion: curate-trending-manifest-v1
windowDays: [7, 30]
pageSize: 5
runId: "trending-16-seeds-001"
generatedAt: "2026-07-11T00:00:00Z"

sources:
  - id: marketplace-01
    lane: marketplace
    url: https://www.aitools.directory/skills
    cursor: null
    pages: 4
    pageQuota: 5
    notes: "Primary marketplace listing; trending label detector"

  - id: marketplace-02
    lane: marketplace
    url: https://awesome-skills.dev/listings
    cursor: null
    pages: 4
    pageQuota: 5
    notes: "Secondary marketplace; cross-source recurrence check"

  - id: source-repo-01
    lane: source-repository
    url: https://github.com/gaia-research/skills
    cursor: null
    pages: 4
    pageQuota: 5
    notes: "Official gaia-research skills repo; star-delta source"

  - id: github-topic-01
    lane: github-topic
    url: https://github.com/topics/gaia-skills
    cursor: null
    pages: 4
    pageQuota: 5
    notes: "GitHub topic page; new-skill discovery lane"
```

### Capacity math

| Parameter | Value |
|---|---|
| Sources | 4 |
| Pages per source | 4 |
| Total pages (shards) | 16 |
| Max raw candidates per page | 5 |
| Maximum raw candidates | 80 |
| Expected unique after dedup | ~25–35 |
| Target review-ready seeds | 16 |
| Safety margin | 80 raw → 16 review-ready (filtering at dedup + mapping) |

---

## 3. Worker-Free Subagent Dispatch Model

### 3.1 Architecture overview

```
Orchestrator (Sol, claude-opus-4, inline)
  │
  ├── Preflight Phase
  │     ├── resolve harness (CLAUDE_BIN → PATH)
  │     ├── write preflight.json
  │     └── establish capacity (canary → wave → scale)
  │
  ├── Manifest Load Phase
  │     ├── read manifest.yaml
  │     ├── compute shards (1 shard per source page = 16 shards)
  │     └── assign shard IDs: shard-00 through shard-15
  │
  ├── Capacity Establishment Phase
  │     ├── Wave 0: 1 worker-free subagent (shard-00)
  │     ├── Wave 1: 2 worker-free subagents (shard-01, shard-02)
  │     └── Gate: both waves succeeded → proceed to full dispatch
  │
  └── Full Dispatch Phase (concurrency=16)
        ├── workflow tool: concurrency=16, agent() × 16
        ├── Each agent = worker-free (kilo-auto/free:medium)
        ├── Each agent processes 1 shard (1 source page)
        └── Parallel execution: all 16 shards in-flight simultaneously
```

### 3.2 How concurrency=16 is achieved

1. The `workflow` tool (not the `subagent` tool) is used for dispatch. It accepts a `concurrency` parameter, `maxAgents`, and `agentRetries`.
2. `~/.pi/workflows/settings.json` already has `defaultConcurrency: 16` — this aligns with `requestedConcurrency: 16` in preflight.json.
3. The `workflow` tool's `agent()` function spawns worker-free subagent processes (`kilo-auto/free:medium` model).
4. 16 `agent()` calls fan out in a single `workflow` invocation with `concurrency: 16`.
5. This operates above the `subagent` tool's cap (`MAX_CONCURRENCY=4`) because the workflow tool manages its own dispatch queue.

### 3.3 Worker-free subagent contract

Each of the 16 worker-free subagents executes this bounded loop per shard:

```
For each shard (source page assignment):
  1. fetch the source page, persist next cursor to source-snapshots.json
  2. resolve each lead to canonical repo path + immutable commit
  3. fetch and parse the real SKILL.md
  4. exact-dedupe by normalized repo/path, canonical URL, content hash
  5. query the generic snapshot (discovery-packet-v2 schema)
  6. supply ≤3 generic mapping options
  7. request one bounded core decision (6 precedence rules from CURATION-CORE.md)
  8. validate and persist candidate to candidates.jsonl
  9. on invalid/ambiguous output → DEFER (write to deferred.jsonl)
  10. on success → write discovery packet to registry-for-review/discovery-packets/
```

### 3.4 Capacity establishment protocol (canary → wave → scale)

| Phase | Concurrency | Agents | Task | Success criterion |
|---|---|---|---|---|
| Canary (Wave 0) | 1 | 1 worker-free | Fetch source page 0, parse SKILL.md, produce discovery packet | Packet validated against discovery-packet-v2 schema |
| Wave 1 | 2 | 2 worker-free | Fetch source pages 1–2, same pipeline | Both packets validated |
| Full scale | 16 | 16 worker-free | All 16 shards in parallel | All shards complete or fail gracefully |

### 3.5 Shard-to-source mapping (16 shards)

| Shard | Source | Page | Lane |
|---|---|---|---|
| shard-00 | marketplace-01 | page 1 | marketplace |
| shard-01 | marketplace-02 | page 1 | marketplace |
| shard-02 | source-repo-01 | page 1 | source-repository |
| shard-03 | github-topic-01 | page 1 | github-topic |
| shard-04 | marketplace-01 | page 2 | marketplace |
| shard-05 | marketplace-02 | page 2 | marketplace |
| shard-06 | source-repo-01 | page 2 | source-repository |
| shard-07 | github-topic-01 | page 2 | github-topic |
| shard-08 | marketplace-01 | page 3 | marketplace |
| shard-09 | marketplace-02 | page 3 | marketplace |
| shard-10 | source-repo-01 | page 3 | source-repository |
| shard-11 | github-topic-01 | page 3 | github-topic |
| shard-12 | marketplace-01 | page 4 | marketplace |
| shard-13 | marketplace-02 | page 4 | marketplace |
| shard-14 | source-repo-01 | page 4 | source-repository |
| shard-15 | github-topic-01 | page 4 | github-topic |

---

## 4. Output Artifact Specification

### 4.1 Working directory (transient, per run)

```
generated-output/curate-discovery/trending-16-seeds-001/
├── run.json
├── source-snapshots.json
├── candidates.jsonl
├── decisions.jsonl
├── deferred.jsonl
└── L4-REVIEW.md
```

### 4.2 Discovery packets (immutable record)

```
registry-for-review/discovery-packets/
├── discovery-packet-001.json
├── discovery-packet-002.json
├── ...
└── discovery-packet-016.json
```

Each packet follows `discovery-packet-v2` schema with these key fields:

| Field | Required | Purpose |
|---|---|---|
| `contractVersion` | yes | `"discovery-packet-v2"` |
| `candidateId` | yes | e.g. `trending-001` |
| `lifecycle` | yes | `["discovered","fetched","parsed","normalized","deduped","mapped","review-ready"]` |
| `source` | yes | `{ sourceId, lane, page, url, observedAt }` |
| `normalized` | yes | `{ id, name, description, attribution, prerequisites, type }` |
| `exactDedupe` | yes | `{ normalizedRepoPath, canonicalUrl, contentHash }` |
| `mappingOptions` | yes | ≤3 options with `genericId`, `confidence`, `reason` |
| `decision` | yes | `{ value: "review-ready", reasonCode, genericId? }` |
| `evidence` | yes | ≥1 entry with `grade: "B"`, `type`, `url`, `notes` |
| `flags` | yes | Array of string tags |
| `band` | yes | `HOT \| RISING \| NEW \| STEADY \| UNKNOWN` |

### 4.3 Batch intake artifact

```
registry-for-review/skill-batches/
└── 20260711150000-trending-16-seeds.json
```

Top-level schema:

| Key | Type | Purpose |
|---|---|---|
| `batchId` | string | Timestamp-prefixed unique ID |
| `userId` | string | `"gaia-curate-dynamic"` |
| `sourceRepo` | string | `"gaia-research/gaia-skill-tree"` |
| `generatedAt` | string | ISO 8601 |
| `fromFile` | boolean | `true` |
| `proposedSkills[]` | array | 16 curation seed entries |
| `similarity[]` | array | Lexical overlap with existing skills |

Each `proposedSkills[]` entry:

| Field | Required | Constraint |
|---|---|---|
| `id` | yes | kebab-case, no vendor names |
| `name` | yes | Human-readable |
| `type` | yes | `"basic"` or `"fusion"` |
| `prerequisites` | yes | `[]` for basic |
| `description` | yes | ≥10 chars, precise, falsifiable |
| `attribution` | yes | `{ upstream_author, skill_file_url (blob/), type: "attributed" }` |
| `evidence` | yes | ≥1 entry, `grade: "B"` or higher |
| `sourceRepo` | yes | `"gaia-research/gaia-skill-tree"` |
| `lifecycle` | yes | `"pending"` |

### 4.4 Mapping between working artifacts and registry directories

| Working artifact | Path | Purpose |
|---|---|---|
| Raw candidates | `generated-output/curate-discovery/trending-16-seeds-001/candidates.jsonl` | All parsed SKILL.md leads |
| Decisions | `generated-output/curate-discovery/trending-16-seeds-001/decisions.jsonl` | Per-candidate mapping decisions |
| Deferred | `generated-output/curate-discovery/trending-16-seeds-001/deferred.jsonl` | Ambiguous/invalid outputs |
| L4 review | `generated-output/curate-discovery/trending-16-seeds-001/L4-REVIEW.md` | Human-readable summary of all 16 seeds |
| Run metadata | `generated-output/curate-discovery/trending-16-seeds-001/run.json` | Run parameters, concurrency stats |
| Source snapshots | `generated-output/curate-discovery/trending-16-seeds-001/source-snapshots.json` | 7-day and 30-day trend observations |
| Discovery packets | `registry-for-review/discovery-packets/discovery-packet-NNNN.json` | One per review-ready candidate |
| Batch intake | `registry-for-review/skill-batches/20260711150000-trending-16-seeds.json` | Immutable batch record for intake issue |

---

## 5. Integration Steps

### Step 1: Create preflight configuration

**File:** `.agents/skills/gaia-curate-dynamic/preflight.json`
**Content:** As specified in Section 1.
**Action:** Write the file. Read-only infrastructure.

### Step 2: Create the source manifest

**File:** `registry-for-review/discovered-artifacts/trending-manifest.yaml`
**Content:** As specified in Section 2.
**Action:** Write the file. Create directory if needed.

### Step 3: Create the working directory structure

**Directory:** `generated-output/curate-discovery/trending-16-seeds-001/`
**Action:** Create directory with `.gitkeep`.

### Step 4: Wire the orchestration script

**File:** `.agents/skills/gaia-curate-dynamic/scripts/run-trending-16.sh`
**Purpose:** Entry point — reads preflight, loads manifest, computes 16 shards, runs canary → wave → full dispatch, validates 16 packets, assembles batch JSON.
**Action:** Write the shell script.

### Step 5: Create the discovery packet validator

**File:** `.agents/skills/gaia-curate-dynamic/scripts/validate-packets.py`
**Purpose:** Validates that each discovery packet conforms to `discovery-packet-v2` schema and that exactly 16 packets are in `review-ready` state.
**Action:** Write the Python script.

### Step 6: Create the batch assembler

**File:** `.agents/skills/gaia-curate-dynamic/scripts/assemble-batch.py`
**Purpose:** Collects 16 review-ready discovery packets and produces the batch JSON for `registry-for-review/skill-batches/`.
**Action:** Write the Python script.

### Step 7: Update the curate-dynamic SKILL.md (if needed)

**File:** `.agents/skills/gaia-curate-dynamic/SKILL.md`
**Action:** No modification required. The existing skill already supports preflight configuration, worker tiers, sharding, and discovery-only constraints.

### Step 8: Verify the intake pipeline end-to-end (dry run)

**Command:** `gaia push --from-file registry-for-review/discovered-artifacts/trending-manifest.yaml --dry-run`

---

## 6. Risk Notes

| Risk | Mitigation |
|---|---|
| Fewer than 16 seeds survive dedup | Over-provision to 80 raw leads; expect ~40 unique → ≥16 after mapping filter |
| One source goes down | 4 sources across 3 lanes; loss of 1 lane = 3 lanes × 4 pages = 60 leads |
| Worker-free subagent produces invalid output | One Luna High repair attempt per shard; invalid → DEFER (not retry loop) |
| 429/overload from target sites | Concurrency reduced on 429; retry at most twice with backoff |
| `kilo-auto/free:medium` model unavailable | Fallback: run sequentially and scale back up |
| `workflow` tool `concurrency` not respected | Validate via `observedConcurrency` in `preflight.json` after run |

---

## 7. Summary of All Files to Create

| # | File | Purpose |
|---|---|---|
| 1 | `.agents/skills/gaia-curate-dynamic/preflight.json` | Runtime config for concurrency=16, worker-free, claude-code |
| 2 | `registry-for-review/discovered-artifacts/trending-manifest.yaml` | Source manifest for 16-seed trending run |
| 3 | `generated-output/curate-discovery/trending-16-seeds-001/.gitkeep` | Working directory placeholder |
| 4 | `.agents/skills/gaia-curate-dynamic/scripts/run-trending-16.sh` | Orchestration entry point |
| 5 | `.agents/skills/gaia-curate-dynamic/scripts/validate-packets.py` | Discovery packet validator |
| 6 | `.agents/skills/gaia-curate-dynamic/scripts/assemble-batch.py` | Batch JSON assembler |
| 7 | `.agents/skills/gaia-curate-dynamic/TRENDING-SETUP-PLAN.md` | This plan document |

No existing files need modification. The plan is additive — it writes new configuration, manifests, scripts, and directory structures without touching any committed registry data or skill definitions.

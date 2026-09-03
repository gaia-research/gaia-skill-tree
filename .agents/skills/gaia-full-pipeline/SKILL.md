---
name: gaia-full-pipeline
description: >-
  End-to-end Gaia curation pipeline orchestrator. Routes each phase to its dedicated
  skill and keeps you on track from first discovery to closed intake. Use when starting
  a fresh curation run or when you want a single skill to hold the sequence together
  without duplicating each phase's instructions. Trigger phrases: "/gaia-full-pipeline",
  "run the full pipeline", "start a curation from scratch", "take this skill through
  the full pipeline", "curate end-to-end", "pipeline run", "full curation flow".
  Fused from: gaia-curate + gaia-curate-chain + gaia-curate-dynamic + gaia-curate-trending
  + gaia-bot-curate + gaia-draft-curate + ev-pipeline + gaia-ingest + gaia-intake-close.
version: 2.0.0
---

> **Have one repo URL and want full automation?** Run [/gaia-quick-curate](../gaia-quick-curate/SKILL.md) — 2 human gates, auto-merge. This document is the **manual reference** explaining what runs inside each gate.

# gaia-full-pipeline

Orchestrates the complete curation lifecycle. Each phase delegates to its canonical skill — this skill is the **routing layer**, not the implementation. Read the referenced skill for the exact commands at each phase.

> **Lost at any point?** Run `/gaia-consult` to open the reference document with the exact command for your current phase.

---

## Phase 1 — Choose a discovery strategy

The pipeline starts differently depending on whether you already know *what* you're curating or need to find it first. Pick exactly one path. All strategies stop at L4 — none touch the registry.

### Strategy decision guide

| You want to… | Use |
|---|---|
| Curate **one specific skill** you already have the URL for | [`/gaia-curate`](#strategy-a) |
| Curate a **small batch of up to ~5** where recoverability matters (each step checkpointed, retries on failure) | [`/gaia-curate-chain`](#strategy-b) |
| Curate a **large or broad batch** with parallelism across multiple candidates (fan-out to Luna workers) | [`/gaia-curate-dynamic`](#strategy-c) |
| **Discover what's trending** — you don't have a specific skill in mind, you want to see what's hot on configured marketplaces/repos | [`/gaia-curate-trending`](#strategy-d) |
| Process **bot crawler output** already sitting in `bot/*` branches | [`/gaia-bot-curate`](#strategy-e) |
| Review **pending `gaia push` intake batches** in `registry-for-review/` that someone else already submitted | [`/gaia-draft-curate`](#strategy-f) |

> **Rule of thumb:** if you're declaring ("I want to curate this skill at this URL"), use A or B. If you're discovering ("show me what exists"), use D. If you're processing a queue, use E or F.

---

### Strategy A — `/gaia-curate` · Single declared skill {#strategy-a}

**When:** You have one specific upstream `SKILL.md` URL. Lowest overhead.

**Depth:** One candidate. No parallelism. No checkpointing.

**Breadth:** 1 skill per run.

```
gaia dev list --generic --json > /tmp/generic-snapshot.json
gaia dev prefill --source "<blob-url>" --output /tmp/prefill-output.json
# … write discovery-packet-v2 JSON …
python3 scripts/validate_discovery_packet.py \
  --generic-snapshot /tmp/generic-snapshot.json <packet>.json
# → Stop at L4
```

→ Full commands: [`/gaia-curate`](../gaia-curate/SKILL.md) · [`CURATION-CORE.md`](../gaia-curate/CURATION-CORE.md)

---

### Strategy B — `/gaia-curate-chain` · Small batch, checkpointed {#strategy-b}

**When:** You have 2–10 candidates and want recoverability. Each candidate transition is atomically checkpointed; a failed field retries in isolation without restarting the whole batch. Good for higher-risk or unfamiliar sources where you expect some defers.

**Depth:** One candidate at a time, sequentially. Max 2 transient-fetch retries, 1 Luna High repair per candidate.

**Breadth:** Small batch. Checkpointed run ledger under `generated-output/curate-discovery/<run-id>/run.json`.

```
/gaia-curate-chain <source-or-small-batch>
# Checkpoints each candidate → validates → persists to registry-for-review/discovery-packets/
# On failure: emits DEFER with exact resume instruction (candidate ID, failed field, next command)
# → Stop at L4
```

→ Full protocol: [`/gaia-curate-chain`](../gaia-curate-chain/SKILL.md)

---

### Strategy C — `/gaia-curate-dynamic` · Large batch, parallel workers {#strategy-c}

**When:** You have a broad source manifest (many repos, a marketplace page, a topic) and want throughput. A Sol/Terra orchestrator shards work to Luna Light harvesters and mappers. Adversarial review only for risky candidates (NEW_GENERIC, fusion proposals, attribution conflicts).

**Depth:** Adversarial review for risky cases only (proposer/refuter isolated passes). Safe/straightforward candidates skip adversarial cost.

**Breadth:** Large batch. Configurable concurrency. Resumable cost log in `usage.jsonl`. Effective concurrency = min(requested, observed harness capacity, remaining shards, budget).

```
/gaia-curate-dynamic <broad-source-manifest>
# Preflight → capacity canary → shard → harvest → map → [adversarial for risky] → assemble → L4
# State: generated-output/curate-discovery/<run-id>/
# → Stop at L4
```

**Note:** Requires configured harness binary (`CLAUDE_BIN`, `CODEX_BIN`, or `HERMES_BIN`). Runs sequentially if concurrency cannot be established.

→ Full protocol: [`/gaia-curate-dynamic`](../gaia-curate-dynamic/SKILL.md)

---

### Strategy D — `/gaia-curate-trending` · Discover what's trending {#strategy-d}

**When:** You don't have a specific skill in mind. You want to snapshot configured external skill sources (marketplaces, GitHub topics, model hubs) and surface the top candidates by trend band. Best for periodic sweeps or identifying what to curate next.

**Depth:** Trend bands only (`HOT`, `RISING`, `NEW`, `STEADY`, `UNKNOWN`) — mechanical, never a model judgment. No evidence scoring, no TM, no trust signal.

**Breadth:** Up to 5 candidates per source page, all configured sources in the run manifest. Resumable with `RESUME <run-id>`.

```
/gaia-curate-trending <source-manifest-or-run-id>
# Snapshot → trend-band → fetch SKILL.md → dedupe → map → L4-REVIEW.md
# State: generated-output/curate-discovery/<run-id>/
# → Stop at L4
```

**Operator controls:** `NEXT` (advance to next candidate), `STOP` (write resumable checkpoint), `RESUME <run-id>`.

→ Full protocol: [`/gaia-curate-trending`](../gaia-curate-trending/SKILL.md)

---

### Strategy E — `/gaia-bot-curate` · Process bot crawler branches {#strategy-e}

**When:** The automated crawler has already run and left `bot/*` branches on the remote. You are processing crawl output — filtering, accepting, rejecting, integrating — not discovering new skills yourself.

**Depth:** Human-in-the-loop filtration per candidate. Fusion analysis included (does it combine capabilities in a novel way?). Demerit assignment at 3★+.

**Breadth:** All pending `bot/*` branches in one run. Narrows by source type (github, vscode-marketplace, huggingface) for triage.

```
git fetch --all --prune
git for-each-ref refs/remotes/origin/bot   # list branches
# Triage → accept/reject/needs-evidence → gaia dev add/evidence/calibrate
# Delete consumed bot branches after review branch exists
gaia dev docs && gaia dev validate
gh pr create ...
```

**Key difference from other strategies:** this is the only strategy that runs `gaia dev add` and mutates the registry directly during curation — it is not discovery-only.

→ Full protocol: [`/gaia-bot-curate`](../gaia-bot-curate/SKILL.md)

---

### Strategy F — `/gaia-draft-curate` · Review pending gaia push batches {#strategy-f}

**When:** Someone has already run `gaia push` and proposals are sitting in `registry-for-review/skill-batches/`. You are the intake gate deciding which proposals move forward.

**Depth:** Read-only triage — accept, rename, duplicate, needs-evidence, or reject. No registry mutation. Hands off to `/gaia-curate-chain` or `/gaia-curate` for accepted proposals.

**Breadth:** All pending batches in `registry-for-review/skill-batches/*.json`.

```
git status --short --branch
python3 scripts/validate_intake.py
gh issue list --state open --search 'label:intake'
# Review decision table → produce handoff packet
# → Hand accepted to /gaia-curate-chain or /gaia-curate
```

→ Full protocol: [`/gaia-draft-curate`](../gaia-draft-curate/SKILL.md)

---

## Phase 2 — L4 Human Gate 🛑

**No skill — human only. All strategies converge here.**

Every strategy stops after producing review-ready `discovery-packet-v2` files in `registry-for-review/discovery-packets/`. (Exception: `/gaia-bot-curate` may go directly to registry mutation — re-read its protocol.)

For strategies A–D and F, L4 means:
1. Open each packet JSON. Verify mapping decision, `blob/` URL, verbatim description.
2. Append `l4Resolution` with ratified `generic`, `named`, and `upstreamSkillFileUrl`.
3. Re-validate: `python3 scripts/validate_discovery_packet.py --generic-snapshot /tmp/generic-snapshot.json <packet>.json`

---

## Phase 3 — Branch + Push + PR

**Skills:** [`/pr`](../pr/SKILL.md)

```bash
git checkout -b review/meta/<handle>--<skill>
gaia push --from-file <packet>.json --dry-run   # preview
gaia push --from-file <packet>.json             # opens intake issue (auto-labels: intake + needs-triage)
git add . && git commit -m "feat(intake): ..." && git push -u origin <branch>
gh pr create --draft --title "..." --body-file /tmp/pr-body.md
```

### `intake:*` label lifecycle — machine gates, applied in order

| Label | Applied to | Who applies | What it triggers |
|---|---|---|---|
| `intake` | Issue + PR | Auto (`gaia push`) or you | Routes into the intake queue |
| `needs-triage` | Issue | Auto (`gaia push`) | Marks as awaiting review |
| `intake:topology-approved` | Issue | **Maintainer only** | Workflow fires: adds `intake:evidence-review`, removes `needs-triage`, posts handoff comment |
| `intake:evidence-review` | Issue | Auto (workflow) | Signals agent to prepare Stage-1 seed + Phase-0 plan |
| `intake:evidence-ready` | Issue | Agent / you | Signals evidence plan is ready for human approval |
| `intake:evidence-approved` | Issue | **Maintainer only** | Workflow fires: opens single draft `review/meta/intake-<N>` PR |
| `intake:rejected` | Issue | **Maintainer only** | Closes intake; no automation fires |
| `human-proposal` | PR | Auto (triage workflow) | Routes non-bot PR for human review |
| `needs-review` | PR | Auto (triage workflow) | Signals PR needs a reviewer |

> **Gate constraint:** `intake:evidence-approved` requires *both* `intake:evidence-review` and `intake:evidence-ready` to already be present — the workflow errors if either is missing. `intake:topology-approved` and `intake:evidence-approved` are rejected by the workflow if the actor is not `admin`/`maintain`/`write`.

```bash
# Auto-triage usually applies PR labels, but if not:
gh pr edit <PR> --add-label "intake" --add-label "human-proposal" --add-label "needs-review"

# When ready to approve topology (maintainer only):
gh issue edit <ISSUE> --add-label "intake:topology-approved"
# ↑ fires intake-approval.yml — watch it:
gh run list --workflow=intake-approval.yml
```

---

## Phase 4 — Evidence Verification

**Skill:** [`/ev-pipeline`](../ev-pipeline/SKILL.md)

| Sub-phase | Skill | Skip when |
|---|---|---|
| Phase 0 — ev-discovery | [`/ev-discovery`](../ev-discovery/SKILL.md) | Stage-1 intakes; only run for promotion candidates needing `benchmark-result`, `arxiv`, or `peer-review` |
| Phase 1 — ev-collection | [`/ev-collection`](../ev-collection/SKILL.md) | Never — rebuilds the **whole-registry** lake |
| Phase 2 — ev-star-verification | [`/ev-star-verification`](../ev-star-verification/SKILL.md) | No `github-stars-own` rows |
| Phase 2B — ev-benchmark-verification | [`/ev-benchmark-verification`](../ev-benchmark-verification/SKILL.md) | No `benchmark-result` rows |
| Phase 3 — ev-adversarial-audit | [`/ev-adversarial-audit`](../ev-adversarial-audit/SKILL.md) | Never |
| Phase 4 — ev-link-validation | [`/ev-link-validation`](../ev-link-validation/SKILL.md) | Never |

**Human gate:** Review source report. Approve rows. Remove dead-link, subjective, or type-mismatched rows before ingest.

---

## Phase 5 — Evidence Ingest

**Skill:** [`/gaia-ingest`](../gaia-ingest/SKILL.md) (single row) · [`/gaia-ingest-batch`](../gaia-ingest-batch/SKILL.md) (multiple rows)

```bash
GAIA_OPERATOR_OVERRIDE=1 gaia dev evidence contributor/skill "<url>" \
  --type <evidence-type> <numeric-flags> \
  --notes "..." --source-started-at YYYY-MM-DD --no-build
# … repeat per row …
GAIA_OPERATOR_OVERRIDE=1 gaia dev build
PYTHONPATH=src python3 scripts/trust_appraise.py --skill contributor/skill
# → Human approves calibration
GAIA_OPERATOR_OVERRIDE=1 gaia dev calibrate contributor/skill --stars N
GAIA_OPERATOR_OVERRIDE=1 gaia dev validate
```

Trust Magnitude → star grade:

| Grade | TM | Max stars |
|---|---|---|
| D | 1.0–1.9 | 1★ |
| C | 2.0–3.9 | 2★ (badge floor) |
| B | 4.0–6.9 | 3★ |
| A | 7.0–9.9 | 4★ |
| S | 10.0+ | 5★–6★ |

→ Methodology: [`/trust-methodology-consult`](../trust-methodology-consult/SKILL.md)

---

## Suite detour — between Phase 5 and Phase 6 🔀

Run only when the intake is a **suite capstone** (contributor has 3+ named skills being fused).

**Skill:** [`/gaia-fuse-full-suite`](../gaia-fuse-full-suite/SKILL.md)

```bash
ls registry/named/<contributor>/        # confirm all components exist
gaia dev fuse <fusion-id> \
  --name "<Fusion Name>" \
  --description "<one-sentence synthesis>" \
  --prereqs <id-1>,<id-2>,... \
  --named-capstone <contributor>/<capstone-slug> \
  --suite-components <named-id-1>,<named-id-2>,...
GAIA_OPERATOR_OVERRIDE=1 gaia dev validate
```

Suite rank gates (TM is sole gate):
- **4★ Extra** — Origin Contributor recorded + TM ≥ 100
- **5★ Ultimate** — Origin in `suiteComponents` + 5 A-graded origins + TM ≥ 250
- **6★ Apex** — full 6-predicate Apex Gate (see `META.md`)

---

## Phase 6 — Close

**Skill:** [`/gaia-intake-close`](../gaia-intake-close/SKILL.md)

```bash
gh pr ready <PR>
gh pr checks <PR>                                   # wait for green
gh pr merge <PR> --subject "feat(registry): ... [closes #ISSUE]"
gh pr comment <PR> --body-file /tmp/pr-close-comment.md
gh issue comment <ISSUE> --body-file /tmp/issue-close-comment.md
gh issue close <ISSUE>
GAIA_OPERATOR_OVERRIDE=1 gaia dev docs             # regenerate Class S artifacts
```

---

## Re-entry map — jumping back in mid-pipeline

| Where you are | Invoke |
|---|---|
| Single declared skill | `/gaia-curate` |
| Small batch, need recoverability | `/gaia-curate-chain` |
| Large batch, need parallelism | `/gaia-curate-dynamic` |
| Want to discover trending skills | `/gaia-curate-trending` |
| Processing bot crawler branches | `/gaia-bot-curate` |
| Reviewing pending gaia push batches | `/gaia-draft-curate` |
| Post-L4, ready to push | `/pr` |
| Evidence collection only | `/ev-collection` |
| Star verification only | `/ev-star-verification` |
| Adversarial audit only | `/ev-adversarial-audit` |
| Link validation only | `/ev-link-validation` |
| Single evidence row | `/gaia-ingest` |
| Batch evidence rows | `/gaia-ingest-batch` |
| Suite fusion only | `/gaia-fuse-full-suite` |
| Closing comments only | `/gaia-intake-close` |
| Regenerate artifacts only | `/regen` or `/gaia-docs-sync` |
| Lost / unsure of command | `/gaia-consult` |

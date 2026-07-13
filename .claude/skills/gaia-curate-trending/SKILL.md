---
name: gaia-curate-trending
description: >-
  Discovery-only global trending extension for Gaia. Snapshots configured
  external skill sources, prioritizes five-candidate pages for L4 review, and
  stops before trust, evidence, intake, or registry mutation.
version: 1.0.0
argument-hint: "<source-manifest-or-run-id>"
---

# Gaia Curate Trending

Read `../gaia-curate/CURATION-CORE.md` first. This ranks what reviewers should inspect now. It is external discovery, not Gaia's internal Trending API, not evidence, and not a trust signal. “Global” means every configured public source in the run manifest; never claim exhaustive web coverage.

## Source manifest

Require a versioned manifest with bounded lanes and cursors:

```yaml
contractVersion: curate-trending-manifest-v1
windowDays: [7, 30]
pageSize: 5
sources:
  - id: source-id
    lane: marketplace | source-repository | github-topic
    url: https://...
    cursor: null
```

Real marketplaces and source repositories are primary lanes. Package registries, MCP directories, model hubs, and extension listings are lead sources only: quarantine each lead until it resolves to an actually fetched upstream `SKILL.md` that passes the core artifact gate. Unknown sources become `newSourceSuggestions`; discovery must not edit `registry/skill-sources.md`.

## Snapshot and trend bands

Persist source-native observations for 7-day and 30-day windows: observed time, source rank/label, first-seen time, listing or download delta when exposed, repository star delta when exposed, and cross-source recurrence. Repository stars may prioritize inspection but are never inherited as implementation evidence or used for TM.

Assign one band mechanically in this priority order:

1. `HOT`: the source explicitly labels the artifact trending/top and it recurs on another configured source during the window.
2. `RISING`: a comparable prior snapshot exists and at least one source-native rank/download/star delta is positive.
3. `NEW`: first observed inside the selected window and neither higher band applies.
4. `STEADY`: comparable snapshots exist with no positive trend signal.
5. `UNKNOWN`: comparable history is missing, contradictory, or unavailable.

Store the raw observations and rule that produced the band. Never ask a model to calculate the band and never convert it to evidence, grade, class, star level, TM, or acceptance.

## Manual page loop

Process at most five candidates per source page, and exactly one active candidate per model turn:

1. fetch the source page and persist its next cursor;
2. resolve each lead to a canonical repository path and immutable commit when possible;
3. fetch and parse the real `SKILL.md`;
4. exact-dedupe by normalized repository/path, canonical URL, cited origin, and content hash;
5. query the generic snapshot and supply at most three mapping options;
6. request one bounded core decision;
7. validate and persist before advancing;
8. on invalid/ambiguous output, `DEFER`; never infer acceptance.

Allowed human/operator controls are `NEXT`, `STOP`, `RESUME <run-id>`, and one core decision for the active candidate. `STOP` writes a resumable checkpoint; it does not discard completed packets.

## Output and handoff

Write only under `generated-output/curate-discovery/<run-id>/`:

```text
run.json
source-snapshots.json
candidates.jsonl
decisions.jsonl
deferred.jsonl
L4-REVIEW.md
```

`L4-REVIEW.md` lists candidate, trend band, source, existing-generic mapping, bounded disposition, and flags. Validate every row as `discovery-packet-v1` and stop at L4. A shortlist decision is not intake, evidence, named-star, or mutation approval. A separate downstream workflow must perform those stages.

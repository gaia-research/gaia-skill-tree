# Trending mode

Use to prioritize what reviewers inspect now across configured public sources.
This is external discovery, not Gaia's internal Trending API, evidence, or a
trust signal. “Global” means all configured sources in this run, never exhaustive
web coverage.

Require a versioned, bounded manifest:

```yaml
contractVersion: curate-trending-manifest-v1
windowDays: [7, 30]
pageSize: 5
sources:
  - id: source-id
    lane: marketplace | source-repository | github-topic
    url: https://example.com/source
    cursor: null
```

Marketplaces and source repositories are primary lanes. Package registries,
directories, model hubs, and extension listings are leads only; quarantine each
until it resolves to an actually fetched upstream `SKILL.md`. Unknown sources
become `newSourceSuggestions`; do not edit `registry/skill-sources.md`.

Persist observed time, native rank/label, first-seen time, available listing,
download, or star deltas, and cross-source recurrence for 7- and 30-day windows.
Assign the first matching band mechanically:

1. `HOT`: source labels it trending/top and it recurs on another configured source.
2. `RISING`: comparable history exists and at least one native delta is positive.
3. `NEW`: first observed inside the window and neither higher band applies.
4. `STEADY`: comparable snapshots exist with no positive trend signal.
5. `UNKNOWN`: history is missing, contradictory, or unavailable.

Store the raw observations and matched rule. Never ask a worker to calculate a
band or convert it into evidence, grade, class, rank, TM, or acceptance.

Process at most five candidates per source page, one active candidate per
decision. Capture the generic snapshot once before the first page and reuse its
digest across every page and checkpoint in the run. `NEXT`, `STOP`, and
`RESUME <run-id>` are the operator controls;
`STOP` writes a resumable checkpoint. Runtime outputs are `run.json`,
`source-snapshots.json`, `candidates.jsonl`, `decisions.jsonl`, `deferred.jsonl`,
and `L4-REVIEW.md` under the run directory. Copy only validator-accepted packets
to the shared review path, present the L4 shortlist, and stop.
